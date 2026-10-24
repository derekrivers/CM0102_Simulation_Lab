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
HARNESS_VERSION = "1.0.0"
PROBE_TIMEOUT_SECONDS = 30 * 60
BUILD_TIMEOUT_SECONDS = 5 * 60
STREAM_CAP_BYTES = 4 * 1024 * 1024
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


def file_identity(path: pathlib.Path) -> dict[str, object]:
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or path.is_symlink():
        raise HarnessError("identity target is not a plain regular file")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            digest.update(chunk)
    after = path.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise HarnessError("identity target changed while hashing")
    return {"byte_count": count, "sha256": digest.hexdigest()}


def _kill(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()


def capture_bounded(
    argv: list[str], timeout_seconds: float, cap_bytes: int
) -> tuple[int, bytes, bytes]:
    if not argv or not os.path.isabs(argv[0]):
        raise HarnessError("command executable must be an absolute path")
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        actual = worktree_path.read_bytes()
        committed = git_bytes(repo, revision, relative)
        if actual != committed:
            raise HarnessError("source differs from source commit")
        worktree_stat = worktree_path.stat(follow_symlinks=False)
        if worktree_path.is_symlink() or not stat.S_ISREG(worktree_stat.st_mode):
            raise HarnessError("source is not a plain regular file")
        snapshots[pathlib.PurePosixPath(relative).name] = committed
        bindings.append(
            {
                "id": pathlib.PurePosixPath(relative).name,
                "identity": {
                    "byte_count": len(actual),
                    "sha256": digest_bytes(actual),
                },
            }
        )
    return bindings, snapshots


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


def prepare_destination(destination: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    absolute = destination.absolute()
    if absolute.exists() or absolute.is_symlink():
        raise HarnessError("retained destination already exists")
    repo_resolved = repo.resolve(strict=True)
    parent = absolute.parent.resolve(strict=True)
    candidate = parent / absolute.name
    if candidate == repo_resolved or repo_resolved in candidate.parents:
        raise HarnessError("retained destination must be outside the repository")
    os.mkdir(candidate, 0o700)
    if stat.S_IMODE(candidate.stat().st_mode) != 0o700:
        raise HarnessError("retained destination is not mode-private")
    build = candidate / "build"
    os.mkdir(build, 0o700)
    return candidate


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


def retained_run(args: argparse.Namespace) -> None:
    repo = args.repo.resolve(strict=True)
    compiler = args.compiler.resolve(strict=True)
    expectations = args.expectations.resolve(strict=True)
    locator = args.private_locator.resolve(strict=True)
    bindings, source_snapshots = source_bindings(repo, args.source_commit)
    compiler_identity = file_identity(compiler)
    expectations_identity = file_identity(expectations)
    locator_identity = file_identity(locator)
    destination = prepare_destination(args.retained_dir, repo)
    executable = destination / "build" / "OriginalHostQualification.exe"
    snapshot_paths = []
    for name, source_bytes in source_snapshots.items():
        snapshot = destination / "build" / name
        write_exclusive(snapshot, source_bytes)
        os.chmod(snapshot, 0o400)
        snapshot_paths.append(snapshot)
    expectations_snapshot = destination / "build" / "expectations.json"
    locator_snapshot = destination / "build" / "private-locator.json"
    write_exclusive(expectations_snapshot, expectations.read_bytes())
    write_exclusive(locator_snapshot, locator.read_bytes())
    os.chmod(expectations_snapshot, 0o400)
    os.chmod(locator_snapshot, 0o400)
    if file_identity(expectations_snapshot) != expectations_identity:
        raise HarnessError("expectations snapshot identity mismatch")
    if file_identity(locator_snapshot) != locator_identity:
        raise HarnessError("locator snapshot identity mismatch")
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
        str(compiler),
        "/nologo",
        "/warnaserror+",
        "/optimize+",
        "/platform:x86",
        "/target:exe",
        "/r:System.Security.dll",
        "/r:System.Web.Extensions.dll",
        "/r:System.Windows.Forms.dll",
        "/out:" + windows_executable,
        *source_windows,
    ]
    build_roles = [
        "compiler",
        "nologo",
        "warnings-as-errors",
        "optimize",
        "platform-x86",
        "target-exe",
        "reference-system-security",
        "reference-system-web-extensions",
        "reference-system-windows-forms",
        "output-probe",
        "source-canonical-json",
        "source-original-host-qualification",
    ]
    build_binding = command_binding(build_argv, build_roles)
    if file_identity(compiler) != compiler_identity:
        raise HarnessError("compiler changed before build")
    build_exit, build_stdout, build_stderr = capture_bounded(
        build_argv, BUILD_TIMEOUT_SECONDS, STREAM_CAP_BYTES
    )
    if build_exit != 0:
        raise HarnessError("probe build failed")
    executable_identity = file_identity(executable)
    os.chmod(executable, 0o700)
    if file_identity(compiler) != compiler_identity:
        raise HarnessError("compiler changed during build")

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
    if file_identity(executable) != executable_identity:
        raise HarnessError("probe executable changed before run")
    if file_identity(expectations_snapshot) != expectations_identity:
        raise HarnessError("expectations snapshot changed before run")
    if file_identity(locator_snapshot) != locator_identity:
        raise HarnessError("private locator snapshot changed before run")
    exit_code, stdout, stderr = capture_bounded(
        probe_argv, PROBE_TIMEOUT_SECONDS, STREAM_CAP_BYTES
    )
    if file_identity(compiler) != compiler_identity:
        raise HarnessError("compiler changed before retained publication")
    if file_identity(executable) != executable_identity:
        raise HarnessError("probe executable changed during run")
    if file_identity(expectations_snapshot) != expectations_identity:
        raise HarnessError("expectations snapshot changed during run")
    if file_identity(locator_snapshot) != locator_identity:
        raise HarnessError("private locator snapshot changed during run")
    for source_record, snapshot in zip(bindings, snapshot_paths):
        if file_identity(snapshot) != source_record["identity"]:
            raise HarnessError("source snapshot changed during build or run")
    report_path = destination / "probe-output.json"
    write_exclusive(report_path, stdout)
    verify_output.verify(report_path, locator_snapshot, expectations_snapshot)
    report = verify_output.decode_json(stdout)
    if not isinstance(report, dict) or exit_code != expected_exit(report):
        raise HarnessError("probe exit code contradicts verified report")
    if report["probe"]["source_revision"] != args.source_commit:
        raise HarnessError("report source revision mismatch")
    if report["probe"]["executable"] != executable_identity:
        raise HarnessError("report executable identity mismatch")
    if report["probe"]["expectations_sha256"] != expectations_identity["sha256"]:
        raise HarnessError("report expectations identity mismatch")
    if report["probe"]["private_locator_sha256"] != locator_identity["sha256"]:
        raise HarnessError("report locator identity mismatch")
    if report["summary"]["completeness"] != "complete":
        raise HarnessError("retained production run must be complete")

    manifest = {
        "bindings": {
            "build_command": build_binding,
            "compiler": compiler_identity,
            "expectations": expectations_identity,
            "private_locator": locator_identity,
            "probe_command": probe_binding,
            "probe_executable": executable_identity,
            "source_commit": args.source_commit,
            "sources": bindings,
        },
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
            "result": "pass",
            "safety_verdict": report["summary"]["safety_verdict"],
        },
    }
    manifest_bytes = canonical(manifest)
    forbidden = verify_output.private_strings(locator_snapshot)
    for string_value in verify_output.iter_strings(manifest):
        if any(item.casefold() in string_value.casefold() for item in forbidden):
            raise HarnessError("private locator string leaked into manifest")
    write_exclusive(destination / "retained-run-v1.json", manifest_bytes)
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
        repo = root / "repo"
        repo.mkdir()
        for relative in BOUND_PATHS:
            source = repo / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(f"// {source.name}\n", encoding="utf-8")
        git = "/usr/bin/git"
        for argv in (
            [git, "-C", str(repo), "init", "-q"],
            [git, "-C", str(repo), "add", "--", *BOUND_PATHS],
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
        (repo / SOURCE_PATHS[0]).write_text("// dirty\n", encoding="utf-8")
        try:
            source_bindings(repo, revision)
        except HarnessError:
            pass
        else:
            raise AssertionError("dirty source rejection")
        retained = prepare_destination(root / "retained", repo)
        if stat.S_IMODE(retained.stat().st_mode) != 0o700:
            raise AssertionError("private retained mode")
        try:
            prepare_destination(retained, repo)
        except HarnessError:
            pass
        else:
            raise AssertionError("destination no-replace")


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
