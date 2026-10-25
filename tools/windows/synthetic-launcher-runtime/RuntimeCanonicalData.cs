using System;
using System.Globalization;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal static class RuntimeCanonicalData
    {
        internal const string ProfileId = "cm0102-synthetic-launcher-runtime-v1";
        internal const string BuildUnpinned = "build-unpinned";
        internal const string BuildPinned = "build-pinned";

        internal const string UiSuccessScenario = "ui-success-v1";
        internal const string TreeTimeoutScenario = "tree-timeout-v1";
        internal const string LockedRefusalScenario = "locked-refusal-v1";

        internal const string SupervisorImage = "SyntheticLauncherSupervisor.exe";
        internal const string ControllerImage = "SyntheticLauncherController.exe";
        internal const string LockedPreflightImage = "SyntheticLauncherLockedPreflight.exe";
        internal const string TimeoutRootImage = "SyntheticLauncherTimeoutFixture.exe";
        internal const string TimeoutChildImage = "SyntheticLauncherTimeoutChild.exe";
        internal const string UiFixtureImage = "SyntheticLauncherFixture.exe";
        internal const int UiFixtureByteCount = 14336;
        internal const string UiFixtureSha256 =
            "f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6";
        internal const string ReadyBmpName = "SyntheticLauncherReady.v1.bmp";
        internal const string CompleteBmpName = "SyntheticLauncherComplete.v1.bmp";
        internal const int CanonicalBmpByteCount = 230454;
        internal const string ReadyBmpSha256 =
            "4f471fd3bc87f53fef9d7f200eaccb0ebe69a0240a9cf09f79bc2bfec3c51f19";
        internal const string CompleteBmpSha256 =
            "5dac08fba06a53bb0a480fe388907e78147b5c0d042fee53eea2ff81b4ee8bc6";

        internal const int ExitAccepted = 0;
        internal const int ExitBuildUnpinned = 20;
        internal const int ExitLockedRefusal = 21;
        internal const int ExitTreeTimeout = 22;
        internal const int ExitBindingRejection = 30;
        internal const int ExitNativeCapabilityFailure = 31;
        internal const int ExitCleanupFailure = 32;
        internal const int ExitReportFailure = 33;

        internal const int RequiredIdentityRoleCount = 6;

        internal static string IdentityRoleAt(int index)
        {
            switch (index)
            {
                case 0: return "controller";
                case 1: return "locked_preflight";
                case 2: return "supervisor";
                case 3: return "timeout_child";
                case 4: return "timeout_root";
                case 5: return "ui_fixture";
                default: return null;
            }
        }

        internal static bool IsScenario(string value)
        {
            return String.Equals(value, UiSuccessScenario, StringComparison.Ordinal) ||
                String.Equals(value, TreeTimeoutScenario, StringComparison.Ordinal) ||
                String.Equals(value, LockedRefusalScenario, StringComparison.Ordinal);
        }

        internal static string WorkerImageFor(string scenarioId)
        {
            if (String.Equals(scenarioId, LockedRefusalScenario, StringComparison.Ordinal))
                return LockedPreflightImage;
            if (String.Equals(scenarioId, UiSuccessScenario, StringComparison.Ordinal) ||
                    String.Equals(scenarioId, TreeTimeoutScenario, StringComparison.Ordinal))
                return ControllerImage;
            return null;
        }

        internal static string TargetImageFor(string scenarioId)
        {
            if (String.Equals(scenarioId, UiSuccessScenario, StringComparison.Ordinal))
                return UiFixtureImage;
            if (String.Equals(scenarioId, TreeTimeoutScenario, StringComparison.Ordinal))
                return TimeoutRootImage;
            return null;
        }

        internal static bool IsGuardPath(string value)
        {
            if (value == null || value.Length < 3 || value.Length > 260 ||
                    !IsAsciiLetter(value[0]) || value[1] != ':' || value[2] != '\\' ||
                    value[value.Length - 1] == '\\')
                return false;
            int segmentStart = 3;
            for (int index = 3; index <= value.Length; index++)
            {
                if (index == value.Length || value[index] == '\\')
                {
                    if (!ValidGuardSegment(value, segmentStart, index - segmentStart))
                        return false;
                    segmentStart = index + 1;
                }
                else if (value[index] < 0x20 || value[index] > 0x7e ||
                        value[index] == '<' || value[index] == '>' || value[index] == ':' ||
                        value[index] == '%' || value[index] == '"' || value[index] == '/' ||
                        value[index] == '|' || value[index] == '?' || value[index] == '*')
                {
                    return false;
                }
            }
            return true;
        }

        internal static bool GuardPathsDistinctAndNonAncestor(string first, string second,
            string third, string fourth)
        {
            string[] values = { first, second, third, fourth };
            for (int index = 0; index < values.Length; index++)
            {
                if (!IsGuardPath(values[index])) return false;
                for (int other = index + 1; other < values.Length; other++)
                {
                    if (SameOrAncestor(values[index], values[other]) ||
                            SameOrAncestor(values[other], values[index]))
                        return false;
                }
            }
            return true;
        }

        private static bool SameOrAncestor(string possibleAncestor, string value)
        {
            if (possibleAncestor == null || value == null ||
                    value.Length < possibleAncestor.Length ||
                    !value.StartsWith(possibleAncestor, StringComparison.OrdinalIgnoreCase))
                return false;
            return value.Length == possibleAncestor.Length ||
                value[possibleAncestor.Length] == '\\';
        }

        private static bool ValidGuardSegment(string value, int start, int length)
        {
            if (length <= 0 || value[start] == '.' ||
                    value[start + length - 1] == '.' || value[start + length - 1] == ' ')
                return false;
            int baseLength = length;
            for (int index = 0; index < length; index++)
            {
                if (value[start + index] == '.')
                {
                    baseLength = index;
                    break;
                }
            }
            string name = value.Substring(start, baseLength).TrimEnd(' ');
            if (String.Equals(name, "CON", StringComparison.OrdinalIgnoreCase) ||
                    String.Equals(name, "PRN", StringComparison.OrdinalIgnoreCase) ||
                    String.Equals(name, "AUX", StringComparison.OrdinalIgnoreCase) ||
                    String.Equals(name, "NUL", StringComparison.OrdinalIgnoreCase) ||
                    String.Equals(name, "CLOCK$", StringComparison.OrdinalIgnoreCase) ||
                    String.Equals(name, "CONIN$", StringComparison.OrdinalIgnoreCase) ||
                    String.Equals(name, "CONOUT$", StringComparison.OrdinalIgnoreCase))
                return false;
            if (name.Length == 4 && (name.StartsWith("COM", StringComparison.OrdinalIgnoreCase) ||
                    name.StartsWith("LPT", StringComparison.OrdinalIgnoreCase)) &&
                    name[3] >= '1' && name[3] <= '9')
                return false;
            return true;
        }

        private static bool IsAsciiLetter(char value)
        {
            return (value >= 'A' && value <= 'Z') || (value >= 'a' && value <= 'z');
        }

        internal static bool TryParseProductionFacts(byte[] publicBytes, byte[] privateBytes,
            RuntimeObjectFacts observed, out RuntimeGateFacts facts)
        {
            return RuntimeCanonicalParser.TryParse(publicBytes, privateBytes, observed, out facts);
        }

        internal static bool TryEncodeCanonicalBmp(byte[] topDownBgra, out byte[] bmp)
        {
            bmp = null;
            if (topDownBgra == null || topDownBgra.Length != 320 * 240 * 4)
                return false;
            byte[] value = new byte[CanonicalBmpByteCount];
            value[0] = (byte)'B'; value[1] = (byte)'M';
            PutUInt32(value, 2, CanonicalBmpByteCount);
            PutUInt32(value, 10, 54);
            PutUInt32(value, 14, 40);
            PutUInt32(value, 18, 320);
            PutUInt32(value, 22, 240);
            PutUInt16(value, 26, 1);
            PutUInt16(value, 28, 24);
            PutUInt32(value, 34, 320 * 240 * 3);
            int output = 54;
            for (int y = 239; y >= 0; y--)
            {
                int input = y * 320 * 4;
                for (int x = 0; x < 320; x++)
                {
                    value[output++] = topDownBgra[input++];
                    value[output++] = topDownBgra[input++];
                    value[output++] = topDownBgra[input++];
                    input++;
                }
            }
            if (output != value.Length)
            {
                Array.Clear(value, 0, value.Length);
                return false;
            }
            bmp = value;
            return true;
        }

        internal static byte[] BuildExpectedCanonicalBmp(bool ready)
        {
            int[,] colors = ready ? new int[,] {
                { 192, 32, 32 }, { 32, 64, 192 }, { 32, 160, 64 }, { 16, 24, 32 }
            } : new int[,] {
                { 24, 176, 80 }, { 224, 176, 24 }, { 128, 48, 192 }, { 32, 200, 216 }
            };
            byte[] bgra = new byte[320 * 240 * 4];
            for (int y = 0; y < 240; y++)
            {
                for (int x = 0; x < 320; x++)
                {
                    int offset = (y * 320 + x) * 4;
                    int band = x / 80;
                    bgra[offset] = (byte)colors[band, 2];
                    bgra[offset + 1] = (byte)colors[band, 1];
                    bgra[offset + 2] = (byte)colors[band, 0];
                }
            }
            byte[] result;
            bool encoded = TryEncodeCanonicalBmp(bgra, out result);
            Array.Clear(bgra, 0, bgra.Length);
            return encoded ? result : null;
        }

        internal static bool IsApprovedCanonicalBmp(byte[] value, bool ready)
        {
            if (value == null || value.Length != CanonicalBmpByteCount)
                return false;
            string expected = ready ? ReadyBmpSha256 : CompleteBmpSha256;
            return String.Equals(Sha256Hex(value), expected, StringComparison.Ordinal);
        }

        internal static string Sha256Hex(byte[] value)
        {
            if (value == null || value.Length > Int32.MaxValue - 72)
                return null;
            int paddedLength = checked(((value.Length + 9 + 63) / 64) * 64);
            byte[] padded = new byte[paddedLength];
            Buffer.BlockCopy(value, 0, padded, 0, value.Length);
            padded[value.Length] = 0x80;
            ulong bitLength = checked((ulong)value.Length * 8UL);
            for (int index = 0; index < 8; index++)
                padded[padded.Length - 1 - index] = (byte)(bitLength >> (index * 8));
            uint[] constants = {
                0x428a2f98U,0x71374491U,0xb5c0fbcfU,0xe9b5dba5U,0x3956c25bU,0x59f111f1U,
                0x923f82a4U,0xab1c5ed5U,0xd807aa98U,0x12835b01U,0x243185beU,0x550c7dc3U,
                0x72be5d74U,0x80deb1feU,0x9bdc06a7U,0xc19bf174U,0xe49b69c1U,0xefbe4786U,
                0x0fc19dc6U,0x240ca1ccU,0x2de92c6fU,0x4a7484aaU,0x5cb0a9dcU,0x76f988daU,
                0x983e5152U,0xa831c66dU,0xb00327c8U,0xbf597fc7U,0xc6e00bf3U,0xd5a79147U,
                0x06ca6351U,0x14292967U,0x27b70a85U,0x2e1b2138U,0x4d2c6dfcU,0x53380d13U,
                0x650a7354U,0x766a0abbU,0x81c2c92eU,0x92722c85U,0xa2bfe8a1U,0xa81a664bU,
                0xc24b8b70U,0xc76c51a3U,0xd192e819U,0xd6990624U,0xf40e3585U,0x106aa070U,
                0x19a4c116U,0x1e376c08U,0x2748774cU,0x34b0bcb5U,0x391c0cb3U,0x4ed8aa4aU,
                0x5b9cca4fU,0x682e6ff3U,0x748f82eeU,0x78a5636fU,0x84c87814U,0x8cc70208U,
                0x90befffaU,0xa4506cebU,0xbef9a3f7U,0xc67178f2U
            };
            uint[] state = { 0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
                0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U };
            uint[] words = new uint[64];
            unchecked
            {
                for (int block = 0; block < padded.Length; block += 64)
                {
                    for (int index = 0; index < 16; index++)
                    {
                        int offset = block + index * 4;
                        words[index] = ((uint)padded[offset] << 24) |
                            ((uint)padded[offset + 1] << 16) |
                            ((uint)padded[offset + 2] << 8) | padded[offset + 3];
                    }
                    for (int index = 16; index < 64; index++)
                    {
                        uint x = words[index - 15];
                        uint y = words[index - 2];
                        uint first = RotateRight(x, 7) ^ RotateRight(x, 18) ^ (x >> 3);
                        uint second = RotateRight(y, 17) ^ RotateRight(y, 19) ^ (y >> 10);
                        words[index] = words[index - 16] + first + words[index - 7] + second;
                    }
                    uint a = state[0], b = state[1], c = state[2], d = state[3];
                    uint e = state[4], f = state[5], g = state[6], h = state[7];
                    for (int index = 0; index < 64; index++)
                    {
                        uint upper = RotateRight(e, 6) ^ RotateRight(e, 11) ^ RotateRight(e, 25);
                        uint choose = (e & f) ^ ((~e) & g);
                        uint first = h + upper + choose + constants[index] + words[index];
                        uint lower = RotateRight(a, 2) ^ RotateRight(a, 13) ^ RotateRight(a, 22);
                        uint majority = (a & b) ^ (a & c) ^ (b & c);
                        uint second = lower + majority;
                        h = g; g = f; f = e; e = d + first;
                        d = c; c = b; b = a; a = first + second;
                    }
                    state[0] += a; state[1] += b; state[2] += c; state[3] += d;
                    state[4] += e; state[5] += f; state[6] += g; state[7] += h;
                }
            }
            string result = String.Empty;
            for (int index = 0; index < state.Length; index++)
                result += state[index].ToString("x8", CultureInfo.InvariantCulture);
            Array.Clear(padded, 0, padded.Length);
            Array.Clear(words, 0, words.Length);
            Array.Clear(state, 0, state.Length);
            return result;
        }

        private static uint RotateRight(uint value, int count)
        {
            return (value >> count) | (value << (32 - count));
        }

        private static void PutUInt16(byte[] value, int offset, int number)
        {
            value[offset] = (byte)number;
            value[offset + 1] = (byte)(number >> 8);
        }

        private static void PutUInt32(byte[] value, int offset, int number)
        {
            value[offset] = (byte)number;
            value[offset + 1] = (byte)(number >> 8);
            value[offset + 2] = (byte)(number >> 16);
            value[offset + 3] = (byte)(number >> 24);
        }
    }

    internal enum RuntimeScenarioStage
    {
        None = 0,
        BindInputs = 1,
        StreamsAbsent = 2,
        GuardBefore = 3,
        SessionDesktop = 4,
        SupervisorJobConfigured = 5,
        SupervisorCreate = 6,
        SupervisorAssign = 7,
        SupervisorMembership = 8,
        SupervisorResume = 9,
        WorkerTopology = 10,
        TokenRelationship = 11,
        QuotaEnabled = 12,
        RegistryDenied = 13,
        GuardBaseline = 14,
        Environment = 15,
        InnerJobConfigured = 16,
        TargetCreate = 17,
        InnerAssign = 18,
        InnerMembership = 19,
        TargetResume = 20,
        UiWindow = 21,
        UiReadyCaptureOne = 22,
        UiReadyCaptureTwo = 23,
        UiInput = 24,
        UiCompleteCaptureOne = 25,
        UiCompleteCaptureTwo = 26,
        UiClose = 27,
        TimeoutRootChildTopology = 28,
        TimeoutObserved = 29,
        InnerCleanup = 30,
        QuotaRestored = 31,
        RebindInputs = 32,
        GuardsStable = 33,
        RegistryStable = 34,
        LockedRefusal = 35,
        LockedNoArtifacts = 36,
        WorkerPublish = 37,
        SupervisorWait = 38,
        OuterJobEmpty = 39,
        SupervisorPostTopology = 40,
        ReportPublish = 41,
        TimeoutRootCreate = 42,
        TimeoutRootWait = 43,
        TimeoutChildWait = 44,
        OutputsAbsent = 45,
        AttemptInventory = 46,
        PrelaunchTopology = 47,
        TokenAcquire = 48,
        ControllerTopology = 49,
        UiProtocolReady = 50,
        UiGeometry = 51,
        UiCompleteState = 52,
        EvidenceValidate = 53,
        EvidenceDeleteInventory = 54,
        TokenRestored = 55,
        SessionDesktopRecheck = 56
    }

    internal enum RuntimeScenarioRole
    {
        None = 0,
        Supervisor = 1,
        Controller = 2,
        LockedPreflight = 3,
        TimeoutRoot = 4,
        TimeoutChild = 5
    }

    internal sealed class RuntimeScenarioStepResult
    {
        private RuntimeScenarioStepResult(bool succeeded, int exitCode)
        {
            Succeeded = succeeded;
            ExitCode = exitCode;
        }

        internal bool Succeeded { get; private set; }
        internal int ExitCode { get; private set; }

        internal static RuntimeScenarioStepResult Passed()
        {
            return new RuntimeScenarioStepResult(true, RuntimeCanonicalData.ExitAccepted);
        }

        internal static RuntimeScenarioStepResult Failed(int exitCode)
        {
            if (!RuntimeScenarioEngine.IsFailureExit(exitCode))
                throw new ArgumentOutOfRangeException("exitCode");
            return new RuntimeScenarioStepResult(false, exitCode);
        }
    }

    internal interface IRuntimeScenarioPort
    {
        RuntimeScenarioRole Role { get; }
        RuntimeScenarioStepResult Execute(RuntimeScenarioStage stage);
        RuntimeScenarioStepResult Cleanup();
    }

    internal interface IRuntimeSupervisorScenarioPort : IRuntimeScenarioPort { }
    internal interface IRuntimeControllerScenarioPort : IRuntimeScenarioPort { }
    internal interface IRuntimeLockedPreflightScenarioPort : IRuntimeScenarioPort { }
    internal interface IRuntimeTimeoutRootScenarioPort : IRuntimeScenarioPort { }
    internal interface IRuntimeTimeoutChildScenarioPort : IRuntimeScenarioPort { }

    internal sealed class RuntimeScenarioPlan
    {
        private readonly string scenarioId;
        private readonly RuntimeScenarioRole role;
        private readonly string workerImage;
        private readonly string targetImage;
        private readonly int successExitCode;
        private readonly int workerExitCode;
        private readonly uint outerActiveProcessLimit;
        private readonly ulong outerJobMemoryLimit;
        private readonly RuntimeScenarioStage[] stages;

        private RuntimeScenarioPlan(string scenarioId, RuntimeScenarioRole role,
            string workerImage, string targetImage, int successExitCode,
            int workerExitCode, uint outerActiveProcessLimit, ulong outerJobMemoryLimit,
            RuntimeScenarioStage[] stages)
        {
            this.scenarioId = scenarioId;
            this.role = role;
            this.workerImage = workerImage;
            this.targetImage = targetImage;
            this.successExitCode = successExitCode;
            this.workerExitCode = workerExitCode;
            this.outerActiveProcessLimit = outerActiveProcessLimit;
            this.outerJobMemoryLimit = outerJobMemoryLimit;
            this.stages = (RuntimeScenarioStage[])stages.Clone();
        }

        internal string ScenarioId { get { return scenarioId; } }
        internal RuntimeScenarioRole Role { get { return role; } }
        internal string WorkerImage { get { return workerImage; } }
        internal string TargetImage { get { return targetImage; } }
        internal int SuccessExitCode { get { return successExitCode; } }
        internal int WorkerExitCode { get { return workerExitCode; } }
        internal uint OuterActiveProcessLimit { get { return outerActiveProcessLimit; } }
        internal ulong OuterJobMemoryLimit { get { return outerJobMemoryLimit; } }
        internal int StageCount { get { return stages.Length; } }

        internal RuntimeScenarioStage StageAt(int index)
        {
            return index >= 0 && index < stages.Length ? stages[index] :
                RuntimeScenarioStage.None;
        }

        internal static bool TryCreate(string scenarioId, RuntimeScenarioRole role,
            out RuntimeScenarioPlan plan)
        {
            plan = null;
            if (!RuntimeCanonicalData.IsScenario(scenarioId)) return false;
            string worker = RuntimeCanonicalData.WorkerImageFor(scenarioId);
            string target = RuntimeCanonicalData.TargetImageFor(scenarioId);
            RuntimeScenarioStage[] selected = null;
            int successExit = RuntimeCanonicalData.ExitAccepted;
            int workerExit = RuntimeCanonicalData.ExitAccepted;
            uint activeLimit = 0;
            ulong jobMemory = 0;
            bool ui = String.Equals(scenarioId, RuntimeCanonicalData.UiSuccessScenario,
                StringComparison.Ordinal);
            bool timeout = String.Equals(scenarioId, RuntimeCanonicalData.TreeTimeoutScenario,
                StringComparison.Ordinal);
            bool locked = String.Equals(scenarioId, RuntimeCanonicalData.LockedRefusalScenario,
                StringComparison.Ordinal);

            if (role == RuntimeScenarioRole.Supervisor)
            {
                selected = new RuntimeScenarioStage[] {
                    RuntimeScenarioStage.BindInputs,
                    RuntimeScenarioStage.OutputsAbsent,
                    RuntimeScenarioStage.AttemptInventory,
                    RuntimeScenarioStage.PrelaunchTopology,
                    RuntimeScenarioStage.SupervisorJobConfigured,
                    RuntimeScenarioStage.SupervisorCreate,
                    RuntimeScenarioStage.SupervisorAssign,
                    RuntimeScenarioStage.SupervisorMembership,
                    RuntimeScenarioStage.WorkerTopology,
                    RuntimeScenarioStage.SupervisorResume,
                    RuntimeScenarioStage.SupervisorWait,
                    RuntimeScenarioStage.OuterJobEmpty,
                    RuntimeScenarioStage.SupervisorPostTopology,
                    RuntimeScenarioStage.EvidenceValidate,
                    RuntimeScenarioStage.ReportPublish,
                    RuntimeScenarioStage.EvidenceDeleteInventory
                };
                if (ui)
                {
                    activeLimit = 2;
                    jobMemory = 536870912;
                    workerExit = RuntimeCanonicalData.ExitAccepted;
                }
                else if (timeout)
                {
                    activeLimit = 3;
                    jobMemory = 805306368;
                    workerExit = RuntimeCanonicalData.ExitTreeTimeout;
                }
                else
                {
                    activeLimit = 1;
                    jobMemory = 268435456;
                    workerExit = RuntimeCanonicalData.ExitLockedRefusal;
                }
                successExit = workerExit;
            }
            else if (role == RuntimeScenarioRole.Controller && (ui || timeout))
            {
                RuntimeScenarioStage[] prefix = {
                    RuntimeScenarioStage.StreamsAbsent,
                    RuntimeScenarioStage.BindInputs,
                    RuntimeScenarioStage.OutputsAbsent,
                    RuntimeScenarioStage.SessionDesktop,
                    RuntimeScenarioStage.ControllerTopology,
                    RuntimeScenarioStage.TokenAcquire,
                    RuntimeScenarioStage.QuotaEnabled,
                    RuntimeScenarioStage.RegistryDenied,
                    RuntimeScenarioStage.GuardBaseline,
                    RuntimeScenarioStage.TokenRelationship,
                    RuntimeScenarioStage.Environment,
                    RuntimeScenarioStage.TargetCreate,
                    RuntimeScenarioStage.InnerJobConfigured,
                    RuntimeScenarioStage.InnerAssign,
                    RuntimeScenarioStage.InnerMembership,
                    RuntimeScenarioStage.TargetResume
                };
                RuntimeScenarioStage[] route;
                if (ui)
                {
                    route = new RuntimeScenarioStage[] {
                        RuntimeScenarioStage.UiWindow,
                        RuntimeScenarioStage.UiProtocolReady,
                        RuntimeScenarioStage.UiGeometry,
                        RuntimeScenarioStage.UiReadyCaptureOne,
                        RuntimeScenarioStage.UiReadyCaptureTwo,
                        RuntimeScenarioStage.UiInput,
                        RuntimeScenarioStage.UiCompleteState,
                        RuntimeScenarioStage.UiCompleteCaptureOne,
                        RuntimeScenarioStage.UiCompleteCaptureTwo,
                        RuntimeScenarioStage.UiClose,
                        RuntimeScenarioStage.InnerCleanup,
                        RuntimeScenarioStage.SessionDesktopRecheck,
                        RuntimeScenarioStage.QuotaRestored,
                        RuntimeScenarioStage.TokenRestored,
                        RuntimeScenarioStage.GuardsStable,
                        RuntimeScenarioStage.RegistryStable,
                        RuntimeScenarioStage.RebindInputs,
                        RuntimeScenarioStage.WorkerPublish
                    };
                }
                else
                {
                    route = new RuntimeScenarioStage[] {
                        RuntimeScenarioStage.TimeoutRootChildTopology,
                        RuntimeScenarioStage.TimeoutObserved,
                        RuntimeScenarioStage.InnerCleanup,
                        RuntimeScenarioStage.SessionDesktopRecheck,
                        RuntimeScenarioStage.QuotaRestored,
                        RuntimeScenarioStage.TokenRestored,
                        RuntimeScenarioStage.GuardsStable,
                        RuntimeScenarioStage.RegistryStable,
                        RuntimeScenarioStage.RebindInputs,
                        RuntimeScenarioStage.WorkerPublish
                    };
                    successExit = RuntimeCanonicalData.ExitTreeTimeout;
                }
                selected = Join(prefix, route);
            }
            else if (role == RuntimeScenarioRole.LockedPreflight && locked)
            {
                selected = new RuntimeScenarioStage[] {
                    RuntimeScenarioStage.StreamsAbsent,
                    RuntimeScenarioStage.BindInputs,
                    RuntimeScenarioStage.OutputsAbsent,
                    RuntimeScenarioStage.SessionDesktop,
                    RuntimeScenarioStage.WorkerTopology,
                    RuntimeScenarioStage.LockedRefusal,
                    RuntimeScenarioStage.LockedNoArtifacts,
                    RuntimeScenarioStage.RebindInputs,
                    RuntimeScenarioStage.WorkerPublish
                };
                successExit = RuntimeCanonicalData.ExitLockedRefusal;
            }
            else if (role == RuntimeScenarioRole.TimeoutRoot && timeout)
            {
                selected = new RuntimeScenarioStage[] {
                    RuntimeScenarioStage.StreamsAbsent,
                    RuntimeScenarioStage.BindInputs,
                    RuntimeScenarioStage.TimeoutRootCreate,
                    RuntimeScenarioStage.TimeoutRootWait
                };
            }
            else if (role == RuntimeScenarioRole.TimeoutChild && timeout)
            {
                selected = new RuntimeScenarioStage[] {
                    RuntimeScenarioStage.StreamsAbsent,
                    RuntimeScenarioStage.TimeoutChildWait
                };
            }
            if (selected == null) return false;
            plan = new RuntimeScenarioPlan(scenarioId, role, worker, target, successExit,
                workerExit, activeLimit, jobMemory, selected);
            return true;
        }

        private static RuntimeScenarioStage[] Join(RuntimeScenarioStage[] first,
            RuntimeScenarioStage[] second)
        {
            RuntimeScenarioStage[] result = new RuntimeScenarioStage[first.Length + second.Length];
            Array.Copy(first, 0, result, 0, first.Length);
            Array.Copy(second, 0, result, first.Length, second.Length);
            return result;
        }
    }

    internal sealed class RuntimeScenarioExecutionResult
    {
        internal RuntimeScenarioExecutionResult(bool accepted, int exitCode,
            RuntimeScenarioStage stoppedStage, int completedStageCount,
            bool cleanupAttempted, bool cleanupSucceeded)
        {
            Accepted = accepted;
            ExitCode = exitCode;
            StoppedStage = stoppedStage;
            CompletedStageCount = completedStageCount;
            CleanupAttempted = cleanupAttempted;
            CleanupSucceeded = cleanupSucceeded;
        }

        internal bool Accepted { get; private set; }
        internal int ExitCode { get; private set; }
        internal RuntimeScenarioStage StoppedStage { get; private set; }
        internal int CompletedStageCount { get; private set; }
        internal bool CleanupAttempted { get; private set; }
        internal bool CleanupSucceeded { get; private set; }
    }

    internal static class RuntimeScenarioEngine
    {
        internal static RuntimeScenarioExecutionResult Run(RuntimeScenarioPlan plan,
            IRuntimeScenarioPort port)
        {
            if (plan == null || port == null || port.Role != plan.Role ||
                    !RoleMatchesPort(plan.Role, port))
                return new RuntimeScenarioExecutionResult(false,
                    RuntimeCanonicalData.ExitBindingRejection, RuntimeScenarioStage.None,
                    0, false, false);

            int exitCode = plan.SuccessExitCode;
            RuntimeScenarioStage stopped = RuntimeScenarioStage.None;
            int completed = 0;
            for (int index = 0; index < plan.StageCount; index++)
            {
                RuntimeScenarioStage stage = plan.StageAt(index);
                RuntimeScenarioStepResult step;
                try
                {
                    step = port.Execute(stage);
                }
                catch (Exception)
                {
                    step = RuntimeScenarioStepResult.Failed(
                        RuntimeCanonicalData.ExitNativeCapabilityFailure);
                }
                if (step == null || !step.Succeeded)
                {
                    exitCode = step == null ? RuntimeCanonicalData.ExitNativeCapabilityFailure :
                        step.ExitCode;
                    stopped = stage;
                    break;
                }
                completed++;
            }

            bool cleanupSucceeded = false;
            try
            {
                RuntimeScenarioStepResult cleanup = port.Cleanup();
                cleanupSucceeded = cleanup != null && cleanup.Succeeded;
            }
            catch (Exception)
            {
                cleanupSucceeded = false;
            }
            if (!cleanupSucceeded)
                exitCode = RuntimeCanonicalData.ExitCleanupFailure;
            bool accepted = stopped == RuntimeScenarioStage.None && cleanupSucceeded;
            return new RuntimeScenarioExecutionResult(accepted, exitCode, stopped,
                completed, true, cleanupSucceeded);
        }

        internal static bool IsFailureExit(int exitCode)
        {
            return exitCode == RuntimeCanonicalData.ExitBindingRejection ||
                exitCode == RuntimeCanonicalData.ExitNativeCapabilityFailure ||
                exitCode == RuntimeCanonicalData.ExitCleanupFailure ||
                exitCode == RuntimeCanonicalData.ExitReportFailure;
        }

        private static bool RoleMatchesPort(RuntimeScenarioRole role,
            IRuntimeScenarioPort port)
        {
            if (role == RuntimeScenarioRole.Supervisor)
                return port is IRuntimeSupervisorScenarioPort;
            if (role == RuntimeScenarioRole.Controller)
                return port is IRuntimeControllerScenarioPort;
            if (role == RuntimeScenarioRole.LockedPreflight)
                return port is IRuntimeLockedPreflightScenarioPort;
            if (role == RuntimeScenarioRole.TimeoutRoot)
                return port is IRuntimeTimeoutRootScenarioPort;
            if (role == RuntimeScenarioRole.TimeoutChild)
                return port is IRuntimeTimeoutChildScenarioPort;
            return false;
        }
    }

    internal static class RuntimeDeadlineMath
    {
        internal static bool TryCreateDeadline(long start, long frequency,
            uint milliseconds, out long deadline)
        {
            deadline = 0;
            if (start < 0 || frequency <= 0 || milliseconds == 0 ||
                    (long)milliseconds > Int64.MaxValue / frequency)
                return false;
            long ticks = (long)milliseconds * frequency / 1000;
            if (ticks <= 0 || start > Int64.MaxValue - ticks)
                return false;
            deadline = start + ticks;
            return deadline > start;
        }

        internal static uint RemainingMilliseconds(long start, long deadline,
            long now, long frequency)
        {
            if (start < 0 || deadline <= start || frequency <= 0 || now < start ||
                    now >= deadline)
                return 0;
            long ticks = deadline - now;
            long seconds = ticks / frequency;
            long remainder = ticks % frequency;
            if (seconds > UInt32.MaxValue / 1000)
                return UInt32.MaxValue;
            ulong milliseconds = (ulong)seconds * 1000UL +
                (ulong)remainder * 1000UL / (ulong)frequency;
            return milliseconds > UInt32.MaxValue ? UInt32.MaxValue :
                (uint)milliseconds;
        }

        internal static bool CanProbe(long start, long deadline, long now,
            long frequency)
        {
            return RemainingMilliseconds(start, deadline, now, frequency) != 0;
        }
    }

    internal sealed class RuntimeIdentity
    {
        private readonly string role;
        private readonly int byteCount;
        private readonly string sha256;

        internal RuntimeIdentity(string role, int byteCount, string sha256)
        {
            this.role = role;
            this.byteCount = byteCount;
            this.sha256 = sha256;
        }

        internal string Role { get { return role; } }
        internal int ByteCount { get { return byteCount; } }
        internal string Sha256 { get { return sha256; } }

        internal bool IsWellFormed()
        {
            return role != null && role.Length > 0 && byteCount > 0 &&
                IsLowerHexNonZero(sha256, 64);
        }

        internal bool Exact(RuntimeIdentity other)
        {
            return other != null && byteCount == other.byteCount &&
                String.Equals(role, other.role, StringComparison.Ordinal) &&
                String.Equals(sha256, other.sha256, StringComparison.Ordinal);
        }

        internal static bool IsLowerHex(string value, int width)
        {
            if (value == null || value.Length != width)
                return false;
            for (int index = 0; index < value.Length; index++)
            {
                char current = value[index];
                if (!((current >= '0' && current <= '9') ||
                        (current >= 'a' && current <= 'f')))
                    return false;
            }
            return true;
        }

        internal static bool IsLowerHexNonZero(string value, int width)
        {
            if (!IsLowerHex(value, width)) return false;
            for (int index = 0; index < value.Length; index++)
                if (value[index] != '0') return true;
            return false;
        }
    }

    internal sealed class RuntimeIdentitySet
    {
        private readonly RuntimeIdentity[] values;

        internal RuntimeIdentitySet(RuntimeIdentity[] source)
        {
            if (source == null)
            {
                values = null;
                return;
            }
            values = new RuntimeIdentity[source.Length];
            for (int index = 0; index < source.Length; index++)
                values[index] = source[index];
        }

        internal int Count { get { return values == null ? 0 : values.Length; } }

        internal RuntimeIdentity At(int index)
        {
            if (values == null || index < 0 || index >= values.Length)
                return null;
            return values[index];
        }

        internal bool IsCanonicalRoleSet()
        {
            if (Count != RuntimeCanonicalData.RequiredIdentityRoleCount)
                return false;
            for (int index = 0; index < Count; index++)
            {
                RuntimeIdentity value = values[index];
                if (value == null || !value.IsWellFormed() ||
                        !String.Equals(value.Role, RuntimeCanonicalData.IdentityRoleAt(index),
                            StringComparison.Ordinal))
                    return false;
            }
            RuntimeIdentity fixture = values[Count - 1];
            if (fixture.ByteCount != RuntimeCanonicalData.UiFixtureByteCount ||
                    !String.Equals(fixture.Sha256, RuntimeCanonicalData.UiFixtureSha256,
                        StringComparison.Ordinal))
                return false;
            return true;
        }

        internal bool Exact(RuntimeIdentitySet other)
        {
            if (other == null || Count != other.Count)
                return false;
            for (int index = 0; index < Count; index++)
            {
                if (values[index] == null || !values[index].Exact(other.values[index]))
                    return false;
            }
            return true;
        }
    }

    internal sealed class RuntimePublicConfiguration
    {
        internal RuntimePublicConfiguration(string profileId, string buildState, string sourceRevision,
            RuntimeIdentity productionManifestIdentity, RuntimeIdentity privateSchemaIdentity,
            RuntimeIdentitySet roleIdentities)
        {
            ProfileId = profileId;
            BuildState = buildState;
            SourceRevision = sourceRevision;
            ProductionManifestIdentity = productionManifestIdentity;
            PrivateSchemaIdentity = privateSchemaIdentity;
            RoleIdentities = roleIdentities;
        }

        internal string ProfileId { get; private set; }
        internal string BuildState { get; private set; }
        internal string SourceRevision { get; private set; }
        internal RuntimeIdentity ProductionManifestIdentity { get; private set; }
        internal RuntimeIdentity PrivateSchemaIdentity { get; private set; }
        internal RuntimeIdentitySet RoleIdentities { get; private set; }
    }

    internal sealed class RuntimePrivateConfiguration
    {
        internal RuntimePrivateConfiguration(string scenarioId, string sourceRevision,
            RuntimeIdentity publicConfigurationIdentity,
            RuntimeIdentity productionManifestIdentity, RuntimeIdentity privateSchemaIdentity,
            RuntimeIdentitySet roleIdentities, string acceptedHostGuard,
            string attemptRootGuard, string installedTreeGuard, string virtualStoreGuard)
        {
            ScenarioId = scenarioId;
            SourceRevision = sourceRevision;
            PublicConfigurationIdentity = publicConfigurationIdentity;
            ProductionManifestIdentity = productionManifestIdentity;
            PrivateSchemaIdentity = privateSchemaIdentity;
            RoleIdentities = roleIdentities;
            AcceptedHostGuard = acceptedHostGuard;
            AttemptRootGuard = attemptRootGuard;
            InstalledTreeGuard = installedTreeGuard;
            VirtualStoreGuard = virtualStoreGuard;
        }

        internal string ScenarioId { get; private set; }
        internal string SourceRevision { get; private set; }
        internal RuntimeIdentity PublicConfigurationIdentity { get; private set; }
        internal RuntimeIdentity ProductionManifestIdentity { get; private set; }
        internal RuntimeIdentity PrivateSchemaIdentity { get; private set; }
        internal RuntimeIdentitySet RoleIdentities { get; private set; }
        internal string AcceptedHostGuard { get; private set; }
        internal string AttemptRootGuard { get; private set; }
        internal string InstalledTreeGuard { get; private set; }
        internal string VirtualStoreGuard { get; private set; }
    }

    internal sealed class RuntimeObjectFacts
    {
        internal RuntimeObjectFacts(string ownerBinding, long generation,
            bool canonicalPublicConfiguration,
            bool canonicalPrivateConfiguration, bool bootstrapAuthorityClosed,
            bool exactObjectSafety, bool pairwiseDistinctObjects, bool stableBindings,
            RuntimeIdentity observedPublicConfigurationIdentity,
            RuntimeIdentity observedProductionManifestIdentity,
            RuntimeIdentitySet observedRoleIdentities)
        {
            OwnerBinding = ownerBinding;
            Generation = generation;
            CanonicalPublicConfiguration = canonicalPublicConfiguration;
            CanonicalPrivateConfiguration = canonicalPrivateConfiguration;
            BootstrapAuthorityClosed = bootstrapAuthorityClosed;
            ExactObjectSafety = exactObjectSafety;
            PairwiseDistinctObjects = pairwiseDistinctObjects;
            StableBindings = stableBindings;
            ObservedPublicConfigurationIdentity = observedPublicConfigurationIdentity;
            ObservedProductionManifestIdentity = observedProductionManifestIdentity;
            ObservedRoleIdentities = observedRoleIdentities;
        }

        internal string OwnerBinding { get; private set; }
        internal long Generation { get; private set; }
        internal bool CanonicalPublicConfiguration { get; private set; }
        internal bool CanonicalPrivateConfiguration { get; private set; }
        internal bool BootstrapAuthorityClosed { get; private set; }
        internal bool ExactObjectSafety { get; private set; }
        internal bool PairwiseDistinctObjects { get; private set; }
        internal bool StableBindings { get; private set; }
        internal RuntimeIdentity ObservedPublicConfigurationIdentity { get; private set; }
        internal RuntimeIdentity ObservedProductionManifestIdentity { get; private set; }
        internal RuntimeIdentitySet ObservedRoleIdentities { get; private set; }
    }

    internal sealed class RuntimeGateFacts
    {
        internal RuntimeGateFacts(RuntimePublicConfiguration publicConfiguration,
            RuntimePrivateConfiguration privateConfiguration, RuntimeObjectFacts objectFacts)
        {
            PublicConfiguration = publicConfiguration;
            PrivateConfiguration = privateConfiguration;
            ObjectFacts = objectFacts;
        }

        internal RuntimePublicConfiguration PublicConfiguration { get; private set; }
        internal RuntimePrivateConfiguration PrivateConfiguration { get; private set; }
        internal RuntimeObjectFacts ObjectFacts { get; private set; }
    }

    internal sealed class RuntimeConsumerBinding
    {
        internal RuntimeConsumerBinding(string ownerBinding, string scenarioId,
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

    internal static class RuntimeCanonicalParser
    {
        private const int MaximumConfigurationBytes = 65536;
        private const string ApprovedArtifacts =
            "{\"complete_bmp\":{\"byte_count\":230454,\"sha256\":" +
            "\"5dac08fba06a53bb0a480fe388907e78147b5c0d042fee53eea2ff81b4ee8bc6\"}," +
            "\"ready_bmp\":{\"byte_count\":230454,\"sha256\":" +
            "\"4f471fd3bc87f53fef9d7f200eaccb0ebe69a0240a9cf09f79bc2bfec3c51f19\"}}";
        private const string FixedNames =
            "{\"build_manifest\":\"SyntheticLauncherBuildManifest.v1.json\"," +
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
            "\"worker_evidence\":\"SyntheticLauncherWorkerEvidence.v1.json\"}";

        internal static bool TryParse(byte[] publicBytes, byte[] privateBytes,
            RuntimeObjectFacts observed, out RuntimeGateFacts facts)
        {
            facts = null;
            if (observed == null)
                return false;
            try
            {
                RuntimePublicConfiguration publicConfiguration = ParsePublic(publicBytes);
                RuntimePrivateConfiguration privateConfiguration = ParsePrivate(privateBytes);
                facts = new RuntimeGateFacts(publicConfiguration, privateConfiguration, observed);
                return true;
            }
            catch (CanonicalParseFailure)
            {
                return false;
            }
        }

        private static RuntimePublicConfiguration ParsePublic(byte[] raw)
        {
            CanonicalReader reader = new CanonicalReader(raw);
            reader.Take("{\"approved_artifacts\":");
            reader.Take(ApprovedArtifacts);
            reader.Take(",\"build_binding\":");
            string buildState = reader.ReadString();
            reader.Take(",\"candidate_production_manifest\":");
            RuntimeIdentity manifest = reader.ReadIdentity("production_manifest");
            reader.Take(",\"fixed_names\":");
            reader.Take(FixedNames);
            reader.Take(",\"profile_id\":");
            string profileId = reader.ReadString();
            reader.Take(",\"role_identities\":");
            RuntimeIdentitySet roles = reader.ReadRoles();
            reader.Take(",\"runtime_private_schema\":");
            RuntimeIdentity privateSchema = reader.ReadIdentity("runtime_private_schema");
            reader.Take(",\"schema_version\":1,\"source_revision\":");
            string sourceRevision = reader.ReadString();
            reader.Take("}");
            reader.Finish();
            if ((!String.Equals(buildState, RuntimeCanonicalData.BuildUnpinned,
                    StringComparison.Ordinal) &&
                    !String.Equals(buildState, RuntimeCanonicalData.BuildPinned,
                        StringComparison.Ordinal)) ||
                    !String.Equals(profileId, RuntimeCanonicalData.ProfileId,
                        StringComparison.Ordinal) ||
                    !RuntimeIdentity.IsLowerHexNonZero(sourceRevision, 40))
                throw new CanonicalParseFailure();
            return new RuntimePublicConfiguration(profileId, buildState, sourceRevision,
                manifest, privateSchema, roles);
        }

        private static RuntimePrivateConfiguration ParsePrivate(byte[] raw)
        {
            CanonicalReader reader = new CanonicalReader(raw);
            reader.Take("{\"expected_identities\":");
            RuntimeIdentitySet roles = reader.ReadRoles();
            reader.Take(",\"guard_paths\":{\"accepted_host_artifact\":");
            string acceptedHost = reader.ReadString();
            reader.Take(",\"attempt_root\":");
            string attemptRoot = reader.ReadString();
            reader.Take(",\"installed_tree\":");
            string installedTree = reader.ReadString();
            reader.Take(",\"virtual_store_tree\":");
            string virtualStore = reader.ReadString();
            reader.Take("},\"production_manifest\":");
            RuntimeIdentity manifest = reader.ReadIdentity("production_manifest");
            reader.Take(",\"public_configuration\":");
            RuntimeIdentity publicConfiguration = reader.ReadIdentity("public_configuration");
            reader.Take(",\"runtime_private_schema\":");
            RuntimeIdentity privateSchema = reader.ReadIdentity("runtime_private_schema");
            reader.Take(",\"scenario_id\":");
            string scenarioId = reader.ReadString();
            reader.Take(",\"schema_version\":1,\"source_revision\":");
            string sourceRevision = reader.ReadString();
            reader.Take("}");
            reader.Finish();
            if (!RuntimeCanonicalData.IsScenario(scenarioId) ||
                    !RuntimeIdentity.IsLowerHexNonZero(sourceRevision, 40) ||
                    !RuntimeCanonicalData.IsGuardPath(acceptedHost) ||
                    !RuntimeCanonicalData.IsGuardPath(attemptRoot) ||
                    !RuntimeCanonicalData.IsGuardPath(installedTree) ||
                    !RuntimeCanonicalData.IsGuardPath(virtualStore))
                throw new CanonicalParseFailure();
            return new RuntimePrivateConfiguration(scenarioId, sourceRevision,
                publicConfiguration, manifest, privateSchema, roles, acceptedHost,
                attemptRoot, installedTree, virtualStore);
        }

        private sealed class CanonicalReader
        {
            private readonly byte[] raw;
            private readonly int limit;
            private int position;

            internal CanonicalReader(byte[] raw)
            {
                if (raw == null || raw.Length < 3 || raw.Length > MaximumConfigurationBytes ||
                        raw[raw.Length - 1] != (byte)'\n')
                    throw new CanonicalParseFailure();
                for (int index = 0; index < raw.Length - 1; index++)
                {
                    if (raw[index] < 0x20 || raw[index] > 0x7e)
                        throw new CanonicalParseFailure();
                }
                this.raw = raw;
                limit = raw.Length - 1;
            }

            internal void Take(string expected)
            {
                if (expected == null || position + expected.Length > limit)
                    throw new CanonicalParseFailure();
                for (int index = 0; index < expected.Length; index++)
                {
                    if (raw[position + index] != (byte)expected[index])
                        throw new CanonicalParseFailure();
                }
                position += expected.Length;
            }

            internal string ReadString()
            {
                if (position >= limit || raw[position++] != (byte)'"')
                    throw new CanonicalParseFailure();
                char[] value = new char[limit - position];
                int count = 0;
                while (position < limit)
                {
                    byte current = raw[position++];
                    if (current == (byte)'"')
                        return new String(value, 0, count);
                    if (current == (byte)'\\')
                    {
                        if (position >= limit || raw[position++] != (byte)'\\')
                            throw new CanonicalParseFailure();
                        value[count++] = '\\';
                    }
                    else
                    {
                        if (current < 0x20 || current > 0x7e)
                            throw new CanonicalParseFailure();
                        value[count++] = (char)current;
                    }
                }
                throw new CanonicalParseFailure();
            }

            internal RuntimeIdentity ReadIdentity(string role)
            {
                Take("{\"byte_count\":");
                int byteCount = ReadPositiveInteger();
                Take(",\"sha256\":");
                string sha256 = ReadString();
                Take("}");
                RuntimeIdentity identity = new RuntimeIdentity(role, byteCount, sha256);
                if (!identity.IsWellFormed())
                    throw new CanonicalParseFailure();
                return identity;
            }

            internal RuntimeIdentitySet ReadRoles()
            {
                Take("{");
                RuntimeIdentity[] roles = new RuntimeIdentity[
                    RuntimeCanonicalData.RequiredIdentityRoleCount];
                for (int index = 0; index < roles.Length; index++)
                {
                    if (index != 0)
                        Take(",");
                    string role = RuntimeCanonicalData.IdentityRoleAt(index);
                    Take("\"" + role + "\":");
                    roles[index] = ReadIdentity(role);
                }
                Take("}");
                return new RuntimeIdentitySet(roles);
            }

            internal void Finish()
            {
                if (position != limit)
                    throw new CanonicalParseFailure();
            }

            private int ReadPositiveInteger()
            {
                if (position >= limit || raw[position] < (byte)'1' ||
                        raw[position] > (byte)'9')
                    throw new CanonicalParseFailure();
                int result = 0;
                while (position < limit && raw[position] >= (byte)'0' &&
                        raw[position] <= (byte)'9')
                {
                    int digit = raw[position++] - (byte)'0';
                    if (result > (Int32.MaxValue - digit) / 10)
                        throw new CanonicalParseFailure();
                    result = result * 10 + digit;
                }
                return result;
            }
        }

        private sealed class CanonicalParseFailure : Exception
        {
        }
    }
}
