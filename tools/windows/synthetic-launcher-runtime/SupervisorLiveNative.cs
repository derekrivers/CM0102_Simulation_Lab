using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal enum SupervisorWorkerRole
    {
        Controller = 1,
        LockedPreflight = 2
    }

    internal sealed class SupervisorRouteFacts
    {
        internal SupervisorRouteFacts(SupervisorWorkerRole role, string imageName,
            uint activeProcessLimit, ulong jobMemoryLimit, int expectedExit)
        {
            Role = role;
            ImageName = imageName;
            ActiveProcessLimit = activeProcessLimit;
            JobMemoryLimit = jobMemoryLimit;
            ExpectedExit = expectedExit;
        }
        internal readonly SupervisorWorkerRole Role;
        internal readonly string ImageName;
        internal readonly uint ActiveProcessLimit;
        internal readonly ulong JobMemoryLimit;
        internal readonly int ExpectedExit;
    }

    internal sealed class SupervisorLiveNative : IRuntimeSupervisorScenarioPort
    {
        private const uint CREATE_SUSPENDED = 0x00000004;
        private const uint CreateNoWindow = 0x08000000;
        private const uint CreateUnicodeEnvironment = 0x00000400;
        private const uint JobObjectExtendedLimitInformationClass = 9;
        private const uint JobObjectBasicAccountingInformation = 1;
        private const uint JobObjectBasicProcessIdListInformation = 3;
        private const uint LimitActiveProcess = 0x00000008;
        private const uint LimitProcessMemory = 0x00000100;
        private const uint LimitJobMemory = 0x00000200;
        private const uint LimitKillOnJobClose = 0x00002000;
        private const uint WaitObject0 = 0;
        private const uint WaitTimeout = 258;
        private const uint WorkerWaitMilliseconds = 120000;
        private const uint EmptyWaitMilliseconds = 5000;
        private const ulong ProcessMemoryLimit = 268435456;
        private readonly RuntimeLeaseUse lease;
        private readonly SupervisorBootstrapSnapshot snapshot;
        private readonly string sourceRevision;
        private readonly RuntimeScenarioPlan plan;
        private readonly SupervisorRouteFacts route;
        private long attemptStart;
        private long attemptFrequency;
        private long attemptDeadline;
        private IntPtr launchBinding = new IntPtr(-1);
        private IntPtr job = IntPtr.Zero;
        private ProcessInformation process = new ProcessInformation();
        private bool cleanupProofRequired;
        private bool created;
        private bool resumed;
        private bool assigned;
        private bool membership;
        private bool terminated;
        private bool empty;
        private bool streamsByConstruction;
        private int completedStageCount;
        private bool cleanupCalled;
        private IntPtr evidence = new IntPtr(-1);
        private byte[] workerEvidence;
        private ByHandleFileInformation evidenceIdentity;
        private IntPtr readyBmpHandle = new IntPtr(-1);
        private IntPtr completeBmpHandle = new IntPtr(-1);
        private byte[] readyBmp;
        private byte[] completeBmp;

        internal SupervisorLiveNative(RuntimeLeaseUse consumedLease,
            SupervisorBootstrapSnapshot boundSnapshot, string boundSourceRevision,
            RuntimeScenarioPlan boundPlan)
        {
            if (consumedLease == null)
                throw new ArgumentNullException("consumedLease");
            if (boundSnapshot == null)
                throw new ArgumentNullException("boundSnapshot");
            if (!RuntimeIdentity.IsLowerHexNonZero(boundSourceRevision, 40))
                throw new ArgumentException("sourceRevision");
            if (boundPlan == null || boundPlan.Role != RuntimeScenarioRole.Supervisor ||
                    !String.Equals(boundPlan.ScenarioId, consumedLease.ScenarioId,
                        StringComparison.Ordinal))
                throw new ArgumentException("boundPlan");
            lease = consumedLease;
            snapshot = boundSnapshot;
            sourceRevision = boundSourceRevision;
            plan = boundPlan;
            SupervisorWorkerRole workerRole = String.Equals(boundPlan.WorkerImage,
                RuntimeCanonicalData.LockedPreflightImage, StringComparison.Ordinal) ?
                SupervisorWorkerRole.LockedPreflight : SupervisorWorkerRole.Controller;
            route = new SupervisorRouteFacts(workerRole, boundPlan.WorkerImage,
                boundPlan.OuterActiveProcessLimit, boundPlan.OuterJobMemoryLimit,
                boundPlan.WorkerExitCode);
        }

        public RuntimeScenarioRole Role { get { return RuntimeScenarioRole.Supervisor; } }

        public RuntimeScenarioStepResult Execute(RuntimeScenarioStage stage)
        {
            if (cleanupCalled || completedStageCount >= plan.StageCount ||
                    plan.StageAt(completedStageCount) != stage)
                return Failed(RuntimeCanonicalData.ExitBindingRejection);
            RuntimeScenarioStepResult result = ExecuteExpectedStage(stage);
            if (result != null && result.Succeeded) completedStageCount++;
            return result;
        }

        private RuntimeScenarioStepResult ExecuteExpectedStage(RuntimeScenarioStage stage)
        {
            if (stage != RuntimeScenarioStage.BindInputs &&
                    RemainingToDeadline(attemptStart, attemptDeadline) == 0)
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            switch (stage)
            {
                case RuntimeScenarioStage.BindInputs:
                    if (!QueryPerformanceFrequency(out attemptFrequency) ||
                            attemptFrequency <= 0 || !QueryPerformanceCounter(out attemptStart) ||
                            !RuntimeDeadlineMath.TryCreateDeadline(attemptStart,
                                attemptFrequency, WorkerWaitMilliseconds,
                                out attemptDeadline))
                        return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
                    if (!snapshot.Objects.ContainsKey(route.ImageName) || !RebindAllInputs())
                        return Failed(RuntimeCanonicalData.ExitBindingRejection);
                    cleanupProofRequired = true;
                    launchBinding = OpenRelative(route.ImageName,
                        0x0001 | 0x0080 | 0x00020000 | 0x00100000, 1);
                    if (launchBinding == new IntPtr(-1) || !ExactBoundObject(launchBinding,
                            snapshot.Objects[route.ImageName]))
                        return Failed(RuntimeCanonicalData.ExitBindingRejection);
                    return Passed();
                case RuntimeScenarioStage.OutputsAbsent:
                    return Result(RelativeNameAbsent("SyntheticLauncherWorkerEvidence.v1.json") &&
                        RelativeNameAbsent("SyntheticLauncherReport.v1.json") &&
                        RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName) &&
                        RelativeNameAbsent(RuntimeCanonicalData.CompleteBmpName),
                        RuntimeCanonicalData.ExitBindingRejection);
                case RuntimeScenarioStage.AttemptInventory:
                    return Result(ExactAttemptInventory(false, false),
                        RuntimeCanonicalData.ExitBindingRejection);
                case RuntimeScenarioStage.PrelaunchTopology:
                    return Result(ExactGuardedNamesBeforeLaunch(),
                        RuntimeCanonicalData.ExitBindingRejection);
                case RuntimeScenarioStage.SupervisorJobConfigured:
                    job = CreateJobObjectW(IntPtr.Zero, null);
                    return Result(job != IntPtr.Zero && ConfigureJob(job,
                        route.ActiveProcessLimit, route.JobMemoryLimit),
                        RuntimeCanonicalData.ExitNativeCapabilityFailure);
                case RuntimeScenarioStage.SupervisorCreate:
                    StartupInfo startup = new StartupInfo();
                    startup.Size = Marshal.SizeOf(typeof(StartupInfo));
                    streamsByConstruction = startup.Flags == 0 &&
                        startup.StandardInput == IntPtr.Zero &&
                        startup.StandardOutput == IntPtr.Zero &&
                        startup.StandardError == IntPtr.Zero;
                    if (!streamsByConstruction)
                        return Failed(RuntimeCanonicalData.ExitBindingRejection);
                    string application = snapshot.ParentFinalPath + "\\" + route.ImageName;
                    created = CreateProcessW(application, null, IntPtr.Zero, IntPtr.Zero, false,
                        CREATE_SUSPENDED | CreateUnicodeEnvironment | CreateNoWindow,
                        IntPtr.Zero, snapshot.ParentFinalPath, ref startup, out process);
                    return Result(created, RuntimeCanonicalData.ExitNativeCapabilityFailure);
                case RuntimeScenarioStage.SupervisorAssign:
                    assigned = AssignProcessToJobObject(job, process.Process);
                    return Result(assigned, RuntimeCanonicalData.ExitNativeCapabilityFailure);
                case RuntimeScenarioStage.SupervisorMembership:
                    return Result(IsProcessInJob(process.Process, job, out membership) &&
                        membership && ExactJobProcessId(job, process.ProcessId),
                        RuntimeCanonicalData.ExitNativeCapabilityFailure);
                case RuntimeScenarioStage.WorkerTopology:
                    return Result(ExactWorkerTopology(route, process.ProcessId),
                        RuntimeCanonicalData.ExitBindingRejection);
                case RuntimeScenarioStage.SupervisorResume:
                    resumed = ResumeThread(process.Thread) != 0xffffffff;
                    return Result(resumed, RuntimeCanonicalData.ExitNativeCapabilityFailure);
                case RuntimeScenarioStage.SupervisorWait:
                    return WaitForWorker();
                case RuntimeScenarioStage.OuterJobEmpty:
                    long emptyStart;
                    long emptyDeadline;
                    empty = TryBoundedDeadline(EmptyWaitMilliseconds, 0,
                        out emptyStart, out emptyDeadline) && WaitForEmptyUntil(job,
                            emptyStart, attemptFrequency, emptyDeadline);
                    return Result(empty, RuntimeCanonicalData.ExitCleanupFailure);
                case RuntimeScenarioStage.SupervisorPostTopology:
                    if (!ExactGuardedNamesBeforeLaunch() ||
                            RemainingToDeadline(attemptStart, attemptDeadline) == 0)
                        return Failed(RuntimeCanonicalData.ExitCleanupFailure);
                    return Result(RebindAllInputs() &&
                        RemainingToDeadline(attemptStart, attemptDeadline) != 0,
                        RuntimeCanonicalData.ExitCleanupFailure);
                case RuntimeScenarioStage.EvidenceValidate:
                    return ValidateWorkerEvidence();
                case RuntimeScenarioStage.ReportPublish:
                    return PublishAndValidateReport();
                case RuntimeScenarioStage.EvidenceDeleteInventory:
                    return DeleteEvidenceAndValidateInventory();
                default:
                    return Failed(RuntimeCanonicalData.ExitBindingRejection);
            }
        }

        public RuntimeScenarioStepResult Cleanup()
        {
            if (cleanupCalled)
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            cleanupCalled = true;
            bool cleanupSucceeded = true;
            if (evidence != new IntPtr(-1))
            {
                CloseHandle(evidence);
                evidence = new IntPtr(-1);
            }
            if (readyBmpHandle != new IntPtr(-1)) CloseHandle(readyBmpHandle);
            if (completeBmpHandle != new IntPtr(-1)) CloseHandle(completeBmpHandle);
            if (readyBmp != null) Array.Clear(readyBmp, 0, readyBmp.Length);
            if (completeBmp != null) Array.Clear(completeBmp, 0, completeBmp.Length);
            if (created && process.Process != IntPtr.Zero)
            {
                bool processExited = WaitForSingleObject(process.Process, 0) == WaitObject0;
                bool jobEmpty = !assigned || JobIsEmptyNow(job);
                if (!processExited || !jobEmpty)
                {
                    long cleanupStart;
                    long cleanupDeadline;
                    bool clockStarted = TryBoundedDeadline(EmptyWaitMilliseconds, 0,
                        out cleanupStart, out cleanupDeadline);
                    bool stopped = assigned ? TerminateJobObject(job,
                        RuntimeCanonicalData.ExitCleanupFailure) : TerminateProcess(
                            process.Process, RuntimeCanonicalData.ExitCleanupFailure);
                    uint processWait = clockStarted ? RemainingToDeadline(cleanupStart,
                        cleanupDeadline) : 0;
                    processExited = stopped && processWait != 0 &&
                        WaitForSingleObject(process.Process, processWait) == WaitObject0;
                    jobEmpty = !assigned || (clockStarted && WaitForEmptyUntil(job,
                        cleanupStart, attemptFrequency, cleanupDeadline));
                    cleanupSucceeded = processExited && jobEmpty;
                }
            }
            if (cleanupProofRequired)
            {
                if (RemainingToDeadline(attemptStart, attemptDeadline) == 0 ||
                        !ExactGuardedNamesBeforeLaunch() ||
                        RemainingToDeadline(attemptStart, attemptDeadline) == 0 ||
                        !RebindAllInputs() ||
                        RemainingToDeadline(attemptStart, attemptDeadline) == 0)
                    cleanupSucceeded = false;
            }
            if (process.Thread != IntPtr.Zero) CloseHandle(process.Thread);
            if (process.Process != IntPtr.Zero) CloseHandle(process.Process);
            if (job != IntPtr.Zero) CloseHandle(job);
            if (launchBinding != new IntPtr(-1)) CloseHandle(launchBinding);
            GC.KeepAlive(lease);
            GC.KeepAlive(plan);
            return cleanupSucceeded ? Passed() :
                Failed(RuntimeCanonicalData.ExitCleanupFailure);
        }

        private RuntimeScenarioStepResult WaitForWorker()
        {
            long workerStart;
            long workerDeadline;
            if (!TryBoundedDeadline(WorkerWaitMilliseconds, EmptyWaitMilliseconds,
                    out workerStart, out workerDeadline))
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            uint workerWait = RemainingToDeadline(workerStart, workerDeadline);
            if (workerWait == 0) return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            uint wait = WaitForSingleObject(process.Process, workerWait);
            if (wait == WaitTimeout)
            {
                long cleanupStart;
                long cleanupDeadline;
                bool clockStarted = TryBoundedDeadline(EmptyWaitMilliseconds, 0,
                    out cleanupStart, out cleanupDeadline);
                uint cleanupWait = clockStarted ? RemainingToDeadline(cleanupStart,
                    cleanupDeadline) : 0;
                terminated = TerminateJobObject(job, RuntimeCanonicalData.ExitCleanupFailure);
                if (!terminated || cleanupWait == 0 || WaitForSingleObject(process.Process,
                        cleanupWait) != WaitObject0)
                    return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            }
            else if (wait != WaitObject0)
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            uint exitCode;
            return Result(GetExitCodeProcess(process.Process, out exitCode) &&
                exitCode == (uint)route.ExpectedExit,
                RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult ValidateWorkerEvidence()
        {
            long evidenceStart;
            long evidenceDeadline;
            if (!TryBoundedDeadline(5000, 0, out evidenceStart, out evidenceDeadline))
                return Failed(RuntimeCanonicalData.ExitReportFailure);
            bool ui = String.Equals(lease.ScenarioId, RuntimeCanonicalData.UiSuccessScenario,
                StringComparison.Ordinal);
            if (ui)
            {
                byte[] expectedReady = RuntimeCanonicalData.BuildExpectedCanonicalBmp(true);
                byte[] expectedComplete = RuntimeCanonicalData.BuildExpectedCanonicalBmp(false);
                bool artifactsExact = WaitOpenAndRead(RuntimeCanonicalData.ReadyBmpName,
                        RuntimeCanonicalData.CanonicalBmpByteCount, evidenceStart,
                        evidenceDeadline, out readyBmpHandle, out readyBmp) &&
                    WaitOpenAndRead(RuntimeCanonicalData.CompleteBmpName,
                        RuntimeCanonicalData.CanonicalBmpByteCount, evidenceStart,
                        evidenceDeadline, out completeBmpHandle, out completeBmp) &&
                    RuntimeCanonicalData.IsApprovedCanonicalBmp(readyBmp, true) &&
                    RuntimeCanonicalData.IsApprovedCanonicalBmp(completeBmp, false) &&
                    EqualBytes(readyBmp, expectedReady) &&
                    EqualBytes(completeBmp, expectedComplete);
                if (expectedReady != null) Array.Clear(expectedReady, 0, expectedReady.Length);
                if (expectedComplete != null)
                    Array.Clear(expectedComplete, 0, expectedComplete.Length);
                if (!artifactsExact)
                    return Failed(RuntimeCanonicalData.ExitReportFailure);
            }
            else if (!RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName) ||
                    !RelativeNameAbsent(RuntimeCanonicalData.CompleteBmpName))
                return Failed(RuntimeCanonicalData.ExitReportFailure);
            if (!WaitOpenAndRead("SyntheticLauncherWorkerEvidence.v1.json", 262144,
                    evidenceStart, evidenceDeadline,
                    out evidence, out workerEvidence))
                return Failed(RuntimeCanonicalData.ExitReportFailure);
            if (!GetFileInformationByHandle(evidence, out evidenceIdentity))
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            return Result(EqualBytes(workerEvidence, ExpectedWorkerEvidence(route)) &&
                    RemainingToDeadline(attemptStart, attemptDeadline) != 0,
                RuntimeCanonicalData.ExitReportFailure);
        }

        private RuntimeScenarioStepResult PublishAndValidateReport()
        {
            byte[] report = ComposeReport(route, created, assigned, membership,
                resumed, terminated, empty, streamsByConstruction);
            if (RemainingToDeadline(attemptStart, attemptDeadline) == 0 ||
                    !PublishCreateNew("SyntheticLauncherReport.v1.json", report) ||
                    RemainingToDeadline(attemptStart, attemptDeadline) == 0)
                return Failed(RuntimeCanonicalData.ExitReportFailure);
            IntPtr retainedReport;
            byte[] retainedBytes;
            long reportStart;
            long reportDeadline;
            if (!TryBoundedDeadline(5000, 0, out reportStart, out reportDeadline) ||
                    !WaitOpenAndRead("SyntheticLauncherReport.v1.json", 262144,
                        reportStart, reportDeadline, out retainedReport, out retainedBytes))
                return Failed(RuntimeCanonicalData.ExitReportFailure);
            try
            {
                return Result(EqualBytes(report, retainedBytes) &&
                        RemainingToDeadline(attemptStart, attemptDeadline) != 0,
                    RuntimeCanonicalData.ExitReportFailure);
            }
            finally { CloseHandle(retainedReport); }
        }

        private RuntimeScenarioStepResult DeleteEvidenceAndValidateInventory()
        {
            if (RemainingToDeadline(attemptStart, attemptDeadline) == 0 ||
                    evidence == new IntPtr(-1) || !DeleteHeldObject(evidence))
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            CloseHandle(evidence);
            evidence = new IntPtr(-1);
            if (RemainingToDeadline(attemptStart, attemptDeadline) == 0 ||
                    !RelativeNameAbsent("SyntheticLauncherWorkerEvidence.v1.json") ||
                    !FileIdentityAbsent(evidenceIdentity) ||
                    !ExactAttemptInventory(true, false) ||
                    RemainingToDeadline(attemptStart, attemptDeadline) == 0)
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            return Passed();
        }

        private static RuntimeScenarioStepResult Result(bool value, int exitCode)
        {
            return value ? Passed() : Failed(exitCode);
        }

        private static RuntimeScenarioStepResult Passed()
        {
            return RuntimeScenarioStepResult.Passed();
        }

        private static RuntimeScenarioStepResult Failed(int exitCode)
        {
            return RuntimeScenarioStepResult.Failed(exitCode);
        }

        private static bool ConfigureJob(IntPtr job, uint activeLimit, ulong jobMemory)
        {
            JobObjectExtendedLimitInformation information =
                new JobObjectExtendedLimitInformation();
            information.BasicLimitInformation.LimitFlags = LimitActiveProcess |
                LimitProcessMemory | LimitJobMemory | LimitKillOnJobClose;
            information.BasicLimitInformation.ActiveProcessLimit = activeLimit;
            information.ProcessMemoryLimit = new UIntPtr(ProcessMemoryLimit);
            information.JobMemoryLimit = new UIntPtr(jobMemory);
            int size = Marshal.SizeOf(typeof(JobObjectExtendedLimitInformation));
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try
            {
                Marshal.StructureToPtr(information, buffer, false);
                if (!SetInformationJobObject(job, JobObjectExtendedLimitInformationClass,
                        buffer, (uint)size))
                    return false;
                uint returned;
                if (!QueryInformationJobObject(job, JobObjectExtendedLimitInformationClass,
                        buffer, (uint)size, out returned) || returned < size)
                    return false;
                JobObjectExtendedLimitInformation observed =
                    (JobObjectExtendedLimitInformation)Marshal.PtrToStructure(buffer,
                        typeof(JobObjectExtendedLimitInformation));
                uint handleFlags;
                return observed.BasicLimitInformation.LimitFlags ==
                        (LimitActiveProcess | LimitProcessMemory | LimitJobMemory |
                            LimitKillOnJobClose) &&
                    observed.BasicLimitInformation.ActiveProcessLimit == activeLimit &&
                    observed.ProcessMemoryLimit.ToUInt64() == ProcessMemoryLimit &&
                    observed.JobMemoryLimit.ToUInt64() == jobMemory &&
                    GetHandleInformation(job, out handleFlags) && (handleFlags & 1) == 0;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool ExactGuardedNamesBeforeLaunch()
        {
            string[] names = {
                "cm0102.exe", "SyntheticLauncherSupervisor.exe",
                "SyntheticLauncherController.exe", "SyntheticLauncherFixture.exe",
                "SyntheticLauncherTimeoutFixture.exe", "SyntheticLauncherTimeoutChild.exe",
                "SyntheticLauncherLockedPreflight.exe"
            };
            int[] counts = new int[names.Length];
            IntPtr value = CreateToolhelp32Snapshot(2, 0);
            if (value == new IntPtr(-1)) return false;
            bool complete = false;
            try
            {
                ProcessEntry entry = new ProcessEntry();
                entry.Size = (uint)Marshal.SizeOf(typeof(ProcessEntry));
                bool more = Process32FirstW(value, ref entry);
                while (more)
                {
                    for (int index = 0; index < names.Length; index++)
                        if (String.Equals(names[index], entry.ExecutableFile,
                                StringComparison.OrdinalIgnoreCase)) counts[index]++;
                    more = Process32NextW(value, ref entry);
                    if (!more) complete = Marshal.GetLastWin32Error() == 18;
                }
            }
            finally { CloseHandle(value); }
            if (!complete) return false;
            if (counts[1] != 1) return false;
            for (int index = 0; index < counts.Length; index++)
                if (index != 1 && counts[index] != 0) return false;
            return true;
        }

        private bool ExactAttemptInventory(bool reportPresent, bool evidencePresent)
        {
            HashSet<string> expected = new HashSet<string>(StringComparer.Ordinal) {
                "SyntheticLauncherSupervisor.exe", "SyntheticLauncherController.exe",
                "SyntheticLauncherLockedPreflight.exe", "SyntheticLauncherTimeoutFixture.exe",
                "SyntheticLauncherTimeoutChild.exe", "SyntheticLauncherFixture.exe",
                "SyntheticLauncherBuildManifest.v1.json",
                "SyntheticLauncherController.public.v1.json",
                "SyntheticLauncherController.private.v1.json"
            };
            if (reportPresent) expected.Add("SyntheticLauncherReport.v1.json");
            if (evidencePresent) expected.Add("SyntheticLauncherWorkerEvidence.v1.json");
            if ((reportPresent || evidencePresent) && String.Equals(lease.ScenarioId,
                    RuntimeCanonicalData.UiSuccessScenario, StringComparison.Ordinal))
            {
                expected.Add(RuntimeCanonicalData.ReadyBmpName);
                expected.Add(RuntimeCanonicalData.CompleteBmpName);
            }
            HashSet<string> observed = new HashSet<string>(StringComparer.Ordinal);
            FindData first;
            IntPtr search = FindFirstFileW(snapshot.ParentFinalPath + "\\*", out first);
            if (search == new IntPtr(-1)) return false;
            try
            {
                FindData value = first;
                while (true)
                {
                    if (!String.Equals(value.FileName, ".", StringComparison.Ordinal) &&
                            !String.Equals(value.FileName, "..", StringComparison.Ordinal))
                    {
                        if ((value.FileAttributes & (0x10 | 0x400 | 0x800 | 0x4000)) != 0 ||
                                !observed.Add(value.FileName))
                            return false;
                    }
                    if (!FindNextFileW(search, out value))
                    {
                        if (Marshal.GetLastWin32Error() != 18) return false;
                        break;
                    }
                }
            }
            finally { FindClose(search); }
            return observed.SetEquals(expected);
        }

        private static bool ExactWorkerTopology(SupervisorRouteFacts route, uint workerProcessId)
        {
            string[] names = {
                "cm0102.exe", "SyntheticLauncherSupervisor.exe",
                "SyntheticLauncherController.exe", "SyntheticLauncherFixture.exe",
                "SyntheticLauncherTimeoutFixture.exe", "SyntheticLauncherTimeoutChild.exe",
                "SyntheticLauncherLockedPreflight.exe"
            };
            int[] counts = new int[names.Length];
            uint observedParent = 0;
            uint currentProcessId = GetCurrentProcessId();
            IntPtr value = CreateToolhelp32Snapshot(2, 0);
            if (value == new IntPtr(-1)) return false;
            bool complete = false;
            try
            {
                ProcessEntry entry = new ProcessEntry();
                entry.Size = (uint)Marshal.SizeOf(typeof(ProcessEntry));
                bool more = Process32FirstW(value, ref entry);
                while (more)
                {
                    for (int index = 0; index < names.Length; index++)
                    {
                        if (!String.Equals(names[index], entry.ExecutableFile,
                                StringComparison.OrdinalIgnoreCase))
                            continue;
                        counts[index]++;
                        if (entry.ProcessId == workerProcessId)
                            observedParent = entry.ParentProcessId;
                    }
                    more = Process32NextW(value, ref entry);
                    if (!more) complete = Marshal.GetLastWin32Error() == 18;
                }
            }
            finally { CloseHandle(value); }
            if (!complete) return false;
            int workerIndex = route.Role == SupervisorWorkerRole.Controller ? 2 : 6;
            for (int index = 0; index < counts.Length; index++)
            {
                int expected = index == 1 || index == workerIndex ? 1 : 0;
                if (counts[index] != expected) return false;
            }
            return workerProcessId != 0 && observedParent == currentProcessId;
        }

        private static bool JobIsEmptyNow(IntPtr job)
        {
            uint active;
            return TryGetJobActiveProcesses(job, out active) && active == 0;
        }

        private static bool TryGetJobActiveProcesses(IntPtr job, out uint active)
        {
            active = UInt32.MaxValue;
            int size = Marshal.SizeOf(typeof(BasicAccountingInformation));
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try
            {
                uint returned;
                if (!QueryInformationJobObject(job, JobObjectBasicAccountingInformation,
                        buffer, (uint)size, out returned) || returned < size)
                    return false;
                BasicAccountingInformation information = (BasicAccountingInformation)
                    Marshal.PtrToStructure(buffer, typeof(BasicAccountingInformation));
                active = information.ActiveProcesses;
                return true;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool WaitForEmptyUntil(IntPtr job, long start, long frequency,
            long deadline)
        {
            while (true)
            {
                long before;
                if (!QueryPerformanceCounter(out before) ||
                        !RuntimeDeadlineMath.CanProbe(start, deadline, before, frequency))
                    return false;
                uint active;
                if (!TryGetJobActiveProcesses(job, out active)) return false;
                long now;
                if (!QueryPerformanceCounter(out now)) return false;
                uint remaining = RuntimeDeadlineMath.RemainingMilliseconds(start, deadline,
                    now, frequency);
                if (remaining == 0) return false;
                if (active == 0) return true;
                Sleep(Math.Min(50U, remaining));
            }
        }

        private static bool ExactJobProcessId(IntPtr job, uint processId)
        {
            int size = 8 + IntPtr.Size * 4;
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try
            {
                for (int index = 0; index < size; index++) Marshal.WriteByte(buffer, index, 0);
                uint returned;
                return QueryInformationJobObject(job, JobObjectBasicProcessIdListInformation,
                        buffer, (uint)size, out returned) && returned >= 8 + IntPtr.Size &&
                    Marshal.ReadInt32(buffer, 0) == 1 && Marshal.ReadInt32(buffer, 4) == 1 &&
                    unchecked((uint)Marshal.ReadIntPtr(buffer, 8).ToInt64()) == processId;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private bool TryBoundedDeadline(uint cap, uint reserve, out long start,
            out long deadline)
        {
            start = 0;
            deadline = 0;
            if (!QueryPerformanceCounter(out start) || start < attemptStart)
                return false;
            long reserveTicks = 0;
            if (reserve != 0)
            {
                long reserveDeadline;
                if (!RuntimeDeadlineMath.TryCreateDeadline(0, attemptFrequency, reserve,
                        out reserveDeadline))
                    return false;
                reserveTicks = reserveDeadline;
            }
            if (attemptDeadline <= reserveTicks) return false;
            long overall = attemptDeadline - reserveTicks;
            long local;
            if (!RuntimeDeadlineMath.TryCreateDeadline(start, attemptFrequency, cap,
                    out local))
                return false;
            deadline = Math.Min(overall, local);
            return deadline > start && RemainingToDeadline(start, deadline) != 0;
        }

        private uint RemainingToDeadline(long start, long deadline)
        {
            long now;
            return QueryPerformanceCounter(out now) ? RuntimeDeadlineMath.RemainingMilliseconds(
                start, deadline, now, attemptFrequency) : 0;
        }

        private bool WaitOpenAndRead(string leaf, int maximum, long start, long deadline,
            out IntPtr handle, out byte[] bytes)
        {
            while (true)
            {
                long before;
                if (!QueryPerformanceCounter(out before) ||
                        !RuntimeDeadlineMath.CanProbe(start, deadline, before,
                            attemptFrequency))
                    break;
                if (TryOpenAndRead(leaf, maximum, out handle, out bytes))
                {
                    if (RemainingToDeadline(start, deadline) != 0) return true;
                    CloseHandle(handle);
                    handle = new IntPtr(-1);
                    bytes = null;
                    break;
                }
                uint remaining = RemainingToDeadline(start, deadline);
                if (remaining == 0) break;
                Sleep(Math.Min(50U, remaining));
            }
            handle = new IntPtr(-1);
            bytes = null;
            return false;
        }

        private bool TryOpenAndRead(string leaf, int maximum, out IntPtr handle, out byte[] bytes)
        {
            uint access = 0x80000000 | 0x80 | 0x00020000 | 0x00100000;
            if (String.Equals(leaf, "SyntheticLauncherWorkerEvidence.v1.json",
                    StringComparison.Ordinal))
                access |= 0x00010000;
            handle = OpenRelative(leaf, access, 1);
            bytes = null;
            if (handle == new IntPtr(-1))
                return false;
            bool keep = false;
            try
            {
                long size;
                if (!GetFileSizeEx(handle, out size) || size <= 0 || size > maximum)
                    return false;
                bytes = new byte[(int)size];
                int offset = 0;
                byte[] block = new byte[65536];
                while (offset < bytes.Length)
                {
                    uint read;
                    int count = Math.Min(block.Length, bytes.Length - offset);
                    if (!ReadFile(handle, block, (uint)count, out read, IntPtr.Zero) ||
                            read == 0 || read > count)
                        return false;
                    Buffer.BlockCopy(block, 0, bytes, offset, (int)read);
                    offset += (int)read;
                }
                if (!ExactCreatedObject(handle, leaf, bytes))
                    return false;
                keep = true;
                return true;
            }
            finally
            {
                if (!keep)
                {
                    CloseHandle(handle);
                    handle = new IntPtr(-1);
                    bytes = null;
                }
            }
        }

        private bool PublishCreateNew(string leaf, byte[] bytes)
        {
            IntPtr handle = OpenRelative(leaf,
                0x0002 | 0x80 | 0x00020000 | 0x00100000, 2);
            if (handle == new IntPtr(-1))
                return false;
            try
            {
                uint written;
                return WriteFile(handle, bytes, (uint)bytes.Length, out written, IntPtr.Zero) &&
                    written == bytes.Length && FlushFileBuffers(handle) &&
                    ExactCreatedObject(handle, leaf, bytes);
            }
            finally { CloseHandle(handle); }
        }

        private IntPtr OpenRelative(string leaf, uint access, uint disposition)
        {
            IntPtr text = Marshal.StringToHGlobalUni(leaf);
            IntPtr unicodePointer = IntPtr.Zero;
            try
            {
                UnicodeString unicode = new UnicodeString();
                unicode.Length = checked((ushort)(leaf.Length * 2));
                unicode.MaximumLength = unicode.Length;
                unicode.Buffer = text;
                unicodePointer = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(UnicodeString)));
                Marshal.StructureToPtr(unicode, unicodePointer, false);
                ObjectAttributes attributes = new ObjectAttributes();
                attributes.Length = Marshal.SizeOf(typeof(ObjectAttributes));
                attributes.RootDirectory = snapshot.ParentHandle;
                attributes.ObjectName = unicodePointer;
                attributes.Attributes = 0x40;
                IoStatusBlock statusBlock;
                IntPtr handle;
                long allocation = 0;
                int status = NtCreateFile(out handle, access, ref attributes, out statusBlock,
                    ref allocation, 0, 1, disposition, 0x20 | 0x40 | 0x00200000,
                    IntPtr.Zero, 0);
                return status < 0 ? new IntPtr(-1) : handle;
            }
            finally
            {
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(text);
            }
        }

        private static bool DeleteHeldObject(IntPtr handle)
        {
            FileDispositionInformation disposition = new FileDispositionInformation();
            disposition.DeleteFile = 1;
            int size = Marshal.SizeOf(typeof(FileDispositionInformation));
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try
            {
                Marshal.StructureToPtr(disposition, buffer, false);
                return SetFileInformationByHandle(handle, 4, buffer, (uint)size);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private bool RelativeNameAbsent(string leaf)
        {
            IntPtr text = Marshal.StringToHGlobalUni(leaf);
            IntPtr unicodePointer = IntPtr.Zero;
            IntPtr handle = new IntPtr(-1);
            try
            {
                UnicodeString unicode = new UnicodeString();
                unicode.Length = checked((ushort)(leaf.Length * 2));
                unicode.MaximumLength = unicode.Length;
                unicode.Buffer = text;
                unicodePointer = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(UnicodeString)));
                Marshal.StructureToPtr(unicode, unicodePointer, false);
                ObjectAttributes attributes = new ObjectAttributes();
                attributes.Length = Marshal.SizeOf(typeof(ObjectAttributes));
                attributes.RootDirectory = snapshot.ParentHandle;
                attributes.ObjectName = unicodePointer;
                attributes.Attributes = 0x40;
                IoStatusBlock statusBlock;
                long allocation = 0;
                int status = NtCreateFile(out handle,
                    0x80 | 0x00020000 | 0x00100000, ref attributes, out statusBlock,
                    ref allocation, 0, 1, 1, 0x20 | 0x40 | 0x00200000,
                    IntPtr.Zero, 0);
                if (status >= 0)
                {
                    CloseHandle(handle);
                    return false;
                }
                return status == unchecked((int)0xc0000034);
            }
            finally
            {
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(text);
            }
        }

        private bool FileIdentityAbsent(ByHandleFileInformation identity)
        {
            StringBuilder root = new StringBuilder(32768);
            if (!GetVolumePathNameW(snapshot.ParentFinalPath, root, root.Capacity))
                return false;
            string rootPath = root.ToString();
            if (rootPath.Length != 3 || rootPath[1] != ':' || rootPath[2] != '\\')
                return false;
            string volumePath = "\\\\.\\" + rootPath.Substring(0, 2);
            IntPtr volume = CreateFileW(volumePath, 0, 7, IntPtr.Zero, 3,
                0x02000000 | 0x00200000, IntPtr.Zero);
            if (volume == new IntPtr(-1))
                return false;
            try
            {
                FileIdDescriptor descriptor = new FileIdDescriptor();
                descriptor.Size = (uint)Marshal.SizeOf(typeof(FileIdDescriptor));
                descriptor.Type = 0;
                descriptor.Identifier.Unused = 0;
                descriptor.Identifier.FileId = unchecked((long)(((ulong)identity.FileIndexHigh << 32) |
                    identity.FileIndexLow));
                IntPtr reopened = OpenFileById(volume, ref descriptor, 0, 7, IntPtr.Zero,
                    0x00200000);
                if (reopened != new IntPtr(-1))
                {
                    CloseHandle(reopened);
                    return false;
                }
                return Marshal.GetLastWin32Error() == 2;
            }
            finally { CloseHandle(volume); }
        }

        private bool RebindAllInputs()
        {
            if (!RebindParent()) return false;
            foreach (System.Collections.Generic.KeyValuePair<string, SupervisorBoundObject> item
                    in snapshot.Objects)
            {
                IntPtr handle = OpenRelative(item.Key,
                    0x0001 | 0x0080 | 0x00020000 | 0x00100000, 1);
                if (handle == new IntPtr(-1)) return false;
                try
                {
                    if (!ExactBoundObject(handle, item.Value)) return false;
                }
                finally { CloseHandle(handle); }
            }
            return true;
        }

        private bool RebindParent()
        {
            ByHandleFileInformation information;
            return GetFileInformationByHandle(snapshot.ParentHandle, out information) &&
                information.VolumeSerialNumber == snapshot.ParentVolumeSerial &&
                information.FileIndexHigh == snapshot.ParentFileIndexHigh &&
                information.FileIndexLow == snapshot.ParentFileIndexLow &&
                information.NumberOfLinks == snapshot.ParentLinkCount &&
                information.FileAttributes == snapshot.ParentAttributes &&
                (information.FileAttributes & 0x10) != 0 &&
                (information.FileAttributes & (0x400 | 0x800 | 0x4000)) == 0 &&
                HasNoNamedDataStreams(snapshot.ParentHandle) &&
                String.Equals(FinalPath(snapshot.ParentHandle), snapshot.ParentFinalPath,
                    StringComparison.Ordinal) &&
                EqualBytes(SecurityDescriptor(snapshot.ParentHandle),
                    snapshot.ParentSecurityDescriptor);
        }

        private bool ExactBoundObject(IntPtr handle, SupervisorBoundObject expected)
        {
            ByHandleFileInformation information;
            if (!GetFileInformationByHandle(handle, out information) ||
                    information.VolumeSerialNumber != expected.VolumeSerial ||
                    information.FileIndexHigh != expected.FileIndexHigh ||
                    information.FileIndexLow != expected.FileIndexLow ||
                    information.NumberOfLinks != 1 || expected.LinkCount != 1 ||
                    information.FileAttributes != expected.Attributes ||
                    (information.FileAttributes & (0x10 | 0x400 | 0x800 | 0x4000)) != 0 ||
                    !String.Equals(FinalPath(handle), expected.FinalPath,
                        StringComparison.Ordinal) || !OnlyUnnamedStream(handle) ||
                    !EqualBytes(SecurityDescriptor(handle), expected.SecurityDescriptor))
                return false;
            long size = ((long)information.FileSizeHigh << 32) | information.FileSizeLow;
            if (size != expected.Bytes.Length) return false;
            byte[] observed = new byte[expected.Bytes.Length];
            int offset = 0;
            byte[] block = new byte[65536];
            while (offset < observed.Length)
            {
                uint read;
                int count = Math.Min(block.Length, observed.Length - offset);
                if (!ReadFile(handle, block, (uint)count, out read, IntPtr.Zero) ||
                        read == 0 || read > count)
                    return false;
                Buffer.BlockCopy(block, 0, observed, offset, (int)read);
                offset += (int)read;
            }
            bool exact = EqualBytes(observed, expected.Bytes);
            Array.Clear(observed, 0, observed.Length);
            return exact;
        }

        private bool ExactCreatedObject(IntPtr handle, string leaf, byte[] bytes)
        {
            ByHandleFileInformation information;
            string expectedPath = snapshot.ParentFinalPath + "\\" + leaf;
            SupervisorBoundObject inheritedFrom = snapshot.Objects[
                "SyntheticLauncherController.private.v1.json"];
            long size;
            return GetFileInformationByHandle(handle, out information) &&
                GetFileSizeEx(handle, out size) && size == bytes.Length &&
                information.VolumeSerialNumber == inheritedFrom.VolumeSerial &&
                information.NumberOfLinks == 1 &&
                (information.FileAttributes & (0x10 | 0x400 | 0x800 | 0x4000)) == 0 &&
                String.Equals(FinalPath(handle), expectedPath, StringComparison.Ordinal) &&
                OnlyUnnamedStream(handle) && EqualBytes(SecurityDescriptor(handle),
                    inheritedFrom.SecurityDescriptor);
        }

        private static string FinalPath(IntPtr handle)
        {
            StringBuilder value = new StringBuilder(32768);
            uint length = GetFinalPathNameByHandleW(handle, value, value.Capacity, 0);
            return length == 0 || length >= value.Capacity ? null : value.ToString();
        }

        private static bool OnlyUnnamedStream(IntPtr handle)
        {
            IntPtr buffer = Marshal.AllocHGlobal(65536);
            try
            {
                if (!GetFileInformationByHandleEx(handle, 7, buffer, 65536)) return false;
                int next = Marshal.ReadInt32(buffer, 0);
                int nameLength = Marshal.ReadInt32(buffer, 4);
                string name = nameLength == 14 ? Marshal.PtrToStringUni(
                    new IntPtr(buffer.ToInt64() + 24), 7) : null;
                return next == 0 && String.Equals(name, "::$DATA", StringComparison.Ordinal);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool HasNoNamedDataStreams(IntPtr handle)
        {
            IntPtr buffer = Marshal.AllocHGlobal(65536);
            try
            {
                if (!GetFileInformationByHandleEx(handle, 7, buffer, 65536)) return false;
                int offset = 0;
                while (true)
                {
                    if (offset < 0 || offset > 65536 - 24) return false;
                    int next = Marshal.ReadInt32(buffer, offset);
                    int nameLength = Marshal.ReadInt32(buffer, offset + 4);
                    if (nameLength < 0 || (nameLength & 1) != 0 ||
                            nameLength > 65536 - offset - 24)
                        return false;
                    string name = Marshal.PtrToStringUni(new IntPtr(buffer.ToInt64() +
                        offset + 24), nameLength / 2);
                    if (name != null && name.EndsWith(":$DATA",
                            StringComparison.OrdinalIgnoreCase) &&
                            !String.Equals(name, "::$DATA", StringComparison.Ordinal))
                        return false;
                    if (next == 0) return true;
                    if (next < 24 || (next & 7) != 0 || offset + next <= offset)
                        return false;
                    offset += next;
                }
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static byte[] SecurityDescriptor(IntPtr handle)
        {
            IntPtr owner;
            IntPtr group;
            IntPtr dacl;
            IntPtr sacl;
            IntPtr descriptor;
            uint result = GetSecurityInfo(handle, 1, 7, out owner, out group, out dacl,
                out sacl, out descriptor);
            if (result != 0 || descriptor == IntPtr.Zero) return new byte[0];
            try
            {
                uint length = GetSecurityDescriptorLength(descriptor);
                if (length == 0 || length > 65536) return new byte[0];
                byte[] bytes = new byte[(int)length];
                Marshal.Copy(descriptor, bytes, 0, bytes.Length);
                return bytes;
            }
            finally { LocalFree(descriptor); }
        }

        private static bool EqualBytes(byte[] first, byte[] second)
        {
            if (first == null || second == null || first.Length != second.Length)
                return false;
            for (int index = 0; index < first.Length; index++)
                if (first[index] != second[index]) return false;
            return true;
        }

        private byte[] ExpectedWorkerEvidence(SupervisorRouteFacts route)
        {
            bool locked = route.Role == SupervisorWorkerRole.LockedPreflight;
            bool timeout = route.ExpectedExit == RuntimeCanonicalData.ExitTreeTimeout;
            string value = "{\"artifacts\":" + ArtifactJson(locked || timeout) +
                ",\"bindings\":{\"build_manifest\":" +
                IdentityJson(snapshot.Objects["SyntheticLauncherBuildManifest.v1.json"]) +
                ",\"private_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.private.v1.json"]) +
                ",\"public_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.public.v1.json"]) +
                ",\"worker_image\":" + IdentityJson(snapshot.Objects[route.ImageName]) +
                "},\"evidence_kind\":\"worker\",\"observations\":{" +
                "\"binding_exact\":true,\"cleanup_exact\":true," +
                "\"controller_create_as_user_calls\":" + (locked ? "0" : "1") + "," +
                "\"environment_exact\":\"" + (locked ? "not-applicable" : "pass") +
                "\",\"fallback_create_calls\":0,\"fixture_resume_calls\":" +
                (locked ? "0" : "1") + ",\"guard_counts_exact\":true," +
                "\"inner_job_exact\":\"" + (locked ? "not-applicable" : "pass") +
                "\",\"input_capture_exact\":\"" +
                (!locked && !timeout ? "pass" : "not-applicable") +
                "\",\"locked_refusal_exact\":\"" + (locked ? "pass" : "not-applicable") +
                "\",\"parent_child_topology_exact\":true,\"registry_denied_exact\":\"" +
                (locked ? "not-applicable" : "pass") +
                "\",\"session_desktop_exact\":\"pass\",\"streams_empty\":true," +
                "\"target_result\":\"" + (locked ? "locked-refusal" :
                    timeout ? "tree-timeout-contained" : "ui-complete") +
                "\",\"timeout_tree_exact\":\"" + (timeout ? "pass" : "not-applicable") +
                "\",\"token_relationship_exact\":\"" +
                (locked ? "not-applicable" : "pass") + "\"}," +
                "\"profile_id\":\"cm0102-synthetic-launcher-runtime-v1\"," +
                "\"scenario_id\":\"" + lease.ScenarioId + "\",\"schema_version\":1," +
                "\"source_revision\":\"" + sourceRevision + "\"}";
            return Encoding.UTF8.GetBytes(value + "\n");
        }

        private byte[] ComposeReport(SupervisorRouteFacts route, bool created,
            bool assigned, bool membership, bool resumed, bool terminated, bool empty,
            bool streamsByConstruction)
        {
            bool locked = route.Role == SupervisorWorkerRole.LockedPreflight;
            bool timeout = route.ExpectedExit == RuntimeCanonicalData.ExitTreeTimeout;
            string attemptId = AttemptIdSha256();
            string attemptRootId = AttemptRootObjectIdSha256();
            string nonceSha256 = NonceSha256();
            int attemptOrdinal = AttemptOrdinal(attemptId);
            uint elapsedMilliseconds = ElapsedMilliseconds();
            string notApplicable = locked ? "not-applicable" : "pass";
            string uiOnly = !locked && !timeout ? "pass" : "not-applicable";
            string checks = "{\"binding-exact\":\"pass\"," +
                "\"capture-complete-exact\":\"" + uiOnly + "\"," +
                "\"capture-ready-exact\":\"" + uiOnly + "\"," +
                "\"cleanup-exact\":\"pass\",\"environment-exact\":\"" +
                notApplicable + "\",\"guard-stability\":\"pass\"," +
                "\"input-exact\":\"" + uiOnly + "\",\"job-containment\":\"pass\"," +
                "\"original-not-run\":\"pass\",\"preflight-safe\":\"pass\"," +
                "\"privacy-safe\":\"pass\",\"registry-denied\":\"" +
                notApplicable + "\",\"resume-once\":\"pass\"," +
                "\"supervisor-containment\":\"pass\",\"token-relationship\":\"" +
                notApplicable + "\",\"window-exact\":\"" + uiOnly + "\"}";
            string observations = "{\"capture\":{\"complete_bmp\":" +
                (locked || timeout ? "\"absent\"" : ArtifactIdentityJson(false)) +
                ",\"complete_repeat_exact\":" + Text(!locked && !timeout) +
                ",\"every_pixel_expected\":" + Text(!locked && !timeout) +
                ",\"ready_bmp\":" +
                (locked || timeout ? "\"absent\"" : ArtifactIdentityJson(true)) +
                ",\"ready_repeat_exact\":" + Text(!locked && !timeout) + "}," +
                "\"environment\":{\"nonce_sha256\":\"" + nonceSha256 +
                "\",\"status\":\"" + (locked ? "not-observed" : "observed") + "\"}," +
                "\"privacy\":{\"forbidden_string_count\":0,\"scan_passed\":true," +
                "\"unexpected_screen_bytes_retained\":0}," +
                "\"worker_stage_evidence_exact\":true}";
            string summary = locked ?
                "{\"comparison_verdict\":\"not-run\",\"completeness\":\"complete\"," +
                "\"fixture_execution_status\":\"not-run\"," +
                "\"original_behavior_qualified\":false," +
                "\"original_execution_status\":\"not-run\"," +
                "\"qualification_eligible\":true," +
                "\"safety_verdict\":\"synthetic-locked-refusal\"," +
                "\"scenario_id\":\"locked-refusal-v1\"}" : timeout ?
                "{\"comparison_verdict\":\"not-run\",\"completeness\":\"complete\"," +
                "\"fixture_execution_status\":\"expected-timeout-contained\"," +
                "\"original_behavior_qualified\":false," +
                "\"original_execution_status\":\"not-run\"," +
                "\"qualification_eligible\":true," +
                "\"safety_verdict\":\"synthetic-tree-timeout-contained\"," +
                "\"scenario_id\":\"tree-timeout-v1\"}" :
                "{\"comparison_verdict\":\"not-run\",\"completeness\":\"complete\"," +
                "\"fixture_execution_status\":\"succeeded\"," +
                "\"original_behavior_qualified\":false," +
                "\"original_execution_status\":\"not-run\"," +
                "\"qualification_eligible\":true," +
                "\"safety_verdict\":\"synthetic-launcher-qualified\"," +
                "\"scenario_id\":\"ui-success-v1\"}";
            string value = "{\"artifacts\":" + ArtifactJson(locked || timeout) +
                ",\"bindings\":{\"attempt_root_object_id_sha256\":\"" + attemptRootId +
                "\",\"build_manifest\":" +
                IdentityJson(snapshot.Objects["SyntheticLauncherBuildManifest.v1.json"]) +
                ",\"private_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.private.v1.json"]) +
                ",\"public_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.public.v1.json"]) +
                ",\"role_identities\":{\"controller\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.exe"]) + ",\"locked_preflight\":" +
                IdentityJson(snapshot.Objects["SyntheticLauncherLockedPreflight.exe"]) +
                ",\"supervisor\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherSupervisor.exe"]) + ",\"timeout_child\":" +
                IdentityJson(snapshot.Objects["SyntheticLauncherTimeoutChild.exe"]) +
                ",\"timeout_root\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherTimeoutFixture.exe"]) + ",\"ui_fixture\":" +
                IdentityJson(snapshot.Objects["SyntheticLauncherFixture.exe"]) + "}," +
                "\"worker_image\":" + IdentityJson(snapshot.Objects[route.ImageName]) + "}," +
                "\"checks\":" + checks + ",\"errors\":[],\"observations\":" +
                observations + "," +
                "\"original_behavior_qualified\":false," +
                "\"original_execution_status\":\"not-run\"," +
                "\"profile_id\":\"cm0102-synthetic-launcher-runtime-v1\"," +
                "\"report_kind\":\"supervisor-composed\",\"run\":{" +
                "\"attempt_id_sha256\":\"" + attemptId + "\",\"attempt_ordinal\":" +
                attemptOrdinal.ToString(CultureInfo.InvariantCulture) + ",\"elapsed_ms\":" +
                elapsedMilliseconds.ToString(CultureInfo.InvariantCulture) +
                ",\"observed_at_utc\":\"" + DateTime.UtcNow.ToString(
                    "yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture) +
                "\",\"source_revision\":\"" + sourceRevision + "\"},\"scenario_id\":\"" +
                lease.ScenarioId + "\",\"schema_version\":1,\"source_revision\":\"" +
                sourceRevision + "\",\"summary\":" + summary +
                ",\"supervisor_observations\":{" +
                "\"active_process_limit\":" + route.ActiveProcessLimit.ToString(
                    CultureInfo.InvariantCulture) + ",\"assigned_before_resume\":" + Text(assigned) +
                ",\"create_calls\":" + (created ? "1" : "0") + ",\"job_empty\":" +
                Text(empty) + ",\"job_memory_limit_bytes\":" + route.JobMemoryLimit.ToString(
                    CultureInfo.InvariantCulture) + ",\"membership_before_resume\":" +
                Text(membership) + ",\"post_worker_topology_exact\":true," +
                "\"process_memory_limit_bytes\":268435456,\"resume_calls\":" +
                (resumed ? "1" : "0") + ",\"streams_empty\":" +
                Text(streamsByConstruction) + "," +
                "\"termination_used\":" + Text(terminated) + ",\"worker_exit_code\":" +
                route.ExpectedExit.ToString(CultureInfo.InvariantCulture) + "}}";
            return Encoding.UTF8.GetBytes(value + "\n");
        }

        private static string ArtifactJson(bool absent)
        {
            if (absent)
                return "{\"complete_bmp\":\"absent\",\"ready_bmp\":\"absent\"}";
            return "{\"complete_bmp\":{\"byte_count\":230454,\"sha256\":\"" +
                RuntimeCanonicalData.CompleteBmpSha256 + "\"},\"ready_bmp\":" +
                "{\"byte_count\":230454,\"sha256\":\"" +
                RuntimeCanonicalData.ReadyBmpSha256 + "\"}}";
        }

        private static string ArtifactIdentityJson(bool ready)
        {
            return "{\"byte_count\":230454,\"sha256\":\"" +
                (ready ? RuntimeCanonicalData.ReadyBmpSha256 :
                    RuntimeCanonicalData.CompleteBmpSha256) + "\"}";
        }

        private string AttemptIdSha256()
        {
            byte[] privateBytes = snapshot.Objects[
                "SyntheticLauncherController.private.v1.json"].Bytes;
            byte[] material = new byte[privateBytes.Length + 12];
            Buffer.BlockCopy(privateBytes, 0, material, 0, privateBytes.Length);
            Buffer.BlockCopy(BitConverter.GetBytes(snapshot.ParentVolumeSerial), 0,
                material, privateBytes.Length, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(snapshot.ParentFileIndexHigh), 0,
                material, privateBytes.Length + 4, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(snapshot.ParentFileIndexLow), 0,
                material, privateBytes.Length + 8, 4);
            string result = LowerSha256(material);
            Array.Clear(material, 0, material.Length);
            return result;
        }

        private string AttemptRootObjectIdSha256()
        {
            byte[] material = new byte[12];
            Buffer.BlockCopy(BitConverter.GetBytes(snapshot.ParentVolumeSerial), 0, material, 0, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(snapshot.ParentFileIndexHigh), 0, material, 4, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(snapshot.ParentFileIndexLow), 0, material, 8, 4);
            string result = LowerSha256(material);
            Array.Clear(material, 0, material.Length);
            return result;
        }

        private string NonceSha256()
        {
            byte[] privateBytes = snapshot.Objects[
                "SyntheticLauncherController.private.v1.json"].Bytes;
            byte[] digest;
            using (System.Security.Cryptography.SHA256 hash =
                    System.Security.Cryptography.SHA256.Create())
                digest = hash.ComputeHash(privateBytes);
            uint nonce = BitConverter.ToUInt32(digest, 0);
            if (nonce == 0) nonce = 1;
            Array.Clear(digest, 0, digest.Length);
            byte[] value = BitConverter.GetBytes(nonce);
            string result = LowerSha256(value);
            Array.Clear(value, 0, value.Length);
            return result;
        }

        private static int AttemptOrdinal(string attemptId)
        {
            uint value = UInt32.Parse(attemptId.Substring(0, 8),
                NumberStyles.HexNumber, CultureInfo.InvariantCulture) & 0x7fffffffU;
            return value == 0 ? 1 : (int)value;
        }

        private uint ElapsedMilliseconds()
        {
            long now;
            if (!QueryPerformanceCounter(out now) || now < attemptStart || attemptFrequency <= 0)
                throw new InvalidOperationException("attempt clock");
            ulong elapsed = (ulong)(now - attemptStart) * 1000UL /
                (ulong)attemptFrequency;
            return elapsed > 3600000UL ? 3600000U : (uint)elapsed;
        }

        private static string LowerSha256(byte[] value)
        {
            using (System.Security.Cryptography.SHA256 hash =
                    System.Security.Cryptography.SHA256.Create())
            {
                byte[] digest = hash.ComputeHash(value);
                StringBuilder text = new StringBuilder(64);
                for (int index = 0; index < digest.Length; index++)
                    text.Append(digest[index].ToString("x2", CultureInfo.InvariantCulture));
                Array.Clear(digest, 0, digest.Length);
                return text.ToString();
            }
        }

        private static string Text(bool value) { return value ? "true" : "false"; }

        private static string IdentityJson(SupervisorBoundObject value)
        {
            return "{\"byte_count\":" + value.Bytes.Length.ToString(
                CultureInfo.InvariantCulture) + ",\"sha256\":\"" + value.Sha256 + "\"}";
        }

        private static string IdentityJson(byte[] value)
        {
            using (System.Security.Cryptography.SHA256 hash =
                    System.Security.Cryptography.SHA256.Create())
            {
                byte[] digest = hash.ComputeHash(value);
                StringBuilder text = new StringBuilder(64);
                for (int index = 0; index < digest.Length; index++)
                    text.Append(digest[index].ToString("x2", CultureInfo.InvariantCulture));
                return "{\"byte_count\":" + value.Length.ToString(
                    CultureInfo.InvariantCulture) + ",\"sha256\":\"" + text.ToString() + "\"}";
            }
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct StartupInfo
        {
            internal int Size; internal string Reserved; internal string Desktop;
            internal string Title; internal int X; internal int Y; internal int XSize;
            internal int YSize; internal int XCountChars; internal int YCountChars;
            internal int FillAttribute; internal int Flags; internal short ShowWindow;
            internal short Reserved2; internal IntPtr Reserved2Pointer;
            internal IntPtr StandardInput; internal IntPtr StandardOutput;
            internal IntPtr StandardError;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct ProcessInformation
        {
            internal IntPtr Process; internal IntPtr Thread;
            internal uint ProcessId; internal uint ThreadId;
        }
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct ProcessEntry
        {
            internal uint Size; internal uint Usage; internal uint ProcessId;
            internal IntPtr DefaultHeapId; internal uint ModuleId; internal uint Threads;
            internal uint ParentProcessId; internal int PriorityClassBase; internal uint Flags;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)]
            internal string ExecutableFile;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct BasicLimitInformation
        {
            internal long PerProcessUserTimeLimit; internal long PerJobUserTimeLimit;
            internal uint LimitFlags; internal UIntPtr MinimumWorkingSetSize;
            internal UIntPtr MaximumWorkingSetSize; internal uint ActiveProcessLimit;
            internal UIntPtr Affinity; internal uint PriorityClass; internal uint SchedulingClass;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct IoCounters
        {
            internal ulong ReadOperationCount; internal ulong WriteOperationCount;
            internal ulong OtherOperationCount; internal ulong ReadTransferCount;
            internal ulong WriteTransferCount; internal ulong OtherTransferCount;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct JobObjectExtendedLimitInformation
        {
            internal BasicLimitInformation BasicLimitInformation; internal IoCounters IoInfo;
            internal UIntPtr ProcessMemoryLimit; internal UIntPtr JobMemoryLimit;
            internal UIntPtr PeakProcessMemoryUsed; internal UIntPtr PeakJobMemoryUsed;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct BasicAccountingInformation
        {
            internal long TotalUserTime; internal long TotalKernelTime;
            internal long ThisPeriodTotalUserTime; internal long ThisPeriodTotalKernelTime;
            internal uint TotalPageFaultCount; internal uint TotalProcesses;
            internal uint ActiveProcesses; internal uint TotalTerminatedProcesses;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct UnicodeString { internal ushort Length; internal ushort MaximumLength; internal IntPtr Buffer; }
        [StructLayout(LayoutKind.Sequential)]
        private struct ObjectAttributes
        {
            internal int Length; internal IntPtr RootDirectory; internal IntPtr ObjectName;
            internal uint Attributes; internal IntPtr SecurityDescriptor;
            internal IntPtr SecurityQualityOfService;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct IoStatusBlock { internal IntPtr Status; internal IntPtr Information; }
        [StructLayout(LayoutKind.Sequential)]
        private struct FileDispositionInformation
        {
            internal byte DeleteFile;
        }
        [StructLayout(LayoutKind.Sequential, Pack = 4, Size = 52)]
        private struct ByHandleFileInformation
        {
            internal uint FileAttributes; internal long CreationTime;
            internal long LastAccessTime; internal long LastWriteTime;
            internal uint VolumeSerialNumber; internal uint FileSizeHigh;
            internal uint FileSizeLow; internal uint NumberOfLinks;
            internal uint FileIndexHigh; internal uint FileIndexLow;
        }
        [StructLayout(LayoutKind.Sequential, Pack = 4, Size = 24)]
        private struct FileIdDescriptor
        {
            internal uint Size; internal int Type; internal FileIdUnion Identifier;
        }
        [StructLayout(LayoutKind.Explicit, Size = 16)]
        private struct FileIdUnion
        {
            [FieldOffset(0)] internal long FileId;
            [FieldOffset(8)] internal long Unused;
        }
        [StructLayout(LayoutKind.Sequential, Pack = 4, Size = 592, CharSet = CharSet.Unicode)]
        private struct FindData
        {
            internal uint FileAttributes; internal long CreationTime;
            internal long LastAccessTime; internal long LastWriteTime;
            internal uint FileSizeHigh; internal uint FileSizeLow;
            internal uint Reserved0; internal uint Reserved1;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)] internal string FileName;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 14)] internal string AlternateFileName;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateJobObjectW(IntPtr attributes, string name);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetInformationJobObject(IntPtr job, uint informationClass,
            IntPtr information, uint length);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CreateProcessW(string applicationName, string commandLine,
            IntPtr processAttributes, IntPtr threadAttributes, bool inheritHandles,
            uint creationFlags, IntPtr environment, string currentDirectory,
            ref StartupInfo startupInfo, out ProcessInformation processInformation);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool result);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern uint ResumeThread(IntPtr thread);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetExitCodeProcess(IntPtr process, out uint exitCode);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool TerminateJobObject(IntPtr job, uint exitCode);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool TerminateProcess(IntPtr process, uint exitCode);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool QueryInformationJobObject(IntPtr job, uint informationClass,
            IntPtr information, uint length, out uint returnedLength);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetHandleInformation(IntPtr handle, out uint flags);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateToolhelp32Snapshot(uint flags, uint processId);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool Process32FirstW(IntPtr snapshot, ref ProcessEntry entry);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool Process32NextW(IntPtr snapshot, ref ProcessEntry entry);
        [DllImport("kernel32.dll")]
        private static extern uint GetCurrentProcessId();
        [DllImport("kernel32.dll")]
        private static extern void Sleep(uint milliseconds);
        [DllImport("kernel32.dll")]
        private static extern bool QueryPerformanceCounter(out long value);
        [DllImport("kernel32.dll")]
        private static extern bool QueryPerformanceFrequency(out long value);
        [DllImport("ntdll.dll")]
        private static extern int NtCreateFile(out IntPtr handle, uint access,
            ref ObjectAttributes attributes, out IoStatusBlock statusBlock, ref long allocationSize,
            uint fileAttributes, uint share, uint disposition, uint options,
            IntPtr extendedAttributes, uint extendedAttributesLength);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileSizeEx(IntPtr handle, out long size);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileInformationByHandle(IntPtr handle,
            out ByHandleFileInformation information);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetFinalPathNameByHandleW(IntPtr handle, StringBuilder path,
            int count, uint flags);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileInformationByHandleEx(IntPtr handle,
            int informationClass, IntPtr information, uint size);
        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern uint GetSecurityInfo(IntPtr handle, int objectType,
            uint securityInformation, out IntPtr owner, out IntPtr group, out IntPtr dacl,
            out IntPtr sacl, out IntPtr descriptor);
        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern uint GetSecurityDescriptorLength(IntPtr descriptor);
        [DllImport("kernel32.dll")]
        private static extern IntPtr LocalFree(IntPtr memory);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool GetVolumePathNameW(string path, StringBuilder volumePath,
            int length);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateFileW(string name, uint access, uint share,
            IntPtr security, uint creation, uint flags, IntPtr template);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr FindFirstFileW(string path, out FindData data);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool FindNextFileW(IntPtr search, out FindData data);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool FindClose(IntPtr search);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenFileById(IntPtr volume, ref FileIdDescriptor descriptor,
            uint access, uint share, IntPtr security, uint flags);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ReadFile(IntPtr handle, byte[] buffer, uint count,
            out uint read, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool WriteFile(IntPtr handle, byte[] buffer, uint count,
            out uint written, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool FlushFileBuffers(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetFileInformationByHandle(IntPtr handle, int informationClass,
            IntPtr information, uint size);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);
    }
}
