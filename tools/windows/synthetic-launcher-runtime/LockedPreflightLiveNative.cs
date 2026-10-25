using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal sealed class LockedPreflightObservation
    {
        internal LockedPreflightObservation(bool activeSession, bool defaultDesktop,
            bool exactTopology, bool gameAbsent)
        {
            ActiveSession = activeSession;
            DefaultDesktop = defaultDesktop;
            ExactTopology = exactTopology;
            GameAbsent = gameAbsent;
        }

        internal readonly bool ActiveSession;
        internal readonly bool DefaultDesktop;
        internal readonly bool ExactTopology;
        internal readonly bool GameAbsent;

    }

    internal sealed class LockedPreflightLiveNative : IRuntimeLockedPreflightScenarioPort
    {
        private const uint SnapshotProcesses = 0x00000002;
        private const uint FileWriteData = 0x0002;
        private const uint FileReadAttributes = 0x0080;
        private const uint ReadControl = 0x00020000;
        private const uint Synchronize = 0x00100000;
        private const uint ShareRead = 0x00000001;
        private const uint FileCreate = 2;
        private const uint FileSynchronousIoNonAlert = 0x20;
        private const uint FileNonDirectoryFile = 0x40;
        private const uint FileOpenReparsePoint = 0x00200000;
        private static readonly IntPtr InvalidHandle = new IntPtr(-1);
        private readonly RuntimeLeaseUse lease;
        private readonly LockedPreflightBootstrapSnapshot snapshot;
        private readonly string sourceRevision;
        private readonly RuntimeScenarioPlan plan;
        private LockedPreflightObservation observation;
        private bool cleanupProofRequired;

        internal LockedPreflightLiveNative(RuntimeLeaseUse consumedLease,
            LockedPreflightBootstrapSnapshot boundSnapshot, string boundSourceRevision,
            RuntimeScenarioPlan boundPlan)
        {
            if (consumedLease == null)
                throw new ArgumentNullException("consumedLease");
            if (boundSnapshot == null)
                throw new ArgumentNullException("boundSnapshot");
            if (!RuntimeIdentity.IsLowerHexNonZero(boundSourceRevision, 40))
                throw new ArgumentException("sourceRevision");
            if (boundPlan == null || boundPlan.Role != RuntimeScenarioRole.LockedPreflight ||
                    !String.Equals(boundPlan.ScenarioId, consumedLease.ScenarioId,
                        StringComparison.Ordinal))
                throw new ArgumentException("boundPlan");
            lease = consumedLease;
            snapshot = boundSnapshot;
            sourceRevision = boundSourceRevision;
            plan = boundPlan;
        }

        public RuntimeScenarioRole Role
        {
            get { return RuntimeScenarioRole.LockedPreflight; }
        }

        public RuntimeScenarioStepResult Execute(RuntimeScenarioStage stage)
        {
            if (stage == RuntimeScenarioStage.StreamsAbsent)
                return Result(StandardStreamsAbsent(), RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.BindInputs)
            {
                bool rebound = RebindAllInputs();
                cleanupProofRequired = rebound;
                return Result(rebound, RuntimeCanonicalData.ExitBindingRejection);
            }
            if (stage == RuntimeScenarioStage.OutputsAbsent ||
                    stage == RuntimeScenarioStage.LockedNoArtifacts)
                return Result(RelativeNameAbsent("SyntheticLauncherWorkerEvidence.v1.json") &&
                    RelativeNameAbsent("SyntheticLauncherReport.v1.json") &&
                    RelativeNameAbsent(RuntimeCanonicalData.ReadyBmpName) &&
                    RelativeNameAbsent(RuntimeCanonicalData.CompleteBmpName),
                    RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.SessionDesktop)
            {
                if (!TryObserve(out observation))
                    return RuntimeScenarioStepResult.Failed(
                        RuntimeCanonicalData.ExitNativeCapabilityFailure);
                return Result(observation.ActiveSession && !observation.DefaultDesktop,
                    RuntimeCanonicalData.ExitBindingRejection);
            }
            if (stage == RuntimeScenarioStage.WorkerTopology)
                return Result(observation != null && observation.ExactTopology,
                    RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.LockedRefusal)
                return Result(observation != null && observation.GameAbsent,
                    RuntimeCanonicalData.ExitBindingRejection);
            if (stage == RuntimeScenarioStage.RebindInputs)
                return Result(RebindAllInputs(), RuntimeCanonicalData.ExitCleanupFailure);
            if (stage == RuntimeScenarioStage.WorkerPublish)
                return Result(PublishCreateNew(CanonicalEvidence()),
                    RuntimeCanonicalData.ExitReportFailure);
            return RuntimeScenarioStepResult.Failed(
                RuntimeCanonicalData.ExitBindingRejection);
        }

        public RuntimeScenarioStepResult Cleanup()
        {
            bool exact = !cleanupProofRequired || RebindAllInputs();
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
            return (output == IntPtr.Zero || output == InvalidHandle) &&
                (error == IntPtr.Zero || error == InvalidHandle);
        }

        private byte[] CanonicalEvidence()
        {
            string value = "{\"artifacts\":{\"complete_bmp\":\"absent\"," +
                "\"ready_bmp\":\"absent\"},\"bindings\":{\"build_manifest\":" +
                IdentityJson(snapshot.Objects["SyntheticLauncherBuildManifest.v1.json"]) +
                ",\"private_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.private.v1.json"]) +
                ",\"public_configuration\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherController.public.v1.json"]) +
                ",\"worker_image\":" + IdentityJson(snapshot.Objects[
                    "SyntheticLauncherLockedPreflight.exe"]) + "},\"evidence_kind\":\"worker\"," +
                "\"observations\":{\"binding_exact\":true,\"cleanup_exact\":true," +
                "\"controller_create_as_user_calls\":0," +
                "\"environment_exact\":\"not-applicable\",\"fallback_create_calls\":0," +
                "\"fixture_resume_calls\":0,\"guard_counts_exact\":true," +
                "\"inner_job_exact\":\"not-applicable\"," +
                "\"input_capture_exact\":\"not-applicable\"," +
                "\"locked_refusal_exact\":\"pass\"," +
                "\"parent_child_topology_exact\":true," +
                "\"registry_denied_exact\":\"not-applicable\"," +
                "\"session_desktop_exact\":\"pass\",\"streams_empty\":true," +
                "\"target_result\":\"locked-refusal\"," +
                "\"timeout_tree_exact\":\"not-applicable\"," +
                "\"token_relationship_exact\":\"not-applicable\"}," +
                "\"profile_id\":\"cm0102-synthetic-launcher-runtime-v1\"," +
                "\"scenario_id\":\"locked-refusal-v1\",\"schema_version\":1," +
                "\"source_revision\":\"" + sourceRevision + "\"}";
            return Encoding.UTF8.GetBytes(value + "\n");
        }

        private static string IdentityJson(LockedPreflightBoundObject value)
        {
            return "{\"byte_count\":" + value.Bytes.Length.ToString(CultureInfo.InvariantCulture) +
                ",\"sha256\":\"" + value.Sha256 + "\"}";
        }

        private static bool TryObserve(out LockedPreflightObservation observation)
        {
            observation = null;
            uint currentProcessId = GetCurrentProcessId();
            uint currentSession;
            if (!ProcessIdToSessionId(currentProcessId, out currentSession))
                return false;
            bool active = currentSession == WTSGetActiveConsoleSessionId();
            bool defaultDesktop;
            if (!TryDesktopIsDefault(out defaultDesktop))
                return false;
            Dictionary<string, int> counts = new Dictionary<string, int>(
                StringComparer.OrdinalIgnoreCase);
            string[] guarded = {
                "cm0102.exe", "SyntheticLauncherSupervisor.exe",
                "SyntheticLauncherController.exe", "SyntheticLauncherFixture.exe",
                "SyntheticLauncherTimeoutFixture.exe", "SyntheticLauncherTimeoutChild.exe",
                "SyntheticLauncherLockedPreflight.exe"
            };
            for (int index = 0; index < guarded.Length; index++) counts.Add(guarded[index], 0);
            uint parent = 0;
            uint supervisorProcessId = 0;
            IntPtr processSnapshot = CreateToolhelp32Snapshot(SnapshotProcesses, 0);
            if (processSnapshot == InvalidHandle)
                return false;
            bool complete = false;
            try
            {
                ProcessEntry entry = new ProcessEntry();
                entry.Size = (uint)Marshal.SizeOf(typeof(ProcessEntry));
                bool more = Process32FirstW(processSnapshot, ref entry);
                while (more)
                {
                    if (counts.ContainsKey(entry.ExecutableFile))
                        counts[entry.ExecutableFile] = counts[entry.ExecutableFile] + 1;
                    if (String.Equals(entry.ExecutableFile,
                            "SyntheticLauncherSupervisor.exe", StringComparison.OrdinalIgnoreCase))
                        supervisorProcessId = entry.ProcessId;
                    if (entry.ProcessId == currentProcessId)
                        parent = entry.ParentProcessId;
                    more = Process32NextW(processSnapshot, ref entry);
                    if (!more) complete = Marshal.GetLastWin32Error() == 18;
                }
            }
            finally { CloseHandle(processSnapshot); }
            if (!complete) return false;
            bool topology = counts["SyntheticLauncherSupervisor.exe"] == 1 &&
                counts["SyntheticLauncherLockedPreflight.exe"] == 1 &&
                parent == supervisorProcessId && parent != 0 &&
                counts["SyntheticLauncherController.exe"] == 0 &&
                counts["SyntheticLauncherFixture.exe"] == 0 &&
                counts["SyntheticLauncherTimeoutFixture.exe"] == 0 &&
                counts["SyntheticLauncherTimeoutChild.exe"] == 0;
            observation = new LockedPreflightObservation(active, defaultDesktop, topology,
                counts["cm0102.exe"] == 0);
            return true;
        }

        private static bool TryDesktopIsDefault(out bool isDefault)
        {
            isDefault = false;
            IntPtr desktop = OpenInputDesktop(0, false, 0x0001);
            if (desktop == IntPtr.Zero)
                return false;
            try
            {
                int required;
                GetUserObjectInformationW(desktop, 2, IntPtr.Zero, 0, out required);
                if (required <= 2 || required > 1024)
                    return false;
                IntPtr buffer = Marshal.AllocHGlobal(required);
                try
                {
                    if (!GetUserObjectInformationW(desktop, 2, buffer, required, out required))
                        return false;
                    string name = Marshal.PtrToStringUni(buffer);
                    isDefault = String.Equals(name, "Default", StringComparison.Ordinal);
                    return true;
                }
                finally { Marshal.FreeHGlobal(buffer); }
            }
            finally { CloseDesktop(desktop); }
        }

        private bool PublishCreateNew(byte[] bytes)
        {
            IntPtr name = Marshal.StringToHGlobalUni("SyntheticLauncherWorkerEvidence.v1.json");
            IntPtr unicodePointer = IntPtr.Zero;
            IntPtr handle = InvalidHandle;
            try
            {
                UnicodeString unicode = new UnicodeString();
                unicode.Length = checked((ushort)("SyntheticLauncherWorkerEvidence.v1.json".Length * 2));
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
                long allocation = 0;
                int status = NtCreateFile(out handle,
                    FileWriteData | FileReadAttributes | ReadControl | Synchronize,
                    ref attributes, out statusBlock, ref allocation, 0, ShareRead,
                    FileCreate, FileNonDirectoryFile | FileSynchronousIoNonAlert |
                        FileOpenReparsePoint, IntPtr.Zero, 0);
                if (status < 0 || handle == InvalidHandle)
                    return false;
                uint written;
                return WriteFile(handle, bytes, (uint)bytes.Length, out written, IntPtr.Zero) &&
                    written == bytes.Length && FlushFileBuffers(handle) &&
                    ExactCreatedObject(handle, bytes);
            }
            finally
            {
                if (handle != InvalidHandle) CloseHandle(handle);
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(name);
            }
        }

        private bool RebindAllInputs()
        {
            if (!RebindParent()) return false;
            foreach (KeyValuePair<string, LockedPreflightBoundObject> item in snapshot.Objects)
            {
                IntPtr handle = OpenRelativeExisting(item.Key);
                if (handle == InvalidHandle) return false;
                try
                {
                    if (!ExactBoundObject(handle, item.Value)) return false;
                }
                finally { CloseHandle(handle); }
            }
            return true;
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

        private IntPtr OpenRelativeExisting(string leaf)
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
                    0x0001 | FileReadAttributes | ReadControl | Synchronize,
                    ref attributes, out statusBlock, ref allocation, 0,
                    ShareRead, 1, FileNonDirectoryFile |
                        FileSynchronousIoNonAlert | FileOpenReparsePoint,
                    IntPtr.Zero, 0);
                return status < 0 ? InvalidHandle : handle;
            }
            finally
            {
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(name);
            }
        }

        private bool RelativeNameAbsent(string leaf)
        {
            IntPtr name = Marshal.StringToHGlobalUni(leaf);
            IntPtr unicodePointer = IntPtr.Zero;
            IntPtr handle = InvalidHandle;
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
                long allocation = 0;
                int status = NtCreateFile(out handle,
                    FileReadAttributes | ReadControl | Synchronize, ref attributes,
                    out statusBlock, ref allocation, 0, ShareRead, 1,
                    FileNonDirectoryFile | FileSynchronousIoNonAlert | FileOpenReparsePoint,
                    IntPtr.Zero, 0);
                if (status >= 0)
                {
                    CloseHandle(handle);
                    handle = InvalidHandle;
                    return false;
                }
                return status == unchecked((int)0xc0000034);
            }
            finally
            {
                if (handle != InvalidHandle) CloseHandle(handle);
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(name);
            }
        }

        private bool ExactBoundObject(IntPtr handle, LockedPreflightBoundObject expected)
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
            return exact;
        }

        private bool ExactCreatedObject(IntPtr handle, byte[] bytes)
        {
            ByHandleFileInformation information;
            LockedPreflightBoundObject inheritedFrom = snapshot.Objects[
                "SyntheticLauncherController.private.v1.json"];
            long size;
            return GetFileInformationByHandle(handle, out information) &&
                GetFileSizeEx(handle, out size) && size == bytes.Length &&
                information.VolumeSerialNumber == inheritedFrom.VolumeSerial &&
                information.NumberOfLinks == 1 &&
                (information.FileAttributes & (0x10 | 0x400 | 0x800 | 0x4000)) == 0 &&
                String.Equals(FinalPath(handle), snapshot.ParentFinalPath +
                    "\\SyntheticLauncherWorkerEvidence.v1.json", StringComparison.Ordinal) &&
                OnlyUnnamedStream(handle) && EqualBytes(SecurityDescriptor(handle),
                    inheritedFrom.SecurityDescriptor);
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
        private struct ProcessEntry
        {
            internal uint Size;
            internal uint Usage;
            internal uint ProcessId;
            internal IntPtr DefaultHeapId;
            internal uint ModuleId;
            internal uint Threads;
            internal uint ParentProcessId;
            internal int PriorityClassBase;
            internal uint Flags;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)]
            internal string ExecutableFile;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct UnicodeString
        {
            internal ushort Length;
            internal ushort MaximumLength;
            internal IntPtr Buffer;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct ObjectAttributes
        {
            internal int Length;
            internal IntPtr RootDirectory;
            internal IntPtr ObjectName;
            internal uint Attributes;
            internal IntPtr SecurityDescriptor;
            internal IntPtr SecurityQualityOfService;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct IoStatusBlock
        {
            internal IntPtr Status;
            internal IntPtr Information;
        }
        [StructLayout(LayoutKind.Sequential, Pack = 4, Size = 52)]
        private struct ByHandleFileInformation
        {
            internal uint FileAttributes; internal long CreationTime;
            internal long LastAccessTime; internal long LastWriteTime;
            internal uint VolumeSerialNumber; internal uint FileSizeHigh;
            internal uint FileSizeLow; internal uint NumberOfLinks;
            internal uint FileIndexHigh; internal uint FileIndexLow;
        }

        [DllImport("kernel32.dll")]
        private static extern uint GetCurrentProcessId();
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr GetStdHandle(int standardHandle);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ProcessIdToSessionId(uint processId, out uint sessionId);
        [DllImport("kernel32.dll")]
        private static extern uint WTSGetActiveConsoleSessionId();
        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint access);
        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool GetUserObjectInformationW(IntPtr handle, int index,
            IntPtr information, int length, out int required);
        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool CloseDesktop(IntPtr desktop);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateToolhelp32Snapshot(uint flags, uint processId);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool Process32FirstW(IntPtr snapshot, ref ProcessEntry entry);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool Process32NextW(IntPtr snapshot, ref ProcessEntry entry);
        [DllImport("ntdll.dll")]
        private static extern int NtCreateFile(out IntPtr handle, uint access,
            ref ObjectAttributes attributes, out IoStatusBlock statusBlock, ref long allocationSize,
            uint fileAttributes, uint share, uint disposition, uint options,
            IntPtr extendedAttributes, uint extendedAttributesLength);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool WriteFile(IntPtr handle, byte[] buffer, uint count,
            out uint written, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ReadFile(IntPtr handle, byte[] buffer, uint count,
            out uint read, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileInformationByHandle(IntPtr handle,
            out ByHandleFileInformation information);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileSizeEx(IntPtr handle, out long size);
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
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool FlushFileBuffers(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);
    }
}
