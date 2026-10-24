using Microsoft.Win32;
using Microsoft.Win32.SafeHandles;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace Cm0102.OriginalHostQualification
{
    internal sealed class Program
    {
        private const int ExitEligible = 0;
        private const int ExitUnsafe = 2;
        private const int ExitInconclusive = 3;
        private const int ExitUsage = 64;

        [STAThread]
        private static int Main(string[] args)
        {
            Console.OutputEncoding = new UTF8Encoding(false);
            try
            {
                Arguments parsed = Arguments.Parse(args);
                Expectations expectations = Expectations.Load(parsed.ExpectationsPath);
                PrivateLocator locator = PrivateLocator.Load(parsed.PrivateConfigPath);
                Probe probe = new Probe(parsed.SourceRevision, parsed.ExpectationsPath, parsed.PrivateConfigPath,
                    expectations, locator);
                ProbeResult result = probe.Run();
                string json = CanonicalJson.Serialize(result.Document);
                if (!result.Redactor.IsSafe(result.Document) || !result.Redactor.IsSerializedSafe(json))
                    return EmitMinimal("redaction-failure", ExitInconclusive);
                Console.Out.Write(json);
                Console.Out.Write('\n');
                return result.ExitCode;
            }
            catch (UsageException)
            {
                return EmitMinimal("usage-or-config", ExitUsage);
            }
            catch (Exception exception)
            {
                return EmitMinimal("unhandled-" + StableExceptionCode(exception), ExitInconclusive);
            }
        }

        private static int EmitMinimal(string detailCode, int exitCode)
        {
            Console.Out.Write(CanonicalJson.Serialize(MinimalDocument(detailCode)));
            Console.Out.Write('\n');
            return exitCode;
        }

        internal static SortedDictionary<string, object> MinimalDocument(string detailCode)
        {
            List<object> checks = new List<object>
            {
                JsonObjects.Object("detail_code", detailCode, "id", "probe", "outcome", "error", "required", true)
            };
            SortedDictionary<string, object> document = JsonObjects.Object(
                "capabilities", JsonObjects.Object(),
                "checks", checks,
                "errors", new List<object> { JsonObjects.Object("category", "probe", "check_id", "probe", "detail_code", detailCode) },
                "guards", JsonObjects.Object("cm0102_launched", false),
                "host", JsonObjects.Object(),
                "inputs", JsonObjects.Object(),
                "probe", JsonObjects.Object(),
                "registry", JsonObjects.Object(),
                "run", JsonObjects.Object(),
                "schema_version", 1,
                "session", JsonObjects.Object(),
                "summary", JsonObjects.Object(
                    "comparison_verdict", "not-run",
                    "completeness", "incomplete",
                    "direct_wsl_launch_safe", false,
                    "error_count", 1,
                    "failed_count", 0,
                    "original_execution_status", "not-run",
                    "passed_count", 0,
                    "required_check_count", 1,
                    "safety_verdict", "inconclusive"),
                "tokens", JsonObjects.Object());
            return document;
        }

        internal static string StableExceptionCode(Exception exception)
        {
            if (exception is UnauthorizedAccessException) return "unauthorized";
            if (exception is FileNotFoundException) return "file-not-found";
            if (exception is DirectoryNotFoundException) return "directory-not-found";
            if (exception is IOException) return "io-" + exception.HResult.ToString("x8", CultureInfo.InvariantCulture);
            if (exception is CryptographicException) return "crypto-" + exception.HResult.ToString("x8", CultureInfo.InvariantCulture);
            return "exception-" + exception.HResult.ToString("x8", CultureInfo.InvariantCulture);
        }
    }

    internal sealed class UsageException : Exception
    {
        public UsageException() : base("invalid-usage") { }
    }

    internal sealed class Arguments
    {
        public string ExpectationsPath;
        public string PrivateConfigPath;
        public string SourceRevision;

        public static Arguments Parse(string[] args)
        {
            if (args.Length != 6) throw new UsageException();
            Dictionary<string, string> values = new Dictionary<string, string>(StringComparer.Ordinal);
            for (int index = 0; index < args.Length; index += 2)
            {
                if (!args[index].StartsWith("--", StringComparison.Ordinal) || values.ContainsKey(args[index]))
                    throw new UsageException();
                values.Add(args[index], args[index + 1]);
            }
            string expectations;
            string privateConfig;
            string sourceRevision;
            if (!values.TryGetValue("--expectations", out expectations) ||
                !values.TryGetValue("--private-config", out privateConfig) ||
                !values.TryGetValue("--source-revision", out sourceRevision) ||
                values.Count != 3 || !Regex.IsMatch(sourceRevision, "^[0-9a-f]{40}$"))
                throw new UsageException();
            return new Arguments
            {
                ExpectationsPath = Path.GetFullPath(expectations),
                PrivateConfigPath = Path.GetFullPath(privateConfig),
                SourceRevision = sourceRevision
            };
        }
    }

    internal static class StrictJson
    {
        public static Dictionary<string, object> ReadObject(string path, string[] exactKeys, out FileIdentity identity)
        {
            FileSnapshot snapshot;
            try { snapshot = FileSnapshot.Read(path, 1024 * 1024); }
            catch (Exception) { throw new UsageException(); }
            byte[] bytes = snapshot.Bytes;
            identity = snapshot.Identity;
            if (bytes.Length == 0) throw new UsageException();
            string text = new UTF8Encoding(false, true).GetString(bytes);
            DuplicateKeyScanner.RejectTopLevelDuplicates(text);
            object decoded = new JavaScriptSerializer { MaxJsonLength = 1024 * 1024 }.DeserializeObject(text);
            Dictionary<string, object> value = decoded as Dictionary<string, object>;
            if (value == null || value.Count != exactKeys.Length) throw new UsageException();
            foreach (string key in exactKeys)
                if (!value.ContainsKey(key)) throw new UsageException();
            return value;
        }

        public static string String(Dictionary<string, object> value, string key)
        {
            string result = value[key] as string;
            if (System.String.IsNullOrEmpty(result)) throw new UsageException();
            return result;
        }

        public static long Integer(Dictionary<string, object> value, string key)
        {
            object raw = value[key];
            if (!(raw is int) && !(raw is long)) throw new UsageException();
            try { return Convert.ToInt64(raw, CultureInfo.InvariantCulture); }
            catch (Exception) { throw new UsageException(); }
        }

        public static string Sha256(Dictionary<string, object> value, string key)
        {
            string result = String(value, key).ToLowerInvariant();
            if (!Regex.IsMatch(result, "^[0-9a-f]{64}$")) throw new UsageException();
            return result;
        }

        public static List<string> SortedIdentifiers(Dictionary<string, object> value, string key)
        {
            object[] raw = value[key] as object[];
            if (raw == null || raw.Length == 0 || raw.Length > 64) throw new UsageException();
            List<string> result = new List<string>();
            string previous = null;
            foreach (object item in raw)
            {
                string identifier = item as string;
                if (System.String.IsNullOrEmpty(identifier) || !Regex.IsMatch(identifier, "^[a-z0-9][a-z0-9-]{0,63}$") ||
                    (previous != null && StringComparer.Ordinal.Compare(previous, identifier) >= 0))
                    throw new UsageException();
                result.Add(identifier);
                previous = identifier;
            }
            return result;
        }
    }

    internal static class DuplicateKeyScanner
    {
        public static void RejectTopLevelDuplicates(string text)
        {
            int position = 0;
            SkipWhitespace(text, ref position);
            Require(text, ref position, '{');
            HashSet<string> keys = new HashSet<string>(StringComparer.Ordinal);
            SkipWhitespace(text, ref position);
            if (Peek(text, position) == '}')
            {
                position++;
                SkipWhitespace(text, ref position);
                if (position != text.Length) throw new UsageException();
                return;
            }
            while (true)
            {
                string key = ReadString(text, ref position);
                if (!keys.Add(key)) throw new UsageException();
                SkipWhitespace(text, ref position);
                Require(text, ref position, ':');
                SkipValue(text, ref position);
                SkipWhitespace(text, ref position);
                char next = Peek(text, position);
                if (next == '}')
                {
                    position++;
                    break;
                }
                Require(text, ref position, ',');
                SkipWhitespace(text, ref position);
            }
            SkipWhitespace(text, ref position);
            if (position != text.Length) throw new UsageException();
        }

        private static void SkipValue(string text, ref int position)
        {
            SkipWhitespace(text, ref position);
            char value = Peek(text, position);
            if (value == '"') { ReadString(text, ref position); return; }
            if (value == '{') { SkipObject(text, ref position); return; }
            if (value == '[') { SkipArray(text, ref position); return; }
            int start = position;
            while (position < text.Length && ",}] \t\r\n".IndexOf(text[position]) < 0) position++;
            if (position == start) throw new UsageException();
        }

        private static void SkipObject(string text, ref int position)
        {
            Require(text, ref position, '{');
            SkipWhitespace(text, ref position);
            if (Peek(text, position) == '}')
            {
                position++;
                return;
            }
            while (true)
            {
                ReadString(text, ref position);
                SkipWhitespace(text, ref position);
                Require(text, ref position, ':');
                SkipValue(text, ref position);
                SkipWhitespace(text, ref position);
                char next = Peek(text, position);
                if (next == '}') { position++; return; }
                Require(text, ref position, ',');
                SkipWhitespace(text, ref position);
            }
        }

        private static void SkipArray(string text, ref int position)
        {
            Require(text, ref position, '[');
            SkipWhitespace(text, ref position);
            if (Peek(text, position) == ']')
            {
                position++;
                return;
            }
            while (true)
            {
                SkipValue(text, ref position);
                SkipWhitespace(text, ref position);
                char next = Peek(text, position);
                if (next == ']') { position++; return; }
                Require(text, ref position, ',');
            }
        }

        private static string ReadString(string text, ref int position)
        {
            SkipWhitespace(text, ref position);
            Require(text, ref position, '"');
            StringBuilder result = new StringBuilder();
            while (position < text.Length)
            {
                char value = text[position++];
                if (value == '"') return result.ToString();
                if (value < 0x20) throw new UsageException();
                if (value != '\\') { result.Append(value); continue; }
                if (position >= text.Length) throw new UsageException();
                char escaped = text[position++];
                switch (escaped)
                {
                    case '"': result.Append('"'); break;
                    case '\\': result.Append('\\'); break;
                    case '/': result.Append('/'); break;
                    case 'b': result.Append('\b'); break;
                    case 'f': result.Append('\f'); break;
                    case 'n': result.Append('\n'); break;
                    case 'r': result.Append('\r'); break;
                    case 't': result.Append('\t'); break;
                    case 'u':
                        if (position + 4 > text.Length) throw new UsageException();
                        int code;
                        if (!Int32.TryParse(text.Substring(position, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out code))
                            throw new UsageException();
                        result.Append((char)code);
                        position += 4;
                        break;
                    default: throw new UsageException();
                }
            }
            throw new UsageException();
        }

        private static void Require(string text, ref int position, char expected)
        {
            if (Peek(text, position) != expected) throw new UsageException();
            position++;
        }

        private static char Peek(string text, int position)
        {
            if (position >= text.Length) throw new UsageException();
            return text[position];
        }

        private static void SkipWhitespace(string text, ref int position)
        {
            while (position < text.Length && Char.IsWhiteSpace(text[position])) position++;
        }
    }

    internal sealed class Expectations
    {
        public string ProfileId;
        public long CleanFileCount;
        public long CleanTotalBytes;
        public long CleanManifestBytes;
        public string CleanManifestSha256;
        public long OriginalExecutableBytes;
        public string OriginalExecutableSha256;
        public long IsoBytes;
        public string IsoSha256;
        public string OpticalVolumeLabel;
        public long OpticalExecutableBytes;
        public string OpticalExecutableSha256;
        public long CompilerBytes;
        public string CompilerSha256;
        public long CompilerUiBytes;
        public string CompilerUiSha256;
        public string RegistryKeyId;
        public string RegistrySubkey;
        public string RegistryValueName;
        public int RegistryExactAccessMask;
        public List<string> RequiredApiIds;
        public List<string> RequiredToolIds;
        public FileIdentity SourceIdentity;

        public static Expectations Load(string path)
        {
            string[] keys = {
                "schema_version", "profile_id", "clean_file_count", "clean_total_bytes",
                "clean_manifest_bytes", "clean_manifest_sha256", "original_executable_bytes",
                "original_executable_sha256", "iso_bytes", "iso_sha256", "optical_volume_label",
                "optical_executable_bytes", "optical_executable_sha256", "registry_key_id",
                "registry_subkey", "registry_value_name", "registry_exact_access_mask",
                "required_api_ids", "required_tool_ids", "compiler_bytes", "compiler_sha256",
                "compiler_ui_bytes", "compiler_ui_sha256"
            };
            FileIdentity sourceIdentity;
            Dictionary<string, object> value = StrictJson.ReadObject(path, keys, out sourceIdentity);
            if (StrictJson.Integer(value, "schema_version") != 1) throw new UsageException();
            Expectations result = new Expectations();
            result.ProfileId = StrictJson.String(value, "profile_id");
            result.CleanFileCount = StrictJson.Integer(value, "clean_file_count");
            result.CleanTotalBytes = StrictJson.Integer(value, "clean_total_bytes");
            result.CleanManifestBytes = StrictJson.Integer(value, "clean_manifest_bytes");
            result.CleanManifestSha256 = StrictJson.Sha256(value, "clean_manifest_sha256");
            result.OriginalExecutableBytes = StrictJson.Integer(value, "original_executable_bytes");
            result.OriginalExecutableSha256 = StrictJson.Sha256(value, "original_executable_sha256");
            result.IsoBytes = StrictJson.Integer(value, "iso_bytes");
            result.IsoSha256 = StrictJson.Sha256(value, "iso_sha256");
            result.OpticalVolumeLabel = StrictJson.String(value, "optical_volume_label");
            result.OpticalExecutableBytes = StrictJson.Integer(value, "optical_executable_bytes");
            result.OpticalExecutableSha256 = StrictJson.Sha256(value, "optical_executable_sha256");
            result.CompilerBytes = StrictJson.Integer(value, "compiler_bytes");
            result.CompilerSha256 = StrictJson.Sha256(value, "compiler_sha256");
            result.CompilerUiBytes = StrictJson.Integer(value, "compiler_ui_bytes");
            result.CompilerUiSha256 = StrictJson.Sha256(value, "compiler_ui_sha256");
            result.RegistryKeyId = StrictJson.String(value, "registry_key_id");
            result.RegistrySubkey = StrictJson.String(value, "registry_subkey");
            result.RegistryValueName = StrictJson.String(value, "registry_value_name");
            result.RequiredApiIds = StrictJson.SortedIdentifiers(value, "required_api_ids");
            result.RequiredToolIds = StrictJson.SortedIdentifiers(value, "required_tool_ids");
            result.SourceIdentity = sourceIdentity;
            long access = StrictJson.Integer(value, "registry_exact_access_mask");
            if (access < 0 || access > Int32.MaxValue) throw new UsageException();
            result.RegistryExactAccessMask = (int)access;
            if (result.RegistryExactAccessMask != 0x000f003f || result.CleanFileCount <= 0 || result.CleanFileCount > 1000000 ||
                result.CleanTotalBytes <= 0 || result.CleanTotalBytes > (1L << 50) ||
                result.CleanManifestBytes <= 0 || result.CleanManifestBytes > 1024 * 1024 ||
                result.OriginalExecutableBytes <= 0 || result.OriginalExecutableBytes > (1L << 34) ||
                result.IsoBytes <= 0 || result.IsoBytes > (1L << 40) ||
                result.OpticalExecutableBytes <= 0 || result.OpticalExecutableBytes > (1L << 34) ||
                result.CompilerBytes <= 0 || result.CompilerBytes > (1L << 34) ||
                result.CompilerUiBytes <= 0 || result.CompilerUiBytes > (1L << 34))
                throw new UsageException();
            ValidateSupported(result.RequiredApiIds, CapabilityCatalog.ApiIds);
            ValidateSupported(result.RequiredToolIds, CapabilityCatalog.ToolIds);
            return result;
        }

        private static void ValidateSupported(IEnumerable<string> required, IEnumerable<string> supported)
        {
            HashSet<string> available = new HashSet<string>(supported, StringComparer.Ordinal);
            foreach (string id in required)
                if (!available.Contains(id)) throw new UsageException();
        }
    }

    internal sealed class PrivateLocator
    {
        public string CleanTree;
        public string CleanManifest;
        public string InstalledTree;
        public string VirtualStoreTree;
        public string IsoFile;
        public string OpticalRoot;
        public FileIdentity SourceIdentity;

        public static PrivateLocator Load(string path)
        {
            string[] keys = { "schema_version", "clean_tree", "clean_manifest", "installed_tree", "virtual_store_tree", "iso_file", "optical_root" };
            FileIdentity sourceIdentity;
            Dictionary<string, object> value = StrictJson.ReadObject(path, keys, out sourceIdentity);
            if (StrictJson.Integer(value, "schema_version") != 1) throw new UsageException();
            PrivateLocator result = new PrivateLocator();
            result.CleanTree = FullPath(value, "clean_tree");
            result.CleanManifest = FullPath(value, "clean_manifest");
            result.InstalledTree = FullPath(value, "installed_tree");
            result.VirtualStoreTree = FullPath(value, "virtual_store_tree");
            result.IsoFile = FullPath(value, "iso_file");
            string opticalRoot = StrictJson.String(value, "optical_root");
            if (!Path.IsPathRooted(opticalRoot)) throw new UsageException();
            result.OpticalRoot = Path.GetFullPath(opticalRoot);
            if (!Regex.IsMatch(result.OpticalRoot, "^[A-Za-z]:\\\\$")) throw new UsageException();
            HashSet<string> distinctPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string locatorPath in result.AllPaths())
                if (!distinctPaths.Add(PathSafety.PreserveRoot(locatorPath)))
                    throw new UsageException();
            result.SourceIdentity = sourceIdentity;
            return result;
        }

        private static string FullPath(Dictionary<string, object> value, string key)
        {
            string raw = StrictJson.String(value, key);
            if (!Path.IsPathRooted(raw)) throw new UsageException();
            return PathSafety.PreserveRoot(Path.GetFullPath(raw));
        }

        public IEnumerable<string> AllPaths()
        {
            yield return CleanTree;
            yield return CleanManifest;
            yield return InstalledTree;
            yield return VirtualStoreTree;
            yield return IsoFile;
            yield return OpticalRoot;
        }
    }

    internal sealed class ProbeResult
    {
        public SortedDictionary<string, object> Document;
        public int ExitCode;
        public Redactor Redactor;
    }

    internal sealed class CheckRecord
    {
        public string Id;
        public bool Required;
        public string Outcome;
        public string Detail;
    }

    internal sealed class Probe
    {
        private readonly string sourceRevision;
        private readonly string expectationsPath;
        private readonly string privateConfigPath;
        private readonly Expectations expectations;
        private readonly PrivateLocator locator;
        private readonly List<CheckRecord> checks = new List<CheckRecord>();
        private readonly List<object> errors = new List<object>();
        private readonly Redactor redactor = new Redactor();

        public Probe(string sourceRevision, string expectationsPath, string privateConfigPath,
            Expectations expectations, PrivateLocator locator)
        {
            this.sourceRevision = sourceRevision;
            this.expectationsPath = expectationsPath;
            this.privateConfigPath = privateConfigPath;
            this.expectations = expectations;
            this.locator = locator;
            foreach (string path in locator.AllPaths()) redactor.Add(path);
            redactor.Add(expectationsPath);
            redactor.Add(privateConfigPath);
            redactor.Add(Environment.UserName);
            redactor.Add(Environment.MachineName);
            redactor.Add(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile));
        }

        public ProbeResult Run()
        {
            Stopwatch elapsed = Stopwatch.StartNew();
            DateTime observedAt = DateTime.UtcNow;
            string executablePath = Assembly.GetExecutingAssembly().Location;
            redactor.Add(executablePath);

            FileIdentity executable = FileIdentity.Read(executablePath);
            FileIdentity expectationsIdentity = expectations.SourceIdentity;
            FileIdentity privateIdentity = locator.SourceIdentity;

            bool privateInputsDistinct = PathSafety.AreDistinctExistingObjects(locator.AllPaths());
            AddCheck("private-inputs-distinct", true, privateInputsDistinct,
                privateInputsDistinct ? "distinct" : "alias-detected");

            int gameCountBefore = CountGameProcesses();
            AddCheck("no-game-process-before", true, gameCountBefore == 0, gameCountBefore == 0 ? "absent" : "present");
            AddCheck("probe-process-x86", true, !Environment.Is64BitProcess,
                Environment.Is64BitProcess ? "x64" : "x86");

            SortedDictionary<string, object> host = ObserveHost();
            SessionObservation session = ObserveSession();
            TokenObservation explorerToken = session.ExplorerToken;
            TokenObservation currentToken = null;
            RegistryObservation registry;
            try
            {
                AddCheck("active-input-desktop", true,
                    QualificationPolicy.SessionSafe(session.ActiveConsoleSessionId, session.ExplorerSessionId, session.InputDesktopName),
                    session.InputDesktopName == "Default" ? "default" : "not-default");

                bool currentTokenWasThreadToken;
                currentToken = TokenObservation.EffectiveCurrent(out currentTokenWasThreadToken);
                bool currentHigh = QualificationPolicy.DirectTokenHazard(currentToken);
                bool explorerMedium = QualificationPolicy.ExplorerTokenSafe(currentToken, explorerToken, session.ActiveConsoleSessionId);
                AddCheck("wsl-token-high-hazard", true, currentHigh, currentHigh ? "confirmed" : "unexpected-token");
                AddCheck("explorer-token-medium", true, explorerMedium, explorerMedium ? "confirmed" : "unexpected-token");
                registry = ObserveRegistry(currentToken, currentTokenWasThreadToken, explorerToken);
            }
            finally
            {
                explorerToken.DisposeImpersonationToken();
            }
            AddCheck("registry-current-exact-access", true, QualificationPolicy.DirectRegistryAccessExpected(registry.CurrentAccessResult),
                "win32-" + registry.CurrentAccessResult.ToString(CultureInfo.InvariantCulture));
            AddCheck("registry-explorer-exact-denial", true, QualificationPolicy.ExplorerRegistryDenied(registry.ExplorerAccessResult),
                "win32-" + registry.ExplorerAccessResult.ToString(CultureInfo.InvariantCulture));
            AddCheck("registry-location-binding", true, registry.LocationMatchesInstalled,
                registry.LocationMatchesInstalled ? "matches" : "mismatch");
            AddCheck("registry-read-only", true, registry.LastWriteBefore == registry.LastWriteAfter,
                registry.LastWriteBefore == registry.LastWriteAfter ? "unchanged" : "changed");

            TreeManifest installedBefore = TreeManifest.Capture(locator.InstalledTree, false);
            TreeManifest virtualBefore = TreeManifest.CaptureOptional(locator.VirtualStoreTree);

            CleanObservation clean = ObserveClean();
            AddCheck("clean-manifest-identity", true, clean.ManifestMatches, clean.ManifestMatches ? "exact" : "mismatch");
            AddCheck("clean-tree-exact", true, clean.BothMatch && clean.Unchanged,
                clean.BothMatch && clean.Unchanged ? "two-captures-exact" : "mismatch-or-mutation");
            AddCheck("clean-tree-read-only", true, clean.Before.WritableOpenCount == 0 && clean.After.WritableOpenCount == 0,
                clean.Before.WritableOpenCount == 0 && clean.After.WritableOpenCount == 0 ? "non-writable" : "writable");

            IsoObservation iso = ObserveIso();
            AddCheck("iso-identity", true, iso.IsoMatches, iso.IsoMatches ? "exact" : "mismatch");
            AddCheck("optical-media", true, iso.OpticalMatches, iso.OpticalMatches ? "exact" : "mismatch");

            SortedDictionary<string, object> capabilities = ObserveCapabilities();
            bool requiredTools = RequiredCapabilitiesPresent(capabilities);
            AddCheck("required-host-tools", true, requiredTools, requiredTools ? "available" : "missing");

            TreeManifest installedAfter = TreeManifest.Capture(locator.InstalledTree, false);
            TreeManifest virtualAfter = TreeManifest.CaptureOptional(locator.VirtualStoreTree);
            bool installedStable = installedBefore.SameIdentity(installedAfter);
            bool virtualStable = virtualBefore.SameIdentity(virtualAfter);
            bool installedPlain = installedBefore.IsPlain(true) && installedAfter.IsPlain(true);
            bool virtualPlain = virtualBefore.IsPlain(false) && virtualAfter.IsPlain(false);
            AddCheck("installed-tree-plain", true, installedPlain, installedPlain ? "plain" : "unsafe-entry");
            AddCheck("installed-tree-stable", true, installedStable, installedStable ? "unchanged" : "changed");
            AddCheck("virtual-store-plain", true, virtualPlain, virtualPlain ? "plain-or-absent" : "unsafe-entry");
            AddCheck("virtual-store-stable", true, virtualStable, virtualStable ? "unchanged" : "changed");

            int gameCountAfter = CountGameProcesses();
            AddCheck("no-game-process-after", true, gameCountAfter == 0, gameCountAfter == 0 ? "absent" : "present");

            FileIdentity executableAfter = FileIdentity.Read(executablePath);
            AddCheck("probe-image-stable", true, executable.Same(executableAfter), executable.Same(executableAfter) ? "unchanged" : "changed");

            checks.Sort(delegate(CheckRecord left, CheckRecord right) { return StringComparer.Ordinal.Compare(left.Id, right.Id); });
            List<object> checkJson = new List<object>();
            int passed = 0;
            int failed = 0;
            int errored = 0;
            foreach (CheckRecord check in checks)
            {
                checkJson.Add(JsonObjects.Object("detail_code", check.Detail, "id", check.Id, "outcome", check.Outcome, "required", check.Required));
                if (check.Outcome == "pass") passed++;
                else if (check.Outcome == "fail") failed++;
                else errored++;
            }
            bool complete = QualificationPolicy.IsComplete(checks);
            bool eligible = QualificationPolicy.IsEligible(checks);
            string verdict = eligible ? "eligible-for-synthetic-launcher-test" : (complete ? "unsafe" : "inconclusive");

            errors.Sort(delegate(object left, object right)
            {
                IDictionary<string, object> l = (IDictionary<string, object>)left;
                IDictionary<string, object> r = (IDictionary<string, object>)right;
                return StringComparer.Ordinal.Compare((string)l["check_id"], (string)r["check_id"]);
            });

            elapsed.Stop();
            SortedDictionary<string, object> document = JsonObjects.Object(
                "capabilities", capabilities,
                "checks", checkJson,
                "errors", errors,
                "guards", JsonObjects.Object(
                    "cm0102_launched", false,
                    "game_process_count_after", gameCountAfter,
                    "game_process_count_before", gameCountBefore,
                    "private_inputs_distinct", privateInputsDistinct,
                    "installed_tree", JsonObjects.Object("after", installedAfter.ToJson(), "before", installedBefore.ToJson(), "unchanged", installedStable),
                    "virtual_store_tree", JsonObjects.Object("after", virtualAfter.ToJson(), "before", virtualBefore.ToJson(), "unchanged", virtualStable)),
                "host", host,
                "inputs", JsonObjects.Object("clean", clean.ToJson(), "iso", iso.ToJson()),
                "probe", JsonObjects.Object(
                    "executable", executable.ToJson(),
                    "executable_after", executableAfter.ToJson(),
                    "executable_unchanged", executable.Same(executableAfter),
                    "expectations_sha256", expectationsIdentity.Sha256,
                    "id", "cm0102-original-host-qualification",
                    "private_locator_sha256", privateIdentity.Sha256,
                    "process_architecture", Environment.Is64BitProcess ? "x64" : "x86",
                    "source_revision", sourceRevision,
                    "version", "1.0.0"),
                "registry", registry.ToJson(expectations.RegistryKeyId, expectations.RegistryExactAccessMask),
                "run", JsonObjects.Object(
                    "elapsed_ms", elapsed.ElapsedMilliseconds,
                    "observed_at_utc", observedAt.ToString("yyyy-MM-dd'T'HH:mm:ss.fffffff'Z'", CultureInfo.InvariantCulture)),
                "schema_version", 1,
                "session", session.ToJson(),
                "summary", JsonObjects.Object(
                    "comparison_verdict", "not-run",
                    "completeness", complete ? "complete" : "incomplete",
                    "direct_wsl_launch_safe", false,
                    "error_count", errored,
                    "failed_count", failed,
                    "original_execution_status", "not-run",
                    "passed_count", passed,
                    "required_check_count", checks.Count,
                    "safety_verdict", verdict),
                "tokens", JsonObjects.Object("explorer", explorerToken.ToJson(), "impersonation_restored", registry.ImpersonationRestored,
                    "probe", currentToken.ToJson()));

            return new ProbeResult
            {
                Document = document,
                ExitCode = eligible ? 0 : (complete ? 2 : 3),
                Redactor = redactor
            };
        }

        private void AddCheck(string id, bool required, bool condition, string detail)
        {
            checks.Add(new CheckRecord { Id = id, Required = required, Outcome = condition ? "pass" : "fail", Detail = detail });
        }

        private SortedDictionary<string, object> ObserveHost()
        {
            NativeMethods.RTL_OSVERSIONINFOEX version = new NativeMethods.RTL_OSVERSIONINFOEX();
            version.dwOSVersionInfoSize = Marshal.SizeOf(version);
            int status = NativeMethods.RtlGetVersion(ref version);
            if (status != 0) throw new InvalidOperationException("rtl-version-failed");
            string productName;
            string displayVersion;
            string edition;
            using (RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64))
            using (RegistryKey currentVersion = baseKey.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion", false))
            {
                productName = ReadRegistryString(currentVersion, "ProductName");
                displayVersion = ReadRegistryString(currentVersion, "DisplayVersion");
                edition = ReadRegistryString(currentVersion, "EditionID");
            }
            string machineFingerprint = Hashing.StringSha256(Environment.MachineName + "\n" + version.dwBuildNumber.ToString(CultureInfo.InvariantCulture));
            return JsonObjects.Object(
                "architecture", Environment.Is64BitOperatingSystem ? "x86-64" : "x86",
                "display_version", displayVersion,
                "edition", edition,
                "locale", CultureInfo.CurrentCulture.Name,
                "machine_fingerprint_sha256", machineFingerprint,
                "os_build", (long)version.dwBuildNumber,
                "os_major", (long)version.dwMajorVersion,
                "os_minor", (long)version.dwMinorVersion,
                "product_name", productName,
                "time_zone", TimeZoneInfo.Local.Id);
        }

        private static string ReadRegistryString(RegistryKey key, string name)
        {
            if (key == null) return "unavailable";
            object value = key.GetValue(name, null, RegistryValueOptions.DoNotExpandEnvironmentNames);
            return value is string ? (string)value : "unavailable";
        }

        private SessionObservation ObserveSession()
        {
            uint active = NativeMethods.WTSGetActiveConsoleSessionId();
            Process[] explorers = Process.GetProcessesByName("explorer");
            try
            {
                List<Process> matching = new List<Process>();
                foreach (Process process in explorers)
                    if ((uint)process.SessionId == active) matching.Add(process);
                if (matching.Count != 1) throw new InvalidOperationException("active-explorer-count");
                string inputDesktop = NativeMethods.GetInputDesktopName();
                string windowStation = NativeMethods.GetWindowStationName();
                Screen primary = Screen.PrimaryScreen;
                int currentSession;
                using (Process current = Process.GetCurrentProcess()) currentSession = current.SessionId;
                SessionObservation result = new SessionObservation
                {
                    ActiveConsoleSessionId = active,
                    CurrentSessionId = currentSession,
                    ExplorerSessionId = matching[0].SessionId,
                    ExplorerProcessCount = matching.Count,
                    InputDesktopName = inputDesktop,
                    WindowStationName = windowStation,
                    ScreenWidth = primary.Bounds.Width,
                    ScreenHeight = primary.Bounds.Height,
                    BitsPerPixel = primary.BitsPerPixel
                };
                result.ExplorerToken = TokenObservation.FromProcess(matching[0]);
                return result;
            }
            finally
            {
                foreach (Process process in explorers) process.Dispose();
            }
        }

        private RegistryObservation ObserveRegistry(TokenObservation currentToken, bool currentTokenWasThreadToken,
            TokenObservation explorerToken)
        {
            long before = NativeMethods.RegistryLastWrite(expectations.RegistrySubkey);
            int currentResult = NativeMethods.ExactRegistryOpen(expectations.RegistrySubkey, expectations.RegistryExactAccessMask);
            int explorerResult;
            using (WindowsImpersonationContext context = WindowsIdentity.Impersonate(explorerToken.ImpersonationTokenHandle))
            {
                try { explorerResult = NativeMethods.ExactRegistryOpen(expectations.RegistrySubkey, expectations.RegistryExactAccessMask); }
                finally { context.Undo(); }
            }
            bool restoredTokenIsThreadToken;
            TokenObservation restoredToken = TokenObservation.EffectiveCurrent(out restoredTokenIsThreadToken);
            if (restoredTokenIsThreadToken != currentTokenWasThreadToken || !restoredToken.SecurityEquivalent(currentToken))
                throw new InvalidOperationException("impersonation-not-restored");

            string location;
            string owner;
            string group;
            List<object> aces = new List<object>();
            RegistryValueKind valueKind;
            using (RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry32))
            using (RegistryKey key = baseKey.OpenSubKey(expectations.RegistrySubkey, RegistryKeyPermissionCheck.ReadSubTree,
                RegistryRights.ReadKey))
            {
                if (key == null) throw new InvalidOperationException("registry-key-missing");
                object rawValue = key.GetValue(expectations.RegistryValueName, null, RegistryValueOptions.DoNotExpandEnvironmentNames);
                location = rawValue as string;
                if (location == null) throw new InvalidOperationException("registry-value-invalid");
                redactor.Add(location);
                RegistrySecurity security = key.GetAccessControl(AccessControlSections.Access | AccessControlSections.Owner | AccessControlSections.Group);
                owner = ((SecurityIdentifier)security.GetOwner(typeof(SecurityIdentifier))).Value;
                group = ((SecurityIdentifier)security.GetGroup(typeof(SecurityIdentifier))).Value;
                AuthorizationRuleCollection rules = security.GetAccessRules(true, true, typeof(SecurityIdentifier));
                foreach (RegistryAccessRule rule in rules)
                {
                    aces.Add(JsonObjects.Object(
                        "access_mask", (long)rule.RegistryRights,
                        "access_type", rule.AccessControlType == AccessControlType.Allow ? "allow" : "deny",
                        "identity_sid", rule.IdentityReference.Value,
                        "inherited", rule.IsInherited,
                        "inheritance_flags", (long)rule.InheritanceFlags,
                        "propagation_flags", (long)rule.PropagationFlags));
                }
                valueKind = key.GetValueKind(expectations.RegistryValueName);
            }
            aces.Sort(delegate(object left, object right)
            {
                IDictionary<string, object> l = (IDictionary<string, object>)left;
                IDictionary<string, object> r = (IDictionary<string, object>)right;
                int sid = StringComparer.Ordinal.Compare((string)l["identity_sid"], (string)r["identity_sid"]);
                if (sid != 0) return sid;
                return Convert.ToInt64(l["access_mask"]).CompareTo(Convert.ToInt64(r["access_mask"]));
            });
            long after = NativeMethods.RegistryLastWrite(expectations.RegistrySubkey);
            string normalizedLocation = NormalizePath(location);
            string normalizedInstalled = NormalizePath(locator.InstalledTree);
            return new RegistryObservation
            {
                CurrentAccessResult = currentResult,
                ExplorerAccessResult = explorerResult,
                ImpersonationRestored = true,
                LastWriteBefore = before,
                LastWriteAfter = after,
                LocationMatchesInstalled = String.Equals(normalizedLocation, normalizedInstalled, StringComparison.OrdinalIgnoreCase),
                LocationSha256 = Hashing.StringSha256(location),
                LocationUtf16Bytes = Encoding.Unicode.GetByteCount(location),
                ValueKind = valueKind.ToString(),
                OwnerSid = owner,
                GroupSid = group,
                Aces = aces
            };
        }

        private static string NormalizePath(string path)
        {
            return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        }

        private CleanObservation ObserveClean()
        {
            FileSnapshot manifestSnapshot = FileSnapshot.Read(locator.CleanManifest, 1024 * 1024);
            Dictionary<string, ManifestRow> expectedRows = ManifestRow.Parse(manifestSnapshot.Bytes);
            HashSet<string> expectedDirectories = ManifestRow.ExpectedDirectories(expectedRows.Keys);
            CleanCaptureObservation before = ObserveCleanCapture(expectedRows, expectedDirectories);
            CleanCaptureObservation after = ObserveCleanCapture(expectedRows, expectedDirectories);
            bool manifestMatches = QualificationPolicy.IdentityMatches(manifestSnapshot.Identity,
                expectations.CleanManifestBytes, expectations.CleanManifestSha256);
            return new CleanObservation
            {
                Manifest = manifestSnapshot.Identity,
                ManifestMatches = manifestMatches,
                Before = before,
                After = after,
                BothMatch = before.TreeMatches && after.TreeMatches,
                Unchanged = before.Tree.SameIdentity(after.Tree) && before.Executable.Same(after.Executable)
            };
        }

        private CleanCaptureObservation ObserveCleanCapture(Dictionary<string, ManifestRow> expectedRows,
            HashSet<string> expectedDirectories)
        {
            TreeManifest tree = TreeManifest.Capture(locator.CleanTree, true);
            int missing = 0;
            int extra = 0;
            int mismatched = 0;
            foreach (KeyValuePair<string, ManifestRow> expected in expectedRows)
            {
                TreeRow actual;
                if (!tree.Rows.TryGetValue(expected.Key, out actual)) missing++;
                else if (actual.Bytes != expected.Value.Bytes || !String.Equals(actual.Sha256, expected.Value.Sha256, StringComparison.OrdinalIgnoreCase)) mismatched++;
            }
            foreach (string actual in tree.Rows.Keys)
                if (!expectedRows.ContainsKey(actual)) extra++;
            int directoryMissing;
            int directoryExtra;
            QualificationPolicy.DirectoryDifference(tree, expectedDirectories, out directoryMissing, out directoryExtra);
            TreeRow executable;
            bool hasExecutable = tree.Rows.TryGetValue("cm0102.exe", out executable);
            bool treeMatches = tree.FileCount == expectations.CleanFileCount && tree.TotalBytes == expectations.CleanTotalBytes &&
                expectedRows.Count == expectations.CleanFileCount && missing == 0 && extra == 0 && mismatched == 0 &&
                directoryMissing == 0 && directoryExtra == 0 && tree.IsPlain(true) &&
                hasExecutable && executable.Bytes == expectations.OriginalExecutableBytes &&
                executable.Sha256 == expectations.OriginalExecutableSha256;
            FileIdentity executableIdentity = hasExecutable ?
                new FileIdentity { Bytes = executable.Bytes, Sha256 = executable.Sha256 } :
                new FileIdentity { Bytes = 0, Sha256 = Hashing.BytesSha256(new byte[0]) };
            return new CleanCaptureObservation
            {
                Tree = tree,
                TreeMatches = treeMatches,
                Executable = executableIdentity,
                ExecutableMatches = hasExecutable && executable.Bytes == expectations.OriginalExecutableBytes &&
                    executable.Sha256 == expectations.OriginalExecutableSha256,
                MissingCount = missing,
                ExtraCount = extra,
                MismatchCount = mismatched,
                DirectoryMissingCount = directoryMissing,
                DirectoryExtraCount = directoryExtra,
                WritableOpenCount = tree.WritableOpenCount
            };
        }

        private IsoObservation ObserveIso()
        {
            FileIdentity iso = FileIdentity.Read(locator.IsoFile);
            bool isoMatches = QualificationPolicy.IdentityMatches(iso, expectations.IsoBytes, expectations.IsoSha256);
            uint driveType = NativeMethods.GetDriveTypeW(locator.OpticalRoot);
            string label = NativeMethods.GetVolumeLabel(locator.OpticalRoot);
            string opticalExecutablePath = Path.Combine(locator.OpticalRoot, "cm0102.exe");
            FileIdentity opticalExecutable = FileIdentity.Read(opticalExecutablePath);
            redactor.Add(opticalExecutablePath);
            bool opticalMatches = driveType == NativeMethods.DriveCdrom && label == expectations.OpticalVolumeLabel &&
                opticalExecutable.Bytes == expectations.OpticalExecutableBytes &&
                opticalExecutable.Sha256 == expectations.OpticalExecutableSha256;
            return new IsoObservation
            {
                Iso = iso,
                IsoMatches = isoMatches,
                DriveType = driveType,
                VolumeLabelSha256 = Hashing.StringSha256(label),
                VolumeLabelMatches = label == expectations.OpticalVolumeLabel,
                OpticalExecutable = opticalExecutable,
                OpticalMatches = opticalMatches
            };
        }

        private SortedDictionary<string, object> ObserveCapabilities()
        {
            string windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            string system = Environment.GetFolderPath(Environment.SpecialFolder.System);
            Dictionary<string, string> candidates = CapabilityCatalog.ToolPaths(windows, system);
            HashSet<string> requiredTools = new HashSet<string>(expectations.RequiredToolIds, StringComparer.Ordinal);
            List<object> tools = new List<object>();
            foreach (KeyValuePair<string, string> candidate in candidates)
            {
                redactor.Add(candidate.Value);
                bool present = File.Exists(candidate.Value);
                tools.Add(JsonObjects.Object(
                    "file", present ? FileIdentity.Read(candidate.Value).ToJson() : null,
                    "id", candidate.Key,
                    "present", present,
                    "required", requiredTools.Contains(candidate.Key)));
            }
            tools.Sort(delegate(object left, object right)
            {
                return StringComparer.Ordinal.Compare((string)((IDictionary<string, object>)left)["id"], (string)((IDictionary<string, object>)right)["id"]);
            });
            HashSet<string> requiredApis = new HashSet<string>(expectations.RequiredApiIds, StringComparer.Ordinal);
            List<object> apis = new List<object>();
            foreach (string id in CapabilityCatalog.ApiIds)
            {
                apis.Add(JsonObjects.Object("id", id, "present", CapabilityCatalog.ApiPresent(id),
                    "required", requiredApis.Contains(id)));
            }
            return JsonObjects.Object("apis", apis, "tools", tools);
        }

        private static bool RequiredCapabilitiesPresent(SortedDictionary<string, object> capabilities)
        {
            foreach (string group in new string[] { "apis", "tools" })
            {
                IEnumerable entries = (IEnumerable)capabilities[group];
                foreach (object item in entries)
                {
                    IDictionary<string, object> entry = (IDictionary<string, object>)item;
                    if ((bool)entry["required"] && !(bool)entry["present"]) return false;
                }
            }
            return true;
        }

        private static int CountGameProcesses()
        {
            int count = 0;
            foreach (string name in new string[] { "cm0102", "cm0102_GDI" })
            {
                Process[] processes = Process.GetProcessesByName(name);
                count += processes.Length;
                foreach (Process process in processes) process.Dispose();
            }
            return count;
        }
    }

    internal static class CapabilityCatalog
    {
        public static readonly string[] ApiIds = {
            "advapi32-registry", "advapi32-token", "kernel32-filesystem", "user32-desktop", "wtsapi32-session"
        };
        public static readonly string[] ToolIds = { "cdb", "cmd", "csc-x64", "csc-x86", "powershell", "python313", "windbg" };

        public static Dictionary<string, string> ToolPaths(string windows, string system)
        {
            return new Dictionary<string, string>(StringComparer.Ordinal)
            {
                { "cdb", Path.Combine(Path.GetPathRoot(windows), @"Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe") },
                { "cmd", Path.Combine(system, "cmd.exe") },
                { "csc-x64", Path.Combine(windows, @"Microsoft.NET\Framework64\v4.0.30319\csc.exe") },
                { "csc-x86", Path.Combine(windows, @"Microsoft.NET\Framework\v4.0.30319\csc.exe") },
                { "powershell", Path.Combine(system, @"WindowsPowerShell\v1.0\powershell.exe") },
                { "python313", Path.Combine(Path.GetPathRoot(windows), @"Python313\python.exe") },
                { "windbg", Path.Combine(Path.GetPathRoot(windows), @"Program Files (x86)\Windows Kits\10\Debuggers\x86\windbg.exe") }
            };
        }

        public static bool ApiPresent(string id)
        {
            if (id == "advapi32-registry") return NativeMethods.ExportsPresent("advapi32.dll", new string[] { "RegOpenKeyExA", "RegQueryInfoKeyA" });
            if (id == "advapi32-token") return NativeMethods.ExportsPresent("advapi32.dll", new string[] { "OpenProcessToken", "DuplicateTokenEx", "GetTokenInformation" });
            if (id == "kernel32-filesystem") return NativeMethods.ExportsPresent("kernel32.dll", new string[] { "CreateFileW", "GetFinalPathNameByHandleW", "GetFileInformationByHandle" });
            if (id == "user32-desktop") return NativeMethods.ExportsPresent("user32.dll", new string[] { "OpenInputDesktop", "GetUserObjectInformationW" });
            if (id == "wtsapi32-session") return NativeMethods.ExportsPresent("wtsapi32.dll", new string[] { "WTSQuerySessionInformationW" });
            throw new InvalidOperationException("unknown-api-id");
        }
    }

    internal static class QualificationPolicy
    {
        public static readonly string[] RequiredCheckIds = {
            "active-input-desktop", "clean-manifest-identity", "clean-tree-exact", "clean-tree-read-only",
            "explorer-token-medium", "installed-tree-plain", "installed-tree-stable", "iso-identity",
            "no-game-process-after", "no-game-process-before", "optical-media", "private-inputs-distinct",
            "probe-image-stable", "probe-process-x86", "registry-current-exact-access",
            "registry-explorer-exact-denial", "registry-location-binding", "registry-read-only",
            "required-host-tools", "virtual-store-plain", "virtual-store-stable", "wsl-token-high-hazard"
        };

        public static bool DirectTokenHazard(TokenObservation token)
        {
            return token != null && token.Integrity == "high" && token.IsAdministrator;
        }

        public static bool ExplorerTokenSafe(TokenObservation current, TokenObservation explorer, uint activeSession)
        {
            return current != null && explorer != null && explorer.Integrity == "medium" && !explorer.IsAdministrator &&
                explorer.SessionId == activeSession && explorer.RawSid == current.RawSid;
        }

        public static bool SessionSafe(uint activeSession, int explorerSession, string desktop)
        {
            return activeSession == explorerSession && desktop == "Default";
        }

        public static bool DirectRegistryAccessExpected(int result) { return result == 0; }
        public static bool ExplorerRegistryDenied(int result) { return result == NativeMethods.ErrorAccessDenied; }

        public static bool IdentityMatches(FileIdentity actual, long expectedBytes, string expectedSha256)
        {
            return actual != null && actual.Bytes == expectedBytes && actual.Sha256 == expectedSha256;
        }

        public static void DirectoryDifference(TreeManifest tree, HashSet<string> expected,
            out int missing, out int extra)
        {
            missing = 0;
            extra = 0;
            foreach (string expectedDirectory in expected)
                if (!tree.DirectoryPaths.Contains(expectedDirectory)) missing++;
            foreach (string actualDirectory in tree.DirectoryPaths)
                if (!expected.Contains(actualDirectory)) extra++;
        }

        public static bool IsComplete(IEnumerable<CheckRecord> checks)
        {
            HashSet<string> expected = new HashSet<string>(RequiredCheckIds, StringComparer.Ordinal);
            HashSet<string> observed = new HashSet<string>(StringComparer.Ordinal);
            foreach (CheckRecord check in checks)
            {
                if (!check.Required || !expected.Contains(check.Id) || !observed.Add(check.Id) || check.Outcome == "error") return false;
            }
            return observed.SetEquals(expected);
        }

        public static bool IsEligible(IEnumerable<CheckRecord> checks)
        {
            if (!IsComplete(checks)) return false;
            foreach (CheckRecord check in checks)
                if (check.Required && check.Outcome != "pass") return false;
            return true;
        }
    }

    internal sealed class SessionObservation
    {
        public uint ActiveConsoleSessionId;
        public int CurrentSessionId;
        public int ExplorerSessionId;
        public int ExplorerProcessCount;
        public string InputDesktopName;
        public string WindowStationName;
        public int ScreenWidth;
        public int ScreenHeight;
        public int BitsPerPixel;
        public TokenObservation ExplorerToken;

        public SortedDictionary<string, object> ToJson()
        {
            return JsonObjects.Object(
                "active_console_session_id", (long)ActiveConsoleSessionId,
                "bits_per_pixel", BitsPerPixel,
                "current_process_session_id", CurrentSessionId,
                "explorer_process_count", ExplorerProcessCount,
                "explorer_session_id", ExplorerSessionId,
                "input_desktop", InputDesktopName,
                "screen_height", ScreenHeight,
                "screen_width", ScreenWidth,
                "window_station", WindowStationName);
        }
    }

    internal sealed class TokenObservation
    {
        public string RawSid;
        public int SessionId;
        public string Integrity;
        public string ElevationType;
        public bool IsAdministrator;
        public List<object> Privileges;
        private SafeKernelHandle duplicatedImpersonationToken;

        public IntPtr ImpersonationTokenHandle
        {
            get
            {
                if (duplicatedImpersonationToken == null || duplicatedImpersonationToken.IsInvalid || duplicatedImpersonationToken.IsClosed)
                    throw new InvalidOperationException("explorer-token-unavailable");
                return duplicatedImpersonationToken.DangerousGetHandle();
            }
        }

        public static TokenObservation Current()
        {
            IntPtr token;
            if (!NativeMethods.OpenProcessToken(NativeMethods.GetCurrentProcess(), NativeMethods.TokenQuery | NativeMethods.TokenDuplicate, out token))
                throw new InvalidOperationException("open-current-token");
            try { return FromToken(token, false); }
            finally { NativeMethods.CloseHandle(token); }
        }

        public static TokenObservation EffectiveCurrent(out bool fromThreadToken)
        {
            IntPtr token;
            if (NativeMethods.TryOpenCurrentThreadToken(out token))
            {
                fromThreadToken = true;
                try { return FromToken(token, false); }
                finally { NativeMethods.CloseHandle(token); }
            }
            fromThreadToken = false;
            return Current();
        }

        public static TokenObservation FromProcess(Process process)
        {
            IntPtr handle = NativeMethods.OpenProcess(NativeMethods.ProcessQueryLimitedInformation, false, process.Id);
            if (handle == IntPtr.Zero) throw new InvalidOperationException("open-explorer-process");
            IntPtr token;
            try
            {
                if (!NativeMethods.OpenProcessToken(handle, NativeMethods.TokenQuery | NativeMethods.TokenDuplicate | NativeMethods.TokenImpersonate, out token))
                    throw new InvalidOperationException("open-explorer-token");
            }
            finally { NativeMethods.CloseHandle(handle); }
            try { return FromToken(token, true); }
            finally { NativeMethods.CloseHandle(token); }
        }

        private static TokenObservation FromToken(IntPtr token, bool duplicate)
        {
            TokenObservation result = new TokenObservation();
            result.RawSid = NativeMethods.TokenSid(token);
            result.SessionId = NativeMethods.TokenSessionId(token);
            result.Integrity = NativeMethods.TokenIntegrity(token);
            result.ElevationType = NativeMethods.TokenElevation(token);
            result.IsAdministrator = NativeMethods.TokenIsAdministrator(token);
            result.Privileges = NativeMethods.TokenPrivileges(token);
            if (duplicate)
            {
                IntPtr duplicated;
                if (!NativeMethods.DuplicateTokenEx(token, NativeMethods.TokenQuery | NativeMethods.TokenImpersonate,
                    IntPtr.Zero, 2, 2, out duplicated))
                    throw new InvalidOperationException("duplicate-explorer-token");
                result.duplicatedImpersonationToken = new SafeKernelHandle(duplicated);
            }
            return result;
        }

        public void DisposeImpersonationToken()
        {
            if (duplicatedImpersonationToken != null)
            {
                duplicatedImpersonationToken.Dispose();
                duplicatedImpersonationToken = null;
            }
        }

        public SortedDictionary<string, object> ToJson()
        {
            return JsonObjects.Object(
                "account_sid_sha256", Hashing.StringSha256(RawSid),
                "elevation_type", ElevationType,
                "integrity", Integrity,
                "is_administrator", IsAdministrator,
                "privileges", Privileges,
                "session_id", SessionId);
        }

        public bool SecurityEquivalent(TokenObservation other)
        {
            return other != null && RawSid == other.RawSid && SessionId == other.SessionId &&
                Integrity == other.Integrity && ElevationType == other.ElevationType &&
                IsAdministrator == other.IsAdministrator &&
                CanonicalJson.Serialize(Privileges) == CanonicalJson.Serialize(other.Privileges);
        }
    }

    internal sealed class RegistryObservation
    {
        public int CurrentAccessResult;
        public int ExplorerAccessResult;
        public bool ImpersonationRestored;
        public long LastWriteBefore;
        public long LastWriteAfter;
        public bool LocationMatchesInstalled;
        public string LocationSha256;
        public int LocationUtf16Bytes;
        public string ValueKind;
        public string OwnerSid;
        public string GroupSid;
        public List<object> Aces;

        public SortedDictionary<string, object> ToJson(string keyId, int exactMask)
        {
            return JsonObjects.Object(
                "acl", JsonObjects.Object("aces", Aces, "group_sid", GroupSid, "owner_sid", OwnerSid),
                "exact_access", JsonObjects.Object(
                    "desired_access", (long)exactMask,
                    "explorer_token_win32_result", ExplorerAccessResult,
                    "probe_token_win32_result", CurrentAccessResult),
                "key_id", keyId,
                "last_write_unchanged", LastWriteBefore == LastWriteAfter,
                "location", JsonObjects.Object(
                    "equals_configured_install_root", LocationMatchesInstalled,
                    "sha256_utf16le", LocationSha256,
                    "utf16le_bytes", LocationUtf16Bytes,
                    "value_kind", ValueKind),
                "view", "32-bit");
        }
    }

    internal sealed class CleanObservation
    {
        public FileIdentity Manifest;
        public bool ManifestMatches;
        public CleanCaptureObservation Before;
        public CleanCaptureObservation After;
        public bool BothMatch;
        public bool Unchanged;

        public SortedDictionary<string, object> ToJson()
        {
            return JsonObjects.Object(
                "after", After.ToJson(),
                "before", Before.ToJson(),
                "manifest", JsonObjects.Object("expected_match", ManifestMatches, "identity", Manifest.ToJson()),
                "unchanged", Unchanged);
        }
    }

    internal sealed class CleanCaptureObservation
    {
        public TreeManifest Tree;
        public bool TreeMatches;
        public FileIdentity Executable;
        public bool ExecutableMatches;
        public int MissingCount;
        public int ExtraCount;
        public int MismatchCount;
        public int DirectoryMissingCount;
        public int DirectoryExtraCount;
        public int WritableOpenCount;

        public SortedDictionary<string, object> ToJson()
        {
            return JsonObjects.Object(
                "executable", JsonObjects.Object("expected_match", ExecutableMatches, "identity", Executable.ToJson()),
                "directory_extra_count", DirectoryExtraCount,
                "directory_missing_count", DirectoryMissingCount,
                "extra_count", ExtraCount,
                "mismatch_count", MismatchCount,
                "missing_count", MissingCount,
                "tree", Tree.ToJson(),
                "tree_expected_match", TreeMatches,
                "writable_open_count", WritableOpenCount);
        }
    }

    internal sealed class IsoObservation
    {
        public FileIdentity Iso;
        public bool IsoMatches;
        public uint DriveType;
        public string VolumeLabelSha256;
        public bool VolumeLabelMatches;
        public FileIdentity OpticalExecutable;
        public bool OpticalMatches;

        public SortedDictionary<string, object> ToJson()
        {
            return JsonObjects.Object(
                "file", JsonObjects.Object("expected_match", IsoMatches, "identity", Iso.ToJson()),
                "optical_media", JsonObjects.Object(
                    "drive_type", (long)DriveType,
                    "expected_match", OpticalMatches,
                    "executable", OpticalExecutable.ToJson(),
                    "volume_label_matches", VolumeLabelMatches,
                    "volume_label_sha256", VolumeLabelSha256));
        }
    }

    internal sealed class FileIdentity
    {
        public long Bytes;
        public string Sha256;

        public static FileIdentity Read(string path)
        {
            using (VerifiedPath opened = PathSafety.OpenVerified(path, false, null, true))
                return FileSnapshot.Hash(opened, null).Identity;
        }

        public bool Same(FileIdentity other) { return Bytes == other.Bytes && Sha256 == other.Sha256; }
        public SortedDictionary<string, object> ToJson() { return JsonObjects.Object("byte_count", Bytes, "sha256", Sha256); }
    }

    internal sealed class FileSnapshot
    {
        public byte[] Bytes;
        public FileIdentity Identity;

        public static FileSnapshot Read(string path, int maximumBytes)
        {
            using (VerifiedPath opened = PathSafety.OpenVerified(path, false, null, true))
                return Hash(opened, maximumBytes);
        }

        internal static FileSnapshot Hash(VerifiedPath opened, int? maximumBytes)
        {
            NativeFileIdentity before = NativeMethods.GetFileIdentity(opened.Handle);
            if (before.IsDirectory || before.IsReparsePoint) throw new InvalidDataException("file-type-invalid");
            if (maximumBytes.HasValue && (before.Bytes < 0 || before.Bytes > maximumBytes.Value))
                throw new InvalidDataException("bounded-input-size");
            byte[] snapshot = maximumBytes.HasValue ? new byte[(int)before.Bytes] : null;
            string hash;
            long observedBytes = 0;
            NativeFileIdentity after;
            using (FileStream input = new FileStream(opened.Handle, FileAccess.Read, 65536, false))
            using (SHA256 sha = SHA256.Create())
            {
                byte[] buffer = new byte[65536];
                int offset = 0;
                int read;
                while ((read = input.Read(buffer, 0, buffer.Length)) != 0)
                {
                    observedBytes += read;
                    if (maximumBytes.HasValue)
                    {
                        if (observedBytes > maximumBytes.Value || offset + read > snapshot.Length)
                            throw new InvalidDataException("bounded-input-growth");
                        Buffer.BlockCopy(buffer, 0, snapshot, offset, read);
                        offset += read;
                    }
                    sha.TransformBlock(buffer, 0, read, null, 0);
                }
                sha.TransformFinalBlock(new byte[0], 0, 0);
                hash = Hashing.Hex(sha.Hash);
                if (maximumBytes.HasValue && offset != snapshot.Length)
                    throw new IOException("file-short-read");
                after = NativeMethods.GetFileIdentity(opened.Handle);
            }
            if (!before.Same(after) || observedBytes != before.Bytes) throw new IOException("file-changed-during-read");
            return new FileSnapshot
            {
                Bytes = snapshot,
                Identity = new FileIdentity { Bytes = observedBytes, Sha256 = hash }
            };
        }
    }

    internal sealed class VerifiedPath : IDisposable
    {
        public SafeFileHandle Handle;
        public NativeFileIdentity Identity;
        public string FinalPath;

        public void Dispose()
        {
            if (Handle != null) Handle.Dispose();
        }
    }

    internal sealed class NativeFileIdentity
    {
        public uint VolumeSerial;
        public ulong FileIndex;
        public long Bytes;
        public long LastWrite;
        public uint Attributes;
        public uint NumberOfLinks;
        public bool IsDirectory { get { return (Attributes & (uint)FileAttributes.Directory) != 0; } }
        public bool IsReparsePoint { get { return (Attributes & (uint)FileAttributes.ReparsePoint) != 0; } }
        public string ObjectId { get { return VolumeSerial.ToString("x8", CultureInfo.InvariantCulture) + ":" + FileIndex.ToString("x16", CultureInfo.InvariantCulture); } }

        public bool Same(NativeFileIdentity other)
        {
            return other != null && VolumeSerial == other.VolumeSerial && FileIndex == other.FileIndex && Bytes == other.Bytes &&
                LastWrite == other.LastWrite && Attributes == other.Attributes && NumberOfLinks == other.NumberOfLinks;
        }
    }

    internal static class PathSafety
    {
        public static string PreserveRoot(string path)
        {
            string full = Path.GetFullPath(path);
            string root = Path.GetPathRoot(full);
            if (String.Equals(full, root, StringComparison.OrdinalIgnoreCase)) return root;
            return full.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        }

        public static VerifiedPath OpenVerified(string path, bool directory, string containmentRoot, bool requirePlain)
        {
            return OpenVerified(path, directory, containmentRoot, requirePlain, !directory);
        }

        public static VerifiedPath OpenVerified(string path, bool directory, string containmentRoot, bool requirePlain, bool readContents)
        {
            string expected = PreserveRoot(path);
            VerifyParentChain(expected);
            SafeFileHandle handle = NativeMethods.OpenPathNoFollow(expected, directory, readContents);
            try
            {
                NativeFileIdentity identity = NativeMethods.GetFileIdentity(handle);
                if (identity.IsDirectory != directory) throw new InvalidDataException("path-type-mismatch");
                if (requirePlain && identity.IsReparsePoint) throw new InvalidDataException("reparse-path");
                string finalPath = PreserveRoot(NativeMethods.GetFinalPath(handle));
                if (!String.Equals(finalPath, expected, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("path-alias");
                if (containmentRoot != null && !IsContained(finalPath, containmentRoot))
                    throw new InvalidDataException("path-escaped-root");
                return new VerifiedPath { Handle = handle, Identity = identity, FinalPath = finalPath };
            }
            catch
            {
                handle.Dispose();
                throw;
            }
        }

        public static bool AreDistinctExistingObjects(IEnumerable<string> paths)
        {
            HashSet<string> objects = new HashSet<string>(StringComparer.Ordinal);
            foreach (string path in paths)
            {
                uint attributes;
                int error;
                if (!NativeMethods.TryGetPathAttributes(path, out attributes, out error))
                {
                    if (error == 2 || error == 3) continue;
                    throw new IOException("locator-attributes-" + error.ToString(CultureInfo.InvariantCulture));
                }
                bool directory = (attributes & (uint)FileAttributes.Directory) != 0;
                using (VerifiedPath opened = OpenVerified(path, directory, null, true))
                    if (!objects.Add(opened.Identity.ObjectId)) return false;
            }
            return true;
        }

        private static bool IsContained(string path, string root)
        {
            string normalizedRoot = PreserveRoot(root);
            if (String.Equals(path, normalizedRoot, StringComparison.OrdinalIgnoreCase)) return true;
            string prefix = normalizedRoot.EndsWith("\\", StringComparison.Ordinal) ? normalizedRoot : normalizedRoot + "\\";
            return path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase);
        }

        private static void VerifyParentChain(string path)
        {
            string root = Path.GetPathRoot(path);
            if (String.IsNullOrEmpty(root)) throw new InvalidDataException("path-root-missing");
            VerifyDirectoryComponent(root);
            string parent = Path.GetDirectoryName(path);
            if (String.IsNullOrEmpty(parent)) return;
            string relative = parent.Substring(root.Length).Trim(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            string current = root;
            if (relative.Length == 0) return;
            foreach (string component in relative.Split(Path.DirectorySeparatorChar))
            {
                current = Path.Combine(current, component);
                VerifyDirectoryComponent(current);
            }
        }

        private static void VerifyDirectoryComponent(string path)
        {
            SafeFileHandle handle = NativeMethods.OpenPathNoFollow(path, true, false);
            try
            {
                NativeFileIdentity identity = NativeMethods.GetFileIdentity(handle);
                if (!identity.IsDirectory || identity.IsReparsePoint) throw new InvalidDataException("unsafe-parent-component");
                if (!String.Equals(PreserveRoot(NativeMethods.GetFinalPath(handle)), PreserveRoot(path), StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("parent-path-alias");
            }
            finally { handle.Dispose(); }
        }
    }

    internal sealed class ManifestRow
    {
        public long Bytes;
        public string Sha256;

        public static Dictionary<string, ManifestRow> Parse(byte[] snapshot)
        {
            Dictionary<string, ManifestRow> rows = new Dictionary<string, ManifestRow>(StringComparer.OrdinalIgnoreCase);
            using (MemoryStream input = new MemoryStream(snapshot, false))
            using (StreamReader reader = new StreamReader(input, new UTF8Encoding(false, true), false))
            {
                string line;
                while ((line = reader.ReadLine()) != null)
                {
                    if (line.Length == 0 || line[0] == '#') continue;
                    string[] fields = line.Split('\t');
                    long bytes;
                    if (fields.Length != 3 || !Regex.IsMatch(fields[0], "^[0-9a-f]{64}$") ||
                        !Int64.TryParse(fields[1], NumberStyles.None, CultureInfo.InvariantCulture, out bytes) || bytes < 0)
                        throw new InvalidDataException("invalid-clean-manifest");
                    string relative = TreeManifest.NormalizeRelative(fields[2]);
                    if (!rows.TryAddCompat(relative, new ManifestRow { Sha256 = fields[0], Bytes = bytes }))
                        throw new InvalidDataException("duplicate-clean-manifest-path");
                }
            }
            return rows;
        }

        public static HashSet<string> ExpectedDirectories(IEnumerable<string> paths)
        {
            HashSet<string> result = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "." };
            foreach (string path in paths)
            {
                int separator = path.LastIndexOf('/');
                while (separator > 0)
                {
                    result.Add(path.Substring(0, separator));
                    separator = path.LastIndexOf('/', separator - 1);
                }
            }
            return result;
        }
    }

    internal static class DictionaryCompat
    {
        public static bool TryAddCompat<T>(this IDictionary<string, T> dictionary, string key, T value)
        {
            if (dictionary.ContainsKey(key)) return false;
            dictionary.Add(key, value);
            return true;
        }
    }

    internal sealed class TreeRow
    {
        public string Relative;
        public long Bytes;
        public string Sha256;
    }

    internal sealed class TreeManifest
    {
        public bool Present;
        public long FileCount;
        public long DirectoryCount;
        public long TotalBytes;
        public string TreeSha256;
        public int CaseCollisionCount;
        public int ReparseCount;
        public int UnstableCount;
        public int ObjectAliasCount;
        public int HardlinkCount;
        public int WritableOpenCount;
        public Dictionary<string, TreeRow> Rows;
        public HashSet<string> DirectoryPaths;
        public string RootObjectIdSha256;

        public static TreeManifest CaptureOptional(string root)
        {
            uint attributes;
            int error;
            if (!NativeMethods.TryGetPathAttributes(root, out attributes, out error))
            {
                if (error == 2 || error == 3) return Missing();
                throw new IOException("optional-tree-attributes-" + error.ToString(CultureInfo.InvariantCulture));
            }
            if ((attributes & (uint)FileAttributes.Directory) == 0) throw new InvalidDataException("tree-root-not-directory");
            return Capture(root, false);
        }

        private static TreeManifest Missing()
        {
            return new TreeManifest
            {
                Present = false,
                RootObjectIdSha256 = Hashing.StringSha256("absent"),
                TreeSha256 = Hashing.BytesSha256(new byte[0]),
                Rows = new Dictionary<string, TreeRow>(StringComparer.OrdinalIgnoreCase),
                DirectoryPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            };
        }

        public static TreeManifest Capture(string root, bool testWriteOpen)
        {
            string canonicalRoot = PathSafety.PreserveRoot(root);
            VerifiedPath openedRoot = PathSafety.OpenVerified(canonicalRoot, true, null, false);
            if (openedRoot.Identity.IsReparsePoint)
            {
                openedRoot.Dispose();
                return UnsafeRootManifest(openedRoot.Identity.ObjectId);
            }
            List<VerifiedPath> heldDirectories = new List<VerifiedPath> { openedRoot };
            try
            {
                TreeManifest result = new TreeManifest
                {
                    Present = true,
                    DirectoryCount = 1,
                    RootObjectIdSha256 = Hashing.StringSha256(openedRoot.Identity.ObjectId),
                    Rows = new Dictionary<string, TreeRow>(StringComparer.OrdinalIgnoreCase),
                    DirectoryPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "." }
                };
                HashSet<string> objectIds = new HashSet<string>(StringComparer.Ordinal) { openedRoot.Identity.ObjectId };
                if (testWriteOpen && NativeMethods.CanOpenForWrite(canonicalRoot, true)) result.WritableOpenCount++;
                HashSet<string> exact = new HashSet<string>(StringComparer.Ordinal);
                HashSet<string> foldedPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                List<string> digestRows = new List<string> { "D\t.\n" };
                Stack<VerifiedPath> pending = new Stack<VerifiedPath>();
                pending.Push(openedRoot);
                while (pending.Count != 0)
                {
                    VerifiedPath current = pending.Pop();
                    string[] children = Directory.GetDirectories(current.FinalPath, "*", SearchOption.TopDirectoryOnly);
                    foreach (string child in children)
                    {
                        string relative = Relative(canonicalRoot, child);
                        RecordName(relative, exact, foldedPaths, result);
                        result.DirectoryCount++;
                        result.DirectoryPaths.Add(relative);
                        VerifiedPath opened = PathSafety.OpenVerified(child, true, canonicalRoot, false);
                        if (!objectIds.Add(opened.Identity.ObjectId)) result.ObjectAliasCount++;
                        if (opened.Identity.IsReparsePoint)
                        {
                            result.ReparseCount++;
                            digestRows.Add("R\t" + relative + "\n");
                            opened.Dispose();
                            continue;
                        }
                        heldDirectories.Add(opened);
                        pending.Push(opened);
                        digestRows.Add("D\t" + relative + "\n");
                        if (testWriteOpen && NativeMethods.CanOpenForWrite(child, true)) result.WritableOpenCount++;
                    }
                    string[] files = Directory.GetFiles(current.FinalPath, "*", SearchOption.TopDirectoryOnly);
                    foreach (string file in files)
                    {
                        string relative = Relative(canonicalRoot, file);
                        RecordName(relative, exact, foldedPaths, result);
                        using (VerifiedPath metadata = PathSafety.OpenVerified(file, false, canonicalRoot, false, false))
                        {
                            if (!objectIds.Add(metadata.Identity.ObjectId)) result.ObjectAliasCount++;
                            if (metadata.Identity.IsReparsePoint)
                            {
                                result.ReparseCount++;
                                digestRows.Add("R\t" + relative + "\n");
                                continue;
                            }
                            if (metadata.Identity.NumberOfLinks > 1) result.HardlinkCount++;
                            if (testWriteOpen && NativeMethods.CanOpenForWrite(file, false)) result.WritableOpenCount++;
                            using (VerifiedPath opened = PathSafety.OpenVerified(file, false, canonicalRoot, true))
                            {
                                if (!metadata.Identity.Same(opened.Identity))
                                    throw new IOException("file-mutated-before-read");
                                FileSnapshot snapshot = FileSnapshot.Hash(opened, null);
                                TreeRow row = new TreeRow { Relative = relative, Bytes = snapshot.Identity.Bytes, Sha256 = snapshot.Identity.Sha256 };
                                if (!result.Rows.ContainsKey(relative)) result.Rows.Add(relative, row);
                                result.FileCount++;
                                result.TotalBytes += row.Bytes;
                                digestRows.Add("F\t" + relative + "\t" + row.Bytes.ToString(CultureInfo.InvariantCulture) + "\t" + row.Sha256 + "\n");
                            }
                        }
                    }
                }
                foreach (VerifiedPath directory in heldDirectories)
                {
                    NativeFileIdentity after = NativeMethods.GetFileIdentity(directory.Handle);
                    if (!directory.Identity.Same(after) ||
                        !String.Equals(directory.FinalPath, PathSafety.PreserveRoot(NativeMethods.GetFinalPath(directory.Handle)), StringComparison.OrdinalIgnoreCase))
                        result.UnstableCount++;
                }
                digestRows.Sort(delegate(string left, string right)
                {
                    int folded = StringComparer.OrdinalIgnoreCase.Compare(left, right);
                    return folded != 0 ? folded : StringComparer.Ordinal.Compare(left, right);
                });
                using (MemoryStream rowsBytes = new MemoryStream())
                {
                    foreach (string row in digestRows)
                    {
                        byte[] bytes = Encoding.UTF8.GetBytes(row);
                        rowsBytes.Write(bytes, 0, bytes.Length);
                    }
                    result.TreeSha256 = Hashing.BytesSha256(rowsBytes.ToArray());
                }
                return result;
            }
            finally
            {
                foreach (VerifiedPath directory in heldDirectories) directory.Dispose();
            }
        }

        private static TreeManifest UnsafeRootManifest(string rootObjectId)
        {
            return new TreeManifest
            {
                Present = true,
                DirectoryCount = 1,
                ReparseCount = 1,
                RootObjectIdSha256 = Hashing.StringSha256(rootObjectId),
                TreeSha256 = Hashing.BytesSha256(Encoding.UTF8.GetBytes("R\t.\n")),
                Rows = new Dictionary<string, TreeRow>(StringComparer.OrdinalIgnoreCase),
                DirectoryPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "." }
            };
        }

        private static string Relative(string root, string path)
        {
            string prefix = root.EndsWith("\\", StringComparison.Ordinal) ? root : root + "\\";
            if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("tree-path-escaped");
            return NormalizeRelative(path.Substring(prefix.Length));
        }

        internal static void RecordName(string relative, HashSet<string> exact, HashSet<string> folded, TreeManifest result)
        {
            if (!exact.Add(relative) || !folded.Add(relative)) result.CaseCollisionCount++;
        }

        public static string NormalizeRelative(string relative)
        {
            string value = relative.Replace('\\', '/').Normalize(NormalizationForm.FormC);
            if (value.Length == 0 || value.StartsWith("/", StringComparison.Ordinal) || value.Contains("\0") || value.Contains("\r") || value.Contains("\n"))
                throw new InvalidDataException("invalid-relative-path");
            string[] parts = value.Split('/');
            foreach (string part in parts)
                if (part.Length == 0 || part == "." || part == "..") throw new InvalidDataException("invalid-relative-path");
            return value;
        }

        public bool SameIdentity(TreeManifest other)
        {
            return Present == other.Present && FileCount == other.FileCount && DirectoryCount == other.DirectoryCount &&
                TotalBytes == other.TotalBytes && TreeSha256 == other.TreeSha256 && CaseCollisionCount == other.CaseCollisionCount &&
                ReparseCount == other.ReparseCount && ObjectAliasCount == other.ObjectAliasCount && HardlinkCount == other.HardlinkCount &&
                RootObjectIdSha256 == other.RootObjectIdSha256 &&
                UnstableCount == 0 && other.UnstableCount == 0;
        }

        public bool IsPlain(bool requirePresent)
        {
            return (!requirePresent || Present) && ReparseCount == 0 && CaseCollisionCount == 0 && UnstableCount == 0 &&
                ObjectAliasCount == 0 && HardlinkCount == 0;
        }

        public SortedDictionary<string, object> ToJson()
        {
            return JsonObjects.Object(
                "case_collision_count", CaseCollisionCount,
                "directory_count", DirectoryCount,
                "file_count", FileCount,
                "hardlink_count", HardlinkCount,
                "object_alias_count", ObjectAliasCount,
                "present", Present,
                "reparse_count", ReparseCount,
                "root_object_id_sha256", RootObjectIdSha256,
                "total_bytes", TotalBytes,
                "tree_sha256", TreeSha256,
                "unstable_count", UnstableCount);
        }
    }

    internal sealed class Redactor
    {
        private readonly List<string> forbidden = new List<string>();

        public void Add(string value)
        {
            if (String.IsNullOrEmpty(value) || value.Length < 3) return;
            AddOne(value);
            AddOne(value.Replace('\\', '/'));
            AddOne(value.Replace('/', '\\'));
        }

        private void AddOne(string value)
        {
            foreach (string existing in forbidden)
                if (String.Equals(existing, value, StringComparison.OrdinalIgnoreCase)) return;
            forbidden.Add(value);
        }

        public bool IsSafe(object value)
        {
            string text = value as string;
            if (text != null) return !ContainsForbidden(text);
            IDictionary<string, object> dictionary = value as IDictionary<string, object>;
            if (dictionary != null)
            {
                foreach (KeyValuePair<string, object> pair in dictionary)
                    if (ContainsForbidden(pair.Key) || !IsSafe(pair.Value)) return false;
                return true;
            }
            IEnumerable sequence = value as IEnumerable;
            if (sequence != null)
            {
                foreach (object item in sequence)
                    if (!IsSafe(item)) return false;
            }
            return true;
        }

        public bool IsSerializedSafe(string value)
        {
            if (ContainsForbidden(value)) return false;
            foreach (string item in forbidden)
            {
                string escaped = item.Replace("\\", "\\\\").Replace("\"", "\\\"");
                if (value.IndexOf(escaped, StringComparison.OrdinalIgnoreCase) >= 0) return false;
            }
            return true;
        }

        private bool ContainsForbidden(string value)
        {
            foreach (string item in forbidden)
                if (value.IndexOf(item, StringComparison.OrdinalIgnoreCase) >= 0) return true;
            return false;
        }
    }

    internal static class Hashing
    {
        public static string StringSha256(string value) { return BytesSha256(Encoding.Unicode.GetBytes(value)); }
        public static string BytesSha256(byte[] bytes) { using (SHA256 sha = SHA256.Create()) return Hex(sha.ComputeHash(bytes)); }
        public static string Hex(byte[] bytes)
        {
            StringBuilder output = new StringBuilder(bytes.Length * 2);
            foreach (byte value in bytes) output.Append(value.ToString("x2", CultureInfo.InvariantCulture));
            return output.ToString();
        }
    }

    internal sealed class SafeKernelHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public SafeKernelHandle() : base(true) { }
        public SafeKernelHandle(IntPtr handle) : base(true) { SetHandle(handle); }
        protected override bool ReleaseHandle() { return NativeMethods.CloseHandle(handle); }
    }

    internal static class NativeMethods
    {
        public const int ErrorAccessDenied = 5;
        private const int ErrorNoToken = 1008;
        public const uint DriveCdrom = 5;
        public const uint TokenAssignPrimary = 0x0001;
        public const uint TokenDuplicate = 0x0002;
        public const uint TokenImpersonate = 0x0004;
        public const uint TokenQuery = 0x0008;
        public const uint ProcessQueryLimitedInformation = 0x1000;
        private const uint GenericRead = 0x80000000;
        private const uint GenericWrite = 0x40000000;
        private const uint FileReadAttributes = 0x00000080;
        private const uint FileShareRead = 0x1;
        private const uint FileShareWrite = 0x2;
        private const uint FileShareDelete = 0x4;
        private const uint OpenExisting = 3;
        private const uint FileFlagBackupSemantics = 0x02000000;
        private const uint FileFlagOpenReparsePoint = 0x00200000;
        private static readonly IntPtr InvalidHandleValue = new IntPtr(-1);
        private static readonly IntPtr HkeyLocalMachine = new IntPtr(unchecked((int)0x80000002));

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        public struct RTL_OSVERSIONINFOEX
        {
            public int dwOSVersionInfoSize;
            public uint dwMajorVersion;
            public uint dwMinorVersion;
            public uint dwBuildNumber;
            public uint dwPlatformId;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string szCSDVersion;
            public ushort wServicePackMajor;
            public ushort wServicePackMinor;
            public ushort wSuiteMask;
            public byte wProductType;
            public byte wReserved;
        }

        [StructLayout(LayoutKind.Sequential)] private struct LUID { public uint LowPart; public int HighPart; }
        [StructLayout(LayoutKind.Sequential)] private struct LUID_AND_ATTRIBUTES { public LUID Luid; public uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] private struct SID_AND_ATTRIBUTES { public IntPtr Sid; public uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] private struct FILETIME { public uint Low; public uint High; }
        [StructLayout(LayoutKind.Sequential)]
        private struct BY_HANDLE_FILE_INFORMATION
        {
            public uint FileAttributes;
            public FILETIME CreationTime;
            public FILETIME LastAccessTime;
            public FILETIME LastWriteTime;
            public uint VolumeSerialNumber;
            public uint FileSizeHigh;
            public uint FileSizeLow;
            public uint NumberOfLinks;
            public uint FileIndexHigh;
            public uint FileIndexLow;
        }

        [DllImport("ntdll.dll", CharSet = CharSet.Unicode)] public static extern int RtlGetVersion(ref RTL_OSVERSIONINFOEX version);
        [DllImport("kernel32.dll")] public static extern IntPtr GetCurrentProcess();
        [DllImport("kernel32.dll")] private static extern IntPtr GetCurrentThread();
        [DllImport("kernel32.dll", SetLastError = true)] public static extern IntPtr OpenProcess(uint access, bool inherit, int processId);
        [DllImport("kernel32.dll", SetLastError = true)] public static extern bool CloseHandle(IntPtr handle);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool OpenThreadToken(IntPtr thread, uint access, bool openAsSelf, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool DuplicateTokenEx(IntPtr existing, uint desiredAccess, IntPtr attributes, int level, int type, out IntPtr duplicated);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool GetTokenInformation(IntPtr token, int infoClass, IntPtr buffer, int length, out int returnLength);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool CheckTokenMembership(IntPtr token, IntPtr sid, out bool isMember);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool AllocateAndInitializeSid(IntPtr authority, byte count, uint a0, uint a1, uint a2, uint a3, uint a4, uint a5, uint a6, uint a7, out IntPtr sid);
        [DllImport("advapi32.dll")] private static extern IntPtr FreeSid(IntPtr sid);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool ConvertSidToStringSidW(IntPtr sid, out IntPtr text);
        [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr memory);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool LookupPrivilegeNameW(string system, ref LUID luid, StringBuilder name, ref int length);
        [DllImport("advapi32.dll", CharSet = CharSet.Ansi, ExactSpelling = true)] private static extern int RegOpenKeyExA(IntPtr key, string subkey, int options, int desired, out IntPtr result);
        [DllImport("advapi32.dll")] private static extern int RegCloseKey(IntPtr key);
        [DllImport("advapi32.dll", CharSet = CharSet.Ansi, ExactSpelling = true)] private static extern int RegQueryInfoKeyA(IntPtr key, IntPtr className, IntPtr classLength, IntPtr reserved, IntPtr subkeys, IntPtr maxSubkey, IntPtr maxClass, IntPtr values, IntPtr maxValueName, IntPtr maxValueLength, IntPtr securityDescriptor, out long lastWrite);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr CreateFileW(string name, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern uint GetFileAttributesW(string name);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder path, uint length, uint flags);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetFileInformationByHandle(SafeFileHandle handle, out BY_HANDLE_FILE_INFORMATION information);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr LoadLibraryW(string fileName);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr GetProcAddress(IntPtr module, string name);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool FreeLibrary(IntPtr module);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] public static extern uint GetDriveTypeW(string root);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool GetVolumeInformationW(string root, StringBuilder label, int labelSize, out uint serial, out uint maxComponent, out uint flags, StringBuilder fileSystem, int fileSystemSize);
        [DllImport("kernel32.dll")] public static extern uint WTSGetActiveConsoleSessionId();
        [DllImport("user32.dll", SetLastError = true)] private static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint access);
        [DllImport("user32.dll", SetLastError = true)] private static extern bool CloseDesktop(IntPtr desktop);
        [DllImport("user32.dll")] private static extern IntPtr GetProcessWindowStation();
        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool GetUserObjectInformationW(IntPtr handle, int index, StringBuilder info, int length, out int needed);

        public static int ExactRegistryOpen(string subkey, int desiredAccess)
        {
            IntPtr handle;
            int result = RegOpenKeyExA(HkeyLocalMachine, subkey, 0, desiredAccess, out handle);
            if (result == 0) RegCloseKey(handle);
            return result;
        }

        public static bool TryOpenCurrentThreadToken(out IntPtr token)
        {
            if (OpenThreadToken(GetCurrentThread(), TokenQuery | TokenDuplicate, true, out token)) return true;
            int error = Marshal.GetLastWin32Error();
            if (error == ErrorNoToken)
            {
                token = IntPtr.Zero;
                return false;
            }
            throw new InvalidOperationException("open-current-thread-token-" + error.ToString(CultureInfo.InvariantCulture));
        }

        public static SafeKernelHandle DuplicateCurrentTokenForImpersonation()
        {
            IntPtr token;
            if (!OpenProcessToken(GetCurrentProcess(), TokenQuery | TokenDuplicate | TokenImpersonate, out token))
                throw new InvalidOperationException("open-current-token-for-duplicate");
            try
            {
                IntPtr duplicated;
                if (!DuplicateTokenEx(token, TokenQuery | TokenImpersonate, IntPtr.Zero, 2, 2, out duplicated))
                    throw new InvalidOperationException("duplicate-current-token");
                return new SafeKernelHandle(duplicated);
            }
            finally { CloseHandle(token); }
        }

        public static long RegistryLastWrite(string subkey)
        {
            IntPtr handle;
            int result = RegOpenKeyExA(HkeyLocalMachine, subkey, 0, 0x20019, out handle);
            if (result != 0) throw new InvalidOperationException("registry-read-open");
            try
            {
                long lastWrite;
                result = RegQueryInfoKeyA(handle, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero,
                    IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, out lastWrite);
                if (result != 0) throw new InvalidOperationException("registry-query-info");
                return lastWrite;
            }
            finally { RegCloseKey(handle); }
        }

        public static bool CanOpenForWrite(string path, bool directory)
        {
            IntPtr handle = CreateFileW(path, GenericWrite, FileShareRead | FileShareWrite | FileShareDelete,
                IntPtr.Zero, OpenExisting, directory ? FileFlagBackupSemantics : 0, IntPtr.Zero);
            if (handle == InvalidHandleValue) return false;
            CloseHandle(handle);
            return true;
        }

        public static SafeFileHandle OpenPathNoFollow(string path, bool directory, bool readContents)
        {
            uint flags = FileFlagOpenReparsePoint | (directory ? FileFlagBackupSemantics : 0);
            IntPtr raw = CreateFileW(path, readContents ? GenericRead : FileReadAttributes,
                readContents ? FileShareRead : (FileShareRead | FileShareWrite),
                IntPtr.Zero, OpenExisting, flags, IntPtr.Zero);
            if (raw == InvalidHandleValue) throw new IOException("open-path-" + Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture));
            return new SafeFileHandle(raw, true);
        }

        public static bool TryGetPathAttributes(string path, out uint attributes, out int error)
        {
            attributes = GetFileAttributesW(path);
            if (attributes != UInt32.MaxValue)
            {
                error = 0;
                return true;
            }
            error = Marshal.GetLastWin32Error();
            return false;
        }

        public static NativeFileIdentity GetFileIdentity(SafeFileHandle handle)
        {
            BY_HANDLE_FILE_INFORMATION information;
            if (!GetFileInformationByHandle(handle, out information)) throw new IOException("file-information");
            return new NativeFileIdentity
            {
                Attributes = information.FileAttributes,
                Bytes = ((long)information.FileSizeHigh << 32) | information.FileSizeLow,
                FileIndex = ((ulong)information.FileIndexHigh << 32) | information.FileIndexLow,
                LastWrite = ((long)information.LastWriteTime.High << 32) | information.LastWriteTime.Low,
                NumberOfLinks = information.NumberOfLinks,
                VolumeSerial = information.VolumeSerialNumber
            };
        }

        public static string GetFinalPath(SafeFileHandle handle)
        {
            StringBuilder path = new StringBuilder(32768);
            uint length = GetFinalPathNameByHandleW(handle, path, (uint)path.Capacity, 0);
            if (length == 0 || length >= path.Capacity) throw new IOException("final-path");
            string result = path.ToString();
            if (result.StartsWith(@"\\?\UNC\", StringComparison.OrdinalIgnoreCase)) return @"\\" + result.Substring(8);
            if (result.StartsWith(@"\\?\", StringComparison.OrdinalIgnoreCase)) return result.Substring(4);
            return result;
        }

        public static bool ExportsPresent(string library, IEnumerable<string> exports)
        {
            IntPtr module = LoadLibraryW(library);
            if (module == IntPtr.Zero) return false;
            try
            {
                foreach (string export in exports)
                    if (GetProcAddress(module, export) == IntPtr.Zero) return false;
                return true;
            }
            finally { FreeLibrary(module); }
        }

        public static string GetVolumeLabel(string root)
        {
            StringBuilder label = new StringBuilder(261);
            StringBuilder fileSystem = new StringBuilder(261);
            uint serial, maxComponent, flags;
            if (!GetVolumeInformationW(root, label, label.Capacity, out serial, out maxComponent, out flags, fileSystem, fileSystem.Capacity))
                throw new InvalidOperationException("volume-information");
            return label.ToString();
        }

        private static byte[] TokenBuffer(IntPtr token, int infoClass)
        {
            int required;
            GetTokenInformation(token, infoClass, IntPtr.Zero, 0, out required);
            if (required <= 0 || required > 1024 * 1024) throw new InvalidOperationException("token-info-size");
            IntPtr buffer = Marshal.AllocHGlobal(required);
            try
            {
                if (!GetTokenInformation(token, infoClass, buffer, required, out required)) throw new InvalidOperationException("token-info");
                byte[] result = new byte[required];
                Marshal.Copy(buffer, result, 0, required);
                return result;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static IntPtr TokenPointer(IntPtr token, int infoClass, out IntPtr allocation)
        {
            int required;
            GetTokenInformation(token, infoClass, IntPtr.Zero, 0, out required);
            allocation = Marshal.AllocHGlobal(required);
            if (!GetTokenInformation(token, infoClass, allocation, required, out required))
            {
                Marshal.FreeHGlobal(allocation);
                throw new InvalidOperationException("token-info");
            }
            return allocation;
        }

        public static string TokenSid(IntPtr token)
        {
            IntPtr allocation;
            IntPtr buffer = TokenPointer(token, 1, out allocation);
            try
            {
                SID_AND_ATTRIBUTES user = (SID_AND_ATTRIBUTES)Marshal.PtrToStructure(buffer, typeof(SID_AND_ATTRIBUTES));
                return SidString(user.Sid);
            }
            finally { Marshal.FreeHGlobal(allocation); }
        }

        public static int TokenSessionId(IntPtr token)
        {
            byte[] data = TokenBuffer(token, 12);
            if (data.Length < 4) throw new InvalidOperationException("token-session-size");
            return BitConverter.ToInt32(data, 0);
        }

        public static string TokenIntegrity(IntPtr token)
        {
            IntPtr allocation;
            IntPtr buffer = TokenPointer(token, 25, out allocation);
            try
            {
                SID_AND_ATTRIBUTES label = (SID_AND_ATTRIBUTES)Marshal.PtrToStructure(buffer, typeof(SID_AND_ATTRIBUTES));
                string[] parts = SidString(label.Sid).Split('-');
                int rid = Int32.Parse(parts[parts.Length - 1], CultureInfo.InvariantCulture);
                if (rid >= 0x4000) return "system";
                if (rid >= 0x3000) return "high";
                if (rid >= 0x2000) return "medium";
                if (rid >= 0x1000) return "low";
                return "untrusted";
            }
            finally { Marshal.FreeHGlobal(allocation); }
        }

        public static string TokenElevation(IntPtr token)
        {
            byte[] data = TokenBuffer(token, 18);
            int value = BitConverter.ToInt32(data, 0);
            if (value == 1) return "default";
            if (value == 2) return "full";
            if (value == 3) return "limited";
            return "unknown";
        }

        public static bool TokenIsAdministrator(IntPtr token)
        {
            byte[] ntAuthority = { 0, 0, 0, 0, 0, 5 };
            IntPtr authority = Marshal.AllocHGlobal(ntAuthority.Length);
            Marshal.Copy(ntAuthority, 0, authority, ntAuthority.Length);
            IntPtr sid;
            try
            {
                if (!AllocateAndInitializeSid(authority, 2, 32, 544, 0, 0, 0, 0, 0, 0, out sid))
                    throw new InvalidOperationException("allocate-admin-sid");
            }
            finally { Marshal.FreeHGlobal(authority); }
            IntPtr impersonation;
            if (!DuplicateTokenEx(token, TokenQuery | TokenImpersonate, IntPtr.Zero, 2, 2, out impersonation))
            {
                FreeSid(sid);
                throw new InvalidOperationException("duplicate-membership-token");
            }
            try
            {
                bool member;
                if (!CheckTokenMembership(impersonation, sid, out member)) throw new InvalidOperationException("check-admin-membership");
                return member;
            }
            finally
            {
                CloseHandle(impersonation);
                FreeSid(sid);
            }
        }

        public static List<object> TokenPrivileges(IntPtr token)
        {
            byte[] data = TokenBuffer(token, 3);
            int count = BitConverter.ToInt32(data, 0);
            int size = Marshal.SizeOf(typeof(LUID_AND_ATTRIBUTES));
            List<object> result = new List<object>();
            for (int index = 0; index < count; index++)
            {
                int offset = 4 + index * size;
                IntPtr allocation = Marshal.AllocHGlobal(size);
                try
                {
                    Marshal.Copy(data, offset, allocation, size);
                    LUID_AND_ATTRIBUTES item = (LUID_AND_ATTRIBUTES)Marshal.PtrToStructure(allocation, typeof(LUID_AND_ATTRIBUTES));
                    int length = 0;
                    LookupPrivilegeNameW(null, ref item.Luid, null, ref length);
                    StringBuilder name = new StringBuilder(length + 1);
                    if (!LookupPrivilegeNameW(null, ref item.Luid, name, ref length)) throw new InvalidOperationException("lookup-privilege");
                    result.Add(JsonObjects.Object("attributes", (long)item.Attributes, "name", name.ToString()));
                }
                finally { Marshal.FreeHGlobal(allocation); }
            }
            result.Sort(delegate(object left, object right)
            {
                return StringComparer.Ordinal.Compare((string)((IDictionary<string, object>)left)["name"], (string)((IDictionary<string, object>)right)["name"]);
            });
            return result;
        }

        private static string SidString(IntPtr sid)
        {
            IntPtr text;
            if (!ConvertSidToStringSidW(sid, out text)) throw new InvalidOperationException("sid-to-string");
            try { return Marshal.PtrToStringUni(text); }
            finally { LocalFree(text); }
        }

        public static string GetInputDesktopName()
        {
            IntPtr desktop = OpenInputDesktop(0, false, 0x0001);
            if (desktop == IntPtr.Zero) throw new InvalidOperationException("open-input-desktop");
            try { return UserObjectName(desktop); }
            finally { CloseDesktop(desktop); }
        }

        public static string GetWindowStationName()
        {
            IntPtr station = GetProcessWindowStation();
            if (station == IntPtr.Zero) throw new InvalidOperationException("get-window-station");
            return UserObjectName(station);
        }

        private static string UserObjectName(IntPtr handle)
        {
            int needed;
            GetUserObjectInformationW(handle, 2, null, 0, out needed);
            StringBuilder name = new StringBuilder((needed / 2) + 1);
            if (!GetUserObjectInformationW(handle, 2, name, name.Capacity * 2, out needed))
                throw new InvalidOperationException("user-object-name");
            return name.ToString();
        }
    }
}
