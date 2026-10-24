using System;

namespace Cm0102.SyntheticLauncherController
{
    internal interface IControllerRecoveryPort
    {
        bool RestoreFixedPrivilegeIfChanged();
        bool TerminateFixedChildAndJobIfCreated();
        bool VerifyFixedJobEmptyIfCreated();
        bool CloseFixedHandles();
        bool VerifyFixedGuardsStable();
        bool VerifyZeroFixedFixtureProcesses();
        bool VerifyZeroFixedGameProcesses();
        RebindFacts RebindFixedInputsForPublication();
    }

    internal interface ICommonControllerPort : IControllerRecoveryPort
    {
        BindingFacts BindFixedInputs();
        PreflightFacts ObserveFixedPreflight();
        TokenRelationshipFacts ObserveFixedTokenRelationship();
        LaunchTokenFacts DuplicateFixedLaunchToken();
        RegistryFacts ExecuteFixedRegistryDenial();
        GuardFacts CaptureFixedGuards();
        EnvironmentFacts BuildFixedEnvironment();
        CreateApprovalFacts PrepareFixedCreate();
        SuspendedChildFacts CreateFixedTargetSuspended();
        JobFacts AssignFixedInnerJob();
        PreResumeFacts RevalidateFixedPreResume();
        ResumeFacts ResumeFixedChildOnce();
    }

    internal interface IUiControllerPort : ICommonControllerPort
    {
        WindowFacts ObserveFixedUiWindow();
        CaptureFacts CaptureFixedReadyOne();
        CaptureFacts CaptureFixedReadyTwo();
        InputGuardFacts ObserveFixedInputGuards();
        SendInputFacts SendFixedInputOnce();
        CaptureFacts CaptureFixedCompleteOne();
        CaptureFacts CaptureFixedCompleteTwo();
        UiCleanupFacts CleanupFixedUi();
    }

    internal interface ITimeoutControllerPort : ICommonControllerPort
    {
        TimeoutCleanupFacts CleanupFixedTimeout();
    }

    internal interface ILockedPreflightPort
    {
        BindingFacts BindFixedInputs();
        PreflightFacts ObserveFixedPreflight();
        LockedCleanupFacts CleanupFixedLockedRefusal();
        bool VerifyFixedProcessCreationCapabilityAbsent();
        bool VerifyFixedProcessCreationNotAttempted();
        bool VerifyFixedNoChildOrJobCreated();
        bool VerifyFixedNoProcessOrTokenHandlesOpened();
        bool VerifyFixedLockedGuardsStable();
        bool VerifyZeroFixedLockedFixtureProcesses();
        bool VerifyZeroFixedLockedGameProcesses();
        RebindFacts RebindFixedLockedInputsForPublication();
    }

    internal enum ControllerRoute
    {
        UiSuccess = 1,
        TreeTimeout = 2,
        LockedRefusal = 3
    }

    internal enum ControllerFailureCategory
    {
        None = 0,
        CapabilityException = 1,
        PolicyRejected = 2,
        StateRejected = 3,
        CleanupFailure = 4,
        ReentrantRun = 5
    }

    internal sealed class ControllerEngineResult
    {
        internal readonly ControllerRoute Route;
        internal readonly AttemptTerminal Terminal;
        internal readonly ControllerFailureCategory FailureCategory;
        internal readonly AttemptStage FailureStage;
        internal readonly bool StateTerminal;
        internal readonly bool CleanupAccepted;
        internal readonly bool RebindAccepted;
        internal readonly bool OriginalExecutionAttempted;

        internal ControllerEngineResult(ControllerRoute route, AttemptTerminal terminal,
            ControllerFailureCategory failureCategory, AttemptStage failureStage,
            bool stateTerminal, bool cleanupAccepted, bool rebindAccepted)
        {
            Route = route;
            Terminal = terminal;
            FailureCategory = failureCategory;
            FailureStage = failureStage;
            StateTerminal = stateTerminal;
            CleanupAccepted = cleanupAccepted;
            RebindAccepted = rebindAccepted;
            OriginalExecutionAttempted = false;
        }
    }

    internal abstract class ControllerEngineBase
    {
        private readonly string scenario;
        private readonly ControllerRoute route;
        private bool runStarted;
        private ControllerFailureCategory failureCategory;
        private AttemptStage failureStage;
        private bool cleanupAccepted;
        private bool rebindAccepted;

        protected ControllerEngineBase(string fixedScenario, ControllerRoute fixedRoute)
        {
            scenario = fixedScenario;
            route = fixedRoute;
        }

        protected AttemptState State { get; private set; }
        protected string Scenario { get { return scenario; } }

        protected bool StartRun()
        {
            if (runStarted) return false;
            runStarted = true;
            State = AttemptState.Start(scenario);
            failureCategory = ControllerFailureCategory.None;
            failureStage = 0;
            cleanupAccepted = false;
            rebindAccepted = false;
            return true;
        }

        protected bool Accept(AttemptStage stage, ControllerPolicy.Permit permit)
        {
            failureStage = stage;
            if (permit == null)
            {
                State.Advance(null);
                failureCategory = ControllerFailureCategory.PolicyRejected;
                return false;
            }
            if (!State.Advance(permit))
            {
                failureCategory = ControllerFailureCategory.StateRejected;
                return false;
            }
            if (stage == AttemptStage.Cleanup) cleanupAccepted = true;
            if (stage == AttemptStage.RebindPublish) rebindAccepted = true;
            return true;
        }

        protected bool CapabilityFailed(AttemptStage stage)
        {
            failureStage = stage;
            failureCategory = ControllerFailureCategory.CapabilityException;
            return false;
        }

        protected ControllerEngineResult ReentrantResult()
        {
            return new ControllerEngineResult(route, AttemptTerminal.Ineligible,
                ControllerFailureCategory.ReentrantRun, AttemptStage.BindInputs,
                State != null && State.IsTerminal, false, false);
        }

        protected abstract AbortCleanupFacts CollectAbortCleanupFacts();
        protected abstract RebindFacts RebindAfterAbort();

        protected ControllerEngineResult Abort()
        {
            ControllerPolicy.Permit abortPermit = ControllerPolicy.Abort(State, scenario,
                new AbortFacts
                {
                    FailureRecorded = true,
                    NoFurtherAuthorityAttempted = true,
                    OriginalExecutionNotAttempted = true,
                    UnexpectedPixelsDiscardedAndZeroed = true
                });
            bool began = State.BeginAbort(abortPermit);

            AbortCleanupFacts cleanupFacts = CollectAbortCleanupFacts();
            ControllerPolicy.Permit cleanupPermit = ControllerPolicy.CleanupAbort(
                State, scenario, cleanupFacts);
            cleanupAccepted = State.Advance(cleanupPermit);

            RebindFacts rebindFacts = RebindAfterAbort();
            ControllerPolicy.Permit rebindPermit = ControllerPolicy.Rebind(
                State, scenario, rebindFacts);
            rebindAccepted = State.Advance(rebindPermit);

            bool terminal = State.Complete(AttemptTerminal.Ineligible);
            bool cleanupFailed = !began || cleanupFacts == null ||
                !cleanupFacts.PrivilegeStateRestoredIfChanged ||
                !cleanupFacts.ChildAndJobTerminatedIfCreated || !cleanupFacts.JobEmptyIfCreated ||
                !cleanupFacts.HandlesClosed || !cleanupFacts.GuardsStable ||
                !cleanupFacts.ZeroFixtureProcesses || !cleanupFacts.ZeroGameProcesses ||
                !cleanupAccepted || rebindFacts == null || !rebindAccepted || !terminal;
            if (cleanupFailed)
            {
                failureCategory = ControllerFailureCategory.CleanupFailure;
                failureStage = AttemptStage.Cleanup;
            }
            return new ControllerEngineResult(route, AttemptTerminal.Ineligible,
                failureCategory, failureStage, State.IsTerminal, cleanupAccepted, rebindAccepted);
        }

        protected ControllerEngineResult Complete(AttemptTerminal terminal)
        {
            if (!State.Complete(terminal))
            {
                failureCategory = ControllerFailureCategory.StateRejected;
                failureStage = AttemptStage.RebindPublish;
                return new ControllerEngineResult(route, AttemptTerminal.Ineligible,
                    failureCategory, failureStage, State.IsTerminal, cleanupAccepted, rebindAccepted);
            }
            return new ControllerEngineResult(route, terminal, ControllerFailureCategory.None, 0,
                true, cleanupAccepted, rebindAccepted);
        }
    }

    internal abstract class CommonControllerEngine : ControllerEngineBase
    {
        private readonly ICommonControllerPort port;

        protected CommonControllerEngine(string fixedScenario, ControllerRoute fixedRoute,
            ICommonControllerPort fixedPort) : base(fixedScenario, fixedRoute)
        {
            port = fixedPort;
        }

        private bool RestorePrivilege()
        {
            try { return port.RestoreFixedPrivilegeIfChanged(); }
            catch (Exception) { return false; }
        }

        private bool TerminateChildAndJob()
        {
            try { return port.TerminateFixedChildAndJobIfCreated(); }
            catch (Exception) { return false; }
        }

        private bool VerifyJobEmpty()
        {
            try { return port.VerifyFixedJobEmptyIfCreated(); }
            catch (Exception) { return false; }
        }

        private bool CloseHandles()
        {
            try { return port.CloseFixedHandles(); }
            catch (Exception) { return false; }
        }

        private bool VerifyGuards()
        {
            try { return port.VerifyFixedGuardsStable(); }
            catch (Exception) { return false; }
        }

        private bool VerifyFixtureProcesses()
        {
            try { return port.VerifyZeroFixedFixtureProcesses(); }
            catch (Exception) { return false; }
        }

        private bool VerifyGameProcesses()
        {
            try { return port.VerifyZeroFixedGameProcesses(); }
            catch (Exception) { return false; }
        }

        protected override AbortCleanupFacts CollectAbortCleanupFacts()
        {
            return new AbortCleanupFacts
            {
                PrivilegeStateRestoredIfChanged = RestorePrivilege(),
                ChildAndJobTerminatedIfCreated = TerminateChildAndJob(),
                JobEmptyIfCreated = VerifyJobEmpty(),
                HandlesClosed = CloseHandles(),
                GuardsStable = VerifyGuards(),
                ZeroFixtureProcesses = VerifyFixtureProcesses(),
                ZeroGameProcesses = VerifyGameProcesses()
            };
        }

        protected override RebindFacts RebindAfterAbort()
        {
            try { return port.RebindFixedInputsForPublication(); }
            catch (Exception) { return null; }
        }

        protected bool RunCommonRoute()
        {
            try
            {
                if (!Accept(AttemptStage.BindInputs,
                    ControllerPolicy.Binding(State, Scenario, port.BindFixedInputs()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.BindInputs); }
            try
            {
                if (!Accept(AttemptStage.PreflightRefusal,
                    ControllerPolicy.Preflight(State, Scenario, port.ObserveFixedPreflight()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.PreflightRefusal); }
            try
            {
                if (!Accept(AttemptStage.ExplorerToken,
                    ControllerPolicy.TokenRelationship(State, Scenario,
                        port.ObserveFixedTokenRelationship()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.ExplorerToken); }
            try
            {
                if (!Accept(AttemptStage.PrimaryToken,
                    ControllerPolicy.LaunchToken(State, Scenario,
                        port.DuplicateFixedLaunchToken()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.PrimaryToken); }
            try
            {
                if (!Accept(AttemptStage.RegistryDenial,
                    ControllerPolicy.Registry(State, Scenario,
                        port.ExecuteFixedRegistryDenial()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.RegistryDenial); }
            try
            {
                if (!Accept(AttemptStage.GuardBefore,
                    ControllerPolicy.Guards(State, Scenario, port.CaptureFixedGuards()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.GuardBefore); }
            try
            {
                if (!Accept(AttemptStage.Environment,
                    ControllerPolicy.Environment(State, Scenario, port.BuildFixedEnvironment()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.Environment); }
            try
            {
                if (!Accept(AttemptStage.CreateApproved,
                    ControllerPolicy.ApproveCreate(State, Scenario, port.PrepareFixedCreate()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.CreateApproved); }
            try
            {
                if (!Accept(AttemptStage.CreateSuspended,
                    ControllerPolicy.RecordSuspendedChild(State, Scenario,
                        port.CreateFixedTargetSuspended()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.CreateSuspended); }
            try
            {
                if (!Accept(AttemptStage.JobAssign,
                    ControllerPolicy.JobBeforeResume(State, Scenario, port.AssignFixedInnerJob()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.JobAssign); }
            try
            {
                if (!Accept(AttemptStage.PreResumeApproved,
                    ControllerPolicy.PreResume(State, Scenario,
                        port.RevalidateFixedPreResume()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.PreResumeApproved); }
            try
            {
                if (!Accept(AttemptStage.Resume,
                    ControllerPolicy.Resume(State, Scenario, port.ResumeFixedChildOnce()))) return false;
            }
            catch (Exception) { return CapabilityFailed(AttemptStage.Resume); }
            return true;
        }
    }

    internal sealed class UiControllerEngine : CommonControllerEngine
    {
        private const string FixedScenario = "ui-success-v1";
        private readonly IUiControllerPort port;

        internal UiControllerEngine(IUiControllerPort fixedPort) :
            base(FixedScenario, ControllerRoute.UiSuccess, fixedPort)
        {
            port = fixedPort;
        }

        internal ControllerEngineResult Run()
        {
            if (!StartRun()) return ReentrantResult();
            if (!RunCommonRoute()) return Abort();
            try { if (!Accept(AttemptStage.WindowReady, ControllerPolicy.Window(State, Scenario, port.ObserveFixedUiWindow()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.WindowReady); return Abort(); }
            try { if (!Accept(AttemptStage.ReadyCaptureOne, ControllerPolicy.ReadyCaptureOne(State, Scenario, port.CaptureFixedReadyOne()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.ReadyCaptureOne); return Abort(); }
            try { if (!Accept(AttemptStage.ReadyCaptureTwo, ControllerPolicy.ReadyCaptureTwo(State, Scenario, port.CaptureFixedReadyTwo()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.ReadyCaptureTwo); return Abort(); }
            try { if (!Accept(AttemptStage.InputGuards, ControllerPolicy.InputGuards(State, Scenario, port.ObserveFixedInputGuards()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.InputGuards); return Abort(); }
            try { if (!Accept(AttemptStage.SendInput, ControllerPolicy.SendInput(State, Scenario, port.SendFixedInputOnce()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.SendInput); return Abort(); }
            try { if (!Accept(AttemptStage.CompleteCaptureOne, ControllerPolicy.CompleteCaptureOne(State, Scenario, port.CaptureFixedCompleteOne()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.CompleteCaptureOne); return Abort(); }
            try { if (!Accept(AttemptStage.CompleteCaptureTwo, ControllerPolicy.CompleteCaptureTwo(State, Scenario, port.CaptureFixedCompleteTwo()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.CompleteCaptureTwo); return Abort(); }
            try { if (!Accept(AttemptStage.Cleanup, ControllerPolicy.CleanupUi(State, Scenario, port.CleanupFixedUi()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.Cleanup); return Abort(); }
            try { if (!Accept(AttemptStage.RebindPublish, ControllerPolicy.Rebind(State, Scenario, port.RebindFixedInputsForPublication()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.RebindPublish); return Abort(); }
            return Complete(AttemptTerminal.UiComplete);
        }
    }

    internal sealed class TimeoutControllerEngine : CommonControllerEngine
    {
        private const string FixedScenario = "tree-timeout-v1";
        private readonly ITimeoutControllerPort port;

        internal TimeoutControllerEngine(ITimeoutControllerPort fixedPort) :
            base(FixedScenario, ControllerRoute.TreeTimeout, fixedPort)
        {
            port = fixedPort;
        }

        internal ControllerEngineResult Run()
        {
            if (!StartRun()) return ReentrantResult();
            if (!RunCommonRoute()) return Abort();
            try { if (!Accept(AttemptStage.Cleanup, ControllerPolicy.CleanupTimeout(State, Scenario, port.CleanupFixedTimeout()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.Cleanup); return Abort(); }
            try { if (!Accept(AttemptStage.RebindPublish, ControllerPolicy.Rebind(State, Scenario, port.RebindFixedInputsForPublication()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.RebindPublish); return Abort(); }
            return Complete(AttemptTerminal.ExpectedTimeout);
        }
    }

    internal sealed class LockedPreflightEngine : ControllerEngineBase
    {
        private const string FixedScenario = "locked-refusal-v1";
        private readonly ILockedPreflightPort port;

        internal LockedPreflightEngine(ILockedPreflightPort fixedPort) :
            base(FixedScenario, ControllerRoute.LockedRefusal)
        {
            port = fixedPort;
        }

        private bool VerifyCreationCapabilityAbsent()
        {
            try { return port.VerifyFixedProcessCreationCapabilityAbsent(); }
            catch (Exception) { return false; }
        }

        private bool VerifyCreationNotAttempted()
        {
            try { return port.VerifyFixedProcessCreationNotAttempted(); }
            catch (Exception) { return false; }
        }

        private bool VerifyNoChildOrJob()
        {
            try { return port.VerifyFixedNoChildOrJobCreated(); }
            catch (Exception) { return false; }
        }

        private bool VerifyNoHandles()
        {
            try { return port.VerifyFixedNoProcessOrTokenHandlesOpened(); }
            catch (Exception) { return false; }
        }

        private bool VerifyLockedGuards()
        {
            try { return port.VerifyFixedLockedGuardsStable(); }
            catch (Exception) { return false; }
        }

        private bool VerifyLockedFixtureProcesses()
        {
            try { return port.VerifyZeroFixedLockedFixtureProcesses(); }
            catch (Exception) { return false; }
        }

        private bool VerifyLockedGameProcesses()
        {
            try { return port.VerifyZeroFixedLockedGameProcesses(); }
            catch (Exception) { return false; }
        }

        protected override AbortCleanupFacts CollectAbortCleanupFacts()
        {
            bool absent = VerifyCreationCapabilityAbsent();
            bool notAttempted = VerifyCreationNotAttempted();
            bool noChildOrJob = VerifyNoChildOrJob();
            return new AbortCleanupFacts
            {
                PrivilegeStateRestoredIfChanged = absent && notAttempted,
                ChildAndJobTerminatedIfCreated = noChildOrJob,
                JobEmptyIfCreated = noChildOrJob,
                HandlesClosed = VerifyNoHandles(),
                GuardsStable = VerifyLockedGuards(),
                ZeroFixtureProcesses = VerifyLockedFixtureProcesses(),
                ZeroGameProcesses = VerifyLockedGameProcesses()
            };
        }

        protected override RebindFacts RebindAfterAbort()
        {
            try { return port.RebindFixedLockedInputsForPublication(); }
            catch (Exception) { return null; }
        }

        internal ControllerEngineResult Run()
        {
            if (!StartRun()) return ReentrantResult();
            try { if (!Accept(AttemptStage.BindInputs, ControllerPolicy.Binding(State, Scenario, port.BindFixedInputs()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.BindInputs); return Abort(); }
            try { if (!Accept(AttemptStage.PreflightRefusal, ControllerPolicy.Preflight(State, Scenario, port.ObserveFixedPreflight()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.PreflightRefusal); return Abort(); }
            try { if (!Accept(AttemptStage.Cleanup, ControllerPolicy.CleanupLocked(State, Scenario, port.CleanupFixedLockedRefusal()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.Cleanup); return Abort(); }
            try { if (!Accept(AttemptStage.RebindPublish, ControllerPolicy.Rebind(State, Scenario, port.RebindFixedLockedInputsForPublication()))) return Abort(); }
            catch (Exception) { CapabilityFailed(AttemptStage.RebindPublish); return Abort(); }
            return Complete(AttemptTerminal.LockedRefusal);
        }
    }
}
