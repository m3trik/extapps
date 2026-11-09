using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace M3trik.UnityScripts
{
    /// <summary>
    /// JSON read and written with the base library alone, for the job files the
    /// panel and the worker exchange: an object reads as a
    /// <c>Dictionary&lt;string, object&gt;</c>, an array as a
    /// <c>List&lt;object&gt;</c>, a number as <c>double</c>, and true, false and
    /// null as themselves; Python's <c>NaN</c> / <c>Infinity</c> /
    /// <c>-Infinity</c> (what its <c>json</c> writes for them) read as those doubles.
    /// </summary>
    /// <remarks>
    /// Prior art: Unity's <c>JsonUtility</c> reads only fixed <c>[Serializable]</c>
    /// types, and a job's args are whatever rows a script names; Newtonsoft
    /// (<c>com.unity.nuget.newtonsoft-json</c>) would add a registry dependency
    /// to a package that installs as a copy and works offline.
    /// </remarks>
    public static class Json
    {
        /// <summary>The value <paramref name="text"/> holds.</summary>
        /// <exception cref="FormatException">It is not one JSON value.</exception>
        public static object Parse(string text)
        {
            var parser = new Parser(text);
            object value = parser.Value();
            parser.End();
            return value;
        }

        /// <summary><paramref name="value"/> as JSON: a dictionary, a list, a
        /// string, a number, a bool or null (anything else as its text).</summary>
        public static string Write(object value)
        {
            var sb = new StringBuilder();
            WriteValue(sb, value);
            return sb.ToString();
        }

        sealed class Parser
        {
            readonly string _s;
            int _i;

            public Parser(string text) { _s = text ?? ""; }

            FormatException Error(string what) => new FormatException($"JSON: {what} at character {_i}");

            void Skip()
            {
                while (_i < _s.Length && char.IsWhiteSpace(_s[_i])) _i++;
            }

            bool Peek(char c) => _i < _s.Length && _s[_i] == c;

            void Expect(char c)
            {
                if (!Peek(c)) throw Error($"expected '{c}'");
                _i++;
            }

            public void End()
            {
                Skip();
                if (_i != _s.Length) throw Error("text after the value");
            }

            public object Value()
            {
                Skip();
                if (_i >= _s.Length) throw Error("unexpected end");
                switch (_s[_i])
                {
                    case '{': return Object();
                    case '[': return Array();
                    case '"': return String();
                    case 't': Word("true"); return true;
                    case 'f': Word("false"); return false;
                    case 'n': Word("null"); return null;
                    case 'N': Word("NaN"); return double.NaN;
                    case 'I': Word("Infinity"); return double.PositiveInfinity;
                    default: return Number();
                }
            }

            void Word(string word)
            {
                if (_i + word.Length > _s.Length || string.CompareOrdinal(_s, _i, word, 0, word.Length) != 0)
                    throw Error("unknown literal");
                _i += word.Length;
            }

            Dictionary<string, object> Object()
            {
                var map = new Dictionary<string, object>();
                _i++;
                Skip();
                if (Peek('}')) { _i++; return map; }
                while (true)
                {
                    Skip();
                    if (!Peek('"')) throw Error("expected a key");
                    string key = String();
                    Skip();
                    Expect(':');
                    map[key] = Value();
                    Skip();
                    if (Peek(',')) { _i++; continue; }
                    Expect('}');
                    return map;
                }
            }

            List<object> Array()
            {
                var list = new List<object>();
                _i++;
                Skip();
                if (Peek(']')) { _i++; return list; }
                while (true)
                {
                    list.Add(Value());
                    Skip();
                    if (Peek(',')) { _i++; continue; }
                    Expect(']');
                    return list;
                }
            }

            string String()
            {
                var sb = new StringBuilder();
                _i++;  // the opening quote
                while (true)
                {
                    if (_i >= _s.Length) throw Error("unterminated string");
                    char c = _s[_i++];
                    if (c == '"') return sb.ToString();
                    if (c != '\\') { sb.Append(c); continue; }
                    if (_i >= _s.Length) throw Error("unterminated escape");
                    char e = _s[_i++];
                    switch (e)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (_i + 4 > _s.Length) throw Error("short \\u escape");
                            sb.Append((char)int.Parse(_s.Substring(_i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                            _i += 4;
                            break;
                        default: throw Error($"unknown escape '\\{e}'");
                    }
                }
            }

            double Number()
            {
                if (_i + 1 < _s.Length && _s[_i] == '-' && _s[_i + 1] == 'I')
                {
                    Word("-Infinity");
                    return double.NegativeInfinity;
                }
                int start = _i;
                while (_i < _s.Length && "+-0123456789.eE".IndexOf(_s[_i]) >= 0) _i++;
                if (start == _i) throw Error($"unexpected '{_s[_i]}'");
                return double.Parse(_s.Substring(start, _i - start), NumberStyles.Float, CultureInfo.InvariantCulture);
            }
        }

        static void WriteValue(StringBuilder sb, object value)
        {
            switch (value)
            {
                case null:
                    sb.Append("null");
                    return;
                case string text:
                    WriteString(sb, text);
                    return;
                case bool flag:
                    sb.Append(flag ? "true" : "false");
                    return;
                case IDictionary map:
                    sb.Append('{');
                    bool first = true;
                    foreach (DictionaryEntry entry in map)
                    {
                        if (!first) sb.Append(',');
                        first = false;
                        WriteString(sb, Convert.ToString(entry.Key, CultureInfo.InvariantCulture));
                        sb.Append(':');
                        WriteValue(sb, entry.Value);
                    }
                    sb.Append('}');
                    return;
                case IEnumerable items:
                    sb.Append('[');
                    bool head = true;
                    foreach (object item in items)
                    {
                        if (!head) sb.Append(',');
                        head = false;
                        WriteValue(sb, item);
                    }
                    sb.Append(']');
                    return;
                case double d:
                    WriteNumber(sb, d);
                    return;
                case float f:
                    WriteNumber(sb, f);
                    return;
                case IConvertible number when IsNumber(number):
                    sb.Append(number.ToString(CultureInfo.InvariantCulture));
                    return;
                default:
                    WriteString(sb, Convert.ToString(value, CultureInfo.InvariantCulture));
                    return;
            }
        }

        static bool IsNumber(IConvertible value)
        {
            switch (value.GetTypeCode())
            {
                case TypeCode.SByte: case TypeCode.Byte: case TypeCode.Int16: case TypeCode.UInt16:
                case TypeCode.Int32: case TypeCode.UInt32: case TypeCode.Int64: case TypeCode.UInt64:
                case TypeCode.Decimal:
                    return true;
                default:
                    return false;
            }
        }

        static void WriteNumber(StringBuilder sb, double d)
        {
            // JSON has no NaN or infinity: null says "no number" honestly.
            if (double.IsNaN(d) || double.IsInfinity(d)) sb.Append("null");
            else sb.Append(d.ToString("R", CultureInfo.InvariantCulture));
        }

        static void WriteString(StringBuilder sb, string text)
        {
            sb.Append('"');
            foreach (char c in text)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    case '\b': sb.Append("\\b"); break;
                    case '\f': sb.Append("\\f"); break;
                    default:
                        if (c < ' ') sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
        }
    }
}
