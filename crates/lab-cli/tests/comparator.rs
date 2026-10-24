use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs;
use std::os::unix::fs::symlink;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

const CLI: &str = env!("CARGO_BIN_EXE_lab-cli");
static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new(label: &str) -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock")
            .as_nanos();
        let sequence = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "lab-comparator-{label}-{}-{nonce}-{sequence}",
            std::process::id()
        ));
        fs::create_dir(&path).expect("create test directory");
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

#[derive(Clone)]
struct SideOptions {
    raw: Vec<u8>,
    state: Value,
    scenario_sha256: String,
    capture_status: &'static str,
    truncated: bool,
    dropped_records: u64,
}

impl SideOptions {
    fn complete(raw: &[u8], state: Value) -> Self {
        Self {
            raw: raw.to_vec(),
            state,
            scenario_sha256: digest(b"scenario"),
            capture_status: "complete",
            truncated: false,
            dropped_records: 0,
        }
    }
}

struct Side {
    bundle_path: PathBuf,
    identity: Value,
}

fn rewrite_bundle(side: &mut Side, update: impl FnOnce(&mut Value)) {
    let mut bundle: Value =
        serde_json::from_slice(&fs::read(&side.bundle_path).expect("read bundle"))
            .expect("parse bundle");
    update(&mut bundle);
    let mut bytes = serde_json::to_vec(&bundle).expect("serialize updated bundle");
    bytes.push(b'\n');
    fs::write(&side.bundle_path, &bytes).expect("write updated bundle");
    side.identity = identity(&bytes);
}

fn rewrite_replay(side: &mut Side, update: impl FnOnce(&mut Value)) {
    let directory = side.bundle_path.parent().expect("bundle parent");
    let replay_path = directory.join("replay-manifest.json");
    let mut replay: Value = serde_json::from_slice(&fs::read(&replay_path).expect("read replay"))
        .expect("parse replay");
    update(&mut replay);
    let mut bytes = serde_json::to_vec(&replay).expect("serialize updated replay");
    bytes.push(b'\n');
    fs::write(&replay_path, &bytes).expect("write updated replay");
    rewrite_bundle(side, |bundle| {
        bundle["replay_manifest"]["byte_count"] = json!(bytes.len());
        bundle["replay_manifest"]["sha256"] = json!(digest(&bytes));
    });
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn identity(bytes: &[u8]) -> Value {
    json!({"byte_count": bytes.len(), "sha256": digest(bytes)})
}

fn artifact(file_name: &str, bytes: &[u8], media_type: &str) -> Value {
    json!({
        "file_name": file_name,
        "byte_count": bytes.len(),
        "sha256": digest(bytes),
        "media_type": media_type
    })
}

fn write_side(root: &Path, name: &str, options: SideOptions) -> Side {
    let side = root.join(name);
    fs::create_dir(&side).expect("create side");
    let request = b"{}\n";
    let stdout = b"{\"kind\":\"terminal\"}\n";
    let stderr = b"";
    fs::write(side.join("request.json"), request).expect("write request");
    fs::write(side.join("stdout.ndjson"), stdout).expect("write stdout");
    fs::write(side.join("stderr.log"), stderr).expect("write stderr");

    let replay = json!({
        "schema_version": 1,
        "request_sha256": digest(request),
        "attempt_id": format!("attempt-{name}"),
        "scenario_id": "scenario-one",
        "profile_id": "profile-one",
        "backend": {
            "kind": if name == "left" { "original-windows" } else { "bosman-native" },
            "source_revision": "1111111111111111111111111111111111111111",
            "executable_sha256": digest(format!("executable-{name}").as_bytes())
        },
        "input_identities": [],
        "command_stream_sha256": digest(b"commands"),
        "command_count": 1,
        "expected_stop_condition": "fixture-complete",
        "limits": {"timeout_ms": 1000, "stdout_bytes": 1048576, "stderr_bytes": 1048576},
        "execution": {
            "status": "succeeded",
            "reason": "completed-target",
            "stop_condition": "fixture-complete",
            "exit_code": 0
        },
        "comparison_verdict": "not-run",
        "artifacts": {
            "request": {"file_name": "request.json", "byte_count": request.len(), "sha256": digest(request)},
            "stdout": {"file_name": "stdout.ndjson", "byte_count": stdout.len(), "sha256": digest(stdout)},
            "stderr": {"file_name": "stderr.log", "byte_count": stderr.len(), "sha256": digest(stderr)}
        }
    });
    let mut replay_bytes = serde_json::to_vec(&replay).expect("serialize replay");
    replay_bytes.push(b'\n');
    fs::write(side.join("replay-manifest.json"), &replay_bytes).expect("write replay");

    fs::write(side.join("raw.bin"), &options.raw).expect("write raw");
    let semantic = json!({
        "schema_version": 1,
        "schema_id": "state-v1",
        "scope_sha256": digest(b"scope"),
        "state": options.state
    });
    let mut semantic_bytes = serde_json::to_vec(&semantic).expect("serialize semantic");
    semantic_bytes.push(b'\n');
    fs::write(side.join("semantic.json"), &semantic_bytes).expect("write semantic");

    let bundle = json!({
        "schema_version": 1,
        "replay_manifest": artifact("replay-manifest.json", &replay_bytes, "application/json"),
        "comparison_key": {
            "scenario_id": "scenario-one",
            "profile_id": "profile-one",
            "scenario_sha256": options.scenario_sha256,
            "baseline_data_sha256": digest(b"data"),
            "fixture_sha256": digest(b"fixture"),
            "logical_command_stream_sha256": digest(b"logical-commands"),
            "rng_policy_sha256": digest(b"rng-policy"),
            "clock_policy_sha256": digest(b"clock-policy"),
            "observation_schema": {"id": "state-v1", "version": 1, "sha256": digest(b"state-schema")},
            "semantic_scope_sha256": digest(b"scope")
        },
        "capture": {
            "status": options.capture_status,
            "truncated": options.truncated,
            "dropped_records": options.dropped_records,
            "unparsed_byte_count": 0,
            "raw": artifact("raw.bin", &options.raw, "application/octet-stream"),
            "semantic": artifact("semantic.json", &semantic_bytes, "application/json")
        }
    });
    let mut bundle_bytes = serde_json::to_vec(&bundle).expect("serialize bundle");
    bundle_bytes.push(b'\n');
    let bundle_path = side.join("observation-bundle.json");
    fs::write(&bundle_path, &bundle_bytes).expect("write bundle");
    Side {
        bundle_path,
        identity: identity(&bundle_bytes),
    }
}

fn cli_digest() -> String {
    digest(&fs::read(CLI).expect("read CLI"))
}

fn write_comparison_request(root: &Path, left: &Side, right: &Side, raw_mode: &str) -> PathBuf {
    let request = json!({
        "schema_version": 1,
        "comparison_id": "comparison-one",
        "comparator": {
            "source_revision": "2222222222222222222222222222222222222222",
            "expected_executable_sha256": cli_digest()
        },
        "left_bundle": left.identity,
        "right_bundle": right.identity,
        "policy": {"id": "exact-observation-v1", "raw_mode": raw_mode, "semantic_mode": "exact-json"}
    });
    let path = root.join("comparison-request.json");
    fs::write(
        &path,
        serde_json::to_vec(&request).expect("serialize request"),
    )
    .expect("write comparison request");
    path
}

fn run_compare(
    root: &Path,
    left: &Side,
    right: &Side,
    raw_mode: &str,
    output_name: &str,
) -> Output {
    let request = write_comparison_request(root, left, right, raw_mode);
    Command::new(CLI)
        .args(["compare-observations", "--request"])
        .arg(request)
        .arg("--left-bundle")
        .arg(&left.bundle_path)
        .arg("--right-bundle")
        .arg(&right.bundle_path)
        .arg("--output-dir")
        .arg(root.join(output_name))
        .output()
        .expect("run comparator")
}

fn report(root: &Path, output_name: &str) -> Value {
    serde_json::from_slice(
        &fs::read(root.join(output_name).join("comparison-report.json")).expect("read report"),
    )
    .expect("parse report")
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn exact_aa_is_equal_and_byte_stable_without_paths() {
    let root = TestDirectory::new("aa");
    let state = json!({"day": 14, "events": ["a", "b"], "rng_calls": 7});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same raw", state.clone()),
    );
    let right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"same raw", state),
    );
    let first = run_compare(root.path(), &left, &right, "exact", "first");
    assert!(first.status.success(), "{}", stderr(&first));
    let second = run_compare(root.path(), &left, &right, "exact", "second");
    assert!(second.status.success(), "{}", stderr(&second));
    let parsed = report(root.path(), "first");
    assert_eq!(parsed["verdict"], "equal");
    assert_eq!(parsed["verdict_scope"], "raw-and-semantic-exact");
    assert_eq!(parsed["raw"]["identity_relation"], "equal");
    let first_bytes = fs::read(root.path().join("first/comparison-report.json")).unwrap();
    let second_bytes = fs::read(root.path().join("second/comparison-report.json")).unwrap();
    assert_eq!(first_bytes, second_bytes);
    assert!(
        !String::from_utf8(first_bytes)
            .unwrap()
            .contains(&root.path().display().to_string())
    );
}

#[test]
fn raw_byte_and_length_mutations_are_detected() {
    let root = TestDirectory::new("raw-diff");
    let state = json!({"day": 14});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"abcdef", state.clone()),
    );
    let right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"abcxef", state),
    );
    let output = run_compare(root.path(), &left, &right, "exact", "byte");
    assert!(output.status.success(), "{}", stderr(&output));
    let parsed = report(root.path(), "byte");
    assert_eq!(parsed["verdict"], "different");
    assert_eq!(parsed["raw"]["first_differing_offset"], 3);

    let root = TestDirectory::new("raw-length");
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"abc", json!({"day": 14})),
    );
    let right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"abcd", json!({"day": 14})),
    );
    let output = run_compare(root.path(), &left, &right, "exact", "length");
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(
        report(root.path(), "length")["raw"]["first_differing_offset"],
        3
    );
}

#[test]
fn semantic_mutations_and_reordering_are_detected_by_pointer() {
    let root = TestDirectory::new("semantic");
    let left_state = json!({"finance": {"cash": 10}, "events": ["a", "b"], "rng": {"calls": 2}});
    let right_state = json!({"finance": {"cash": 11}, "events": ["b", "a"], "rng": {}});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", left_state),
    );
    let right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"same", right_state),
    );
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(output.status.success(), "{}", stderr(&output));
    let parsed = report(root.path(), "out");
    assert_eq!(parsed["verdict"], "different");
    let pointers: Vec<_> = parsed["semantic"]["differences"]
        .as_array()
        .unwrap()
        .iter()
        .map(|difference| difference["pointer"].as_str().unwrap())
        .collect();
    assert_eq!(
        pointers,
        vec!["/events/0", "/events/1", "/finance/cash", "/rng/calls"]
    );
    assert_eq!(
        parsed["semantic"]["differences"][3]["kind"],
        "missing-right"
    );
}

#[test]
fn retain_only_keeps_raw_difference_visible_but_scopes_equal_to_semantics() {
    let root = TestDirectory::new("retain-only");
    let state = json!({"day": 14});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"left", state.clone()),
    );
    let right = write_side(root.path(), "right", SideOptions::complete(b"right", state));
    let output = run_compare(root.path(), &left, &right, "retain-only", "out");
    assert!(output.status.success(), "{}", stderr(&output));
    let parsed = report(root.path(), "out");
    assert_eq!(parsed["verdict"], "equal");
    assert_eq!(parsed["verdict_scope"], "semantic-exact");
    assert_eq!(parsed["raw"]["comparison_status"], "not-compared");
    assert_eq!(parsed["raw"]["identity_relation"], "different");
}

#[test]
fn incompatible_key_and_incomplete_capture_get_scientific_non_pass_verdicts() {
    let root = TestDirectory::new("not-comparable");
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    let mut options = SideOptions::complete(b"same", json!({"day": 14}));
    options.scenario_sha256 = digest(b"other scenario");
    let right = write_side(root.path(), "right", options);
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(report(root.path(), "out")["verdict"], "not-comparable");

    let root = TestDirectory::new("incomplete");
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    let mut options = SideOptions::complete(b"same", json!({"day": 14}));
    options.dropped_records = 1;
    let right = write_side(root.path(), "right", options);
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(report(root.path(), "out")["verdict"], "inconclusive");
}

#[test]
fn corrupt_or_symlinked_evidence_fails_without_output() {
    let root = TestDirectory::new("corrupt");
    let state = json!({"day": 14});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", state.clone()),
    );
    let right = write_side(root.path(), "right", SideOptions::complete(b"same", state));
    fs::write(root.path().join("right/raw.bin"), b"changed after bundle").unwrap();
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());

    let root = TestDirectory::new("symlink");
    let state = json!({"day": 14});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", state.clone()),
    );
    let right = write_side(root.path(), "right", SideOptions::complete(b"same", state));
    fs::remove_file(root.path().join("right/raw.bin")).unwrap();
    symlink(
        root.path().join("left/raw.bin"),
        root.path().join("right/raw.bin"),
    )
    .unwrap();
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());
}

#[test]
fn floats_unknown_policy_fields_and_existing_output_are_rejected() {
    let root = TestDirectory::new("float");
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", json!({"rating": 1.5})),
    );
    let right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"same", json!({"rating": 1.5})),
    );
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());

    let root = TestDirectory::new("mask");
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    let right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    let request_path = write_comparison_request(root.path(), &left, &right, "exact");
    let mut request: Value = serde_json::from_slice(&fs::read(&request_path).unwrap()).unwrap();
    request["policy"]["ignored_paths"] = json!(["/day"]);
    fs::write(&request_path, serde_json::to_vec(&request).unwrap()).unwrap();
    let output = Command::new(CLI)
        .args(["compare-observations", "--request"])
        .arg(&request_path)
        .arg("--left-bundle")
        .arg(&left.bundle_path)
        .arg("--right-bundle")
        .arg(&right.bundle_path)
        .arg("--output-dir")
        .arg(root.path().join("out"))
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());

    fs::create_dir(root.path().join("out")).unwrap();
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(!output.status.success());
}

#[test]
fn duplicate_keys_unsafe_paths_and_failed_replays_are_invalid_evidence() {
    let root = TestDirectory::new("duplicate-key");
    let state = json!({"day": 14});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", state.clone()),
    );
    let mut right = write_side(root.path(), "right", SideOptions::complete(b"same", state));
    let duplicate = format!(
        "{{\"schema_version\":1,\"schema_id\":\"state-v1\",\"scope_sha256\":\"{}\",\"state\":{{\"day\":14,\"day\":15}}}}\n",
        digest(b"scope")
    );
    let duplicate_bytes = duplicate.as_bytes();
    fs::write(
        right.bundle_path.parent().unwrap().join("semantic.json"),
        duplicate_bytes,
    )
    .unwrap();
    rewrite_bundle(&mut right, |bundle| {
        bundle["capture"]["semantic"]["byte_count"] = json!(duplicate_bytes.len());
        bundle["capture"]["semantic"]["sha256"] = json!(digest(duplicate_bytes));
    });
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());

    let root = TestDirectory::new("unsafe-path");
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    let mut right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    rewrite_bundle(&mut right, |bundle| {
        bundle["capture"]["raw"]["file_name"] = json!("../left/raw.bin");
    });
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());

    let root = TestDirectory::new("failed-replay");
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    let mut right = write_side(
        root.path(),
        "right",
        SideOptions::complete(b"same", json!({"day": 14})),
    );
    rewrite_replay(&mut right, |replay| {
        replay["execution"]["status"] = json!("failed");
    });
    let output = run_compare(root.path(), &left, &right, "exact", "out");
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());
}

#[test]
fn bundle_identity_drift_is_rejected_before_publication() {
    let root = TestDirectory::new("bundle-drift");
    let state = json!({"day": 14});
    let left = write_side(
        root.path(),
        "left",
        SideOptions::complete(b"same", state.clone()),
    );
    let right = write_side(root.path(), "right", SideOptions::complete(b"same", state));
    let request = write_comparison_request(root.path(), &left, &right, "exact");
    let mut bytes = fs::read(&right.bundle_path).unwrap();
    bytes.push(b' ');
    fs::write(&right.bundle_path, bytes).unwrap();
    let output = Command::new(CLI)
        .args(["compare-observations", "--request"])
        .arg(request)
        .arg("--left-bundle")
        .arg(&left.bundle_path)
        .arg("--right-bundle")
        .arg(&right.bundle_path)
        .arg("--output-dir")
        .arg(root.path().join("out"))
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(!root.path().join("out").exists());
}
