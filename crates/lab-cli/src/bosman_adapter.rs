use crate::process_contract::{BackendKind, BosmanSameSaveParameters, InputIdentity, RunRequest};
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::os::unix::fs::PermissionsExt;
use std::os::unix::process::CommandExt;
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Stdio};

const CONFIG_MAX_BYTES: u64 = 64 * 1024;
const REQUEST_MAX_BYTES: u64 = 1024 * 1024;
const NESTED_OUTPUT_MAX_BYTES: usize = 1024 * 1024;
const STOP: &str = "classic-same-save-normal-again-14-days-equal";

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct BackendConfig {
    python_executable: PathBuf,
    smoke_runner: PathBuf,
    bosman_executable: PathBuf,
    clean_game_dir: PathBuf,
    clean_manifest: PathBuf,
}

#[derive(Debug)]
struct ManifestEntry {
    sha256: String,
    byte_count: u64,
}

pub fn run() -> Result<(), String> {
    let arguments: Vec<String> = env::args().skip(1).collect();
    if !arguments.is_empty() {
        return launch_bosman(&arguments);
    }
    run_protocol()
}

fn run_protocol() -> Result<(), String> {
    let request = read_request()?;
    if request.backend.kind != BackendKind::BosmanNative {
        return Err("request backend must be bosman-native".to_owned());
    }
    let command = &request.commands[0];
    let parameters: BosmanSameSaveParameters =
        serde_json::from_value(command.parameters.clone())
            .map_err(|error| format!("parse bounded Bosman command: {error}"))?;
    let config = read_config()?;

    verify_file(
        "Bosman executable",
        &config.bosman_executable,
        &request.input_identities[parameters.input_slots.bosman_executable],
        true,
    )?;
    verify_file(
        "clean manifest",
        &config.clean_manifest,
        &request.input_identities[parameters.input_slots.clean_manifest],
        false,
    )?;
    verify_file(
        "smoke runner",
        &config.smoke_runner,
        &request.input_identities[parameters.input_slots.smoke_runner],
        false,
    )?;
    let python = verify_file(
        "Python interpreter",
        &config.python_executable,
        &request.input_identities[parameters.input_slots.python_interpreter],
        true,
    )?;
    let clean_count = verify_clean_tree(&config.clean_game_dir, &config.clean_manifest)?;

    emit(
        &request,
        0,
        "handshake",
        json!({
            "backend_kind": "bosman-native",
            "source_revision": request.backend.source_revision,
            "executable_sha256": request.backend.expected_executable_sha256,
            "capabilities": ["classic-same-save", "fixed-clock", "seeded-start", "save-byte-compare"]
        }),
    )?;
    emit(
        &request,
        1,
        "progress",
        json!({"stage": "inputs-verified", "clean_file_count": clean_count}),
    )?;

    let adapter = env::current_exe().map_err(|error| format!("resolve adapter path: {error}"))?;
    let config_path = required_env("LAB_BACKEND_CONFIG")?;
    let home = required_env("HOME")?;
    let temp = required_env("TMPDIR")?;
    let mut command = Command::new(format!("/proc/self/fd/{}", python.as_raw_fd()));
    command
        .arg("-I")
        .arg(&config.smoke_runner)
        .arg(&adapter)
        .arg(&config.clean_game_dir)
        .args([
            "--same-save",
            "--mode",
            "classic",
            "--days",
            "14",
            "--jobs",
            "2",
            "--runs",
            "normal,again",
        ])
        .env_clear()
        .env("HOME", home)
        .env("TMPDIR", temp)
        .env("TZ", "UTC")
        .env("LC_ALL", "C")
        .env("LANG", "C")
        .env("SDL_VIDEODRIVER", "dummy")
        .env("SDL_AUDIODRIVER", "dummy")
        .env("LAB_BACKEND_CONFIG", config_path)
        .env(
            "LAB_BOSMAN_EXPECTED_SHA256",
            &request.input_identities[parameters.input_slots.bosman_executable].sha256,
        )
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let output = command
        .output()
        .map_err(|error| format!("run pinned smoke runner: {error}"))?;
    if output.stdout.len() > NESTED_OUTPUT_MAX_BYTES
        || output.stderr.len() > NESTED_OUTPUT_MAX_BYTES
    {
        return Err("pinned smoke runner exceeded the nested output limit".to_owned());
    }
    let stdout = std::str::from_utf8(&output.stdout)
        .map_err(|error| format!("smoke runner stdout was not UTF-8: {error}"))?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    write_diagnostics(stdout, &stderr, &config)?;
    if !output.status.success() {
        return Err(format!(
            "smoke runner exited unsuccessfully: {}",
            output.status
        ));
    }
    verify_endpoint(stdout)?;

    // Detect changes to every scientific input after the nested process has ended.
    verify_file(
        "Bosman executable",
        &config.bosman_executable,
        &request.input_identities[parameters.input_slots.bosman_executable],
        true,
    )?;
    verify_file(
        "smoke runner",
        &config.smoke_runner,
        &request.input_identities[parameters.input_slots.smoke_runner],
        false,
    )?;
    verify_clean_tree(&config.clean_game_dir, &config.clean_manifest)?;

    emit(
        &request,
        2,
        "progress",
        json!({"stage": "normal-complete", "game_days": 14, "idle_sleep_observed": true}),
    )?;
    emit(
        &request,
        3,
        "progress",
        json!({"stage": "again-complete", "game_days": 14}),
    )?;
    emit(
        &request,
        4,
        "progress",
        json!({"stage": "save-comparison", "relation": "byte-identical"}),
    )?;
    emit(
        &request,
        5,
        "terminal",
        json!({
            "execution_status": "succeeded",
            "reason": "completed-target",
            "stop_condition": STOP
        }),
    )
}

fn read_request() -> Result<RunRequest, String> {
    let mut bytes = Vec::new();
    std::io::stdin()
        .take(REQUEST_MAX_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("read canonical request: {error}"))?;
    crate::process_contract::parse_and_validate_request_bytes(&bytes)
}

fn read_config() -> Result<BackendConfig, String> {
    let path = required_env("LAB_BACKEND_CONFIG")?;
    let file =
        File::open(&path).map_err(|error| format!("open private backend config: {error}"))?;
    let mut bytes = Vec::new();
    file.take(CONFIG_MAX_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("read private backend config: {error}"))?;
    if bytes.len() as u64 > CONFIG_MAX_BYTES {
        return Err(format!(
            "private backend config exceeds the {CONFIG_MAX_BYTES}-byte limit"
        ));
    }
    serde_json::from_slice(&bytes).map_err(|error| format!("parse private backend config: {error}"))
}

fn required_env(name: &str) -> Result<String, String> {
    env::var(name).map_err(|_| format!("required environment variable {name} is missing"))
}

fn verify_file(
    label: &str,
    path: &Path,
    expected: &InputIdentity,
    executable: bool,
) -> Result<File, String> {
    let metadata =
        fs::symlink_metadata(path).map_err(|error| format!("inspect {label}: {error}"))?;
    if !metadata.file_type().is_file() {
        return Err(format!("{label} must be a regular non-symlink file"));
    }
    if executable && metadata.permissions().mode() & 0o111 == 0 {
        return Err(format!("{label} must be executable"));
    }
    if metadata.len() != expected.byte_count {
        return Err(format!(
            "{label} byte count mismatch: expected {}, actual {}",
            expected.byte_count,
            metadata.len()
        ));
    }
    let mut file = File::open(path).map_err(|error| format!("open {label}: {error}"))?;
    let actual = digest_reader(&mut file, label)?;
    if !actual.eq_ignore_ascii_case(&expected.sha256) {
        return Err(format!(
            "{label} SHA-256 mismatch: expected {}, actual {actual}",
            expected.sha256
        ));
    }
    Ok(file)
}

fn verify_clean_tree(game_dir: &Path, manifest_path: &Path) -> Result<usize, String> {
    let root_metadata = fs::symlink_metadata(game_dir)
        .map_err(|error| format!("inspect clean game directory: {error}"))?;
    if !root_metadata.file_type().is_dir() || root_metadata.permissions().mode() & 0o222 != 0 {
        return Err("clean game directory must be a read-only, non-symlink directory".to_owned());
    }
    let manifest = parse_manifest(manifest_path)?;
    let actual = collect_tree(game_dir, game_dir)?;
    if actual.len() != manifest.len() {
        return Err(format!(
            "clean tree file count mismatch: expected {}, actual {}",
            manifest.len(),
            actual.len()
        ));
    }
    for (path, expected) in &manifest {
        let actual_path = actual
            .get(path)
            .ok_or_else(|| format!("clean tree is missing manifest path {path:?}"))?;
        verify_file(
            &format!("clean tree file {path:?}"),
            actual_path,
            &InputIdentity {
                sha256: expected.sha256.clone(),
                byte_count: expected.byte_count,
            },
            false,
        )?;
    }
    Ok(manifest.len())
}

fn parse_manifest(path: &Path) -> Result<BTreeMap<String, ManifestEntry>, String> {
    let text = fs::read_to_string(path).map_err(|error| format!("read clean manifest: {error}"))?;
    let mut entries = BTreeMap::new();
    let mut folded = BTreeSet::new();
    for (line_index, line) in text.lines().enumerate() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        if fields.len() != 3 {
            return Err(format!(
                "clean manifest line {} must have three fields",
                line_index + 1
            ));
        }
        let relative = Path::new(fields[2]);
        if fields[2].is_empty()
            || fields[2].contains('\\')
            || relative
                .components()
                .any(|component| !matches!(component, Component::Normal(_)))
        {
            return Err(format!(
                "clean manifest line {} has an unsafe path",
                line_index + 1
            ));
        }
        if fields[0].len() != 64 || !fields[0].bytes().all(|byte| byte.is_ascii_hexdigit()) {
            return Err(format!(
                "clean manifest line {} has an invalid SHA-256",
                line_index + 1
            ));
        }
        let byte_count = fields[1].parse::<u64>().map_err(|error| {
            format!(
                "clean manifest line {} has an invalid size: {error}",
                line_index + 1
            )
        })?;
        let key = fields[2].to_owned();
        if !folded.insert(key.to_ascii_lowercase()) {
            return Err(format!(
                "clean manifest has a duplicate or case-colliding path {key:?}"
            ));
        }
        if entries
            .insert(
                key.clone(),
                ManifestEntry {
                    sha256: fields[0].to_ascii_lowercase(),
                    byte_count,
                },
            )
            .is_some()
        {
            return Err(format!("clean manifest has duplicate path {key:?}"));
        }
    }
    if entries.is_empty() {
        return Err("clean manifest contains no files".to_owned());
    }
    Ok(entries)
}

fn collect_tree(root: &Path, directory: &Path) -> Result<BTreeMap<String, PathBuf>, String> {
    let mut files = BTreeMap::new();
    collect_tree_into(root, directory, &mut files)?;
    Ok(files)
}

fn collect_tree_into(
    root: &Path,
    directory: &Path,
    files: &mut BTreeMap<String, PathBuf>,
) -> Result<(), String> {
    for entry in fs::read_dir(directory).map_err(|error| format!("read clean tree: {error}"))? {
        let entry = entry.map_err(|error| format!("read clean tree entry: {error}"))?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path)
            .map_err(|error| format!("inspect clean tree entry: {error}"))?;
        if metadata.permissions().mode() & 0o222 != 0 {
            return Err("clean tree entries must be read-only".to_owned());
        }
        if metadata.file_type().is_symlink() {
            return Err("clean tree must not contain symlinks".to_owned());
        }
        if metadata.is_dir() {
            collect_tree_into(root, &path, files)?;
        } else if metadata.is_file() {
            let relative = path
                .strip_prefix(root)
                .map_err(|error| format!("make clean tree path relative: {error}"))?;
            let key = relative
                .components()
                .map(|component| component.as_os_str().to_string_lossy())
                .collect::<Vec<_>>()
                .join("/");
            if files.insert(key.clone(), path).is_some() {
                return Err(format!("clean tree has duplicate path {key:?}"));
            }
        } else {
            return Err("clean tree contains an unsupported file type".to_owned());
        }
    }
    Ok(())
}

fn verify_endpoint(stdout: &str) -> Result<(), String> {
    let lines: Vec<&str> = stdout.lines().collect();
    if lines.len() != 4 {
        return Err(format!(
            "smoke runner emitted {} lines; expected four",
            lines.len()
        ));
    }
    verify_saved_line(lines[0], "normal", true)?;
    verify_saved_line(lines[1], "again", false)?;
    if lines[2] != "ok    again: the save is the same as normal" {
        return Err("smoke runner did not report byte-identical again/normal saves".to_owned());
    }
    if lines[3] != "PASS" {
        return Err("smoke runner did not finish with PASS".to_owned());
    }
    Ok(())
}

fn verify_saved_line(line: &str, run: &str, require_idle: bool) -> Result<(), String> {
    let prefix = format!("run   {run}: saved after 14 game days in ");
    let rest = line
        .strip_prefix(&prefix)
        .ok_or_else(|| format!("smoke runner did not report the {run} 14-day save"))?;
    let (seconds, sleeps) = rest
        .split_once(" s, idle sleeps ")
        .ok_or_else(|| format!("smoke runner {run} line has an unexpected shape"))?;
    seconds
        .parse::<u64>()
        .map_err(|_| format!("smoke runner {run} duration is not an integer"))?;
    let sleeps = sleeps
        .parse::<u64>()
        .map_err(|_| format!("smoke runner {run} idle count is not an integer"))?;
    if require_idle && sleeps == 0 {
        return Err("smoke runner normal run observed no idle sleeps".to_owned());
    }
    Ok(())
}

fn write_diagnostics(stdout: &str, stderr: &str, config: &BackendConfig) -> Result<(), String> {
    let mut text = format!("smoke runner stdout:\n{stdout}");
    if !stderr.is_empty() {
        text.push_str("smoke runner stderr:\n");
        text.push_str(stderr);
        if !stderr.ends_with('\n') {
            text.push('\n');
        }
    }
    for path in [
        &config.python_executable,
        &config.smoke_runner,
        &config.bosman_executable,
        &config.clean_game_dir,
        &config.clean_manifest,
    ] {
        text = text.replace(&path.to_string_lossy().to_string(), "[private-path]");
    }
    std::io::stderr()
        .write_all(text.as_bytes())
        .map_err(|error| format!("write sanitized diagnostics: {error}"))
}

fn emit(
    request: &RunRequest,
    sequence: u64,
    kind: &str,
    payload: serde_json::Value,
) -> Result<(), String> {
    let frame = json!({
        "protocol_version": 1,
        "attempt_id": request.attempt_id,
        "sequence": sequence,
        "kind": kind,
        "payload": payload,
    });
    let mut stdout = std::io::stdout().lock();
    serde_json::to_writer(&mut stdout, &frame)
        .map_err(|error| format!("serialize protocol frame: {error}"))?;
    stdout
        .write_all(b"\n")
        .and_then(|()| stdout.flush())
        .map_err(|error| format!("write protocol frame: {error}"))
}

fn launch_bosman(arguments: &[String]) -> Result<(), String> {
    if arguments.len() != 4
        || arguments[0] != "--game"
        || arguments[2] != "-seed"
        || arguments[3] != "1"
    {
        return Err("launcher accepts only --game <clean-dir> -seed 1".to_owned());
    }
    let config = read_config()?;
    if Path::new(&arguments[1]) != config.clean_game_dir {
        return Err("launcher game directory does not match private config".to_owned());
    }
    let expected_hash = required_env("LAB_BOSMAN_EXPECTED_SHA256")?;
    let metadata = fs::metadata(&config.bosman_executable)
        .map_err(|error| format!("inspect Bosman executable: {error}"))?;
    let identity = InputIdentity {
        sha256: expected_hash,
        byte_count: metadata.len(),
    };
    let executable = verify_file(
        "Bosman executable",
        &config.bosman_executable,
        &identity,
        true,
    )?;
    let executable_path = format!("/proc/self/fd/{}", executable.as_raw_fd());
    let mut command = Command::new(executable_path);
    command.args(arguments).env_clear();
    for name in [
        "HOME",
        "TMPDIR",
        "TZ",
        "LC_ALL",
        "LANG",
        "SDL_VIDEODRIVER",
        "SDL_AUDIODRIVER",
        "RECOMP_NO_BOX",
        "RECOMP_USER_DIR",
        "RECOMP_FIXED_CLOCK",
        "RECOMP_SAVE_AFTER_DAYS",
        "RECOMP_IDLE_COUNT",
        "RECOMP_SCRIPT",
    ] {
        if let Some(value) = env::var_os(name) {
            command.env(name, value);
        }
    }
    let error = command.exec();
    Err(format!("launch Bosman executable: {error}"))
}

fn digest_reader(file: &mut File, label: &str) -> Result<String, String> {
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let count = file
            .read(&mut buffer)
            .map_err(|error| format!("hash {label}: {error}"))?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_only_exact_success_endpoint() {
        let good = "run   normal: saved after 14 game days in 83 s, idle sleeps 21017\n\
                    run   again: saved after 14 game days in 83 s, idle sleeps 21024\n\
                    ok    again: the save is the same as normal\n\
                    PASS\n";
        assert!(verify_endpoint(good).is_ok());
        assert!(verify_endpoint(&good.replace("PASS", "FAIL")).is_err());
        assert!(verify_endpoint(&good.replace("21017", "0")).is_err());
        assert!(verify_endpoint(&good.replace("the same", "different")).is_err());
    }

    #[test]
    fn rejects_unsafe_and_case_colliding_manifest_paths() {
        let base = env::temp_dir().join(format!("lab-bosman-manifest-{}", std::process::id()));
        let _ = fs::remove_dir_all(&base);
        fs::create_dir(&base).unwrap();
        let unsafe_path = base.join("unsafe.tsv");
        fs::write(&unsafe_path, format!("{}\t1\t../escape\n", "a".repeat(64))).unwrap();
        assert!(parse_manifest(&unsafe_path).unwrap_err().contains("unsafe"));
        let collision = base.join("collision.tsv");
        fs::write(
            &collision,
            format!(
                "{}\t1\tData/a.dat\n{}\t1\tdata/A.dat\n",
                "a".repeat(64),
                "b".repeat(64)
            ),
        )
        .unwrap();
        assert!(
            parse_manifest(&collision)
                .unwrap_err()
                .contains("case-colliding")
        );
        fs::remove_dir_all(base).unwrap();
    }
}
