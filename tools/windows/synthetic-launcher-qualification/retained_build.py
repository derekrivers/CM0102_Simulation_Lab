#!/usr/bin/env python3
"""Retained, path-private build evidence for the harmless synthetic fixture.

The only produced executable this harness runs is SyntheticFixtureTests.exe.
SyntheticLauncherFixture.exe is compiled and structurally inspected, never run.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time


SCHEMA_VERSION = 1
HARNESS_ID = "cm0102-synthetic-fixture-retained-build"
HARNESS_VERSION = "1.0.0"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_STREAM_BYTES = 256 * 1024
BUILD_TIMEOUT_SECONDS = 300
TEST_TIMEOUT_SECONDS = 60
EXPECTED_TEST_STDOUT = b"PASS 230518\r\n"
EXPECTED_CSC_SHA256 = "012e8cd8adff0c439a90ffd22c0e33efeb6fbc8cf660d52b4858d310649382fa"
EXPECTED_CSCUI_SHA256 = "5d925200762a6b25467da367c622883c3616c21edfaaad9548fd085d5d48757f"
EXPECTED_CSC_WINDOWS = r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
EXPECTED_CSCUI_WINDOWS = r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\1033\cscui.dll"
FRAMEWORK_NAMES = (
    "mscorlib.dll",
    "System.dll",
    "System.Core.dll",
    "System.Drawing.dll",
    "System.Security.dll",
    "System.Windows.Forms.dll",
)
SOURCE_PATHS = {
    "fixture_source": "tools/windows/synthetic-launcher-qualification/SyntheticFixture.cs",
    "test_source": "tools/windows/synthetic-launcher-qualification/SyntheticFixtureTests.cs",
    "profile": "config/synthetic-launcher-fixture-v1.json",
    "verifier": "tools/windows/synthetic-launcher-qualification/verify_fixture.py",
    "harness": "tools/windows/synthetic-launcher-qualification/retained_build.py",
}
SNAPSHOT_NAMES = {
    "fixture_source": "SyntheticFixture.cs",
    "test_source": "SyntheticFixtureTests.cs",
    "profile": "synthetic-launcher-fixture-v1.json",
    "verifier": "verify_fixture.py",
    "harness": "retained_build.py",
}
ARTIFACT_PATHS = {
    "fixture_source_snapshot": ("inputs", "SyntheticFixture.cs"),
    "test_source_snapshot": ("inputs", "SyntheticFixtureTests.cs"),
    "profile_snapshot": ("inputs", "synthetic-launcher-fixture-v1.json"),
    "verifier_snapshot": ("inputs", "verify_fixture.py"),
    "harness_snapshot": ("inputs", "retained_build.py"),
    "compiler_snapshot": ("build", "csc.exe"),
    "compiler_ui_snapshot": ("build", "1033", "cscui.dll"),
    "fixture_executable": ("build", "SyntheticLauncherFixture.exe"),
    "test_executable": ("build", "SyntheticFixtureTests.exe"),
    "fixture_build_stdout": ("build", "fixture-build.stdout"),
    "fixture_build_stderr": ("build", "fixture-build.stderr"),
    "test_build_stdout": ("build", "test-build.stdout"),
    "test_build_stderr": ("build", "test-build.stderr"),
    "test_stdout": ("build", "test.stdout"),
    "test_stderr": ("build", "test.stderr"),
}


class HarnessError(Exception):
    pass


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def identity_bytes(value: bytes) -> dict[str, object]:
    return {"byte_count": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def stat_fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_plain(path: pathlib.Path, maximum: int = MAX_FILE_BYTES, single_link: bool = False) -> tuple[bytes, dict[str, object]]:
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise HarnessError("input is not a plain regular file")
    if single_link and before.st_nlink != 1:
        raise HarnessError("retained file link count is not one")
    if before.st_size < 0 or before.st_size > maximum:
        raise HarnessError("input exceeds byte limit")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if stat_fingerprint(opened) != stat_fingerprint(before):
            raise HarnessError("input changed before open")
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(descriptor, min(65536, maximum + 1 - observed))
            if not chunk:
                break
            observed += len(chunk)
            if observed > maximum:
                raise HarnessError("input grew beyond byte limit")
            chunks.append(chunk)
        finished = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = path.stat(follow_symlinks=False)
    if not (stat_fingerprint(before) == stat_fingerprint(finished) == stat_fingerprint(after)):
        raise HarnessError("input changed while read")
    raw = b"".join(chunks)
    if len(raw) != before.st_size:
        raise HarnessError("input length changed")
    return raw, identity_bytes(raw)


def require_absolute_canonical(path: pathlib.Path, kind: str) -> pathlib.Path:
    if not path.is_absolute():
        raise HarnessError(kind + " must be absolute")
    absolute = pathlib.Path(os.path.normpath(os.fspath(path)))
    resolved = absolute.resolve(strict=True)
    if absolute != resolved:
        raise HarnessError(kind + " must be canonical and contain no symlink")
    return resolved


def private_parent(path: pathlib.Path) -> pathlib.Path:
    if not path.is_absolute():
        raise HarnessError("retained directory must be absolute")
    absolute = pathlib.Path(os.path.normpath(os.fspath(path)))
    if absolute.exists() or absolute.is_symlink():
        raise HarnessError("retained directory already exists")
    parent = require_absolute_canonical(absolute.parent, "retained parent")
    metadata = parent.stat(follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode):
        raise HarnessError("retained parent is not a directory")
    if os.name != "nt":
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise HarnessError("retained parent must be owned and mode 0700")
    return parent / absolute.name


def write_exclusive(path: pathlib.Path, raw: bytes, executable: bool = False) -> dict[str, object]:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        if os.name != "nt":
            os.chmod(path, 0o700 if executable else 0o400)
        observed_raw, observed = read_plain(path, single_link=True)
        if observed_raw != raw:
            raise HarnessError("retained write readback mismatch")
        return observed
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def find_git() -> pathlib.Path:
    if os.name != "nt" and pathlib.Path("/usr/bin/git").is_file():
        return pathlib.Path("/usr/bin/git")
    located = shutil.which("git")
    if not located:
        raise HarnessError("Git is unavailable")
    return pathlib.Path(located).resolve(strict=True)


def kill_process(process: subprocess.Popen[bytes]) -> None:
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except (ProcessLookupError, PermissionError):
            pass
    try:
        process.kill()
    except ProcessLookupError:
        pass


def capture_bounded(
    argv: list[str], cwd: pathlib.Path, environment: dict[str, str], timeout: float, cap: int
) -> tuple[int, bytes, bytes]:
    if not argv or not os.path.isabs(argv[0]):
        raise HarnessError("command executable must be absolute")
    process = subprocess.Popen(
        argv,
        cwd=os.fspath(cwd),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    output = [bytearray(), bytearray()]
    overflow = threading.Event()

    def drain(index: int, pipe: object) -> None:
        reader = pipe
        while True:
            chunk = reader.read(65536)  # type: ignore[attr-defined]
            if not chunk:
                return
            remaining = cap + 1 - len(output[index])
            if remaining > 0:
                output[index].extend(chunk[:remaining])
            if len(output[index]) > cap:
                overflow.set()
                return

    threads = (
        threading.Thread(target=drain, args=(0, process.stdout), daemon=True),
        threading.Thread(target=drain, args=(1, process.stderr), daemon=True),
    )
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    failure = None
    while process.poll() is None:
        if overflow.is_set():
            failure = "command stream exceeded cap"
            kill_process(process)
            break
        if time.monotonic() >= deadline:
            failure = "command timed out"
            kill_process(process)
            break
        time.sleep(0.01)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired as error:
        kill_process(process)
        raise HarnessError("command could not be terminated") from error
    for thread in threads:
        thread.join(timeout=2)
    if any(thread.is_alive() for thread in threads):
        raise HarnessError("stream capture did not terminate")
    if failure or overflow.is_set():
        raise HarnessError(failure or "command stream exceeded cap")
    return process.returncode, bytes(output[0]), bytes(output[1])


def git_command(repo: pathlib.Path, arguments: list[str], maximum: int = 2 * 1024 * 1024) -> bytes:
    git = find_git()
    environment = {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "LANG": "C",
        "LC_ALL": "C",
    }
    if os.name == "nt":
        environment["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
        environment["WINDIR"] = environment["SystemRoot"]
    code, stdout, stderr = capture_bounded(
        [os.fspath(git), "--no-replace-objects", "-C", os.fspath(repo), *arguments],
        repo,
        environment,
        20,
        maximum,
    )
    if code != 0 or stderr:
        raise HarnessError("Git command failed")
    return stdout


def source_bindings(repo: pathlib.Path, commit: str) -> tuple[dict[str, object], dict[str, bytes]]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise HarnessError("source commit must be full lowercase SHA-1")
    top = pathlib.Path(git_command(repo, ["rev-parse", "--show-toplevel"]).decode("utf-8", "strict").strip()).resolve(strict=True)
    if top != repo:
        raise HarnessError("repository root mismatch")
    if git_command(repo, ["cat-file", "-t", commit]) != b"commit\n":
        raise HarnessError("source object is not a commit")
    resolved = git_command(repo, ["rev-parse", commit + "^{commit}"]).decode("ascii", "strict").strip()
    if resolved != commit:
        raise HarnessError("source commit did not resolve exactly")
    records: dict[str, object] = {}
    snapshots: dict[str, bytes] = {}
    for role, relative in SOURCE_PATHS.items():
        repository_file = require_absolute_canonical(repo / pathlib.PurePosixPath(relative), role)
        working_raw, working_identity = read_plain(repository_file, single_link=True)
        committed = git_command(repo, ["show", commit + ":" + relative])
        if working_raw != committed:
            raise HarnessError("working source differs from source commit")
        blob = git_command(repo, ["rev-parse", commit + ":" + relative]).decode("ascii", "strict").strip()
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", blob):
            raise HarnessError("invalid Git blob identity")
        if git_command(repo, ["cat-file", "-t", blob]) != b"blob\n":
            raise HarnessError("bound Git object is not a blob")
        records[role] = {"git_blob": blob, "identity": working_identity}
        snapshots[role] = committed
    expected_harness = repo / pathlib.PurePosixPath(SOURCE_PATHS["harness"])
    if pathlib.Path(__file__).absolute() != expected_harness:
        raise HarnessError("running harness is not the canonical repository file")
    return records, snapshots


def validate_profile(raw: bytes, snapshots: dict[str, bytes]) -> None:
    try:
        value = json.loads(raw.decode("ascii", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HarnessError("profile is not canonical JSON") from error
    if not isinstance(value, dict) or canonical(value) != raw:
        raise HarnessError("profile is not canonical JSON")
    if set(value) != {"fixture", "profile", "schema_version", "tests"} or value["schema_version"] != 1:
        raise HarnessError("profile schema mismatch")
    if value["fixture"] != identity_bytes(snapshots["fixture_source"]):
        raise HarnessError("profile fixture identity mismatch")
    if value["tests"] != identity_bytes(snapshots["test_source"]):
        raise HarnessError("profile test identity mismatch")
    if not isinstance(value["profile"], dict) or value["profile"].get("schema_version") != 1:
        raise HarnessError("fixture profile payload mismatch")
    try:
        verifier_tree = ast.parse(snapshots["verifier"].decode("utf-8", "strict"))
        assignments = [
            node for node in verifier_tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "PROFILE" for target in node.targets)
        ]
        if len(assignments) != 1 or ast.literal_eval(assignments[0].value) != value["profile"]:
            raise HarnessError("profile differs from verifier constant")
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise HarnessError("verifier profile constant is invalid") from error


def is_wsl() -> bool:
    if os.name == "nt":
        return False
    try:
        return "microsoft" in pathlib.Path("/proc/sys/kernel/osrelease").read_text(encoding="ascii").lower()
    except OSError:
        return False


def to_windows_path(path: pathlib.Path) -> str:
    resolved = path.resolve(strict=True)
    if os.name == "nt":
        return os.fspath(resolved)
    if not is_wsl() or not pathlib.Path("/usr/bin/wslpath").is_file():
        raise HarnessError("run mode requires native Windows or WSL")
    code, stdout, stderr = capture_bounded(
        ["/usr/bin/wslpath", "-w", "--", os.fspath(resolved)],
        pathlib.Path("/"),
        {"LANG": "C", "LC_ALL": "C"},
        10,
        4096,
    )
    if code != 0 or stderr:
        raise HarnessError("wslpath failed")
    try:
        result = stdout.decode("utf-8", "strict").rstrip("\r\n")
    except UnicodeDecodeError as error:
        raise HarnessError("wslpath output encoding") from error
    if not result or "\r" in result or "\n" in result:
        raise HarnessError("wslpath output shape")
    return result


def windows_key(value: str) -> str:
    return value.replace("/", "\\").rstrip("\\").casefold()


def to_windows_child(path: pathlib.Path) -> str:
    if not path.is_absolute() or not path.name or path.name in {".", ".."}:
        raise HarnessError("Windows child path is invalid")
    parent = require_absolute_canonical(path.parent, "Windows child parent")
    if path.exists() or path.is_symlink():
        existing = require_absolute_canonical(path, "Windows child")
        if existing.parent != parent:
            raise HarnessError("Windows child parent changed")
    parent_windows = to_windows_path(parent)
    separator = "" if parent_windows.endswith(("\\", "/")) else "\\"
    return parent_windows + separator + path.name


def compiler_inputs(compiler_argument: pathlib.Path) -> tuple[pathlib.Path, bytes, dict[str, object], pathlib.Path, bytes, dict[str, object], dict[str, tuple[pathlib.Path, dict[str, object]]]]:
    compiler = require_absolute_canonical(compiler_argument, "compiler")
    if windows_key(to_windows_path(compiler)) != windows_key(EXPECTED_CSC_WINDOWS):
        raise HarnessError("compiler is not canonical x86 Framework csc.exe")
    compiler_raw, compiler_identity = read_plain(compiler)
    if compiler_identity["sha256"] != EXPECTED_CSC_SHA256:
        raise HarnessError("compiler SHA-256 mismatch")
    compiler_ui = require_absolute_canonical(compiler.parent / "1033" / "cscui.dll", "compiler UI")
    if windows_key(to_windows_path(compiler_ui)) != windows_key(EXPECTED_CSCUI_WINDOWS):
        raise HarnessError("compiler UI is not canonical cscui.dll")
    compiler_ui_raw, compiler_ui_identity = read_plain(compiler_ui)
    if compiler_ui_identity["sha256"] != EXPECTED_CSCUI_SHA256:
        raise HarnessError("compiler UI SHA-256 mismatch")
    references: dict[str, tuple[pathlib.Path, dict[str, object]]] = {}
    for name in FRAMEWORK_NAMES:
        reference = require_absolute_canonical(compiler.parent / name, "framework reference")
        expected = EXPECTED_CSC_WINDOWS.rsplit("\\", 1)[0] + "\\" + name
        if windows_key(to_windows_path(reference)) != windows_key(expected):
            raise HarnessError("framework reference is not canonical x86 Framework")
        references[name] = (reference, read_plain(reference)[1])
    return compiler, compiler_raw, compiler_identity, compiler_ui, compiler_ui_raw, compiler_ui_identity, references


def command_binding(argv: list[str], roles: list[str]) -> dict[str, object]:
    if len(argv) != len(roles):
        raise HarnessError("command role count mismatch")
    return {
        "argument_count": len(argv),
        "argv_roles": roles,
        "sha256": hashlib.sha256(canonical(argv)).hexdigest(),
    }


def minimal_environment(build: pathlib.Path) -> tuple[dict[str, str], dict[str, object]]:
    windows_build = to_windows_path(build)
    values = {
        "SystemRoot": r"C:\Windows",
        "TEMP": windows_build,
        "TMP": windows_build,
        "WINDIR": r"C:\Windows",
    }
    binding = {
        "names": sorted(values),
        "sha256": hashlib.sha256(canonical(values)).hexdigest(),
    }
    return values, binding


def build_arguments(
    compiler_snapshot: pathlib.Path,
    output: pathlib.Path,
    sources: list[pathlib.Path],
    references: dict[str, tuple[pathlib.Path, dict[str, object]]],
    target: str,
    main: str,
) -> tuple[list[str], list[str]]:
    reference_arguments = ["/r:" + to_windows_path(references[name][0]) for name in FRAMEWORK_NAMES]
    argv = [
        os.fspath(compiler_snapshot),
        "/nologo",
        "/noconfig",
        "/nostdlib+",
        "/warnaserror+",
        "/optimize+",
        "/debug-",
        "/platform:x86",
        "/target:" + target,
        "/main:" + main,
        *reference_arguments,
        "/out:" + to_windows_child(output),
        *(to_windows_path(source) for source in sources),
    ]
    roles = [
        "compiler",
        "nologo",
        "no-default-response-file",
        "no-standard-library",
        "warnings-as-errors",
        "optimized",
        "no-debug-output",
        "platform-x86",
        "target-" + target,
        "entrypoint",
        *("reference-" + name.casefold() for name in FRAMEWORK_NAMES),
        "output",
        *("source-" + source.name.casefold() for source in sources),
    ]
    return argv, roles


def map_rva(raw: bytes, sections: list[tuple[int, int, int, int]], rva: int, size: int) -> int:
    if rva <= 0 or size <= 0:
        raise HarnessError("PE directory is empty")
    for virtual_address, virtual_size, raw_pointer, raw_size in sections:
        span = max(virtual_size, raw_size)
        if virtual_address <= rva and rva + size <= virtual_address + span:
            offset = raw_pointer + rva - virtual_address
            if rva + size > virtual_address + raw_size or offset + size > len(raw):
                raise HarnessError("PE directory is not file-backed")
            return offset
    raise HarnessError("PE directory is outside sections")


def metadata_index_size(rows: list[int], table: int) -> int:
    return 2 if rows[table] < 0x10000 else 4


def coded_index_size(rows: list[int], tables: tuple[int, ...], tag_bits: int) -> int:
    limit = 1 << (16 - tag_bits)
    return 2 if max(rows[table] for table in tables) < limit else 4


def compressed_unsigned(raw: bytes, offset: int, limit: int) -> tuple[int, int]:
    if offset >= limit:
        raise HarnessError("metadata blob index is outside stream")
    first = raw[offset]
    if first & 0x80 == 0:
        return first, 1
    if first & 0xC0 == 0x80:
        if offset + 2 > limit:
            raise HarnessError("metadata blob length is truncated")
        return ((first & 0x3F) << 8) | raw[offset + 1], 2
    if first & 0xE0 == 0xC0:
        if offset + 4 > limit:
            raise HarnessError("metadata blob length is truncated")
        return (
            ((first & 0x1F) << 24)
            | (raw[offset + 1] << 16)
            | (raw[offset + 2] << 8)
            | raw[offset + 3],
            4,
        )
    raise HarnessError("metadata blob length prefix is invalid")


def validate_cli_metadata(
    raw: bytes,
    sections: list[tuple[int, int, int, int]],
    metadata_rva: int,
    metadata_size: int,
    entrypoint: int,
) -> dict[str, object]:
    metadata = map_rva(raw, sections, metadata_rva, metadata_size)
    end = metadata + metadata_size
    if metadata_size < 32 or raw[metadata:metadata + 4] != b"BSJB":
        raise HarnessError("CLI metadata root signature is invalid")
    major, minor = struct.unpack_from("<HH", raw, metadata + 4)
    reserved, version_length = struct.unpack_from("<II", raw, metadata + 8)
    if major not in (1, 2) or minor > 1 or reserved != 0 or not (1 <= version_length <= 256):
        raise HarnessError("CLI metadata root header is invalid")
    version_start = metadata + 16
    version_end = version_start + version_length
    if version_end > end or raw[version_end - 1] != 0:
        raise HarnessError("CLI metadata version is invalid")
    version_field = raw[version_start:version_end]
    terminator = version_field.find(b"\0")
    if terminator <= 0 or any(version_field[terminator:]):
        raise HarnessError("CLI metadata version padding is invalid")
    version = version_field[:terminator]
    if not version or any(byte < 0x20 or byte > 0x7E for byte in version):
        raise HarnessError("CLI metadata version is not printable ASCII")
    cursor = (version_end + 3) & ~3
    if cursor + 4 > end:
        raise HarnessError("CLI metadata stream header is truncated")
    flags, stream_count = struct.unpack_from("<HH", raw, cursor)
    cursor += 4
    if flags != 0 or not (3 <= stream_count <= 8):
        raise HarnessError("CLI metadata stream count or flags are invalid")
    streams: dict[str, tuple[int, int]] = {}
    stream_ranges: list[tuple[int, int]] = []
    allowed_streams = {"#~", "#-", "#Strings", "#US", "#GUID", "#Blob", "#Pdb"}
    for _ in range(stream_count):
        if cursor + 9 > end:
            raise HarnessError("CLI metadata stream descriptor is truncated")
        stream_offset, stream_size = struct.unpack_from("<II", raw, cursor)
        name_start = cursor + 8
        name_limit = min(name_start + 32, end)
        terminator = raw.find(b"\0", name_start, name_limit)
        if terminator < 0:
            raise HarnessError("CLI metadata stream name is unterminated")
        try:
            name = raw[name_start:terminator].decode("ascii", "strict")
        except UnicodeDecodeError as error:
            raise HarnessError("CLI metadata stream name is not ASCII") from error
        cursor = (terminator + 4) & ~3
        if name not in allowed_streams or name in streams or stream_offset % 4 != 0 or stream_size <= 0:
            raise HarnessError("CLI metadata stream descriptor is invalid")
        stream_start = metadata + stream_offset
        stream_end = stream_start + stream_size
        if stream_start < cursor or stream_end > end:
            raise HarnessError("CLI metadata stream range is invalid")
        streams[name] = (stream_start, stream_end)
        stream_ranges.append((stream_start, stream_end))
    if any(stream_start < cursor for stream_start, _ in stream_ranges):
        raise HarnessError("CLI metadata stream overlaps descriptors")
    stream_ranges.sort()
    if any(left[1] > right[0] for left, right in zip(stream_ranges, stream_ranges[1:])):
        raise HarnessError("CLI metadata streams overlap")
    table_names = [name for name in ("#~", "#-") if name in streams]
    if len(table_names) != 1 or "#Strings" not in streams or "#Blob" not in streams:
        raise HarnessError("CLI metadata required streams are missing")
    table_start, table_end = streams[table_names[0]]
    if table_start + 24 > table_end:
        raise HarnessError("CLI metadata tables header is truncated")
    table_reserved = struct.unpack_from("<I", raw, table_start)[0]
    table_major, table_minor, heap_sizes, table_reserved2 = struct.unpack_from("<BBBB", raw, table_start + 4)
    valid, sorted_mask = struct.unpack_from("<QQ", raw, table_start + 8)
    if (
        table_reserved != 0
        or table_major != 2
        or table_minor != 0
        or heap_sizes & ~0x07
        or table_reserved2 != 1
        or sorted_mask >> 45
        or valid >> 45
        or valid & (1 << 6) == 0
    ):
        raise HarnessError("CLI metadata tables header is invalid")
    rows = [0] * 64
    table_cursor = table_start + 24
    for table in range(64):
        if valid & (1 << table):
            if table_cursor + 4 > table_end:
                raise HarnessError("CLI metadata row counts are truncated")
            rows[table] = struct.unpack_from("<I", raw, table_cursor)[0]
            table_cursor += 4
    method_rid = entrypoint & 0x00FFFFFF
    if entrypoint >> 24 != 0x06 or method_rid == 0 or method_rid > rows[6]:
        raise HarnessError("CLI entrypoint is not a valid MethodDef token")
    string_size = 4 if heap_sizes & 0x01 else 2
    guid_size = 4 if heap_sizes & 0x02 else 2
    blob_size = 4 if heap_sizes & 0x04 else 2
    table_sizes = {
        0: 2 + string_size + guid_size * 3,
        1: coded_index_size(rows, (0, 26, 35, 1), 2) + string_size * 2,
        2: 4 + string_size * 2 + coded_index_size(rows, (2, 1, 27), 2)
        + metadata_index_size(rows, 4) + metadata_index_size(rows, 6),
        3: metadata_index_size(rows, 4),
        4: 2 + string_size + blob_size,
        5: metadata_index_size(rows, 6),
    }
    method_size = 8 + string_size + blob_size + metadata_index_size(rows, 8)
    method_table = table_cursor + sum(rows[table] * table_sizes[table] for table in range(6))
    method_end = method_table + rows[6] * method_size
    if method_end > table_end:
        raise HarnessError("CLI MethodDef table is truncated")
    method = method_table + (method_rid - 1) * method_size
    method_rva = struct.unpack_from("<I", raw, method)[0]
    index_cursor = method + 8

    def read_index(size: int) -> int:
        nonlocal index_cursor
        value = struct.unpack_from("<H" if size == 2 else "<I", raw, index_cursor)[0]
        index_cursor += size
        return value

    name_index = read_index(string_size)
    signature_index = read_index(blob_size)
    parameter_index = read_index(metadata_index_size(rows, 8))
    map_rva(raw, sections, method_rva, 1)
    strings_start, strings_end = streams["#Strings"]
    name_start = strings_start + name_index
    if name_index == 0 or name_start >= strings_end:
        raise HarnessError("CLI entrypoint name index is invalid")
    name_end = raw.find(b"\0", name_start, strings_end)
    if name_end < 0 or raw[name_start:name_end] != b"Main":
        raise HarnessError("CLI entrypoint name is not exact Main")
    blob_start, blob_end = streams["#Blob"]
    signature_start = blob_start + signature_index
    signature_length, prefix_length = compressed_unsigned(raw, signature_start, blob_end)
    if signature_index == 0 or signature_length == 0 or signature_start + prefix_length + signature_length > blob_end:
        raise HarnessError("CLI entrypoint signature blob is invalid")
    if parameter_index == 0 or parameter_index > rows[8] + 1:
        raise HarnessError("CLI entrypoint parameter list is invalid")
    return {
        "entrypoint_method_rid": method_rid,
        "metadata_streams": sorted(streams),
        "metadata_version_sha256": hashlib.sha256(version).hexdigest(),
        "methoddef_rows": rows[6],
    }


def validate_pe32_cli(raw: bytes, expected_subsystem: int) -> dict[str, object]:
    if len(raw) < 512 or raw[:2] != b"MZ":
        raise HarnessError("output is not DOS/PE")
    pe = struct.unpack_from("<I", raw, 0x3C)[0]
    if pe < 0x40 or pe + 24 > len(raw) or raw[pe:pe + 4] != b"PE\0\0":
        raise HarnessError("output PE signature is invalid")
    coff = pe + 4
    machine, section_count = struct.unpack_from("<HH", raw, coff)
    optional_size, characteristics = struct.unpack_from("<HH", raw, coff + 16)
    if machine != 0x014C or not (1 <= section_count <= 32) or optional_size != 0xE0:
        raise HarnessError("output is not PE32/i386")
    if characteristics & 0x0002 == 0:
        raise HarnessError("output is not executable")
    optional = coff + 20
    if optional + optional_size > len(raw) or struct.unpack_from("<H", raw, optional)[0] != 0x010B:
        raise HarnessError("output optional header is not PE32")
    subsystem = struct.unpack_from("<H", raw, optional + 68)[0]
    if subsystem != expected_subsystem:
        raise HarnessError("output subsystem mismatch")
    directory_count = struct.unpack_from("<I", raw, optional + 92)[0]
    if directory_count < 15:
        raise HarnessError("output has no CLI directory")
    cli_rva, cli_size = struct.unpack_from("<II", raw, optional + 96 + 14 * 8)
    if cli_size < 72:
        raise HarnessError("CLI header is too small")
    section_table = optional + optional_size
    if section_table + section_count * 40 > len(raw):
        raise HarnessError("PE section table is truncated")
    sections: list[tuple[int, int, int, int]] = []
    raw_ranges: list[tuple[int, int]] = []
    for index in range(section_count):
        row = section_table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", raw, row + 8)
        if raw_size:
            if raw_pointer < section_table + section_count * 40 or raw_pointer + raw_size > len(raw):
                raise HarnessError("PE section raw range is invalid")
            raw_ranges.append((raw_pointer, raw_pointer + raw_size))
        sections.append((virtual_address, virtual_size, raw_pointer, raw_size))
    raw_ranges.sort()
    if any(left[1] > right[0] for left, right in zip(raw_ranges, raw_ranges[1:])):
        raise HarnessError("PE sections overlap")
    cli = map_rva(raw, sections, cli_rva, 72)
    header_size = struct.unpack_from("<I", raw, cli)[0]
    metadata_rva, metadata_size = struct.unpack_from("<II", raw, cli + 8)
    flags, entrypoint = struct.unpack_from("<II", raw, cli + 16)
    if header_size != 72 or flags != 0x00000003:
        raise HarnessError("CLI flags are not IL-only x86-required")
    if entrypoint == 0:
        raise HarnessError("CLI entrypoint is empty")
    metadata = validate_cli_metadata(raw, sections, metadata_rva, metadata_size, entrypoint)
    return {
        "cli_flags": flags,
        "machine": machine,
        "optional_magic": 0x010B,
        "subsystem": subsystem,
        **metadata,
    }


def artifact_identities(root: pathlib.Path) -> dict[str, object]:
    return {role: read_plain(root.joinpath(*parts), single_link=True)[1] for role, parts in ARTIFACT_PATHS.items()}


def expected_inventory() -> set[str]:
    result = {"manifest.json", "inputs", "build", "build/1033"}
    for parts in ARTIFACT_PATHS.values():
        result.add("/".join(parts))
    return result


def verify_inventory(root: pathlib.Path) -> None:
    observed: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise HarnessError("retained tree contains symlink")
        if not path.is_file() and not path.is_dir():
            raise HarnessError("retained tree contains special object")
        observed.add(relative)
    if observed != expected_inventory():
        raise HarnessError("retained tree inventory mismatch")


def verify_private_modes(root: pathlib.Path) -> None:
    if os.name == "nt":
        return
    directory_names = ((), ("inputs",), ("build",), ("build", "1033"))
    for parts in directory_names:
        metadata = root.joinpath(*parts).stat(follow_symlinks=False)
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise HarnessError("retained directory is not owned mode 0700")
    for role, parts in ARTIFACT_PATHS.items():
        expected = 0o700 if role == "compiler_snapshot" else 0o400
        metadata = root.joinpath(*parts).stat(follow_symlinks=False)
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != expected:
            raise HarnessError("retained artifact mode mismatch")
    manifest = (root / "manifest.json").stat(follow_symlinks=False)
    if manifest.st_uid != os.geteuid() or stat.S_IMODE(manifest.st_mode) != 0o400:
        raise HarnessError("retained manifest mode mismatch")


def manifest_shape(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {
        "commands", "compiler", "environment", "executables", "framework", "harness",
        "retained", "schema_version", "source", "status", "test",
    }:
        raise HarnessError("manifest shape mismatch")
    if value["schema_version"] != SCHEMA_VERSION:
        raise HarnessError("manifest schema mismatch")
    if value["harness"] != {"id": HARNESS_ID, "version": HARNESS_VERSION}:
        raise HarnessError("manifest harness mismatch")
    if value["status"] != {
        "fixture_executed": False,
        "original_execution_status": "not-run",
        "test_execution_status": "succeeded",
    }:
        raise HarnessError("manifest status mismatch")
    if value["test"] != {
        "exit_code": 0,
        "stderr_empty": True,
        "stdout": identity_bytes(EXPECTED_TEST_STDOUT),
    }:
        raise HarnessError("manifest test result mismatch")
    return value


def read_manifest(root: pathlib.Path) -> tuple[dict[str, object], dict[str, object]]:
    raw, identity = read_plain(root / "manifest.json", maximum=2 * 1024 * 1024, single_link=True)
    try:
        value = json.loads(raw.decode("ascii", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HarnessError("manifest is not JSON") from error
    if canonical(value) != raw:
        raise HarnessError("manifest is not canonical")
    return manifest_shape(value), identity


def compare_reference_identities(references: dict[str, tuple[pathlib.Path, dict[str, object]]], expected: object) -> None:
    observed = current_reference_identities(references)
    if expected != observed:
        raise HarnessError("framework reference identity mismatch")


def current_reference_identities(
    references: dict[str, tuple[pathlib.Path, dict[str, object]]]
) -> dict[str, object]:
    return {name: read_plain(value[0])[1] for name, value in references.items()}


def command_set(
    root: pathlib.Path,
    references: dict[str, tuple[pathlib.Path, dict[str, object]]],
) -> tuple[dict[str, object], dict[str, object]]:
    inputs = root / "inputs"
    build = root / "build"
    compiler_snapshot = build / "csc.exe"
    fixture_arguments, fixture_roles = build_arguments(
        compiler_snapshot,
        build / "SyntheticLauncherFixture.exe",
        [inputs / "SyntheticFixture.cs"],
        references,
        "winexe",
        "Cm0102.SyntheticLauncherQualification.SyntheticFixture",
    )
    test_arguments, test_roles = build_arguments(
        compiler_snapshot,
        build / "SyntheticFixtureTests.exe",
        [inputs / "SyntheticFixture.cs", inputs / "SyntheticFixtureTests.cs"],
        references,
        "exe",
        "Cm0102.SyntheticLauncherQualification.SyntheticFixtureTests",
    )
    test_run = [os.fspath(build / "SyntheticFixtureTests.exe")]
    commands = {
        "fixture_build": command_binding(fixture_arguments, fixture_roles),
        "test_build": command_binding(test_arguments, test_roles),
        "test_run": command_binding(test_run, ["test-executable"]),
    }
    raw = {
        "fixture_build": fixture_arguments,
        "test_build": test_arguments,
        "test_run": test_run,
    }
    return commands, raw


def revalidate_sources(repo: pathlib.Path, commit: str, expected: object) -> None:
    bindings, _ = source_bindings(repo, commit)
    if bindings != expected:
        raise HarnessError("source identity changed")


def run_mode(arguments: argparse.Namespace) -> dict[str, object]:
    if os.name != "nt" and not is_wsl():
        raise HarnessError("run mode requires Windows or WSL")
    repo = require_absolute_canonical(arguments.repo, "repository")
    source_before, snapshots = source_bindings(repo, arguments.source_commit)
    validate_profile(snapshots["profile"], snapshots)
    compiler, compiler_raw, compiler_identity, compiler_ui, compiler_ui_raw, compiler_ui_identity, references = compiler_inputs(arguments.compiler)
    reference_before = {name: item[1] for name, item in references.items()}
    destination = private_parent(arguments.retained_dir)
    os.mkdir(destination, 0o700)
    os.mkdir(destination / "inputs", 0o700)
    os.mkdir(destination / "build", 0o700)
    os.mkdir(destination / "build" / "1033", 0o700)
    try:
        for role, raw in snapshots.items():
            write_exclusive(destination / "inputs" / SNAPSHOT_NAMES[role], raw)
        write_exclusive(destination / "build" / "csc.exe", compiler_raw, executable=True)
        write_exclusive(destination / "build" / "1033" / "cscui.dll", compiler_ui_raw)
        commands, raw_commands = command_set(destination, references)
        environment, environment_binding = minimal_environment(destination / "build")
        build_outputs: dict[str, tuple[int, bytes, bytes]] = {}
        for name in ("fixture_build", "test_build"):
            revalidate_sources(repo, arguments.source_commit, source_before)
            if read_plain(compiler)[1] != compiler_identity or read_plain(compiler_ui)[1] != compiler_ui_identity:
                raise HarnessError("compiler inputs changed before build")
            if read_plain(destination / "build" / "csc.exe", single_link=True)[1] != compiler_identity:
                raise HarnessError("compiler snapshot changed before build")
            if read_plain(destination / "build" / "1033" / "cscui.dll", single_link=True)[1] != compiler_ui_identity:
                raise HarnessError("compiler UI snapshot changed before build")
            compare_reference_identities(references, reference_before)
            result = capture_bounded(
                raw_commands[name], destination / "build", environment, BUILD_TIMEOUT_SECONDS, MAX_STREAM_BYTES
            )
            if result[0] != 0 or result[1] or result[2]:
                raise HarnessError("compiler result was not exact success")
            if read_plain(destination / "build" / "csc.exe", single_link=True)[1] != compiler_identity:
                raise HarnessError("compiler snapshot changed during build")
            if read_plain(destination / "build" / "1033" / "cscui.dll", single_link=True)[1] != compiler_ui_identity:
                raise HarnessError("compiler UI snapshot changed during build")
            compare_reference_identities(references, reference_before)
            build_outputs[name] = result
        if os.name != "nt":
            os.chmod(destination / "build" / "SyntheticLauncherFixture.exe", 0o400)
            os.chmod(destination / "build" / "SyntheticFixtureTests.exe", 0o700)
        fixture_raw, fixture_identity = read_plain(destination / "build" / "SyntheticLauncherFixture.exe", single_link=True)
        test_raw, test_identity = read_plain(destination / "build" / "SyntheticFixtureTests.exe", single_link=True)
        pe = {
            "fixture": validate_pe32_cli(fixture_raw, 2),
            "tests": validate_pe32_cli(test_raw, 3),
        }
        executable_after_build = {"fixture": fixture_identity, "tests": test_identity}
        code, stdout, stderr = capture_bounded(
            raw_commands["test_run"], destination / "build", environment, TEST_TIMEOUT_SECONDS, MAX_STREAM_BYTES
        )
        if code != 0 or stdout != EXPECTED_TEST_STDOUT or stderr:
            raise HarnessError("test executable result was not exact success")
        if os.name != "nt":
            os.chmod(destination / "build" / "SyntheticFixtureTests.exe", 0o400)
        if read_plain(destination / "build" / "SyntheticLauncherFixture.exe", single_link=True)[1] != fixture_identity:
            raise HarnessError("fixture executable changed without execution")
        if read_plain(destination / "build" / "SyntheticFixtureTests.exe", single_link=True)[1] != test_identity:
            raise HarnessError("test executable changed during execution")
        executable_after_test = {"fixture": fixture_identity, "tests": test_identity}
        stream_values = {
            "fixture_build_stdout": build_outputs["fixture_build"][1],
            "fixture_build_stderr": build_outputs["fixture_build"][2],
            "test_build_stdout": build_outputs["test_build"][1],
            "test_build_stderr": build_outputs["test_build"][2],
            "test_stdout": stdout,
            "test_stderr": stderr,
        }
        for role, raw in stream_values.items():
            write_exclusive(destination.joinpath(*ARTIFACT_PATHS[role]), raw)
        source_after, _ = source_bindings(repo, arguments.source_commit)
        if source_after != source_before:
            raise HarnessError("source changed during retained build")
        if read_plain(compiler)[1] != compiler_identity or read_plain(compiler_ui)[1] != compiler_ui_identity:
            raise HarnessError("compiler changed during retained build")
        framework_after = current_reference_identities(references)
        if framework_after != reference_before:
            raise HarnessError("framework references changed during retained build")
        retained = artifact_identities(destination)
        manifest = {
            "commands": commands,
            "compiler": {
                "csc": {"before": compiler_identity, "after": read_plain(compiler)[1]},
                "cscui": {"before": compiler_ui_identity, "after": read_plain(compiler_ui)[1]},
            },
            "environment": environment_binding,
            "executables": {
                "after_build": executable_after_build,
                "after_test": executable_after_test,
                "pe32_cli": pe,
            },
            "framework": {
                "before": reference_before,
                "after": framework_after,
            },
            "harness": {"id": HARNESS_ID, "version": HARNESS_VERSION},
            "retained": retained,
            "schema_version": SCHEMA_VERSION,
            "source": {
                "after": source_after,
                "before": source_before,
                "commit": arguments.source_commit,
            },
            "status": {
                "fixture_executed": False,
                "original_execution_status": "not-run",
                "test_execution_status": "succeeded",
            },
            "test": {
                "exit_code": 0,
                "stderr_empty": True,
                "stdout": identity_bytes(EXPECTED_TEST_STDOUT),
            },
        }
        write_exclusive(destination / "manifest.json", canonical(manifest))
        return verify_retained(repo, arguments.source_commit, arguments.compiler, destination)
    except Exception:
        raise


def verify_retained(repo_argument: pathlib.Path, commit: str, compiler_argument: pathlib.Path, retained_argument: pathlib.Path) -> dict[str, object]:
    repo = require_absolute_canonical(repo_argument, "repository")
    root = require_absolute_canonical(retained_argument, "retained directory")
    if not root.is_dir():
        raise HarnessError("retained root is not a directory")
    manifest, manifest_identity = read_manifest(root)
    verify_inventory(root)
    verify_private_modes(root)
    source, snapshots = source_bindings(repo, commit)
    validate_profile(snapshots["profile"], snapshots)
    source_record = manifest["source"]
    if not isinstance(source_record, dict) or source_record != {"after": source, "before": source, "commit": commit}:
        raise HarnessError("manifest source binding mismatch")
    compiler, _compiler_raw, compiler_identity, compiler_ui, _ui_raw, compiler_ui_identity, references = compiler_inputs(compiler_argument)
    compiler_record = manifest["compiler"]
    if compiler_record != {
        "csc": {"before": compiler_identity, "after": compiler_identity},
        "cscui": {"before": compiler_ui_identity, "after": compiler_ui_identity},
    }:
        raise HarnessError("manifest compiler binding mismatch")
    reference_identities = {name: item[1] for name, item in references.items()}
    if manifest["framework"] != {"before": reference_identities, "after": reference_identities}:
        raise HarnessError("manifest framework binding mismatch")
    retained = artifact_identities(root)
    if manifest["retained"] != retained:
        raise HarnessError("retained artifact identity mismatch")
    for role, source_role in (
        ("fixture_source_snapshot", "fixture_source"),
        ("test_source_snapshot", "test_source"),
        ("profile_snapshot", "profile"),
        ("verifier_snapshot", "verifier"),
        ("harness_snapshot", "harness"),
    ):
        if read_plain(root.joinpath(*ARTIFACT_PATHS[role]), single_link=True)[0] != snapshots[source_role]:
            raise HarnessError("retained source snapshot mismatch")
    if retained["compiler_snapshot"] != compiler_identity or retained["compiler_ui_snapshot"] != compiler_ui_identity:
        raise HarnessError("retained compiler snapshot mismatch")
    fixture_raw, fixture_identity = read_plain(root.joinpath(*ARTIFACT_PATHS["fixture_executable"]), single_link=True)
    tests_raw, tests_identity = read_plain(root.joinpath(*ARTIFACT_PATHS["test_executable"]), single_link=True)
    pe = {"fixture": validate_pe32_cli(fixture_raw, 2), "tests": validate_pe32_cli(tests_raw, 3)}
    executable_record = {
        "after_build": {"fixture": fixture_identity, "tests": tests_identity},
        "after_test": {"fixture": fixture_identity, "tests": tests_identity},
        "pe32_cli": pe,
    }
    if manifest["executables"] != executable_record:
        raise HarnessError("manifest executable binding mismatch")
    for role in ("fixture_build_stdout", "fixture_build_stderr", "test_build_stdout", "test_build_stderr", "test_stderr"):
        if read_plain(root.joinpath(*ARTIFACT_PATHS[role]), single_link=True)[0] != b"":
            raise HarnessError("retained stream is not exact empty output")
    if read_plain(root.joinpath(*ARTIFACT_PATHS["test_stdout"]), single_link=True)[0] != EXPECTED_TEST_STDOUT:
        raise HarnessError("retained test stdout mismatch")
    commands, _ = command_set(root, references)
    if manifest["commands"] != commands:
        raise HarnessError("manifest command binding mismatch")
    environment, environment_binding = minimal_environment(root / "build")
    del environment
    if manifest["environment"] != environment_binding:
        raise HarnessError("manifest environment binding mismatch")
    if read_plain(compiler)[1] != compiler_identity or read_plain(compiler_ui)[1] != compiler_ui_identity:
        raise HarnessError("compiler changed during verification")
    compare_reference_identities(references, reference_identities)
    revalidate_sources(repo, commit, source)
    return {
        "manifest": manifest_identity,
        "source_commit": commit,
        "verification": "passed",
    }


def synthetic_pe(subsystem: int = 2, flags: int = 3) -> bytes:
    raw = bytearray(2048)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 0x3C, 0x80)
    raw[0x80:0x84] = b"PE\0\0"
    coff = 0x84
    struct.pack_into("<HHIIIHH", raw, coff, 0x014C, 1, 0, 0, 0, 0xE0, 0x0002)
    optional = coff + 20
    struct.pack_into("<H", raw, optional, 0x010B)
    struct.pack_into("<H", raw, optional + 68, subsystem)
    struct.pack_into("<I", raw, optional + 92, 16)
    struct.pack_into("<II", raw, optional + 96 + 14 * 8, 0x2100, 72)
    section = optional + 0xE0
    raw[section:section + 5] = b".text"
    struct.pack_into("<IIII", raw, section + 8, 0x600, 0x2000, 0x600, 0x200)
    struct.pack_into("<I", raw, 0x300, 72)
    struct.pack_into("<II", raw, 0x308, 0x2180, 0xA0)
    struct.pack_into("<II", raw, 0x310, flags, 0x06000001)
    metadata = 0x380
    version = b"v4.0.30319\0"
    raw[metadata:metadata + 4] = b"BSJB"
    struct.pack_into("<HHII", raw, metadata + 4, 1, 1, 0, len(version))
    raw[metadata + 16:metadata + 16 + len(version)] = version
    cursor = (metadata + 16 + len(version) + 3) & ~3
    struct.pack_into("<HH", raw, cursor, 0, 3)
    cursor += 4
    table_offset = 0x50
    strings_offset = 0x88
    blob_offset = 0x98
    for name, offset, size in (
        (b"#~\0", table_offset, 56),
        (b"#Strings\0", strings_offset, 15),
        (b"#Blob\0", blob_offset, 5),
    ):
        struct.pack_into("<II", raw, cursor, offset, size)
        raw[cursor + 8:cursor + 8 + len(name)] = name
        cursor = (cursor + 8 + len(name) + 3) & ~3
    tables = metadata + table_offset
    struct.pack_into("<IBBBBQQ", raw, tables, 0, 2, 0, 0, 1, (1 << 0) | (1 << 6), 0)
    struct.pack_into("<II", raw, tables + 24, 1, 1)
    rows = tables + 32
    struct.pack_into("<HHHHH", raw, rows, 0, 1, 0, 0, 0)
    struct.pack_into("<IHHHHH", raw, rows + 10, 0x2300, 0, 0, 10, 1, 1)
    raw[metadata + strings_offset:metadata + strings_offset + 15] = b"\0<Module>\0Main\0"
    raw[metadata + blob_offset:metadata + blob_offset + 5] = b"\0\x03\x00\x00\x08"
    raw[0x500] = 0x2A
    return bytes(raw)


def self_test() -> None:
    base = synthetic_pe()
    observed = validate_pe32_cli(base, 2)
    if not (
        observed["cli_flags"] == 3
        and observed["machine"] == 0x014C
        and observed["optional_magic"] == 0x010B
        and observed["subsystem"] == 2
        and observed["entrypoint_method_rid"] == 1
        and observed["methoddef_rows"] == 1
        and observed["metadata_streams"] == ["#Blob", "#Strings", "#~"]
    ):
        raise AssertionError("PE positive control")
    mutations = []
    for label, offset, packed in (
        ("machine", 0x84, struct.pack("<H", 0x8664)),
        ("optional magic", 0x84 + 20, struct.pack("<H", 0x020B)),
        ("subsystem", 0x84 + 20 + 68, struct.pack("<H", 3)),
        ("CLI flags", 0x310, struct.pack("<I", 1)),
        ("CLI unsupported strong-name flag", 0x310, struct.pack("<I", 0x7)),
        ("CLI native entrypoint flag", 0x310, struct.pack("<I", 0x13)),
        ("CLI extra tracking flag", 0x310, struct.pack("<I", 0x103)),
        ("entrypoint", 0x314, struct.pack("<I", 0)),
        ("metadata signature", 0x380, b"NOPE"),
        ("metadata stream/header overlap", 0x3A0, struct.pack("<I", 0x30)),
        ("metadata missing MethodDef rows", 0x3EC, struct.pack("<I", 0)),
        ("metadata MethodDef token", 0x314, struct.pack("<I", 0x02000001)),
        ("metadata method name", 0x380 + 0x88 + 10, b"X"),
    ):
        changed = bytearray(base)
        changed[offset:offset + len(packed)] = packed
        mutations.append((label, bytes(changed)))
    for label, changed in mutations:
        try:
            validate_pe32_cli(changed, 2)
        except HarnessError:
            pass
        else:
            raise AssertionError("accepted PE mutation " + label)
    if canonical({"b": 1, "a": 2}) != b'{"a":2,"b":1}\n':
        raise AssertionError("canonical encoding")
    if not re.fullmatch(rb"PASS [0-9]+\r\n", EXPECTED_TEST_STDOUT):
        raise AssertionError("test output contract")
    mock_references = {
        name: (pathlib.Path("/framework") / name, {"byte_count": 1, "sha256": "0" * 64})
        for name in FRAMEWORK_NAMES
    }
    original_converter = globals()["to_windows_path"]
    globals()["to_windows_path"] = lambda path: "C:\\bound\\" + path.name
    try:
        with tempfile.TemporaryDirectory() as command_directory:
            command_root = pathlib.Path(command_directory)
            (command_root / "inputs").mkdir()
            (command_root / "build").mkdir()
            commands, raw_commands = command_set(command_root, mock_references)
    finally:
        globals()["to_windows_path"] = original_converter
    if set(commands) != {"fixture_build", "test_build", "test_run"}:
        raise AssertionError("command set roles")
    if len(raw_commands["fixture_build"]) != 18 or len(raw_commands["test_build"]) != 19:
        raise AssertionError("command set arity")
    if raw_commands["fixture_build"].count("/noconfig") != 1:
        raise AssertionError("fixture build controls")
    if raw_commands["test_build"].count("/noconfig") != 1:
        raise AssertionError("test build controls")
    if raw_commands["fixture_build"].count("/nostdlib+") != 1:
        raise AssertionError("fixture standard library control")
    if raw_commands["test_build"].count("/nostdlib+") != 1:
        raise AssertionError("test standard library control")
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        plain = root / "plain"
        plain.write_bytes(b"x")
        alias = root / "alias"
        os.link(plain, alias)
        try:
            read_plain(alias, single_link=True)
        except HarnessError:
            pass
        else:
            raise AssertionError("accepted hardlinked retained file")
        replacement_repo = root / "replacement-repo"
        replacement_repo.mkdir()
        test_environment = {
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_AUTHOR_NAME": "fixture-test",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "fixture-test",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "LANG": "C",
            "LC_ALL": "C",
        }

        def test_git(arguments: list[str]) -> bytes:
            completed = subprocess.run(
                [os.fspath(find_git()), "-C", os.fspath(replacement_repo), *arguments],
                cwd=os.fspath(root),
                env=test_environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                check=False,
            )
            if completed.returncode != 0 or completed.stderr:
                raise AssertionError("replacement self-test Git command")
            return completed.stdout

        test_git(["init", "-q"])
        bound = replacement_repo / "bound.txt"
        bound.write_bytes(b"original\n")
        test_git(["add", "bound.txt"])
        original_tree = test_git(["write-tree"]).decode("ascii").strip()
        original_commit = test_git(["commit-tree", original_tree, "-m", "original"]).decode("ascii").strip()
        bound.write_bytes(b"replacement\n")
        test_git(["add", "bound.txt"])
        replacement_tree = test_git(["write-tree"]).decode("ascii").strip()
        replacement_commit = test_git(["commit-tree", replacement_tree, "-m", "replacement"]).decode("ascii").strip()
        test_git(["replace", original_commit, replacement_commit])
        if test_git(["show", original_commit + ":bound.txt"]) != b"replacement\n":
            raise AssertionError("replacement self-test positive control")
        if git_command(replacement_repo, ["show", original_commit + ":bound.txt"]) != b"original\n":
            raise AssertionError("Git replacement object affected build binding")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    modes = result.add_subparsers(dest="mode", required=True)
    for name in ("run", "verify"):
        mode = modes.add_parser(name)
        mode.add_argument("--repo", required=True, type=pathlib.Path)
        mode.add_argument("--source-commit", required=True)
        mode.add_argument("--compiler", required=True, type=pathlib.Path)
        mode.add_argument("--retained-dir", required=True, type=pathlib.Path)
    modes.add_parser("self-test")
    return result


def main() -> int:
    arguments = parser().parse_args()
    if arguments.mode == "self-test":
        self_test()
        print("PASS")
        return 0
    if arguments.mode == "run":
        result = run_mode(arguments)
    else:
        result = verify_retained(arguments.repo, arguments.source_commit, arguments.compiler, arguments.retained_dir)
    print(canonical(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HarnessError, OSError, ValueError, UnicodeError, json.JSONDecodeError) as error:
        print("FAIL: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
