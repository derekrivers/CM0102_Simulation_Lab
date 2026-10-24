#!/usr/bin/env python3
"""Verify the authority-free synthetic controller runtime contract."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import tempfile


PROFILE_PATH = "config/synthetic-launcher-controller-runtime-v1.json"
PROFILE_SCHEMA_PATH = "config/synthetic-launcher-controller-runtime-v1.schema.json"
REPORT_SCHEMA_PATH = "config/synthetic-launcher-controller-report-v1.schema.json"
POLICY_PROFILE_PATH = "config/synthetic-launcher-controller-policy-v1.json"
POLICY_PRIVATE_SCHEMA_PATH = "config/synthetic-launcher-controller-private-v1.schema.json"
FIXTURE_PATH = "tools/windows/synthetic-launcher-qualification/SyntheticFixture.cs"
ARCHITECTURE_PATH = "docs/architecture/SYNTHETIC_LAUNCHER_QUALIFICATION_V1.md"
RUNTIME_README_PATH = "tools/windows/synthetic-launcher-controller/RUNTIME_CONTRACT.md"
VERIFIER_PATH = "tools/windows/synthetic-launcher-controller/verify_controller_runtime_contract.py"
BOUND_PATHS = (
    PROFILE_PATH, PROFILE_SCHEMA_PATH, REPORT_SCHEMA_PATH, POLICY_PROFILE_PATH,
    POLICY_PRIVATE_SCHEMA_PATH, FIXTURE_PATH, ARCHITECTURE_PATH, RUNTIME_README_PATH,
    VERIFIER_PATH,
)
MAX_BYTES = 512 * 1024
GIT = pathlib.Path("/usr/bin/git")

EXPECTED_INPUTS = {
    "accepted_host_artifact": {
        "byte_count": 3310,
        "sha256": "96e38bb7932e1acb64aa7c9a33012f3425318b3a8e3aaf7ce98aaf8e1cd27659",
    },
    "controller_policy_private_schema": {
        "byte_count": 2881,
        "sha256": "f8b1ae19840c9bbb9dbc9ab32d8872e4b44f5091a9a5440ae851a78daed7a279",
    },
    "controller_policy_profile": {
        "byte_count": 3002,
        "sha256": "0c6d36a80786ff123e428ee5f0f0493306067b50bbf387c011864100d3fcd6c4",
    },
    "ui_fixture": {
        "byte_count": 14336,
        "sha256": "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6",
    },
}
EXPECTED_NAMES = {
    "controller": "SyntheticLauncherController.exe",
    "locked_preflight": "SyntheticLauncherLockedPreflight.exe",
    "private_configuration": "SyntheticLauncherController.private.v1.json",
    "public_runtime_configuration": "SyntheticLauncherController.public.v1.json",
    "report": "SyntheticLauncherReport.v1.json",
    "supervisor": "SyntheticLauncherSupervisor.exe",
    "timeout_child": "SyntheticLauncherTimeoutChild.exe",
    "timeout_root": "SyntheticLauncherTimeoutFixture.exe",
    "ui_fixture": "SyntheticLauncherFixture.exe",
}
EXPECTED_REPORT_DIFFERENCES = [
    "/bindings/attempt_root_object_id_sha256",
    "/bindings/private_configuration/byte_count",
    "/bindings/private_configuration/sha256",
    "/observations/environment/nonce_sha256",
    "/run/attempt_id_sha256",
    "/run/attempt_ordinal",
    "/run/elapsed_ms",
    "/run/observed_at_utc",
]
EXPECTED_MANIFEST_DIFFERENCES = [
    "/artifacts/report/byte_count",
    "/artifacts/report/sha256",
    "/inputs/private_configuration/byte_count",
    "/inputs/private_configuration/sha256",
    "/run/elapsed_ms",
    "/run/observed_at_utc",
]
EXPECTED_CHECKS = [
    "binding-exact", "capture-complete-exact", "capture-ready-exact",
    "cleanup-exact", "environment-exact", "guard-stability", "input-exact",
    "job-containment", "original-not-run", "preflight-safe", "privacy-safe",
    "registry-denied", "resume-once", "supervisor-containment",
    "token-relationship", "window-exact",
]
EXPECTED_ERRORS = [
    "access-denied", "api-failure", "binding-failure", "cleanup-failure",
    "configuration-failure", "interference", "privacy-rejection", "timeout",
    "unexpected-result",
]
EXPECTED_API_ROLES = {
    "controller": ["capture-client-bitblt", "create-fixed-fixture-as-user",
        "environment-block-build", "filesystem-bind-read", "guard-tree-read",
        "input-sendinput", "job-inner", "registry-denial-read",
        "report-canonical-write", "session-desktop-read",
        "token-observe-duplicate-adjust", "window-observe"],
    "locked_preflight": ["filesystem-bind-read", "guard-process-read",
        "report-canonical-write", "session-desktop-read"],
    "supervisor": ["create-fixed-worker-suspended", "filesystem-bind-read",
        "job-outer", "report-relay", "worker-wait-terminate"],
    "timeout_child": ["wait-only"],
    "timeout_root": ["create-fixed-timeout-child", "filesystem-bind-read", "wait-only"],
    "ui_fixture": ["fixture-accepted-ui-only"],
}
EXPECTED_OUTER_JOB = {
    "active_process_limit_by_scenario": {"locked-refusal-v1": 1,
        "tree-timeout-v1": 3, "ui-success-v1": 2},
    "assign_worker_before_resume": True, "breakaway_forbidden": True,
    "job_memory_limit_bytes_by_scenario": {"locked-refusal-v1": 268435456,
        "tree-timeout-v1": 805306368, "ui-success-v1": 536870912},
    "kill_on_close": True,
    "nested_inner_job_required_for": ["tree-timeout-v1", "ui-success-v1"],
    "non_inheritable_handle": True, "process_memory_limit_bytes": 268435456,
    "supervisor_is_member": False, "unnamed": True, "worker_created_suspended": True,
    "worker_membership_queried": True, "worker_resume_call_count": 1,
}
EXPECTED_OMITTED_VALUES = [
    "attempt-root-file-id", "attempt-root-path", "hwnd", "nonce", "pid", "sid",
    "token-handle",
]
EXPECTED_EQUALITIES = [
    "approved-bmp-bytes", "bindings-except-permitted-paths", "check-map",
    "scenario-id", "source-revision", "summary", "worker-image-bytes",
]
EXPECTED_FORBIDDEN_STRINGS = [
    "command-line", "environment-value", "exception-message", "exception-type",
    "hostname", "hwnd", "path", "pid", "registry-location", "sid",
    "stack-trace", "username", "window-title",
]
EXPECTED_REPORT_CONTRACT = {
    "allowed_report_kinds": ["minimal"], "canonical_json": True, "eligible_reports": False,
    "encoding": "utf-8-ascii-subset-no-bom",
    "forbidden_string_classes": EXPECTED_FORBIDDEN_STRINGS,
    "full_report_required_check_ids": EXPECTED_CHECKS, "line_ending": "lf",
    "max_bytes": 262144, "minimal_error_category_ids": EXPECTED_ERRORS,
    "original_behavior_qualified": False, "original_execution_status": "not-run",
    "schema_id": "cm0102-synthetic-launcher-controller-report-v1",
}

# The executing verifier is bound to its exact Git blob instead of this map to
# avoid a self-hash cycle.
FROZEN_IDENTITIES: dict[str, tuple[int, str]] = {
    PROFILE_PATH: (5510, "0f4e98d7fe1c273e3c0b7cf342bae84bcc99a4a5ef16cf087a4fe99d3bb396d1"),
    PROFILE_SCHEMA_PATH: (5593, "e2816005c4e1e3c62862bae431723cfc9f2a3431cf82e674c55c319104344218"),
    REPORT_SCHEMA_PATH: (20438, "12eaae8d677abed0fd0b5418069cd5445d9b13378f7e2cd56521ab63094a8161"),
    POLICY_PROFILE_PATH: (3002, "0c6d36a80786ff123e428ee5f0f0493306067b50bbf387c011864100d3fcd6c4"),
    POLICY_PRIVATE_SCHEMA_PATH: (2881, "f8b1ae19840c9bbb9dbc9ab32d8872e4b44f5091a9a5440ae851a78daed7a279"),
    FIXTURE_PATH: (20355, "d730bda0acc2cf89ab6e212f49620a2e42b00392a3976f1467c0931bce66ae1c"),
    ARCHITECTURE_PATH: (23840, "aaddf101ade96bf1ad2256e0ba92a3ee18dc12429b819480a67ce6967b3ddd66"),
    RUNTIME_README_PATH: (2282, "4842e90637262c407425d115e25d4047e7f9a663b2c50ec7a1317f328c8eccf3"),
}


class VerificationError(Exception):
    pass


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
        separators=(",", ":")) + "\n").encode("ascii")


def identity(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def json_equal(left: object, right: object) -> bool:
    try:
        return canonical(left) == canonical(right)
    except (TypeError, ValueError):
        return False


def duplicate_guard(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError("duplicate JSON key")
        result[key] = value
    return result


def parse_canonical(raw: bytes, label: str) -> object:
    try:
        value = json.loads(raw.decode("ascii", "strict"), object_pairs_hook=duplicate_guard,
            parse_float=lambda _value: (_ for _ in ()).throw(VerificationError("float JSON value")),
            parse_constant=lambda _value: (_ for _ in ()).throw(VerificationError("non-finite JSON value")))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(label + " JSON") from error
    if canonical(value) != raw:
        raise VerificationError(label + " is not canonical")
    return value


def require_path_components(path: pathlib.Path) -> None:
    if not path.is_absolute():
        raise VerificationError("path is not absolute")
    current = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if stat.S_ISLNK(os.lstat(current).st_mode):
            raise VerificationError("symlink path component")


def read_bound(path: pathlib.Path) -> bytes:
    require_path_components(path)
    before = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
        raise VerificationError("input is not a bounded single-link regular file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
    try:
        opened = os.fstat(descriptor)
        raw = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, MAX_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                raise VerificationError("input exceeds byte limit")
        after = os.stat(path, follow_symlinks=False)
    finally:
        os.close(descriptor)
    def stable(value: os.stat_result) -> tuple[int, ...]:
        return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if stable(before) != stable(opened) or stable(before) != stable(after) or len(raw) != before.st_size:
        raise VerificationError("input changed during read")
    return bytes(raw)


def git_environment() -> dict[str, str]:
    return {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1", "LANG": "C", "LC_ALL": "C"}


def run_git(repo: pathlib.Path, arguments: list[str]) -> bytes:
    completed = subprocess.run(
        [os.fspath(GIT), "--no-replace-objects", "-c", "core.hooksPath=/dev/null",
         "-C", os.fspath(repo), *arguments], cwd="/", env=git_environment(),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=10, check=False)
    if completed.returncode != 0 or completed.stderr:
        raise VerificationError("Git binding failed")
    return completed.stdout


def validate_commit(repo: pathlib.Path, commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise VerificationError("source commit is not a full lowercase hash")
    if run_git(repo, ["cat-file", "-t", commit]) != b"commit\n":
        raise VerificationError("source object is not a commit")
    resolved = run_git(repo, ["rev-parse", "--verify", commit + "^{commit}"]).decode().strip()
    head = run_git(repo, ["rev-parse", "--verify", "HEAD^{commit}"]).decode().strip()
    if resolved != commit or head != commit:
        raise VerificationError("source commit is not exact HEAD")


def resolve_pointer(root: dict[str, object], pointer: str) -> object:
    if not pointer.startswith("#/"):
        raise VerificationError("unsupported schema reference")
    value: object = root
    for part in pointer[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or part not in value:
            raise VerificationError("unresolved schema reference")
        value = value[part]
    return value


def schema_accepts(schema: object, value: object, root: dict[str, object]) -> bool:
    if not isinstance(schema, dict):
        return False
    if "$ref" in schema and not schema_accepts(resolve_pointer(root, schema["$ref"]), value, root):
        return False
    if "const" in schema and not json_equal(value, schema["const"]):
        return False
    if "enum" in schema and not any(json_equal(value, item) for item in schema["enum"]):
        return False
    if "type" in schema:
        kind = schema["type"]
        matches = {
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
        }.get(kind, False)
        if not matches:
            return False
    if isinstance(value, dict):
        required = schema.get("required", [])
        if not isinstance(required, list) or any(key not in value for key in required):
            return False
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return False
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            return False
        if any(key in properties and not schema_accepts(properties[key], item, root)
               for key, item in value.items()):
            return False
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            return False
        if "items" in schema and any(not schema_accepts(schema["items"], item, root) for item in value):
            return False
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            return False
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            return False
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            return False
        if schema.get("format") == "date-time":
            try:
                datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                return False
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            return False
        if "maximum" in schema and value > schema["maximum"]:
            return False
    if "allOf" in schema and not all(schema_accepts(item, value, root) for item in schema["allOf"]):
        return False
    if "anyOf" in schema and not any(schema_accepts(item, value, root) for item in schema["anyOf"]):
        return False
    if "oneOf" in schema and sum(schema_accepts(item, value, root) for item in schema["oneOf"]) != 1:
        return False
    if "not" in schema and schema_accepts(schema["not"], value, root):
        return False
    if "if" in schema and schema_accepts(schema["if"], value, root):
        if "then" in schema and not schema_accepts(schema["then"], value, root):
            return False
    return True


def verify_profile(profile: object, schema: object, report_schema: object) -> None:
    if not isinstance(profile, dict) or not isinstance(schema, dict) or not isinstance(report_schema, dict):
        raise VerificationError("contract root shape")
    if not json_equal(schema, {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "const": profile, "type": "object"}):
        raise VerificationError("runtime schema is not the exact profile schema")
    if not json_equal(profile.get("schema_version"), 1) or \
            profile.get("profile_id") != "cm0102-synthetic-launcher-controller-runtime-v1":
        raise VerificationError("runtime profile identity")
    if not json_equal(profile.get("accepted_inputs"), EXPECTED_INPUTS) or \
            not json_equal(profile.get("fixed_names"), EXPECTED_NAMES):
        raise VerificationError("runtime fixed inputs or names")
    state = profile.get("contract_state")
    if not json_equal(state, {"build_binding": "build-unpinned", "live_execution_status": "not-run",
                 "original_behavior_qualified": False, "original_execution_status": "not-run",
                 "process_creation_reachable": False, "qualification_eligible": False}):
        raise VerificationError("runtime must fail closed before build binding")
    status = profile.get("status", {})
    if status.get("ui_fixture_image") != "bound-not-run" or status.get("runtime_private_schema") != "absent" or \
            any(status.get(key) != "unbound" for key in ("controller_image", "locked_preflight_image",
                "supervisor_image", "timeout_child_image", "timeout_root_image")) or \
            status.get("retained_run_harness") != "absent" or \
            status.get("runtime_implementation_verifier") != "absent":
        raise VerificationError("runtime image status")
    scenarios = profile.get("scenario_images")
    expected_scenarios = {
        "locked-refusal-v1": {"descendant": "absent", "expected_fixture_execution_status": "not-run",
            "primary_target": "absent", "worker": "locked_preflight", "worker_process_creation_capability": False},
        "tree-timeout-v1": {"descendant": "timeout_child", "expected_fixture_execution_status": "expected-timeout-contained",
            "primary_target": "timeout_root", "worker": "controller", "worker_process_creation_capability": True},
        "ui-success-v1": {"descendant": "absent", "expected_fixture_execution_status": "succeeded",
            "primary_target": "ui_fixture", "worker": "controller", "worker_process_creation_capability": True},
    }
    if not json_equal(scenarios, expected_scenarios):
        raise VerificationError("scenario image map")
    comparison = profile.get("cross_attempt_comparison", {})
    if comparison.get("algorithm") != "remove-exact-json-pointers-then-canonical-sha256-v1" or \
            not json_equal(comparison.get("omitted_private_value_ids"), EXPECTED_OMITTED_VALUES) or \
            not json_equal(comparison.get("report_permitted_difference_paths"), EXPECTED_REPORT_DIFFERENCES) or \
            not json_equal(comparison.get("retained_manifest_permitted_difference_paths"), EXPECTED_MANIFEST_DIFFERENCES) or \
            not json_equal(comparison.get("private_configuration_permitted_difference_paths"), ["/guard_paths/attempt_root"]) or \
            not json_equal(comparison.get("required_equalities"), EXPECTED_EQUALITIES):
        raise VerificationError("cross-attempt difference projection")
    report_contract = profile.get("report_contract", {})
    if not json_equal(report_contract, EXPECTED_REPORT_CONTRACT):
        raise VerificationError("report contract")
    if not json_equal(profile.get("api_roles"), EXPECTED_API_ROLES) or \
            not json_equal(profile.get("outer_job"), EXPECTED_OUTER_JOB):
        raise VerificationError("runtime authority or outer Job contract")
    definitions = report_schema.get("$defs", {})
    if report_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or \
            not json_equal(report_schema.get("oneOf"), [{"$ref": "#/$defs/minimal_report"}]) or \
            set(definitions) != {"bindings", "check_status", "checks", "error", "full_report", "identity",
                "identity_or_absent", "minimal_report", "observations", "run", "sha256", "summary", "utc"}:
        raise VerificationError("report schema definitions")
    checks = definitions["checks"]
    if not json_equal(checks.get("required"), EXPECTED_CHECKS) or \
            list(checks.get("properties", {})) != EXPECTED_CHECKS:
        raise VerificationError("report check map")
    if definitions["error"]["properties"]["category_id"].get("enum") != EXPECTED_ERRORS:
        raise VerificationError("report error categories")
    if definitions["full_report"].get("additionalProperties") is not False or \
            definitions["minimal_report"].get("additionalProperties") is not False or \
            len(definitions["full_report"].get("allOf", [])) != 3 or \
            len(definitions["minimal_report"].get("allOf", [])) != 3:
        raise VerificationError("report scenario closure")
    summary_guard = definitions["summary"].get("allOf")
    expected_guard = [{"properties": {"qualification_eligible": {"const": False},
        "safety_verdict": {"enum": ["inconclusive", "unsafe"]}},
        "required": ["qualification_eligible", "safety_verdict"]}]
    if not json_equal(summary_guard, expected_guard):
        raise VerificationError("build-unpinned report eligibility guard")


def minimal_report() -> dict[str, object]:
    scenario = "ui-success-v1"
    return {
        "error": {"category_id": "configuration-failure", "stage_id": "bind-inputs"},
        "profile_id": "cm0102-synthetic-launcher-controller-runtime-v1",
        "report_kind": "minimal",
        "run": {"attempt_id_sha256": "1" * 64, "attempt_ordinal": 1, "elapsed_ms": 0,
                "observed_at_utc": "2026-10-24T00:00:00Z", "source_revision": "2" * 40},
        "scenario_id": scenario,
        "schema_version": 1,
        "summary": {"comparison_verdict": "not-run", "completeness": "incomplete",
            "fixture_execution_status": "unknown", "original_behavior_qualified": False,
            "original_execution_status": "not-run", "qualification_eligible": False,
            "safety_verdict": "inconclusive", "scenario_id": scenario},
    }


def verify_report_schema(schema: dict[str, object]) -> None:
    value = minimal_report()
    if not schema_accepts(schema, value, schema):
        raise VerificationError("report schema rejects canonical minimal report")
    mutations = []
    changed = json.loads(json.dumps(value)); changed["extra"] = True; mutations.append(changed)
    changed = json.loads(json.dumps(value)); changed["summary"]["original_execution_status"] = "succeeded"; mutations.append(changed)
    changed = json.loads(json.dumps(value)); changed["summary"]["qualification_eligible"] = True; mutations.append(changed)
    changed = json.loads(json.dumps(value)); changed["summary"]["scenario_id"] = "locked-refusal-v1"; mutations.append(changed)
    changed = json.loads(json.dumps(value)); changed["error"]["category_id"] = "exception-text"; mutations.append(changed)
    changed = json.loads(json.dumps(value)); changed["run"]["source_revision"] = "A" * 40; mutations.append(changed)
    changed = json.loads(json.dumps(value)); changed["run"]["attempt_id_sha256"] = "0" * 64; mutations.append(changed)
    for mutation in mutations:
        if schema_accepts(schema, mutation, schema):
            raise VerificationError("report schema accepted negative mutation")


def verify(repo_argument: pathlib.Path, commit: str) -> dict[str, dict[str, object]]:
    if not GIT.is_file():
        raise VerificationError("absolute Git unavailable")
    if not repo_argument.is_absolute() or repo_argument.resolve(strict=True) != repo_argument:
        raise VerificationError("repository path is not canonical absolute")
    repo = repo_argument
    require_path_components(repo)
    if pathlib.Path(run_git(repo, ["rev-parse", "--show-toplevel"]).decode().strip()) != repo:
        raise VerificationError("repository is not canonical top level")
    if pathlib.Path(__file__).absolute() != repo / VERIFIER_PATH:
        raise VerificationError("verifier is not executing from canonical path")
    validate_commit(repo, commit)
    captured: dict[str, bytes] = {}
    result: dict[str, dict[str, object]] = {}
    for relative in BOUND_PATHS:
        raw = read_bound(repo / relative)
        frozen = FROZEN_IDENTITIES.get(relative)
        if frozen is not None and (len(raw), hashlib.sha256(raw).hexdigest()) != frozen:
            raise VerificationError(relative + " frozen identity")
        if raw != run_git(repo, ["show", commit + ":" + relative]):
            raise VerificationError(relative + " differs from source commit")
        captured[relative] = raw
        result[relative] = identity(raw)
    if identity(captured[POLICY_PROFILE_PATH]) != EXPECTED_INPUTS["controller_policy_profile"] or \
            identity(captured[POLICY_PRIVATE_SCHEMA_PATH]) != EXPECTED_INPUTS["controller_policy_private_schema"] or \
            identity(captured[FIXTURE_PATH]) != {"byte_count": 20355,
                "sha256": "d730bda0acc2cf89ab6e212f49620a2e42b00392a3976f1467c0931bce66ae1c"}:
        raise VerificationError("accepted source identity drift")
    profile = parse_canonical(captured[PROFILE_PATH], "runtime profile")
    profile_schema = parse_canonical(captured[PROFILE_SCHEMA_PATH], "runtime schema")
    report_schema = parse_canonical(captured[REPORT_SCHEMA_PATH], "report schema")
    verify_profile(profile, profile_schema, report_schema)
    verify_report_schema(report_schema)
    architecture = captured[ARCHITECTURE_PATH].decode("utf-8", "strict")
    readme = captured[RUNTIME_README_PATH].decode("utf-8", "strict")
    for required in ("build-unpinned", "SyntheticLauncherLockedPreflight.exe",
                     "SyntheticLauncherTimeoutFixture.exe", "SyntheticLauncherSupervisor.exe",
                     "worker-evidence document", "supervisor validates it",
                     "proves the inner Job empty", "sole output artifact"):
        if required not in architecture or required not in readme + architecture:
            raise VerificationError("missing documented contract literal")
    if "game remains never launched" not in architecture:
        raise VerificationError("missing original-execution boundary")
    for relative, original in captured.items():
        if read_bound(repo / relative) != original:
            raise VerificationError(relative + " changed across aggregate verification")
    validate_commit(repo, commit)
    return result


def self_test() -> None:
    root = pathlib.Path(__file__).parents[3]
    profile = parse_canonical((root / PROFILE_PATH).read_bytes(), "runtime profile")
    profile_schema = parse_canonical((root / PROFILE_SCHEMA_PATH).read_bytes(), "runtime schema")
    report_path = pathlib.Path(__file__).parents[3] / REPORT_SCHEMA_PATH
    schema = parse_canonical(report_path.read_bytes(), "report schema")
    if not isinstance(profile, dict) or not isinstance(profile_schema, dict) or not isinstance(schema, dict):
        raise AssertionError("contract schema root")
    verify_profile(profile, profile_schema, schema)
    weakened_profiles = []
    changed = json.loads(json.dumps(profile)); changed["api_roles"]["locked_preflight"].append("shell-exec"); weakened_profiles.append(changed)
    changed = json.loads(json.dumps(profile)); changed["outer_job"]["kill_on_close"] = False; weakened_profiles.append(changed)
    changed = json.loads(json.dumps(profile)); changed["cross_attempt_comparison"]["required_equalities"] = []; weakened_profiles.append(changed)
    changed = json.loads(json.dumps(profile)); changed["report_contract"]["forbidden_string_classes"] = []; weakened_profiles.append(changed)
    changed = json.loads(json.dumps(profile)); changed["schema_version"] = True; weakened_profiles.append(changed)
    changed = json.loads(json.dumps(profile)); changed["contract_state"]["qualification_eligible"] = 0; weakened_profiles.append(changed)
    for changed in weakened_profiles:
        changed_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                          "const": changed, "type": "object"}
        try:
            verify_profile(changed, changed_schema, schema)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted weakened runtime profile")
    weakened_schema = json.loads(json.dumps(schema))
    weakened_schema["$defs"]["full_report"]["additionalProperties"] = True
    try:
        verify_profile(profile, profile_schema, weakened_schema)
    except VerificationError:
        pass
    else:
        raise AssertionError("accepted widened report schema")
    verify_report_schema(schema)
    boolean_version = minimal_report()
    boolean_version["schema_version"] = True
    if schema_accepts(schema, boolean_version, schema):
        raise AssertionError("accepted boolean as integer")
    numeric_boolean = minimal_report()
    numeric_boolean["summary"]["original_behavior_qualified"] = 0
    if schema_accepts(schema, numeric_boolean, schema):
        raise AssertionError("accepted integer as boolean")
    invalid_date = minimal_report()
    invalid_date["run"]["observed_at_utc"] = "2026-02-31T00:00:00Z"
    if schema_accepts(schema, invalid_date, schema):
        raise AssertionError("accepted impossible calendar date")
    for scenario, impossible_stage in (("locked-refusal-v1", "send-input"),
                                        ("tree-timeout-v1", "complete-capture-two")):
        impossible = minimal_report()
        impossible["scenario_id"] = scenario
        impossible["summary"]["scenario_id"] = scenario
        impossible["error"]["stage_id"] = impossible_stage
        if schema_accepts(schema, impossible, schema):
            raise AssertionError("accepted impossible scenario stage")
    eligible = {
        "comparison_verdict": "not-run", "completeness": "complete",
        "fixture_execution_status": "succeeded", "original_behavior_qualified": False,
        "original_execution_status": "not-run", "qualification_eligible": True,
        "safety_verdict": "synthetic-launcher-qualified", "scenario_id": "ui-success-v1",
    }
    if schema_accepts(schema["$defs"]["summary"], eligible, schema):
        raise AssertionError("build-unpinned schema accepted eligible summary")
    for raw in (b'{"a":1,"a":2}\n', b'{"a":1.0}\n', b'{"a":NaN}\n', b'{ "a":1}\n'):
        try:
            parse_canonical(raw, "mutation")
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted malformed canonical JSON")
    with tempfile.TemporaryDirectory() as directory:
        copied = pathlib.Path(directory) / pathlib.Path(__file__).name
        copied.write_bytes(pathlib.Path(__file__).read_bytes())
        completed = subprocess.run(["/usr/bin/python3", os.fspath(copied), "self-test"], cwd=directory,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, check=False)
        if completed.returncode == 0:
            raise AssertionError("copied verifier executed successfully")


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("self-test")
    check = modes.add_parser("verify")
    check.add_argument("--repo", required=True, type=pathlib.Path)
    check.add_argument("--source-commit", required=True)
    arguments = parser.parse_args()
    try:
        result = None if arguments.mode == "self-test" else verify(arguments.repo, arguments.source_commit)
        if arguments.mode == "self-test":
            self_test()
    except (VerificationError, AssertionError, OSError, subprocess.SubprocessError) as error:
        print("FAIL " + str(error))
        return 1
    if result is None:
        print("PASS controller-runtime-contract-self-test")
    else:
        print(json.dumps({"files": result, "status": "controller-runtime-contract-verified"},
            sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
