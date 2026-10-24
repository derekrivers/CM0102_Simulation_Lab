#!/usr/bin/env python3
"""Strict verifier for the authority-free controller-policy increment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import tempfile


POLICY_PATH = "tools/windows/synthetic-launcher-controller/ControllerPolicy.cs"
TEST_PATH = "tools/windows/synthetic-launcher-controller/ControllerPolicyTests.cs"
VERIFIER_PATH = "tools/windows/synthetic-launcher-controller/verify_controller_policy.py"
README_PATH = "tools/windows/synthetic-launcher-controller/README.md"
PUBLIC_PATH = "config/synthetic-launcher-controller-policy-v1.json"
PUBLIC_SCHEMA_PATH = "config/synthetic-launcher-controller-policy-v1.schema.json"
PRIVATE_SCHEMA_PATH = "config/synthetic-launcher-controller-private-v1.schema.json"
MAX_BYTES = 256 * 1024
GIT = pathlib.Path("/usr/bin/git")

FROZEN_IDENTITIES = {
    POLICY_PATH: (41856, "0bd6e9590a31f64326706377a0789ad9fef5b715815898d074bb73bd3dec329d"),
    TEST_PATH: (95806, "b9e9b72e48006f4806bbd972f73ab6d4d09bd6367ef524a79a117efd9a36086f"),
    PUBLIC_PATH: (3002, "0c6d36a80786ff123e428ee5f0f0493306067b50bbf387c011864100d3fcd6c4"),
    PUBLIC_SCHEMA_PATH: (3085, "a343d814e0bc31b46fa4e43d239d7e764a8b485efa56507231a7c3f61aa488f0"),
    PRIVATE_SCHEMA_PATH: (2881, "f8b1ae19840c9bbb9dbc9ab32d8872e4b44f5091a9a5440ae851a78daed7a279"),
    README_PATH: (2971, "acd2233f035ab9e7e7b6275c8e2f7dbd7125d07bc9c8f6259e5bcc736fafe843"),
}

BOUND_PATHS = tuple(FROZEN_IDENTITIES) + (VERIFIER_PATH,)
EXPECTED_STAGES = [
    "BindInputs", "PreflightRefusal", "ExplorerToken", "PrimaryToken",
    "RegistryDenial", "GuardBefore", "Environment", "CreateApproved",
    "CreateSuspended", "JobAssign", "PreResumeApproved", "Resume", "WindowReady",
    "ReadyCaptureOne", "ReadyCaptureTwo", "InputGuards", "SendInput",
    "CompleteCaptureOne", "CompleteCaptureTwo", "Abort", "Cleanup", "RebindPublish",
]
EXPECTED_ENVIRONMENT = [
    "CM0102_SYNTHETIC_CWD_SHA256", "CM0102_SYNTHETIC_INPUT_NONCE",
    "SystemRoot", "TEMP", "TMP", "WINDIR",
]
EXPECTED_SCENARIOS = ["locked-refusal-v1", "tree-timeout-v1", "ui-success-v1"]
EXPECTED_FIXED_NAMES = {
    "controller": "SyntheticLauncherController.exe",
    "fixture": "SyntheticLauncherFixture.exe",
    "private_configuration": "SyntheticLauncherController.private.v1.json",
    "public_configuration": "SyntheticLauncherController.public.v1.json",
}
EXPECTED_HOST = {
    "byte_count": 3310,
    "sha256": "96e38bb7932e1acb64aa7c9a33012f3425318b3a8e3aaf7ce98aaf8e1cd27659",
}
EXPECTED_FIXTURE = {
    "build_source_commit": "067600d9d41bb372531b9d4e1a38f04f093abf3d",
    "executable": {"byte_count": 14336, "sha256": "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6"},
    "profile": {"byte_count": 1104, "sha256": "e9952158c5789149ab0bda8e1afc90f1467281b2e1ca1155a2e780a8276aa80b"},
    "retained_manifest": {"byte_count": 8377, "sha256": "f5e4b6938fb7fde7111de3ccb7b1e685abb4945aaa7521be2210ece640c52e4c"},
    "source": {"byte_count": 20355, "sha256": "d730bda0acc2cf89ab6e212f49620a2e42b00392a3976f1467c0931bce66ae1c"},
    "tests": {"byte_count": 11742, "sha256": "da970254f9455ff14e681de0c291235cf35298c3fc230b194f8ce778b7a83cf6"},
}
EXPECTED_STATUS = {
    "controller_entrypoint": "absent", "controller_image": "absent",
    "fixture_execution_status": "not-run", "live_adapter": "absent",
    "original_behavior_qualified": False, "original_execution_status": "not-run",
    "private_configuration_instance": "absent", "qualification_eligible": False,
    "reporting": "absent", "retained_run_harness": "absent",
    "tree_timeout_fixture_image": "absent",
}
POST_SCHEMA_CONSTRAINT = ("private instances must first be parsed as canonical duplicate-free ASCII JSON with no "
    "floating-point lexical forms; guard_paths are additionally required to be pairwise case-insensitive distinct "
    "and non-ancestor under Windows path semantics; verify_controller_policy.py enforces these constraints")


class VerificationError(Exception):
    pass


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False,
        sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def identity(raw: bytes) -> tuple[int, str]:
    return len(raw), hashlib.sha256(raw).hexdigest()


def duplicate_guard(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError("duplicate JSON key")
        result[key] = value
    return result


def parse_canonical_json(raw: bytes, label: str) -> object:
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
    def stable_file_identity(value: os.stat_result) -> tuple[int, ...]:
        return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
                value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
                value.st_ctime_ns)

    expected = stable_file_identity(before)
    if expected != stable_file_identity(opened) or expected != stable_file_identity(after) or len(raw) != before.st_size:
        raise VerificationError("input changed during read")
    return bytes(raw)


def decode_source(raw: bytes, label: str) -> str:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n") or b"\0" in raw:
        raise VerificationError(label + " encoding")
    try:
        return raw.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise VerificationError(label + " UTF-8") from error


def compact_code(text: str, label: str) -> tuple[str, list[str]]:
    try:
        text.encode("ascii", "strict")
    except UnicodeEncodeError as error:
        raise VerificationError(label + " non-ASCII source") from error
    if any(marker in text for marker in ("//", "/*", "*/")) or re.search(r"(?m)^\s*#", text):
        raise VerificationError(label + " comments or directives")
    if re.search(r"\\(?:u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|x[0-9A-Fa-f]{1,4})", text):
        raise VerificationError(label + " escaped identifier")
    if re.search(r"(?:@|\$)\"", text):
        raise VerificationError(label + " unsupported string form")
    strings: list[str] = []

    def replace(match: re.Match[str]) -> str:
        value = match.group(0)[1:-1]
        if "\\" in value:
            raise VerificationError(label + " escaped string")
        strings.append(value)
        return '""'

    without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', replace, text)
    if "@" in without_strings:
        raise VerificationError(label + " verbatim identifier")
    return re.sub(r"\s+", "", without_strings), strings


def verify_authority_surface(text: str, label: str) -> tuple[str, list[str]]:
    using_values = re.findall(r"(?m)^using\s+[^;]+;", text)
    if using_values != ["using System;"]:
        raise VerificationError(label + " using surface")
    compact, strings = compact_code(text, label)
    forbidden = (
        "DllImport", "System.Runtime.InteropServices", "System.IO", "System.Diagnostics",
        "System.Net", "System.Reflection", "System.Threading", "Microsoft.Win32",
        "Microsoft.VisualBasic", "extern", "unsafe", "dynamic", "global::",
        "Environment.", "AppDomain.", "Activator.", "Marshal.", "GCHandle",
        "Process.Start", "File.", "Directory.", "Registry.", "Socket.", "HttpClient",
        "DateTime", "DateTimeOffset", "Stopwatch", "Random(", "Guid.", "CodeDom",
        "ManagementObject", "Interaction.Shell", "System.", "Type.GetType", ".GetMethod",
        ".GetConstructor", ".Invoke", "Delegate.", "Activator.CreateInstance",
        "typeof(", ".GetType", ".GetMethods", ".GetMembers", ".InvokeMember",
        "Console.Open", "Console.Read", "Console.In", "Console.Set",
        "Console.Error", "Console.Out",
    )
    for value in forbidden:
        if value in compact:
            raise VerificationError(label + " forbidden token " + value)
    if re.search(r"\b(?:CreateProcessAsUserW|CreateProcessWithTokenW|CreateProcessW|ShellExecute\w*)\(", compact):
        raise VerificationError(label + " authority invocation")
    return compact, strings


def verify_profile(profile: object, schema: object, private_schema: object) -> None:
    if not isinstance(profile, dict):
        raise VerificationError("public profile shape")
    if profile.get("schema_version") != 1 or profile.get("policy_only") is not True:
        raise VerificationError("public profile version")
    if profile.get("authority") != {name: False for name in (
        "capture", "clock", "environment_read", "filesystem", "input", "native_interop",
        "network", "process_creation", "publication", "randomness", "registry", "reporting", "ui") }:
        raise VerificationError("authority profile")
    if profile.get("accepted_host_artifact") != EXPECTED_HOST or profile.get("fixture") != EXPECTED_FIXTURE:
        raise VerificationError("accepted input identities")
    if profile.get("fixed_names") != EXPECTED_FIXED_NAMES or profile.get("environment_names") != EXPECTED_ENVIRONMENT:
        raise VerificationError("fixed names or environment")
    if profile.get("scenarios") != EXPECTED_SCENARIOS or profile.get("stage_order") != EXPECTED_STAGES:
        raise VerificationError("scenario or stage profile")
    if profile.get("capture") != {"height": 240, "per_state_count": 2, "width": 320}:
        raise VerificationError("capture profile")
    if profile.get("input") != {"event_count": 3}:
        raise VerificationError("input profile")
    if profile.get("registry") != {"required_result": 5, "sam_desired": 983103,
                                    "target_id": "cm0102-installation-32-v1", "wow64_view_flags": 0}:
        raise VerificationError("registry profile")
    expected_jobs = {
        "locked-refusal-v1": {"job_required": False},
        "tree-timeout-v1": {"active_process_limit": 2, "breakaway_forbidden": True,
            "job_memory_limit_bytes": 536870912, "job_required": True, "kill_on_close": True,
            "process_memory_limit_bytes": 268435456},
        "ui-success-v1": {"active_process_limit": 1, "breakaway_forbidden": True,
            "job_memory_limit_bytes": 268435456, "job_required": True, "kill_on_close": True,
            "process_memory_limit_bytes": 268435456},
    }
    if profile.get("job_profiles") != expected_jobs or profile.get("status") != EXPECTED_STATUS:
        raise VerificationError("job or status profile")
    if profile.get("private_guard_roles") != ["accepted-host-artifact", "attempt-root", "installed-tree", "virtual-store-tree"]:
        raise VerificationError("private guard roles")
    if profile.get("relationship_policy_id") != "uac-linked-filtered-v1" or profile.get("test_assembly_only_entrypoint") is not True:
        raise VerificationError("policy identity")
    if schema != {"$schema": "https://json-schema.org/draft/2020-12/schema", "const": profile, "type": "object"}:
        raise VerificationError("public schema is not exact")
    if not isinstance(private_schema, dict) or private_schema.get("additionalProperties") is not False:
        raise VerificationError("private schema root")
    if private_schema.get("$comment") != POST_SCHEMA_CONSTRAINT:
        raise VerificationError("private schema semantic constraint")
    properties = private_schema.get("properties")
    if not isinstance(properties, dict) or set(properties) != {"expected_identities", "guard_paths", "scenario_id", "schema_version"}:
        raise VerificationError("private schema fields")
    if private_schema.get("required") != ["expected_identities", "guard_paths", "scenario_id", "schema_version"]:
        raise VerificationError("private schema required fields")
    if properties["scenario_id"].get("enum") != EXPECTED_SCENARIOS:
        raise VerificationError("private scenario enum")
    identity_properties = properties["expected_identities"].get("properties", {})
    if identity_properties.get("accepted_host_artifact") != {"const": EXPECTED_HOST} or \
            identity_properties.get("fixture_image") != {"const": EXPECTED_FIXTURE["executable"]}:
        raise VerificationError("private fixed identity schema")


def valid_identity(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {"byte_count", "sha256"}:
        return False
    count = value["byte_count"]
    integral = (isinstance(count, int) and not isinstance(count, bool)) or \
        (isinstance(count, float) and count.is_integer())
    return (integral and 1 <= count <= 2147483647 and isinstance(value["sha256"], str) and
        re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None and value["sha256"] != "0" * 64)


def valid_guard_path(value: object, artifact: bool) -> bool:
    if not isinstance(value, str) or not value.isascii() or not 3 <= len(value) <= 260 or \
            re.fullmatch(r"[A-Za-z]:\\[^\x00-\x1f]+", value) is None:
        return False
    if any(marker in value for marker in ("/", "%", "*", "?", "<", ">", '"', "|")) or ":" in value[2:]:
        return False
    segments = value[3:].split("\\")
    if any(not segment or segment.startswith(".") or segment.endswith((" ", ".")) for segment in segments):
        return False
    reserved = {"con", "prn", "aux", "nul", "clock$", "conin$", "conout$",
                "com1", "com2", "com3", "com4", "com5",
                "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
                "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"}
    stems = [segment.split(".", 1)[0].rstrip(" .").casefold() for segment in segments]
    if any(stem in reserved or re.fullmatch(r"(?:com|lpt)(?:[1-9]|\u00b9|\u00b2|\u00b3)", stem)
            for stem in stems):
        return False
    folded = value.casefold()
    if artifact:
        return folded.endswith(".json")
    return not folded.endswith((".exe", ".com", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".dll"))


def validate_private_instance(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"schema_version", "scenario_id", "expected_identities", "guard_paths"}:
        raise VerificationError("private instance root")
    if isinstance(value["schema_version"], bool) or value["schema_version"] != 1 or \
            value["scenario_id"] not in EXPECTED_SCENARIOS:
        raise VerificationError("private instance version or scenario")
    identities = value["expected_identities"]
    identity_keys = {"accepted_host_artifact", "controller_image", "fixture_image", "public_configuration"}
    if not isinstance(identities, dict) or set(identities) != identity_keys or not all(valid_identity(item) for item in identities.values()):
        raise VerificationError("private identities")
    if identities["accepted_host_artifact"] != EXPECTED_HOST or identities["fixture_image"] != EXPECTED_FIXTURE["executable"]:
        raise VerificationError("private fixed identities")
    paths = value["guard_paths"]
    path_keys = {"accepted_host_artifact", "attempt_root", "installed_tree", "virtual_store_tree"}
    if not isinstance(paths, dict) or set(paths) != path_keys:
        raise VerificationError("private guard paths")
    for key, item in paths.items():
        if not valid_guard_path(item, key == "accepted_host_artifact"):
            raise VerificationError("private guard path value")
    folded = [item.casefold().rstrip("\\") for item in paths.values()]
    if len(set(folded)) != len(folded) or any(left.startswith(right + "\\") or right.startswith(left + "\\")
        for index, left in enumerate(folded) for right in folded[index + 1:]):
        raise VerificationError("private guard overlap")


def verify_texts(policy: str, tests: str, profile: dict[str, object]) -> None:
    policy_compact, policy_strings = verify_authority_surface(policy, "policy")
    tests_compact, test_strings = verify_authority_surface(tests, "tests")
    if "Main(" in policy_compact or "Console." in policy_compact:
        raise VerificationError("production entrypoint or console")
    if tests_compact.count("intMain()") != 1 or tests_compact.count("Console.WriteLine(") != 1:
        raise VerificationError("test entrypoint")
    if re.findall(r"Console\.([A-Za-z][A-Za-z0-9]*)", tests_compact) != ["WriteLine"]:
        raise VerificationError("test console surface")
    if "PASS " not in test_strings or tests_compact.count("return0;") != 1:
        raise VerificationError("test output structure")
    executable_strings = [value for value in policy_strings + test_strings if value.casefold().endswith(".exe")]
    if sorted(executable_strings) != ["SyntheticLauncherController.exe", "SyntheticLauncherFixture.exe"]:
        raise VerificationError("executable literal surface")
    enum = re.search(r"internalenumAttemptStage\{(?P<body>.*?)\}internalenumAttemptTerminal", policy_compact)
    if enum is None:
        raise VerificationError("stage enum")
    stages = re.findall(r"([A-Za-z][A-Za-z0-9]*)=[0-9]+", enum.group("body"))
    if stages != EXPECTED_STAGES or stages != profile["stage_order"]:
        raise VerificationError("source stage order")
    required = (
        "internalstaticPermitTokenRelationship(", "internalstaticPermitLaunchToken(",
        "internalstaticPermitPreflight(", "internalstaticPermitApproveCreate(",
        "internalstaticPermitJobBeforeResume(", "internalstaticPermitPreResume(",
        "internalstaticPermitReadyCaptureOne(", "internalstaticPermitReadyCaptureTwo(",
        "internalstaticPermitCompleteCaptureOne(", "internalstaticPermitCompleteCaptureTwo(",
        "internalstaticPermitCleanupUi(", "internalstaticPermitCleanupTimeout(",
        "internalstaticPermitCleanupLocked(", "internalstaticPermitAbort(",
        "internalstaticPermitCleanupAbort(", "internalstaticAttemptStateStart(",
        "newPermit(stage,scenario,state,state.Generation,PermitKey)",
        "newPermit(AttemptStage.Abort,scenario,state,state.Generation,PermitKey)",
        "facts.ResumeCallsSoFar==0",
    )
    for fragment in required:
        if policy_compact.count(fragment) != 1:
            raise VerificationError("required policy fragment " + fragment)
    for value in EXPECTED_ENVIRONMENT + EXPECTED_SCENARIOS + list(EXPECTED_FIXED_NAMES.values()):
        if value not in policy_strings:
            raise VerificationError("missing fixed source literal")
    fact_classes = re.findall(r"internalsealedclass([A-Za-z][A-Za-z0-9]*Facts)\{(.*?)\}", policy_compact)
    if len(fact_classes) != 22:
        raise VerificationError("fact class count")
    critical_fields = []
    for _class_name, body in fact_classes:
        critical_fields.extend(re.findall(
            r"internal(?:bool|int|long|string|string\[\])([A-Za-z][A-Za-z0-9]*);", body))
    for field in sorted(set(critical_fields)):
        if len(re.findall(r"\b" + re.escape(field) + r"\b", tests)) < 2:
            raise VerificationError("fact field lacks mutation test " + field)


def git_environment() -> dict[str, str]:
    return {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1", "LANG": "C", "LC_ALL": "C"}


def run_git(repo: pathlib.Path, arguments: list[str]) -> bytes:
    if not GIT.is_file():
        raise VerificationError("absolute Git unavailable")
    completed = subprocess.run(
        [os.fspath(GIT), "--no-replace-objects", "-c", "core.hooksPath=/dev/null",
         "-C", os.fspath(repo), *arguments], cwd="/", env=git_environment(),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=10, check=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise VerificationError("Git binding failed")
    return completed.stdout


def validate_commit(repo: pathlib.Path, commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise VerificationError("source commit is not a full lowercase hash")
    if run_git(repo, ["cat-file", "-t", commit]) != b"commit\n":
        raise VerificationError("source object is not a commit")
    resolved = run_git(repo, ["rev-parse", "--verify", commit + "^{commit}"]).decode("ascii").strip()
    head = run_git(repo, ["rev-parse", "--verify", "HEAD^{commit}"]).decode("ascii").strip()
    if resolved != commit or head != commit:
        raise VerificationError("source commit is not exact HEAD")


def verify(repo_argument: pathlib.Path, commit: str) -> dict[str, tuple[int, str]]:
    if not repo_argument.is_absolute() or repo_argument.resolve(strict=True) != repo_argument:
        raise VerificationError("repository path is not canonical absolute")
    repo = repo_argument
    require_path_components(repo)
    top = run_git(repo, ["rev-parse", "--show-toplevel"]).decode("utf-8").strip()
    if pathlib.Path(top) != repo:
        raise VerificationError("repository is not canonical top level")
    expected_verifier = repo / VERIFIER_PATH
    if pathlib.Path(__file__).absolute() != expected_verifier:
        raise VerificationError("verifier is not executing from canonical path")
    validate_commit(repo, commit)
    captured: dict[str, bytes] = {}
    identities: dict[str, tuple[int, str]] = {}
    for relative in BOUND_PATHS:
        raw = read_bound(repo / relative)
        if relative in FROZEN_IDENTITIES and identity(raw) != FROZEN_IDENTITIES[relative]:
            raise VerificationError(relative + " frozen identity")
        committed = run_git(repo, ["show", commit + ":" + relative])
        if raw != committed:
            raise VerificationError(relative + " differs from source commit")
        captured[relative] = raw
        identities[relative] = identity(raw)
    policy = decode_source(captured[POLICY_PATH], "policy")
    tests = decode_source(captured[TEST_PATH], "tests")
    profile = parse_canonical_json(captured[PUBLIC_PATH], "public profile")
    public_schema = parse_canonical_json(captured[PUBLIC_SCHEMA_PATH], "public schema")
    private_schema = parse_canonical_json(captured[PRIVATE_SCHEMA_PATH], "private schema")
    verify_profile(profile, public_schema, private_schema)
    verify_texts(policy, tests, profile)
    if "PASS 2601" not in decode_source(captured[README_PATH], "README"):
        raise VerificationError("README test result")
    return identities


def private_fixture() -> dict[str, object]:
    return {
        "schema_version": 1, "scenario_id": "ui-success-v1",
        "expected_identities": {
            "accepted_host_artifact": EXPECTED_HOST,
            "controller_image": {"byte_count": 10, "sha256": "1" * 64},
            "fixture_image": EXPECTED_FIXTURE["executable"],
            "public_configuration": {"byte_count": 10, "sha256": "2" * 64},
        },
        "guard_paths": {
            "accepted_host_artifact": "C:\\private-a\\host.json",
            "attempt_root": "C:\\private-b\\attempt",
            "installed_tree": "C:\\private-c\\installed",
            "virtual_store_tree": "C:\\private-d\\virtual-store",
        },
    }


def self_test() -> None:
    for value in ("HEAD", "a" * 39, "A" * 40, "a" * 40 + "^{tree}"):
        if re.fullmatch(r"[0-9a-f]{40}", value) is not None:
            raise AssertionError("commit grammar")
    mutations = (
        "System . Diagnostics . Process . Start(\"x\")",
        "global :: System . IO . File . ReadAllText(\"x\")",
        "Microsoft . Win32 . Registry . GetValue(\"x\",\"y\",null)",
        "[DllImport(\"x\")] extern static void X();", "unsafe { }", "dynamic value",
        "System . Reflection . Assembly . Load(\"x\")", "DateTime . UtcNow",
        "Type.GetType(\"System.Diagnostics.Process, System\").GetMethod(\"Start\").Invoke(null,null)",
        "typeof(Object).Assembly.GetTypes()",
        "System.@Diagnostics.@Process.@Start(\"x\")",
        "System.Diagnos\u200ctics.Process.St\u200cart(\"x\")",
        "Func<string,Type> f = Type.GetType",
        "System.Resources.ResourceManager.CreateFileBasedResourceManager(\"x\", \".\", null).GetString(\"secret\")",
        "Console.OpenStandardInput()",
    )
    for mutation in mutations:
        try:
            verify_authority_surface("using System;\n" + mutation + ";\n", "mutation")
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted authority mutation")
    value = private_fixture()
    validate_private_instance(value)
    integral_float = json.loads(json.dumps(value))
    for item in integral_float["expected_identities"].values():
        item["byte_count"] = float(item["byte_count"])
    validate_private_instance(integral_float)
    try:
        parse_canonical_json(b'{"byte_count":10.0}\n', "float mutation")
    except VerificationError:
        pass
    else:
        raise AssertionError("accepted floating-point lexical form")
    for raw in (b'NaN\n', b'Infinity\n', b'-Infinity\n', b'{"value":NaN}\n'):
        try:
            parse_canonical_json(raw, "non-finite mutation")
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted non-finite JSON value")
    for key, bad in (
        ("schema_version", True),
        ("scenario_id", "unknown"),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "..\\relative"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\private-a"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\tool.exe"}),
        ("guard_paths", {**value["guard_paths"], "accepted_host_artifact": "C:\\bad\\.json"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\.exe"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\attempt\n"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\NUL"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\NUL .json"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\COM\u00b9"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\LPT\u00b2"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\CONIN$"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\CONOUT$"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\cloc\u212a$"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\tool.p\u017f1"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\%TEMP%\\attempt"}),
        ("guard_paths", {**value["guard_paths"], "attempt_root": "C:\\bad\\x\u0000y"}),
        ("expected_identities", {**value["expected_identities"],
            "accepted_host_artifact": {"byte_count": 3310, "sha256": "3" * 64}}),
        ("expected_identities", {**value["expected_identities"],
            "fixture_image": {"byte_count": 14336, "sha256": "4" * 64}}),
        ("expected_identities", {**value["expected_identities"],
            "controller_image": {"byte_count": 10, "sha256": "0" * 64}}),
        ("expected_identities", {**value["expected_identities"],
            "controller_image": {"byte_count": 10, "sha256": "1" * 64 + "\n"}}),
    ):
        changed = dict(value)
        changed[key] = bad
        try:
            validate_private_instance(changed)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted private mutation")
    with tempfile.TemporaryDirectory() as directory:
        copied = pathlib.Path(directory) / "verify_controller_policy.py"
        copied.write_bytes(pathlib.Path(__file__).read_bytes())
        if copied.absolute() == pathlib.Path(__file__).absolute():
            raise AssertionError("copied verifier control")


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("self-test")
    check = modes.add_parser("verify")
    check.add_argument("--repo", required=True, type=pathlib.Path)
    check.add_argument("--source-commit", required=True)
    arguments = parser.parse_args()
    try:
        if arguments.mode == "self-test":
            self_test()
            result = None
        else:
            result = verify(arguments.repo, arguments.source_commit)
    except (VerificationError, AssertionError, OSError, subprocess.SubprocessError) as error:
        print("FAIL " + str(error))
        return 1
    if result is None:
        print("PASS controller-policy-self-test")
    else:
        print(json.dumps({"files": {key: {"byte_count": value[0], "sha256": value[1]}
            for key, value in sorted(result.items())}, "status": "controller-policy-verified"},
            sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
