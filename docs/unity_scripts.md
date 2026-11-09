# Unity Scripts

Run built-in and your own C# editor scripts in a Unity project from one panel, each script's settings as rows. A script runs in the Unity editor that has the project open, as one undo step; what it and the Console report comes back to the panel's log.

Opened from Maya or Blender (tentacle's Scene menu), a script that takes an asset can be given the **Current Scene**: the Scope is exported by that host's Scene Exporter, as a fresh Scene Exporter panel would export it, and copied into the project. On its own the panel gives a script a **model file**.

## Set up a project (once)

1. Set the **Unity Project** field to the folder holding `Assets/` and `ProjectSettings/`.
2. From the field's menu, choose **Install / Update Connection**. It copies the small `com.m3trik.unity-scripts` editor package into the project's `Packages/` folder, as an embedded package: it works offline, needs no git, and travels with the project to your teammates.
3. Switch to Unity. The Console says the connection is serving the project.

**Tools ▸ M3trik Scripts ▸ Pause** in Unity stops it for that project; the panel then says it is paused and sends nothing. **Remove Connection** (the same menu) takes the package out, with the script copies it wrote into `Assets/M3trikScripts`.

An editor in batch mode (`-batchmode`) serves only when started with `-m3trikScriptsServe`, so a build or a CI run never takes a script by accident. Such an editor, started by automation for itself, ends between scripts when asked to (`ptk.JobQueue.stop`); an editor you opened never ends on that request, and Pause is its switch.

With Unity closed, a Source is still copied into the project, and Unity imports it when the project next opens. The script itself runs only while Unity is open: a script left to run on the next open would act on whatever scene Unity restored.

## The built-in scripts

| Script | Takes | What it does |
|---|---|---|
| **Send to Unity** | a model file or the scene | Imports it into `Assets/<subfolder>`, adds an instance to the open scene when it holds none (a model sent again updates its instances in place), then selects and frames it. |
| **Make Prefab** | a model file or the scene | Imports it and saves a prefab variant in `Assets/<Prefab Folder>`, which follows the model; one already there is kept, with your overrides. |
| **Reimport Folder** | nothing | Reimports everything under `Assets/<subfolder>`. |

## Write your own

The script list's menu: **Copy to My Scripts** copies the selected script into your own scripts folder, to edit; yours then runs in its place. **Open My Scripts Folder** shows that folder (`<your config folder>/scripts/unity`), where any new `.cs` file shows in the list after **Refresh Templates**.

A script is one C# file whose class is named as the file, with a `[UnityScript]` static method taking `ScriptArgs` (or nothing):

```csharp
// Tag Selection: add a tag to everything selected in the open scene.
// SOURCES = ()
// Rows: __ASSETS_SUBDIR__
using M3trik.UnityScripts;
using UnityEditor;
using UnityEngine;

public static class TagSelection
{
    [UnityScript]
    public static void Run(ScriptArgs args)
    {
        foreach (GameObject go in Selection.gameObjects)
        {
            Undo.RecordObject(go, "Tag");
            go.tag = "Respawn";
        }
        args.Report($"Tagged {Selection.gameObjects.Length} object(s).");
    }
}
```

- **The header** is read by the panel without compiling the script. Its first line is the description the log shows. `SOURCES` says what the script takes: `("scene", "file")` (the default when the line is missing), one of them, or `()` for a script that runs on the project alone. Each `__KEY__` token shows that row in the panel.
- **The rows** are the panel's: `ASSETS_SUBDIR`, `ASSET_NAME`, `PLACE_IN_SCENE`, `FRAME_SELECTION`, `PREFAB_FOLDER`, plus the host's (`SCOPE`). A script reads a row's value by its key; nothing is substituted into the source, so a script compiles once per project, not on every run.
- **`ScriptArgs`**: `Asset` (the delivered file's project path, imported already, or null), `GetString`, `GetBool`, `GetInt`, `GetFloat`, `GetNumber` and `Has` (a row's value by key), `Created(path)` (an asset this run made, listed and linked in the panel), `Report(line)` (a line for the panel's log), `CancelRequested` (the panel's **Cancel Running Script**: check it between steps).
- **`ScriptHost`**, what the built-ins use: `LoadModel(path)`, `Instances(model)` (its instances in the open scenes), `Place(model)` (one undo step), `Show(object, frame)`, `SaveVariant(model, folder)`, `EnsureFolder(path)`, `AssetsFolder(sub)`.
- **Undo**: a run is one undo step, named after the script. Record what you change (`Undo.RecordObject`, `Undo.RegisterCreatedObjectUndo`), as any editor tool does.

## When something goes wrong

- **A script that does not compile** never enters your project: Unity compiles a changed script on its own first (into `Library/`), and only one that compiles is written into `Assets/M3trikScripts`. Its compiler errors land in the panel's log; fix your copy and run it again. Should Unity close between writing a script and compiling it, it puts the project back as it was when it next opens.
- **"Unity did not compile the script in time"**: another script in the project does not compile (Unity compiles nothing while one fails), or the editor's **Auto Refresh** is off (Preferences ▸ Asset Pipeline).
- **"open the project in Unity"**: no editor is serving the project. Open it in Unity Hub (or resume a paused connection), then run again.
- **A Scene Exporter check fails** while sending the scene: the panel asks the Scene Exporter's own question, in its words: Override All, Override (this check), or Cancel.
