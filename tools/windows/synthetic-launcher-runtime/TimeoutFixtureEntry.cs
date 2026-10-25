using System;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal static class TimeoutFixtureEntry
    {
        private static int Main()
        {
            TimeoutFixtureBootstrapSnapshot snapshot;
            if (!TimeoutFixtureBootstrapNative.TryCapture(out snapshot))
                return RuntimeCanonicalData.ExitBindingRejection;
            using (snapshot)
            {
                try
                {
                    RuntimeObjectFacts observed = ObservedFacts(snapshot);
                    RuntimeGateFacts facts;
                    if (!RuntimeCanonicalData.TryParseProductionFacts(
                            snapshot.Objects["SyntheticLauncherController.public.v1.json"].Bytes,
                            snapshot.Objects["SyntheticLauncherController.private.v1.json"].Bytes,
                            observed, out facts))
                        return RuntimeCanonicalData.ExitBindingRejection;
                    RuntimeGate gate = new RuntimeGate();
                    RuntimeGateDecision decision = gate.Evaluate(facts);
                    RuntimeConsumerBinding binding = new RuntimeConsumerBinding(
                        snapshot.OwnerBinding, facts.PrivateConfiguration.ScenarioId, 1,
                        facts.PublicConfiguration.ProfileId);
                    if (decision.Disposition == RuntimeGateDisposition.BuildUnpinnedRefusal)
                    {
                        RuntimeRefusalUse refusal;
                        return gate.TryConsumeRefusal(decision.Refusal, binding, out refusal) ?
                            refusal.ExitCode : RuntimeCanonicalData.ExitBindingRejection;
                    }
                    if (decision.Disposition != RuntimeGateDisposition.PinnedLease ||
                            !String.Equals(facts.PrivateConfiguration.ScenarioId,
                                RuntimeCanonicalData.TreeTimeoutScenario,
                                StringComparison.Ordinal))
                        return RuntimeCanonicalData.ExitBindingRejection;
                    RuntimeLeaseUse lease;
                    if (!gate.TryConsumeLease(decision.Lease, binding, out lease))
                        return RuntimeCanonicalData.ExitBindingRejection;
                    RuntimeScenarioPlan plan;
                    if (!RuntimeScenarioPlan.TryCreate(lease.ScenarioId,
                            RuntimeScenarioRole.TimeoutRoot, out plan))
                        return RuntimeCanonicalData.ExitBindingRejection;
                    IRuntimeTimeoutRootScenarioPort port = new TimeoutFixtureLiveNative(
                        lease, snapshot, plan);
                    return RuntimeScenarioEngine.Run(plan, port).ExitCode;
                }
                catch (Exception)
                {
                    return RuntimeCanonicalData.ExitBindingRejection;
                }
            }
        }

        private static RuntimeObjectFacts ObservedFacts(TimeoutFixtureBootstrapSnapshot snapshot)
        {
            string[] roles = { "controller", "locked_preflight", "supervisor",
                "timeout_child", "timeout_root", "ui_fixture" };
            string[] leaves = { "SyntheticLauncherController.exe",
                "SyntheticLauncherLockedPreflight.exe", "SyntheticLauncherSupervisor.exe",
                "SyntheticLauncherTimeoutChild.exe", "SyntheticLauncherTimeoutFixture.exe",
                "SyntheticLauncherFixture.exe" };
            RuntimeIdentity[] identities = new RuntimeIdentity[roles.Length];
            for (int index = 0; index < roles.Length; index++)
            {
                TimeoutFixtureBoundObject value = snapshot.Objects[leaves[index]];
                identities[index] = new RuntimeIdentity(roles[index], value.Bytes.Length,
                    value.Sha256);
            }
            TimeoutFixtureBoundObject publicConfiguration =
                snapshot.Objects["SyntheticLauncherController.public.v1.json"];
            TimeoutFixtureBoundObject manifest =
                snapshot.Objects["SyntheticLauncherBuildManifest.v1.json"];
            return new RuntimeObjectFacts(snapshot.OwnerBinding, 1,
                true, true, true, snapshot.ExactObjectSafety,
                snapshot.PairwiseDistinctObjects, snapshot.StableBindings,
                new RuntimeIdentity("public_configuration", publicConfiguration.Bytes.Length,
                    publicConfiguration.Sha256),
                new RuntimeIdentity("production_manifest", manifest.Bytes.Length,
                    manifest.Sha256), new RuntimeIdentitySet(identities));
        }
    }
}
