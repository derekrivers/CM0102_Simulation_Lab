using System;

namespace Cm0102.SyntheticLauncherController
{
    internal sealed class RuntimeFactsBuilder
    {
        internal RuntimeContractFacts Contract;
        internal RuntimeImageDeclarationFacts Supervisor;
        internal RuntimeImageDeclarationFacts Controller;
        internal RuntimeImageDeclarationFacts LockedPreflight;
        internal RuntimeImageDeclarationFacts UiFixture;
        internal RuntimeImageDeclarationFacts TimeoutRoot;
        internal RuntimeImageDeclarationFacts TimeoutChild;
        internal RuntimeObjectBindingRequirementFacts ObjectBindingRequirements;
        internal RuntimeRouteDeclarationFacts UiRoute;
        internal RuntimeRouteDeclarationFacts TimeoutRoute;
        internal RuntimeRouteDeclarationFacts LockedRoute;
        internal RuntimeOuterJobDeclarationFacts UiOuterJob;
        internal RuntimeOuterJobDeclarationFacts TimeoutOuterJob;
        internal RuntimeOuterJobDeclarationFacts LockedOuterJob;

        internal RuntimeFactsBuilder()
        {
            Contract = RuntimeBindingPolicyTests.Contract(0);
            Supervisor = RuntimeBindingPolicyTests.Image(RuntimeImageRole.Supervisor, 0);
            Controller = RuntimeBindingPolicyTests.Image(RuntimeImageRole.Controller, 0);
            LockedPreflight = RuntimeBindingPolicyTests.Image(RuntimeImageRole.LockedPreflight, 0);
            UiFixture = RuntimeBindingPolicyTests.Image(RuntimeImageRole.UiFixture, 0);
            TimeoutRoot = RuntimeBindingPolicyTests.Image(RuntimeImageRole.TimeoutRoot, 0);
            TimeoutChild = RuntimeBindingPolicyTests.Image(RuntimeImageRole.TimeoutChild, 0);
            ObjectBindingRequirements = RuntimeBindingPolicyTests.ObjectBindingRequirements(0);
            UiRoute = RuntimeBindingPolicyTests.Route(0, 0);
            TimeoutRoute = RuntimeBindingPolicyTests.Route(1, 0);
            LockedRoute = RuntimeBindingPolicyTests.Route(2, 0);
            UiOuterJob = RuntimeBindingPolicyTests.OuterJob(0, 0);
            TimeoutOuterJob = RuntimeBindingPolicyTests.OuterJob(1, 0);
            LockedOuterJob = RuntimeBindingPolicyTests.OuterJob(2, 0);
        }

        internal RuntimeBindingFacts Build()
        {
            return new RuntimeBindingFacts(Contract, Supervisor, Controller, LockedPreflight,
                UiFixture, TimeoutRoot, TimeoutChild, ObjectBindingRequirements, UiRoute,
                TimeoutRoute, LockedRoute, UiOuterJob, TimeoutOuterJob, LockedOuterJob);
        }

        internal void SetImage(int index, RuntimeImageDeclarationFacts value)
        {
            switch (index)
            {
                case 0: Supervisor = value; break;
                case 1: Controller = value; break;
                case 2: LockedPreflight = value; break;
                case 3: UiFixture = value; break;
                case 4: TimeoutRoot = value; break;
                case 5: TimeoutChild = value; break;
                default: throw new ArgumentException("index");
            }
        }

        internal void SetRoute(int index, RuntimeRouteDeclarationFacts value)
        {
            switch (index)
            {
                case 0: UiRoute = value; break;
                case 1: TimeoutRoute = value; break;
                case 2: LockedRoute = value; break;
                default: throw new ArgumentException("index");
            }
        }

        internal void SetOuterJob(int index, RuntimeOuterJobDeclarationFacts value)
        {
            switch (index)
            {
                case 0: UiOuterJob = value; break;
                case 1: TimeoutOuterJob = value; break;
                case 2: LockedOuterJob = value; break;
                default: throw new ArgumentException("index");
            }
        }
    }

    internal static class RuntimeBindingPolicyTests
    {
        private static int assertions;

        private static void Assert(bool value)
        {
            assertions++;
            if (!value) throw new InvalidOperationException("assertion-failed-" + assertions.ToString());
        }

        internal static RuntimeContractFacts Contract(int mutation)
        {
            string profileId = FixedRuntimeBindingContract.ProfileId;
            RuntimeArtifactIdentity profile = new RuntimeArtifactIdentity(
                FixedRuntimeBindingContract.RuntimeProfileByteCount,
                FixedRuntimeBindingContract.RuntimeProfileSha256);
            RuntimeBuildBinding buildBinding = RuntimeBuildBinding.BuildUnpinned;
            bool publicManifestBindingUnbound = true;
            RuntimeArtifactIdentity publicManifestBindingIdentity = null;
            bool liveNotRun = true;
            bool unreachable = true;
            bool ineligible = true;
            bool originalNotRun = true;
            bool originalUnqualified = true;
            bool noImageExecution = true;
            bool noObjectObservation = true;
            bool noLiveJobObservation = true;
            switch (mutation)
            {
                case 1: profileId = "other-profile"; break;
                case 2: profile = new RuntimeArtifactIdentity(profile.ByteCount + 1, profile.Sha256); break;
                case 3: profile = new RuntimeArtifactIdentity(profile.ByteCount, new String('2', 64)); break;
                case 4: buildBinding = RuntimeBuildBinding.ImagesPinned; break;
                case 5: publicManifestBindingUnbound = false; break;
                case 6:
                    publicManifestBindingIdentity =
                        new RuntimeArtifactIdentity(1, new String('1', 64));
                    break;
                case 7: liveNotRun = false; break;
                case 8: unreachable = false; break;
                case 9: ineligible = false; break;
                case 10: originalNotRun = false; break;
                case 11: originalUnqualified = false; break;
                case 12: noImageExecution = false; break;
                case 13: noObjectObservation = false; break;
                case 14: noLiveJobObservation = false; break;
                case 15: profileId = null; break;
                case 16: profile = null; break;
                case 17: profile = new RuntimeArtifactIdentity(profile.ByteCount, null); break;
            }
            return new RuntimeContractFacts(profileId, profile, buildBinding,
                publicManifestBindingUnbound, publicManifestBindingIdentity, liveNotRun,
                unreachable, ineligible, originalNotRun, originalUnqualified,
                noImageExecution, noObjectObservation, noLiveJobObservation);
        }

        internal static RuntimeImageDeclarationFacts Image(RuntimeImageRole expectedRole,
            int mutation)
        {
            RuntimeImageRole role = expectedRole;
            string name = FixedRuntimeBindingContract.NameFor(expectedRole);
            bool ui = expectedRole == RuntimeImageRole.UiFixture;
            RuntimeImageBindingState binding = ui ? RuntimeImageBindingState.BoundNotRun :
                RuntimeImageBindingState.Unbound;
            RuntimeArtifactIdentity identity = ui ? new RuntimeArtifactIdentity(
                FixedRuntimeBindingContract.UiFixtureByteCount,
                FixedRuntimeBindingContract.UiFixtureSha256) : null;
            switch (mutation)
            {
                case 1: role = RuntimeImageRole.Absent; break;
                case 2: name = "Other.exe"; break;
                case 3: binding = ui ? RuntimeImageBindingState.Unbound :
                    RuntimeImageBindingState.BoundNotRun; break;
                case 4:
                    identity = ui ? new RuntimeArtifactIdentity(identity.ByteCount + 1,
                        identity.Sha256) : new RuntimeArtifactIdentity(1, new String('1', 64));
                    break;
                case 5:
                    identity = ui ? new RuntimeArtifactIdentity(identity.ByteCount,
                        new String('2', 64)) : new RuntimeArtifactIdentity(2, new String('2', 64));
                    break;
                case 6: name = null; break;
                case 7:
                    identity = ui ? new RuntimeArtifactIdentity(identity.ByteCount, null) :
                        new RuntimeArtifactIdentity(1, null);
                    break;
                case 8: identity = null; break;
            }
            return new RuntimeImageDeclarationFacts(role, name, binding, identity);
        }

        internal static RuntimeObjectBindingRequirementFacts ObjectBindingRequirements(
            int mutation)
        {
            string publicName = FixedRuntimeBindingContract.PublicConfigurationName;
            string privateName = FixedRuntimeBindingContract.PrivateConfigurationName;
            string reportName = FixedRuntimeBindingContract.ReportName;
            bool heldParent = true;
            bool finalPaths = true;
            bool objectIds = true;
            bool sameVolume = true;
            bool regularFiles = true;
            bool alternateMountRejection = true;
            bool distinct = true;
            bool singleLink = true;
            bool noReparse = true;
            bool noAds = true;
            bool stable = true;
            bool copiesNotHardlinks = true;
            bool privateWithoutExecutablePath = true;
            bool rebindBefore = true;
            bool rebindAfter = true;
            switch (mutation)
            {
                case 1: publicName = "Other.public.json"; break;
                case 2: privateName = "Other.private.json"; break;
                case 3: reportName = "Other.report.json"; break;
                case 4: heldParent = false; break;
                case 5: finalPaths = false; break;
                case 6: objectIds = false; break;
                case 7: sameVolume = false; break;
                case 8: distinct = false; break;
                case 9: singleLink = false; break;
                case 10: noReparse = false; break;
                case 11: noAds = false; break;
                case 12: stable = false; break;
                case 13: copiesNotHardlinks = false; break;
                case 14: privateWithoutExecutablePath = false; break;
                case 15: rebindBefore = false; break;
                case 16: rebindAfter = false; break;
                case 17: regularFiles = false; break;
                case 18: alternateMountRejection = false; break;
                case 19: publicName = null; break;
                case 20: privateName = null; break;
                case 21: reportName = null; break;
            }
            return new RuntimeObjectBindingRequirementFacts(publicName, privateName, reportName,
                heldParent, finalPaths, objectIds, sameVolume, regularFiles,
                alternateMountRejection, distinct, singleLink, noReparse, noAds, stable,
                copiesNotHardlinks, privateWithoutExecutablePath, rebindBefore, rebindAfter);
        }

        private static RuntimeImageRole RoleAt(int index)
        {
            switch (index)
            {
                case 0: return RuntimeImageRole.Supervisor;
                case 1: return RuntimeImageRole.Controller;
                case 2: return RuntimeImageRole.LockedPreflight;
                case 3: return RuntimeImageRole.UiFixture;
                case 4: return RuntimeImageRole.TimeoutRoot;
                case 5: return RuntimeImageRole.TimeoutChild;
                default: throw new ArgumentException("index");
            }
        }

        internal static RuntimeRouteDeclarationFacts Route(int index, int mutation)
        {
            string scenario = index == 0 ? "ui-success-v1" :
                (index == 1 ? "tree-timeout-v1" : "locked-refusal-v1");
            RuntimeImageRole worker = index == 2 ? RuntimeImageRole.LockedPreflight :
                RuntimeImageRole.Controller;
            RuntimeImageRole target = index == 0 ? RuntimeImageRole.UiFixture :
                (index == 1 ? RuntimeImageRole.TimeoutRoot : RuntimeImageRole.Absent);
            RuntimeImageRole descendant = index == 1 ? RuntimeImageRole.TimeoutChild :
                RuntimeImageRole.Absent;
            bool processCreation = index != 2;
            DeclaredFixtureStatus fixtureStatus = index == 0 ? DeclaredFixtureStatus.Succeeded :
                (index == 1 ? DeclaredFixtureStatus.ExpectedTimeoutContained :
                    DeclaredFixtureStatus.NotRun);
            switch (mutation)
            {
                case 1: scenario = "other-scenario"; break;
                case 2: worker = RuntimeImageRole.Supervisor; break;
                case 3: target = target == RuntimeImageRole.Absent ?
                    RuntimeImageRole.UiFixture : RuntimeImageRole.Absent; break;
                case 4: descendant = descendant == RuntimeImageRole.Absent ?
                    RuntimeImageRole.TimeoutChild : RuntimeImageRole.Absent; break;
                case 5: processCreation = !processCreation; break;
                case 6: fixtureStatus = fixtureStatus == DeclaredFixtureStatus.NotRun ?
                    DeclaredFixtureStatus.Succeeded : DeclaredFixtureStatus.NotRun; break;
                case 7: scenario = null; break;
            }
            return new RuntimeRouteDeclarationFacts(scenario, worker, target, descendant,
                processCreation, fixtureStatus);
        }

        internal static RuntimeOuterJobDeclarationFacts OuterJob(int index, int mutation)
        {
            string scenario = index == 0 ? "ui-success-v1" :
                (index == 1 ? "tree-timeout-v1" : "locked-refusal-v1");
            int activeLimit = index == 0 ? 2 : (index == 1 ? 3 : 1);
            long processMemory = FixedRuntimeBindingContract.ProcessMemoryLimitBytes;
            long jobMemory = index == 0 ? 536870912 : (index == 1 ? 805306368 : 268435456);
            bool killOnClose = true;
            bool breakawayForbidden = true;
            bool nested = index != 2;
            bool nonInheritable = true;
            bool supervisorNotMember = true;
            bool unnamed = true;
            bool suspended = true;
            bool assigned = true;
            bool membership = true;
            int resumeCount = 1;
            switch (mutation)
            {
                case 1: scenario = "other-scenario"; break;
                case 2: activeLimit++; break;
                case 3: processMemory++; break;
                case 4: jobMemory++; break;
                case 5: killOnClose = false; break;
                case 6: breakawayForbidden = false; break;
                case 7: nested = !nested; break;
                case 8: nonInheritable = false; break;
                case 9: supervisorNotMember = false; break;
                case 10: unnamed = false; break;
                case 11: suspended = false; break;
                case 12: assigned = false; break;
                case 13: membership = false; break;
                case 14: resumeCount = 2; break;
                case 15: scenario = null; break;
            }
            return new RuntimeOuterJobDeclarationFacts(scenario, activeLimit, processMemory,
                jobMemory, killOnClose, breakawayForbidden, nested, nonInheritable,
                supervisorNotMember, unnamed, suspended, assigned, membership, resumeCount);
        }

        private static void AssertRejected(RuntimeBindingFacts facts)
        {
            RuntimeBindingState state = RuntimeBindingState.Start("ui-success-v1");
            Assert(RuntimeBindingPolicy.Validate(state, facts) == null);
        }

        private static void AcceptanceCases()
        {
            string[] scenarios = new string[]
            {
                "ui-success-v1", "tree-timeout-v1", "locked-refusal-v1"
            };
            for (int index = 0; index < scenarios.Length; index++)
            {
                RuntimeBindingState state = RuntimeBindingState.Start(scenarios[index]);
                RuntimeBindingPolicy.BuildUnpinnedRefusal refusal =
                    RuntimeBindingPolicy.Validate(state, new RuntimeFactsBuilder().Build());
                Assert(refusal != null);
                Assert(state.AcceptRefusal(refusal));
                Assert(state.IsTerminal);
                Assert(state.IsIneligible);
                Assert(state.IsUnreachable);
                Assert(!state.IsRejected);
            }
        }

        private static void ContractMutationCases()
        {
            for (int mutation = 1; mutation <= 17; mutation++)
            {
                RuntimeFactsBuilder builder = new RuntimeFactsBuilder();
                builder.Contract = Contract(mutation);
                AssertRejected(builder.Build());
            }
        }

        private static void ImageMutationCases()
        {
            for (int image = 0; image < 6; image++)
            {
                int mutations = RoleAt(image) == RuntimeImageRole.UiFixture ? 8 : 7;
                for (int mutation = 1; mutation <= mutations; mutation++)
                {
                    RuntimeFactsBuilder builder = new RuntimeFactsBuilder();
                    builder.SetImage(image, Image(RoleAt(image), mutation));
                    AssertRejected(builder.Build());
                }
            }
        }

        private static void ObjectBindingRequirementMutationCases()
        {
            for (int mutation = 1; mutation <= 21; mutation++)
            {
                RuntimeFactsBuilder builder = new RuntimeFactsBuilder();
                builder.ObjectBindingRequirements = ObjectBindingRequirements(mutation);
                AssertRejected(builder.Build());
            }
        }

        private static void RouteMutationCases()
        {
            for (int route = 0; route < 3; route++)
            {
                for (int mutation = 1; mutation <= 7; mutation++)
                {
                    RuntimeFactsBuilder builder = new RuntimeFactsBuilder();
                    builder.SetRoute(route, Route(route, mutation));
                    AssertRejected(builder.Build());
                }
            }
        }

        private static void OuterJobMutationCases()
        {
            for (int job = 0; job < 3; job++)
            {
                for (int mutation = 1; mutation <= 15; mutation++)
                {
                    RuntimeFactsBuilder builder = new RuntimeFactsBuilder();
                    builder.SetOuterJob(job, OuterJob(job, mutation));
                    AssertRejected(builder.Build());
                }
            }
        }

        private static void TopLevelNullCases()
        {
            for (int mutation = 0; mutation < 14; mutation++)
            {
                RuntimeFactsBuilder builder = new RuntimeFactsBuilder();
                switch (mutation)
                {
                    case 0: builder.Contract = null; break;
                    case 1: builder.Supervisor = null; break;
                    case 2: builder.Controller = null; break;
                    case 3: builder.LockedPreflight = null; break;
                    case 4: builder.UiFixture = null; break;
                    case 5: builder.TimeoutRoot = null; break;
                    case 6: builder.TimeoutChild = null; break;
                    case 7: builder.ObjectBindingRequirements = null; break;
                    case 8: builder.UiRoute = null; break;
                    case 9: builder.TimeoutRoute = null; break;
                    case 10: builder.LockedRoute = null; break;
                    case 11: builder.UiOuterJob = null; break;
                    case 12: builder.TimeoutOuterJob = null; break;
                    case 13: builder.LockedOuterJob = null; break;
                }
                AssertRejected(builder.Build());
            }
        }

        private static void RefusalOwnershipCases()
        {
            RuntimeBindingFacts facts = new RuntimeFactsBuilder().Build();
            RuntimeBindingState owner = RuntimeBindingState.Start("ui-success-v1");
            RuntimeBindingState sameScenarioOther = RuntimeBindingState.Start("ui-success-v1");
            RuntimeBindingState otherScenario = RuntimeBindingState.Start("tree-timeout-v1");
            RuntimeBindingPolicy.BuildUnpinnedRefusal refusal =
                RuntimeBindingPolicy.Validate(owner, facts);
            Assert(refusal != null);
            Assert(!sameScenarioOther.AcceptRefusal(refusal));
            Assert(sameScenarioOther.IsRejected);
            Assert(!otherScenario.AcceptRefusal(refusal));
            Assert(otherScenario.IsRejected);
            Assert(owner.AcceptRefusal(refusal));
            Assert(owner.IsTerminal && owner.IsIneligible && owner.IsUnreachable);
            Assert(!owner.AcceptRefusal(refusal));
            Assert(!owner.IsRejected);
            Assert(RuntimeBindingPolicy.Validate(owner, facts) == null);
            Assert(RuntimeBindingPolicy.Validate(null, facts) == null);
            Assert(RuntimeBindingPolicy.Validate(RuntimeBindingState.Start("ui-success-v1"), null) == null);

            RuntimeBindingState staleOwner = RuntimeBindingState.Start("ui-success-v1");
            RuntimeBindingPolicy.BuildUnpinnedRefusal stale =
                RuntimeBindingPolicy.Validate(staleOwner, facts);
            Assert(stale != null);
            Assert(!staleOwner.AcceptRefusal(null));
            Assert(!staleOwner.AcceptRefusal(stale));
            Assert(!staleOwner.IsTerminal && staleOwner.IsRejected);

            bool threw = false;
            try { RuntimeBindingState.Start("unknown"); }
            catch (ArgumentException) { threw = true; }
            Assert(threw);

            threw = false;
            try { RuntimeBindingState.Start(null); }
            catch (ArgumentException) { threw = true; }
            Assert(threw);
        }

        private static void ConcurrentRefusalCase()
        {
            RuntimeBindingState state = RuntimeBindingState.Start("ui-success-v1");
            RuntimeBindingPolicy.BuildUnpinnedRefusal refusal = RuntimeBindingPolicy.Validate(
                state, new RuntimeFactsBuilder().Build());
            bool firstAccepted = false;
            bool secondAccepted = false;
            System.Threading.ManualResetEvent firstReady =
                new System.Threading.ManualResetEvent(false);
            System.Threading.ManualResetEvent secondReady =
                new System.Threading.ManualResetEvent(false);
            System.Threading.ManualResetEvent release =
                new System.Threading.ManualResetEvent(false);
            System.Threading.Thread first = new System.Threading.Thread(
                new System.Threading.ThreadStart(delegate
                {
                    firstReady.Set();
                    release.WaitOne();
                    firstAccepted = state.AcceptRefusal(refusal);
                }));
            System.Threading.Thread second = new System.Threading.Thread(
                new System.Threading.ThreadStart(delegate
                {
                    secondReady.Set();
                    release.WaitOne();
                    secondAccepted = state.AcceptRefusal(refusal);
                }));
            first.Start();
            second.Start();
            firstReady.WaitOne();
            secondReady.WaitOne();
            release.Set();
            first.Join();
            second.Join();
            firstReady.Close();
            secondReady.Close();
            release.Close();
            Assert(firstAccepted != secondAccepted);
            Assert(state.IsTerminal);
            Assert(state.IsIneligible);
            Assert(state.IsUnreachable);
            Assert(!state.IsRejected);
        }

        private static int Main()
        {
            AcceptanceCases();
            ContractMutationCases();
            ImageMutationCases();
            RouteMutationCases();
            OuterJobMutationCases();
            ObjectBindingRequirementMutationCases();
            TopLevelNullCases();
            RefusalOwnershipCases();
            ConcurrentRefusalCase();
            if (assertions != 202) throw new InvalidOperationException("assertion-count");
            Console.WriteLine("PASS " + assertions.ToString());
            return 0;
        }
    }
}
