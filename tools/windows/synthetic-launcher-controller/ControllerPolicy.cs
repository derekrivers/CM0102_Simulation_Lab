using System;

namespace Cm0102.SyntheticLauncherController
{
    internal enum AttemptStage
    {
        BindInputs = 1,
        PreflightRefusal = 2,
        ExplorerToken = 3,
        PrimaryToken = 4,
        RegistryDenial = 5,
        GuardBefore = 6,
        Environment = 7,
        CreateApproved = 8,
        CreateSuspended = 9,
        JobAssign = 10,
        PreResumeApproved = 11,
        Resume = 12,
        WindowReady = 13,
        ReadyCaptureOne = 14,
        ReadyCaptureTwo = 15,
        InputGuards = 16,
        SendInput = 17,
        CompleteCaptureOne = 18,
        CompleteCaptureTwo = 19,
        Abort = 20,
        Cleanup = 21,
        RebindPublish = 22
    }

    internal enum AttemptTerminal
    {
        UiComplete = 1,
        ExpectedTimeout = 2,
        LockedRefusal = 3,
        Ineligible = 4
    }

    internal static class FixedControllerContract
    {
        internal const string ControllerName = "SyntheticLauncherController.exe";
        internal const string FixtureName = "SyntheticLauncherFixture.exe";
        internal const string PublicConfigurationName = "SyntheticLauncherController.public.v1.json";
        internal const string PrivateConfigurationName = "SyntheticLauncherController.private.v1.json";
        internal const string RelationshipPolicyId = "uac-linked-filtered-v1";
        internal const string RegistryTargetId = "cm0102-installation-32-v1";
        internal const int RegistryAllAccess = 0x000F003F;
        internal const long FixtureByteCount = 14336;
        internal const string FixtureSha256 = "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6";
        internal const long FixtureSourceByteCount = 20355;
        internal const string FixtureSourceSha256 = "d730bda0acc2cf89ab6e212f49620a2e42b00392a3976f1467c0931bce66ae1c";
        internal const long FixtureProfileByteCount = 1104;
        internal const string FixtureProfileSha256 = "e9952158c5789149ab0bda8e1afc90f1467281b2e1ca1155a2e780a8276aa80b";
        internal const long AcceptedHostArtifactByteCount = 3310;
        internal const string AcceptedHostArtifactSha256 = "96e38bb7932e1acb64aa7c9a33012f3425318b3a8e3aaf7ce98aaf8e1cd27659";
        internal const long ProcessMemoryLimitBytes = 268435456;
        internal const long UiJobMemoryLimitBytes = 268435456;
        internal const long TimeoutJobMemoryLimitBytes = 536870912;
        internal const int EnvironmentNameCount = 6;

        internal static string EnvironmentNameAt(int index)
        {
            switch (index)
            {
                case 0: return "CM0102_SYNTHETIC_CWD_SHA256";
                case 1: return "CM0102_SYNTHETIC_INPUT_NONCE";
                case 2: return "SystemRoot";
                case 3: return "TEMP";
                case 4: return "TMP";
                case 5: return "WINDIR";
                default: return null;
            }
        }

        internal static bool IsScenario(string value)
        {
            return String.Equals(value, "ui-success-v1", StringComparison.Ordinal) ||
                String.Equals(value, "tree-timeout-v1", StringComparison.Ordinal) ||
                String.Equals(value, "locked-refusal-v1", StringComparison.Ordinal);
        }
    }

    internal sealed class BindingFacts
    {
        internal long ObservedControllerByteCount;
        internal string ObservedControllerSha256;
        internal long ExpectedControllerByteCount;
        internal string ExpectedControllerSha256;
        internal long ObservedFixtureByteCount;
        internal string ObservedFixtureSha256;
        internal long ObservedFixtureSourceByteCount;
        internal string ObservedFixtureSourceSha256;
        internal long ObservedFixtureProfileByteCount;
        internal string ObservedFixtureProfileSha256;
        internal long ObservedHostArtifactByteCount;
        internal string ObservedHostArtifactSha256;
        internal bool SameHeldParent;
        internal bool SameVolume;
        internal bool DistinctObjects;
        internal bool SingleLinks;
        internal bool NoReparsePoints;
        internal bool StableBeforeAfter;
        internal bool FreshPrivateAttempt;
        internal bool GuardsDistinct;
    }

    internal sealed class PreflightFacts
    {
        internal bool ZeroGameProcesses;
        internal bool ZeroFixtureProcesses;
        internal bool ActiveConsoleSessionStable;
        internal bool ControllerSessionIsActiveConsole;
        internal bool ShellSessionIsActiveConsole;
        internal bool CanonicalExplorerSelected;
        internal bool DefaultInputDesktop;
        internal bool InputDesktopSwitchable;
        internal bool DesktopObservationStable;
        internal bool ProcessCreationCapabilityAbsent;
        internal bool ProcessCreationNotAttempted;
        internal bool ZeroAttemptArtifacts;
    }

    internal sealed class TokenRelationshipFacts
    {
        internal bool ThreadTokenAbsent;
        internal bool CallerPrimary;
        internal bool CallerElevationFull;
        internal bool CallerElevated;
        internal bool CallerHighIntegrity;
        internal bool CallerAdministrator;
        internal bool CallerPrivilegeTupleExact;
        internal bool ShellPrimary;
        internal bool ShellElevationLimited;
        internal bool ShellNotElevated;
        internal bool ShellMediumIntegrity;
        internal bool ShellNotAdministrator;
        internal bool ShellPrivilegeTupleExact;
        internal bool SameUser;
        internal bool SameSession;
        internal bool SameAuthenticationId;
        internal bool ShellHasRestrictions;
        internal bool CallerLinkedQuerySucceeded;
        internal bool CallerLinkedHandleValid;
        internal bool CallerLinkedTokenIdEqualsShellTokenId;
        internal bool ShellLinkedQuerySucceeded;
        internal bool ShellLinkedHandleValid;
        internal bool ShellLinkedTokenIdEqualsCallerTokenId;
        internal bool CallerLinkedElevationLimited;
        internal bool ShellLinkedElevationFull;
        internal bool TokenIdsStable;
        internal bool ModifiedIdsStable;
        internal bool PolicyShapeStable;
        internal bool LinkedHandleOwnershipExact;
        internal bool AssignPrimaryPrivilegeAbsent;
        internal bool IncreaseQuotaPrivilegePresent;
        internal bool ProcessCreationNotAttempted;
        internal bool FixtureExecutionNotAttempted;
    }

    internal sealed class LaunchTokenFacts
    {
        internal bool DuplicatedExactlyOnce;
        internal bool DuplicateCallSucceeded;
        internal bool SourceIsHeldProvenShellToken;
        internal bool DesiredAccessQueryDuplicateAssignPrimaryOnly;
        internal bool NonInheritable;
        internal bool Primary;
        internal bool SameUser;
        internal bool SameSession;
        internal bool SameAuthenticationId;
        internal bool MediumIntegrity;
        internal bool ElevationLimited;
        internal bool NotElevated;
        internal bool NotAdministrator;
        internal bool HasRestrictions;
        internal bool PrivilegeTupleExact;
        internal bool SourceTokenIdStable;
        internal bool SourceModifiedIdStable;
        internal bool DuplicateTokenIdStable;
        internal bool DuplicateModifiedIdStable;
        internal bool SourceAndDuplicateHandlesHeld;
        internal bool ProcessCreationNotAttempted;
    }

    internal sealed class RegistryFacts
    {
        internal string TargetId;
        internal int RequestedAccess;
        internal int Wow64ViewFlags;
        internal int ExactResult;
        internal bool EffectiveTokenIsHeldLaunchSource;
        internal bool ImpersonationActiveOnlyForRequest;
        internal bool ImpersonationRestored;
        internal bool ControllerTokenRestoredExact;
        internal bool LastWriteObservedBeforeAfter;
        internal bool LastWriteStable;
    }

    internal sealed class GuardFacts
    {
        internal bool InstalledTreeSummaryComplete;
        internal bool VirtualStoreSummaryComplete;
        internal bool RegistrySummaryComplete;
        internal bool GuardsDistinctFromAttempt;
        internal bool NoWritableGuardHandles;
    }

    internal sealed class EnvironmentFacts
    {
        internal string[] Names;
        internal bool CaseSensitiveUnique;
        internal bool NoAmbientInheritance;
        internal bool ValuesContainNoControlCharacters;
        internal bool SystemRootEqualsWindowsDirectory;
        internal bool SystemPathsCanonicalAbsoluteInBox;
        internal bool TemporaryValuesEqual;
        internal bool TemporaryContainedByAttempt;
        internal bool TemporaryIsExactFixedAttemptChild;
        internal bool NoDriveCurrentDirectoryEntries;
        internal bool WorkingDirectoryHashExact;
        internal bool NonceIsNonzeroUInt32;
        internal bool SortedDoubleNullUnicodeBlock;
    }

    internal sealed class CreateApprovalFacts
    {
        internal bool FixedSiblingTarget;
        internal bool LaunchTokenIsPolicyAccepted;
        internal bool IncreaseQuotaPresentBefore;
        internal bool AdjustCalledExactlyOnce;
        internal bool AdjustReturnedTrue;
        internal bool AdjustLastErrorSuccess;
        internal bool IncreaseQuotaEnabledAfter;
        internal bool AssignPrimaryPrivilegeStillAbsent;
        internal bool NoOtherPrivilegeChanged;
        internal bool ThreadTokenAbsent;
        internal bool RelationshipRevalidatedAfterAdjustment;
        internal bool LaunchTokenRevalidatedAfterAdjustment;
        internal bool NoPriorCreationAttempt;
        internal bool CreateProcessAsUserOnly;
        internal bool NoFallbackAttempted;
        internal bool InheritHandlesFalse;
        internal bool DesktopWinsta0DefaultExact;
        internal bool WorkingDirectoryExact;
        internal bool OriginalExecutionNotAttempted;
    }

    internal sealed class SuspendedChildFacts
    {
        internal bool CreateCalledExactlyOnce;
        internal bool CreateSucceeded;
        internal bool ChildCreatedSuspended;
        internal bool ChildIdentityReverified;
        internal bool PrimaryThreadSuspendCountOne;
        internal bool NoChildCodeObserved;
    }

    internal sealed class JobFacts
    {
        internal bool CreatedWhileChildSuspended;
        internal bool KillOnClose;
        internal bool BreakawayForbidden;
        internal int ActiveProcessLimit;
        internal long ProcessMemoryLimitBytes;
        internal long JobMemoryLimitBytes;
        internal bool LimitsQueried;
        internal bool ChildStillSuspended;
        internal bool AssignedBeforeResume;
        internal bool MembershipQueried;
        internal bool ProcessNotResumed;
    }

    internal sealed class ResumeFacts
    {
        internal int ResumeCallCount;
        internal int PreviousSuspendCount;
        internal bool ThreadObservedRunning;
        internal bool NoSecondResume;
    }

    internal sealed class PreResumeFacts
    {
        internal bool BindingStillStable;
        internal bool GuardsStillStable;
        internal bool RelationshipRevalidated;
        internal bool LaunchTokenRevalidated;
        internal bool RegistryObservationStillBound;
        internal bool EnvironmentBlockStillBound;
        internal bool QuotaStateStillExact;
        internal bool ChildExactAndSuspended;
        internal bool JobMembershipExact;
        internal bool JobLimitsExact;
        internal bool ThreadTokenAbsent;
        internal bool DefaultDesktopRechecked;
        internal bool DesktopStillSwitchable;
        internal bool ZeroGameProcesses;
        internal int ResumeCallsSoFar;
    }

    internal sealed class WindowFacts
    {
        internal bool UniqueVisibleUnownedTopLevel;
        internal bool ExactChildProcess;
        internal bool ProtocolExact;
        internal bool ReadyStateExact;
        internal bool ClientGeometryExact;
        internal bool ActiveSessionExact;
        internal bool DefaultDesktopExact;
        internal bool DisplayExact;
        internal bool DpiExact;
        internal bool ForegroundExact;
    }

    internal sealed class CaptureFacts
    {
        internal int Width;
        internal int Height;
        internal int Ordinal;
        internal int ObservedStateId;
        internal bool ClientRectangleOnly;
        internal bool DesktopDcBitBltOnly;
        internal bool EveryPixelExpected;
        internal bool CanonicalBmpExact;
        internal bool MatchesFirstCapture;
        internal bool UnexpectedPixelsDiscardedAndZeroed;
    }

    internal sealed class InputGuardFacts
    {
        internal bool AllRelevantInputUp;
        internal bool ForegroundRechecked;
        internal bool DesktopRechecked;
        internal bool FixedClientPoint;
    }

    internal sealed class SendInputFacts
    {
        internal bool ExactNonce;
        internal bool UsedSendInputOnly;
        internal int InsertedEventCount;
        internal bool CompleteStateExact;
    }

    internal sealed class UiCleanupFacts
    {
        internal bool OrderlyCloseRequested;
        internal bool OrderlyCloseSucceeded;
        internal bool GraceBounded;
        internal bool JobEmpty;
        internal bool HandlesClosed;
        internal bool QuotaPrivilegeRestored;
        internal bool ZeroFixtureProcesses;
        internal bool ZeroGameProcesses;
    }

    internal sealed class TimeoutCleanupFacts
    {
        internal bool ExactlyOneDescendantObserved;
        internal bool TimeoutBounded;
        internal bool WholeJobTerminationRequested;
        internal bool WholeJobTerminationSucceeded;
        internal bool ActiveProcessCountZero;
        internal bool JobEmpty;
        internal bool HandlesClosed;
        internal bool QuotaPrivilegeRestored;
        internal bool ZeroFixtureProcesses;
        internal bool ZeroGameProcesses;
    }

    internal sealed class LockedCleanupFacts
    {
        internal bool ProcessCreationCapabilityAbsent;
        internal bool ProcessCreationNotAttempted;
        internal bool FixtureExecutionNotAttempted;
        internal bool ZeroFixtureProcesses;
        internal bool ZeroGameProcesses;
        internal bool ZeroAttemptArtifacts;
        internal bool NoProcessOrTokenHandlesOpened;
    }

    internal sealed class RebindFacts
    {
        internal bool InputsStable;
        internal bool InstalledTreeStable;
        internal bool VirtualStoreStable;
        internal bool RegistryStable;
        internal bool ZeroFixtureProcesses;
        internal bool ZeroGameProcesses;
        internal bool PublicationNotAttempted;
    }

    internal sealed class AbortFacts
    {
        internal bool FailureRecorded;
        internal bool NoFurtherAuthorityAttempted;
        internal bool OriginalExecutionNotAttempted;
        internal bool UnexpectedPixelsDiscardedAndZeroed;
    }

    internal sealed class AbortCleanupFacts
    {
        internal bool PrivilegeStateRestoredIfChanged;
        internal bool ChildAndJobTerminatedIfCreated;
        internal bool JobEmptyIfCreated;
        internal bool HandlesClosed;
        internal bool GuardsStable;
        internal bool ZeroFixtureProcesses;
        internal bool ZeroGameProcesses;
    }

    internal static class ControllerPolicy
    {
        private static readonly object PermitKey = new object();

        internal sealed class Permit
        {
            private readonly AttemptStage stage;
            private readonly string scenario;
            private readonly AttemptState owner;
            private readonly int generation;
            private bool consumed;

            internal Permit(AttemptStage acceptedStage, string acceptedScenario,
                AttemptState acceptedOwner, int acceptedGeneration, object key)
            {
                if (!Object.ReferenceEquals(key, PermitKey)) throw new ArgumentException("key");
                stage = acceptedStage;
                scenario = acceptedScenario;
                owner = acceptedOwner;
                generation = acceptedGeneration;
            }

            internal AttemptStage Stage { get { return stage; } }
            internal string Scenario { get { return scenario; } }

            internal bool Consume(AttemptState state, int currentGeneration)
            {
                if (consumed || !Object.ReferenceEquals(owner, state) || generation != currentGeneration)
                    return false;
                consumed = true;
                return true;
            }

        }

        private static Permit Accept(AttemptState state, string scenario, AttemptStage stage, bool condition)
        {
            return state != null && state.Accepts(scenario, stage) && condition ?
                new Permit(stage, scenario, state, state.Generation, PermitKey) : null;
        }

        private static Permit AcceptAbort(AttemptState state, string scenario, bool condition)
        {
            return state != null && state.CanAbort(scenario) && condition ?
                new Permit(AttemptStage.Abort, scenario, state, state.Generation, PermitKey) : null;
        }

        private static bool ExactHash(string value)
        {
            if (value == null || value.Length != 64) return false;
            for (int index = 0; index < value.Length; index++)
                if (!((value[index] >= '0' && value[index] <= '9') ||
                    (value[index] >= 'a' && value[index] <= 'f'))) return false;
            return true;
        }

        internal static Permit Binding(AttemptState state, string scenario, BindingFacts facts)
        {
            bool controller = facts != null && facts.ObservedControllerByteCount > 0 &&
                facts.ObservedControllerByteCount == facts.ExpectedControllerByteCount &&
                ExactHash(facts.ObservedControllerSha256) && ExactHash(facts.ExpectedControllerSha256) &&
                String.Equals(facts.ObservedControllerSha256, facts.ExpectedControllerSha256, StringComparison.Ordinal);
            bool fixedInputs = facts != null && facts.ObservedFixtureByteCount == FixedControllerContract.FixtureByteCount &&
                String.Equals(facts.ObservedFixtureSha256, FixedControllerContract.FixtureSha256, StringComparison.Ordinal) &&
                facts.ObservedFixtureSourceByteCount == FixedControllerContract.FixtureSourceByteCount &&
                String.Equals(facts.ObservedFixtureSourceSha256, FixedControllerContract.FixtureSourceSha256, StringComparison.Ordinal) &&
                facts.ObservedFixtureProfileByteCount == FixedControllerContract.FixtureProfileByteCount &&
                String.Equals(facts.ObservedFixtureProfileSha256, FixedControllerContract.FixtureProfileSha256, StringComparison.Ordinal) &&
                facts.ObservedHostArtifactByteCount == FixedControllerContract.AcceptedHostArtifactByteCount &&
                String.Equals(facts.ObservedHostArtifactSha256, FixedControllerContract.AcceptedHostArtifactSha256, StringComparison.Ordinal);
            return Accept(state, scenario, AttemptStage.BindInputs, controller && fixedInputs &&
                facts.SameHeldParent && facts.SameVolume && facts.DistinctObjects && facts.SingleLinks &&
                facts.NoReparsePoints && facts.StableBeforeAfter && facts.FreshPrivateAttempt && facts.GuardsDistinct);
        }

        internal static Permit Preflight(AttemptState state, string scenario, PreflightFacts facts)
        {
            if (facts == null) return null;
            bool common = facts != null && facts.ZeroGameProcesses && facts.ZeroFixtureProcesses &&
                facts.ActiveConsoleSessionStable && facts.ControllerSessionIsActiveConsole &&
                facts.DesktopObservationStable && facts.ProcessCreationNotAttempted;
            bool locked = String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal);
            bool scenarioFacts = locked ?
                (!facts.DefaultInputDesktop || !facts.InputDesktopSwitchable) &&
                    facts.ProcessCreationCapabilityAbsent && facts.ZeroAttemptArtifacts :
                facts.DefaultInputDesktop && facts.InputDesktopSwitchable &&
                    !facts.ProcessCreationCapabilityAbsent && facts.ShellSessionIsActiveConsole &&
                    facts.CanonicalExplorerSelected;
            return Accept(state, scenario, AttemptStage.PreflightRefusal, common && scenarioFacts);
        }

        internal static Permit TokenRelationship(AttemptState state, string scenario, TokenRelationshipFacts facts)
        {
            return Accept(state, scenario, AttemptStage.ExplorerToken, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.ThreadTokenAbsent && facts.CallerPrimary && facts.CallerElevationFull &&
                facts.CallerElevated && facts.CallerHighIntegrity && facts.CallerAdministrator &&
                facts.CallerPrivilegeTupleExact && facts.ShellPrimary && facts.ShellElevationLimited &&
                facts.ShellNotElevated && facts.ShellMediumIntegrity && facts.ShellNotAdministrator &&
                facts.ShellPrivilegeTupleExact && facts.SameUser && facts.SameSession &&
                facts.SameAuthenticationId && facts.ShellHasRestrictions &&
                facts.CallerLinkedQuerySucceeded && facts.CallerLinkedHandleValid &&
                facts.CallerLinkedTokenIdEqualsShellTokenId &&
                facts.ShellLinkedQuerySucceeded && facts.ShellLinkedHandleValid &&
                facts.ShellLinkedTokenIdEqualsCallerTokenId && facts.CallerLinkedElevationLimited &&
                facts.ShellLinkedElevationFull && facts.TokenIdsStable && facts.ModifiedIdsStable &&
                facts.PolicyShapeStable && facts.LinkedHandleOwnershipExact &&
                facts.AssignPrimaryPrivilegeAbsent &&
                facts.IncreaseQuotaPrivilegePresent && facts.ProcessCreationNotAttempted &&
                facts.FixtureExecutionNotAttempted);
        }

        internal static Permit LaunchToken(AttemptState state, string scenario, LaunchTokenFacts facts)
        {
            return Accept(state, scenario, AttemptStage.PrimaryToken, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.DuplicatedExactlyOnce && facts.DuplicateCallSucceeded &&
                facts.SourceIsHeldProvenShellToken &&
                facts.DesiredAccessQueryDuplicateAssignPrimaryOnly && facts.NonInheritable &&
                facts.Primary && facts.SameUser && facts.SameSession && facts.SameAuthenticationId &&
                facts.MediumIntegrity && facts.ElevationLimited && facts.NotElevated &&
                facts.NotAdministrator && facts.HasRestrictions && facts.PrivilegeTupleExact &&
                facts.SourceTokenIdStable && facts.SourceModifiedIdStable &&
                facts.DuplicateTokenIdStable && facts.DuplicateModifiedIdStable &&
                facts.SourceAndDuplicateHandlesHeld &&
                facts.ProcessCreationNotAttempted);
        }

        internal static Permit Registry(AttemptState state, string scenario, RegistryFacts facts)
        {
            return Accept(state, scenario, AttemptStage.RegistryDenial, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                String.Equals(facts.TargetId, FixedControllerContract.RegistryTargetId, StringComparison.Ordinal) &&
                facts.RequestedAccess == FixedControllerContract.RegistryAllAccess &&
                facts.Wow64ViewFlags == 0 && facts.ExactResult == 5 &&
                facts.EffectiveTokenIsHeldLaunchSource && facts.ImpersonationActiveOnlyForRequest &&
                facts.ImpersonationRestored && facts.ControllerTokenRestoredExact &&
                facts.LastWriteObservedBeforeAfter && facts.LastWriteStable);
        }

        internal static Permit Guards(AttemptState state, string scenario, GuardFacts facts)
        {
            return Accept(state, scenario, AttemptStage.GuardBefore, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.InstalledTreeSummaryComplete && facts.VirtualStoreSummaryComplete &&
                facts.RegistrySummaryComplete && facts.GuardsDistinctFromAttempt &&
                facts.NoWritableGuardHandles);
        }

        internal static Permit Environment(AttemptState state, string scenario, EnvironmentFacts facts)
        {
            if (facts == null || facts.Names == null ||
                facts.Names.Length != FixedControllerContract.EnvironmentNameCount) return null;
            for (int index = 0; index < FixedControllerContract.EnvironmentNameCount; index++)
                if (!String.Equals(facts.Names[index], FixedControllerContract.EnvironmentNameAt(index),
                    StringComparison.Ordinal)) return null;
            return Accept(state, scenario, AttemptStage.Environment,
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.CaseSensitiveUnique && facts.NoAmbientInheritance &&
                facts.ValuesContainNoControlCharacters && facts.SystemRootEqualsWindowsDirectory &&
                facts.SystemPathsCanonicalAbsoluteInBox && facts.TemporaryValuesEqual &&
                facts.TemporaryContainedByAttempt && facts.TemporaryIsExactFixedAttemptChild &&
                facts.NoDriveCurrentDirectoryEntries &&
                facts.WorkingDirectoryHashExact && facts.NonceIsNonzeroUInt32 &&
                facts.SortedDoubleNullUnicodeBlock);
        }

        internal static Permit ApproveCreate(AttemptState state, string scenario, CreateApprovalFacts facts)
        {
            return Accept(state, scenario, AttemptStage.CreateApproved, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.FixedSiblingTarget && facts.LaunchTokenIsPolicyAccepted &&
                facts.IncreaseQuotaPresentBefore && facts.AdjustCalledExactlyOnce &&
                facts.AdjustReturnedTrue && facts.AdjustLastErrorSuccess &&
                facts.IncreaseQuotaEnabledAfter && facts.AssignPrimaryPrivilegeStillAbsent &&
                facts.NoOtherPrivilegeChanged && facts.ThreadTokenAbsent &&
                facts.RelationshipRevalidatedAfterAdjustment &&
                facts.LaunchTokenRevalidatedAfterAdjustment && facts.NoPriorCreationAttempt &&
                facts.CreateProcessAsUserOnly && facts.NoFallbackAttempted && facts.InheritHandlesFalse &&
                facts.DesktopWinsta0DefaultExact && facts.WorkingDirectoryExact &&
                facts.OriginalExecutionNotAttempted);
        }

        internal static Permit RecordSuspendedChild(AttemptState state, string scenario, SuspendedChildFacts facts)
        {
            return Accept(state, scenario, AttemptStage.CreateSuspended, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.CreateCalledExactlyOnce && facts.CreateSucceeded && facts.ChildCreatedSuspended &&
                facts.ChildIdentityReverified && facts.PrimaryThreadSuspendCountOne &&
                facts.NoChildCodeObserved);
        }

        internal static Permit JobBeforeResume(AttemptState state, string scenario, JobFacts facts)
        {
            int activeLimit = String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal) ? 2 : 1;
            long jobMemory = String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal) ?
                FixedControllerContract.TimeoutJobMemoryLimitBytes : FixedControllerContract.UiJobMemoryLimitBytes;
            return Accept(state, scenario, AttemptStage.JobAssign, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.CreatedWhileChildSuspended && facts.KillOnClose && facts.BreakawayForbidden &&
                facts.ActiveProcessLimit == activeLimit &&
                facts.ProcessMemoryLimitBytes == FixedControllerContract.ProcessMemoryLimitBytes &&
                facts.JobMemoryLimitBytes == jobMemory && facts.LimitsQueried &&
                facts.ChildStillSuspended && facts.AssignedBeforeResume && facts.MembershipQueried &&
                facts.ProcessNotResumed);
        }

        internal static Permit PreResume(AttemptState state, string scenario, PreResumeFacts facts)
        {
            return Accept(state, scenario, AttemptStage.PreResumeApproved, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.BindingStillStable && facts.GuardsStillStable &&
                facts.RelationshipRevalidated && facts.LaunchTokenRevalidated &&
                facts.RegistryObservationStillBound && facts.EnvironmentBlockStillBound &&
                facts.QuotaStateStillExact && facts.ChildExactAndSuspended &&
                facts.JobMembershipExact && facts.JobLimitsExact && facts.ThreadTokenAbsent &&
                facts.DefaultDesktopRechecked && facts.DesktopStillSwitchable &&
                facts.ZeroGameProcesses && facts.ResumeCallsSoFar == 0);
        }

        internal static Permit Resume(AttemptState state, string scenario, ResumeFacts facts)
        {
            return Accept(state, scenario, AttemptStage.Resume, facts != null &&
                !String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.ResumeCallCount == 1 && facts.PreviousSuspendCount == 1 &&
                facts.ThreadObservedRunning && facts.NoSecondResume);
        }

        internal static Permit Window(AttemptState state, string scenario, WindowFacts facts)
        {
            return Accept(state, scenario, AttemptStage.WindowReady, facts != null &&
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) &&
                facts.UniqueVisibleUnownedTopLevel && facts.ExactChildProcess && facts.ProtocolExact &&
                facts.ReadyStateExact && facts.ClientGeometryExact && facts.ActiveSessionExact &&
                facts.DefaultDesktopExact && facts.DisplayExact && facts.DpiExact && facts.ForegroundExact);
        }

        private static bool CaptureCommon(CaptureFacts facts, int state, int ordinal)
        {
            return facts != null && facts.Width == 320 && facts.Height == 240 && facts.Ordinal == ordinal &&
                facts.ObservedStateId == state && facts.ClientRectangleOnly && facts.DesktopDcBitBltOnly &&
                facts.EveryPixelExpected && facts.CanonicalBmpExact &&
                (ordinal == 1 ? !facts.MatchesFirstCapture : facts.MatchesFirstCapture) &&
                facts.UnexpectedPixelsDiscardedAndZeroed;
        }

        internal static Permit ReadyCaptureOne(AttemptState state, string scenario, CaptureFacts facts)
        {
            return Accept(state, scenario, AttemptStage.ReadyCaptureOne,
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) && CaptureCommon(facts, 1, 1));
        }

        internal static Permit ReadyCaptureTwo(AttemptState state, string scenario, CaptureFacts facts)
        {
            return Accept(state, scenario, AttemptStage.ReadyCaptureTwo,
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) && CaptureCommon(facts, 1, 2));
        }

        internal static Permit InputGuards(AttemptState state, string scenario, InputGuardFacts facts)
        {
            return Accept(state, scenario, AttemptStage.InputGuards, facts != null &&
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) &&
                facts.AllRelevantInputUp && facts.ForegroundRechecked &&
                facts.DesktopRechecked && facts.FixedClientPoint);
        }

        internal static Permit SendInput(AttemptState state, string scenario, SendInputFacts facts)
        {
            return Accept(state, scenario, AttemptStage.SendInput, facts != null &&
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) &&
                facts.ExactNonce && facts.UsedSendInputOnly && facts.InsertedEventCount == 3 &&
                facts.CompleteStateExact);
        }

        internal static Permit CompleteCaptureOne(AttemptState state, string scenario, CaptureFacts facts)
        {
            return Accept(state, scenario, AttemptStage.CompleteCaptureOne,
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) && CaptureCommon(facts, 2, 1));
        }

        internal static Permit CompleteCaptureTwo(AttemptState state, string scenario, CaptureFacts facts)
        {
            return Accept(state, scenario, AttemptStage.CompleteCaptureTwo,
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) && CaptureCommon(facts, 2, 2));
        }

        internal static Permit CleanupUi(AttemptState state, string scenario, UiCleanupFacts facts)
        {
            return Accept(state, scenario, AttemptStage.Cleanup, state != null && !state.IsAborting && facts != null &&
                String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) &&
                facts.OrderlyCloseRequested && facts.OrderlyCloseSucceeded && facts.GraceBounded &&
                facts.JobEmpty && facts.HandlesClosed && facts.QuotaPrivilegeRestored &&
                facts.ZeroFixtureProcesses && facts.ZeroGameProcesses);
        }

        internal static Permit CleanupTimeout(AttemptState state, string scenario, TimeoutCleanupFacts facts)
        {
            return Accept(state, scenario, AttemptStage.Cleanup, state != null && !state.IsAborting && facts != null &&
                String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal) &&
                facts.ExactlyOneDescendantObserved && facts.TimeoutBounded &&
                facts.WholeJobTerminationRequested && facts.WholeJobTerminationSucceeded &&
                facts.ActiveProcessCountZero && facts.JobEmpty && facts.HandlesClosed &&
                facts.QuotaPrivilegeRestored && facts.ZeroFixtureProcesses && facts.ZeroGameProcesses);
        }

        internal static Permit CleanupLocked(AttemptState state, string scenario, LockedCleanupFacts facts)
        {
            return Accept(state, scenario, AttemptStage.Cleanup, state != null && !state.IsAborting && facts != null &&
                String.Equals(scenario, "locked-refusal-v1", StringComparison.Ordinal) &&
                facts.ProcessCreationCapabilityAbsent && facts.ProcessCreationNotAttempted &&
                facts.FixtureExecutionNotAttempted && facts.ZeroFixtureProcesses &&
                facts.ZeroGameProcesses && facts.ZeroAttemptArtifacts &&
                facts.NoProcessOrTokenHandlesOpened);
        }

        internal static Permit Abort(AttemptState state, string scenario, AbortFacts facts)
        {
            return AcceptAbort(state, scenario, facts != null && facts.FailureRecorded &&
                facts.NoFurtherAuthorityAttempted && facts.OriginalExecutionNotAttempted &&
                facts.UnexpectedPixelsDiscardedAndZeroed);
        }

        internal static Permit CleanupAbort(AttemptState state, string scenario, AbortCleanupFacts facts)
        {
            return Accept(state, scenario, AttemptStage.Cleanup, state != null && state.IsAborting && facts != null &&
                facts.PrivilegeStateRestoredIfChanged && facts.ChildAndJobTerminatedIfCreated &&
                facts.JobEmptyIfCreated && facts.HandlesClosed && facts.GuardsStable &&
                facts.ZeroFixtureProcesses && facts.ZeroGameProcesses);
        }

        internal static Permit Rebind(AttemptState state, string scenario, RebindFacts facts)
        {
            return Accept(state, scenario, AttemptStage.RebindPublish, facts != null &&
                facts.InputsStable && facts.InstalledTreeStable && facts.VirtualStoreStable &&
                facts.RegistryStable && facts.ZeroFixtureProcesses && facts.ZeroGameProcesses &&
                facts.PublicationNotAttempted);
        }
    }

    internal sealed class AttemptState
    {
        private readonly string scenario;
        private readonly AttemptStage[] route;
        private int nextIndex;
        private int generation;
        private bool terminal;
        private bool rejected;
        private bool aborting;
        private int abortPhase;

        private AttemptState(string scenarioId)
        {
            if (!FixedControllerContract.IsScenario(scenarioId))
                throw new ArgumentException("scenario");
            scenario = scenarioId;
            if (String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal))
                route = new AttemptStage[]
                {
                    AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
                    AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
                    AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
                    AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
                    AttemptStage.WindowReady, AttemptStage.ReadyCaptureOne, AttemptStage.ReadyCaptureTwo,
                    AttemptStage.InputGuards, AttemptStage.SendInput, AttemptStage.CompleteCaptureOne,
                    AttemptStage.CompleteCaptureTwo,
                    AttemptStage.Cleanup, AttemptStage.RebindPublish
                };
            else if (String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal))
                route = new AttemptStage[]
                {
                    AttemptStage.BindInputs, AttemptStage.PreflightRefusal, AttemptStage.ExplorerToken,
                    AttemptStage.PrimaryToken, AttemptStage.RegistryDenial, AttemptStage.GuardBefore,
                    AttemptStage.Environment, AttemptStage.CreateApproved, AttemptStage.CreateSuspended,
                    AttemptStage.JobAssign, AttemptStage.PreResumeApproved, AttemptStage.Resume,
                    AttemptStage.Cleanup, AttemptStage.RebindPublish
                };
            else
                route = new AttemptStage[]
                {
                    AttemptStage.BindInputs, AttemptStage.PreflightRefusal,
                    AttemptStage.Cleanup, AttemptStage.RebindPublish
                };
        }

        internal static AttemptState Start(string scenarioId)
        {
            return new AttemptState(scenarioId);
        }

        internal bool Accepts(string scenarioId, AttemptStage stage)
        {
            if (aborting)
                return !terminal && String.Equals(scenario, scenarioId, StringComparison.Ordinal) &&
                    ((abortPhase == 0 && stage == AttemptStage.Cleanup) ||
                    (abortPhase == 1 && stage == AttemptStage.RebindPublish));
            return !terminal && !rejected && nextIndex < route.Length &&
                String.Equals(scenario, scenarioId, StringComparison.Ordinal) &&
                route[nextIndex] == stage;
        }

        internal int Generation { get { return generation; } }
        internal bool IsAborting { get { return aborting; } }

        internal bool CanAbort(string scenarioId)
        {
            return !terminal && !aborting && nextIndex < route.Length &&
                String.Equals(scenario, scenarioId, StringComparison.Ordinal);
        }

        internal bool BeginAbort(ControllerPolicy.Permit permit)
        {
            if (permit == null || !CanAbort(scenario) || permit.Stage != AttemptStage.Abort ||
                !permit.Consume(this, generation))
            {
                rejected = true;
                generation++;
                return false;
            }
            aborting = true;
            abortPhase = 0;
            rejected = false;
            generation++;
            return true;
        }

        internal bool Advance(ControllerPolicy.Permit permit)
        {
            if (terminal || (!aborting && rejected) || permit == null || (!aborting && nextIndex >= route.Length) ||
                !String.Equals(permit.Scenario, scenario, StringComparison.Ordinal) ||
                (aborting ? !Accepts(scenario, permit.Stage) : permit.Stage != route[nextIndex]) ||
                !permit.Consume(this, generation))
            {
                rejected = true;
                generation++;
                return false;
            }
            if (aborting) abortPhase++;
            else nextIndex++;
            rejected = false;
            generation++;
            return true;
        }

        internal bool Complete(AttemptTerminal value)
        {
            AttemptTerminal expected = aborting ? AttemptTerminal.Ineligible :
                (String.Equals(scenario, "ui-success-v1", StringComparison.Ordinal) ?
                AttemptTerminal.UiComplete :
                (String.Equals(scenario, "tree-timeout-v1", StringComparison.Ordinal) ?
                    AttemptTerminal.ExpectedTimeout : AttemptTerminal.LockedRefusal));
            bool routeComplete = aborting ? abortPhase == 2 : nextIndex == route.Length;
            if (terminal || rejected || !routeComplete || value != expected)
            {
                rejected = true;
                return false;
            }
            terminal = true;
            return true;
        }

        internal bool IsTerminal { get { return terminal; } }
        internal bool IsRejected { get { return rejected; } }
        internal int AcceptedStageCount { get { return nextIndex; } }
    }
}
