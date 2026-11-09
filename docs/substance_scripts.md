# Substance Scripts

Run Python scripts in Adobe Substance 3D Painter: the built-in ones and your own, each with the settings it declares, from a panel that needs no DCC.

## What it is

`substance_scripts` is a Switchboard panel over the Painter engine the Maya and Blender **Substance Bridge** panels use (`SubstanceEngine`, vendored byte-identical from mayatk with its Painter plugin, `substance_rpc`). With no host, a script that works on a mesh takes a **mesh file**.

- **A script** is a Python file Painter runs as written, with `args` holding its values (`args["MESH"]`, `args.get("AO_RAYS", 64)`), `args.report(line)`, `args.progress(f, text)` and `args.check_cancel()`. Its header, read without running it:

  ```python
  """Bake Lighting to Diffuse: Iray AO baked and laid over Base Color."""
  WORKS_ON = "project"   # "new" | "mesh" | "project"
  # Rows: __PAINTER_PROJECT__ __PAINTER_SAVE__ __PAINTER__
  # Row: __AO_RAYS__ int 64 "AO Rays" min=1 max=256
  ```

  The first docstring line is the description the panel logs. A `# Rows:` line shows panel rows (`__KEY__` tokens). A `# Row:` line declares a row of the script's own: a key, a kind (`bool`, `int`, `float`, `str`, `choice`, `path`, `file`), a default, a label and `option=value` pairs (`min`, `max`, `step`, `decimals`, `choices=a|b`, `tooltip`, `section`, `placeholder`).

- **Built-in scripts** (`templates/`):

  | Script | Runs on | Does |
  |---|---|---|
  | New Project | a new project from the mesh | `project.create` with its mesh maps; the high poly and per-material mesh maps from a host |
  | Update Mesh | the project made from the mesh | reloads it (paint kept where UVs match) |
  | Bake Lighting to Diffuse | a project | Iray AO (and curvature) baked and laid over Base Color |
  | Bake Mesh Maps | a project | the ticked mesh maps, every texture set |
  | Export Textures | a project | every texture set through an export preset |

- **Your scripts** live in `ptk.ScriptTemplate.user_dir("substance")`. The Maya and Blender bridges list them too. One named like a built-in runs in its place; **Copy to My Scripts** on the script list's menu copies the selected one there to edit.

## Which Painter

Each Painter running the plugin writes an **instance record** (pythontk's `RpcInstances`, under the per-user cache). The record holds the port the OS gave it, a token every call must carry, and the project it holds (path, name, UUID, its mesh). A Painter is found by that record, never by a fixed port, so any number can serve at once.

The **Painter** row is Auto, New Painter, or a running Painter by its project. Auto picks by what the script works on:
- **New Project:** a Painter with no project open, else a new one.
- **Update Mesh:** the Painter whose project was made from the mesh.
- **A project script:** the Painter holding the Project row's `.spp`. Otherwise one with none open, which opens it. Otherwise a new one. With no Project named, it runs on the project open in Painter.

A run carries the project it was meant for, and Painter refuses it if another project is open by then.

## Your Painter, by your hand

**Install in Painter** (Utilities menu) puts the plugin in Painter's plugins folder, ticked in its **Python** menu, and untick it there to switch it off. While it serves, Painter's menu bar shows **M3trik Scripts**: what it serves, and **Pause scripts**, which refuses scripts sent to that Painter until you untick it (one under way finishes; nothing from outside Painter resumes it). The panel's Painter row says when one is paused, and Auto never takes a paused Painter as a free one. A Painter you open then runs a script only when you click **Run in Painter**, and only when it isn't busy (not mid-bake or mid-load). Its edits are in **Painter's undo history**, one entry per step (the script, then each `args.when_idle` step) named for the script (`layerstack.ScopedModification`). What Painter itself does not undo (a project created, opened or saved) stays done. **Cancel Script** (Utilities) stops a queued script or a bake under way. A Run that has to launch Painter, or open the project in it, waits for that off the panel's UI thread: the panel stays live, and the script is queued once Painter is ready.

A send never installs the plugin: it only refreshes an install already there. A Painter the panel launches loads the plugin from a launch root (`SUBSTANCE_PAINTER_PLUGINS_PATH`) and touches nothing of yours.

The plugin's server accepts only local, token-bearing requests. It refuses any request a web page could send (an `Origin` header, a non-JSON body, a non-loopback `Host`). Agents and tests only ever launch their own Painter: a hidden one (on a private desktop) matched by the PID they launched, or a Python stand-in.

## Run

```powershell
extapps substance_scripts
```

```python
from extapps import SubstanceScripts

engine = SubstanceScripts()
result = engine.send(mesh="C:/meshes/crate.fbx", template="new_project",
                     params={"PAINTER_PROJECT": "C:/projects/crate.spp", "PAINTER_SAVE": True})
status = engine.wait(result)   # {"state": "done", "report": [...], ...}
```

## Tests

```powershell
& python -m pytest test/test_substance_scripts_panel.py      # the panel, a stand-in Painter
# live, in an owned hidden Painter (launches one; yours is never touched):
$env:EXTAPPS_PAINTER_LIVE = '1'
& python -m pytest test/test_substance_scripts_live.py
```

The engine and plugin are tested where they live: mayatk's `test_substance_bridge.py`, `test_substance_rpc_plugin.py`, `test_substance_bake_ops.py` and `test_substance_connection.py`.

## Known gaps

- Bake Lighting to Diffuse bakes the AO and adds its layer, but the layer's Base Color is not yet driven by the AO map: Painter's Python API has no verified setter for a fill layer's mesh-map source, so it warns.
- Bake Mesh Maps and Export Textures are new. They had no implementation before, and their live pass is the opt-in test above.
