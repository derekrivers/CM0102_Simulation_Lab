using System;

namespace Cm0102.SyntheticLauncherController
{
    internal static class ControllerPolicyTests
    {
        private static int assertions;

        private static void Assert(bool value)
        {
            assertions++;
            if (!value) throw new InvalidOperationException("assertion-failed-" + assertions.ToString());
        }

        private static bool Allowed(ControllerPolicy.Permit value)
        {
            return value != null;
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
                LinkedHandleOwnershipExact = true,
                AssignPrimaryPrivilegeAbsent = true, IncreaseQuotaPrivilegePresent = true,
                ProcessCreationNotAttempted = true, FixtureExecutionNotAttempted = true
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
                SourceAndDuplicateHandlesHeld = true,
                ProcessCreationNotAttempted = true
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
                NoDriveCurrentDirectoryEntries = true,
                WorkingDirectoryHashExact = true, NonceIsNonzeroUInt32 = true,
                SortedDoubleNullUnicodeBlock = true
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
                CreateProcessAsUserOnly = true,
                NoFallbackAttempted = true, InheritHandlesFalse = true,
                DesktopWinsta0DefaultExact = true, WorkingDirectoryExact = true,
                OriginalExecutionNotAttempted = true
            };
        }

        private static SuspendedChildFacts SuspendedChild()
        {
            return new SuspendedChildFacts
            {
                CreateCalledExactlyOnce = true, CreateSucceeded = true, ChildCreatedSuspended = true,
                ChildIdentityReverified = true, PrimaryThreadSuspendCountOne = true,
                NoChildCodeObserved = true
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
                UniqueVisibleUnownedTopLevel = true, ExactChildProcess = true, ProtocolExact = true,
                ReadyStateExact = true, ClientGeometryExact = true, ActiveSessionExact = true,
                DefaultDesktopExact = true, DisplayExact = true, DpiExact = true, ForegroundExact = true
            };
        }

        private static CaptureFacts Capture(int state, int ordinal)
        {
            return new CaptureFacts
            {
                Width = 320, Height = 240, Ordinal = ordinal, ObservedStateId = state,
                ClientRectangleOnly = true, DesktopDcBitBltOnly = true, EveryPixelExpected = true,
                CanonicalBmpExact = true, MatchesFirstCapture = ordinal == 2,
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
                QuotaPrivilegeRestored = true, ZeroFixtureProcesses = true, ZeroGameProcesses = true
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
                RegistryStable = true, ZeroFixtureProcesses = true, ZeroGameProcesses = true,
                PublicationNotAttempted = true
            };
        }

        private static AbortFacts Abort()
        {
            return new AbortFacts
            {
                FailureRecorded = true, NoFurtherAuthorityAttempted = true,
                OriginalExecutionNotAttempted = true,
                UnexpectedPixelsDiscardedAndZeroed = true
            };
        }

        private static AbortCleanupFacts AbortCleanup()
        {
            return new AbortCleanupFacts
            {
                PrivilegeStateRestoredIfChanged = true,
                ChildAndJobTerminatedIfCreated = true, JobEmptyIfCreated = true,
                HandlesClosed = true, GuardsStable = true,
                ZeroFixtureProcesses = true, ZeroGameProcesses = true
            };
        }

        private static ControllerPolicy.Permit ValidPermit(AttemptState state, string scenario, AttemptStage stage)
        {
            switch (stage)
            {
                case AttemptStage.BindInputs: return ControllerPolicy.Binding(state, scenario, Binding());
                case AttemptStage.PreflightRefusal: return ControllerPolicy.Preflight(state, scenario, Preflight(String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal)));
                case AttemptStage.ExplorerToken: return ControllerPolicy.TokenRelationship(state, scenario, Relationship());
                case AttemptStage.PrimaryToken: return ControllerPolicy.LaunchToken(state, scenario, LaunchToken());
                case AttemptStage.RegistryDenial: return ControllerPolicy.Registry(state, scenario, Registry());
                case AttemptStage.GuardBefore: return ControllerPolicy.Guards(state, scenario, Guards());
                case AttemptStage.Environment: return ControllerPolicy.Environment(state, scenario, EnvironmentBlock());
                case AttemptStage.CreateApproved: return ControllerPolicy.ApproveCreate(state, scenario, CreateApproval());
                case AttemptStage.CreateSuspended: return ControllerPolicy.RecordSuspendedChild(state, scenario, SuspendedChild());
                case AttemptStage.JobAssign: return ControllerPolicy.JobBeforeResume(state, scenario, Job(String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal)));
                case AttemptStage.PreResumeApproved: return ControllerPolicy.PreResume(state, scenario, PreResume());
                case AttemptStage.Resume: return ControllerPolicy.Resume(state, scenario, Resume());
                case AttemptStage.WindowReady: return ControllerPolicy.Window(state, scenario, Window());
                case AttemptStage.ReadyCaptureOne: return ControllerPolicy.ReadyCaptureOne(state, scenario, Capture(1, 1));
                case AttemptStage.ReadyCaptureTwo: return ControllerPolicy.ReadyCaptureTwo(state, scenario, Capture(1, 2));
                case AttemptStage.InputGuards: return ControllerPolicy.InputGuards(state, scenario, InputGuards());
                case AttemptStage.SendInput: return ControllerPolicy.SendInput(state, scenario, SendInput());
                case AttemptStage.CompleteCaptureOne: return ControllerPolicy.CompleteCaptureOne(state, scenario, Capture(2, 1));
                case AttemptStage.CompleteCaptureTwo: return ControllerPolicy.CompleteCaptureTwo(state, scenario, Capture(2, 2));
                case AttemptStage.Cleanup:
                    if (String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal)) return ControllerPolicy.CleanupUi(state, scenario, UiCleanup());
                    if (String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal)) return ControllerPolicy.CleanupTimeout(state, scenario, TimeoutCleanup());
                    return ControllerPolicy.CleanupLocked(state, scenario, LockedCleanup());
                case AttemptStage.RebindPublish: return ControllerPolicy.Rebind(state, scenario, Rebind());
                default: return null;
            }
        }

        private static AttemptState StateBefore(string scenario, AttemptStage target)
        {
            AttemptState state = AttemptState.Start(scenario);
            AttemptStage[] route = String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) ?
                new AttemptStage[]
                {
                    AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
                    AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
                    AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
                    AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
                    AttemptStage.WindowReady, AttemptStage.ReadyCaptureOne, AttemptStage.ReadyCaptureTwo,
                    AttemptStage.InputGuards, AttemptStage.SendInput, AttemptStage.CompleteCaptureOne,
                    AttemptStage.CompleteCaptureTwo, AttemptStage.Cleanup, AttemptStage.RebindPublish
                } : (String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal) ?
                new AttemptStage[]
                {
                    AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
                    AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
                    AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
                    AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
                    AttemptStage.Cleanup, AttemptStage.RebindPublish
                } : new AttemptStage[]
                {
                    AttemptStage.BindInputs, AttemptStage.PreflightRefusal,
                    AttemptStage.Cleanup, AttemptStage.RebindPublish
                });
            for (int index = 0; index < route.Length && route[index] != target; index++)
                Assert(state.Advance(ValidPermit(state, scenario, route[index])));
            return state;
        }

        private static void RelationshipMutationCases()
        {
            const string scenario = "ui-success-v1";
            Assert(Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, Relationship())));
            TokenRelationshipFacts value = Relationship(); value.ThreadTokenAbsent = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerPrimary = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerElevationFull = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerElevated = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerHighIntegrity = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerAdministrator = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerPrivilegeTupleExact = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellPrimary = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellElevationLimited = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellNotElevated = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellMediumIntegrity = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellNotAdministrator = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellPrivilegeTupleExact = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.SameUser = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.SameSession = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.SameAuthenticationId = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellHasRestrictions = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerLinkedTokenIdEqualsShellTokenId = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellLinkedTokenIdEqualsCallerTokenId = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.CallerLinkedElevationLimited = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ShellLinkedElevationFull = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.TokenIdsStable = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ModifiedIdsStable = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.PolicyShapeStable = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.AssignPrimaryPrivilegeAbsent = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.IncreaseQuotaPrivilegePresent = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.ProcessCreationNotAttempted = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
            value = Relationship(); value.FixtureExecutionNotAttempted = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore(scenario, AttemptStage.ExplorerToken), scenario, value)));
        }

        private static void LaunchTokenMutationCases()
        {
            const string scenario = "ui-success-v1";
            Assert(Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, LaunchToken())));
            LaunchTokenFacts value = LaunchToken(); value.DuplicatedExactlyOnce = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.SourceIsHeldProvenShellToken = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.DesiredAccessQueryDuplicateAssignPrimaryOnly = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.NonInheritable = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.Primary = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.SameUser = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.SameSession = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.SameAuthenticationId = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.MediumIntegrity = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.ElevationLimited = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.NotElevated = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.NotAdministrator = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.HasRestrictions = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.PrivilegeTupleExact = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
            value = LaunchToken(); value.ProcessCreationNotAttempted = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore(scenario, AttemptStage.PrimaryToken), scenario, value)));
        }

        private static void RejectAbortCleanup(AbortCleanupFacts facts)
        {
            const string scenario = "ui-success-v1";
            AttemptState state = StateBefore(scenario, AttemptStage.JobAssign);
            Assert(state.BeginAbort(ControllerPolicy.Abort(state, scenario, Abort())));
            Assert(!Allowed(ControllerPolicy.CleanupAbort(state, scenario, facts)));
        }

        private static void ComprehensiveMutationCases()
        {
            BindingFacts mutation0;
            mutation0 = Binding(); mutation0.ObservedControllerByteCount = 0; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedControllerSha256 = null; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ExpectedControllerByteCount = 0; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ExpectedControllerSha256 = null; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedFixtureByteCount = 0; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedFixtureSha256 = null; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedFixtureSourceByteCount = 0; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedFixtureSourceSha256 = null; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedFixtureProfileByteCount = 0; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedFixtureProfileSha256 = null; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedHostArtifactByteCount = 0; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.ObservedHostArtifactSha256 = null; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.SameHeldParent = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.SameVolume = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.DistinctObjects = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.SingleLinks = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.NoReparsePoints = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.StableBeforeAfter = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.FreshPrivateAttempt = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            mutation0 = Binding(); mutation0.GuardsDistinct = false; Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", mutation0)));
            PreflightFacts mutation1;
            mutation1 = Preflight(false); mutation1.ZeroGameProcesses = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.ZeroFixtureProcesses = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.ActiveConsoleSessionStable = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.ControllerSessionIsActiveConsole = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.ShellSessionIsActiveConsole = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.CanonicalExplorerSelected = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.DefaultInputDesktop = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.InputDesktopSwitchable = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.DesktopObservationStable = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.ProcessCreationCapabilityAbsent = true; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            mutation1 = Preflight(false); mutation1.ProcessCreationNotAttempted = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", mutation1)));
            TokenRelationshipFacts mutation2;
            mutation2 = Relationship(); mutation2.ThreadTokenAbsent = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerPrimary = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerElevationFull = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerElevated = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerHighIntegrity = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerAdministrator = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerPrivilegeTupleExact = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellPrimary = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellElevationLimited = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellNotElevated = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellMediumIntegrity = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellNotAdministrator = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellPrivilegeTupleExact = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.SameUser = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.SameSession = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.SameAuthenticationId = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellHasRestrictions = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerLinkedQuerySucceeded = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerLinkedHandleValid = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerLinkedTokenIdEqualsShellTokenId = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellLinkedQuerySucceeded = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellLinkedHandleValid = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellLinkedTokenIdEqualsCallerTokenId = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.CallerLinkedElevationLimited = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ShellLinkedElevationFull = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.TokenIdsStable = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ModifiedIdsStable = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.PolicyShapeStable = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.LinkedHandleOwnershipExact = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.AssignPrimaryPrivilegeAbsent = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.IncreaseQuotaPrivilegePresent = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.ProcessCreationNotAttempted = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            mutation2 = Relationship(); mutation2.FixtureExecutionNotAttempted = false; Assert(!Allowed(ControllerPolicy.TokenRelationship(StateBefore("ui-success-v1", AttemptStage.ExplorerToken), "ui-success-v1", mutation2)));
            LaunchTokenFacts mutation3;
            mutation3 = LaunchToken(); mutation3.DuplicatedExactlyOnce = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.DuplicateCallSucceeded = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.SourceIsHeldProvenShellToken = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.DesiredAccessQueryDuplicateAssignPrimaryOnly = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.NonInheritable = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.Primary = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.SameUser = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.SameSession = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.SameAuthenticationId = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.MediumIntegrity = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.ElevationLimited = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.NotElevated = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.NotAdministrator = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.HasRestrictions = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.PrivilegeTupleExact = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.SourceTokenIdStable = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.SourceModifiedIdStable = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.DuplicateTokenIdStable = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.DuplicateModifiedIdStable = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.SourceAndDuplicateHandlesHeld = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            mutation3 = LaunchToken(); mutation3.ProcessCreationNotAttempted = false; Assert(!Allowed(ControllerPolicy.LaunchToken(StateBefore("ui-success-v1", AttemptStage.PrimaryToken), "ui-success-v1", mutation3)));
            RegistryFacts mutation4;
            mutation4 = Registry(); mutation4.TargetId = null; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.RequestedAccess = 0; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.Wow64ViewFlags = 512; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.ExactResult = 0; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.EffectiveTokenIsHeldLaunchSource = false; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.ImpersonationActiveOnlyForRequest = false; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.ImpersonationRestored = false; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.ControllerTokenRestoredExact = false; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.LastWriteObservedBeforeAfter = false; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            mutation4 = Registry(); mutation4.LastWriteStable = false; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", mutation4)));
            GuardFacts mutation5;
            mutation5 = Guards(); mutation5.InstalledTreeSummaryComplete = false; Assert(!Allowed(ControllerPolicy.Guards(StateBefore("ui-success-v1", AttemptStage.GuardBefore), "ui-success-v1", mutation5)));
            mutation5 = Guards(); mutation5.VirtualStoreSummaryComplete = false; Assert(!Allowed(ControllerPolicy.Guards(StateBefore("ui-success-v1", AttemptStage.GuardBefore), "ui-success-v1", mutation5)));
            mutation5 = Guards(); mutation5.RegistrySummaryComplete = false; Assert(!Allowed(ControllerPolicy.Guards(StateBefore("ui-success-v1", AttemptStage.GuardBefore), "ui-success-v1", mutation5)));
            mutation5 = Guards(); mutation5.GuardsDistinctFromAttempt = false; Assert(!Allowed(ControllerPolicy.Guards(StateBefore("ui-success-v1", AttemptStage.GuardBefore), "ui-success-v1", mutation5)));
            mutation5 = Guards(); mutation5.NoWritableGuardHandles = false; Assert(!Allowed(ControllerPolicy.Guards(StateBefore("ui-success-v1", AttemptStage.GuardBefore), "ui-success-v1", mutation5)));
            EnvironmentFacts mutation6;
            mutation6 = EnvironmentBlock(); mutation6.Names = null; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.CaseSensitiveUnique = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.NoAmbientInheritance = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.ValuesContainNoControlCharacters = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.SystemRootEqualsWindowsDirectory = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.SystemPathsCanonicalAbsoluteInBox = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.TemporaryValuesEqual = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.TemporaryContainedByAttempt = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.TemporaryIsExactFixedAttemptChild = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.NoDriveCurrentDirectoryEntries = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.WorkingDirectoryHashExact = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.NonceIsNonzeroUInt32 = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            mutation6 = EnvironmentBlock(); mutation6.SortedDoubleNullUnicodeBlock = false; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", mutation6)));
            CreateApprovalFacts mutation7;
            mutation7 = CreateApproval(); mutation7.FixedSiblingTarget = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.LaunchTokenIsPolicyAccepted = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.IncreaseQuotaPresentBefore = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.AdjustCalledExactlyOnce = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.AdjustReturnedTrue = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.AdjustLastErrorSuccess = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.IncreaseQuotaEnabledAfter = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.AssignPrimaryPrivilegeStillAbsent = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.NoOtherPrivilegeChanged = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.ThreadTokenAbsent = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.RelationshipRevalidatedAfterAdjustment = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.LaunchTokenRevalidatedAfterAdjustment = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.NoPriorCreationAttempt = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.CreateProcessAsUserOnly = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.NoFallbackAttempted = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.InheritHandlesFalse = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.DesktopWinsta0DefaultExact = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.WorkingDirectoryExact = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            mutation7 = CreateApproval(); mutation7.OriginalExecutionNotAttempted = false; Assert(!Allowed(ControllerPolicy.ApproveCreate(StateBefore("ui-success-v1", AttemptStage.CreateApproved), "ui-success-v1", mutation7)));
            SuspendedChildFacts mutation8;
            mutation8 = SuspendedChild(); mutation8.CreateCalledExactlyOnce = false; Assert(!Allowed(ControllerPolicy.RecordSuspendedChild(StateBefore("ui-success-v1", AttemptStage.CreateSuspended), "ui-success-v1", mutation8)));
            mutation8 = SuspendedChild(); mutation8.CreateSucceeded = false; Assert(!Allowed(ControllerPolicy.RecordSuspendedChild(StateBefore("ui-success-v1", AttemptStage.CreateSuspended), "ui-success-v1", mutation8)));
            mutation8 = SuspendedChild(); mutation8.ChildCreatedSuspended = false; Assert(!Allowed(ControllerPolicy.RecordSuspendedChild(StateBefore("ui-success-v1", AttemptStage.CreateSuspended), "ui-success-v1", mutation8)));
            mutation8 = SuspendedChild(); mutation8.ChildIdentityReverified = false; Assert(!Allowed(ControllerPolicy.RecordSuspendedChild(StateBefore("ui-success-v1", AttemptStage.CreateSuspended), "ui-success-v1", mutation8)));
            mutation8 = SuspendedChild(); mutation8.PrimaryThreadSuspendCountOne = false; Assert(!Allowed(ControllerPolicy.RecordSuspendedChild(StateBefore("ui-success-v1", AttemptStage.CreateSuspended), "ui-success-v1", mutation8)));
            mutation8 = SuspendedChild(); mutation8.NoChildCodeObserved = false; Assert(!Allowed(ControllerPolicy.RecordSuspendedChild(StateBefore("ui-success-v1", AttemptStage.CreateSuspended), "ui-success-v1", mutation8)));
            JobFacts mutation9;
            mutation9 = Job(false); mutation9.CreatedWhileChildSuspended = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.KillOnClose = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.BreakawayForbidden = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.ActiveProcessLimit = 0; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.ProcessMemoryLimitBytes = 0; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.JobMemoryLimitBytes = 0; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.LimitsQueried = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.ChildStillSuspended = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.AssignedBeforeResume = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.MembershipQueried = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            mutation9 = Job(false); mutation9.ProcessNotResumed = false; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation9)));
            ResumeFacts mutation10;
            mutation10 = Resume(); mutation10.ResumeCallCount = 0; Assert(!Allowed(ControllerPolicy.Resume(StateBefore("ui-success-v1", AttemptStage.Resume), "ui-success-v1", mutation10)));
            mutation10 = Resume(); mutation10.PreviousSuspendCount = 0; Assert(!Allowed(ControllerPolicy.Resume(StateBefore("ui-success-v1", AttemptStage.Resume), "ui-success-v1", mutation10)));
            mutation10 = Resume(); mutation10.ThreadObservedRunning = false; Assert(!Allowed(ControllerPolicy.Resume(StateBefore("ui-success-v1", AttemptStage.Resume), "ui-success-v1", mutation10)));
            mutation10 = Resume(); mutation10.NoSecondResume = false; Assert(!Allowed(ControllerPolicy.Resume(StateBefore("ui-success-v1", AttemptStage.Resume), "ui-success-v1", mutation10)));
            PreResumeFacts mutation11;
            mutation11 = PreResume(); mutation11.BindingStillStable = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.GuardsStillStable = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.RelationshipRevalidated = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.LaunchTokenRevalidated = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.RegistryObservationStillBound = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.EnvironmentBlockStillBound = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.QuotaStateStillExact = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.ChildExactAndSuspended = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.JobMembershipExact = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.JobLimitsExact = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.ThreadTokenAbsent = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.DefaultDesktopRechecked = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.DesktopStillSwitchable = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.ZeroGameProcesses = false; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            mutation11 = PreResume(); mutation11.ResumeCallsSoFar = 1; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", mutation11)));
            WindowFacts mutation12;
            mutation12 = Window(); mutation12.UniqueVisibleUnownedTopLevel = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.ExactChildProcess = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.ProtocolExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.ReadyStateExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.ClientGeometryExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.ActiveSessionExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.DefaultDesktopExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.DisplayExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.DpiExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            mutation12 = Window(); mutation12.ForegroundExact = false; Assert(!Allowed(ControllerPolicy.Window(StateBefore("ui-success-v1", AttemptStage.WindowReady), "ui-success-v1", mutation12)));
            CaptureFacts mutation13;
            mutation13 = Capture(1, 1); mutation13.Width = 0; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.Height = 0; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.Ordinal = 0; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.ObservedStateId = 0; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.ClientRectangleOnly = false; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.DesktopDcBitBltOnly = false; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.EveryPixelExpected = false; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.CanonicalBmpExact = false; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.MatchesFirstCapture = true; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            mutation13 = Capture(1, 1); mutation13.UnexpectedPixelsDiscardedAndZeroed = false; Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", mutation13)));
            InputGuardFacts mutation14;
            mutation14 = InputGuards(); mutation14.AllRelevantInputUp = false; Assert(!Allowed(ControllerPolicy.InputGuards(StateBefore("ui-success-v1", AttemptStage.InputGuards), "ui-success-v1", mutation14)));
            mutation14 = InputGuards(); mutation14.ForegroundRechecked = false; Assert(!Allowed(ControllerPolicy.InputGuards(StateBefore("ui-success-v1", AttemptStage.InputGuards), "ui-success-v1", mutation14)));
            mutation14 = InputGuards(); mutation14.DesktopRechecked = false; Assert(!Allowed(ControllerPolicy.InputGuards(StateBefore("ui-success-v1", AttemptStage.InputGuards), "ui-success-v1", mutation14)));
            mutation14 = InputGuards(); mutation14.FixedClientPoint = false; Assert(!Allowed(ControllerPolicy.InputGuards(StateBefore("ui-success-v1", AttemptStage.InputGuards), "ui-success-v1", mutation14)));
            SendInputFacts mutation15;
            mutation15 = SendInput(); mutation15.ExactNonce = false; Assert(!Allowed(ControllerPolicy.SendInput(StateBefore("ui-success-v1", AttemptStage.SendInput), "ui-success-v1", mutation15)));
            mutation15 = SendInput(); mutation15.UsedSendInputOnly = false; Assert(!Allowed(ControllerPolicy.SendInput(StateBefore("ui-success-v1", AttemptStage.SendInput), "ui-success-v1", mutation15)));
            mutation15 = SendInput(); mutation15.InsertedEventCount = 0; Assert(!Allowed(ControllerPolicy.SendInput(StateBefore("ui-success-v1", AttemptStage.SendInput), "ui-success-v1", mutation15)));
            mutation15 = SendInput(); mutation15.CompleteStateExact = false; Assert(!Allowed(ControllerPolicy.SendInput(StateBefore("ui-success-v1", AttemptStage.SendInput), "ui-success-v1", mutation15)));
            UiCleanupFacts mutation16;
            mutation16 = UiCleanup(); mutation16.OrderlyCloseRequested = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            mutation16 = UiCleanup(); mutation16.OrderlyCloseSucceeded = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            mutation16 = UiCleanup(); mutation16.GraceBounded = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            mutation16 = UiCleanup(); mutation16.JobEmpty = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            mutation16 = UiCleanup(); mutation16.HandlesClosed = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            mutation16 = UiCleanup(); mutation16.QuotaPrivilegeRestored = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            mutation16 = UiCleanup(); mutation16.ZeroFixtureProcesses = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            mutation16 = UiCleanup(); mutation16.ZeroGameProcesses = false; Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", mutation16)));
            TimeoutCleanupFacts mutation17;
            mutation17 = TimeoutCleanup(); mutation17.ExactlyOneDescendantObserved = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.TimeoutBounded = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.WholeJobTerminationRequested = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.WholeJobTerminationSucceeded = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.ActiveProcessCountZero = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.JobEmpty = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.HandlesClosed = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.QuotaPrivilegeRestored = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.ZeroFixtureProcesses = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            mutation17 = TimeoutCleanup(); mutation17.ZeroGameProcesses = false; Assert(!Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", mutation17)));
            LockedCleanupFacts mutation18;
            mutation18 = LockedCleanup(); mutation18.ProcessCreationCapabilityAbsent = false; Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", mutation18)));
            mutation18 = LockedCleanup(); mutation18.ProcessCreationNotAttempted = false; Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", mutation18)));
            mutation18 = LockedCleanup(); mutation18.FixtureExecutionNotAttempted = false; Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", mutation18)));
            mutation18 = LockedCleanup(); mutation18.ZeroFixtureProcesses = false; Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", mutation18)));
            mutation18 = LockedCleanup(); mutation18.ZeroGameProcesses = false; Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", mutation18)));
            mutation18 = LockedCleanup(); mutation18.ZeroAttemptArtifacts = false; Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", mutation18)));
            mutation18 = LockedCleanup(); mutation18.NoProcessOrTokenHandlesOpened = false; Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", mutation18)));
            RebindFacts mutation19;
            mutation19 = Rebind(); mutation19.InputsStable = false; Assert(!Allowed(ControllerPolicy.Rebind(StateBefore("ui-success-v1", AttemptStage.RebindPublish), "ui-success-v1", mutation19)));
            mutation19 = Rebind(); mutation19.InstalledTreeStable = false; Assert(!Allowed(ControllerPolicy.Rebind(StateBefore("ui-success-v1", AttemptStage.RebindPublish), "ui-success-v1", mutation19)));
            mutation19 = Rebind(); mutation19.VirtualStoreStable = false; Assert(!Allowed(ControllerPolicy.Rebind(StateBefore("ui-success-v1", AttemptStage.RebindPublish), "ui-success-v1", mutation19)));
            mutation19 = Rebind(); mutation19.RegistryStable = false; Assert(!Allowed(ControllerPolicy.Rebind(StateBefore("ui-success-v1", AttemptStage.RebindPublish), "ui-success-v1", mutation19)));
            mutation19 = Rebind(); mutation19.ZeroFixtureProcesses = false; Assert(!Allowed(ControllerPolicy.Rebind(StateBefore("ui-success-v1", AttemptStage.RebindPublish), "ui-success-v1", mutation19)));
            mutation19 = Rebind(); mutation19.ZeroGameProcesses = false; Assert(!Allowed(ControllerPolicy.Rebind(StateBefore("ui-success-v1", AttemptStage.RebindPublish), "ui-success-v1", mutation19)));
            mutation19 = Rebind(); mutation19.PublicationNotAttempted = false; Assert(!Allowed(ControllerPolicy.Rebind(StateBefore("ui-success-v1", AttemptStage.RebindPublish), "ui-success-v1", mutation19)));
            AbortFacts mutation20;
            mutation20 = Abort(); mutation20.FailureRecorded = false; Assert(!Allowed(ControllerPolicy.Abort(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation20)));
            mutation20 = Abort(); mutation20.NoFurtherAuthorityAttempted = false; Assert(!Allowed(ControllerPolicy.Abort(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation20)));
            mutation20 = Abort(); mutation20.OriginalExecutionNotAttempted = false; Assert(!Allowed(ControllerPolicy.Abort(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation20)));
            mutation20 = Abort(); mutation20.UnexpectedPixelsDiscardedAndZeroed = false; Assert(!Allowed(ControllerPolicy.Abort(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", mutation20)));
            AbortCleanupFacts abortCleanup;
            abortCleanup = AbortCleanup(); abortCleanup.PrivilegeStateRestoredIfChanged = false; RejectAbortCleanup(abortCleanup);
            abortCleanup = AbortCleanup(); abortCleanup.ChildAndJobTerminatedIfCreated = false; RejectAbortCleanup(abortCleanup);
            abortCleanup = AbortCleanup(); abortCleanup.JobEmptyIfCreated = false; RejectAbortCleanup(abortCleanup);
            abortCleanup = AbortCleanup(); abortCleanup.HandlesClosed = false; RejectAbortCleanup(abortCleanup);
            abortCleanup = AbortCleanup(); abortCleanup.GuardsStable = false; RejectAbortCleanup(abortCleanup);
            abortCleanup = AbortCleanup(); abortCleanup.ZeroFixtureProcesses = false; RejectAbortCleanup(abortCleanup);
            abortCleanup = AbortCleanup(); abortCleanup.ZeroGameProcesses = false; RejectAbortCleanup(abortCleanup);
            PreflightFacts lockedMutation = Preflight(true); lockedMutation.ZeroAttemptArtifacts = false; Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("locked-refusal-v1", AttemptStage.PreflightRefusal), "locked-refusal-v1", lockedMutation)));
        }

        private static void PolicyBoundaryCases()
        {
            BindingFacts binding = Binding();
            Assert(Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", binding)));
            binding.ObservedFixtureSha256 = new String('0', 64); Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", binding)));
            binding = Binding(); binding.ObservedControllerSha256 = new String('A', 64); Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "ui-success-v1", binding)));
            Assert(!Allowed(ControllerPolicy.Binding(StateBefore("ui-success-v1", AttemptStage.BindInputs), "unknown", Binding())));

            Assert(Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", Preflight(false))));
            Assert(Allowed(ControllerPolicy.Preflight(StateBefore("locked-refusal-v1", AttemptStage.PreflightRefusal), "locked-refusal-v1", Preflight(true))));
            PreflightFacts preflight = Preflight(true); preflight.ProcessCreationNotAttempted = false;
            Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("locked-refusal-v1", AttemptStage.PreflightRefusal), "locked-refusal-v1", preflight)));
            Assert(!Allowed(ControllerPolicy.Preflight(StateBefore("ui-success-v1", AttemptStage.PreflightRefusal), "ui-success-v1", Preflight(true))));

            RegistryFacts registry = Registry(); Assert(Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", registry)));
            registry.RequestedAccess = 0; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", registry)));
            registry = Registry(); registry.Wow64ViewFlags = 0x200; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", registry)));
            registry = Registry(); registry.TargetId = "other"; Assert(!Allowed(ControllerPolicy.Registry(StateBefore("ui-success-v1", AttemptStage.RegistryDenial), "ui-success-v1", registry)));

            EnvironmentFacts environment = EnvironmentBlock(); Assert(Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", environment)));
            environment.Names[0] = "PATH"; Assert(!Allowed(ControllerPolicy.Environment(StateBefore("ui-success-v1", AttemptStage.Environment), "ui-success-v1", environment)));
            Assert(String.Equals(FixedControllerContract.EnvironmentNameAt(0), "CM0102_SYNTHETIC_CWD_SHA256", StringComparison.Ordinal));

            JobFacts job = Job(false); Assert(Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", job)));
            Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("tree-timeout-v1", AttemptStage.JobAssign), "tree-timeout-v1", Job(false))));
            Assert(Allowed(ControllerPolicy.JobBeforeResume(StateBefore("tree-timeout-v1", AttemptStage.JobAssign), "tree-timeout-v1", Job(true))));
            Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("ui-success-v1", AttemptStage.JobAssign), "ui-success-v1", Job(true))));
            job = Job(true); job.ActiveProcessLimit = 0; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("tree-timeout-v1", AttemptStage.JobAssign), "tree-timeout-v1", job)));
            job = Job(true); job.ActiveProcessLimit = 3; Assert(!Allowed(ControllerPolicy.JobBeforeResume(StateBefore("tree-timeout-v1", AttemptStage.JobAssign), "tree-timeout-v1", job)));

            PreResumeFacts beforeResume = PreResume(); Assert(Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", beforeResume)));
            beforeResume.ResumeCallsSoFar = 1; Assert(!Allowed(ControllerPolicy.PreResume(StateBefore("ui-success-v1", AttemptStage.PreResumeApproved), "ui-success-v1", beforeResume)));
            ResumeFacts resumed = Resume(); resumed.ResumeCallCount = 2; Assert(!Allowed(ControllerPolicy.Resume(StateBefore("ui-success-v1", AttemptStage.Resume), "ui-success-v1", resumed)));

            CaptureFacts capture = Capture(1, 1); Assert(Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", capture)));
            Assert(!Allowed(ControllerPolicy.ReadyCaptureTwo(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", capture)));
            capture = Capture(1, 2); Assert(Allowed(ControllerPolicy.ReadyCaptureTwo(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureTwo), "ui-success-v1", capture)));
            capture.MatchesFirstCapture = false; Assert(!Allowed(ControllerPolicy.ReadyCaptureTwo(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureTwo), "ui-success-v1", capture)));
            capture = Capture(2, 1); Assert(!Allowed(ControllerPolicy.ReadyCaptureOne(StateBefore("ui-success-v1", AttemptStage.ReadyCaptureOne), "ui-success-v1", capture)));

            Assert(Allowed(ControllerPolicy.CleanupUi(StateBefore("ui-success-v1", AttemptStage.Cleanup), "ui-success-v1", UiCleanup())));
            Assert(!Allowed(ControllerPolicy.CleanupUi(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", UiCleanup())));
            Assert(Allowed(ControllerPolicy.CleanupTimeout(StateBefore("tree-timeout-v1", AttemptStage.Cleanup), "tree-timeout-v1", TimeoutCleanup())));
            Assert(Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", LockedCleanup())));
            LockedCleanupFacts locked = LockedCleanup(); locked.ProcessCreationNotAttempted = false;
            Assert(!Allowed(ControllerPolicy.CleanupLocked(StateBefore("locked-refusal-v1", AttemptStage.Cleanup), "locked-refusal-v1", locked)));
        }

        private static void AdvanceRoute(AttemptState state, string scenario, AttemptStage[] route)
        {
            for (int index = 0; index < route.Length; index++)
            {
                ControllerPolicy.Permit permit = ValidPermit(state, scenario, route[index]);
                Assert(permit != null);
                Assert(state.Advance(permit));
            }
        }

        private static void StateCases()
        {
            const string uiScenario = "ui-success-v1";
            AttemptStage[] uiRoute = new AttemptStage[]
            {
                AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
                AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
                AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
                AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
                AttemptStage.WindowReady, AttemptStage.ReadyCaptureOne, AttemptStage.ReadyCaptureTwo,
                AttemptStage.InputGuards, AttemptStage.SendInput, AttemptStage.CompleteCaptureOne,
                AttemptStage.CompleteCaptureTwo, AttemptStage.Cleanup, AttemptStage.RebindPublish
            };
            AttemptState ui = AttemptState.Start(uiScenario);
            AdvanceRoute(ui, uiScenario, uiRoute);
            Assert(ui.AcceptedStageCount == 21);
            Assert(ui.Complete(AttemptTerminal.UiComplete));
            Assert(ui.IsTerminal);
            Assert(!ui.Advance(ControllerPolicy.Binding(ui, uiScenario, Binding())));
            Assert(!ui.Complete(AttemptTerminal.UiComplete));

            AttemptState reordered = AttemptState.Start(uiScenario);
            ControllerPolicy.Permit premature = ControllerPolicy.Preflight(reordered, uiScenario, Preflight(false));
            Assert(premature == null);
            Assert(!reordered.Advance(premature));
            Assert(reordered.IsRejected);
            Assert(reordered.AcceptedStageCount == 0);

            AttemptState first = AttemptState.Start(uiScenario);
            AttemptState second = AttemptState.Start(uiScenario);
            ControllerPolicy.Permit bound = ControllerPolicy.Binding(first, uiScenario, Binding());
            Assert(first.Advance(bound));
            Assert(!second.Advance(bound));
            Assert(second.IsRejected);
            Assert(!first.Advance(bound));
            Assert(first.IsRejected);

            const string timeout = "tree-timeout-v1";
            AttemptState tree = AttemptState.Start(timeout);
            AttemptStage[] treeRoute = new AttemptStage[]
            {
                AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
                AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
                AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
                AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
                AttemptStage.Cleanup, AttemptStage.RebindPublish
            };
            AdvanceRoute(tree, timeout, treeRoute);
            Assert(tree.Complete(AttemptTerminal.ExpectedTimeout));

            const string locked = "locked-refusal-v1";
            AttemptState refusal = AttemptState.Start(locked);
            AdvanceRoute(refusal, locked, new AttemptStage[]
            {
                AttemptStage.BindInputs, AttemptStage.PreflightRefusal,
                AttemptStage.Cleanup, AttemptStage.RebindPublish
            });
            Assert(refusal.Complete(AttemptTerminal.LockedRefusal));

            AttemptState forbidden = StateBefore(locked, AttemptStage.Cleanup);
            ControllerPolicy.Permit token = ControllerPolicy.TokenRelationship(forbidden, locked, Relationship());
            Assert(token == null);
            Assert(!forbidden.Advance(token));
            Assert(forbidden.IsRejected);

            AttemptState aborting = StateBefore(uiScenario, AttemptStage.JobAssign);
            ControllerPolicy.Permit abortPermit = ControllerPolicy.Abort(aborting, uiScenario, Abort());
            Assert(abortPermit != null);
            Assert(aborting.BeginAbort(abortPermit));
            Assert(aborting.Advance(ControllerPolicy.CleanupAbort(aborting, uiScenario, AbortCleanup())));
            Assert(aborting.Advance(ControllerPolicy.Rebind(aborting, uiScenario, Rebind())));
            Assert(aborting.Complete(AttemptTerminal.Ineligible));

            AttemptState abortOwner = StateBefore(uiScenario, AttemptStage.CreateSuspended);
            AttemptState abortOther = StateBefore(uiScenario, AttemptStage.CreateSuspended);
            ControllerPolicy.Permit ownedAbort = ControllerPolicy.Abort(abortOwner, uiScenario, Abort());
            Assert(!abortOther.BeginAbort(ownedAbort));
            Assert(abortOther.IsRejected);
            Assert(abortOwner.BeginAbort(ownedAbort));
            Assert(!abortOwner.BeginAbort(ownedAbort));
            Assert(abortOwner.IsRejected);

            AttemptState tooEarly = AttemptState.Start(uiScenario);
            Assert(!tooEarly.Advance(null));
            Assert(tooEarly.BeginAbort(ControllerPolicy.Abort(tooEarly, uiScenario, Abort())));
            Assert(tooEarly.Advance(ControllerPolicy.CleanupAbort(tooEarly, uiScenario, AbortCleanup())));
            Assert(tooEarly.Advance(ControllerPolicy.Rebind(tooEarly, uiScenario, Rebind())));
            Assert(tooEarly.Complete(AttemptTerminal.Ineligible));

            AttemptState rejectedAfterCreate = StateBefore(uiScenario, AttemptStage.JobAssign);
            Assert(!rejectedAfterCreate.Advance(null));
            Assert(rejectedAfterCreate.IsRejected);
            Assert(rejectedAfterCreate.BeginAbort(ControllerPolicy.Abort(rejectedAfterCreate, uiScenario, Abort())));
            Assert(rejectedAfterCreate.Advance(ControllerPolicy.CleanupAbort(rejectedAfterCreate, uiScenario, AbortCleanup())));
            Assert(rejectedAfterCreate.Advance(ControllerPolicy.Rebind(rejectedAfterCreate, uiScenario, Rebind())));
            Assert(rejectedAfterCreate.Complete(AttemptTerminal.Ineligible));

            AttemptState cleanupFailure = StateBefore(uiScenario, AttemptStage.Cleanup);
            UiCleanupFacts failedCleanup = UiCleanup();
            failedCleanup.JobEmpty = false;
            Assert(!cleanupFailure.Advance(ControllerPolicy.CleanupUi(cleanupFailure, uiScenario, failedCleanup)));
            Assert(cleanupFailure.BeginAbort(ControllerPolicy.Abort(cleanupFailure, uiScenario, Abort())));
            Assert(cleanupFailure.Advance(ControllerPolicy.CleanupAbort(cleanupFailure, uiScenario, AbortCleanup())));
            Assert(cleanupFailure.Advance(ControllerPolicy.Rebind(cleanupFailure, uiScenario, Rebind())));
            Assert(cleanupFailure.Complete(AttemptTerminal.Ineligible));

            AttemptState rebindFailure = StateBefore(uiScenario, AttemptStage.RebindPublish);
            RebindFacts failedRebind = Rebind();
            failedRebind.RegistryStable = false;
            Assert(!rebindFailure.Advance(ControllerPolicy.Rebind(rebindFailure, uiScenario, failedRebind)));
            Assert(rebindFailure.BeginAbort(ControllerPolicy.Abort(rebindFailure, uiScenario, Abort())));
            Assert(rebindFailure.Advance(ControllerPolicy.CleanupAbort(rebindFailure, uiScenario, AbortCleanup())));
            Assert(rebindFailure.Advance(ControllerPolicy.Rebind(rebindFailure, uiScenario, Rebind())));
            Assert(rebindFailure.Complete(AttemptTerminal.Ineligible));

            AttemptState abortRetry = StateBefore(uiScenario, AttemptStage.JobAssign);
            Assert(abortRetry.BeginAbort(ControllerPolicy.Abort(abortRetry, uiScenario, Abort())));
            AbortCleanupFacts failedAbortCleanup = AbortCleanup();
            failedAbortCleanup.HandlesClosed = false;
            Assert(!abortRetry.Advance(ControllerPolicy.CleanupAbort(abortRetry, uiScenario, failedAbortCleanup)));
            Assert(abortRetry.IsRejected);
            Assert(abortRetry.Advance(ControllerPolicy.CleanupAbort(abortRetry, uiScenario, AbortCleanup())));
            Assert(abortRetry.Advance(ControllerPolicy.Rebind(abortRetry, uiScenario, Rebind())));
            Assert(abortRetry.Complete(AttemptTerminal.Ineligible));

            Assert(ControllerPolicy.CleanupAbort(StateBefore(uiScenario, AttemptStage.Cleanup), uiScenario, AbortCleanup()) == null);
            Assert(ControllerPolicy.CleanupAbort(StateBefore(timeout, AttemptStage.Cleanup), timeout, AbortCleanup()) == null);
            Assert(ControllerPolicy.CleanupAbort(StateBefore(locked, AttemptStage.Cleanup), locked, AbortCleanup()) == null);

            AttemptState abortUiMode = StateBefore(uiScenario, AttemptStage.JobAssign);
            Assert(abortUiMode.BeginAbort(ControllerPolicy.Abort(abortUiMode, uiScenario, Abort())));
            Assert(ControllerPolicy.CleanupUi(abortUiMode, uiScenario, UiCleanup()) == null);
            AttemptState abortTimeoutMode = StateBefore(timeout, AttemptStage.JobAssign);
            Assert(abortTimeoutMode.BeginAbort(ControllerPolicy.Abort(abortTimeoutMode, timeout, Abort())));
            Assert(ControllerPolicy.CleanupTimeout(abortTimeoutMode, timeout, TimeoutCleanup()) == null);
            AttemptState abortLockedMode = StateBefore(locked, AttemptStage.Cleanup);
            Assert(abortLockedMode.BeginAbort(ControllerPolicy.Abort(abortLockedMode, locked, Abort())));
            Assert(ControllerPolicy.CleanupLocked(abortLockedMode, locked, LockedCleanup()) == null);

            bool threw = false;
            try { AttemptState.Start("unknown"); }
            catch (ArgumentException) { threw = true; }
            Assert(threw);
        }

        private static int Main()
        {
            RelationshipMutationCases();
            LaunchTokenMutationCases();
            ComprehensiveMutationCases();
            PolicyBoundaryCases();
            StateCases();
            Console.WriteLine("PASS " + assertions.ToString());
            return 0;
        }
    }
}
