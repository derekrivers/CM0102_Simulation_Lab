using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;

namespace Cm0102.SyntheticLauncherRuntime
{
    internal sealed class ControllerBoundObject
    {
        internal ControllerBoundObject(string leafName, byte[] bytes, string finalPath,
            uint volumeSerial, uint fileIndexHigh, uint fileIndexLow, uint linkCount,
            uint attributes, byte[] securityDescriptor, bool onlyUnnamedDataStream,
            bool stable)
        {
            LeafName = leafName;
            Bytes = bytes;
            FinalPath = finalPath;
            VolumeSerial = volumeSerial;
            FileIndexHigh = fileIndexHigh;
            FileIndexLow = fileIndexLow;
            LinkCount = linkCount;
            Attributes = attributes;
            SecurityDescriptor = securityDescriptor;
            OnlyUnnamedDataStream = onlyUnnamedDataStream;
            Stable = stable;
            using (SHA256 hash = SHA256.Create())
            {
                Sha256 = ToHex(hash.ComputeHash(bytes));
            }
        }

        internal readonly string LeafName;
        internal readonly byte[] Bytes;
        internal readonly string FinalPath;
        internal readonly uint VolumeSerial;
        internal readonly uint FileIndexHigh;
        internal readonly uint FileIndexLow;
        internal readonly uint LinkCount;
        internal readonly uint Attributes;
        internal readonly byte[] SecurityDescriptor;
        internal readonly bool OnlyUnnamedDataStream;
        internal readonly bool Stable;
        internal readonly string Sha256;

        private static string ToHex(byte[] value)
        {
            StringBuilder result = new StringBuilder(value.Length * 2);
            for (int index = 0; index < value.Length; index++)
                result.Append(value[index].ToString("x2"));
            return result.ToString();
        }
    }

    internal sealed class ControllerBootstrapSnapshot : IDisposable
    {
        internal ControllerBootstrapSnapshot(IntPtr selfHandle, IntPtr parentHandle, string parentFinalPath,
            string fileSystemName, string ownerBinding, uint parentVolumeSerial,
            uint parentFileIndexHigh, uint parentFileIndexLow, uint parentLinkCount,
            uint parentAttributes, byte[] parentSecurityDescriptor, bool exactObjectSafety,
            bool pairwiseDistinctObjects, bool stableBindings,
            IDictionary<string, ControllerBoundObject> objects)
        {
            SelfHandle = selfHandle;
            ParentHandle = parentHandle;
            ParentFinalPath = parentFinalPath;
            FileSystemName = fileSystemName;
            OwnerBinding = ownerBinding;
            ParentVolumeSerial = parentVolumeSerial;
            ParentFileIndexHigh = parentFileIndexHigh;
            ParentFileIndexLow = parentFileIndexLow;
            ParentLinkCount = parentLinkCount;
            ParentAttributes = parentAttributes;
            ParentSecurityDescriptor = (byte[])parentSecurityDescriptor.Clone();
            ExactObjectSafety = exactObjectSafety;
            PairwiseDistinctObjects = pairwiseDistinctObjects;
            StableBindings = stableBindings;
            Objects = new Dictionary<string, ControllerBoundObject>(objects,
                StringComparer.Ordinal);
        }

        internal IntPtr SelfHandle { get; private set; }
        internal IntPtr ParentHandle { get; private set; }
        internal readonly string ParentFinalPath;
        internal readonly string FileSystemName;
        internal readonly string OwnerBinding;
        internal readonly uint ParentVolumeSerial;
        internal readonly uint ParentFileIndexHigh;
        internal readonly uint ParentFileIndexLow;
        internal readonly uint ParentLinkCount;
        internal readonly uint ParentAttributes;
        internal readonly byte[] ParentSecurityDescriptor;
        internal readonly bool ExactObjectSafety;
        internal readonly bool PairwiseDistinctObjects;
        internal readonly bool StableBindings;
        internal readonly IDictionary<string, ControllerBoundObject> Objects;

        public void Dispose()
        {
            if (SelfHandle != IntPtr.Zero && SelfHandle != new IntPtr(-1))
            {
                ControllerBootstrapNative.CloseHandle(SelfHandle);
                SelfHandle = IntPtr.Zero;
            }
            if (ParentHandle != IntPtr.Zero && ParentHandle != new IntPtr(-1))
            {
                ControllerBootstrapNative.CloseHandle(ParentHandle);
                ParentHandle = IntPtr.Zero;
            }
        }
    }

    internal static class ControllerBootstrapNative
    {
        private const uint GenericRead = 0x80000000;
        private const uint FileReadAttributes = 0x80;
        private const uint FileReadData = 0x0001;
        private const uint ReadControl = 0x00020000;
        private const uint Synchronize = 0x00100000;
        private const uint ShareRead = 0x00000001;
        private const uint OpenExisting = 3;
        private const uint BackupSemantics = 0x02000000;
        private const uint OpenReparsePoint = 0x00200000;
        private const uint SecurityInformation = 0x00000007;
        private const uint FileOpen = 1;
        private const uint FileSynchronousIoNonAlert = 0x20;
        private const uint FileNonDirectoryFile = 0x40;
        private const int FileStreamInfo = 7;
        private const int MaximumBoundBytes = 16 * 1024 * 1024;
        private static readonly IntPtr InvalidHandle = new IntPtr(-1);

        private static readonly string[] RequiredLeaves = {
            "SyntheticLauncherSupervisor.exe", "SyntheticLauncherController.exe",
            "SyntheticLauncherLockedPreflight.exe", "SyntheticLauncherTimeoutFixture.exe",
            "SyntheticLauncherTimeoutChild.exe", "SyntheticLauncherFixture.exe",
            "SyntheticLauncherBuildManifest.v1.json",
            "SyntheticLauncherController.public.v1.json",
            "SyntheticLauncherController.private.v1.json"
        };

        internal static bool TryCapture(out ControllerBootstrapSnapshot snapshot)
        {
            snapshot = null;
            IntPtr image = InvalidHandle;
            IntPtr parent = InvalidHandle;
            IntPtr current = InvalidHandle;
            try
            {
                string modulePath = ModulePath();
                image = CreateFileW(modulePath, GenericRead | ReadControl,
                    ShareRead, IntPtr.Zero, OpenExisting, OpenReparsePoint, IntPtr.Zero);
                if (image == InvalidHandle)
                    return false;
                string imageFinal = FinalPath(image);
                if (!HasExactLeaf(imageFinal, "SyntheticLauncherController.exe"))
                    return false;
                string parentPath = ParentPath(imageFinal);
                parent = CreateFileW(parentPath, FileReadAttributes | ReadControl,
                    ShareRead, IntPtr.Zero, OpenExisting,
                    BackupSemantics | OpenReparsePoint, IntPtr.Zero);
                if (parent == InvalidHandle)
                    return false;
                string parentFinal = FinalPath(parent);
                string currentPath = CurrentDirectoryPath();
                current = CreateFileW(currentPath, FileReadAttributes | ReadControl,
                    ShareRead, IntPtr.Zero, OpenExisting,
                    BackupSemantics | OpenReparsePoint, IntPtr.Zero);
                if (current == InvalidHandle || !SameObject(parent, current) ||
                    !String.Equals(parentFinal, FinalPath(current), StringComparison.OrdinalIgnoreCase))
                    return false;
                string fileSystem = FileSystemName(parent);
                if (!String.Equals(fileSystem, "NTFS", StringComparison.Ordinal))
                    return false;

                Dictionary<string, ControllerBoundObject> objects =
                    new Dictionary<string, ControllerBoundObject>(StringComparer.Ordinal);
                for (int index = 0; index < RequiredLeaves.Length; index++)
                {
                    string leaf = RequiredLeaves[index];
                    IntPtr handle = String.Equals(leaf, "SyntheticLauncherController.exe",
                        StringComparison.Ordinal) ? image : OpenRelativeRead(parent, leaf);
                    if (handle == InvalidHandle)
                        return false;
                    bool close = handle != image;
                    try
                    {
                        ControllerBoundObject value;
                        if (!TryReadBound(handle, leaf, out value))
                            return false;
                        objects.Add(leaf, value);
                    }
                    finally
                    {
                        if (close)
                            CloseHandle(handle);
                    }
                }
                ByHandleFileInformation parentInformation;
                byte[] parentSecurityDescriptor = SecurityDescriptor(parent);
                bool exactSafety = GetFileInformationByHandle(parent, out parentInformation) &&
                    parentInformation.NumberOfLinks == 1 &&
                    (parentInformation.FileAttributes & (0x400U | 0x800U | 0x4000U)) == 0 &&
                    HasNoNamedDataStreams(parent) &&
                    ExactProtectedAcl(parentSecurityDescriptor, true);
                bool distinct = true;
                bool stable = true;
                HashSet<string> identities = new HashSet<string>(StringComparer.Ordinal);
                foreach (ControllerBoundObject value in objects.Values)
                {
                    exactSafety = exactSafety && value.LinkCount == 1 &&
                        (value.Attributes & (0x400U | 0x800U | 0x4000U)) == 0 &&
                        value.OnlyUnnamedDataStream &&
                        ExactProtectedAcl(value.SecurityDescriptor, false);
                    stable = stable && value.Stable;
                    distinct = distinct && identities.Add(value.VolumeSerial.ToString("x8") + ":" +
                        value.FileIndexHigh.ToString("x8") + value.FileIndexLow.ToString("x8"));
                }
                snapshot = new ControllerBootstrapSnapshot(image, parent, parentFinal, fileSystem,
                    OwnerBinding(parent), parentInformation.VolumeSerialNumber,
                    parentInformation.FileIndexHigh, parentInformation.FileIndexLow,
                    parentInformation.NumberOfLinks, parentInformation.FileAttributes,
                    parentSecurityDescriptor, exactSafety, distinct, stable, objects);
                image = InvalidHandle;
                parent = InvalidHandle;
                return true;
            }
            catch (Exception)
            {
                return false;
            }
            finally
            {
                if (current != InvalidHandle) CloseHandle(current);
                if (parent != InvalidHandle) CloseHandle(parent);
                if (image != InvalidHandle) CloseHandle(image);
            }
        }

        private static bool TryReadBound(IntPtr handle, string leaf,
            out ControllerBoundObject value)
        {
            value = null;
            ByHandleFileInformation before;
            ByHandleFileInformation after;
            if (!GetFileInformationByHandle(handle, out before) ||
                (before.FileAttributes & 0x400) != 0 || before.NumberOfLinks != 1)
                return false;
            string finalBefore = FinalPath(handle);
            if (!HasExactLeaf(finalBefore, leaf))
                return false;
            long size = ((long)before.FileSizeHigh << 32) | before.FileSizeLow;
            if (size < 0 || size > MaximumBoundBytes)
                return false;
            byte[] bytes = new byte[(int)size];
            int offset = 0;
            byte[] chunk = new byte[65536];
            while (offset < bytes.Length)
            {
                uint read;
                int count = Math.Min(chunk.Length, bytes.Length - offset);
                if (!ReadFile(handle, chunk, (uint)count, out read, IntPtr.Zero) ||
                    read == 0 || read > count)
                    return false;
                Buffer.BlockCopy(chunk, 0, bytes, offset, (int)read);
                offset += (int)read;
            }
            byte[] descriptor = SecurityDescriptor(handle);
            bool streams = HasOnlyUnnamedDataStream(handle);
            if (!GetFileInformationByHandle(handle, out after))
                return false;
            string finalAfter = FinalPath(handle);
            bool stable = SameInformation(before, after) &&
                String.Equals(finalBefore, finalAfter, StringComparison.Ordinal);
            value = new ControllerBoundObject(leaf, bytes, finalAfter,
                before.VolumeSerialNumber, before.FileIndexHigh, before.FileIndexLow,
                before.NumberOfLinks, before.FileAttributes, descriptor, streams, stable);
            return stable && descriptor.Length != 0 && streams;
        }

        private static IntPtr OpenRelativeRead(IntPtr parent, string leaf)
        {
            IntPtr text = Marshal.StringToHGlobalUni(leaf);
            IntPtr unicodePointer = IntPtr.Zero;
            try
            {
                UnicodeString unicode = new UnicodeString();
                unicode.Length = checked((ushort)(leaf.Length * 2));
                unicode.MaximumLength = unicode.Length;
                unicode.Buffer = text;
                unicodePointer = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(UnicodeString)));
                Marshal.StructureToPtr(unicode, unicodePointer, false);
                ObjectAttributes attributes = new ObjectAttributes();
                attributes.Length = Marshal.SizeOf(typeof(ObjectAttributes));
                attributes.RootDirectory = parent;
                attributes.ObjectName = unicodePointer;
                attributes.Attributes = 0x40;
                IoStatusBlock statusBlock;
                IntPtr handle;
                long allocation = 0;
                int status = NtCreateFile(out handle,
                    FileReadData | FileReadAttributes | ReadControl | Synchronize,
                    ref attributes, out statusBlock, ref allocation, 0,
                    ShareRead, FileOpen,
                    FileNonDirectoryFile | FileSynchronousIoNonAlert | OpenReparsePoint,
                    IntPtr.Zero, 0);
                return status < 0 ? InvalidHandle : handle;
            }
            finally
            {
                if (unicodePointer != IntPtr.Zero) Marshal.FreeHGlobal(unicodePointer);
                Marshal.FreeHGlobal(text);
            }
        }

        private static bool HasOnlyUnnamedDataStream(IntPtr handle)
        {
            IntPtr buffer = Marshal.AllocHGlobal(65536);
            try
            {
                if (!GetFileInformationByHandleEx(handle, FileStreamInfo, buffer, 65536))
                    return false;
                int next = Marshal.ReadInt32(buffer, 0);
                int nameLength = Marshal.ReadInt32(buffer, 4);
                if (next != 0 || nameLength != 14)
                    return false;
                string name = Marshal.PtrToStringUni(new IntPtr(buffer.ToInt64() + 24), 7);
                return String.Equals(name, "::$DATA", StringComparison.Ordinal);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static bool HasNoNamedDataStreams(IntPtr handle)
        {
            IntPtr buffer = Marshal.AllocHGlobal(65536);
            try
            {
                if (!GetFileInformationByHandleEx(handle, FileStreamInfo, buffer, 65536))
                    return false;
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
            uint result = GetSecurityInfo(handle, 1, SecurityInformation,
                out owner, out group, out dacl, out sacl, out descriptor);
            if (result != 0 || descriptor == IntPtr.Zero)
                return new byte[0];
            try
            {
                uint length = GetSecurityDescriptorLength(descriptor);
                if (length == 0 || length > 65536)
                    return new byte[0];
                byte[] bytes = new byte[(int)length];
                Marshal.Copy(descriptor, bytes, 0, bytes.Length);
                return bytes;
            }
            finally { LocalFree(descriptor); }
        }

        private static string ModulePath()
        {
            StringBuilder value = new StringBuilder(32768);
            uint length = GetModuleFileNameW(IntPtr.Zero, value, value.Capacity);
            if (length == 0 || length >= value.Capacity)
                throw new InvalidOperationException();
            return value.ToString();
        }

        private static string CurrentDirectoryPath()
        {
            StringBuilder value = new StringBuilder(32768);
            uint length = GetCurrentDirectoryW(value.Capacity, value);
            if (length == 0 || length >= value.Capacity)
                throw new InvalidOperationException();
            return value.ToString();
        }

        private static string FinalPath(IntPtr handle)
        {
            StringBuilder value = new StringBuilder(32768);
            uint length = GetFinalPathNameByHandleW(handle, value, value.Capacity, 0);
            if (length == 0 || length >= value.Capacity)
                throw new InvalidOperationException();
            return value.ToString();
        }

        private static string ParentPath(string value)
        {
            int separator = value.LastIndexOf('\\');
            if (separator <= 3)
                throw new InvalidOperationException();
            return value.Substring(0, separator);
        }

        private static bool HasExactLeaf(string path, string leaf)
        {
            int separator = path.LastIndexOf('\\');
            return separator >= 0 && String.Equals(path.Substring(separator + 1), leaf,
                StringComparison.Ordinal);
        }

        private static string FileSystemName(IntPtr handle)
        {
            StringBuilder name = new StringBuilder(64);
            uint serial;
            uint maximum;
            uint flags;
            if (!GetVolumeInformationByHandleW(handle, null, 0, out serial, out maximum,
                out flags, name, name.Capacity))
                throw new InvalidOperationException();
            return name.ToString();
        }

        private static bool SameObject(IntPtr first, IntPtr second)
        {
            ByHandleFileInformation left;
            ByHandleFileInformation right;
            return GetFileInformationByHandle(first, out left) &&
                GetFileInformationByHandle(second, out right) &&
                left.VolumeSerialNumber == right.VolumeSerialNumber &&
                left.FileIndexHigh == right.FileIndexHigh && left.FileIndexLow == right.FileIndexLow;
        }

        private static string OwnerBinding(IntPtr parent)
        {
            ByHandleFileInformation information;
            if (!GetFileInformationByHandle(parent, out information))
                throw new InvalidOperationException();
            byte[] descriptor = SecurityDescriptor(parent);
            if (descriptor.Length == 0)
                throw new InvalidOperationException();
            byte[] value = new byte[descriptor.Length + 12];
            Buffer.BlockCopy(descriptor, 0, value, 0, descriptor.Length);
            Buffer.BlockCopy(BitConverter.GetBytes(information.VolumeSerialNumber), 0,
                value, descriptor.Length, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(information.FileIndexHigh), 0,
                value, descriptor.Length + 4, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(information.FileIndexLow), 0,
                value, descriptor.Length + 8, 4);
            using (SHA256 hash = SHA256.Create())
            {
                byte[] digest = hash.ComputeHash(value);
                StringBuilder result = new StringBuilder(64);
                for (int index = 0; index < digest.Length; index++)
                    result.Append(digest[index].ToString("x2"));
                return result.ToString();
            }
        }

        private static bool ExactProtectedAcl(byte[] descriptor, bool directory)
        {
            if (descriptor == null || descriptor.Length < 28 || descriptor[0] != 1)
                return false;
            ushort control = BitConverter.ToUInt16(descriptor, 2);
            if ((control & 0x0004) != 0x0004 ||
                    ((control & 0x1000) != 0) != directory)
                return false;
            int ownerOffset = BitConverter.ToInt32(descriptor, 4);
            int daclOffset = BitConverter.ToInt32(descriptor, 16);
            byte[] owner;
            if (!TryReadSid(descriptor, ownerOffset, out owner) || daclOffset < 20 ||
                    daclOffset + 8 > descriptor.Length)
                return false;
            ushort aclSize = BitConverter.ToUInt16(descriptor, daclOffset + 2);
            ushort aceCount = BitConverter.ToUInt16(descriptor, daclOffset + 4);
            if (aceCount != 2 || daclOffset + aclSize != descriptor.Length)
                return false;
            int cursor = daclOffset + 8;
            byte[] firstSid;
            byte[] secondSid;
            if (!TryReadAllowAce(descriptor, ref cursor, directory, out firstSid) ||
                    !IsLocalSystem(firstSid) ||
                    !TryReadAllowAce(descriptor, ref cursor, directory, out secondSid) ||
                    cursor != descriptor.Length || !EqualBytes(owner, secondSid))
                return false;
            return true;
        }

        private static bool TryReadAllowAce(byte[] descriptor, ref int cursor, bool directory,
            out byte[] sid)
        {
            sid = null;
            if (cursor < 0 || cursor + 8 > descriptor.Length || descriptor[cursor] != 0)
                return false;
            byte flags = descriptor[cursor + 1];
            byte expectedFlags = directory ? (byte)0x03 : (byte)0x10;
            if (flags != expectedFlags)
                return false;
            ushort size = BitConverter.ToUInt16(descriptor, cursor + 2);
            uint mask = BitConverter.ToUInt32(descriptor, cursor + 4);
            if (size < 20 || cursor + size > descriptor.Length || mask != 0x001f01ff)
                return false;
            if (!TryReadSid(descriptor, cursor + 8, out sid) || sid.Length + 8 != size)
                return false;
            cursor += size;
            return true;
        }

        private static bool TryReadSid(byte[] descriptor, int offset, out byte[] sid)
        {
            sid = null;
            if (offset <= 0 || offset + 8 > descriptor.Length || descriptor[offset] != 1)
                return false;
            int length = 8 + descriptor[offset + 1] * 4;
            if (length < 12 || offset + length > descriptor.Length)
                return false;
            sid = new byte[length];
            Buffer.BlockCopy(descriptor, offset, sid, 0, length);
            return true;
        }

        private static bool IsLocalSystem(byte[] sid)
        {
            return sid != null && sid.Length == 12 && sid[0] == 1 && sid[1] == 1 &&
                sid[2] == 0 && sid[3] == 0 && sid[4] == 0 && sid[5] == 0 && sid[6] == 0 &&
                sid[7] == 5 && BitConverter.ToUInt32(sid, 8) == 18;
        }

        private static bool EqualBytes(byte[] first, byte[] second)
        {
            if (first == null || second == null || first.Length != second.Length)
                return false;
            for (int index = 0; index < first.Length; index++)
                if (first[index] != second[index]) return false;
            return true;
        }

        private static bool SameInformation(ByHandleFileInformation first,
            ByHandleFileInformation second)
        {
            return first.FileAttributes == second.FileAttributes &&
                first.CreationTime == second.CreationTime &&
                first.LastAccessTime == second.LastAccessTime &&
                first.LastWriteTime == second.LastWriteTime &&
                first.VolumeSerialNumber == second.VolumeSerialNumber &&
                first.FileSizeHigh == second.FileSizeHigh && first.FileSizeLow == second.FileSizeLow &&
                first.NumberOfLinks == second.NumberOfLinks &&
                first.FileIndexHigh == second.FileIndexHigh && first.FileIndexLow == second.FileIndexLow;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct ByHandleFileInformation
        {
            internal uint FileAttributes;
            internal long CreationTime;
            internal long LastAccessTime;
            internal long LastWriteTime;
            internal uint VolumeSerialNumber;
            internal uint FileSizeHigh;
            internal uint FileSizeLow;
            internal uint NumberOfLinks;
            internal uint FileIndexHigh;
            internal uint FileIndexLow;
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

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetModuleFileNameW(IntPtr module, StringBuilder path, int size);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetCurrentDirectoryW(int size, StringBuilder path);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateFileW(string name, uint access, uint share,
            IntPtr security, uint creation, uint flags, IntPtr template);
        [DllImport("ntdll.dll")]
        private static extern int NtCreateFile(out IntPtr handle, uint access,
            ref ObjectAttributes attributes, out IoStatusBlock statusBlock, ref long allocationSize,
            uint fileAttributes, uint share, uint disposition, uint options,
            IntPtr extendedAttributes, uint extendedAttributesLength);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ReadFile(IntPtr handle, [Out] byte[] buffer, uint count,
            out uint read, IntPtr overlapped);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetFinalPathNameByHandleW(IntPtr handle, StringBuilder path,
            int size, uint flags);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileInformationByHandle(IntPtr handle,
            out ByHandleFileInformation information);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetFileInformationByHandleEx(IntPtr handle, int informationClass,
            IntPtr information, uint size);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool GetVolumeInformationByHandleW(IntPtr handle,
            StringBuilder volumeName, int volumeNameSize, out uint serial, out uint maximumNameLength,
            out uint flags, StringBuilder fileSystemName, int fileSystemNameSize);
        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern uint GetSecurityInfo(IntPtr handle, uint objectType,
            uint securityInformation, out IntPtr owner, out IntPtr group, out IntPtr dacl,
            out IntPtr sacl, out IntPtr securityDescriptor);
        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern uint GetSecurityDescriptorLength(IntPtr securityDescriptor);
        [DllImport("kernel32.dll")]
        private static extern IntPtr LocalFree(IntPtr memory);
        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern bool CloseHandle(IntPtr handle);
    }
}
