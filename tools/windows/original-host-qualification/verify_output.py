#!/usr/bin/env python3
"""Strict verifier and static safety checks for the Windows qualification probe."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile


TOP_LEVEL = {
    "capabilities",
    "checks",
    "errors",
    "guards",
    "host",
    "inputs",
    "probe",
    "registry",
    "run",
    "schema_version",
    "session",
    "summary",
    "tokens",
}
SUMMARY = {
    "comparison_verdict",
    "completeness",
    "direct_wsl_launch_safe",
    "error_count",
    "failed_count",
    "original_execution_status",
    "passed_count",
    "required_check_count",
    "safety_verdict",
}
REQUIRED_CHECK_IDS = {
    "active-input-desktop",
    "clean-manifest-identity",
    "clean-tree-exact",
    "clean-tree-read-only",
    "explorer-token-medium",
    "installed-tree-plain",
    "installed-tree-stable",
    "iso-identity",
    "no-game-process-after",
    "no-game-process-before",
    "optical-media",
    "probe-image-stable",
    "probe-process-x86",
    "registry-current-exact-access",
    "registry-explorer-exact-denial",
    "registry-location-binding",
    "registry-read-only",
    "required-host-tools",
    "virtual-store-plain",
    "virtual-store-stable",
    "wsl-token-high-hazard",
}
REQUIRED_API_IDS = {
    "advapi32-registry",
    "advapi32-token",
    "kernel32-filesystem",
    "user32-desktop",
    "wtsapi32-session",
}
REQUIRED_TOOL_IDS = {
    "cdb",
    "cmd",
    "csc-x64",
    "csc-x86",
    "powershell",
    "python313",
    "windbg",
}
BANNED_PRODUCTION_TOKENS = (
    "CreateProcess",
    "ShellExecute",
    "Process.Start",
    "RegSetValue",
    "RegistryKey.SetValue",
    "File.WriteAll",
    "File.AppendAll",
    "Directory.CreateDirectory",
    "Directory.Delete",
    "File.Delete",
    "File.Move",
    "File.Copy",
)


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")


def reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def decode_json(raw: bytes | str) -> object:
    return json.loads(
        raw,
        object_pairs_hook=strict_pairs,
        parse_constant=reject_constant,
    )


def strict_object(value: object, keys: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name}: keys")
    return value


def integer(value: object, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name}: integer")
    return value


def boolean(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name}: boolean")
    return value


def text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name}: string")
    if re.search(r"(?:[A-Za-z]:[\\/]|\\\\|/home/|/mnt/)", value):
        raise ValueError(f"{name}: path-like string")
    return value


def sha256(value: object, name: str) -> str:
    result = text(value, name)
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise ValueError(f"{name}: sha256")
    return result


def identity(value: object, name: str) -> None:
    item = strict_object(value, {"byte_count", "sha256"}, name)
    if integer(item["byte_count"], f"{name}.byte_count") < 0:
        raise ValueError(f"{name}: negative size")
    sha256(item["sha256"], f"{name}.sha256")


def tree(value: object, name: str) -> None:
    item = strict_object(
        value,
        {
            "case_collision_count",
            "directory_count",
            "file_count",
            "present",
            "reparse_count",
            "total_bytes",
            "tree_sha256",
            "unstable_count",
        },
        name,
    )
    boolean(item["present"], f"{name}.present")
    for key in (
        "case_collision_count",
        "directory_count",
        "file_count",
        "reparse_count",
        "total_bytes",
        "unstable_count",
    ):
        if integer(item[key], f"{name}.{key}") < 0:
            raise ValueError(f"{name}.{key}: negative")
    sha256(item["tree_sha256"], f"{name}.tree_sha256")


def validate_full_schema(value: dict[str, object]) -> None:
    probe = strict_object(
        value["probe"],
        {
            "executable",
            "expectations_sha256",
            "id",
            "private_locator_sha256",
            "source_revision",
            "version",
        },
        "probe",
    )
    identity(probe["executable"], "probe.executable")
    sha256(probe["expectations_sha256"], "probe.expectations_sha256")
    sha256(probe["private_locator_sha256"], "probe.private_locator_sha256")
    if not re.fullmatch(r"[0-9a-f]{40}", text(probe["source_revision"], "probe.source_revision")):
        raise ValueError("probe.source_revision")
    text(probe["id"], "probe.id")
    text(probe["version"], "probe.version")

    run = strict_object(value["run"], {"elapsed_ms", "observed_at_utc"}, "run")
    if integer(run["elapsed_ms"], "run.elapsed_ms") < 0:
        raise ValueError("run.elapsed_ms")
    text(run["observed_at_utc"], "run.observed_at_utc")

    host = strict_object(
        value["host"],
        {
            "architecture",
            "display_version",
            "edition",
            "locale",
            "machine_fingerprint_sha256",
            "os_build",
            "os_major",
            "os_minor",
            "product_name",
            "time_zone",
        },
        "host",
    )
    sha256(host["machine_fingerprint_sha256"], "host.machine_fingerprint_sha256")
    for key in ("os_build", "os_major", "os_minor"):
        integer(host[key], f"host.{key}")
    for key in ("architecture", "display_version", "edition", "locale", "product_name", "time_zone"):
        text(host[key], f"host.{key}")

    session = strict_object(
        value["session"],
        {
            "active_console_session_id",
            "bits_per_pixel",
            "current_process_session_id",
            "explorer_process_count",
            "explorer_session_id",
            "input_desktop",
            "screen_height",
            "screen_width",
            "window_station",
        },
        "session",
    )
    for key in session:
        if key in {"input_desktop", "window_station"}:
            text(session[key], f"session.{key}")
        else:
            if integer(session[key], f"session.{key}") < 0:
                raise ValueError(f"session.{key}: negative")

    tokens = strict_object(value["tokens"], {"explorer", "probe"}, "tokens")
    for side in ("explorer", "probe"):
        token = strict_object(
            tokens[side],
            {"account_sid_sha256", "elevation_type", "integrity", "is_administrator", "privileges", "session_id"},
            f"tokens.{side}",
        )
        sha256(token["account_sid_sha256"], f"tokens.{side}.account_sid_sha256")
        text(token["elevation_type"], f"tokens.{side}.elevation_type")
        text(token["integrity"], f"tokens.{side}.integrity")
        boolean(token["is_administrator"], f"tokens.{side}.is_administrator")
        integer(token["session_id"], f"tokens.{side}.session_id")
        privileges = token["privileges"]
        if not isinstance(privileges, list):
            raise ValueError(f"tokens.{side}.privileges")
        names = []
        for privilege in privileges:
            entry = strict_object(privilege, {"attributes", "name"}, "privilege")
            integer(entry["attributes"], "privilege.attributes")
            names.append(text(entry["name"], "privilege.name"))
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError(f"tokens.{side}.privileges ordering")

    registry = strict_object(
        value["registry"],
        {"acl", "exact_access", "key_id", "last_write_unchanged", "location", "view"},
        "registry",
    )
    text(registry["key_id"], "registry.key_id")
    boolean(registry["last_write_unchanged"], "registry.last_write_unchanged")
    if registry["view"] != "32-bit":
        raise ValueError("registry.view")
    exact = strict_object(
        registry["exact_access"],
        {"desired_access", "explorer_token_win32_result", "probe_token_win32_result"},
        "registry.exact_access",
    )
    if integer(exact["desired_access"], "registry.desired_access") != 0x000F003F:
        raise ValueError("registry.desired_access")
    if integer(exact["explorer_token_win32_result"], "registry.explorer_result") < 0:
        raise ValueError("registry.explorer_result: negative")
    if integer(exact["probe_token_win32_result"], "registry.probe_result") < 0:
        raise ValueError("registry.probe_result: negative")
    location = strict_object(
        registry["location"],
        {"equals_configured_install_root", "sha256_utf16le", "utf16le_bytes", "value_kind"},
        "registry.location",
    )
    boolean(location["equals_configured_install_root"], "registry.location.equals")
    sha256(location["sha256_utf16le"], "registry.location.sha256")
    if integer(location["utf16le_bytes"], "registry.location.bytes") < 0:
        raise ValueError("registry.location.bytes: negative")
    text(location["value_kind"], "registry.location.kind")
    acl = strict_object(registry["acl"], {"aces", "group_sid", "owner_sid"}, "registry.acl")
    text(acl["group_sid"], "registry.acl.group_sid")
    text(acl["owner_sid"], "registry.acl.owner_sid")
    if not isinstance(acl["aces"], list):
        raise ValueError("registry.acl.aces")
    for ace in acl["aces"]:
        entry = strict_object(
            ace,
            {"access_mask", "access_type", "identity_sid", "inheritance_flags", "inherited", "propagation_flags"},
            "registry.ace",
        )
        for key in ("access_mask", "inheritance_flags", "propagation_flags"):
            if integer(entry[key], f"registry.ace.{key}") < 0:
                raise ValueError(f"registry.ace.{key}: negative")
        boolean(entry["inherited"], "registry.ace.inherited")
        text(entry["access_type"], "registry.ace.access_type")
        text(entry["identity_sid"], "registry.ace.identity_sid")

    inputs = strict_object(value["inputs"], {"clean", "iso"}, "inputs")
    clean = strict_object(
        inputs["clean"],
        {"extra_count", "manifest", "mismatch_count", "missing_count", "tree", "tree_expected_match", "writable_open_count"},
        "inputs.clean",
    )
    for key in ("extra_count", "mismatch_count", "missing_count", "writable_open_count"):
        if integer(clean[key], f"inputs.clean.{key}") < 0:
            raise ValueError(f"inputs.clean.{key}: negative")
    boolean(clean["tree_expected_match"], "inputs.clean.tree_expected_match")
    manifest = strict_object(clean["manifest"], {"expected_match", "identity"}, "inputs.clean.manifest")
    boolean(manifest["expected_match"], "inputs.clean.manifest.expected_match")
    identity(manifest["identity"], "inputs.clean.manifest.identity")
    tree(clean["tree"], "inputs.clean.tree")
    iso = strict_object(inputs["iso"], {"file", "optical_media"}, "inputs.iso")
    iso_file = strict_object(iso["file"], {"expected_match", "identity"}, "inputs.iso.file")
    boolean(iso_file["expected_match"], "inputs.iso.file.expected_match")
    identity(iso_file["identity"], "inputs.iso.file.identity")
    optical = strict_object(
        iso["optical_media"],
        {"drive_type", "executable", "expected_match", "volume_label_matches", "volume_label_sha256"},
        "inputs.iso.optical_media",
    )
    integer(optical["drive_type"], "inputs.iso.optical_media.drive_type")
    identity(optical["executable"], "inputs.iso.optical_media.executable")
    boolean(optical["expected_match"], "inputs.iso.optical_media.expected_match")
    boolean(optical["volume_label_matches"], "inputs.iso.optical_media.volume_label_matches")
    sha256(optical["volume_label_sha256"], "inputs.iso.optical_media.volume_label_sha256")

    guards = strict_object(
        value["guards"],
        {"cm0102_launched", "game_process_count_after", "game_process_count_before", "installed_tree", "virtual_store_tree"},
        "guards",
    )
    boolean(guards["cm0102_launched"], "guards.cm0102_launched")
    if integer(guards["game_process_count_after"], "guards.game_process_count_after") < 0:
        raise ValueError("guards.game_process_count_after: negative")
    if integer(guards["game_process_count_before"], "guards.game_process_count_before") < 0:
        raise ValueError("guards.game_process_count_before: negative")
    for name in ("installed_tree", "virtual_store_tree"):
        wrapper = strict_object(guards[name], {"after", "before", "unchanged"}, f"guards.{name}")
        tree(wrapper["before"], f"guards.{name}.before")
        tree(wrapper["after"], f"guards.{name}.after")
        boolean(wrapper["unchanged"], f"guards.{name}.unchanged")

    capabilities = strict_object(value["capabilities"], {"apis", "tools"}, "capabilities")
    for kind in ("apis", "tools"):
        items = capabilities[kind]
        if not isinstance(items, list):
            raise ValueError(f"capabilities.{kind}")
        ids = []
        for item in items:
            expected = {"id", "present"} if kind == "apis" else {"file", "id", "present"}
            entry = strict_object(item, expected, f"capabilities.{kind}.item")
            ids.append(text(entry["id"], f"capabilities.{kind}.id"))
            boolean(entry["present"], f"capabilities.{kind}.present")
            if kind == "tools" and entry["file"] is not None:
                identity(entry["file"], "capabilities.tools.file")
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError(f"capabilities.{kind} ordering")
        expected_ids = REQUIRED_API_IDS if kind == "apis" else REQUIRED_TOOL_IDS
        if set(ids) != expected_ids:
            raise ValueError(f"capabilities.{kind} set")
        if kind == "apis" and any(item["present"] is not True for item in items):
            raise ValueError("capabilities.apis unavailable")
        if kind == "tools":
            for item in items:
                if item["present"] != (item["file"] is not None):
                    raise ValueError("capabilities.tools identity consistency")

    errors = value["errors"]
    if not isinstance(errors, list):
        raise ValueError("errors")
    for error in errors:
        entry = strict_object(error, {"category", "check_id", "detail_code"}, "error")
        for key in entry:
            text(entry[key], f"error.{key}")


def iter_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def private_strings(config_path: pathlib.Path) -> list[str]:
    value = decode_json(config_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("private config must be an object")
    result: list[str] = []
    for item in value.values():
        if isinstance(item, str) and len(item) >= 3:
            result.extend((item, item.replace("\\", "/"), item.replace("/", "\\")))
    return result


def verify(path: pathlib.Path, forbid_file: pathlib.Path | None) -> None:
    raw = path.read_bytes()
    if len(raw) > 4 * 1024 * 1024 or not raw.endswith(b"\n") or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("output framing")
    value = decode_json(raw)
    strict_object(value, TOP_LEVEL, "top-level")
    if value["schema_version"] != 1:
        raise ValueError("schema version")
    summary = strict_object(value["summary"], SUMMARY, "summary")
    if summary["original_execution_status"] != "not-run" or summary["comparison_verdict"] != "not-run":
        raise ValueError("execution/comparison boundary")
    if summary["direct_wsl_launch_safe"] is not False:
        raise ValueError("direct launch safety")
    for key in ("error_count", "failed_count", "passed_count", "required_check_count"):
        if integer(summary[key], f"summary.{key}") < 0:
            raise ValueError(f"summary.{key}: negative")
    text(summary["completeness"], "summary.completeness")
    text(summary["safety_verdict"], "summary.safety_verdict")
    checks = value["checks"]
    if not isinstance(checks, list) or not checks:
        raise ValueError("checks")
    ids = []
    for item in checks:
        check = strict_object(item, {"detail_code", "id", "outcome", "required"}, "check")
        text(check["detail_code"], "check.detail_code")
        text(check["id"], "check.id")
        if check["outcome"] not in {"pass", "fail", "error"} or check["required"] is not True:
            raise ValueError("check value")
        ids.append(check["id"])
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("check ordering")
    counts = {state: sum(item["outcome"] == state for item in checks) for state in ("pass", "fail", "error")}
    if summary["passed_count"] != counts["pass"] or summary["failed_count"] != counts["fail"] or summary["error_count"] != counts["error"]:
        raise ValueError("check counts")
    if summary["required_check_count"] != len(checks):
        raise ValueError("required check count")
    errors = value["errors"]
    if not isinstance(errors, list) or len(errors) != summary["error_count"]:
        raise ValueError("error count")
    if not isinstance(value["guards"], dict) or value["guards"].get("cm0102_launched") is not False:
        raise ValueError("game launch guard")
    completeness = summary["completeness"]
    if completeness == "complete":
        if set(ids) != REQUIRED_CHECK_IDS:
            raise ValueError("required check set")
        validate_full_schema(value)
        expected_verdict = "eligible-for-synthetic-launcher-test" if counts["fail"] == 0 and counts["error"] == 0 else "unsafe"
        if summary["safety_verdict"] != expected_verdict or counts["error"] != 0:
            raise ValueError("complete verdict consistency")
    elif completeness == "incomplete":
        if ids != ["probe"] or counts != {"pass": 0, "fail": 0, "error": 1}:
            raise ValueError("minimal incomplete checks")
        if summary["safety_verdict"] != "inconclusive":
            raise ValueError("incomplete verdict consistency")
        if not isinstance(errors, list) or len(errors) != 1:
            raise ValueError("minimal errors")
        error = strict_object(errors[0], {"category", "check_id", "detail_code"}, "minimal error")
        if error["category"] != "probe" or error["check_id"] != "probe":
            raise ValueError("minimal error identity")
        text(error["detail_code"], "minimal error detail")
    else:
        raise ValueError("completeness")
    if raw != canonical(value):
        raise ValueError("non-canonical JSON")
    if forbid_file:
        forbidden = private_strings(forbid_file)
        for string_value in iter_strings(value):
            lowered = string_value.casefold()
            if any(item.casefold() in lowered for item in forbidden):
                raise ValueError("private string present")


def static_source(paths: list[pathlib.Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in BANNED_PRODUCTION_TOKENS:
            if token in text:
                raise ValueError(f"{path.name}: banned token {token}")
        if re.search(r"DllImport\(\s*\"(?:shell32|winexec)", text, re.IGNORECASE):
            raise ValueError(f"{path.name}: banned launch library")


def self_test() -> None:
    sample = {
        "a": [1, "\u00e9", False],
        "z": {"escaped": "x\ny"},
    }
    expected = b'{"a":[1,"\\u00e9",false],"z":{"escaped":"x\\ny"}}\n'
    if canonical(sample) != expected:
        raise AssertionError("canonical self-test")
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        private = root / "private.json"
        private.write_text(json.dumps({"path": r"C:\private\game"}), encoding="utf-8")
        if r"C:\private\game" not in private_strings(private):
            raise AssertionError("redaction self-test")
        check = {
            "detail_code": "self-test",
            "id": "probe",
            "outcome": "error",
            "required": True,
        }
        document = {
            "capabilities": {},
            "checks": [check],
            "errors": [
                {"category": "probe", "check_id": "probe", "detail_code": "self-test"}
            ],
            "guards": {"cm0102_launched": False},
            "host": {},
            "inputs": {},
            "probe": {},
            "registry": {},
            "run": {},
            "schema_version": 1,
            "session": {},
            "summary": {
                "comparison_verdict": "not-run",
                "completeness": "incomplete",
                "direct_wsl_launch_safe": False,
                "error_count": 1,
                "failed_count": 0,
                "original_execution_status": "not-run",
                "passed_count": 0,
                "required_check_count": 1,
                "safety_verdict": "inconclusive",
            },
            "tokens": {},
        }
        output = root / "output.json"
        output.write_bytes(canonical(document))
        verify(output, private)
        output.write_bytes(b'{"schema_version":1,"schema_version":1}\n')
        try:
            verify(output, private)
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate-key self-test")
        document["guards"]["cm0102_launched"] = True
        output.write_bytes(canonical(document))
        try:
            verify(output, private)
        except ValueError:
            pass
        else:
            raise AssertionError("game-launch guard self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    static = sub.add_parser("static-source")
    static.add_argument("paths", nargs="+", type=pathlib.Path)
    output = sub.add_parser("verify")
    output.add_argument("path", type=pathlib.Path)
    output.add_argument("--forbid-file", type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
    elif args.command == "static-source":
        static_source(args.paths)
    else:
        verify(args.path, args.forbid_file)
    print("PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, AssertionError, json.JSONDecodeError) as error:
        print(f"FAIL: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
