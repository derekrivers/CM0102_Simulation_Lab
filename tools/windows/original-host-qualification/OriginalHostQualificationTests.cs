using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

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
            Run("redactor", TestRedactor);
            Run("strict-expectations", TestStrictExpectations);
            Run("strict-private-config", TestStrictPrivateConfig);
            Run("tree-manifest-stability", TestTreeManifestStability);
            Run("tree-plain-qualification", TestTreePlainQualification);
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
            SortedDictionary<string, object> document = Program.MinimalDocument("synthetic-error");
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

                File.WriteAllText(path, valid.Replace("{\"schema_version\":1", "{\"schema_version\":1,\"schema_version\":1"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"clean_file_count\":1", "\"clean_file_count\":1.5"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"registry_exact_access_mask\":983103", "\"registry_exact_access_mask\":983102"), new UTF8Encoding(false));
                AssertThrowsUsage(delegate { Expectations.Load(path); });

                File.WriteAllText(path, valid.Replace("\"clean_total_bytes\":1", "\"clean_total_bytes\":-1"), new UTF8Encoding(false));
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
                "\"registry_key_id\":\"test\",\"registry_subkey\":\"SOFTWARE\\\\test\",\"registry_value_name\":\"Path\"," +
                "\"registry_exact_access_mask\":983103}";
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
                File.WriteAllText(Path.Combine(root, "B", "two.txt"), "two", new UTF8Encoding(false));
                File.WriteAllText(Path.Combine(root, "a", "one.txt"), "one", new UTF8Encoding(false));
                TreeManifest first = TreeManifest.Capture(root, false);
                TreeManifest second = TreeManifest.Capture(root, false);
                Assert(first.SameIdentity(second));
                Assert(first.FileCount == 2);
                Assert(first.TotalBytes == 6);
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
    }
}
