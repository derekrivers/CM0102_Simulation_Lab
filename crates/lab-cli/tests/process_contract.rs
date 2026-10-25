use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const CLI: &str = env!("CARGO_BIN_EXE_lab-cli");
const FIXTURE: &str = env!("CARGO_BIN_EXE_lab-protocol-fixture");
const ONE_MIB: u64 = 1024 * 1024;
static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new(label: &str) -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock must follow the Unix epoch")
            .as_nanos();
        let sequence = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "lab-cli-{label}-{}-{nonce}-{sequence}",
            std::process::id()
        ));
        fs::create_dir(&path).expect("create unique test directory");
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TestDirectory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn fixture_digest() -> String {
    digest(&fs::read(FIXTURE).expect("read fixture executable"))
}

fn request(mode: &str, expected_hash: &str, timeout_ms: u64) -> Value {
    json!({
        "schema_version": 1,
        "attempt_id": format!("attempt-{mode}"),
        "scenario_id": mode,
        "profile_id": "test-profile",
        "backend": {
            "kind": "synthetic-test",
            "source_revision": "144ed82c248228c7769c6785899527eae5b33c3d",
            "expected_executable_sha256": expected_hash
        },
        "expected_stop_condition": "fixture-complete",
        "timeout_ms": timeout_ms,
        "stdout_limit_bytes": ONE_MIB,
        "stderr_limit_bytes": ONE_MIB,
        "input_identities": [],
        "commands": [
            {"id": "command-1", "kind": "synthetic", "parameters": {"step": 1}},
            {"id": "command-2", "kind": "synthetic", "parameters": {"step": 2}}
        ]
    })
}

fn write_request(root: &Path, value: &Value) -> PathBuf {
    let path = root.join("request.json");
    fs::write(
        &path,
        serde_json::to_vec_pretty(value).expect("serialize request"),
    )
    .expect("write request");
    path
}

fn execute(root: &Path, mode: &str, timeout_ms: u64) -> (PathBuf, Output) {
    let request_path = write_request(root, &request(mode, &fixture_digest(), timeout_ms));
    let attempt_path = root.join("attempt");
    let output = Command::new(CLI)
        .args(["execute-process", "--request"])
        .arg(request_path)
        .arg("--backend-executable")
        .arg(FIXTURE)
        .arg("--attempt-dir")
        .arg(&attempt_path)
        .output()
        .expect("run lab-cli");
    (attempt_path, output)
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn valid_execution_publishes_hashed_replay_without_private_paths() {
    let root = TestDirectory::new("valid");
    let (attempt, output) = execute(root.path(), "valid-replay", 2_000);
    assert!(output.status.success(), "{}", stderr(&output));

    let stdout = fs::read(attempt.join("stdout.ndjson")).expect("read captured protocol");
    let diagnostics = fs::read(attempt.join("stderr.log")).expect("read diagnostics");
    let canonical_request = fs::read(attempt.join("request.json")).expect("read canonical request");
    let manifest_bytes =
        fs::read(attempt.join("replay-manifest.json")).expect("read replay manifest");
    let manifest: Value = serde_json::from_slice(&manifest_bytes).expect("parse replay manifest");

    assert_eq!(manifest["execution"]["status"], "succeeded");
    assert_eq!(manifest["execution"]["reason"], "completed-target");
    assert_eq!(manifest["comparison_verdict"], "not-run");
    let validation = Command::new(CLI)
        .args(["validate-run", "--request"])
        .arg(root.path().join("request.json"))
        .output()
        .expect("validate replay request");
    assert!(validation.status.success(), "{}", stderr(&validation));
    let validation: Value =
        serde_json::from_slice(&validation.stdout).expect("parse validation report");
    assert_eq!(manifest["request_sha256"], validation["request_sha256"]);
    assert_eq!(
        manifest["artifacts"]["request"]["sha256"],
        digest(&canonical_request)
    );
    assert_eq!(manifest["request_sha256"], digest(&canonical_request));
    assert_eq!(manifest["artifacts"]["stdout"]["sha256"], digest(&stdout));
    assert_eq!(manifest["artifacts"]["stdout"]["byte_count"], stdout.len());
    assert_eq!(
        manifest["artifacts"]["stderr"]["sha256"],
        digest(&diagnostics)
    );
    assert_eq!(manifest["command_count"], 2);
    let manifest_text = String::from_utf8(manifest_bytes).expect("manifest is UTF-8");
    assert!(!manifest_text.contains(&root.path().display().to_string()));
    assert!(!attempt.join(".stdout.ndjson.tmp").exists());
    assert!(!attempt.join(".request.json.tmp").exists());
    assert!(!attempt.join(".stderr.log.tmp").exists());
    assert!(!attempt.join(".replay-manifest.json.tmp").exists());
}

#[test]
fn validator_rejects_malformed_and_oversize_requests_deterministically() {
    let root = TestDirectory::new("invalid-request");
    let malformed = root.path().join("malformed.json");
    fs::write(&malformed, b"{\"schema_version\":1,\"unknown\":true}")
        .expect("write malformed request");
    let run = || {
        Command::new(CLI)
            .args(["validate-run", "--request"])
            .arg(&malformed)
            .output()
            .expect("run validator")
    };
    let first = run();
    let second = run();
    assert!(!first.status.success());
    assert_eq!(first.stderr, second.stderr);

    let oversize = root.path().join("oversize.json");
    fs::write(&oversize, vec![b' '; 1024 * 1024 + 1]).expect("write oversized request");
    let output = Command::new(CLI)
        .args(["validate-run", "--request"])
        .arg(oversize)
        .output()
        .expect("run validator");
    assert!(!output.status.success());
    assert!(stderr(&output).contains("1048576-byte limit"));
}

#[test]
fn valid_validator_output_is_byte_stable() {
    let root = TestDirectory::new("validator-stable");
    let request_value = request("valid", &fixture_digest(), 2_000);
    let request_path = write_request(root.path(), &request_value);
    let run = || {
        Command::new(CLI)
            .args(["validate-run", "--request"])
            .arg(&request_path)
            .output()
            .expect("run validator")
    };
    let first = run();
    fs::write(
        &request_path,
        serde_json::to_vec(&request_value).expect("serialize compact request"),
    )
    .expect("rewrite request with different whitespace");
    let second = run();
    assert!(first.status.success(), "{}", stderr(&first));
    assert_eq!(first.stdout, second.stdout);

    let mut uppercase = request_value;
    uppercase["backend"]["source_revision"] = Value::String(
        uppercase["backend"]["source_revision"]
            .as_str()
            .unwrap()
            .to_uppercase(),
    );
    uppercase["backend"]["expected_executable_sha256"] = Value::String(
        uppercase["backend"]["expected_executable_sha256"]
            .as_str()
            .unwrap()
            .to_uppercase(),
    );
    fs::write(
        &request_path,
        serde_json::to_vec(&uppercase).expect("serialize uppercase request"),
    )
    .expect("rewrite request with uppercase hashes");
    let third = run();
    assert!(third.status.success(), "{}", stderr(&third));
    assert_eq!(first.stdout, third.stdout);
}

#[test]
fn executable_hash_mismatch_is_rejected_before_spawn() {
    let root = TestDirectory::new("hash-mismatch");
    let request_path = write_request(
        root.path(),
        &request("spawn-marker", &"0".repeat(64), 2_000),
    );
    let attempt = root.path().join("attempt");
    let output = Command::new(CLI)
        .args(["execute-process", "--request"])
        .arg(request_path)
        .arg("--backend-executable")
        .arg(FIXTURE)
        .arg("--attempt-dir")
        .arg(&attempt)
        .output()
        .expect("run lab-cli");
    assert!(!output.status.success());
    assert!(stderr(&output).contains("SHA-256 mismatch"));
    assert!(
        !attempt.exists(),
        "attempt creation must follow hash validation"
    );
}

#[test]
fn inherited_secret_is_absent_from_child_environment() {
    let root = TestDirectory::new("secret");
    let request_path = write_request(root.path(), &request("check-env", &fixture_digest(), 2_000));
    let attempt = root.path().join("attempt");
    let output = Command::new(CLI)
        .env("LAB_TEST_SECRET", "must-not-leak")
        .args(["execute-process", "--request"])
        .arg(request_path)
        .arg("--backend-executable")
        .arg(FIXTURE)
        .arg("--attempt-dir")
        .arg(&attempt)
        .output()
        .expect("run lab-cli");
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(attempt.join("replay-manifest.json").is_file());
}

#[test]
fn out_of_order_protocol_is_rejected() {
    let root = TestDirectory::new("sequence");
    let (_, output) = execute(root.path(), "out-of-order", 2_000);
    assert!(!output.status.success());
    assert!(stderr(&output).contains("sequence 2; expected 1"));
}

#[test]
fn missing_and_wrong_terminal_endpoints_are_rejected() {
    let missing_root = TestDirectory::new("missing-terminal");
    let (_, missing) = execute(missing_root.path(), "missing-terminal", 2_000);
    assert!(!missing.status.success());
    assert!(stderr(&missing).contains("no terminal frame"));

    let wrong_root = TestDirectory::new("wrong-terminal");
    let (_, wrong) = execute(wrong_root.path(), "wrong-terminal-stop", 2_000);
    assert!(!wrong.status.success());
    assert!(stderr(&wrong).contains("does not match expected"));
}

#[test]
fn mismatched_handshake_identity_is_rejected() {
    let root = TestDirectory::new("wrong-handshake");
    let (_, output) = execute(root.path(), "wrong-handshake", 2_000);
    assert!(!output.status.success());
    assert!(stderr(&output).contains("source_revision does not match"));
}

#[test]
fn output_cap_terminates_backend_and_rejects_execution() {
    let root = TestDirectory::new("output-cap");
    let (_, output) = execute(root.path(), "output-cap", 2_000);
    assert!(!output.status.success());
    assert!(stderr(&output).contains("stdout exceeded its configured byte limit"));
}

#[test]
fn timeout_kills_the_entire_process_group() {
    let root = TestDirectory::new("timeout");
    let started = Instant::now();
    let (attempt, output) = execute(root.path(), "timeout-group", 100);
    assert!(!output.status.success());
    assert!(stderr(&output).contains("timed out after 100 ms"));
    assert!(started.elapsed() < Duration::from_secs(5));

    let pid: u32 = fs::read_to_string(attempt.join("child.pid"))
        .expect("fixture recorded descendant PID")
        .trim()
        .parse()
        .expect("descendant PID is numeric");
    let proc_status = PathBuf::from(format!("/proc/{pid}/status"));
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        match fs::read_to_string(&proc_status) {
            Err(_) => break,
            Ok(status) if status.lines().any(|line| line.starts_with("State:\tZ")) => break,
            Ok(_) if Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
            Ok(status) => panic!("descendant process survived group kill:\n{status}"),
        }
    }
}

#[test]
fn timeout_kills_a_descendant_that_escaped_the_process_group() {
    let root = TestDirectory::new("timeout-escaped");
    let started = Instant::now();
    let (attempt, output) = execute(root.path(), "timeout-escaped", 100);
    assert!(!output.status.success());
    assert!(stderr(&output).contains("timed out after 100 ms"));
    assert!(started.elapsed() < Duration::from_secs(5));

    let pid: u32 = fs::read_to_string(attempt.join("child.pid"))
        .expect("fixture recorded escaped descendant PID")
        .trim()
        .parse()
        .expect("escaped descendant PID is numeric");
    assert!(
        !PathBuf::from(format!("/proc/{pid}")).exists(),
        "escaped descendant survived timeout cleanup"
    );
}

#[test]
fn escaped_descendant_cannot_hold_pipes_or_survive_success() {
    let root = TestDirectory::new("escaped-descendant");
    let started = Instant::now();
    let (attempt, output) = execute(root.path(), "escaped-descendant", 2_000);
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(started.elapsed() < Duration::from_secs(5));

    let pid: u32 = fs::read_to_string(attempt.join("child.pid"))
        .expect("fixture recorded escaped descendant PID")
        .trim()
        .parse()
        .expect("escaped descendant PID is numeric");
    assert!(
        !PathBuf::from(format!("/proc/{pid}")).exists(),
        "escaped descendant survived successful execution"
    );
}

#[test]
fn preexisting_attempt_directory_is_never_reused() {
    let root = TestDirectory::new("reuse");
    let request_path = write_request(root.path(), &request("valid", &fixture_digest(), 2_000));
    let attempt = root.path().join("attempt");
    fs::create_dir(&attempt).expect("create existing attempt");
    fs::write(attempt.join("owner.marker"), b"original\n").expect("write marker");
    let output = Command::new(CLI)
        .args(["execute-process", "--request"])
        .arg(request_path)
        .arg("--backend-executable")
        .arg(FIXTURE)
        .arg("--attempt-dir")
        .arg(&attempt)
        .output()
        .expect("run lab-cli");
    assert!(!output.status.success());
    assert!(stderr(&output).contains("create attempt directory"));
    assert_eq!(
        fs::read(attempt.join("owner.marker")).expect("marker remains"),
        b"original\n"
    );
    assert!(!attempt.join("stdout.ndjson").exists());
}

#[test]
fn failed_executions_publish_bounded_hashed_evidence() {
    for (mode, timeout, reason) in [
        ("timeout-group", 100, "timeout"),
        ("output-cap", 2000, "output-limit"),
        ("missing-terminal", 2000, "infrastructure-error"),
        ("unknown-mode", 2000, "crash"),
    ] {
        let root = TestDirectory::new(mode);
        let (attempt, output) = execute(root.path(), mode, timeout);
        assert!(!output.status.success());
        let manifest: Value =
            serde_json::from_slice(&fs::read(attempt.join("replay-manifest.json")).unwrap())
                .unwrap();
        assert_eq!(manifest["execution"]["status"], "failed");
        assert_eq!(manifest["execution"]["reason"], reason);
        assert_eq!(manifest["execution"]["stop_condition"], "");
        assert_eq!(manifest["comparison_verdict"], "not-run");
        for (key, name) in [
            ("request", "request.json"),
            ("stdout", "stdout.ndjson"),
            ("stderr", "stderr.log"),
        ] {
            let bytes = fs::read(attempt.join(name)).unwrap();
            assert!(bytes.len() <= ONE_MIB as usize);
            assert_eq!(manifest["artifacts"][key]["sha256"], digest(&bytes));
            assert_eq!(manifest["artifacts"][key]["byte_count"], bytes.len());
        }
        if mode == "output-cap" {
            assert_eq!(
                fs::metadata(attempt.join("stdout.ndjson")).unwrap().len(),
                ONE_MIB
            );
        }
        let published = fs::read(attempt.join("replay-manifest.json")).unwrap();
        let retry = Command::new(CLI)
            .args(["execute-process", "--request"])
            .arg(root.path().join("request.json"))
            .arg("--backend-executable")
            .arg(FIXTURE)
            .arg("--attempt-dir")
            .arg(&attempt)
            .output()
            .unwrap();
        assert!(!retry.status.success());
        assert_eq!(
            published,
            fs::read(attempt.join("replay-manifest.json")).unwrap()
        );
    }
}

#[test]
fn spawn_failure_still_publishes_the_admitted_attempt() {
    use std::os::unix::fs::PermissionsExt;
    let root = TestDirectory::new("spawn-failure");
    let backend = root.path().join("bad-interpreter");
    fs::write(&backend, b"#!/nonexistent/lab-test-interpreter\n").unwrap();
    fs::set_permissions(&backend, fs::Permissions::from_mode(0o500)).unwrap();
    let request_path = write_request(
        root.path(),
        &request("valid", &digest(&fs::read(&backend).unwrap()), 1000),
    );
    let attempt = root.path().join("attempt");
    let output = Command::new(CLI)
        .args(["execute-process", "--request"])
        .arg(request_path)
        .arg("--backend-executable")
        .arg(backend)
        .arg("--attempt-dir")
        .arg(&attempt)
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(stderr(&output).contains("spawn backend"));
    let manifest: Value =
        serde_json::from_slice(&fs::read(attempt.join("replay-manifest.json")).unwrap()).unwrap();
    assert_eq!(manifest["execution"]["status"], "failed");
    assert_eq!(manifest["execution"]["exit_code"], -1);
    assert_eq!(manifest["comparison_verdict"], "not-run");
    for name in ["request.json", "stdout.ndjson", "stderr.log"] {
        assert!(attempt.join(name).is_file());
    }
}
