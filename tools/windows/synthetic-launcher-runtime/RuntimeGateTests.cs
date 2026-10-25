using System;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal static class RuntimeGateTests
    {
        private static int assertions;

        private sealed class ConcurrentRefusalAttempt
        {
            internal RuntimeGate Gate;
            internal BuildUnpinnedRefusal Refusal;
            internal RuntimeConsumerBinding Binding;
            internal System.Threading.ManualResetEvent Start;
            internal int Success;

            internal void Run()
            {
                Start.WaitOne();
                RuntimeRefusalUse use;
                if (Gate.TryConsumeRefusal(Refusal, Binding, out use))
                    System.Threading.Interlocked.Increment(ref Success);
            }
        }

        private sealed class ConcurrentLeaseAttempt
        {
            internal RuntimeGate Gate;
            internal PinnedRuntimeLease Lease;
            internal RuntimeConsumerBinding Binding;
            internal System.Threading.ManualResetEvent Start;
            internal int Success;

            internal void Run()
            {
                Start.WaitOne();
                RuntimeLeaseUse use;
                if (Gate.TryConsumeLease(Lease, Binding, out use))
                    System.Threading.Interlocked.Increment(ref Success);
            }
        }

        private class ScriptedScenarioPort : IRuntimeScenarioPort
        {
            private readonly RuntimeScenarioRole role;
            private readonly int failAt;
            private readonly int throwAt;
            private readonly int cleanupMode;
            private readonly RuntimeScenarioStage[] calls = new RuntimeScenarioStage[64];
            private int callCount;
            private int cleanupCount;

            internal ScriptedScenarioPort(RuntimeScenarioRole role, int failAt,
                int throwAt, int cleanupMode)
            {
                this.role = role;
                this.failAt = failAt;
                this.throwAt = throwAt;
                this.cleanupMode = cleanupMode;
            }

            public RuntimeScenarioRole Role { get { return role; } }
            internal int CallCount { get { return callCount; } }
            internal int CleanupCount { get { return cleanupCount; } }

            internal RuntimeScenarioStage CallAt(int index)
            {
                return index >= 0 && index < callCount ? calls[index] :
                    RuntimeScenarioStage.None;
            }

            public RuntimeScenarioStepResult Execute(RuntimeScenarioStage stage)
            {
                int index = callCount;
                calls[callCount++] = stage;
                if (index == throwAt) throw new InvalidOperationException("scripted-stage");
                if (index == failAt)
                    return RuntimeScenarioStepResult.Failed(
                        RuntimeCanonicalData.ExitBindingRejection);
                return RuntimeScenarioStepResult.Passed();
            }

            public RuntimeScenarioStepResult Cleanup()
            {
                cleanupCount++;
                if (cleanupMode == 2)
                    throw new InvalidOperationException("scripted-cleanup");
                if (cleanupMode == 1)
                    return RuntimeScenarioStepResult.Failed(
                        RuntimeCanonicalData.ExitCleanupFailure);
                return RuntimeScenarioStepResult.Passed();
            }
        }

        private sealed class ScriptedSupervisorPort : ScriptedScenarioPort,
            IRuntimeSupervisorScenarioPort
        {
            internal ScriptedSupervisorPort(RuntimeScenarioRole role, int failAt,
                int throwAt, int cleanupMode) : base(role, failAt, throwAt, cleanupMode) { }
        }

        private sealed class ScriptedControllerPort : ScriptedScenarioPort,
            IRuntimeControllerScenarioPort
        {
            internal ScriptedControllerPort(RuntimeScenarioRole role, int failAt,
                int throwAt, int cleanupMode) : base(role, failAt, throwAt, cleanupMode) { }
        }

        private sealed class ScriptedLockedPort : ScriptedScenarioPort,
            IRuntimeLockedPreflightScenarioPort
        {
            internal ScriptedLockedPort(RuntimeScenarioRole role, int failAt,
                int throwAt, int cleanupMode) : base(role, failAt, throwAt, cleanupMode) { }
        }

        private sealed class ScriptedTimeoutRootPort : ScriptedScenarioPort,
            IRuntimeTimeoutRootScenarioPort
        {
            internal ScriptedTimeoutRootPort(RuntimeScenarioRole role, int failAt,
                int throwAt, int cleanupMode) : base(role, failAt, throwAt, cleanupMode) { }
        }

        private sealed class ScriptedTimeoutChildPort : ScriptedScenarioPort,
            IRuntimeTimeoutChildScenarioPort
        {
            internal ScriptedTimeoutChildPort(RuntimeScenarioRole role, int failAt,
                int throwAt, int cleanupMode) : base(role, failAt, throwAt, cleanupMode) { }
        }

        private static void Assert(bool value)
        {
            assertions++;
            if (!value)
                throw new InvalidOperationException("assertion-failed-" + assertions.ToString());
        }

        private static string Hex(char value, int width)
        {
            return new String(value, width);
        }

        private static RuntimeIdentity Identity(string role, int offset)
        {
            if (String.Equals(role, "ui_fixture", StringComparison.Ordinal))
                return new RuntimeIdentity(role, RuntimeCanonicalData.UiFixtureByteCount,
                    RuntimeCanonicalData.UiFixtureSha256);
            char value = (char)('1' + offset);
            if (value > '9')
                value = (char)('a' + offset - 9);
            return new RuntimeIdentity(role, 1000 + offset, Hex(value, 64));
        }

        private static string IdentityJson(int offset)
        {
            RuntimeIdentity identity = Identity("unused", offset);
            return "{\"byte_count\":" + identity.ByteCount.ToString() +
                ",\"sha256\":\"" + identity.Sha256 + "\"}";
        }

        private static string RoleIdentityJson(int index)
        {
            RuntimeIdentity identity = Identity(RuntimeCanonicalData.IdentityRoleAt(index), index);
            return "{\"byte_count\":" + identity.ByteCount.ToString() +
                ",\"sha256\":\"" + identity.Sha256 + "\"}";
        }

        private static string RolesJson()
        {
            string result = "{";
            for (int index = 0; index < RuntimeCanonicalData.RequiredIdentityRoleCount; index++)
            {
                if (index != 0)
                    result += ",";
                result += "\"" + RuntimeCanonicalData.IdentityRoleAt(index) + "\":" +
                    RoleIdentityJson(index);
            }
            return result + "}";
        }

        private static byte[] Ascii(string value)
        {
            byte[] result = new byte[value.Length];
            for (int index = 0; index < value.Length; index++)
            {
                Assert(value[index] <= 0x7f);
                result[index] = (byte)value[index];
            }
            return result;
        }

        private static string PublicJson(string buildState)
        {
            return "{\"approved_artifacts\":{\"complete_bmp\":{\"byte_count\":230454," +
                "\"sha256\":\"5dac08fba06a53bb0a480fe388907e78147b5c0d042fee53eea2ff81b4ee8bc6\"}," +
                "\"ready_bmp\":{\"byte_count\":230454,\"sha256\":" +
                "\"4f471fd3bc87f53fef9d7f200eaccb0ebe69a0240a9cf09f79bc2bfec3c51f19\"}}," +
                "\"build_binding\":\"" + buildState + "\"," +
                "\"candidate_production_manifest\":" + IdentityJson(10) + "," +
                "\"fixed_names\":{\"build_manifest\":\"SyntheticLauncherBuildManifest.v1.json\"," +
                "\"complete_bmp\":\"SyntheticLauncherComplete.v1.bmp\"," +
                "\"controller\":\"SyntheticLauncherController.exe\"," +
                "\"locked_preflight\":\"SyntheticLauncherLockedPreflight.exe\"," +
                "\"private_configuration\":\"SyntheticLauncherController.private.v1.json\"," +
                "\"public_configuration\":\"SyntheticLauncherController.public.v1.json\"," +
                "\"ready_bmp\":\"SyntheticLauncherReady.v1.bmp\"," +
                "\"report\":\"SyntheticLauncherReport.v1.json\"," +
                "\"supervisor\":\"SyntheticLauncherSupervisor.exe\"," +
                "\"timeout_child\":\"SyntheticLauncherTimeoutChild.exe\"," +
                "\"timeout_root\":\"SyntheticLauncherTimeoutFixture.exe\"," +
                "\"ui_fixture\":\"SyntheticLauncherFixture.exe\"," +
                "\"worker_evidence\":\"SyntheticLauncherWorkerEvidence.v1.json\"}," +
                "\"profile_id\":\"cm0102-synthetic-launcher-runtime-v1\"," +
                "\"role_identities\":" + RolesJson() + "," +
                "\"runtime_private_schema\":" + IdentityJson(11) + "," +
                "\"schema_version\":1,\"source_revision\":\"" + Hex('b', 40) + "\"}\n";
        }

        private static string PrivateJson()
        {
            return "{\"expected_identities\":" + RolesJson() + "," +
                "\"guard_paths\":{\"accepted_host_artifact\":\"C:\\\\stage2\\\\accepted-host.json\"," +
                "\"attempt_root\":\"C:\\\\stage2\\\\attempt\"," +
                "\"installed_tree\":\"C:\\\\stage2\\\\installed\"," +
                "\"virtual_store_tree\":\"C:\\\\stage2\\\\virtual-store\"}," +
                "\"production_manifest\":" + IdentityJson(10) + "," +
                "\"public_configuration\":" + IdentityJson(12) + "," +
                "\"runtime_private_schema\":" + IdentityJson(11) + "," +
                "\"scenario_id\":\"ui-success-v1\",\"schema_version\":1," +
                "\"source_revision\":\"" + Hex('b', 40) + "\"}\n";
        }

        private static RuntimeObjectFacts ParserObjects()
        {
            return new RuntimeObjectFacts(Hex('a', 64), 1, true, true, true, true, true, true,
                Identity("public_configuration", 12), Identity("production_manifest", 10),
                Roles(-1, null, 0));
        }

        private static RuntimeIdentitySet Roles(int changedIndex, string changedRole,
            int changedOffset)
        {
            RuntimeIdentity[] values = new RuntimeIdentity[
                RuntimeCanonicalData.RequiredIdentityRoleCount];
            for (int index = 0; index < values.Length; index++)
            {
                string role = RuntimeCanonicalData.IdentityRoleAt(index);
                int offset = index;
                if (index == changedIndex)
                {
                    if (changedRole != null)
                        role = changedRole;
                    offset += changedOffset;
                }
                values[index] = Identity(role, offset);
            }
            return new RuntimeIdentitySet(values);
        }

        private static RuntimeIdentitySet RolesWithWrongUiFixture()
        {
            RuntimeIdentity[] values = new RuntimeIdentity[
                RuntimeCanonicalData.RequiredIdentityRoleCount];
            for (int index = 0; index < values.Length; index++)
                values[index] = Identity(RuntimeCanonicalData.IdentityRoleAt(index), index);
            values[values.Length - 1] = new RuntimeIdentity("ui_fixture", 1, Hex('e', 64));
            return new RuntimeIdentitySet(values);
        }

        private static RuntimeGateFacts Facts(string buildState, string scenarioId, int mutation)
        {
            string owner = Hex('a', 64);
            long generation = 7;
            string profile = RuntimeCanonicalData.ProfileId;
            string sourceRevision = Hex('b', 40);
            RuntimeIdentity manifest = Identity("production_manifest", 10);
            RuntimeIdentity schema = Identity("runtime_private_schema", 11);
            RuntimeIdentitySet publicRoles = Roles(-1, null, 0);
            RuntimeIdentity publicIdentity = Identity("public_configuration", 12);

            string privateScenario = scenarioId;
            string privateSourceRevision = sourceRevision;
            RuntimeIdentity privateManifest = manifest;
            RuntimeIdentity privateSchema = schema;
            RuntimeIdentitySet privateRoles = Roles(-1, null, 0);
            RuntimeIdentity observedPublic = publicIdentity;
            RuntimeIdentity observedManifest = manifest;
            RuntimeIdentitySet observedRoles = Roles(-1, null, 0);
            bool canonicalPublic = true;
            bool canonicalPrivate = true;
            bool closedBootstrap = true;
            bool exactObjects = true;
            bool distinctObjects = true;
            bool stableBindings = true;
            string acceptedHostGuard = "C:\\stage2\\accepted-host.json";
            string attemptRootGuard = "C:\\stage2\\attempt";
            string installedTreeGuard = "C:\\stage2\\installed";
            string virtualStoreGuard = "C:\\stage2\\virtual-store";

            if (mutation == 1) owner = Hex('A', 64);
            if (mutation == 2) generation = 0;
            if (mutation == 3) profile = "profile-drift";
            if (mutation == 4) sourceRevision = Hex('g', 40);
            if (mutation == 5) manifest = Identity("manifest-drift", 10);
            if (mutation == 6) schema = Identity("schema-drift", 11);
            if (mutation == 7) publicRoles = Roles(4, "role-drift", 0);
            if (mutation == 8) publicRoles = Roles(4, null, 1);
            if (mutation == 9) privateSourceRevision = Hex('c', 40);
            if (mutation == 10) privateScenario = "scenario-drift";
            if (mutation == 11) privateSourceRevision = Hex('d', 40);
            if (mutation == 12) buildState = "build-state-drift";
            if (mutation == 13) publicIdentity = Identity("public-drift", 12);
            if (mutation == 14) privateManifest = Identity("production_manifest", 13);
            if (mutation == 15) privateSchema = Identity("runtime_private_schema", 14);
            if (mutation == 16) privateRoles = Roles(3, null, 1);
            if (mutation == 17) observedPublic = Identity("public_configuration", 15);
            if (mutation == 18) observedManifest = Identity("production_manifest", 16);
            if (mutation == 19) observedRoles = Roles(2, null, 1);
            if (mutation == 20) observedRoles = null;
            if (mutation == 21) canonicalPublic = false;
            if (mutation == 22) canonicalPrivate = false;
            if (mutation == 23) closedBootstrap = false;
            if (mutation == 24) exactObjects = false;
            if (mutation == 25) distinctObjects = false;
            if (mutation == 26) stableBindings = false;
            if (mutation == 27) generation = -1;
            if (mutation == 28) publicRoles = new RuntimeIdentitySet(new RuntimeIdentity[0]);
            if (mutation == 29) privateRoles = null;
            if (mutation == 30) observedManifest = null;
            if (mutation == 31) acceptedHostGuard = "relative";
            if (mutation == 32) attemptRootGuard = acceptedHostGuard;
            if (mutation == 33) installedTreeGuard = "C:\\stage2\\bad%path";
            if (mutation == 34) virtualStoreGuard = "C:\\stage2\\";
            if (mutation == 35) privateSourceRevision = Hex('A', 40);
            if (mutation == 36) publicRoles = RolesWithWrongUiFixture();
            if (mutation == 37) attemptRootGuard = "C:\\stage2\\installed\\attempt";

            RuntimePublicConfiguration publicConfiguration =
                new RuntimePublicConfiguration(profile, buildState, sourceRevision,
                    manifest, schema, publicRoles);
            RuntimePrivateConfiguration privateConfiguration =
                new RuntimePrivateConfiguration(privateScenario, privateSourceRevision,
                    publicIdentity, privateManifest, privateSchema, privateRoles,
                    acceptedHostGuard, attemptRootGuard, installedTreeGuard, virtualStoreGuard);
            RuntimeObjectFacts objects = new RuntimeObjectFacts(owner, generation,
                canonicalPublic,
                canonicalPrivate, closedBootstrap, exactObjects, distinctObjects,
                stableBindings, observedPublic, observedManifest, observedRoles);
            return new RuntimeGateFacts(publicConfiguration, privateConfiguration, objects);
        }

        private static RuntimeConsumerBinding Binding(string owner, string scenario,
            long generation, string profile)
        {
            return new RuntimeConsumerBinding(owner, scenario, generation, profile);
        }

        private static RuntimeConsumerBinding GoodBinding(string scenario)
        {
            return Binding(Hex('a', 64), scenario, 7, RuntimeCanonicalData.ProfileId);
        }

        private static RuntimeGateFacts SparseUnpinnedFacts()
        {
            RuntimeIdentity publicIdentity = Identity("public_configuration", 12);
            RuntimePublicConfiguration publicConfiguration =
                new RuntimePublicConfiguration(RuntimeCanonicalData.ProfileId,
                    RuntimeCanonicalData.BuildUnpinned,
                    Hex('b', 40), null, null, null);
            RuntimePrivateConfiguration privateConfiguration =
                new RuntimePrivateConfiguration(RuntimeCanonicalData.UiSuccessScenario,
                    Hex('b', 40), publicIdentity, null, null, null,
                    "C:\\stage2\\accepted-host.json", "C:\\stage2\\attempt",
                    "C:\\stage2\\installed", "C:\\stage2\\virtual-store");
            RuntimeObjectFacts objects = new RuntimeObjectFacts(Hex('a', 64), 7,
                true, true, true, true,
                true, true, publicIdentity, null, null);
            return new RuntimeGateFacts(publicConfiguration, privateConfiguration, objects);
        }

        private static void CanonicalDataCases()
        {
            Assert(RuntimeCanonicalData.IsScenario(RuntimeCanonicalData.UiSuccessScenario));
            Assert(RuntimeCanonicalData.IsScenario(RuntimeCanonicalData.TreeTimeoutScenario));
            Assert(RuntimeCanonicalData.IsScenario(RuntimeCanonicalData.LockedRefusalScenario));
            Assert(!RuntimeCanonicalData.IsScenario("UI-SUCCESS-V1"));
            Assert(!RuntimeCanonicalData.IsScenario(null));
            Assert(String.Equals(RuntimeCanonicalData.WorkerImageFor(
                RuntimeCanonicalData.UiSuccessScenario), RuntimeCanonicalData.ControllerImage,
                StringComparison.Ordinal));
            Assert(String.Equals(RuntimeCanonicalData.WorkerImageFor(
                RuntimeCanonicalData.TreeTimeoutScenario), RuntimeCanonicalData.ControllerImage,
                StringComparison.Ordinal));
            Assert(String.Equals(RuntimeCanonicalData.WorkerImageFor(
                RuntimeCanonicalData.LockedRefusalScenario),
                RuntimeCanonicalData.LockedPreflightImage, StringComparison.Ordinal));
            Assert(String.Equals(RuntimeCanonicalData.TargetImageFor(
                RuntimeCanonicalData.UiSuccessScenario), RuntimeCanonicalData.UiFixtureImage,
                StringComparison.Ordinal));
            Assert(String.Equals(RuntimeCanonicalData.TargetImageFor(
                RuntimeCanonicalData.TreeTimeoutScenario), RuntimeCanonicalData.TimeoutRootImage,
                StringComparison.Ordinal));
            Assert(RuntimeCanonicalData.TargetImageFor(
                RuntimeCanonicalData.LockedRefusalScenario) == null);
            Assert(RuntimeCanonicalData.WorkerImageFor("scenario-drift") == null);
            Assert(RuntimeCanonicalData.TargetImageFor("scenario-drift") == null);
            for (int index = 0; index < RuntimeCanonicalData.RequiredIdentityRoleCount; index++)
                Assert(RuntimeCanonicalData.IdentityRoleAt(index) != null);
            Assert(RuntimeCanonicalData.IdentityRoleAt(-1) == null);
            Assert(RuntimeCanonicalData.IdentityRoleAt(
                RuntimeCanonicalData.RequiredIdentityRoleCount) == null);
            Assert(RuntimeCanonicalData.IsGuardPath("C:\\stage2\\attempt"));
            Assert(!RuntimeCanonicalData.IsGuardPath("relative"));
            Assert(!RuntimeCanonicalData.IsGuardPath("C:\\stage2\\bad%path"));
            Assert(!RuntimeCanonicalData.IsGuardPath("C:\\stage2\\"));
            Assert(RuntimeCanonicalData.IsGuardPath("C:\\stage 2\\accepted-host.json"));
            Assert(!RuntimeCanonicalData.IsGuardPath("C:\\stage2\\NUL"));
            Assert(!RuntimeCanonicalData.IsGuardPath("C:\\stage2\\COM1.txt"));
            Assert(!RuntimeCanonicalData.IsGuardPath("C:\\stage2\\.hidden"));
            Assert(!RuntimeCanonicalData.IsGuardPath("C:\\stage2\\trailing."));
            Assert(!RuntimeCanonicalData.IsGuardPath("C:\\stage2\\trailing "));
            Assert(RuntimeIdentity.IsLowerHexNonZero(Hex('a', 64), 64));
            Assert(!RuntimeIdentity.IsLowerHexNonZero(Hex('0', 64), 64));
            Assert(RuntimeCanonicalData.GuardPathsDistinctAndNonAncestor(
                "C:\\one\\host.json", "C:\\two\\attempt", "C:\\three\\installed",
                "C:\\four\\virtual"));
            Assert(!RuntimeCanonicalData.GuardPathsDistinctAndNonAncestor(
                "C:\\one", "C:\\one\\attempt", "C:\\three", "C:\\four"));
        }

        private static void ParserCases()
        {
            string publicJson = PublicJson(RuntimeCanonicalData.BuildPinned);
            string privateJson = PrivateJson();
            RuntimeGateFacts facts;
            Assert(RuntimeCanonicalData.TryParseProductionFacts(Ascii(publicJson),
                Ascii(privateJson), ParserObjects(), out facts));
            Assert(facts != null);
            RuntimeGate gate = new RuntimeGate();
            RuntimeGateDecision decision = gate.Evaluate(facts);
            Assert(decision.Disposition == RuntimeGateDisposition.PinnedLease);
            RuntimeLeaseUse use;
            Assert(gate.TryConsumeLease(decision.Lease,
                Binding(Hex('a', 64), RuntimeCanonicalData.UiSuccessScenario, 1,
                    RuntimeCanonicalData.ProfileId), out use));

            string unpinnedPublicJson = PublicJson(RuntimeCanonicalData.BuildUnpinned);
            Assert(RuntimeCanonicalData.TryParseProductionFacts(Ascii(unpinnedPublicJson),
                Ascii(privateJson), ParserObjects(), out facts));
            RuntimeGate unpinnedGate = new RuntimeGate();
            RuntimeGateDecision unpinnedDecision = unpinnedGate.Evaluate(facts);
            Assert(unpinnedDecision.Disposition ==
                RuntimeGateDisposition.BuildUnpinnedRefusal);
            RuntimeRefusalUse refusalUse;
            Assert(unpinnedGate.TryConsumeRefusal(unpinnedDecision.Refusal,
                Binding(Hex('a', 64), RuntimeCanonicalData.UiSuccessScenario, 1,
                    RuntimeCanonicalData.ProfileId), out refusalUse));
            Assert(refusalUse != null &&
                refusalUse.ExitCode == RuntimeCanonicalData.ExitBuildUnpinned);

            string[] badPublic = new string[] {
                " " + publicJson,
                publicJson.Substring(0, publicJson.Length - 1),
                publicJson.Replace("\"build_binding\":", "\"extra\":1,\"build_binding\":"),
                publicJson.Replace("build-pinned", "BUILD-PINNED"),
                publicJson.Replace("build-pinned", "build-third"),
                publicJson.Replace("SyntheticLauncherReady.v1.bmp", "Ready.bmp"),
                publicJson.Replace(RuntimeCanonicalData.ReadyBmpSha256, Hex('e', 64)),
                publicJson.Replace("\"approved_artifacts\":", "\"approved_artifact\":"),
                publicJson.Replace("SyntheticLauncherSupervisor.exe", "Supervisor.exe"),
                publicJson.Replace("locked_preflight", "locked-preflight"),
                publicJson.Replace("\"byte_count\":1000", "\"byte_count\":01000"),
                publicJson.Replace(Hex('1', 64), Hex('A', 64)),
                publicJson.Replace("\"schema_version\":1", "\"schema_version\":2"),
                publicJson.Replace(Hex('b', 40), Hex('B', 40)),
                publicJson.Replace(Hex('b', 40), Hex('0', 40)),
                publicJson.Replace(Hex('1', 64), Hex('0', 64))
            };
            for (int index = 0; index < badPublic.Length; index++)
                Assert(!RuntimeCanonicalData.TryParseProductionFacts(Ascii(badPublic[index]),
                    Ascii(privateJson), ParserObjects(), out facts));

            string[] badPrivate = new string[] {
                " " + privateJson,
                privateJson.Substring(0, privateJson.Length - 1),
                privateJson.Replace("ui-success-v1", "scenario-drift"),
                privateJson.Replace("locked_preflight", "locked-preflight"),
                privateJson.Replace("accepted-host.json", "bad%path"),
                privateJson.Replace("\"schema_version\":1", "\"schema_version\":2"),
                privateJson.Replace(Hex('b', 40), Hex('B', 40))
            };
            for (int index = 0; index < badPrivate.Length; index++)
                Assert(!RuntimeCanonicalData.TryParseProductionFacts(Ascii(publicJson),
                    Ascii(badPrivate[index]), ParserObjects(), out facts));
            Assert(!RuntimeCanonicalData.TryParseProductionFacts(null, Ascii(privateJson),
                ParserObjects(), out facts));
            Assert(!RuntimeCanonicalData.TryParseProductionFacts(Ascii(publicJson), null,
                ParserObjects(), out facts));
            Assert(!RuntimeCanonicalData.TryParseProductionFacts(Ascii(publicJson),
                Ascii(privateJson), null, out facts));
        }

        private static void UnpinnedRefusalCases()
        {
            RuntimeGate sparseGate = new RuntimeGate();
            RuntimeGateDecision sparse = sparseGate.Evaluate(SparseUnpinnedFacts());
            Assert(sparse.Disposition == RuntimeGateDisposition.BuildUnpinnedRefusal);
            Assert(sparse.Refusal != null && sparse.Lease == null);

            RuntimeGate gate = new RuntimeGate();
            RuntimeGateDecision decision = gate.Evaluate(Facts(RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            Assert(decision.Disposition == RuntimeGateDisposition.BuildUnpinnedRefusal);
            Assert(decision.Failure == null);
            Assert(decision.Refusal != null);
            Assert(decision.Lease == null);
            RuntimeRefusalUse use;
            Assert(gate.TryConsumeRefusal(decision.Refusal,
                GoodBinding(RuntimeCanonicalData.UiSuccessScenario), out use));
            Assert(use != null && use.ExitCode == RuntimeCanonicalData.ExitBuildUnpinned);
            Assert(use.Generation == 7);
            RuntimeRefusalUse replay;
            Assert(!gate.TryConsumeRefusal(decision.Refusal,
                GoodBinding(RuntimeCanonicalData.UiSuccessScenario), out replay));
            Assert(replay == null);
            Assert(gate.Evaluate(Facts(RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0)).Disposition ==
                RuntimeGateDisposition.Rejected);

            RuntimeGate wrongOwnerGate = new RuntimeGate();
            RuntimeGateDecision wrongOwner = wrongOwnerGate.Evaluate(Facts(
                RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            RuntimeRefusalUse rejected;
            Assert(!wrongOwnerGate.TryConsumeRefusal(wrongOwner.Refusal,
                Binding(Hex('c', 64), RuntimeCanonicalData.UiSuccessScenario, 7,
                    RuntimeCanonicalData.ProfileId), out rejected));
            Assert(!wrongOwnerGate.TryConsumeRefusal(wrongOwner.Refusal,
                GoodBinding(RuntimeCanonicalData.UiSuccessScenario), out rejected));

            RuntimeGate staleGate = new RuntimeGate();
            RuntimeGateDecision stale = staleGate.Evaluate(Facts(RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            Assert(!staleGate.TryConsumeRefusal(stale.Refusal,
                Binding(Hex('a', 64), RuntimeCanonicalData.UiSuccessScenario, 6,
                    RuntimeCanonicalData.ProfileId), out rejected));

            RuntimeGate scenarioGate = new RuntimeGate();
            RuntimeGateDecision scenario = scenarioGate.Evaluate(Facts(
                RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            Assert(!scenarioGate.TryConsumeRefusal(scenario.Refusal,
                GoodBinding(RuntimeCanonicalData.TreeTimeoutScenario), out rejected));

            RuntimeGate profileGate = new RuntimeGate();
            RuntimeGateDecision profile = profileGate.Evaluate(Facts(
                RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            Assert(!profileGate.TryConsumeRefusal(profile.Refusal,
                Binding(Hex('a', 64), RuntimeCanonicalData.UiSuccessScenario, 7,
                    "profile-drift"), out rejected));

            RuntimeGate transferSource = new RuntimeGate();
            RuntimeGateDecision transfer = transferSource.Evaluate(Facts(
                RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            RuntimeGate transferTarget = new RuntimeGate();
            Assert(!transferTarget.TryConsumeRefusal(transfer.Refusal,
                GoodBinding(RuntimeCanonicalData.UiSuccessScenario), out rejected));
            Assert(!transferSource.TryConsumeRefusal(transfer.Refusal,
                GoodBinding(RuntimeCanonicalData.UiSuccessScenario), out rejected));
        }

        private static void PinnedLeaseCases()
        {
            RuntimeGate gate = new RuntimeGate();
            RuntimeGateDecision decision = gate.Evaluate(Facts(RuntimeCanonicalData.BuildPinned,
                RuntimeCanonicalData.TreeTimeoutScenario, 0));
            Assert(decision.Disposition == RuntimeGateDisposition.PinnedLease);
            Assert(decision.Failure == null);
            Assert(decision.Refusal == null);
            Assert(decision.Lease != null);
            RuntimeLeaseUse use;
            Assert(gate.TryConsumeLease(decision.Lease,
                GoodBinding(RuntimeCanonicalData.TreeTimeoutScenario), out use));
            Assert(use != null && use.Generation == 7);
            Assert(String.Equals(use.OwnerBinding, Hex('a', 64), StringComparison.Ordinal));
            Assert(String.Equals(use.ScenarioId, RuntimeCanonicalData.TreeTimeoutScenario,
                StringComparison.Ordinal));
            Assert(String.Equals(use.ProfileId, RuntimeCanonicalData.ProfileId,
                StringComparison.Ordinal));
            RuntimeLeaseUse replay;
            Assert(!gate.TryConsumeLease(decision.Lease,
                GoodBinding(RuntimeCanonicalData.TreeTimeoutScenario), out replay));
            Assert(replay == null);

            RuntimeGate staleGate = new RuntimeGate();
            RuntimeGateDecision stale = staleGate.Evaluate(Facts(RuntimeCanonicalData.BuildPinned,
                RuntimeCanonicalData.TreeTimeoutScenario, 0));
            Assert(!staleGate.TryConsumeLease(stale.Lease,
                Binding(Hex('a', 64), RuntimeCanonicalData.TreeTimeoutScenario, 8,
                    RuntimeCanonicalData.ProfileId), out replay));
            Assert(!staleGate.TryConsumeLease(stale.Lease,
                GoodBinding(RuntimeCanonicalData.TreeTimeoutScenario), out replay));

            RuntimeGate transferSource = new RuntimeGate();
            RuntimeGateDecision transfer = transferSource.Evaluate(Facts(
                RuntimeCanonicalData.BuildPinned,
                RuntimeCanonicalData.LockedRefusalScenario, 0));
            RuntimeGate transferTarget = new RuntimeGate();
            Assert(!transferTarget.TryConsumeLease(transfer.Lease,
                GoodBinding(RuntimeCanonicalData.LockedRefusalScenario), out replay));
            Assert(!transferSource.TryConsumeLease(transfer.Lease,
                GoodBinding(RuntimeCanonicalData.LockedRefusalScenario), out replay));
        }

        private static void LeaseBindingMismatchCases()
        {
            RuntimeLeaseUse rejected;
            RuntimeGate ownerGate = new RuntimeGate();
            RuntimeGateDecision owner = ownerGate.Evaluate(Facts(RuntimeCanonicalData.BuildPinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            Assert(!ownerGate.TryConsumeLease(owner.Lease,
                Binding(Hex('c', 64), RuntimeCanonicalData.UiSuccessScenario, 7,
                    RuntimeCanonicalData.ProfileId), out rejected));

            RuntimeGate scenarioGate = new RuntimeGate();
            RuntimeGateDecision scenario = scenarioGate.Evaluate(Facts(
                RuntimeCanonicalData.BuildPinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            Assert(!scenarioGate.TryConsumeLease(scenario.Lease,
                GoodBinding(RuntimeCanonicalData.TreeTimeoutScenario), out rejected));

            RuntimeGate profileGate = new RuntimeGate();
            RuntimeGateDecision profile = profileGate.Evaluate(Facts(
                RuntimeCanonicalData.BuildPinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            Assert(!profileGate.TryConsumeLease(profile.Lease,
                Binding(Hex('a', 64), RuntimeCanonicalData.UiSuccessScenario, 7,
                    "profile-drift"), out rejected));

            int contentionState = 0;
            Assert(System.Threading.Interlocked.CompareExchange(ref contentionState, 1, 0) == 0);
            Assert(System.Threading.Interlocked.CompareExchange(ref contentionState, 1, 0) == 1);
        }

        private static void ConcurrentConsumptionCases()
        {
            RuntimeGate refusalGate = new RuntimeGate();
            RuntimeGateDecision refusalDecision = refusalGate.Evaluate(Facts(
                RuntimeCanonicalData.BuildUnpinned,
                RuntimeCanonicalData.UiSuccessScenario, 0));
            using (System.Threading.ManualResetEvent start =
                    new System.Threading.ManualResetEvent(false))
            {
                ConcurrentRefusalAttempt first = new ConcurrentRefusalAttempt();
                first.Gate = refusalGate; first.Refusal = refusalDecision.Refusal;
                first.Binding = GoodBinding(RuntimeCanonicalData.UiSuccessScenario);
                first.Start = start;
                ConcurrentRefusalAttempt second = new ConcurrentRefusalAttempt();
                second.Gate = refusalGate; second.Refusal = refusalDecision.Refusal;
                second.Binding = GoodBinding(RuntimeCanonicalData.UiSuccessScenario);
                second.Start = start;
                System.Threading.Thread firstThread = new System.Threading.Thread(first.Run);
                System.Threading.Thread secondThread = new System.Threading.Thread(second.Run);
                firstThread.Start(); secondThread.Start(); start.Set();
                firstThread.Join(); secondThread.Join();
                Assert(first.Success + second.Success == 1);
            }

            RuntimeGate leaseGate = new RuntimeGate();
            RuntimeGateDecision leaseDecision = leaseGate.Evaluate(Facts(
                RuntimeCanonicalData.BuildPinned,
                RuntimeCanonicalData.TreeTimeoutScenario, 0));
            using (System.Threading.ManualResetEvent start =
                    new System.Threading.ManualResetEvent(false))
            {
                ConcurrentLeaseAttempt first = new ConcurrentLeaseAttempt();
                first.Gate = leaseGate; first.Lease = leaseDecision.Lease;
                first.Binding = GoodBinding(RuntimeCanonicalData.TreeTimeoutScenario);
                first.Start = start;
                ConcurrentLeaseAttempt second = new ConcurrentLeaseAttempt();
                second.Gate = leaseGate; second.Lease = leaseDecision.Lease;
                second.Binding = GoodBinding(RuntimeCanonicalData.TreeTimeoutScenario);
                second.Start = start;
                System.Threading.Thread firstThread = new System.Threading.Thread(first.Run);
                System.Threading.Thread secondThread = new System.Threading.Thread(second.Run);
                firstThread.Start(); secondThread.Start(); start.Set();
                firstThread.Join(); secondThread.Join();
                Assert(first.Success + second.Success == 1);
            }
        }

        private static void BindingFailureCases()
        {
            for (int mutation = 1; mutation <= 37; mutation++)
            {
                RuntimeGate gate = new RuntimeGate();
                RuntimeGateDecision decision = gate.Evaluate(Facts(
                    RuntimeCanonicalData.BuildPinned,
                    RuntimeCanonicalData.UiSuccessScenario, mutation));
                Assert(decision.Disposition == RuntimeGateDisposition.Rejected);
                Assert(decision.Failure != null);
                Assert(decision.Refusal == null && decision.Lease == null);
            }
            RuntimeGate invalidScenario = new RuntimeGate();
            Assert(invalidScenario.Evaluate(Facts(RuntimeCanonicalData.BuildPinned,
                "scenario-drift", 0)).Disposition == RuntimeGateDisposition.Rejected);
            RuntimeGate missing = new RuntimeGate();
            Assert(missing.Evaluate(null).Disposition == RuntimeGateDisposition.Rejected);
            RuntimeGate missingPublic = new RuntimeGate();
            Assert(missingPublic.Evaluate(new RuntimeGateFacts(null, null, null)).Disposition ==
                RuntimeGateDisposition.Rejected);
        }

        private static void IdentityImmutabilityCase()
        {
            RuntimeIdentity[] source = new RuntimeIdentity[
                RuntimeCanonicalData.RequiredIdentityRoleCount];
            for (int index = 0; index < source.Length; index++)
                source[index] = Identity(RuntimeCanonicalData.IdentityRoleAt(index), index);
            RuntimeIdentitySet copy = new RuntimeIdentitySet(source);
            source[0] = Identity("role-drift", 0);
            Assert(copy.IsCanonicalRoleSet());
            Assert(String.Equals(copy.At(0).Role, RuntimeCanonicalData.IdentityRoleAt(0),
                StringComparison.Ordinal));
            Assert(copy.At(-1) == null && copy.At(copy.Count) == null);
        }

        private static ScriptedScenarioPort PortFor(RuntimeScenarioRole role, int failAt,
            int throwAt, int cleanupMode)
        {
            if (role == RuntimeScenarioRole.Supervisor)
                return new ScriptedSupervisorPort(role, failAt, throwAt, cleanupMode);
            if (role == RuntimeScenarioRole.Controller)
                return new ScriptedControllerPort(role, failAt, throwAt, cleanupMode);
            if (role == RuntimeScenarioRole.LockedPreflight)
                return new ScriptedLockedPort(role, failAt, throwAt, cleanupMode);
            if (role == RuntimeScenarioRole.TimeoutRoot)
                return new ScriptedTimeoutRootPort(role, failAt, throwAt, cleanupMode);
            if (role == RuntimeScenarioRole.TimeoutChild)
                return new ScriptedTimeoutChildPort(role, failAt, throwAt, cleanupMode);
            return null;
        }

        private static void AssertExactStages(RuntimeScenarioPlan plan,
            RuntimeScenarioStage[] expected)
        {
            Assert(plan != null);
            Assert(plan.StageCount == expected.Length);
            Assert(plan.StageAt(-1) == RuntimeScenarioStage.None);
            Assert(plan.StageAt(plan.StageCount) == RuntimeScenarioStage.None);
            for (int index = 0; index < expected.Length; index++)
                Assert(plan.StageAt(index) == expected[index]);
        }

        private static RuntimeScenarioPlan Plan(string scenarioId, RuntimeScenarioRole role)
        {
            RuntimeScenarioPlan plan;
            Assert(RuntimeScenarioPlan.TryCreate(scenarioId, role, out plan));
            Assert(plan != null && plan.Role == role);
            Assert(String.Equals(plan.ScenarioId, scenarioId, StringComparison.Ordinal));
            return plan;
        }

        private static void RouteMappingAndStageCases()
        {
            RuntimeScenarioStage[] supervisor = {
                RuntimeScenarioStage.BindInputs, RuntimeScenarioStage.OutputsAbsent,
                RuntimeScenarioStage.AttemptInventory,
                RuntimeScenarioStage.PrelaunchTopology,
                RuntimeScenarioStage.SupervisorJobConfigured,
                RuntimeScenarioStage.SupervisorCreate, RuntimeScenarioStage.SupervisorAssign,
                RuntimeScenarioStage.SupervisorMembership,
                RuntimeScenarioStage.WorkerTopology, RuntimeScenarioStage.SupervisorResume,
                RuntimeScenarioStage.SupervisorWait, RuntimeScenarioStage.OuterJobEmpty,
                RuntimeScenarioStage.SupervisorPostTopology,
                RuntimeScenarioStage.EvidenceValidate, RuntimeScenarioStage.ReportPublish,
                RuntimeScenarioStage.EvidenceDeleteInventory
            };
            RuntimeScenarioStage[] uiController = {
                RuntimeScenarioStage.StreamsAbsent, RuntimeScenarioStage.BindInputs,
                RuntimeScenarioStage.OutputsAbsent, RuntimeScenarioStage.SessionDesktop,
                RuntimeScenarioStage.ControllerTopology, RuntimeScenarioStage.TokenAcquire,
                RuntimeScenarioStage.QuotaEnabled,
                RuntimeScenarioStage.RegistryDenied, RuntimeScenarioStage.GuardBaseline,
                RuntimeScenarioStage.TokenRelationship, RuntimeScenarioStage.Environment,
                RuntimeScenarioStage.TargetCreate,
                RuntimeScenarioStage.InnerJobConfigured, RuntimeScenarioStage.InnerAssign,
                RuntimeScenarioStage.InnerMembership, RuntimeScenarioStage.TargetResume,
                RuntimeScenarioStage.UiWindow, RuntimeScenarioStage.UiProtocolReady,
                RuntimeScenarioStage.UiGeometry, RuntimeScenarioStage.UiReadyCaptureOne,
                RuntimeScenarioStage.UiReadyCaptureTwo, RuntimeScenarioStage.UiInput,
                RuntimeScenarioStage.UiCompleteState,
                RuntimeScenarioStage.UiCompleteCaptureOne,
                RuntimeScenarioStage.UiCompleteCaptureTwo, RuntimeScenarioStage.UiClose,
                RuntimeScenarioStage.InnerCleanup,
                RuntimeScenarioStage.SessionDesktopRecheck,
                RuntimeScenarioStage.QuotaRestored, RuntimeScenarioStage.TokenRestored,
                RuntimeScenarioStage.GuardsStable, RuntimeScenarioStage.RegistryStable,
                RuntimeScenarioStage.RebindInputs, RuntimeScenarioStage.WorkerPublish
            };
            RuntimeScenarioStage[] timeoutController = {
                RuntimeScenarioStage.StreamsAbsent, RuntimeScenarioStage.BindInputs,
                RuntimeScenarioStage.OutputsAbsent, RuntimeScenarioStage.SessionDesktop,
                RuntimeScenarioStage.ControllerTopology, RuntimeScenarioStage.TokenAcquire,
                RuntimeScenarioStage.QuotaEnabled,
                RuntimeScenarioStage.RegistryDenied, RuntimeScenarioStage.GuardBaseline,
                RuntimeScenarioStage.TokenRelationship, RuntimeScenarioStage.Environment,
                RuntimeScenarioStage.TargetCreate,
                RuntimeScenarioStage.InnerJobConfigured, RuntimeScenarioStage.InnerAssign,
                RuntimeScenarioStage.InnerMembership, RuntimeScenarioStage.TargetResume,
                RuntimeScenarioStage.TimeoutRootChildTopology,
                RuntimeScenarioStage.TimeoutObserved, RuntimeScenarioStage.InnerCleanup,
                RuntimeScenarioStage.SessionDesktopRecheck,
                RuntimeScenarioStage.QuotaRestored, RuntimeScenarioStage.TokenRestored,
                RuntimeScenarioStage.GuardsStable, RuntimeScenarioStage.RegistryStable,
                RuntimeScenarioStage.RebindInputs, RuntimeScenarioStage.WorkerPublish
            };
            RuntimeScenarioStage[] locked = {
                RuntimeScenarioStage.StreamsAbsent, RuntimeScenarioStage.BindInputs,
                RuntimeScenarioStage.OutputsAbsent,
                RuntimeScenarioStage.SessionDesktop, RuntimeScenarioStage.WorkerTopology,
                RuntimeScenarioStage.LockedRefusal, RuntimeScenarioStage.LockedNoArtifacts,
                RuntimeScenarioStage.RebindInputs, RuntimeScenarioStage.WorkerPublish
            };
            RuntimeScenarioStage[] timeoutRoot = {
                RuntimeScenarioStage.StreamsAbsent, RuntimeScenarioStage.BindInputs,
                RuntimeScenarioStage.TimeoutRootCreate,
                RuntimeScenarioStage.TimeoutRootWait
            };
            RuntimeScenarioStage[] timeoutChild = {
                RuntimeScenarioStage.StreamsAbsent, RuntimeScenarioStage.TimeoutChildWait
            };

            RuntimeScenarioPlan uiSupervisor = Plan(RuntimeCanonicalData.UiSuccessScenario,
                RuntimeScenarioRole.Supervisor);
            RuntimeScenarioPlan timeoutSupervisor = Plan(
                RuntimeCanonicalData.TreeTimeoutScenario, RuntimeScenarioRole.Supervisor);
            RuntimeScenarioPlan lockedSupervisor = Plan(
                RuntimeCanonicalData.LockedRefusalScenario, RuntimeScenarioRole.Supervisor);
            AssertExactStages(uiSupervisor, supervisor);
            AssertExactStages(timeoutSupervisor, supervisor);
            AssertExactStages(lockedSupervisor, supervisor);
            AssertExactStages(Plan(RuntimeCanonicalData.UiSuccessScenario,
                RuntimeScenarioRole.Controller), uiController);
            RuntimeScenarioPlan timeoutControllerPlan = Plan(
                RuntimeCanonicalData.TreeTimeoutScenario, RuntimeScenarioRole.Controller);
            AssertExactStages(timeoutControllerPlan, timeoutController);
            Assert(timeoutControllerPlan.SuccessExitCode == RuntimeCanonicalData.ExitTreeTimeout);
            RuntimeScenarioPlan lockedPlan = Plan(RuntimeCanonicalData.LockedRefusalScenario,
                RuntimeScenarioRole.LockedPreflight);
            AssertExactStages(lockedPlan, locked);
            Assert(lockedPlan.SuccessExitCode == RuntimeCanonicalData.ExitLockedRefusal);
            AssertExactStages(Plan(RuntimeCanonicalData.TreeTimeoutScenario,
                RuntimeScenarioRole.TimeoutRoot), timeoutRoot);
            AssertExactStages(Plan(RuntimeCanonicalData.TreeTimeoutScenario,
                RuntimeScenarioRole.TimeoutChild), timeoutChild);
            Assert(String.Equals(uiSupervisor.WorkerImage,
                RuntimeCanonicalData.ControllerImage, StringComparison.Ordinal));
            Assert(String.Equals(uiSupervisor.TargetImage,
                RuntimeCanonicalData.UiFixtureImage, StringComparison.Ordinal));
            Assert(String.Equals(timeoutSupervisor.TargetImage,
                RuntimeCanonicalData.TimeoutRootImage, StringComparison.Ordinal));
            Assert(String.Equals(lockedSupervisor.WorkerImage,
                RuntimeCanonicalData.LockedPreflightImage, StringComparison.Ordinal));
            Assert(lockedSupervisor.TargetImage == null);
            Assert(uiSupervisor.WorkerExitCode == RuntimeCanonicalData.ExitAccepted);
            Assert(uiSupervisor.OuterActiveProcessLimit == 2 &&
                uiSupervisor.OuterJobMemoryLimit == 536870912UL);
            Assert(timeoutSupervisor.WorkerExitCode == RuntimeCanonicalData.ExitTreeTimeout);
            Assert(timeoutSupervisor.SuccessExitCode == RuntimeCanonicalData.ExitTreeTimeout);
            Assert(timeoutSupervisor.OuterActiveProcessLimit == 3 &&
                timeoutSupervisor.OuterJobMemoryLimit == 805306368UL);
            Assert(lockedSupervisor.WorkerExitCode == RuntimeCanonicalData.ExitLockedRefusal);
            Assert(lockedSupervisor.SuccessExitCode == RuntimeCanonicalData.ExitLockedRefusal);
            Assert(lockedSupervisor.OuterActiveProcessLimit == 1 &&
                lockedSupervisor.OuterJobMemoryLimit == 268435456UL);

            RuntimeScenarioPlan rejected;
            Assert(!RuntimeScenarioPlan.TryCreate("scenario-drift",
                RuntimeScenarioRole.Supervisor, out rejected));
            Assert(!RuntimeScenarioPlan.TryCreate(RuntimeCanonicalData.UiSuccessScenario,
                RuntimeScenarioRole.LockedPreflight, out rejected));
            Assert(!RuntimeScenarioPlan.TryCreate(RuntimeCanonicalData.LockedRefusalScenario,
                RuntimeScenarioRole.Controller, out rejected));
            Assert(!RuntimeScenarioPlan.TryCreate(RuntimeCanonicalData.UiSuccessScenario,
                RuntimeScenarioRole.TimeoutRoot, out rejected));
            Assert(!RuntimeScenarioPlan.TryCreate(RuntimeCanonicalData.TreeTimeoutScenario,
                RuntimeScenarioRole.None, out rejected));
        }

        private static void AssertEngineForEveryStage(string scenarioId,
            RuntimeScenarioRole role)
        {
            RuntimeScenarioPlan plan = Plan(scenarioId, role);
            ScriptedScenarioPort acceptedPort = PortFor(role, -1, -1, 0);
            RuntimeScenarioExecutionResult accepted = RuntimeScenarioEngine.Run(plan,
                acceptedPort);
            Assert(accepted.Accepted);
            Assert(accepted.ExitCode == plan.SuccessExitCode);
            Assert(accepted.StoppedStage == RuntimeScenarioStage.None);
            Assert(accepted.CompletedStageCount == plan.StageCount);
            Assert(accepted.CleanupAttempted && accepted.CleanupSucceeded);
            Assert(acceptedPort.CallCount == plan.StageCount);
            Assert(acceptedPort.CleanupCount == 1);
            for (int index = 0; index < plan.StageCount; index++)
                Assert(acceptedPort.CallAt(index) == plan.StageAt(index));

            for (int index = 0; index < plan.StageCount; index++)
            {
                ScriptedScenarioPort failedPort = PortFor(role, index, -1, 0);
                RuntimeScenarioExecutionResult failed = RuntimeScenarioEngine.Run(plan,
                    failedPort);
                Assert(!failed.Accepted);
                Assert(failed.ExitCode == RuntimeCanonicalData.ExitBindingRejection);
                Assert(failed.StoppedStage == plan.StageAt(index));
                Assert(failed.CompletedStageCount == index);
                Assert(failedPort.CallCount == index + 1);
                Assert(failedPort.CleanupCount == 1);
                for (int call = 0; call <= index; call++)
                    Assert(failedPort.CallAt(call) == plan.StageAt(call));

                ScriptedScenarioPort thrownPort = PortFor(role, -1, index, 0);
                RuntimeScenarioExecutionResult thrown = RuntimeScenarioEngine.Run(plan,
                    thrownPort);
                Assert(!thrown.Accepted);
                Assert(thrown.ExitCode == RuntimeCanonicalData.ExitNativeCapabilityFailure);
                Assert(thrown.StoppedStage == plan.StageAt(index));
                Assert(thrown.CompletedStageCount == index);
                Assert(thrownPort.CallCount == index + 1);
                Assert(thrownPort.CleanupCount == 1);
            }
        }

        private static void ScenarioEngineCases()
        {
            AssertEngineForEveryStage(RuntimeCanonicalData.UiSuccessScenario,
                RuntimeScenarioRole.Supervisor);
            AssertEngineForEveryStage(RuntimeCanonicalData.TreeTimeoutScenario,
                RuntimeScenarioRole.Supervisor);
            AssertEngineForEveryStage(RuntimeCanonicalData.LockedRefusalScenario,
                RuntimeScenarioRole.Supervisor);
            AssertEngineForEveryStage(RuntimeCanonicalData.UiSuccessScenario,
                RuntimeScenarioRole.Controller);
            AssertEngineForEveryStage(RuntimeCanonicalData.LockedRefusalScenario,
                RuntimeScenarioRole.LockedPreflight);
            AssertEngineForEveryStage(RuntimeCanonicalData.TreeTimeoutScenario,
                RuntimeScenarioRole.TimeoutRoot);
            AssertEngineForEveryStage(RuntimeCanonicalData.TreeTimeoutScenario,
                RuntimeScenarioRole.TimeoutChild);
            AssertEngineForEveryStage(RuntimeCanonicalData.TreeTimeoutScenario,
                RuntimeScenarioRole.Controller);

            RuntimeScenarioPlan supervisorPlan = Plan(RuntimeCanonicalData.UiSuccessScenario,
                RuntimeScenarioRole.Supervisor);
            ScriptedScenarioPort wrongRole = new ScriptedSupervisorPort(
                RuntimeScenarioRole.Controller, -1, -1, 0);
            RuntimeScenarioExecutionResult wrong = RuntimeScenarioEngine.Run(supervisorPlan,
                wrongRole);
            Assert(!wrong.Accepted && wrong.ExitCode ==
                RuntimeCanonicalData.ExitBindingRejection);
            Assert(!wrong.CleanupAttempted && wrongRole.CallCount == 0 &&
                wrongRole.CleanupCount == 0);
            ScriptedScenarioPort wrongInterface = new ScriptedControllerPort(
                RuntimeScenarioRole.Supervisor, -1, -1, 0);
            wrong = RuntimeScenarioEngine.Run(supervisorPlan, wrongInterface);
            Assert(!wrong.Accepted && !wrong.CleanupAttempted);
            Assert(RuntimeScenarioEngine.Run(null, wrongRole).ExitCode ==
                RuntimeCanonicalData.ExitBindingRejection);
            Assert(RuntimeScenarioEngine.Run(supervisorPlan, null).ExitCode ==
                RuntimeCanonicalData.ExitBindingRejection);

            ScriptedScenarioPort cleanupFailure = PortFor(RuntimeScenarioRole.Supervisor,
                2, -1, 1);
            RuntimeScenarioExecutionResult cleanupOverride = RuntimeScenarioEngine.Run(
                supervisorPlan, cleanupFailure);
            Assert(!cleanupOverride.Accepted);
            Assert(cleanupOverride.ExitCode == RuntimeCanonicalData.ExitCleanupFailure);
            Assert(cleanupOverride.StoppedStage == supervisorPlan.StageAt(2));
            Assert(cleanupFailure.CleanupCount == 1);
            ScriptedScenarioPort cleanupException = PortFor(RuntimeScenarioRole.Supervisor,
                -1, -1, 2);
            cleanupOverride = RuntimeScenarioEngine.Run(supervisorPlan, cleanupException);
            Assert(!cleanupOverride.Accepted);
            Assert(cleanupOverride.ExitCode == RuntimeCanonicalData.ExitCleanupFailure);
            Assert(cleanupOverride.StoppedStage == RuntimeScenarioStage.None);
            Assert(cleanupException.CleanupCount == 1);
        }

        private static void DeadlineMathCases()
        {
            long deadline;
            Assert(RuntimeDeadlineMath.TryCreateDeadline(1000, 10000, 5000,
                out deadline));
            Assert(deadline == 51000);
            Assert(RuntimeDeadlineMath.RemainingMilliseconds(1000, deadline,
                41000, 10000) == 1000);
            Assert(RuntimeDeadlineMath.RemainingMilliseconds(1000, deadline,
                50990, 10000) == 1);
            Assert(RuntimeDeadlineMath.RemainingMilliseconds(1000, deadline,
                deadline - 1, 10000) == 0);
            Assert(RuntimeDeadlineMath.RemainingMilliseconds(1000, deadline,
                deadline, 10000) == 0);
            Assert(RuntimeDeadlineMath.RemainingMilliseconds(1000, deadline,
                999, 10000) == 0);
            Assert(!RuntimeDeadlineMath.TryCreateDeadline(Int64.MaxValue - 1,
                10000, 1, out deadline));
            Assert(!RuntimeDeadlineMath.TryCreateDeadline(0, Int64.MaxValue,
                UInt32.MaxValue, out deadline));
            Assert(!RuntimeDeadlineMath.CanProbe(1000, 51000, 51000, 10000));
            Assert(!RuntimeDeadlineMath.CanProbe(1000, 51000, 51001, 10000));
            Assert(!RuntimeDeadlineMath.CanProbe(1000, 51000, 50999, 10000));
            Assert(RuntimeDeadlineMath.CanProbe(1000, 51000, 50990, 10000));
            Assert(!RuntimeDeadlineMath.CanProbe(1000, 51000, 999, 10000));
            Assert(!RuntimeDeadlineMath.CanProbe(1000, 1000, 1000, 10000));
            Assert(!RuntimeDeadlineMath.CanProbe(1000, 51000, 2000, 0));
        }

        private static int ReadInt32(byte[] value, int offset)
        {
            return value[offset] | (value[offset + 1] << 8) |
                (value[offset + 2] << 16) | (value[offset + 3] << 24);
        }

        private static void CanonicalBmpCases()
        {
            Assert(RuntimeCanonicalData.Sha256Hex(new byte[0]) ==
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
            Assert(RuntimeCanonicalData.Sha256Hex(Ascii("abc")) ==
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
            byte[] ready = RuntimeCanonicalData.BuildExpectedCanonicalBmp(true);
            byte[] complete = RuntimeCanonicalData.BuildExpectedCanonicalBmp(false);
            Assert(RuntimeCanonicalData.CanonicalBmpByteCount == 230454);
            Assert(RuntimeCanonicalData.ReadyBmpName == "SyntheticLauncherReady.v1.bmp");
            Assert(RuntimeCanonicalData.CompleteBmpName == "SyntheticLauncherComplete.v1.bmp");
            Assert(RuntimeCanonicalData.IsApprovedCanonicalBmp(ready, true));
            Assert(RuntimeCanonicalData.IsApprovedCanonicalBmp(complete, false));
            Assert(!RuntimeCanonicalData.IsApprovedCanonicalBmp(ready, false));
            Assert(!RuntimeCanonicalData.IsApprovedCanonicalBmp(complete, true));
            Assert(ready.Length == 230454 && ready[0] == (byte)'B' && ready[1] == (byte)'M');
            Assert(ReadInt32(ready, 2) == 230454 && ReadInt32(ready, 10) == 54);
            Assert(ReadInt32(ready, 14) == 40 && ReadInt32(ready, 18) == 320);
            Assert(ReadInt32(ready, 22) == 240 && ready[26] == 1 && ready[27] == 0);
            Assert(ready[28] == 24 && ready[29] == 0 && ReadInt32(ready, 30) == 0);
            Assert(ReadInt32(ready, 34) == 230400 && ReadInt32(ready, 38) == 0 &&
                ReadInt32(ready, 42) == 0 && ReadInt32(ready, 46) == 0 &&
                ReadInt32(ready, 50) == 0);
            int[] readyBgr = { 32, 32, 192, 192, 64, 32, 64, 160, 32, 32, 24, 16 };
            for (int band = 0; band < 4; band++)
            {
                int offset = 54 + band * 80 * 3;
                Assert(ready[offset] == readyBgr[band * 3] &&
                    ready[offset + 1] == readyBgr[band * 3 + 1] &&
                    ready[offset + 2] == readyBgr[band * 3 + 2]);
            }
            byte[] wrong = new byte[320 * 240 * 4 - 1];
            byte[] ignored;
            Assert(!RuntimeCanonicalData.TryEncodeCanonicalBmp(wrong, out ignored));
            byte[] oriented = new byte[320 * 240 * 4];
            oriented[0] = 1; oriented[1] = 2; oriented[2] = 3;
            int last = (239 * 320) * 4;
            oriented[last] = 4; oriented[last + 1] = 5; oriented[last + 2] = 6;
            Assert(RuntimeCanonicalData.TryEncodeCanonicalBmp(oriented, out ignored));
            Assert(ignored[54] == 4 && ignored[55] == 5 && ignored[56] == 6);
            int finalRow = 54 + 239 * 960;
            Assert(ignored[finalRow] == 1 && ignored[finalRow + 1] == 2 &&
                ignored[finalRow + 2] == 3);
            Array.Clear(oriented, 0, oriented.Length);
            Array.Clear(ignored, 0, ignored.Length);
            byte original = ready[54];
            ready[54] ^= 1;
            Assert(!RuntimeCanonicalData.IsApprovedCanonicalBmp(ready, true));
            ready[54] = original;
            Assert(RuntimeCanonicalData.IsApprovedCanonicalBmp(ready, true));
            Array.Clear(ready, 0, ready.Length);
            Array.Clear(complete, 0, complete.Length);
        }

        private static int Main()
        {
            CanonicalDataCases();
            ParserCases();
            IdentityImmutabilityCase();
            UnpinnedRefusalCases();
            PinnedLeaseCases();
            LeaseBindingMismatchCases();
            ConcurrentConsumptionCases();
            BindingFailureCases();
            RouteMappingAndStageCases();
            ScenarioEngineCases();
            DeadlineMathCases();
            CanonicalBmpCases();
            Console.WriteLine("PASS runtime-gate-v1");
            return 0;
        }
    }
}
