using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal enum ControllerRoute
    {
        UiSuccess = 1,
        TreeTimeout = 2
    }

    internal sealed class ControllerRouteFacts
    {
        internal ControllerRouteFacts(ControllerRoute route, string target,
            int expectedExit)
        {
            Route = route;
            Target = target;
            ExpectedExit = expectedExit;
        }
        internal readonly ControllerRoute Route;
        internal readonly string Target;
        internal readonly int ExpectedExit;
    }

    internal sealed class ControllerGuardSnapshot
    {
        internal ControllerGuardSnapshot(string acceptedHost, string attemptRoot,
            string installedTree, string virtualStore, long registryLastWrite)
        {
            AcceptedHost = acceptedHost;
            AttemptRoot = attemptRoot;
            InstalledTree = installedTree;
            VirtualStore = virtualStore;
            RegistryLastWrite = registryLastWrite;
        }

        internal readonly string AcceptedHost;
        internal readonly string AttemptRoot;
        internal readonly string InstalledTree;
        internal readonly string VirtualStore;
        internal readonly long RegistryLastWrite;

        internal bool Exact(ControllerGuardSnapshot other)
        {
            return ExactPaths(other) && ExactRegistry(other);
        }

        internal bool ExactPaths(ControllerGuardSnapshot other)
        {
            return other != null &&
                String.Equals(AcceptedHost, other.AcceptedHost, StringComparison.Ordinal) &&
                String.Equals(AttemptRoot, other.AttemptRoot, StringComparison.Ordinal) &&
                String.Equals(InstalledTree, other.InstalledTree, StringComparison.Ordinal) &&
                String.Equals(VirtualStore, other.VirtualStore, StringComparison.Ordinal);
        }

        internal bool ExactRegistry(ControllerGuardSnapshot other)
        {
            return other != null && RegistryLastWrite == other.RegistryLastWrite;
        }
    }

    internal sealed class ControllerLiveNative : IRuntimeControllerScenarioPort
    {
        private const uint CREATE_SUSPENDED = 0x00000004;
        private const uint CreateNoWindow = 0x08000000;
        private const uint CreateUnicodeEnvironment = 0x00000400;
        private const uint WaitObject0 = 0;
        private const uint WaitTimeout = 258;
        private const uint SnapshotProcesses = 0x00000002;
        private const uint FileReadAttributes = 0x00000080;
        private const uint ReadControl = 0x00020000;
        private const uint Synchronize = 0x00100000;
        private const uint FileSynchronousIoNonAlert = 0x00000020;
        private const uint FileNonDirectoryFile = 0x00000040;
        private const uint FileOpenReparsePoint = 0x00200000;
        private const uint TokenQuery = 0x0008;
        private const uint TokenDuplicate = 0x0002;
        private const uint TokenAssignPrimary = 0x0001;
        private const uint TokenAdjustPrivileges = 0x0020;
        private const int TokenUserInformation = 1;
        private const int TokenGroupsInformation = 2;
        private const int TokenPrivilegesInformation = 3;
        private const int TokenStatisticsInformation = 10;
        private const int TokenSessionIdInformation = 12;
        private const int TokenElevationTypeInformation = 18;
        private const int TokenElevationInformation = 20;
        private const int TokenLinkedTokenInformation = 19;
        private const int TokenIntegrityLevelInformation = 25;
        private const uint ProcessQueryLimitedInformation = 0x1000;
        private const uint KeyAllAccess = 0x000f003f;
        private const uint ErrorAccessDenied = 5;
        private const uint JobObjectExtendedLimitInformationClass = 9;
        private const uint JobObjectBasicAccountingInformation = 1;
        private const uint JobObjectBasicProcessIdListInformation = 3;
        private const uint LimitActiveProcess = 0x00000008;
        private const uint LimitProcessMemory = 0x00000100;
        private const uint LimitJobMemory = 0x00000200;
        private const uint LimitKillOnJobClose = 0x00002000;
        private const uint ProcessMemoryLimit = 268435456;
        private const uint UiJobMemoryLimit = 268435456;
        private const uint TimeoutJobMemoryLimit = 536870912;
        private const uint SmtoAbortIfHung = 0x0002;
        private const uint WmClose = 0x0010;
        private const uint ProtocolQueryMessage = 0x8051;
        private const uint StateQueryMessage = 0x8052;
        private const ulong ProtocolMagic = 0x434d0101;
        private const uint Srccopy = 0x00cc0020;
        private readonly RuntimeLeaseUse lease;
        private readonly RuntimeScenarioPlan plan;
        private readonly ControllerRouteFacts route;
        private readonly ControllerBootstrapSnapshot snapshot;
        private readonly string sourceRevision;
        private readonly RuntimePrivateConfiguration privateConfiguration;
        private IntPtr launchBinding;
        private IntPtr sourceToken;
        private IntPtr primaryToken;
        private IntPtr callerToken;
        private IntPtr environment;
        private IntPtr job;
        private ProcessInformation child;
        private bool childCreated;
        private bool childAssigned;
        private uint quotaOriginalAttributes;
        private bool quotaAdjusted;
        private bool quotaRestored;
        private ControllerGuardSnapshot guardBefore;
        private ControllerGuardSnapshot guardAfter;
        private bool guardsVerified;
        private IntPtr window;
        private Rect client;
        private Point clickPoint;
        private byte[] readyOne;
        private byte[] readyTwo;
        private byte[] completeOne;
        private byte[] completeTwo;
        private byte[] readyBmp;
        private byte[] completeBmp;
        private bool readyBmpPublished;
        private bool completeBmpPublished;
        private bool workerEvidencePublished;
        private bool outputsAccepted;
        private bool inputReleaseArmed;
        private Input releaseInput;
        private long routeDeadlineStart;
        private long routeDeadlineFrequency;
        private long routeDeadlineTicks;
        private bool routeDeadlineStarted;
        private long transitionDeadlineStart;
        private long transitionDeadlineFrequency;
        private long transitionDeadlineTicks;
        private bool transitionDeadlineStarted;
        private bool timeoutTerminationAttempted;
        private int completedStageCount;
        private bool cleanupCalled;
        private bool bindingsCleanupRequired;

        internal ControllerLiveNative(RuntimeLeaseUse consumedLease, RuntimeScenarioPlan scenarioPlan,
            ControllerBootstrapSnapshot boundSnapshot, string boundSourceRevision,
            RuntimePrivateConfiguration boundPrivateConfiguration)
        {
            if (consumedLease == null)
                throw new ArgumentNullException("consumedLease");
            if (boundSnapshot == null)
                throw new ArgumentNullException("boundSnapshot");
            if (!RuntimeIdentity.IsLowerHexNonZero(boundSourceRevision, 40))
                throw new ArgumentException("sourceRevision");
            if (boundPrivateConfiguration == null)
                throw new ArgumentNullException("boundPrivateConfiguration");
            if (scenarioPlan == null || scenarioPlan.Role != RuntimeScenarioRole.Controller ||
                    !String.Equals(scenarioPlan.ScenarioId, consumedLease.ScenarioId,
                        StringComparison.Ordinal) ||
                    !String.Equals(scenarioPlan.ScenarioId,
                        boundPrivateConfiguration.ScenarioId, StringComparison.Ordinal))
                throw new ArgumentException("scenarioPlan");
            ControllerRoute selectedRoute;
            if (String.Equals(scenarioPlan.ScenarioId, RuntimeCanonicalData.UiSuccessScenario,
                    StringComparison.Ordinal))
                selectedRoute = ControllerRoute.UiSuccess;
            else if (String.Equals(scenarioPlan.ScenarioId,
                    RuntimeCanonicalData.TreeTimeoutScenario, StringComparison.Ordinal))
                selectedRoute = ControllerRoute.TreeTimeout;
            else
                throw new ArgumentException("scenarioPlan");
            lease = consumedLease;
            plan = scenarioPlan;
            route = new ControllerRouteFacts(selectedRoute, scenarioPlan.TargetImage,
                scenarioPlan.SuccessExitCode);
            snapshot = boundSnapshot;
            sourceRevision = boundSourceRevision;
            privateConfiguration = boundPrivateConfiguration;
            launchBinding = new IntPtr(-1);
        }

        public RuntimeScenarioRole Role
        {
            get { return RuntimeScenarioRole.Controller; }
        }

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
            if (stage == RuntimeScenarioStage.StreamsAbsent)
                return Result(StandardStreamsAbsent(), RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.BindInputs)
                return BindInputs();
            if (stage == RuntimeScenarioStage.OutputsAbsent)
                return Result(RelativeNameAbsent("SyntheticLauncherWorkerEvidence.v1.json") &&
                    RelativeNameAbsent("SyntheticLauncherReport.v1.json") &&
                    RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName) &&
                    RelativeNameAbsent(RuntimeCanonicalData.CompleteBmpName),
                    RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.SessionDesktop)
                return Result(ExactSessionDesktop(), RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.ControllerTopology)
                return Result(ExactControllerTopology(route, 0, false, false),
                    RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.TokenAcquire)
                return Result(TryAcquireLimitedExplorerToken(out sourceToken, out primaryToken,
                    out callerToken), RuntimeCanonicalData.ExitNativeCapabilityFailure);
            if (stage == RuntimeScenarioStage.QuotaEnabled)
                return Result(EnableIncreaseQuota(callerToken, out quotaOriginalAttributes,
                    out quotaAdjusted), RuntimeCanonicalData.ExitNativeCapabilityFailure);
            if (stage == RuntimeScenarioStage.RegistryDenied)
                return Result(RequireRegistryDenial(primaryToken),
                    RuntimeCanonicalData.ExitNativeCapabilityFailure);
            if (stage == RuntimeScenarioStage.GuardBaseline)
                return Result(CaptureGuards(out guardBefore),
                    RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.TokenRelationship)
                return Result(ExactTokenRelationship(callerToken, sourceToken, primaryToken, true),
                    RuntimeCanonicalData.ExitNativeCapabilityFailure);
            if (stage == RuntimeScenarioStage.Environment)
            {
                environment = BuildEnvironmentBlock(snapshot.ParentFinalPath,
                    NonceFromPrivateConfiguration());
                return Result(environment != IntPtr.Zero,
                    RuntimeCanonicalData.ExitBindingRejection);
            }
            if (stage == RuntimeScenarioStage.InnerJobConfigured)
            {
                job = CreateJobObjectW(IntPtr.Zero, null);
                return Result(job != IntPtr.Zero && ConfigureInnerJob(job, route),
                    RuntimeCanonicalData.ExitNativeCapabilityFailure);
            }
            if (stage == RuntimeScenarioStage.TargetCreate)
                return CreateTarget();
            if (stage == RuntimeScenarioStage.InnerAssign)
            {
                childAssigned = AssignProcessToJobObject(job, child.Process);
                return Result(childAssigned, RuntimeCanonicalData.ExitNativeCapabilityFailure);
            }
            if (stage == RuntimeScenarioStage.InnerMembership)
            {
                bool member;
                return Result(IsProcessInJob(child.Process, job, out member) && member &&
                    ExactJobProcessIds(job, child.ProcessId, 0),
                    RuntimeCanonicalData.ExitNativeCapabilityFailure);
            }
            if (stage == RuntimeScenarioStage.TargetResume)
            {
                uint routeBudget = route.Route == ControllerRoute.UiSuccess ? 30000U : 5000U;
                routeDeadlineStarted = TryStartDeadline(routeBudget, out routeDeadlineStart,
                    out routeDeadlineFrequency, out routeDeadlineTicks);
                return Result(routeDeadlineStarted && ResumeThread(child.Thread) != 0xffffffff,
                    RuntimeCanonicalData.ExitNativeCapabilityFailure);
            }
            if (stage == RuntimeScenarioStage.UiWindow)
                return UiWindow();
            if (stage == RuntimeScenarioStage.UiProtocolReady)
                return UiProtocolReady();
            if (stage == RuntimeScenarioStage.UiGeometry)
                return UiGeometry();
            if (stage == RuntimeScenarioStage.UiReadyCaptureOne)
                return Result(CaptureExactClient(window, client, true, out readyOne),
                    RuntimeCanonicalData.ExitNativeCapabilityFailure);
            if (stage == RuntimeScenarioStage.UiReadyCaptureTwo)
                return ReadyCaptureTwo();
            if (stage == RuntimeScenarioStage.UiInput)
                return UiInput();
            if (stage == RuntimeScenarioStage.UiCompleteState)
                return UiCompleteState();
            if (stage == RuntimeScenarioStage.UiCompleteCaptureOne)
                return Result(CaptureExactClient(window, client, false, out completeOne),
                    RuntimeCanonicalData.ExitNativeCapabilityFailure);
            if (stage == RuntimeScenarioStage.UiCompleteCaptureTwo)
                return CompleteCaptureTwo();
            if (stage == RuntimeScenarioStage.UiClose)
                return UiClose();
            if (stage == RuntimeScenarioStage.TimeoutRootChildTopology)
                return TimeoutRootChildTopology();
            if (stage == RuntimeScenarioStage.TimeoutObserved)
                return TimeoutObserved();
            if (stage == RuntimeScenarioStage.InnerCleanup)
                return InnerCleanup();
            if (stage == RuntimeScenarioStage.SessionDesktopRecheck)
                return Result(ExactSessionDesktop(), RuntimeCanonicalData.ExitCleanupFailure);
            if (stage == RuntimeScenarioStage.QuotaRestored)
            {
                quotaRestored = RestoreIncreaseQuota(callerToken, quotaOriginalAttributes);
                return Result(quotaRestored, RuntimeCanonicalData.ExitCleanupFailure);
            }
            if (stage == RuntimeScenarioStage.TokenRestored)
                return Result(ExactTokenRelationship(callerToken, sourceToken, primaryToken, false),
                    RuntimeCanonicalData.ExitCleanupFailure);
            if (stage == RuntimeScenarioStage.GuardsStable)
                return Result(CaptureGuards(out guardAfter) &&
                    guardBefore.ExactPaths(guardAfter), RuntimeCanonicalData.ExitCleanupFailure);
            if (stage == RuntimeScenarioStage.RegistryStable)
            {
                guardsVerified = guardBefore.ExactRegistry(guardAfter);
                return Result(guardsVerified, RuntimeCanonicalData.ExitCleanupFailure);
            }
            if (stage == RuntimeScenarioStage.RebindInputs)
                return Result(RebindAllInputs(), RuntimeCanonicalData.ExitCleanupFailure);
            if (stage == RuntimeScenarioStage.WorkerPublish)
                return Result(PublishWorkerEvidence(route, route.ExpectedExit),
                    RuntimeCanonicalData.ExitReportFailure);
            return Failed(RuntimeCanonicalData.ExitBindingRejection);
        }

        private RuntimeScenarioStepResult BindInputs()
        {
            if (!snapshot.Objects.ContainsKey(route.Target) || !RebindAllInputs())
                return Failed(RuntimeCanonicalData.ExitBindingRejection);
            bindingsCleanupRequired = true;
            launchBinding = OpenRelativeExisting(route.Target,
                0x0001 | 0x0080 | 0x00020000 | 0x00100000);
            bool exact = launchBinding != new IntPtr(-1) &&
                ExactBoundObject(launchBinding, snapshot.Objects[route.Target], true);
            return Result(exact, RuntimeCanonicalData.ExitBindingRejection);
        }

        private RuntimeScenarioStepResult CreateTarget()
        {
            StartupInfo startup = new StartupInfo();
            startup.Size = Marshal.SizeOf(typeof(StartupInfo));
            startup.Desktop = "winsta0\\default";
            string application = snapshot.ParentFinalPath + "\\" + route.Target;
            childCreated = CreateProcessAsUserW(primaryToken, application, null,
                IntPtr.Zero, IntPtr.Zero, false, CREATE_SUSPENDED | CreateUnicodeEnvironment |
                    CreateNoWindow, environment, snapshot.ParentFinalPath, ref startup, out child);
            return Result(childCreated, RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult UiWindow()
        {
            return Result(routeDeadlineStarted && WaitForUniqueChildWindow(child.ProcessId,
                routeDeadlineStart, routeDeadlineFrequency, routeDeadlineTicks, out window) &&
                ExactControllerTopology(route, child.ProcessId, true, false),
                RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult UiProtocolReady()
        {
            uint remaining = routeDeadlineStarted ? RemainingMilliseconds(routeDeadlineStart,
                routeDeadlineTicks, routeDeadlineFrequency) : 0;
            if (remaining == 0)
                return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
            UIntPtr protocol;
            if (SendMessageTimeoutW(window, ProtocolQueryMessage, IntPtr.Zero, IntPtr.Zero,
                    SmtoAbortIfHung, Math.Min(1000U, remaining), out protocol) == IntPtr.Zero ||
                    protocol.ToUInt64() != ProtocolMagic)
                return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
            remaining = RemainingMilliseconds(routeDeadlineStart, routeDeadlineTicks,
                routeDeadlineFrequency);
            if (remaining == 0)
                return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
            UIntPtr readyState;
            bool ready = SendMessageTimeoutW(window, StateQueryMessage, IntPtr.Zero, IntPtr.Zero,
                SmtoAbortIfHung, Math.Min(1000U, remaining), out readyState) != IntPtr.Zero &&
                readyState.ToUInt64() == 1;
            return Result(ready && GetForegroundWindow() == window && AllRelevantInputUp() &&
                ExactSessionDesktop() && RemainingMilliseconds(routeDeadlineStart,
                    routeDeadlineTicks, routeDeadlineFrequency) != 0,
                RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult UiGeometry()
        {
            Rect exactClient;
            Point exactClick;
            if (!TryExactUiGeometry(out exactClient, out exactClick))
                return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
            client = exactClient;
            clickPoint = exactClick;
            return RuntimeScenarioStepResult.Passed();
        }

        private bool TryExactUiGeometry(out Rect exactClient, out Point exactClick)
        {
            exactClient = new Rect();
            exactClick = new Point();
            Rect windowRectangle;
            int dpiAwareness;
            if (!GetClientRect(window, out exactClient) || exactClient.Left != 0 ||
                    exactClient.Top != 0 || exactClient.Right != 320 ||
                    exactClient.Bottom != 240 || !GetWindowRect(window, out windowRectangle) ||
                    windowRectangle.Left != 64 || windowRectangle.Top != 64 ||
                    GetProcessDpiAwareness(child.Process, out dpiAwareness) != 0 ||
                    dpiAwareness != 1 || GetSystemMetrics(0) < 400 ||
                    GetSystemMetrics(1) < 352)
                return false;
            exactClick.X = 96;
            exactClick.Y = 112;
            return ClientToScreen(window, ref exactClick);
        }

        private RuntimeScenarioStepResult ReadyCaptureTwo()
        {
            bool exact = CaptureExactClient(window, client, true, out readyTwo) &&
                EqualBytes(readyOne, readyTwo);
            ZeroBytes(readyTwo);
            readyTwo = null;
            return Result(exact, RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult UiInput()
        {
            Rect currentClient;
            Point currentClick;
            if (GetForegroundWindow() != window || !AllRelevantInputUp() ||
                    !ExactSessionDesktop() ||
                    !ExactControllerTopology(route, child.ProcessId, true, false) ||
                    !TryExactUiGeometry(out currentClient, out currentClick) ||
                    currentClient.Left != client.Left || currentClient.Top != client.Top ||
                    currentClient.Right != client.Right || currentClient.Bottom != client.Bottom ||
                    currentClick.X != clickPoint.X || currentClick.Y != clickPoint.Y)
                return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
            transitionDeadlineStarted = TryStartDeadline(10000,
                out transitionDeadlineStart, out transitionDeadlineFrequency,
                out transitionDeadlineTicks);
            if (!transitionDeadlineStarted)
                return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
            Input[] input = FixedClick(clickPoint, NonceFromPrivateConfiguration());
            releaseInput = input[2];
            inputReleaseArmed = true;
            uint inserted = SendInput((uint)input.Length, input, Marshal.SizeOf(typeof(Input)));
            if (inserted == (uint)input.Length)
                return RuntimeScenarioStepResult.Passed();
            Input[] release = new Input[] { releaseInput };
            bool released = SendInput(1, release, Marshal.SizeOf(typeof(Input))) == 1 &&
                AllRelevantInputUp();
            inputReleaseArmed = !released;
            return Failed(released ? RuntimeCanonicalData.ExitNativeCapabilityFailure :
                RuntimeCanonicalData.ExitCleanupFailure);
        }

        private RuntimeScenarioStepResult UiCompleteState()
        {
            if (!transitionDeadlineStarted)
                return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
            while (true)
            {
                uint remaining = RemainingMilliseconds(transitionDeadlineStart,
                    transitionDeadlineTicks, transitionDeadlineFrequency);
                if (remaining == 0)
                    return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
                UIntPtr state;
                if (SendMessageTimeoutW(window, StateQueryMessage, IntPtr.Zero, IntPtr.Zero,
                        SmtoAbortIfHung, Math.Min(1000U, remaining), out state) == IntPtr.Zero)
                    return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
                remaining = RemainingMilliseconds(transitionDeadlineStart,
                    transitionDeadlineTicks, transitionDeadlineFrequency);
                if (remaining == 0)
                    return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
                if (state.ToUInt64() == 2)
                    return RuntimeScenarioStepResult.Passed();
                if (state.ToUInt64() != 1)
                    return Failed(RuntimeCanonicalData.ExitNativeCapabilityFailure);
                Sleep(Math.Min(50U, remaining));
            }
        }

        private RuntimeScenarioStepResult CompleteCaptureTwo()
        {
            bool exact = CaptureExactClient(window, client, false, out completeTwo) &&
                EqualBytes(completeOne, completeTwo);
            if (exact)
            {
                exact = RuntimeCanonicalData.TryEncodeCanonicalBmp(readyOne, out readyBmp) &&
                    RuntimeCanonicalData.TryEncodeCanonicalBmp(completeOne, out completeBmp) &&
                    RuntimeCanonicalData.IsApprovedCanonicalBmp(readyBmp, true) &&
                    RuntimeCanonicalData.IsApprovedCanonicalBmp(completeBmp, false);
            }
            ZeroBytes(readyOne);
            readyOne = null;
            ZeroBytes(completeOne);
            ZeroBytes(completeTwo);
            completeOne = null;
            completeTwo = null;
            if (!exact)
            {
                ZeroBytes(readyBmp); ZeroBytes(completeBmp);
                readyBmp = null; completeBmp = null;
            }
            return Result(exact, RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult UiClose()
        {
            routeDeadlineStarted = TryStartDeadline(5000, out routeDeadlineStart,
                out routeDeadlineFrequency, out routeDeadlineTicks);
            if (!routeDeadlineStarted)
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            UIntPtr ignored;
            return Result(SendMessageTimeoutW(window, WmClose, IntPtr.Zero, IntPtr.Zero,
                SmtoAbortIfHung, 1000, out ignored) != IntPtr.Zero,
                RuntimeCanonicalData.ExitCleanupFailure);
        }

        private RuntimeScenarioStepResult TimeoutRootChildTopology()
        {
            return Result(routeDeadlineStarted && WaitForExactTimeoutTopology(route,
                job, child.ProcessId, routeDeadlineStart, routeDeadlineFrequency,
                routeDeadlineTicks),
                RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult TimeoutObserved()
        {
            uint remaining = routeDeadlineStarted ? RemainingMilliseconds(routeDeadlineStart,
                routeDeadlineTicks, routeDeadlineFrequency) : 0;
            return Result(remaining != 0 &&
                WaitForSingleObject(child.Process, remaining) == WaitTimeout,
                RuntimeCanonicalData.ExitNativeCapabilityFailure);
        }

        private RuntimeScenarioStepResult InnerCleanup()
        {
            if (route.Route == ControllerRoute.TreeTimeout)
            {
                routeDeadlineStarted = TryStartDeadline(5000, out routeDeadlineStart,
                    out routeDeadlineFrequency, out routeDeadlineTicks);
                timeoutTerminationAttempted = routeDeadlineStarted;
                if (!routeDeadlineStarted ||
                        !TerminateJobObject(job, RuntimeCanonicalData.ExitTreeTimeout))
                    return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            }
            uint remaining = routeDeadlineStarted ? RemainingMilliseconds(routeDeadlineStart,
                routeDeadlineTicks, routeDeadlineFrequency) : 0;
            if (remaining == 0 || WaitForSingleObject(child.Process, remaining) != WaitObject0 ||
                    !WaitForJobEmptyUntil(job, routeDeadlineStart, routeDeadlineFrequency,
                        routeDeadlineTicks))
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            uint exitCode;
            if (route.Route == ControllerRoute.UiSuccess &&
                    (!GetExitCodeProcess(child.Process, out exitCode) || exitCode != 0))
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            if (!ExactControllerTopology(route, 0, false, false) || !AllRelevantInputUp())
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            inputReleaseArmed = false;
            return RuntimeScenarioStepResult.Passed();
        }

        public RuntimeScenarioStepResult Cleanup()
        {
            if (cleanupCalled)
                return Failed(RuntimeCanonicalData.ExitCleanupFailure);
            cleanupCalled = true;
            bool exact = true;
            if (inputReleaseArmed)
            {
                Input[] release = new Input[] { releaseInput };
                exact = SendInput(1, release, Marshal.SizeOf(typeof(Input))) == 1 &&
                    AllRelevantInputUp() && exact;
                inputReleaseArmed = false;
            }
            if (childCreated && child.Process != IntPtr.Zero)
                exact = CleanupChild() && exact;
            if (child.Thread != IntPtr.Zero) CloseHandle(child.Thread);
            if (child.Process != IntPtr.Zero) CloseHandle(child.Process);
            if (job != IntPtr.Zero) CloseHandle(job);
            if (environment != IntPtr.Zero)
            {
                ZeroMemory(environment, EnvironmentByteLength(environment));
                Marshal.FreeHGlobal(environment);
                environment = IntPtr.Zero;
            }
            if (quotaAdjusted && !quotaRestored && callerToken != IntPtr.Zero)
            {
                quotaRestored = RestoreIncreaseQuota(callerToken, quotaOriginalAttributes);
                exact = quotaRestored && ExactTokenRelationship(callerToken, sourceToken,
                    primaryToken, false) && exact;
            }
            if (guardBefore != null && !guardsVerified)
            {
                ControllerGuardSnapshot observed;
                guardsVerified = CaptureGuards(out observed) && guardBefore.Exact(observed);
                exact = guardsVerified && exact;
            }
            if (bindingsCleanupRequired)
                exact = RebindAllInputs() && exact;
            if (!outputsAccepted)
            {
                if (workerEvidencePublished)
                    exact = DeleteRelativeOutput("SyntheticLauncherWorkerEvidence.v1.json") && exact;
                if (completeBmpPublished)
                    exact = DeleteRelativeOutput(RuntimeCanonicalData.CompleteBmpName) && exact;
                if (readyBmpPublished)
                    exact = DeleteRelativeOutput(RuntimeCanonicalData.ReadyBmpName) && exact;
            }
            ZeroBytes(readyOne); ZeroBytes(readyTwo);
            ZeroBytes(completeOne); ZeroBytes(completeTwo);
            ZeroBytes(readyBmp); ZeroBytes(completeBmp);
            if (primaryToken != IntPtr.Zero) CloseHandle(primaryToken);
            if (sourceToken != IntPtr.Zero) CloseHandle(sourceToken);
            if (callerToken != IntPtr.Zero) CloseHandle(callerToken);
            if (launchBinding != IntPtr.Zero && launchBinding != new IntPtr(-1))
                CloseHandle(launchBinding);
            GC.KeepAlive(lease);
            return Result(exact, RuntimeCanonicalData.ExitCleanupFailure);
        }

        private bool CleanupChild()
        {
            bool processExited = WaitForSingleObject(child.Process, 0) == WaitObject0;
            bool jobEmpty = !childAssigned || JobIsEmptyNow(job);
            if (processExited && jobEmpty) return true;
            long cleanupStart;
            long cleanupFrequency;
            long cleanupDeadline;
            bool reuseTimeoutDeadline = route.Route == ControllerRoute.TreeTimeout &&
                timeoutTerminationAttempted && routeDeadlineStarted;
            if (reuseTimeoutDeadline)
            {
                cleanupStart = routeDeadlineStart;
                cleanupFrequency = routeDeadlineFrequency;
                cleanupDeadline = routeDeadlineTicks;
            }
            else if (!TryStartDeadline(5000, out cleanupStart, out cleanupFrequency,
                    out cleanupDeadline))
                return false;
            if (RemainingMilliseconds(cleanupStart, cleanupDeadline, cleanupFrequency) == 0)
                return false;
            bool stopped = childAssigned ? TerminateJobObject(job,
                RuntimeCanonicalData.ExitCleanupFailure) : TerminateProcess(child.Process,
                RuntimeCanonicalData.ExitCleanupFailure);
            if (!stopped) return false;
            uint processWait = RemainingMilliseconds(cleanupStart, cleanupDeadline,
                cleanupFrequency);
            processExited = processWait != 0 &&
                WaitForSingleObject(child.Process, processWait) == WaitObject0;
            jobEmpty = !childAssigned || WaitForJobEmptyUntil(job, cleanupStart,
                cleanupFrequency, cleanupDeadline);
            return processExited && jobEmpty;
        }

        private static RuntimeScenarioStepResult Result(bool succeeded, int failureExit)
        {
            return succeeded ? RuntimeScenarioStepResult.Passed() : Failed(failureExit);
        }

        private static RuntimeScenarioStepResult Failed(int exitCode)
        {
            return RuntimeScenarioStepResult.Failed(exitCode);
        }

        private static bool TryAcquireLimitedExplorerToken(out IntPtr sourceToken,
            out IntPtr primaryToken, out IntPtr callerToken)
        {
            sourceToken = IntPtr.Zero;
            primaryToken = IntPtr.Zero;
            callerToken = IntPtr.Zero;
            IntPtr shell = GetShellWindow();
            if (shell == IntPtr.Zero)
                return false;
            uint processId;
            GetWindowThreadProcessId(shell, out processId);
            IntPtr process = OpenProcess(ProcessQueryLimitedInformation, false, processId);
            if (process == IntPtr.Zero)
                return false;
            try
            {
                StringBuilder image = new StringBuilder(32768);
                int size = image.Capacity;
                StringBuilder windows = new StringBuilder(32768);
                if (!QueryFullProcessImageNameW(process, 0, image, ref size) ||
                        GetWindowsDirectoryW(windows, windows.Capacity) == 0 ||
                        !String.Equals(image.ToString(), windows.ToString() + "\\explorer.exe",
                            StringComparison.OrdinalIgnoreCase))
                    return false;
                if (!OpenProcessToken(process, TokenQuery | TokenDuplicate, out sourceToken))
                    return false;
                if (!OpenProcessToken(GetCurrentProcess(), TokenQuery | TokenAdjustPrivileges,
                        out callerToken))
                    return false;
                if (!ExactTokenRelationship(callerToken, sourceToken, IntPtr.Zero, false))
                    return false;
                SecurityAttributes attributes = new SecurityAttributes();
                attributes.Length = Marshal.SizeOf(typeof(SecurityAttributes));
                if (!DuplicateTokenEx(sourceToken, TokenQuery | TokenAssignPrimary |
                        TokenDuplicate,
                        ref attributes, 2, 1,
                        out primaryToken))
                    return false;
                uint shellSession;
                uint currentSession;
                return ProcessIdToSessionId(processId, out shellSession) &&
                    ProcessIdToSessionId(GetCurrentProcessId(), out currentSession) &&
                    shellSession == currentSession && shellSession == WTSGetActiveConsoleSessionId();
            }
            finally { CloseHandle(process); }
        }

        private static bool EnableIncreaseQuota(IntPtr token, out uint originalAttributes,
            out bool adjustmentApplied)
        {
            originalAttributes = 0;
            adjustmentApplied = false;
            Luid luid;
            if (!LookupPrivilegeValueW(null, "SeIncreaseQuotaPrivilege", out luid))
                return false;
            if (!TryPrivilegeAttributes(token, luid, out originalAttributes) ||
                    (originalAttributes & 0x2) != 0)
                return false;
            TokenPrivileges privileges = new TokenPrivileges();
            privileges.Count = 1;
            privileges.Luid = luid;
            privileges.Attributes = 2;
            if (!AdjustTokenPrivileges(token, false, ref privileges, 0, IntPtr.Zero,
                    IntPtr.Zero) || Marshal.GetLastWin32Error() != 0)
                return false;
            adjustmentApplied = true;
            return PrivilegeAttributes(token, luid) == (originalAttributes | 0x2);
        }

        private static bool RestoreIncreaseQuota(IntPtr token, uint originalAttributes)
        {
            Luid luid;
            if (!LookupPrivilegeValueW(null, "SeIncreaseQuotaPrivilege", out luid))
                return false;
            TokenPrivileges privileges = new TokenPrivileges();
            privileges.Count = 1;
            privileges.Luid = luid;
            privileges.Attributes = originalAttributes;
            return AdjustTokenPrivileges(token, false, ref privileges, 0, IntPtr.Zero,
                IntPtr.Zero) && Marshal.GetLastWin32Error() == 0 &&
                PrivilegeAttributes(token, luid) == originalAttributes;
        }

        private static bool ExactTokenRelationship(IntPtr caller, IntPtr source,
            IntPtr primary, bool quotaEnabled)
        {
            bool callerAdministrator;
            bool sourceAdministrator;
            if (!TryAdministratorEnabled(caller, out callerAdministrator) ||
                    !TryAdministratorEnabled(source, out sourceAdministrator))
                return false;
            if (caller == IntPtr.Zero || source == IntPtr.Zero ||
                    TokenInteger(caller, TokenElevationTypeInformation) != 2 ||
                    TokenInteger(caller, TokenElevationInformation) != 1 ||
                    TokenIntegrityRid(caller) != 0x3000 || !callerAdministrator ||
                    TokenInteger(source, TokenElevationTypeInformation) != 3 ||
                    TokenInteger(source, TokenElevationInformation) != 0 ||
                    TokenIntegrityRid(source) != 0x2000 || sourceAdministrator ||
                    !IsTokenRestricted(source) || !SameTokenUser(caller, source) ||
                    TokenInteger(caller, TokenSessionIdInformation) !=
                        TokenInteger(source, TokenSessionIdInformation) ||
                    (uint)TokenInteger(source, TokenSessionIdInformation) !=
                        WTSGetActiveConsoleSessionId() ||
                    !SameAuthentication(caller, source) || !ThreadTokenAbsent())
                return false;
            Luid quota;
            Luid impersonate;
            Luid assignPrimary;
            uint quotaAttributes;
            uint impersonateAttributes;
            uint ignored;
            if (!LookupPrivilegeValueW(null, "SeIncreaseQuotaPrivilege", out quota) ||
                    !LookupPrivilegeValueW(null, "SeImpersonatePrivilege", out impersonate) ||
                    !LookupPrivilegeValueW(null, "SeAssignPrimaryTokenPrivilege",
                        out assignPrimary) ||
                    !TryPrivilegeAttributes(caller, quota, out quotaAttributes) ||
                    ((quotaAttributes & 0x2) != 0) != quotaEnabled ||
                    !TryPrivilegeAttributes(caller, impersonate, out impersonateAttributes) ||
                    (impersonateAttributes & 0x2) == 0 ||
                    TryPrivilegeAttributes(caller, assignPrimary, out ignored) ||
                    TryPrivilegeAttributes(source, assignPrimary, out ignored))
                return false;
            IntPtr callerLinked = IntPtr.Zero;
            IntPtr sourceLinked = IntPtr.Zero;
            try
            {
                if (!TryLinkedToken(caller, out callerLinked) ||
                        !TryLinkedToken(source, out sourceLinked) ||
                        !SameTokenId(callerLinked, source) ||
                        !SameTokenId(sourceLinked, caller) ||
                        TokenInteger(callerLinked, TokenElevationTypeInformation) != 3 ||
                        TokenInteger(sourceLinked, TokenElevationTypeInformation) != 2)
                    return false;
            }
            finally
            {
                if (callerLinked != IntPtr.Zero) CloseHandle(callerLinked);
                if (sourceLinked != IntPtr.Zero) CloseHandle(sourceLinked);
            }
            if (primary == IntPtr.Zero)
                return true;
            bool primaryAdministrator;
            if (!TryAdministratorEnabled(primary, out primaryAdministrator))
                return false;
            return TokenInteger(primary, TokenElevationTypeInformation) == 3 &&
                TokenInteger(primary, TokenElevationInformation) == 0 &&
                TokenIntegrityRid(primary) == 0x2000 && !primaryAdministrator &&
                IsTokenRestricted(primary) && SameTokenUser(source, primary) &&
                SameAuthentication(source, primary) &&
                TokenInteger(source, TokenSessionIdInformation) ==
                    TokenInteger(primary, TokenSessionIdInformation) &&
                EqualBytes(TokenBytes(source, TokenPrivilegesInformation),
                    TokenBytes(primary, TokenPrivilegesInformation));
        }

        private static bool ThreadTokenAbsent()
        {
            IntPtr token;
            if (OpenThreadToken(GetCurrentThread(), TokenQuery, true, out token))
            {
                CloseHandle(token);
                return false;
            }
            return Marshal.GetLastWin32Error() == 1008;
        }

        private static bool TryLinkedToken(IntPtr token, out IntPtr linked)
        {
            linked = IntPtr.Zero;
            IntPtr buffer;
            int length;
            if (!TryTokenBuffer(token, TokenLinkedTokenInformation, out buffer, out length))
                return false;
            try
            {
                if (length < IntPtr.Size) return false;
                linked = Marshal.ReadIntPtr(buffer);
                return linked != IntPtr.Zero;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool SameTokenId(IntPtr first, IntPtr second)
        {
            TokenStatistics left;
            TokenStatistics right;
            return TryTokenStatistics(first, out left) && TryTokenStatistics(second, out right) &&
                EqualLuid(left.TokenId, right.TokenId) &&
                EqualLuid(left.AuthenticationId, right.AuthenticationId);
        }

        private static bool SameAuthentication(IntPtr first, IntPtr second)
        {
            TokenStatistics left;
            TokenStatistics right;
            return TryTokenStatistics(first, out left) && TryTokenStatistics(second, out right) &&
                EqualLuid(left.AuthenticationId, right.AuthenticationId);
        }

        private static bool TryTokenStatistics(IntPtr token, out TokenStatistics statistics)
        {
            statistics = new TokenStatistics();
            IntPtr buffer;
            int length;
            if (!TryTokenBuffer(token, TokenStatisticsInformation, out buffer, out length))
                return false;
            try
            {
                if (length < Marshal.SizeOf(typeof(TokenStatistics))) return false;
                statistics = (TokenStatistics)Marshal.PtrToStructure(buffer,
                    typeof(TokenStatistics));
                return true;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool SameTokenUser(IntPtr first, IntPtr second)
        {
            IntPtr firstBuffer;
            IntPtr secondBuffer;
            int firstLength;
            int secondLength;
            if (!TryTokenBuffer(first, TokenUserInformation, out firstBuffer, out firstLength))
                return false;
            try
            {
                if (!TryTokenBuffer(second, TokenUserInformation, out secondBuffer,
                        out secondLength))
                    return false;
                try
                {
                    SidAndAttributes left = (SidAndAttributes)Marshal.PtrToStructure(firstBuffer,
                        typeof(SidAndAttributes));
                    SidAndAttributes right = (SidAndAttributes)Marshal.PtrToStructure(secondBuffer,
                        typeof(SidAndAttributes));
                    return EqualSid(left.Sid, right.Sid);
                }
                finally { Marshal.FreeHGlobal(secondBuffer); }
            }
            finally { Marshal.FreeHGlobal(firstBuffer); }
        }

        private static bool TryAdministratorEnabled(IntPtr token, out bool enabled)
        {
            enabled = false;
            uint sidSize = 68;
            IntPtr administrator = Marshal.AllocHGlobal((int)sidSize);
            try
            {
                if (!CreateWellKnownSid(26, IntPtr.Zero, administrator, ref sidSize))
                    return false;
                IntPtr groups;
                int length;
                if (!TryTokenBuffer(token, TokenGroupsInformation, out groups, out length))
                    return false;
                try
                {
                    int count = Marshal.ReadInt32(groups);
                    int stride = Marshal.SizeOf(typeof(SidAndAttributes));
                    int offset = IntPtr.Size == 8 ? 8 : 4;
                    if (count < 0 || count > 4096 || offset + count * stride > length)
                        return false;
                    for (int index = 0; index < count; index++)
                    {
                        IntPtr itemPointer = new IntPtr(groups.ToInt64() + offset + index * stride);
                        SidAndAttributes item = (SidAndAttributes)Marshal.PtrToStructure(itemPointer,
                            typeof(SidAndAttributes));
                        if (EqualSid(item.Sid, administrator))
                        {
                            enabled = (item.Attributes & 0x4) != 0 &&
                                (item.Attributes & 0x10) == 0;
                            return true;
                        }
                    }
                    enabled = false;
                    return true;
                }
                finally { Marshal.FreeHGlobal(groups); }
            }
            finally { Marshal.FreeHGlobal(administrator); }
        }

        private static int TokenIntegrityRid(IntPtr token)
        {
            IntPtr buffer;
            int length;
            if (!TryTokenBuffer(token, TokenIntegrityLevelInformation, out buffer, out length))
                return -1;
            try
            {
                SidAndAttributes label = (SidAndAttributes)Marshal.PtrToStructure(buffer,
                    typeof(SidAndAttributes));
                IntPtr countPointer = GetSidSubAuthorityCount(label.Sid);
                if (countPointer == IntPtr.Zero) return -1;
                byte count = Marshal.ReadByte(countPointer);
                if (count == 0) return -1;
                IntPtr rid = GetSidSubAuthority(label.Sid, (uint)(count - 1));
                return rid == IntPtr.Zero ? -1 : Marshal.ReadInt32(rid);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static int TokenInteger(IntPtr token, int informationClass)
        {
            IntPtr buffer;
            int length;
            if (!TryTokenBuffer(token, informationClass, out buffer, out length))
                return -1;
            try { return length < 4 ? -1 : Marshal.ReadInt32(buffer); }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static uint PrivilegeAttributes(IntPtr token, Luid luid)
        {
            uint value;
            return TryPrivilegeAttributes(token, luid, out value) ? value : UInt32.MaxValue;
        }

        private static bool TryPrivilegeAttributes(IntPtr token, Luid luid, out uint attributes)
        {
            attributes = 0;
            byte[] bytes = TokenBytes(token, TokenPrivilegesInformation);
            if (bytes == null || bytes.Length < 4) return false;
            int count = BitConverter.ToInt32(bytes, 0);
            int stride = Marshal.SizeOf(typeof(LuidAndAttributes));
            if (count < 0 || count > 4096 || 4 + count * stride > bytes.Length)
                return false;
            for (int index = 0; index < count; index++)
            {
                int offset = 4 + index * stride;
                Luid observed = new Luid();
                observed.LowPart = BitConverter.ToUInt32(bytes, offset);
                observed.HighPart = BitConverter.ToInt32(bytes, offset + 4);
                if (EqualLuid(observed, luid))
                {
                    attributes = BitConverter.ToUInt32(bytes, offset + 8);
                    return true;
                }
            }
            return false;
        }

        private static byte[] TokenBytes(IntPtr token, int informationClass)
        {
            IntPtr buffer;
            int length;
            if (!TryTokenBuffer(token, informationClass, out buffer, out length))
                return null;
            try
            {
                byte[] value = new byte[length];
                Marshal.Copy(buffer, value, 0, length);
                return value;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool TryTokenBuffer(IntPtr token, int informationClass,
            out IntPtr buffer, out int length)
        {
            buffer = IntPtr.Zero;
            length = 0;
            GetTokenInformation(token, informationClass, IntPtr.Zero, 0, out length);
            if (length <= 0 || length > 1048576) return false;
            buffer = Marshal.AllocHGlobal(length);
            if (!GetTokenInformation(token, informationClass, buffer, length, out length))
            {
                Marshal.FreeHGlobal(buffer);
                buffer = IntPtr.Zero;
                return false;
            }
            return true;
        }

        private static bool EqualLuid(Luid first, Luid second)
        {
            return first.LowPart == second.LowPart && first.HighPart == second.HighPart;
        }

        private static bool RequireRegistryDenial(IntPtr token)
        {
            if (!ImpersonateLoggedOnUser(token))
                return false;
            int result;
            IntPtr key;
            bool reverted;
            try
            {
                result = RegOpenKeyExA(new IntPtr(unchecked((int)0x80000002)),
                    "SOFTWARE\\Sports Interactive Ltd\\Championship Manager 01-02",
                    0, KeyAllAccess, out key);
                if (result == 0) RegCloseKey(key);
            }
            finally
            {
                reverted = RevertToSelf();
            }
            return reverted && result == ErrorAccessDenied;
        }

        private bool CaptureGuards(out ControllerGuardSnapshot result)
        {
            result = null;
            string acceptedHost;
            string attemptRoot;
            string installedTree;
            string virtualStore;
            long registryLastWrite;
            if (!CanonicalAbsolutePath(privateConfiguration.AcceptedHostGuard, false) ||
                    !CanonicalAbsolutePath(privateConfiguration.AttemptRootGuard, false) ||
                    !CanonicalAbsolutePath(privateConfiguration.InstalledTreeGuard, false) ||
                    !CanonicalAbsolutePath(privateConfiguration.VirtualStoreGuard, true) ||
                    !CaptureAcceptedHost(privateConfiguration.AcceptedHostGuard, out acceptedHost) ||
                    !CaptureTree(privateConfiguration.AttemptRootGuard, false, out attemptRoot) ||
                    !CaptureTree(privateConfiguration.InstalledTreeGuard, false,
                        out installedTree) ||
                    !CaptureTree(privateConfiguration.VirtualStoreGuard, true,
                        out virtualStore) ||
                    !CaptureRegistryLastWrite(out registryLastWrite))
                return false;
            string parent = StripFinalPrefix(snapshot.ParentFinalPath);
            if (!String.Equals(parent, privateConfiguration.AttemptRootGuard,
                    StringComparison.OrdinalIgnoreCase))
                return false;
            result = new ControllerGuardSnapshot(acceptedHost, attemptRoot, installedTree,
                virtualStore, registryLastWrite);
            return true;
        }

        private static bool CanonicalAbsolutePath(string path, bool allowAbsent)
        {
            StringBuilder full = new StringBuilder(32768);
            IntPtr filePart;
            uint fullLength = GetFullPathNameW(path, full.Capacity, full, out filePart);
            if (fullLength == 0 || fullLength >= full.Capacity ||
                    !String.Equals(full.ToString(), path, StringComparison.OrdinalIgnoreCase))
                return false;
            StringBuilder longPath = new StringBuilder(32768);
            uint longLength = GetLongPathNameW(path, longPath, longPath.Capacity);
            if (longLength == 0)
            {
                int error = Marshal.GetLastWin32Error();
                return allowAbsent && (error == 2 || error == 3);
            }
            return longLength < longPath.Capacity && String.Equals(longPath.ToString(), path,
                StringComparison.OrdinalIgnoreCase);
        }

        private static bool CaptureAcceptedHost(string path, out string identity)
        {
            identity = null;
            string record;
            string contentHash;
            if (!CapturePathRecord(path, false, "accepted-host", out record,
                    out contentHash))
                return false;
            if (!String.Equals(contentHash,
                    "96e38bb7932e1acb64aa7c9a33012f3425318b3a8e3aaf7ce98aaf8e1cd27659",
                    StringComparison.Ordinal))
                return false;
            IntPtr handle = OpenAbsolute(path, false);
            if (handle == new IntPtr(-1)) return false;
            try
            {
                long size;
                if (!GetFileSizeEx(handle, out size) || size != 3310) return false;
            }
            finally { CloseHandle(handle); }
            identity = record;
            return true;
        }

        private static bool CaptureRegistryLastWrite(out long lastWrite)
        {
            lastWrite = 0;
            IntPtr key;
            int opened = RegOpenKeyExA(new IntPtr(unchecked((int)0x80000002)),
                "SOFTWARE\\Sports Interactive Ltd\\Championship Manager 01-02",
                0, 0x00020019, out key);
            if (opened != 0) return false;
            try
            {
                return RegQueryInfoKeyA(key, null, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero,
                    IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero,
                    IntPtr.Zero, out lastWrite) == 0;
            }
            finally { RegCloseKey(key); }
        }

        private static bool CaptureTree(string root, bool allowAbsent, out string digest)
        {
            digest = null;
            IntPtr rootHandle = OpenAbsolute(root, true);
            if (rootHandle == new IntPtr(-1))
            {
                int error = Marshal.GetLastWin32Error();
                if (allowAbsent && (error == 2 || error == 3))
                {
                    digest = "absent";
                    return true;
                }
                return false;
            }
            CloseHandle(rootHandle);
            List<string> records = new List<string>();
            if (!WalkTree(root, "", records, 0) || records.Count == 0 ||
                    records.Count > 100000)
                return false;
            records.Sort(StringComparer.Ordinal);
            StringBuilder canonical = new StringBuilder();
            for (int index = 0; index < records.Count; index++)
                canonical.Append(records[index]).Append('\n');
            digest = Sha256(Encoding.UTF8.GetBytes(canonical.ToString()));
            return true;
        }

        private static bool WalkTree(string root, string relative, List<string> records,
            int depth)
        {
            if (depth > 64 || records.Count > 100000) return false;
            string current = relative.Length == 0 ? root : root + "\\" + relative;
            string record;
            string ignored;
            if (!CapturePathRecord(current, true, relative.Length == 0 ? "." : relative,
                    out record, out ignored))
                return false;
            records.Add(record);
            FindData first;
            IntPtr search = FindFirstFileW(current + "\\*", out first);
            if (search == new IntPtr(-1)) return false;
            List<string> children = new List<string>();
            try
            {
                FindData value = first;
                while (true)
                {
                    if (!String.Equals(value.FileName, ".", StringComparison.Ordinal) &&
                            !String.Equals(value.FileName, "..", StringComparison.Ordinal))
                    {
                        if (value.FileName == null || value.FileName.Length == 0 ||
                                (value.FileAttributes & 0x400) != 0)
                            return false;
                        children.Add(value.FileName);
                    }
                    if (!FindNextFileW(search, out value))
                    {
                        if (Marshal.GetLastWin32Error() != 18) return false;
                        break;
                    }
                }
            }
            finally { FindClose(search); }
            children.Sort(StringComparer.Ordinal);
            for (int index = 0; index < children.Count; index++)
            {
                string childRelative = relative.Length == 0 ? children[index] :
                    relative + "\\" + children[index];
                string childPath = root + "\\" + childRelative;
                uint attributes = GetFileAttributesW(childPath);
                if (attributes == 0xffffffff ||
                        (attributes & (0x400 | 0x800 | 0x4000)) != 0)
                    return false;
                if ((attributes & 0x10) != 0)
                {
                    if (!WalkTree(root, childRelative, records, depth + 1)) return false;
                }
                else
                {
                    if (!CapturePathRecord(childPath, false, childRelative, out record,
                            out ignored))
                        return false;
                    records.Add(record);
                }
            }
            return true;
        }

        private static bool CapturePathRecord(string path, bool directory, string relative,
            out string record, out string contentHash)
        {
            record = null;
            contentHash = null;
            IntPtr handle = OpenAbsolute(path, directory);
            if (handle == new IntPtr(-1)) return false;
            try
            {
                ByHandleFileInformation information;
                if (!GetFileInformationByHandle(handle, out information) ||
                        ((information.FileAttributes & 0x10) != 0) != directory ||
                        (information.FileAttributes & (0x400 | 0x800 | 0x4000)) != 0 ||
                        (!directory && information.NumberOfLinks != 1) ||
                        !FinalPathMatches(FinalPath(handle), path) ||
                        (directory && !HasNoNamedDataStreams(handle)) ||
                        (!directory && !OnlyUnnamedStream(handle)))
                    return false;
                byte[] descriptor = SecurityDescriptor(handle);
                if (descriptor.Length == 0) return false;
                string descriptorHash = Sha256(descriptor);
                Array.Clear(descriptor, 0, descriptor.Length);
                long size = ((long)information.FileSizeHigh << 32) | information.FileSizeLow;
                if (!directory)
                {
                    if (!HashOpenFile(handle, out contentHash)) return false;
                }
                else contentHash = "directory";
                record = relative + "|" + information.FileAttributes.ToString("x8",
                    CultureInfo.InvariantCulture) + "|" +
                    information.VolumeSerialNumber.ToString("x8", CultureInfo.InvariantCulture) +
                    "|" + information.FileIndexHigh.ToString("x8",
                        CultureInfo.InvariantCulture) + information.FileIndexLow.ToString("x8",
                        CultureInfo.InvariantCulture) + "|" +
                    information.CreationTime.ToString(CultureInfo.InvariantCulture) + "|" +
                    information.LastWriteTime.ToString(CultureInfo.InvariantCulture) + "|" +
                    size.ToString(CultureInfo.InvariantCulture) + "|" + descriptorHash + "|" +
                    contentHash;
                return true;
            }
            finally { CloseHandle(handle); }
        }

        private static IntPtr OpenAbsolute(string path, bool directory)
        {
            uint flags = 0x00200000 | (directory ? 0x02000000U : 0U);
            return CreateFileW(path, 0x80000000 | 0x0080 | 0x00020000 | 0x00100000,
                1, IntPtr.Zero, 3, flags, IntPtr.Zero);
        }

        private static bool HashOpenFile(IntPtr handle, out string digest)
        {
            digest = null;
            using (System.Security.Cryptography.SHA256 hash =
                    System.Security.Cryptography.SHA256.Create())
            {
                byte[] block = new byte[65536];
                while (true)
                {
                    uint read;
                    if (!ReadFile(handle, block, (uint)block.Length, out read, IntPtr.Zero))
                        return false;
                    if (read == 0) break;
                    hash.TransformBlock(block, 0, (int)read, null, 0);
                }
                hash.TransformFinalBlock(new byte[0], 0, 0);
                digest = Hex(hash.Hash);
                Array.Clear(block, 0, block.Length);
                return true;
            }
        }

        private static string Sha256(byte[] value)
        {
            using (System.Security.Cryptography.SHA256 hash =
                    System.Security.Cryptography.SHA256.Create())
                return Hex(hash.ComputeHash(value));
        }

        private static string Hex(byte[] value)
        {
            StringBuilder text = new StringBuilder(value.Length * 2);
            for (int index = 0; index < value.Length; index++)
                text.Append(value[index].ToString("x2", CultureInfo.InvariantCulture));
            return text.ToString();
        }

        private static bool FinalPathMatches(string observed, string expected)
        {
            return String.Equals(StripFinalPrefix(observed), expected,
                StringComparison.OrdinalIgnoreCase);
        }

        private static string StripFinalPrefix(string value)
        {
            return value != null && value.StartsWith("\\\\?\\", StringComparison.Ordinal) ?
                value.Substring(4) : value;
        }

        private static IntPtr BuildEnvironmentBlock(string parent, uint nonce)
        {
            StringBuilder windows = new StringBuilder(32768);
            if (GetWindowsDirectoryW(windows, windows.Capacity) == 0)
                return IntPtr.Zero;
            string temporary = parent + "\\temp";
            string cwdHash = LowerSha256Utf16(parent);
            string[] values = {
                "CM0102_SYNTHETIC_CWD_SHA256=" + cwdHash,
                "CM0102_SYNTHETIC_INPUT_NONCE=" + nonce.ToString("x8"),
                "SystemRoot=" + windows.ToString(), "TEMP=" + temporary,
                "TMP=" + temporary, "WINDIR=" + windows.ToString()
            };
            Array.Sort(values, StringComparer.OrdinalIgnoreCase);
            string block = String.Join("\0", values) + "\0\0";
            byte[] bytes = Encoding.Unicode.GetBytes(block);
            IntPtr result = Marshal.AllocHGlobal(bytes.Length);
            Marshal.Copy(bytes, 0, result, bytes.Length);
            return result;
        }

        private uint NonceFromPrivateConfiguration()
        {
            byte[] bytes = snapshot.Objects["SyntheticLauncherController.private.v1.json"].Bytes;
            using (System.Security.Cryptography.SHA256 hash =
                    System.Security.Cryptography.SHA256.Create())
            {
                byte[] value = hash.ComputeHash(bytes);
                uint nonce = BitConverter.ToUInt32(value, 0);
                return nonce == 0 ? 1U : nonce;
            }
        }

        private static string LowerSha256Utf16(string value)
        {
            using (System.Security.Cryptography.SHA256 hash =
                    System.Security.Cryptography.SHA256.Create())
            {
                byte[] digest = hash.ComputeHash(Encoding.Unicode.GetBytes(value));
                StringBuilder result = new StringBuilder(64);
                for (int index = 0; index < digest.Length; index++)
                    result.Append(digest[index].ToString("x2"));
                return result.ToString();
            }
        }

        private static bool ConfigureInnerJob(IntPtr job, ControllerRouteFacts route)
        {
            JobObjectExtendedLimitInformation information =
                new JobObjectExtendedLimitInformation();
            information.BasicLimitInformation.LimitFlags = LimitActiveProcess |
                LimitProcessMemory | LimitJobMemory | LimitKillOnJobClose;
            information.BasicLimitInformation.ActiveProcessLimit =
                route.Route == ControllerRoute.TreeTimeout ? 2U : 1U;
            information.ProcessMemoryLimit = new UIntPtr(ProcessMemoryLimit);
            information.JobMemoryLimit = new UIntPtr(route.Route == ControllerRoute.TreeTimeout ?
                TimeoutJobMemoryLimit : UiJobMemoryLimit);
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
                uint expectedActive = route.Route == ControllerRoute.TreeTimeout ? 2U : 1U;
                ulong expectedJobMemory = route.Route == ControllerRoute.TreeTimeout ?
                    TimeoutJobMemoryLimit : UiJobMemoryLimit;
                uint handleFlags;
                return observed.BasicLimitInformation.LimitFlags ==
                        (LimitActiveProcess | LimitProcessMemory | LimitJobMemory |
                            LimitKillOnJobClose) &&
                    observed.BasicLimitInformation.ActiveProcessLimit == expectedActive &&
                    observed.ProcessMemoryLimit.ToUInt64() == ProcessMemoryLimit &&
                    observed.JobMemoryLimit.ToUInt64() == expectedJobMemory &&
                    GetHandleInformation(job, out handleFlags) && (handleFlags & 1) == 0;
            }
            finally { Marshal.FreeHGlobal(buffer); }
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
                BasicAccountingInformation value = (BasicAccountingInformation)
                    Marshal.PtrToStructure(buffer, typeof(BasicAccountingInformation));
                active = value.ActiveProcesses;
                return true;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool WaitForJobEmptyUntil(IntPtr job, long start, long frequency,
            long deadline)
        {
            while (true)
            {
                long before;
                if (!QueryPerformanceCounter(out before) ||
                        !RuntimeDeadlineMath.CanProbe(start, deadline, before, frequency))
                    return false;
                uint remaining = RemainingMilliseconds(start, deadline, frequency);
                uint active;
                if (!TryGetJobActiveProcesses(job, out active) ||
                        (remaining = RemainingMilliseconds(start, deadline, frequency)) == 0)
                    return false;
                if (active == 0) return true;
                Sleep(Math.Min(50U, remaining));
            }
        }

        private static bool WaitForExactTimeoutTopology(ControllerRouteFacts route,
            IntPtr job, uint rootProcessId, long start, long frequency, long deadline)
        {
            while (true)
            {
                long before;
                if (!QueryPerformanceCounter(out before) ||
                        !RuntimeDeadlineMath.CanProbe(start, deadline, before, frequency))
                    return false;
                uint childProcessId;
                if (ExactControllerTopology(route, rootProcessId, true, true,
                        out childProcessId))
                {
                    if (RemainingMilliseconds(start, deadline, frequency) == 0)
                        return false;
                    if (ExactJobProcessIds(job, rootProcessId, childProcessId))
                        return RemainingMilliseconds(start, deadline, frequency) != 0;
                }
                uint remaining = RemainingMilliseconds(start, deadline, frequency);
                if (remaining == 0) return false;
                Sleep(Math.Min(50U, remaining));
            }
        }

        private static bool ExactControllerTopology(ControllerRouteFacts route,
            uint targetProcessId, bool targetPresent, bool timeoutChildPresent)
        {
            uint ignored;
            return ExactControllerTopology(route, targetProcessId, targetPresent,
                timeoutChildPresent, out ignored);
        }

        private static bool ExactControllerTopology(ControllerRouteFacts route,
            uint targetProcessId, bool targetPresent, bool timeoutChildPresent,
            out uint observedTimeoutChildProcessId)
        {
            observedTimeoutChildProcessId = 0;
            if (route == null || (timeoutChildPresent &&
                    route.Route != ControllerRoute.TreeTimeout))
                return false;
            string[] names = {
                "cm0102.exe", "SyntheticLauncherSupervisor.exe",
                "SyntheticLauncherController.exe", "SyntheticLauncherFixture.exe",
                "SyntheticLauncherTimeoutFixture.exe", "SyntheticLauncherTimeoutChild.exe",
                "SyntheticLauncherLockedPreflight.exe"
            };
            int[] counts = new int[names.Length];
            uint supervisorProcessId = 0;
            uint controllerParent = 0;
            uint observedTargetParent = 0;
            uint timeoutChildParent = 0;
            uint observedTargetProcessId = 0;
            uint timeoutChildProcessId = 0;
            uint currentProcessId = GetCurrentProcessId();
            IntPtr processSnapshot = CreateToolhelp32Snapshot(SnapshotProcesses, 0);
            if (processSnapshot == new IntPtr(-1)) return false;
            bool complete = false;
            try
            {
                ProcessEntry entry = new ProcessEntry();
                entry.Size = (uint)Marshal.SizeOf(typeof(ProcessEntry));
                bool more = Process32FirstW(processSnapshot, ref entry);
                while (more)
                {
                    for (int index = 0; index < names.Length; index++)
                    {
                        if (!String.Equals(names[index], entry.ExecutableFile,
                                StringComparison.OrdinalIgnoreCase))
                            continue;
                        counts[index]++;
                        if (index == 1) supervisorProcessId = entry.ProcessId;
                        if (index == 2 && entry.ProcessId == currentProcessId)
                            controllerParent = entry.ParentProcessId;
                        if ((index == 3 || index == 4) &&
                                entry.ProcessId == targetProcessId)
                        {
                            observedTargetProcessId = entry.ProcessId;
                            observedTargetParent = entry.ParentProcessId;
                        }
                        if (index == 5)
                        {
                            timeoutChildProcessId = entry.ProcessId;
                            timeoutChildParent = entry.ParentProcessId;
                        }
                    }
                    more = Process32NextW(processSnapshot, ref entry);
                    if (!more) complete = Marshal.GetLastWin32Error() == 18;
                }
            }
            finally { CloseHandle(processSnapshot); }
            if (!complete) return false;
            if (counts[0] != 0 || counts[1] != 1 || counts[2] != 1 ||
                    supervisorProcessId == 0 || controllerParent != supervisorProcessId)
                return false;
            int targetIndex = route.Route == ControllerRoute.UiSuccess ? 3 : 4;
            for (int index = 3; index < counts.Length; index++)
            {
                int expected = targetPresent && index == targetIndex ? 1 :
                    timeoutChildPresent && index == 5 ? 1 : 0;
                if (counts[index] != expected) return false;
            }
            if (!targetPresent)
                return targetProcessId == 0 && !timeoutChildPresent;
            if (targetProcessId == 0 || observedTargetProcessId != targetProcessId ||
                    observedTargetParent != currentProcessId)
                return false;
            uint activeSession = WTSGetActiveConsoleSessionId();
            uint targetSession;
            if (!ProcessIdToSessionId(targetProcessId, out targetSession) ||
                    targetSession != activeSession)
                return false;
            if (!timeoutChildPresent) return true;
            uint childSession;
            bool exact = timeoutChildProcessId != 0 && timeoutChildParent == targetProcessId &&
                ProcessIdToSessionId(timeoutChildProcessId, out childSession) &&
                childSession == activeSession;
            if (exact) observedTimeoutChildProcessId = timeoutChildProcessId;
            return exact;
        }

        private static bool ExactJobProcessIds(IntPtr job, uint first, uint second)
        {
            int expected = second == 0 ? 1 : 2;
            int size = 8 + IntPtr.Size * 4;
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try
            {
                for (int index = 0; index < size; index++) Marshal.WriteByte(buffer, index, 0);
                uint returned;
                if (!QueryInformationJobObject(job, JobObjectBasicProcessIdListInformation,
                        buffer, (uint)size, out returned) || returned < 8 + IntPtr.Size * expected ||
                        Marshal.ReadInt32(buffer, 0) != expected ||
                        Marshal.ReadInt32(buffer, 4) != expected)
                    return false;
                uint one = unchecked((uint)Marshal.ReadIntPtr(buffer, 8).ToInt64());
                if (expected == 1) return one == first;
                uint two = unchecked((uint)Marshal.ReadIntPtr(buffer, 8 + IntPtr.Size).ToInt64());
                return (one == first && two == second) || (one == second && two == first);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool ExactSessionDesktop()
        {
            uint session;
            if (!ProcessIdToSessionId(GetCurrentProcessId(), out session) ||
                    session != WTSGetActiveConsoleSessionId())
                return false;
            IntPtr desktop = OpenInputDesktop(0, false, 0x0001);
            if (desktop == IntPtr.Zero) return false;
            try
            {
                int required;
                GetUserObjectInformationW(desktop, 2, IntPtr.Zero, 0, out required);
                if (required <= 2 || required > 1024) return false;
                IntPtr buffer = Marshal.AllocHGlobal(required);
                try
                {
                    return GetUserObjectInformationW(desktop, 2, buffer, required,
                        out required) && String.Equals(Marshal.PtrToStringUni(buffer), "Default",
                            StringComparison.Ordinal);
                }
                finally { Marshal.FreeHGlobal(buffer); }
            }
            finally { CloseDesktop(desktop); }
        }

        private static bool WaitForUniqueChildWindow(uint processId, long start,
            long frequency, long deadline, out IntPtr window)
        {
            window = IntPtr.Zero;
            while (true)
            {
                long before;
                if (!QueryPerformanceCounter(out before) ||
                        !RuntimeDeadlineMath.CanProbe(start, deadline, before, frequency))
                    return false;
                List<IntPtr> matches = new List<IntPtr>();
                if (!EnumWindows(delegate(IntPtr current, IntPtr parameter) {
                    uint owner;
                    GetWindowThreadProcessId(current, out owner);
                    if (owner == processId && IsWindowVisible(current) &&
                            GetWindow(current, 4) == IntPtr.Zero)
                        matches.Add(current);
                    return true;
                }, IntPtr.Zero)) return false;
                uint remaining = RemainingMilliseconds(start, deadline, frequency);
                if (remaining == 0) return false;
                if (matches.Count == 1) { window = matches[0]; return true; }
                if (matches.Count > 1) return false;
                Sleep(Math.Min(50U, remaining));
            }
        }

        private static bool TryStartDeadline(uint milliseconds, out long start,
            out long frequency, out long deadline)
        {
            start = 0;
            frequency = 0;
            deadline = 0;
            return QueryPerformanceFrequency(out frequency) && frequency > 0 &&
                QueryPerformanceCounter(out start) && RuntimeDeadlineMath.TryCreateDeadline(
                    start, frequency, milliseconds, out deadline);
        }

        private static uint RemainingMilliseconds(long start, long deadline, long frequency)
        {
            long now;
            return QueryPerformanceCounter(out now) ? RuntimeDeadlineMath.RemainingMilliseconds(
                start, deadline, now, frequency) : 0;
        }

        private static bool AllRelevantInputUp()
        {
            for (int key = 1; key <= 6; key++)
                if ((GetAsyncKeyState(key) & 0x8000) != 0) return false;
            return true;
        }

        private static bool StandardStreamsAbsent()
        {
            IntPtr output = GetStdHandle(-11);
            IntPtr error = GetStdHandle(-12);
            return (output == IntPtr.Zero || output == new IntPtr(-1)) &&
                (error == IntPtr.Zero || error == new IntPtr(-1));
        }

        private static Input[] FixedClick(Point point, uint nonce)
        {
            Input move = new Input();
            move.Type = 0;
            move.Mouse.X = point.X * 65535 / Math.Max(1, GetSystemMetrics(0) - 1);
            move.Mouse.Y = point.Y * 65535 / Math.Max(1, GetSystemMetrics(1) - 1);
            move.Mouse.MouseData = 0;
            move.Mouse.Flags = 0x8000 | 0x0001;
            move.Mouse.Time = 0;
            move.Mouse.ExtraInfo = new UIntPtr(nonce);
            Input down = move;
            down.Mouse.Flags = 0x8000 | 0x0002;
            Input up = move;
            up.Mouse.Flags = 0x8000 | 0x0004;
            return new Input[] { move, down, up };
        }

        private static bool CaptureExactClient(IntPtr window, Rect client, bool ready,
            out byte[] pixels)
        {
            pixels = null;
            IntPtr source = GetDC(IntPtr.Zero);
            if (source == IntPtr.Zero)
                return false;
            IntPtr target = CreateCompatibleDC(source);
            IntPtr bitmap = CreateCompatibleBitmap(source, client.Right, client.Bottom);
            if (target == IntPtr.Zero || bitmap == IntPtr.Zero)
            {
                if (bitmap != IntPtr.Zero) DeleteObject(bitmap);
                if (target != IntPtr.Zero) DeleteDC(target);
                ReleaseDC(IntPtr.Zero, source);
                return false;
            }
            IntPtr previous = SelectObject(target, bitmap);
            if (previous == IntPtr.Zero || previous == new IntPtr(-1))
            {
                DeleteObject(bitmap); DeleteDC(target); ReleaseDC(IntPtr.Zero, source);
                return false;
            }
            bool bitmapSelected = true;
            Point origin = new Point();
            try
            {
                if (!ClientToScreen(window, ref origin) || !BitBlt(target, 0, 0,
                        client.Right, client.Bottom, source, origin.X, origin.Y, Srccopy))
                    return false;
                IntPtr restored = SelectObject(target, previous);
                if (restored == IntPtr.Zero || restored == new IntPtr(-1))
                    return false;
                bitmapSelected = false;
                BitmapInfo information = new BitmapInfo();
                information.Header.Size = (uint)Marshal.SizeOf(typeof(BitmapInfoHeader));
                information.Header.Width = client.Right;
                information.Header.Height = -client.Bottom;
                information.Header.Planes = 1;
                information.Header.BitCount = 32;
                information.Header.Compression = 0;
                byte[] value = new byte[client.Right * client.Bottom * 4];
                if (GetDIBits(target, bitmap, 0, (uint)client.Bottom, value,
                        ref information, 0) != client.Bottom || !ExactPixelPlan(value, ready))
                {
                    ZeroBytes(value);
                    return false;
                }
                pixels = value;
                return true;
            }
            finally
            {
                if (bitmapSelected) SelectObject(target, previous);
                DeleteObject(bitmap);
                DeleteDC(target); ReleaseDC(IntPtr.Zero, source);
            }
        }

        private static bool ExactPixelPlan(byte[] value, bool ready)
        {
            int[,] colors = ready ? new int[,] {
                { 192, 32, 32 }, { 32, 64, 192 }, { 32, 160, 64 }, { 16, 24, 32 }
            } : new int[,] {
                { 24, 176, 80 }, { 224, 176, 24 }, { 128, 48, 192 }, { 32, 200, 216 }
            };
            if (value == null || value.Length != 320 * 240 * 4)
                return false;
            for (int y = 0; y < 240; y++)
            {
                for (int x = 0; x < 320; x++)
                {
                    int band = x / 80;
                    int offset = (y * 320 + x) * 4;
                    if (value[offset] != colors[band, 2] ||
                            value[offset + 1] != colors[band, 1] ||
                            value[offset + 2] != colors[band, 0])
                        return false;
                }
            }
            return true;
        }

        private static bool EqualBytes(byte[] first, byte[] second)
        {
            if (first == null || second == null || first.Length != second.Length)
                return false;
            for (int index = 0; index < first.Length; index++)
                if (first[index] != second[index]) return false;
            return true;
        }

        private static void ZeroBytes(byte[] value)
        {
            if (value == null) return;
            for (int index = 0; index < value.Length; index++) value[index] = 0;
        }

        private bool RebindAllInputs()
        {
            if (!RebindParent()) return false;
            foreach (KeyValuePair<string, ControllerBoundObject> item in snapshot.Objects)
            {
                IntPtr handle = OpenRelativeExisting(item.Key,
                    0x0001 | 0x0080 | 0x00020000 | 0x00100000);
                if (handle == new IntPtr(-1)) return false;
                try
                {
                    if (!ExactBoundObject(handle, item.Value, true)) return false;
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

        private bool ExactBoundObject(IntPtr handle, ControllerBoundObject expected,
            bool compareBytes)
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
            if (!compareBytes) return true;
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
            ZeroBytes(observed);
            return exact;
        }

        private bool ExactCreatedObject(IntPtr handle, string leaf, byte[] bytes)
        {
            ByHandleFileInformation information;
            string expectedPath = snapshot.ParentFinalPath + "\\" + leaf;
            ControllerBoundObject inheritedFrom = snapshot.Objects[
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

        private IntPtr OpenRelativeExisting(string leaf, uint access)
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
                    ref allocation, 0, 1, 1, 0x20 | 0x40 | 0x00200000,
                    IntPtr.Zero, 0);
                return status < 0 ? new IntPtr(-1) : handle;
            }
            finally
            {
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(text);
            }
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
                    FileReadAttributes | ReadControl | Synchronize, ref attributes,
                    out statusBlock, ref allocation, 0, 1, 1,
                    FileSynchronousIoNonAlert | FileNonDirectoryFile | FileOpenReparsePoint,
                    IntPtr.Zero, 0);
                if (status >= 0)
                {
                    CloseHandle(handle);
                    handle = new IntPtr(-1);
                    return false;
                }
                return status == unchecked((int)0xc0000034);
            }
            finally
            {
                if (handle != new IntPtr(-1)) CloseHandle(handle);
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(text);
            }
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

        private bool PublishWorkerEvidence(ControllerRouteFacts route, int result)
        {
            if (result != route.ExpectedExit)
                return false;
            bool timeout = route.Route == ControllerRoute.TreeTimeout;
            string artifacts = timeout ?
                "{\"complete_bmp\":\"absent\",\"ready_bmp\":\"absent\"}" :
                "{\"complete_bmp\":{\"byte_count\":230454,\"sha256\":\"" +
                    RuntimeCanonicalData.CompleteBmpSha256 + "\"},\"ready_bmp\":" +
                    "{\"byte_count\":230454,\"sha256\":\"" +
                    RuntimeCanonicalData.ReadyBmpSha256 + "\"}}";
            if (timeout)
            {
                if (!RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName) ||
                        !RelativeNameAbsent(RuntimeCanonicalData.CompleteBmpName))
                    return false;
            }
            else if (!RuntimeCanonicalData.IsApprovedCanonicalBmp(readyBmp, true) ||
                    !RuntimeCanonicalData.IsApprovedCanonicalBmp(completeBmp, false) ||
                    !PublishCreateNewOutput(RuntimeCanonicalData.ReadyBmpName, readyBmp,
                        ref readyBmpPublished) ||
                    !PublishCreateNewOutput(RuntimeCanonicalData.CompleteBmpName, completeBmp,
                        ref completeBmpPublished))
                return false;
            string value = "{\"artifacts\":" + artifacts +
                ",\"bindings\":{\"build_manifest\":" +
                IdentityJson(snapshot.Objects["SyntheticLauncherBuildManifest.v1.json"]) +
                ",\"private_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.private.v1.json"]) +
                ",\"public_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.public.v1.json"]) +
                ",\"worker_image\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.exe"]) + "},\"evidence_kind\":\"worker\"," +
                "\"observations\":{\"binding_exact\":true,\"cleanup_exact\":true," +
                "\"controller_create_as_user_calls\":1,\"environment_exact\":\"pass\"," +
                "\"fallback_create_calls\":0,\"fixture_resume_calls\":1," +
                "\"guard_counts_exact\":true,\"inner_job_exact\":\"pass\"," +
                "\"input_capture_exact\":\"" + (timeout ? "not-applicable" : "pass") +
                "\",\"locked_refusal_exact\":\"not-applicable\"," +
                "\"parent_child_topology_exact\":true,\"registry_denied_exact\":\"pass\"," +
                "\"session_desktop_exact\":\"pass\",\"streams_empty\":true," +
                "\"target_result\":\"" + (timeout ? "tree-timeout-contained" :
                    "ui-complete") + "\",\"timeout_tree_exact\":\"" +
                (timeout ? "pass" : "not-applicable") +
                "\",\"token_relationship_exact\":\"pass\"}," +
                "\"profile_id\":\"cm0102-synthetic-launcher-runtime-v1\"," +
                "\"scenario_id\":\"" + lease.ScenarioId + "\",\"schema_version\":1," +
                "\"source_revision\":\"" + sourceRevision + "\"}";
            byte[] bytes = Encoding.UTF8.GetBytes(value + "\n");
            if (!PublishCreateNewOutput("SyntheticLauncherWorkerEvidence.v1.json", bytes,
                    ref workerEvidencePublished))
                return false;
            outputsAccepted = true;
            return true;
        }

        private bool PublishCreateNewOutput(string leaf, byte[] bytes,
            ref bool publicationStarted)
        {
            IntPtr handle = OpenRelativeCreateNew(leaf);
            if (handle == new IntPtr(-1)) return false;
            publicationStarted = true;
            try
            {
                uint written;
                return WriteFile(handle, bytes, (uint)bytes.Length, out written, IntPtr.Zero) &&
                    written == bytes.Length && FlushFileBuffers(handle) &&
                    ExactCreatedObject(handle, leaf, bytes);
            }
            finally { CloseHandle(handle); }
        }

        private bool DeleteRelativeOutput(string leaf)
        {
            IntPtr handle = OpenRelativeExisting(leaf,
                0x00010000 | FileReadAttributes | ReadControl | Synchronize);
            if (handle == new IntPtr(-1)) return false;
            bool deleted = false;
            try
            {
                if (!ExactCreatedOutputObject(handle, leaf)) return false;
                FileDispositionInformation information = new FileDispositionInformation();
                information.DeleteFile = true;
                int size = Marshal.SizeOf(typeof(FileDispositionInformation));
                IntPtr buffer = Marshal.AllocHGlobal(size);
                try
                {
                    Marshal.StructureToPtr(information, buffer, false);
                    deleted = SetFileInformationByHandle(handle, 4, buffer, (uint)size);
                }
                finally { Marshal.FreeHGlobal(buffer); }
            }
            finally { CloseHandle(handle); }
            return deleted && RelativeNameAbsent(leaf);
        }

        private bool ExactCreatedOutputObject(IntPtr handle, string leaf)
        {
            ByHandleFileInformation information;
            ControllerBoundObject inheritedFrom = snapshot.Objects[
                "SyntheticLauncherController.private.v1.json"];
            return GetFileInformationByHandle(handle, out information) &&
                information.VolumeSerialNumber == inheritedFrom.VolumeSerial &&
                information.NumberOfLinks == 1 &&
                (information.FileAttributes & (0x10 | 0x400 | 0x800 | 0x4000)) == 0 &&
                String.Equals(FinalPath(handle), snapshot.ParentFinalPath + "\\" + leaf,
                    StringComparison.Ordinal) && OnlyUnnamedStream(handle) &&
                EqualBytes(SecurityDescriptor(handle), inheritedFrom.SecurityDescriptor);
        }

        private static string IdentityJson(ControllerBoundObject value)
        {
            return "{\"byte_count\":" + value.Bytes.Length.ToString(CultureInfo.InvariantCulture) +
                ",\"sha256\":\"" + value.Sha256 + "\"}";
        }

        private IntPtr OpenRelativeCreateNew(string leaf)
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
                int status = NtCreateFile(out handle,
                    0x0002 | 0x0080 | 0x00020000 | 0x00100000,
                    ref attributes, out statusBlock, ref allocation, 0, 1, 2,
                    0x20 | 0x40 | 0x00200000, IntPtr.Zero, 0);
                return status < 0 ? new IntPtr(-1) : handle;
            }
            finally
            {
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(text);
            }
        }

        private static int EnvironmentByteLength(IntPtr environment)
        {
            int characters = 0;
            while (!(Marshal.ReadInt16(environment, characters * 2) == 0 &&
                    Marshal.ReadInt16(environment, (characters + 1) * 2) == 0)) characters++;
            return (characters + 2) * 2;
        }
        private static void ZeroMemory(IntPtr value, int count)
        {
            for (int index = 0; index < count; index++) Marshal.WriteByte(value, index, 0);
        }

        [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes { internal int Length; internal IntPtr SecurityDescriptor; internal bool InheritHandle; }
        [StructLayout(LayoutKind.Sequential)] private struct Luid { internal uint LowPart; internal int HighPart; }
        [StructLayout(LayoutKind.Sequential)] private struct LuidAndAttributes { internal Luid Luid; internal uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] private struct TokenPrivileges { internal uint Count; internal Luid Luid; internal uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] private struct SidAndAttributes { internal IntPtr Sid; internal uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] private struct TokenStatistics { internal Luid TokenId; internal Luid AuthenticationId; internal long ExpirationTime; internal int TokenType; internal int ImpersonationLevel; internal uint DynamicCharged; internal uint DynamicAvailable; internal uint GroupCount; internal uint PrivilegeCount; internal Luid ModifiedId; }
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct StartupInfo
        {
            internal int Size; internal string Reserved; internal string Desktop; internal string Title;
            internal int X; internal int Y; internal int XSize; internal int YSize;
            internal int XCountChars; internal int YCountChars; internal int FillAttribute;
            internal int Flags; internal short ShowWindow; internal short Reserved2;
            internal IntPtr Reserved2Pointer; internal IntPtr StandardInput;
            internal IntPtr StandardOutput; internal IntPtr StandardError;
        }
        [StructLayout(LayoutKind.Sequential)] private struct ProcessInformation { internal IntPtr Process; internal IntPtr Thread; internal uint ProcessId; internal uint ThreadId; }
        [StructLayout(LayoutKind.Sequential)] private struct BasicLimitInformation { internal long PerProcessUserTimeLimit; internal long PerJobUserTimeLimit; internal uint LimitFlags; internal UIntPtr MinimumWorkingSetSize; internal UIntPtr MaximumWorkingSetSize; internal uint ActiveProcessLimit; internal UIntPtr Affinity; internal uint PriorityClass; internal uint SchedulingClass; }
        [StructLayout(LayoutKind.Sequential)] private struct IoCounters { internal ulong ReadOperationCount; internal ulong WriteOperationCount; internal ulong OtherOperationCount; internal ulong ReadTransferCount; internal ulong WriteTransferCount; internal ulong OtherTransferCount; }
        [StructLayout(LayoutKind.Sequential)] private struct JobObjectExtendedLimitInformation { internal BasicLimitInformation BasicLimitInformation; internal IoCounters IoInfo; internal UIntPtr ProcessMemoryLimit; internal UIntPtr JobMemoryLimit; internal UIntPtr PeakProcessMemoryUsed; internal UIntPtr PeakJobMemoryUsed; }
        [StructLayout(LayoutKind.Sequential)] private struct BasicAccountingInformation { internal long TotalUserTime; internal long TotalKernelTime; internal long ThisPeriodTotalUserTime; internal long ThisPeriodTotalKernelTime; internal uint TotalPageFaultCount; internal uint TotalProcesses; internal uint ActiveProcesses; internal uint TotalTerminatedProcesses; }
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct ProcessEntry
        {
            internal uint Size; internal uint Usage; internal uint ProcessId;
            internal UIntPtr DefaultHeapId; internal uint ModuleId; internal uint Threads;
            internal uint ParentProcessId; internal int PriorityClassBase; internal uint Flags;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)] internal string ExecutableFile;
        }
        [StructLayout(LayoutKind.Sequential)] private struct Rect { internal int Left; internal int Top; internal int Right; internal int Bottom; }
        [StructLayout(LayoutKind.Sequential)] private struct Point { internal int X; internal int Y; }
        [StructLayout(LayoutKind.Sequential)] private struct BitmapInfoHeader { internal uint Size; internal int Width; internal int Height; internal ushort Planes; internal ushort BitCount; internal uint Compression; internal uint SizeImage; internal int XPelsPerMeter; internal int YPelsPerMeter; internal uint ColorsUsed; internal uint ColorsImportant; }
        [StructLayout(LayoutKind.Sequential)] private struct BitmapInfo { internal BitmapInfoHeader Header; internal uint Color0; internal uint Color1; internal uint Color2; }
        [StructLayout(LayoutKind.Sequential)] private struct MouseInput { internal int X; internal int Y; internal uint MouseData; internal uint Flags; internal uint Time; internal UIntPtr ExtraInfo; }
        [StructLayout(LayoutKind.Explicit)] private struct Input { [FieldOffset(0)] internal uint Type; [FieldOffset(4)] internal MouseInput Mouse; }
        [StructLayout(LayoutKind.Sequential)] private struct UnicodeString { internal ushort Length; internal ushort MaximumLength; internal IntPtr Buffer; }
        [StructLayout(LayoutKind.Sequential)] private struct ObjectAttributes { internal int Length; internal IntPtr RootDirectory; internal IntPtr ObjectName; internal uint Attributes; internal IntPtr SecurityDescriptor; internal IntPtr SecurityQualityOfService; }
        [StructLayout(LayoutKind.Sequential)] private struct IoStatusBlock { internal IntPtr Status; internal IntPtr Information; }
        [StructLayout(LayoutKind.Sequential)] private struct FileDispositionInformation { [MarshalAs(UnmanagedType.Bool)] internal bool DeleteFile; }
        [StructLayout(LayoutKind.Sequential)]
        private struct ByHandleFileInformation
        {
            internal uint FileAttributes; internal long CreationTime;
            internal long LastAccessTime; internal long LastWriteTime;
            internal uint VolumeSerialNumber; internal uint FileSizeHigh;
            internal uint FileSizeLow; internal uint NumberOfLinks;
            internal uint FileIndexHigh; internal uint FileIndexLow;
        }
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct FindData
        {
            internal uint FileAttributes; internal long CreationTime;
            internal long LastAccessTime; internal long LastWriteTime;
            internal uint FileSizeHigh; internal uint FileSizeLow;
            internal uint Reserved0; internal uint Reserved1;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)] internal string FileName;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 14)] internal string AlternateFileName;
        }

        [DllImport("user32.dll")] private static extern IntPtr GetShellWindow();
        [DllImport("user32.dll", SetLastError = true)] private static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint access);
        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool GetUserObjectInformationW(IntPtr handle, int index, IntPtr information, int length, out int required);
        [DllImport("user32.dll", SetLastError = true)] private static extern bool CloseDesktop(IntPtr desktop);
        [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr OpenProcess(uint access, bool inherit, uint processId);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool QueryFullProcessImageNameW(IntPtr process, uint flags, StringBuilder name, ref int size);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool OpenThreadToken(IntPtr thread, uint access, bool openAsSelf, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool DuplicateTokenEx(IntPtr existing, uint access, ref SecurityAttributes attributes, int impersonationLevel, int tokenType, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool GetTokenInformation(IntPtr token, int informationClass, IntPtr buffer, int bufferLength, out int returnLength);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool IsTokenRestricted(IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool EqualSid(IntPtr first, IntPtr second);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool CreateWellKnownSid(int sidType, IntPtr domain, IntPtr sid, ref uint size);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern IntPtr GetSidSubAuthorityCount(IntPtr sid);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern IntPtr GetSidSubAuthority(IntPtr sid, uint index);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool LookupPrivilegeValueW(string system, string name, out Luid luid);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool AdjustTokenPrivileges(IntPtr token, bool disableAll, ref TokenPrivileges state, uint size, IntPtr previous, IntPtr returned);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool ImpersonateLoggedOnUser(IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool RevertToSelf();
        [DllImport("advapi32.dll", CharSet = CharSet.Ansi)] private static extern int RegOpenKeyExA(IntPtr key, string subKey, uint options, uint access, out IntPtr result);
        [DllImport("advapi32.dll")] private static extern int RegCloseKey(IntPtr key);
        [DllImport("advapi32.dll", CharSet = CharSet.Ansi, SetLastError = true)]
        private static extern int RegQueryInfoKeyA(IntPtr key, StringBuilder keyClass,
            IntPtr classLength, IntPtr reserved, IntPtr subKeys, IntPtr maximumSubKeyLength,
            IntPtr maximumClassLength, IntPtr values, IntPtr maximumValueNameLength,
            IntPtr maximumValueLength, IntPtr securityDescriptorLength, out long lastWriteTime);
        [DllImport("kernel32.dll")] private static extern uint GetCurrentProcessId();
        [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr CreateToolhelp32Snapshot(uint flags, uint processId);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool Process32FirstW(IntPtr snapshotHandle, ref ProcessEntry entry);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool Process32NextW(IntPtr snapshotHandle, ref ProcessEntry entry);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr GetStdHandle(int standardHandle);
        [DllImport("kernel32.dll")] private static extern IntPtr GetCurrentProcess();
        [DllImport("kernel32.dll")] private static extern IntPtr GetCurrentThread();
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool ProcessIdToSessionId(uint processId, out uint sessionId);
        [DllImport("kernel32.dll")] private static extern uint WTSGetActiveConsoleSessionId();
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] private static extern uint GetWindowsDirectoryW(StringBuilder path, int size);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr CreateJobObjectW(IntPtr attributes, string name);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool SetInformationJobObject(IntPtr job, uint informationClass, IntPtr information, uint length);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool CreateProcessAsUserW(IntPtr token, string application, string commandLine, IntPtr processAttributes, IntPtr threadAttributes, bool inherit, uint flags, IntPtr environment, string currentDirectory, ref StartupInfo startup, out ProcessInformation process);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool result);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern uint ResumeThread(IntPtr thread);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetExitCodeProcess(IntPtr process, out uint exitCode);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool TerminateJobObject(IntPtr job, int exitCode);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool TerminateProcess(IntPtr process, int exitCode);
        [DllImport("kernel32.dll")] private static extern bool QueryPerformanceCounter(out long value);
        [DllImport("kernel32.dll")] private static extern bool QueryPerformanceFrequency(out long value);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool QueryInformationJobObject(IntPtr job, uint informationClass, IntPtr information, uint length, out uint returned);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetHandleInformation(IntPtr handle, out uint flags);
        [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsCallback callback, IntPtr parameter);
        private delegate bool EnumWindowsCallback(IntPtr window, IntPtr parameter);
        [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
        [DllImport("user32.dll")] private static extern IntPtr GetWindow(IntPtr window, uint command);
        [DllImport("user32.dll", SetLastError = true)] private static extern bool GetClientRect(IntPtr window, out Rect rectangle);
        [DllImport("user32.dll", SetLastError = true)] private static extern bool GetWindowRect(IntPtr window, out Rect rectangle);
        [DllImport("user32.dll", SetLastError = true)] private static extern bool ClientToScreen(IntPtr window, ref Point point);
        [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] private static extern short GetAsyncKeyState(int key);
        [DllImport("user32.dll", SetLastError = true)] private static extern uint SendInput(uint count, Input[] input, int size);
        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr SendMessageTimeoutW(IntPtr window, uint message, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out UIntPtr result);
        [DllImport("user32.dll")] private static extern int GetSystemMetrics(int index);
        [DllImport("shcore.dll")] private static extern int GetProcessDpiAwareness(IntPtr process, out int awareness);
        [DllImport("user32.dll")] private static extern IntPtr GetDC(IntPtr window);
        [DllImport("user32.dll")] private static extern int ReleaseDC(IntPtr window, IntPtr dc);
        [DllImport("gdi32.dll")] private static extern IntPtr CreateCompatibleDC(IntPtr dc);
        [DllImport("gdi32.dll")] private static extern IntPtr CreateCompatibleBitmap(IntPtr dc, int width, int height);
        [DllImport("gdi32.dll")] private static extern IntPtr SelectObject(IntPtr dc, IntPtr value);
        [DllImport("gdi32.dll")] private static extern bool BitBlt(IntPtr destination, int x, int y, int width, int height, IntPtr source, int sourceX, int sourceY, uint operation);
        [DllImport("gdi32.dll")] private static extern int GetDIBits(IntPtr dc, IntPtr bitmap, uint start, uint lines, [Out] byte[] bits, ref BitmapInfo information, uint usage);
        [DllImport("gdi32.dll")] private static extern bool DeleteObject(IntPtr value);
        [DllImport("gdi32.dll")] private static extern bool DeleteDC(IntPtr dc);
        [DllImport("kernel32.dll")] private static extern void Sleep(uint milliseconds);
        [DllImport("ntdll.dll")] private static extern int NtCreateFile(out IntPtr handle, uint access, ref ObjectAttributes attributes, out IoStatusBlock statusBlock, ref long allocationSize, uint fileAttributes, uint share, uint disposition, uint options, IntPtr extendedAttributes, uint extendedAttributesLength);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetFileInformationByHandle(IntPtr handle, out ByHandleFileInformation information);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetFileSizeEx(IntPtr handle, out long size);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool ReadFile(IntPtr handle, byte[] bytes, uint count, out uint read, IntPtr overlapped);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern uint GetFinalPathNameByHandleW(IntPtr handle, StringBuilder path, int count, uint flags);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetFileInformationByHandleEx(IntPtr handle, int informationClass, IntPtr information, uint size);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateFileW(string path, uint access, uint share,
            IntPtr security, uint creation, uint flags, IntPtr template);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetFileAttributesW(string path);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetFullPathNameW(string path, int size, StringBuilder value,
            out IntPtr filePart);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetLongPathNameW(string path, StringBuilder value, int size);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr FindFirstFileW(string path, out FindData data);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool FindNextFileW(IntPtr search, out FindData data);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool FindClose(IntPtr search);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern uint GetSecurityInfo(IntPtr handle, int objectType, uint securityInformation, out IntPtr owner, out IntPtr group, out IntPtr dacl, out IntPtr sacl, out IntPtr descriptor);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern uint GetSecurityDescriptorLength(IntPtr descriptor);
        [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr memory);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool WriteFile(IntPtr handle, byte[] bytes, uint count, out uint written, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool FlushFileBuffers(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool SetFileInformationByHandle(IntPtr handle, int informationClass, IntPtr information, uint size);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool CloseHandle(IntPtr handle);
    }
}
