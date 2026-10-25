#!/usr/bin/env python3
"""Retained Stage 2 build: compile/static-inspect production, run pure gate tests only."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import stat
import struct
import sys
import tempfile
import time
import types
from subprocess import DEVNULL, PIPE, run as trusted_run


SCHEMA_VERSION = 1
HARNESS_ID = "cm0102-synthetic-launcher-runtime-retained-build"
MAX_SOURCE_BYTES = 1024 * 1024
MAX_STREAM_BYTES = 65536
BUILD_TIMEOUT_SECONDS = 180
TEST_TIMEOUT_SECONDS = 30
HARNESS_TIMEOUT_SECONDS = 1200
EXPECTED_TEST_STDOUT = b"PASS runtime-gate-v1\r\n"
EXPECTED_UI_FIXTURE = {
    "byte_count": 14336,
    "sha256": "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6",
}
RUNTIME_ROOT = "tools/windows/synthetic-launcher-runtime"
VERIFIER_PATH = RUNTIME_ROOT + "/verify_runtime_implementation.py"
HELPER_PATH = "tools/windows/synthetic-launcher-qualification/retained_build.py"
CONTRACT_PATH = "docs/architecture/SYNTHETIC_LAUNCHER_IMPLEMENTATION_V1.md"
CONFIG_PATHS = (
    "config/synthetic-launcher-implementation-v1.json",
    "config/synthetic-launcher-implementation-v1.schema.json",
    "config/synthetic-launcher-runtime-private-pinned-fixture-v1.json",
    "config/synthetic-launcher-runtime-private-v1.schema.json",
    "config/synthetic-launcher-runtime-public-pinned-fixture-v1.json",
    "config/synthetic-launcher-runtime-public-v1.schema.json",
    "config/synthetic-launcher-worker-evidence-v1.schema.json",
    "config/synthetic-launcher-report-full-v1.schema.json",
)
SHARED_SOURCES = ("RuntimeCanonicalData.cs", "RuntimeGate.cs")
GATE_TEST_SOURCE = "RuntimeGateTests.cs"
IMAGE_SPECS = {
    "SyntheticLauncherSupervisor.exe": (
        "Cm0102.SyntheticLauncherRuntime.SupervisorEntry",
        ("SupervisorEntry.cs", "SupervisorBootstrapNative.cs", "SupervisorLiveNative.cs"),
    ),
    "SyntheticLauncherController.exe": (
        "Cm0102.SyntheticLauncherRuntime.ControllerEntry",
        ("ControllerEntry.cs", "ControllerBootstrapNative.cs", "ControllerLiveNative.cs"),
    ),
    "SyntheticLauncherLockedPreflight.exe": (
        "Cm0102.SyntheticLauncherRuntime.LockedPreflightEntry",
        ("LockedPreflightEntry.cs", "LockedPreflightBootstrapNative.cs", "LockedPreflightLiveNative.cs"),
    ),
    "SyntheticLauncherTimeoutFixture.exe": (
        "Cm0102.SyntheticLauncherRuntime.TimeoutFixtureEntry",
        ("TimeoutFixtureEntry.cs", "TimeoutFixtureBootstrapNative.cs", "TimeoutFixtureLiveNative.cs"),
    ),
    "SyntheticLauncherTimeoutChild.exe": (
        "Cm0102.SyntheticLauncherRuntime.TimeoutChildEntry",
        ("TimeoutChildEntry.cs", "TimeoutChildBootstrapNative.cs", "TimeoutChildLiveNative.cs"),
    ),
}
PROCESS_CALLS = {
    "SyntheticLauncherSupervisor.exe": {"CreateProcessAsUserW": 0, "CreateProcessW": 1},
    "SyntheticLauncherController.exe": {"CreateProcessAsUserW": 1, "CreateProcessW": 0},
    "SyntheticLauncherLockedPreflight.exe": {"CreateProcessAsUserW": 0, "CreateProcessW": 0},
    "SyntheticLauncherTimeoutFixture.exe": {"CreateProcessAsUserW": 0, "CreateProcessW": 1},
    "SyntheticLauncherTimeoutChild.exe": {"CreateProcessAsUserW": 0, "CreateProcessW": 0},
}
IMPORT_MATRIX_SHA256 = {
    "SyntheticLauncherSupervisor.exe":
        "57183c32b84edf6a665e01265a5a304aac6601100d7a8cab85768bceb80b64ef",
    "SyntheticLauncherController.exe":
        "ed9482dc3dc8a33e14b520c00587fb559c0618432cc510e20f761ec0a6711fe6",
    "SyntheticLauncherLockedPreflight.exe":
        "4e05ca02fb4254246bcd22cb4d33998e77d5ded85bfa64cf75f9304d0ad40108",
    "SyntheticLauncherTimeoutFixture.exe":
        "bf8b61e4c4ae23884ef93e6da6251cbec4d83065759bea9acc8168f5f3bb4a25",
    "SyntheticLauncherTimeoutChild.exe":
        "9f70801d6cb5017635fa1959b0ad21b0dbe92551ba2e2f839619307c00f5f34c",
}
RUNTIME_FILES = tuple(sorted({
    *SHARED_SOURCES,
    GATE_TEST_SOURCE,
    *(name for _, names in IMAGE_SPECS.values() for name in names),
    "README.md",
    "retained_build.py",
    "verify_runtime_implementation.py",
}))
SOURCE_PATHS = tuple(RUNTIME_ROOT + "/" + name for name in RUNTIME_FILES) + \
    CONFIG_PATHS + (HELPER_PATH, CONTRACT_PATH)
TRUSTED_GIT = pathlib.Path("/usr/bin/git")
TRUSTED_GIT_TIMEOUT_SECONDS = 20
TRUSTED_HELPER_EXPORTS = (
    "capture_bounded", "compiler_inputs", "compressed_unsigned", "git_command",
    "map_rva", "metadata_field_size", "metadata_schemas", "minimal_environment",
    "private_parent", "read_plain", "synthetic_pe", "to_windows_child",
    "to_windows_path", "validate_pe32_cli", "verify_tree_mount_binding",
    "write_exclusive", "wsl_native_mount_binding",
)


class HarnessError(Exception):
    pass


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")) + "\n").encode("ascii")


def identity(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def trusted_git(repo: pathlib.Path, arguments: list[str], maximum: int) -> bytes:
    if not TRUSTED_GIT.is_file() or maximum <= 0 or maximum > MAX_SOURCE_BYTES:
        raise HarnessError("trusted Git bootstrap")
    environment = {
        "PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": "/dev/null",
        "GIT_CONFIG_KEY_1": "extensions.objectFormat",
        "GIT_CONFIG_VALUE_1": "sha1",
    }
    try:
        completed = trusted_run([os.fspath(TRUSTED_GIT), "--no-replace-objects",
            "-c", "protocol.file.allow=never", "-c", "core.fsmonitor=false", *arguments],
            cwd=repo, env=environment, stdin=DEVNULL, stdout=PIPE, stderr=PIPE,
            timeout=TRUSTED_GIT_TIMEOUT_SECONDS, check=False)
    except (OSError, ValueError) as error:
        raise HarnessError("trusted Git bootstrap") from error
    if completed.returncode != 0 or completed.stderr or len(completed.stdout) > maximum:
        raise HarnessError("trusted Git bootstrap")
    return completed.stdout


def trusted_path_components(path: pathlib.Path) -> None:
    if not path.is_absolute():
        raise HarnessError("trusted helper path")
    current = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            mode = os.lstat(current).st_mode
        except OSError as error:
            raise HarnessError("trusted helper path") from error
        if stat.S_ISLNK(mode):
            raise HarnessError("trusted helper path")


def trusted_read_helper(path: pathlib.Path) -> bytes:
    trusted_path_components(path)
    try:
        before = os.lstat(path)
    except OSError as error:
        raise HarnessError("trusted helper read") from error
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or \
            before.st_size <= 0 or before.st_size > MAX_SOURCE_BYTES:
        raise HarnessError("trusted helper object")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        raw = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, MAX_SOURCE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_SOURCE_BYTES:
                raise HarnessError("trusted helper size")
        after = os.lstat(path)
    except OSError as error:
        raise HarnessError("trusted helper read") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if fields(before) != fields(opened) or fields(before) != fields(after) or \
            len(raw) != before.st_size:
        raise HarnessError("trusted helper changed during read")
    return bytes(raw)


def trusted_validate_head(repo: pathlib.Path, commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise HarnessError("source commit must be a full lowercase SHA-1")
    top = trusted_git(repo, ["rev-parse", "--show-toplevel"], 4096).decode(
        "ascii", "strict").strip()
    if top != os.fspath(repo):
        raise HarnessError("repository top level mismatch")
    if trusted_git(repo, ["cat-file", "-t", commit], 64) != b"commit\n":
        raise HarnessError("source object is not a commit")
    resolved = trusted_git(repo, ["rev-parse", "--verify", commit + "^{commit}"],
        64).decode("ascii", "strict").strip()
    head = trusted_git(repo, ["rev-parse", "--verify", "HEAD^{commit}"], 64).decode(
        "ascii", "strict").strip()
    if resolved != commit or head != commit:
        raise HarnessError("source commit is not exact HEAD")


def trusted_bind_helper(repo: pathlib.Path, commit: str) -> tuple[pathlib.Path, bytes]:
    trusted_validate_head(repo, commit)
    path = repo / pathlib.PurePosixPath(HELPER_PATH)
    trusted_path_components(path)
    if path.resolve(strict=True) != path:
        raise HarnessError("helper path is not canonical")
    raw = trusted_read_helper(path)
    if raw != trusted_git(repo, ["show", commit + ":" + HELPER_PATH], MAX_SOURCE_BYTES):
        raise HarnessError("working helper differs from exact HEAD")
    blob = trusted_git(repo, ["rev-parse", commit + ":" + HELPER_PATH], 128).decode(
        "ascii", "strict").strip()
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", blob) is None or \
            trusted_git(repo, ["cat-file", "-t", blob], 64) != b"blob\n":
        raise HarnessError("helper source is not a Git blob")
    return path, raw


def trusted_head(repo: pathlib.Path) -> str:
    top = trusted_git(repo, ["rev-parse", "--show-toplevel"], 4096).decode(
        "ascii", "strict").strip()
    head = trusted_git(repo, ["rev-parse", "--verify", "HEAD^{commit}"], 64).decode(
        "ascii", "strict").strip()
    if top != os.fspath(repo) or re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise HarnessError("trusted HEAD bootstrap")
    return head


def load_helper(repo: pathlib.Path, commit: str):
    path, raw = trusted_bind_helper(repo, commit)
    module = types.ModuleType("stage1_retained_build")
    module.__file__ = os.fspath(path)
    module.__package__ = ""
    module.__spec__ = None
    try:
        code = compile(raw, os.fspath(path), "exec", dont_inherit=True, optimize=0)
        exec(code, module.__dict__)
    except Exception as error:
        raise HarnessError("cannot load retained-build helper") from error
    rebound_path, rebound_raw = trusted_bind_helper(repo, commit)
    if rebound_path != path or rebound_raw != raw or module.__file__ != os.fspath(path) or \
            module.__name__ != "stage1_retained_build" or any(not callable(
                getattr(module, name, None)) for name in TRUSTED_HELPER_EXPORTS):
        raise HarnessError("retained-build helper binding changed")
    return module


def trusted_bootstrap_static_check() -> None:
    source_path = pathlib.Path(__file__).absolute()
    try:
        tree = ast.parse(trusted_read_helper(source_path), filename=os.fspath(source_path))
    except (SyntaxError, ValueError) as error:
        raise HarnessError("trusted bootstrap source") from error
    observed: list[tuple[str, str]] = []
    for function in (node for node in ast.walk(tree) if isinstance(node,
            (ast.FunctionDef, ast.AsyncFunctionDef))):
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            if isinstance(call.func, ast.Name) and call.func.id in {
                    "trusted_run", "compile", "exec"}:
                observed.append((call.func.id, function.name))
    if sorted(observed) != sorted((
            ("trusted_run", "trusted_git"),
            ("compile", "load_helper"),
            ("exec", "load_helper"),
        )):
        raise HarnessError("trusted bootstrap execution surface")
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and
        node.module == "subprocess"]
    if len(imports) != 1 or [(item.name, item.asname) for item in imports[0].names] != [
            ("DEVNULL", None), ("PIPE", None), ("run", "trusted_run")]:
        raise HarnessError("trusted bootstrap subprocess import")


def exact_repo(path: pathlib.Path) -> pathlib.Path:
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise HarnessError("repository path must be absolute and canonical")
    return path


def git(helper, repo: pathlib.Path, arguments: list[str]) -> bytes:
    try:
        return helper.git_command(repo, arguments, MAX_SOURCE_BYTES)
    except Exception as error:
        raise HarnessError("Git binding failed") from error


def bind_sources(helper, repo: pathlib.Path, commit: str) -> tuple[dict[str, bytes], dict[str, object]]:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise HarnessError("source commit must be a full lowercase SHA-1")
    if git(helper, repo, ["rev-parse", "--show-toplevel"]).decode().strip() != os.fspath(repo):
        raise HarnessError("repository top level mismatch")
    if git(helper, repo, ["cat-file", "-t", commit]) != b"commit\n":
        raise HarnessError("source object is not a commit")
    if git(helper, repo, ["rev-parse", "--verify", "HEAD^{commit}"]).decode().strip() != commit:
        raise HarnessError("source commit is not exact HEAD")
    snapshots: dict[str, bytes] = {}
    records: dict[str, object] = {}
    for relative in SOURCE_PATHS:
        path = repo / pathlib.PurePosixPath(relative)
        try:
            raw, observed = helper.read_plain(path, MAX_SOURCE_BYTES, single_link=True)
        except Exception as error:
            raise HarnessError("invalid source " + relative) from error
        committed = git(helper, repo, ["show", commit + ":" + relative])
        if raw != committed:
            raise HarnessError("working source differs from commit: " + relative)
        blob = git(helper, repo, ["rev-parse", commit + ":" + relative]).decode().strip()
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", blob) is None or \
                git(helper, repo, ["cat-file", "-t", blob]) != b"blob\n":
            raise HarnessError("source is not a Git blob")
        snapshots[relative] = raw
        records[relative] = {"git_blob": blob, "identity": observed}
    expected = repo / RUNTIME_ROOT / "retained_build.py"
    if pathlib.Path(__file__).absolute() != expected:
        raise HarnessError("running harness is not canonical repository source")
    return snapshots, records


def make_private_tree(helper, target: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, object]:
    try:
        destination = helper.private_parent(target)
        if destination != target:
            raise HarnessError("retained destination is not canonical")
        mount = helper.wsl_native_mount_binding(destination.parent)
        destination.mkdir(mode=0o700)
        inputs = destination / "inputs"
        build = destination / "build"
        inputs.mkdir(mode=0o700)
        build.mkdir(mode=0o700)
        (build / "1033").mkdir(mode=0o700)
        helper.verify_tree_mount_binding(destination, mount)
        return inputs, build, mount
    except Exception as error:
        raise HarnessError("retained tree privacy rejection") from error


def snapshot_name(relative: str) -> str:
    return relative.replace("/", "__")


def windows_path(helper, path: pathlib.Path) -> str:
    try:
        return helper.to_windows_path(path)
    except Exception as error:
        raise HarnessError("Windows path conversion failed") from error


def compile_arguments(helper, compiler: pathlib.Path, output: pathlib.Path,
        sources: list[pathlib.Path], references: dict[str, tuple[pathlib.Path, dict[str, object]]],
        reference_names: tuple[str, ...], main: str) -> list[str]:
    return [
        os.fspath(compiler), "/nologo", "/noconfig", "/nostdlib+", "/warnaserror+",
        "/optimize+", "/debug-", "/platform:x86", "/target:exe", "/main:" + main,
        *("/reference:" + windows_path(helper, references[name][0]) for name in reference_names),
        "/out:" + helper.to_windows_child(output),
        *(windows_path(helper, source) for source in sources),
    ]


def run_command(helper, argv: list[str], cwd: pathlib.Path, environment: dict[str, str],
        timeout: int) -> tuple[bytes, bytes]:
    try:
        code, stdout, stderr = helper.capture_bounded(
            argv, cwd, environment, timeout, MAX_STREAM_BYTES)
    except Exception as error:
        raise HarnessError("bounded command failed") from error
    if code != 0:
        raise HarnessError("bounded command returned nonzero")
    return stdout, stderr


def remaining(deadline: float, maximum: int) -> float:
    value = min(float(maximum), deadline - time.monotonic())
    if value <= 0:
        raise HarnessError("complete retained harness timed out")
    return value


def run_compiler(helper, argv: list[str], compiler: pathlib.Path, output: pathlib.Path,
        sources: list[pathlib.Path], references: dict[str, tuple[pathlib.Path,
        dict[str, object]]], reference_names: tuple[str, ...], main: str,
        cwd: pathlib.Path,
        environment: dict[str, str], deadline: float) -> tuple[bytes, bytes]:
    expected_sources = [windows_path(helper, source) for source in sources]
    expected = [
        os.fspath(compiler), "/nologo", "/noconfig", "/nostdlib+", "/warnaserror+",
        "/optimize+", "/debug-", "/platform:x86", "/target:exe", "/main:" + main,
        *("/reference:" + windows_path(helper, references[name][0])
            for name in reference_names),
        "/out:" + helper.to_windows_child(output),
        *expected_sources,
    ]
    if argv != expected or pathlib.Path(argv[0]) != compiler or \
            any(value.startswith("@") for value in argv):
        raise HarnessError("compiler command executable or response file")
    return run_command(helper, argv, cwd, environment,
        remaining(deadline, BUILD_TIMEOUT_SECONDS))


def run_gate_test(helper, executable: pathlib.Path, cwd: pathlib.Path,
        environment: dict[str, str], deadline: float) -> tuple[bytes, bytes]:
    if executable.parent != cwd or executable.name != "RuntimeGateTests.exe":
        raise HarnessError("only RuntimeGateTests.exe may execute")
    return run_command(helper, [os.fspath(executable)], cwd, environment,
        remaining(deadline, TEST_TIMEOUT_SECONDS))


def run_static_verifier(helper, repo: pathlib.Path, commit: str,
        verifier_raw: bytes, deadline: float) -> tuple[bytes, bytes]:
    wrapper = (
        'import fcntl,hashlib,os,stat,sys; '
        'source=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC); '
        'before=os.fstat(source); raw=os.read(source,1048577); after=os.fstat(source); '
        'ok=stat.S_ISREG(before.st_mode) and before.st_nlink==1 and '
        'before.st_size==len(raw) and len(raw)<=1048576 and os.read(source,1)==b"" and '
        '(before.st_dev,before.st_ino,before.st_mode,before.st_nlink,before.st_size,'
        'before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_mode,'
        'after.st_nlink,after.st_size,after.st_mtime_ns,after.st_ctime_ns) and '
        'hashlib.sha256(raw).hexdigest()==sys.argv[2]; ok or sys.exit(1); '
        'snapshot=os.memfd_create("runtime-implementation-verifier",'
        'os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING); len(raw)==os.write(snapshot,raw) or sys.exit(1); '
        'fcntl.fcntl(snapshot,fcntl.F_ADD_SEALS,fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|'
        'fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE); os.lseek(snapshot,0,os.SEEK_SET); '
        'os.set_inheritable(snapshot,True); os.close(source); '
        'os.execve("/usr/bin/python3",["/usr/bin/python3","-I","-B",'
        '"/proc/self/fd/"+str(snapshot)]+sys.argv[3:],'
        '{"PATH":"/usr/bin:/bin","LC_ALL":"C","PYTHONDONTWRITEBYTECODE":"1"})')
    argv = ["/usr/bin/env", "-i", "PATH=/usr/bin:/bin", "LC_ALL=C",
        "/usr/bin/python3", "-I", "-B", "-c", wrapper,
        os.fspath(repo / RUNTIME_ROOT / "verify_runtime_implementation.py"),
        hashlib.sha256(verifier_raw).hexdigest(), "verify", "--repo", os.fspath(repo),
        "--source-commit", commit]
    stdout, stderr = run_command(helper, argv, repo,
        {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, remaining(deadline, 120))
    if stderr or b'"status":"runtime-implementation-verified"' not in stdout:
        raise HarnessError("static verifier result")
    return stdout, stderr


def write(helper, path: pathlib.Path, raw: bytes, executable: bool = False) -> dict[str, object]:
    try:
        return helper.write_exclusive(path, raw, executable=executable)
    except Exception as error:
        raise HarnessError("exclusive retained write failed") from error


def expected_impl_maps(source_values: list[str]) -> list[dict[str, object]]:
    combined = "\n".join(source_values)
    pattern = re.compile(
        r'\[DllImport\("(?P<module>[a-z0-9.]+)"(?P<options>[^\]]*)\)\]\s*'
        r'(?:private|internal)\s+static\s+extern\s+[^;()]+?\s+'
        r'(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(',
        re.ASCII,
    )
    values: list[dict[str, object]] = []
    for match in pattern.finditer(combined):
        options = match.group("options")
        if "EntryPoint" in options or "CallingConvention" in options or \
                "ExactSpelling" in options or "BestFitMapping" in options or \
                "ThrowOnUnmappableChar" in options:
            raise HarnessError("unsupported DllImport option")
        flags = 0x0100
        if "CharSet = CharSet.Unicode" in options:
            flags |= 0x0004
        elif "CharSet = CharSet.Ansi" in options:
            flags |= 0x0002
        elif "CharSet" in options:
            raise HarnessError("unsupported DllImport character set")
        if "SetLastError = true" in options:
            flags |= 0x0040
        elif "SetLastError" in options:
            raise HarnessError("unsupported DllImport last-error option")
        values.append({"import_name": match.group("name"),
            "managed_name": match.group("name"), "mapping_flags": flags,
            "module": match.group("module")})
    if len(values) != combined.count("DllImport") or len(values) != \
            len(re.findall(r"\b(?:private|internal)\s+static\s+extern\b", combined)):
        raise HarnessError("DllImport source grammar")
    return sorted(values, key=lambda value: (str(value["module"]),
        str(value["import_name"]), str(value["managed_name"])))


def frozen_impl_maps(output_name: str,
        source_values: list[str]) -> list[dict[str, object]]:
    values = expected_impl_maps(source_values)
    if output_name not in IMPORT_MATRIX_SHA256 or \
            hashlib.sha256(canonical(values)).hexdigest() != \
            IMPORT_MATRIX_SHA256[output_name]:
        raise HarnessError("production DllImport matrix drift " + output_name)
    return values


def metadata_model(helper, raw: bytes) -> dict[str, object]:
    pe = struct.unpack_from("<I", raw, 0x3C)[0]
    coff = pe + 4
    optional = coff + 20
    optional_size = struct.unpack_from("<H", raw, coff + 16)[0]
    section_count = struct.unpack_from("<H", raw, coff + 2)[0]
    cli_rva, cli_size = struct.unpack_from("<II", raw, optional + 96 + 14 * 8)
    section_table = optional + optional_size
    sections: list[tuple[int, int, int, int]] = []
    for index in range(section_count):
        row = section_table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", raw, row + 8)
        sections.append((virtual_address, virtual_size, raw_pointer, raw_size))
    cli = helper.map_rva(raw, sections, cli_rva, cli_size)
    metadata_rva, metadata_size = struct.unpack_from("<II", raw, cli + 8)
    metadata = helper.map_rva(raw, sections, metadata_rva, metadata_size)
    metadata_end = metadata + metadata_size
    version_length = struct.unpack_from("<I", raw, metadata + 12)[0]
    cursor = (metadata + 16 + version_length + 3) & ~3
    _, stream_count = struct.unpack_from("<HH", raw, cursor)
    cursor += 4
    streams: dict[str, tuple[int, int]] = {}
    for _ in range(stream_count):
        stream_offset, stream_size = struct.unpack_from("<II", raw, cursor)
        terminator = raw.find(b"\0", cursor + 8, min(cursor + 40, metadata_end))
        if terminator < 0:
            raise HarnessError("metadata stream name")
        name = raw[cursor + 8:terminator].decode("ascii", "strict")
        streams[name] = (metadata + stream_offset, metadata + stream_offset + stream_size)
        cursor = (terminator + 4) & ~3
    table_start, table_end = streams["#~"]
    heap_sizes = raw[table_start + 6]
    valid = struct.unpack_from("<Q", raw, table_start + 8)[0]
    counts = [0] * 64
    table_cursor = table_start + 24
    for table in range(64):
        if valid & (1 << table):
            counts[table] = struct.unpack_from("<I", raw, table_cursor)[0]
            table_cursor += 4
    string_size = 4 if heap_sizes & 0x01 else 2
    guid_size = 4 if heap_sizes & 0x02 else 2
    blob_size = 4 if heap_sizes & 0x04 else 2
    schemas = helper.metadata_schemas(counts, string_size, guid_size, blob_size)
    rows: dict[int, list[list[int]]] = {}
    physical = table_cursor
    for table, schema in enumerate(schemas):
        current: list[list[int]] = []
        for _ in range(counts[table]):
            values: list[int] = []
            for field in schema:
                size = helper.metadata_field_size(field, counts,
                    string_size, guid_size, blob_size)
                values.append(struct.unpack_from("<H" if size == 2 else "<I",
                    raw, physical)[0])
                physical += size
            current.append(values)
        rows[table] = current
    if physical > table_end:
        raise HarnessError("metadata table range")
    strings_start, strings_end = streams["#Strings"]
    blob_start, blob_end = streams["#Blob"]

    def string(index: int) -> str:
        if index == 0:
            return ""
        if index < 0 or strings_start + index >= strings_end:
            raise HarnessError("metadata string index")
        end = raw.find(b"\0", strings_start + index, strings_end)
        if end < 0:
            raise HarnessError("metadata string terminator")
        return raw[strings_start + index:end].decode("utf-8", "strict")

    def blob(index: int) -> bytes:
        if index <= 0 or blob_start + index >= blob_end:
            raise HarnessError("metadata blob index")
        length, prefix = helper.compressed_unsigned(raw, blob_start + index, blob_end)
        start = blob_start + index + prefix
        if start + length > blob_end:
            raise HarnessError("metadata blob range")
        return raw[start:start + length]

    return {"blob": blob, "counts": counts, "rows": rows, "sections": sections,
        "string": string}


def il_instructions(helper, raw: bytes, sections: list[tuple[int, int, int, int]],
        rva: int) -> list[tuple[str, int | None]]:
    offset = helper.map_rva(raw, sections, rva, 1)
    first = raw[offset]
    if first & 0x03 == 0x02:
        header = 1
        size = first >> 2
    elif first & 0x03 == 0x03:
        word = struct.unpack_from("<H", raw, offset)[0]
        header = ((word >> 12) & 0x0F) * 4
        size = struct.unpack_from("<I", raw, offset + 4)[0]
    else:
        raise HarnessError("method IL header")
    helper.map_rva(raw, sections, rva, header + size)
    cursor = offset + header
    end = cursor + size
    none = set(range(0x00, 0x0E)) | set(range(0x14, 0x1F)) | {0x25, 0x26, 0x2A} | \
        set(range(0x46, 0x6F)) | {0x76, 0x7A} | set(range(0x82, 0x8C)) | \
        {0x8E} | set(range(0x90, 0xA3)) | set(range(0xB3, 0xBB)) | \
        {0xC3} | set(range(0xD1, 0xDD)) | {0xDC, 0xDF, 0xE0}
    one = set(range(0x0E, 0x14)) | {0x1F} | set(range(0x2B, 0x38))
    four = {0x20, 0x22} | set(range(0x38, 0x45))
    eight = {0x21, 0x23}
    token = {0x27, 0x28, 0x29, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75,
        0x79, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x8C, 0x8D, 0x8F,
        0xA3, 0xA4, 0xA5, 0xC2, 0xC6, 0xD0}
    extended_none = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x0F, 0x11, 0x13,
        0x14, 0x17, 0x18, 0x1A, 0x1D, 0x1E}
    extended_two = set(range(0x09, 0x0F))
    extended_token = {0x06, 0x07, 0x15, 0x16, 0x1C}
    result: list[tuple[str, int | None]] = []
    while cursor < end:
        opcode = raw[cursor]
        cursor += 1
        value: int | None = None
        label = "%02x" % opcode
        if opcode == 0xFE:
            if cursor >= end:
                raise HarnessError("truncated extended IL opcode")
            second = raw[cursor]
            cursor += 1
            label = "fe%02x" % second
            if second in extended_none:
                operand = 0
            elif second in (0x12, 0x19):
                operand = 1
            elif second in extended_two:
                operand = 2
            elif second in extended_token:
                operand = 4
            else:
                raise HarnessError("unsupported extended IL opcode " + label)
        elif opcode in none:
            operand = 0
        elif opcode in one:
            operand = 1
        elif opcode in four or opcode in token:
            operand = 4
        elif opcode in eight:
            operand = 8
        elif opcode == 0x45:
            if cursor + 4 > end:
                raise HarnessError("truncated IL switch")
            count = struct.unpack_from("<I", raw, cursor)[0]
            operand = 4 + count * 4
        else:
            raise HarnessError("unsupported IL opcode " + label)
        if cursor + operand > end:
            raise HarnessError("truncated IL operand")
        if operand == 4 and (opcode in token or label in {"fe06", "fe07", "fe15",
                "fe16", "fe1c"}):
            value = struct.unpack_from("<I", raw, cursor)[0]
        result.append((label, value))
        cursor += operand
    if cursor != end:
        raise HarnessError("IL body boundary")
    return result


def inspect_cli_authority(helper, raw: bytes, expected_maps: list[dict[str, object]],
        expected_process_calls: dict[str, int]) -> dict[str, object]:
    helper.validate_pe32_cli(raw, 3)
    model = metadata_model(helper, raw)
    rows = model["rows"]
    counts = model["counts"]
    string = model["string"]
    blob = model["blob"]
    sections = model["sections"]
    if not isinstance(rows, dict) or not isinstance(counts, list) or not callable(string) or \
            not callable(blob) or not isinstance(sections, list):
        raise HarnessError("metadata authority model")

    type_refs = {rid: ((string(row[2]) + ".") if string(row[2]) else "") +
        string(row[1]) for rid, row in enumerate(rows[1], 1)}
    type_defs = {rid: ((string(row[2]) + ".") if string(row[2]) else "") +
        string(row[1]) for rid, row in enumerate(rows[2], 1)}
    method_owner: dict[int, str] = {}
    for rid, row in enumerate(rows[2], 1):
        finish = rows[2][rid][5] if rid < len(rows[2]) else counts[6] + 1
        for method in range(row[5], finish):
            method_owner[method] = type_defs[rid]
    methods: dict[int, dict[str, object]] = {}
    for rid, row in enumerate(rows[6], 1):
        methods[rid] = {"attributes": row[2], "impl_flags": row[1],
            "name": string(row[3]), "owner": method_owner.get(rid, "<global>"),
            "rva": row[0], "signature": blob(row[4]).hex()}
    module_refs = {rid: string(row[0]) for rid, row in enumerate(rows[26], 1)}
    expected_modules = sorted({str(value["module"]) for value in expected_maps})
    if sorted(module_refs.values()) != expected_modules:
        raise HarnessError("per-image ModuleRef mismatch")
    assembly_refs = [{"build": row[2], "culture": string(row[7]), "flags": row[4],
        "hash_value": "" if row[8] == 0 else blob(row[8]).hex(), "major": row[0],
        "minor": row[1], "name": string(row[6]),
        "public_key_or_token": "" if row[5] == 0 else blob(row[5]).hex(),
        "revision": row[3]} for row in rows[35]]

    def member_parent(value: int) -> str:
        tag = value & 7
        rid = value >> 3
        if tag == 0:
            return type_defs.get(rid, "TypeDef#" + str(rid))
        if tag == 1:
            return type_refs.get(rid, "TypeRef#" + str(rid))
        if tag == 2:
            return module_refs.get(rid, "ModuleRef#" + str(rid))
        if tag == 3:
            method = methods.get(rid)
            return "MethodDef#" + str(rid) if method is None else \
                str(method["owner"]) + "::" + str(method["name"])
        if tag == 4 and 0 < rid <= len(rows[27]):
            return "TypeSpec:" + blob(rows[27][rid - 1][0]).hex()
        raise HarnessError("MemberRef parent")

    member_refs: dict[int, dict[str, str]] = {}
    for rid, row in enumerate(rows[10], 1):
        member_refs[rid] = {"name": string(row[1]), "owner": member_parent(row[0]),
            "signature": blob(row[2]).hex()}

    impl_maps: list[dict[str, object]] = []
    mapped: dict[int, dict[str, object]] = {}
    for row in rows[28]:
        tag = row[1] & 1
        rid = row[1] >> 1
        if tag != 1 or rid not in methods or row[3] not in module_refs:
            raise HarnessError("ImplMap target")
        method = methods[rid]
        value = {"import_name": string(row[2]), "managed_name": method["name"],
            "mapping_flags": row[0], "module": module_refs[row[3]]}
        if rid in mapped:
            raise HarnessError("duplicate ImplMap method")
        mapped[rid] = value
        impl_maps.append(value)
    impl_maps.sort(key=lambda value: (str(value["module"]), str(value["import_name"]),
        str(value["managed_name"])))
    if impl_maps != expected_maps:
        raise HarnessError("per-image ImplMap mismatch")
    pinvoke_methods = {rid for rid, value in methods.items()
        if int(value["attributes"]) & 0x2000}
    if pinvoke_methods != set(mapped):
        raise HarnessError("P/Invoke method and ImplMap mismatch")
    for value in methods.values():
        code_type = int(value["impl_flags"]) & 0x0003
        if code_type in (1, 2) or int(value["impl_flags"]) & 0x1000:
            raise HarnessError("native or internal-call MethodDef")
        if int(value["rva"]) != 0 and code_type != 0:
            raise HarnessError("non-IL MethodDef has a body")
        if int(value["rva"]) == 0 and int(value["attributes"]) & 0x2000 == 0 and \
                code_type != 3 and \
                int(value["attributes"]) & 0x0400 == 0:
            raise HarnessError("bodyless managed MethodDef")

    def target(token_value: int) -> tuple[str, int | None]:
        table = token_value >> 24
        rid = token_value & 0x00FFFFFF
        if table == 0x06 and rid in methods:
            value = methods[rid]
            return (str(value["owner"]) + "::" + str(value["name"]) + ":" +
                str(value["signature"]), rid)
        if table == 0x0A and rid in member_refs:
            value = member_refs[rid]
            return (value["owner"] + "::" + value["name"] + ":" +
                value["signature"], None)
        if table == 0x2B and 0 < rid <= len(rows[43]):
            method_spec = rows[43][rid - 1]
            base = method_spec[0]
            base_table = 0x06 if base & 1 == 0 else 0x0A
            base_rid = base >> 1
            label, pinvoke = target((base_table << 24) | base_rid)
            return (label + "<" + blob(method_spec[1]).hex() + ">", pinvoke)
        raise HarnessError("unresolved managed call target")

    call_counts: dict[str, int] = {}
    import_calls = {rid: 0 for rid in mapped}
    main_count = 0
    for rid, method in methods.items():
        if method["name"] == "Main":
            main_count += 1
        rva = int(method["rva"])
        if rva == 0:
            continue
        source = str(method["owner"]) + "::" + str(method["name"]) + ":" + \
            str(method["signature"])
        for opcode, token_value in il_instructions(helper, raw, sections, rva):
            if opcode == "29":
                raise HarnessError("calli is forbidden")
            if token_value is None or opcode not in {"27", "28", "6f", "73", "fe06", "fe07"}:
                continue
            label, pinvoke = target(token_value)
            edge = source + " --" + opcode + "--> " + label
            call_counts[edge] = call_counts.get(edge, 0) + 1
            if pinvoke in import_calls:
                import_calls[pinvoke] += 1
    if main_count != 1:
        raise HarnessError("exact Main MethodDef count")
    if any(count == 0 for count in import_calls.values()):
        raise HarnessError("uncalled P/Invoke declaration")
    observed_process = {name: sum(import_calls[rid] for rid, value in mapped.items()
        if value["import_name"] == name) for name in expected_process_calls}
    if observed_process != expected_process_calls:
        raise HarnessError("process-creation call count")
    forbidden = ("System.Diagnostics.", "System.Reflection.", "System.IO.",
        "Microsoft.Win32.", "System.Net.", "System.Environment::", "System.Activator::",
        "::Invoke:", "::DynamicInvoke:", "Marshal::GetDelegateForFunctionPointer:",
        "Marshal::GetFunctionPointerForDelegate:")
    if any(any(marker in edge for marker in forbidden) for edge in call_counts):
        raise HarnessError("forbidden managed call target")
    if any("System.Type::" in edge and "System.Type::GetTypeFromHandle:" not in edge
            for edge in call_counts):
        raise HarnessError("forbidden managed type discovery")
    return {"assembly_refs": assembly_refs,
        "call_edges": [{"count": count, "edge": edge}
            for edge, count in sorted(call_counts.items())],
        "impl_maps": impl_maps, "member_refs": [member_refs[rid]
            for rid in sorted(member_refs)], "module_refs": sorted(module_refs.values()),
        "process_creation_calls": observed_process}


def output_record(helper, path: pathlib.Path, expected_maps: list[dict[str, object]],
        expected_process_calls: dict[str, int]) -> dict[str, object]:
    try:
        raw, file_identity = helper.read_plain(path, 64 * 1024 * 1024, single_link=True)
        pe = helper.validate_pe32_cli(raw, 3)
        authority = inspect_cli_authority(helper, raw, expected_maps, expected_process_calls)
    except Exception as error:
        raise HarnessError("production output failed static PE/CLI validation") from error
    return {"execution_status": "not-run", "identity": file_identity,
        "pe32_cli": pe, "qualification_eligible": False, "static_authority": authority}


def synthetic_implmap_pe(helper) -> bytes:
    raw = bytearray(helper.synthetic_pe(3))
    metadata = 0x380
    raw[metadata:metadata + 0x140] = b"\0" * 0x140
    struct.pack_into("<II", raw, 0x308, 0x2180, 0x140)
    version = b"v4.0.30319\0"
    raw[metadata:metadata + 4] = b"BSJB"
    struct.pack_into("<HHII", raw, metadata + 4, 1, 1, 0, len(version))
    raw[metadata + 16:metadata + 16 + len(version)] = version
    cursor = (metadata + 16 + len(version) + 3) & ~3
    struct.pack_into("<HH", raw, cursor, 0, 4)
    cursor += 4
    streams = ((b"#~\0", 0x80, 88), (b"#Strings\0", 0xE0, 34),
        (b"#Blob\0", 0x110, 5), (b"#GUID\0", 0x120, 16))
    for name, offset, size in streams:
        struct.pack_into("<II", raw, cursor, offset, size)
        raw[cursor + 8:cursor + 8 + len(name)] = name
        cursor = (cursor + 8 + len(name) + 3) & ~3
    tables = metadata + 0x80
    valid = (1 << 0) | (1 << 6) | (1 << 26) | (1 << 28)
    struct.pack_into("<IBBBBQQ", raw, tables, 0, 2, 0, 0, 1, valid, 0)
    struct.pack_into("<IIII", raw, tables + 24, 1, 2, 1, 1)
    rows = tables + 40
    struct.pack_into("<HHHHH", raw, rows, 0, 1, 1, 0, 0)
    rows += 10
    struct.pack_into("<IHHHHH", raw, rows, 0x2300, 0, 0x0091, 10, 1, 1)
    rows += 14
    struct.pack_into("<IHHHHH", raw, rows, 0, 0x0080, 0x2091, 28, 1, 1)
    rows += 14
    struct.pack_into("<H", raw, rows, 15)
    rows += 2
    struct.pack_into("<HHHH", raw, rows, 0x0100, 5, 28, 1)
    raw[metadata + 0xE0:metadata + 0xE0 + 34] = \
        b"\0<Module>\0Main\0kernel32.dll\0Sleep\0"
    raw[metadata + 0x110:metadata + 0x115] = b"\0\x03\x00\x00\x08"
    raw[metadata + 0x120:metadata + 0x130] = bytes(range(1, 17))
    raw[0x500:0x507] = b"\x1a\x28\x02\x00\x00\x06\x2a"
    return bytes(raw)


def expected_inventory() -> set[str]:
    names = {"manifest.json", "inputs", "build", "build/1033",
        "build/csc.exe", "build/1033/cscui.dll", "build/RuntimeGateTests.exe",
        "build/SyntheticLauncherFixture.exe",
        "build/SyntheticLauncherBuildManifest.v1.json",
        "build/runtime-gate-build.stdout", "build/runtime-gate-build.stderr",
        "build/runtime-gate-test.stdout", "build/runtime-gate-test.stderr",
        "build/runtime-verifier.stdout", "build/runtime-verifier.stderr"}
    names.update("inputs/" + snapshot_name(path) for path in SOURCE_PATHS)
    for output in IMAGE_SPECS:
        stem = output[:-4]
        names.update(("build/" + output, "build/" + stem + ".build.stdout",
            "build/" + stem + ".build.stderr"))
    return names


def inventory(root: pathlib.Path) -> set[str]:
    found: set[str] = set()
    for current, directories, files in os.walk(root, followlinks=False):
        base = pathlib.Path(current)
        for name in directories + files:
            path = base / name
            if path.is_symlink():
                raise HarnessError("retained inventory contains symlink")
            found.add(path.relative_to(root).as_posix())
    return found


def verify_private_modes(root: pathlib.Path) -> None:
    if os.name == "nt":
        raise HarnessError("retained evidence requires POSIX ownership and modes")
    root_metadata = root.stat(follow_symlinks=False)
    if not stat.S_ISDIR(root_metadata.st_mode) or root_metadata.st_uid != os.geteuid() or \
            stat.S_IMODE(root_metadata.st_mode) != 0o700:
        raise HarnessError("retained root ownership or mode")
    for relative in expected_inventory():
        path = root / pathlib.PurePosixPath(relative)
        metadata = path.stat(follow_symlinks=False)
        if metadata.st_uid != os.geteuid():
            raise HarnessError("retained ownership")
        if stat.S_ISDIR(metadata.st_mode):
            expected = 0o700
        elif stat.S_ISREG(metadata.st_mode):
            expected = 0o700 if relative == "build/csc.exe" else 0o400
        else:
            raise HarnessError("retained special object")
        if stat.S_IMODE(metadata.st_mode) != expected:
            raise HarnessError("retained mode " + relative)


def validate_manifest(value: object, commit: str) -> dict[str, object]:
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or \
            value.get("harness_id") != HARNESS_ID or value.get("source_commit") != commit:
        raise HarnessError("retained manifest header")
    if set(value) != {"accepted_ui_fixture", "candidate_production_manifest", "compiler",
            "environment", "harness_id", "production_outputs", "pure_tests",
            "schema_version", "source_commit", "sources", "status"}:
        raise HarnessError("retained manifest inventory")
    fixed = {
        "comparison_verdict": "not-run", "fixture_execution_status": "not-run",
        "live_execution_status": "not-run", "original_behavior_qualified": False,
        "original_execution_status": "not-run", "qualification_eligible": False,
    }
    if value.get("status") != fixed:
        raise HarnessError("retained manifest overclaims execution")
    if value.get("accepted_ui_fixture") != {
            "execution_status": "not-run", "identity": EXPECTED_UI_FIXTURE}:
        raise HarnessError("retained UI fixture record")
    candidate = value.get("candidate_production_manifest")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("byte_count"), int) or \
            candidate.get("byte_count", 0) <= 0 or re.fullmatch(
                r"[0-9a-f]{64}", str(candidate.get("sha256", ""))) is None:
        raise HarnessError("candidate production manifest record")
    outputs = value.get("production_outputs")
    if not isinstance(outputs, dict) or set(outputs) != set(IMAGE_SPECS):
        raise HarnessError("retained manifest output inventory")
    if any(not isinstance(item, dict) or item.get("execution_status") != "not-run" or
            item.get("qualification_eligible") is not False or
            not isinstance(item.get("static_authority"), dict)
            for item in outputs.values()):
        raise HarnessError("production execution status")
    tests = value.get("pure_tests")
    if not isinstance(tests, dict) or tests.get("executed") is not True or \
            tests.get("stdout") != "PASS runtime-gate-v1" or tests.get("timeout_seconds") != 30 or \
            not isinstance(tests.get("static_authority"), dict):
        raise HarnessError("pure-test record")
    return value


def run_mode(arguments: argparse.Namespace) -> dict[str, object]:
    deadline = time.monotonic() + HARNESS_TIMEOUT_SECONDS
    repo = exact_repo(pathlib.Path(arguments.repo))
    helper = load_helper(repo, arguments.source_commit)
    snapshots, source_records = bind_sources(helper, repo, arguments.source_commit)
    inputs, build, mount = make_private_tree(helper, pathlib.Path(arguments.retained_dir))
    for relative, raw in snapshots.items():
        write(helper, inputs / snapshot_name(relative), raw)
    try:
        ui_raw, ui_identity = helper.read_plain(pathlib.Path(arguments.ui_fixture),
            64 * 1024 * 1024, single_link=True)
    except Exception as error:
        raise HarnessError("accepted UI fixture input") from error
    if ui_identity != EXPECTED_UI_FIXTURE:
        raise HarnessError("accepted UI fixture identity")
    write(helper, build / "SyntheticLauncherFixture.exe", ui_raw)
    verifier_stdout, verifier_stderr = run_static_verifier(helper, repo,
        arguments.source_commit, snapshots[VERIFIER_PATH], deadline)
    write(helper, build / "runtime-verifier.stdout", verifier_stdout)
    write(helper, build / "runtime-verifier.stderr", verifier_stderr)
    try:
        compiler, compiler_raw, compiler_identity, compiler_ui, compiler_ui_raw, \
            compiler_ui_identity, references = helper.compiler_inputs(pathlib.Path(arguments.compiler))
    except Exception as error:
        raise HarnessError("compiler input rejection") from error
    del compiler, compiler_ui
    compiler_snapshot = build / "csc.exe"
    write(helper, compiler_snapshot, compiler_raw, executable=True)
    write(helper, build / "1033" / "cscui.dll", compiler_ui_raw)
    environment, environment_binding = helper.minimal_environment(build)
    production: dict[str, object] = {}
    for output_name, (main, exclusive) in IMAGE_SPECS.items():
        output = build / output_name
        source_names = (*SHARED_SOURCES, *exclusive)
        sources = [inputs / snapshot_name(RUNTIME_ROOT + "/" + name) for name in source_names]
        reference_names = ("mscorlib.dll", "System.dll", "System.Core.dll",
            "System.Drawing.dll", "System.Security.dll", "System.Windows.Forms.dll")
        argv = compile_arguments(helper, compiler_snapshot, output, sources, references,
            reference_names, main)
        stdout, stderr = run_compiler(helper, argv, compiler_snapshot, output,
            sources, references, reference_names, main, build, environment, deadline)
        if stdout or stderr:
            raise HarnessError("compiler emitted output")
        stem = output_name[:-4]
        write(helper, build / (stem + ".build.stdout"), stdout)
        write(helper, build / (stem + ".build.stderr"), stderr)
        if os.name != "nt":
            os.chmod(output, 0o400)
        imports = frozen_impl_maps(output_name, [snapshots[RUNTIME_ROOT + "/" + name].decode(
            "ascii", "strict") for name in source_names])
        production[output_name] = output_record(helper, output, imports,
            PROCESS_CALLS[output_name])
    gate_output = build / "RuntimeGateTests.exe"
    gate_sources = [inputs / snapshot_name(RUNTIME_ROOT + "/" + name)
        for name in (*SHARED_SOURCES, GATE_TEST_SOURCE)]
    gate_argv = compile_arguments(helper, compiler_snapshot, gate_output, gate_sources,
        references, ("mscorlib.dll", "System.dll"),
        "Cm0102.SyntheticLauncherRuntime.RuntimeGateTests")
    build_stdout, build_stderr = run_compiler(helper, gate_argv, compiler_snapshot,
        gate_output, gate_sources, references, ("mscorlib.dll", "System.dll"),
        "Cm0102.SyntheticLauncherRuntime.RuntimeGateTests", build, environment, deadline)
    if build_stdout or build_stderr:
        raise HarnessError("gate compiler emitted output")
    write(helper, build / "runtime-gate-build.stdout", build_stdout)
    write(helper, build / "runtime-gate-build.stderr", build_stderr)
    if os.name != "nt":
        os.chmod(gate_output, 0o700)
    gate_record = output_record(helper, gate_output, [],
        {"CreateProcessAsUserW": 0, "CreateProcessW": 0})
    test_stdout, test_stderr = run_gate_test(helper, gate_output, build, environment, deadline)
    if test_stdout != EXPECTED_TEST_STDOUT or test_stderr:
        raise HarnessError("unexpected pure-test result")
    write(helper, build / "runtime-gate-test.stdout", test_stdout)
    write(helper, build / "runtime-gate-test.stderr", test_stderr)
    if os.name != "nt":
        os.chmod(gate_output, 0o400)
    production_sources = {
        relative: source_records[relative]
        for relative in sorted(source_records)
        if relative.startswith(RUNTIME_ROOT + "/") and relative.endswith(".cs") and
        not relative.endswith("RuntimeGateTests.cs")
    }
    candidate = {
        "accepted_ui_fixture": ui_identity,
        "compiler": {"csc": compiler_identity, "cscui": compiler_ui_identity,
            "references": {name: value[1] for name, value in sorted(references.items())}},
        "manifest_kind": "candidate-production-build-v1",
        "production_outputs": {name: value["identity"]
            for name, value in sorted(production.items())},
        "production_sources": production_sources,
        "schema_version": 1,
    }
    candidate_raw = canonical(candidate)
    candidate_identity = write(helper,
        build / "SyntheticLauncherBuildManifest.v1.json", candidate_raw)
    manifest = {
        "accepted_ui_fixture": {"execution_status": "not-run", "identity": ui_identity},
        "candidate_production_manifest": candidate_identity,
        "compiler": {"csc": compiler_identity, "cscui": compiler_ui_identity,
            "references": {name: value[1] for name, value in sorted(references.items())}},
        "environment": environment_binding,
        "harness_id": HARNESS_ID,
        "production_outputs": production,
        "pure_tests": {"executed": True, "identity": helper.read_plain(
            gate_output, 64 * 1024 * 1024, single_link=True)[1],
            "static_authority": gate_record["static_authority"],
            "stdout": "PASS runtime-gate-v1", "timeout_seconds": TEST_TIMEOUT_SECONDS},
        "schema_version": SCHEMA_VERSION,
        "source_commit": arguments.source_commit,
        "sources": source_records,
        "status": {"comparison_verdict": "not-run", "fixture_execution_status": "not-run",
            "live_execution_status": "not-run", "original_behavior_qualified": False,
            "original_execution_status": "not-run", "qualification_eligible": False},
    }
    validate_manifest(manifest, arguments.source_commit)
    write(helper, pathlib.Path(arguments.retained_dir) / "manifest.json", canonical(manifest))
    try:
        helper.verify_tree_mount_binding(pathlib.Path(arguments.retained_dir), mount)
    except Exception as error:
        raise HarnessError("retained mount changed") from error
    if inventory(pathlib.Path(arguments.retained_dir)) != expected_inventory():
        raise HarnessError("retained inventory mismatch")
    remaining(deadline, HARNESS_TIMEOUT_SECONDS)
    result = verify_mode(arguments)
    remaining(deadline, HARNESS_TIMEOUT_SECONDS)
    return result


def verify_mode(arguments: argparse.Namespace) -> dict[str, object]:
    repo = exact_repo(pathlib.Path(arguments.repo))
    helper = load_helper(repo, arguments.source_commit)
    snapshots, source_records = bind_sources(helper, repo, arguments.source_commit)
    root = pathlib.Path(arguments.retained_dir)
    if not root.is_absolute() or root.resolve(strict=True) != root or \
            inventory(root) != expected_inventory():
        raise HarnessError("retained root or inventory")
    try:
        mount = helper.wsl_native_mount_binding(root)
        helper.verify_tree_mount_binding(root, mount)
        verify_private_modes(root)
        raw, _ = helper.read_plain(root / "manifest.json", MAX_SOURCE_BYTES, single_link=True)
        value = json.loads(raw.decode("ascii", "strict"))
    except Exception as error:
        raise HarnessError("retained manifest read") from error
    if canonical(value) != raw:
        raise HarnessError("retained manifest is not canonical")
    manifest = validate_manifest(value, arguments.source_commit)
    if manifest.get("sources") != source_records:
        raise HarnessError("retained source bindings")
    try:
        _, expected_environment = helper.minimal_environment(root / "build")
    except Exception as error:
        raise HarnessError("retained environment revalidation") from error
    if manifest.get("environment") != expected_environment:
        raise HarnessError("retained environment binding changed")
    try:
        ui_raw, ui_identity = helper.read_plain(pathlib.Path(arguments.ui_fixture),
            64 * 1024 * 1024, single_link=True)
        retained_ui, retained_ui_identity = helper.read_plain(
            root / "build" / "SyntheticLauncherFixture.exe",
            64 * 1024 * 1024, single_link=True)
    except Exception as error:
        raise HarnessError("accepted UI fixture revalidation") from error
    if ui_identity != EXPECTED_UI_FIXTURE or retained_ui != ui_raw or \
            retained_ui_identity != EXPECTED_UI_FIXTURE:
        raise HarnessError("accepted UI fixture changed")
    try:
        _, compiler_raw, compiler_identity, _, compiler_ui_raw, compiler_ui_identity, \
            references = helper.compiler_inputs(pathlib.Path(arguments.compiler))
    except Exception as error:
        raise HarnessError("compiler revalidation") from error
    expected_compiler = {"csc": compiler_identity, "cscui": compiler_ui_identity,
        "references": {name: item[1] for name, item in sorted(references.items())}}
    if manifest.get("compiler") != expected_compiler:
        raise HarnessError("compiler binding changed")
    retained_compiler, _ = helper.read_plain(root / "build" / "csc.exe",
        64 * 1024 * 1024, single_link=True)
    retained_ui, _ = helper.read_plain(root / "build" / "1033" / "cscui.dll",
        64 * 1024 * 1024, single_link=True)
    if retained_compiler != compiler_raw or retained_ui != compiler_ui_raw:
        raise HarnessError("compiler snapshot mismatch")
    for relative, source_raw in snapshots.items():
        observed, _ = helper.read_plain(root / "inputs" / snapshot_name(relative),
            MAX_SOURCE_BYTES, single_link=True)
        if observed != source_raw:
            raise HarnessError("retained source snapshot mismatch")
    for output_name in IMAGE_SPECS:
        source_names = (*SHARED_SOURCES, *IMAGE_SPECS[output_name][1])
        imports = frozen_impl_maps(output_name, [snapshots[RUNTIME_ROOT + "/" + name].decode(
            "ascii", "strict") for name in source_names])
        observed = output_record(helper, root / "build" / output_name, imports,
            PROCESS_CALLS[output_name])
        if observed != manifest["production_outputs"][output_name]:
            raise HarnessError("retained production output mismatch")
        stem = output_name[:-4]
        for suffix in (".build.stdout", ".build.stderr"):
            stream, _ = helper.read_plain(root / "build" / (stem + suffix),
                MAX_STREAM_BYTES, single_link=True)
            if stream:
                raise HarnessError("retained compiler stream is not empty")
    candidate_raw, candidate_identity = helper.read_plain(
        root / "build" / "SyntheticLauncherBuildManifest.v1.json",
        MAX_SOURCE_BYTES, single_link=True)
    candidate = json.loads(candidate_raw.decode("ascii", "strict"))
    expected_candidate = {
        "accepted_ui_fixture": EXPECTED_UI_FIXTURE,
        "compiler": expected_compiler,
        "manifest_kind": "candidate-production-build-v1",
        "production_outputs": {name: value["identity"] for name, value in sorted(
            manifest["production_outputs"].items())},
        "production_sources": {relative: source_records[relative]
            for relative in sorted(source_records)
            if relative.startswith(RUNTIME_ROOT + "/") and relative.endswith(".cs") and
            not relative.endswith("RuntimeGateTests.cs")},
        "schema_version": 1,
    }
    if candidate_raw != canonical(candidate) or candidate != expected_candidate or \
            candidate_identity != manifest["candidate_production_manifest"]:
        raise HarnessError("candidate production manifest mismatch")
    gate_raw, gate_identity = helper.read_plain(
        root / "build" / "RuntimeGateTests.exe", 64 * 1024 * 1024, single_link=True)
    gate_authority = inspect_cli_authority(helper, gate_raw, [],
        {"CreateProcessAsUserW": 0, "CreateProcessW": 0})
    if gate_identity != manifest["pure_tests"]["identity"]:
        raise HarnessError("retained gate-test identity")
    if gate_authority != manifest["pure_tests"]["static_authority"]:
        raise HarnessError("retained gate-test static authority")
    stdout, _ = helper.read_plain(root / "build" / "runtime-gate-test.stdout",
        MAX_STREAM_BYTES, single_link=True)
    stderr, _ = helper.read_plain(root / "build" / "runtime-gate-test.stderr",
        MAX_STREAM_BYTES, single_link=True)
    if stdout != EXPECTED_TEST_STDOUT or stderr:
        raise HarnessError("retained gate-test streams")
    for name in ("runtime-gate-build.stdout", "runtime-gate-build.stderr"):
        stream, _ = helper.read_plain(root / "build" / name,
            MAX_STREAM_BYTES, single_link=True)
        if stream:
            raise HarnessError("retained gate-build stream is not empty")
    verifier_stdout, _ = helper.read_plain(root / "build" / "runtime-verifier.stdout",
        MAX_STREAM_BYTES, single_link=True)
    verifier_stderr, _ = helper.read_plain(root / "build" / "runtime-verifier.stderr",
        MAX_STREAM_BYTES, single_link=True)
    if verifier_stderr or b'"status":"runtime-implementation-verified"' not in verifier_stdout:
        raise HarnessError("retained static verifier streams")
    return manifest


def self_test() -> None:
    if len(RUNTIME_FILES) != len(set(RUNTIME_FILES)) or len(IMAGE_SPECS) != 5:
        raise HarnessError("source inventory constants")
    if set(IMAGE_SPECS) & {"RuntimeGateTests.exe", "SyntheticLauncherFixture.exe"}:
        raise HarnessError("executable role overlap")
    trusted_bootstrap_static_check()
    repo = exact_repo(pathlib.Path.cwd().resolve(strict=True))
    head = trusted_head(repo)
    helper = load_helper(repo, head)
    try:
        load_helper(repo, "0" * 40)
    except HarnessError:
        pass
    else:
        raise HarnessError("accepted unbound retained-build helper")
    class PrivateTreeTestHelper:
        def private_parent(self, target: pathlib.Path) -> pathlib.Path:
            return target
        def wsl_native_mount_binding(self, path: pathlib.Path) -> dict[str, object]:
            if not path.is_dir():
                raise HarnessError("tested mount path does not exist")
            return {"test_mount": True}
        def verify_tree_mount_binding(self, path: pathlib.Path,
                mount: dict[str, object]) -> None:
            if not path.is_dir() or mount != {"test_mount": True}:
                raise HarnessError("tested retained tree binding")
    with tempfile.TemporaryDirectory(prefix="cm0102-runtime-retained-self-test-") as temporary:
        parent = pathlib.Path(temporary)
        os.chmod(parent, 0o700)
        target = parent / "fresh"
        tested_inputs, tested_build, tested_mount = make_private_tree(
            PrivateTreeTestHelper(), target)
        if tested_inputs != target / "inputs" or tested_build != target / "build" or \
                tested_mount != {"test_mount": True}:
            raise HarnessError("fresh retained tree self-test")
    synthetic = helper.synthetic_pe(3)
    empty_authority = inspect_cli_authority(helper, synthetic, [],
        {"CreateProcessAsUserW": 0, "CreateProcessW": 0})
    if empty_authority != {"assembly_refs": [], "call_edges": [], "impl_maps": [],
            "member_refs": [], "module_refs": [],
            "process_creation_calls": {"CreateProcessAsUserW": 0, "CreateProcessW": 0}}:
        raise HarnessError("synthetic static authority positive control")
    import_map = {"import_name": "Sleep", "managed_name": "Sleep",
        "mapping_flags": 0x0100, "module": "kernel32.dll"}
    imported = inspect_cli_authority(helper, synthetic_implmap_pe(helper), [import_map],
        {"CreateProcessAsUserW": 0, "CreateProcessW": 0})
    if imported["impl_maps"] != [import_map] or len(imported["call_edges"]) != 1 or \
            imported["call_edges"][0]["count"] != 1:
        raise HarnessError("synthetic ImplMap positive control")
    try:
        inspect_cli_authority(helper, synthetic_implmap_pe(helper), [import_map],
            {"CreateProcessAsUserW": 0, "CreateProcessW": 1})
    except HarnessError:
        pass
    else:
        raise HarnessError("accepted process-creation count mutation")
    for label, changed in (
            ("reserved opcode", synthetic[:0x501] + b"\x24" + synthetic[0x502:]),
            ("calli", synthetic[:0x500] + b"\x16\x29\0\0\0\0" + synthetic[0x506:])):
        try:
            inspect_cli_authority(helper, changed, [],
                {"CreateProcessAsUserW": 0, "CreateProcessW": 0})
        except HarnessError:
            pass
        else:
            raise HarnessError("accepted synthetic authority mutation " + label)
    source_import = ('[DllImport("kernel32.dll", CharSet = CharSet.Unicode, '
        'SetLastError = true)] private static extern bool CreateProcessW();')
    if expected_impl_maps([source_import]) != [{"import_name": "CreateProcessW",
            "managed_name": "CreateProcessW", "mapping_flags": 0x0144,
            "module": "kernel32.dll"}]:
        raise HarnessError("DllImport source positive control")
    try:
        expected_impl_maps([source_import.replace("SetLastError = true",
            "EntryPoint = \"other\"")])
    except HarnessError:
        pass
    else:
        raise HarnessError("accepted DllImport source mutation")
    runtime = pathlib.Path.cwd() / RUNTIME_ROOT
    for output_name, (_, exclusive) in IMAGE_SPECS.items():
        names = (*SHARED_SOURCES, *exclusive)
        source_values = [(runtime / name).read_text(encoding="ascii") for name in names]
        frozen_impl_maps(output_name, source_values)
        changed = list(source_values)
        changed[-1] += ("\n[DllImport(\"kernel32.dll\")] "
            "private static extern void Beep();\n")
        try:
            frozen_impl_maps(output_name, changed)
        except HarnessError:
            pass
        else:
            raise HarnessError("accepted extra production import " + output_name)
    sample = {
        "accepted_ui_fixture": {"execution_status": "not-run",
            "identity": EXPECTED_UI_FIXTURE},
        "candidate_production_manifest": {"byte_count": 1, "sha256": "3" * 64},
        "compiler": {}, "environment": {},
        "harness_id": HARNESS_ID,
        "production_outputs": {name: {"execution_status": "not-run",
            "identity": {"byte_count": 1, "sha256": "1" * 64},
            "pe32_cli": {}, "qualification_eligible": False,
            "static_authority": empty_authority} for name in IMAGE_SPECS},
        "pure_tests": {"executed": True, "identity": {"byte_count": 1,
            "sha256": "2" * 64}, "static_authority": empty_authority,
            "stdout": "PASS runtime-gate-v1", "timeout_seconds": 30},
        "schema_version": 1, "source_commit": "1" * 40, "sources": {},
        "status": {"comparison_verdict": "not-run", "fixture_execution_status": "not-run",
            "live_execution_status": "not-run", "original_behavior_qualified": False,
            "original_execution_status": "not-run", "qualification_eligible": False},
    }
    validate_manifest(sample, "1" * 40)
    for key, bad in (("live_execution_status", "passed"),
            ("original_execution_status", "passed"), ("qualification_eligible", True)):
        changed = json.loads(json.dumps(sample))
        changed["status"][key] = bad
        try:
            validate_manifest(changed, "1" * 40)
        except HarnessError:
            pass
        else:
            raise HarnessError("accepted manifest overclaim")
    print("PASS runtime-retained-build-self-test")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("self-test")
    for name in ("run", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--repo", type=pathlib.Path, required=True)
        command.add_argument("--source-commit", required=True)
        command.add_argument("--compiler", type=pathlib.Path, required=True)
        command.add_argument("--ui-fixture", type=pathlib.Path, required=True)
        command.add_argument("--retained-dir", type=pathlib.Path, required=True)
    return result


def main() -> int:
    arguments = parser().parse_args()
    try:
        if arguments.command == "self-test":
            self_test()
            return 0
        value = run_mode(arguments) if arguments.command == "run" else verify_mode(arguments)
        print(canonical({"manifest": identity(canonical(value)), "status": arguments.command + "-passed"}).decode(), end="")
        return 0
    except (HarnessError, OSError, ValueError, json.JSONDecodeError) as error:
        print("FAIL " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
