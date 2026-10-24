using System;
using System.Collections.Generic;
using System.Windows.Forms;

namespace Cm0102.SyntheticLauncherQualification
{
    internal static class SyntheticFixtureTests
    {
        private static int assertions;

        private static void Assert(bool value)
        {
            assertions++;
            if (!value) throw new InvalidOperationException("assertion-failed");
        }

        private static void Reject(Action action)
        {
            bool rejected = false;
            try { action(); }
            catch (InvalidOperationException) { rejected = true; }
            Assert(rejected);
        }

        private static Dictionary<string, string> EnvironmentValues(string cwd)
        {
            return new Dictionary<string, string>(StringComparer.Ordinal)
            {
                { FixtureConfiguration.CwdHashName, FixtureConfiguration.Sha256Utf16(cwd) },
                { FixtureConfiguration.InputNonceName, "10203040" },
                { "SystemRoot", @"C:\Windows" },
                { "TEMP", @"C:\fixture-temp" },
                { "TMP", @"C:\fixture-temp" },
                { "WINDIR", @"C:\Windows" }
            };
        }

        private static void ConfigurationCases()
        {
            const string cwd = @"C:\fixture-attempt";
            Dictionary<string, string> values = EnvironmentValues(cwd);
            FixtureConfiguration parsed = FixtureConfiguration.Parse(values, cwd, 1);
            Assert(parsed.InputNonce == 0x10203040);
            Assert(FixtureConfiguration.Sha256Utf16(cwd) ==
                "521a08c9d7ca42cb60f5180a0497c0d5dc2537cd256e715d44937af46f5276d6");

            Dictionary<string, string> missing = EnvironmentValues(cwd);
            missing.Remove("TMP");
            Reject(delegate { FixtureConfiguration.Parse(missing, cwd, 1); });

            Dictionary<string, string> extra = EnvironmentValues(cwd);
            extra.Add("PATH", "forbidden");
            Reject(delegate { FixtureConfiguration.Parse(extra, cwd, 1); });

            Dictionary<string, string> wrongCase = EnvironmentValues(cwd);
            string systemRoot = wrongCase["SystemRoot"];
            wrongCase.Remove("SystemRoot");
            wrongCase.Add("SYSTEMROOT", systemRoot);
            Reject(delegate { FixtureConfiguration.Parse(wrongCase, cwd, 1); });

            Dictionary<string, string> wrongCwd = EnvironmentValues(cwd);
            Reject(delegate { FixtureConfiguration.Parse(wrongCwd, cwd + "-other", 1); });

            Dictionary<string, string> uppercaseHash = EnvironmentValues(cwd);
            uppercaseHash[FixtureConfiguration.CwdHashName] =
                uppercaseHash[FixtureConfiguration.CwdHashName].ToUpperInvariant();
            Reject(delegate { FixtureConfiguration.Parse(uppercaseHash, cwd, 1); });

            Dictionary<string, string> zeroNonce = EnvironmentValues(cwd);
            zeroNonce[FixtureConfiguration.InputNonceName] = "00000000";
            Reject(delegate { FixtureConfiguration.Parse(zeroNonce, cwd, 1); });

            Dictionary<string, string> uppercaseNonce = EnvironmentValues(cwd);
            uppercaseNonce[FixtureConfiguration.InputNonceName] = "ABCDEF12";
            Reject(delegate { FixtureConfiguration.Parse(uppercaseNonce, cwd, 1); });

            Dictionary<string, string> mismatchedWindows = EnvironmentValues(cwd);
            mismatchedWindows["WINDIR"] = @"C:\Other";
            Reject(delegate { FixtureConfiguration.Parse(mismatchedWindows, cwd, 1); });

            Dictionary<string, string> mismatchedTemp = EnvironmentValues(cwd);
            mismatchedTemp["TMP"] = @"C:\Other";
            Reject(delegate { FixtureConfiguration.Parse(mismatchedTemp, cwd, 1); });

            Reject(delegate { FixtureConfiguration.Parse(EnvironmentValues(cwd), cwd, 2); });
        }

        private static TokenFacts SafeToken()
        {
            return new TokenFacts
            {
                IntegrityRid = TokenPolicy.MediumIntegrityRid,
                ElevationType = TokenPolicy.TokenElevationTypeLimited,
                IsElevated = false,
                IsAdministrator = false,
                ProcessSessionId = 3,
                ActiveConsoleSessionId = 3,
                InputDesktopName = "Default"
            };
        }

        private static void TokenCases()
        {
            Assert(TokenPolicy.IsSafe(SafeToken()));
            TokenFacts facts = SafeToken(); facts.IntegrityRid = 0x3000; Assert(!TokenPolicy.IsSafe(facts));
            facts = SafeToken(); facts.ElevationType = 1; Assert(!TokenPolicy.IsSafe(facts));
            facts = SafeToken(); facts.IsElevated = true; Assert(!TokenPolicy.IsSafe(facts));
            facts = SafeToken(); facts.IsAdministrator = true; Assert(!TokenPolicy.IsSafe(facts));
            facts = SafeToken(); facts.ProcessSessionId = 4; Assert(!TokenPolicy.IsSafe(facts));
            facts = SafeToken(); facts.ActiveConsoleSessionId = UInt32.MaxValue; Assert(!TokenPolicy.IsSafe(facts));
            facts = SafeToken(); facts.InputDesktopName = "default"; Assert(!TokenPolicy.IsSafe(facts));
            Assert(!TokenPolicy.IsSafe(null));
        }

        private static void InputCases()
        {
            uint nonce = 0x10203040;
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX, FixtureProtocol.ExpectedInputY, nonce, nonce) ==
                FixtureState.Complete);
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Right,
                FixtureProtocol.ExpectedInputX, FixtureProtocol.ExpectedInputY, nonce, nonce) ==
                FixtureState.Fault);
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX + 1, FixtureProtocol.ExpectedInputY, nonce, nonce) ==
                FixtureState.Fault);
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX - 1, FixtureProtocol.ExpectedInputY, nonce, nonce) ==
                FixtureState.Fault);
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX, FixtureProtocol.ExpectedInputY + 1, nonce, nonce) ==
                FixtureState.Fault);
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX, FixtureProtocol.ExpectedInputY - 1, nonce, nonce) ==
                FixtureState.Fault);
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX, FixtureProtocol.ExpectedInputY, nonce + 1, nonce) ==
                FixtureState.Fault);
            Assert(InputPolicy.Apply(FixtureState.Ready, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX, FixtureProtocol.ExpectedInputY, 0x110203040L, nonce) ==
                FixtureState.Fault);
            Assert(InputPolicy.Apply(FixtureState.Complete, MouseButtons.Left,
                FixtureProtocol.ExpectedInputX, FixtureProtocol.ExpectedInputY, nonce, nonce) ==
                FixtureState.Fault);
        }

        private static void AssertBlock(PaintBlock block, int x, int red, int green, int blue)
        {
            Assert(block.X == x && block.Y == 0 && block.Width == 80 && block.Height == 240);
            Assert(block.Red == red && block.Green == green && block.Blue == blue);
        }

        private static void PaintCases()
        {
            Assert(FixtureProtocol.ClientWidth == 320 && FixtureProtocol.ClientHeight == 240);
            Assert(FixtureProtocol.WindowX == 64 && FixtureProtocol.WindowY == 64);
            Assert(FixtureProtocol.ExpectedInputX == 96 && FixtureProtocol.ExpectedInputY == 112);
            Assert(FixtureProtocol.ProtocolQueryMessage == 0x8051);
            Assert(FixtureProtocol.StateQueryMessage == 0x8052);
            Assert(FixtureProtocol.ProtocolMagic == 0x434D0101);
            Assert(DisplayPolicy.RequireProcessDpiAware);
            Assert(DisplayPolicy.IsSupportedBounds(400, 352));
            Assert(!DisplayPolicy.IsSupportedBounds(399, 352));
            Assert(!DisplayPolicy.IsSupportedBounds(400, 351));

            PaintBlock[] ready = PaintPolicy.ForState(FixtureState.Ready);
            PaintBlock[] complete = PaintPolicy.ForState(FixtureState.Complete);
            PaintBlock[] fault = PaintPolicy.ForState(FixtureState.Fault);
            Assert(ready.Length == 4 && complete.Length == 4 && fault.Length == 4);
            AssertBlock(ready[0], 0, 192, 32, 32);
            AssertBlock(ready[1], 80, 32, 64, 192);
            AssertBlock(ready[2], 160, 32, 160, 64);
            AssertBlock(ready[3], 240, 16, 24, 32);
            AssertBlock(complete[0], 0, 24, 176, 80);
            AssertBlock(complete[1], 80, 224, 176, 24);
            AssertBlock(complete[2], 160, 128, 48, 192);
            AssertBlock(complete[3], 240, 32, 200, 216);
            AssertBlock(fault[0], 0, 0, 0, 0);
            AssertBlock(fault[1], 80, 224, 0, 224);
            AssertBlock(fault[2], 160, 0, 0, 0);
            AssertBlock(fault[3], 240, 224, 0, 224);

            foreach (PaintBlock[] plan in new PaintBlock[][] { ready, complete, fault })
            {
                int[] coverage = new int[FixtureProtocol.ClientWidth * FixtureProtocol.ClientHeight];
                foreach (PaintBlock block in plan)
                {
                    Assert(block.X >= 0 && block.Y >= 0 && block.Width > 0 && block.Height > 0);
                    Assert(block.X + block.Width <= FixtureProtocol.ClientWidth);
                    Assert(block.Y + block.Height <= FixtureProtocol.ClientHeight);
                    Assert(block.Red >= 0 && block.Red <= 255 && block.Green >= 0 && block.Green <= 255 &&
                        block.Blue >= 0 && block.Blue <= 255);
                    for (int y = block.Y; y < block.Y + block.Height; y++)
                        for (int x = block.X; x < block.X + block.Width; x++)
                            coverage[y * FixtureProtocol.ClientWidth + x]++;
                }
                foreach (int count in coverage) Assert(count == 1);
            }
        }

        private static int Main()
        {
            ConfigurationCases();
            TokenCases();
            InputCases();
            PaintCases();
            Console.WriteLine("PASS " + assertions.ToString());
            return 0;
        }
    }
}
