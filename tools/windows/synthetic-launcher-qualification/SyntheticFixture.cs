using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

namespace Cm0102.SyntheticLauncherQualification
{
    internal enum FixtureState
    {
        Ready = 1,
        Complete = 2,
        Fault = 3
    }

    internal sealed class FixtureConfiguration
    {
        internal const string CwdHashName = "CM0102_SYNTHETIC_CWD_SHA256";
        internal const string InputNonceName = "CM0102_SYNTHETIC_INPUT_NONCE";

        internal static readonly string[] AllowedEnvironmentNames = new string[]
        {
            CwdHashName,
            InputNonceName,
            "SystemRoot",
            "TEMP",
            "TMP",
            "WINDIR"
        };

        internal uint InputNonce;

        internal static FixtureConfiguration FromCurrentProcess()
        {
            IDictionary raw = Environment.GetEnvironmentVariables();
            Dictionary<string, string> values = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (DictionaryEntry entry in raw)
            {
                string name = entry.Key as string;
                string value = entry.Value as string;
                if (name == null || value == null || values.ContainsKey(name))
                    throw new InvalidOperationException("invalid-environment");
                values.Add(name, value);
            }
            return Parse(values, Environment.CurrentDirectory, Environment.GetCommandLineArgs().Length);
        }

        internal static FixtureConfiguration Parse(IDictionary<string, string> values, string currentDirectory,
            int commandLineArgumentCount)
        {
            if (values == null || currentDirectory == null || commandLineArgumentCount != 1)
                throw new InvalidOperationException("invalid-process-shape");
            if (values.Count != AllowedEnvironmentNames.Length)
                throw new InvalidOperationException("environment-count");
            foreach (string name in AllowedEnvironmentNames)
                if (!values.ContainsKey(name)) throw new InvalidOperationException("environment-name");
            foreach (string name in values.Keys)
            {
                bool found = false;
                foreach (string allowed in AllowedEnvironmentNames)
                    if (String.Equals(name, allowed, StringComparison.Ordinal)) found = true;
                if (!found) throw new InvalidOperationException("environment-extra");
            }

            string expectedCwd = values[CwdHashName];
            if (!IsLowerHex(expectedCwd, 64) ||
                !String.Equals(expectedCwd, Sha256Utf16(currentDirectory), StringComparison.Ordinal))
                throw new InvalidOperationException("working-directory");

            string nonceText = values[InputNonceName];
            uint nonce;
            if (!IsLowerHex(nonceText, 8) ||
                !UInt32.TryParse(nonceText, NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture, out nonce) ||
                nonce == 0)
                throw new InvalidOperationException("input-nonce");

            string systemRoot = values["SystemRoot"];
            string windowsDirectory = values["WINDIR"];
            string temporary = values["TEMP"];
            string temporaryAlias = values["TMP"];
            if (!IsPlainEnvironmentValue(systemRoot) || !IsPlainEnvironmentValue(windowsDirectory) ||
                !IsPlainEnvironmentValue(temporary) || !IsPlainEnvironmentValue(temporaryAlias) ||
                !String.Equals(systemRoot, windowsDirectory, StringComparison.OrdinalIgnoreCase) ||
                !String.Equals(temporary, temporaryAlias, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("environment-value");

            FixtureConfiguration result = new FixtureConfiguration();
            result.InputNonce = nonce;
            return result;
        }

        internal static string Sha256Utf16(string value)
        {
            using (SHA256 sha = SHA256.Create())
            {
                byte[] digest = sha.ComputeHash(Encoding.Unicode.GetBytes(value));
                StringBuilder text = new StringBuilder(64);
                foreach (byte item in digest)
                    text.Append(item.ToString("x2", CultureInfo.InvariantCulture));
                return text.ToString();
            }
        }

        private static bool IsLowerHex(string value, int length)
        {
            if (value == null || value.Length != length) return false;
            foreach (char item in value)
                if (!((item >= '0' && item <= '9') || (item >= 'a' && item <= 'f'))) return false;
            return true;
        }

        private static bool IsPlainEnvironmentValue(string value)
        {
            return !String.IsNullOrEmpty(value) && value.IndexOf('\0') < 0 &&
                value.IndexOf('\r') < 0 && value.IndexOf('\n') < 0;
        }
    }

    internal sealed class TokenFacts
    {
        internal int IntegrityRid;
        internal int ElevationType;
        internal bool IsElevated;
        internal bool IsAdministrator;
        internal uint ProcessSessionId;
        internal uint ActiveConsoleSessionId;
        internal string InputDesktopName;
    }

    internal static class TokenPolicy
    {
        internal const int MediumIntegrityRid = 0x2000;
        internal const int TokenElevationTypeLimited = 3;

        internal static bool IsSafe(TokenFacts facts)
        {
            return facts != null && facts.IntegrityRid == MediumIntegrityRid &&
                facts.ElevationType == TokenElevationTypeLimited && !facts.IsElevated &&
                !facts.IsAdministrator &&
                facts.ActiveConsoleSessionId != UInt32.MaxValue &&
                facts.ProcessSessionId == facts.ActiveConsoleSessionId &&
                String.Equals(facts.InputDesktopName, "Default", StringComparison.Ordinal);
        }
    }

    internal static class FixtureProtocol
    {
        internal const int ClientWidth = 320;
        internal const int ClientHeight = 240;
        internal const int WindowX = 64;
        internal const int WindowY = 64;
        internal const int ExpectedInputX = 96;
        internal const int ExpectedInputY = 112;
        internal const int ProtocolQueryMessage = 0x8051;
        internal const int StateQueryMessage = 0x8052;
        internal const int ProtocolMagic = 0x434D0101;
    }

    internal static class DisplayPolicy
    {
        internal const bool RequireProcessDpiAware = true;

        internal static bool IsSupportedBounds(int width, int height)
        {
            return width >= FixtureProtocol.WindowX + FixtureProtocol.ClientWidth + 16 &&
                height >= FixtureProtocol.WindowY + FixtureProtocol.ClientHeight + 48;
        }
    }

    internal sealed class PaintBlock
    {
        internal int X;
        internal int Y;
        internal int Width;
        internal int Height;
        internal int Red;
        internal int Green;
        internal int Blue;

        internal PaintBlock(int x, int y, int width, int height, int red, int green, int blue)
        {
            X = x;
            Y = y;
            Width = width;
            Height = height;
            Red = red;
            Green = green;
            Blue = blue;
        }
    }

    internal static class PaintPolicy
    {
        private static readonly PaintBlock[] ReadyPlan = new PaintBlock[]
        {
            new PaintBlock(0, 0, 80, 240, 192, 32, 32),
            new PaintBlock(80, 0, 80, 240, 32, 64, 192),
            new PaintBlock(160, 0, 80, 240, 32, 160, 64),
            new PaintBlock(240, 0, 80, 240, 16, 24, 32)
        };

        private static readonly PaintBlock[] CompletePlan = new PaintBlock[]
        {
            new PaintBlock(0, 0, 80, 240, 24, 176, 80),
            new PaintBlock(80, 0, 80, 240, 224, 176, 24),
            new PaintBlock(160, 0, 80, 240, 128, 48, 192),
            new PaintBlock(240, 0, 80, 240, 32, 200, 216)
        };

        private static readonly PaintBlock[] FaultPlan = new PaintBlock[]
        {
            new PaintBlock(0, 0, 80, 240, 0, 0, 0),
            new PaintBlock(80, 0, 80, 240, 224, 0, 224),
            new PaintBlock(160, 0, 80, 240, 0, 0, 0),
            new PaintBlock(240, 0, 80, 240, 224, 0, 224)
        };

        internal static PaintBlock[] ForState(FixtureState state)
        {
            if (state == FixtureState.Ready) return ReadyPlan;
            if (state == FixtureState.Complete) return CompletePlan;
            return FaultPlan;
        }
    }

    internal static class InputPolicy
    {
        internal static FixtureState Apply(FixtureState current, MouseButtons button, int x, int y,
            long messageExtraInfo, uint expectedNonce)
        {
            if (current != FixtureState.Ready) return FixtureState.Fault;
            if (button != MouseButtons.Left || x != FixtureProtocol.ExpectedInputX ||
                y != FixtureProtocol.ExpectedInputY ||
                messageExtraInfo != (long)expectedNonce)
                return FixtureState.Fault;
            return FixtureState.Complete;
        }
    }

    internal sealed class SyntheticFixtureForm : Form
    {
        private readonly uint inputNonce;
        private FixtureState state;

        internal FixtureState State { get { return state; } }

        internal SyntheticFixtureForm(uint expectedInputNonce)
        {
            inputNonce = expectedInputNonce;
            state = FixtureState.Ready;
            AutoScaleMode = AutoScaleMode.None;
            ClientSize = new Size(FixtureProtocol.ClientWidth, FixtureProtocol.ClientHeight);
            StartPosition = FormStartPosition.Manual;
            Location = new Point(FixtureProtocol.WindowX, FixtureProtocol.WindowY);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            ControlBox = false;
            MaximizeBox = false;
            MinimizeBox = false;
            ShowIcon = false;
            ShowInTaskbar = true;
            Text = "CM0102 Synthetic Fixture v1";
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.Opaque, true);
        }

        protected override void OnPaint(PaintEventArgs eventArgs)
        {
            foreach (PaintBlock block in PaintPolicy.ForState(state))
            {
                using (SolidBrush brush = new SolidBrush(Color.FromArgb(block.Red, block.Green, block.Blue)))
                    eventArgs.Graphics.FillRectangle(brush, block.X, block.Y, block.Width, block.Height);
            }
        }

        protected override void OnMouseDown(MouseEventArgs eventArgs)
        {
            long extra = NativeMethods.GetMessageExtraInfo().ToInt64();
            state = InputPolicy.Apply(state, eventArgs.Button, eventArgs.X, eventArgs.Y, extra, inputNonce);
            Invalidate();
            Update();
            base.OnMouseDown(eventArgs);
        }

        protected override void WndProc(ref Message message)
        {
            if (message.Msg == FixtureProtocol.ProtocolQueryMessage)
            {
                message.Result = new IntPtr(FixtureProtocol.ProtocolMagic);
                return;
            }
            if (message.Msg == FixtureProtocol.StateQueryMessage)
            {
                message.Result = new IntPtr((int)state);
                return;
            }
            base.WndProc(ref message);
        }
    }

    internal static class NativeMethods
    {
        private const uint TokenQuery = 0x0008;
        private const int TokenElevationType = 18;
        private const int TokenElevation = 20;
        private const int TokenIntegrityLevel = 25;
        private const int UserObjectName = 2;

        [StructLayout(LayoutKind.Sequential)]
        private struct SidAndAttributes
        {
            internal IntPtr Sid;
            internal uint Attributes;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct SidIdentifierAuthority
        {
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 6)] internal byte[] Value;
        }

        [DllImport("kernel32.dll")]
        private static extern IntPtr GetCurrentProcess();

        [DllImport("kernel32.dll")]
        private static extern uint GetCurrentProcessId();

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ProcessIdToSessionId(uint processId, out uint sessionId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern bool OpenProcessToken(IntPtr process, uint desiredAccess, out IntPtr token);

        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern bool GetTokenInformation(IntPtr token, int informationClass, IntPtr buffer,
            int bufferLength, out int returnLength);

        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern bool CheckTokenMembership(IntPtr token, IntPtr sidToCheck, out bool isMember);

        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern bool AllocateAndInitializeSid(ref SidIdentifierAuthority identifierAuthority,
            byte subAuthorityCount, uint subAuthority0, uint subAuthority1, uint subAuthority2,
            uint subAuthority3, uint subAuthority4, uint subAuthority5, uint subAuthority6,
            uint subAuthority7, out IntPtr sid);

        [DllImport("advapi32.dll")]
        private static extern IntPtr FreeSid(IntPtr sid);

        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern IntPtr GetSidSubAuthorityCount(IntPtr sid);

        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern IntPtr GetSidSubAuthority(IntPtr sid, uint subAuthority);

        [DllImport("kernel32.dll")]
        private static extern uint WTSGetActiveConsoleSessionId();

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint desiredAccess);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool CloseDesktop(IntPtr desktop);

        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool GetUserObjectInformationW(IntPtr handle, int index, StringBuilder information,
            int length, out int needed);

        [DllImport("user32.dll")]
        internal static extern IntPtr GetMessageExtraInfo();

        [DllImport("user32.dll", SetLastError = true)]
        internal static extern bool SetProcessDPIAware();

        internal static TokenFacts ObserveTokenAndSession()
        {
            IntPtr token;
            if (!OpenProcessToken(GetCurrentProcess(), TokenQuery, out token))
                throw new InvalidOperationException("open-process-token");
            try
            {
                TokenFacts result = new TokenFacts();
                result.IntegrityRid = TokenInteger(token, TokenIntegrityLevel, true);
                result.ElevationType = TokenInteger(token, TokenElevationType, false);
                result.IsElevated = TokenInteger(token, TokenElevation, false) != 0;
                result.IsAdministrator = IsAdministrator();
                if (!ProcessIdToSessionId(GetCurrentProcessId(), out result.ProcessSessionId))
                    throw new InvalidOperationException("process-session");
                result.ActiveConsoleSessionId = WTSGetActiveConsoleSessionId();
                result.InputDesktopName = InputDesktopName();
                return result;
            }
            finally
            {
                CloseHandle(token);
            }
        }

        private static int TokenInteger(IntPtr token, int informationClass, bool integrityRid)
        {
            int needed;
            GetTokenInformation(token, informationClass, IntPtr.Zero, 0, out needed);
            if (needed <= 0) throw new InvalidOperationException("token-information-size");
            IntPtr buffer = Marshal.AllocHGlobal(needed);
            try
            {
                if (!GetTokenInformation(token, informationClass, buffer, needed, out needed))
                    throw new InvalidOperationException("token-information");
                if (!integrityRid) return Marshal.ReadInt32(buffer);
                SidAndAttributes label = (SidAndAttributes)Marshal.PtrToStructure(buffer,
                    typeof(SidAndAttributes));
                IntPtr countPointer = GetSidSubAuthorityCount(label.Sid);
                if (countPointer == IntPtr.Zero) throw new InvalidOperationException("integrity-count");
                byte count = Marshal.ReadByte(countPointer);
                if (count == 0) throw new InvalidOperationException("integrity-empty");
                IntPtr ridPointer = GetSidSubAuthority(label.Sid, (uint)(count - 1));
                if (ridPointer == IntPtr.Zero) throw new InvalidOperationException("integrity-rid");
                return Marshal.ReadInt32(ridPointer);
            }
            finally
            {
                Marshal.FreeHGlobal(buffer);
            }
        }

        private static bool IsAdministrator()
        {
            SidIdentifierAuthority authority = new SidIdentifierAuthority();
            authority.Value = new byte[] { 0, 0, 0, 0, 0, 5 };
            IntPtr sid;
            if (!AllocateAndInitializeSid(ref authority, 2, 32, 544, 0, 0, 0, 0, 0, 0, out sid))
                throw new InvalidOperationException("admin-sid");
            try
            {
                bool member;
                if (!CheckTokenMembership(IntPtr.Zero, sid, out member))
                    throw new InvalidOperationException("admin-membership");
                return member;
            }
            finally
            {
                FreeSid(sid);
            }
        }

        private static string InputDesktopName()
        {
            IntPtr desktop = OpenInputDesktop(0, false, 0x0001);
            if (desktop == IntPtr.Zero) throw new InvalidOperationException("input-desktop");
            try
            {
                int needed;
                GetUserObjectInformationW(desktop, UserObjectName, null, 0, out needed);
                if (needed <= 2) throw new InvalidOperationException("desktop-name-size");
                StringBuilder name = new StringBuilder((needed / 2) + 1);
                if (!GetUserObjectInformationW(desktop, UserObjectName, name, name.Capacity * 2, out needed))
                    throw new InvalidOperationException("desktop-name");
                return name.ToString();
            }
            finally
            {
                CloseDesktop(desktop);
            }
        }
    }

    internal static class SyntheticFixture
    {
        [STAThread]
        private static int Main()
        {
            try
            {
                FixtureConfiguration configuration = FixtureConfiguration.FromCurrentProcess();
                TokenFacts token = NativeMethods.ObserveTokenAndSession();
                if (!TokenPolicy.IsSafe(token)) return 2;
                if (DisplayPolicy.RequireProcessDpiAware && !NativeMethods.SetProcessDPIAware()) return 3;
                Rectangle screen = Screen.PrimaryScreen.Bounds;
                if (!DisplayPolicy.IsSupportedBounds(screen.Width, screen.Height))
                    return 3;
                Application.SetUnhandledExceptionMode(UnhandledExceptionMode.ThrowException);
                SyntheticFixtureForm form = new SyntheticFixtureForm(configuration.InputNonce);
                Application.Run(form);
                return form.State == FixtureState.Complete ? 0 : 4;
            }
            catch
            {
                return 1;
            }
        }
    }
}
