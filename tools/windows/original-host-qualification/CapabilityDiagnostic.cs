using System;
using System.Collections.Generic;

namespace Cm0102.OriginalHostQualification
{
    internal sealed class CapabilityDiagnostic
    {
        private static int failures;

        private static int Main()
        {
            string windows = null;
            string system = null;
            Run("folder-windows", delegate { windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows); });
            Run("folder-system", delegate { system = Environment.GetFolderPath(Environment.SpecialFolder.System); });
            if (windows != null && system != null)
            {
                Dictionary<string, string> tools = null;
                Run("tool-catalog", delegate { tools = CapabilityCatalog.ToolPaths(windows, system); });
                if (tools != null)
                {
                    foreach (KeyValuePair<string, string> tool in tools)
                    {
                        string id = tool.Key;
                        string path = tool.Value;
                        Run("tool-" + id, delegate
                        {
                            if (System.IO.File.Exists(path)) FileIdentity.Read(path);
                        });
                    }
                }
            }
            foreach (string id in CapabilityCatalog.ApiIds)
            {
                string captured = id;
                Run("api-" + captured, delegate { CapabilityCatalog.ApiPresent(captured); });
            }
            Console.WriteLine(failures == 0 ? "PASS" : "FAIL " + failures.ToString());
            return failures == 0 ? 0 : 1;
        }

        private static void Run(string id, Action action)
        {
            try
            {
                action();
                Console.WriteLine("ok " + id);
            }
            catch (Exception exception)
            {
                failures++;
                Console.WriteLine("not ok " + id + " " + Program.StableExceptionCode(exception));
            }
        }
    }
}
