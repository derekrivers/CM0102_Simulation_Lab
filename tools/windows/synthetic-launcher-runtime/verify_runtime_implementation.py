#!/usr/bin/env python3
"""Fail-closed verifier for the dormant Stage 2 synthetic launcher runtime."""

from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import json
import os
import pathlib
import re
import stat
import struct
import subprocess
import sys


RUNTIME_ROOT = "tools/windows/synthetic-launcher-runtime"
VERIFIER_PATH = RUNTIME_ROOT + "/verify_runtime_implementation.py"
HARNESS_PATH = RUNTIME_ROOT + "/retained_build.py"
QUALIFICATION_HELPER_PATH = "tools/windows/synthetic-launcher-qualification/retained_build.py"
README_PATH = RUNTIME_ROOT + "/README.md"
CONTRACT_PATH = "docs/architecture/SYNTHETIC_LAUNCHER_IMPLEMENTATION_V1.md"
IMPLEMENTATION_PATH = "config/synthetic-launcher-implementation-v1.json"
IMPLEMENTATION_SCHEMA_PATH = "config/synthetic-launcher-implementation-v1.schema.json"
CONFIG_PATHS = (
    IMPLEMENTATION_PATH,
    IMPLEMENTATION_SCHEMA_PATH,
    "config/synthetic-launcher-runtime-private-pinned-fixture-v1.json",
    "config/synthetic-launcher-runtime-private-v1.schema.json",
    "config/synthetic-launcher-runtime-public-pinned-fixture-v1.json",
    "config/synthetic-launcher-runtime-public-v1.schema.json",
    "config/synthetic-launcher-worker-evidence-v1.schema.json",
    "config/synthetic-launcher-report-full-v1.schema.json",
)
SHARED_FILES = ("RuntimeCanonicalData.cs", "RuntimeGate.cs")
PURE_FILES = (*SHARED_FILES, "RuntimeGateTests.cs")
IMAGE_SPECS = {
    "SyntheticLauncherSupervisor.exe": (
        "SupervisorEntry.cs", "SupervisorBootstrapNative.cs", "SupervisorLiveNative.cs"),
    "SyntheticLauncherController.exe": (
        "ControllerEntry.cs", "ControllerBootstrapNative.cs", "ControllerLiveNative.cs"),
    "SyntheticLauncherLockedPreflight.exe": (
        "LockedPreflightEntry.cs", "LockedPreflightBootstrapNative.cs",
        "LockedPreflightLiveNative.cs"),
    "SyntheticLauncherTimeoutFixture.exe": (
        "TimeoutFixtureEntry.cs", "TimeoutFixtureBootstrapNative.cs",
        "TimeoutFixtureLiveNative.cs"),
    "SyntheticLauncherTimeoutChild.exe": (
        "TimeoutChildEntry.cs", "TimeoutChildBootstrapNative.cs", "TimeoutChildLiveNative.cs"),
}
PRODUCTION_FILES = tuple(name for names in IMAGE_SPECS.values() for name in names)
EXPECTED_RUNTIME_FILES = tuple(sorted((*PURE_FILES, *PRODUCTION_FILES,
    "README.md", "retained_build.py", "verify_runtime_implementation.py")))
MAX_BYTES = 1024 * 1024
GIT = pathlib.Path("/usr/bin/git")
EXPECTED_FIXED_NAMES = {
    "build_manifest": "SyntheticLauncherBuildManifest.v1.json",
    "complete_bmp": "SyntheticLauncherComplete.v1.bmp",
    "controller": "SyntheticLauncherController.exe",
    "locked_preflight": "SyntheticLauncherLockedPreflight.exe",
    "private_configuration": "SyntheticLauncherController.private.v1.json",
    "public_configuration": "SyntheticLauncherController.public.v1.json",
    "ready_bmp": "SyntheticLauncherReady.v1.bmp",
    "report": "SyntheticLauncherReport.v1.json",
    "supervisor": "SyntheticLauncherSupervisor.exe",
    "timeout_child": "SyntheticLauncherTimeoutChild.exe",
    "timeout_root": "SyntheticLauncherTimeoutFixture.exe",
    "ui_fixture": "SyntheticLauncherFixture.exe",
    "worker_evidence": "SyntheticLauncherWorkerEvidence.v1.json",
}
APPROVED_ARTIFACTS = {
    "complete_bmp": {
        "byte_count": 230454,
        "sha256": "5dac08fba06a53bb0a480fe388907e78147b5c0d042fee53eea2ff81b4ee8bc6",
    },
    "ready_bmp": {
        "byte_count": 230454,
        "sha256": "4f471fd3bc87f53fef9d7f200eaccb0ebe69a0240a9cf09f79bc2bfec3c51f19",
    },
}
CHECK_IDS = {
    "binding-exact", "capture-complete-exact", "capture-ready-exact", "cleanup-exact",
    "environment-exact", "guard-stability", "input-exact", "job-containment",
    "original-not-run", "preflight-safe", "privacy-safe", "registry-denied",
    "resume-once", "supervisor-containment", "token-relationship", "window-exact",
}
REPORT_PERMITTED_DIFFERENCE_PATHS = (
    "/bindings/attempt_root_object_id_sha256",
    "/bindings/private_configuration/byte_count",
    "/bindings/private_configuration/sha256",
    "/observations/environment/nonce_sha256",
    "/run/attempt_id_sha256",
    "/run/attempt_ordinal",
    "/run/elapsed_ms",
    "/run/observed_at_utc",
)

# Filled from an independently reviewed exact source set before merge.  The
# implementation config/schema and verifier are validated without a digest
# edge so the trust graph remains acyclic; the workflow seals this verifier.
FROZEN_IDENTITIES: dict[str, tuple[int, str]] = {
    "config/synthetic-launcher-report-full-v1.schema.json": (12295,
        "9509730c70e3b8c74f552e7d568593a9b7fcb88427262fbcbde30843e93b64ed"),
    "config/synthetic-launcher-runtime-private-pinned-fixture-v1.json": (1337,
        "5850c8ade2e6e9c743df6b34ba2844cbdc8a29b9a454496e84625cfad4d1d493"),
    "config/synthetic-launcher-runtime-private-v1.schema.json": (2447,
        "17ca3599f791aebb1f88e37cdf36af0b94a8b744850c66bf88c526bd42b0e3e0"),
    "config/synthetic-launcher-runtime-public-pinned-fixture-v1.json": (2035,
        "697a042604498911ce2f349757ef1f9d6086539dc293298e6a24e586376c9670"),
    "config/synthetic-launcher-runtime-public-v1.schema.json": (2426,
        "9e409e76499ad03f1bd211298b3f64a8f0615c6480eeca4e5ee52f5c84762f6d"),
    "config/synthetic-launcher-worker-evidence-v1.schema.json": (5115,
        "48a86874dd7d36097dae17aa239ceee8788e02d502fdefb805678eb877553299"),
    "docs/architecture/SYNTHETIC_LAUNCHER_IMPLEMENTATION_V1.md": (19737,
        "6269a4390bdf64cf9c36043036f77a3d91710ac35949bbc5526264caf831185a"),
    QUALIFICATION_HELPER_PATH: (81360,
        "f097b28eea2489f1486c0b0fdf5a3bc3578911367593528263ac8320bcc162e4"),
    RUNTIME_ROOT + "/ControllerBootstrapNative.cs": (30201,
        "a8c63a24c0f89414d5e0d8250f39b5f3249da5453ee53f8f25a7466cf2b254a6"),
    RUNTIME_ROOT + "/ControllerEntry.cs": (4471,
        "2b043ebeca5d4b8823757f30c6f9fb6fa44367c814ba701be589a8ac2ece675a"),
    RUNTIME_ROOT + "/ControllerLiveNative.cs": (125813,
        "abebd005d885855bd94a760eb3dbd494a3f54fd74e216a3c8ba40e3834fcd053"),
    RUNTIME_ROOT + "/LockedPreflightBootstrapNative.cs": (30301,
        "126e9e8f467681b06eecbe56ec42ed960a5693bc01b66e2363c3b7c8a7a718c7"),
    RUNTIME_ROOT + "/LockedPreflightEntry.cs": (4689,
        "d093a9bcf33a858a7427d92972bf1bc1f93e45987ccac4828d5c7632d3e0b4c1"),
    RUNTIME_ROOT + "/LockedPreflightLiveNative.cs": (31653,
        "61cf3e70a621872e148a8a6af436d8f52cd1f4f236fc849e613a38662e85f662"),
    RUNTIME_ROOT + "/README.md": (5146,
        "320da6620a2a53cb12bf666364a4b78b9ccb0560e9992c92d4f265f6beb68427"),
    RUNTIME_ROOT + "/RuntimeCanonicalData.cs": (55581,
        "59f7ea8bb1a596671c6b46fe88a02cd450a97d07637751a65c6a14d7cfae1561"),
    RUNTIME_ROOT + "/RuntimeGate.cs": (12681,
        "48b76d9002855bf60452ed00a3366582a0d8d02c8d0b72347a978a5b0faa3985"),
    RUNTIME_ROOT + "/RuntimeGateTests.cs": (60649,
        "85058d63859f3f639064f92ac42a409d381bf21552e97886657a4df1e7e01e52"),
    RUNTIME_ROOT + "/SupervisorBootstrapNative.cs": (30201,
        "dd9efa8e3e17f8b760ca7253b62870f9a76c98db715098b7dd1e9035b39fb60d"),
    RUNTIME_ROOT + "/SupervisorEntry.cs": (4419,
        "a6d66688d653523010f8660f789e4a8632526bfe09282de4a3b7a998b428e7c6"),
    RUNTIME_ROOT + "/SupervisorLiveNative.cs": (77135,
        "9070b8df8113bd1c9535e9ff6e896886253387f59db49610f1fcd712f13502c3"),
    RUNTIME_ROOT + "/TimeoutChildBootstrapNative.cs": (29083,
        "7001aa567556a7784210ef3657c461de8a72611e5de199cfb774189c04c05ad1"),
    RUNTIME_ROOT + "/TimeoutChildEntry.cs": (4615,
        "804a58cb30df30c5a1aff5ff51edf7e8cf28aca9d31d38c98a8123f9b048723f"),
    RUNTIME_ROOT + "/TimeoutChildLiveNative.cs": (2639,
        "6ee874a22cc1e346234e26c31f14d4d7f85fcfcd866a3cd67e2b9312298106d4"),
    RUNTIME_ROOT + "/TimeoutFixtureBootstrapNative.cs": (30281,
        "def39fafc7953138670f175aaa290e085f73eb36a6554d7f53a0a925acaebc8a"),
    RUNTIME_ROOT + "/TimeoutFixtureEntry.cs": (4629,
        "dee2f37a7266e824010d4e028196ed928970570384d9ae3037ef154f5c690b3a"),
    RUNTIME_ROOT + "/TimeoutFixtureLiveNative.cs": (17943,
        "d785c9cd9b1ad3d61cfd79e9979193493ef765714ef7f89937232e9191e6fe19"),
    RUNTIME_ROOT + "/retained_build.py": (67082,
        "3988f14ebaa0d3b5eb4ef54609d1dd1d4e1a7cd4c8abc5d0eca11563897cbbbc"),
}


class VerificationError(Exception):
    pass


def identity(raw: bytes) -> tuple[int, str]:
    return len(raw), hashlib.sha256(raw).hexdigest()


def identity_object(raw: bytes) -> dict[str, object]:
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")) + "\n").encode("ascii")


def projected_report(value: object) -> bytes:
    projected = json.loads(json.dumps(value, ensure_ascii=True, separators=(",", ":")))
    for pointer in REPORT_PERMITTED_DIFFERENCE_PATHS:
        current = projected
        parts = pointer[1:].split("/")
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                raise VerificationError("report projection path")
            current = current[part]
        if not isinstance(current, dict) or parts[-1] not in current:
            raise VerificationError("report projection leaf")
        del current[parts[-1]]
    return canonical(projected)


def derived_canonical_bmp(ready: bool) -> bytes:
    colors = ((192, 32, 32), (32, 64, 192), (32, 160, 64), (16, 24, 32)) if ready \
        else ((24, 176, 80), (224, 176, 24), (128, 48, 192), (32, 200, 216))
    value = bytearray(230454)
    value[0:2] = b"BM"
    struct.pack_into("<I", value, 2, 230454)
    struct.pack_into("<I", value, 10, 54)
    struct.pack_into("<I", value, 14, 40)
    struct.pack_into("<i", value, 18, 320)
    struct.pack_into("<i", value, 22, 240)
    struct.pack_into("<H", value, 26, 1)
    struct.pack_into("<H", value, 28, 24)
    struct.pack_into("<I", value, 34, 320 * 240 * 3)
    output = 54
    for _y in range(239, -1, -1):
        for x in range(320):
            red, green, blue = colors[x // 80]
            value[output:output + 3] = bytes((blue, green, red))
            output += 3
    if output != len(value):
        raise VerificationError("canonical BMP derivation size")
    return bytes(value)


def require_path_components(path: pathlib.Path) -> None:
    if not path.is_absolute():
        raise VerificationError("path is not absolute")
    current = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if stat.S_ISLNK(os.lstat(current).st_mode):
            raise VerificationError("symbolic path component")


def read_bound(path: pathlib.Path) -> bytes:
    require_path_components(path)
    before = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or \
            before.st_size <= 0 or before.st_size > MAX_BYTES:
        raise VerificationError("invalid bound file " + os.fspath(path))
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        raw = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, MAX_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                raise VerificationError("bound file exceeds limit")
        after = os.stat(path, follow_symlinks=False)
    finally:
        os.close(descriptor)
    fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if fields(before) != fields(opened) or fields(before) != fields(after) or \
            len(raw) != before.st_size:
        raise VerificationError("bound file changed during read")
    return bytes(raw)


def decode_ascii(raw: bytes, label: str) -> str:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or b"\0" in raw or \
            not raw.endswith(b"\n"):
        raise VerificationError(label + " encoding")
    try:
        return raw.decode("ascii", "strict")
    except UnicodeDecodeError as error:
        raise VerificationError(label + " non-ASCII") from error


def parse_canonical_json(raw: bytes, label: str) -> object:
    try:
        value = json.loads(raw.decode("ascii", "strict"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            object_pairs_hook=lambda pairs: duplicate_free(pairs, label))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(label + " JSON") from error
    if canonical(value) != raw:
        raise VerificationError(label + " is not canonical JSON")
    return value


def duplicate_free(pairs: list[tuple[str, object]], label: str) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(label + " duplicate key")
        value[key] = item
    return value


def run_git(repo: pathlib.Path, arguments: list[str], maximum: int = MAX_BYTES) -> bytes:
    environment = {
        "PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": "/dev/null", "GIT_CONFIG_KEY_1": "extensions.objectFormat",
        "GIT_CONFIG_VALUE_1": "sha1",
    }
    completed = subprocess.run([os.fspath(GIT), "--no-replace-objects",
        "-c", "protocol.file.allow=never", "-c", "core.fsmonitor=false", *arguments],
        cwd=repo, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=20, check=False)
    if completed.returncode != 0 or completed.stderr or len(completed.stdout) > maximum:
        raise VerificationError("Git command failed")
    return completed.stdout


def validate_commit(repo: pathlib.Path, commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None or \
            run_git(repo, ["cat-file", "-t", commit]) != b"commit\n":
        raise VerificationError("invalid source commit")
    resolved = run_git(repo, ["rev-parse", "--verify", commit + "^{commit}"]).decode().strip()
    head = run_git(repo, ["rev-parse", "--verify", "HEAD^{commit}"]).decode().strip()
    if resolved != commit or head != commit:
        raise VerificationError("source commit is not exact HEAD")


def validate_execution_source(repo: pathlib.Path, raw: bytes) -> None:
    if not __file__.startswith("/proc/self/fd/"):
        raise VerificationError("verifier execution source")
    try:
        descriptor = os.open(__file__, os.O_RDONLY | os.O_CLOEXEC)
        target = os.readlink("/proc/self/fd/" + str(descriptor))
        observed = os.read(descriptor, MAX_BYTES + 1)
        seals = fcntl.fcntl(descriptor, fcntl.F_GET_SEALS)
    except OSError as error:
        raise VerificationError("verifier sealed source") from error
    finally:
        try:
            os.close(descriptor)
        except (OSError, UnboundLocalError):
            pass
    required = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
    if not target.startswith("/memfd:runtime-implementation-verifier") or \
            observed != raw or seals & required != required or \
            raw != run_git(repo, ["show", "HEAD:" + VERIFIER_PATH]):
        raise VerificationError("verifier execution source")


def strip_literals(source: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(source):
        if source.startswith("//", index):
            end = source.find("\n", index)
            if end < 0:
                end = len(source)
            result.append(" " * (end - index))
            index = end
        elif source.startswith("/*", index):
            end = source.find("*/", index + 2)
            if end < 0:
                raise VerificationError("unterminated comment")
            end += 2
            result.append(" " * (end - index))
            index = end
        elif source[index] == '"':
            start = index
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise VerificationError("unterminated string")
            result.append('""' + " " * max(0, index - start - 2))
        elif source[index] == "'":
            start = index
            index += 1
            if index < len(source) and source[index] == "\\":
                index += 2
            else:
                index += 1
            if index >= len(source) or source[index] != "'":
                raise VerificationError("invalid character literal")
            index += 1
            result.append("'x'" + " " * max(0, index - start - 3))
        else:
            result.append(source[index])
            index += 1
    return "".join(result)


def require_ordered(source: str, markers: tuple[str, ...], label: str,
        exact_count: bool = True) -> None:
    position = -1
    for marker in markers:
        if (exact_count and source.count(marker) != 1) or \
                (not exact_count and marker not in source):
            raise VerificationError(label + " marker " + marker)
        next_position = source.find(marker, position + 1)
        if next_position <= position:
            raise VerificationError(label + " ordering " + marker)
        position = next_position


def verify_pure_sources(sources: dict[str, str]) -> None:
    forbidden = (
        "DllImport", "LibraryImport", "System.IO", "Microsoft.Win32", "System.Diagnostics",
        "System.Reflection", "System.Environment", "System.Net", "System.Windows",
        "System.Security", "System.Runtime.InteropServices", "Process.Start", "File.",
        "Directory.", "Registry.", "Socket", "Http", "WebRequest", "dynamic ", "unsafe",
        "delegate", "=>", "async", "await", "Task", "Console.Read", "Console.Open",
        "Type.GetType", ".GetType()", ".GetMethod", ".GetMethods", ".Invoke(",
        "Activator", "MethodInfo", "PropertyInfo", "FieldInfo",
    )
    for name in PURE_FILES:
        source = sources[name]
        code = strip_literals(source)
        for marker in forbidden:
            if marker in code:
                raise VerificationError(name + " pure authority: " + marker)
        if re.search(r"(?m)^\s*#", code) or re.search(
                r"\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{1,4})", source):
            raise VerificationError(name + " disguised source")
    if sources["RuntimeGateTests.cs"].count(
            'Console.WriteLine("PASS runtime-gate-v1");') != 1:
        raise VerificationError("gate-test result")
    required = (
        "BuildUnpinnedRefusal", "PinnedRuntimeLease", "RuntimeRefusalUse", "RuntimeLeaseUse",
        "Interlocked.CompareExchange", "TryConsumeRefusal", "TryConsumeLease",
        "BuildUnpinned", "BuildPinned", "RuntimeConsumerBinding", "RuntimeObjectFacts",
        "RuntimeScenarioStage", "RuntimeScenarioRole", "RuntimeScenarioStepResult",
        "IRuntimeScenarioPort", "RuntimeScenarioPlan", "RuntimeScenarioExecutionResult",
        "RuntimeScenarioEngine", "RoleMatchesPort", "CleanupAttempted", "CleanupSucceeded",
        "RuntimeDeadlineMath", "TryCreateDeadline", "RemainingMilliseconds", "CanProbe",
    )
    combined = sources["RuntimeCanonicalData.cs"] + sources["RuntimeGate.cs"]
    for marker in required:
        if marker not in combined:
            raise VerificationError("gate contract missing " + marker)
    canonical_source = sources["RuntimeCanonicalData.cs"]
    bmp_constants = (
        'internal const string ReadyBmpName = "SyntheticLauncherReady.v1.bmp";',
        'internal const string CompleteBmpName = "SyntheticLauncherComplete.v1.bmp";',
        "internal const int CanonicalBmpByteCount = 230454;",
        '"4f471fd3bc87f53fef9d7f200eaccb0ebe69a0240a9cf09f79bc2bfec3c51f19";',
        '"5dac08fba06a53bb0a480fe388907e78147b5c0d042fee53eea2ff81b4ee8bc6";',
    )
    for marker in bmp_constants:
        if canonical_source.count(marker) != 1:
            raise VerificationError("canonical BMP constant " + marker)
    require_ordered(canonical_source, (
        "byte[] value = new byte[CanonicalBmpByteCount];",
        "value[0] = (byte)'B'; value[1] = (byte)'M';",
        "PutUInt32(value, 2, CanonicalBmpByteCount);",
        "PutUInt32(value, 10, 54);",
        "PutUInt32(value, 14, 40);",
        "PutUInt32(value, 18, 320);",
        "PutUInt32(value, 22, 240);",
        "PutUInt16(value, 26, 1);",
        "PutUInt16(value, 28, 24);",
        "PutUInt32(value, 34, 320 * 240 * 3);",
        "for (int y = 239; y >= 0; y--)",
        "for (int x = 0; x < 320; x++)",
        "value[output++] = topDownBgra[input++];",
        "input++;",
        "if (output != value.Length)",
        "bmp = value;",
    ), "canonical BMP encoder", False)
    for marker in (
            "{ 192, 32, 32 }, { 32, 64, 192 }, { 32, 160, 64 }, { 16, 24, 32 }",
            "{ 24, 176, 80 }, { 224, 176, 24 }, { 128, 48, 192 }, { 32, 200, 216 }",
            "int band = x / 80;", "bgra[offset] = (byte)colors[band, 2];",
            "bgra[offset + 1] = (byte)colors[band, 1];",
            "bgra[offset + 2] = (byte)colors[band, 0];",
            "internal static string Sha256Hex(byte[] value)",
            "uint[] constants = {", "uint[] state = { 0x6a09e667U",
            "for (int block = 0; block < padded.Length; block += 64)",
            "return String.Equals(Sha256Hex(value), expected, StringComparison.Ordinal);"):
        if canonical_source.count(marker) != 1:
            raise VerificationError("canonical BMP derivation " + marker)
    typed_ports = (
        "IRuntimeSupervisorScenarioPort", "IRuntimeControllerScenarioPort",
        "IRuntimeLockedPreflightScenarioPort", "IRuntimeTimeoutRootScenarioPort",
        "IRuntimeTimeoutChildScenarioPort",
    )
    canonical = canonical_source
    for port in typed_ports:
        declaration = "internal interface " + port + " : IRuntimeScenarioPort"
        if canonical.count(declaration) != 1:
            raise VerificationError("typed scenario port " + port)
        if canonical.count("port is " + port) != 1:
            raise VerificationError("typed scenario port dispatch " + port)
    engine_markers = (
        "for (int index = 0; index < plan.StageCount; index++)",
        "RuntimeScenarioStage stage = plan.StageAt(index);",
        "step = port.Execute(stage);",
        "RuntimeScenarioStepResult cleanup = port.Cleanup();",
    )
    position = -1
    for marker in engine_markers:
        if canonical.count(marker) != 1 or canonical.index(marker) <= position:
            raise VerificationError("scenario engine control " + marker)
        position = canonical.index(marker)
    deadline_declarations = (
        "internal static class RuntimeDeadlineMath",
        "internal static bool TryCreateDeadline(",
        "internal static uint RemainingMilliseconds(",
        "internal static bool CanProbe(",
    )
    for marker in deadline_declarations:
        if canonical.count(marker) != 1:
            raise VerificationError("shared deadline math " + marker)
    for marker in ("now >= deadline", "deadline - now",
            "return RemainingMilliseconds(start, deadline, now, frequency) != 0;"):
        if canonical.count(marker) != 1:
            raise VerificationError("shared deadline boundary " + marker)
    require_ordered(canonical, (
        "RuntimeScenarioStage.Environment,",
        "RuntimeScenarioStage.TargetCreate,",
        "RuntimeScenarioStage.InnerJobConfigured,",
        "RuntimeScenarioStage.InnerAssign,",
        "RuntimeScenarioStage.InnerMembership,",
        "RuntimeScenarioStage.TargetResume",
    ), "controller create/job stage order", False)
    require_ordered(canonical, (
        "RuntimeScenarioStage.SupervisorCreate,",
        "RuntimeScenarioStage.SupervisorAssign,",
        "RuntimeScenarioStage.SupervisorMembership,",
        "RuntimeScenarioStage.WorkerTopology,",
        "RuntimeScenarioStage.SupervisorResume,",
    ), "supervisor create/job stage order", False)
    legacy = (
        "RuntimeScenarioFaultModel", "RuntimeScenarioSimulationResult",
        "RuntimeSafetyMutation", "TraverseMutation", "MutationStage",
    )
    for marker in legacy:
        if marker in combined or marker in sources["RuntimeGateTests.cs"]:
            raise VerificationError("legacy scenario model " + marker)
    tests = sources["RuntimeGateTests.cs"]
    if tests.count("private static void DeadlineMathCases()") != 1 or \
            tests.count("DeadlineMathCases();") != 1 or \
            tests.count("RuntimeDeadlineMath.CanProbe(") != 7 or \
            "deadline - 1" not in tests or "Int64.MaxValue" not in tests:
        raise VerificationError("shared deadline math negative controls")
    if tests.count("private static void CanonicalBmpCases()") != 1 or \
            tests.count("CanonicalBmpCases();") != 1 or \
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" \
                not in tests or \
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" \
                not in tests or \
            "Assert(ignored[54] == 4 && ignored[55] == 5 && ignored[56] == 6);" \
                not in tests or \
            "ready[54] ^= 1;" not in tests:
        raise VerificationError("canonical BMP/hash negative controls")
    for marker in ("UnpinnedRefusalCases", "PinnedLeaseCases", "BindingFailureCases",
            "IdentityImmutabilityCase", "RouteMappingAndStageCases", "ScenarioEngineCases",
            "AssertEngineForEveryStage", "ScriptedSupervisorPort",
            "ScriptedControllerPort", "ScriptedLockedPort",
            "ScriptedTimeoutRootPort", "ScriptedTimeoutChildPort",
            "TimeoutRootChildTopology", "SupervisorPostTopology", "RebindInputs",
            "GuardsStable", "RegistryStable", "evaluation-replay", "scenario-drift",
            "profile-drift", "ConcurrentConsumptionCases", "ManualResetEvent",
            "DeadlineMathCases", "PASS runtime-gate-v1"):
        if marker not in tests and marker not in combined:
            raise VerificationError("gate negative control " + marker)


def verify_production_sources(sources: dict[str, str]) -> None:
    all_production = "\n".join(sources[name] for name in PRODUCTION_FILES)
    forbidden = (
        "Process.Start", "ProcessStartInfo", "ShellExecute", "WinExec", "system(",
        "CreateProcessWithToken", "CreateProcessWithLogon", "CommandLine", "GetCommandLine",
        "Environment.GetEnvironment", "Environment.SetEnvironment", "Assembly.Load",
        "Activator.CreateInstance", "Microsoft.Win32", "System.Net", "Socket", "WebRequest",
    )
    code = strip_literals(all_production)
    for marker in forbidden:
        if marker in code:
            raise VerificationError("production alternate authority " + marker)
    if re.search(r"(?m)^\s*#", code) or "unsafe" in code or "dynamic " in code or \
            re.search(r"\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{1,4})",
                all_production):
        raise VerificationError("production unsupported source form")
    legacy_orchestration = (
        "RunFixedWorker", "RunFixedScenario", "RunUiRoute", "RunTimeoutRoute",
        "ObserveLockedDesktopAndPublish", "CreateFixedChildAndWait", "WaitOnly",
        "RuntimeScenarioFaultModel", "RuntimeScenarioSimulationResult",
        "RuntimeSafetyMutation", "TraverseMutation", "MutationStage",
    )
    for marker in legacy_orchestration:
        if re.search(r"\b" + re.escape(marker) + r"\b", code):
            raise VerificationError("legacy production orchestration " + marker)
    entry_integrations = {
        "SupervisorEntry.cs": ("Supervisor", "IRuntimeSupervisorScenarioPort",
            "SupervisorLiveNative"),
        "ControllerEntry.cs": ("Controller", "IRuntimeControllerScenarioPort",
            "ControllerLiveNative"),
        "LockedPreflightEntry.cs": ("LockedPreflight",
            "IRuntimeLockedPreflightScenarioPort", "LockedPreflightLiveNative"),
        "TimeoutFixtureEntry.cs": ("TimeoutRoot", "IRuntimeTimeoutRootScenarioPort",
            "TimeoutFixtureLiveNative"),
        "TimeoutChildEntry.cs": ("TimeoutChild", "IRuntimeTimeoutChildScenarioPort",
            "TimeoutChildLiveNative"),
    }
    for output, names in IMAGE_SPECS.items():
        entry, bootstrap, live = names
        entry_source = sources[entry]
        if len(re.findall(r"\bMain\s*\(", entry_source)) != 1 or \
                re.search(r"private\s+static\s+int\s+Main\s*\(\s*\)", entry_source) is None or \
                re.search(r"\bMain\s*\([^)]*\bstring\b", entry_source, re.I):
            raise VerificationError(entry + " parameterless entrypoint")
        if "DllImport" in entry_source:
            raise VerificationError(entry + " native declarations outside adapter")
        if "BootstrapNative" not in sources[bootstrap] or "LiveNative" not in sources[live]:
            raise VerificationError(output + " adapter ownership")
        for other_output, other_names in IMAGE_SPECS.items():
            if other_output != output and any(name in entry_source for name in other_names):
                raise VerificationError(entry + " cross-image source reference")
        role, port, adapter = entry_integrations[entry]
        plan_pattern = (r"RuntimeScenarioPlan\.TryCreate\(lease\.ScenarioId,\s*" +
            r"RuntimeScenarioRole\." + role + r",\s*out plan\)")
        typed_port_pattern = (r"\b" + port + r"\s+port\s*=\s*new\s+" + adapter +
            r"\s*\(")
        if len(re.findall(plan_pattern, entry_source)) != 1 or \
                len(re.findall(typed_port_pattern, entry_source)) != 1 or \
                entry_source.count("RuntimeScenarioEngine.Run(plan, port).ExitCode") != 1:
            raise VerificationError(entry + " shared scenario engine integration")
        ordered = ("TryConsumeLease(decision.Lease, binding, out lease)",
            "RuntimeScenarioPlan.TryCreate(lease.ScenarioId",
            port + " port = new " + adapter + "(",
            "RuntimeScenarioEngine.Run(plan, port).ExitCode")
        position = -1
        for marker in ordered:
            next_position = entry_source.find(marker)
            if next_position <= position:
                raise VerificationError(entry + " scenario lease/engine ordering")
            position = next_position
        if ".Execute(" in strip_literals(entry_source) or ".Cleanup(" in strip_literals(
                entry_source):
            raise VerificationError(entry + " scenario engine bypass")
        live_source = sources[live]
        declaration = "internal sealed class " + adapter + " : " + port
        if live_source.count(declaration) != 1 or \
                "public RuntimeScenarioRole Role" not in live_source or \
                "public RuntimeScenarioStepResult Execute(RuntimeScenarioStage stage)" not in \
                    live_source or \
                "public RuntimeScenarioStepResult Cleanup()" not in live_source:
            raise VerificationError(live + " typed scenario port implementation")
    required_literals = (
        "SyntheticLauncherSupervisor.exe", "SyntheticLauncherController.exe",
        "SyntheticLauncherLockedPreflight.exe", "SyntheticLauncherTimeoutFixture.exe",
        "SyntheticLauncherTimeoutChild.exe", "SyntheticLauncherFixture.exe",
        "SyntheticLauncherBuildManifest.v1.json",
        "SyntheticLauncherController.public.v1.json",
        "SyntheticLauncherController.private.v1.json",
        "SyntheticLauncherWorkerEvidence.v1.json", "SyntheticLauncherReport.v1.json",
        "cm0102.exe", "CreateProcessW", "CreateProcessAsUserW", "CREATE_SUSPENDED",
    )
    combined = sources["RuntimeCanonicalData.cs"] + all_production
    for literal in required_literals:
        if literal not in combined:
            raise VerificationError("production contract literal " + literal)
    if all_production.count("CreateProcessAsUserW") < 2 or \
            all_production.count("CreateProcessW") < 4:
        raise VerificationError("fixed creation surface")
    source_requirements = {
        "SupervisorLiveNative.cs": ("ExactAttemptInventory", "ExactWorkerTopology",
            "ExactJobProcessId", "RemainingMilliseconds", "TerminateProcess",
            "FileIdentityAbsent", "RebindParent",
            "HasNoNamedDataStreams(snapshot.ParentHandle)",
            "private IntPtr launchBinding", "ExactBoundObject(launchBinding",
            "CloseHandle(launchBinding)"),
        "ControllerLiveNative.cs": ("TryAcquireLimitedExplorerToken",
            "TryAdministratorEnabled", "ExactTokenRelationship", "CaptureGuards",
            "ExactJobProcessIds", "ExactSessionDesktop", "ExactPixelPlan",
            "TerminateProcess", "RebindParent",
            "HasNoNamedDataStreams(snapshot.ParentHandle)",
            "(directory && !HasNoNamedDataStreams(handle))",
            "(!directory && !OnlyUnnamedStream(handle))",
            "private IntPtr launchBinding", "ExactBoundObject(launchBinding",
            "CloseHandle(launchBinding)",
            "if (guardBefore != null && !guardsVerified)",
            "CaptureGuards(out observed) && guardBefore.Exact(observed)",
            "if (inserted == (uint)input.Length)",
            "inputReleaseArmed = !released", "if (inputReleaseArmed)",
            "SendInput(1, release", "move.Mouse.Flags = 0x8000 | 0x0001;",
            "down.Mouse.Flags = 0x8000 | 0x0002;",
            "up.Mouse.Flags = 0x8000 | 0x0004;",
            "bitmapSelected = false;"),
        "LockedPreflightLiveNative.cs": ("TryObserve",
            "RelativeNameAbsent", "ExactCreatedObject", "RebindParent",
            "HasNoNamedDataStreams(snapshot.ParentHandle)"),
        "TimeoutFixtureLiveNative.cs": ("RebindChild", "RebindParent",
            "SyntheticLauncherTimeoutChild.exe",
            "HasNoNamedDataStreams(snapshot.ParentHandle)",
            "private IntPtr launchBinding", "RebindChild(out launchBinding)",
            "CloseHandle(launchBinding)"),
        "SupervisorBootstrapNative.cs": ("HasNoNamedDataStreams", "ExactProtectedAcl",
            "((control & 0x1000) != 0) != directory"),
        "ControllerBootstrapNative.cs": ("HasNoNamedDataStreams", "ExactProtectedAcl",
            "((control & 0x1000) != 0) != directory"),
        "LockedPreflightBootstrapNative.cs": ("HasNoNamedDataStreams", "ExactProtectedAcl",
            "((control & 0x1000) != 0) != directory"),
        "TimeoutFixtureBootstrapNative.cs": ("HasNoNamedDataStreams", "ExactProtectedAcl",
            "((control & 0x1000) != 0) != directory"),
        "TimeoutChildBootstrapNative.cs": ("HasNoNamedDataStreams", "ExactProtectedAcl",
            "((control & 0x1000) != 0) != directory"),
    }
    for name, markers in source_requirements.items():
        for marker in markers:
            if marker not in sources[name]:
                raise VerificationError(name + " missing production control " + marker)
    exact_control_counts = {
        "SupervisorLiveNative.cs": {
            "HasNoNamedDataStreams(snapshot.ParentHandle)": 1,
            "private IntPtr launchBinding": 1,
            "CloseHandle(launchBinding)": 1,
            "RuntimeDeadlineMath.CanProbe(": 2,
        },
        "ControllerLiveNative.cs": {
            "HasNoNamedDataStreams(snapshot.ParentHandle)": 1,
            "(directory && !HasNoNamedDataStreams(handle))": 1,
            "private IntPtr launchBinding": 1,
            "CloseHandle(launchBinding)": 1,
            "if (guardBefore != null && !guardsVerified)": 1,
            "CaptureGuards(out observed) && guardBefore.Exact(observed)": 1,
            "if (inserted == (uint)input.Length)": 1,
            "inputReleaseArmed = !released": 1,
            "if (inputReleaseArmed)": 1,
            "SendInput(1, release": 2,
            "RuntimeDeadlineMath.CanProbe(": 3,
        },
        "LockedPreflightLiveNative.cs": {
            "HasNoNamedDataStreams(snapshot.ParentHandle)": 1,
        },
        "TimeoutFixtureLiveNative.cs": {
            "HasNoNamedDataStreams(snapshot.ParentHandle)": 1,
            "private IntPtr launchBinding": 1,
            "RebindChild(out launchBinding)": 1,
            "CloseHandle(launchBinding)": 1,
        },
    }
    for name, counts in exact_control_counts.items():
        for marker, expected_count in counts.items():
            if sources[name].count(marker) != expected_count:
                raise VerificationError(name + " production control count " + marker)
    controller = sources["ControllerLiveNative.cs"]
    supervisor = sources["SupervisorLiveNative.cs"]
    locked_live = sources["LockedPreflightLiveNative.cs"]
    controller_counts = {
        "CaptureExactClient(window, client, true": 2,
        "CaptureExactClient(window, client, false": 2,
        "RuntimeCanonicalData.TryEncodeCanonicalBmp(": 2,
        "RuntimeCanonicalData.IsApprovedCanonicalBmp(": 4,
        "PublishCreateNewOutput(": 4,
        "DeleteRelativeOutput(": 4,
        "GetProcessDpiAwareness(child.Process, out dpiAwareness)": 1,
        "RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName)": 2,
        "RelativeNameAbsent(RuntimeCanonicalData.CompleteBmpName)": 2,
    }
    for marker, expected_count in controller_counts.items():
        if controller.count(marker) != expected_count:
            raise VerificationError("controller capture/publication count " + marker)
    for forbidden_marker in ("GetProcessDpiAwareness(IntPtr.Zero",
            ".TrimEnd('\\n')", ".TrimEnd('\\r', '\\n')", ".TrimEnd()"):
        if forbidden_marker in controller + supervisor:
            raise VerificationError("evidence/capture alternate implementation " +
                forbidden_marker)
    require_ordered(controller, (
        "CaptureExactClient(window, client, false, out completeTwo)",
        "EqualBytes(completeOne, completeTwo)",
        "RuntimeCanonicalData.TryEncodeCanonicalBmp(readyOne, out readyBmp)",
        "RuntimeCanonicalData.TryEncodeCanonicalBmp(completeOne, out completeBmp)",
        "RuntimeCanonicalData.IsApprovedCanonicalBmp(readyBmp, true)",
        "RuntimeCanonicalData.IsApprovedCanonicalBmp(completeBmp, false)",
        "PublishCreateNewOutput(RuntimeCanonicalData.ReadyBmpName, readyBmp",
        "PublishCreateNewOutput(RuntimeCanonicalData.CompleteBmpName, completeBmp",
        'PublishCreateNewOutput("SyntheticLauncherWorkerEvidence.v1.json", bytes',
        "outputsAccepted = true;",
    ), "controller capture to publication", False)
    require_ordered(controller, (
        "if (workerEvidencePublished)",
        'DeleteRelativeOutput("SyntheticLauncherWorkerEvidence.v1.json")',
        "if (completeBmpPublished)",
        "DeleteRelativeOutput(RuntimeCanonicalData.CompleteBmpName)",
        "if (readyBmpPublished)",
        "DeleteRelativeOutput(RuntimeCanonicalData.ReadyBmpName)",
    ), "controller failed-publication deletion", False)
    require_ordered(controller, (
        "private RuntimeScenarioStepResult UiInput()",
        "if (GetForegroundWindow() != window || !AllRelevantInputUp() ||",
        "!ExactSessionDesktop() ||",
        "!ExactControllerTopology(route, child.ProcessId, true, false) ||",
        "!TryExactUiGeometry(out currentClient, out currentClick) ||",
        "transitionDeadlineStarted = TryStartDeadline(10000,",
        "Input[] input = FixedClick(clickPoint, NonceFromPrivateConfiguration());",
        "inputReleaseArmed = true;",
        "uint inserted = SendInput((uint)input.Length, input, Marshal.SizeOf(typeof(Input)));",
    ), "immediate pre-SendInput checks", False)
    require_ordered(controller, (
        "IntPtr previous = SelectObject(target, bitmap);",
        "BitBlt(target, 0, 0,",
        "IntPtr restored = SelectObject(target, previous);",
        "bitmapSelected = false;",
        "GetDIBits(target, bitmap, 0,",
    ), "capture bitmap deselection", False)
    for marker in ("private const uint ProcessMemoryLimit = 268435456;",
            "private const uint UiJobMemoryLimit = 268435456;",
            "private const uint TimeoutJobMemoryLimit = 536870912;",
            "LimitActiveProcess |\n                LimitProcessMemory | LimitJobMemory | LimitKillOnJobClose",
            "route.Route == ControllerRoute.TreeTimeout ? 2U : 1U",
            "TimeoutJobMemoryLimit : UiJobMemoryLimit",
            "observed.ProcessMemoryLimit.ToUInt64() == ProcessMemoryLimit",
            "observed.JobMemoryLimit.ToUInt64() == expectedJobMemory"):
        if marker not in controller:
            raise VerificationError("inner Job limits " + marker)
    if supervisor.count("EqualBytes(workerEvidence, ExpectedWorkerEvidence(route))") != 1 or \
            '\\"worker_evidence\\":' in supervisor:
        raise VerificationError("worker evidence validation/projection")
    for name, source, expected_count in (
            ("controller", controller, 2), ("supervisor", supervisor, 2),
            ("locked", locked_live, 1)):
        if source.count("RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName)") != \
                expected_count or source.count(
                    "RelativeNameAbsent(RuntimeCanonicalData.CompleteBmpName)") != expected_count:
            raise VerificationError(name + " route BMP absence")
    report_markers = (
        '\\"checks\\":', '\\"errors\\":[]', '\\"observations\\":',
        '\\"attempt_root_object_id_sha256\\":', '\\"run\\":{', '\\"summary\\":',
        '\\"worker_stage_evidence_exact\\":true', '\\"source_revision\\":',
    )
    for marker in report_markers:
        if marker not in supervisor:
            raise VerificationError("full report source field " + marker)
    for marker in ("RemainingToDeadline(attemptStart, attemptDeadline) == 0",
            "RemainingToDeadline(attemptStart, attemptDeadline) != 0",
            "TryBoundedDeadline(WorkerWaitMilliseconds, EmptyWaitMilliseconds",
            "deadline = Math.Min(overall, local);",
            "RuntimeDeadlineMath.CanProbe(start, deadline, before, frequency)"):
        if marker not in supervisor:
            raise VerificationError("supervisor hard deadline " + marker)
    for marker in ("routeDeadlineStarted = TryStartDeadline(routeBudget",
            "transitionDeadlineStarted = TryStartDeadline(10000",
            "Math.Min(1000U, remaining)",
            "RuntimeDeadlineMath.CanProbe(start, deadline, before, frequency)"):
        if marker not in controller:
            raise VerificationError("controller hard deadline " + marker)
    termination_calls = {
        "SupervisorLiveNative.cs": r"\bTerminateProcess\s*\(\s*process\.Process\s*,",
        "ControllerLiveNative.cs": r"\bTerminateProcess\s*\(\s*child\.Process\s*,",
    }
    for name, pattern in termination_calls.items():
        if len(re.findall(pattern, strip_literals(sources[name]))) != 1:
            raise VerificationError(name + " direct orphan termination")
    locked = sources["LockedPreflightEntry.cs"] + sources["LockedPreflightBootstrapNative.cs"] + \
        sources["LockedPreflightLiveNative.cs"]
    for marker in ("CreateProcess", "CreateProcessAsUser", "DuplicateToken", "SendInput",
            "BitBlt", "RegOpen", "CreateEnvironmentBlock"):
        if marker in strip_literals(locked):
            raise VerificationError("locked preflight authority " + marker)
    timeout_child = sources["TimeoutChildEntry.cs"] + sources["TimeoutChildBootstrapNative.cs"] + \
        sources["TimeoutChildLiveNative.cs"]
    for marker in ("CreateProcess", "CreateProcessAsUser", "DuplicateToken", "SendInput",
            "BitBlt", "RegOpen", "CreateEnvironmentBlock"):
        if marker in strip_literals(timeout_child):
            raise VerificationError("timeout child authority " + marker)


def expect_identity(value: object, raw: bytes, label: str) -> None:
    if value != identity_object(raw):
        raise VerificationError(label + " identity")


def verify_control_data(captured: dict[str, bytes]) -> None:
    public = parse_canonical_json(captured[
        "config/synthetic-launcher-runtime-public-pinned-fixture-v1.json"], "public fixture")
    public_schema = parse_canonical_json(captured[
        "config/synthetic-launcher-runtime-public-v1.schema.json"], "public schema")
    private = parse_canonical_json(captured[
        "config/synthetic-launcher-runtime-private-pinned-fixture-v1.json"], "private fixture")
    worker_schema = parse_canonical_json(captured[
        "config/synthetic-launcher-worker-evidence-v1.schema.json"], "worker schema")
    full_schema = parse_canonical_json(captured[
        "config/synthetic-launcher-report-full-v1.schema.json"], "full report schema")
    derived_artifacts = {
        role + "_bmp": identity_object(derived_canonical_bmp(role == "ready"))
        for role in ("complete", "ready")
    }
    if derived_artifacts != APPROVED_ARTIFACTS:
        raise VerificationError("approved BMP independent derivation")
    if not isinstance(public, dict) or public.get("build_binding") != "build-pinned" or \
            public.get("schema_version") != 1 or not isinstance(private, dict) or \
            private.get("scenario_id") != "ui-success-v1" or private.get("schema_version") != 1:
        raise VerificationError("pinned fixtures")
    if public.get("profile_id") != "cm0102-synthetic-launcher-runtime-v1" or \
            set(public.get("role_identities", {})) != {
                "controller", "locked_preflight", "supervisor", "timeout_child",
                "timeout_root", "ui_fixture"} or \
            set(private.get("expected_identities", {})) != set(public["role_identities"]):
        raise VerificationError("pinned fixture role set")
    for value in public.get("role_identities", {}).values():
        if not isinstance(value, dict) or value.get("byte_count") not in (1, 14336):
            raise VerificationError("fixture placeholder identity")
    if public.get("fixed_names") != EXPECTED_FIXED_NAMES or \
            public.get("approved_artifacts") != APPROVED_ARTIFACTS:
        raise VerificationError("public fixed names or approved artifacts")
    if not isinstance(public_schema, dict) or public_schema.get("type") != "object" or \
            public_schema.get("additionalProperties") is not False or \
            set(public_schema.get("required", [])) != {
                "approved_artifacts", "build_binding", "candidate_production_manifest",
                "fixed_names", "profile_id", "role_identities", "runtime_private_schema",
                "schema_version", "source_revision"}:
        raise VerificationError("public schema grammar")
    public_properties = public_schema.get("properties")
    if not isinstance(public_properties, dict) or \
            public_properties.get("fixed_names") != {"const": EXPECTED_FIXED_NAMES} or \
            public_properties.get("approved_artifacts") != {"const": APPROVED_ARTIFACTS}:
        raise VerificationError("public schema fixed names or approved artifacts")
    if not isinstance(worker_schema, dict) or worker_schema.get("type") != "object" or \
            worker_schema.get("additionalProperties") is not False or \
            set(worker_schema.get("required", [])) != {
                "artifacts", "bindings", "evidence_kind", "observations", "profile_id",
                "scenario_id", "schema_version", "source_revision"}:
        raise VerificationError("worker evidence grammar")
    worker_properties = worker_schema.get("properties")
    if not isinstance(worker_properties, dict) or \
            worker_properties.get("evidence_kind") != {"const": "worker"} or \
            worker_properties.get("profile_id") != {
                "const": "cm0102-synthetic-launcher-runtime-v1"} or \
            worker_properties.get("schema_version") != {"const": 1} or \
            worker_properties.get("artifacts") != {"$ref": "#/$defs/artifact_set"}:
        raise VerificationError("worker evidence header")
    worker_defs = worker_schema.get("$defs")
    worker_artifacts = worker_defs.get("artifact_set") if isinstance(worker_defs, dict) else None
    if not isinstance(worker_artifacts, dict) or \
            worker_artifacts.get("additionalProperties") is not False or \
            set(worker_artifacts.get("required", [])) != {"complete_bmp", "ready_bmp"} or \
            set(worker_artifacts.get("properties", {})) != {"complete_bmp", "ready_bmp"}:
        raise VerificationError("worker artifact grammar")
    worker_observations = worker_properties.get("observations")
    expected_worker_observations = {
        "binding_exact", "cleanup_exact", "controller_create_as_user_calls",
        "environment_exact", "fallback_create_calls", "fixture_resume_calls",
        "guard_counts_exact", "inner_job_exact", "input_capture_exact",
        "locked_refusal_exact", "parent_child_topology_exact", "registry_denied_exact",
        "session_desktop_exact", "streams_empty", "target_result", "timeout_tree_exact",
        "token_relationship_exact",
    }
    if not isinstance(worker_observations, dict) or \
            worker_observations.get("additionalProperties") is not False or \
            set(worker_observations.get("required", [])) != expected_worker_observations or \
            set(worker_observations.get("properties", {})) != expected_worker_observations:
        raise VerificationError("worker evidence observations")
    worker_routes = worker_schema.get("allOf")
    if not isinstance(worker_routes, list) or len(worker_routes) != 3 or \
            {route.get("if", {}).get("properties", {}).get("scenario_id", {}).get("const")
                for route in worker_routes if isinstance(route, dict)} != {
                    "locked-refusal-v1", "tree-timeout-v1", "ui-success-v1"}:
        raise VerificationError("worker evidence routes")
    expected_route_artifacts = {
        "locked-refusal-v1": {"complete_bmp": "absent", "ready_bmp": "absent"},
        "tree-timeout-v1": {"complete_bmp": "absent", "ready_bmp": "absent"},
        "ui-success-v1": APPROVED_ARTIFACTS,
    }
    for route in worker_routes:
        if not isinstance(route, dict):
            raise VerificationError("worker evidence route object")
        scenario = route.get("if", {}).get("properties", {}).get(
            "scenario_id", {}).get("const")
        artifacts = route.get("then", {}).get("properties", {}).get("artifacts")
        if artifacts != {"const": expected_route_artifacts.get(scenario)}:
            raise VerificationError("worker route artifacts")
    route_text = json.dumps(worker_routes, ensure_ascii=True, sort_keys=True)
    for marker in ("locked-refusal", "tree-timeout-contained", "ui-complete",
            "not-applicable", "pass"):
        if marker not in route_text:
            raise VerificationError("worker evidence route value " + marker)

    if not isinstance(full_schema, dict) or full_schema.get("type") != "object" or \
            full_schema.get("additionalProperties") is not False or \
            "two-party" not in str(full_schema.get("$comment", "")).lower() or \
            set(full_schema.get("required", [])) != {
                "artifacts", "bindings", "checks", "errors", "observations",
                "original_behavior_qualified", "original_execution_status", "profile_id",
                "report_kind", "run", "scenario_id", "schema_version", "source_revision",
                "summary", "supervisor_observations"}:
        raise VerificationError("full report grammar")
    full_properties = full_schema.get("properties")
    if not isinstance(full_properties, dict) or \
            full_properties.get("original_behavior_qualified") != {"const": False} or \
            full_properties.get("original_execution_status") != {"const": "not-run"} or \
            full_properties.get("report_kind") != {"const": "supervisor-composed"} or \
            full_properties.get("artifacts") != {"$ref": "#/$defs/artifact_set"} or \
            full_properties.get("checks") != {"$ref": "#/$defs/checks"} or \
            full_properties.get("errors") != {"const": []} or \
            full_properties.get("observations") != {"$ref": "#/$defs/observations"} or \
            full_properties.get("run") != {"$ref": "#/$defs/run"} or \
            full_properties.get("summary") != {"$ref": "#/$defs/summary"} or \
            "worker_evidence" in full_properties:
        raise VerificationError("full report composition")
    full_defs = full_schema.get("$defs")
    if not isinstance(full_defs, dict):
        raise VerificationError("full report definitions")
    full_checks = full_defs.get("checks")
    if not isinstance(full_checks, dict) or full_checks.get("additionalProperties") is not False or \
            set(full_checks.get("required", [])) != CHECK_IDS or \
            set(full_checks.get("properties", {})) != CHECK_IDS:
        raise VerificationError("full report checks")
    observations = full_defs.get("observations")
    if not isinstance(observations, dict) or observations.get("additionalProperties") is not False or \
            set(observations.get("required", [])) != {
                "capture", "environment", "privacy", "worker_stage_evidence_exact"} or \
            set(observations.get("properties", {})) != {
                "capture", "environment", "privacy", "worker_stage_evidence_exact"}:
        raise VerificationError("full report observations")
    observation_shapes = {
        "capture": {"complete_bmp", "complete_repeat_exact", "every_pixel_expected",
            "ready_bmp", "ready_repeat_exact"},
        "environment": {"nonce_sha256", "status"},
        "privacy": {"forbidden_string_count", "scan_passed",
            "unexpected_screen_bytes_retained"},
    }
    for name, expected in observation_shapes.items():
        value = observations.get("properties", {}).get(name)
        if not isinstance(value, dict) or value.get("additionalProperties") is not False or \
                set(value.get("required", [])) != expected or \
                set(value.get("properties", {})) != expected:
            raise VerificationError("full report observation " + name)
    run = full_defs.get("run")
    if not isinstance(run, dict) or run.get("additionalProperties") is not False or \
            set(run.get("required", [])) != {
                "attempt_id_sha256", "attempt_ordinal", "elapsed_ms", "observed_at_utc",
                "source_revision"} or set(run.get("properties", {})) != {
                    "attempt_id_sha256", "attempt_ordinal", "elapsed_ms", "observed_at_utc",
                    "source_revision"}:
        raise VerificationError("full report run")
    bindings_schema = full_properties.get("bindings")
    expected_full_bindings = {"attempt_root_object_id_sha256", "build_manifest",
        "private_configuration", "public_configuration", "role_identities", "worker_image"}
    if not isinstance(bindings_schema, dict) or \
            bindings_schema.get("additionalProperties") is not False or \
            set(bindings_schema.get("required", [])) != expected_full_bindings or \
            set(bindings_schema.get("properties", {})) != expected_full_bindings:
        raise VerificationError("full report bindings")
    expected_summaries = {
        ("locked-refusal-v1", "not-run", "synthetic-locked-refusal"),
        ("tree-timeout-v1", "expected-timeout-contained",
            "synthetic-tree-timeout-contained"),
        ("ui-success-v1", "succeeded", "synthetic-launcher-qualified"),
    }
    summary = full_defs.get("summary")
    summary_values = summary.get("oneOf") if isinstance(summary, dict) else None
    if not isinstance(summary_values, list) or len(summary_values) != 3:
        raise VerificationError("full report summary")
    observed_summaries = set()
    for item in summary_values:
        value = item.get("const") if isinstance(item, dict) else None
        if not isinstance(value, dict) or set(value) != {"comparison_verdict", "completeness",
                "fixture_execution_status", "original_behavior_qualified",
                "original_execution_status", "qualification_eligible", "safety_verdict",
                "scenario_id"} or value.get("comparison_verdict") != "not-run" or \
                value.get("completeness") != "complete" or \
                value.get("original_behavior_qualified") is not False or \
                value.get("original_execution_status") != "not-run" or \
                value.get("qualification_eligible") is not True:
            raise VerificationError("full report summary value")
        observed_summaries.add((value.get("scenario_id"),
            value.get("fixture_execution_status"), value.get("safety_verdict")))
    if observed_summaries != expected_summaries:
        raise VerificationError("full report scenario summaries")
    supervisor = full_properties.get("supervisor_observations")
    expected_supervisor = {
        "active_process_limit", "assigned_before_resume", "create_calls", "job_empty",
        "job_memory_limit_bytes", "membership_before_resume", "post_worker_topology_exact",
        "process_memory_limit_bytes", "resume_calls", "streams_empty", "termination_used",
        "worker_exit_code",
    }
    if not isinstance(supervisor, dict) or supervisor.get("additionalProperties") is not False or \
            set(supervisor.get("required", [])) != expected_supervisor or \
            set(supervisor.get("properties", {})) != expected_supervisor:
        raise VerificationError("supervisor report observations")
    full_routes = full_schema.get("allOf")
    if not isinstance(full_routes, list) or len(full_routes) != 3 or \
            {route.get("if", {}).get("properties", {}).get("scenario_id", {}).get("const")
                for route in full_routes if isinstance(route, dict)} != {
                    "locked-refusal-v1", "tree-timeout-v1", "ui-success-v1"}:
        raise VerificationError("full report routes")
    summary_by_scenario = {value["scenario_id"]: value for value in
        (item["const"] for item in summary_values)}
    expected_outer = {
        "locked-refusal-v1": (1, 268435456, 21),
        "tree-timeout-v1": (3, 805306368, 22),
        "ui-success-v1": (2, 536870912, 0),
    }
    expected_checks_by_scenario = {}
    for scenario in expected_outer:
        checks = {name: "pass" for name in CHECK_IDS}
        not_applicable = set()
        if scenario == "locked-refusal-v1":
            not_applicable = {"capture-complete-exact", "capture-ready-exact",
                "environment-exact", "input-exact", "registry-denied",
                "token-relationship", "window-exact"}
        elif scenario == "tree-timeout-v1":
            not_applicable = {"capture-complete-exact", "capture-ready-exact",
                "input-exact", "window-exact"}
        for name in not_applicable:
            checks[name] = "not-applicable"
        expected_checks_by_scenario[scenario] = checks
    for route in full_routes:
        if not isinstance(route, dict):
            raise VerificationError("full report route object")
        scenario = route.get("if", {}).get("properties", {}).get(
            "scenario_id", {}).get("const")
        then = route.get("then", {}).get("properties", {})
        expected_artifacts = expected_route_artifacts.get(scenario)
        expected_capture = {"complete_bmp": expected_artifacts["complete_bmp"],
            "complete_repeat_exact": scenario == "ui-success-v1",
            "every_pixel_expected": scenario == "ui-success-v1",
            "ready_bmp": expected_artifacts["ready_bmp"],
            "ready_repeat_exact": scenario == "ui-success-v1"}
        route_observations = then.get("observations", {}).get("properties", {})
        outer = expected_outer.get(scenario)
        supervisor_route = then.get("supervisor_observations", {}).get("properties", {})
        if expected_artifacts is None or then.get("artifacts") != {
                "const": expected_artifacts} or then.get("summary") != {
                    "const": summary_by_scenario[scenario]} or \
                route_observations.get("capture") != {"const": expected_capture} or \
                "worker_evidence" in then or outer is None or \
                supervisor_route.get("active_process_limit") != {"const": outer[0]} or \
                supervisor_route.get("job_memory_limit_bytes") != {"const": outer[1]} or \
                supervisor_route.get("worker_exit_code") != {"const": outer[2]}:
            raise VerificationError("full report route binding")
        check_value = then.get("checks", {}).get("const")
        environment_status = route_observations.get("environment", {}).get(
            "properties", {}).get("status")
        if check_value != expected_checks_by_scenario.get(scenario) or \
                environment_status != {"const": "not-observed" if
                    scenario == "locked-refusal-v1" else "observed"}:
            raise VerificationError("full report route checks")

    first_report = {
        "bindings": {"attempt_root_object_id_sha256": "1" * 64,
            "private_configuration": {"byte_count": 100, "sha256": "2" * 64}},
        "observations": {"environment": {"nonce_sha256": "3" * 64}},
        "run": {"attempt_id_sha256": "4" * 64, "attempt_ordinal": 1,
            "elapsed_ms": 10, "observed_at_utc": "2026-10-25T00:00:00Z"},
        "stable": {"scenario_id": "ui-success-v1", "worker_image": "5" * 64},
    }
    second_report = json.loads(json.dumps(first_report))
    second_report["bindings"]["attempt_root_object_id_sha256"] = "6" * 64
    second_report["bindings"]["private_configuration"] = {
        "byte_count": 101, "sha256": "7" * 64}
    second_report["observations"]["environment"]["nonce_sha256"] = "8" * 64
    second_report["run"] = {"attempt_id_sha256": "9" * 64, "attempt_ordinal": 2,
        "elapsed_ms": 11, "observed_at_utc": "2026-10-25T00:00:01Z"}
    if projected_report(first_report) != projected_report(second_report):
        raise VerificationError("frozen cross-attempt projection")
    first_report["worker_evidence"] = {"private_configuration": "a" * 64}
    second_report["worker_evidence"] = {"private_configuration": "b" * 64}
    if projected_report(first_report) == projected_report(second_report):
        raise VerificationError("cross-attempt projection silently broadened")

    implementation = parse_canonical_json(captured[IMPLEMENTATION_PATH], "implementation config")
    schema = parse_canonical_json(captured[IMPLEMENTATION_SCHEMA_PATH], "implementation schema")
    if not isinstance(implementation, dict) or implementation.get("schema_version") != 1 or \
            implementation.get("profile_id") != "cm0102-synthetic-launcher-implementation-v1":
        raise VerificationError("implementation config header")
    if set(implementation) != {"contract_state", "execution_policy", "fixed_names",
            "production_images", "profile_id", "schema_version", "source_bindings"}:
        raise VerificationError("implementation config inventory")
    expected_state = {
        "build_binding": "build-unpinned", "comparison_verdict": "not-run",
        "fixture_execution_status": "not-run", "live_execution_status": "not-run",
        "original_behavior_qualified": False, "original_execution_status": "not-run",
        "process_creation_reachable": False, "qualification_eligible": False,
    }
    if implementation.get("contract_state") != expected_state:
        raise VerificationError("implementation config state")
    if implementation.get("execution_policy") != {
            "allowed_test_executable": "RuntimeGateTests.exe",
            "production_execution_forbidden": True,
            "retained_harness_timeout_seconds": 1200,
            "test_timeout_seconds": 30,
        } or implementation.get("fixed_names") != {
            **EXPECTED_FIXED_NAMES,
        }:
        raise VerificationError("implementation execution or names")
    bindings = implementation.get("source_bindings")
    if not isinstance(bindings, dict):
        raise VerificationError("implementation source bindings")
    expected_bindings = {
        "runtime_implementation_verifier": VERIFIER_PATH,
        "retained_no_ui_harness": HARNESS_PATH,
        "runtime_private_schema": "config/synthetic-launcher-runtime-private-v1.schema.json",
        "runtime_public_pinned_fixture":
            "config/synthetic-launcher-runtime-public-pinned-fixture-v1.json",
        "runtime_public_schema": "config/synthetic-launcher-runtime-public-v1.schema.json",
        "retained_qualification_helper": QUALIFICATION_HELPER_PATH,
        "worker_evidence_schema": "config/synthetic-launcher-worker-evidence-v1.schema.json",
        "full_report_schema": "config/synthetic-launcher-report-full-v1.schema.json",
    }
    if set(bindings) != set(expected_bindings):
        raise VerificationError("implementation binding inventory")
    for role, path in expected_bindings.items():
        expect_identity(bindings[role], captured[path], role)
    outputs = implementation.get("production_images")
    if not isinstance(outputs, dict) or set(outputs) != set(IMAGE_SPECS) or \
            any(value != "live-unbound-not-run" for value in outputs.values()):
        raise VerificationError("implementation production status")
    expected_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
        "const": implementation, "type": "object"}
    if schema != expected_schema:
        raise VerificationError("implementation exact-const schema")


def verify_harness(source: str) -> None:
    for marker in (
        'EXPECTED_TEST_STDOUT = b"PASS runtime-gate-v1\\r\\n"',
        "BUILD_TIMEOUT_SECONDS = 180", "TEST_TIMEOUT_SECONDS = 30",
        '"live_execution_status": "not-run"', '"original_execution_status": "not-run"',
        '"qualification_eligible": False', "validate_pe32_cli", "IMAGE_SPECS",
        "RuntimeGateTests.exe", "compiler_inputs", "source commit is not exact HEAD",
        "only RuntimeGateTests.exe may execute", "candidate-production-build-v1",
        "run_static_verifier", "HARNESS_TIMEOUT_SECONDS = 1200",
        "IMPORT_MATRIX_SHA256", "frozen_impl_maps",
        "accepted extra production import", "TRUSTED_HELPER_EXPORTS",
        "trusted_bind_helper", "trusted_bootstrap_static_check",
        "working helper differs from exact HEAD", "retained-build helper binding changed",
        "destination = helper.private_parent(target)",
        "helper.wsl_native_mount_binding(destination.parent)",
        "helper.verify_tree_mount_binding(destination, mount)",
        "retained root ownership or mode", "retained manifest inventory",
        "stat.S_IMODE(root_metadata.st_mode) != 0o700",
        "manifest.get(\"environment\") != expected_environment",
        "fresh retained tree self-test",
    ):
        if marker not in source:
            raise VerificationError("retained harness contract " + marker)
    for name in IMAGE_SPECS:
        if name not in source:
            raise VerificationError("retained harness output " + name)
    if re.search(r"run_command\([^\n]*SyntheticLauncher", source):
        raise VerificationError("production execution helper route")
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise VerificationError("retained harness syntax") from error
    allowed_callers = {"run_compiler", "run_gate_test", "run_static_verifier"}
    for function in (node for node in ast.walk(tree) if isinstance(node,
            (ast.FunctionDef, ast.AsyncFunctionDef))):
        for node in ast.walk(function):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                    node.func.id == "run_command" and function.name not in allowed_callers:
                raise VerificationError("unapproved command caller " + function.name)
    for marker in ("subprocess.", "os.system", "os.popen", "shell=True"):
        if marker in source:
            raise VerificationError("retained harness alternate execution " + marker)
    subprocess_imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and
        node.module == "subprocess"]
    if len(subprocess_imports) != 1 or \
            [(item.name, item.asname) for item in subprocess_imports[0].names] != [
                ("DEVNULL", None), ("PIPE", None), ("run", "trusted_run")]:
        raise VerificationError("retained harness trusted subprocess import")
    trusted_calls: list[tuple[str, str]] = []
    for function in (node for node in ast.walk(tree) if isinstance(node,
            (ast.FunctionDef, ast.AsyncFunctionDef))):
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            if isinstance(call.func, ast.Name) and call.func.id in {
                    "trusted_run", "compile", "exec"}:
                trusted_calls.append((call.func.id, function.name))
    if sorted(trusted_calls) != sorted((
            ("trusted_run", "trusted_git"),
            ("compile", "load_helper"),
            ("exec", "load_helper"),
        )):
        raise VerificationError("retained harness trusted helper execution surface")
    require_ordered(source, (
        "trusted_validate_head(repo, commit)",
        "raw = trusted_read_helper(path)",
        'trusted_git(repo, ["show", commit + ":" + HELPER_PATH], MAX_SOURCE_BYTES)',
        'trusted_git(repo, ["rev-parse", commit + ":" + HELPER_PATH], 128)',
        'trusted_git(repo, ["cat-file", "-t", blob], 64)',
        "code = compile(raw, os.fspath(path), \"exec\", dont_inherit=True, optimize=0)",
        "exec(code, module.__dict__)",
        "rebound_path, rebound_raw = trusted_bind_helper(repo, commit)",
    ), "retained harness trusted helper bootstrap", False)


def verify_all(captured: dict[str, bytes]) -> None:
    expected_frozen = set(captured_paths()) - {
        VERIFIER_PATH, IMPLEMENTATION_PATH, IMPLEMENTATION_SCHEMA_PATH}
    if set(FROZEN_IDENTITIES) != expected_frozen:
        raise VerificationError("frozen identity inventory")
    for relative in sorted(expected_frozen):
        if identity(captured[relative]) != FROZEN_IDENTITIES[relative]:
            raise VerificationError(relative + " frozen identity")
    sources = {name: decode_ascii(captured[RUNTIME_ROOT + "/" + name], name)
        for name in (*PURE_FILES, *PRODUCTION_FILES)}
    verify_pure_sources(sources)
    verify_production_sources(sources)
    verify_control_data(captured)
    verify_harness(decode_ascii(captured[HARNESS_PATH], "retained harness"))
    readme = decode_ascii(captured[README_PATH], "runtime README")
    contract = captured[CONTRACT_PATH].decode("utf-8", "strict")
    for marker in ("build-unpinned", "No production image", "not-run",
            "RuntimeGateTests.exe", "one-use"):
        if marker not in readme:
            raise VerificationError("runtime README " + marker)
    for marker in ("two-party", "one-use", "P/Invoke-free", "not run"):
        if marker.lower() not in contract.lower():
            raise VerificationError("implementation contract " + marker)


def captured_paths() -> tuple[str, ...]:
    return tuple(RUNTIME_ROOT + "/" + name for name in EXPECTED_RUNTIME_FILES) + \
        CONFIG_PATHS + (QUALIFICATION_HELPER_PATH, CONTRACT_PATH)


def verify(repo_argument: pathlib.Path, commit: str) -> dict[str, tuple[int, str]]:
    if not GIT.is_file() or not repo_argument.is_absolute() or \
            repo_argument.resolve(strict=True) != repo_argument:
        raise VerificationError("repository path")
    repo = repo_argument
    require_path_components(repo)
    if pathlib.Path(run_git(repo, ["rev-parse", "--show-toplevel"]).decode().strip()) != repo:
        raise VerificationError("repository is not canonical top level")
    validate_commit(repo, commit)
    inventory = run_git(repo, ["ls-tree", "-r", "--name-only", commit, "--", RUNTIME_ROOT]).decode(
        "ascii", "strict").splitlines()
    expected = [RUNTIME_ROOT + "/" + name for name in EXPECTED_RUNTIME_FILES]
    if inventory != sorted(expected):
        raise VerificationError("runtime commit inventory")
    observed_names = sorted(path.name for path in (repo / RUNTIME_ROOT).iterdir())
    if observed_names != sorted(EXPECTED_RUNTIME_FILES):
        raise VerificationError("runtime filesystem inventory")
    captured: dict[str, bytes] = {}
    identities: dict[str, tuple[int, str]] = {}
    for relative in captured_paths():
        raw = read_bound(repo / relative)
        if raw != run_git(repo, ["show", commit + ":" + relative]):
            raise VerificationError(relative + " differs from source commit")
        if relative in FROZEN_IDENTITIES and identity(raw) != FROZEN_IDENTITIES[relative]:
            raise VerificationError(relative + " frozen identity")
        captured[relative] = raw
        identities[relative] = identity(raw)
    validate_execution_source(repo, captured[VERIFIER_PATH])
    verify_all(captured)
    for relative, raw in captured.items():
        if read_bound(repo / relative) != raw:
            raise VerificationError(relative + " changed across verification")
    validate_commit(repo, commit)
    return identities


def self_test() -> None:
    repo = pathlib.Path.cwd().resolve(strict=True)
    captured = {relative: read_bound(repo / relative) for relative in captured_paths()}
    validate_execution_source(repo, captured[VERIFIER_PATH])
    verify_all(captured)
    pure = {name: decode_ascii(captured[RUNTIME_ROOT + "/" + name], name)
        for name in PURE_FILES}
    for name, marker in (("RuntimeGate.cs", "System.IO.File.ReadAllText"),
            ("RuntimeGateTests.cs", "[DllImport(\"kernel32.dll\")]") ,
            ("RuntimeCanonicalData.cs", "System.Environment.GetEnvironmentVariable")):
        changed = dict(pure)
        changed[name] += "\n" + marker + ";\n"
        try:
            verify_pure_sources(changed)
        except VerificationError:
            pass
        else:
            raise VerificationError("accepted pure authority mutation")
    production = {name: decode_ascii(captured[RUNTIME_ROOT + "/" + name], name)
        for name in (*PRODUCTION_FILES, "RuntimeCanonicalData.cs")}

    def reject_pure_replacement(name: str, old: str, new: str, label: str) -> None:
        if pure[name].count(old) != 1:
            raise VerificationError("self-test source marker " + label)
        changed = dict(pure)
        changed[name] = pure[name].replace(old, new, 1)
        try:
            verify_pure_sources(changed)
        except VerificationError:
            return
        raise VerificationError("accepted " + label + " mutation")

    def reject_production_replacement(name: str, old: str, new: str, label: str,
            expected_count: int = 1) -> None:
        if production[name].count(old) != expected_count:
            raise VerificationError("self-test source marker " + label)
        changed = dict(production)
        changed[name] = production[name].replace(old, new, 1)
        try:
            verify_production_sources(changed)
        except VerificationError:
            return
        raise VerificationError("accepted " + label + " mutation")

    reject_production_replacement("SupervisorEntry.cs",
        "RuntimeScenarioEngine.Run(plan, port).ExitCode",
        "port.Execute(plan.StageAt(0)).ExitCode", "scenario engine bypass")
    reject_pure_replacement("RuntimeCanonicalData.cs",
        "step = port.Execute(stage);", "step = RuntimeScenarioStepResult.Passed();",
        "scenario engine stage")
    reject_pure_replacement("RuntimeCanonicalData.cs",
        "RuntimeScenarioStepResult cleanup = port.Cleanup();",
        "RuntimeScenarioStepResult cleanup = RuntimeScenarioStepResult.Passed();",
        "scenario engine cleanup")
    reject_pure_replacement("RuntimeCanonicalData.cs",
        "internal static bool CanProbe(", "internal static bool CanPoll(",
        "shared deadline probe")
    reject_pure_replacement("RuntimeGateTests.cs", "DeadlineMathCases();",
        "CanonicalDataCases();", "shared deadline tests")
    reject_pure_replacement("RuntimeCanonicalData.cs",
        "PutUInt32(value, 10, 54);", "PutUInt32(value, 10, 40);",
        "canonical BMP pixel offset")
    reject_pure_replacement("RuntimeCanonicalData.cs",
        "for (int y = 239; y >= 0; y--)", "for (int y = 0; y < 240; y++)",
        "canonical BMP orientation")
    reject_pure_replacement("RuntimeCanonicalData.cs",
        "return String.Equals(Sha256Hex(value), expected, StringComparison.Ordinal);",
        "return value.Length == CanonicalBmpByteCount;", "canonical BMP hash approval")
    reject_pure_replacement("RuntimeGateTests.cs", "CanonicalBmpCases();",
        "CanonicalDataCases();", "canonical BMP/hash tests")
    reject_pure_replacement("RuntimeCanonicalData.cs",
        "RuntimeScenarioStage.TargetCreate,\n                    " +
        "RuntimeScenarioStage.InnerJobConfigured,",
        "RuntimeScenarioStage.InnerJobConfigured,\n                    " +
        "RuntimeScenarioStage.TargetCreate,", "controller create/job stage order")
    legacy_pure = dict(pure)
    legacy_pure["RuntimeCanonicalData.cs"] += \
        "\ninternal sealed class RuntimeScenarioFaultModel { }\n"
    try:
        verify_pure_sources(legacy_pure)
    except VerificationError:
        pass
    else:
        raise VerificationError("accepted legacy scenario model mutation")
    reject_production_replacement("ControllerLiveNative.cs",
        "(directory && !HasNoNamedDataStreams(handle))",
        "(directory && false)", "controller directory ADS")
    reject_production_replacement("ControllerBootstrapNative.cs",
        "((control & 0x1000) != 0) != directory", "false",
        "directory-protected/file-inherited DACL distinction")
    reject_production_replacement("SupervisorLiveNative.cs",
        "RuntimeDeadlineMath.CanProbe(", "RuntimeDeadlineMath.RemainingMilliseconds(",
        "supervisor deadline probe", 2)
    reject_production_replacement("ControllerLiveNative.cs",
        "RuntimeDeadlineMath.CanProbe(", "RuntimeDeadlineMath.RemainingMilliseconds(",
        "controller deadline probe", 3)
    reject_production_replacement("ControllerLiveNative.cs",
        "GetProcessDpiAwareness(child.Process, out dpiAwareness)",
        "GetProcessDpiAwareness(IntPtr.Zero, out dpiAwareness)", "child DPI authority")
    reject_production_replacement("ControllerLiveNative.cs",
        "if (GetForegroundWindow() != window || !AllRelevantInputUp() ||",
        "if (!AllRelevantInputUp() ||", "immediate foreground input check")
    reject_production_replacement("ControllerLiveNative.cs",
        "move.Mouse.Flags = 0x8000 | 0x0001;",
        "move.Mouse.Flags = 0x8000 | 0x4000 | 0x0001;",
        "primary-monitor absolute input")
    reject_production_replacement("ControllerLiveNative.cs",
        "bitmapSelected = false;", "bitmapSelected = true;",
        "capture bitmap deselection")
    reject_production_replacement("ControllerLiveNative.cs",
        "private const uint TimeoutJobMemoryLimit = 536870912;",
        "private const uint TimeoutJobMemoryLimit = 805306368;", "inner Job memory limit")
    reject_production_replacement("ControllerLiveNative.cs",
        "RuntimeCanonicalData.TryEncodeCanonicalBmp(readyOne, out readyBmp)",
        "readyBmp = readyOne", "ready BMP encoding")
    reject_production_replacement("ControllerLiveNative.cs",
        "CaptureExactClient(window, client, true, out readyTwo)",
        "readyTwo = readyOne", "ready double capture")
    reject_production_replacement("ControllerLiveNative.cs",
        "PublishCreateNewOutput(RuntimeCanonicalData.ReadyBmpName, readyBmp",
        "PublishCreateNewOutput(RuntimeCanonicalData.CompleteBmpName, readyBmp",
        "fixed ready BMP publication")
    reject_production_replacement("ControllerLiveNative.cs",
        "DeleteRelativeOutput(RuntimeCanonicalData.ReadyBmpName)",
        "RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName)",
        "failed ready BMP deletion")
    reject_production_replacement("LockedPreflightLiveNative.cs",
        "RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName)", "true",
        "locked-route BMP absence")
    reject_production_replacement("ControllerLiveNative.cs",
        "RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName)", "true",
        "timeout-route BMP absence", 2)
    reject_production_replacement("SupervisorLiveNative.cs",
        "EqualBytes(workerEvidence, ExpectedWorkerEvidence(route))",
        "workerEvidence != null", "exact worker-evidence validation")
    reject_production_replacement("SupervisorLiveNative.cs",
        "deadline = Math.Min(overall, local);", "deadline = local;",
        "supervisor overall deadline clamp")
    legacy_production = dict(production)
    legacy_production["SupervisorLiveNative.cs"] += \
        "\nprivate void RunFixedWorker() { }\n"
    try:
        verify_production_sources(legacy_production)
    except VerificationError:
        pass
    else:
        raise VerificationError("accepted legacy orchestration mutation")
    harness = decode_ascii(captured[HARNESS_PATH], "retained harness")
    if harness.count("raw != trusted_git(repo, [\"show\", commit + \":\" + " +
            "HELPER_PATH], MAX_SOURCE_BYTES)") != 1:
        raise VerificationError("self-test source marker trusted helper binding")
    changed_harness = harness.replace(
        "raw != trusted_git(repo, [\"show\", commit + \":\" + HELPER_PATH], " +
        "MAX_SOURCE_BYTES)", "False", 1)
    try:
        verify_harness(changed_harness)
    except VerificationError:
        pass
    else:
        raise VerificationError("accepted unbound retained helper mutation")
    changed_harness = harness.replace(
        "helper.wsl_native_mount_binding(destination.parent)",
        "helper.wsl_native_mount_binding(destination)", 1)
    try:
        verify_harness(changed_harness)
    except VerificationError:
        pass
    else:
        raise VerificationError("accepted nonexistent retained mount binding")
    for old, new, label in (
            ("stat.S_IMODE(root_metadata.st_mode) != 0o700", "False",
                "retained root mode omission"),
            ('manifest.get("environment") != expected_environment', "False",
                "retained environment omission")):
        changed_harness = harness.replace(old, new, 1)
        try:
            verify_harness(changed_harness)
        except VerificationError:
            continue
        raise VerificationError("accepted " + label)

    def reject_control_mutation(path: str, mutate, label: str) -> None:
        value = parse_canonical_json(captured[path], label)
        mutate(value)
        changed = dict(captured)
        changed[path] = canonical(value)
        try:
            verify_control_data(changed)
        except VerificationError:
            return
        raise VerificationError("accepted " + label + " mutation")

    reject_control_mutation("config/synthetic-launcher-runtime-public-pinned-fixture-v1.json",
        lambda value: value["fixed_names"].__setitem__("ready_bmp", "Ready.bmp"),
        "public fixed name")
    reject_control_mutation("config/synthetic-launcher-runtime-public-v1.schema.json",
        lambda value: value["properties"]["approved_artifacts"]["const"]
            ["ready_bmp"].__setitem__("sha256", "0" * 64),
        "public approved artifact")
    reject_control_mutation("config/synthetic-launcher-worker-evidence-v1.schema.json",
        lambda value: value["required"].remove("artifacts"),
        "worker artifact requirement")
    reject_control_mutation("config/synthetic-launcher-worker-evidence-v1.schema.json",
        lambda value: value["allOf"][2]["then"]["properties"]["artifacts"]["const"]
            .__setitem__("ready_bmp", "absent"), "worker UI artifact identity")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["required"].remove("checks"),
        "full report checks requirement")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["allOf"][1]["then"]["properties"]["checks"]["const"]
            .__setitem__("input-exact", "pass"), "full report route checks")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["properties"]["errors"].__setitem__("const", ["ignored"]),
        "full report empty errors")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["$defs"]["run"]["required"].remove("attempt_id_sha256"),
        "full report attempt binding")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["properties"]["bindings"]["required"].remove(
            "attempt_root_object_id_sha256"), "full report attempt-root binding")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["$defs"]["observations"]["required"].remove("privacy"),
        "full report observations")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["allOf"][2]["then"]["properties"]["artifacts"]["const"]
            .__setitem__("complete_bmp", "absent"), "full report UI artifact identity")
    reject_control_mutation("config/synthetic-launcher-report-full-v1.schema.json",
        lambda value: value["$defs"]["summary"]["oneOf"][2]["const"].__setitem__(
            "qualification_eligible", False), "full report summary")
    implementation = parse_canonical_json(captured[IMPLEMENTATION_PATH], "implementation config")
    assert isinstance(implementation, dict)
    for field, bad in (("process_creation_reachable", True),
            ("qualification_eligible", True), ("live_execution_status", "passed")):
        changed = json.loads(json.dumps(implementation))
        changed["contract_state"][field] = bad
        mutated = dict(captured)
        mutated[IMPLEMENTATION_PATH] = canonical(changed)
        mutated[IMPLEMENTATION_SCHEMA_PATH] = canonical({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "const": changed, "type": "object"})
        try:
            verify_control_data(mutated)
        except VerificationError:
            pass
        else:
            raise VerificationError("accepted implementation overclaim")
    print("PASS runtime-implementation-self-test")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("self-test")
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--repo", type=pathlib.Path, required=True)
    verify_parser.add_argument("--source-commit", required=True)
    return result


def main() -> int:
    arguments = parser().parse_args()
    try:
        if arguments.command == "self-test":
            self_test()
        else:
            result = verify(arguments.repo, arguments.source_commit)
            print(json.dumps({"files": {path: {"byte_count": value[0], "sha256": value[1]}
                for path, value in sorted(result.items())},
                "status": "runtime-implementation-verified"}, sort_keys=True,
                separators=(",", ":")))
        return 0
    except (VerificationError, OSError, ValueError, AssertionError) as error:
        print("FAIL " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
