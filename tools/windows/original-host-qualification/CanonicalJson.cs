using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Cm0102.OriginalHostQualification
{
    internal static class CanonicalJson
    {
        public static string Serialize(object value)
        {
            StringBuilder output = new StringBuilder();
            WriteValue(output, value);
            return output.ToString();
        }

        private static void WriteValue(StringBuilder output, object value)
        {
            if (value == null)
            {
                output.Append("null");
                return;
            }

            string text = value as string;
            if (text != null)
            {
                WriteString(output, text);
                return;
            }

            if (value is bool)
            {
                output.Append((bool)value ? "true" : "false");
                return;
            }

            if (value is byte || value is sbyte || value is short || value is ushort ||
                value is int || value is uint || value is long || value is ulong)
            {
                output.Append(Convert.ToString(value, CultureInfo.InvariantCulture));
                return;
            }

            IDictionary<string, object> dictionary = value as IDictionary<string, object>;
            if (dictionary != null)
            {
                WriteDictionary(output, dictionary);
                return;
            }

            IEnumerable sequence = value as IEnumerable;
            if (sequence != null)
            {
                WriteSequence(output, sequence);
                return;
            }

            throw new InvalidOperationException("unsupported-json-type");
        }

        private static void WriteDictionary(StringBuilder output, IDictionary<string, object> value)
        {
            List<string> keys = new List<string>(value.Keys);
            keys.Sort(StringComparer.Ordinal);
            output.Append('{');
            for (int index = 0; index < keys.Count; index++)
            {
                if (index != 0)
                    output.Append(',');
                WriteString(output, keys[index]);
                output.Append(':');
                WriteValue(output, value[keys[index]]);
            }
            output.Append('}');
        }

        private static void WriteSequence(StringBuilder output, IEnumerable value)
        {
            output.Append('[');
            bool first = true;
            foreach (object item in value)
            {
                if (!first)
                    output.Append(',');
                WriteValue(output, item);
                first = false;
            }
            output.Append(']');
        }

        private static void WriteString(StringBuilder output, string value)
        {
            output.Append('"');
            foreach (char character in value)
            {
                switch (character)
                {
                    case '"': output.Append("\\\""); break;
                    case '\\': output.Append("\\\\"); break;
                    case '\b': output.Append("\\b"); break;
                    case '\f': output.Append("\\f"); break;
                    case '\n': output.Append("\\n"); break;
                    case '\r': output.Append("\\r"); break;
                    case '\t': output.Append("\\t"); break;
                    default:
                        if (character < 0x20 || character > 0x7e)
                            output.Append("\\u" + ((int)character).ToString("x4", CultureInfo.InvariantCulture));
                        else
                            output.Append(character);
                        break;
                }
            }
            output.Append('"');
        }
    }

    internal static class JsonObjects
    {
        public static SortedDictionary<string, object> Object(params object[] keyValues)
        {
            if (keyValues.Length % 2 != 0)
                throw new ArgumentException("key-values-must-be-paired");
            SortedDictionary<string, object> result = new SortedDictionary<string, object>(StringComparer.Ordinal);
            for (int index = 0; index < keyValues.Length; index += 2)
                result.Add((string)keyValues[index], keyValues[index + 1]);
            return result;
        }

        public static List<object> Array()
        {
            return new List<object>();
        }
    }
}
