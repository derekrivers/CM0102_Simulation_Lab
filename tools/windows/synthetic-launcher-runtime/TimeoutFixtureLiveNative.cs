using System;
using System.Runtime.InteropServices;
using System.Text;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal sealed class TimeoutFixtureLiveNative : IRuntimeTimeoutRootScenarioPort
    {
        private const uint CreateNoWindow = 0x08000000;
        private const uint Infinite = 0xffffffff;
        private const uint WaitObject0 = 0;
        private const uint CreateUnicodeEnvironment = 0x00000400;
        private readonly RuntimeLeaseUse lease;
        private readonly TimeoutFixtureBootstrapSnapshot snapshot;
        private readonly RuntimeScenarioPlan plan;
        private IntPtr launchBinding = new IntPtr(-1);
        private ProcessInformation process = new ProcessInformation();
        private bool created;

        internal TimeoutFixtureLiveNative(RuntimeLeaseUse consumedLease,
            TimeoutFixtureBootstrapSnapshot boundSnapshot, RuntimeScenarioPlan boundPlan)
        {
            if (consumedLease == null)
                throw new ArgumentNullException("consumedLease");
            if (boundSnapshot == null)
                throw new ArgumentNullException("boundSnapshot");
            if (boundPlan == null || boundPlan.Role != RuntimeScenarioRole.TimeoutRoot ||
                    !String.Equals(boundPlan.ScenarioId, consumedLease.ScenarioId,
                        StringComparison.Ordinal))
                throw new ArgumentException("boundPlan");
            lease = consumedLease;
            snapshot = boundSnapshot;
            plan = boundPlan;
        }

        public RuntimeScenarioRole Role { get { return RuntimeScenarioRole.TimeoutRoot; } }

        public RuntimeScenarioStepResult Execute(RuntimeScenarioStage stage)
        {
            if (stage == RuntimeScenarioStage.StreamsAbsent)
                return Result(StandardStreamsAbsent(),
                    RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.BindInputs)
            {
                return Result(snapshot.Objects.ContainsKey(
                    "SyntheticLauncherTimeoutChild.exe") && RebindChild(out launchBinding),
                    RuntimeCanonicalData.ExitBindingRejection);
            }
            if (stage == RuntimeScenarioStage.TimeoutRootCreate)
            {
                string application = snapshot.ParentFinalPath +
                    "\\SyntheticLauncherTimeoutChild.exe";
                StartupInfo startup = new StartupInfo();
                startup.Size = Marshal.SizeOf(typeof(StartupInfo));
                created = CreateProcessW(application, null, IntPtr.Zero, IntPtr.Zero, false,
                    CreateUnicodeEnvironment | CreateNoWindow, IntPtr.Zero,
                    snapshot.ParentFinalPath, ref startup, out process);
                return Result(created, RuntimeCanonicalData.ExitNativeCapabilityFailure);
            }
            if (stage == RuntimeScenarioStage.TimeoutRootWait)
            {
                return Result(WaitForSingleObject(process.Process, Infinite) == WaitObject0,
                    RuntimeCanonicalData.ExitCleanupFailure);
            }
            return RuntimeScenarioStepResult.Failed(
                RuntimeCanonicalData.ExitBindingRejection);
        }

        public RuntimeScenarioStepResult Cleanup()
        {
            bool exact = true;
            if (launchBinding != new IntPtr(-1))
            {
                IntPtr rebound;
                exact = RebindChild(out rebound);
                if (exact) CloseHandle(rebound);
            }
            if (process.Thread != IntPtr.Zero) CloseHandle(process.Thread);
            if (process.Process != IntPtr.Zero) CloseHandle(process.Process);
            if (launchBinding != new IntPtr(-1)) CloseHandle(launchBinding);
            GC.KeepAlive(lease);
            GC.KeepAlive(plan);
            return exact ? RuntimeScenarioStepResult.Passed() :
                RuntimeScenarioStepResult.Failed(RuntimeCanonicalData.ExitCleanupFailure);
        }

        private static RuntimeScenarioStepResult Result(bool value, int exitCode)
        {
            return value ? RuntimeScenarioStepResult.Passed() :
                RuntimeScenarioStepResult.Failed(exitCode);
        }

        private static bool StandardStreamsAbsent()
        {
            IntPtr output = GetStdHandle(-11);
            IntPtr error = GetStdHandle(-12);
            return (output == IntPtr.Zero || output == new IntPtr(-1)) &&
                (error == IntPtr.Zero || error == new IntPtr(-1));
        }

        private bool RebindChild(out IntPtr retainedHandle)
        {
            retainedHandle = new IntPtr(-1);
            if (!RebindParent()) return false;
            const string leaf = "SyntheticLauncherTimeoutChild.exe";
            TimeoutFixtureBoundObject expected = snapshot.Objects[leaf];
            IntPtr handle = OpenRelative(leaf);
            if (handle == new IntPtr(-1)) return false;
            try
            {
                ByHandleFileInformation information;
                if (!GetFileInformationByHandle(handle, out information) ||
                        information.VolumeSerialNumber != expected.VolumeSerial ||
                        information.FileIndexHigh != expected.FileIndexHigh ||
                        information.FileIndexLow != expected.FileIndexLow ||
                        information.NumberOfLinks != 1 || expected.LinkCount != 1 ||
                        information.FileAttributes != expected.Attributes ||
                        (information.FileAttributes & (0x10 | 0x400 | 0x800 | 0x4000)) != 0 ||
                        !String.Equals(FinalPath(handle), expected.FinalPath,
                            StringComparison.Ordinal) || !OnlyUnnamedStream(handle) ||
                        !EqualBytes(SecurityDescriptor(handle), expected.SecurityDescriptor))
                    return false;
                long size = ((long)information.FileSizeHigh << 32) | information.FileSizeLow;
                if (size != expected.Bytes.Length) return false;
                byte[] observed = new byte[expected.Bytes.Length];
                int offset = 0;
                byte[] block = new byte[65536];
                while (offset < observed.Length)
                {
                    uint read;
                    int count = Math.Min(block.Length, observed.Length - offset);
                    if (!ReadFile(handle, block, (uint)count, out read, IntPtr.Zero) ||
                            read == 0 || read > count)
                        return false;
                    Buffer.BlockCopy(block, 0, observed, offset, (int)read);
                    offset += (int)read;
                }
                bool exact = EqualBytes(observed, expected.Bytes);
                Array.Clear(observed, 0, observed.Length);
                if (exact)
                {
                    retainedHandle = handle;
                    handle = new IntPtr(-1);
                }
                return exact;
            }
            finally
            {
                if (handle != new IntPtr(-1)) CloseHandle(handle);
            }
        }

        private bool RebindParent()
        {
            ByHandleFileInformation information;
            return GetFileInformationByHandle(snapshot.ParentHandle, out information) &&
                information.VolumeSerialNumber == snapshot.ParentVolumeSerial &&
                information.FileIndexHigh == snapshot.ParentFileIndexHigh &&
                information.FileIndexLow == snapshot.ParentFileIndexLow &&
                information.NumberOfLinks == snapshot.ParentLinkCount &&
                information.FileAttributes == snapshot.ParentAttributes &&
                (information.FileAttributes & 0x10) != 0 &&
                (information.FileAttributes & (0x400 | 0x800 | 0x4000)) == 0 &&
                HasNoNamedDataStreams(snapshot.ParentHandle) &&
                String.Equals(FinalPath(snapshot.ParentHandle), snapshot.ParentFinalPath,
                    StringComparison.Ordinal) &&
                EqualBytes(SecurityDescriptor(snapshot.ParentHandle),
                    snapshot.ParentSecurityDescriptor);
        }

        private IntPtr OpenRelative(string leaf)
        {
            IntPtr name = Marshal.StringToHGlobalUni(leaf);
            IntPtr unicodePointer = IntPtr.Zero;
            try
            {
                UnicodeString unicode = new UnicodeString();
                unicode.Length = checked((ushort)(leaf.Length * 2));
                unicode.MaximumLength = unicode.Length;
                unicode.Buffer = name;
                unicodePointer = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(UnicodeString)));
                Marshal.StructureToPtr(unicode, unicodePointer, false);
                ObjectAttributes attributes = new ObjectAttributes();
                attributes.Length = Marshal.SizeOf(typeof(ObjectAttributes));
                attributes.RootDirectory = snapshot.ParentHandle;
                attributes.ObjectName = unicodePointer;
                attributes.Attributes = 0x40;
                IoStatusBlock statusBlock;
                IntPtr handle;
                long allocation = 0;
                int status = NtCreateFile(out handle,
                    0x0001 | 0x0080 | 0x00020000 | 0x00100000,
                    ref attributes, out statusBlock, ref allocation, 0, 1, 1,
                    0x20 | 0x40 | 0x00200000, IntPtr.Zero, 0);
                return status < 0 ? new IntPtr(-1) : handle;
            }
            finally
            {
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(name);
            }
        }

        private static string FinalPath(IntPtr handle)
        {
            StringBuilder value = new StringBuilder(32768);
            uint length = GetFinalPathNameByHandleW(handle, value, value.Capacity, 0);
            return length == 0 || length >= value.Capacity ? null : value.ToString();
        }

        private static bool OnlyUnnamedStream(IntPtr handle)
        {
            IntPtr buffer = Marshal.AllocHGlobal(65536);
            try
            {
                if (!GetFileInformationByHandleEx(handle, 7, buffer, 65536)) return false;
                int next = Marshal.ReadInt32(buffer, 0);
                int nameLength = Marshal.ReadInt32(buffer, 4);
                string name = nameLength == 14 ? Marshal.PtrToStringUni(
                    new IntPtr(buffer.ToInt64() + 24), 7) : null;
                return next == 0 && String.Equals(name, "::$DATA", StringComparison.Ordinal);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool HasNoNamedDataStreams(IntPtr handle)
        {
            IntPtr buffer = Marshal.AllocHGlobal(65536);
            try
            {
                if (!GetFileInformationByHandleEx(handle, 7, buffer, 65536)) return false;
                int offset = 0;
                while (true)
                {
                    if (offset < 0 || offset > 65536 - 24) return false;
                    int next = Marshal.ReadInt32(buffer, offset);
                    int nameLength = Marshal.ReadInt32(buffer, offset + 4);
                    if (nameLength < 0 || (nameLength & 1) != 0 ||
                            nameLength > 65536 - offset - 24)
                        return false;
                    string name = Marshal.PtrToStringUni(new IntPtr(buffer.ToInt64() +
                        offset + 24), nameLength / 2);
                    if (name != null && name.EndsWith(":$DATA",
                            StringComparison.OrdinalIgnoreCase) &&
                            !String.Equals(name, "::$DATA", StringComparison.Ordinal))
                        return false;
                    if (next == 0) return true;
                    if (next < 24 || (next & 7) != 0 || offset + next <= offset)
                        return false;
                    offset += next;
                }
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static byte[] SecurityDescriptor(IntPtr handle)
        {
            IntPtr owner;
            IntPtr group;
            IntPtr dacl;
            IntPtr sacl;
            IntPtr descriptor;
            uint result = GetSecurityInfo(handle, 1, 7, out owner, out group, out dacl,
                out sacl, out descriptor);
            if (result != 0 || descriptor == IntPtr.Zero) return new byte[0];
            try
            {
                uint length = GetSecurityDescriptorLength(descriptor);
                if (length == 0 || length > 65536) return new byte[0];
                byte[] bytes = new byte[(int)length];
                Marshal.Copy(descriptor, bytes, 0, bytes.Length);
                return bytes;
            }
            finally { LocalFree(descriptor); }
        }

        private static bool EqualBytes(byte[] first, byte[] second)
        {
            if (first == null || second == null || first.Length != second.Length) return false;
            for (int index = 0; index < first.Length; index++)
                if (first[index] != second[index]) return false;
            return true;
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct StartupInfo
        {
            internal int Size;
            internal string Reserved;
            internal string Desktop;
            internal string Title;
            internal int X;
            internal int Y;
            internal int XSize;
            internal int YSize;
            internal int XCountChars;
            internal int YCountChars;
            internal int FillAttribute;
            internal int Flags;
            internal short ShowWindow;
            internal short Reserved2;
            internal IntPtr Reserved2Pointer;
            internal IntPtr StandardInput;
            internal IntPtr StandardOutput;
            internal IntPtr StandardError;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct ProcessInformation
        {
            internal IntPtr Process;
            internal IntPtr Thread;
            internal uint ProcessId;
            internal uint ThreadId;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct UnicodeString
        {
            internal ushort Length; internal ushort MaximumLength; internal IntPtr Buffer;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct ObjectAttributes
        {
            internal int Length; internal IntPtr RootDirectory; internal IntPtr ObjectName;
            internal uint Attributes; internal IntPtr SecurityDescriptor;
            internal IntPtr SecurityQualityOfService;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct IoStatusBlock { internal IntPtr Status; internal IntPtr Information; }
        [StructLayout(LayoutKind.Sequential, Pack = 4, Size = 52)]
        private struct ByHandleFileInformation
        {
            internal uint FileAttributes; internal long CreationTime;
            internal long LastAccessTime; internal long LastWriteTime;
            internal uint VolumeSerialNumber; internal uint FileSizeHigh;
            internal uint FileSizeLow; internal uint NumberOfLinks;
            internal uint FileIndexHigh; internal uint FileIndexLow;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CreateProcessW(string applicationName, string commandLine,
            IntPtr processAttributes, IntPtr threadAttributes, bool inheritHandles,
            uint creationFlags, IntPtr environment, string currentDirectory,
            ref StartupInfo startupInfo, out ProcessInformation processInformation);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr GetStdHandle(int standardHandle);
        [DllImport("ntdll.dll")]
        private static extern int NtCreateFile(out IntPtr handle, uint access,
            ref ObjectAttributes attributes, out IoStatusBlock statusBlock,
            ref long allocationSize, uint fileAttributes, uint share, uint disposition,
            uint options, IntPtr extendedAttributes, uint extendedAttributesLength);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileInformationByHandle(IntPtr handle,
            out ByHandleFileInformation information);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ReadFile(IntPtr handle, byte[] buffer, uint count,
            out uint read, IntPtr overlapped);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetFinalPathNameByHandleW(IntPtr handle, StringBuilder path,
            int count, uint flags);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileInformationByHandleEx(IntPtr handle,
            int informationClass, IntPtr information, uint size);
        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern uint GetSecurityInfo(IntPtr handle, int objectType,
            uint securityInformation, out IntPtr owner, out IntPtr group, out IntPtr dacl,
            out IntPtr sacl, out IntPtr descriptor);
        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern uint GetSecurityDescriptorLength(IntPtr descriptor);
        [DllImport("kernel32.dll")]
        private static extern IntPtr LocalFree(IntPtr memory);
    }
}
