use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::fd::{AsRawFd, RawFd};
use std::os::unix::fs::DirBuilderExt;
use std::os::unix::fs::PermissionsExt;
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, mpsc};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

const REQUEST_MAX_BYTES: u64 = 1024 * 1024;
const OUTPUT_MIN_BYTES: u64 = 1024 * 1024;
const OUTPUT_MAX_BYTES: u64 = 16 * 1024 * 1024;
const FRAME_MAX_BYTES: usize = 64 * 1024;
const TIMEOUT_MAX_MS: u64 = 3_600_000;
const ID_MAX_BYTES: usize = 64;
const STOP_MAX_BYTES: usize = 128;
const INPUT_MAX_COUNT: usize = 256;
const INPUT_MAX_BYTES: u64 = 1 << 50;
const COMMAND_MAX_COUNT: usize = 256;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RunRequest {
    pub schema_version: u32,
    pub attempt_id: String,
    pub scenario_id: String,
    pub profile_id: String,
    pub backend: BackendIdentity,
    pub expected_stop_condition: String,
    pub timeout_ms: u64,
    pub stdout_limit_bytes: u64,
    pub stderr_limit_bytes: u64,
    pub input_identities: Vec<InputIdentity>,
    pub commands: Vec<RunCommand>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BackendIdentity {
    pub kind: BackendKind,
    pub source_revision: String,
    pub expected_executable_sha256: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BackendKind {
    #[serde(rename = "bosman-native")]
    BosmanNative,
    #[serde(rename = "synthetic-test")]
    SyntheticTest,
}

impl BackendKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::BosmanNative => "bosman-native",
            Self::SyntheticTest => "synthetic-test",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InputIdentity {
    pub sha256: String,
    pub byte_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RunCommand {
    pub id: String,
    pub kind: String,
    #[serde(default)]
    pub parameters: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct BosmanSameSaveParameters {
    pub mode: String,
    pub days: u32,
    pub jobs: u32,
    pub runs: Vec<String>,
    pub seed: u32,
    pub fixed_clock: bool,
    pub expected_save_relation: String,
    pub input_slots: BosmanInputSlots,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct BosmanInputSlots {
    pub bosman_executable: usize,
    pub clean_manifest: usize,
    pub smoke_runner: usize,
    pub python_interpreter: usize,
}

#[derive(Debug, Serialize)]
struct ValidationReport<'a> {
    schema_version: u32,
    status: &'static str,
    request_sha256: &'a str,
    attempt_id: &'a str,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ProtocolFrame {
    protocol_version: u32,
    attempt_id: String,
    sequence: u64,
    kind: String,
    payload: Value,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct TerminalPayload {
    execution_status: String,
    reason: String,
    stop_condition: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct HandshakePayload {
    backend_kind: String,
    source_revision: String,
    executable_sha256: String,
    capabilities: Vec<String>,
}

#[derive(Debug, Serialize)]
struct ReplayManifest<'a> {
    schema_version: u32,
    request_sha256: &'a str,
    attempt_id: &'a str,
    scenario_id: &'a str,
    profile_id: &'a str,
    backend: ReplayBackend<'a>,
    input_identities: &'a [InputIdentity],
    command_stream_sha256: String,
    command_count: usize,
    expected_stop_condition: &'a str,
    limits: ReplayLimits,
    execution: ReplayExecution<'a>,
    comparison_verdict: &'static str,
    artifacts: ReplayArtifacts,
}

#[derive(Debug, Serialize)]
struct ReplayBackend<'a> {
    kind: &'static str,
    source_revision: &'a str,
    executable_sha256: &'a str,
}

#[derive(Debug, Serialize)]
struct ReplayLimits {
    timeout_ms: u64,
    stdout_bytes: u64,
    stderr_bytes: u64,
}

#[derive(Debug, Serialize)]
struct ReplayExecution<'a> {
    status: &'static str,
    reason: &'static str,
    stop_condition: &'a str,
    exit_code: i32,
}

#[derive(Debug, Serialize)]
struct ReplayArtifacts {
    request: ArtifactIdentity,
    stdout: ArtifactIdentity,
    stderr: ArtifactIdentity,
}

#[derive(Debug, Serialize)]
struct ArtifactIdentity {
    file_name: &'static str,
    byte_count: usize,
    sha256: String,
}

pub fn validate_request_file(path: &Path) -> Result<String, String> {
    let request = read_and_validate_request(path)?;
    let canonical_request = serde_json::to_vec(&request)
        .map_err(|error| format!("serialize validated request: {error}"))?;
    let request_sha256 = digest_bytes(&canonical_request);
    let report = ValidationReport {
        schema_version: 1,
        status: "valid",
        request_sha256: &request_sha256,
        attempt_id: &request.attempt_id,
    };
    serde_json::to_string(&report).map_err(|error| format!("serialize validation report: {error}"))
}

pub fn execute_process(
    request_path: &Path,
    backend_executable: &Path,
    backend_config: Option<&Path>,
    attempt_dir: &Path,
) -> Result<(), String> {
    let request = read_and_validate_request(request_path)?;
    let backend_config = match (request.backend.kind, backend_config) {
        (BackendKind::BosmanNative, Some(path)) => Some(
            path.canonicalize()
                .map_err(|error| format!("resolve private backend config: {error}"))?,
        ),
        (BackendKind::BosmanNative, None) => {
            return Err("bosman-native execution requires --backend-config".to_owned());
        }
        (BackendKind::SyntheticTest, Some(_)) => {
            return Err("synthetic-test execution rejects --backend-config".to_owned());
        }
        (BackendKind::SyntheticTest, None) => None,
    };
    if let Some(path) = &backend_config
        && !path
            .metadata()
            .map_err(|error| format!("inspect private backend config: {error}"))?
            .is_file()
    {
        return Err("private backend config must be a regular file".to_owned());
    }
    let executable = backend_executable
        .canonicalize()
        .map_err(|error| format!("resolve backend executable: {error}"))?;
    let mut executable_file =
        File::open(&executable).map_err(|error| format!("open backend executable: {error}"))?;
    let metadata = executable_file
        .metadata()
        .map_err(|error| format!("inspect backend executable: {error}"))?;
    if !metadata.is_file() || metadata.permissions().mode() & 0o111 == 0 {
        return Err("backend executable must be an executable regular file".to_owned());
    }
    let executable_sha256 = digest_reader(&mut executable_file)?;
    if !executable_sha256.eq_ignore_ascii_case(&request.backend.expected_executable_sha256) {
        return Err(format!(
            "backend executable SHA-256 mismatch: expected {}, actual {executable_sha256}",
            request.backend.expected_executable_sha256
        ));
    }
    let canonical_request = serde_json::to_vec(&request)
        .map_err(|error| format!("serialize validated request: {error}"))?;
    let request_sha256 = digest_bytes(&canonical_request);
    let mut request_bytes = canonical_request.clone();
    request_bytes.push(b'\n');

    create_private_dir(attempt_dir, "attempt directory")?;
    let attempt_dir = attempt_dir
        .canonicalize()
        .map_err(|error| format!("resolve created attempt directory: {error}"))?;
    let mut stdout_bytes = Vec::new();
    let mut stderr_bytes = Vec::new();
    let mut exit_code = -1;
    let result = (|| -> Result<(), String> {
        let home_dir = attempt_dir.join("home");
        let temp_dir = attempt_dir.join("tmp");
        create_private_dir(&home_dir, "private HOME")?;
        create_private_dir(&temp_dir, "private temporary directory")?;

        enable_child_subreaper()?;
        let executable_descriptor = executable_file.as_raw_fd();
        let executable_path = PathBuf::from(format!("/proc/self/fd/{executable_descriptor}"));
        let mut command = Command::new(executable_path);
        command
            .current_dir(&attempt_dir)
            .env_clear()
            .env("HOME", &home_dir)
            .env("TMPDIR", &temp_dir)
            .env("TZ", "UTC")
            .env("LC_ALL", "C")
            .env("LANG", "C")
            .env("SDL_VIDEODRIVER", "dummy")
            .env("SDL_AUDIODRIVER", "dummy")
            .env("LAB_PROTOCOL_VERSION", "1")
            .env("LAB_REQUEST_TRANSPORT", "stdin-json-v1")
            .env("LAB_ATTEMPT_ID", &request.attempt_id)
            .env("LAB_SCENARIO_ID", &request.scenario_id)
            .env("LAB_PROFILE_ID", &request.profile_id)
            .env("LAB_BACKEND_KIND", request.backend.kind.as_str())
            .env("LAB_SOURCE_REVISION", &request.backend.source_revision)
            .env(
                "LAB_EXECUTABLE_SHA256",
                &request.backend.expected_executable_sha256,
            )
            .env(
                "LAB_EXPECTED_STOP_CONDITION",
                &request.expected_stop_condition,
            )
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .process_group(0);
        if let Some(path) = &backend_config {
            command.env("LAB_BACKEND_CONFIG", path);
        }

        let mut child = command
            .spawn()
            .map_err(|error| format!("spawn backend: {error}"))?;
        drop(executable_file);
        let process_group = child.id() as i32;
        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "send backend request: pipe missing".to_owned())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "capture backend stdout: pipe missing".to_owned())?;
        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| "capture backend stderr: pipe missing".to_owned())?;
        let (limit_tx, limit_rx) = mpsc::channel();
        let io_cancel = Arc::new(AtomicBool::new(false));
        let input_handle = match spawn_input(stdin, request_bytes, Arc::clone(&io_cancel)) {
            Ok(handle) => handle,
            Err(error) => {
                return Err(terminate_with_reason(process_group, &mut child, error));
            }
        };
        let stdout_handle = match spawn_capture(
            stdout,
            request.stdout_limit_bytes as usize,
            "stdout",
            limit_tx.clone(),
            Arc::clone(&io_cancel),
        ) {
            Ok(handle) => handle,
            Err(error) => {
                let error = terminate_with_reason(process_group, &mut child, error);
                io_cancel.store(true, Ordering::Release);
                let _ = join_input(input_handle);
                return Err(error);
            }
        };
        let stderr_handle = match spawn_capture(
            stderr,
            request.stderr_limit_bytes as usize,
            "stderr",
            limit_tx,
            Arc::clone(&io_cancel),
        ) {
            Ok(handle) => handle,
            Err(error) => {
                let error = terminate_with_reason(process_group, &mut child, error);
                io_cancel.store(true, Ordering::Release);
                let _ = join_input(input_handle);
                stdout_bytes = join_capture(stdout_handle).unwrap_or_default();
                return Err(error);
            }
        };

        let deadline = Instant::now() + Duration::from_millis(request.timeout_ms);
        let status = loop {
            if let Ok(stream) = limit_rx.try_recv() {
                let error = terminate_with_reason(
                    process_group,
                    &mut child,
                    format!("backend {stream} exceeded its configured byte limit"),
                );
                io_cancel.store(true, Ordering::Release);
                let _ = join_input(input_handle);
                stdout_bytes = join_capture(stdout_handle).unwrap_or_default();
                stderr_bytes = join_capture(stderr_handle).unwrap_or_default();
                return Err(error);
            }
            match child.try_wait() {
                Err(error) => {
                    let error = terminate_with_reason(
                        process_group,
                        &mut child,
                        format!("wait for backend: {error}"),
                    );
                    io_cancel.store(true, Ordering::Release);
                    let _ = join_input(input_handle);
                    stdout_bytes = join_capture(stdout_handle).unwrap_or_default();
                    stderr_bytes = join_capture(stderr_handle).unwrap_or_default();
                    return Err(error);
                }
                Ok(Some(status)) => break status,
                Ok(None) if Instant::now() >= deadline => {
                    let error = terminate_with_reason(
                        process_group,
                        &mut child,
                        format!("backend timed out after {} ms", request.timeout_ms),
                    );
                    io_cancel.store(true, Ordering::Release);
                    let _ = join_input(input_handle);
                    stdout_bytes = join_capture(stdout_handle).unwrap_or_default();
                    stderr_bytes = join_capture(stderr_handle).unwrap_or_default();
                    return Err(error);
                }
                Ok(None) => thread::sleep(Duration::from_millis(2)),
            }
        };
        // A child must not leave descendants holding capture pipes or mutating its attempt.
        kill_process_group(process_group);
        let cleanup_result = cleanup_adopted_children();
        io_cancel.store(true, Ordering::Release);
        let input_result = join_input(input_handle);
        let stdout_result = join_capture(stdout_handle);
        let stderr_result = join_capture(stderr_handle);
        // Join every pipe before propagating an error so the other stream survives.
        let mut capture_error = None;
        match stdout_result {
            Ok(bytes) => stdout_bytes = bytes,
            Err(error) => capture_error = Some(error),
        }
        match stderr_result {
            Ok(bytes) => stderr_bytes = bytes,
            Err(error) => capture_error = Some(error),
        }
        input_result?;
        if let Some(error) = capture_error {
            return Err(error);
        }
        exit_code = status.code().unwrap_or(-1);
        cleanup_result?;
        if let Ok(stream) = limit_rx.try_recv() {
            return Err(format!(
                "backend {stream} exceeded its configured byte limit"
            ));
        }
        require_success_exit(status)?;
        validate_protocol(&stdout_bytes, &request)?;
        Ok(())
    })();
    let reason = match &result {
        Ok(()) => "completed-target",
        Err(error) if error.contains("timed out") => "timeout",
        Err(error) if error.contains("byte limit") => "output-limit",
        Err(error) if error.contains("exited unsuccessfully") => "crash",
        Err(_) => "infrastructure-error",
    };

    let command_bytes = serde_json::to_vec(&request.commands)
        .map_err(|error| format!("serialize command stream: {error}"))?;
    let manifest = ReplayManifest {
        schema_version: 1,
        request_sha256: &request_sha256,
        attempt_id: &request.attempt_id,
        scenario_id: &request.scenario_id,
        profile_id: &request.profile_id,
        backend: ReplayBackend {
            kind: request.backend.kind.as_str(),
            source_revision: &request.backend.source_revision,
            executable_sha256: &request.backend.expected_executable_sha256,
        },
        input_identities: &request.input_identities,
        command_stream_sha256: digest_bytes(&command_bytes),
        command_count: request.commands.len(),
        expected_stop_condition: &request.expected_stop_condition,
        limits: ReplayLimits {
            timeout_ms: request.timeout_ms,
            stdout_bytes: request.stdout_limit_bytes,
            stderr_bytes: request.stderr_limit_bytes,
        },
        execution: ReplayExecution {
            status: if result.is_ok() {
                "succeeded"
            } else {
                "failed"
            },
            reason,
            stop_condition: if result.is_ok() {
                &request.expected_stop_condition
            } else {
                ""
            },
            exit_code,
        },
        comparison_verdict: "not-run",
        artifacts: ReplayArtifacts {
            request: artifact_identity("request.json", &canonical_request),
            stdout: artifact_identity("stdout.ndjson", &stdout_bytes),
            stderr: artifact_identity("stderr.log", &stderr_bytes),
        },
    };
    let mut manifest_bytes = serde_json::to_vec_pretty(&manifest)
        .map_err(|error| format!("serialize replay manifest: {error}"))?;
    manifest_bytes.push(b'\n');

    atomic_write(&attempt_dir, "request.json", &canonical_request)?;
    atomic_write(&attempt_dir, "stdout.ndjson", &stdout_bytes)?;
    atomic_write(&attempt_dir, "stderr.log", &stderr_bytes)?;
    atomic_write(&attempt_dir, "replay-manifest.json", &manifest_bytes)?;
    result
}

fn read_and_validate_request(path: &Path) -> Result<RunRequest, String> {
    let file = File::open(path).map_err(|error| format!("open request: {error}"))?;
    let mut bytes = Vec::new();
    file.take(REQUEST_MAX_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("read request: {error}"))?;
    if bytes.len() as u64 > REQUEST_MAX_BYTES {
        return Err(format!(
            "request exceeds the {REQUEST_MAX_BYTES}-byte limit"
        ));
    }
    parse_and_validate_request_bytes(&bytes)
}

pub fn parse_and_validate_request_bytes(bytes: &[u8]) -> Result<RunRequest, String> {
    if bytes.len() as u64 > REQUEST_MAX_BYTES {
        return Err(format!(
            "request exceeds the {REQUEST_MAX_BYTES}-byte limit"
        ));
    }
    let mut request: RunRequest =
        serde_json::from_slice(bytes).map_err(|error| format!("parse request JSON: {error}"))?;
    validate_request(&request)?;
    request.backend.source_revision.make_ascii_lowercase();
    request
        .backend
        .expected_executable_sha256
        .make_ascii_lowercase();
    for input in &mut request.input_identities {
        input.sha256.make_ascii_lowercase();
    }
    Ok(request)
}

fn validate_request(request: &RunRequest) -> Result<(), String> {
    if request.schema_version != 1 {
        return Err("schema_version must be the number 1".to_owned());
    }
    validate_id("attempt_id", &request.attempt_id, ID_MAX_BYTES)?;
    validate_id("scenario_id", &request.scenario_id, ID_MAX_BYTES)?;
    validate_id("profile_id", &request.profile_id, ID_MAX_BYTES)?;
    validate_id(
        "expected_stop_condition",
        &request.expected_stop_condition,
        STOP_MAX_BYTES,
    )?;
    validate_hex(
        "backend.source_revision",
        &request.backend.source_revision,
        40,
    )?;
    validate_hex(
        "backend.expected_executable_sha256",
        &request.backend.expected_executable_sha256,
        64,
    )?;
    if !(1..=TIMEOUT_MAX_MS).contains(&request.timeout_ms) {
        return Err(format!("timeout_ms must be in 1..={TIMEOUT_MAX_MS}"));
    }
    validate_output_limit("stdout_limit_bytes", request.stdout_limit_bytes)?;
    validate_output_limit("stderr_limit_bytes", request.stderr_limit_bytes)?;
    if request.input_identities.len() > INPUT_MAX_COUNT {
        return Err(format!(
            "input_identities must contain at most {INPUT_MAX_COUNT} entries"
        ));
    }
    if matches!(request.backend.kind, BackendKind::BosmanNative)
        && request.input_identities.is_empty()
    {
        return Err("bosman-native requests require at least one input identity".to_owned());
    }
    let mut input_hashes = BTreeSet::new();
    for (index, input) in request.input_identities.iter().enumerate() {
        validate_hex(
            &format!("input_identities[{index}].sha256"),
            &input.sha256,
            64,
        )?;
        if input.byte_count > INPUT_MAX_BYTES {
            return Err(format!(
                "input_identities[{index}].byte_count exceeds {INPUT_MAX_BYTES}"
            ));
        }
        if !input_hashes.insert(input.sha256.to_ascii_lowercase()) {
            return Err(format!(
                "input_identities[{index}].sha256 duplicates an earlier identity"
            ));
        }
    }
    if request.commands.len() > COMMAND_MAX_COUNT {
        return Err(format!(
            "commands must contain at most {COMMAND_MAX_COUNT} entries"
        ));
    }
    let mut command_ids = BTreeSet::new();
    for (index, command) in request.commands.iter().enumerate() {
        validate_id(&format!("commands[{index}].id"), &command.id, ID_MAX_BYTES)?;
        validate_id(
            &format!("commands[{index}].kind"),
            &command.kind,
            ID_MAX_BYTES,
        )?;
        if !command.parameters.is_object() {
            return Err(format!("commands[{index}].parameters must be an object"));
        }
        if !command_ids.insert(&command.id) {
            return Err(format!(
                "commands[{index}].id duplicates an earlier command ID"
            ));
        }
    }
    if request.backend.kind == BackendKind::BosmanNative {
        validate_bosman_request(request)?;
    }
    Ok(())
}

fn validate_bosman_request(request: &RunRequest) -> Result<(), String> {
    const STOP: &str = "classic-same-save-normal-again-14-days-equal";
    if request.expected_stop_condition != STOP {
        return Err(format!(
            "bosman-native expected_stop_condition must be {STOP:?}"
        ));
    }
    if request.input_identities.len() != 4 {
        return Err("bosman-native requests require exactly four input identities".to_owned());
    }
    if request.commands.len() != 1 {
        return Err("bosman-native requests require exactly one command".to_owned());
    }
    let command = &request.commands[0];
    if command.kind != "bosman-classic-same-save-v1" {
        return Err("bosman-native command kind must be bosman-classic-same-save-v1".to_owned());
    }
    let parameters: BosmanSameSaveParameters =
        serde_json::from_value(command.parameters.clone())
            .map_err(|error| format!("parse bosman-native command parameters: {error}"))?;
    let expected = BosmanSameSaveParameters {
        mode: "classic".to_owned(),
        days: 14,
        jobs: 2,
        runs: vec!["normal".to_owned(), "again".to_owned()],
        seed: 1,
        fixed_clock: true,
        expected_save_relation: "byte-identical".to_owned(),
        input_slots: BosmanInputSlots {
            bosman_executable: 0,
            clean_manifest: 1,
            smoke_runner: 2,
            python_interpreter: 3,
        },
    };
    if parameters != expected {
        return Err(
            "bosman-native command parameters do not match the bounded v1 profile".to_owned(),
        );
    }
    Ok(())
}

fn validate_id(field: &str, value: &str, maximum: usize) -> Result<(), String> {
    let mut bytes = value.bytes();
    let Some(first) = bytes.next() else {
        return Err(format!("{field} must not be empty"));
    };
    if value.len() > maximum {
        return Err(format!("{field} must be at most {maximum} bytes"));
    }
    if !first.is_ascii_alphanumeric()
        || !bytes.all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.'))
    {
        return Err(format!("{field} must match [A-Za-z0-9][A-Za-z0-9._-]*"));
    }
    Ok(())
}

fn validate_hex(field: &str, value: &str, length: usize) -> Result<(), String> {
    if value.len() != length || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(format!(
            "{field} must be exactly {length} hexadecimal characters"
        ));
    }
    Ok(())
}

fn validate_output_limit(field: &str, value: u64) -> Result<(), String> {
    if !(OUTPUT_MIN_BYTES..=OUTPUT_MAX_BYTES).contains(&value) {
        return Err(format!(
            "{field} must be in {OUTPUT_MIN_BYTES}..={OUTPUT_MAX_BYTES}"
        ));
    }
    Ok(())
}

fn create_private_dir(path: &Path, label: &str) -> Result<(), String> {
    let mut builder = fs::DirBuilder::new();
    builder.mode(0o700);
    builder
        .create(path)
        .map_err(|error| format!("create {label}: {error}"))?;
    fs::set_permissions(path, fs::Permissions::from_mode(0o700))
        .map_err(|error| format!("secure {label}: {error}"))
}

fn digest_reader(file: &mut File) -> Result<String, String> {
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let count = file
            .read(&mut buffer)
            .map_err(|error| format!("hash backend executable: {error}"))?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

fn digest_bytes(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn spawn_input<W: Write + AsRawFd + Send + 'static>(
    mut writer: W,
    bytes: Vec<u8>,
    cancelled: Arc<AtomicBool>,
) -> Result<JoinHandle<Result<(), String>>, String> {
    set_nonblocking(writer.as_raw_fd(), "backend stdin")?;
    Ok(thread::spawn(move || {
        let mut offset = 0;
        while offset < bytes.len() {
            match writer.write(&bytes[offset..]) {
                Ok(0) => return Err("send validated request: pipe wrote zero bytes".to_owned()),
                Ok(count) => offset += count,
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    if cancelled.load(Ordering::Acquire) {
                        return Err(
                            "send validated request: execution ended before delivery".to_owned()
                        );
                    }
                    thread::sleep(Duration::from_millis(2));
                }
                Err(error) => return Err(format!("send validated request to backend: {error}")),
            }
        }
        Ok(())
    }))
}

fn spawn_capture<R: Read + AsRawFd + Send + 'static>(
    mut reader: R,
    limit: usize,
    label: &'static str,
    limit_tx: mpsc::Sender<&'static str>,
    cancelled: Arc<AtomicBool>,
) -> Result<JoinHandle<Result<Vec<u8>, String>>, String> {
    set_nonblocking(reader.as_raw_fd(), &format!("backend {label}"))?;
    Ok(thread::spawn(move || {
        let mut bytes = Vec::with_capacity(limit.min(64 * 1024));
        let mut buffer = [0_u8; 8192];
        loop {
            let count = match reader.read(&mut buffer) {
                Ok(count) => count,
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    if cancelled.load(Ordering::Acquire) {
                        return Ok(bytes);
                    }
                    thread::sleep(Duration::from_millis(2));
                    continue;
                }
                Err(error) => return Err(format!("read backend {label}: {error}")),
            };
            if count == 0 {
                return Ok(bytes);
            }
            let remaining = limit.saturating_sub(bytes.len());
            bytes.extend_from_slice(&buffer[..count.min(remaining)]);
            if count > remaining {
                let _ = limit_tx.send(label);
                return Ok(bytes);
            }
        }
    }))
}

pub(crate) fn set_nonblocking(file_descriptor: RawFd, label: &str) -> Result<(), String> {
    // SAFETY: fcntl only reads or changes flags on a live, owned pipe descriptor.
    let flags = unsafe { libc::fcntl(file_descriptor, libc::F_GETFL) };
    if flags == -1 {
        return Err(format!(
            "read {label} flags: {}",
            std::io::Error::last_os_error()
        ));
    }
    // SAFETY: the descriptor remains live for the following spawned I/O thread.
    if unsafe { libc::fcntl(file_descriptor, libc::F_SETFL, flags | libc::O_NONBLOCK) } == -1 {
        return Err(format!(
            "set {label} nonblocking: {}",
            std::io::Error::last_os_error()
        ));
    }
    Ok(())
}

fn join_capture(handle: JoinHandle<Result<Vec<u8>, String>>) -> Result<Vec<u8>, String> {
    handle
        .join()
        .map_err(|_| "backend capture thread panicked".to_owned())?
}

fn join_input(handle: JoinHandle<Result<(), String>>) -> Result<(), String> {
    handle
        .join()
        .map_err(|_| "backend input thread panicked".to_owned())?
}

fn terminate_process_group(process_group: i32, child: &mut Child) -> Result<(), String> {
    kill_process_group(process_group);
    let wait_result = child
        .wait()
        .map(|_| ())
        .map_err(|error| format!("wait for terminated backend: {error}"));
    let cleanup_result = cleanup_adopted_children();
    match (wait_result, cleanup_result) {
        (Ok(()), Ok(())) => Ok(()),
        (Err(error), Ok(())) | (Ok(()), Err(error)) => Err(error),
        (Err(wait_error), Err(cleanup_error)) => Err(format!(
            "{wait_error}; descendant cleanup also failed: {cleanup_error}"
        )),
    }
}

fn terminate_with_reason(process_group: i32, child: &mut Child, reason: String) -> String {
    match terminate_process_group(process_group, child) {
        Ok(()) => reason,
        Err(error) => format!("{reason}; process cleanup failed: {error}"),
    }
}

fn kill_process_group(process_group: i32) {
    // SAFETY: kill is called with a known positive child PGID, negated to target only that group.
    unsafe {
        libc::kill(-process_group, libc::SIGKILL);
    }
}

fn enable_child_subreaper() -> Result<(), String> {
    // SAFETY: prctl is called with the documented Linux PR_SET_CHILD_SUBREAPER operation.
    if unsafe { libc::prctl(libc::PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) } == -1 {
        return Err(format!(
            "enable child subreaper: {}",
            std::io::Error::last_os_error()
        ));
    }
    Ok(())
}

fn cleanup_adopted_children() -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(1);
    loop {
        reap_exited_children();
        let children_path = format!("/proc/self/task/{}/children", std::process::id());
        let contents = fs::read_to_string(&children_path)
            .map_err(|error| format!("inspect adopted backend descendants: {error}"))?;
        let children = contents
            .split_whitespace()
            .map(|pid| {
                pid.parse::<i32>()
                    .map_err(|error| format!("parse adopted descendant PID: {error}"))
            })
            .collect::<Result<Vec<_>, _>>()?;
        if children.is_empty() {
            return Ok(());
        }
        for child in children {
            // SAFETY: each positive PID came from this process's kernel-reported child list.
            unsafe {
                libc::kill(child, libc::SIGKILL);
            }
        }
        if Instant::now() >= deadline {
            return Err("adopted backend descendants survived process cleanup".to_owned());
        }
        thread::sleep(Duration::from_millis(2));
    }
}

fn reap_exited_children() {
    loop {
        let mut status = 0;
        // SAFETY: waitpid(-1, WNOHANG) reaps only children of this supervisor process.
        let pid = unsafe { libc::waitpid(-1, &mut status, libc::WNOHANG) };
        if pid <= 0 {
            return;
        }
    }
}

fn require_success_exit(status: ExitStatus) -> Result<(), String> {
    if status.success() {
        Ok(())
    } else {
        Err(format!("backend exited unsuccessfully: {status}"))
    }
}

fn validate_protocol(stdout: &[u8], request: &RunRequest) -> Result<(), String> {
    if stdout.is_empty() {
        return Err("backend stdout contained no protocol frames".to_owned());
    }
    if !stdout.ends_with(b"\n") {
        return Err("backend stdout ended with an incomplete NDJSON frame".to_owned());
    }
    let mut terminal: Option<TerminalPayload> = None;
    let mut handshake_seen = false;
    let mut frame_count = 0_usize;
    for (index, line) in stdout[..stdout.len() - 1]
        .split(|byte| *byte == b'\n')
        .enumerate()
    {
        if line.is_empty() {
            return Err(format!("protocol frame {} is empty", index + 1));
        }
        if line.len() > FRAME_MAX_BYTES {
            return Err(format!(
                "protocol frame {} exceeds the {FRAME_MAX_BYTES}-byte line limit",
                index + 1
            ));
        }
        let frame: ProtocolFrame = serde_json::from_slice(line)
            .map_err(|error| format!("parse protocol frame {}: {error}", index + 1))?;
        if frame.protocol_version != 1 {
            return Err(format!(
                "protocol frame {} has unsupported protocol_version {}",
                index + 1,
                frame.protocol_version
            ));
        }
        if frame.attempt_id != request.attempt_id {
            return Err(format!(
                "protocol frame {} attempt_id does not match the request",
                index + 1
            ));
        }
        if frame.sequence != index as u64 {
            return Err(format!(
                "protocol frame {} has sequence {}; expected {}",
                index + 1,
                frame.sequence,
                index
            ));
        }
        validate_id(
            &format!("protocol frame {} kind", index + 1),
            &frame.kind,
            ID_MAX_BYTES,
        )?;
        if !frame.payload.is_object() {
            return Err(format!(
                "protocol frame {} payload must be an object",
                index + 1
            ));
        }
        if index == 0 && frame.kind != "handshake" {
            return Err("the first protocol frame must be a handshake".to_owned());
        }
        if index > 0 && frame.kind == "handshake" {
            return Err("protocol contains more than one handshake".to_owned());
        }
        if frame.kind == "handshake" {
            validate_handshake(frame.payload, request)?;
            handshake_seen = true;
        } else if frame.kind == "terminal" {
            if terminal.is_some() {
                return Err("protocol contains more than one terminal frame".to_owned());
            }
            terminal = Some(
                serde_json::from_value(frame.payload)
                    .map_err(|error| format!("parse terminal payload: {error}"))?,
            );
        } else if terminal.is_some() {
            return Err("terminal protocol frame must be last".to_owned());
        }
        frame_count = index + 1;
    }
    let terminal = terminal.ok_or_else(|| "protocol has no terminal frame".to_owned())?;
    if !handshake_seen {
        return Err("protocol has no handshake frame".to_owned());
    }
    if frame_count < 2 {
        return Err("protocol must contain a handshake and terminal frame".to_owned());
    }
    if terminal.execution_status != "succeeded" {
        return Err(format!(
            "terminal execution_status is {:?}, expected \"succeeded\"",
            terminal.execution_status
        ));
    }
    if terminal.reason != "completed-target" {
        return Err(format!(
            "terminal reason is {:?}, expected \"completed-target\"",
            terminal.reason
        ));
    }
    if terminal.stop_condition != request.expected_stop_condition {
        return Err(format!(
            "terminal stop_condition {:?} does not match expected {:?}",
            terminal.stop_condition, request.expected_stop_condition
        ));
    }
    Ok(())
}

fn validate_handshake(payload: Value, request: &RunRequest) -> Result<(), String> {
    let handshake: HandshakePayload = serde_json::from_value(payload)
        .map_err(|error| format!("parse handshake payload: {error}"))?;
    if handshake.backend_kind != request.backend.kind.as_str() {
        return Err("handshake backend_kind does not match the request".to_owned());
    }
    if !handshake
        .source_revision
        .eq_ignore_ascii_case(&request.backend.source_revision)
    {
        return Err("handshake source_revision does not match the request".to_owned());
    }
    if !handshake
        .executable_sha256
        .eq_ignore_ascii_case(&request.backend.expected_executable_sha256)
    {
        return Err("handshake executable_sha256 does not match the request".to_owned());
    }
    let mut capabilities = BTreeSet::new();
    for (index, capability) in handshake.capabilities.iter().enumerate() {
        validate_id(
            &format!("handshake capabilities[{index}]"),
            capability,
            ID_MAX_BYTES,
        )?;
        if !capabilities.insert(capability) {
            return Err(format!(
                "handshake capabilities[{index}] duplicates an earlier capability"
            ));
        }
    }
    Ok(())
}

fn artifact_identity(file_name: &'static str, bytes: &[u8]) -> ArtifactIdentity {
    ArtifactIdentity {
        file_name,
        byte_count: bytes.len(),
        sha256: digest_bytes(bytes),
    }
}

fn atomic_write(directory: &Path, file_name: &str, bytes: &[u8]) -> Result<(), String> {
    let final_path = directory.join(file_name);
    let temporary_path = temporary_path(directory, file_name);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary_path)
        .map_err(|error| format!("create temporary {file_name}: {error}"))?;
    if let Err(error) = file.write_all(bytes).and_then(|()| file.sync_all()) {
        let _ = fs::remove_file(&temporary_path);
        return Err(format!("write temporary {file_name}: {error}"));
    }
    drop(file);
    fs::rename(&temporary_path, &final_path)
        .map_err(|error| format!("publish {file_name}: {error}"))?;
    File::open(directory)
        .and_then(|directory| directory.sync_all())
        .map_err(|error| format!("sync published {file_name}: {error}"))?;
    Ok(())
}

fn temporary_path(directory: &Path, file_name: &str) -> PathBuf {
    directory.join(format!(".{file_name}.tmp"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request() -> RunRequest {
        RunRequest {
            schema_version: 1,
            attempt_id: "attempt-1".to_owned(),
            scenario_id: "scenario-1".to_owned(),
            profile_id: "profile-1".to_owned(),
            backend: BackendIdentity {
                kind: BackendKind::SyntheticTest,
                source_revision: "a".repeat(40),
                expected_executable_sha256: "b".repeat(64),
            },
            expected_stop_condition: "completed".to_owned(),
            timeout_ms: 1_000,
            stdout_limit_bytes: OUTPUT_MIN_BYTES,
            stderr_limit_bytes: OUTPUT_MIN_BYTES,
            input_identities: Vec::new(),
            commands: vec![RunCommand {
                id: "command-1".to_owned(),
                kind: "advance".to_owned(),
                parameters: serde_json::json!({}),
            }],
        }
    }

    #[test]
    fn request_validation_is_repeatable() {
        let request = request();
        assert_eq!(validate_request(&request), validate_request(&request));
        let first = serde_json::to_vec(&request).unwrap();
        let second = serde_json::to_vec(&request).unwrap();
        assert_eq!(first, second);
    }

    #[test]
    fn rejects_duplicate_commands_and_unsafe_ids() {
        let mut duplicate = request();
        duplicate.commands.push(duplicate.commands[0].clone());
        assert!(
            validate_request(&duplicate)
                .unwrap_err()
                .contains("duplicates")
        );
        let mut unsafe_id = request();
        unsafe_id.attempt_id = "../escape".to_owned();
        assert!(
            validate_request(&unsafe_id)
                .unwrap_err()
                .contains("must match")
        );
    }

    #[test]
    fn bosman_requires_an_input_identity() {
        let mut request = request();
        request.backend.kind = BackendKind::BosmanNative;
        assert!(
            validate_request(&request)
                .unwrap_err()
                .contains("at least one input")
        );
    }

    fn bounded_bosman_request() -> RunRequest {
        RunRequest {
            schema_version: 1,
            attempt_id: "bosman-attempt-1".to_owned(),
            scenario_id: "clean-same-save".to_owned(),
            profile_id: "bosman-clean-3968".to_owned(),
            backend: BackendIdentity {
                kind: BackendKind::BosmanNative,
                source_revision: "a".repeat(40),
                expected_executable_sha256: "b".repeat(64),
            },
            expected_stop_condition: "classic-same-save-normal-again-14-days-equal".to_owned(),
            timeout_ms: 600_000,
            stdout_limit_bytes: OUTPUT_MIN_BYTES,
            stderr_limit_bytes: OUTPUT_MIN_BYTES,
            input_identities: (0..4)
                .map(|index| InputIdentity {
                    sha256: format!("{index:064x}"),
                    byte_count: index,
                })
                .collect(),
            commands: vec![RunCommand {
                id: "same-save-1".to_owned(),
                kind: "bosman-classic-same-save-v1".to_owned(),
                parameters: serde_json::to_value(BosmanSameSaveParameters {
                    mode: "classic".to_owned(),
                    days: 14,
                    jobs: 2,
                    runs: vec!["normal".to_owned(), "again".to_owned()],
                    seed: 1,
                    fixed_clock: true,
                    expected_save_relation: "byte-identical".to_owned(),
                    input_slots: BosmanInputSlots {
                        bosman_executable: 0,
                        clean_manifest: 1,
                        smoke_runner: 2,
                        python_interpreter: 3,
                    },
                })
                .unwrap(),
            }],
        }
    }

    #[test]
    fn bosman_profile_is_exact_and_binds_distinct_input_slots() {
        let request = bounded_bosman_request();
        assert!(validate_request(&request).is_ok());

        let mut wrong_days = request.clone();
        wrong_days.commands[0].parameters["days"] = serde_json::json!(13);
        assert!(
            validate_request(&wrong_days)
                .unwrap_err()
                .contains("bounded v1 profile")
        );

        let mut remapped = request;
        remapped.commands[0].parameters["input_slots"]["smoke_runner"] = serde_json::json!(0);
        assert!(
            validate_request(&remapped)
                .unwrap_err()
                .contains("bounded v1 profile")
        );
    }

    #[test]
    fn protocol_requires_a_contiguous_terminal_endpoint() {
        let request = request();
        let frames = format!(
            "{{\"protocol_version\":1,\"attempt_id\":\"attempt-1\",\"sequence\":0,\"kind\":\"handshake\",\"payload\":{{\"backend_kind\":\"synthetic-test\",\"source_revision\":\"{}\",\"executable_sha256\":\"{}\",\"capabilities\":[]}}}}\n{{\"protocol_version\":1,\"attempt_id\":\"attempt-1\",\"sequence\":2,\"kind\":\"terminal\",\"payload\":{{\"execution_status\":\"succeeded\",\"reason\":\"completed-target\",\"stop_condition\":\"completed\"}}}}\n",
            "a".repeat(40),
            "b".repeat(64)
        );
        assert!(
            validate_protocol(frames.as_bytes(), &request)
                .unwrap_err()
                .contains("expected 1")
        );
    }
}
