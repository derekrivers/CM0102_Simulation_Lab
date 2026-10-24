using System;

namespace Cm0102.SyntheticLauncherController
{
    internal sealed class FakeCapabilities :
        IUiControllerPort, ITimeoutControllerPort, ILockedPreflightPort
    {
        private readonly string scenario;
        private readonly int[] calls = new int[23];
        private readonly bool hasFailure;
        private readonly AttemptStage failureStage;
        private readonly bool invalidFacts;
        private bool failureInjected;

        private readonly int[] recoveryCalls = new int[10];
        private readonly bool[] acquired = new bool[23];
        internal int OriginalExecutionAttempts;
        internal int FailedRecoveryIndex = -1;
        internal bool ThrowRecoveryFailure;
        internal bool FailAbortRebind;
        internal bool FailAfterAcquisition;
        internal System.Threading.ManualResetEvent BindEntered;
        internal System.Threading.ManualResetEvent ReleaseBind;

        internal FakeCapabilities(string scenarioId)
        {
            scenario = scenarioId;
            OriginalExecutionAttempts = 0;
        }

        internal FakeCapabilities(string scenarioId, AttemptStage injectedStage, bool useInvalidFacts)
        {
            scenario = scenarioId;
            hasFailure = true;
            failureStage = injectedStage;
            invalidFacts = useInvalidFacts;
            OriginalExecutionAttempts = 0;
        }

        private bool Call(AttemptStage stage)
        {
            calls[(int)stage]++;
            if (hasFailure && !failureInjected && failureStage == stage)
            {
                failureInjected = true;
                if (!invalidFacts)
                {
                    if (FailAfterAcquisition) acquired[(int)stage] = true;
                    throw new InvalidOperationException("synthetic-failure");
                }
                return false;
            }
            return true;
        }

        internal int Calls(AttemptStage stage)
        {
            return calls[(int)stage];
        }

        internal int RecoveryCalls(int index)
        {
            return recoveryCalls[index];
        }

        internal bool Acquired(AttemptStage stage)
        {
            return acquired[(int)stage];
        }

        internal int TotalCalls()
        {
            int total = 0;
            for (int index = 1; index < calls.Length; index++) total += calls[index];
            for (int index = 0; index < recoveryCalls.Length; index++) total += recoveryCalls[index];
            return total;
        }

        internal bool ExactRecoveryCalls(int expected)
        {
            for (int index = 0; index < recoveryCalls.Length; index++)
                if (recoveryCalls[index] != expected) return false;
            return true;
        }

        internal bool ExactFailureCalls(AttemptStage[] route, int failureIndex)
        {
            for (int raw = 1; raw <= 22; raw++)
            {
                AttemptStage stage = (AttemptStage)raw;
                int expected = 0;
                for (int index = 0; index <= failureIndex; index++)
                    if (route[index] == stage) expected++;
                if (stage == AttemptStage.RebindPublish) expected++;
                if (calls[raw] != expected) return false;
            }
            return true;
        }

        internal bool ExactSuccessCalls(AttemptStage[] route)
        {
            for (int raw = 1; raw <= 22; raw++)
            {
                int expected = 0;
                for (int index = 0; index < route.Length; index++)
                    if ((int)route[index] == raw) expected++;
                if (calls[raw] != expected) return false;
            }
            return true;
        }

        private static BindingFacts Binding()
        {
            return new BindingFacts
            {
                ObservedControllerByteCount = 12345, ExpectedControllerByteCount = 12345,
                ObservedControllerSha256 = new String('1', 64), ExpectedControllerSha256 = new String('1', 64),
                ObservedFixtureByteCount = FixedControllerContract.FixtureByteCount,
                ObservedFixtureSha256 = FixedControllerContract.FixtureSha256,
                ObservedFixtureSourceByteCount = FixedControllerContract.FixtureSourceByteCount,
                ObservedFixtureSourceSha256 = FixedControllerContract.FixtureSourceSha256,
                ObservedFixtureProfileByteCount = FixedControllerContract.FixtureProfileByteCount,
                ObservedFixtureProfileSha256 = FixedControllerContract.FixtureProfileSha256,
                ObservedHostArtifactByteCount = FixedControllerContract.AcceptedHostArtifactByteCount,
                ObservedHostArtifactSha256 = FixedControllerContract.AcceptedHostArtifactSha256,
                SameHeldParent = true, SameVolume = true, DistinctObjects = true, SingleLinks = true,
                NoReparsePoints = true, StableBeforeAfter = true, FreshPrivateAttempt = true,
                GuardsDistinct = true
            };
        }

        private static PreflightFacts Preflight(bool locked)
        {
            return new PreflightFacts
            {
                ZeroGameProcesses = true, ZeroFixtureProcesses = true,
                ActiveConsoleSessionStable = true, ControllerSessionIsActiveConsole = true,
                ShellSessionIsActiveConsole = true, CanonicalExplorerSelected = true,
                DefaultInputDesktop = !locked, InputDesktopSwitchable = !locked,
                DesktopObservationStable = true, ProcessCreationCapabilityAbsent = locked,
                ProcessCreationNotAttempted = true, ZeroAttemptArtifacts = locked
            };
        }

        private static TokenRelationshipFacts Relationship()
        {
            return new TokenRelationshipFacts
            {
                ThreadTokenAbsent = true, CallerPrimary = true, CallerElevationFull = true,
                CallerElevated = true, CallerHighIntegrity = true, CallerAdministrator = true,
                CallerPrivilegeTupleExact = true, ShellPrimary = true, ShellElevationLimited = true,
                ShellNotElevated = true, ShellMediumIntegrity = true, ShellNotAdministrator = true,
                ShellPrivilegeTupleExact = true, SameUser = true, SameSession = true,
                SameAuthenticationId = true, ShellHasRestrictions = true,
                CallerLinkedQuerySucceeded = true, CallerLinkedHandleValid = true,
                CallerLinkedTokenIdEqualsShellTokenId = true,
                ShellLinkedQuerySucceeded = true, ShellLinkedHandleValid = true,
                ShellLinkedTokenIdEqualsCallerTokenId = true,
                CallerLinkedElevationLimited = true, ShellLinkedElevationFull = true,
                TokenIdsStable = true, ModifiedIdsStable = true, PolicyShapeStable = true,
                LinkedHandleOwnershipExact = true, AssignPrimaryPrivilegeAbsent = true,
                IncreaseQuotaPrivilegePresent = true, ProcessCreationNotAttempted = true,
                FixtureExecutionNotAttempted = true
            };
        }

        private static LaunchTokenFacts LaunchToken()
        {
            return new LaunchTokenFacts
            {
                DuplicatedExactlyOnce = true, DuplicateCallSucceeded = true,
                SourceIsHeldProvenShellToken = true,
                DesiredAccessQueryDuplicateAssignPrimaryOnly = true, NonInheritable = true,
                Primary = true, SameUser = true, SameSession = true, SameAuthenticationId = true,
                MediumIntegrity = true, ElevationLimited = true, NotElevated = true,
                NotAdministrator = true, HasRestrictions = true, PrivilegeTupleExact = true,
                SourceTokenIdStable = true, SourceModifiedIdStable = true,
                DuplicateTokenIdStable = true, DuplicateModifiedIdStable = true,
                SourceAndDuplicateHandlesHeld = true, ProcessCreationNotAttempted = true
            };
        }

        private static RegistryFacts Registry()
        {
            return new RegistryFacts
            {
                TargetId = FixedControllerContract.RegistryTargetId,
                RequestedAccess = FixedControllerContract.RegistryAllAccess, Wow64ViewFlags = 0,
                ExactResult = 5, EffectiveTokenIsHeldLaunchSource = true,
                ImpersonationActiveOnlyForRequest = true, ImpersonationRestored = true,
                ControllerTokenRestoredExact = true, LastWriteObservedBeforeAfter = true,
                LastWriteStable = true
            };
        }

        private static GuardFacts Guards()
        {
            return new GuardFacts
            {
                InstalledTreeSummaryComplete = true, VirtualStoreSummaryComplete = true,
                RegistrySummaryComplete = true, GuardsDistinctFromAttempt = true,
                NoWritableGuardHandles = true
            };
        }

        private static EnvironmentFacts EnvironmentBlock()
        {
            string[] names = new string[FixedControllerContract.EnvironmentNameCount];
            for (int index = 0; index < names.Length; index++)
                names[index] = FixedControllerContract.EnvironmentNameAt(index);
            return new EnvironmentFacts
            {
                Names = names, CaseSensitiveUnique = true, NoAmbientInheritance = true,
                ValuesContainNoControlCharacters = true, SystemRootEqualsWindowsDirectory = true,
                SystemPathsCanonicalAbsoluteInBox = true, TemporaryValuesEqual = true,
                TemporaryContainedByAttempt = true, TemporaryIsExactFixedAttemptChild = true,
                NoDriveCurrentDirectoryEntries = true, WorkingDirectoryHashExact = true,
                NonceIsNonzeroUInt32 = true, SortedDoubleNullUnicodeBlock = true
            };
        }

        private static CreateApprovalFacts CreateApproval()
        {
            return new CreateApprovalFacts
            {
                FixedSiblingTarget = true, LaunchTokenIsPolicyAccepted = true,
                IncreaseQuotaPresentBefore = true, AdjustCalledExactlyOnce = true,
                AdjustReturnedTrue = true, AdjustLastErrorSuccess = true,
                IncreaseQuotaEnabledAfter = true, AssignPrimaryPrivilegeStillAbsent = true,
                NoOtherPrivilegeChanged = true, ThreadTokenAbsent = true,
                RelationshipRevalidatedAfterAdjustment = true,
                LaunchTokenRevalidatedAfterAdjustment = true, NoPriorCreationAttempt = true,
                CreateProcessAsUserOnly = true, NoFallbackAttempted = true,
                InheritHandlesFalse = true, DesktopWinsta0DefaultExact = true,
                WorkingDirectoryExact = true, OriginalExecutionNotAttempted = true
            };
        }

        private static SuspendedChildFacts SuspendedChild()
        {
            return new SuspendedChildFacts
            {
                CreateCalledExactlyOnce = true, CreateSucceeded = true,
                ChildCreatedSuspended = true, ChildIdentityReverified = true,
                PrimaryThreadSuspendCountOne = true, NoChildCodeObserved = true
            };
        }

        private static JobFacts Job(bool timeout)
        {
            return new JobFacts
            {
                CreatedWhileChildSuspended = true, KillOnClose = true, BreakawayForbidden = true,
                ActiveProcessLimit = timeout ? 2 : 1,
                ProcessMemoryLimitBytes = FixedControllerContract.ProcessMemoryLimitBytes,
                JobMemoryLimitBytes = timeout ? FixedControllerContract.TimeoutJobMemoryLimitBytes :
                    FixedControllerContract.UiJobMemoryLimitBytes,
                LimitsQueried = true, ChildStillSuspended = true, AssignedBeforeResume = true,
                MembershipQueried = true, ProcessNotResumed = true
            };
        }

        private static PreResumeFacts PreResume()
        {
            return new PreResumeFacts
            {
                BindingStillStable = true, GuardsStillStable = true,
                RelationshipRevalidated = true, LaunchTokenRevalidated = true,
                RegistryObservationStillBound = true, EnvironmentBlockStillBound = true,
                QuotaStateStillExact = true, ChildExactAndSuspended = true,
                JobMembershipExact = true, JobLimitsExact = true, ThreadTokenAbsent = true,
                DefaultDesktopRechecked = true, DesktopStillSwitchable = true,
                ZeroGameProcesses = true, ResumeCallsSoFar = 0
            };
        }

        private static ResumeFacts Resume()
        {
            return new ResumeFacts
            {
                ResumeCallCount = 1, PreviousSuspendCount = 1,
                ThreadObservedRunning = true, NoSecondResume = true
            };
        }

        private static WindowFacts Window()
        {
            return new WindowFacts
            {
                UniqueVisibleUnownedTopLevel = true, ExactChildProcess = true,
                ProtocolExact = true, ReadyStateExact = true, ClientGeometryExact = true,
                ActiveSessionExact = true, DefaultDesktopExact = true, DisplayExact = true,
                DpiExact = true, ForegroundExact = true
            };
        }

        private static CaptureFacts Capture(int state, int ordinal)
        {
            return new CaptureFacts
            {
                Width = 320, Height = 240, Ordinal = ordinal, ObservedStateId = state,
                ClientRectangleOnly = true, DesktopDcBitBltOnly = true,
                EveryPixelExpected = true, CanonicalBmpExact = true,
                MatchesFirstCapture = ordinal == 2,
                UnexpectedPixelsDiscardedAndZeroed = true
            };
        }

        private static InputGuardFacts InputGuards()
        {
            return new InputGuardFacts
            {
                AllRelevantInputUp = true, ForegroundRechecked = true,
                DesktopRechecked = true, FixedClientPoint = true
            };
        }

        private static SendInputFacts SendInput()
        {
            return new SendInputFacts
            {
                ExactNonce = true, UsedSendInputOnly = true,
                InsertedEventCount = 3, CompleteStateExact = true
            };
        }

        private static UiCleanupFacts UiCleanup()
        {
            return new UiCleanupFacts
            {
                OrderlyCloseRequested = true, OrderlyCloseSucceeded = true, GraceBounded = true,
                JobEmpty = true, HandlesClosed = true, QuotaPrivilegeRestored = true,
                ZeroFixtureProcesses = true, ZeroGameProcesses = true
            };
        }

        private static TimeoutCleanupFacts TimeoutCleanup()
        {
            return new TimeoutCleanupFacts
            {
                ExactlyOneDescendantObserved = true, TimeoutBounded = true,
                WholeJobTerminationRequested = true, WholeJobTerminationSucceeded = true,
                ActiveProcessCountZero = true, JobEmpty = true, HandlesClosed = true,
                QuotaPrivilegeRestored = true, ZeroFixtureProcesses = true,
                ZeroGameProcesses = true
            };
        }

        private static LockedCleanupFacts LockedCleanup()
        {
            return new LockedCleanupFacts
            {
                ProcessCreationCapabilityAbsent = true, ProcessCreationNotAttempted = true,
                FixtureExecutionNotAttempted = true, ZeroFixtureProcesses = true,
                ZeroGameProcesses = true, ZeroAttemptArtifacts = true,
                NoProcessOrTokenHandlesOpened = true
            };
        }

        private static RebindFacts Rebind()
        {
            return new RebindFacts
            {
                InputsStable = true, InstalledTreeStable = true, VirtualStoreStable = true,
                RegistryStable = true, ZeroFixtureProcesses = true,
                ZeroGameProcesses = true, PublicationNotAttempted = true
            };
        }

        public BindingFacts BindFixedInputs()
        {
            bool accepted = Call(AttemptStage.BindInputs);
            if (BindEntered != null)
            {
                BindEntered.Set();
                ReleaseBind.WaitOne();
            }
            return accepted ? Binding() : null;
        }

        public PreflightFacts ObserveFixedPreflight()
        {
            return Call(AttemptStage.PreflightRefusal) ?
                Preflight(String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal)) : null;
        }

        public TokenRelationshipFacts ObserveFixedTokenRelationship()
        {
            return Call(AttemptStage.ExplorerToken) ? Relationship() : null;
        }

        public LaunchTokenFacts DuplicateFixedLaunchToken()
        {
            return Call(AttemptStage.PrimaryToken) ? LaunchToken() : null;
        }

        public RegistryFacts ExecuteFixedRegistryDenial()
        {
            return Call(AttemptStage.RegistryDenial) ? Registry() : null;
        }

        public GuardFacts CaptureFixedGuards()
        {
            return Call(AttemptStage.GuardBefore) ? Guards() : null;
        }

        public EnvironmentFacts BuildFixedEnvironment()
        {
            return Call(AttemptStage.Environment) ? EnvironmentBlock() : null;
        }

        public CreateApprovalFacts PrepareFixedCreate()
        {
            return Call(AttemptStage.CreateApproved) ? CreateApproval() : null;
        }

        public SuspendedChildFacts CreateFixedTargetSuspended()
        {
            return Call(AttemptStage.CreateSuspended) ? SuspendedChild() : null;
        }

        public JobFacts AssignFixedInnerJob()
        {
            return Call(AttemptStage.JobAssign) ?
                Job(String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal)) : null;
        }

        public PreResumeFacts RevalidateFixedPreResume()
        {
            return Call(AttemptStage.PreResumeApproved) ? PreResume() : null;
        }

        public ResumeFacts ResumeFixedChildOnce()
        {
            return Call(AttemptStage.Resume) ? Resume() : null;
        }

        public WindowFacts ObserveFixedUiWindow()
        {
            return Call(AttemptStage.WindowReady) ? Window() : null;
        }

        public CaptureFacts CaptureFixedReadyOne()
        {
            return Call(AttemptStage.ReadyCaptureOne) ? Capture(1, 1) : null;
        }

        public CaptureFacts CaptureFixedReadyTwo()
        {
            return Call(AttemptStage.ReadyCaptureTwo) ? Capture(1, 2) : null;
        }

        public InputGuardFacts ObserveFixedInputGuards()
        {
            return Call(AttemptStage.InputGuards) ? InputGuards() : null;
        }

        public SendInputFacts SendFixedInputOnce()
        {
            return Call(AttemptStage.SendInput) ? SendInput() : null;
        }

        public CaptureFacts CaptureFixedCompleteOne()
        {
            return Call(AttemptStage.CompleteCaptureOne) ? Capture(2, 1) : null;
        }

        public CaptureFacts CaptureFixedCompleteTwo()
        {
            return Call(AttemptStage.CompleteCaptureTwo) ? Capture(2, 2) : null;
        }

        public UiCleanupFacts CleanupFixedUi()
        {
            return Call(AttemptStage.Cleanup) ? UiCleanup() : null;
        }

        public TimeoutCleanupFacts CleanupFixedTimeout()
        {
            return Call(AttemptStage.Cleanup) ? TimeoutCleanup() : null;
        }

        public LockedCleanupFacts CleanupFixedLockedRefusal()
        {
            return Call(AttemptStage.Cleanup) ? LockedCleanup() : null;
        }

        private bool Recover(int index)
        {
            recoveryCalls[index]++;
            if (FailedRecoveryIndex != index) return true;
            if (ThrowRecoveryFailure)
                throw new InvalidOperationException("private-recovery-secret");
            return false;
        }

        public bool DiscardAndZeroFixedUnexpectedPixels() { return Recover(0); }
        public bool RestoreFixedRegistryImpersonationIfActive() { return Recover(1); }
        public bool ReleaseFixedEnvironmentIfAllocated() { return Recover(2); }
        public bool RestoreFixedPrivilegeIfChanged() { return Recover(3); }
        public bool TerminateFixedChildAndJobIfCreated() { return Recover(4); }
        public bool VerifyFixedJobEmptyIfCreated() { return Recover(5); }
        public bool CloseFixedHandles() { return Recover(6); }
        public bool VerifyFixedGuardsStable() { return Recover(7); }
        public bool VerifyZeroFixedFixtureProcesses() { return Recover(8); }
        public bool VerifyZeroFixedGameProcesses() { return Recover(9); }

        public bool VerifyFixedCaptureCapabilityAbsent() { return Recover(0); }
        public bool VerifyFixedRegistryImpersonationCapabilityAbsent() { return Recover(1); }
        public bool VerifyFixedEnvironmentAllocationCapabilityAbsent() { return Recover(2); }
        public bool VerifyFixedPrivilegeAdjustmentCapabilityAbsent() { return Recover(3); }
        public bool VerifyFixedProcessCreationAbsentAndNotAttempted() { return Recover(4); }
        public bool VerifyFixedNoChildOrJobCreated() { return Recover(5); }
        public bool VerifyFixedNoProcessOrTokenHandlesOpened() { return Recover(6); }
        public bool VerifyFixedLockedGuardsStable() { return Recover(7); }
        public bool VerifyZeroFixedLockedFixtureProcesses() { return Recover(8); }
        public bool VerifyZeroFixedLockedGameProcesses() { return Recover(9); }

        private RebindFacts RebindInternal()
        {
            if (FailAbortRebind && recoveryCalls[0] > 0)
            {
                Call(AttemptStage.RebindPublish);
                throw new InvalidOperationException("private-rebind-secret");
            }
            return Call(AttemptStage.RebindPublish) ? Rebind() : null;
        }

        public RebindFacts RebindFixedInputsForPublication() { return RebindInternal(); }
        public RebindFacts RebindFixedLockedInputsForPublication() { return RebindInternal(); }
    }

    internal sealed class ConcurrentEngineRunner
    {
        internal readonly UiControllerEngine Engine;
        internal ControllerEngineResult FirstResult;
        internal ControllerEngineResult SecondResult;

        internal ConcurrentEngineRunner(UiControllerEngine engine)
        {
            Engine = engine;
        }

        internal void RunFirst()
        {
            FirstResult = Engine.Run();
        }

        internal void RunSecond()
        {
            SecondResult = Engine.Run();
        }
    }

    internal static class ControllerEngineTests
    {
        private static int assertions;

        private static readonly AttemptStage[] UiRoute = new AttemptStage[]
        {
            AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
            AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
            AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
            AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
            AttemptStage.WindowReady, AttemptStage.ReadyCaptureOne, AttemptStage.ReadyCaptureTwo,
            AttemptStage.InputGuards, AttemptStage.SendInput, AttemptStage.CompleteCaptureOne,
            AttemptStage.CompleteCaptureTwo, AttemptStage.Cleanup, AttemptStage.RebindPublish
        };

        private static readonly AttemptStage[] TimeoutRoute = new AttemptStage[]
        {
            AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
            AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
            AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
            AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
            AttemptStage.Cleanup, AttemptStage.RebindPublish
        };

        private static readonly AttemptStage[] LockedRoute = new AttemptStage[]
        {
            AttemptStage.BindInputs, AttemptStage.PreflightRefusal,
            AttemptStage.Cleanup, AttemptStage.RebindPublish
        };

        private static void Assert(bool value)
        {
            assertions++;
            if (!value) throw new InvalidOperationException("assertion-failed-" + assertions.ToString());
        }

        private static ControllerEngineResult RunEngine(string scenario, FakeCapabilities fake)
        {
            if (String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal))
                return new UiControllerEngine(fake).Run();
            if (String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal))
                return new TimeoutControllerEngine(fake).Run();
            return new LockedPreflightEngine(fake).Run();
        }

        private static void SuccessCase(string scenario, ControllerRoute route,
            AttemptTerminal terminal, AttemptStage[] stages)
        {
            FakeCapabilities fake = new FakeCapabilities(scenario);
            ControllerEngineResult result = RunEngine(scenario, fake);
            Assert(result.Route == route);
            Assert(result.Terminal == terminal);
            Assert(result.FailureCategory == ControllerFailureCategory.None);
            Assert((int)result.FailureStage == 0);
            Assert(result.StateTerminal);
            Assert(result.CleanupAccepted);
            Assert(result.RebindAccepted);
            Assert(!result.OriginalExecutionAttempted);
            for (int index = 0; index < stages.Length; index++)
                Assert(fake.Calls(stages[index]) == 1);
            Assert(fake.ExactRecoveryCalls(0));
            Assert(fake.OriginalExecutionAttempts == 0);
            Assert(fake.ExactSuccessCalls(stages));
        }

        private static void FailureCases(string scenario, ControllerRoute route, AttemptStage[] stages)
        {
            for (int index = 0; index < stages.Length; index++)
            {
                FakeCapabilities fake = new FakeCapabilities(scenario, stages[index], false);
                ControllerEngineResult result = RunEngine(scenario, fake);
                Assert(result.Route == route);
                Assert(result.Terminal == AttemptTerminal.Ineligible);
                Assert(result.FailureCategory == ControllerFailureCategory.CapabilityException);
                Assert(result.FailureStage == stages[index]);
                Assert(result.StateTerminal);
                Assert(result.CleanupAccepted);
                Assert(result.RebindAccepted);
                Assert(!result.OriginalExecutionAttempted);
                Assert(fake.Calls(stages[index]) == (stages[index] == AttemptStage.RebindPublish ? 2 : 1));
                Assert(fake.ExactRecoveryCalls(1));
                Assert(fake.ExactFailureCalls(stages, index));
                Assert(fake.OriginalExecutionAttempts == 0);
            }
        }

        private static void RejectedFactsCases(string scenario, ControllerRoute route,
            AttemptStage[] stages)
        {
            for (int index = 0; index < stages.Length; index++)
            {
                FakeCapabilities fake = new FakeCapabilities(scenario, stages[index], true);
                ControllerEngineResult result = RunEngine(scenario, fake);
                Assert(result.Route == route);
                Assert(result.Terminal == AttemptTerminal.Ineligible);
                Assert(result.FailureCategory == ControllerFailureCategory.PolicyRejected);
                Assert(result.FailureStage == stages[index]);
                Assert(result.StateTerminal);
                Assert(result.CleanupAccepted);
                Assert(result.RebindAccepted);
                Assert(!result.OriginalExecutionAttempted);
                Assert(fake.Calls(stages[index]) ==
                    (stages[index] == AttemptStage.RebindPublish ? 2 : 1));
                Assert(fake.ExactRecoveryCalls(1));
                Assert(fake.ExactFailureCalls(stages, index));
                Assert(fake.OriginalExecutionAttempts == 0);
            }
        }

        private static void PermitOneUseCase()
        {
            AttemptState state = AttemptState.Start("ui-success-v1");
            FakeCapabilities fake = new FakeCapabilities("ui-success-v1");
            ControllerPolicy.Permit permit = ControllerPolicy.Binding(
                state, "ui-success-v1", fake.BindFixedInputs());
            Assert(permit != null);
            Assert(state.Advance(permit));
            Assert(!state.Advance(permit));
            Assert(state.IsRejected);
            Assert(fake.Calls(AttemptStage.BindInputs) == 1);
            Assert(fake.OriginalExecutionAttempts == 0);
        }

        private static void AbortFailureCases()
        {
            for (int index = 0; index < 10; index++)
            {
                FakeCapabilities cleanupFailure = new FakeCapabilities(
                    "ui-success-v1", AttemptStage.BindInputs, false);
                cleanupFailure.FailedRecoveryIndex = index;
                cleanupFailure.ThrowRecoveryFailure = index % 2 == 0;
                ControllerEngineResult cleanupResult = new UiControllerEngine(cleanupFailure).Run();
                Assert(cleanupResult.Route == ControllerRoute.UiSuccess);
                Assert(cleanupResult.Terminal == AttemptTerminal.Ineligible);
                Assert(cleanupResult.FailureCategory == ControllerFailureCategory.CleanupFailure);
                Assert(cleanupResult.FailureStage == AttemptStage.Cleanup);
                Assert(!cleanupResult.StateTerminal);
                Assert(!cleanupResult.CleanupAccepted);
                Assert(!cleanupResult.RebindAccepted);
                Assert(cleanupFailure.ExactRecoveryCalls(1));
                Assert(cleanupFailure.Calls(AttemptStage.RebindPublish) == 1);
                Assert(!cleanupResult.OriginalExecutionAttempted && cleanupFailure.OriginalExecutionAttempts == 0);
            }

            FakeCapabilities rebindFailure = new FakeCapabilities(
                "ui-success-v1", AttemptStage.BindInputs, false);
            rebindFailure.FailAbortRebind = true;
            ControllerEngineResult rebindResult = new UiControllerEngine(rebindFailure).Run();
            Assert(rebindResult.Route == ControllerRoute.UiSuccess);
            Assert(rebindResult.Terminal == AttemptTerminal.Ineligible);
            Assert(rebindResult.FailureCategory == ControllerFailureCategory.CleanupFailure);
            Assert(rebindResult.FailureStage == AttemptStage.Cleanup);
            Assert(!rebindResult.StateTerminal);
            Assert(rebindResult.CleanupAccepted);
            Assert(!rebindResult.RebindAccepted);
            Assert(rebindFailure.ExactRecoveryCalls(1));
            Assert(rebindFailure.Calls(AttemptStage.RebindPublish) == 1);
            Assert(!rebindResult.OriginalExecutionAttempted && rebindFailure.OriginalExecutionAttempts == 0);
        }

        private static void AcquireThenThrowCases()
        {
            AttemptStage[] stages = new AttemptStage[]
            {
                AttemptStage.RegistryDenial, AttemptStage.Environment,
                AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
                AttemptStage.WindowReady, AttemptStage.ReadyCaptureOne,
                AttemptStage.ReadyCaptureTwo, AttemptStage.CompleteCaptureOne,
                AttemptStage.CompleteCaptureTwo
            };
            for (int caseIndex = 0; caseIndex < stages.Length; caseIndex++)
            {
                AttemptStage stage = stages[caseIndex];
                int routeIndex = 0;
                while (UiRoute[routeIndex] != stage) routeIndex++;
                FakeCapabilities fake = new FakeCapabilities("ui-success-v1", stage, false);
                fake.FailAfterAcquisition = true;
                ControllerEngineResult result = new UiControllerEngine(fake).Run();
                Assert(fake.Acquired(stage));
                Assert(result.Terminal == AttemptTerminal.Ineligible);
                Assert(result.FailureCategory == ControllerFailureCategory.CapabilityException);
                Assert(result.FailureStage == stage);
                Assert(result.StateTerminal);
                Assert(result.CleanupAccepted);
                Assert(result.RebindAccepted);
                Assert(fake.ExactRecoveryCalls(1));
                Assert(fake.ExactFailureCalls(UiRoute, routeIndex));
                Assert(!result.OriginalExecutionAttempted && fake.OriginalExecutionAttempts == 0);
            }
        }

        private static void ReentrantRunCase()
        {
            FakeCapabilities fake = new FakeCapabilities("ui-success-v1");
            UiControllerEngine engine = new UiControllerEngine(fake);
            ControllerEngineResult first = engine.Run();
            int calls = fake.TotalCalls();
            ControllerEngineResult second = engine.Run();
            Assert(first.Terminal == AttemptTerminal.UiComplete);
            Assert(second.Terminal == AttemptTerminal.Ineligible);
            Assert(second.FailureCategory == ControllerFailureCategory.ReentrantRun);
            Assert(second.FailureStage == AttemptStage.BindInputs);
            Assert(second.StateTerminal);
            Assert(!second.CleanupAccepted);
            Assert(!second.RebindAccepted);
            Assert(fake.TotalCalls() == calls);
            Assert(fake.ExactRecoveryCalls(0));
            Assert(fake.OriginalExecutionAttempts == 0);
        }

        private static void ConcurrentRunCase()
        {
            FakeCapabilities fake = new FakeCapabilities("ui-success-v1");
            fake.BindEntered = new System.Threading.ManualResetEvent(false);
            fake.ReleaseBind = new System.Threading.ManualResetEvent(false);
            ConcurrentEngineRunner runner = new ConcurrentEngineRunner(new UiControllerEngine(fake));
            System.Threading.Thread first = new System.Threading.Thread(
                new System.Threading.ThreadStart(runner.RunFirst));
            System.Threading.Thread second = new System.Threading.Thread(
                new System.Threading.ThreadStart(runner.RunSecond));
            first.Start();
            bool bindEntered = fake.BindEntered.WaitOne(5000);
            second.Start();
            bool secondFinishedBeforeRelease = second.Join(5000);
            fake.ReleaseBind.Set();
            bool firstFinished = first.Join(5000);
            if (!secondFinishedBeforeRelease) second.Join(5000);
            Assert(bindEntered);
            Assert(secondFinishedBeforeRelease);
            Assert(firstFinished);
            Assert(runner.SecondResult != null);
            Assert(runner.SecondResult.FailureCategory == ControllerFailureCategory.ReentrantRun);
            Assert(fake.Calls(AttemptStage.BindInputs) == 1);
            Assert(runner.FirstResult != null);
            Assert(runner.FirstResult.Terminal == AttemptTerminal.UiComplete);
            Assert(fake.Calls(AttemptStage.BindInputs) == 1);
            Assert(fake.ExactRecoveryCalls(0));
            Assert(fake.OriginalExecutionAttempts == 0);
            fake.BindEntered.Close();
            fake.ReleaseBind.Close();
        }

        private static int Main()
        {
            SuccessCase("ui-success-v1", ControllerRoute.UiSuccess,
                AttemptTerminal.UiComplete, UiRoute);
            SuccessCase("tree-timeout-v1", ControllerRoute.TreeTimeout,
                AttemptTerminal.ExpectedTimeout, TimeoutRoute);
            SuccessCase("locked-refusal-v1", ControllerRoute.LockedRefusal,
                AttemptTerminal.LockedRefusal, LockedRoute);
            FailureCases("ui-success-v1", ControllerRoute.UiSuccess, UiRoute);
            FailureCases("tree-timeout-v1", ControllerRoute.TreeTimeout, TimeoutRoute);
            FailureCases("locked-refusal-v1", ControllerRoute.LockedRefusal, LockedRoute);
            RejectedFactsCases("ui-success-v1", ControllerRoute.UiSuccess, UiRoute);
            RejectedFactsCases("tree-timeout-v1", ControllerRoute.TreeTimeout, TimeoutRoute);
            RejectedFactsCases("locked-refusal-v1", ControllerRoute.LockedRefusal, LockedRoute);
            PermitOneUseCase();
            AbortFailureCases();
            AcquireThenThrowCases();
            ReentrantRunCase();
            ConcurrentRunCase();
            Console.WriteLine("PASS " + assertions.ToString());
            return 0;
        }
    }
}
