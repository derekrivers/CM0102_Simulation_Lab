#!/usr/bin/env python3
"""Strict verifier for the authority-free build-unpinned binding policy."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import tempfile


SOURCE_PATH = "tools/windows/synthetic-launcher-controller/RuntimeBindingPolicy.cs"
TEST_PATH = "tools/windows/synthetic-launcher-controller/RuntimeBindingPolicyTests.cs"
README_PATH = "tools/windows/synthetic-launcher-controller/RUNTIME_BINDING.md"
PROFILE_PATH = "config/synthetic-launcher-controller-runtime-v1.json"
VERIFIER_PATH = "tools/windows/synthetic-launcher-controller/verify_runtime_binding_policy.py"
WORKFLOW_PATH = ".github/workflows/rust.yml"
CONTROLLER_DIRECTORY = "tools/windows/synthetic-launcher-controller"
MAX_BYTES = 256 * 1024
GIT = pathlib.Path("/usr/bin/git")
WORKFLOW_SHA_PLACEHOLDER = "RUNTIME_BINDING_VERIFIER_SHA256"
NORMALIZED_WORKFLOW_IDENTITY = (
    8426, "632dab3a69cf9a303f8f3f1d28f8c82251ec1bdaed7dec398d26a173bafa8bc7")

# Filled only with exact reviewed bytes. The verifier itself is commit-bound below.
FROZEN_IDENTITIES: dict[str, tuple[int, str]] = {
    SOURCE_PATH: (26943, "32d7890f04894956e5b72b055c8326947559e5d30f3108558420eea68ecebe6c"),
    TEST_PATH: (24400, "c726f5240a6ca0d4a9f7cce267ed25af64f1e2cc04784e67b8cf4b563710e8e5"),
    README_PATH: (3571, "416b96ccb4b6599936a4542a608c5346989b1b06ab8f6ae9b1c38bfaada0aa9f"),
    PROFILE_PATH: (5510, "0f4e98d7fe1c273e3c0b7cf342bae84bcc99a4a5ef16cf087a4fe99d3bb396d1"),
}
BOUND_PATHS = tuple(FROZEN_IDENTITIES) + (WORKFLOW_PATH, VERIFIER_PATH)
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


def open_directory_at(root_descriptor: int, relative: str) -> int:
    parts = pathlib.PurePosixPath(relative).parts
    if not parts or pathlib.PurePosixPath(relative).is_absolute() or any(
            part in ("", ".", "..") for part in parts):
        raise VerificationError("invalid descriptor-relative directory")
    current = os.dup(root_descriptor)
    try:
        for part in parts:
            following = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW |
                os.O_CLOEXEC, dir_fd=current)
            opened = os.fstat(following)
            if not stat.S_ISDIR(opened.st_mode):
                os.close(following)
                raise VerificationError("descriptor-relative component is not a directory")
            os.close(current)
            current = following
        return current
    except Exception:
        os.close(current)
        raise


def read_bound_at(root_descriptor: int, relative: str) -> bytes:
    pure = pathlib.PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(part in ("", ".", "..") for part in pure.parts):
        raise VerificationError("invalid descriptor-relative file")
    parent_relative = "/".join(pure.parts[:-1])
    parent = os.dup(root_descriptor) if not parent_relative else \
        open_directory_at(root_descriptor, parent_relative)
    try:
        name = pure.parts[-1]
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
            raise VerificationError("invalid descriptor-relative bound file " + relative)
        descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise VerificationError("descriptor-relative input changed type")
            raw = bytearray()
            while True:
                chunk = os.read(descriptor, min(65536, MAX_BYTES + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_BYTES:
                    raise VerificationError("descriptor-relative input exceeds byte limit")
            after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        finally:
            os.close(descriptor)
    finally:
        os.close(parent)
    fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if fields(before) != fields(opened) or fields(before) != fields(after) or len(raw) != before.st_size:
        raise VerificationError("descriptor-relative input changed during read")
    return bytes(raw)


def validate_execution_source(repo: pathlib.Path, expected_raw: bytes) -> None:
    executing = os.fspath(pathlib.Path(__file__).absolute())
    match = re.fullmatch(r"/proc/self/fd/([0-9]+)", executing)
    if match is None:
        raise VerificationError("verifier execution source")
    descriptor = int(match.group(1))
    observed = os.fstat(descriptor)
    required_seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | \
        fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
    if not stat.S_ISREG(observed.st_mode) or observed.st_size != len(expected_raw) or \
            fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != required_seals:
        raise VerificationError("verifier snapshot state")
    raw = bytearray()
    offset = 0
    while len(raw) <= MAX_BYTES:
        chunk = os.pread(descriptor, min(65536, MAX_BYTES + 1 - len(raw)), offset)
        if not chunk:
            break
        raw.extend(chunk)
        offset += len(chunk)
    if bytes(raw) != expected_raw:
        raise VerificationError("executing verifier snapshot identity")


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
        "Microsoft.Win32", "extern", "unsafe", "dynamic", "global::", "Environment.",
        "AppDomain.", "Activator.", "Marshal.", "IntPtr", "SafeHandle", "GCHandle",
        "File.", "Directory.", "Process.", "Registry.", "Socket.", "HttpClient",
        "DateTime", "Stopwatch", "Random(", "Guid.", "Type.GetType", ".GetMethod",
        ".Invoke", "typeof(", ".GetType", "ResourceManager", "Console.Open",
        "Console.Read", "Console.In", "Console.Set", "Console.Error", "delegate", "=>",
        "String.Concat", "Encoding.", "CodeDomProvider", "WindowsIdentity",
        "RandomNumberGenerator", "ResourceWriter", "RemotingConfiguration",
    )
    for value in forbidden:
        if tests and value in ("System.Threading", "delegate"):
            continue
        if value in compact:
            raise VerificationError(label + " forbidden token " + value)
    source_without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
    source_without_strings = re.sub(r"\s*\.\s*", ".", source_without_strings)
    observed_system_members = set(re.findall(
        r"\bSystem(?:\.[A-Za-z_][A-Za-z0-9_]*)+", source_without_strings))
    allowed_system_members = {"System.Threading.ManualResetEvent", "System.Threading.Thread",
        "System.Threading.ThreadStart"} if tests else set()
    if observed_system_members != allowed_system_members:
        raise VerificationError(label + " qualified System surface")
    if not tests and "Console." in compact:
        raise VerificationError(label + " console authority")
    if re.search(r"\b(?:CreateProcess\w*|ShellExecute\w*|WinExec)\(", compact):
        raise VerificationError(label + " native authority invocation")
    return compact, strings


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
        position = text.find(value, position + 1)
        if position < 0:
            raise VerificationError(label + " order " + value)


def require_count(text: str, value: str, expected: int, label: str) -> None:
    actual = text.count(value)
    if actual != expected:
        raise VerificationError(label + " count " + value + " " + str(actual))


def verify_policy(source: str, tests: str, readme: str, profile_raw: bytes, workflow: str,
        verifier_sha256: str) -> None:
    compact, strings = verify_authority_surface(source, "runtime binding policy", False)
    test_compact, _ = verify_authority_surface(tests, "runtime binding tests", True)
    if "Main(" in compact or len(re.findall(r"(?:private|internal|public)staticintMain\(\)", test_compact)) != 1:
        raise VerificationError("entrypoint surface")
    for forbidden in ("RuntimeBindingExpectations", "ControllerEngine", "ControllerPolicy",
            "AttemptState", "Permit", "IController", "ICommonControllerPort"):
        if forbidden in compact:
            raise VerificationError("forward policy surface " + forbidden)
    required_types = (
        "internalenumRuntimeImageRole", "internalenumRuntimeImageBindingState",
        "internalenumRuntimeBuildBinding",
        "internalenumDeclaredFixtureStatus", "internalstaticclassFixedRuntimeBindingContract",
        "internalsealedclassRuntimeArtifactIdentity", "internalsealedclassRuntimeContractFacts",
        "internalsealedclassRuntimeImageDeclarationFacts",
        "internalsealedclassRuntimeObjectBindingRequirementFacts",
        "internalsealedclassRuntimeRouteDeclarationFacts",
        "internalsealedclassRuntimeOuterJobDeclarationFacts",
        "internalsealedclassRuntimeBindingFacts", "internalsealedclassRuntimeBindingState",
        "internalstaticclassRuntimeBindingPolicy", "internalsealedclassBuildUnpinnedRefusal",
    )
    for value in required_types:
        require_count(compact, value, 1, "policy type")
    if compact.count("internalreadonly") != 71:
        raise VerificationError("immutable fact field count")
    readonly_fields = re.findall(r"internal\s+readonly\s+[A-Za-z0-9_.<>\[\]]+\s+([A-Z][A-Za-z0-9]+);",
        source)
    parameter_aliases = {"DeclaredBindingState": "bindingState", "DeclaredIdentity": "identity"}
    enum_assignment_names = {"Supervisor", "Controller", "LockedPreflight", "UiFixture",
        "TimeoutRoot", "TimeoutChild"}
    for field in set(readonly_fields):
        parameter = parameter_aliases.get(field, field[0].lower() + field[1:])
        expected_assignments = readonly_fields.count(field)
        exact_assignment = r"(?<![A-Za-z0-9_])" + re.escape(field) + "=" + \
            re.escape(parameter) + ";"
        any_assignment = r"(?<![A-Za-z0-9_])" + re.escape(field) + r"=(?!=)"
        total_expected = expected_assignments + (1 if field in enum_assignment_names else 0)
        if len(re.findall(exact_assignment, compact)) != expected_assignments or \
                len(re.findall(any_assignment, compact)) != total_expected:
            raise VerificationError("readonly constructor normalization " + field)
    expected_strings = (
        "cm0102-synthetic-launcher-controller-runtime-v1",
        "0f4e98d7fe1c273e3c0b7cf342bae84bcc99a4a5ef16cf087a4fe99d3bb396d1",
        "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6",
        "SyntheticLauncherController.public.v1.json",
        "SyntheticLauncherController.private.v1.json", "SyntheticLauncherReport.v1.json",
        "SyntheticLauncherSupervisor.exe", "SyntheticLauncherController.exe",
        "SyntheticLauncherLockedPreflight.exe", "SyntheticLauncherFixture.exe",
        "SyntheticLauncherTimeoutFixture.exe", "SyntheticLauncherTimeoutChild.exe",
        "ui-success-v1", "tree-timeout-v1", "locked-refusal-v1", "scenario", "key",
        "ui-success-v1", "tree-timeout-v1", "locked-refusal-v1",
        "ui-success-v1", "tree-timeout-v1", "locked-refusal-v1",
    )
    if tuple(strings) != expected_strings:
        raise VerificationError("fixed production literal sequence")
    exact_foundations = {
        "internalenumRuntimeImageRole":
            "Absent=0,Supervisor=1,Controller=2,LockedPreflight=3,UiFixture=4,TimeoutRoot=5,TimeoutChild=6",
        "internalenumRuntimeImageBindingState": "Unbound=1,BoundNotRun=2",
        "internalenumRuntimeBuildBinding": "BuildUnpinned=1,ImagesPinned=2",
        "internalenumDeclaredFixtureStatus":
            "NotRun=1,ExpectedTimeoutContained=2,Succeeded=3",
        "internalstaticclassFixedRuntimeBindingContract":
            "internalconststringProfileId=\"\";internalconstlongRuntimeProfileByteCount=5510;"
            "internalconststringRuntimeProfileSha256=\"\";internalconstlongUiFixtureByteCount=14336;"
            "internalconststringUiFixtureSha256=\"\";internalconstlongProcessMemoryLimitBytes=268435456;"
            "internalconststringPublicConfigurationName=\"\";"
            "internalconststringPrivateConfigurationName=\"\";internalconststringReportName=\"\";"
            "internalstaticstringNameFor(RuntimeImageRolerole){switch(role){"
            "caseRuntimeImageRole.Supervisor:return\"\";caseRuntimeImageRole.Controller:return\"\";"
            "caseRuntimeImageRole.LockedPreflight:return\"\";caseRuntimeImageRole.UiFixture:return\"\";"
            "caseRuntimeImageRole.TimeoutRoot:return\"\";caseRuntimeImageRole.TimeoutChild:return\"\";"
            "default:returnnull;}}internalstaticboolIsScenario(stringvalue){"
            "returnString.Equals(value,\"\",StringComparison.Ordinal)||"
            "String.Equals(value,\"\",StringComparison.Ordinal)||"
            "String.Equals(value,\"\",StringComparison.Ordinal);}",
    }
    for marker, expected_body in exact_foundations.items():
        if extract_block(compact, marker, marker) != expected_body:
            raise VerificationError("exact policy foundation " + marker)
    expected_bodies = {
        "internalstaticstringNameFor(RuntimeImageRolerole)":
            "switch(role){caseRuntimeImageRole.Supervisor:return\"\";caseRuntimeImageRole.Controller:return\"\";caseRuntimeImageRole.LockedPreflight:return\"\";caseRuntimeImageRole.UiFixture:return\"\";caseRuntimeImageRole.TimeoutRoot:return\"\";caseRuntimeImageRole.TimeoutChild:return\"\";default:returnnull;}",
        "internalstaticboolIsScenario(stringvalue)":
            "returnString.Equals(value,\"\",StringComparison.Ordinal)||String.Equals(value,\"\",StringComparison.Ordinal)||String.Equals(value,\"\",StringComparison.Ordinal);",
        "privatestaticboolExactContract(RuntimeContractFactsfacts)":
            "returnfacts!=null&&String.Equals(facts.ProfileId,FixedRuntimeBindingContract.ProfileId,StringComparison.Ordinal)&&ExactIdentity(facts.RuntimeProfile,FixedRuntimeBindingContract.RuntimeProfileByteCount,FixedRuntimeBindingContract.RuntimeProfileSha256)&&facts.BuildBinding==RuntimeBuildBinding.BuildUnpinned&&facts.PublicBuildManifestBindingUnbound&&facts.PublicBuildManifestBindingIdentity==null&&facts.LiveExecutionNotRun&&facts.ProcessCreationUnreachable&&facts.QualificationIneligible&&facts.OriginalExecutionNotRun&&facts.OriginalBehaviorUnqualified&&facts.NoImageExecutionObserved&&facts.NoObjectObservationAttempted&&facts.NoLiveJobObservationAttempted;",
        "privatestaticboolExactUnboundImage(RuntimeImageDeclarationFactsfacts,RuntimeImageRolerole)":
            "returnfacts!=null&&facts.Role==role&&String.Equals(facts.FixedName,FixedRuntimeBindingContract.NameFor(role),StringComparison.Ordinal)&&facts.DeclaredBindingState==RuntimeImageBindingState.Unbound&&facts.DeclaredIdentity==null;",
        "privatestaticboolExactUiFixture(RuntimeImageDeclarationFactsfacts)":
            "returnfacts!=null&&facts.Role==RuntimeImageRole.UiFixture&&String.Equals(facts.FixedName,FixedRuntimeBindingContract.NameFor(RuntimeImageRole.UiFixture),StringComparison.Ordinal)&&facts.DeclaredBindingState==RuntimeImageBindingState.BoundNotRun&&ExactIdentity(facts.DeclaredIdentity,FixedRuntimeBindingContract.UiFixtureByteCount,FixedRuntimeBindingContract.UiFixtureSha256);",
        "privatestaticboolExactObjectBindingRequirements(RuntimeObjectBindingRequirementFactsfacts)":
            "returnfacts!=null&&String.Equals(facts.PublicConfigurationName,FixedRuntimeBindingContract.PublicConfigurationName,StringComparison.Ordinal)&&String.Equals(facts.PrivateConfigurationName,FixedRuntimeBindingContract.PrivateConfigurationName,StringComparison.Ordinal)&&String.Equals(facts.ReportName,FixedRuntimeBindingContract.ReportName,StringComparison.Ordinal)&&facts.RequireHeldExactParent&&facts.RequireCanonicalFinalPaths&&facts.RequireObjectIds&&facts.RequireSameVolume&&facts.RequireRegularFiles&&facts.RequireAlternateMountRejection&&facts.RequirePairwiseDistinctObjects&&facts.RequireSingleLinkFiles&&facts.RequireNoReparsePoints&&facts.RequireNoAlternateDataStreams&&facts.RequireStableBeforeAfter&&facts.RequireRuntimeCopiesNotHardlinks&&facts.RequirePrivateConfigurationWithoutExecutablePath&&facts.RequireRebindBefore&&facts.RequireRebindAfter;",
        "privatestaticboolExactRoute(RuntimeRouteDeclarationFactsfacts,stringscenario,RuntimeImageRoleworker,RuntimeImageRoletarget,RuntimeImageRoledescendant,boolprocessCreation,DeclaredFixtureStatusfixtureStatus)":
            "returnfacts!=null&&String.Equals(facts.Scenario,scenario,StringComparison.Ordinal)&&facts.Worker==worker&&facts.PrimaryTarget==target&&facts.Descendant==descendant&&facts.WorkerProcessCreationCapabilityDeclared==processCreation&&facts.ExpectedFixtureStatus==fixtureStatus;",
        "privatestaticboolExactOuterJob(RuntimeOuterJobDeclarationFactsfacts,stringscenario,intactiveLimit,longjobMemory,boolnested)":
            "returnfacts!=null&&String.Equals(facts.Scenario,scenario,StringComparison.Ordinal)&&facts.ActiveProcessLimit==activeLimit&&facts.ProcessMemoryLimitBytes==FixedRuntimeBindingContract.ProcessMemoryLimitBytes&&facts.JobMemoryLimitBytes==jobMemory&&facts.RequireKillOnClose&&facts.RequireBreakawayForbidden&&facts.RequireNestedInnerJob==nested&&facts.RequireNonInheritableHandle&&facts.DeclareSupervisorNotMember&&facts.RequireUnnamedJob&&facts.RequireWorkerCreatedSuspended&&facts.RequireWorkerAssignedBeforeResume&&facts.RequireWorkerMembershipQuery&&facts.RequiredWorkerResumeCallCount==1;",
    }
    for marker, expected_body in expected_bodies.items():
        if extract_block(compact, marker, marker) != expected_body:
            raise VerificationError("exact policy predicate " + marker)
    if "PublicBuildManifestBindingUnbound&&facts.PublicBuildManifestBindingIdentity==null" not in compact or \
            "BuildBinding==RuntimeBuildBinding.BuildUnpinned" not in compact:
        raise VerificationError("build-unpinned manifest boundary")
    for value in (
        "LiveExecutionNotRun", "ProcessCreationUnreachable", "QualificationIneligible",
        "OriginalExecutionNotRun", "OriginalBehaviorUnqualified", "NoImageExecutionObserved",
        "NoObjectObservationAttempted", "NoLiveJobObservationAttempted",
    ):
        if ("facts." + value) not in compact:
            raise VerificationError("contract refusal field " + value)
    if "facts.LiveExecutionNotRun&&facts.ProcessCreationUnreachable&&facts.QualificationIneligible" not in compact:
        raise VerificationError("unreachable refusal conjunction")
    validate = extract_block(compact,
        "internalstaticBuildUnpinnedRefusalValidate(RuntimeBindingStatestate,RuntimeBindingFactsfacts)",
        "validate")
    require_order(validate, (
        "state!=null", "state.TryGetRefusalBinding(outscenario,outgeneration)",
        "stateReady&&facts!=null", "ExactContract(facts.Contract)",
        "ExactUnboundImage(facts.Supervisor", "ExactUnboundImage(facts.Controller",
        "ExactUnboundImage(facts.LockedPreflight", "ExactUiFixture(facts.UiFixture)",
        "ExactUnboundImage(facts.TimeoutRoot", "ExactUnboundImage(facts.TimeoutChild",
        "ExactObjectBindingRequirements(facts.ObjectBindingRequirements)",
        "ExactRoute(facts.UiRoute", "ExactRoute(facts.TimeoutRoute",
        "ExactRoute(facts.LockedRoute", "ExactOuterJob(facts.UiOuterJob",
        "ExactOuterJob(facts.TimeoutOuterJob", "ExactOuterJob(facts.LockedOuterJob",
        "newBuildUnpinnedRefusal(",
    ), "validation")
    expected_validate = 'stringscenario=null;intgeneration=-1;boolstateReady=state!=null&&state.TryGetRefusalBinding(outscenario,outgeneration);boolexact=stateReady&&facts!=null&&ExactContract(facts.Contract)&&ExactUnboundImage(facts.Supervisor,RuntimeImageRole.Supervisor)&&ExactUnboundImage(facts.Controller,RuntimeImageRole.Controller)&&ExactUnboundImage(facts.LockedPreflight,RuntimeImageRole.LockedPreflight)&&ExactUiFixture(facts.UiFixture)&&ExactUnboundImage(facts.TimeoutRoot,RuntimeImageRole.TimeoutRoot)&&ExactUnboundImage(facts.TimeoutChild,RuntimeImageRole.TimeoutChild)&&ExactObjectBindingRequirements(facts.ObjectBindingRequirements)&&ExactRoute(facts.UiRoute,"",RuntimeImageRole.Controller,RuntimeImageRole.UiFixture,RuntimeImageRole.Absent,true,DeclaredFixtureStatus.Succeeded)&&ExactRoute(facts.TimeoutRoute,"",RuntimeImageRole.Controller,RuntimeImageRole.TimeoutRoot,RuntimeImageRole.TimeoutChild,true,DeclaredFixtureStatus.ExpectedTimeoutContained)&&ExactRoute(facts.LockedRoute,"",RuntimeImageRole.LockedPreflight,RuntimeImageRole.Absent,RuntimeImageRole.Absent,false,DeclaredFixtureStatus.NotRun)&&ExactOuterJob(facts.UiOuterJob,"",2,536870912,true)&&ExactOuterJob(facts.TimeoutOuterJob,"",3,805306368,true)&&ExactOuterJob(facts.LockedOuterJob,"",1,268435456,false);returnexact?newBuildUnpinnedRefusal(state,scenario,generation,FixedRuntimeBindingContract.ProfileId,FixedRuntimeBindingContract.RuntimeProfileByteCount,FixedRuntimeBindingContract.RuntimeProfileSha256,RefusalKey):null;'
    if validate != expected_validate:
        raise VerificationError("exact validation route")
    refusal = extract_block(compact, "internalsealedclassBuildUnpinnedRefusal", "refusal")
    for value in ("owner", "scenario", "generation", "profileId", "profileByteCount",
            "profileSha256", "consumed"):
        if value not in refusal:
            raise VerificationError("refusal binding " + value)
    accept = extract_block(compact,
        "internalboolAcceptRefusal(RuntimeBindingPolicy.BuildUnpinnedRefusalrefusal)",
        "refusal acceptance")
    require_order(accept, ("lock(sync)", "terminal||rejected", "refusal==null", "refusal.Consume(",
        "rejected=true", "terminal=true", "ineligible=true", "unreachable=true"),
        "refusal acceptance")
    expected_accept = 'lock(sync){if(terminal||rejected)returnfalse;if(refusal==null||!refusal.Consume(this,scenario,generation,FixedRuntimeBindingContract.ProfileId,FixedRuntimeBindingContract.RuntimeProfileByteCount,FixedRuntimeBindingContract.RuntimeProfileSha256)){rejected=true;generation++;returnfalse;}terminal=true;ineligible=true;unreachable=true;generation++;returntrue;}'
    if accept != expected_accept:
        raise VerificationError("exact refusal acceptance")
    consume = extract_block(compact,
        "internalboolConsume(RuntimeBindingStatecandidateOwner,stringcandidateScenario",
        "refusal consumption")
    require_order(consume, ("lock(sync)", "consumed||", "consumed=true", "returntrue"),
        "refusal consumption")
    expected_consume = 'lock(sync){if(consumed||!Object.ReferenceEquals(owner,candidateOwner)||!String.Equals(scenario,candidateScenario,StringComparison.Ordinal)||generation!=candidateGeneration||!String.Equals(profileId,candidateProfileId,StringComparison.Ordinal)||profileByteCount!=candidateProfileByteCount||!String.Equals(profileSha256,candidateProfileSha256,StringComparison.Ordinal))returnfalse;consumed=true;returntrue;}'
    if consume != expected_consume:
        raise VerificationError("exact refusal consumption")
    snapshot = extract_block(compact,
        "internalboolTryGetRefusalBinding(outstringboundScenario,outintboundGeneration)",
        "refusal snapshot")
    if snapshot != 'lock(sync){boundScenario=scenario;boundGeneration=generation;return!terminal&&!rejected;}':
        raise VerificationError("exact refusal snapshot")
    assert_body = extract_block(test_compact, "privatestaticvoidAssert(boolvalue)", "assertion")
    if assert_body != 'assertions++;if(!value)thrownewInvalidOperationException(""+assertions.ToString());':
        raise VerificationError("test assertion body")
    if test_compact.count("Console.") != 1 or \
            test_compact.count('Console.WriteLine(""+assertions.ToString())') != 1:
        raise VerificationError("test console surface")
    main_body = extract_block(test_compact, "privatestaticintMain()", "test main")
    require_order(main_body, ("AcceptanceCases();", "ContractMutationCases();",
        "ImageMutationCases();", "RouteMutationCases();", "OuterJobMutationCases();",
        "ObjectBindingRequirementMutationCases();", "TopLevelNullCases();",
        "RefusalOwnershipCases();", "ConcurrentRefusalCase();", "if(assertions!=202)",
        "Console.WriteLine("), "test main")
    for value in ("for(intmutation=1;mutation<=17;mutation++)",
            "for(intimage=0;image<6;image++)", "for(introute=0;route<3;route++)",
            "for(intjob=0;job<3;job++)", "for(intmutation=1;mutation<=21;mutation++)",
            "for(intmutation=0;mutation<14;mutation++)", "AcceptRefusal(null)",
            "System.Threading.ManualResetEvent", "ThreadStart(delegate",
            "firstAccepted!=secondAccepted", "PASS "):
        if value not in test_compact and value not in tests:
            raise VerificationError("missing negative test " + value)
    if identity(profile_raw) != (5510,
            "0f4e98d7fe1c273e3c0b7cf342bae84bcc99a4a5ef16cf087a4fe99d3bb396d1"):
        raise VerificationError("runtime profile identity")
    profile = json.loads(profile_raw.decode("ascii", "strict"))
    expected_state = {"build_binding": "build-unpinned", "live_execution_status": "not-run",
        "original_behavior_qualified": False, "original_execution_status": "not-run",
        "process_creation_reachable": False, "qualification_eligible": False}
    if profile.get("contract_state") != expected_state:
        raise VerificationError("runtime profile refusal state")
    expected_status = {"controller_image": "unbound", "locked_preflight_image": "unbound",
        "retained_run_harness": "absent", "runtime_implementation_verifier": "absent",
        "runtime_private_schema": "absent", "supervisor_image": "unbound",
        "timeout_child_image": "unbound", "timeout_root_image": "unbound",
        "ui_fixture_image": "bound-not-run"}
    if profile.get("status") != expected_status:
        raise VerificationError("runtime profile image status")
    expected_names = {"controller": "SyntheticLauncherController.exe",
        "locked_preflight": "SyntheticLauncherLockedPreflight.exe",
        "private_configuration": "SyntheticLauncherController.private.v1.json",
        "public_runtime_configuration": "SyntheticLauncherController.public.v1.json",
        "report": "SyntheticLauncherReport.v1.json",
        "supervisor": "SyntheticLauncherSupervisor.exe",
        "timeout_child": "SyntheticLauncherTimeoutChild.exe",
        "timeout_root": "SyntheticLauncherTimeoutFixture.exe",
        "ui_fixture": "SyntheticLauncherFixture.exe"}
    expected_routes = {
        "locked-refusal-v1": {"descendant": "absent",
            "expected_fixture_execution_status": "not-run", "primary_target": "absent",
            "worker": "locked_preflight", "worker_process_creation_capability": False},
        "tree-timeout-v1": {"descendant": "timeout_child",
            "expected_fixture_execution_status": "expected-timeout-contained",
            "primary_target": "timeout_root", "worker": "controller",
            "worker_process_creation_capability": True},
        "ui-success-v1": {"descendant": "absent",
            "expected_fixture_execution_status": "succeeded", "primary_target": "ui_fixture",
            "worker": "controller", "worker_process_creation_capability": True},
    }
    expected_outer_job = {"active_process_limit_by_scenario": {
            "locked-refusal-v1": 1, "tree-timeout-v1": 3, "ui-success-v1": 2},
        "assign_worker_before_resume": True, "breakaway_forbidden": True,
        "job_memory_limit_bytes_by_scenario": {"locked-refusal-v1": 268435456,
            "tree-timeout-v1": 805306368, "ui-success-v1": 536870912},
        "kill_on_close": True, "nested_inner_job_required_for": [
            "tree-timeout-v1", "ui-success-v1"], "non_inheritable_handle": True,
        "process_memory_limit_bytes": 268435456, "supervisor_is_member": False,
        "unnamed": True, "worker_created_suspended": True,
        "worker_membership_queried": True, "worker_resume_call_count": 1}
    if profile.get("fixed_names") != expected_names or \
            profile.get("scenario_images") != expected_routes or \
            profile.get("outer_job") != expected_outer_job:
        raise VerificationError("runtime profile fixed binding declarations")
    if profile.get("accepted_inputs", {}).get("ui_fixture") != {
            "byte_count": 14336,
            "sha256": "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6"}:
        raise VerificationError("runtime profile UI fixture identity")
    normalized_readme = re.sub(r"\s+", " ", readme).lower()
    for phrase in ("build-unpinned refusal", "caller supplies no expected values",
            "public build-manifest binding is unbound", "makes no claim that compiled files are absent",
            "object-binding requirements", "regular files", "alternate-mount rejection",
            "returns only a `BuildUnpinnedRefusal`", "not a forward permit", "PASS 202",
            "must not execute"):
        if phrase.lower() not in normalized_readme:
            raise VerificationError("README boundary " + phrase)
    if workflow.count(verifier_sha256) != 1:
        raise VerificationError("workflow verifier digest binding")
    normalized_workflow = workflow.replace(verifier_sha256, WORKFLOW_SHA_PLACEHOLDER)
    if identity(normalized_workflow.encode("ascii", "strict")) != NORMALIZED_WORKFLOW_IDENTITY:
        raise VerificationError("normalized workflow identity")
    for value in ("run_bound_runtime_verifier self-test",
            "run_bound_runtime_verifier verify", "/usr/bin/python3 -I -B -c",
            "os.O_NOFOLLOW", "os.memfd_create", "fcntl.F_ADD_SEALS", "fcntl.F_SEAL_WRITE",
            '"/proc/self/fd/"+str(snapshot)', 'os.execve("/usr/bin/python3"',
            "RuntimeBindingPolicyTests.exe",
            "/main:Cm0102.SyntheticLauncherController.RuntimeBindingPolicyTests",
            "PASS 202", "WaitForExit(30000)"):
        if value not in workflow:
            raise VerificationError("workflow binding gate " + value)


def run_git(repo: pathlib.Path, arguments: list[str]) -> bytes:
    environment = {
        "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null",
        "GIT_CONFIG_KEY_1": "extensions.objectFormat", "GIT_CONFIG_VALUE_1": "sha1",
        "LC_ALL": "C",
    }
    completed = subprocess.run([os.fspath(GIT), "--no-replace-objects",
        "-c", "protocol.file.allow=never", "-c", "core.fsmonitor=false", *arguments],
        cwd=repo, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=20, check=False)
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


def verify_inventory(repo: pathlib.Path, commit: str, root_descriptor: int) -> None:
    prefix = CONTROLLER_DIRECTORY + "/"
    committed = run_git(repo, ["ls-tree", "-r", "--name-only", commit, "--",
        CONTROLLER_DIRECTORY]).decode("ascii", "strict").splitlines()
    expected = [prefix + name for name in EXPECTED_CONTROLLER_FILES]
    if committed != sorted(expected):
        raise VerificationError("controller commit inventory")
    controller_descriptor = open_directory_at(root_descriptor, CONTROLLER_DIRECTORY)
    try:
        readable_descriptor = os.open(".", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
            os.O_CLOEXEC, dir_fd=controller_descriptor)
        try:
            observed = os.listdir(readable_descriptor)
            for name in observed:
                value = os.stat(name, dir_fd=readable_descriptor, follow_symlinks=False)
                if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
                    raise VerificationError("controller filesystem inventory type")
        finally:
            os.close(readable_descriptor)
    finally:
        os.close(controller_descriptor)
    if sorted(observed) != sorted(EXPECTED_CONTROLLER_FILES):
        raise VerificationError("controller filesystem inventory")


def verify(repo_argument: pathlib.Path, commit: str) -> dict[str, tuple[int, str]]:
    if not GIT.is_file() or not repo_argument.is_absolute() or \
            repo_argument.resolve(strict=True) != repo_argument:
        raise VerificationError("repository path")
    repo = repo_argument
    require_path_components(repo)
    root_descriptor = os.open(repo, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        root_identity = os.fstat(root_descriptor)
        lexical_root = os.stat(repo, follow_symlinks=False)
        root_fields = lambda value: (value.st_dev, value.st_ino, value.st_mode,
            value.st_uid, value.st_gid)
        if root_fields(root_identity) != root_fields(lexical_root):
            raise VerificationError("repository descriptor identity")
        if pathlib.Path(run_git(repo, ["rev-parse", "--show-toplevel"]).decode().strip()) != repo:
            raise VerificationError("repository is not canonical top level")
        validate_commit(repo, commit)
        verify_inventory(repo, commit, root_descriptor)
        captured: dict[str, bytes] = {}
        identities: dict[str, tuple[int, str]] = {}
        for relative in BOUND_PATHS:
            raw = read_bound_at(root_descriptor, relative)
            if relative in FROZEN_IDENTITIES and identity(raw) != FROZEN_IDENTITIES[relative]:
                raise VerificationError(relative + " frozen identity")
            if raw != run_git(repo, ["show", commit + ":" + relative]):
                raise VerificationError(relative + " differs from source commit")
            captured[relative] = raw
            identities[relative] = identity(raw)
        validate_execution_source(repo, captured[VERIFIER_PATH])
        verify_policy(decode_source(captured[SOURCE_PATH], "runtime binding policy"),
            decode_source(captured[TEST_PATH], "runtime binding tests"),
            captured[README_PATH].decode("ascii", "strict"), captured[PROFILE_PATH],
            captured[WORKFLOW_PATH].decode("ascii", "strict"), identity(captured[VERIFIER_PATH])[1])
        for relative, original in captured.items():
            if read_bound_at(root_descriptor, relative) != original:
                raise VerificationError(relative + " changed across aggregate verification")
        verify_inventory(repo, commit, root_descriptor)
        validate_commit(repo, commit)
        if root_fields(root_identity) != root_fields(os.stat(repo, follow_symlinks=False)):
            raise VerificationError("repository root replaced during verification")
        return identities
    finally:
        os.close(root_descriptor)


def self_test() -> None:
    repo = pathlib.Path.cwd().resolve(strict=True)
    if pathlib.Path(run_git(repo, ["rev-parse", "--show-toplevel"]).decode().strip()) != repo:
        raise VerificationError("self-test repository root")
    source = decode_source(read_bound(repo / SOURCE_PATH), "runtime binding policy")
    tests = decode_source(read_bound(repo / TEST_PATH), "runtime binding tests")
    readme = read_bound(repo / README_PATH).decode("ascii", "strict")
    profile = read_bound(repo / PROFILE_PATH)
    workflow_raw = read_bound(repo / WORKFLOW_PATH)
    verifier_raw = read_bound(repo / VERIFIER_PATH)
    validate_execution_source(repo, verifier_raw)
    verifier_sha256 = identity(verifier_raw)[1]
    workflow = workflow_raw.decode("ascii", "strict")
    verify_policy(source, tests, readme, profile, workflow, verifier_sha256)
    for mutation in (
        "System.IO.File.ReadAllText(\"x\")", "System.Diagnostics.Process.Start(\"x\")",
        "[DllImport(\"x\")] extern static void X();", "unsafe { }", "dynamic value",
        "System.Reflection.Assembly.Load(\"x\")", "DateTime.UtcNow", "delegate { }",
        "Func<int> value = () => 1", "Console.OpenStandardInput()",
        "System.Security.Principal.WindowsIdentity.GetCurrent()",
        "new System.Resources.ResourceWriter(\"x\")",
        "System.Runtime.Remoting.RemotingConfiguration.Configure(\"x\",false)",
        "System . Diagnostics . Process . Start(\"x\")",
    ):
        try:
            verify_authority_surface("using System;\n" + mutation + ";\n", "mutation", False)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted authority mutation")
    disabled_assert = tests.replace(
        'if (!value) throw new InvalidOperationException("assertion-failed-" + assertions.ToString());',
        "if (!value) assertions++;")
    try:
        verify_policy(source, disabled_assert, readme, profile, workflow, verifier_sha256)
    except VerificationError:
        pass
    else:
        raise AssertionError("accepted disabled assertion")
    for old, new in (
        ("BuildUnpinnedRefusal", "Permit"),
        ("facts.PublicBuildManifestBindingIdentity == null",
            "facts.PublicBuildManifestBindingIdentity != null"),
        ("facts.LiveExecutionNotRun && facts.ProcessCreationUnreachable",
            "facts.LiveExecutionNotRun && !facts.ProcessCreationUnreachable"),
        ("RuntimeProfileByteCount = 5510", "RuntimeProfileByteCount = 1"),
        ("UiFixtureByteCount = 14336", "UiFixtureByteCount = 1"),
        ("ProcessMemoryLimitBytes = 268435456", "ProcessMemoryLimitBytes = 1"),
        ("Supervisor = 1", "Supervisor = 9"),
    ):
        changed = source.replace(old, new, 1)
        try:
            verify_policy(changed, tests, readme, profile, workflow, verifier_sha256)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted policy weakening")
    synchronized = (
        (source.replace("ExactOuterJob(facts.UiOuterJob, \"ui-success-v1\", 2, 536870912, true)",
            "ExactOuterJob(facts.UiOuterJob, \"ui-success-v1\", 2, 536870913, true)"),
         tests.replace("index == 0 ? 536870912", "index == 0 ? 536870913")),
        (source.replace("facts.RequireNoReparsePoints &&",
            "!facts.RequireNoReparsePoints &&"),
         tests.replace("bool noReparse = true;", "bool noReparse = false;")),
        (source.replace("RequireNoReparsePoints = requireNoReparsePoints;",
            "RequireNoReparsePoints = requireNoReparsePoints;\n"
            "            RequireNoReparsePoints = true;"),
         tests.replace("bool noReparse = true;", "bool noReparse = false;")),
        (source.replace(
            'case RuntimeImageRole.Supervisor: return "SyntheticLauncherSupervisor.exe";',
            'case RuntimeImageRole.Controller: return "SyntheticLauncherSupervisor.exe";', 1).replace(
            'case RuntimeImageRole.Controller: return "SyntheticLauncherController.exe";',
            'case RuntimeImageRole.Supervisor: return "SyntheticLauncherController.exe";', 1), tests),
        (source.replace("StringComparison.Ordinal) ||",
            "StringComparison.OrdinalIgnoreCase) ||", 1), tests),
    )
    for changed_source, changed_tests in synchronized:
        try:
            verify_policy(changed_source, changed_tests, readme, profile, workflow,
                verifier_sha256)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted synchronized semantic weakening")
    console_mutation = tests.replace('Console.WriteLine("PASS " + assertions.ToString());',
        'Console.Title = Console.Title; Console.WriteLine("PASS " + assertions.ToString());')
    try:
        verify_policy(source, console_mutation, readme, profile, workflow, verifier_sha256)
    except VerificationError:
        pass
    else:
        raise AssertionError("accepted ambient console authority")
    workflow_mutations = (
        workflow.replace("env:\n", "env:\n  BASH_ENV: ci-shadow.sh\n", 1),
        workflow.replace("          $policy $tests\n", "          $policy ControllerEngine.cs $tests\n", 1),
        workflow + "\n  execute-fixture:\n    runs-on: windows-latest\n"
            "    steps:\n    - run: SyntheticLauncherFixture.exe\n",
        workflow.replace("    - name: Build and run authority-free x86 runtime binding tests\n",
            "    # - name: Build and run authority-free x86 runtime binding tests\n", 1),
    )
    for changed_workflow in workflow_mutations:
        try:
            verify_policy(source, tests, readme, profile, changed_workflow, verifier_sha256)
        except VerificationError:
            pass
        else:
            raise AssertionError("accepted disabled workflow gate")
    with tempfile.TemporaryDirectory() as directory:
        replacement_repo = pathlib.Path(directory)
        git_environment = {"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "LC_ALL": "C"}
        def control_git(arguments: list[str]) -> bytes:
            completed = subprocess.run([os.fspath(GIT), *arguments], cwd=replacement_repo,
                env=git_environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=10, check=False)
            if completed.returncode != 0:
                raise AssertionError("replacement control setup")
            return completed.stdout
        control_git(["init", "--quiet"])
        control_git(["config", "user.name", "runtime-binding-self-test"])
        control_git(["config", "user.email", "runtime-binding-self-test.invalid"])
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
    except (VerificationError, AssertionError, OSError, subprocess.SubprocessError,
            json.JSONDecodeError) as error:
        print("FAIL " + str(error))
        return 1
    if result is None:
        print("PASS runtime-binding-self-test")
    else:
        print(json.dumps({"files": {key: {"byte_count": value[0], "sha256": value[1]}
            for key, value in sorted(result.items())}, "status": "runtime-binding-verified"},
            sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
