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
import tempfile


MAX_SOURCE_BYTES = 256 * 1024
FIXTURE_NAME = "SyntheticFixture.cs"
TEST_NAME = "SyntheticFixtureTests.cs"
PROFILE_NAME = "synthetic-launcher-fixture-v1.json"

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
    "messageExtraInfo != (long)expectedNonce",
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


def read_source(path: pathlib.Path, expected_name: str) -> bytes:
    if path.name != expected_name or not path.is_absolute():
        raise VerificationError("source path or name")
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_SOURCE_BYTES:
        raise VerificationError("source is not a bounded single-link regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        raw = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, MAX_SOURCE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_SOURCE_BYTES:
                raise VerificationError("source exceeds byte limit")
        opened = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = os.lstat(path)
    fingerprint = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if fingerprint(before) != fingerprint(opened) or fingerprint(before) != fingerprint(after):
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
    if fixture.count(ALLOWED_ENVIRONMENT_BLOCK) != 1:
        raise VerificationError("environment allowlist structure")
    for fragment in REQUIRED_FIXTURE_FRAGMENTS:
        if fixture.count(fragment) != 1:
            raise VerificationError("fixture fragment: " + fragment)
    for fragment in REQUIRED_TEST_FRAGMENTS:
        if tests.count(fragment) != 1:
            raise VerificationError("test fragment: " + fragment)
    for pattern, label in FORBIDDEN_PATTERNS:
        if re.search(pattern, fixture, re.IGNORECASE):
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
    if fixture.count(": Form") != 1 or fixture.count("new SyntheticFixtureForm(") != 1:
        raise VerificationError("top-level form count")
    if "Main(string[]" in fixture or "Main(String[]" in fixture:
        raise VerificationError("fixture accepts arguments")


def verify_paths(
    fixture_path: pathlib.Path, tests_path: pathlib.Path, profile_path: pathlib.Path
) -> dict[str, object]:
    script_directory = pathlib.Path(__file__).resolve(strict=True).parent
    expected_fixture = script_directory / FIXTURE_NAME
    expected_tests = script_directory / TEST_NAME
    expected_profile = script_directory.parents[2] / "config" / PROFILE_NAME
    if fixture_path.resolve(strict=True) != expected_fixture or tests_path.resolve(strict=True) != expected_tests:
        raise VerificationError("sources are not canonical siblings")
    if profile_path.resolve(strict=True) != expected_profile:
        raise VerificationError("profile is not canonical repository file")
    fixture_raw = read_source(fixture_path.absolute(), FIXTURE_NAME)
    tests_raw = read_source(tests_path.absolute(), TEST_NAME)
    verify_texts(decode_source(fixture_raw, FIXTURE_NAME), decode_source(tests_raw, TEST_NAME))
    result = {
        "fixture": identity(fixture_raw),
        "profile": PROFILE,
        "schema_version": 1,
        "tests": identity(tests_raw),
    }
    profile_raw = read_source(profile_path.absolute(), PROFILE_NAME)
    if profile_raw != canonical(result):
        raise VerificationError("committed profile differs from verified sources")
    return result


def expect_rejected(fixture: str, tests: str, label: str) -> None:
    try:
        verify_texts(fixture, tests)
    except VerificationError:
        return
    raise AssertionError("accepted " + label)


def self_test() -> None:
    root = pathlib.Path(__file__).resolve(strict=True).parent
    fixture_raw = read_source(root / FIXTURE_NAME, FIXTURE_NAME)
    tests_raw = read_source(root / TEST_NAME, TEST_NAME)
    fixture = decode_source(fixture_raw, FIXTURE_NAME)
    tests = decode_source(tests_raw, TEST_NAME)
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
    expect_rejected(fixture, tests.replace("MouseButtons.Right", "MouseButtons.Left", 1), "input negative")

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
    verify_paths(
        root / FIXTURE_NAME,
        root / TEST_NAME,
        root.parents[2] / "config" / PROFILE_NAME,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("self-test")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--fixture", required=True, type=pathlib.Path)
    verify.add_argument("--tests", required=True, type=pathlib.Path)
    verify.add_argument("--profile", required=True, type=pathlib.Path)
    arguments = parser.parse_args()
    if arguments.command == "self-test":
        self_test()
        print("PASS")
        return 0
    result = verify_paths(
        arguments.fixture.absolute(), arguments.tests.absolute(), arguments.profile.absolute()
    )
    print(canonical(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (VerificationError, OSError, ValueError, json.JSONDecodeError) as error:
        print("FAIL: " + type(error).__name__, file=os.sys.stderr)
        raise SystemExit(1)
