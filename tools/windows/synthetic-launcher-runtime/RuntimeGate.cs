using System;
using System.Threading;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal enum RuntimeGateDisposition
    {
        Rejected = 0,
        BuildUnpinnedRefusal = 1,
        PinnedLease = 2
    }

    internal sealed class RuntimeGateDecision
    {
        private RuntimeGateDecision(RuntimeGateDisposition disposition, string failure,
            BuildUnpinnedRefusal refusal, PinnedRuntimeLease lease)
        {
            Disposition = disposition;
            Failure = failure;
            Refusal = refusal;
            Lease = lease;
        }

        internal RuntimeGateDisposition Disposition { get; private set; }
        internal string Failure { get; private set; }
        internal BuildUnpinnedRefusal Refusal { get; private set; }
        internal PinnedRuntimeLease Lease { get; private set; }

        internal static RuntimeGateDecision Reject(string failure)
        {
            return new RuntimeGateDecision(RuntimeGateDisposition.Rejected, failure, null, null);
        }

        internal static RuntimeGateDecision Refuse(BuildUnpinnedRefusal refusal)
        {
            return new RuntimeGateDecision(RuntimeGateDisposition.BuildUnpinnedRefusal,
                null, refusal, null);
        }

        internal static RuntimeGateDecision Permit(PinnedRuntimeLease lease)
        {
            return new RuntimeGateDecision(RuntimeGateDisposition.PinnedLease,
                null, null, lease);
        }
    }

    internal sealed class RuntimeRefusalUse
    {
        internal RuntimeRefusalUse(string ownerBinding, string scenarioId,
            long generation, string profileId)
        {
            OwnerBinding = ownerBinding;
            ScenarioId = scenarioId;
            Generation = generation;
            ProfileId = profileId;
        }

        internal string OwnerBinding { get; private set; }
        internal string ScenarioId { get; private set; }
        internal long Generation { get; private set; }
        internal string ProfileId { get; private set; }
        internal int ExitCode { get { return RuntimeCanonicalData.ExitBuildUnpinned; } }
    }

    internal sealed class RuntimeLeaseUse
    {
        internal RuntimeLeaseUse(string ownerBinding, string scenarioId,
            long generation, string profileId)
        {
            OwnerBinding = ownerBinding;
            ScenarioId = scenarioId;
            Generation = generation;
            ProfileId = profileId;
        }

        internal string OwnerBinding { get; private set; }
        internal string ScenarioId { get; private set; }
        internal long Generation { get; private set; }
        internal string ProfileId { get; private set; }
    }

    internal sealed class BuildUnpinnedRefusal
    {
        private readonly object gateKey;
        private readonly string ownerBinding;
        private readonly string scenarioId;
        private readonly long generation;
        private readonly string profileId;
        private int consumed;

        internal BuildUnpinnedRefusal(object gateKey, string ownerBinding, string scenarioId,
            long generation, string profileId)
        {
            this.gateKey = gateKey;
            this.ownerBinding = ownerBinding;
            this.scenarioId = scenarioId;
            this.generation = generation;
            this.profileId = profileId;
        }

        internal bool TryConsume(object expectedGateKey, RuntimeConsumerBinding binding,
            out RuntimeRefusalUse use)
        {
            use = null;
            if (Interlocked.CompareExchange(ref consumed, 1, 0) != 0)
                return false;
            if (!Object.ReferenceEquals(gateKey, expectedGateKey) ||
                    !ExactBinding(binding, ownerBinding, scenarioId, generation, profileId))
                return false;
            use = new RuntimeRefusalUse(ownerBinding, scenarioId, generation, profileId);
            return true;
        }

        private static bool ExactBinding(RuntimeConsumerBinding binding, string owner,
            string scenario, long expectedGeneration, string profile)
        {
            return binding != null && binding.Generation == expectedGeneration &&
                String.Equals(binding.OwnerBinding, owner, StringComparison.Ordinal) &&
                String.Equals(binding.ScenarioId, scenario, StringComparison.Ordinal) &&
                String.Equals(binding.ProfileId, profile, StringComparison.Ordinal);
        }
    }

    internal sealed class PinnedRuntimeLease
    {
        private readonly object gateKey;
        private readonly string ownerBinding;
        private readonly string scenarioId;
        private readonly long generation;
        private readonly string profileId;
        private int consumed;

        internal PinnedRuntimeLease(object gateKey, string ownerBinding, string scenarioId,
            long generation, string profileId)
        {
            this.gateKey = gateKey;
            this.ownerBinding = ownerBinding;
            this.scenarioId = scenarioId;
            this.generation = generation;
            this.profileId = profileId;
        }

        internal bool TryConsume(object expectedGateKey, RuntimeConsumerBinding binding,
            out RuntimeLeaseUse use)
        {
            use = null;
            if (Interlocked.CompareExchange(ref consumed, 1, 0) != 0)
                return false;
            if (!Object.ReferenceEquals(gateKey, expectedGateKey) ||
                    !ExactBinding(binding, ownerBinding, scenarioId, generation, profileId))
                return false;
            use = new RuntimeLeaseUse(ownerBinding, scenarioId, generation, profileId);
            return true;
        }

        private static bool ExactBinding(RuntimeConsumerBinding binding, string owner,
            string scenario, long expectedGeneration, string profile)
        {
            return binding != null && binding.Generation == expectedGeneration &&
                String.Equals(binding.OwnerBinding, owner, StringComparison.Ordinal) &&
                String.Equals(binding.ScenarioId, scenario, StringComparison.Ordinal) &&
                String.Equals(binding.ProfileId, profile, StringComparison.Ordinal);
        }
    }

    internal sealed class RuntimeGate
    {
        private readonly object gateKey = new object();
        private int evaluated;

        internal RuntimeGateDecision Evaluate(RuntimeGateFacts facts)
        {
            if (Interlocked.CompareExchange(ref evaluated, 1, 0) != 0)
                return RuntimeGateDecision.Reject("evaluation-replay");
            string failure = Validate(facts);
            if (failure != null)
                return RuntimeGateDecision.Reject(failure);
            RuntimePublicConfiguration configuration = facts.PublicConfiguration;
            RuntimePrivateConfiguration privateConfiguration = facts.PrivateConfiguration;
            RuntimeObjectFacts objects = facts.ObjectFacts;
            if (String.Equals(configuration.BuildState,
                    RuntimeCanonicalData.BuildUnpinned, StringComparison.Ordinal))
            {
                return RuntimeGateDecision.Refuse(new BuildUnpinnedRefusal(gateKey,
                    objects.OwnerBinding, privateConfiguration.ScenarioId,
                    objects.Generation, configuration.ProfileId));
            }
            if (!String.Equals(configuration.BuildState,
                    RuntimeCanonicalData.BuildPinned, StringComparison.Ordinal))
                return RuntimeGateDecision.Reject("build-state");
            return RuntimeGateDecision.Permit(new PinnedRuntimeLease(gateKey,
                objects.OwnerBinding, privateConfiguration.ScenarioId,
                objects.Generation, configuration.ProfileId));
        }

        internal bool TryConsumeRefusal(BuildUnpinnedRefusal refusal,
            RuntimeConsumerBinding binding, out RuntimeRefusalUse use)
        {
            use = null;
            return refusal != null && refusal.TryConsume(gateKey, binding, out use);
        }

        internal bool TryConsumeLease(PinnedRuntimeLease lease,
            RuntimeConsumerBinding binding, out RuntimeLeaseUse use)
        {
            use = null;
            return lease != null && lease.TryConsume(gateKey, binding, out use);
        }

        private static string Validate(RuntimeGateFacts facts)
        {
            if (facts == null || facts.PublicConfiguration == null ||
                    facts.PrivateConfiguration == null || facts.ObjectFacts == null)
                return "missing-facts";
            RuntimePublicConfiguration publicValue = facts.PublicConfiguration;
            RuntimePrivateConfiguration privateValue = facts.PrivateConfiguration;
            RuntimeObjectFacts objects = facts.ObjectFacts;
            if (!RuntimeCanonicalData.IsScenario(privateValue.ScenarioId))
                return "scenario";
            if (!RuntimeIdentity.IsLowerHexNonZero(objects.OwnerBinding, 64) ||
                    objects.Generation <= 0 ||
                    !String.Equals(publicValue.ProfileId, RuntimeCanonicalData.ProfileId,
                        StringComparison.Ordinal) ||
                    !RuntimeIdentity.IsLowerHexNonZero(publicValue.SourceRevision, 40))
                return "public-binding";
            if (!String.Equals(publicValue.BuildState, RuntimeCanonicalData.BuildUnpinned,
                    StringComparison.Ordinal) &&
                    !String.Equals(publicValue.BuildState, RuntimeCanonicalData.BuildPinned,
                        StringComparison.Ordinal))
                return "build-state";
            if (!RuntimeIdentity.IsLowerHexNonZero(privateValue.SourceRevision, 40) ||
                    !String.Equals(privateValue.SourceRevision, publicValue.SourceRevision,
                        StringComparison.Ordinal))
                return "private-binding";
            if (!RuntimeCanonicalData.GuardPathsDistinctAndNonAncestor(
                    privateValue.AcceptedHostGuard, privateValue.AttemptRootGuard,
                    privateValue.InstalledTreeGuard, privateValue.VirtualStoreGuard))
                return "guard-paths";
            if (privateValue.PublicConfigurationIdentity == null ||
                    !privateValue.PublicConfigurationIdentity.IsWellFormed() ||
                    !String.Equals(privateValue.PublicConfigurationIdentity.Role,
                        "public_configuration", StringComparison.Ordinal))
                return "public-configuration-identity";
            if (!objects.CanonicalPublicConfiguration ||
                    !objects.CanonicalPrivateConfiguration ||
                    !objects.BootstrapAuthorityClosed || !objects.ExactObjectSafety ||
                    !objects.PairwiseDistinctObjects || !objects.StableBindings)
                return "object-safety";
            if (!privateValue.PublicConfigurationIdentity.Exact(
                        objects.ObservedPublicConfigurationIdentity))
                return "observed-public-configuration";
            if (String.Equals(publicValue.BuildState, RuntimeCanonicalData.BuildUnpinned,
                    StringComparison.Ordinal))
                return null;
            if (publicValue.ProductionManifestIdentity == null ||
                    !publicValue.ProductionManifestIdentity.IsWellFormed() ||
                    !String.Equals(publicValue.ProductionManifestIdentity.Role,
                        "production_manifest", StringComparison.Ordinal) ||
                    publicValue.PrivateSchemaIdentity == null ||
                    !publicValue.PrivateSchemaIdentity.IsWellFormed() ||
                    !String.Equals(publicValue.PrivateSchemaIdentity.Role,
                        "runtime_private_schema", StringComparison.Ordinal) ||
                    publicValue.RoleIdentities == null ||
                    !publicValue.RoleIdentities.IsCanonicalRoleSet())
                return "public-identities";
            if (!publicValue.ProductionManifestIdentity.Exact(
                        privateValue.ProductionManifestIdentity) ||
                    !publicValue.PrivateSchemaIdentity.Exact(privateValue.PrivateSchemaIdentity) ||
                    !publicValue.RoleIdentities.Exact(privateValue.RoleIdentities))
                return "private-identities";
            if (!publicValue.ProductionManifestIdentity.Exact(
                        objects.ObservedProductionManifestIdentity) ||
                    !publicValue.RoleIdentities.Exact(objects.ObservedRoleIdentities))
                return "observed-identities";
            return null;
        }

    }
}
