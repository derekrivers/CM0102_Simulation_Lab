#!/usr/bin/env python3
"""Strict static/profile verification for the harmless WinForms fixture."""

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


MAX_SOURCE_BYTES = 256 * 1024
FIXTURE_NAME = "SyntheticFixture.cs"
TEST_NAME = "SyntheticFixtureTests.cs"
PROFILE_NAME = "synthetic-launcher-fixture-v1.json"
VERIFIER_NAME = "verify_fixture.py"

FROZEN_IDENTITIES = {
    FIXTURE_NAME: {
        "byte_count": 20355,
        "sha256": "d730bda0acc2cf89ab6e212f49620a2e42b00392a3976f1467c0931bce66ae1c",
    },
    TEST_NAME: {
        "byte_count": 11742,
        "sha256": "da970254f9455ff14e681de0c291235cf35298c3fc230b194f8ce778b7a83cf6",
    },
}

ALLOWED_ENVIRONMENT_BLOCK = '''internal static readonly string[] AllowedEnvironmentNames = new string[]
        {
            CwdHashName,
            InputNonceName,
            "SystemRoot",
            "TEMP",
            "TMP",
            "WINDIR"
        };'''

PROFILE = {
    "schema_version": 1,
    "client": {"height": 240, "width": 320},
    "display": {"minimum_height": 352, "minimum_width": 400, "process_dpi_aware": True},
    "environment_names": [
        "CM0102_SYNTHETIC_CWD_SHA256",
        "CM0102_SYNTHETIC_INPUT_NONCE",
        "SystemRoot",
        "TEMP",
        "TMP",
        "WINDIR",
    ],
    "input": {"button": "left", "nonce_bits": 32, "x": 96, "y": 112},
    "messages": {"magic": 0x434D0101, "protocol": 0x8051, "state": 0x8052},
    "paint": {
        "complete": [[0, 0, 80, 240, 24, 176, 80], [80, 0, 80, 240, 224, 176, 24],
                     [160, 0, 80, 240, 128, 48, 192], [240, 0, 80, 240, 32, 200, 216]],
        "fault": [[0, 0, 80, 240, 0, 0, 0], [80, 0, 80, 240, 224, 0, 224],
                  [160, 0, 80, 240, 0, 0, 0], [240, 0, 80, 240, 224, 0, 224]],
        "ready": [[0, 0, 80, 240, 192, 32, 32], [80, 0, 80, 240, 32, 64, 192],
                  [160, 0, 80, 240, 32, 160, 64], [240, 0, 80, 240, 16, 24, 32]],
    },
    "position": {"x": 64, "y": 64},
    "states": {"complete": 2, "fault": 3, "ready": 1},
    "token": {"administrator": False, "elevated": False, "elevation_type": 3,
              "integrity_rid": 0x2000},
}

REQUIRED_FIXTURE_FRAGMENTS = (
    "private static int Main()",
    "Environment.GetCommandLineArgs().Length",
    "sha.ComputeHash(Encoding.Unicode.GetBytes(value))",
    "AutoScaleMode = AutoScaleMode.None;",
    "ClientSize = new Size(FixtureProtocol.ClientWidth, FixtureProtocol.ClientHeight);",
    "StartPosition = FormStartPosition.Manual;",
    "Location = new Point(FixtureProtocol.WindowX, FixtureProtocol.WindowY);",
    "FormBorderStyle = FormBorderStyle.FixedSingle;",
    "ControlBox = false;",
    "Application.SetUnhandledExceptionMode(UnhandledExceptionMode.ThrowException);",
    "DisplayPolicy.RequireProcessDpiAware && !NativeMethods.SetProcessDPIAware()",
    "Application.Run(form);",
    "NativeMethods.GetMessageExtraInfo()",
    "if (message.Msg == FixtureProtocol.ProtocolQueryMessage)",
    "if (message.Msg == FixtureProtocol.StateQueryMessage)",
    "internal const int ClientWidth = 320;",
    "internal const int ClientHeight = 240;",
    "internal const int WindowX = 64;",
    "internal const int WindowY = 64;",
    "internal const int ExpectedInputX = 96;",
    "internal const int ExpectedInputY = 112;",
    "internal const int ProtocolQueryMessage = 0x8051;",
    "internal const int StateQueryMessage = 0x8052;",
    "internal const int ProtocolMagic = 0x434D0101;",
    "Ready = 1",
    "Complete = 2",
    "Fault = 3",
    "internal const int MediumIntegrityRid = 0x2000;",
    "internal const int TokenElevationTypeLimited = 3;",
    "private const int TokenElevation = 20;",
    "result.IsElevated = TokenInteger(token, TokenElevation, false) != 0;",
    "facts.ElevationType == TokenElevationTypeLimited && !facts.IsElevated",
    "!facts.IsAdministrator",
    "facts.ProcessSessionId == facts.ActiveConsoleSessionId",
    "String.Equals(facts.InputDesktopName, \"Default\", StringComparison.Ordinal)",
    "new PaintBlock(0, 0, 80, 240, 192, 32, 32)",
    "new PaintBlock(80, 0, 80, 240, 32, 64, 192)",
    "new PaintBlock(160, 0, 80, 240, 32, 160, 64)",
    "new PaintBlock(240, 0, 80, 240, 16, 24, 32)",
    "new PaintBlock(0, 0, 80, 240, 24, 176, 80)",
    "new PaintBlock(80, 0, 80, 240, 224, 176, 24)",
    "new PaintBlock(160, 0, 80, 240, 128, 48, 192)",
    "new PaintBlock(240, 0, 80, 240, 32, 200, 216)",
    "new PaintBlock(0, 0, 80, 240, 0, 0, 0)",
    "new PaintBlock(80, 0, 80, 240, 224, 0, 224)",
    "new PaintBlock(160, 0, 80, 240, 0, 0, 0)",
    "new PaintBlock(240, 0, 80, 240, 224, 0, 224)",
    "messageExtraInfo < Int32.MinValue || messageExtraInfo > UInt32.MaxValue",
    "uint observedNonce = unchecked((uint)messageExtraInfo);",
    "observedNonce != expectedNonce",
)

REQUIRED_TEST_FRAGMENTS = (
    "FixtureConfiguration.Parse(values, cwd, 1)",
    "wrongCase.Add(\"SYSTEMROOT\", systemRoot);",
    "zeroNonce[FixtureConfiguration.InputNonceName] = \"00000000\";",
    "521a08c9d7ca42cb60f5180a0497c0d5dc2537cd256e715d44937af46f5276d6",
    "facts.IntegrityRid = 0x3000",
    "facts.ElevationType = 1",
    "facts.IsElevated = true",
    "facts.IsAdministrator = true",
    "facts.ProcessSessionId = 4",
    "facts.InputDesktopName = \"default\"",
    "MouseButtons.Right",
    "FixtureProtocol.ExpectedInputX + 1",
    "FixtureProtocol.ExpectedInputX - 1",
    "FixtureProtocol.ExpectedInputY + 1",
    "FixtureProtocol.ExpectedInputY - 1",
    "nonce + 1",
    "0x110203040L",
    "unchecked((int)0x80000000U), 0x80000000U",
    "unchecked((int)0xF0203040U), 0xF0203040U",
    "unchecked((int)0xFFFFFFFFU), 0xFFFFFFFFU",
    "(long)UInt32.MaxValue + 1L, UInt32.MaxValue",
    "(long)Int32.MinValue - 1L, 0x7FFFFFFFU",
    "AssertBlock(fault[3], 240, 224, 0, 224);",
    "foreach (int count in coverage) Assert(count == 1);",
)

FORBIDDEN_PATTERNS = (
    (r"\bSystem\.IO\b", "filesystem namespace"),
    (r"\bMicrosoft\.Win32\b", "registry namespace"),
    (r"\bSystem\.Net\b", "network namespace"),
    (r"\bSystem\.Diagnostics\b", "process namespace"),
    (r"\bCreateProcess(?:A|W)?\b", "process creation"),
    (r"\bShellExecute(?:ExA|ExW|A|W)?\b", "shell execution"),
    (r"\bProcess\.Start\b", "process start"),
    (r"\bFile\s*\.", "file API"),
    (r"\bDirectory\s*\.", "directory API"),
    (r"\bRegistry(?:Key)?\b", "registry API"),
    (r"\bSocket\b|\bWebClient\b|\bHttpClient\b", "network API"),
    (r"\bClipboard\b", "clipboard API"),
    (r"\bConsole\s*\.", "console output"),
    (r"\bMessageBox\b", "message box"),
    (r"\bApplication\.EnableVisualStyles\b", "visual themes"),
    (r"\bFont\b|\bImage\b|\bBitmap\b|\bIcon\b", "font or asset API"),
    (r"\bSendInput\b|\bPostMessage\b", "input injection"),
)

ALLOWED_DLL_IMPORTS = {
    "AllocateAndInitializeSid",
    "CheckTokenMembership",
    "CloseDesktop",
    "CloseHandle",
    "FreeSid",
    "GetCurrentProcess",
    "GetCurrentProcessId",
    "GetMessageExtraInfo",
    "SetProcessDPIAware",
    "GetSidSubAuthority",
    "GetSidSubAuthorityCount",
    "GetTokenInformation",
    "GetUserObjectInformationW",
    "OpenInputDesktop",
    "OpenProcessToken",
    "ProcessIdToSessionId",
    "WTSGetActiveConsoleSessionId",
}


class VerificationError(Exception):
    pass


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def identity(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def require_frozen_identity(raw: bytes, name: str) -> None:
    if identity(raw) != FROZEN_IDENTITIES[name]:
        raise VerificationError(name + " differs from frozen reviewed identity")


def require_no_symlink_components(path: pathlib.Path) -> None:
    if not path.is_absolute():
        raise VerificationError("path is not absolute")
    current = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if stat.S_ISLNK(os.lstat(current).st_mode):
            raise VerificationError("path contains symlink component")


def fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_source(path: pathlib.Path, expected_name: str) -> bytes:
    if path.name != expected_name or not path.is_absolute():
        raise VerificationError("source path or name")
    if os.name != "posix" or not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise VerificationError("held descriptor traversal is unavailable")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    directory_descriptors = [os.open(path.anchor, directory_flags)]
    directory_bindings: list[tuple[int, str, tuple[int, ...]]] = []
    descriptor = -1
    try:
        for component in path.parts[1:-1]:
            parent = directory_descriptors[-1]
            child = os.open(component, directory_flags, dir_fd=parent)
            child_fingerprint = fingerprint(os.fstat(child))
            directory_bindings.append((parent, component, child_fingerprint))
            directory_descriptors.append(child)
        descriptor = os.open(path.name, file_flags, dir_fd=directory_descriptors[-1])
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_SOURCE_BYTES:
            raise VerificationError("source is not a bounded single-link regular file")
        raw = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, MAX_SOURCE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_SOURCE_BYTES:
                raise VerificationError("source exceeds byte limit")
        opened = os.fstat(descriptor)
        named_after = os.stat(path.name, dir_fd=directory_descriptors[-1], follow_symlinks=False)
        for parent, component, expected in directory_bindings:
            if fingerprint(os.stat(component, dir_fd=parent, follow_symlinks=False)) != expected:
                raise VerificationError("source directory changed during read")
    except OSError as error:
        raise VerificationError("held descriptor traversal failed") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)
    if fingerprint(before) != fingerprint(opened) or fingerprint(before) != fingerprint(named_after):
        raise VerificationError("source changed during read")
    return bytes(raw)


def decode_source(raw: bytes, name: str) -> str:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        raise VerificationError(name + " encoding or line endings")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise VerificationError(name + " is not UTF-8") from error
    if "\0" in text:
        raise VerificationError(name + " contains NUL")
    return text


def verify_texts(fixture: str, tests: str) -> None:
    if any(marker in fixture for marker in ("//", "/*", "*/")):
        raise VerificationError("fixture comments are forbidden")
    if any(marker in tests for marker in ("//", "/*", "*/")):
        raise VerificationError("test comments are forbidden")
    if re.search(r"\\(?:u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|x[0-9A-Fa-f]{1,4})", fixture + tests):
        raise VerificationError("C# escaped identifiers are forbidden")
    if re.search(r"\bEntryPoint\s*=", fixture, re.IGNORECASE):
        raise VerificationError("DllImport EntryPoint alias")
    if fixture.count(ALLOWED_ENVIRONMENT_BLOCK) != 1:
        raise VerificationError("environment allowlist structure")
    for fragment in REQUIRED_FIXTURE_FRAGMENTS:
        if fixture.count(fragment) != 1:
            raise VerificationError("fixture fragment: " + fragment)
    for fragment in REQUIRED_TEST_FRAGMENTS:
        if tests.count(fragment) != 1:
            raise VerificationError("test fragment: " + fragment)
    compact_fixture = re.sub(r"\s+", "", fixture)
    for pattern, label in FORBIDDEN_PATTERNS:
        if re.search(pattern, fixture, re.IGNORECASE) or re.search(pattern, compact_fixture, re.IGNORECASE):
            raise VerificationError("forbidden " + label)
    imports = re.findall(r"extern\s+[A-Za-z0-9_.<>\[\]]+\s+([A-Za-z0-9_]+)\s*\(", fixture)
    if len(imports) != len(ALLOWED_DLL_IMPORTS) or set(imports) != ALLOWED_DLL_IMPORTS:
        raise VerificationError("DllImport surface")
    if fixture.count("[DllImport(") != len(ALLOWED_DLL_IMPORTS):
        raise VerificationError("DllImport declaration count")
    dlls = set(re.findall(r'\[DllImport\("([^"]+)"', fixture))
    if dlls != {"advapi32.dll", "kernel32.dll", "user32.dll"}:
        raise VerificationError("DllImport library surface")
    environment_literals = sorted(set(re.findall(
        r'"(CM0102_SYNTHETIC_[A-Z0-9_]+|SystemRoot|TEMP|TMP|WINDIR)"', fixture
    )))
    if environment_literals != PROFILE["environment_names"]:
        raise VerificationError("environment profile")
    if fixture.count("[STAThread]") != 1 or fixture.count("Application.Run(") != 1:
        raise VerificationError("window entrypoint")
    if len(re.findall(r"\bMain\s*\(", fixture)) != 1:
        raise VerificationError("fixture entrypoint count")
    if tests.count("private static int Main()") != 1 or tests.count("return 0;") != 1:
        raise VerificationError("test entrypoint structure")
    if fixture.count(": Form") != 1 or fixture.count("new SyntheticFixtureForm(") != 1:
        raise VerificationError("top-level form count")
    if "Main(string[]" in fixture or "Main(String[]" in fixture:
        raise VerificationError("fixture accepts arguments")


def verify_local_paths(
    repo_path: pathlib.Path,
    fixture_path: pathlib.Path,
    tests_path: pathlib.Path,
    profile_path: pathlib.Path,
) -> tuple[dict[str, object], dict[str, bytes]]:
    expected_directory = repo_path / "tools" / "windows" / "synthetic-launcher-qualification"
    expected_fixture = expected_directory / FIXTURE_NAME
    expected_tests = expected_directory / TEST_NAME
    expected_profile = repo_path / "config" / PROFILE_NAME
    expected_verifier = expected_directory / VERIFIER_NAME
    if pathlib.Path(__file__).absolute() != expected_verifier:
        raise VerificationError("verifier is not the canonical repository file")
    if fixture_path != expected_fixture or tests_path != expected_tests:
        raise VerificationError("sources are not canonical siblings")
    if profile_path != expected_profile:
        raise VerificationError("profile is not canonical repository file")
    for path in (repo_path, expected_directory, expected_fixture, expected_tests, expected_profile,
                 expected_verifier):
        require_no_symlink_components(path)
    fixture_raw = read_source(fixture_path, FIXTURE_NAME)
    tests_raw = read_source(tests_path, TEST_NAME)
    require_frozen_identity(fixture_raw, FIXTURE_NAME)
    require_frozen_identity(tests_raw, TEST_NAME)
    verify_texts(decode_source(fixture_raw, FIXTURE_NAME), decode_source(tests_raw, TEST_NAME))
    result = {
        "fixture": identity(fixture_raw),
        "profile": PROFILE,
        "schema_version": 1,
        "tests": identity(tests_raw),
    }
    profile_raw = read_source(profile_path, PROFILE_NAME)
    if profile_raw != canonical(result):
        raise VerificationError("committed profile differs from verified sources")
    verifier_raw = read_source(expected_verifier, VERIFIER_NAME)
    return result, {
        "config/" + PROFILE_NAME: profile_raw,
        "tools/windows/synthetic-launcher-qualification/" + FIXTURE_NAME: fixture_raw,
        "tools/windows/synthetic-launcher-qualification/" + TEST_NAME: tests_raw,
        "tools/windows/synthetic-launcher-qualification/" + VERIFIER_NAME: verifier_raw,
    }


def git(repo_path: pathlib.Path, arguments: list[str]) -> bytes:
    completed = subprocess.run(
        ["/usr/bin/git", "-C", os.fspath(repo_path), *arguments],
        cwd="/",
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "LANG": "C",
            "LC_ALL": "C",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise VerificationError("Git command failed")
    if len(completed.stdout) > MAX_SOURCE_BYTES:
        raise VerificationError("Git output exceeds byte limit")
    return completed.stdout


def verify_paths(
    repo_path: pathlib.Path,
    source_commit: str,
    fixture_path: pathlib.Path,
    tests_path: pathlib.Path,
    profile_path: pathlib.Path,
) -> dict[str, object]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise VerificationError("source commit is not a full lowercase object ID")
    result, committed_files = verify_local_paths(repo_path, fixture_path, tests_path, profile_path)
    if git(repo_path, ["rev-parse", "--show-toplevel"]) != (os.fspath(repo_path) + "\n").encode("utf-8"):
        raise VerificationError("repository root mismatch")
    if git(repo_path, ["cat-file", "-t", source_commit]) != b"commit\n":
        raise VerificationError("source object is not a commit")
    for relative_path, local_raw in committed_files.items():
        if git(repo_path, ["show", source_commit + ":" + relative_path]) != local_raw:
            raise VerificationError("working file differs from source commit: " + relative_path)
    result["source_commit"] = source_commit
    return result


def expect_rejected(fixture: str, tests: str, label: str) -> None:
    try:
        verify_texts(fixture, tests)
    except VerificationError:
        return
    raise AssertionError("accepted " + label)


def self_test() -> None:
    root = pathlib.Path(__file__).absolute().parent
    repo = root.parents[2]
    fixture_raw = read_source(root / FIXTURE_NAME, FIXTURE_NAME)
    tests_raw = read_source(root / TEST_NAME, TEST_NAME)
    fixture = decode_source(fixture_raw, FIXTURE_NAME)
    tests = decode_source(tests_raw, TEST_NAME)
    require_frozen_identity(fixture_raw, FIXTURE_NAME)
    require_frozen_identity(tests_raw, TEST_NAME)
    verify_texts(fixture, tests)

    mutations = (
        ("internal const int ClientWidth = 320;", "internal const int ClientWidth = 321;", "width"),
        ("internal const int ProtocolQueryMessage = 0x8051;", "internal const int ProtocolQueryMessage = 0x8053;", "message"),
        ("internal const int MediumIntegrityRid = 0x2000;", "internal const int MediumIntegrityRid = 0x3000;", "integrity"),
        ("private const int TokenElevation = 20;", "private const int TokenElevation = 21;", "elevation class"),
        ("DisplayPolicy.RequireProcessDpiAware && !NativeMethods.SetProcessDPIAware()", "false && !NativeMethods.SetProcessDPIAware()", "DPI call"),
        ("new PaintBlock(0, 0, 80, 240, 192, 32, 32)", "new PaintBlock(0, 0, 80, 240, 191, 32, 32)", "paint"),
        ("using System.Text;", "using System.Text;\nusing System.IO;", "filesystem"),
        ("private static int Main()", "private static int Main(string[] args)", "arguments"),
        ("            \"WINDIR\"\n        };", "            \"WINDIR\",\n            \"SECRET\"\n        };", "environment extra"),
    )
    for old, new, label in mutations:
        if fixture.count(old) != 1:
            raise AssertionError("self-test mutation anchor " + label)
        expect_rejected(fixture.replace(old, new), tests, label)

    expect_rejected(fixture + "\n// CreateProcessW\n", tests, "process route")
    expect_rejected(fixture + "\n// ShellExecuteW\n", tests, "shell route")
    expect_rejected(fixture + "\n// Microsoft.Win32\n", tests, "registry route")
    expect_rejected(fixture + "\n// System.Net\n", tests, "network route")
    expect_rejected(fixture + "\n// Clipboard\n", tests, "clipboard route")
    expect_rejected(fixture + "\n// Console.WriteLine\n", tests, "console route")
    expect_rejected(fixture + "\n// Font\n", tests, "font route")
    expect_rejected(fixture + "\n// PostMessage\n", tests, "posted input route")
    expect_rejected(fixture.replace("using System.Diagnostics;", "using System . Diagnostics;")
                    if "using System.Diagnostics;" in fixture else fixture + "\nSystem . Diagnostics . Process . Start();\n",
                    tests, "spaced process route")
    expect_rejected(fixture + "\nSystem . IO . File . OpenRead(\"x\");\n", tests, "spaced filesystem route")
    expect_rejected(fixture + "\nSystem . Net . WebClient client;\n", tests, "spaced network route")
    expect_rejected(fixture + "\nSystem.Diagn\\u006fstics.Pr\\u006fcess.Start();\n", tests,
                    "escaped process route")
    expect_rejected(fixture.replace('[DllImport("kernel32.dll")]',
                                    '[DllImport("kernel32.dll", EntryPoint = "WinExec")]', 1),
                    tests, "DllImport alias")
    expect_rejected(fixture, tests.replace("MouseButtons.Right", "MouseButtons.Left", 1), "input negative")
    expect_rejected(fixture, tests.replace("private static int Main()\n        {",
                                           "private static int Main()\n        {\n            if (DateTime.Now.Ticks >= 0) return 0;", 1),
                    "early test return")

    altered_fixture = fixture_raw.replace(b"internal const int ClientWidth = 320;",
                                          b"internal const int ClientWidth = 321;", 1)
    try:
        require_frozen_identity(altered_fixture, FIXTURE_NAME)
    except VerificationError:
        pass
    else:
        raise AssertionError("accepted regenerated-profile source identity")

    with tempfile.TemporaryDirectory() as directory:
        temporary = pathlib.Path(directory)
        plain = temporary / "plain.cs"
        plain.write_bytes(fixture_raw)
        linked = temporary / FIXTURE_NAME
        os.link(plain, linked)
        try:
            read_source(linked.absolute(), FIXTURE_NAME)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted hardlinked source")
        symlink = temporary / "symlink" / FIXTURE_NAME
        symlink.parent.mkdir()
        symlink.symlink_to(root / FIXTURE_NAME)
        try:
            read_source(symlink.absolute(), FIXTURE_NAME)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted symlinked source")
        real_parent = temporary / "real-parent"
        real_parent.mkdir()
        (real_parent / FIXTURE_NAME).write_bytes(fixture_raw)
        alias_parent = temporary / "alias-parent"
        alias_parent.symlink_to(real_parent, target_is_directory=True)
        try:
            require_no_symlink_components(alias_parent / FIXTURE_NAME)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted symlinked ancestor")
        copied_tree = temporary / "copied-tree-without-git-metadata"
        copied_tree.mkdir()
        try:
            git(copied_tree, ["rev-parse", "--show-toplevel"])
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted copied non-Git tree")
    verify_local_paths(repo, root / FIXTURE_NAME, root / TEST_NAME, repo / "config" / PROFILE_NAME)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("self-test")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--fixture", required=True, type=pathlib.Path)
    verify.add_argument("--tests", required=True, type=pathlib.Path)
    verify.add_argument("--profile", required=True, type=pathlib.Path)
    verify.add_argument("--repo", required=True, type=pathlib.Path)
    verify.add_argument("--source-commit", required=True)
    arguments = parser.parse_args()
    if arguments.command == "self-test":
        self_test()
        print("PASS")
        return 0
    result = verify_paths(
        arguments.repo.absolute(),
        arguments.source_commit,
        arguments.fixture.absolute(),
        arguments.tests.absolute(),
        arguments.profile.absolute(),
    )
    print(canonical(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (VerificationError, OSError, ValueError, json.JSONDecodeError) as error:
        print("FAIL: " + type(error).__name__, file=os.sys.stderr)
        raise SystemExit(1)
