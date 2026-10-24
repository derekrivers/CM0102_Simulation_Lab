use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

const ADAPTER: &str = env!("CARGO_BIN_EXE_lab-bosman-adapter");
static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new() -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let sequence = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "lab-bosman-adapter-{}-{nonce}-{sequence}",
            std::process::id()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
}

impl Drop for TestDirectory {
    fn drop(&mut self) {
        make_writable(&self.0);
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn make_writable(path: &Path) {
    let Ok(metadata) = fs::symlink_metadata(path) else {
        return;
    };
    if metadata.is_dir() {
        let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o700));
        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                make_writable(&entry.path());
            }
        }
    } else if !metadata.file_type().is_symlink() {
        let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o600));
    }
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn file_identity(path: &Path) -> Value {
    let bytes = fs::read(path).unwrap();
    json!({"sha256": digest(&bytes), "byte_count": bytes.len()})
}

fn write_executable(path: &Path, body: &str) {
    fs::write(path, body).unwrap();
    fs::set_permissions(path, fs::Permissions::from_mode(0o500)).unwrap();
}

fn fixture(pass: bool) -> (TestDirectory, PathBuf, PathBuf) {
    let root = TestDirectory::new();
    let game = root.0.join("clean-game");
    let home = root.0.join("home");
    let temp = root.0.join("tmp");
    fs::create_dir(&game).unwrap();
    fs::create_dir(&home).unwrap();
    fs::create_dir(&temp).unwrap();
    let game_file = game.join("Data.bin");
    fs::write(&game_file, b"clean-data").unwrap();
    fs::set_permissions(&game_file, fs::Permissions::from_mode(0o400)).unwrap();
    fs::set_permissions(&game, fs::Permissions::from_mode(0o500)).unwrap();

    let bosman = root.0.join("bosman");
    write_executable(&bosman, "#!/bin/sh\nexit 0\n");
    let runner = root.0.join("runner");
    let final_line = if pass { "PASS" } else { "FAIL" };
    fs::write(
        &runner,
        format!(
            "import sys\n\
             print('run   normal: saved after 14 game days in 1 s, idle sleeps 7')\n\
             print('run   again: saved after 14 game days in 1 s, idle sleeps 8')\n\
             print('ok    again: the save is the same as normal')\n\
             print('{final_line}')\n\
             print({:?}, file=sys.stderr)\n",
            game.display().to_string()
        ),
    )
    .unwrap();
    let manifest_bytes = format!(
        "# sha256\tsize\tpath\n{}\t10\tData.bin\n",
        digest(b"clean-data")
    );
    let manifest = root.0.join("manifest.tsv");
    fs::write(&manifest, manifest_bytes).unwrap();
    let python = Path::new("/usr/bin/python3.12");
    assert!(python.is_file(), "integration fixture requires Python 3.12");

    let config = root.0.join("config.json");
    fs::write(
        &config,
        serde_json::to_vec(&json!({
            "python_executable": python,
            "smoke_runner": runner,
            "bosman_executable": bosman,
            "clean_game_dir": game,
            "clean_manifest": manifest
        }))
        .unwrap(),
    )
    .unwrap();

    let request = root.0.join("request.json");
    fs::write(
        &request,
        serde_json::to_vec(&json!({
            "schema_version": 1,
            "attempt_id": if pass { "adapter-success" } else { "adapter-failure" },
            "scenario_id": "adapter-test",
            "profile_id": "adapter-test",
            "backend": {
                "kind": "bosman-native",
                "source_revision": "a".repeat(40),
                "expected_executable_sha256": "b".repeat(64)
            },
            "expected_stop_condition": "classic-same-save-normal-again-14-days-equal",
            "timeout_ms": 1000,
            "stdout_limit_bytes": 1048576,
            "stderr_limit_bytes": 1048576,
            "input_identities": [
                file_identity(&bosman),
                file_identity(&manifest),
                file_identity(&runner),
                file_identity(python)
            ],
            "commands": [{
                "id": "same-save-1",
                "kind": "bosman-classic-same-save-v1",
                "parameters": {
                    "mode": "classic",
                    "days": 14,
                    "jobs": 2,
                    "runs": ["normal", "again"],
                    "seed": 1,
                    "fixed_clock": true,
                    "expected_save_relation": "byte-identical",
                    "input_slots": {
                        "bosman_executable": 0,
                        "clean_manifest": 1,
                        "smoke_runner": 2,
                        "python_interpreter": 3
                    }
                }
            }]
        }))
        .unwrap(),
    )
    .unwrap();
    (root, request, config)
}

fn run_adapter(root: &TestDirectory, request: &Path, config: &Path) -> Output {
    Command::new(ADAPTER)
        .env_clear()
        .env("LAB_BACKEND_CONFIG", config)
        .env("HOME", root.0.join("home"))
        .env("TMPDIR", root.0.join("tmp"))
        .stdin(fs::File::open(request).unwrap())
        .output()
        .unwrap()
}

#[test]
fn adapter_emits_success_only_for_the_exact_nested_endpoint_and_redacts_paths() {
    let (success_root, request, config) = fixture(true);
    let output = run_adapter(&success_root, &request, &config);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let frames: Vec<Value> = output
        .stdout
        .split(|byte| *byte == b'\n')
        .filter(|line| !line.is_empty())
        .map(|line| serde_json::from_slice(line).unwrap())
        .collect();
    assert_eq!(frames.len(), 6);
    assert_eq!(frames[0]["kind"], "handshake");
    assert_eq!(frames[5]["kind"], "terminal");
    assert_eq!(frames[5]["payload"]["execution_status"], "succeeded");
    let diagnostics = String::from_utf8(output.stderr).unwrap();
    assert!(diagnostics.contains("[private-path]"));
    assert!(!diagnostics.contains(&success_root.0.join("clean-game").display().to_string()));

    let (failure_root, request, config) = fixture(false);
    let output = run_adapter(&failure_root, &request, &config);
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("did not finish with PASS"));
    assert!(!String::from_utf8_lossy(&output.stdout).contains("\"kind\":\"terminal\""));
}
