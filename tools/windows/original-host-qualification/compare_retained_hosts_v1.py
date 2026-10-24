#!/usr/bin/env python3
"""Compare two retained host-qualification attempts without hiding build drift."""

from __future__ import annotations

import argparse
import datetime
import dataclasses
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import secrets
import stat
import struct
import sys
import tempfile
import types

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
PUBLIC_EXPECTATIONS_IDENTITY = {
    "byte_count": 1382,
    "sha256": "1d4af10dba7a85c74c58620eba074b667e2804120aac07930602ad88db1ba5d6",
}
RUNTIME_VERIFIER_IDENTITY = {
    "byte_count": 69268,
    "sha256": "36d52b8b7cee6949fe4c7fbbac709178c1eefbbc9cc8396cf16c1a0f0be3b211",
}
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


@dataclasses.dataclass(frozen=True)
class ComparisonProfile:
    profile_id: str
    source_revision: str
    expectations_identity: dict[str, object]
    bound_sources: tuple[tuple[str, dict[str, object]], ...]


PRODUCTION_PROFILE = ComparisonProfile(
    profile_id=PROFILE_ID,
    source_revision=SOURCE_REVISION,
    expectations_identity=PUBLIC_EXPECTATIONS_IDENTITY,
    bound_sources=BOUND_SOURCES,
)


class ComparisonError(Exception):
    pass


def _fingerprint(value: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _mount_id(descriptor: int) -> int:
    try:
        raw = pathlib.Path("/proc/self/fdinfo").joinpath(str(descriptor)).read_text(
            encoding="ascii"
        )
    except (OSError, UnicodeError) as error:
        raise ComparisonError("mount identity unavailable") from error
    matches = re.findall(r"(?m)^mnt_id:\s*([0-9]+)\s*$", raw)
    if len(matches) != 1 or int(matches[0]) <= 0:
        raise ComparisonError("invalid mount identity")
    return int(matches[0])


def _read_descriptor(descriptor: int, maximum: int) -> tuple[bytes, os.stat_result]:
    before = os.fstat(descriptor)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size < 0
        or before.st_size > maximum
    ):
        raise ComparisonError("input is not a bounded single-link regular file")
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = os.read(descriptor, min(65536, maximum + 1 - observed))
        if not chunk:
            break
        observed += len(chunk)
        if observed > maximum:
            raise ComparisonError("input grew beyond byte limit")
        chunks.append(chunk)
    after = os.fstat(descriptor)
    if _fingerprint(before) != _fingerprint(after) or observed != before.st_size:
        raise ComparisonError("input changed during bounded read")
    return b"".join(chunks), before


def _read_exact_path(path: pathlib.Path, maximum: int) -> bytes:
    absolute = path.absolute()
    _parent, parent_descriptors, _objects = _open_absolute_directory(absolute.parent)
    try:
        before = os.stat(
            absolute.name, dir_fd=parent_descriptors[-1], follow_symlinks=False
        )
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ComparisonError("input path is not a single-link regular file")
        descriptor = os.open(
            absolute.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_descriptors[-1],
        )
        try:
            raw, opened = _read_descriptor(descriptor, maximum)
        finally:
            os.close(descriptor)
        after = os.stat(
            absolute.name, dir_fd=parent_descriptors[-1], follow_symlinks=False
        )
        if _fingerprint(before) != _fingerprint(opened) or _fingerprint(before) != _fingerprint(after):
            raise ComparisonError("input path changed during bounded read")
        return raw
    finally:
        for held in reversed(parent_descriptors):
            os.close(held)


def _open_absolute_directory(
    path: pathlib.Path,
) -> tuple[pathlib.Path, list[int], list[tuple[int, int]]]:
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
    ):
        raise ComparisonError("required descriptor-relative no-follow APIs unavailable")
    absolute = path.absolute()
    if not absolute.is_absolute() or ".." in absolute.parts:
        raise ComparisonError("directory path is not normalized absolute")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptors = [os.open("/", flags)]
    objects = [(os.fstat(descriptors[0]).st_dev, os.fstat(descriptors[0]).st_ino)]
    try:
        for component in absolute.parts[1:]:
            before = os.stat(component, dir_fd=descriptors[-1], follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise ComparisonError("directory path component is not a plain directory")
            child = os.open(component, flags, dir_fd=descriptors[-1])
            opened = os.fstat(child)
            after = os.stat(component, dir_fd=descriptors[-1], follow_symlinks=False)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
                or (opened.st_dev, opened.st_ino) != (after.st_dev, after.st_ino)
            ):
                os.close(child)
                raise ComparisonError("directory path changed during open")
            descriptors.append(child)
            objects.append((opened.st_dev, opened.st_ino))
    except Exception:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise
    return absolute, descriptors, objects


def _load_bound_verifier_from(
    script: pathlib.Path,
    verifier: pathlib.Path,
    expected_identity: dict[str, object],
) -> types.ModuleType:
    script_path = script.absolute()
    _read_exact_path(script_path, STREAM_CAP_BYTES)
    verifier_path = verifier.absolute()
    if verifier_path != script_path.with_name("verify_output.py"):
        raise ComparisonError("runtime verifier is not the canonical sibling")
    verifier_raw = _read_exact_path(verifier_path, 1024 * 1024)
    if identity(verifier_raw) != expected_identity:
        raise ComparisonError("runtime verifier identity does not match profile")
    module = types.ModuleType("cm0102_bound_verify_output")
    module.__file__ = str(verifier_path)
    module.__spec__ = importlib.util.spec_from_loader(module.__name__, loader=None)
    exec(compile(verifier_raw, str(verifier_path), "exec"), module.__dict__)
    if pathlib.Path(module.__file__).absolute() != verifier_path:
        raise ComparisonError("runtime verifier path mismatch")
    return module


def _load_bound_verifier() -> types.ModuleType:
    script = pathlib.Path(__file__)
    return _load_bound_verifier_from(
        script, script.absolute().with_name("verify_output.py"), RUNTIME_VERIFIER_IDENTITY
    )


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def identity(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


verify_output = _load_bound_verifier()


def strict_object(value: object, keys: set[str], name: str) -> dict[str, object]:
    return verify_output.strict_object(value, keys, name)


def identity_value(value: object, name: str) -> dict[str, object]:
    return verify_output.identity(value, name)


def integer(value: object, name: str) -> int:
    return verify_output.integer(value, name)


def text(value: object, name: str) -> str:
    return verify_output.text(value, name)


def read_plain(path: pathlib.Path, maximum: int = STREAM_CAP_BYTES) -> bytes:
    return _read_exact_path(path, maximum)


class RetainedRoot:
    def __init__(self, path: pathlib.Path):
        self.path, self.absolute_descriptors, self.ancestor_objects = _open_absolute_directory(path)
        self.descriptor = self.absolute_descriptors[-1]
        opened = os.fstat(self.descriptor)
        self.root_object = (opened.st_dev, opened.st_ino)
        self.root_mount_id = _mount_id(self.descriptor)
        self.directories: dict[tuple[str, ...], int] = {(): self.descriptor}
        self.directory_fingerprints: dict[tuple[str, ...], tuple[int, int, int, int, int, int, int]] = {
            (): _fingerprint(opened)
        }
        self.files: dict[
            str, tuple[int, tuple[int, int, int, int, int, int, int], bytes]
        ] = {}

    def close(self) -> None:
        for descriptor in [item[0] for item in self.files.values()]:
            os.close(descriptor)
        for parts, descriptor in sorted(self.directories.items(), key=lambda item: len(item[0]), reverse=True):
            if parts:
                os.close(descriptor)
        for descriptor in reversed(self.absolute_descriptors):
            os.close(descriptor)
        self.files.clear()
        self.directories.clear()
        self.directory_fingerprints.clear()
        self.absolute_descriptors.clear()

    @staticmethod
    def _parts(relative: str) -> tuple[str, ...]:
        pure = pathlib.PurePosixPath(relative)
        parts = pure.parts
        if pure.is_absolute() or not parts or any(item in ("", ".", "..") for item in parts):
            raise ComparisonError("invalid retained artifact path")
        return parts

    def _directory(self, parts: tuple[str, ...]) -> int:
        if parts in self.directories:
            return self.directories[parts]
        parent = self._directory(parts[:-1])
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent,
        )
        opened = os.fstat(descriptor)
        if not stat.S_ISDIR(opened.st_mode):
            os.close(descriptor)
            raise ComparisonError("retained path component is not a directory")
        self.directories[parts] = descriptor
        self.directory_fingerprints[parts] = _fingerprint(opened)
        return descriptor

    def read(self, relative: str, maximum: int = STREAM_CAP_BYTES) -> bytes:
        if relative in self.files:
            raise ComparisonError("retained artifact read more than once")
        parts = self._parts(relative)
        parent = self._directory(parts[:-1])
        descriptor = os.open(
            parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent
        )
        try:
            raw, opened = _read_descriptor(descriptor, maximum)
        except Exception:
            os.close(descriptor)
            raise
        self.files[relative] = (descriptor, _fingerprint(opened), raw)
        return raw

    def object_id(self, relative: str) -> tuple[int, int]:
        descriptor, _fingerprint_value, _raw = self.files[relative]
        observed = os.fstat(descriptor)
        return (observed.st_dev, observed.st_ino)

    def revalidate(self) -> None:
        for index, component in enumerate(self.path.parts[1:], start=1):
            observed = os.stat(
                component,
                dir_fd=self.absolute_descriptors[index - 1],
                follow_symlinks=False,
            )
            held = os.fstat(self.absolute_descriptors[index])
            if (
                (observed.st_dev, observed.st_ino) != self.ancestor_objects[index]
                or (held.st_dev, held.st_ino) != self.ancestor_objects[index]
            ):
                raise ComparisonError("retained absolute path changed during comparison")
        current_root = os.fstat(self.descriptor)
        if (
            (current_root.st_dev, current_root.st_ino) != self.root_object
            or _mount_id(self.descriptor) != self.root_mount_id
        ):
            raise ComparisonError("retained root changed during comparison")
        if len(self.absolute_descriptors) > 1:
            root_name = self.path.parts[-1]
            path_root = os.stat(
                root_name,
                dir_fd=self.absolute_descriptors[-2],
                follow_symlinks=False,
            )
            if (path_root.st_dev, path_root.st_ino) != self.root_object:
                raise ComparisonError("retained root path changed during comparison")
        for parts, descriptor in self.directories.items():
            if not parts:
                continue
            parent = self.directories[parts[:-1]]
            observed = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if (
                _fingerprint(os.fstat(descriptor)) != self.directory_fingerprints[parts]
                or _fingerprint(observed) != self.directory_fingerprints[parts]
            ):
                raise ComparisonError("retained directory changed during comparison")
        for relative, (descriptor, expected, raw) in self.files.items():
            if _fingerprint(os.fstat(descriptor)) != expected:
                raise ComparisonError("retained artifact changed during comparison")
            if os.pread(descriptor, len(raw) + 1, 0) != raw:
                raise ComparisonError("retained artifact bytes changed during comparison")
            parts = self._parts(relative)
            parent = self._directory(parts[:-1])
            check = os.open(
                parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent
            )
            try:
                if _fingerprint(os.fstat(check)) != expected:
                    raise ComparisonError("retained artifact path changed during comparison")
            finally:
                os.close(check)


def read_artifact(root: RetainedRoot, relative: str, maximum: int = STREAM_CAP_BYTES) -> bytes:
    return root.read(relative, maximum)


def parse_command(value: object, expected_roles: tuple[str, ...], name: str) -> dict[str, object]:
    command = strict_object(value, {"argument_count", "argv_roles", "sha256"}, name)
    if integer(command["argument_count"], name + ".argument_count") != len(expected_roles):
        raise ComparisonError(name + " argument count")
    if command["argv_roles"] != list(expected_roles):
        raise ComparisonError(name + " roles")
    verify_output.sha256(command["sha256"], name + ".sha256")
    return command


def parse_sources(
    value: object, bound_sources: tuple[tuple[str, dict[str, object]], ...] = BOUND_SOURCES
) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) != len(bound_sources):
        raise ComparisonError("manifest sources")
    result: list[dict[str, object]] = []
    for item, expected in zip(value, bound_sources):
        source = strict_object(item, {"id", "identity"}, "manifest source")
        if source["id"] != expected[0]:
            raise ComparisonError("manifest source order")
        observed = identity_value(source["identity"], "manifest source identity")
        if observed != expected[1]:
            raise ComparisonError("manifest source profile identity")
        result.append(source)
    return result


def parse_manifest(
    raw: bytes, profile: ComparisonProfile = PRODUCTION_PROFILE
) -> dict[str, object]:
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
    if text(bindings["source_commit"], "manifest source commit") != profile.source_revision:
        raise ComparisonError("manifest source commit")
    parse_sources(bindings["sources"], profile.bound_sources)
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
    size_of_headers = u32(raw, optional + 60, section_table)
    if size_of_headers < section_table + section_count * 40 or size_of_headers > len(raw):
        raise ComparisonError("invalid PE header span")
    directory_count = u32(raw, optional + 92, section_table)
    if directory_count < 15 or 96 + directory_count * 8 > optional_size:
        raise ComparisonError("missing CLI data directory")
    cli_rva = u32(raw, optional + 96 + 14 * 8, section_table)
    cli_size = u32(raw, optional + 96 + 14 * 8 + 4, section_table)
    if cli_rva == 0 or cli_size < 0x48:
        raise ComparisonError("missing CLI header")
    sections: list[tuple[int, int, int, int]] = []
    raw_ranges: list[tuple[int, int]] = []
    virtual_ranges: list[tuple[int, int]] = []
    for index in range(section_count):
        header = section_table + index * 40
        virtual_size = u32(raw, header + 8)
        virtual_address = u32(raw, header + 12)
        raw_size = u32(raw, header + 16)
        raw_offset = u32(raw, header + 20)
        if raw_size:
            if (
                raw_offset < size_of_headers
                or raw_offset > len(raw)
                or raw_size > len(raw) - raw_offset
            ):
                raise ComparisonError("section outside image or overlaps headers")
            raw_ranges.append((raw_offset, raw_offset + raw_size))
        mapped_size = max(virtual_size, raw_size)
        if mapped_size:
            if virtual_address == 0 or virtual_address + mapped_size > 1 << 32:
                raise ComparisonError("invalid virtual section range")
            virtual_ranges.append((virtual_address, virtual_address + mapped_size))
        sections.append((virtual_address, virtual_size, raw_size, raw_offset))
    for ranges, label in ((raw_ranges, "raw"), (virtual_ranges, "virtual")):
        ordered = sorted(ranges)
        for first, second in zip(ordered, ordered[1:]):
            if first[1] > second[0]:
                raise ComparisonError("overlapping PE " + label + " sections")

    def rva_to_offset(rva: int, size: int) -> int:
        matches = []
        for virtual_address, virtual_size, raw_size, raw_offset in sections:
            relative = rva - virtual_address
            if (
                rva >= virtual_address
                and size <= raw_size
                and relative <= raw_size - size
                and (virtual_size == 0 or (size <= virtual_size and relative <= virtual_size - size))
            ):
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
    entrypoint_token = u32(raw, cli + 20, cli + cli_header_size)
    if (
        u16(raw, cli + 4, cli + cli_header_size) != 2
        or u16(raw, cli + 6, cli + cli_header_size) != 5
        or u32(raw, cli + 16, cli + cli_header_size) != 0x00000003
        or entrypoint_token == 0
    ):
        raise ComparisonError("unexpected CLI runtime profile")
    metadata_rva = u32(raw, cli + 8, cli + cli_header_size)
    metadata_size = u32(raw, cli + 12, cli + cli_header_size)
    if metadata_rva == 0 or metadata_size < 20:
        raise ComparisonError("missing CLI metadata")
    metadata = rva_to_offset(metadata_rva, metadata_size)
    metadata_end = metadata + metadata_size
    if not (cli + cli_header_size <= metadata or metadata_end <= cli):
        raise ComparisonError("CLI header overlaps metadata")
    if u32(raw, metadata, metadata_end) != 0x424A5342:
        raise ComparisonError("invalid CLI metadata signature")
    if (
        u16(raw, metadata + 4, metadata_end) != 1
        or u16(raw, metadata + 6, metadata_end) != 1
        or u32(raw, metadata + 8, metadata_end) != 0
    ):
        raise ComparisonError("invalid CLI metadata version header")
    version_size = u32(raw, metadata + 12, metadata_end)
    if version_size < 1 or version_size > 256:
        raise ComparisonError("invalid CLI metadata version size")
    version_end = metadata + 16 + version_size
    aligned_version_end = align4(version_end)
    if aligned_version_end > metadata_end:
        raise ComparisonError("CLI metadata version outside metadata")
    version = raw[metadata + 16 : version_end]
    terminator = version.find(b"\0")
    if (
        terminator < 1
        or any(item < 0x20 or item > 0x7E for item in version[:terminator])
        or any(raw[metadata + 16 + terminator : aligned_version_end])
    ):
        raise ComparisonError("invalid CLI metadata version string")
    cursor = aligned_version_end
    if cursor + 4 > metadata_end:
        raise ComparisonError("truncated CLI stream header")
    if u16(raw, cursor, metadata_end) != 0:
        raise ComparisonError("invalid CLI metadata flags")
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
        aligned_name_end = align4(name_end + 1)
        if any(raw[name_end + 1 : aligned_name_end]):
            raise ComparisonError("nonzero CLI stream-name padding")
        cursor = aligned_name_end
        if cursor > metadata_end or relative > metadata_size or size > metadata_size - relative:
            raise ComparisonError("CLI stream outside metadata")
        if relative % 4:
            raise ComparisonError("unaligned CLI stream")
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
    if len(table_names) != 1 or set(streams) != {"#~", "#Strings", "#US", "#GUID", "#Blob"}:
        raise ComparisonError("missing or ambiguous CLI tables")
    if streams["#GUID"][1] != 16 or any(
        streams[name][1] < 1 or raw[streams[name][0]] != 0
        for name in ("#Strings", "#US", "#Blob")
    ):
        raise ComparisonError("invalid CLI heap")
    tables, tables_size = streams[table_names[0]]
    tables_end = tables + tables_size
    if tables_size < 24:
        raise ComparisonError("truncated CLI tables")
    if (
        u32(raw, tables, tables_end) != 0
        or raw[tables + 4] != 2
        or raw[tables + 5] != 0
        or raw[tables + 6] & ~0x07
        or raw[tables + 7] != 1
    ):
        raise ComparisonError("invalid CLI tables header")
    heap_sizes = raw[tables + 6]
    valid = u64(raw, tables + 8, tables_end)
    sorted_tables = u64(raw, tables + 16, tables_end)
    if valid >> 45:
        raise ComparisonError("invalid CLI table masks")
    sortable_mask = sum(
        1 << item for item in (9, 11, 12, 13, 14, 15, 16, 18, 21, 24, 25, 28, 29, 41, 42, 44)
    )
    if sorted_tables & ~sortable_mask:
        raise ComparisonError("invalid CLI sorted mask")
    if table_names[0] == "#~" and valid & sum(1 << item for item in (3, 5, 7, 19, 22, 30, 31)):
        raise ComparisonError("optimized CLI tables contain pointer or ENC table")
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
    if entrypoint_token >> 24 != 0x06:
        raise ComparisonError("invalid CLI entrypoint table")
    entrypoint_rid = entrypoint_token & 0x00FFFFFF
    if entrypoint_rid == 0 or entrypoint_rid > rows.get(6, 0):
        raise ComparisonError("invalid CLI entrypoint row")
    string_index_size = 4 if heap_sizes & 0x01 else 2
    guid_index_size = 4 if heap_sizes & 0x02 else 2
    blob_index_size = 4 if heap_sizes & 0x04 else 2

    def table_index_size(table: int) -> int:
        return 4 if rows.get(table, 0) >= 0x10000 else 2

    def coded_index_size(tables: tuple[int, ...], tag_bits: int) -> int:
        limit = 1 << (16 - tag_bits)
        return 4 if any(rows.get(table, 0) >= limit for table in tables) else 2

    module_size = 2 + string_index_size + 3 * guid_index_size
    table_sizes = {
        0: module_size,
        1: coded_index_size((0, 1, 26, 35), 2) + 2 * string_index_size,
        2: (
            4
            + 2 * string_index_size
            + coded_index_size((1, 2, 27), 2)
            + table_index_size(4)
            + table_index_size(6)
        ),
        3: table_index_size(4),
        4: 2 + string_index_size + blob_index_size,
        5: table_index_size(6),
        6: 8 + string_index_size + blob_index_size + table_index_size(8),
    }
    method_row = row_cursor
    for table in range(6):
        method_row += rows.get(table, 0) * table_sizes[table]
        if method_row > tables_end:
            raise ComparisonError("truncated CLI table rows before MethodDef")
    method_table_end = method_row + rows[6] * table_sizes[6]
    if method_table_end > tables_end:
        raise ComparisonError("truncated CLI MethodDef table")
    if row_cursor + module_size > tables_end:
        raise ComparisonError("truncated CLI Module row")
    generation = u16(raw, row_cursor, tables_end)
    name_index_offset = row_cursor + 2
    name_index = (
        u32(raw, name_index_offset, tables_end)
        if string_index_size == 4
        else u16(raw, name_index_offset, tables_end)
    )
    mvid_index_offset = row_cursor + 2 + string_index_size
    mvid_index = (
        u32(raw, mvid_index_offset, tables_end)
        if guid_index_size == 4
        else u16(raw, mvid_index_offset, tables_end)
    )
    enc_id_offset = mvid_index_offset + guid_index_size
    enc_base_id_offset = enc_id_offset + guid_index_size
    enc_id = (
        u32(raw, enc_id_offset, tables_end)
        if guid_index_size == 4
        else u16(raw, enc_id_offset, tables_end)
    )
    enc_base_id = (
        u32(raw, enc_base_id_offset, tables_end)
        if guid_index_size == 4
        else u16(raw, enc_base_id_offset, tables_end)
    )
    strings, strings_size = streams["#Strings"]
    if generation != 0 or mvid_index != 1 or enc_id != 0 or enc_base_id != 0:
        raise ComparisonError("invalid CLI Module reserved fields")
    if name_index == 0 or name_index >= strings_size:
        raise ComparisonError("invalid CLI Module name index")
    name_end = raw.find(b"\0", strings + name_index, strings + strings_size)
    if name_end <= strings + name_index:
        raise ComparisonError("invalid CLI Module name")
    try:
        raw[strings + name_index : name_end].decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise ComparisonError("invalid CLI Module name") from error
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
    root: RetainedRoot,
    expectations_raw: bytes,
    private_raw: bytes,
    expectations: dict[str, object],
    profile: ComparisonProfile = PRODUCTION_PROFILE,
) -> dict[str, object]:
    report_raw = read_artifact(root, "probe-output.json")
    manifest_raw = read_artifact(root, "retained-run-v1.json")
    executable_raw = read_artifact(root, "build/OriginalHostQualification.exe")
    verify_output.verify_bytes(report_raw, private_raw, expectations_raw)
    report = verify_output.decode_json(report_raw)
    manifest = parse_manifest(manifest_raw, profile)
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
    if report["probe"]["id"] != PROBE_ID or report["probe"]["version"] != PROBE_VERSION or report["probe"]["source_revision"] != profile.source_revision:
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
    retained_raw: dict[str, bytes] = {}
    for relative, expected in artifact_bindings.items():
        retained_raw[relative] = read_artifact(root, relative)
        if identity(retained_raw[relative]) != expected:
            raise ComparisonError("retained artifact binding")
    if retained_raw["build/expectations.json"] != expectations_raw or retained_raw["build/private-locator.json"] != private_raw:
        raise ComparisonError("retained configuration snapshot")
    return {
        "executable_identity": executable_identity,
        "executable_raw": executable_raw,
        "manifest": manifest,
        "manifest_identity": identity(manifest_raw),
        "report": report,
        "report_identity": identity(report_raw),
        "retained_objects": {
            relative: root.object_id(relative)
            for relative in (
                "probe-output.json",
                "retained-run-v1.json",
                "build/OriginalHostQualification.exe",
                *artifact_bindings.keys(),
            )
        },
    }


def stable_projection(report: dict[str, object], normalized_sha256: str) -> dict[str, object]:
    projected = verify_output.decode_json(canonical(report))
    projected["run"]["elapsed_ms"] = 0
    projected["run"]["observed_at_utc"] = "0000-00-00T00:00:00.0000000Z"
    projected["probe"]["executable"]["sha256"] = normalized_sha256
    projected["probe"]["executable_after"]["sha256"] = normalized_sha256
    return projected


def compare_attempts(
    first_root: RetainedRoot,
    second_root: RetainedRoot,
    expectations_raw: bytes,
    private_raw: bytes,
    comparator_identity: dict[str, object],
    runtime_verifier_identity: dict[str, object],
    profile: ComparisonProfile = PRODUCTION_PROFILE,
) -> dict[str, object]:
    if first_root.root_object == second_root.root_object:
        raise ComparisonError("retained roots are not distinct")
    if (
        first_root.root_object[0] != second_root.root_object[0]
        or first_root.root_mount_id != second_root.root_mount_id
    ):
        raise ComparisonError("retained roots use different mount views")
    if (
        first_root.root_object in second_root.ancestor_objects
        or second_root.root_object in first_root.ancestor_objects
    ):
        raise ComparisonError("retained roots physically overlap")
    for outer, inner in ((first_root.path, second_root.path), (second_root.path, first_root.path)):
        try:
            inner.relative_to(outer)
        except ValueError:
            continue
        raise ComparisonError("retained roots overlap")
    if identity(expectations_raw) != profile.expectations_identity:
        raise ComparisonError("expectations identity does not match profile")
    expectations = verify_output.parse_expectations(expectations_raw)
    verify_output.parse_private_locator(private_raw)
    first = load_attempt(first_root, expectations_raw, private_raw, expectations, profile)
    second = load_attempt(second_root, expectations_raw, private_raw, expectations, profile)
    if set(first["retained_objects"].values()) & set(second["retained_objects"].values()):
        raise ComparisonError("retained attempts share artifact objects")
    if timestamp_ticks(first["report"]["run"]["observed_at_utc"]) >= timestamp_ticks(second["report"]["run"]["observed_at_utc"]):
        raise ComparisonError("retained reports are not chronological")
    common_binding_keys = ("compiler", "compiler_ui", "expectations", "private_locator", "source_commit", "sources")
    if any(first["manifest"]["bindings"][key] != second["manifest"]["bindings"][key] for key in common_binding_keys):
        raise ComparisonError("retained producer binding mismatch")
    for command_key in ("build_command", "probe_command"):
        if first["manifest"]["bindings"][command_key]["sha256"] == second["manifest"]["bindings"][command_key]["sha256"]:
            raise ComparisonError("retained attempt command binding is reused")
    first_pe = parse_pe_build_identity(first["executable_raw"])
    second_pe = parse_pe_build_identity(second["executable_raw"])
    if first_pe["timestamp_offset"] != second_pe["timestamp_offset"] or first_pe["mvid_offset"] != second_pe["mvid_offset"]:
        raise ComparisonError("PE build identity layout mismatch")
    if first_pe["normalized"] != second_pe["normalized"]:
        raise ComparisonError("probe images differ outside PE build identity")
    if second_pe["timestamp"] <= first_pe["timestamp"] or second_pe["mvid"] == first_pe["mvid"]:
        raise ComparisonError("probe builds are not distinct and chronological")
    first_root.revalidate()
    second_root.revalidate()
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
            "profile_id": profile.profile_id,
            "profile_source_revision": profile.source_revision,
            "runtime_verifier": runtime_verifier_identity,
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


class OutputTarget:
    def __init__(self, path: pathlib.Path, roots: tuple[RetainedRoot, ...]):
        self.output = path.absolute()
        if not self.output.name:
            raise ComparisonError("comparison output has no filename")
        self.parent, self.parent_descriptors, self.ancestor_objects = _open_absolute_directory(
            self.output.parent
        )
        self.parent_descriptor = self.parent_descriptors[-1]
        parent_stat = os.fstat(self.parent_descriptor)
        self.parent_mount_id = _mount_id(self.parent_descriptor)
        if parent_stat.st_uid != os.geteuid() or stat.S_IMODE(parent_stat.st_mode) & 0o077:
            self.close()
            raise ComparisonError("comparison output parent is not private and owned")
        for retained_root in roots:
            if (
                parent_stat.st_dev != retained_root.root_object[0]
                or self.parent_mount_id != retained_root.root_mount_id
            ):
                self.close()
                raise ComparisonError("comparison output uses a different mount view")
            if retained_root.root_object in self.ancestor_objects:
                self.close()
                raise ComparisonError("comparison output physically overlaps retained input")
            try:
                self.parent.relative_to(retained_root.path)
            except ValueError:
                continue
            self.close()
            raise ComparisonError("comparison output lexically overlaps retained input")

    def revalidate(self) -> None:
        for index, component in enumerate(self.parent.parts[1:], start=1):
            observed = os.stat(
                component,
                dir_fd=self.parent_descriptors[index - 1],
                follow_symlinks=False,
            )
            held = os.fstat(self.parent_descriptors[index])
            if (
                (observed.st_dev, observed.st_ino) != self.ancestor_objects[index]
                or (held.st_dev, held.st_ino) != self.ancestor_objects[index]
            ):
                raise ComparisonError("comparison output path changed")
        parent_stat = os.fstat(self.parent_descriptor)
        if (
            _mount_id(self.parent_descriptor) != self.parent_mount_id
            or parent_stat.st_uid != os.geteuid()
            or stat.S_IMODE(parent_stat.st_mode) & 0o077
        ):
            raise ComparisonError("comparison output parent privacy changed")

    def close(self) -> None:
        for descriptor in reversed(getattr(self, "parent_descriptors", [])):
            os.close(descriptor)
        self.parent_descriptors = []

    def publish(self, raw: bytes, post_check=lambda: None) -> None:
        parent_descriptor = self.parent_descriptor
        temporary = "." + self.output.name + ".tmp-" + secrets.token_hex(16)
        temporary_created = False
        final_created = False
        descriptor: int | None = None
        try:
            self.revalidate()
            try:
                os.stat(self.output.name, dir_fd=parent_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError(self.output)
            descriptor = os.open(
                temporary,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent_descriptor,
            )
            temporary_created = True
            view = memoryview(raw)
            written = 0
            while written < len(raw):
                count = os.write(descriptor, view[written:])
                if count <= 0:
                    raise ComparisonError("short comparison output write")
                written += count
            os.fsync(descriptor)
            observed = os.fstat(descriptor)
            if (
                not stat.S_ISREG(observed.st_mode)
                or observed.st_uid != os.geteuid()
                or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_nlink != 1
                or observed.st_size != len(raw)
                or os.pread(descriptor, len(raw) + 1, 0) != raw
            ):
                raise ComparisonError("invalid temporary comparison output")
            named_temporary = os.stat(
                temporary, dir_fd=parent_descriptor, follow_symlinks=False
            )
            if (named_temporary.st_dev, named_temporary.st_ino) != (
                observed.st_dev,
                observed.st_ino,
            ):
                raise ComparisonError("temporary comparison output name changed")
            self.revalidate()
            os.link(
                temporary,
                self.output.name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            final_created = True
            self.revalidate()
            final_stat = os.stat(
                self.output.name, dir_fd=parent_descriptor, follow_symlinks=False
            )
            temporary_stat = os.stat(
                temporary, dir_fd=parent_descriptor, follow_symlinks=False
            )
            expected_object = (observed.st_dev, observed.st_ino)
            if (
                (final_stat.st_dev, final_stat.st_ino) != expected_object
                or (temporary_stat.st_dev, temporary_stat.st_ino) != expected_object
                or final_stat.st_nlink != 2
                or final_stat.st_uid != os.geteuid()
                or stat.S_IMODE(final_stat.st_mode) != 0o600
                or os.pread(descriptor, len(raw) + 1, 0) != raw
            ):
                raise ComparisonError("published comparison output identity mismatch")
            post_check()
            self.revalidate()
            os.fsync(parent_descriptor)
            os.unlink(temporary, dir_fd=parent_descriptor)
            temporary_created = False
            os.fsync(parent_descriptor)
            self.revalidate()
            final_stat = os.stat(
                self.output.name, dir_fd=parent_descriptor, follow_symlinks=False
            )
            if (
                (final_stat.st_dev, final_stat.st_ino) != expected_object
                or final_stat.st_nlink != 1
                or os.pread(descriptor, len(raw) + 1, 0) != raw
            ):
                raise ComparisonError("final comparison output changed")
            post_check()
            self.revalidate()
            final_created = False
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if final_created:
                try:
                    os.unlink(self.output.name, dir_fd=parent_descriptor)
                    os.fsync(parent_descriptor)
                except FileNotFoundError:
                    pass
            if temporary_created:
                try:
                    os.unlink(temporary, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass


def write_exclusive(path: pathlib.Path, raw: bytes) -> None:
    target = OutputTarget(path, ())
    try:
        target.publish(raw)
    finally:
        target.close()


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
    struct.pack_into("<I", raw, optional + 60, 0x200)
    struct.pack_into("<I", raw, optional + 92, 16)
    struct.pack_into("<II", raw, optional + 96 + 14 * 8, 0x1100, 0x48)
    section = optional + 0xE0
    raw[section : section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", raw, section + 8, 0x400, 0x1000, 0x400, 0x200)
    cli = 0x300
    struct.pack_into("<IHHII", raw, cli, 0x48, 2, 5, 0x1200, 0x180)
    struct.pack_into("<II", raw, cli + 16, 0x00000003, 0x06000001)
    metadata = 0x400
    struct.pack_into("<IHHII", raw, metadata, 0x424A5342, 1, 1, 0, 4)
    raw[metadata + 16 : metadata + 20] = b"v1\0\0"
    struct.pack_into("<HH", raw, metadata + 20, 0, 5)
    cursor = metadata + 24
    struct.pack_into("<II", raw, cursor, 0x80, 0x40)
    raw[cursor + 8 : cursor + 12] = b"#~\0\0"
    cursor += 12
    struct.pack_into("<II", raw, cursor, 0xC0, 0x10)
    raw[cursor + 8 : cursor + 16] = b"#GUID\0\0\0"
    cursor += 16
    struct.pack_into("<II", raw, cursor, 0xD0, 0x20)
    raw[cursor + 8 : cursor + 20] = b"#Strings\0\0\0\0"
    cursor += 20
    struct.pack_into("<II", raw, cursor, 0xF0, 0x10)
    raw[cursor + 8 : cursor + 12] = b"#US\0"
    cursor += 12
    struct.pack_into("<II", raw, cursor, 0x100, 0x10)
    raw[cursor + 8 : cursor + 16] = b"#Blob\0\0\0"
    tables = metadata + 0x80
    struct.pack_into("<IBBBBQQ", raw, tables, 0, 2, 0, 0, 1, 1 | (1 << 6), 0)
    struct.pack_into("<I", raw, tables + 24, 1)
    struct.pack_into("<I", raw, tables + 28, 1)
    struct.pack_into("<HHHHH", raw, tables + 32, 0, 1, 1, 0, 0)
    guid = metadata + 0xC0
    raw[guid : guid + 16] = mvid
    strings = metadata + 0xD0
    raw[strings + 1 : strings + 8] = b"Module\0"
    raw[0x250] = payload_byte
    return bytes(raw)


def expect_rejected(action, label: str) -> None:
    try:
        action()
    except (ComparisonError, ValueError, OSError):
        return
    raise AssertionError("accepted " + label)


def _self_test_materials() -> dict[str, object]:
    compiler_raw = b"synthetic-csc"
    compiler_ui_raw = b"synthetic-cscui"
    source_blobs = {
        name: ("synthetic-" + name).encode("ascii") for name, _expected in BOUND_SOURCES
    }
    expectations_value = {
        "clean_file_count": 1,
        "clean_manifest_bytes": 10,
        "clean_manifest_sha256": "1" * 64,
        "clean_total_bytes": 20,
        "compiler_bytes": len(compiler_raw),
        "compiler_sha256": identity(compiler_raw)["sha256"],
        "compiler_ui_bytes": len(compiler_ui_raw),
        "compiler_ui_sha256": identity(compiler_ui_raw)["sha256"],
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
        "required_api_ids": sorted(verify_output.REQUIRED_API_IDS),
        "required_tool_ids": ["csc-x86", "powershell", "python313"],
        "schema_version": 1,
    }
    expectations_raw = canonical(expectations_value)
    private_value = {
        "clean_manifest": r"C:\private\clean.tsv",
        "clean_tree": r"C:\private\clean",
        "installed_tree": r"C:\private\installed",
        "iso_file": r"C:\private\disc.iso",
        "optical_root": "D:\\",
        "schema_version": 1,
        "virtual_store_tree": r"C:\private\virtual",
    }
    private_raw = canonical(private_value)
    bound_sources = tuple(
        (name, identity(source_blobs[name])) for name, _expected in BOUND_SOURCES
    )
    profile = ComparisonProfile(
        profile_id="self-test-only",
        source_revision="1" * 40,
        expectations_identity=identity(expectations_raw),
        bound_sources=bound_sources,
    )
    return {
        "bound_sources": bound_sources,
        "compiler_raw": compiler_raw,
        "compiler_ui_raw": compiler_ui_raw,
        "expectations_raw": expectations_raw,
        "expectations_value": expectations_value,
        "private_raw": private_raw,
        "private_value": private_value,
        "profile": profile,
        "source_blobs": source_blobs,
    }


def _write_self_test_attempt(
    root: pathlib.Path,
    materials: dict[str, object],
    attempt_id: str,
    timestamp: int,
    mvid: bytes,
    observed_at_utc: str,
    elapsed_ms: int,
    payload_byte: int = 0x2A,
) -> None:
    root.mkdir(mode=0o700)
    build = root / "build"
    (build / "1033").mkdir(parents=True)
    executable_raw = build_pe_fixture(timestamp, mvid, payload_byte)
    executable_identity = identity(executable_raw)
    expectations_raw = materials["expectations_raw"]
    private_raw = materials["private_raw"]
    expectations_value = materials["expectations_value"]
    profile = materials["profile"]
    report = verify_output.synthetic_full_document(
        expectations_value, expectations_raw, private_raw
    )
    report["probe"]["source_revision"] = profile.source_revision
    report["probe"]["executable"] = executable_identity
    report["probe"]["executable_after"] = executable_identity
    report["run"]["elapsed_ms"] = elapsed_ms
    report["run"]["observed_at_utc"] = observed_at_utc
    report_raw = canonical(report)
    command_seed = attempt_id.encode("ascii")
    bindings = {
        "build_command": {
            "argument_count": len(BUILD_ROLES),
            "argv_roles": list(BUILD_ROLES),
            "sha256": hashlib.sha256(b"build-" + command_seed).hexdigest(),
        },
        "compiler": identity(materials["compiler_raw"]),
        "compiler_ui": identity(materials["compiler_ui_raw"]),
        "expectations": identity(expectations_raw),
        "private_locator": identity(private_raw),
        "probe_command": {
            "argument_count": len(PROBE_ROLES),
            "argv_roles": list(PROBE_ROLES),
            "sha256": hashlib.sha256(b"probe-" + command_seed).hexdigest(),
        },
        "probe_executable": executable_identity,
        "source_commit": profile.source_revision,
        "sources": [
            {"id": name, "identity": expected}
            for name, expected in profile.bound_sources
        ],
    }
    manifest = {
        "bindings": bindings,
        "execution": {
            "build_exit_code": 0,
            "build_stderr": EMPTY_IDENTITY,
            "build_stdout": EMPTY_IDENTITY,
            "probe_exit_code": 0,
            "probe_stderr": EMPTY_IDENTITY,
            "probe_stdout": identity(report_raw),
            "stream_cap_bytes": STREAM_CAP_BYTES,
            "timeout_seconds": TIMEOUT_SECONDS,
        },
        "harness": {"id": HARNESS_ID, "version": HARNESS_VERSION},
        "retained_artifacts": {"canonical_stdout": "probe-output.json"},
        "schema_version": SCHEMA_VERSION,
        "verification": {
            "canonical_stdout": True,
            "completeness": "complete",
            "privacy_locator_enforced": True,
            "qualification_eligible": True,
            "result": "pass",
            "safety_verdict": "eligible-for-synthetic-launcher-test",
        },
    }
    (root / "probe-output.json").write_bytes(report_raw)
    (root / "retained-run-v1.json").write_bytes(canonical(manifest))
    (build / "OriginalHostQualification.exe").write_bytes(executable_raw)
    (build / "csc.exe").write_bytes(materials["compiler_raw"])
    (build / "1033" / "cscui.dll").write_bytes(materials["compiler_ui_raw"])
    (build / "expectations.json").write_bytes(expectations_raw)
    (build / "private-locator.json").write_bytes(private_raw)
    for name, raw in materials["source_blobs"].items():
        (build / name).write_bytes(raw)


def _rewrite_self_test_report(root: pathlib.Path, mutate) -> None:
    report_path = root / "probe-output.json"
    manifest_path = root / "retained-run-v1.json"
    report = verify_output.decode_json(report_path.read_bytes())
    mutate(report)
    report_raw = canonical(report)
    manifest = verify_output.decode_json(manifest_path.read_bytes())
    manifest["execution"]["probe_stdout"] = identity(report_raw)
    report_path.write_bytes(report_raw)
    manifest_path.write_bytes(canonical(manifest))


def _replace_self_test_executable(root: pathlib.Path, executable_raw: bytes) -> None:
    report_path = root / "probe-output.json"
    manifest_path = root / "retained-run-v1.json"
    executable_path = root / "build" / "OriginalHostQualification.exe"
    observed_identity = identity(executable_raw)
    report = verify_output.decode_json(report_path.read_bytes())
    report["probe"]["executable"] = observed_identity
    report["probe"]["executable_after"] = observed_identity
    report_raw = canonical(report)
    manifest = verify_output.decode_json(manifest_path.read_bytes())
    manifest["bindings"]["probe_executable"] = observed_identity
    manifest["execution"]["probe_stdout"] = identity(report_raw)
    executable_path.write_bytes(executable_raw)
    report_path.write_bytes(report_raw)
    manifest_path.write_bytes(canonical(manifest))


def _compare_self_test_pair(
    first_path: pathlib.Path,
    second_path: pathlib.Path,
    materials: dict[str, object],
    profile: ComparisonProfile | None = None,
) -> dict[str, object]:
    first_root = RetainedRoot(first_path)
    try:
        second_root = RetainedRoot(second_path)
        try:
            return compare_attempts(
                first_root,
                second_root,
                materials["expectations_raw"],
                materials["private_raw"],
                identity(b"self-test-comparator"),
                RUNTIME_VERIFIER_IDENTITY,
                materials["profile"] if profile is None else profile,
            )
        finally:
            second_root.close()
    finally:
        first_root.close()


def _build_self_test_pair(base: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, dict[str, object]]:
    materials = _self_test_materials()
    first = base / "first"
    second = base / "second"
    _write_self_test_attempt(
        first,
        materials,
        "first",
        100,
        b"a" * 16,
        "2026-01-01T00:00:00.0000000Z",
        100,
    )
    _write_self_test_attempt(
        second,
        materials,
        "second",
        166,
        b"b" * 16,
        "2026-01-01T00:01:06.0000000Z",
        110,
    )
    return first, second, materials


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
    struct.pack_into("<H", zero_mvid, 0x400 + 0x80 + 32 + 4, 0)
    expect_rejected(lambda: parse_pe_build_identity(bytes(zero_mvid)), "zero MVID")
    truncated = first[:0x450]
    expect_rejected(lambda: parse_pe_build_identity(truncated), "truncated PE")
    overlapping = bytearray(first)
    struct.pack_into("<H", overlapping, 0x84 + 2, 2)
    second_section = 0x84 + 20 + 0xE0 + 40
    overlapping[second_section : second_section + 8] = b".alias\0\0"
    struct.pack_into("<IIII", overlapping, second_section + 8, 0x100, 0x2000, 0x100, 0x200)
    expect_rejected(lambda: parse_pe_build_identity(bytes(overlapping)), "overlapping PE sections")
    for offset, width, value, label in (
        (0x300 + 16, 4, 0, "CLI flags"),
        (0x300 + 20, 4, 0x06000002, "CLI entrypoint row"),
        (0x400 + 4, 2, 99, "metadata major version"),
        (0x400 + 8, 4, 1, "metadata reserved field"),
        (0x400 + 0x80, 4, 1, "tables reserved field"),
        (0x400 + 0x80 + 7, 1, 0, "tables reserved byte"),
        (0x400 + 0x80 + 28, 4, 42, "truncated declared MethodDef table"),
        (0x400 + 0x80 + 32, 2, 1, "Module generation"),
        (0x400 + 0x80 + 34, 2, 0, "Module name"),
        (0x400 + 0x80 + 38, 2, 1, "Module EncId"),
        (0x400 + 0x80 + 40, 2, 1, "Module EncBaseId"),
        (0x400 + 24 + 4, 4, 42, "truncated entrypoint MethodDef row"),
        (0x400 + 0x38, 4, 0, "Strings heap size"),
        (0x400 + 0x4C, 4, 0, "US heap size"),
        (0x400 + 0x58, 4, 0, "Blob heap size"),
        (0x400 + 0xD0, 1, 1, "Strings heap sentinel"),
        (0x400 + 0xF0, 1, 1, "US heap sentinel"),
        (0x400 + 0x100, 1, 1, "Blob heap sentinel"),
    ):
        malformed = bytearray(first)
        if width == 1:
            malformed[offset] = value
        elif width == 2:
            struct.pack_into("<H", malformed, offset, value)
        else:
            struct.pack_into("<I", malformed, offset, value)
        expect_rejected(lambda raw=bytes(malformed): parse_pe_build_identity(raw), label)
    exact_method_boundary = bytearray(first)
    struct.pack_into("<I", exact_method_boundary, 0x400 + 24 + 4, 56)
    parse_pe_build_identity(bytes(exact_method_boundary))
    for declared_rows in (2, 0x10000, 0xFFFFFFFF):
        missing_methods = bytearray(first)
        struct.pack_into("<I", missing_methods, 0x400 + 0x80 + 28, declared_rows)
        expect_rejected(
            lambda raw=bytes(missing_methods): parse_pe_build_identity(raw),
            f"truncated MethodDef table with {declared_rows} declared rows",
        )
    missing_entrypoint = bytearray(exact_method_boundary)
    struct.pack_into("<I", missing_entrypoint, 0x400 + 0x80 + 28, 2)
    struct.pack_into("<I", missing_entrypoint, 0x300 + 20, 0x06000002)
    expect_rejected(
        lambda: parse_pe_build_identity(bytes(missing_entrypoint)),
        "entrypoint RID beyond physically present MethodDef rows",
    )
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        output = root / "result.json"
        write_exclusive(output, canonical({"schema_version": 1}))
        expect_rejected(
            lambda: write_exclusive(output, canonical({"schema_version": 1})),
            "comparison output replacement",
        )
        if output.read_bytes() != canonical({"schema_version": 1}):
            raise AssertionError("atomic output contents")

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        parent = root / "parent"
        parent.mkdir(mode=0o700)
        target = OutputTarget(parent / "result.json", ())
        try:
            moved = root / "moved"
            parent.rename(moved)
            parent.mkdir(mode=0o700)
            expect_rejected(
                lambda: target.publish(canonical({"schema_version": 1})),
                "output ancestor replacement",
            )
            if (parent / "result.json").exists() or (moved / "result.json").exists():
                raise AssertionError("detached output publication")
        finally:
            target.close()

    repository = pathlib.Path(__file__).resolve(strict=True).parents[3]
    public_expectations = repository / "config" / "original-host-qualification-v1.json"
    if public_expectations.exists() and identity(read_plain(public_expectations, 1024 * 1024)) != PUBLIC_EXPECTATIONS_IDENTITY:
        raise AssertionError("production expectations identity")

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        first_path, second_path, materials = _build_self_test_pair(root)
        result = _compare_self_test_pair(first_path, second_path, materials)
        if result["summary"] != {
            "original_behavior_qualified": False,
            "original_execution_status": "not-run",
            "stability_verdict": "pe-build-identity-normalized-stable",
        }:
            raise AssertionError("retained pair gate boundary")
        if result["comparison"]["observed_report_difference_paths"] != list(ALLOWED_REPORT_DIFFERENCES):
            raise AssertionError("retained pair difference allowlist")
        if (
            result["comparison"]["different_probe_byte_count"] != 17
            or result["comparison"]["timestamp_different_byte_count"] != 1
            or result["comparison"]["mvid_different_byte_count"] != 16
            or result["comparison"]["timestamp_delta_seconds"] != 66
        ):
            raise AssertionError("retained pair PE difference classification")
        if canonical(verify_output.decode_json(canonical(result))) != canonical(result):
            raise AssertionError("retained pair canonical output")
        verify_output.reject_path_like_strings(result)

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        _rewrite_self_test_report(second_path, lambda report: report["host"].__setitem__("os_build", 2))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "fifth report difference",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        report_path = second_path / "probe-output.json"
        report = verify_output.decode_json(report_path.read_bytes())
        executable_path = second_path / "build" / "OriginalHostQualification.exe"
        changed = bytearray(executable_path.read_bytes())
        changed[0x250] ^= 1
        changed_raw = bytes(changed)
        changed_identity = identity(changed_raw)
        report["probe"]["executable"] = changed_identity
        report["probe"]["executable_after"] = changed_identity
        report_raw = canonical(report)
        manifest_path = second_path / "retained-run-v1.json"
        manifest = verify_output.decode_json(manifest_path.read_bytes())
        manifest["bindings"]["probe_executable"] = changed_identity
        manifest["execution"]["probe_stdout"] = identity(report_raw)
        executable_path.write_bytes(changed_raw)
        report_path.write_bytes(report_raw)
        manifest_path.write_bytes(canonical(manifest))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "probe payload difference",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        _rewrite_self_test_report(
            second_path,
            lambda report: report["probe"]["executable_after"].__setitem__("sha256", "0" * 64),
        )
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "within-run image contradiction",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        report_path = second_path / "probe-output.json"
        report = verify_output.decode_json(report_path.read_bytes())
        report["run"]["elapsed_ms"] += 1
        report_path.write_bytes(canonical(report))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "report manifest binding",
        )

    for relative in (
        "build/csc.exe",
        "build/CanonicalJson.cs",
        "build/expectations.json",
    ):
        with tempfile.TemporaryDirectory() as directory:
            first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
            target = second_path / pathlib.PurePosixPath(relative)
            target.write_bytes(target.read_bytes() + b"x")
            expect_rejected(
                lambda: _compare_self_test_pair(first_path, second_path, materials),
                "retained artifact rebinding " + relative,
            )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        manifest_path = second_path / "retained-run-v1.json"
        manifest = verify_output.decode_json(manifest_path.read_bytes())
        first_manifest = verify_output.decode_json((first_path / "retained-run-v1.json").read_bytes())
        manifest["bindings"]["build_command"] = first_manifest["bindings"]["build_command"]
        manifest_path.write_bytes(canonical(manifest))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "reused command binding",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        _rewrite_self_test_report(
            second_path,
            lambda report: report["run"].__setitem__(
                "observed_at_utc", "2026-01-01T00:00:00.0000000Z"
            ),
        )
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "reversed report chronology",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        _replace_self_test_executable(second_path, build_pe_fixture(99, b"b" * 16))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "reversed build chronology",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        _replace_self_test_executable(
            second_path,
            (first_path / "build" / "OriginalHostQualification.exe").read_bytes(),
        )
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "reused probe build",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        _rewrite_self_test_report(
            second_path,
            lambda report: report["probe"].__setitem__("source_revision", "2" * 40),
        )
        manifest_path = second_path / "retained-run-v1.json"
        manifest = verify_output.decode_json(manifest_path.read_bytes())
        manifest["bindings"]["source_commit"] = "2" * 40
        manifest_path.write_bytes(canonical(manifest))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "producer tuple drift",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))

        def make_unsafe(report):
            report["guards"]["game_process_count_after"] = 1
            check = next(
                item for item in report["checks"] if item["id"] == "no-game-process-after"
            )
            check["outcome"] = "fail"
            check["detail_code"] = "present"
            report["summary"]["passed_count"] -= 1
            report["summary"]["failed_count"] += 1
            report["summary"]["safety_verdict"] = "unsafe"

        _rewrite_self_test_report(second_path, make_unsafe)
        manifest_path = second_path / "retained-run-v1.json"
        manifest = verify_output.decode_json(manifest_path.read_bytes())
        manifest["verification"]["qualification_eligible"] = False
        manifest["verification"]["result"] = "fail"
        manifest["verification"]["safety_verdict"] = "unsafe"
        manifest_path.write_bytes(canonical(manifest))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "noneligible retained report",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        private_value = materials["private_value"]
        _rewrite_self_test_report(
            second_path,
            lambda report: report["host"].__setitem__("edition", private_value["clean_tree"]),
        )
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "private path disclosure",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        second_compiler = second_path / "build" / "csc.exe"
        second_compiler.unlink()
        os.link(first_path / "build" / "csc.exe", second_compiler)
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, second_path, materials),
            "cross-attempt hardlink",
        )

    with tempfile.TemporaryDirectory() as directory:
        first_path, second_path, materials = _build_self_test_pair(pathlib.Path(directory))
        expect_rejected(
            lambda: _compare_self_test_pair(first_path, first_path, materials),
            "same retained root",
        )
        first_root = RetainedRoot(first_path)
        try:
            nested_root = RetainedRoot(first_path / "build")
            try:
                expect_rejected(
                    lambda: OutputTarget(
                        first_path / "comparison.json", (first_root, nested_root)
                    ),
                    "comparison output overlap",
                )
                expect_rejected(
                    lambda: compare_attempts(
                        first_root,
                        nested_root,
                        materials["expectations_raw"],
                        materials["private_raw"],
                        identity(b"self-test-comparator"),
                        RUNTIME_VERIFIER_IDENTITY,
                        materials["profile"],
                    ),
                    "nested retained root",
                )
            finally:
                nested_root.close()
        finally:
            first_root.close()
        alias_nested = pathlib.Path("//" + str(first_path / "build").lstrip("/"))
        alias_first_root = RetainedRoot(first_path)
        try:
            alias_nested_root = RetainedRoot(alias_nested)
            try:
                expect_rejected(
                    lambda: compare_attempts(
                        alias_first_root,
                        alias_nested_root,
                        materials["expectations_raw"],
                        materials["private_raw"],
                        identity(b"self-test-comparator"),
                        RUNTIME_VERIFIER_IDENTITY,
                        materials["profile"],
                    ),
                    "alternate-spelling nested root",
                )
                expect_rejected(
                    lambda: OutputTarget(
                        pathlib.Path("//" + str(first_path).lstrip("/"))
                        / "comparison.json",
                        (alias_first_root,),
                    ),
                    "alternate-spelling output overlap",
                )
            finally:
                alias_nested_root.close()
        finally:
            alias_first_root.close()
        mount_first_root = RetainedRoot(first_path)
        try:
            mount_second_root = RetainedRoot(second_path)
            try:
                mount_second_root.root_mount_id += 1
                expect_rejected(
                    lambda: compare_attempts(
                        mount_first_root,
                        mount_second_root,
                        materials["expectations_raw"],
                        materials["private_raw"],
                        identity(b"self-test-comparator"),
                        RUNTIME_VERIFIER_IDENTITY,
                        materials["profile"],
                    ),
                    "different retained mount views",
                )
            finally:
                mount_second_root.close()
        finally:
            mount_first_root.close()
        mount_output_root = RetainedRoot(first_path)
        try:
            mount_output_root.root_mount_id += 1
            expect_rejected(
                lambda: OutputTarget(
                    pathlib.Path(directory) / "mount-output.json", (mount_output_root,)
                ),
                "different output mount view",
            )
        finally:
            mount_output_root.close()
        expect_rejected(
            lambda: _compare_self_test_pair(
                first_path, second_path, materials, PRODUCTION_PROFILE
            ),
            "production expectations profile mismatch",
        )

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        attempt = root / "attempt"
        attempt.mkdir()
        artifact = attempt / "artifact.bin"
        artifact.write_bytes(b"before")
        held = RetainedRoot(attempt)
        try:
            held.read("artifact.bin")
            artifact.write_bytes(b"after!")
            expect_rejected(held.revalidate, "same-size retained byte mutation")
        finally:
            held.close()

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        parent = root / "parent"
        attempt = parent / "attempt"
        attempt.mkdir(parents=True)
        (attempt / "artifact.bin").write_bytes(b"stable")
        held = RetainedRoot(attempt)
        try:
            held.read("artifact.bin")
            moved = root / "moved"
            parent.rename(moved)
            parent.mkdir()
            expect_rejected(held.revalidate, "retained ancestor replacement")
        finally:
            held.close()

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        script = root / "comparator.py"
        verifier = root / "verify_output.py"
        script.write_bytes(b"# comparator\n")
        verifier_raw = read_plain(pathlib.Path(verify_output.__file__), 1024 * 1024)
        verifier.write_bytes(verifier_raw)
        _load_bound_verifier_from(script, verifier, identity(verifier_raw))
        verifier.write_bytes(verifier_raw + b"# altered\n")
        expect_rejected(
            lambda: _load_bound_verifier_from(script, verifier, identity(verifier_raw)),
            "altered runtime verifier",
        )
        external = root / "external"
        external.mkdir()
        external_verifier = external / "verify_output.py"
        external_verifier.write_bytes(verifier_raw)
        expect_rejected(
            lambda: _load_bound_verifier_from(script, external_verifier, identity(verifier_raw)),
            "external runtime verifier",
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
    expectations_raw = read_plain(args.expectations, 1024 * 1024)
    private_raw = read_plain(args.private_locator, 1024 * 1024)
    implementation_path = pathlib.Path(__file__).absolute()
    implementation_identity = identity(read_plain(implementation_path, 1024 * 1024))
    runtime_path = pathlib.Path(verify_output.__file__).absolute()
    runtime_identity = identity(read_plain(runtime_path, 1024 * 1024))
    if runtime_path != implementation_path.with_name("verify_output.py") or runtime_identity != RUNTIME_VERIFIER_IDENTITY:
        raise ComparisonError("runtime verifier changed after load")
    first_root = RetainedRoot(args.first_dir)
    try:
        second_root = RetainedRoot(args.second_dir)
        try:
            target = OutputTarget(args.output, (first_root, second_root))
            try:
                result = compare_attempts(
                    first_root,
                    second_root,
                    expectations_raw,
                    private_raw,
                    implementation_identity,
                    runtime_identity,
                    PRODUCTION_PROFILE,
                )
                first_root.revalidate()
                second_root.revalidate()
                target.publish(
                    canonical(result),
                    lambda: (first_root.revalidate(), second_root.revalidate()),
                )
            finally:
                target.close()
        finally:
            second_root.close()
    finally:
        first_root.close()
    print("PASS " + identity(canonical(result))["sha256"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ComparisonError, OSError, ValueError, AssertionError, json.JSONDecodeError) as error:
        print("FAIL: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
