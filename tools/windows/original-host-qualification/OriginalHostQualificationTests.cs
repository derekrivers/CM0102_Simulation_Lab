using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using Microsoft.Win32.SafeHandles;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace Cm0102.OriginalHostQualification
{
    internal sealed class OriginalHostQualificationTests
    {
        private static int failures;

        private static int Main()
        {
            Run("canonical-json", TestCanonicalJson);
            Run("canonical-json-rejects-float", TestCanonicalJsonRejectsFloat);
            Run("minimal-document", TestMinimalDocument);
            Run("stage-diagnostic", TestStageDiagnostic);
            Run("redactor", TestRedactor);
            Run("strict-expectations", TestStrictExpectations);
            Run("strict-private-config", TestStrictPrivateConfig);
            Run("tree-manifest-stability", TestTreeManifestStability);
            Run("manifest-directory-exactness", TestManifestDirectoryExactness);
            Run("tree-plain-qualification", TestTreePlainQualification);
            Run("case-collision", TestCaseCollision);
            Run("actual-reparse", TestActualReparse);
            Run("object-alias", TestObjectAlias);
            Run("outside-tree-hardlink", TestOutsideTreeHardlink);
            Run("unreadable-and-share-protected", TestUnreadableAndShareProtected);
            Run("mid-read-mutation-and-share-denial", TestMidReadMutationAndShareDenial);
            Run("qualification-policies", TestQualificationPolicies);
            Run("restoration-cleanup", TestRestorationCleanup);
            Run("actual-token-restoration", TestActualTokenRestoration);
            Run("capability-x86-system-path", TestCapabilityX86SystemPath);
            Run("clean-iso-identity-mismatch", TestCleanIsoIdentityMismatch);
            Run("installed-virtual-store-mutation", TestInstalledVirtualStoreMutation);
            Run("completeness", TestCompleteness);
            Run("relative-path-rejection", TestRelativePathRejection);
            Console.WriteLine(failures == 0 ? "PASS" : "FAIL " + failures);
            return failures == 0 ? 0 : 1;
        }

        private static void Run(string name, Action test)
        {
            try { test(); Console.WriteLine("ok " + name); }
            catch (Exception exception) { failures++; Console.WriteLine("not ok " + name + " " + exception.GetType().Name); }
        }

        private static void TestCanonicalJson()
        {
            SortedDictionary<string, object> value = JsonObjects.Object(
                "z", new List<object> { 2, "\u00e9" },
                "a", JsonObjects.Object("line", "x\ny", "false", false));
            string actual = CanonicalJson.Serialize(value);
            string expected = "{\"a\":{\"false\":false,\"line\":\"x\\ny\"},\"z\":[2,\"\\u00e9\"]}";
            Assert(actual == expected);
        }

        private static void TestCanonicalJsonRejectsFloat()
        {
            bool rejected = false;
            try { CanonicalJson.Serialize(JsonObjects.Object("value", 1.5)); }
            catch (InvalidOperationException) { rejected = true; }
            Assert(rejected);
        }

        private static void TestMinimalDocument()
        {
            SortedDictionary<string, object> document = Program.MinimalDocument(
                "unhandled-v1-host-observation-exception-80131501");
            string[] requiredTopLevel = { "capabilities", "checks", "errors", "guards", "host", "inputs", "probe",
                "registry", "run", "schema_version", "session", "summary", "tokens" };
            Assert(document.Count == requiredTopLevel.Length);
            foreach (string key in requiredTopLevel) Assert(document.ContainsKey(key));
            List<object> checks = (List<object>)document["checks"];
            Assert(checks.Count == 1);
            IDictionary<string, object> check = (IDictionary<string, object>)checks[0];
            Assert((string)check["id"] == "probe");
            Assert((string)check["outcome"] == "error");
            Assert((bool)check["required"]);
            IDictionary<string, object> summary = (IDictionary<string, object>)document["summary"];
            Assert(Convert.ToInt32(summary["required_check_count"]) == 1);
            Assert(Convert.ToInt32(summary["passed_count"]) == 0);
            Assert(Convert.ToInt32(summary["failed_count"]) == 0);
            Assert(Convert.ToInt32(summary["error_count"]) == 1);
        }

        private static void TestStageDiagnostic()
        {
            string detail = Program.UnhandledDetail(DiagnosticStages.HostObservation,
                new SystemException(@"C:\private\user\secret"));
            Assert(detail == "unhandled-v1-host-observation-exception-80131501");
            ProbeStageException wrapped = new ProbeStageException(DiagnosticStages.SessionDiscovery,
                new UnauthorizedAccessException(@"\\private\share\secret"));
            Assert(wrapped.Stage == DiagnosticStages.SessionDiscovery);
            Assert(Program.UnhandledDetail(wrapped.Stage, wrapped.InnerException) ==
                "unhandled-v1-session-discovery-unauthorized");
            Assert(Program.UnhandledDetail("C:\\private\\injected", new SystemException()) ==
                "unhandled-v1-stage-tracker-exception-80131501");
            Assert(!detail.Contains("SystemException"));
            Assert(!detail.Contains("private"));

            string stage = DiagnosticStages.CleanManifest;
            Assert(Program.UnhandledDetail(stage, new FileNotFoundException(@"C:\private\file")) ==
                "unhandled-v1-clean-manifest-file-not-found");
            Assert(Program.UnhandledDetail(stage, new DirectoryNotFoundException(@"C:\private\directory")) ==
                "unhandled-v1-clean-manifest-directory-not-found");
            string ioDetail = Program.UnhandledDetail(stage, new IOException(@"C:\private\io"));
            string cryptoDetail = Program.UnhandledDetail(stage, new CryptographicException(@"C:\private\crypto"));
            Assert(Regex.IsMatch(ioDetail, @"\Aunhandled-v1-clean-manifest-io-[0-9a-f]{8}\z"));
            Assert(Regex.IsMatch(cryptoDetail, @"\Aunhandled-v1-clean-manifest-crypto-[0-9a-f]{8}\z"));
            Assert(!ioDetail.Contains("private"));
            Assert(!cryptoDetail.Contains("private"));

            Assert(DiagnosticStages.AfterRestoration(true, true) == DiagnosticStages.RegistryExplorerAccess);
            Assert(DiagnosticStages.AfterRestoration(true, false) == DiagnosticStages.ImpersonationRestore);
            Assert(DiagnosticStages.AfterRestoration(false, true) == DiagnosticStages.ImpersonationRestore);
            Assert(DiagnosticStages.AfterRestoration(false, false) == DiagnosticStages.ImpersonationRestore);

            string first = CanonicalJson.Serialize(Program.MinimalDocument(detail));
            string second = CanonicalJson.Serialize(Program.MinimalDocument(detail));
            Assert(first == second);
            Assert(!first.Contains("private"));
        }

        private static void TestRedactor()
        {
            Redactor redactor = new Redactor();
            redactor.Add(@"C:\private\game");
            Assert(redactor.IsSafe(JsonObjects.Object("sha256", new string('a', 64))));
            Assert(!redactor.IsSafe(JsonObjects.Object("detail", @"C:\private\game\cm0102.exe")));
            Assert(!redactor.IsSerializedSafe("{\"detail\":\"C:\\\\private\\\\game\"}"));
        }

        private static void TestStrictExpectations()
        {
            string root = NewTemporaryDirectory();
            try
            {
                string path = Path.Combine(root, "expectations.json");
                string valid = ValidExpectationsJson();
                File.WriteAllText(path, valid, new UTF8Encoding(false));
                Expectations expectations = Expectations.Load(path);
                Assert(expectations.RegistryExactAccessMask == 0x000f003f);
                Assert(expectations.CompilerBytes == 1);
                Assert(expectations.CompilerUiBytes == 1);
                Assert(expectations.SourceIdentity.Sha256 == Hashing.BytesSha256(new UTF8Encoding(false).GetBytes(valid)));

                File.WriteAllText(path, valid.Replace("{\"schema_version\":1", "{\"schema_version\":1,\"schema_version\":1"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"clean_file_count\":1", "\"clean_file_count\":1.5"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"registry_exact_access_mask\":983103", "\"registry_exact_access_mask\":983102"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"clean_total_bytes\":1", "\"clean_total_bytes\":-1"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"compiler_bytes\":1", "\"compiler_bytes\":0"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"compiler_ui_bytes\":1", "\"compiler_ui_bytes\":0"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"csc-x86\",\"powershell\"", "\"powershell\",\"csc-x86\""), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"csc-x86\"", "\"unsupported-tool\""), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                DuplicateKeyScanner.RejectTopLevelDuplicates("{\"nested\":{\"items\":[{\"value\":1}]},\"other\":true}");
                AssertThrowsUsage(delegate { DuplicateKeyScanner.RejectTopLevelDuplicates("{\"nested\":{},\"nested\":[]}"); });
            }
            finally { Directory.Delete(root, true); }
        }

        private static string ValidExpectationsJson()
        {
            string hash = new string('a', 64);
            return "{\"schema_version\":1,\"profile_id\":\"test\",\"clean_file_count\":1,\"clean_total_bytes\":1," +
                "\"clean_manifest_bytes\":1,\"clean_manifest_sha256\":\"" + hash + "\",\"original_executable_bytes\":1," +
                "\"original_executable_sha256\":\"" + hash + "\",\"iso_bytes\":1,\"iso_sha256\":\"" + hash + "\"," +
                "\"optical_volume_label\":\"TEST\",\"optical_executable_bytes\":1,\"optical_executable_sha256\":\"" + hash + "\"," +
                "\"compiler_bytes\":1,\"compiler_sha256\":\"" + hash + "\"," +
                "\"compiler_ui_bytes\":1,\"compiler_ui_sha256\":\"" + hash + "\"," +
                "\"registry_key_id\":\"test\",\"registry_subkey\":\"SOFTWARE\\\\test\",\"registry_value_name\":\"Path\"," +
                "\"registry_exact_access_mask\":983103," +
                "\"required_api_ids\":[\"advapi32-registry\",\"advapi32-token\",\"kernel32-filesystem\",\"user32-desktop\",\"wtsapi32-session\"]," +
                "\"required_tool_ids\":[\"csc-x86\",\"powershell\",\"python313\"]}";
        }

        private static void TestStrictPrivateConfig()
        {
            string root = NewTemporaryDirectory();
            try
            {
                string path = Path.Combine(root, "private.json");
                File.WriteAllText(path,
                    "{\"schema_version\":1,\"clean_tree\":\"C:\\\\clean\",\"clean_manifest\":\"C:\\\\manifest.tsv\",\"installed_tree\":\"C:\\\\installed\",\"virtual_store_tree\":\"C:\\\\virtual\",\"iso_file\":\"C:\\\\disc.iso\",\"optical_root\":\"D:\\\\\"}",
                    new UTF8Encoding(false));
                PrivateLocator locator = PrivateLocator.Load(path);
                Assert(locator.OpticalRoot == @"D:\");
                File.WriteAllText(path,
                    "{\"schema_version\":1,\"clean_tree\":\"C:\\\\clean\",\"clean_manifest\":\"C:\\\\manifest.tsv\",\"installed_tree\":\"C:\\\\installed\",\"virtual_store_tree\":\"C:\\\\virtual\",\"iso_file\":\"C:\\\\disc.iso\",\"optical_root\":\"D:\\\\\",\"extra\":1}",
                    new UTF8Encoding(false));
                bool rejected = false;
                try { PrivateLocator.Load(path); }
                catch (UsageException) { rejected = true; }
                Assert(rejected);

                File.WriteAllText(path,
                    "{\"schema_version\":1,\"clean_tree\":\"relative\",\"clean_manifest\":\"C:\\\\manifest.tsv\",\"installed_tree\":\"C:\\\\installed\",\"virtual_store_tree\":\"C:\\\\virtual\",\"iso_file\":\"C:\\\\disc.iso\",\"optical_root\":\"D:\\\\\"}",
                    new UTF8Encoding(false));
                AssertThrowsUsage(delegate { PrivateLocator.Load(path); });

                File.WriteAllText(path,
                    "{\"schema_version\":1,\"clean_tree\":\"C:\\\\same\",\"clean_manifest\":\"C:\\\\manifest.tsv\",\"installed_tree\":\"c:\\\\SAME\\\\\",\"virtual_store_tree\":\"C:\\\\virtual\",\"iso_file\":\"C:\\\\disc.iso\",\"optical_root\":\"D:\\\\\"}",
                    new UTF8Encoding(false));
                AssertThrowsUsage(delegate { PrivateLocator.Load(path); });
            }
            finally { Directory.Delete(root, true); }
        }

        private static void TestTreeManifestStability()
        {
            string root = NewTemporaryDirectory();
            try
            {
                Directory.CreateDirectory(Path.Combine(root, "B"));
                Directory.CreateDirectory(Path.Combine(root, "a"));
                Directory.CreateDirectory(Path.Combine(root, "empty"));
                File.WriteAllText(Path.Combine(root, "B", "two.txt"), "two", new UTF8Encoding(false));
                File.WriteAllText(Path.Combine(root, "a", "one.txt"), "one", new UTF8Encoding(false));
                TreeManifest first = TreeManifest.Capture(root, false);
                TreeManifest second = TreeManifest.Capture(root, false);
                Assert(first.SameIdentity(second));
                Assert(first.FileCount == 2);
                Assert(first.TotalBytes == 6);
                Assert(first.DirectoryCount == 4);
                TreeManifest writable = TreeManifest.Capture(root, true);
                Assert(writable.WritableOpenCount >= 3);
                Directory.Delete(Path.Combine(root, "empty"));
                TreeManifest withoutEmpty = TreeManifest.Capture(root, false);
                Assert(first.TreeSha256 != withoutEmpty.TreeSha256);
                File.AppendAllText(Path.Combine(root, "a", "one.txt"), "changed");
                TreeManifest third = TreeManifest.Capture(root, false);
                Assert(!first.SameIdentity(third));
            }
            finally { Directory.Delete(root, true); }
        }

        private static void TestTreePlainQualification()
        {
            TreeManifest plain = new TreeManifest { Present = true };
            Assert(plain.IsPlain(true));
            Assert(plain.IsPlain(false));
            Assert(!new TreeManifest { Present = false }.IsPlain(true));
            Assert(new TreeManifest { Present = false }.IsPlain(false));
            Assert(!new TreeManifest { Present = true, ReparseCount = 1 }.IsPlain(true));
            Assert(!new TreeManifest { Present = true, CaseCollisionCount = 1 }.IsPlain(true));
            Assert(!new TreeManifest { Present = true, UnstableCount = 1 }.IsPlain(true));
            Assert(!new TreeManifest { Present = true, ObjectAliasCount = 1 }.IsPlain(true));
            Assert(!new TreeManifest { Present = true, HardlinkCount = 1 }.IsPlain(true));
        }

        private static void TestManifestDirectoryExactness()
        {
            string root = NewTemporaryDirectory();
            try
            {
                Directory.CreateDirectory(Path.Combine(root, "Data"));
                Directory.CreateDirectory(Path.Combine(root, "empty"));
                File.WriteAllText(Path.Combine(root, "Data", "one.dat"), "one", new UTF8Encoding(false));
                TreeManifest tree = TreeManifest.Capture(root, false);
                HashSet<string> expected = ManifestRow.ExpectedDirectories(new string[] { "Data/one.dat" });
                int missing;
                int extra;
                QualificationPolicy.DirectoryDifference(tree, expected, out missing, out extra);
                Assert(missing == 0);
                Assert(extra == 1);
                expected = ManifestRow.ExpectedDirectories(new string[] { "Data/one.dat", "Missing/two.dat" });
                QualificationPolicy.DirectoryDifference(tree, expected, out missing, out extra);
                Assert(missing == 1);
                Assert(extra == 1);
            }
            finally { Directory.Delete(root, true); }
        }

        private static void TestCaseCollision()
        {
            TreeManifest manifest = new TreeManifest();
            HashSet<string> exact = new HashSet<string>(StringComparer.Ordinal);
            HashSet<string> folded = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            TreeManifest.RecordName("Data/index.dat", exact, folded, manifest);
            TreeManifest.RecordName("data/INDEX.dat", exact, folded, manifest);
            Assert(manifest.CaseCollisionCount == 1);
        }

        private static void TestActualReparse()
        {
            string root = NewTemporaryDirectory();
            string target = NewTemporaryDirectory();
            try
            {
                string link = Path.Combine(root, "junction");
                if (!CreateSymbolicLinkW(link, target, 0x1 | 0x2))
                    throw new InvalidOperationException("create-synthetic-reparse-" + Marshal.GetLastWin32Error());
                TreeManifest manifest = TreeManifest.Capture(root, false);
                Assert(manifest.ReparseCount == 1);
                Assert(!manifest.IsPlain(true));
            }
            finally
            {
                Directory.Delete(root, true);
                Directory.Delete(target, true);
            }
        }

        private static void TestObjectAlias()
        {
            string root = NewTemporaryDirectory();
            try
            {
                string original = Path.Combine(root, "original.bin");
                string alias = Path.Combine(root, "alias.bin");
                File.WriteAllText(original, "same-object", new UTF8Encoding(false));
                if (!CreateHardLinkW(alias, original, IntPtr.Zero))
                    throw new InvalidOperationException("create-synthetic-hardlink-" + Marshal.GetLastWin32Error());
                Assert(!PathSafety.AreDistinctExistingObjects(new string[] { original, alias }));
                Assert(!PathSafety.AreDistinctExistingObjects(new string[] { original }));
                TreeManifest manifest = TreeManifest.Capture(root, false);
                Assert(manifest.ObjectAliasCount == 1);
                Assert(manifest.HardlinkCount == 2);
                Assert(!manifest.IsPlain(true));
            }
            finally { Directory.Delete(root, true); }
        }

        private static void TestOutsideTreeHardlink()
        {
            string root = NewTemporaryDirectory();
            string outside = NewTemporaryDirectory();
            try
            {
                string original = Path.Combine(outside, "original.bin");
                string link = Path.Combine(root, "linked.bin");
                File.WriteAllText(original, "outside-object", new UTF8Encoding(false));
                if (!CreateHardLinkW(link, original, IntPtr.Zero))
                    throw new InvalidOperationException("create-outside-hardlink-" + Marshal.GetLastWin32Error());
                TreeManifest manifest = TreeManifest.Capture(root, false);
                Assert(manifest.ObjectAliasCount == 0);
                Assert(manifest.HardlinkCount == 1);
                Assert(!manifest.IsPlain(true));
                Assert(!PathSafety.AreDistinctExistingObjects(new string[] { link }));
            }
            finally
            {
                Directory.Delete(root, true);
                Directory.Delete(outside, true);
            }
        }

        private static void TestUnreadableAndShareProtected()
        {
            string root = NewTemporaryDirectory();
            try
            {
                string path = Path.Combine(root, "locked.bin");
                File.WriteAllText(path, "stable", new UTF8Encoding(false));
                using (FileStream exclusive = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
                    AssertThrowsIo(delegate { FileIdentity.Read(path); });
                using (VerifiedPath opened = PathSafety.OpenVerified(path, false, root, true))
                using (FileStream reader = new FileStream(opened.Handle, FileAccess.Read, 4096, false))
                    AssertThrowsIo(delegate { using (FileStream writer = new FileStream(path, FileMode.Open, FileAccess.Write, FileShare.Read)) { } });
            }
            finally { Directory.Delete(root, true); }
        }

        private static void TestMidReadMutationAndShareDenial()
        {
            string root = NewTemporaryDirectory();
            try
            {
                string path = Path.Combine(root, "changing.bin");
                File.WriteAllText(path, new string('x', 128 * 1024), new UTF8Encoding(false));
                bool shareDenied = false;
                bool mutationDetected = false;
                using (VerifiedPath opened = PathSafety.OpenVerified(path, false, root, true))
                {
                    try
                    {
                        FileSnapshot.Hash(opened, null, delegate(SafeFileHandle handle)
                        {
                            try
                            {
                                using (FileStream writer = new FileStream(path, FileMode.Open, FileAccess.Write, FileShare.Read)) { }
                            }
                            catch (IOException) { shareDenied = true; }
                            NativeFileIdentity changed = NativeMethods.GetFileIdentity(handle);
                            changed.LastWrite++;
                            return changed;
                        });
                    }
                    catch (IOException) { mutationDetected = true; }
                }
                Assert(shareDenied);
                Assert(mutationDetected);
            }
            finally { Directory.Delete(root, true); }
        }

        private static void TestQualificationPolicies()
        {
            TokenObservation current = new TokenObservation { RawSid = "S-1-5-21-1", Integrity = "high", IsAdministrator = true, SessionId = 3 };
            TokenObservation explorer = new TokenObservation { RawSid = "S-1-5-21-1", Integrity = "medium", IsAdministrator = false, SessionId = 3 };
            Assert(QualificationPolicy.DirectTokenHazard(current));
            Assert(QualificationPolicy.ExplorerTokenSafe(current, explorer, 3));
            Assert(!QualificationPolicy.ExplorerTokenSafe(current, explorer, 4));
            Assert(QualificationPolicy.SessionSafe(3, 3, "Default"));
            Assert(!QualificationPolicy.SessionSafe(3, 3, "Winlogon"));
            Assert(QualificationPolicy.DirectRegistryAccessExpected(0));
            Assert(!QualificationPolicy.DirectRegistryAccessExpected(5));
            Assert(QualificationPolicy.ExplorerRegistryDenied(5));
            Assert(!QualificationPolicy.ExplorerRegistryDenied(0));
        }

        private static void TestActualTokenRestoration()
        {
            bool initialWasThreadToken;
            TokenObservation initial = TokenObservation.EffectiveCurrent(out initialWasThreadToken);
            Assert(!initialWasThreadToken);
            using (Process current = Process.GetCurrentProcess()) Assert(initial.SessionId == current.SessionId);
            using (SafeKernelHandle duplicate = NativeMethods.DuplicateCurrentTokenForImpersonation())
            {
                using (WindowsImpersonationContext context = WindowsIdentity.Impersonate(duplicate.DangerousGetHandle()))
                {
                    bool duringWasThreadToken;
                    TokenObservation during = TokenObservation.EffectiveCurrent(out duringWasThreadToken);
                    Assert(duringWasThreadToken);
                    Assert(during.SessionId == initial.SessionId);
                    Assert(during.SecurityEquivalent(initial));
                    context.Undo();
                }
                AssertTokenRestored(initial, initialWasThreadToken);

                bool observed = false;
                try
                {
                    using (WindowsImpersonationContext context = WindowsIdentity.Impersonate(duplicate.DangerousGetHandle()))
                    {
                        try
                        {
                            bool duringWasThreadToken;
                            TokenObservation during = TokenObservation.EffectiveCurrent(out duringWasThreadToken);
                            Assert(duringWasThreadToken);
                            Assert(during.SecurityEquivalent(initial));
                            throw new SyntheticTokenException();
                        }
                        finally { context.Undo(); }
                    }
                }
                catch (SyntheticTokenException) { observed = true; }
                Assert(observed);
                AssertTokenRestored(initial, initialWasThreadToken);
            }
        }

        private static void TestCapabilityX86SystemPath()
        {
            string windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            string expectedSystem = Environment.GetFolderPath(Environment.SpecialFolder.SystemX86);
            string actualSystem = CapabilityCatalog.SystemX86Path();
            Assert(!String.IsNullOrEmpty(windows));
            Assert(!String.IsNullOrEmpty(actualSystem));
            Assert(String.Equals(actualSystem, expectedSystem, StringComparison.OrdinalIgnoreCase));
            Dictionary<string, string> tools = CapabilityCatalog.ToolPaths(windows, actualSystem);
            foreach (string id in new string[] { "cmd", "powershell" })
            {
                Assert(File.Exists(tools[id]));
                FileIdentity identity = FileIdentity.Read(tools[id]);
                Assert(identity.Bytes > 0);
                Assert(identity.Sha256.Length == 64);
            }
        }

        private static void TestRestorationCleanup()
        {
            bool disposeAttempted = false;
            bool undoFailureObserved = false;
            try
            {
                Probe.RestoreImpersonation(null,
                    delegate { throw new SyntheticTokenException(); },
                    delegate { disposeAttempted = true; });
            }
            catch (SyntheticTokenException) { undoFailureObserved = true; }
            Assert(undoFailureObserved);
            Assert(disposeAttempted);

            bool undoAttempted = false;
            bool disposeFailureObserved = false;
            try
            {
                Probe.RestoreImpersonation(null,
                    delegate { undoAttempted = true; },
                    delegate { throw new SyntheticTokenException(); });
            }
            catch (SyntheticTokenException) { disposeFailureObserved = true; }
            Assert(undoAttempted);
            Assert(disposeFailureObserved);
        }

        private static void AssertTokenRestored(TokenObservation initial, bool initialWasThreadToken)
        {
            bool restoredWasThreadToken;
            TokenObservation restored = TokenObservation.EffectiveCurrent(out restoredWasThreadToken);
            Assert(restoredWasThreadToken == initialWasThreadToken);
            Assert(restored.SecurityEquivalent(initial));
        }

        private sealed class SyntheticTokenException : Exception { }

        private static void TestCleanIsoIdentityMismatch()
        {
            FileIdentity identity = new FileIdentity { Bytes = 10, Sha256 = new string('a', 64) };
            Assert(QualificationPolicy.IdentityMatches(identity, 10, new string('a', 64)));
            Assert(!QualificationPolicy.IdentityMatches(identity, 11, new string('a', 64)));
            Assert(!QualificationPolicy.IdentityMatches(identity, 10, new string('b', 64)));
        }

        private static void TestInstalledVirtualStoreMutation()
        {
            string installed = NewTemporaryDirectory();
            string virtualStore = NewTemporaryDirectory();
            string movedVirtual = virtualStore + "-moved";
            try
            {
                string installedFile = Path.Combine(installed, "state.bin");
                File.WriteAllText(installedFile, "before", new UTF8Encoding(false));
                TreeManifest installedBefore = TreeManifest.Capture(installed, false);
                File.WriteAllText(installedFile, "after", new UTF8Encoding(false));
                TreeManifest installedAfter = TreeManifest.Capture(installed, false);
                Assert(!installedBefore.SameIdentity(installedAfter));

                File.WriteAllText(Path.Combine(virtualStore, "same.bin"), "same", new UTF8Encoding(false));
                TreeManifest virtualBefore = TreeManifest.Capture(virtualStore, false);
                Directory.Move(virtualStore, movedVirtual);
                Directory.CreateDirectory(virtualStore);
                File.WriteAllText(Path.Combine(virtualStore, "same.bin"), "same", new UTF8Encoding(false));
                TreeManifest virtualAfter = TreeManifest.Capture(virtualStore, false);
                Assert(virtualBefore.TreeSha256 == virtualAfter.TreeSha256);
                Assert(virtualBefore.RootObjectIdSha256 != virtualAfter.RootObjectIdSha256);
                Assert(!virtualBefore.SameIdentity(virtualAfter));
            }
            finally
            {
                if (Directory.Exists(installed)) Directory.Delete(installed, true);
                if (Directory.Exists(virtualStore)) Directory.Delete(virtualStore, true);
                if (Directory.Exists(movedVirtual)) Directory.Delete(movedVirtual, true);
            }
        }

        private static void TestCompleteness()
        {
            List<CheckRecord> passing = new List<CheckRecord>();
            foreach (string id in QualificationPolicy.RequiredCheckIds)
                passing.Add(new CheckRecord { Id = id, Required = true, Outcome = "pass" });
            Assert(QualificationPolicy.IsComplete(passing));
            Assert(QualificationPolicy.IsEligible(passing));
            List<CheckRecord> failed = new List<CheckRecord>(passing);
            failed[0] = new CheckRecord { Id = QualificationPolicy.RequiredCheckIds[0], Required = true, Outcome = "fail" };
            Assert(QualificationPolicy.IsComplete(failed));
            Assert(!QualificationPolicy.IsEligible(failed));
            List<CheckRecord> errored = new List<CheckRecord>(passing);
            errored[0] = new CheckRecord { Id = QualificationPolicy.RequiredCheckIds[0], Required = true, Outcome = "error" };
            Assert(!QualificationPolicy.IsComplete(errored));
            Assert(!QualificationPolicy.IsEligible(errored));
            List<CheckRecord> missing = new List<CheckRecord>(passing);
            missing.RemoveAt(0);
            Assert(!QualificationPolicy.IsComplete(missing));
        }

        private static void TestRelativePathRejection()
        {
            AssertThrows(delegate { TreeManifest.NormalizeRelative("../escape"); });
            AssertThrows(delegate { TreeManifest.NormalizeRelative("a//b"); });
            Assert(TreeManifest.NormalizeRelative(@"Data\index.dat") == "Data/index.dat");
        }

        private static string NewTemporaryDirectory()
        {
            string path = Path.Combine(Path.GetTempPath(), "cm0102-host-probe-test-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(path);
            return path;
        }

        private static void Assert(bool condition)
        {
            if (!condition) throw new InvalidOperationException("assertion-failed");
        }

        private static void AssertThrows(Action action)
        {
            bool threw = false;
            try { action(); }
            catch (InvalidDataException) { threw = true; }
            Assert(threw);
        }

        private static void AssertThrowsUsage(Action action)
        {
            bool threw = false;
            try { action(); }
            catch (UsageException) { threw = true; }
            Assert(threw);
        }

        private static void AssertThrowsIo(Action action)
        {
            bool threw = false;
            try { action(); }
            catch (IOException) { threw = true; }
            Assert(threw);
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CreateSymbolicLinkW(string symbolicFileName, string targetFileName, uint flags);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CreateHardLinkW(string fileName, string existingFileName, IntPtr securityAttributes);
    }
}
