using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace M3trik.UnityScripts
{
    /// <summary>
    /// What a script is run with: the values of the rows its header names (the
    /// panel's attributes, by key), the asset the panel delivered, and the way
    /// back to the panel (<see cref="Created"/>, <see cref="Report"/>,
    /// <see cref="CancelRequested"/>).
    /// </summary>
    public sealed class ScriptArgs
    {
        readonly Dictionary<string, object> _values;
        readonly string _cancelFile;
        internal readonly List<string> CreatedAssets = new List<string>();
        internal readonly List<string> Lines = new List<string>();

        internal ScriptArgs(string script, string asset, Dictionary<string, object> values, string cancelFile)
        {
            Script = script;
            Asset = string.IsNullOrEmpty(asset) ? null : asset;
            _values = values ?? new Dictionary<string, object>();
            _cancelFile = cancelFile;
        }

        /// <summary>The script's name (its file's, and its class's).</summary>
        public string Script { get; }

        /// <summary>The delivered asset's project path (<c>Assets/Imported/Crate.fbx</c>),
        /// imported already; null when the script runs on the project alone.</summary>
        public string Asset { get; }

        /// <summary>Every value the panel sent, by key.</summary>
        public IReadOnlyDictionary<string, object> Values => _values;

        /// <summary>Whether the panel sent a value for <paramref name="key"/>.</summary>
        public bool Has(string key) => _values.ContainsKey(key);

        /// <summary>The value of <paramref name="key"/> as text, else <paramref name="fallback"/>.</summary>
        public string GetString(string key, string fallback = "")
        {
            return _values.TryGetValue(key, out object value) && value != null
                ? Convert.ToString(value, CultureInfo.InvariantCulture)
                : fallback;
        }

        /// <summary>The value of <paramref name="key"/> as a flag (a bool, a number, or
        /// "true" / "yes" / "on" / "1"), else <paramref name="fallback"/>.</summary>
        public bool GetBool(string key, bool fallback = false)
        {
            if (!_values.TryGetValue(key, out object value) || value == null) return fallback;
            if (value is bool flag) return flag;
            if (value is double number) return Math.Abs(number) > double.Epsilon;
            switch (Convert.ToString(value, CultureInfo.InvariantCulture).Trim().ToLowerInvariant())
            {
                case "true": case "yes": case "on": case "1": return true;
                case "false": case "no": case "off": case "0": case "": return false;
                default: return fallback;
            }
        }

        /// <summary>The value of <paramref name="key"/> as a number, else <paramref name="fallback"/>.</summary>
        public double GetNumber(string key, double fallback = 0)
        {
            if (!_values.TryGetValue(key, out object value) || value == null) return fallback;
            if (value is double number) return number;
            return double.TryParse(Convert.ToString(value, CultureInfo.InvariantCulture), NumberStyles.Float,
                CultureInfo.InvariantCulture, out double parsed) ? parsed : fallback;
        }

        /// <summary>The value of <paramref name="key"/> as a whole number, else <paramref name="fallback"/>.</summary>
        public int GetInt(string key, int fallback = 0) => (int)Math.Round(GetNumber(key, fallback));

        /// <summary>The value of <paramref name="key"/> as a float, else <paramref name="fallback"/>.</summary>
        public float GetFloat(string key, float fallback = 0f) => (float)GetNumber(key, fallback);

        /// <summary>Whether the panel asked this run to stop: a long script checks
        /// it between steps and returns early.</summary>
        public bool CancelRequested => !string.IsNullOrEmpty(_cancelFile) && File.Exists(_cancelFile);

        /// <summary>Tell the panel an asset this run made or changed (its project
        /// path); the panel lists it, linked.</summary>
        public void Created(string assetPath)
        {
            if (!string.IsNullOrEmpty(assetPath) && !CreatedAssets.Contains(assetPath)) CreatedAssets.Add(assetPath);
        }

        /// <summary>A line for the panel's log (the Console keeps its own).</summary>
        public void Report(string line)
        {
            if (line != null) Lines.Add(line);
        }
    }
}
