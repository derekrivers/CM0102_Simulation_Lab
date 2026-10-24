use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::ffi::CString;
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{DirBuilderExt, OpenOptionsExt};
use std::path::{Component, Path};

const JSON_MAX_BYTES: u64 = 16 * 1024 * 1024;
const BUNDLE_MAX_BYTES: u64 = 1024 * 1024;
const MAX_JSON_DEPTH: usize = 64;
const MAX_DIFFERENCE_SAMPLES: usize = 64;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ComparisonRequest {
    schema_version: u32,
    comparison_id: String,
    comparator: ComparatorIdentity,
    left_bundle: Identity,
    right_bundle: Identity,
    policy: ComparisonPolicy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ComparatorIdentity {
    source_revision: String,
    expected_executable_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Identity {
    byte_count: u64,
    sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ComparisonPolicy {
    id: String,
    raw_mode: RawMode,
    semantic_mode: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
enum RawMode {
    Exact,
    RetainOnly,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ObservationBundle {
    schema_version: u32,
    replay_manifest: ArtifactRef,
    comparison_key: ComparisonKey,
    capture: Capture,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ComparisonKey {
    scenario_id: String,
    profile_id: String,
    scenario_sha256: String,
    baseline_data_sha256: String,
    fixture_sha256: String,
    logical_command_stream_sha256: String,
    rng_policy_sha256: String,
    clock_policy_sha256: String,
    observation_schema: ObservationSchema,
    semantic_scope_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ObservationSchema {
    id: String,
    version: u32,
    sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Capture {
    status: CaptureStatus,
    truncated: bool,
    dropped_records: u64,
    unparsed_byte_count: u64,
    raw: ArtifactRef,
    semantic: ArtifactRef,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
enum CaptureStatus {
    Complete,
    Incomplete,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ArtifactRef {
    file_name: String,
    byte_count: u64,
    sha256: String,
    media_type: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SemanticArtifact {
    schema_version: u32,
    schema_id: String,
    scope_sha256: String,
    state: Value,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayManifest {
    schema_version: u32,
    request_sha256: String,
    attempt_id: String,
    scenario_id: String,
    profile_id: String,
    backend: ReplayBackend,
    input_identities: Value,
    command_stream_sha256: String,
    command_count: u64,
    expected_stop_condition: String,
    limits: Value,
    execution: ReplayExecution,
    comparison_verdict: String,
    artifacts: ReplayArtifacts,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayBackend {
    kind: String,
    source_revision: String,
    executable_sha256: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayExecution {
    status: String,
    reason: String,
    stop_condition: String,
    exit_code: i32,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayArtifacts {
    request: ReplayArtifact,
    stdout: ReplayArtifact,
    stderr: ReplayArtifact,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayArtifact {
    file_name: String,
    byte_count: u64,
    sha256: String,
}

struct LoadedObservation {
    bundle_identity: Identity,
    bundle: ObservationBundle,
    replay: ReplaySummary,
    raw: VerifiedFile,
    semantic: Value,
}

#[derive(Debug, Clone, Serialize)]
struct ReplaySummary {
    attempt_id: String,
    backend: ReplayBackend,
}

struct VerifiedFile {
    file: File,
    identity: Identity,
}

#[derive(Debug, Serialize)]
struct ComparisonReport<'a> {
    schema_version: u32,
    comparison_id: &'a str,
    request_sha256: &'a str,
    policy: &'a ComparisonPolicy,
    left: ReportSide<'a>,
    right: ReportSide<'a>,
    left_comparison_key: &'a ComparisonKey,
    right_comparison_key: &'a ComparisonKey,
    incompatible_key_fields: Vec<&'static str>,
    capture: CaptureReport,
    raw: RawReport,
    semantic: SemanticReport,
    verdict: &'static str,
    verdict_scope: &'static str,
}

#[derive(Debug, Serialize)]
struct ReportSide<'a> {
    bundle: &'a Identity,
    attempt_id: &'a str,
    backend: &'a ReplayBackend,
    unparsed_byte_count: u64,
}

#[derive(Debug, Serialize)]
struct CaptureReport {
    left: CaptureSide,
    right: CaptureSide,
}

#[derive(Debug, Serialize)]
struct CaptureSide {
    status: CaptureStatus,
    truncated: bool,
    dropped_records: u64,
    complete_for_comparison: bool,
}

#[derive(Debug, Serialize)]
struct RawReport {
    comparison_status: &'static str,
    identity_relation: &'static str,
    first_differing_offset: Option<u64>,
    left: Identity,
    right: Identity,
}

#[derive(Debug, Serialize)]
struct SemanticReport {
    comparison_status: &'static str,
    difference_count: u64,
    differences_truncated: bool,
    differences: Vec<SemanticDifference>,
    left: Identity,
    right: Identity,
}

#[derive(Debug, Serialize)]
struct SemanticDifference {
    pointer: String,
    kind: &'static str,
}

#[derive(Debug, Serialize)]
struct ComparisonManifest<'a> {
    schema_version: u32,
    comparison_id: &'a str,
    comparator: ManifestComparator<'a>,
    artifacts: ManifestArtifacts,
}

#[derive(Debug, Serialize)]
struct ManifestComparator<'a> {
    source_revision: &'a str,
    executable_sha256: &'a str,
}

#[derive(Debug, Serialize)]
struct ManifestArtifacts {
    request: PublishedArtifact,
    report: PublishedArtifact,
}

#[derive(Debug, Serialize)]
struct PublishedArtifact {
    file_name: &'static str,
    byte_count: usize,
    sha256: String,
}

pub fn compare_observations(
    request_path: &Path,
    left_bundle_path: &Path,
    right_bundle_path: &Path,
    output_dir: &Path,
) -> Result<(), String> {
    if output_dir.exists() {
        return Err(format!(
            "output directory already exists: {}",
            output_dir.display()
        ));
    }
    let request_bytes = read_bounded_regular(request_path, BUNDLE_MAX_BYTES, "comparison request")?;
    let mut request: ComparisonRequest = parse_strict(&request_bytes, "comparison request")?;
    validate_request(&mut request)?;
    let canonical_request = json_line(&request, "comparison request")?;
    let request_sha256 = digest(&canonical_request);

    let executable_sha256 = live_executable_sha256()?;
    if executable_sha256 != request.comparator.expected_executable_sha256 {
        return Err(format!(
            "comparator executable hash mismatch: expected {}, observed {}",
            request.comparator.expected_executable_sha256, executable_sha256
        ));
    }

    let mut left = load_observation(left_bundle_path, &request.left_bundle, "left")?;
    let mut right = load_observation(right_bundle_path, &request.right_bundle, "right")?;
    let incompatible_key_fields =
        key_mismatches(&left.bundle.comparison_key, &right.bundle.comparison_key);
    let capture_complete =
        capture_complete(&left.bundle.capture) && capture_complete(&right.bundle.capture);
    let (raw_equal, first_differing_offset) = compare_raw(&mut left.raw, &mut right.raw)?;

    let mut differences = Vec::new();
    let mut difference_count = 0;
    compare_values(
        &left.semantic,
        &right.semantic,
        "",
        &mut difference_count,
        &mut differences,
    );
    let semantic_equal = difference_count == 0;
    let (verdict, verdict_scope) = if !capture_complete {
        ("inconclusive", scope_for(request.policy.raw_mode))
    } else if !incompatible_key_fields.is_empty() {
        ("not-comparable", scope_for(request.policy.raw_mode))
    } else if !semantic_equal || (request.policy.raw_mode == RawMode::Exact && !raw_equal) {
        ("different", scope_for(request.policy.raw_mode))
    } else {
        ("equal", scope_for(request.policy.raw_mode))
    };

    let semantic_comparison_status = if incompatible_key_fields.is_empty() {
        "compared"
    } else {
        "not-comparable"
    };
    let report = ComparisonReport {
        schema_version: 1,
        comparison_id: &request.comparison_id,
        request_sha256: &request_sha256,
        policy: &request.policy,
        left: ReportSide {
            bundle: &left.bundle_identity,
            attempt_id: &left.replay.attempt_id,
            backend: &left.replay.backend,
            unparsed_byte_count: left.bundle.capture.unparsed_byte_count,
        },
        right: ReportSide {
            bundle: &right.bundle_identity,
            attempt_id: &right.replay.attempt_id,
            backend: &right.replay.backend,
            unparsed_byte_count: right.bundle.capture.unparsed_byte_count,
        },
        left_comparison_key: &left.bundle.comparison_key,
        right_comparison_key: &right.bundle.comparison_key,
        incompatible_key_fields,
        capture: CaptureReport {
            left: capture_side(&left.bundle.capture),
            right: capture_side(&right.bundle.capture),
        },
        raw: RawReport {
            comparison_status: if request.policy.raw_mode == RawMode::Exact {
                "compared"
            } else {
                "not-compared"
            },
            identity_relation: if raw_equal { "equal" } else { "different" },
            first_differing_offset,
            left: left.raw.identity.clone(),
            right: right.raw.identity.clone(),
        },
        semantic: SemanticReport {
            comparison_status: semantic_comparison_status,
            difference_count,
            differences_truncated: difference_count as usize > differences.len(),
            differences,
            left: semantic_identity(&left.bundle.capture.semantic),
            right: semantic_identity(&right.bundle.capture.semantic),
        },
        verdict,
        verdict_scope,
    };
    let report_bytes = json_line(&report, "comparison report")?;
    publish(
        output_dir,
        &request,
        &canonical_request,
        &report_bytes,
        &executable_sha256,
    )
}

pub fn live_executable_sha256() -> Result<String, String> {
    let mut file = File::open("/proc/self/exe")
        .map_err(|error| format!("open live comparator executable: {error}"))?;
    if !file
        .metadata()
        .map_err(|error| format!("stat live comparator executable: {error}"))?
        .file_type()
        .is_file()
    {
        return Err("live comparator executable is not a regular file".into());
    }
    Ok(hash_open_file(&mut file, "live comparator executable")?.sha256)
}

fn validate_request(request: &mut ComparisonRequest) -> Result<(), String> {
    if request.schema_version != 1 {
        return Err("comparison request schema_version must be 1".into());
    }
    safe_id(&request.comparison_id, "comparison_id")?;
    request.comparator.source_revision = canonical_hex(
        &request.comparator.source_revision,
        40,
        "comparator.source_revision",
    )?;
    request.comparator.expected_executable_sha256 = canonical_digest(
        &request.comparator.expected_executable_sha256,
        "comparator.expected_executable_sha256",
    )?;
    canonical_identity(&mut request.left_bundle, "left_bundle")?;
    canonical_identity(&mut request.right_bundle, "right_bundle")?;
    if request.policy.id != "exact-observation-v1" {
        return Err("policy.id must be exact-observation-v1".into());
    }
    if request.policy.semantic_mode != "exact-json" {
        return Err("policy.semantic_mode must be exact-json".into());
    }
    Ok(())
}

fn load_observation(
    path: &Path,
    expected: &Identity,
    side: &str,
) -> Result<LoadedObservation, String> {
    let bundle_bytes = read_bounded_regular(path, BUNDLE_MAX_BYTES, &format!("{side} bundle"))?;
    verify_bytes(&bundle_bytes, expected, &format!("{side} bundle"))?;
    let mut bundle: ObservationBundle = parse_strict(&bundle_bytes, &format!("{side} bundle"))?;
    validate_bundle(&mut bundle, side)?;
    let root = path.parent().unwrap_or_else(|| Path::new("."));

    let replay_bytes = read_verified_artifact(root, &bundle.replay_manifest, JSON_MAX_BYTES, side)?;
    let mut replay: ReplayManifest =
        parse_strict(&replay_bytes, &format!("{side} replay manifest"))?;
    validate_replay(&mut replay, &bundle, root, side)?;
    let mut raw = open_verified_artifact(root, &bundle.capture.raw, side)?;
    raw.file
        .seek(SeekFrom::Start(0))
        .map_err(|error| format!("rewind {side} raw artifact: {error}"))?;
    let semantic_bytes =
        read_verified_artifact(root, &bundle.capture.semantic, JSON_MAX_BYTES, side)?;
    let semantic: SemanticArtifact =
        parse_strict(&semantic_bytes, &format!("{side} semantic artifact"))?;
    validate_semantic(&semantic, &bundle, side)?;

    Ok(LoadedObservation {
        bundle_identity: expected.clone(),
        bundle,
        replay: ReplaySummary {
            attempt_id: replay.attempt_id,
            backend: replay.backend,
        },
        raw,
        semantic: semantic.state,
    })
}

fn validate_bundle(bundle: &mut ObservationBundle, side: &str) -> Result<(), String> {
    if bundle.schema_version != 1 {
        return Err(format!("{side} bundle schema_version must be 1"));
    }
    let key = &mut bundle.comparison_key;
    safe_id(&key.scenario_id, &format!("{side}.scenario_id"))?;
    safe_id(&key.profile_id, &format!("{side}.profile_id"))?;
    safe_id(
        &key.observation_schema.id,
        &format!("{side}.observation_schema.id"),
    )?;
    if key.observation_schema.version == 0 {
        return Err(format!(
            "{side} observation schema version must be positive"
        ));
    }
    for (name, value) in [
        ("scenario_sha256", &mut key.scenario_sha256),
        ("baseline_data_sha256", &mut key.baseline_data_sha256),
        ("fixture_sha256", &mut key.fixture_sha256),
        (
            "logical_command_stream_sha256",
            &mut key.logical_command_stream_sha256,
        ),
        ("rng_policy_sha256", &mut key.rng_policy_sha256),
        ("clock_policy_sha256", &mut key.clock_policy_sha256),
        (
            "observation_schema.sha256",
            &mut key.observation_schema.sha256,
        ),
        ("semantic_scope_sha256", &mut key.semantic_scope_sha256),
    ] {
        *value = canonical_digest(value, &format!("{side}.{name}"))?;
    }
    for (name, artifact) in [
        ("replay_manifest", &mut bundle.replay_manifest),
        ("capture.raw", &mut bundle.capture.raw),
        ("capture.semantic", &mut bundle.capture.semantic),
    ] {
        validate_artifact_ref(artifact, &format!("{side}.{name}"))?;
    }
    if bundle.capture.semantic.media_type != "application/json" {
        return Err(format!(
            "{side} semantic media_type must be application/json"
        ));
    }
    Ok(())
}

fn validate_replay(
    replay: &mut ReplayManifest,
    bundle: &ObservationBundle,
    root: &Path,
    side: &str,
) -> Result<(), String> {
    if replay.schema_version != 1
        || replay.execution.status != "succeeded"
        || replay.execution.reason != "completed-target"
        || replay.execution.exit_code != 0
        || replay.execution.stop_condition != replay.expected_stop_condition
        || replay.comparison_verdict != "not-run"
    {
        return Err(format!(
            "{side} replay manifest is not a successful uncompared schema-v1 attempt"
        ));
    }
    if replay.scenario_id != bundle.comparison_key.scenario_id
        || replay.profile_id != bundle.comparison_key.profile_id
    {
        return Err(format!(
            "{side} replay scenario/profile does not match observation bundle"
        ));
    }
    safe_id(&replay.attempt_id, &format!("{side}.replay.attempt_id"))?;
    safe_id(&replay.backend.kind, &format!("{side}.replay.backend.kind"))?;
    replay.request_sha256 = canonical_digest(
        &replay.request_sha256,
        &format!("{side}.replay.request_sha256"),
    )?;
    replay.command_stream_sha256 = canonical_digest(
        &replay.command_stream_sha256,
        &format!("{side}.replay.command_stream_sha256"),
    )?;
    replay.backend.executable_sha256 = canonical_digest(
        &replay.backend.executable_sha256,
        &format!("{side}.replay.backend.executable_sha256"),
    )?;
    replay.backend.source_revision = canonical_hex(
        &replay.backend.source_revision,
        40,
        &format!("{side}.replay.backend.source_revision"),
    )?;
    let _ = (
        &replay.input_identities,
        replay.command_count,
        &replay.expected_stop_condition,
        &replay.limits,
    );
    for (name, artifact) in [
        ("request", &replay.artifacts.request),
        ("stdout", &replay.artifacts.stdout),
        ("stderr", &replay.artifacts.stderr),
    ] {
        validate_replay_artifact(artifact, &format!("{side}.replay.artifacts.{name}"))?;
        let expected = Identity {
            byte_count: artifact.byte_count,
            sha256: artifact.sha256.to_ascii_lowercase(),
        };
        let bytes = read_named_regular(
            root,
            &artifact.file_name,
            JSON_MAX_BYTES,
            &format!("{side} replay {name}"),
        )?;
        verify_bytes(&bytes, &expected, &format!("{side} replay {name}"))?;
    }
    if replay.artifacts.request.sha256.to_ascii_lowercase() != replay.request_sha256 {
        return Err(format!("{side} replay request identities disagree"));
    }
    Ok(())
}

fn validate_semantic(
    semantic: &SemanticArtifact,
    bundle: &ObservationBundle,
    side: &str,
) -> Result<(), String> {
    if semantic.schema_version != 1
        || semantic.schema_id != bundle.comparison_key.observation_schema.id
        || semantic.scope_sha256.to_ascii_lowercase() != bundle.comparison_key.semantic_scope_sha256
    {
        return Err(format!(
            "{side} semantic artifact schema/scope does not match observation bundle"
        ));
    }
    if !semantic.state.is_object() {
        return Err(format!("{side} semantic state must be an object"));
    }
    validate_semantic_value(&semantic.state, 0, side)
}

fn validate_semantic_value(value: &Value, depth: usize, side: &str) -> Result<(), String> {
    if depth > MAX_JSON_DEPTH {
        return Err(format!(
            "{side} semantic JSON exceeds maximum depth {MAX_JSON_DEPTH}"
        ));
    }
    match value {
        Value::Number(number) if !number.is_i64() && !number.is_u64() => Err(format!(
            "{side} semantic JSON contains a non-integer number"
        )),
        Value::Array(values) => values
            .iter()
            .try_for_each(|value| validate_semantic_value(value, depth + 1, side)),
        Value::Object(values) => values
            .values()
            .try_for_each(|value| validate_semantic_value(value, depth + 1, side)),
        _ => Ok(()),
    }
}

fn compare_raw(
    left: &mut VerifiedFile,
    right: &mut VerifiedFile,
) -> Result<(bool, Option<u64>), String> {
    let mut offset = 0u64;
    let mut first_differing_offset = None;
    let mut left_hasher = Sha256::new();
    let mut right_hasher = Sha256::new();
    let mut left_byte_count = 0u64;
    let mut right_byte_count = 0u64;
    let mut left_buffer = [0u8; 64 * 1024];
    let mut right_buffer = [0u8; 64 * 1024];
    loop {
        let left_read = read_full_chunk(&mut left.file, &mut left_buffer, "left raw artifact")?;
        let right_read = read_full_chunk(&mut right.file, &mut right_buffer, "right raw artifact")?;
        left_hasher.update(&left_buffer[..left_read]);
        right_hasher.update(&right_buffer[..right_read]);
        left_byte_count += left_read as u64;
        right_byte_count += right_read as u64;
        if left_byte_count > left.identity.byte_count {
            return Err("left raw artifact grew while comparing".into());
        }
        if right_byte_count > right.identity.byte_count {
            return Err("right raw artifact grew while comparing".into());
        }
        let shared = left_read.min(right_read);
        if first_differing_offset.is_none() {
            if let Some(index) =
                (0..shared).find(|index| left_buffer[*index] != right_buffer[*index])
            {
                first_differing_offset = Some(offset + index as u64);
            } else if left_read != right_read {
                first_differing_offset = Some(offset + shared as u64);
            }
        }
        if left_read == 0 && right_read == 0 {
            break;
        }
        offset += shared as u64;
    }
    let left_observed = Identity {
        byte_count: left_byte_count,
        sha256: format!("{:x}", left_hasher.finalize()),
    };
    let right_observed = Identity {
        byte_count: right_byte_count,
        sha256: format!("{:x}", right_hasher.finalize()),
    };
    if left_observed.byte_count != left.identity.byte_count
        || left_observed.sha256 != left.identity.sha256
    {
        return Err("left raw artifact identity changed while comparing".into());
    }
    if right_observed.byte_count != right.identity.byte_count
        || right_observed.sha256 != right.identity.sha256
    {
        return Err("right raw artifact identity changed while comparing".into());
    }
    Ok((first_differing_offset.is_none(), first_differing_offset))
}

fn read_full_chunk(file: &mut File, buffer: &mut [u8], label: &str) -> Result<usize, String> {
    let mut filled = 0;
    while filled < buffer.len() {
        let read = file
            .read(&mut buffer[filled..])
            .map_err(|error| format!("read {label}: {error}"))?;
        if read == 0 {
            break;
        }
        filled += read;
    }
    Ok(filled)
}

fn compare_values(
    left: &Value,
    right: &Value,
    pointer: &str,
    count: &mut u64,
    samples: &mut Vec<SemanticDifference>,
) {
    match (left, right) {
        (Value::Object(left), Value::Object(right)) => {
            let keys: BTreeSet<_> = left.keys().chain(right.keys()).collect();
            for key in keys {
                let child = format!("{pointer}/{}", pointer_escape(key));
                match (left.get(key), right.get(key)) {
                    (Some(left), Some(right)) => {
                        compare_values(left, right, &child, count, samples)
                    }
                    (None, Some(_)) => add_difference(&child, "missing-left", count, samples),
                    (Some(_), None) => add_difference(&child, "missing-right", count, samples),
                    (None, None) => unreachable!(),
                }
            }
        }
        (Value::Array(left), Value::Array(right)) => {
            if left.len() != right.len() {
                add_difference(pointer, "array-length", count, samples);
            }
            for (index, (left, right)) in left.iter().zip(right.iter()).enumerate() {
                compare_values(left, right, &format!("{pointer}/{index}"), count, samples);
            }
        }
        _ if value_kind(left) != value_kind(right) => {
            add_difference(pointer, "type", count, samples)
        }
        _ if left != right => add_difference(pointer, "value", count, samples),
        _ => {}
    }
}

fn add_difference(
    pointer: &str,
    kind: &'static str,
    count: &mut u64,
    samples: &mut Vec<SemanticDifference>,
) {
    *count += 1;
    if samples.len() < MAX_DIFFERENCE_SAMPLES {
        samples.push(SemanticDifference {
            pointer: pointer.to_owned(),
            kind,
        });
    }
}

fn value_kind(value: &Value) -> u8 {
    match value {
        Value::Null => 0,
        Value::Bool(_) => 1,
        Value::Number(_) => 2,
        Value::String(_) => 3,
        Value::Array(_) => 4,
        Value::Object(_) => 5,
    }
}

fn pointer_escape(value: &str) -> String {
    value.replace('~', "~0").replace('/', "~1")
}

fn key_mismatches(left: &ComparisonKey, right: &ComparisonKey) -> Vec<&'static str> {
    let mut fields = Vec::new();
    if left.scenario_id != right.scenario_id {
        fields.push("scenario_id");
    }
    if left.profile_id != right.profile_id {
        fields.push("profile_id");
    }
    if left.scenario_sha256 != right.scenario_sha256 {
        fields.push("scenario_sha256");
    }
    if left.baseline_data_sha256 != right.baseline_data_sha256 {
        fields.push("baseline_data_sha256");
    }
    if left.fixture_sha256 != right.fixture_sha256 {
        fields.push("fixture_sha256");
    }
    if left.logical_command_stream_sha256 != right.logical_command_stream_sha256 {
        fields.push("logical_command_stream_sha256");
    }
    if left.rng_policy_sha256 != right.rng_policy_sha256 {
        fields.push("rng_policy_sha256");
    }
    if left.clock_policy_sha256 != right.clock_policy_sha256 {
        fields.push("clock_policy_sha256");
    }
    if left.observation_schema.id != right.observation_schema.id {
        fields.push("observation_schema.id");
    }
    if left.observation_schema.version != right.observation_schema.version {
        fields.push("observation_schema.version");
    }
    if left.observation_schema.sha256 != right.observation_schema.sha256 {
        fields.push("observation_schema.sha256");
    }
    if left.semantic_scope_sha256 != right.semantic_scope_sha256 {
        fields.push("semantic_scope_sha256");
    }
    fields
}

fn capture_complete(capture: &Capture) -> bool {
    capture.status == CaptureStatus::Complete && !capture.truncated && capture.dropped_records == 0
}

fn capture_side(capture: &Capture) -> CaptureSide {
    CaptureSide {
        status: capture.status,
        truncated: capture.truncated,
        dropped_records: capture.dropped_records,
        complete_for_comparison: capture_complete(capture),
    }
}

fn scope_for(mode: RawMode) -> &'static str {
    match mode {
        RawMode::Exact => "raw-and-semantic-exact",
        RawMode::RetainOnly => "semantic-exact",
    }
}

fn semantic_identity(artifact: &ArtifactRef) -> Identity {
    Identity {
        byte_count: artifact.byte_count,
        sha256: artifact.sha256.clone(),
    }
}

fn publish(
    output_dir: &Path,
    request: &ComparisonRequest,
    request_bytes: &[u8],
    report_bytes: &[u8],
    executable_sha256: &str,
) -> Result<(), String> {
    let parent = output_dir.parent().unwrap_or_else(|| Path::new("."));
    if !parent.is_dir() {
        return Err(format!(
            "output parent is not a directory: {}",
            parent.display()
        ));
    }
    let name = output_dir
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| "output directory must have a UTF-8 final component".to_owned())?;
    let staging = parent.join(format!(".{name}.tmp-{}", std::process::id()));
    if staging.exists() {
        return Err(format!(
            "staging directory already exists: {}",
            staging.display()
        ));
    }
    fs::DirBuilder::new()
        .mode(0o700)
        .create(&staging)
        .map_err(|error| format!("create staging directory: {error}"))?;
    let result = (|| {
        write_new(&staging.join("comparison-request.json"), request_bytes)?;
        write_new(&staging.join("comparison-report.json"), report_bytes)?;
        let manifest = ComparisonManifest {
            schema_version: 1,
            comparison_id: &request.comparison_id,
            comparator: ManifestComparator {
                source_revision: &request.comparator.source_revision,
                executable_sha256,
            },
            artifacts: ManifestArtifacts {
                request: PublishedArtifact {
                    file_name: "comparison-request.json",
                    byte_count: request_bytes.len(),
                    sha256: digest(request_bytes),
                },
                report: PublishedArtifact {
                    file_name: "comparison-report.json",
                    byte_count: report_bytes.len(),
                    sha256: digest(report_bytes),
                },
            },
        };
        let manifest_bytes = json_line(&manifest, "comparison manifest")?;
        write_new(&staging.join("comparison-manifest.json"), &manifest_bytes)?;
        rename_noreplace(&staging, output_dir)
            .map_err(|error| format!("publish output directory without replacement: {error}"))
    })();
    if result.is_err() {
        let _ = fs::remove_dir_all(&staging);
    }
    result
}

fn write_new(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(path)
        .map_err(|error| format!("create {}: {error}", path.display()))?;
    file.write_all(bytes)
        .map_err(|error| format!("write {}: {error}", path.display()))?;
    file.sync_all()
        .map_err(|error| format!("sync {}: {error}", path.display()))
}

fn rename_noreplace(source: &Path, destination: &Path) -> std::io::Result<()> {
    let source = CString::new(source.as_os_str().as_bytes()).map_err(|_| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "source path contains a NUL byte",
        )
    })?;
    let destination = CString::new(destination.as_os_str().as_bytes()).map_err(|_| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "destination path contains a NUL byte",
        )
    })?;
    // Linux renameat2 is the atomic primitive that guarantees an output created
    // after our early existence check is never replaced, including an empty dir.
    let result = unsafe {
        libc::syscall(
            libc::SYS_renameat2,
            libc::AT_FDCWD,
            source.as_ptr(),
            libc::AT_FDCWD,
            destination.as_ptr(),
            libc::RENAME_NOREPLACE,
        )
    };
    if result == 0 {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}

fn read_verified_artifact(
    root: &Path,
    artifact: &ArtifactRef,
    max: u64,
    side: &str,
) -> Result<Vec<u8>, String> {
    let bytes = read_named_regular(
        root,
        &artifact.file_name,
        max,
        &format!("{side} artifact {}", artifact.file_name),
    )?;
    verify_bytes(
        &bytes,
        &Identity {
            byte_count: artifact.byte_count,
            sha256: artifact.sha256.clone(),
        },
        &format!("{side} artifact {}", artifact.file_name),
    )?;
    Ok(bytes)
}

fn open_verified_artifact(
    root: &Path,
    artifact: &ArtifactRef,
    side: &str,
) -> Result<VerifiedFile, String> {
    let path = root.join(&artifact.file_name);
    let file = open_regular_no_follow(&path, &format!("{side} artifact {}", artifact.file_name))?;
    let expected = Identity {
        byte_count: artifact.byte_count,
        sha256: artifact.sha256.clone(),
    };
    let observed_size = file
        .metadata()
        .map_err(|error| format!("stat {side} artifact {}: {error}", artifact.file_name))?
        .len();
    if observed_size != expected.byte_count {
        return Err(format!(
            "{side} artifact {} identity mismatch",
            artifact.file_name
        ));
    }
    Ok(VerifiedFile {
        file,
        identity: expected,
    })
}

fn read_named_regular(
    root: &Path,
    file_name: &str,
    max: u64,
    label: &str,
) -> Result<Vec<u8>, String> {
    safe_file_name(file_name, label)?;
    let mut file = open_regular_no_follow(&root.join(file_name), label)?;
    read_bounded_open(&mut file, max, label)
}

fn read_bounded_regular(path: &Path, max: u64, label: &str) -> Result<Vec<u8>, String> {
    let mut file = open_regular_no_follow(path, label)?;
    read_bounded_open(&mut file, max, label)
}

fn read_bounded_open(file: &mut File, max: u64, label: &str) -> Result<Vec<u8>, String> {
    let size = file
        .metadata()
        .map_err(|error| format!("stat {label}: {error}"))?
        .len();
    if size > max {
        return Err(format!("{label} exceeds {max}-byte limit"));
    }
    let capacity = usize::try_from(size.min(max.saturating_add(1)))
        .map_err(|_| format!("{label} size cannot be represented on this host"))?;
    let mut bytes = Vec::with_capacity(capacity);
    file.take(max.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| format!("read {label}: {error}"))?;
    if bytes.len() as u64 > max {
        return Err(format!("{label} exceeds {max}-byte limit while reading"));
    }
    Ok(bytes)
}

fn open_regular_no_follow(path: &Path, label: &str) -> Result<File, String> {
    let file = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(path)
        .map_err(|error| format!("open {label}: {error}"))?;
    if !file
        .metadata()
        .map_err(|error| format!("stat {label}: {error}"))?
        .file_type()
        .is_file()
    {
        return Err(format!("{label} is not a regular file"));
    }
    Ok(file)
}

fn hash_open_file(file: &mut File, label: &str) -> Result<Identity, String> {
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    let mut byte_count = 0u64;
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|error| format!("read {label}: {error}"))?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
        byte_count += read as u64;
    }
    Ok(Identity {
        byte_count,
        sha256: format!("{:x}", hasher.finalize()),
    })
}

fn validate_artifact_ref(artifact: &mut ArtifactRef, label: &str) -> Result<(), String> {
    safe_file_name(&artifact.file_name, label)?;
    artifact.sha256 = canonical_digest(&artifact.sha256, &format!("{label}.sha256"))?;
    if artifact.media_type.is_empty()
        || artifact.media_type.len() > 128
        || !artifact.media_type.is_ascii()
    {
        return Err(format!("{label}.media_type is invalid"));
    }
    Ok(())
}

fn validate_replay_artifact(artifact: &ReplayArtifact, label: &str) -> Result<(), String> {
    safe_file_name(&artifact.file_name, label)?;
    canonical_digest(&artifact.sha256, &format!("{label}.sha256"))?;
    Ok(())
}

fn safe_file_name(value: &str, label: &str) -> Result<(), String> {
    let path = Path::new(value);
    if value.is_empty()
        || value.len() > 255
        || path.components().count() != 1
        || !matches!(path.components().next(), Some(Component::Normal(_)))
    {
        return Err(format!("{label} must use a safe basename"));
    }
    Ok(())
}

fn safe_id(value: &str, label: &str) -> Result<(), String> {
    if value.is_empty()
        || value.len() > 128
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.'))
    {
        return Err(format!(
            "{label} must contain 1-128 safe identifier characters"
        ));
    }
    Ok(())
}

fn canonical_identity(identity: &mut Identity, label: &str) -> Result<(), String> {
    identity.sha256 = canonical_digest(&identity.sha256, &format!("{label}.sha256"))?;
    Ok(())
}

fn canonical_digest(value: &str, label: &str) -> Result<String, String> {
    canonical_hex(value, 64, label)
}

fn canonical_hex(value: &str, length: usize, label: &str) -> Result<String, String> {
    if value.len() != length || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(format!("{label} must be {length} hexadecimal characters"));
    }
    Ok(value.to_ascii_lowercase())
}

fn verify_bytes(bytes: &[u8], expected: &Identity, label: &str) -> Result<(), String> {
    let observed = Identity {
        byte_count: bytes.len() as u64,
        sha256: digest(bytes),
    };
    if observed.byte_count != expected.byte_count || observed.sha256 != expected.sha256 {
        return Err(format!("{label} identity mismatch"));
    }
    Ok(())
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn json_line<T: Serialize>(value: &T, label: &str) -> Result<Vec<u8>, String> {
    let mut bytes =
        serde_json::to_vec(value).map_err(|error| format!("serialize {label}: {error}"))?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn parse_strict<T: for<'de> Deserialize<'de>>(bytes: &[u8], label: &str) -> Result<T, String> {
    let mut deserializer = serde_json::Deserializer::from_slice(bytes);
    let value = NoDuplicates
        .deserialize(&mut deserializer)
        .map_err(|error| format!("parse {label}: {error}"))?;
    deserializer
        .end()
        .map_err(|error| format!("parse {label}: {error}"))?;
    serde_json::from_value(value).map_err(|error| format!("parse {label}: {error}"))
}

struct NoDuplicates;

impl<'de> DeserializeSeed<'de> for NoDuplicates {
    type Value = Value;
    fn deserialize<D: Deserializer<'de>>(self, deserializer: D) -> Result<Self::Value, D::Error> {
        deserializer.deserialize_any(NoDuplicateVisitor)
    }
}

struct NoDuplicateVisitor;

impl<'de> Visitor<'de> for NoDuplicateVisitor {
    type Value = Value;
    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a JSON value without duplicate object keys")
    }
    fn visit_bool<E: de::Error>(self, value: bool) -> Result<Value, E> {
        Ok(Value::Bool(value))
    }
    fn visit_i64<E: de::Error>(self, value: i64) -> Result<Value, E> {
        Ok(Value::Number(value.into()))
    }
    fn visit_u64<E: de::Error>(self, value: u64) -> Result<Value, E> {
        Ok(Value::Number(value.into()))
    }
    fn visit_f64<E: de::Error>(self, value: f64) -> Result<Value, E> {
        serde_json::Number::from_f64(value)
            .map(Value::Number)
            .ok_or_else(|| E::custom("non-finite number"))
    }
    fn visit_str<E: de::Error>(self, value: &str) -> Result<Value, E> {
        Ok(Value::String(value.to_owned()))
    }
    fn visit_string<E: de::Error>(self, value: String) -> Result<Value, E> {
        Ok(Value::String(value))
    }
    fn visit_none<E: de::Error>(self) -> Result<Value, E> {
        Ok(Value::Null)
    }
    fn visit_unit<E: de::Error>(self) -> Result<Value, E> {
        Ok(Value::Null)
    }
    fn visit_some<D: Deserializer<'de>>(self, deserializer: D) -> Result<Value, D::Error> {
        NoDuplicates.deserialize(deserializer)
    }
    fn visit_seq<A: SeqAccess<'de>>(self, mut sequence: A) -> Result<Value, A::Error> {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element_seed(NoDuplicates)? {
            values.push(value);
        }
        Ok(Value::Array(values))
    }
    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Value, A::Error> {
        let mut values = serde_json::Map::new();
        while let Some(key) = map.next_key::<String>()? {
            if values.contains_key(&key) {
                return Err(de::Error::custom(format!("duplicate object key `{key}`")));
            }
            let value = map.next_value_seed(NoDuplicates)?;
            values.insert(key, value);
        }
        Ok(Value::Object(values))
    }
}

#[cfg(test)]
mod tests {
    use super::rename_noreplace;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn no_replace_publication_preserves_a_concurrent_destination() {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock")
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "lab-comparator-rename-{}-{nonce}",
            std::process::id()
        ));
        let source = root.join("source");
        let destination = root.join("destination");
        fs::create_dir(&root).expect("create test root");
        fs::create_dir(&source).expect("create source");
        fs::write(source.join("evidence"), b"source").expect("write source evidence");
        fs::create_dir(&destination).expect("create concurrent destination");

        let error = rename_noreplace(&source, &destination).expect_err("must not replace");
        assert_eq!(error.kind(), std::io::ErrorKind::AlreadyExists);
        assert!(source.join("evidence").is_file());
        assert!(destination.is_dir());

        fs::remove_dir_all(&root).expect("remove test root");
    }
}
