using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;
using Assembly = System.Reflection.Assembly;
using Debug = UnityEngine.Debug;

namespace M3trik.UnityScripts
{
    /// <summary>
    /// Serves this project's script queue (<c>Library/M3trikUnityScripts/queue</c>)
    /// while the project is open: each job the Unity Scripts panel sends, in
    /// order, on the main thread, between editor updates, never while Unity
    /// compiles, imports or plays.
    /// </summary>
    /// <remarks>
    /// A job's script is written into <c>Assets/M3trikScripts</c>, an
    /// assembly of its own (<see cref="UserAssembly"/>). A changed one is first
    /// compiled on the side, into Library (<c>AssemblyBuilder</c>): one that does
    /// not compile never enters the project, its errors reported. One that does
    /// is written, compiles and the domain reloads, and this class re-arms itself
    /// (<see cref="InitializeOnLoadAttribute"/>, its job in
    /// <see cref="SessionState"/>) and runs it; should the project's own compile
    /// still fail, the previous file is put back, and an editor that closed
    /// mid-way puts it back when it next opens. A person's assemblies are never
    /// left failing. A run is one undo step.
    /// Visible and switchable off (CODE_STANDARD section 15): it says so in the
    /// Console when it starts, and Tools &gt; M3trik Scripts &gt; Pause stops it, kept
    /// in the project. A batch editor serves only with <see cref="ServeFlag"/>.
    /// Prior art: Unity's <c>-executeMethod</c> runs one method in an editor it
    /// starts, and cannot reach a project already open; socket servers in the
    /// editor (mcp-unity and similar) open a port any local process can call and
    /// drop their calls on every domain reload. pythontk's JobQueue (a folder of
    /// JSON jobs, no port) survives both; its file names here are generated
    /// from pythontk (<see cref="QueueLayout"/>).
    /// </remarks>
    [InitializeOnLoad]
    public static class ScriptWorker
    {
        /// <summary>The command-line flag a batch editor serves the queue with.</summary>
        public const string ServeFlag = "-m3trikScriptsServe";
        /// <summary>This package's folder in the project's Library.</summary>
        public const string Folder = "Library/M3trikUnityScripts";
        /// <summary>Where a job's script is written, its own assembly.</summary>
        public const string ScriptsFolder = "Assets/M3trikScripts";
        /// <summary>The scripts' assembly: editor-only, over this package's.</summary>
        public const string UserAssembly = "M3trik.UnityScripts.User";
        /// <summary>A running job's cancel request: <c>&lt;id&gt;.cancel</c> beside it.</summary>
        public const string CancelSuffix = ".cancel";

        const string MenuPause = "Tools/M3trik Scripts/Pause";
        const string KeyJob = "M3trik.UnityScripts.Job";
        const string KeyStage = "M3trik.UnityScripts.Stage";
        const string KeyErrors = "M3trik.UnityScripts.Errors";
        const string KeyCompiled = "M3trik.UnityScripts.Compiled";
        const string KeyDomain = "M3trik.UnityScripts.Domain";
        const string KeyWrittenIn = "M3trik.UnityScripts.WrittenIn";
        const string KeyWrittenAt = "M3trik.UnityScripts.WrittenAt";
        const string KeyTakenAt = "M3trik.UnityScripts.TakenAt";
        const string KeyStarted = "M3trik.UnityScripts.Started";
        const string KeyAnnounced = "M3trik.UnityScripts.Announced";
        const string KeyChecked = "M3trik.UnityScripts.Checked";
        const string KeyCheckIn = "M3trik.UnityScripts.CheckIn";
        const string KeyCheckAt = "M3trik.UnityScripts.CheckAt";
        const double TickEvery = 0.25;
        const int BeatEveryMs = 2000;
        /// <summary>Seconds a changed script may take to compile and reload.</summary>
        const double CompileTimeout = 180;

        static readonly object Gate = new object();
        static readonly int Pid = Process.GetCurrentProcess().Id;
        static string _queue, _paused, _unity, _project, _job;
        static double _started, _lastTick;
        static bool _restorePending;
        static int _domain;
        static Timer _beat;

        static ScriptWorker()
        {
            if (AssetDatabase.IsAssetImportWorkerProcess()) return;
            if (Application.isBatchMode && !Environment.GetCommandLineArgs().Contains(ServeFlag)) return;
            _queue = Path.GetFullPath(Path.Combine(Folder, "queue"));
            _paused = Path.GetFullPath(Path.Combine(Folder, "paused"));
            _unity = Application.unityVersion;
            _project = Path.GetFullPath(".");
            Directory.CreateDirectory(_queue);
            _domain = SessionState.GetInt(KeyDomain, 0) + 1;
            SessionState.SetInt(KeyDomain, _domain);
            _started = ReadTime(KeyStarted);
            if (_started <= 0)
            {
                _started = Now();
                WriteTime(KeyStarted, _started);
                // A stop asked of an earlier editor is spent (as pythontk's
                // worker does when it starts serving); a reload keeps one.
                try { File.Delete(StopPath); }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }
                // A script an earlier editor wrote and closed (or crashed)
                // before it compiled is put back, on the first tick that is not
                // compiling or importing (the database knows the file by then).
                _restorePending = File.Exists(PendingPath);
            }
            _job = SessionState.GetString(KeyJob, "");
            if (_job.Length == 0) _job = null;
            CompilationPipeline.assemblyCompilationFinished += OnAssemblyCompiled;
            EditorApplication.update += Tick;
            EditorApplication.quitting += OnQuitting;
            AssemblyReloadEvents.beforeAssemblyReload += StopBeating;
            FailOrphans();
            StartBeating();
            if (!SessionState.GetBool(KeyAnnounced, false))
            {
                SessionState.SetBool(KeyAnnounced, true);
                Debug.Log(Paused
                    ? "M3trik Unity Scripts: paused for this project; Tools > M3trik Scripts > Pause resumes it."
                    : "M3trik Unity Scripts: serving this project's scripts from the Unity Scripts panel; Tools > M3trik Scripts > Pause stops it.");
            }
        }

        /// <summary>Whether the person paused the worker for this project.</summary>
        public static bool Paused => _paused != null && File.Exists(_paused);

        // ------------------------------------------------------------------ menu
        [MenuItem(MenuPause, false, 2000)]
        static void TogglePause()
        {
            if (_paused == null) return;
            if (Paused) File.Delete(_paused);
            else File.WriteAllText(_paused, "paused");
            Beat();
            Debug.Log(Paused
                ? "M3trik Unity Scripts: paused; the panel says so and sends nothing until you resume."
                : "M3trik Unity Scripts: serving again.");
        }

        [MenuItem(MenuPause, true)]
        static bool TogglePauseValidate()
        {
            Menu.SetChecked(MenuPause, Paused);
            return _paused != null;
        }

        // ------------------------------------------------------------------ heartbeat
        static void StartBeating()
        {
            StopBeating();
            _beat = new Timer(_ => Beat(), null, 0, BeatEveryMs);
        }

        static void StopBeating()
        {
            _beat?.Dispose();
            _beat = null;
        }

        static void OnQuitting()
        {
            StopBeating();
            Beat(QueueLayout.StateStopped);
        }

        /// <summary>The heartbeat, from the timer thread too: file work and fields
        /// only, never a Unity API. A paused worker says "stopped", so the panel
        /// sends nothing.</summary>
        static void Beat(string state = null)
        {
            if (_queue == null) return;
            bool paused = Paused;
            var data = new Dictionary<string, object>
            {
                ["pid"] = Pid,
                ["host"] = Environment.MachineName,
                ["state"] = state ?? (paused ? QueueLayout.StateStopped : QueueLayout.StateServing),
                ["paused"] = paused,
                ["job"] = _job,
                ["started"] = _started,
                ["beat"] = Now(),
                ["unity"] = _unity,
                ["project"] = _project,
            };
            lock (Gate)
            {
                try { WriteJson(Path.Combine(_queue, QueueLayout.Worker), data); }
                catch (IOException) { }  // a reader held it open: the next beat lands
                catch (UnauthorizedAccessException) { }
            }
        }

        // ------------------------------------------------------------------ the loop
        static void Tick()
        {
            double now = EditorApplication.timeSinceStartup;
            if (now - _lastTick < TickEvery) return;
            _lastTick = now;
            if (EditorApplication.isCompiling || EditorApplication.isUpdating
                || EditorApplication.isPlayingOrWillChangePlaymode)
                return;
            if (_restorePending)
            {
                _restorePending = false;
                RestorePending();
                return;
            }
            string id = _job;
            if (id == null)
            {
                if (StopAsked())
                {
                    EndServing();
                    return;
                }
                if (Paused) return;
                id = Take();
                if (id == null) return;
            }
            Advance(id);
        }

        static string StopPath => Path.Combine(_queue, QueueLayout.Stop);

        /// <summary>Whether the tooling asked its own editor to end (pythontk's
        /// <c>JobQueue.stop</c>): only a batch editor served with
        /// <see cref="ServeFlag"/> honours it, between jobs. A person's editor
        /// never ends on a file; Pause is their switch.</summary>
        static bool StopAsked() => Application.isBatchMode && File.Exists(StopPath);

        /// <summary>Spend the stop request, say "stopped" and end the editor.</summary>
        static void EndServing()
        {
            try { File.Delete(StopPath); }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
            StopBeating();
            Beat(QueueLayout.StateStopped);
            EditorApplication.Exit(0);
        }

        /// <summary>The oldest queued job, now running, or null.</summary>
        static string Take()
        {
            string name = Directory.GetFiles(_queue, "*" + QueueLayout.Queued)
                .Select(Path.GetFileName)
                .OrderBy(n => n, StringComparer.Ordinal)
                .FirstOrDefault();
            if (name == null) return null;
            string id = name.Substring(0, name.Length - QueueLayout.Queued.Length);
            try
            {
                File.Move(Path.Combine(_queue, name), Running(id));
            }
            catch (IOException)
            {
                return null;  // withdrawn meanwhile, or held a moment: the next tick
            }
            _job = id;
            SessionState.SetString(KeyJob, id);
            SessionState.SetString(KeyStage, "start");
            WriteTime(KeyTakenAt, Now());
            Beat();
            return id;
        }

        static void Advance(string id)
        {
            Dictionary<string, object> job;
            try
            {
                job = Json.Parse(File.ReadAllText(Running(id))) as Dictionary<string, object>
                      ?? throw new FormatException("the job is no JSON object");
            }
            catch (FileNotFoundException)
            {
                Close(id);
                return;
            }
            catch (Exception error)
            {
                Fail(id, "The job could not be read: " + error.Message);
                return;
            }
            try
            {
                string op = Text(job, "op");
                switch (op)
                {
                    case "ping":
                        Finish(id, new Dictionary<string, object> { ["unity"] = _unity, ["project"] = _project });
                        return;
                    case "script.run":
                        RunScript(id, job);
                        return;
                    default:
                        Fail(id, $"Unknown op '{op}': this package is older than the panel? Update the connection.");
                        return;
                }
            }
            catch (Exception error)
            {
                Fail(id, error.ToString());
            }
        }

        // ------------------------------------------------------------------ script.run
        static void RunScript(string id, Dictionary<string, object> job)
        {
            string name = Text(job, "script");
            string source = Text(job, "source");
            if (!ValidName(name))
            {
                Fail(id, $"'{name}' is no script name: letters, digits and underscores, the C# class its file defines.");
                return;
            }
            string path = ScriptsFolder + "/" + name + ".cs";
            string stage = SessionState.GetString(KeyStage, "start");
            if (stage == "start")
            {
                EnsureAssembly();
                string current = File.Exists(path) ? File.ReadAllText(path) : null;
                if (current != source)
                {
                    StartCheck(name, source);
                    SessionState.SetString(KeyStage, "checking");
                    return;  // compiled on the side first: the next ticks read the answer
                }
                stage = "run";
                SessionState.SetString(KeyStage, stage);
            }
            if (stage == "checking")
            {
                if (SessionState.GetInt(KeyCheckIn, 0) != _domain)
                {
                    StartCheck(name, source);  // a reload dropped the builder (or it was busy)
                    return;
                }
                if (!SessionState.GetBool(KeyChecked, false))
                {
                    if (Now() - ReadTime(KeyCheckAt) > CompileTimeout)
                        Fail(id, "Unity did not compile the script in time; your project was left as it was.");
                    return;
                }
                string problems = SessionState.GetString(KeyErrors, "");
                if (problems.Length > 0)
                {
                    Fail(id, "The script did not compile, so it was not added to your project, which compiles as before:\n" + problems);
                    return;
                }
                string current = File.Exists(path) ? File.ReadAllText(path) : null;
                Backup(name, current);
                WritePending(name);
                File.WriteAllText(path, source);
                SessionState.SetString(KeyErrors, "");
                SessionState.SetBool(KeyCompiled, false);
                SessionState.SetInt(KeyWrittenIn, _domain);
                WriteTime(KeyWrittenAt, Now());
                SessionState.SetString(KeyStage, "compiling");
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                CompilationPipeline.RequestScriptCompilation();
                return;  // compiled, the domain reloads and the next tick here runs it
            }
            if (stage == "compiling")
            {
                string errors = SessionState.GetString(KeyErrors, "");
                if (errors.Length > 0)
                {
                    Restore(name);
                    Fail(id, "The script did not compile, so it was taken out again and your project compiles as before:\n" + errors);
                    return;
                }
                bool reloaded = SessionState.GetBool(KeyCompiled, false) && _domain > SessionState.GetInt(KeyWrittenIn, 0);
                if (!reloaded)
                {
                    if (Now() - ReadTime(KeyWrittenAt) > CompileTimeout)
                    {
                        Restore(name);
                        Fail(id, "Unity did not compile the script in time: another script in the project may not compile, "
                                 + "or Auto Refresh is off (Preferences > Asset Pipeline). It was taken out again.");
                    }
                    return;
                }
                ClearPending();  // it compiles: nothing to put back if Unity closes now
                SessionState.SetString(KeyStage, "run");
            }
            Invoke(id, name, job);
        }

        static string CheckFolder => Path.GetFullPath(Path.Combine(Folder, "check"));

        /// <summary>Compile the script on its own, into Library, beside the other
        /// scripts of its assembly as that assembly would hold them: only one that
        /// compiles is written into Assets, so neither the project's build nor a
        /// later editor start ever meets one that does not (Unity in batch mode
        /// quits on such a project, and a GUI editor asks for Safe Mode).</summary>
        static void StartCheck(string name, string source)
        {
            Directory.CreateDirectory(CheckFolder);
            string script = Path.Combine(CheckFolder, name + ".cs");
            File.WriteAllText(script, source);
            SessionState.SetString(KeyErrors, "");
            SessionState.SetBool(KeyChecked, false);
            SessionState.SetInt(KeyCheckIn, _domain);
            WriteTime(KeyCheckAt, Now());
            string[] scripts = (Directory.Exists(ScriptsFolder) ? Directory.GetFiles(ScriptsFolder, "*.cs") : new string[0])
                .Where(p => Path.GetFileNameWithoutExtension(p) != name)
                .Select(Path.GetFullPath)
                .Append(script)
                .ToArray();
            var builder = new AssemblyBuilder(Path.Combine(CheckFolder, UserAssembly + ".dll"), scripts)
            {
                flags = AssemblyBuilderFlags.EditorAssembly,
                referencesOptions = ReferencesOptions.UseEngineModules,
            };
            string package = typeof(ScriptArgs).Assembly.Location;
            if (!builder.defaultReferences.Any(r => Path.GetFileName(r) == Path.GetFileName(package)))
                builder.additionalReferences = new[] { package };
            builder.buildFinished += (assembly, messages) =>
            {
                string[] errors = messages
                    .Where(m => m.type == CompilerMessageType.Error)
                    .Select(m => $"{Path.GetFileName(m.file)}({m.line}): {m.message}")
                    .ToArray();
                SessionState.SetString(KeyErrors, string.Join("\n", errors));
                SessionState.SetBool(KeyChecked, true);
            };
            if (!builder.Build())
                SessionState.SetInt(KeyCheckIn, -1);  // Unity is busy compiling: asked again next tick
        }

        static void OnAssemblyCompiled(string assemblyPath, CompilerMessage[] messages)
        {
            if (Path.GetFileNameWithoutExtension(assemblyPath) != UserAssembly) return;
            string[] errors = messages
                .Where(m => m.type == CompilerMessageType.Error)
                .Select(m => $"{m.file}({m.line}): {m.message}")
                .ToArray();
            SessionState.SetString(KeyErrors, string.Join("\n", errors));
            SessionState.SetBool(KeyCompiled, errors.Length == 0);
        }

        static void Invoke(string id, string name, Dictionary<string, object> job)
        {
            MethodInfo method = FindScript(name, out string problem);
            if (method == null)
            {
                Fail(id, problem);
                return;
            }
            var values = job.TryGetValue("args", out object raw) ? raw as Dictionary<string, object> : null;
            var args = new ScriptArgs(name, Text(job, "asset"), values, Cancel(id));
            var console = new List<object>();
            Application.LogCallback capture = (message, trace, type) =>
                console.Add(new Dictionary<string, object> { ["type"] = type.ToString(), ["message"] = message });
            Undo.IncrementCurrentGroup();
            Undo.SetCurrentGroupName("M3trik Script: " + name);
            int group = Undo.GetCurrentGroup();
            var watch = Stopwatch.StartNew();
            string failure = null;
            Application.logMessageReceived += capture;
            try
            {
                if (args.Asset != null)
                    AssetDatabase.ImportAsset(args.Asset, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                method.Invoke(null, method.GetParameters().Length == 1 ? new object[] { args } : null);
            }
            catch (TargetInvocationException error)
            {
                failure = (error.InnerException ?? error).ToString();
            }
            catch (Exception error)
            {
                failure = error.ToString();
            }
            finally
            {
                Application.logMessageReceived -= capture;
                Undo.CollapseUndoOperations(group);
            }
            if (failure != null)
            {
                Fail(id, failure, console);
                return;
            }
            Finish(id, new Dictionary<string, object>
            {
                ["script"] = name,
                ["created"] = args.CreatedAssets,
                ["report"] = args.Lines,
                ["console"] = console,
                ["cancelled"] = args.CancelRequested,
                ["seconds"] = Math.Round(watch.Elapsed.TotalSeconds, 3),
            });
        }

        static MethodInfo FindScript(string name, out string problem)
        {
            problem = null;
            Assembly assembly = AppDomain.CurrentDomain.GetAssemblies()
                .FirstOrDefault(a => a.GetName().Name == UserAssembly);
            if (assembly == null)
            {
                problem = $"The scripts' assembly ({UserAssembly}) is not loaded: is another script in {ScriptsFolder} failing to compile?";
                return null;
            }
            Type type = assembly.GetTypes().FirstOrDefault(t => t.Name == name);
            if (type == null)
            {
                problem = $"{ScriptsFolder}/{name}.cs defines no class {name}: a script's class is named as its file.";
                return null;
            }
            MethodInfo method = type
                .GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)
                .FirstOrDefault(m => m.GetCustomAttribute<UnityScriptAttribute>() != null);
            if (method == null)
            {
                problem = $"{name} has no [UnityScript] static method to run.";
                return null;
            }
            ParameterInfo[] parameters = method.GetParameters();
            if (parameters.Length > 1 || (parameters.Length == 1 && parameters[0].ParameterType != typeof(ScriptArgs)))
            {
                problem = $"{name}.{method.Name} takes {parameters.Length} parameter(s): a script's method takes one ScriptArgs, or none.";
                return null;
            }
            return method;
        }

        // ------------------------------------------------------------------ the scripts' folder
        static void EnsureAssembly()
        {
            Directory.CreateDirectory(ScriptsFolder);
            string asmdef = ScriptsFolder + "/" + UserAssembly + ".asmdef";
            if (File.Exists(asmdef)) return;
            File.WriteAllText(asmdef,
                "{\n" +
                $"    \"name\": \"{UserAssembly}\",\n" +
                "    \"references\": [\"M3trik.UnityScripts.Editor\"],\n" +
                "    \"includePlatforms\": [\"Editor\"],\n" +
                "    \"autoReferenced\": false\n" +
                "}\n");
            AssetDatabase.ImportAsset(asmdef);
        }

        static string BackupPath(string name) => Path.GetFullPath(Path.Combine(Folder, "backup", name + ".cs"));

        /// <summary>Keep the script's previous text (or that there was none).</summary>
        static void Backup(string name, string current)
        {
            string path = BackupPath(name);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            if (current == null) File.Delete(path);
            else File.WriteAllText(path, current);
        }

        /// <summary>Put the script back as it was before this job wrote it.</summary>
        static void Restore(string name)
        {
            string path = ScriptsFolder + "/" + name + ".cs";
            string backup = BackupPath(name);
            if (File.Exists(backup))
            {
                File.WriteAllText(path, File.ReadAllText(backup));
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            }
            else if (!AssetDatabase.DeleteAsset(path))
            {
                // Not an asset the database knows yet (written, then Unity
                // closed before it imported): the file itself goes.
                TryDelete(path);
                TryDelete(path + ".meta");
                AssetDatabase.Refresh();
            }
            ClearPending();
        }

        /// <summary>The script written and not yet compiled, on disk (it outlives
        /// the editor, where SessionState does not).</summary>
        static string PendingPath => Path.GetFullPath(Path.Combine(Folder, "pending"));

        static void WritePending(string name)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(PendingPath));
            File.WriteAllText(PendingPath, name);
        }

        static void ClearPending() => TryDelete(PendingPath);

        /// <summary>An earlier editor wrote a script and closed before it
        /// compiled: put it back, so a script that does not compile never stays
        /// in the project.</summary>
        static void RestorePending()
        {
            string name;
            try { name = File.ReadAllText(PendingPath).Trim(); }
            catch (IOException) { return; }
            if (!ValidName(name))
            {
                ClearPending();
                return;
            }
            Restore(name);
            Debug.Log($"M3trik Unity Scripts: {name} was being compiled when Unity closed, so it was put back as it was before.");
        }

        // ------------------------------------------------------------------ results
        static void Finish(string id, Dictionary<string, object> result)
        {
            WriteJson(Path.Combine(_queue, id + QueueLayout.Done), new Dictionary<string, object>
            {
                ["result"] = result,
                ["seconds"] = Math.Round(Now() - ReadTime(KeyTakenAt), 3),
            });
            Close(id);
        }

        static void Fail(string id, string error, List<object> console = null)
        {
            var record = new Dictionary<string, object> { ["error"] = error };
            if (console != null) record["console"] = console;
            WriteJson(Path.Combine(_queue, id + QueueLayout.Failed), record);
            Close(id);
        }

        static void Close(string id)
        {
            TryDelete(Running(id));
            TryDelete(Cancel(id));
            SessionState.EraseString(KeyJob);
            SessionState.EraseString(KeyStage);
            _job = null;
            Beat();
        }

        /// <summary>A job left running by an editor that closed mid-run fails, said.</summary>
        static void FailOrphans()
        {
            foreach (string file in Directory.GetFiles(_queue, "*" + QueueLayout.Running))
            {
                string name = Path.GetFileName(file);
                string id = name.Substring(0, name.Length - QueueLayout.Running.Length);
                if (id == _job) continue;
                WriteJson(Path.Combine(_queue, id + QueueLayout.Failed), new Dictionary<string, object>
                {
                    ["error"] = "The Unity editor running it closed before it finished.",
                });
                TryDelete(file);
            }
        }

        // ------------------------------------------------------------------ helpers
        static string Running(string id) => Path.Combine(_queue, id + QueueLayout.Running);

        static string Cancel(string id) => Path.Combine(_queue, id + CancelSuffix);

        static bool ValidName(string name)
        {
            return !string.IsNullOrEmpty(name)
                   && (char.IsLetter(name[0]) || name[0] == '_')
                   && name.All(c => char.IsLetterOrDigit(c) || c == '_');
        }

        static string Text(Dictionary<string, object> map, string key)
        {
            return map.TryGetValue(key, out object value) && value != null
                ? Convert.ToString(value, CultureInfo.InvariantCulture)
                : "";
        }

        static double Now() => (DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;

        // SessionState has no double: seconds since the epoch overflow a float's precision.
        static void WriteTime(string key, double value) => SessionState.SetString(key, value.ToString("R", CultureInfo.InvariantCulture));

        static double ReadTime(string key)
        {
            return double.TryParse(SessionState.GetString(key, ""), NumberStyles.Float, CultureInfo.InvariantCulture, out double value)
                ? value
                : 0;
        }

        /// <summary>Whole or not at all: a reader never sees half a file.</summary>
        static void WriteJson(string path, object data)
        {
            string temp = path + ".tmp";
            File.WriteAllText(temp, Json.Write(data));
            if (File.Exists(path)) File.Replace(temp, path, null);
            else File.Move(temp, path);
        }

        static void TryDelete(string path)
        {
            try
            {
                if (File.Exists(path)) File.Delete(path);
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
    }
}
