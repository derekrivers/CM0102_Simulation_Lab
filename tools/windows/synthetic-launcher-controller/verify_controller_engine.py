#!/usr/bin/env python3
"""Strict verifier for the authority-free controller-engine increment."""

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


POLICY_PATH = "tools/windows/synthetic-launcher-controller/ControllerPolicy.cs"
ENGINE_PATH = "tools/windows/synthetic-launcher-controller/ControllerEngine.cs"
TEST_PATH = "tools/windows/synthetic-launcher-controller/ControllerEngineTests.cs"
README_PATH = "tools/windows/synthetic-launcher-controller/ENGINE.md"
VERIFIER_PATH = "tools/windows/synthetic-launcher-controller/verify_controller_engine.py"
WORKFLOW_PATH = ".github/workflows/rust.yml"
MAX_BYTES = 256 * 1024
GIT = pathlib.Path("/usr/bin/git")

FROZEN_IDENTITIES = {
    POLICY_PATH: (41856, "0bd6e9590a31f64326706377a0789ad9fef5b715815898d074bb73bd3dec329d"),
    ENGINE_PATH: (25413, "33d5d643f086c1bb057310d6368e8712b096e1165cd07946e11744426089082b"),
    TEST_PATH: (36652, "ee2517e0d77199aba4a7ee2c2870594bce745d1e3240ab925316f9fbd27df316"),
    README_PATH: (2718, "c3671bc8dfeb2c50afea0b219d211698eb4d2c9fb09340a07fba578c016ccba0"),
    WORKFLOW_PATH: (8602, "9d2a6ad409bd111d3a9bc16f85ec931fe0f4d2216d60ad5ab4db0e35615fc6ab"),
}
BOUND_PATHS = tuple(FROZEN_IDENTITIES) + (VERIFIER_PATH,)
CONTROLLER_DIRECTORY = "tools/windows/synthetic-launcher-controller"
EXPECTED_CONTROLLER_FILES = (
    "ControllerEngine.cs", "ControllerEngineTests.cs", "ControllerPolicy.cs",
    "ControllerPolicyTests.cs", "ENGINE.md", "README.md", "RUNTIME_BINDING.md",
    "RUNTIME_CONTRACT.md", "RuntimeBindingPolicy.cs", "RuntimeBindingPolicyTests.cs",
    "verify_controller_engine.py", "verify_controller_policy.py",
    "verify_controller_runtime_contract.py", "verify_runtime_binding_policy.py",
)


class VerificationError(Exception):
    pass


def identity(raw: bytes) -> tuple[int, str]:
    return len(raw), hashlib.sha256(raw).hexdigest()


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
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
        raise VerificationError("invalid bound file " + os.fspath(path))
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise VerificationError("bound input changed type")
        raw = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, MAX_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                raise VerificationError("input exceeds byte limit")
        after = os.stat(path, follow_symlinks=False)
    finally:
        os.close(descriptor)
    fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if fields(before) != fields(opened) or fields(before) != fields(after) or len(raw) != before.st_size:
        raise VerificationError("input changed during read")
    return bytes(raw)


def decode_source(raw: bytes, label: str) -> str:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or b"\0" in raw or not raw.endswith(b"\n"):
        raise VerificationError(label + " encoding")
    try:
        text = raw.decode("ascii", "strict")
    except UnicodeDecodeError as error:
        raise VerificationError(label + " non-ASCII source") from error
    if any(marker in text for marker in ("//", "/*", "*/")) or re.search(r"(?m)^\s*#", text):
        raise VerificationError(label + " comments or directives")
    if re.search(r"\\(?:u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|x[0-9A-Fa-f]{1,4})", text):
        raise VerificationError(label + " escaped identifier")
    if re.search(r'(?:@|\$)"', text):
        raise VerificationError(label + " unsupported string form")
    return text


def compact_code(text: str, label: str) -> tuple[str, list[str]]:
    strings: list[str] = []

    def replace(match: re.Match[str]) -> str:
        value = match.group(0)[1:-1]
        if "\\" in value:
            raise VerificationError(label + " escaped string")
        strings.append(value)
        return '""'

    without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', replace, text)
    if "@" in without_strings:
        raise VerificationError(label + " verbatim identifier")
    return re.sub(r"\s+", "", without_strings), strings


def verify_authority_surface(text: str, label: str, tests: bool) -> tuple[str, list[str]]:
    if re.findall(r"(?m)^using\s+[^;]+;", text) != ["using System;"]:
        raise VerificationError(label + " using surface")
    compact, strings = compact_code(text, label)
    forbidden = (
        "DllImport", "LibraryImport", "Runtime.InteropServices", "System.IO",
        "System.Diagnostics", "System.Net", "System.Reflection", "System.Threading",
        "System.Security", "System.Timers", "System.CodeDom", "System.ComponentModel",
        "System.Media", "System.Configuration", "System.Activities", "Microsoft.CSharp",
        "WindowsIdentity", "RandomNumberGenerator", "CodeDomProvider",
        "Microsoft.Win32", "extern", "unsafe", "dynamic", "global::", "Environment.",
        "AppDomain.", "Activator.", "Marshal.", "IntPtr", "SafeHandle", "GCHandle",
        "File.", "Directory.", "Process.Start", "Registry.", "Socket.", "HttpClient",
        "DateTime", "Stopwatch", "Random(", "Guid.", "Type.GetType", ".GetMethod",
        ".Invoke", "typeof(", ".GetType", "ResourceManager", "Console.Open",
        "Console.Read", "Console.In", "Console.Set", "Console.Error", "delegate", "=>",
        "String.Concat", "newstring(", "Encoding.", "char",
    )
    for value in forbidden:
        if tests and value == "System.Threading":
            continue
        if value in compact:
            raise VerificationError(label + " forbidden token " + value)
    allowed_system_members = {
        "System.Threading.ManualResetEvent", "System.Threading.Thread",
        "System.Threading.ThreadStart",
    } if tests else set()
    source_without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
    source_without_strings = re.sub(r"\s*\.\s*", ".", source_without_strings)
    observed_system_members = set(re.findall(
        r"\bSystem(?:\.[A-Za-z_][A-Za-z0-9_]*)+", source_without_strings))
    if observed_system_members != allowed_system_members:
        raise VerificationError(label + " System member surface")
    if not tests and "Console." in compact:
        raise VerificationError(label + " console authority")
    if re.search(r"\b(?:CreateProcess\w*|ShellExecute\w*|WinExec)\(", compact):
        raise VerificationError(label + " native authority invocation")
    return compact, strings


def require_count(text: str, value: str, expected: int, label: str) -> None:
    actual = text.count(value)
    if actual != expected:
        raise VerificationError(label + " count " + value + " " + str(actual))


def extract_block(text: str, marker: str, label: str) -> str:
    marker_index = text.find(marker)
    if marker_index < 0:
        raise VerificationError(label + " marker")
    opening = text.find("{", marker_index + len(marker))
    if opening < 0:
        raise VerificationError(label + " opening brace")
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index]
    raise VerificationError(label + " closing brace")


def require_order(text: str, values: tuple[str, ...], label: str) -> None:
    position = -1
    for value in values:
        next_position = text.find(value, position + 1)
        if next_position < 0:
            raise VerificationError(label + " order " + value)
        position = next_position


def verify_engine(engine: str, tests: str, readme: str, workflow: str) -> None:
    compact, strings = verify_authority_surface(engine, "engine", False)
    test_compact, test_strings = verify_authority_surface(tests, "tests", True)
    if "Main(" in compact or require_main_count(test_compact) != 1:
        raise VerificationError("entrypoint surface")
    expected_interfaces = (
        "IControllerRecoveryPort", "ICommonControllerPort", "IUiControllerPort",
        "ITimeoutControllerPort", "ILockedPreflightPort",
    )
    declared = re.findall(r"internalinterface(I[A-Za-z0-9]+)", compact)
    if tuple(declared) != expected_interfaces:
        raise VerificationError("interface surface")
    for literal in ("ui-success-v1", "tree-timeout-v1", "locked-refusal-v1"):
        if strings.count(literal) != 1:
            raise VerificationError("fixed engine scenario " + literal)
    allowed_strings = {"ui-success-v1", "tree-timeout-v1", "locked-refusal-v1"}
    if set(strings) != allowed_strings:
        raise VerificationError("engine free-form string")
    required_types = (
        "internalsealedclassUiControllerEngine", "internalsealedclassTimeoutControllerEngine",
        "internalsealedclassLockedPreflightEngine", "internalabstractclassControllerEngineBase",
        "internalabstractclassCommonControllerEngine",
    )
    for value in required_types:
        require_count(compact, value, 1, "engine type")
    policy_counts = {
        "ControllerPolicy.Binding(": 2, "ControllerPolicy.Preflight(": 2,
        "ControllerPolicy.TokenRelationship(": 1, "ControllerPolicy.LaunchToken(": 1,
        "ControllerPolicy.Registry(": 1, "ControllerPolicy.Guards(": 1,
        "ControllerPolicy.Environment(": 1, "ControllerPolicy.ApproveCreate(": 1,
        "ControllerPolicy.RecordSuspendedChild(": 1, "ControllerPolicy.JobBeforeResume(": 1,
        "ControllerPolicy.PreResume(": 1, "ControllerPolicy.Resume(": 1,
        "ControllerPolicy.Window(": 1, "ControllerPolicy.ReadyCaptureOne(": 1,
        "ControllerPolicy.ReadyCaptureTwo(": 1, "ControllerPolicy.InputGuards(": 1,
        "ControllerPolicy.SendInput(": 1, "ControllerPolicy.CompleteCaptureOne(": 1,
        "ControllerPolicy.CompleteCaptureTwo(": 1, "ControllerPolicy.CleanupUi(": 1,
        "ControllerPolicy.CleanupTimeout(": 1, "ControllerPolicy.CleanupLocked(": 1,
        "ControllerPolicy.Abort(": 1, "ControllerPolicy.CleanupAbort(": 1,
        "ControllerPolicy.Rebind(": 4,
    }
    for value, expected in policy_counts.items():
        require_count(compact, value, expected, "policy route")
    base_class = extract_block(compact, "internalabstractclassControllerEngineBase", "base class")
    common_class = extract_block(compact, "internalabstractclassCommonControllerEngine", "common class")
    ui_class = extract_block(compact, "internalsealedclassUiControllerEngine", "UI class")
    timeout_class = extract_block(compact, "internalsealedclassTimeoutControllerEngine", "timeout class")
    locked_class = extract_block(compact, "internalsealedclassLockedPreflightEngine", "locked class")
    common_route = extract_block(common_class, "protectedboolRunCommonRoute()", "common route")
    require_order(common_route, (
        "ControllerPolicy.Binding(", "ControllerPolicy.Preflight(",
        "ControllerPolicy.TokenRelationship(", "ControllerPolicy.LaunchToken(",
        "ControllerPolicy.Registry(", "ControllerPolicy.Guards(",
        "ControllerPolicy.Environment(", "ControllerPolicy.ApproveCreate(",
        "ControllerPolicy.RecordSuspendedChild(", "ControllerPolicy.JobBeforeResume(",
        "ControllerPolicy.PreResume(", "ControllerPolicy.Resume("), "common route")
    ui_run = extract_block(ui_class, "internalControllerEngineResultRun()", "UI run")
    require_order(ui_run, ("StartRun()", "RunCommonRoute()", "ControllerPolicy.Window(",
        "ControllerPolicy.ReadyCaptureOne(", "ControllerPolicy.ReadyCaptureTwo(",
        "ControllerPolicy.InputGuards(", "ControllerPolicy.SendInput(",
        "ControllerPolicy.CompleteCaptureOne(", "ControllerPolicy.CompleteCaptureTwo(",
        "ControllerPolicy.CleanupUi(", "ControllerPolicy.Rebind(",
        "Complete(AttemptTerminal.UiComplete)"), "UI run")
    timeout_run = extract_block(timeout_class, "internalControllerEngineResultRun()", "timeout run")
    require_order(timeout_run, ("StartRun()", "RunCommonRoute()",
        "ControllerPolicy.CleanupTimeout(", "ControllerPolicy.Rebind(",
        "Complete(AttemptTerminal.ExpectedTimeout)"), "timeout run")
    locked_run = extract_block(locked_class, "internalControllerEngineResultRun()", "locked run")
    require_order(locked_run, ("StartRun()", "ControllerPolicy.Binding(",
        "ControllerPolicy.Preflight(", "ControllerPolicy.CleanupLocked(",
        "ControllerPolicy.Rebind(", "Complete(AttemptTerminal.LockedRefusal)"), "locked run")
    abort_body = extract_block(base_class, "protectedControllerEngineResultAbort()", "abort")
    require_order(abort_body, ("DiscardUnexpectedPixelsBeforeAbort()", "ControllerPolicy.Abort(",
        "State.BeginAbort(", "CollectAbortCleanupFacts()", "ControllerPolicy.CleanupAbort(",
        "State.Advance(cleanupPermit)", "RebindAfterAbort()", "ControllerPolicy.Rebind(",
        "State.Advance(rebindPermit)", "State.Complete(AttemptTerminal.Ineligible)"), "abort")
    for value in (
        "DiscardAndZeroFixedUnexpectedPixels()",
        "RestoreFixedRegistryImpersonationIfActive()",
        "ReleaseFixedEnvironmentIfAllocated()",
        "RestoreFixedPrivilegeIfChanged()", "TerminateFixedChildAndJobIfCreated()",
        "VerifyFixedJobEmptyIfCreated()", "CloseFixedHandles()", "VerifyFixedGuardsStable()",
        "VerifyZeroFixedFixtureProcesses()", "VerifyZeroFixedGameProcesses()",
    ):
        require_count(compact, value, 2, "recovery declaration and call")
    recovery_order = (
        "boolpixelsDiscarded=DiscardUnexpectedPixelsBeforeAbort();",
        "ControllerPolicy.Abort(",
        "AbortCleanupFactscleanupFacts=CollectAbortCleanupFacts();",
        "ControllerPolicy.CleanupAbort(", "RebindFactsrebindFacts=RebindAfterAbort();",
        "State.Complete(AttemptTerminal.Ineligible)",
    )
    require_order(abort_body, recovery_order, "recovery")
    common_recovery_order = (
        "boolregistry=RestoreRegistryImpersonation();",
        "boolenvironment=ReleaseEnvironment();", "boolprivilege=RestorePrivilege();",
        "booltermination=TerminateChildAndJob();", "boolempty=VerifyJobEmpty();",
        "boolhandles=CloseHandles();", "boolguards=VerifyGuards();",
        "boolfixtureProcesses=VerifyFixtureProcesses();",
        "boolgameProcesses=VerifyGameProcesses();", "returnnewAbortCleanupFacts",
    )
    common_cleanup = extract_block(common_class,
        "protectedoverrideAbortCleanupFactsCollectAbortCleanupFacts()", "common cleanup")
    require_order(common_cleanup, common_recovery_order, "common recovery")
    locked_start = compact.find("internalinterfaceILockedPreflightPort")
    locked_end = compact.find("internalenumControllerRoute", locked_start)
    locked_surface = compact[locked_start:locked_end]
    for forbidden_locked in ("TokenRelationship", "LaunchToken", "RegistryFacts",
            "EnvironmentFacts", "CreateApprovalFacts", "SuspendedChildFacts", "ResumeFacts",
            "WindowFacts", "CaptureFacts", "InputGuardFacts", "SendInputFacts", "Terminate"):
        if forbidden_locked in locked_surface:
            raise VerificationError("locked port authority " + forbidden_locked)
    if "privatereadonlyobjectrunGate=newobject();" not in compact or \
            "lock(runGate){if(runStarted)returnfalse;runStarted=true;State=AttemptState.Start(scenario);" not in compact:
        raise VerificationError("one-run guard")
    if "ControllerFailureCategory.CleanupFailure" not in compact or \
            "ControllerFailureCategory.ReentrantRun" not in compact:
        raise VerificationError("fixed failure categories")
    assert_body = extract_block(test_compact, "privatestaticvoidAssert(boolvalue)", "test assertion")
    if assert_body != 'assertions++;if(!value)thrownewInvalidOperationException(""+assertions.ToString());':
        raise VerificationError("test assertion body")
    main_body = extract_block(test_compact, "privatestaticintMain()", "test main")
    require_order(main_body, ("SuccessCase(", "FailureCases(", "RejectedFactsCases(",
        "PermitOneUseCase();", "AbortFailureCases();", "AcquireThenThrowCases();",
        "ReentrantRunCase();", "ConcurrentRunCase();", "Console.WriteLine("), "test main")
    for required in (
        "FailureCases(", "RejectedFactsCases(", "AbortFailureCases()", "ReentrantRunCase()",
        "AcquireThenThrowCases()", "FailAfterAcquisition=true", "Acquired(stage)",
        "ConcurrentRunCase()", "secondFinishedBeforeRelease", "ThreadStart(runner.RunFirst)",
        "for(intindex=0;index<10;index++)", "ExactRecoveryCalls(1)",
        "ControllerFailureCategory.CleanupFailure", "ControllerFailureCategory.ReentrantRun",
        "OriginalExecutionAttempts==0", 'Console.WriteLine(""+assertions.ToString())',
    ):
        if required not in test_compact:
            raise VerificationError("missing engine test " + required)
    if not any("secret" in value.lower() for value in test_strings) or \
            any("secret" in value.lower() for value in strings):
        raise VerificationError("secret-exception test boundary")
    for required in (
        "build-unpinned scaffolding", "no native adapter may be", "PASS 1235",
        "no production image", "original executable",
    ):
        if required.lower() not in readme.lower():
            raise VerificationError("engine README boundary " + required)
    for required in (
        "verify_controller_engine.py self-test", "ControllerEngineTests.exe",
        "/main:Cm0102.SyntheticLauncherController.ControllerEngineTests", "PASS 1235",
    ):
        if required not in workflow:
            raise VerificationError("workflow engine gate " + required)


def require_main_count(compact: str) -> int:
    return len(re.findall(r"(?:private|internal|public)staticintMain\(\)", compact))


def run_git(repo: pathlib.Path, arguments: list[str]) -> bytes:
    environment = {
        "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": "/dev/null", "GIT_CONFIG_KEY_1": "extensions.objectFormat",
        "GIT_CONFIG_VALUE_1": "sha1", "LC_ALL": "C",
    }
    completed = subprocess.run([os.fspath(GIT), "--no-replace-objects",
        "-c", "protocol.file.allow=never",
        "-c", "core.fsmonitor=false", *arguments], cwd=repo, env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=20, check=False)
    if completed.returncode != 0 or completed.stderr or len(completed.stdout) > MAX_BYTES:
        raise VerificationError("Git command failed")
    return completed.stdout


def validate_commit(repo: pathlib.Path, commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise VerificationError("source commit is not a full lowercase hash")
    if run_git(repo, ["cat-file", "-t", commit]) != b"commit\n":
        raise VerificationError("source object is not a commit")
    resolved = run_git(repo, ["rev-parse", "--verify", commit + "^{commit}"]).decode().strip()
    head = run_git(repo, ["rev-parse", "--verify", "HEAD^{commit}"]).decode().strip()
    if resolved != commit or head != commit:
        raise VerificationError("source commit is not exact HEAD")


def verify_inventory(repo: pathlib.Path, commit: str) -> None:
    prefix = CONTROLLER_DIRECTORY + "/"
    committed = run_git(repo, ["ls-tree", "-r", "--name-only", commit, "--",
        CONTROLLER_DIRECTORY]).decode("ascii", "strict").splitlines()
    expected = [prefix + name for name in EXPECTED_CONTROLLER_FILES]
    if committed != sorted(expected):
        raise VerificationError("controller commit inventory")
    directory = repo / CONTROLLER_DIRECTORY
    require_path_components(directory)
    observed = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                raise VerificationError("controller filesystem inventory type")
            observed.append(entry.name)
    if sorted(observed) != sorted(EXPECTED_CONTROLLER_FILES):
        raise VerificationError("controller filesystem inventory")


def verify(repo_argument: pathlib.Path, commit: str) -> dict[str, tuple[int, str]]:
    if not GIT.is_file() or not repo_argument.is_absolute() or \
            repo_argument.resolve(strict=True) != repo_argument:
        raise VerificationError("repository path")
    repo = repo_argument
    require_path_components(repo)
    if pathlib.Path(run_git(repo, ["rev-parse", "--show-toplevel"]).decode().strip()) != repo:
        raise VerificationError("repository is not canonical top level")
    if pathlib.Path(__file__).absolute() != repo / VERIFIER_PATH:
        raise VerificationError("verifier is not executing from canonical path")
    validate_commit(repo, commit)
    verify_inventory(repo, commit)
    captured: dict[str, bytes] = {}
    identities: dict[str, tuple[int, str]] = {}
    for relative in BOUND_PATHS:
        raw = read_bound(repo / relative)
        if relative in FROZEN_IDENTITIES and identity(raw) != FROZEN_IDENTITIES[relative]:
            raise VerificationError(relative + " frozen identity")
        if raw != run_git(repo, ["show", commit + ":" + relative]):
            raise VerificationError(relative + " differs from source commit")
        captured[relative] = raw
        identities[relative] = identity(raw)
    engine = decode_source(captured[ENGINE_PATH], "engine")
    tests = decode_source(captured[TEST_PATH], "tests")
    readme = captured[README_PATH].decode("ascii", "strict")
    workflow = captured[WORKFLOW_PATH].decode("ascii", "strict")
    verify_engine(engine, tests, readme, workflow)
    for relative, original in captured.items():
        if read_bound(repo / relative) != original:
            raise VerificationError(relative + " changed across aggregate verification")
    verify_inventory(repo, commit)
    validate_commit(repo, commit)
    return identities


def self_test() -> None:
    repo = pathlib.Path(__file__).parents[3]
    if pathlib.Path(__file__).absolute() != repo / VERIFIER_PATH:
        raise VerificationError("verifier is not executing from canonical path")
    engine = decode_source(read_bound(repo / ENGINE_PATH), "engine")
    tests = decode_source(read_bound(repo / TEST_PATH), "tests")
    readme = read_bound(repo / README_PATH).decode("ascii", "strict")
    workflow = read_bound(repo / WORKFLOW_PATH).decode("ascii", "strict")
    workflow_raw = read_bound(repo / WORKFLOW_PATH)
    if identity(workflow_raw) != FROZEN_IDENTITIES[WORKFLOW_PATH]:
        raise AssertionError("workflow frozen identity")
    verify_engine(engine, tests, readme, workflow)
    mutations = (
        "System.IO.File.ReadAllText(\"x\")", "System.Diagnostics.Process.Start(\"x\")",
        "[DllImport(\"x\")] extern static void X();", "unsafe { }", "dynamic value",
        "System.Reflection.Assembly.Load(\"x\")", "DateTime.UtcNow", "delegate { }",
        "Func<int> value = () => 1", "Console.OpenStandardInput()",
        "System.Security.Principal.WindowsIdentity.GetCurrent()",
        "System.Security.Cryptography.RandomNumberGenerator.Create()",
        "new System.Timers.Timer()",
        "System.CodeDom.Compiler.CodeDomProvider.CreateProvider(\"x\")",
        "new string(new char[] { (char)80 })",
        "new System.Resources.ResourceWriter(\"x\")",
        "System.Runtime.Remoting.RemotingConfiguration.Configure(\"x\",false)",
        "new System.Text.StringBuilder()",
    )
    for mutation in mutations:
        try:
            verify_authority_surface("using System;\n" + mutation + ";\n", "mutation", False)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted authority mutation")
    for mutation in (
        "System.Threading.ThreadPool.GetAvailableThreads(out worker,out completion)",
        "System.Threading.ManualResetEventSlim value",
        "System . Threading . ThreadPool value",
        "System . Threading . ManualResetEventSlim value",
        "System . Threading . ThreadStateException value",
    ):
        try:
            verify_authority_surface("using System;\n" + mutation + ";\n",
                "test mutation", True)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted test System member mutation")
    for mutation in (
        "new System . Resources . ResourceWriter(path)",
        "System . Runtime . Remoting . RemotingConfiguration . Configure(path,false)",
    ):
        try:
            verify_authority_surface("using System;\n" + mutation + ";\n",
                "spaced mutation", False)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted spaced System member mutation")
    disabled_assert = tests.replace(
        'if (!value) throw new InvalidOperationException("assertion-failed-" + assertions.ToString());',
        "if (!value) assertions++;")
    try:
        verify_engine(engine, disabled_assert, readme, workflow)
    except VerificationError:
        pass
    else:
        raise AssertionError("accepted disabled assertion")
    relocated_policy = engine.replace("ControllerPolicy.Window(State, Scenario,",
        "ControllerPolicy.DisabledWindow(State, Scenario,", 1) + "\nControllerPolicy.Window(\n"
    try:
        verify_engine(relocated_policy, tests, readme, workflow)
    except VerificationError:
        pass
    else:
        raise AssertionError("accepted relocated policy call")
    for suffix in (b"\nif: false\n", b"\ncontinue-on-error: true\n", b"\nexit 0\n"):
        if identity(workflow_raw + suffix) == FROZEN_IDENTITIES[WORKFLOW_PATH]:
            raise AssertionError("accepted workflow mutation")
    with tempfile.TemporaryDirectory() as directory:
        replacement_repo = pathlib.Path(directory)
        git_environment = {
            "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "LC_ALL": "C",
        }
        def control_git(arguments: list[str]) -> bytes:
            completed = subprocess.run([os.fspath(GIT), *arguments], cwd=replacement_repo,
                env=git_environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=10, check=False)
            if completed.returncode != 0:
                raise AssertionError("replacement control setup")
            return completed.stdout
        control_git(["init", "--quiet"])
        control_git(["config", "user.name", "controller-engine-self-test"])
        control_git(["config", "user.email", "controller-engine-self-test.invalid"])
        marker = replacement_repo / "marker"
        marker.write_text("first\n", encoding="ascii")
        control_git(["add", "marker"])
        control_git(["commit", "--quiet", "-m", "first"])
        first = control_git(["rev-parse", "HEAD"]).decode("ascii").strip()
        marker.write_text("replacement\n", encoding="ascii")
        control_git(["commit", "--quiet", "-am", "replacement"])
        replacement = control_git(["rev-parse", "HEAD"]).decode("ascii").strip()
        control_git(["replace", first, replacement])
        if control_git(["show", first + ":marker"]) != b"replacement\n":
            raise AssertionError("replacement control inactive")
        if run_git(replacement_repo, ["show", first + ":marker"]) != b"first\n":
            raise AssertionError("replacement object affected bound Git read")
    with tempfile.TemporaryDirectory() as directory:
        copied = pathlib.Path(directory) / pathlib.Path(__file__).name
        copied.write_bytes(pathlib.Path(__file__).read_bytes())
        completed = subprocess.run(["/usr/bin/python3", os.fspath(copied), "self-test"],
            cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=10, check=False)
        if completed.returncode == 0:
            raise AssertionError("copied verifier executed successfully")


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("self-test")
    check = modes.add_parser("verify")
    check.add_argument("--repo", required=True, type=pathlib.Path)
    check.add_argument("--source-commit", required=True)
    arguments = parser.parse_args()
    try:
        if arguments.mode == "self-test":
            self_test()
            result = None
        else:
            result = verify(arguments.repo, arguments.source_commit)
    except (VerificationError, AssertionError, OSError, subprocess.SubprocessError) as error:
        print("FAIL " + str(error))
        return 1
    if result is None:
        print("PASS controller-engine-self-test")
    else:
        print(json.dumps({"files": {key: {"byte_count": value[0], "sha256": value[1]}
            for key, value in sorted(result.items())}, "status": "controller-engine-verified"},
            sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
