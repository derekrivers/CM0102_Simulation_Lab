#!/usr/bin/env python3
"""Build and run the v1 probe with retained, privacy-safe provenance.

This harness is intended to run in WSL.  It invokes the Windows compiler and
probe executable directly (``shell=False``); it never accepts or constructs a
game executable argument.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

import verify_output


SCHEMA_VERSION = 1
HARNESS_ID = "cm0102-original-host-retained-run"
HARNESS_VERSION = "1.1.0"
PROBE_TIMEOUT_SECONDS = 30 * 60
BUILD_TIMEOUT_SECONDS = 5 * 60
STREAM_CAP_BYTES = 4 * 1024 * 1024
EXPECTATIONS_RELATIVE = "config/original-host-qualification-v1.json"
EXPECTED_COMPILER_WINDOWS = r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
EXPECTED_COMPILER_UI_WINDOWS = (
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\1033\cscui.dll"
)
FRAMEWORK_REFERENCE_WINDOWS = (
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\System.dll",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\System.Core.dll",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\System.Drawing.dll",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\System.Security.dll",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\System.Web.Extensions.dll",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\System.Windows.Forms.dll",
)
GAME_LIKE = re.compile(r"(?:cm0?1[-_ ]?0?2|champ(?:ionship)?[-_ ]*man(?:ager)?)", re.IGNORECASE)
SOURCE_PATHS = (
    "tools/windows/original-host-qualification/CanonicalJson.cs",
    "tools/windows/original-host-qualification/OriginalHostQualification.cs",
)
CONTROL_PATHS = (
    "tools/windows/original-host-qualification/verify_output.py",
    "tools/windows/original-host-qualification/retained_run_v1.py",
)
BOUND_PATHS = SOURCE_PATHS + CONTROL_PATHS


class HarnessError(Exception):
    pass


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_plain_bytes(
    path: pathlib.Path, maximum_bytes: int = STREAM_CAP_BYTES
) -> tuple[bytes, dict[str, object]]:
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or path.is_symlink():
        raise HarnessError("identity target is not a plain regular file")
    if before.st_size < 0 or before.st_size > maximum_bytes:
        raise HarnessError("identity target exceeds byte limit")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ) or opened.st_size < 0 or opened.st_size > maximum_bytes:
            raise HarnessError("identity target changed before open")
        chunks = []
        observed = 0
        while True:
            chunk = os.read(
                descriptor, min(1024 * 1024, maximum_bytes + 1 - observed)
            )
            if not chunk:
                break
            observed += len(chunk)
            if observed > maximum_bytes:
                raise HarnessError("identity target grew beyond byte limit")
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
        raise HarnessError("identity target changed while hashing")
    raw = b"".join(chunks)
    return raw, {"byte_count": len(raw), "sha256": digest_bytes(raw)}


def file_identity(path: pathlib.Path) -> dict[str, object]:
    return read_plain_bytes(path)[1]


def require_identity(
    path: pathlib.Path, expected: dict[str, object], context: str
) -> None:
    if file_identity(path) != expected:
        raise HarnessError(f"{context} identity changed")


def reject_game_like_name(value: str) -> None:
    if GAME_LIKE.search(value):
        raise HarnessError("game-like executable/name is forbidden")


def _kill(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()


def capture_bounded(
    argv: list[str],
    timeout_seconds: float,
    cap_bytes: int,
    cwd: pathlib.Path | None = None,
) -> tuple[int, bytes, bytes]:
    if not argv or not os.path.isabs(argv[0]):
        raise HarnessError("command executable must be an absolute path")
    reject_game_like_name(pathlib.Path(argv[0]).name)
    fixed_cwd = pathlib.Path("/") if cwd is None else cwd.resolve(strict=True)
    if not fixed_cwd.is_dir() or fixed_cwd.is_symlink():
        raise HarnessError("command working directory is not a plain directory")
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(fixed_cwd),
        env={},
        shell=False,
        start_new_session=True,
    )
    outputs = [bytearray(), bytearray()]
    overflow = threading.Event()

    def drain(index: int, pipe) -> None:
        while True:
            chunk = pipe.read(65536)
            if not chunk:
                return
            room = cap_bytes + 1 - len(outputs[index])
            if room > 0:
                outputs[index].extend(chunk[:room])
            if len(outputs[index]) > cap_bytes:
                overflow.set()
                return

    threads = [
        threading.Thread(target=drain, args=(0, process.stdout), daemon=True),
        threading.Thread(target=drain, args=(1, process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout_seconds
    failure = None
    while process.poll() is None:
        if overflow.is_set():
            failure = "stream exceeded cap"
            _kill(process)
            break
        if time.monotonic() >= deadline:
            failure = "command timed out"
            _kill(process)
            break
        time.sleep(0.01)
    try:
        process.wait(timeout=10 if failure is not None else 1)
    except subprocess.TimeoutExpired:
        _kill(process)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as error:
            raise HarnessError("command could not be terminated") from error
    for thread in threads:
        thread.join(timeout=2)
    if any(thread.is_alive() for thread in threads):
        raise HarnessError("capture thread did not finish")
    if failure is not None or overflow.is_set():
        raise HarnessError(failure or "stream exceeded cap")
    return process.returncode, bytes(outputs[0]), bytes(outputs[1])


def run_small(argv: list[str], timeout_seconds: float = 30) -> bytes:
    code, stdout, _stderr = capture_bounded(
        argv, timeout_seconds, STREAM_CAP_BYTES
    )
    if code != 0:
        raise HarnessError("support command failed")
    return stdout


def to_windows_path(path: pathlib.Path) -> str:
    resolved = path.resolve(strict=True)
    wslpath = pathlib.Path("/usr/bin/wslpath")
    if not wslpath.is_file():
        raise HarnessError("wslpath is unavailable")
    raw = run_small([str(wslpath), "-w", "--", str(resolved)]).decode(
        "utf-8", "strict"
    )
    result = raw.rstrip("\r\n")
    if not result or "\n" in result or "\r" in result:
        raise HarnessError("invalid wslpath result")
    return result


def from_windows_path(value: str) -> pathlib.Path:
    wslpath = pathlib.Path("/usr/bin/wslpath")
    if not wslpath.is_file():
        raise HarnessError("wslpath is unavailable")
    raw = run_small([str(wslpath), "-u", "--", value]).decode("utf-8", "strict")
    result = raw.rstrip("\r\n")
    if not result or "\n" in result or "\r" in result or not os.path.isabs(result):
        raise HarnessError("invalid Windows locator mapping")
    return pathlib.Path(result)


def resolve_nearest(path: pathlib.Path) -> pathlib.Path:
    absolute = pathlib.Path(os.path.normpath(str(path.absolute())))
    missing = []
    cursor = absolute
    while not cursor.exists() and not cursor.is_symlink():
        if cursor.parent == cursor:
            raise HarnessError("path has no resolvable parent")
        missing.append(cursor.name)
        cursor = cursor.parent
    resolved = cursor.resolve(strict=True)
    for component in reversed(missing):
        resolved /= component
    return resolved


def paths_overlap(left: pathlib.Path, right: pathlib.Path) -> bool:
    left_key = tuple(part.casefold() for part in left.parts)
    right_key = tuple(part.casefold() for part in right.parts)
    shortest = min(len(left_key), len(right_key))
    return left_key[:shortest] == right_key[:shortest]


def existing_projections(path: pathlib.Path):
    full = resolve_nearest(path)
    cursor = full
    suffix: tuple[str, ...] = ()
    while not cursor.exists():
        suffix = (cursor.name, *suffix)
        cursor = cursor.parent
    while True:
        yield cursor, tuple(part.casefold() for part in suffix)
        if cursor.parent == cursor:
            return
        suffix = (cursor.name, *suffix)
        cursor = cursor.parent


def paths_alias_or_overlap(left: pathlib.Path, right: pathlib.Path) -> bool:
    if paths_overlap(left, right):
        return True
    for left_anchor, left_suffix in existing_projections(left):
        for right_anchor, right_suffix in existing_projections(right):
            try:
                same = os.path.samefile(left_anchor, right_anchor)
            except OSError:
                same = False
            if same:
                shortest = min(len(left_suffix), len(right_suffix))
                if left_suffix[:shortest] == right_suffix[:shortest]:
                    return True
    return False


def mapped_locator_paths(locator: dict[str, object]) -> list[pathlib.Path]:
    result = []
    for key in sorted(verify_output.PRIVATE_LOCATOR_KEYS - {"schema_version"}):
        value = locator[key]
        assert isinstance(value, str)
        result.append(resolve_nearest(from_windows_path(value)))
    return result


def git_bytes(repo: pathlib.Path, revision: str, relative: str) -> bytes:
    git = pathlib.Path("/usr/bin/git")
    return run_small(
        [str(git), "-C", str(repo), "show", f"{revision}:{relative}"]
    )


def source_bindings(
    repo: pathlib.Path, revision: str
) -> tuple[list[dict[str, object]], dict[str, bytes]]:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise HarnessError("source revision must be 40 lowercase hex")
    git = pathlib.Path("/usr/bin/git")
    resolved_revision = run_small(
        [str(git), "-C", str(repo), "rev-parse", f"{revision}^{{commit}}"]
    ).decode("ascii", "strict").strip()
    if resolved_revision != revision:
        raise HarnessError("source revision did not resolve exactly")
    bindings = []
    snapshots = {}
    for relative in BOUND_PATHS:
        worktree_path = repo / pathlib.PurePosixPath(relative)
        actual, actual_identity = read_plain_bytes(worktree_path)
        committed = git_bytes(repo, revision, relative)
        if actual != committed:
            raise HarnessError("source differs from source commit")
        snapshots[pathlib.PurePosixPath(relative).name] = committed
        bindings.append(
            {
                "id": pathlib.PurePosixPath(relative).name,
                "identity": actual_identity,
            }
        )
    return bindings, snapshots


def validate_runtime_controls(
    repo: pathlib.Path,
    bindings: list[dict[str, object]],
    harness_path: pathlib.Path | None = None,
    verifier_path: pathlib.Path | None = None,
) -> None:
    expected_paths = {
        "retained_run_v1.py": (
            repo / "tools/windows/original-host-qualification/retained_run_v1.py"
        ).resolve(strict=True),
        "verify_output.py": (
            repo / "tools/windows/original-host-qualification/verify_output.py"
        ).resolve(strict=True),
    }
    actual_paths = {
        "retained_run_v1.py": (
            pathlib.Path(__file__) if harness_path is None else harness_path
        ).resolve(strict=True),
        "verify_output.py": (
            pathlib.Path(verify_output.__file__)
            if verifier_path is None
            else verifier_path
        ).resolve(strict=True),
    }
    identities = {
        record["id"]: record["identity"]
        for record in bindings
        if record["id"] in expected_paths
    }
    if set(identities) != set(expected_paths):
        raise HarnessError("runtime control binding is incomplete")
    for name in sorted(expected_paths):
        if actual_paths[name] != expected_paths[name]:
            raise HarnessError("runtime control is outside the canonical repository path")
        require_identity(actual_paths[name], identities[name], "runtime control")


def committed_expectations(
    repo: pathlib.Path, revision: str, supplied: pathlib.Path
) -> tuple[pathlib.Path, bytes, dict[str, object]]:
    repository_path = repo / pathlib.PurePosixPath(EXPECTATIONS_RELATIVE)
    repository_stat = repository_path.stat(follow_symlinks=False)
    if repository_path.is_symlink() or not stat.S_ISREG(repository_stat.st_mode):
        raise HarnessError("canonical expectations is not a plain regular file")
    canonical_path = repository_path.resolve(strict=True)
    supplied_path = supplied.resolve(strict=True)
    if supplied_path != canonical_path:
        raise HarnessError("expectations must use the canonical repository path")
    raw, identity = read_plain_bytes(canonical_path, 1024 * 1024)
    if raw != git_bytes(repo, revision, EXPECTATIONS_RELATIVE):
        raise HarnessError("expectations differ from source commit")
    return canonical_path, raw, identity


def validate_compiler_windows_path(path: str, name: str) -> None:
    reject_game_like_name(name)
    if name.casefold() != "csc.exe":
        raise HarnessError("compiler name is not csc.exe")
    if path.replace("/", "\\").casefold() != EXPECTED_COMPILER_WINDOWS.casefold():
        raise HarnessError("compiler is not the exact x86 Framework compiler")


def validate_compiler_ui_windows_path(path: str, name: str) -> None:
    reject_game_like_name(name)
    if name.casefold() != "cscui.dll":
        raise HarnessError("compiler UI name is not cscui.dll")
    if path.replace("/", "\\").casefold() != EXPECTED_COMPILER_UI_WINDOWS.casefold():
        raise HarnessError("compiler UI is not the exact x86 Framework companion")


def verified_compiler(
    compiler: pathlib.Path, expectations: dict[str, object]
) -> tuple[pathlib.Path, bytes, dict[str, object]]:
    resolved = compiler.resolve(strict=True)
    validate_compiler_windows_path(to_windows_path(resolved), resolved.name)
    raw, identity = read_plain_bytes(resolved)
    expected_identity = {
        "byte_count": expectations["compiler_bytes"],
        "sha256": expectations["compiler_sha256"],
    }
    if identity != expected_identity:
        raise HarnessError("compiler identity does not match committed expectations")
    return resolved, raw, identity


def verified_compiler_ui(
    compiler: pathlib.Path, expectations: dict[str, object]
) -> tuple[pathlib.Path, bytes, dict[str, object]]:
    candidate = compiler.parent / "1033" / "cscui.dll"
    resolved = candidate.resolve(strict=True)
    validate_compiler_ui_windows_path(to_windows_path(resolved), resolved.name)
    raw, identity = read_plain_bytes(resolved)
    expected_identity = {
        "byte_count": expectations["compiler_ui_bytes"],
        "sha256": expectations["compiler_ui_sha256"],
    }
    if identity != expected_identity:
        raise HarnessError("compiler UI identity does not match committed expectations")
    return resolved, raw, identity


def command_binding(argv: list[str], roles: list[str]) -> dict[str, object]:
    if len(argv) != len(roles):
        raise HarnessError("command role mismatch")
    return {
        "argument_count": len(argv),
        "argv_roles": roles,
        "sha256": digest_bytes(canonical(argv)),
    }


def write_exclusive(path: pathlib.Path, value: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
        if stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) & 0o077:
            raise HarnessError("retained file is not mode-private")
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def write_verified_snapshot(
    path: pathlib.Path,
    value: bytes,
    expected: dict[str, object],
    mode: int,
) -> None:
    write_exclusive(path, value)
    os.chmod(path, mode)
    require_identity(path, expected, "snapshot")


class DestinationGuard:
    def __init__(
        self,
        path: pathlib.Path,
        parent_path: pathlib.Path,
        parent_handle: int,
        root_handle: int,
    ) -> None:
        self.path = path
        self.parent_path = parent_path
        self.parent_handle = parent_handle
        self.root_handle = root_handle
        self.parent_identity = self._identity(os.fstat(parent_handle))
        self.root_identity = self._identity(os.fstat(root_handle))

    @staticmethod
    def _identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_uid,
            stat.S_IMODE(value.st_mode),
        )

    def verify(self) -> None:
        if self._identity(os.fstat(self.parent_handle)) != self.parent_identity:
            raise HarnessError("retained parent handle changed")
        if self._identity(os.fstat(self.root_handle)) != self.root_identity:
            raise HarnessError("retained root handle changed")
        parent_now = self.parent_path.stat(follow_symlinks=False)
        root_now = self.path.stat(follow_symlinks=False)
        if (
            self.parent_path.is_symlink()
            or self.path.is_symlink()
            or self._identity(parent_now) != self.parent_identity
            or self._identity(root_now) != self.root_identity
        ):
            raise HarnessError("retained destination path changed")

    def close(self) -> None:
        for name in ("root_handle", "parent_handle"):
            descriptor = getattr(self, name, -1)
            if descriptor >= 0:
                os.close(descriptor)
                setattr(self, name, -1)


def prepare_destination(
    destination: pathlib.Path,
    repo: pathlib.Path,
    locator_objects: list[pathlib.Path],
) -> DestinationGuard:
    absolute = pathlib.Path(os.path.normpath(str(destination.absolute())))
    if absolute.exists() or absolute.is_symlink():
        raise HarnessError("retained destination already exists")
    parent_path = absolute.parent.resolve(strict=True)
    candidate = parent_path / absolute.name
    parent_metadata = parent_path.stat(follow_symlinks=False)
    if (
        parent_path.is_symlink()
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or parent_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
    ):
        raise HarnessError("retained parent must be owned and mode 0700")
    protected = [repo.resolve(strict=True), *locator_objects]
    for item in protected:
        if paths_alias_or_overlap(candidate, item):
            raise HarnessError("retained destination overlaps protected input")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_handle = os.open(parent_path, directory_flags)
    root_handle = -1
    try:
        opened_parent = os.fstat(parent_handle)
        if (opened_parent.st_dev, opened_parent.st_ino) != (
            parent_metadata.st_dev,
            parent_metadata.st_ino,
        ):
            raise HarnessError("retained parent changed before create")
        os.mkdir(candidate.name, 0o700, dir_fd=parent_handle)
        root_handle = os.open(candidate.name, directory_flags, dir_fd=parent_handle)
        os.mkdir("build", 0o700, dir_fd=root_handle)
        guard = DestinationGuard(candidate, parent_path, parent_handle, root_handle)
        guard.verify()
        return guard
    except Exception:
        if root_handle >= 0:
            os.close(root_handle)
        os.close(parent_handle)
        raise


def expected_exit(report: dict[str, object]) -> int:
    summary = report["summary"]
    assert isinstance(summary, dict)
    if summary["completeness"] == "complete":
        return (
            0
            if summary["safety_verdict"]
            == "eligible-for-synthetic-launcher-test"
            else 2
        )
    checks = report["checks"]
    assert isinstance(checks, list) and isinstance(checks[0], dict)
    return 64 if checks[0]["detail_code"] == "usage-or-config" else 3


def validate_exit_pair(report: object, exit_code: int) -> dict[str, object]:
    if not isinstance(report, dict) or exit_code != expected_exit(report):
        raise HarnessError("probe exit code contradicts verified report")
    return report


def is_qualification_eligible(report: dict[str, object], exit_code: int) -> bool:
    return (
        report["summary"]["completeness"] == "complete"
        and exit_code == 0
        and report["summary"]["safety_verdict"]
        == "eligible-for-synthetic-launcher-test"
    )


def finalize_retained_attempt(
    destination: pathlib.Path,
    stdout: bytes,
    stderr: bytes,
    exit_code: int,
    locator_value: dict[str, object],
    locator_raw: bytes,
    expectations_raw: bytes,
    report_bindings: dict[str, object],
    manifest_bindings: dict[str, object],
    build_exit: int,
    build_stdout: bytes,
    build_stderr: bytes,
) -> dict[str, object]:
    verify_output.verify_bytes(stdout, locator_raw, expectations_raw)
    report = validate_exit_pair(verify_output.decode_json(stdout), exit_code)
    if report["summary"]["completeness"] == "complete":
        for key in (
            "source_revision",
            "executable",
            "expectations_sha256",
            "private_locator_sha256",
        ):
            if report["probe"][key] != report_bindings[key]:
                raise HarnessError(f"report {key} binding mismatch")
    manifest = {
        "bindings": manifest_bindings,
        "execution": {
            "build_exit_code": build_exit,
            "build_stderr": {
                "byte_count": len(build_stderr),
                "sha256": digest_bytes(build_stderr),
            },
            "build_stdout": {
                "byte_count": len(build_stdout),
                "sha256": digest_bytes(build_stdout),
            },
            "probe_exit_code": exit_code,
            "probe_stderr": {
                "byte_count": len(stderr),
                "sha256": digest_bytes(stderr),
            },
            "probe_stdout": {
                "byte_count": len(stdout),
                "sha256": digest_bytes(stdout),
            },
            "stream_cap_bytes": STREAM_CAP_BYTES,
            "timeout_seconds": PROBE_TIMEOUT_SECONDS,
        },
        "harness": {"id": HARNESS_ID, "version": HARNESS_VERSION},
        "retained_artifacts": {"canonical_stdout": "probe-output.json"},
        "schema_version": SCHEMA_VERSION,
        "verification": {
            "canonical_stdout": True,
            "completeness": report["summary"]["completeness"],
            "privacy_locator_enforced": True,
            "qualification_eligible": is_qualification_eligible(report, exit_code),
            "result": "pass",
            "safety_verdict": report["summary"]["safety_verdict"],
        },
    }
    forbidden = verify_output.private_strings_from_value(locator_value)
    for string_value in verify_output.iter_strings(manifest):
        if any(item.casefold() in string_value.casefold() for item in forbidden):
            raise HarnessError("private locator string leaked into manifest")
    manifest_bytes = canonical(manifest)
    report_path = destination / "probe-output.json"
    manifest_path = destination / "retained-run-v1.json"
    if (
        report_path.exists()
        or report_path.is_symlink()
        or manifest_path.exists()
        or manifest_path.is_symlink()
    ):
        raise FileExistsError("retained artifact already exists")
    write_exclusive(report_path, stdout)
    write_exclusive(manifest_path, manifest_bytes)
    return manifest


def retained_run(args: argparse.Namespace) -> None:
    repo = args.repo.resolve(strict=True)
    locator_argument = args.private_locator.absolute()
    locator_stat = locator_argument.stat(follow_symlinks=False)
    if locator_argument.is_symlink() or not stat.S_ISREG(locator_stat.st_mode):
        raise HarnessError("private locator is not a plain regular file")
    locator = locator_argument.resolve(strict=True)
    bindings, source_snapshots = source_bindings(repo, args.source_commit)
    validate_runtime_controls(repo, bindings)
    expectations, expectations_raw, expectations_identity = committed_expectations(
        repo, args.source_commit, args.expectations
    )
    expectations_value = verify_output.parse_expectations(expectations_raw)
    compiler, compiler_raw, compiler_identity = verified_compiler(
        args.compiler, expectations_value
    )
    compiler_ui, compiler_ui_raw, compiler_ui_identity = verified_compiler_ui(
        compiler, expectations_value
    )
    locator_raw, locator_identity = read_plain_bytes(locator, 1024 * 1024)
    locator_value = verify_output.parse_private_locator(locator_raw)
    locator_objects = mapped_locator_paths(locator_value)
    destination_guard = prepare_destination(args.retained_dir, repo, locator_objects)
    destination = destination_guard.path
    executable = destination / "build" / "OriginalHostQualification.exe"
    reject_game_like_name(executable.name)
    snapshot_paths = []
    for name, source_bytes in source_snapshots.items():
        snapshot = destination / "build" / name
        write_exclusive(snapshot, source_bytes)
        os.chmod(snapshot, 0o400)
        snapshot_paths.append(snapshot)
    expectations_snapshot = destination / "build" / "expectations.json"
    locator_snapshot = destination / "build" / "private-locator.json"
    compiler_snapshot = destination / "build" / "csc.exe"
    compiler_ui_directory = destination / "build" / "1033"
    os.mkdir(compiler_ui_directory, 0o700)
    compiler_ui_snapshot = compiler_ui_directory / "cscui.dll"
    write_exclusive(expectations_snapshot, expectations_raw)
    write_exclusive(locator_snapshot, locator_raw)
    write_verified_snapshot(compiler_snapshot, compiler_raw, compiler_identity, 0o700)
    write_verified_snapshot(
        compiler_ui_snapshot, compiler_ui_raw, compiler_ui_identity, 0o400
    )
    os.chmod(expectations_snapshot, 0o400)
    os.chmod(locator_snapshot, 0o400)
    if file_identity(expectations_snapshot) != expectations_identity:
        raise HarnessError("expectations snapshot identity mismatch")
    if file_identity(locator_snapshot) != locator_identity:
        raise HarnessError("locator snapshot identity mismatch")
    if file_identity(compiler_snapshot) != compiler_identity:
        raise HarnessError("compiler snapshot identity mismatch")
    if file_identity(compiler_ui_snapshot) != compiler_ui_identity:
        raise HarnessError("compiler UI snapshot identity mismatch")
    verify_output.static_source(
        [
            destination / "build" / pathlib.PurePosixPath(relative).name
            for relative in SOURCE_PATHS
        ]
    )

    windows_executable = to_windows_path(executable.parent) + "\\" + executable.name
    source_windows = [
        to_windows_path(destination / "build" / pathlib.PurePosixPath(relative).name)
        for relative in SOURCE_PATHS
    ]
    build_argv = [
        str(compiler_snapshot),
        "/nologo",
        "/noconfig",
        "/warnaserror+",
        "/optimize+",
        "/platform:x86",
        "/target:exe",
        *("/r:" + path for path in FRAMEWORK_REFERENCE_WINDOWS),
        "/out:" + windows_executable,
        *source_windows,
    ]
    build_roles = [
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
    ]
    build_binding = command_binding(build_argv, build_roles)
    destination_guard.verify()
    if file_identity(compiler) != compiler_identity:
        raise HarnessError("compiler changed before build")
    if file_identity(compiler_snapshot) != compiler_identity:
        raise HarnessError("compiler snapshot changed before build")
    if file_identity(compiler_ui) != compiler_ui_identity:
        raise HarnessError("compiler UI changed before build")
    if file_identity(compiler_ui_snapshot) != compiler_ui_identity:
        raise HarnessError("compiler UI snapshot changed before build")
    build_exit, build_stdout, build_stderr = capture_bounded(
        build_argv,
        BUILD_TIMEOUT_SECONDS,
        STREAM_CAP_BYTES,
        destination / "build",
    )
    if build_exit != 0:
        raise HarnessError("probe build failed")
    executable_identity = file_identity(executable)
    os.chmod(executable, 0o700)
    if file_identity(compiler) != compiler_identity:
        raise HarnessError("compiler changed during build")
    if file_identity(compiler_snapshot) != compiler_identity:
        raise HarnessError("compiler snapshot changed during build")
    if file_identity(compiler_ui) != compiler_ui_identity:
        raise HarnessError("compiler UI changed during build")
    if file_identity(compiler_ui_snapshot) != compiler_ui_identity:
        raise HarnessError("compiler UI snapshot changed during build")

    probe_argv = [
        str(executable),
        "--expectations",
        to_windows_path(expectations_snapshot),
        "--private-config",
        to_windows_path(locator_snapshot),
        "--source-revision",
        args.source_commit,
    ]
    probe_roles = [
        "probe",
        "expectations-option",
        "expectations",
        "private-config-option",
        "private-locator",
        "source-revision-option",
        "source-revision",
    ]
    probe_binding = command_binding(probe_argv, probe_roles)
    destination_guard.verify()
    if file_identity(executable) != executable_identity:
        raise HarnessError("probe executable changed before run")
    if file_identity(expectations_snapshot) != expectations_identity:
        raise HarnessError("expectations snapshot changed before run")
    if file_identity(locator_snapshot) != locator_identity:
        raise HarnessError("private locator snapshot changed before run")
    exit_code, stdout, stderr = capture_bounded(
        probe_argv,
        PROBE_TIMEOUT_SECONDS,
        STREAM_CAP_BYTES,
        destination / "build",
    )
    if file_identity(compiler) != compiler_identity:
        raise HarnessError("compiler changed before retained publication")
    if file_identity(compiler_snapshot) != compiler_identity:
        raise HarnessError("compiler snapshot changed before retained publication")
    if file_identity(compiler_ui) != compiler_ui_identity:
        raise HarnessError("compiler UI changed before retained publication")
    if file_identity(compiler_ui_snapshot) != compiler_ui_identity:
        raise HarnessError("compiler UI snapshot changed before retained publication")
    if file_identity(executable) != executable_identity:
        raise HarnessError("probe executable changed during run")
    if file_identity(expectations_snapshot) != expectations_identity:
        raise HarnessError("expectations snapshot changed during run")
    if file_identity(locator_snapshot) != locator_identity:
        raise HarnessError("private locator snapshot changed during run")
    for source_record, snapshot in zip(bindings, snapshot_paths):
        if file_identity(snapshot) != source_record["identity"]:
            raise HarnessError("source snapshot changed during build or run")
    manifest_bindings = {
            "build_command": build_binding,
            "compiler": compiler_identity,
            "compiler_ui": compiler_ui_identity,
            "expectations": expectations_identity,
            "private_locator": locator_identity,
            "probe_command": probe_binding,
            "probe_executable": executable_identity,
            "source_commit": args.source_commit,
            "sources": bindings,
    }
    destination_guard.verify()
    finalize_retained_attempt(
        destination,
        stdout,
        stderr,
        exit_code,
        locator_value,
        locator_raw,
        expectations_raw,
        {
            "source_revision": args.source_commit,
            "executable": executable_identity,
            "expectations_sha256": expectations_identity["sha256"],
            "private_locator_sha256": locator_identity["sha256"],
        },
        manifest_bindings,
        build_exit,
        build_stdout,
        build_stderr,
    )
    destination_guard.verify()
    destination_guard.close()
    print("PASS")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        success = root / "success"
        success.write_text("#!/bin/sh\nprintf ok\nprintf err >&2\n", encoding="utf-8")
        success.chmod(0o700)
        code, stdout, stderr = capture_bounded([str(success)], 2, 16)
        if (code, stdout, stderr) != (0, b"ok", b"err"):
            raise AssertionError("bounded capture success")
        environment_probe = root / "environment-probe"
        environment_probe.write_text(
            "#!/usr/bin/python3\nimport os,sys\nsys.stdout.write(str(len(os.environ)))\n",
            encoding="utf-8",
        )
        environment_probe.chmod(0o700)
        code, stdout, stderr = capture_bounded([str(environment_probe)], 2, 16)
        if code != 0 or stderr != b"" or stdout not in {b"0", b"1"}:
            raise AssertionError("bounded capture environment")
        oversized_identity = root / "oversized-identity.bin"
        with oversized_identity.open("wb") as output:
            output.truncate(STREAM_CAP_BYTES + 1)
        try:
            read_plain_bytes(oversized_identity)
        except HarnessError:
            pass
        else:
            raise AssertionError("identity pre-read byte limit")
        overflow = root / "overflow"
        overflow.write_text("#!/bin/sh\nprintf 12345\n", encoding="utf-8")
        overflow.chmod(0o700)
        try:
            capture_bounded([str(overflow)], 2, 4)
        except HarnessError:
            pass
        else:
            raise AssertionError("bounded capture overflow")
        timeout = root / "timeout"
        timeout.write_text("#!/bin/sh\nsleep 1\n", encoding="utf-8")
        timeout.chmod(0o700)
        try:
            capture_bounded([str(timeout)], 0.05, 16)
        except HarnessError:
            pass
        else:
            raise AssertionError("bounded capture timeout")
        target = root / "exclusive"
        write_exclusive(target, b"first")
        try:
            write_exclusive(target, b"second")
        except FileExistsError:
            pass
        else:
            raise AssertionError("exclusive publication")
        binding = command_binding(["/bin/true"], ["tool"])
        if binding["argument_count"] != 1 or len(binding["sha256"]) != 64:
            raise AssertionError("command binding")
        reject_game_like_name("csc.exe")
        validate_compiler_windows_path(EXPECTED_COMPILER_WINDOWS, "csc.exe")
        validate_compiler_ui_windows_path(
            EXPECTED_COMPILER_UI_WINDOWS, "cscui.dll"
        )
        for wrong_path, wrong_name in (
            (r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe", "csc.exe"),
            (EXPECTED_COMPILER_WINDOWS, "other.exe"),
            (EXPECTED_COMPILER_WINDOWS, "cm0102.exe"),
        ):
            try:
                validate_compiler_windows_path(wrong_path, wrong_name)
            except HarnessError:
                pass
            else:
                raise AssertionError("compiler path/name rejection")
        for wrong_path, wrong_name in (
            (
                r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\1033\cscui.dll",
                "cscui.dll",
            ),
            (EXPECTED_COMPILER_UI_WINDOWS, "other.dll"),
            (EXPECTED_COMPILER_UI_WINDOWS, "cm0102.dll"),
        ):
            try:
                validate_compiler_ui_windows_path(wrong_path, wrong_name)
            except HarnessError:
                pass
            else:
                raise AssertionError("compiler UI path/name rejection")
        for forbidden_name in ("cm0102.exe", "Championship-Manager.exe"):
            try:
                reject_game_like_name(forbidden_name)
            except HarnessError:
                pass
            else:
                raise AssertionError("game-like name rejection")
        forbidden_executable = root / "cm0102.exe"
        forbidden_executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        forbidden_executable.chmod(0o700)
        try:
            capture_bounded([str(forbidden_executable)], 1, 16)
        except HarnessError:
            pass
        else:
            raise AssertionError("game-like execution rejection")
        identity_fixture = root / "identity.bin"
        identity_fixture.write_bytes(b"verified")
        expected_identity = file_identity(identity_fixture)
        identity_fixture.write_bytes(b"replaced")
        try:
            require_identity(identity_fixture, expected_identity, "fixture")
        except HarnessError:
            pass
        else:
            raise AssertionError("identity drift rejection")
        bad_snapshot = root / "bad-snapshot.exe"
        try:
            write_verified_snapshot(bad_snapshot, b"different", expected_identity, 0o700)
        except HarnessError:
            pass
        else:
            raise AssertionError("snapshot identity rejection")
        symlink_fixture = root / "identity-link"
        symlink_fixture.symlink_to(identity_fixture)
        try:
            file_identity(symlink_fixture)
        except HarnessError:
            pass
        else:
            raise AssertionError("identity symlink rejection")

        full_report = {
            "checks": [{"detail_code": "eligible"}],
            "summary": {
                "completeness": "complete",
                "safety_verdict": "eligible-for-synthetic-launcher-test",
            },
        }
        unsafe_report = json.loads(json.dumps(full_report))
        unsafe_report["summary"]["safety_verdict"] = "unsafe"
        minimal_report = {
            "checks": [{"detail_code": "unhandled-v1-host-observation-exception-80131501"}],
            "summary": {"completeness": "incomplete", "safety_verdict": "inconclusive"},
        }
        usage_report = json.loads(json.dumps(minimal_report))
        usage_report["checks"][0]["detail_code"] = "usage-or-config"
        for report, exit_code in (
            (full_report, 0),
            (unsafe_report, 2),
            (minimal_report, 3),
            (usage_report, 64),
        ):
            validate_exit_pair(report, exit_code)
            try:
                validate_exit_pair(report, 99)
            except HarnessError:
                pass
            else:
                raise AssertionError("exit/report mismatch rejection")

        private_value = {
            "clean_manifest": r"C:\private\clean.tsv",
            "clean_tree": r"C:\private\clean",
            "installed_tree": r"C:\private\installed",
            "iso_file": r"C:\private\disc.iso",
            "optical_root": "D:\\",
            "schema_version": 1,
            "virtual_store_tree": r"C:\private\virtual",
        }
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
            "required_api_ids": sorted(verify_output.REQUIRED_API_IDS),
            "required_tool_ids": ["csc-x86", "powershell", "python313"],
            "schema_version": 1,
        }
        strict_private = root / "strict-private.json"
        strict_expectations = root / "strict-expectations.json"
        strict_private.write_bytes(verify_output.canonical(private_value))
        strict_expectations.write_bytes(verify_output.canonical(expectations_value))
        strict_full = verify_output.synthetic_full_document(
            expectations_value,
            strict_expectations.read_bytes(),
            strict_private.read_bytes(),
        )
        strict_cases = [(strict_full, 0)]
        strict_unsafe = json.loads(json.dumps(strict_full))
        strict_unsafe["guards"]["game_process_count_after"] = 1
        unsafe_check = next(
            item
            for item in strict_unsafe["checks"]
            if item["id"] == "no-game-process-after"
        )
        unsafe_check["outcome"] = "fail"
        unsafe_check["detail_code"] = "present"
        strict_unsafe["summary"]["passed_count"] -= 1
        strict_unsafe["summary"]["failed_count"] += 1
        strict_unsafe["summary"]["safety_verdict"] = "unsafe"
        strict_cases.append((strict_unsafe, 2))
        minimal_detail = "unhandled-v1-host-observation-exception-80131501"
        strict_minimal = {
            "capabilities": {},
            "checks": [{"detail_code": minimal_detail, "id": "probe", "outcome": "error", "required": True}],
            "errors": [{"category": "probe", "check_id": "probe", "detail_code": minimal_detail}],
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
        strict_cases.append((strict_minimal, 3))
        report_binding_fixture = {
            "source_revision": strict_full["probe"]["source_revision"],
            "executable": strict_full["probe"]["executable"],
            "expectations_sha256": strict_full["probe"]["expectations_sha256"],
            "private_locator_sha256": strict_full["probe"]["private_locator_sha256"],
        }
        identity_fixture_value = {"byte_count": 1, "sha256": "7" * 64}
        manifest_binding_fixture = {
            "build_command": command_binding(["/bound/csc.exe"], ["compiler"]),
            "compiler": identity_fixture_value,
            "compiler_ui": identity_fixture_value,
            "expectations": verify_output.bytes_identity(strict_expectations.read_bytes()),
            "private_locator": verify_output.bytes_identity(strict_private.read_bytes()),
            "probe_command": command_binding(["/bound/probe.exe"], ["probe"]),
            "probe_executable": strict_full["probe"]["executable"],
            "source_commit": strict_full["probe"]["source_revision"],
            "sources": [{"id": "fixture.cs", "identity": identity_fixture_value}],
        }
        for index, (report, exit_code) in enumerate(strict_cases):
            producer = root / f"strict-producer-{index}"
            payload = verify_output.canonical(report)
            producer.write_text(
                "#!/usr/bin/python3\n"
                "import sys\n"
                f"sys.stdout.buffer.write({payload!r})\n"
                f"sys.exit({exit_code})\n",
                encoding="utf-8",
            )
            os.chmod(producer, 0o700)
            actual_exit, actual_stdout, actual_stderr = capture_bounded(
                [str(producer)], 2, STREAM_CAP_BYTES
            )
            if actual_stderr != b"":
                raise AssertionError("strict producer wrote stderr")
            report_path = root / f"strict-report-{index}.json"
            report_path.write_bytes(actual_stdout)
            verify_output.verify(report_path, strict_private, strict_expectations)
            decoded = verify_output.decode_json(report_path.read_bytes())
            validate_exit_pair(decoded, actual_exit)
            if is_qualification_eligible(decoded, actual_exit) != (index == 0):
                raise AssertionError(
                    "qualification eligibility did not distinguish full from unsafe/incomplete"
                )
            retained = root / f"retained-{index}"
            retained.mkdir(mode=0o700)
            manifest = finalize_retained_attempt(
                retained,
                actual_stdout,
                actual_stderr,
                actual_exit,
                private_value,
                strict_private.read_bytes(),
                strict_expectations.read_bytes(),
                report_binding_fixture,
                manifest_binding_fixture,
                0,
                b"build-out",
                b"build-err",
            )
            if manifest["verification"]["qualification_eligible"] != (index == 0):
                raise AssertionError("published qualification eligibility")
            if (retained / "probe-output.json").read_bytes() != actual_stdout:
                raise AssertionError("published canonical report")
            retained_manifest = (retained / "retained-run-v1.json").read_bytes()
            if retained_manifest != canonical(manifest):
                raise AssertionError("published canonical manifest")
            if manifest["execution"]["probe_stdout"] != verify_output.bytes_identity(actual_stdout):
                raise AssertionError("published stdout identity")

        wrong_exit = root / "retained-wrong-exit"
        wrong_exit.mkdir(mode=0o700)
        try:
            finalize_retained_attempt(
                wrong_exit,
                verify_output.canonical(strict_full),
                b"",
                2,
                private_value,
                strict_private.read_bytes(),
                strict_expectations.read_bytes(),
                report_binding_fixture,
                manifest_binding_fixture,
                0,
                b"",
                b"",
            )
        except HarnessError:
            pass
        else:
            raise AssertionError("wrong exit publication rejection")
        if list(wrong_exit.iterdir()):
            raise AssertionError("wrong exit published artifacts")

        private_leak = root / "retained-private-leak"
        private_leak.mkdir(mode=0o700)
        leaking_bindings = dict(manifest_binding_fixture)
        leaking_bindings["source_commit"] = private_value["clean_tree"]
        try:
            finalize_retained_attempt(
                private_leak,
                verify_output.canonical(strict_full),
                b"",
                0,
                private_value,
                strict_private.read_bytes(),
                strict_expectations.read_bytes(),
                report_binding_fixture,
                leaking_bindings,
                0,
                b"",
                b"",
            )
        except HarnessError:
            pass
        else:
            raise AssertionError("private manifest leak rejection")
        if list(private_leak.iterdir()):
            raise AssertionError("private leak published artifacts")

        no_replace = root / "retained-no-replace"
        no_replace.mkdir(mode=0o700)
        existing_report = no_replace / "probe-output.json"
        existing_report.write_bytes(b"existing")
        try:
            finalize_retained_attempt(
                no_replace,
                verify_output.canonical(strict_full),
                b"",
                0,
                private_value,
                strict_private.read_bytes(),
                strict_expectations.read_bytes(),
                report_binding_fixture,
                manifest_binding_fixture,
                0,
                b"",
                b"",
            )
        except FileExistsError:
            pass
        else:
            raise AssertionError("retained artifact no-replace")
        if existing_report.read_bytes() != b"existing" or (no_replace / "retained-run-v1.json").exists():
            raise AssertionError("retained no-replace preservation")
        repo = root / "repo"
        repo.mkdir()
        for relative in (*BOUND_PATHS, EXPECTATIONS_RELATIVE):
            source = repo / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(f"// {source.name}\n", encoding="utf-8")
        git = "/usr/bin/git"
        for argv in (
            [git, "-C", str(repo), "init", "-q"],
            [git, "-C", str(repo), "add", "--", *BOUND_PATHS, EXPECTATIONS_RELATIVE],
            [
                git,
                "-C",
                str(repo),
                "-c",
                "user.name=Harness Self Test",
                "-c",
                "user.email=harness-self-test.invalid",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
        ):
            code, _stdout, _stderr = capture_bounded(argv, 10, STREAM_CAP_BYTES)
            if code != 0:
                raise AssertionError("git fixture")
        revision = run_small([git, "-C", str(repo), "rev-parse", "HEAD"]).decode().strip()
        source_records, snapshots = source_bindings(repo, revision)
        if len(source_records) != len(BOUND_PATHS) or set(snapshots) != {
            pathlib.PurePosixPath(item).name for item in BOUND_PATHS
        }:
            raise AssertionError("source binding fixture")
        harness_fixture = repo / CONTROL_PATHS[1]
        verifier_fixture = repo / CONTROL_PATHS[0]
        validate_runtime_controls(
            repo, source_records, harness_fixture, verifier_fixture
        )
        external_harness = root / "external-retained-run.py"
        external_harness.write_bytes(harness_fixture.read_bytes())
        try:
            validate_runtime_controls(
                repo, source_records, external_harness, verifier_fixture
            )
        except HarnessError:
            pass
        else:
            raise AssertionError("external runtime control rejection")
        external_verifier = root / "external-verify-output.py"
        external_verifier.write_bytes(verifier_fixture.read_bytes())
        try:
            validate_runtime_controls(
                repo, source_records, harness_fixture, external_verifier
            )
        except HarnessError:
            pass
        else:
            raise AssertionError("external verifier rejection")
        expectations_path, expectations_bytes, expectations_identity = committed_expectations(
            repo, revision, repo / EXPECTATIONS_RELATIVE
        )
        if expectations_path != (repo / EXPECTATIONS_RELATIVE).resolve() or expectations_identity != verify_output.bytes_identity(expectations_bytes):
            raise AssertionError("committed expectations fixture")
        alternate_expectations = root / "alternate-expectations.json"
        alternate_expectations.write_bytes(expectations_bytes)
        try:
            committed_expectations(repo, revision, alternate_expectations)
        except HarnessError:
            pass
        else:
            raise AssertionError("noncanonical expectations rejection")
        canonical_expectations = repo / EXPECTATIONS_RELATIVE
        canonical_expectations.write_bytes(b"dirty")
        try:
            committed_expectations(repo, revision, canonical_expectations)
        except HarnessError:
            pass
        else:
            raise AssertionError("dirty expectations rejection")
        canonical_expectations.write_bytes(expectations_bytes)
        expectations_backing = root / "expectations-backing.json"
        canonical_expectations.rename(expectations_backing)
        canonical_expectations.symlink_to(expectations_backing)
        try:
            committed_expectations(repo, revision, canonical_expectations)
        except HarnessError:
            pass
        else:
            raise AssertionError("symlink expectations rejection")
        canonical_expectations.unlink()
        expectations_backing.rename(canonical_expectations)
        (repo / SOURCE_PATHS[0]).write_text("// dirty\n", encoding="utf-8")
        try:
            source_bindings(repo, revision)
        except HarnessError:
            pass
        else:
            raise AssertionError("dirty source rejection")
        protected = root / "protected"
        protected.mkdir()
        protected_alias = root / "protected-alias"
        protected_alias.symlink_to(protected, target_is_directory=True)
        retained_guard = prepare_destination(root / "retained", repo, [protected.resolve()])
        retained = retained_guard.path
        if stat.S_IMODE(retained.stat().st_mode) != 0o700:
            raise AssertionError("private retained mode")
        retained_guard.verify()
        try:
            prepare_destination(retained, repo, [protected.resolve()])
        except HarnessError:
            pass
        else:
            raise AssertionError("destination no-replace")
        overlap_candidates = (
            repo / "retained-inside-repo",
            root / "missing-segment" / ".." / "repo" / "normalized-inside-repo",
            protected / "retained-inside-input",
            protected_alias / "retained-through-alias",
            root / "future-parent",
        )
        future_locator = resolve_nearest(root / "future-parent" / "missing" / "virtual")
        for candidate in overlap_candidates:
            objects = [protected.resolve(), future_locator]
            try:
                prepare_destination(candidate, repo, objects)
            except HarnessError:
                if candidate.exists():
                    raise AssertionError("overlap rejection created destination")
            else:
                raise AssertionError("destination overlap rejection")
        retained_guard.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    run = sub.add_parser("run")
    run.add_argument("--repo", required=True, type=pathlib.Path)
    run.add_argument("--source-commit", required=True)
    run.add_argument("--compiler", required=True, type=pathlib.Path)
    run.add_argument("--expectations", required=True, type=pathlib.Path)
    run.add_argument("--private-locator", required=True, type=pathlib.Path)
    run.add_argument("--retained-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
        print("PASS")
    else:
        retained_run(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HarnessError, OSError, ValueError, AssertionError) as error:
        print(f"FAIL: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
