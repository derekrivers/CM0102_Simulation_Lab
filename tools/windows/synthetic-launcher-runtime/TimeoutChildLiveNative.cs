using System;
using System.Runtime.InteropServices;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal sealed class TimeoutChildLiveNative : IRuntimeTimeoutChildScenarioPort
    {
        private readonly RuntimeLeaseUse lease;
        private readonly TimeoutChildBootstrapSnapshot snapshot;
        private readonly RuntimeScenarioPlan plan;

        internal TimeoutChildLiveNative(RuntimeLeaseUse consumedLease,
            TimeoutChildBootstrapSnapshot boundSnapshot, RuntimeScenarioPlan boundPlan)
        {
            if (consumedLease == null)
                throw new ArgumentNullException("consumedLease");
            if (boundSnapshot == null)
                throw new ArgumentNullException("boundSnapshot");
            if (boundPlan == null || boundPlan.Role != RuntimeScenarioRole.TimeoutChild ||
                    !String.Equals(boundPlan.ScenarioId, consumedLease.ScenarioId,
                        StringComparison.Ordinal))
                throw new ArgumentException("boundPlan");
            lease = consumedLease;
            snapshot = boundSnapshot;
            plan = boundPlan;
        }

        public RuntimeScenarioRole Role { get { return RuntimeScenarioRole.TimeoutChild; } }

        public RuntimeScenarioStepResult Execute(RuntimeScenarioStage stage)
        {
            if (stage == RuntimeScenarioStage.StreamsAbsent)
            {
                IntPtr output = GetStdHandle(-11);
                IntPtr error = GetStdHandle(-12);
                return (output == IntPtr.Zero || output == new IntPtr(-1)) &&
                    (error == IntPtr.Zero || error == new IntPtr(-1)) ?
                    RuntimeScenarioStepResult.Passed() : RuntimeScenarioStepResult.Failed(
                        RuntimeCanonicalData.ExitBindingRejection);
            }
            if (stage == RuntimeScenarioStage.TimeoutChildWait)
            {
                Sleep(0xffffffff);
                return RuntimeScenarioStepResult.Failed(
                    RuntimeCanonicalData.ExitCleanupFailure);
            }
            return RuntimeScenarioStepResult.Failed(
                RuntimeCanonicalData.ExitBindingRejection);
        }

        public RuntimeScenarioStepResult Cleanup()
        {
            GC.KeepAlive(snapshot);
            GC.KeepAlive(lease);
            GC.KeepAlive(plan);
            return RuntimeScenarioStepResult.Passed();
        }

        [DllImport("kernel32.dll")]
        private static extern void Sleep(uint milliseconds);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr GetStdHandle(int standardHandle);
    }
}
