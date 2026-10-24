#!/usr/bin/env python3
"""Compare two retained host-qualification attempts without hiding build drift."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import stat
import struct
import sys
import tempfile

import verify_output


SCHEMA_VERSION = 1
COMPARATOR_ID = "cm0102-original-host-qualification-stability"
COMPARATOR_VERSION = "1.0.0"
PROFILE_ID = "cm0102-original-host-qualification-stability-5e6dc7d-v1"
SOURCE_REVISION = "5e6dc7ddd2fe60a4270089c3a1c686c2f90244a1"
HARNESS_ID = "cm0102-original-host-retained-run"
HARNESS_VERSION = "1.1.0"
PROBE_ID = "cm0102-original-host-qualification"
PROBE_VERSION = "1.1.0"
STREAM_CAP_BYTES = 4 * 1024 * 1024
TIMEOUT_SECONDS = 30 * 60
EMPTY_IDENTITY = {
    "byte_count": 0,
    "sha256": hashlib.sha256(b"").hexdigest(),
}
ALLOWED_REPORT_DIFFERENCES = (
    "/probe/executable/sha256",
    "/probe/executable_after/sha256",
    "/run/elapsed_ms",
    "/run/observed_at_utc",
)
BUILD_ROLES = (
    "compiler",
    "nologo",
    "no-default-response-file",
    "warnings-as-errors",
    "optimize",
    "platform-x86",
    "target-exe",
    "reference-system",
    "reference-system-core",
    "reference-system-drawing",
    "reference-system-security",
    "reference-system-web-extensions",
    "reference-system-windows-forms",
    "output-probe",
    "source-canonical-json",
    "source-original-host-qualification",
)
PROBE_ROLES = (
    "probe",
    "expectations-option",
    "expectations",
    "private-config-option",
    "private-locator",
    "source-revision-option",
    "source-revision",
)
BOUND_SOURCES = (
    (
        "CanonicalJson.cs",
        {
            "byte_count": 4499,
            "sha256": "99dd5a2a49802c75297c71be5d15b75a152dec46af9c23072fe4217e7ab16669",
        },
    ),
    (
        "OriginalHostQualification.cs",
        {
            "byte_count": 122500,
            "sha256": "176276570d48a8eb21b067e72d0f47345bab16a8dcba235bbf6a8c4ae89cd6ae",
        },
    ),
    (
        "verify_output.py",
        {
            "byte_count": 69268,
            "sha256": "36d52b8b7cee6949fe4c7fbbac709178c1eefbbc9cc8396cf16c1a0f0be3b211",
        },
    ),
    (
        "retained_run_v1.py",
        {
            "byte_count": 57468,
            "sha256": "9c72a29ffb197af53fb617d13d3c133e43a1bce2ad92b63cf64ab6425dd32918",
        },
    ),
)


class ComparisonError(Exception):
    pass


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def identity(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def strict_object(value: object, keys: set[str], name: str) -> dict[str, object]:
    return verify_output.strict_object(value, keys, name)


def identity_value(value: object, name: str) -> dict[str, object]:
    return verify_output.identity(value, name)


def integer(value: object, name: str) -> int:
    return verify_output.integer(value, name)


def text(value: object, name: str) -> str:
    return verify_output.text(value, name)


def read_plain(path: pathlib.Path, maximum: int = STREAM_CAP_BYTES) -> bytes:
    return verify_output.read_bounded_plain(path, maximum)


def ensure_retained_root(path: pathlib.Path) -> pathlib.Path:
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not stat.S_ISDIR(before.st_mode):
        raise ComparisonError("retained root is not a plain directory")
    resolved = path.resolve(strict=True)
    after = resolved.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise ComparisonError("retained root changed during resolution")
    return resolved


def read_artifact(root: pathlib.Path, relative: str, maximum: int = STREAM_CAP_BYTES) -> bytes:
    candidate = root / pathlib.PurePosixPath(relative)
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ComparisonError("retained artifact escaped root") from error
    if resolved != candidate:
        raise ComparisonError("retained artifact is an alias")
    return read_plain(candidate, maximum)


def parse_command(value: object, expected_roles: tuple[str, ...], name: str) -> dict[str, object]:
    command = strict_object(value, {"argument_count", "argv_roles", "sha256"}, name)
    if integer(command["argument_count"], name + ".argument_count") != len(expected_roles):
        raise ComparisonError(name + " argument count")
    if command["argv_roles"] != list(expected_roles):
        raise ComparisonError(name + " roles")
    verify_output.sha256(command["sha256"], name + ".sha256")
    return command


def parse_sources(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) != len(BOUND_SOURCES):
        raise ComparisonError("manifest sources")
    result: list[dict[str, object]] = []
    for item, expected in zip(value, BOUND_SOURCES):
        source = strict_object(item, {"id", "identity"}, "manifest source")
        if source["id"] != expected[0]:
            raise ComparisonError("manifest source order")
        observed = identity_value(source["identity"], "manifest source identity")
        if observed != expected[1]:
            raise ComparisonError("manifest source profile identity")
        result.append(source)
    return result


def parse_manifest(raw: bytes) -> dict[str, object]:
    if len(raw) > STREAM_CAP_BYTES or not raw.endswith(b"\n") or raw.startswith(b"\xef\xbb\xbf"):
        raise ComparisonError("manifest framing")
    value = verify_output.decode_json(raw)
    if raw != canonical(value):
        raise ComparisonError("manifest is not canonical")
    manifest = strict_object(
        value,
        {
            "bindings",
            "execution",
            "harness",
            "retained_artifacts",
            "schema_version",
            "verification",
        },
        "manifest",
    )
    if integer(manifest["schema_version"], "manifest schema_version") != SCHEMA_VERSION:
        raise ComparisonError("manifest schema")
    harness = strict_object(manifest["harness"], {"id", "version"}, "manifest harness")
    text(harness["id"], "manifest harness id")
    text(harness["version"], "manifest harness version")
    if harness != {"id": HARNESS_ID, "version": HARNESS_VERSION}:
        raise ComparisonError("manifest harness")
    if manifest["retained_artifacts"] != {"canonical_stdout": "probe-output.json"}:
        raise ComparisonError("manifest retained artifacts")
    verification = strict_object(
        manifest["verification"],
        {
            "canonical_stdout",
            "completeness",
            "privacy_locator_enforced",
            "qualification_eligible",
            "result",
            "safety_verdict",
        },
        "manifest verification",
    )
    for key in ("canonical_stdout", "privacy_locator_enforced", "qualification_eligible"):
        verify_output.boolean(verification[key], "manifest verification " + key)
    for key in ("completeness", "result", "safety_verdict"):
        text(verification[key], "manifest verification " + key)
    if verification != {
        "canonical_stdout": True,
        "completeness": "complete",
        "privacy_locator_enforced": True,
        "qualification_eligible": True,
        "result": "pass",
        "safety_verdict": "eligible-for-synthetic-launcher-test",
    }:
        raise ComparisonError("manifest is not eligible")
    bindings = strict_object(
        manifest["bindings"],
        {
            "build_command",
            "compiler",
            "compiler_ui",
            "expectations",
            "private_locator",
            "probe_command",
            "probe_executable",
            "source_commit",
            "sources",
        },
        "manifest bindings",
    )
    parse_command(bindings["build_command"], BUILD_ROLES, "build command")
    parse_command(bindings["probe_command"], PROBE_ROLES, "probe command")
    for key in ("compiler", "compiler_ui", "expectations", "private_locator", "probe_executable"):
        identity_value(bindings[key], "manifest " + key)
    if text(bindings["source_commit"], "manifest source commit") != SOURCE_REVISION:
        raise ComparisonError("manifest source commit")
    parse_sources(bindings["sources"])
    execution = strict_object(
        manifest["execution"],
        {
            "build_exit_code",
            "build_stderr",
            "build_stdout",
            "probe_exit_code",
            "probe_stderr",
            "probe_stdout",
            "stream_cap_bytes",
            "timeout_seconds",
        },
        "manifest execution",
    )
    build_exit = integer(execution["build_exit_code"], "manifest build exit")
    probe_exit = integer(execution["probe_exit_code"], "manifest probe exit")
    stream_cap = integer(execution["stream_cap_bytes"], "manifest stream cap")
    timeout = integer(execution["timeout_seconds"], "manifest timeout")
    if build_exit != 0 or probe_exit != 0:
        raise ComparisonError("manifest execution exit")
    if stream_cap != STREAM_CAP_BYTES or timeout != TIMEOUT_SECONDS:
        raise ComparisonError("manifest execution limits")
    for key in ("build_stderr", "build_stdout", "probe_stderr", "probe_stdout"):
        identity_value(execution[key], "manifest " + key)
    if execution["build_stderr"] != EMPTY_IDENTITY or execution["build_stdout"] != EMPTY_IDENTITY or execution["probe_stderr"] != EMPTY_IDENTITY:
        raise ComparisonError("manifest nonempty successful stream")
    verify_output.reject_path_like_strings(manifest)
    return manifest


def u16(raw: bytes, offset: int, limit: int | None = None) -> int:
    maximum = len(raw) if limit is None else min(limit, len(raw))
    if offset < 0 or offset + 2 > maximum:
        raise ComparisonError("truncated PE field")
    return struct.unpack_from("<H", raw, offset)[0]


def u32(raw: bytes, offset: int, limit: int | None = None) -> int:
    maximum = len(raw) if limit is None else min(limit, len(raw))
    if offset < 0 or offset + 4 > maximum:
        raise ComparisonError("truncated PE field")
    return struct.unpack_from("<I", raw, offset)[0]


def u64(raw: bytes, offset: int, limit: int | None = None) -> int:
    maximum = len(raw) if limit is None else min(limit, len(raw))
    if offset < 0 or offset + 8 > maximum:
        raise ComparisonError("truncated PE field")
    return struct.unpack_from("<Q", raw, offset)[0]


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_pe_build_identity(raw: bytes) -> dict[str, object]:
    if len(raw) < 0x40 or raw[:2] != b"MZ":
        raise ComparisonError("not an MZ image")
    pe = u32(raw, 0x3C)
    if pe < 0x40 or pe + 24 > len(raw) or raw[pe : pe + 4] != b"PE\0\0":
        raise ComparisonError("invalid PE header")
    coff = pe + 4
    if u16(raw, coff) != 0x14C:
        raise ComparisonError("PE is not i386")
    section_count = u16(raw, coff + 2)
    optional_size = u16(raw, coff + 16)
    if section_count < 1 or section_count > 96:
        raise ComparisonError("invalid PE section count")
    optional = coff + 20
    section_table = optional + optional_size
    if optional_size < 96 + 15 * 8 or section_table + section_count * 40 > len(raw):
        raise ComparisonError("truncated PE optional header")
    if u16(raw, optional) != 0x10B:
        raise ComparisonError("PE is not PE32")
    directory_count = u32(raw, optional + 92, section_table)
    if directory_count < 15 or 96 + directory_count * 8 > optional_size:
        raise ComparisonError("missing CLI data directory")
    cli_rva = u32(raw, optional + 96 + 14 * 8, section_table)
    cli_size = u32(raw, optional + 96 + 14 * 8 + 4, section_table)
    if cli_rva == 0 or cli_size < 0x48:
        raise ComparisonError("missing CLI header")
    sections: list[tuple[int, int, int]] = []
    for index in range(section_count):
        header = section_table + index * 40
        virtual_address = u32(raw, header + 12)
        raw_size = u32(raw, header + 16)
        raw_offset = u32(raw, header + 20)
        if raw_size and (raw_offset > len(raw) or raw_size > len(raw) - raw_offset):
            raise ComparisonError("section outside image")
        sections.append((virtual_address, raw_size, raw_offset))

    def rva_to_offset(rva: int, size: int) -> int:
        matches = []
        for virtual_address, raw_size, raw_offset in sections:
            if rva >= virtual_address and size <= raw_size and rva - virtual_address <= raw_size - size:
                matches.append(raw_offset + (rva - virtual_address))
        if len(matches) != 1:
            raise ComparisonError("ambiguous or unmapped RVA")
        if matches[0] > len(raw) or size > len(raw) - matches[0]:
            raise ComparisonError("RVA outside image")
        return matches[0]

    cli = rva_to_offset(cli_rva, cli_size)
    cli_header_size = u32(raw, cli)
    if cli_header_size < 0x48 or cli_header_size > cli_size:
        raise ComparisonError("invalid CLI header size")
    metadata_rva = u32(raw, cli + 8, cli + cli_header_size)
    metadata_size = u32(raw, cli + 12, cli + cli_header_size)
    if metadata_rva == 0 or metadata_size < 20:
        raise ComparisonError("missing CLI metadata")
    metadata = rva_to_offset(metadata_rva, metadata_size)
    metadata_end = metadata + metadata_size
    if u32(raw, metadata, metadata_end) != 0x424A5342:
        raise ComparisonError("invalid CLI metadata signature")
    version_size = u32(raw, metadata + 12, metadata_end)
    cursor = align4(metadata + 16 + version_size)
    if cursor + 4 > metadata_end:
        raise ComparisonError("truncated CLI stream header")
    stream_count = u16(raw, cursor + 2, metadata_end)
    if stream_count < 1 or stream_count > 32:
        raise ComparisonError("invalid CLI stream count")
    cursor += 4
    streams: dict[str, tuple[int, int]] = {}
    for _index in range(stream_count):
        relative = u32(raw, cursor, metadata_end)
        size = u32(raw, cursor + 4, metadata_end)
        name_start = cursor + 8
        name_end = raw.find(b"\0", name_start, min(metadata_end, name_start + 32))
        if name_end < 0:
            raise ComparisonError("unterminated CLI stream name")
        try:
            name = raw[name_start:name_end].decode("ascii", "strict")
        except UnicodeDecodeError as error:
            raise ComparisonError("non-ASCII CLI stream name") from error
        cursor = align4(name_end + 1)
        if cursor > metadata_end or relative > metadata_size or size > metadata_size - relative:
            raise ComparisonError("CLI stream outside metadata")
        if name in streams:
            raise ComparisonError("duplicate CLI stream")
        streams[name] = (metadata + relative, size)
    if any(start < cursor for start, _size in streams.values()):
        raise ComparisonError("CLI stream overlaps metadata headers")
    ranges = sorted((start, start + size) for start, size in streams.values() if size)
    for first, second in zip(ranges, ranges[1:]):
        if first[1] > second[0]:
            raise ComparisonError("overlapping CLI streams")
    table_names = [name for name in ("#~", "#-") if name in streams]
    if len(table_names) != 1 or "#GUID" not in streams:
        raise ComparisonError("missing or ambiguous CLI tables")
    tables, tables_size = streams[table_names[0]]
    tables_end = tables + tables_size
    if tables_size < 24:
        raise ComparisonError("truncated CLI tables")
    heap_sizes = raw[tables + 6]
    valid = u64(raw, tables + 8, tables_end)
    if (valid & 1) == 0:
        raise ComparisonError("missing CLI Module table")
    row_cursor = tables + 24
    rows: dict[int, int] = {}
    for table in range(64):
        if valid & (1 << table):
            rows[table] = u32(raw, row_cursor, tables_end)
            row_cursor += 4
    if rows.get(0) != 1:
        raise ComparisonError("CLI Module row count")
    string_index_size = 4 if heap_sizes & 0x01 else 2
    guid_index_size = 4 if heap_sizes & 0x02 else 2
    module_size = 2 + string_index_size + 3 * guid_index_size
    if row_cursor + module_size > tables_end:
        raise ComparisonError("truncated CLI Module row")
    mvid_index_offset = row_cursor + 2 + string_index_size
    mvid_index = (
        u32(raw, mvid_index_offset, tables_end)
        if guid_index_size == 4
        else u16(raw, mvid_index_offset, tables_end)
    )
    if mvid_index == 0:
        raise ComparisonError("zero CLI MVID index")
    guid, guid_size = streams["#GUID"]
    mvid_offset = guid + (mvid_index - 1) * 16
    if mvid_offset < guid or mvid_offset + 16 > guid + guid_size:
        raise ComparisonError("CLI MVID outside GUID heap")
    timestamp_offset = coff + 4
    if not (timestamp_offset + 4 <= mvid_offset or mvid_offset + 16 <= timestamp_offset):
        raise ComparisonError("overlapping PE build identity fields")
    normalized = bytearray(raw)
    normalized[timestamp_offset : timestamp_offset + 4] = b"\0" * 4
    normalized[mvid_offset : mvid_offset + 16] = b"\0" * 16
    return {
        "mvid": raw[mvid_offset : mvid_offset + 16],
        "mvid_offset": mvid_offset,
        "normalized": bytes(normalized),
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
        "timestamp": u32(raw, timestamp_offset),
        "timestamp_offset": timestamp_offset,
    }


def timestamp_ticks(value: object) -> int:
    observed = text(value, "observed_at_utc")
    match = re.fullmatch(
        r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})\.([0-9]{7})Z",
        observed,
    )
    if not match:
        raise ComparisonError("invalid observation timestamp")
    parts = [int(item) for item in match.groups()]
    try:
        moment = datetime.datetime(
            parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], tzinfo=datetime.timezone.utc
        )
    except ValueError as error:
        raise ComparisonError("invalid observation timestamp") from error
    return int(moment.timestamp()) * 10_000_000 + parts[6]


def json_differences(left: object, right: object, path: str = "") -> list[str]:
    if type(left) is not type(right):
        return [path or "/"]
    if isinstance(left, dict):
        result: list[str] = []
        for key in sorted(set(left) | set(right)):
            escaped = key.replace("~", "~0").replace("/", "~1")
            child = path + "/" + escaped
            if key not in left or key not in right:
                result.append(child)
            else:
                result.extend(json_differences(left[key], right[key], child))
        return result
    if isinstance(left, list):
        result = []
        if len(left) != len(right):
            result.append(path + "/length")
        for index, (first, second) in enumerate(zip(left, right)):
            result.extend(json_differences(first, second, path + "/" + str(index)))
        return result
    return [] if left == right else [path or "/"]


def load_attempt(
    root: pathlib.Path,
    expectations_raw: bytes,
    private_raw: bytes,
    expectations: dict[str, object],
) -> dict[str, object]:
    report_raw = read_artifact(root, "probe-output.json")
    manifest_raw = read_artifact(root, "retained-run-v1.json")
    executable_raw = read_artifact(root, "build/OriginalHostQualification.exe")
    verify_output.verify_bytes(report_raw, private_raw, expectations_raw)
    report = verify_output.decode_json(report_raw)
    manifest = parse_manifest(manifest_raw)
    if report["summary"] != {
        "comparison_verdict": "not-run",
        "completeness": "complete",
        "direct_wsl_launch_safe": False,
        "error_count": 0,
        "failed_count": 0,
        "original_execution_status": "not-run",
        "passed_count": len(verify_output.REQUIRED_CHECK_IDS),
        "required_check_count": len(verify_output.REQUIRED_CHECK_IDS),
        "safety_verdict": "eligible-for-synthetic-launcher-test",
    }:
        raise ComparisonError("report is not fully eligible")
    if any(item["outcome"] != "pass" for item in report["checks"]):
        raise ComparisonError("report has a non-pass check")
    if report["probe"]["id"] != PROBE_ID or report["probe"]["version"] != PROBE_VERSION or report["probe"]["source_revision"] != SOURCE_REVISION:
        raise ComparisonError("report producer profile")
    elapsed = integer(report["run"]["elapsed_ms"], "run.elapsed_ms")
    if elapsed > TIMEOUT_SECONDS * 1000:
        raise ComparisonError("report elapsed time exceeds timeout")
    bindings = manifest["bindings"]
    execution = manifest["execution"]
    executable_identity = identity(executable_raw)
    if report["probe"]["executable"] != executable_identity or report["probe"]["executable_after"] != executable_identity or report["probe"]["executable_unchanged"] is not True or bindings["probe_executable"] != executable_identity:
        raise ComparisonError("probe executable binding")
    if execution["probe_stdout"] != identity(report_raw):
        raise ComparisonError("probe stdout binding")
    expected_expectations = identity(expectations_raw)
    expected_private = identity(private_raw)
    if bindings["expectations"] != expected_expectations or bindings["private_locator"] != expected_private:
        raise ComparisonError("configuration binding")
    if report["probe"]["expectations_sha256"] != expected_expectations["sha256"] or report["probe"]["private_locator_sha256"] != expected_private["sha256"]:
        raise ComparisonError("report configuration binding")
    if bindings["compiler"] != {
        "byte_count": expectations["compiler_bytes"],
        "sha256": expectations["compiler_sha256"],
    } or bindings["compiler_ui"] != {
        "byte_count": expectations["compiler_ui_bytes"],
        "sha256": expectations["compiler_ui_sha256"],
    }:
        raise ComparisonError("compiler binding")
    artifact_bindings = {
        "build/csc.exe": bindings["compiler"],
        "build/1033/cscui.dll": bindings["compiler_ui"],
        "build/expectations.json": bindings["expectations"],
        "build/private-locator.json": bindings["private_locator"],
    }
    for source in bindings["sources"]:
        artifact_bindings["build/" + source["id"]] = source["identity"]
    for relative, expected in artifact_bindings.items():
        if identity(read_artifact(root, relative)) != expected:
            raise ComparisonError("retained artifact binding")
    if read_artifact(root, "build/expectations.json", 1024 * 1024) != expectations_raw or read_artifact(root, "build/private-locator.json", 1024 * 1024) != private_raw:
        raise ComparisonError("retained configuration snapshot")
    return {
        "executable_identity": executable_identity,
        "executable_raw": executable_raw,
        "manifest": manifest,
        "manifest_identity": identity(manifest_raw),
        "report": report,
        "report_identity": identity(report_raw),
    }


def stable_projection(report: dict[str, object], normalized_sha256: str) -> dict[str, object]:
    projected = verify_output.decode_json(canonical(report))
    projected["run"]["elapsed_ms"] = 0
    projected["run"]["observed_at_utc"] = "0000-00-00T00:00:00.0000000Z"
    projected["probe"]["executable"]["sha256"] = normalized_sha256
    projected["probe"]["executable_after"]["sha256"] = normalized_sha256
    return projected


def compare_attempts(
    first_root: pathlib.Path,
    second_root: pathlib.Path,
    expectations_raw: bytes,
    private_raw: bytes,
    comparator_identity: dict[str, object],
) -> dict[str, object]:
    if os.path.samefile(first_root, second_root):
        raise ComparisonError("retained roots are not distinct")
    expectations = verify_output.parse_expectations(expectations_raw)
    verify_output.parse_private_locator(private_raw)
    first = load_attempt(first_root, expectations_raw, private_raw, expectations)
    second = load_attempt(second_root, expectations_raw, private_raw, expectations)
    if timestamp_ticks(first["report"]["run"]["observed_at_utc"]) >= timestamp_ticks(second["report"]["run"]["observed_at_utc"]):
        raise ComparisonError("retained reports are not chronological")
    common_binding_keys = ("compiler", "compiler_ui", "expectations", "private_locator", "source_commit", "sources")
    if any(first["manifest"]["bindings"][key] != second["manifest"]["bindings"][key] for key in common_binding_keys):
        raise ComparisonError("retained producer binding mismatch")
    first_pe = parse_pe_build_identity(first["executable_raw"])
    second_pe = parse_pe_build_identity(second["executable_raw"])
    if first_pe["timestamp_offset"] != second_pe["timestamp_offset"] or first_pe["mvid_offset"] != second_pe["mvid_offset"]:
        raise ComparisonError("PE build identity layout mismatch")
    if first_pe["normalized"] != second_pe["normalized"]:
        raise ComparisonError("probe images differ outside PE build identity")
    if second_pe["timestamp"] < first_pe["timestamp"]:
        raise ComparisonError("probe build timestamps are reversed")
    normalized_identity = identity(first_pe["normalized"])
    differences = json_differences(first["report"], second["report"])
    if any(item not in ALLOWED_REPORT_DIFFERENCES for item in differences):
        raise ComparisonError("report difference outside closed allowlist")
    first_projection = stable_projection(first["report"], normalized_identity["sha256"])
    second_projection = stable_projection(second["report"], normalized_identity["sha256"])
    if first_projection != second_projection:
        raise ComparisonError("stable report projection mismatch")
    differing_offsets = [
        index
        for index, (left, right) in enumerate(zip(first["executable_raw"], second["executable_raw"]))
        if left != right
    ]
    timestamp_range = range(first_pe["timestamp_offset"], first_pe["timestamp_offset"] + 4)
    mvid_range = range(first_pe["mvid_offset"], first_pe["mvid_offset"] + 16)
    timestamp_differences = sum(item in timestamp_range for item in differing_offsets)
    mvid_differences = sum(item in mvid_range for item in differing_offsets)
    if timestamp_differences + mvid_differences != len(differing_offsets):
        raise ComparisonError("unclassified probe image difference")
    result = {
        "allowed_report_difference_paths": list(ALLOWED_REPORT_DIFFERENCES),
        "attempts": [
            {
                "id": "first",
                "mvid_sha256": hashlib.sha256(first_pe["mvid"]).hexdigest(),
                "probe_executable": first["executable_identity"],
                "report": first["report_identity"],
                "retained_manifest": first["manifest_identity"],
                "timestamp": first_pe["timestamp"],
            },
            {
                "id": "second",
                "mvid_sha256": hashlib.sha256(second_pe["mvid"]).hexdigest(),
                "probe_executable": second["executable_identity"],
                "report": second["report_identity"],
                "retained_manifest": second["manifest_identity"],
                "timestamp": second_pe["timestamp"],
            },
        ],
        "bindings": {
            key: first["manifest"]["bindings"][key] for key in common_binding_keys
        },
        "comparison": {
            "different_probe_byte_count": len(differing_offsets),
            "mvid_different_byte_count": mvid_differences,
            "mvid_field_offset": first_pe["mvid_offset"],
            "normalized_probe": normalized_identity,
            "observed_report_difference_paths": differences,
            "stable_projection_sha256": hashlib.sha256(canonical(first_projection)).hexdigest(),
            "timestamp_delta_seconds": second_pe["timestamp"] - first_pe["timestamp"],
            "timestamp_different_byte_count": timestamp_differences,
            "timestamp_field_offset": first_pe["timestamp_offset"],
        },
        "comparator": {
            "id": COMPARATOR_ID,
            "implementation": comparator_identity,
            "profile_id": PROFILE_ID,
            "profile_source_revision": SOURCE_REVISION,
            "version": COMPARATOR_VERSION,
        },
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "original_behavior_qualified": False,
            "original_execution_status": "not-run",
            "stability_verdict": "pe-build-identity-normalized-stable",
        },
    }
    verify_output.reject_path_like_strings(result)
    return result


def write_exclusive(path: pathlib.Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    finally:
        os.close(descriptor)


def build_pe_fixture(timestamp: int, mvid: bytes, payload_byte: int = 0x2A) -> bytes:
    if len(mvid) != 16:
        raise AssertionError("fixture MVID")
    raw = bytearray(0x600)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 0x3C, 0x80)
    raw[0x80:0x84] = b"PE\0\0"
    coff = 0x84
    struct.pack_into("<HHIIIHH", raw, coff, 0x14C, 1, timestamp, 0, 0, 0xE0, 0x0002)
    optional = coff + 20
    struct.pack_into("<H", raw, optional, 0x10B)
    struct.pack_into("<I", raw, optional + 92, 16)
    struct.pack_into("<II", raw, optional + 96 + 14 * 8, 0x1100, 0x48)
    section = optional + 0xE0
    raw[section : section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", raw, section + 8, 0x400, 0x1000, 0x400, 0x200)
    cli = 0x300
    struct.pack_into("<IHHII", raw, cli, 0x48, 2, 5, 0x1200, 0x180)
    metadata = 0x400
    struct.pack_into("<IHHII", raw, metadata, 0x424A5342, 1, 1, 0, 4)
    raw[metadata + 16 : metadata + 20] = b"v1\0\0"
    struct.pack_into("<HH", raw, metadata + 20, 0, 2)
    cursor = metadata + 24
    struct.pack_into("<II", raw, cursor, 0x40, 0x40)
    raw[cursor + 8 : cursor + 12] = b"#~\0\0"
    cursor += 12
    struct.pack_into("<II", raw, cursor, 0x80, 0x20)
    raw[cursor + 8 : cursor + 16] = b"#GUID\0\0\0"
    tables = metadata + 0x40
    struct.pack_into("<IBBBBQQ", raw, tables, 0, 2, 0, 0, 1, 1, 0)
    struct.pack_into("<I", raw, tables + 24, 1)
    struct.pack_into("<HHHHH", raw, tables + 28, 0, 0, 1, 0, 0)
    guid = metadata + 0x80
    raw[guid : guid + 16] = mvid
    raw[0x250] = payload_byte
    return bytes(raw)


def expect_rejected(action, label: str) -> None:
    try:
        action()
    except (ComparisonError, ValueError, OSError):
        return
    raise AssertionError("accepted " + label)


def self_test() -> None:
    first = build_pe_fixture(1, b"a" * 16)
    second = build_pe_fixture(0x01020304, b"b" * 16)
    first_parsed = parse_pe_build_identity(first)
    second_parsed = parse_pe_build_identity(second)
    if first_parsed["normalized"] != second_parsed["normalized"]:
        raise AssertionError("PE normalization positive")
    changed_payload = build_pe_fixture(2, b"c" * 16, 0x2B)
    if parse_pe_build_identity(first)["normalized"] == parse_pe_build_identity(changed_payload)["normalized"]:
        raise AssertionError("PE payload negative")
    wrong_machine = bytearray(first)
    struct.pack_into("<H", wrong_machine, 0x84, 0x8664)
    expect_rejected(lambda: parse_pe_build_identity(bytes(wrong_machine)), "PE32+ machine")
    zero_mvid = bytearray(first)
    struct.pack_into("<H", zero_mvid, 0x400 + 0x40 + 28 + 4, 0)
    expect_rejected(lambda: parse_pe_build_identity(bytes(zero_mvid)), "zero MVID")
    truncated = first[:0x450]
    expect_rejected(lambda: parse_pe_build_identity(truncated), "truncated PE")
    with tempfile.TemporaryDirectory() as directory:
        output = pathlib.Path(directory) / "result.json"
        write_exclusive(output, canonical({"schema_version": 1}))
        expect_rejected(
            lambda: write_exclusive(output, canonical({"schema_version": 1})),
            "comparison output replacement",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    compare = sub.add_parser("compare")
    compare.add_argument("--first-dir", required=True, type=pathlib.Path)
    compare.add_argument("--second-dir", required=True, type=pathlib.Path)
    compare.add_argument("--expectations", required=True, type=pathlib.Path)
    compare.add_argument("--private-locator", required=True, type=pathlib.Path)
    compare.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
        print("PASS")
        return 0
    first_root = ensure_retained_root(args.first_dir)
    second_root = ensure_retained_root(args.second_dir)
    expectations_raw = read_plain(args.expectations, 1024 * 1024)
    private_raw = read_plain(args.private_locator, 1024 * 1024)
    implementation_path = pathlib.Path(__file__).resolve(strict=True)
    implementation_identity = identity(read_plain(implementation_path, 1024 * 1024))
    result = compare_attempts(
        first_root,
        second_root,
        expectations_raw,
        private_raw,
        implementation_identity,
    )
    output = args.output.absolute()
    output_parent = output.parent.resolve(strict=True)
    for retained_root in (first_root, second_root):
        try:
            output_parent.relative_to(retained_root)
        except ValueError:
            continue
        raise ComparisonError("comparison output overlaps retained input")
    write_exclusive(output, canonical(result))
    print("PASS " + identity(canonical(result))["sha256"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ComparisonError, OSError, ValueError, AssertionError, json.JSONDecodeError) as error:
        print("FAIL: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
