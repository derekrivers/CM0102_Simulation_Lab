using System;

namespace Cm0102.SyntheticLauncherController
{
    internal enum RuntimeImageRole
    {
        Absent = 0,
        Supervisor = 1,
        Controller = 2,
        LockedPreflight = 3,
        UiFixture = 4,
        TimeoutRoot = 5,
        TimeoutChild = 6
    }

    internal enum RuntimeImageBindingState
    {
        Unbound = 1,
        BoundNotRun = 2
    }

    internal enum RuntimeBuildBinding
    {
        BuildUnpinned = 1,
        ImagesPinned = 2
    }

    internal enum DeclaredFixtureStatus
    {
        NotRun = 1,
        ExpectedTimeoutContained = 2,
        Succeeded = 3
    }

    internal static class FixedRuntimeBindingContract
    {
        internal const string ProfileId = "cm0102-synthetic-launcher-controller-runtime-v1";
        internal const long RuntimeProfileByteCount = 5510;
        internal const string RuntimeProfileSha256 =
            "0f4e98d7fe1c273e3c0b7cf342bae84bcc99a4a5ef16cf087a4fe99d3bb396d1";
        internal const long UiFixtureByteCount = 14336;
        internal const string UiFixtureSha256 =
            "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6";
        internal const long ProcessMemoryLimitBytes = 268435456;
        internal const string PublicConfigurationName =
            "SyntheticLauncherController.public.v1.json";
        internal const string PrivateConfigurationName =
            "SyntheticLauncherController.private.v1.json";
        internal const string ReportName = "SyntheticLauncherReport.v1.json";

        internal static string NameFor(RuntimeImageRole role)
        {
            switch (role)
            {
                case RuntimeImageRole.Supervisor: return "SyntheticLauncherSupervisor.exe";
                case RuntimeImageRole.Controller: return "SyntheticLauncherController.exe";
                case RuntimeImageRole.LockedPreflight: return "SyntheticLauncherLockedPreflight.exe";
                case RuntimeImageRole.UiFixture: return "SyntheticLauncherFixture.exe";
                case RuntimeImageRole.TimeoutRoot: return "SyntheticLauncherTimeoutFixture.exe";
                case RuntimeImageRole.TimeoutChild: return "SyntheticLauncherTimeoutChild.exe";
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

    internal sealed class RuntimeArtifactIdentity
    {
        internal readonly long ByteCount;
        internal readonly string Sha256;

        internal RuntimeArtifactIdentity(long byteCount, string sha256)
        {
            ByteCount = byteCount;
            Sha256 = sha256;
        }
    }

    internal sealed class RuntimeContractFacts
    {
        internal readonly string ProfileId;
        internal readonly RuntimeArtifactIdentity RuntimeProfile;
        internal readonly RuntimeBuildBinding BuildBinding;
        internal readonly bool PublicBuildManifestBindingUnbound;
        internal readonly RuntimeArtifactIdentity PublicBuildManifestBindingIdentity;
        internal readonly bool LiveExecutionNotRun;
        internal readonly bool ProcessCreationUnreachable;
        internal readonly bool QualificationIneligible;
        internal readonly bool OriginalExecutionNotRun;
        internal readonly bool OriginalBehaviorUnqualified;
        internal readonly bool NoImageExecutionObserved;
        internal readonly bool NoObjectObservationAttempted;
        internal readonly bool NoLiveJobObservationAttempted;

        internal RuntimeContractFacts(string profileId, RuntimeArtifactIdentity runtimeProfile,
            RuntimeBuildBinding buildBinding, bool publicBuildManifestBindingUnbound,
            RuntimeArtifactIdentity publicBuildManifestBindingIdentity, bool liveExecutionNotRun,
            bool processCreationUnreachable, bool qualificationIneligible,
            bool originalExecutionNotRun, bool originalBehaviorUnqualified,
            bool noImageExecutionObserved, bool noObjectObservationAttempted,
            bool noLiveJobObservationAttempted)
        {
            ProfileId = profileId;
            RuntimeProfile = runtimeProfile;
            BuildBinding = buildBinding;
            PublicBuildManifestBindingUnbound = publicBuildManifestBindingUnbound;
            PublicBuildManifestBindingIdentity = publicBuildManifestBindingIdentity;
            LiveExecutionNotRun = liveExecutionNotRun;
            ProcessCreationUnreachable = processCreationUnreachable;
            QualificationIneligible = qualificationIneligible;
            OriginalExecutionNotRun = originalExecutionNotRun;
            OriginalBehaviorUnqualified = originalBehaviorUnqualified;
            NoImageExecutionObserved = noImageExecutionObserved;
            NoObjectObservationAttempted = noObjectObservationAttempted;
            NoLiveJobObservationAttempted = noLiveJobObservationAttempted;
        }
    }

    internal sealed class RuntimeImageDeclarationFacts
    {
        internal readonly RuntimeImageRole Role;
        internal readonly string FixedName;
        internal readonly RuntimeImageBindingState DeclaredBindingState;
        internal readonly RuntimeArtifactIdentity DeclaredIdentity;

        internal RuntimeImageDeclarationFacts(RuntimeImageRole role, string fixedName,
            RuntimeImageBindingState bindingState, RuntimeArtifactIdentity identity)
        {
            Role = role;
            FixedName = fixedName;
            DeclaredBindingState = bindingState;
            DeclaredIdentity = identity;
        }
    }

    internal sealed class RuntimeObjectBindingRequirementFacts
    {
        internal readonly string PublicConfigurationName;
        internal readonly string PrivateConfigurationName;
        internal readonly string ReportName;
        internal readonly bool RequireHeldExactParent;
        internal readonly bool RequireCanonicalFinalPaths;
        internal readonly bool RequireObjectIds;
        internal readonly bool RequireSameVolume;
        internal readonly bool RequireRegularFiles;
        internal readonly bool RequireAlternateMountRejection;
        internal readonly bool RequirePairwiseDistinctObjects;
        internal readonly bool RequireSingleLinkFiles;
        internal readonly bool RequireNoReparsePoints;
        internal readonly bool RequireNoAlternateDataStreams;
        internal readonly bool RequireStableBeforeAfter;
        internal readonly bool RequireRuntimeCopiesNotHardlinks;
        internal readonly bool RequirePrivateConfigurationWithoutExecutablePath;
        internal readonly bool RequireRebindBefore;
        internal readonly bool RequireRebindAfter;

        internal RuntimeObjectBindingRequirementFacts(string publicConfigurationName,
            string privateConfigurationName, string reportName, bool requireHeldExactParent,
            bool requireCanonicalFinalPaths, bool requireObjectIds, bool requireSameVolume,
            bool requireRegularFiles, bool requireAlternateMountRejection,
            bool requirePairwiseDistinctObjects, bool requireSingleLinkFiles,
            bool requireNoReparsePoints, bool requireNoAlternateDataStreams,
            bool requireStableBeforeAfter, bool requireRuntimeCopiesNotHardlinks,
            bool requirePrivateConfigurationWithoutExecutablePath,
            bool requireRebindBefore, bool requireRebindAfter)
        {
            PublicConfigurationName = publicConfigurationName;
            PrivateConfigurationName = privateConfigurationName;
            ReportName = reportName;
            RequireHeldExactParent = requireHeldExactParent;
            RequireCanonicalFinalPaths = requireCanonicalFinalPaths;
            RequireObjectIds = requireObjectIds;
            RequireSameVolume = requireSameVolume;
            RequireRegularFiles = requireRegularFiles;
            RequireAlternateMountRejection = requireAlternateMountRejection;
            RequirePairwiseDistinctObjects = requirePairwiseDistinctObjects;
            RequireSingleLinkFiles = requireSingleLinkFiles;
            RequireNoReparsePoints = requireNoReparsePoints;
            RequireNoAlternateDataStreams = requireNoAlternateDataStreams;
            RequireStableBeforeAfter = requireStableBeforeAfter;
            RequireRuntimeCopiesNotHardlinks = requireRuntimeCopiesNotHardlinks;
            RequirePrivateConfigurationWithoutExecutablePath =
                requirePrivateConfigurationWithoutExecutablePath;
            RequireRebindBefore = requireRebindBefore;
            RequireRebindAfter = requireRebindAfter;
        }
    }

    internal sealed class RuntimeRouteDeclarationFacts
    {
        internal readonly string Scenario;
        internal readonly RuntimeImageRole Worker;
        internal readonly RuntimeImageRole PrimaryTarget;
        internal readonly RuntimeImageRole Descendant;
        internal readonly bool WorkerProcessCreationCapabilityDeclared;
        internal readonly DeclaredFixtureStatus ExpectedFixtureStatus;

        internal RuntimeRouteDeclarationFacts(string scenario, RuntimeImageRole worker,
            RuntimeImageRole primaryTarget, RuntimeImageRole descendant,
            bool workerProcessCreationCapabilityDeclared,
            DeclaredFixtureStatus expectedFixtureStatus)
        {
            Scenario = scenario;
            Worker = worker;
            PrimaryTarget = primaryTarget;
            Descendant = descendant;
            WorkerProcessCreationCapabilityDeclared = workerProcessCreationCapabilityDeclared;
            ExpectedFixtureStatus = expectedFixtureStatus;
        }
    }

    internal sealed class RuntimeOuterJobDeclarationFacts
    {
        internal readonly string Scenario;
        internal readonly int ActiveProcessLimit;
        internal readonly long ProcessMemoryLimitBytes;
        internal readonly long JobMemoryLimitBytes;
        internal readonly bool RequireKillOnClose;
        internal readonly bool RequireBreakawayForbidden;
        internal readonly bool RequireNestedInnerJob;
        internal readonly bool RequireNonInheritableHandle;
        internal readonly bool DeclareSupervisorNotMember;
        internal readonly bool RequireUnnamedJob;
        internal readonly bool RequireWorkerCreatedSuspended;
        internal readonly bool RequireWorkerAssignedBeforeResume;
        internal readonly bool RequireWorkerMembershipQuery;
        internal readonly int RequiredWorkerResumeCallCount;

        internal RuntimeOuterJobDeclarationFacts(string scenario, int activeProcessLimit,
            long processMemoryLimitBytes, long jobMemoryLimitBytes, bool requireKillOnClose,
            bool requireBreakawayForbidden, bool requireNestedInnerJob,
            bool requireNonInheritableHandle, bool declareSupervisorNotMember,
            bool requireUnnamedJob, bool requireWorkerCreatedSuspended,
            bool requireWorkerAssignedBeforeResume, bool requireWorkerMembershipQuery,
            int requiredWorkerResumeCallCount)
        {
            Scenario = scenario;
            ActiveProcessLimit = activeProcessLimit;
            ProcessMemoryLimitBytes = processMemoryLimitBytes;
            JobMemoryLimitBytes = jobMemoryLimitBytes;
            RequireKillOnClose = requireKillOnClose;
            RequireBreakawayForbidden = requireBreakawayForbidden;
            RequireNestedInnerJob = requireNestedInnerJob;
            RequireNonInheritableHandle = requireNonInheritableHandle;
            DeclareSupervisorNotMember = declareSupervisorNotMember;
            RequireUnnamedJob = requireUnnamedJob;
            RequireWorkerCreatedSuspended = requireWorkerCreatedSuspended;
            RequireWorkerAssignedBeforeResume = requireWorkerAssignedBeforeResume;
            RequireWorkerMembershipQuery = requireWorkerMembershipQuery;
            RequiredWorkerResumeCallCount = requiredWorkerResumeCallCount;
        }
    }

    internal sealed class RuntimeBindingFacts
    {
        internal readonly RuntimeContractFacts Contract;
        internal readonly RuntimeImageDeclarationFacts Supervisor;
        internal readonly RuntimeImageDeclarationFacts Controller;
        internal readonly RuntimeImageDeclarationFacts LockedPreflight;
        internal readonly RuntimeImageDeclarationFacts UiFixture;
        internal readonly RuntimeImageDeclarationFacts TimeoutRoot;
        internal readonly RuntimeImageDeclarationFacts TimeoutChild;
        internal readonly RuntimeObjectBindingRequirementFacts ObjectBindingRequirements;
        internal readonly RuntimeRouteDeclarationFacts UiRoute;
        internal readonly RuntimeRouteDeclarationFacts TimeoutRoute;
        internal readonly RuntimeRouteDeclarationFacts LockedRoute;
        internal readonly RuntimeOuterJobDeclarationFacts UiOuterJob;
        internal readonly RuntimeOuterJobDeclarationFacts TimeoutOuterJob;
        internal readonly RuntimeOuterJobDeclarationFacts LockedOuterJob;

        internal RuntimeBindingFacts(RuntimeContractFacts contract,
            RuntimeImageDeclarationFacts supervisor,
            RuntimeImageDeclarationFacts controller,
            RuntimeImageDeclarationFacts lockedPreflight,
            RuntimeImageDeclarationFacts uiFixture,
            RuntimeImageDeclarationFacts timeoutRoot,
            RuntimeImageDeclarationFacts timeoutChild,
            RuntimeObjectBindingRequirementFacts objectBindingRequirements,
            RuntimeRouteDeclarationFacts uiRoute,
            RuntimeRouteDeclarationFacts timeoutRoute,
            RuntimeRouteDeclarationFacts lockedRoute,
            RuntimeOuterJobDeclarationFacts uiOuterJob,
            RuntimeOuterJobDeclarationFacts timeoutOuterJob,
            RuntimeOuterJobDeclarationFacts lockedOuterJob)
        {
            Contract = contract;
            Supervisor = supervisor;
            Controller = controller;
            LockedPreflight = lockedPreflight;
            UiFixture = uiFixture;
            TimeoutRoot = timeoutRoot;
            TimeoutChild = timeoutChild;
            ObjectBindingRequirements = objectBindingRequirements;
            UiRoute = uiRoute;
            TimeoutRoute = timeoutRoute;
            LockedRoute = lockedRoute;
            UiOuterJob = uiOuterJob;
            TimeoutOuterJob = timeoutOuterJob;
            LockedOuterJob = lockedOuterJob;
        }
    }

    internal sealed class RuntimeBindingState
    {
        private readonly object sync = new object();
        private readonly string scenario;
        private int generation;
        private bool terminal;
        private bool ineligible;
        private bool unreachable;
        private bool rejected;

        private RuntimeBindingState(string scenarioId)
        {
            if (!FixedRuntimeBindingContract.IsScenario(scenarioId))
                throw new ArgumentException("scenario");
            scenario = scenarioId;
        }

        internal static RuntimeBindingState Start(string scenarioId)
        {
            return new RuntimeBindingState(scenarioId);
        }

        internal bool TryGetRefusalBinding(out string boundScenario, out int boundGeneration)
        {
            lock (sync)
            {
                boundScenario = scenario;
                boundGeneration = generation;
                return !terminal && !rejected;
            }
        }

        internal bool IsTerminal { get { lock (sync) { return terminal; } } }
        internal bool IsIneligible { get { lock (sync) { return ineligible; } } }
        internal bool IsUnreachable { get { lock (sync) { return unreachable; } } }
        internal bool IsRejected { get { lock (sync) { return rejected; } } }

        internal bool AcceptRefusal(RuntimeBindingPolicy.BuildUnpinnedRefusal refusal)
        {
            lock (sync)
            {
                if (terminal || rejected) return false;
                if (refusal == null || !refusal.Consume(this, scenario, generation,
                        FixedRuntimeBindingContract.ProfileId,
                        FixedRuntimeBindingContract.RuntimeProfileByteCount,
                        FixedRuntimeBindingContract.RuntimeProfileSha256))
                {
                    rejected = true;
                    generation++;
                    return false;
                }
                terminal = true;
                ineligible = true;
                unreachable = true;
                generation++;
                return true;
            }
        }
    }

    internal static class RuntimeBindingPolicy
    {
        private static readonly object RefusalKey = new object();

        internal sealed class BuildUnpinnedRefusal
        {
            private readonly RuntimeBindingState owner;
            private readonly object sync = new object();
            private readonly string scenario;
            private readonly int generation;
            private readonly string profileId;
            private readonly long profileByteCount;
            private readonly string profileSha256;
            private bool consumed;

            internal BuildUnpinnedRefusal(RuntimeBindingState acceptedOwner,
                string acceptedScenario, int acceptedGeneration, string acceptedProfileId,
                long acceptedProfileByteCount, string acceptedProfileSha256, object key)
            {
                if (!Object.ReferenceEquals(key, RefusalKey)) throw new ArgumentException("key");
                owner = acceptedOwner;
                scenario = acceptedScenario;
                generation = acceptedGeneration;
                profileId = acceptedProfileId;
                profileByteCount = acceptedProfileByteCount;
                profileSha256 = acceptedProfileSha256;
            }

            internal bool Consume(RuntimeBindingState candidateOwner, string candidateScenario,
                int candidateGeneration, string candidateProfileId,
                long candidateProfileByteCount, string candidateProfileSha256)
            {
                lock (sync)
                {
                    if (consumed || !Object.ReferenceEquals(owner, candidateOwner) ||
                        !String.Equals(scenario, candidateScenario, StringComparison.Ordinal) ||
                        generation != candidateGeneration ||
                        !String.Equals(profileId, candidateProfileId, StringComparison.Ordinal) ||
                        profileByteCount != candidateProfileByteCount ||
                        !String.Equals(profileSha256, candidateProfileSha256,
                            StringComparison.Ordinal)) return false;
                    consumed = true;
                    return true;
                }
            }
        }

        private static bool ExactHash(string value)
        {
            if (value == null || value.Length != 64) return false;
            for (int index = 0; index < value.Length; index++)
                if (!((value[index] >= '0' && value[index] <= '9') ||
                    (value[index] >= 'a' && value[index] <= 'f'))) return false;
            return value != new String('0', 64);
        }

        private static bool ExactIdentity(RuntimeArtifactIdentity observed,
            long expectedByteCount, string expectedSha256)
        {
            return observed != null && observed.ByteCount == expectedByteCount &&
                ExactHash(observed.Sha256) &&
                String.Equals(observed.Sha256, expectedSha256, StringComparison.Ordinal);
        }

        private static bool ExactContract(RuntimeContractFacts facts)
        {
            return facts != null && String.Equals(facts.ProfileId,
                FixedRuntimeBindingContract.ProfileId, StringComparison.Ordinal) &&
                ExactIdentity(facts.RuntimeProfile,
                    FixedRuntimeBindingContract.RuntimeProfileByteCount,
                    FixedRuntimeBindingContract.RuntimeProfileSha256) &&
                facts.BuildBinding == RuntimeBuildBinding.BuildUnpinned &&
                facts.PublicBuildManifestBindingUnbound &&
                facts.PublicBuildManifestBindingIdentity == null &&
                facts.LiveExecutionNotRun && facts.ProcessCreationUnreachable &&
                facts.QualificationIneligible && facts.OriginalExecutionNotRun &&
                facts.OriginalBehaviorUnqualified && facts.NoImageExecutionObserved &&
                facts.NoObjectObservationAttempted && facts.NoLiveJobObservationAttempted;
        }

        private static bool ExactUnboundImage(RuntimeImageDeclarationFacts facts,
            RuntimeImageRole role)
        {
            return facts != null && facts.Role == role &&
                String.Equals(facts.FixedName, FixedRuntimeBindingContract.NameFor(role),
                    StringComparison.Ordinal) &&
                facts.DeclaredBindingState == RuntimeImageBindingState.Unbound &&
                facts.DeclaredIdentity == null;
        }

        private static bool ExactUiFixture(RuntimeImageDeclarationFacts facts)
        {
            return facts != null && facts.Role == RuntimeImageRole.UiFixture &&
                String.Equals(facts.FixedName,
                    FixedRuntimeBindingContract.NameFor(RuntimeImageRole.UiFixture),
                    StringComparison.Ordinal) &&
                facts.DeclaredBindingState == RuntimeImageBindingState.BoundNotRun &&
                ExactIdentity(facts.DeclaredIdentity,
                    FixedRuntimeBindingContract.UiFixtureByteCount,
                    FixedRuntimeBindingContract.UiFixtureSha256);
        }

        private static bool ExactObjectBindingRequirements(
            RuntimeObjectBindingRequirementFacts facts)
        {
            return facts != null && String.Equals(facts.PublicConfigurationName,
                FixedRuntimeBindingContract.PublicConfigurationName,
                StringComparison.Ordinal) && String.Equals(facts.PrivateConfigurationName,
                FixedRuntimeBindingContract.PrivateConfigurationName,
                StringComparison.Ordinal) && String.Equals(facts.ReportName,
                FixedRuntimeBindingContract.ReportName, StringComparison.Ordinal) &&
                facts.RequireHeldExactParent && facts.RequireCanonicalFinalPaths &&
                facts.RequireObjectIds && facts.RequireSameVolume && facts.RequireRegularFiles &&
                facts.RequireAlternateMountRejection &&
                facts.RequirePairwiseDistinctObjects && facts.RequireSingleLinkFiles &&
                facts.RequireNoReparsePoints && facts.RequireNoAlternateDataStreams &&
                facts.RequireStableBeforeAfter && facts.RequireRuntimeCopiesNotHardlinks &&
                facts.RequirePrivateConfigurationWithoutExecutablePath &&
                facts.RequireRebindBefore && facts.RequireRebindAfter;
        }

        private static bool ExactRoute(RuntimeRouteDeclarationFacts facts, string scenario,
            RuntimeImageRole worker, RuntimeImageRole target, RuntimeImageRole descendant,
            bool processCreation, DeclaredFixtureStatus fixtureStatus)
        {
            return facts != null && String.Equals(facts.Scenario, scenario,
                StringComparison.Ordinal) && facts.Worker == worker &&
                facts.PrimaryTarget == target && facts.Descendant == descendant &&
                facts.WorkerProcessCreationCapabilityDeclared == processCreation &&
                facts.ExpectedFixtureStatus == fixtureStatus;
        }

        private static bool ExactOuterJob(RuntimeOuterJobDeclarationFacts facts,
            string scenario, int activeLimit, long jobMemory, bool nested)
        {
            return facts != null && String.Equals(facts.Scenario, scenario,
                StringComparison.Ordinal) && facts.ActiveProcessLimit == activeLimit &&
                facts.ProcessMemoryLimitBytes == FixedRuntimeBindingContract.ProcessMemoryLimitBytes &&
                facts.JobMemoryLimitBytes == jobMemory && facts.RequireKillOnClose &&
                facts.RequireBreakawayForbidden && facts.RequireNestedInnerJob == nested &&
                facts.RequireNonInheritableHandle && facts.DeclareSupervisorNotMember &&
                facts.RequireUnnamedJob && facts.RequireWorkerCreatedSuspended &&
                facts.RequireWorkerAssignedBeforeResume && facts.RequireWorkerMembershipQuery &&
                facts.RequiredWorkerResumeCallCount == 1;
        }

        internal static BuildUnpinnedRefusal Validate(RuntimeBindingState state,
            RuntimeBindingFacts facts)
        {
            string scenario = null;
            int generation = -1;
            bool stateReady = state != null &&
                state.TryGetRefusalBinding(out scenario, out generation);
            bool exact = stateReady && facts != null &&
                ExactContract(facts.Contract) &&
                ExactUnboundImage(facts.Supervisor, RuntimeImageRole.Supervisor) &&
                ExactUnboundImage(facts.Controller, RuntimeImageRole.Controller) &&
                ExactUnboundImage(facts.LockedPreflight, RuntimeImageRole.LockedPreflight) &&
                ExactUiFixture(facts.UiFixture) &&
                ExactUnboundImage(facts.TimeoutRoot, RuntimeImageRole.TimeoutRoot) &&
                ExactUnboundImage(facts.TimeoutChild, RuntimeImageRole.TimeoutChild) &&
                ExactObjectBindingRequirements(facts.ObjectBindingRequirements) &&
                ExactRoute(facts.UiRoute, "ui-success-v1", RuntimeImageRole.Controller,
                    RuntimeImageRole.UiFixture, RuntimeImageRole.Absent, true,
                    DeclaredFixtureStatus.Succeeded) &&
                ExactRoute(facts.TimeoutRoute, "tree-timeout-v1", RuntimeImageRole.Controller,
                    RuntimeImageRole.TimeoutRoot, RuntimeImageRole.TimeoutChild, true,
                    DeclaredFixtureStatus.ExpectedTimeoutContained) &&
                ExactRoute(facts.LockedRoute, "locked-refusal-v1",
                    RuntimeImageRole.LockedPreflight, RuntimeImageRole.Absent,
                    RuntimeImageRole.Absent, false, DeclaredFixtureStatus.NotRun) &&
                ExactOuterJob(facts.UiOuterJob, "ui-success-v1", 2, 536870912, true) &&
                ExactOuterJob(facts.TimeoutOuterJob, "tree-timeout-v1", 3, 805306368, true) &&
                ExactOuterJob(facts.LockedOuterJob, "locked-refusal-v1", 1, 268435456, false);
            return exact ? new BuildUnpinnedRefusal(state, scenario, generation,
                FixedRuntimeBindingContract.ProfileId,
                FixedRuntimeBindingContract.RuntimeProfileByteCount,
                FixedRuntimeBindingContract.RuntimeProfileSha256, RefusalKey) : null;
        }
    }
}
