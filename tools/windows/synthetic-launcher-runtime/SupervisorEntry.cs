using System;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal static class SupervisorEntry
    {
        private static int Main()
        {
            SupervisorBootstrapSnapshot snapshot;
            if (!SupervisorBootstrapNative.TryCapture(out snapshot))
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
                    if (decision.Disposition != RuntimeGateDisposition.PinnedLease)
                        return RuntimeCanonicalData.ExitBindingRejection;
                    RuntimeLeaseUse lease;
                    if (!gate.TryConsumeLease(decision.Lease, binding, out lease))
                        return RuntimeCanonicalData.ExitBindingRejection;
                    RuntimeScenarioPlan plan;
                    if (!RuntimeScenarioPlan.TryCreate(lease.ScenarioId,
                            RuntimeScenarioRole.Supervisor, out plan))
                        return RuntimeCanonicalData.ExitBindingRejection;
                    IRuntimeSupervisorScenarioPort port = new SupervisorLiveNative(lease,
                        snapshot, facts.PublicConfiguration.SourceRevision, plan);
                    return RuntimeScenarioEngine.Run(plan, port).ExitCode;
                }
                catch (Exception)
                {
                    return RuntimeCanonicalData.ExitBindingRejection;
                }
            }
        }

        private static RuntimeObjectFacts ObservedFacts(SupervisorBootstrapSnapshot snapshot)
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
                SupervisorBoundObject value = snapshot.Objects[leaves[index]];
                identities[index] = new RuntimeIdentity(roles[index], value.Bytes.Length,
                    value.Sha256);
            }
            SupervisorBoundObject publicConfiguration =
                snapshot.Objects["SyntheticLauncherController.public.v1.json"];
            SupervisorBoundObject manifest =
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
