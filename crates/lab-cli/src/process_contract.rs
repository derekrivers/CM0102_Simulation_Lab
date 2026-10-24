use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::DirBuilderExt;
use std::os::unix::fs::PermissionsExt;
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::mpsc;
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

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum BackendKind {
    #[serde(rename = "bosman-native")]
    BosmanNative,
    #[serde(rename = "synthetic-test")]
    SyntheticTest,
}

impl BackendKind {
    fn as_str(self) -> &'static str {
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
    attempt_dir: &Path,
) -> Result<(), String> {
    let request = read_and_validate_request(request_path)?;
    let executable = backend_executable
        .canonicalize()
        .map_err(|error| format!("resolve backend executable: {error}"))?;
    let executable_sha256 = digest_file(&executable)?;
    if !executable_sha256.eq_ignore_ascii_case(&request.backend.expected_executable_sha256) {
        return Err(format!(
            "backend executable SHA-256 mismatch: expected {}, actual {executable_sha256}",
            request.backend.expected_executable_sha256
        ));
    }
    let canonical_request = serde_json::to_vec(&request)
        .map_err(|error| format!("serialize validated request: {error}"))?;
    let request_sha256 = digest_bytes(&canonical_request);
    let mut request_bytes = canonical_request;
    request_bytes.push(b'\n');

    create_private_dir(attempt_dir, "attempt directory")?;
    let attempt_dir = attempt_dir
        .canonicalize()
        .map_err(|error| format!("resolve created attempt directory: {error}"))?;
    let home_dir = attempt_dir.join("home");
    let temp_dir = attempt_dir.join("tmp");
    create_private_dir(&home_dir, "private HOME")?;
    create_private_dir(&temp_dir, "private temporary directory")?;

    let mut command = Command::new(&executable);
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

    let mut child = command
        .spawn()
        .map_err(|error| format!("spawn backend: {error}"))?;
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
    let input_handle = thread::spawn(move || {
        let mut stdin = stdin;
        stdin
            .write_all(&request_bytes)
            .map_err(|error| format!("send validated request to backend: {error}"))
    });
    let stdout_handle = spawn_capture(
        stdout,
        request.stdout_limit_bytes as usize,
        "stdout",
        limit_tx.clone(),
    );
    let stderr_handle = spawn_capture(
        stderr,
        request.stderr_limit_bytes as usize,
        "stderr",
        limit_tx,
    );

    let deadline = Instant::now() + Duration::from_millis(request.timeout_ms);
    let status = loop {
        if let Ok(stream) = limit_rx.try_recv() {
            terminate_process_group(process_group, &mut child);
            let _ = join_input(input_handle);
            let _ = join_capture(stdout_handle);
            let _ = join_capture(stderr_handle);
            return Err(format!(
                "backend {stream} exceeded its configured byte limit"
            ));
        }
        match child.try_wait() {
            Err(error) => {
                terminate_process_group(process_group, &mut child);
                let _ = join_input(input_handle);
                let _ = join_capture(stdout_handle);
                let _ = join_capture(stderr_handle);
                return Err(format!("wait for backend: {error}"));
            }
            Ok(Some(status)) => break status,
            Ok(None) if Instant::now() >= deadline => {
                terminate_process_group(process_group, &mut child);
                let _ = join_input(input_handle);
                let _ = join_capture(stdout_handle);
                let _ = join_capture(stderr_handle);
                return Err(format!("backend timed out after {} ms", request.timeout_ms));
            }
            Ok(None) => thread::sleep(Duration::from_millis(2)),
        }
    };
    // A child must not leave descendants holding capture pipes or mutating its attempt.
    kill_process_group(process_group);
    join_input(input_handle)?;
    let stdout = join_capture(stdout_handle)?;
    let stderr = join_capture(stderr_handle)?;
    require_success_exit(status)?;
    validate_protocol(&stdout, &request)?;

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
            status: "succeeded",
            reason: "completed-target",
            stop_condition: &request.expected_stop_condition,
            exit_code: 0,
        },
        comparison_verdict: "not-run",
        artifacts: ReplayArtifacts {
            stdout: artifact_identity("stdout.ndjson", &stdout),
            stderr: artifact_identity("stderr.log", &stderr),
        },
    };
    let mut manifest_bytes = serde_json::to_vec_pretty(&manifest)
        .map_err(|error| format!("serialize replay manifest: {error}"))?;
    manifest_bytes.push(b'\n');

    atomic_write(&attempt_dir, "stdout.ndjson", &stdout)?;
    atomic_write(&attempt_dir, "stderr.log", &stderr)?;
    atomic_write(&attempt_dir, "replay-manifest.json", &manifest_bytes)?;
    Ok(())
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
    let mut request: RunRequest =
        serde_json::from_slice(&bytes).map_err(|error| format!("parse request JSON: {error}"))?;
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

fn digest_file(path: &Path) -> Result<String, String> {
    let mut file = File::open(path).map_err(|error| format!("open backend executable: {error}"))?;
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

fn spawn_capture<R: Read + Send + 'static>(
    mut reader: R,
    limit: usize,
    label: &'static str,
    limit_tx: mpsc::Sender<&'static str>,
) -> JoinHandle<Result<Vec<u8>, String>> {
    thread::spawn(move || {
        let mut bytes = Vec::with_capacity(limit.min(64 * 1024));
        let mut buffer = [0_u8; 8192];
        loop {
            let count = reader
                .read(&mut buffer)
                .map_err(|error| format!("read backend {label}: {error}"))?;
            if count == 0 {
                return Ok(bytes);
            }
            let remaining = limit.saturating_sub(bytes.len());
            bytes.extend_from_slice(&buffer[..count.min(remaining)]);
            if count > remaining {
                let _ = limit_tx.send(label);
                return Err(format!(
                    "backend {label} exceeded its configured byte limit"
                ));
            }
        }
    })
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

fn terminate_process_group(process_group: i32, child: &mut Child) {
    kill_process_group(process_group);
    let _ = child.wait();
}

fn kill_process_group(process_group: i32) {
    // SAFETY: kill is called with a known positive child PGID, negated to target only that group.
    unsafe {
        libc::kill(-process_group, libc::SIGKILL);
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
