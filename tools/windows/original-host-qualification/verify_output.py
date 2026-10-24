#!/usr/bin/env python3
"""Strict verifier and static safety checks for the Windows qualification probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
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
    "private-inputs-distinct",
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
DIAGNOSTIC_STAGE_CSV = "arguments,canonical-serialization,capabilities,clean-manifest,clean-tree-after,clean-tree-before,console-initialization,current-token,expectations-load,explorer-token,game-process-after,game-process-before,host-observation,impersonation-restore,installed-tree-after,installed-tree-before,iso-file,locator-load,optical-media,preflight-inputs,probe-construction,probe-image-after,probe-start,redaction-scan,registry-current-access,registry-explorer-access,registry-last-write-after,registry-last-write-before,registry-metadata,report-assembly,session-desktop,session-discovery,session-display,stage-tracker,stdout-emission,virtual-store-after,virtual-store-before"
DIAGNOSTIC_STAGE_IDS = frozenset(DIAGNOSTIC_STAGE_CSV.split(","))
STABLE_EXCEPTION_CODE = re.compile(
    r"(?:unauthorized|file-not-found|directory-not-found|(?:io|crypto|exception)-[0-9a-f]{8})\Z"
)
BANNED_NORMALIZED_PATTERNS = (
    (r"\.start\(", "instance/static Start"),
    (r"\bcreateprocess(?:a|w)?\(", "CreateProcess"),
    (r"\bshellexecute(?:exa|exw|a|w)?\(", "ShellExecute"),
    (r"\bwinexec\(", "WinExec"),
    (r"\breg(?:create|set|delete|rename|replace|restore|load|unload|save)\w*\(", "registry mutation"),
    (r"\.(?:createsubkey|deletesubkeytree|deletesubkey|deletevalue|setvalue)\(", "managed registry mutation"),
    (r"\bfile\.(?:write\w*|append\w*|create|delete|move|copy|replace|setattributes|setcreationtime\w*|setlastaccesstime\w*|setlastwritetime\w*|encrypt|decrypt)\(", "file mutation"),
    (r"\bdirectory\.(?:create\w*|delete|move|setcreationtime\w*|setlastaccesstime\w*|setlastwritetime\w*)\(", "directory mutation"),
    (r"\bfilemode\.(?:append|create|createnew|openorcreate|truncate)\b", "writable FileMode"),
    (r"\bfileaccess\.(?:write|readwrite)\b", "writable FileAccess"),
)
ALLOWED_PINVOKES = {
    ("advapi32.dll", "AllocateAndInitializeSid"),
    ("advapi32.dll", "CheckTokenMembership"),
    ("advapi32.dll", "ConvertSidToStringSidW"),
    ("advapi32.dll", "DuplicateTokenEx"),
    ("advapi32.dll", "FreeSid"),
    ("advapi32.dll", "GetTokenInformation"),
    ("advapi32.dll", "LookupPrivilegeNameW"),
    ("advapi32.dll", "OpenProcessToken"),
    ("advapi32.dll", "OpenThreadToken"),
    ("advapi32.dll", "RegCloseKey"),
    ("advapi32.dll", "RegOpenKeyExA"),
    ("advapi32.dll", "RegQueryInfoKeyA"),
    ("kernel32.dll", "CloseHandle"),
    ("kernel32.dll", "CreateFileW"),
    ("kernel32.dll", "FreeLibrary"),
    ("kernel32.dll", "GetCurrentProcess"),
    ("kernel32.dll", "GetCurrentThread"),
    ("kernel32.dll", "GetDriveTypeW"),
    ("kernel32.dll", "GetFileAttributesW"),
    ("kernel32.dll", "GetFileInformationByHandle"),
    ("kernel32.dll", "GetFinalPathNameByHandleW"),
    ("kernel32.dll", "GetProcAddress"),
    ("kernel32.dll", "GetVolumeInformationW"),
    ("kernel32.dll", "LoadLibraryW"),
    ("kernel32.dll", "LocalFree"),
    ("kernel32.dll", "OpenProcess"),
    ("kernel32.dll", "WTSGetActiveConsoleSessionId"),
    ("ntdll.dll", "RtlGetVersion"),
    ("user32.dll", "CloseDesktop"),
    ("user32.dll", "GetProcessWindowStation"),
    ("user32.dll", "GetUserObjectInformationW"),
    ("user32.dll", "OpenInputDesktop"),
}


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


def bytes_identity(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read_bounded_plain(path: pathlib.Path, maximum_bytes: int) -> bytes:
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise ValueError("input is not a plain regular file")
    if before.st_size < 0 or before.st_size > maximum_bytes:
        raise ValueError("input exceeds byte limit")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
            or opened.st_size < 0
            or opened.st_size > maximum_bytes
        ):
            raise ValueError("input changed before bounded read")
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(descriptor, min(65536, maximum_bytes + 1 - observed))
            if not chunk:
                break
            observed += len(chunk)
            if observed > maximum_bytes:
                raise ValueError("input grew beyond byte limit")
            chunks.append(chunk)
        finished = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = path.stat(follow_symlinks=False)
    fingerprints = {
        (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
        for item in (before, opened, finished, after)
    }
    if len(fingerprints) != 1 or observed != before.st_size:
        raise ValueError("input changed during bounded read")
    return b"".join(chunks)


EXPECTATION_KEYS = {
    "clean_file_count",
    "clean_manifest_bytes",
    "clean_manifest_sha256",
    "clean_total_bytes",
    "compiler_bytes",
    "compiler_sha256",
    "compiler_ui_bytes",
    "compiler_ui_sha256",
    "iso_bytes",
    "iso_sha256",
    "optical_executable_bytes",
    "optical_executable_sha256",
    "optical_volume_label",
    "original_executable_bytes",
    "original_executable_sha256",
    "profile_id",
    "registry_exact_access_mask",
    "registry_key_id",
    "registry_subkey",
    "registry_value_name",
    "required_api_ids",
    "required_tool_ids",
    "schema_version",
}


def parse_expectations(raw: bytes) -> dict[str, object]:
    if len(raw) > 1024 * 1024 or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("expectations framing")
    value = strict_object(decode_json(raw), EXPECTATION_KEYS, "expectations")
    if value["schema_version"] != 1:
        raise ValueError("expectations schema")
    for key in (
        "clean_file_count",
        "clean_manifest_bytes",
        "clean_total_bytes",
        "compiler_bytes",
        "compiler_ui_bytes",
        "iso_bytes",
        "optical_executable_bytes",
        "original_executable_bytes",
    ):
        if integer(value[key], f"expectations.{key}") <= 0:
            raise ValueError(f"expectations.{key}")
    numeric_limits = {
        "clean_file_count": 1_000_000,
        "clean_manifest_bytes": 1024 * 1024,
        "clean_total_bytes": 1 << 50,
        "compiler_bytes": 1 << 34,
        "compiler_ui_bytes": 1 << 34,
        "iso_bytes": 1 << 40,
        "optical_executable_bytes": 1 << 34,
        "original_executable_bytes": 1 << 34,
    }
    for key, limit in numeric_limits.items():
        if value[key] > limit:
            raise ValueError(f"expectations.{key}")
    for key in (
        "clean_manifest_sha256",
        "compiler_sha256",
        "compiler_ui_sha256",
        "iso_sha256",
        "optical_executable_sha256",
        "original_executable_sha256",
    ):
        sha256(value[key], f"expectations.{key}")
    for key in (
        "optical_volume_label",
        "profile_id",
        "registry_key_id",
        "registry_subkey",
        "registry_value_name",
    ):
        text(value[key], f"expectations.{key}")
    if value["registry_exact_access_mask"] != 0x000F003F:
        raise ValueError("expectations.registry_exact_access_mask")
    for key, supported in (
        ("required_api_ids", REQUIRED_API_IDS),
        ("required_tool_ids", REQUIRED_TOOL_IDS),
    ):
        items = value[key]
        if (
            not isinstance(items, list)
            or not items
            or len(items) > 64
            or any(not isinstance(item, str) or not item for item in items)
            or any(not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", item) for item in items)
            or items != sorted(items)
            or len(items) != len(set(items))
            or not set(items).issubset(supported)
        ):
            raise ValueError(f"expectations.{key}")
    return value


def load_expectations(path: pathlib.Path) -> tuple[dict[str, object], bytes]:
    raw = read_bounded_plain(path, 1024 * 1024)
    return parse_expectations(raw), raw


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


def validate_minimal_detail(value: object) -> str:
    detail = text(value, "minimal error detail")
    if detail in {"redaction-failure", "usage-or-config"}:
        return detail
    if detail.startswith("unhandled-v1-"):
        remainder = detail[len("unhandled-v1-") :]
        for stage in DIAGNOSTIC_STAGE_IDS:
            prefix = stage + "-"
            if remainder.startswith(prefix) and STABLE_EXCEPTION_CODE.fullmatch(
                remainder[len(prefix) :]
            ):
                return detail
        raise ValueError("minimal staged detail")
    if detail.startswith("unhandled-") and STABLE_EXCEPTION_CODE.fullmatch(
        detail[len("unhandled-") :]
    ):
        return detail
    raise ValueError("minimal detail")


def sha256(value: object, name: str) -> str:
    result = text(value, name)
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise ValueError(f"{name}: sha256")
    return result


def identity(value: object, name: str) -> dict[str, object]:
    item = strict_object(value, {"byte_count", "sha256"}, name)
    if integer(item["byte_count"], f"{name}.byte_count") < 0:
        raise ValueError(f"{name}: negative size")
    sha256(item["sha256"], f"{name}.sha256")
    if item["byte_count"] == 0 and item["sha256"] != hashlib.sha256(b"").hexdigest():
        raise ValueError(f"{name}: empty identity contradiction")
    return item


def tree(value: object, name: str) -> dict[str, object]:
    item = strict_object(
        value,
        {
            "case_collision_count",
            "directory_count",
            "file_count",
            "hardlink_count",
            "object_alias_count",
            "present",
            "reparse_count",
            "root_object_id_sha256",
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
        "hardlink_count",
        "object_alias_count",
        "reparse_count",
        "total_bytes",
        "unstable_count",
    ):
        if integer(item[key], f"{name}.{key}") < 0:
            raise ValueError(f"{name}.{key}: negative")
    sha256(item["tree_sha256"], f"{name}.tree_sha256")
    sha256(item["root_object_id_sha256"], f"{name}.root_object_id_sha256")
    if item["present"] and item["directory_count"] < 1:
        raise ValueError(f"{name}: present tree without root")
    if not item["present"] and any(
        item[key] != 0
        for key in (
            "case_collision_count",
            "directory_count",
            "file_count",
            "hardlink_count",
            "object_alias_count",
            "reparse_count",
            "total_bytes",
            "unstable_count",
        )
    ):
        raise ValueError(f"{name}: absent tree has observations")
    if not item["present"] and (
        item["tree_sha256"] != hashlib.sha256(b"").hexdigest()
        or item["root_object_id_sha256"]
        != hashlib.sha256("absent".encode("utf-16le")).hexdigest()
    ):
        raise ValueError(f"{name}: absent identity contradiction")
    if item["case_collision_count"] > item["file_count"] + item["directory_count"]:
        raise ValueError(f"{name}: collision count contradiction")
    return item


def validate_full_schema(
    value: dict[str, object], expectations: dict[str, object], expectations_raw: bytes
) -> dict[str, tuple[bool, str]]:
    probe = strict_object(
        value["probe"],
        {
            "executable",
            "executable_after",
            "executable_unchanged",
            "expectations_sha256",
            "id",
            "private_locator_sha256",
            "process_architecture",
            "source_revision",
            "version",
        },
        "probe",
    )
    executable = identity(probe["executable"], "probe.executable")
    executable_after = identity(probe["executable_after"], "probe.executable_after")
    boolean(probe["executable_unchanged"], "probe.executable_unchanged")
    if probe["executable_unchanged"] != (executable == executable_after):
        raise ValueError("probe executable consistency")
    if probe["expectations_sha256"] != hashlib.sha256(expectations_raw).hexdigest():
        raise ValueError("probe expectations identity")
    sha256(probe["private_locator_sha256"], "probe.private_locator_sha256")
    if not re.fullmatch(r"[0-9a-f]{40}", text(probe["source_revision"], "probe.source_revision")):
        raise ValueError("probe.source_revision")
    if probe["id"] != "cm0102-original-host-qualification" or probe["version"] != "1.1.0":
        raise ValueError("probe identity")
    if probe["process_architecture"] not in {"x86", "x64"}:
        raise ValueError("probe.process_architecture")

    run = strict_object(value["run"], {"elapsed_ms", "observed_at_utc"}, "run")
    if integer(run["elapsed_ms"], "run.elapsed_ms") < 0:
        raise ValueError("run.elapsed_ms")
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{7}Z",
        text(run["observed_at_utc"], "run.observed_at_utc"),
    ):
        raise ValueError("run.observed_at_utc")

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
        if integer(host[key], f"host.{key}") < 0:
            raise ValueError(f"host.{key}")
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
    if session["explorer_process_count"] != 1:
        raise ValueError("session.explorer_process_count")
    if session["screen_width"] <= 0 or session["screen_height"] <= 0 or session["bits_per_pixel"] <= 0:
        raise ValueError("session display bounds")

    tokens = strict_object(
        value["tokens"], {"explorer", "impersonation_restored", "probe"}, "tokens"
    )
    boolean(tokens["impersonation_restored"], "tokens.impersonation_restored")
    for side in ("explorer", "probe"):
        token = strict_object(
            tokens[side],
            {"account_sid_sha256", "elevation_type", "integrity", "is_administrator", "privileges", "session_id"},
            f"tokens.{side}",
        )
        sha256(token["account_sid_sha256"], f"tokens.{side}.account_sid_sha256")
        text(token["elevation_type"], f"tokens.{side}.elevation_type")
        text(token["integrity"], f"tokens.{side}.integrity")
        if token["elevation_type"] not in {"default", "full", "limited", "unknown"}:
            raise ValueError(f"tokens.{side}.elevation_type")
        if token["integrity"] not in {"untrusted", "low", "medium", "high", "system"}:
            raise ValueError(f"tokens.{side}.integrity")
        boolean(token["is_administrator"], f"tokens.{side}.is_administrator")
        integer(token["session_id"], f"tokens.{side}.session_id")
        privileges = token["privileges"]
        if not isinstance(privileges, list):
            raise ValueError(f"tokens.{side}.privileges")
        names = []
        for privilege in privileges:
            entry = strict_object(privilege, {"attributes", "name"}, "privilege")
            if integer(entry["attributes"], "privilege.attributes") < 0:
                raise ValueError("privilege.attributes")
            names.append(text(entry["name"], "privilege.name"))
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError(f"tokens.{side}.privileges ordering")
    if tokens["probe"]["session_id"] != session["current_process_session_id"]:
        raise ValueError("probe token session contradiction")

    registry = strict_object(
        value["registry"],
        {"acl", "exact_access", "key_id", "last_write_unchanged", "location", "view"},
        "registry",
    )
    if registry["key_id"] != expectations["registry_key_id"]:
        raise ValueError("registry.key_id")
    boolean(registry["last_write_unchanged"], "registry.last_write_unchanged")
    if registry["view"] != "32-bit":
        raise ValueError("registry.view")
    exact = strict_object(
        registry["exact_access"],
        {"desired_access", "explorer_token_win32_result", "probe_token_win32_result"},
        "registry.exact_access",
    )
    if integer(exact["desired_access"], "registry.desired_access") != expectations["registry_exact_access_mask"]:
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
    if location["utf16le_bytes"] <= 0 or location["utf16le_bytes"] % 2 != 0:
        raise ValueError("registry.location.bytes")
    if location["value_kind"] not in {"String", "ExpandString"}:
        raise ValueError("registry.location.kind")
    acl = strict_object(registry["acl"], {"aces", "group_sid", "owner_sid"}, "registry.acl")
    text(acl["group_sid"], "registry.acl.group_sid")
    text(acl["owner_sid"], "registry.acl.owner_sid")
    for sid_name in ("group_sid", "owner_sid"):
        if not re.fullmatch(r"S-[0-9]+(?:-[0-9]+)+", acl[sid_name]):
            raise ValueError(f"registry.acl.{sid_name}")
    if not isinstance(acl["aces"], list):
        raise ValueError("registry.acl.aces")
    ace_order = []
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
        if not re.fullmatch(r"S-[0-9]+(?:-[0-9]+)+", entry["identity_sid"]):
            raise ValueError("registry.ace.identity_sid")
        if entry["access_type"] not in {"allow", "deny"}:
            raise ValueError("registry.ace.access_type")
        ace_order.append((entry["identity_sid"], entry["access_mask"]))
    if ace_order != sorted(ace_order):
        raise ValueError("registry.ace ordering")

    inputs = strict_object(value["inputs"], {"clean", "iso"}, "inputs")
    clean = strict_object(inputs["clean"], {"after", "before", "manifest", "unchanged"}, "inputs.clean")
    boolean(clean["unchanged"], "inputs.clean.unchanged")
    manifest = strict_object(clean["manifest"], {"expected_match", "identity"}, "inputs.clean.manifest")
    boolean(manifest["expected_match"], "inputs.clean.manifest.expected_match")
    manifest_identity = identity(manifest["identity"], "inputs.clean.manifest.identity")
    manifest_match = manifest_identity == {
        "byte_count": expectations["clean_manifest_bytes"],
        "sha256": expectations["clean_manifest_sha256"],
    }
    if manifest["expected_match"] != manifest_match:
        raise ValueError("clean manifest expected_match contradiction")

    clean_captures: dict[str, dict[str, object]] = {}
    for side in ("before", "after"):
        capture = strict_object(
            clean[side],
            {"directory_extra_count", "directory_missing_count", "executable", "extra_count", "mismatch_count", "missing_count", "tree", "tree_expected_match", "writable_open_count"},
            f"inputs.clean.{side}",
        )
        for key in ("directory_extra_count", "directory_missing_count", "extra_count", "mismatch_count", "missing_count", "writable_open_count"):
            if integer(capture[key], f"inputs.clean.{side}.{key}") < 0:
                raise ValueError(f"inputs.clean.{side}.{key}")
        boolean(capture["tree_expected_match"], f"inputs.clean.{side}.tree_expected_match")
        executable_wrapper = strict_object(
            capture["executable"], {"expected_match", "identity"}, f"inputs.clean.{side}.executable"
        )
        boolean(executable_wrapper["expected_match"], f"inputs.clean.{side}.executable.expected_match")
        clean_executable = identity(
            executable_wrapper["identity"], f"inputs.clean.{side}.executable.identity"
        )
        expected_executable = {
            "byte_count": expectations["original_executable_bytes"],
            "sha256": expectations["original_executable_sha256"],
        }
        if executable_wrapper["expected_match"] != (clean_executable == expected_executable):
            raise ValueError(f"clean {side} executable contradiction")
        tree_value = tree(capture["tree"], f"inputs.clean.{side}.tree")
        tree_match = (
            tree_value["present"] is True
            and tree_value["file_count"] == expectations["clean_file_count"]
            and tree_value["total_bytes"] == expectations["clean_total_bytes"]
            and capture["missing_count"] == 0
            and capture["extra_count"] == 0
            and capture["mismatch_count"] == 0
            and capture["directory_missing_count"] == 0
            and capture["directory_extra_count"] == 0
            and tree_value["case_collision_count"] == 0
            and tree_value["hardlink_count"] == 0
            and tree_value["object_alias_count"] == 0
            and tree_value["reparse_count"] == 0
            and tree_value["unstable_count"] == 0
            and executable_wrapper["expected_match"] is True
        )
        if capture["tree_expected_match"] != tree_match:
            raise ValueError(f"clean {side} tree contradiction")
        clean_captures[side] = capture
    clean_same = (
        clean_captures["before"]["tree"] == clean_captures["after"]["tree"]
        and clean_captures["before"]["executable"] == clean_captures["after"]["executable"]
    )
    if clean["unchanged"] != clean_same:
        raise ValueError("clean unchanged contradiction")
    iso = strict_object(inputs["iso"], {"file", "optical_media"}, "inputs.iso")
    iso_file = strict_object(iso["file"], {"expected_match", "identity"}, "inputs.iso.file")
    boolean(iso_file["expected_match"], "inputs.iso.file.expected_match")
    iso_identity = identity(iso_file["identity"], "inputs.iso.file.identity")
    iso_match = iso_identity == {
        "byte_count": expectations["iso_bytes"],
        "sha256": expectations["iso_sha256"],
    }
    if iso_file["expected_match"] != iso_match:
        raise ValueError("iso identity contradiction")
    optical = strict_object(
        iso["optical_media"],
        {"drive_type", "executable", "expected_match", "volume_label_matches", "volume_label_sha256"},
        "inputs.iso.optical_media",
    )
    integer(optical["drive_type"], "inputs.iso.optical_media.drive_type")
    optical_executable = identity(optical["executable"], "inputs.iso.optical_media.executable")
    boolean(optical["expected_match"], "inputs.iso.optical_media.expected_match")
    boolean(optical["volume_label_matches"], "inputs.iso.optical_media.volume_label_matches")
    sha256(optical["volume_label_sha256"], "inputs.iso.optical_media.volume_label_sha256")
    label_hash = hashlib.sha256(str(expectations["optical_volume_label"]).encode("utf-16le")).hexdigest()
    label_matches = optical["volume_label_sha256"] == label_hash
    if optical["volume_label_matches"] != label_matches:
        raise ValueError("optical label contradiction")
    optical_match = (
        optical["drive_type"] == 5
        and label_matches
        and optical_executable
        == {
            "byte_count": expectations["optical_executable_bytes"],
            "sha256": expectations["optical_executable_sha256"],
        }
    )
    if optical["expected_match"] != optical_match:
        raise ValueError("optical expected_match contradiction")

    guards = strict_object(
        value["guards"],
        {"cm0102_launched", "game_process_count_after", "game_process_count_before", "installed_tree", "private_inputs_distinct", "virtual_store_tree"},
        "guards",
    )
    boolean(guards["cm0102_launched"], "guards.cm0102_launched")
    boolean(guards["private_inputs_distinct"], "guards.private_inputs_distinct")
    if integer(guards["game_process_count_after"], "guards.game_process_count_after") < 0:
        raise ValueError("guards.game_process_count_after: negative")
    if integer(guards["game_process_count_before"], "guards.game_process_count_before") < 0:
        raise ValueError("guards.game_process_count_before: negative")
    guard_trees = {}
    for name in ("installed_tree", "virtual_store_tree"):
        wrapper = strict_object(guards[name], {"after", "before", "unchanged"}, f"guards.{name}")
        before = tree(wrapper["before"], f"guards.{name}.before")
        after = tree(wrapper["after"], f"guards.{name}.after")
        boolean(wrapper["unchanged"], f"guards.{name}.unchanged")
        same = before == after and before["unstable_count"] == 0 and after["unstable_count"] == 0
        if wrapper["unchanged"] != same:
            raise ValueError(f"guards.{name}.unchanged contradiction")
        guard_trees[name] = wrapper

    capabilities = strict_object(value["capabilities"], {"apis", "tools"}, "capabilities")
    for kind in ("apis", "tools"):
        items = capabilities[kind]
        if not isinstance(items, list):
            raise ValueError(f"capabilities.{kind}")
        ids = []
        for item in items:
            expected = {"id", "present", "required"} if kind == "apis" else {"file", "id", "present", "required"}
            entry = strict_object(item, expected, f"capabilities.{kind}.item")
            ids.append(text(entry["id"], f"capabilities.{kind}.id"))
            boolean(entry["present"], f"capabilities.{kind}.present")
            boolean(entry["required"], f"capabilities.{kind}.required")
            if kind == "tools" and entry["file"] is not None:
                identity(entry["file"], "capabilities.tools.file")
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError(f"capabilities.{kind} ordering")
        expected_ids = REQUIRED_API_IDS if kind == "apis" else REQUIRED_TOOL_IDS
        if set(ids) != expected_ids:
            raise ValueError(f"capabilities.{kind} set")
        configured = set(expectations["required_api_ids" if kind == "apis" else "required_tool_ids"])
        if {item["id"] for item in items if item["required"]} != configured:
            raise ValueError(f"capabilities.{kind} required flags")
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

    installed_before = guard_trees["installed_tree"]["before"]
    installed_after = guard_trees["installed_tree"]["after"]
    virtual_before = guard_trees["virtual_store_tree"]["before"]
    virtual_after = guard_trees["virtual_store_tree"]["after"]
    installed_plain = all(
        item["present"] is True
        and item["reparse_count"] == 0
        and item["case_collision_count"] == 0
        and item["hardlink_count"] == 0
        and item["object_alias_count"] == 0
        and item["unstable_count"] == 0
        for item in (installed_before, installed_after)
    )
    virtual_plain = all(
        item["reparse_count"] == 0
        and item["case_collision_count"] == 0
        and item["hardlink_count"] == 0
        and item["object_alias_count"] == 0
        and item["unstable_count"] == 0
        for item in (virtual_before, virtual_after)
    )
    all_required_capabilities = all(
        entry["present"] is True
        for kind in ("apis", "tools")
        for entry in capabilities[kind]
        if entry["required"]
    )
    predicates = {
        "active-input-desktop": (
            session["active_console_session_id"] == session["explorer_session_id"]
            and session["input_desktop"] == "Default",
            "default" if session["input_desktop"] == "Default" else "not-default",
        ),
        "clean-manifest-identity": (manifest_match, "exact" if manifest_match else "mismatch"),
        "clean-tree-exact": (
            clean_captures["before"]["tree_expected_match"] is True
            and clean_captures["after"]["tree_expected_match"] is True
            and clean["unchanged"] is True,
            "two-captures-exact"
            if clean_captures["before"]["tree_expected_match"] is True
            and clean_captures["after"]["tree_expected_match"] is True
            and clean["unchanged"] is True
            else "mismatch-or-mutation",
        ),
        "clean-tree-read-only": (
            clean_captures["before"]["writable_open_count"] == 0
            and clean_captures["after"]["writable_open_count"] == 0,
            "non-writable"
            if clean_captures["before"]["writable_open_count"] == 0
            and clean_captures["after"]["writable_open_count"] == 0
            else "writable",
        ),
        "explorer-token-medium": (
            tokens["explorer"]["integrity"] == "medium"
            and tokens["explorer"]["is_administrator"] is False
            and tokens["explorer"]["session_id"] == session["active_console_session_id"]
            and tokens["explorer"]["account_sid_sha256"] == tokens["probe"]["account_sid_sha256"],
            "confirmed"
            if tokens["explorer"]["integrity"] == "medium"
            and tokens["explorer"]["is_administrator"] is False
            and tokens["explorer"]["session_id"] == session["active_console_session_id"]
            and tokens["explorer"]["account_sid_sha256"] == tokens["probe"]["account_sid_sha256"]
            else "unexpected-token",
        ),
        "installed-tree-plain": (installed_plain, "plain" if installed_plain else "unsafe-entry"),
        "installed-tree-stable": (guards["installed_tree"]["unchanged"], "unchanged" if guards["installed_tree"]["unchanged"] else "changed"),
        "iso-identity": (iso_match, "exact" if iso_match else "mismatch"),
        "no-game-process-after": (guards["game_process_count_after"] == 0, "absent" if guards["game_process_count_after"] == 0 else "present"),
        "no-game-process-before": (guards["game_process_count_before"] == 0, "absent" if guards["game_process_count_before"] == 0 else "present"),
        "optical-media": (optical_match, "exact" if optical_match else "mismatch"),
        "private-inputs-distinct": (guards["private_inputs_distinct"], "distinct" if guards["private_inputs_distinct"] else "alias-detected"),
        "probe-image-stable": (probe["executable_unchanged"], "unchanged" if probe["executable_unchanged"] else "changed"),
        "probe-process-x86": (probe["process_architecture"] == "x86", probe["process_architecture"]),
        "registry-current-exact-access": (exact["probe_token_win32_result"] == 0, f"win32-{exact['probe_token_win32_result']}"),
        "registry-explorer-exact-denial": (exact["explorer_token_win32_result"] == 5, f"win32-{exact['explorer_token_win32_result']}"),
        "registry-location-binding": (location["equals_configured_install_root"], "matches" if location["equals_configured_install_root"] else "mismatch"),
        "registry-read-only": (registry["last_write_unchanged"], "unchanged" if registry["last_write_unchanged"] else "changed"),
        "required-host-tools": (all_required_capabilities, "available" if all_required_capabilities else "missing"),
        "virtual-store-plain": (virtual_plain, "plain-or-absent" if virtual_plain else "unsafe-entry"),
        "virtual-store-stable": (guards["virtual_store_tree"]["unchanged"], "unchanged" if guards["virtual_store_tree"]["unchanged"] else "changed"),
        "wsl-token-high-hazard": (
            tokens["probe"]["integrity"] == "high" and tokens["probe"]["is_administrator"] is True,
            "confirmed" if tokens["probe"]["integrity"] == "high" and tokens["probe"]["is_administrator"] is True else "unexpected-token",
        ),
    }
    if set(predicates) != REQUIRED_CHECK_IDS:
        raise AssertionError("semantic predicate coverage")
    if guards["cm0102_launched"] is not False:
        raise ValueError("game launch guard")
    if tokens["impersonation_restored"] is not True:
        raise ValueError("impersonation restoration")
    return predicates


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


PRIVATE_LOCATOR_KEYS = {
    "clean_manifest",
    "clean_tree",
    "installed_tree",
    "iso_file",
    "optical_root",
    "schema_version",
    "virtual_store_tree",
}


def parse_private_locator(raw: bytes) -> dict[str, object]:
    if len(raw) > 1024 * 1024 or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("private locator framing")
    value = strict_object(decode_json(raw), PRIVATE_LOCATOR_KEYS, "private locator")
    if value["schema_version"] != 1:
        raise ValueError("private locator schema")
    for key in PRIVATE_LOCATOR_KEYS - {"schema_version"}:
        item = value[key]
        if not isinstance(item, str) or not re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", item):
            raise ValueError(f"private locator {key}")
    return value


def load_private_locator(config_path: pathlib.Path) -> tuple[dict[str, object], bytes]:
    raw = read_bounded_plain(config_path, 1024 * 1024)
    return parse_private_locator(raw), raw


def private_strings_from_value(value: dict[str, object]) -> list[str]:
    result: list[str] = []
    for item in value.values():
        if isinstance(item, str) and len(item) >= 3:
            result.extend((item, item.replace("\\", "/"), item.replace("/", "\\")))
    return result


def private_strings(config_path: pathlib.Path) -> list[str]:
    value, _raw = load_private_locator(config_path)
    return private_strings_from_value(value)


def reject_path_like_strings(value: object) -> None:
    path_pattern = re.compile(
        r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'])(?:/mnt/|/home/|/root/|/tmp/|/var/tmp/))",
        re.IGNORECASE,
    )
    for string_value in iter_strings(value):
        if path_pattern.search(string_value):
            raise ValueError("path-like string present")


def verify_bytes(raw: bytes, private_raw: bytes, expectations_raw: bytes) -> None:
    if len(raw) > 4 * 1024 * 1024 or not raw.endswith(b"\n") or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("output framing")
    value = decode_json(raw)
    strict_object(value, TOP_LEVEL, "top-level")
    private_locator = parse_private_locator(private_raw)
    expectations = parse_expectations(expectations_raw)
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
    completeness = summary["completeness"]
    if completeness == "complete":
        if set(ids) != REQUIRED_CHECK_IDS:
            raise ValueError("required check set")
        predicates = validate_full_schema(value, expectations, expectations_raw)
        check_by_id = {item["id"]: item for item in checks}
        for check_id, (passed, detail) in predicates.items():
            check = check_by_id[check_id]
            if check["outcome"] != ("pass" if passed else "fail") or check["detail_code"] != detail:
                raise ValueError(f"semantic check contradiction: {check_id}")
        if value["probe"]["private_locator_sha256"] != hashlib.sha256(private_raw).hexdigest():
            raise ValueError("probe private locator identity")
        expected_verdict = "eligible-for-synthetic-launcher-test" if all(result[0] for result in predicates.values()) else "unsafe"
        if summary["safety_verdict"] != expected_verdict or counts["error"] != 0 or value["errors"] != []:
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
        detail = validate_minimal_detail(error["detail_code"])
        if detail != checks[0]["detail_code"]:
            raise ValueError("minimal detail contradiction")
        exact_minimal = {
            "capabilities": {},
            "guards": {"cm0102_launched": False},
            "host": {},
            "inputs": {},
            "probe": {},
            "registry": {},
            "run": {},
            "session": {},
            "tokens": {},
        }
        for key, expected in exact_minimal.items():
            if value[key] != expected:
                raise ValueError(f"minimal {key} shape")
    else:
        raise ValueError("completeness")
    if raw != canonical(value):
        raise ValueError("non-canonical JSON")
    reject_path_like_strings(value)
    forbidden = []
    for item in private_locator.values():
        if isinstance(item, str) and len(item) >= 3:
            forbidden.extend((item, item.replace("\\", "/"), item.replace("/", "\\")))
    for string_value in iter_strings(value):
        lowered = string_value.casefold()
        if any(item.casefold() in lowered for item in forbidden):
            raise ValueError("private string present")


def verify(
    path: pathlib.Path, forbid_file: pathlib.Path, expectations_path: pathlib.Path
) -> None:
    raw = read_bounded_plain(path, 4 * 1024 * 1024)
    private_raw = read_bounded_plain(forbid_file, 1024 * 1024)
    expectations_raw = read_bounded_plain(expectations_path, 1024 * 1024)
    verify_bytes(raw, private_raw, expectations_raw)


def static_source(paths: list[pathlib.Path]) -> None:
    for path in paths:
        source = read_bounded_plain(path, 4 * 1024 * 1024).decode("utf-8", "strict")
        if path.name == "OriginalHostQualification.cs":
            stage_constants = re.findall(
                r'internal const string Csv = "([a-z0-9,-]+)";', source
            )
            if stage_constants != [DIAGNOSTIC_STAGE_CSV]:
                raise ValueError(f"{path.name}: diagnostic-stage parity")
        without_comments = re.sub(r"/\*.*?\*/|//[^\r\n]*", "", source, flags=re.DOTALL)
        normalized = re.sub(r"\s+", "", without_comments).casefold()
        for pattern, label in BANNED_NORMALIZED_PATTERNS:
            if re.search(pattern, normalized):
                raise ValueError(f"{path.name}: banned {label}")
        if re.search(r"dllimport\(\"(?:shell32|winexec)", normalized):
            raise ValueError(f"{path.name}: banned launch library")
        for constructor in re.findall(r"newfilestream\(([^;]*)\)", normalized):
            if "fileaccess.read," not in constructor:
                raise ValueError(f"{path.name}: non-read-only FileStream")
        declarations = re.findall(
            r"\[\s*(?:System\.Runtime\.InteropServices\.)?dllimport\s*\(\s*\"([^\"]+)\"[^)]*\)\s*\]"
            r"\s*[^;{}]*?\bextern\s+[^\s]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            source,
            re.IGNORECASE,
        )
        attribute_count = len(
            re.findall(
                r"\[\s*(?:System\.Runtime\.InteropServices\.)?DllImport\b",
                source,
                re.IGNORECASE,
            )
        )
        extern_count = len(re.findall(r"\bextern\b", source, re.IGNORECASE))
        if "libraryimport" in normalized or "dllimportattribute" in normalized:
            raise ValueError(f"{path.name}: unapproved interop attribute")
        if re.search(r"\bentrypoint=", normalized):
            raise ValueError(f"{path.name}: DllImport EntryPoint is forbidden")
        if len(declarations) != attribute_count or len(declarations) != extern_count:
            raise ValueError(f"{path.name}: unparsed DllImport declaration")
        for library, method in declarations:
            pair = (library.casefold(), method)
            if pair not in ALLOWED_PINVOKES:
                raise ValueError(f"{path.name}: unapproved P/Invoke")


def expect_rejected(action, name: str) -> None:
    try:
        action()
    except (ValueError, OSError):
        return
    raise AssertionError(name)


def synthetic_full_document(
    expectations: dict[str, object], expectations_raw: bytes, private_raw: bytes
) -> dict[str, object]:
    present_tree = {
        "case_collision_count": 0,
        "directory_count": 1,
        "file_count": expectations["clean_file_count"],
        "hardlink_count": 0,
        "object_alias_count": 0,
        "present": True,
        "reparse_count": 0,
        "root_object_id_sha256": "d" * 64,
        "total_bytes": expectations["clean_total_bytes"],
        "tree_sha256": "a" * 64,
        "unstable_count": 0,
    }
    absent_tree = {
        "case_collision_count": 0,
        "directory_count": 0,
        "file_count": 0,
        "hardlink_count": 0,
        "object_alias_count": 0,
        "present": False,
        "reparse_count": 0,
        "root_object_id_sha256": hashlib.sha256("absent".encode("utf-16le")).hexdigest(),
        "total_bytes": 0,
        "tree_sha256": hashlib.sha256(b"").hexdigest(),
        "unstable_count": 0,
    }
    expected_executable = {
        "byte_count": expectations["original_executable_bytes"],
        "sha256": expectations["original_executable_sha256"],
    }
    clean_capture = {
        "directory_extra_count": 0,
        "directory_missing_count": 0,
        "executable": {"expected_match": True, "identity": expected_executable},
        "extra_count": 0,
        "mismatch_count": 0,
        "missing_count": 0,
        "tree": present_tree,
        "tree_expected_match": True,
        "writable_open_count": 0,
    }
    details = {
        "active-input-desktop": "default",
        "clean-manifest-identity": "exact",
        "clean-tree-exact": "two-captures-exact",
        "clean-tree-read-only": "non-writable",
        "explorer-token-medium": "confirmed",
        "installed-tree-plain": "plain",
        "installed-tree-stable": "unchanged",
        "iso-identity": "exact",
        "no-game-process-after": "absent",
        "no-game-process-before": "absent",
        "optical-media": "exact",
        "private-inputs-distinct": "distinct",
        "probe-image-stable": "unchanged",
        "probe-process-x86": "x86",
        "registry-current-exact-access": "win32-0",
        "registry-explorer-exact-denial": "win32-5",
        "registry-location-binding": "matches",
        "registry-read-only": "unchanged",
        "required-host-tools": "available",
        "virtual-store-plain": "plain-or-absent",
        "virtual-store-stable": "unchanged",
        "wsl-token-high-hazard": "confirmed",
    }
    checks = [
        {"detail_code": details[check_id], "id": check_id, "outcome": "pass", "required": True}
        for check_id in sorted(REQUIRED_CHECK_IDS)
    ]
    api_required = set(expectations["required_api_ids"])
    tool_required = set(expectations["required_tool_ids"])
    capabilities = {
        "apis": [
            {"id": item, "present": True, "required": item in api_required}
            for item in sorted(REQUIRED_API_IDS)
        ],
        "tools": [
            {
                "file": {"byte_count": 1, "sha256": "b" * 64}
                if item in tool_required
                else None,
                "id": item,
                "present": item in tool_required,
                "required": item in tool_required,
            }
            for item in sorted(REQUIRED_TOOL_IDS)
        ],
    }
    token_common = {
        "account_sid_sha256": "8" * 64,
        "elevation_type": "full",
        "integrity": "high",
        "is_administrator": True,
        "privileges": [],
        "session_id": 2,
    }
    explorer = dict(token_common)
    explorer.update({"elevation_type": "limited", "integrity": "medium", "is_administrator": False})
    return {
        "capabilities": capabilities,
        "checks": checks,
        "errors": [],
        "guards": {
            "cm0102_launched": False,
            "game_process_count_after": 0,
            "game_process_count_before": 0,
            "installed_tree": {"after": present_tree, "before": present_tree, "unchanged": True},
            "private_inputs_distinct": True,
            "virtual_store_tree": {"after": absent_tree, "before": absent_tree, "unchanged": True},
        },
        "host": {
            "architecture": "x86-64",
            "display_version": "self-test",
            "edition": "self-test",
            "locale": "en-GB",
            "machine_fingerprint_sha256": "7" * 64,
            "os_build": 1,
            "os_major": 10,
            "os_minor": 0,
            "product_name": "Windows",
            "time_zone": "UTC",
        },
        "inputs": {
            "clean": {
                "after": clean_capture,
                "before": clean_capture,
                "manifest": {
                    "expected_match": True,
                    "identity": {
                        "byte_count": expectations["clean_manifest_bytes"],
                        "sha256": expectations["clean_manifest_sha256"],
                    },
                },
                "unchanged": True,
            },
            "iso": {
                "file": {
                    "expected_match": True,
                    "identity": {"byte_count": expectations["iso_bytes"], "sha256": expectations["iso_sha256"]},
                },
                "optical_media": {
                    "drive_type": 5,
                    "executable": {
                        "byte_count": expectations["optical_executable_bytes"],
                        "sha256": expectations["optical_executable_sha256"],
                    },
                    "expected_match": True,
                    "volume_label_matches": True,
                    "volume_label_sha256": hashlib.sha256(
                        str(expectations["optical_volume_label"]).encode("utf-16le")
                    ).hexdigest(),
                },
            },
        },
        "probe": {
            "executable": {"byte_count": 100, "sha256": "9" * 64},
            "executable_after": {"byte_count": 100, "sha256": "9" * 64},
            "executable_unchanged": True,
            "expectations_sha256": hashlib.sha256(expectations_raw).hexdigest(),
            "id": "cm0102-original-host-qualification",
            "private_locator_sha256": hashlib.sha256(private_raw).hexdigest(),
            "process_architecture": "x86",
            "source_revision": "6" * 40,
            "version": "1.1.0",
        },
        "registry": {
            "acl": {"aces": [], "group_sid": "S-1-5-18", "owner_sid": "S-1-5-18"},
            "exact_access": {
                "desired_access": expectations["registry_exact_access_mask"],
                "explorer_token_win32_result": 5,
                "probe_token_win32_result": 0,
            },
            "key_id": expectations["registry_key_id"],
            "last_write_unchanged": True,
            "location": {
                "equals_configured_install_root": True,
                "sha256_utf16le": "c" * 64,
                "utf16le_bytes": 20,
                "value_kind": "String",
            },
            "view": "32-bit",
        },
        "run": {"elapsed_ms": 1, "observed_at_utc": "2026-01-01T00:00:00.0000000Z"},
        "schema_version": 1,
        "session": {
            "active_console_session_id": 2,
            "bits_per_pixel": 32,
            "current_process_session_id": 2,
            "explorer_process_count": 1,
            "explorer_session_id": 2,
            "input_desktop": "Default",
            "screen_height": 1080,
            "screen_width": 1920,
            "window_station": "WinSta0",
        },
        "summary": {
            "comparison_verdict": "not-run",
            "completeness": "complete",
            "direct_wsl_launch_safe": False,
            "error_count": 0,
            "failed_count": 0,
            "original_execution_status": "not-run",
            "passed_count": len(checks),
            "required_check_count": len(checks),
            "safety_verdict": "eligible-for-synthetic-launcher-test",
        },
        "tokens": {"explorer": explorer, "impersonation_restored": True, "probe": token_common},
    }


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
        oversized = root / "oversized.bin"
        with oversized.open("wb") as output:
            output.truncate(4 * 1024 * 1024 + 1)
        expect_rejected(
            lambda: read_bounded_plain(oversized, 4 * 1024 * 1024),
            "pre-read byte limit",
        )
        plain = root / "plain.bin"
        plain.write_bytes(b"plain")
        plain_link = root / "plain-link.bin"
        plain_link.symlink_to(plain)
        expect_rejected(
            lambda: read_bounded_plain(plain_link, 1024),
            "bounded input symlink",
        )
        private = root / "private.json"
        private_value = {
            "clean_manifest": r"C:\private\clean.tsv",
            "clean_tree": r"C:\private\clean",
            "installed_tree": r"C:\private\installed",
            "iso_file": r"C:\private\disc.iso",
            "optical_root": "D:\\",
            "schema_version": 1,
            "virtual_store_tree": r"C:\private\virtual",
        }
        private.write_bytes(canonical(private_value))
        if r"C:\private\clean" not in private_strings(private):
            raise AssertionError("redaction self-test")
        expectations_value = {
            "clean_file_count": 1,
            "clean_manifest_bytes": 10,
            "clean_manifest_sha256": "1" * 64,
            "clean_total_bytes": 20,
            "compiler_bytes": 60,
            "compiler_sha256": "2" * 64,
            "compiler_ui_bytes": 61,
            "compiler_ui_sha256": "6" * 64,
            "iso_bytes": 30,
            "iso_sha256": "3" * 64,
            "optical_executable_bytes": 50,
            "optical_executable_sha256": "5" * 64,
            "optical_volume_label": "CM0102",
            "original_executable_bytes": 40,
            "original_executable_sha256": "4" * 64,
            "profile_id": "self-test",
            "registry_exact_access_mask": 0x000F003F,
            "registry_key_id": "cm0102-install-location",
            "registry_subkey": "Software\\Vendor\\Product",
            "registry_value_name": "Location",
            "required_api_ids": sorted(REQUIRED_API_IDS),
            "required_tool_ids": ["csc-x86", "powershell", "python313"],
            "schema_version": 1,
        }
        expectations = root / "expectations.json"
        expectations.write_bytes(canonical(expectations_value))
        full = synthetic_full_document(
            expectations_value, expectations.read_bytes(), private.read_bytes()
        )
        full_output = root / "full-output.json"
        full_output.write_bytes(canonical(full))
        verify(full_output, private, expectations)
        for check_id in sorted(REQUIRED_CHECK_IDS):
            contradiction = decode_json(canonical(full))
            changed = next(
                item for item in contradiction["checks"] if item["id"] == check_id
            )
            changed["outcome"] = "fail"
            contradiction["summary"]["passed_count"] -= 1
            contradiction["summary"]["failed_count"] += 1
            contradiction["summary"]["safety_verdict"] = "unsafe"
            full_output.write_bytes(canonical(contradiction))
            expect_rejected(
                lambda: verify(full_output, private, expectations),
                f"semantic contradiction {check_id}",
            )
        leaked = decode_json(canonical(full))
        leaked["host"]["product_name"] = private_value["installed_tree"]
        full_output.write_bytes(canonical(leaked))
        expect_rejected(
            lambda: verify(full_output, private, expectations), "full privacy leak"
        )
        unsafe_hidden = decode_json(canonical(full))
        unsafe_hidden["guards"]["game_process_count_after"] = 1
        full_output.write_bytes(canonical(unsafe_hidden))
        expect_rejected(
            lambda: verify(full_output, private, expectations), "hidden unsafe observation"
        )
        alias_hidden = decode_json(canonical(full))
        alias_hidden["guards"]["installed_tree"]["before"]["object_alias_count"] = 1
        alias_hidden["guards"]["installed_tree"]["after"]["object_alias_count"] = 1
        full_output.write_bytes(canonical(alias_hidden))
        expect_rejected(
            lambda: verify(full_output, private, expectations), "hidden object alias"
        )
        hardlink_hidden = decode_json(canonical(full))
        hardlink_hidden["guards"]["installed_tree"]["before"]["hardlink_count"] = 1
        hardlink_hidden["guards"]["installed_tree"]["after"]["hardlink_count"] = 1
        full_output.write_bytes(canonical(hardlink_hidden))
        expect_rejected(
            lambda: verify(full_output, private, expectations), "hidden hardlink"
        )
        directory_hidden = decode_json(canonical(full))
        directory_hidden["inputs"]["clean"]["before"]["directory_extra_count"] = 1
        full_output.write_bytes(canonical(directory_hidden))
        expect_rejected(
            lambda: verify(full_output, private, expectations), "hidden directory mismatch"
        )
        staged_detail = "unhandled-v1-host-observation-exception-80131501"
        check = {
            "detail_code": staged_detail,
            "id": "probe",
            "outcome": "error",
            "required": True,
        }
        document = {
            "capabilities": {},
            "checks": [check],
            "errors": [
                {"category": "probe", "check_id": "probe", "detail_code": staged_detail}
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
        verify(output, private, expectations)
        for stage in DIAGNOSTIC_STAGE_IDS:
            validate_minimal_detail(f"unhandled-v1-{stage}-exception-80131501")
        validate_minimal_detail("unhandled-exception-80131501")
        for malformed in (
            "unhandled-v1-unknown-stage-exception-80131501",
            "unhandled-v1-host-observation-SystemException",
            r"unhandled-v1-C:\\private-exception-80131501",
            "unhandled-v1-HOST-OBSERVATION-exception-80131501",
            "unhandled-v1-host-observation-exception-8013150",
        ):
            expect_rejected(
                lambda malformed=malformed: validate_minimal_detail(malformed),
                "minimal diagnostic detail",
            )
        document["checks"][0]["detail_code"] = "unhandled-v1-unknown-stage-exception-80131501"
        document["errors"][0]["detail_code"] = "unhandled-v1-unknown-stage-exception-80131501"
        output.write_bytes(canonical(document))
        expect_rejected(lambda: verify(output, private, expectations), "unknown diagnostic stage")
        document["checks"][0]["detail_code"] = staged_detail
        document["errors"][0]["detail_code"] = staged_detail
        output.write_bytes(b'{"schema_version":1,"schema_version":1}\n')
        expect_rejected(lambda: verify(output, private, expectations), "duplicate-key self-test")
        document["guards"]["cm0102_launched"] = True
        output.write_bytes(canonical(document))
        expect_rejected(lambda: verify(output, private, expectations), "minimal shape self-test")
        document["guards"]["cm0102_launched"] = False
        document["host"] = {"leak": r"C:\private\clean"}
        output.write_bytes(canonical(document))
        expect_rejected(lambda: verify(output, private, expectations), "privacy self-test")

        static_good = root / "good.cs"
        static_good.write_text("class X { void Observe() { File.OpenRead(\"x\"); } }", encoding="utf-8")
        static_source([static_good])
        banned_samples = (
            "p . StArT ( );",
            "p./* disguise */Start();",
            "Create ProcessW (x);".replace(" ", ""),
            "Shell Execute ExW (x);".replace(" ", ""),
            "WIN EXEC (x);".replace(" ", ""),
            "Reg Set Value ExW (x);".replace(" ", ""),
            "key . Create Sub Key (x);".replace(" ", ""),
            "File . Write All Bytes (x,y);".replace(" ", ""),
            "Directory . Create Directory (x);".replace(" ", ""),
            "new FileStream(x, FileMode . Open Or Create);".replace(" ", ""),
            "new FileStream(x, FileMode.Open, File Access . Read Write);".replace(" ", ""),
            "new FileStream(x, FileMode.Open);",
            '[DllImport("kernel32.dll")] static extern int Beep(int a, int b);',
            '[DllImport("kernel32.dll", Entry /* disguise */ Point = "WinExec")] static extern int GetCurrentProcess();',
        )
        for index, source in enumerate(banned_samples):
            banned = root / f"banned-{index}.cs"
            banned.write_text(source, encoding="utf-8")
            expect_rejected(lambda banned=banned: static_source([banned]), f"static negative {index}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    static = sub.add_parser("static-source")
    static.add_argument("paths", nargs="+", type=pathlib.Path)
    output = sub.add_parser("verify")
    output.add_argument("path", type=pathlib.Path)
    output.add_argument("--forbid-file", required=True, type=pathlib.Path)
    output.add_argument("--expectations", required=True, type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
    elif args.command == "static-source":
        static_source(args.paths)
    else:
        verify(args.path, args.forbid_file, args.expectations)
    print("PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, AssertionError, json.JSONDecodeError) as error:
        print(f"FAIL: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
