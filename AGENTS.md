# extapps

<!-- packs (generated: edit the packs, then sync) -->
Shared rules (packs; Claude Code loads them, other agents read them first): [principles](.agents/packs/principles.md) · [python](.agents/packs/python.md)
<!-- /packs -->

**Role**: The standalone product: the host-free content-pipeline apps, each app's engine, panel (`.ui`) and Slots class together, on pythontk and uitk alone. Each is a uitk external app (`uitk.external_apps.in_process` entry points); tentacle's DCC menus open one BY NAME through uitk's `ExternalAppHandler`. Nothing imports extapps.

**Nav**: [← root](../AGENTS.md) · [docs](docs/README.md) · **Deps**: [pythontk](../pythontk/AGENTS.md) · [uitk](../uitk/AGENTS.md) · **Opened by**: [tentacle](../tentacle/AGENTS.md) (by name, never an import)

## API surface

Searched live (`api.search`; MCP `api_search`), never a committed file — rules in [root](../AGENTS.md). Upstream: [pythontk](../pythontk/AGENTS.md) · [uitk](../uitk/AGENTS.md).

Package-level public API.

## Scope

Belongs here: a host-free app -- no host half, needing no DCC to run (a host may open it in process and inject behaviour) -- whole: its app- or SDK-specific engine (Metashape, RealityScan, Brush, Painter, Toolbag), its `.ui`, Slots class and launcher. Not here: a tool with a host half, or one that needs a DCC to run (tentacle's panel over mayatk / blendertk); CLI-only utilities (`m3trik/scripts/`); a generic primitive (`pythontk`; generic Qt: `uitk`).

## Hard rules

- **No host and no tentacle import.** No module imports `maya`, `bpy`, `mayatk`, `blendertk` or `tentacle` (`test/test_imports.py`), and nothing imports extapps (`check_layers.py`: the product role). A host reaches an app only through uitk's `ExternalAppHandler`, by its entry-point name, and hands it context on the window it gets back (`launch(name, show=False)`).
- **Generic mechanism lives in `pythontk`; app-specific engines live with their apps.** pythontk is **app-agnostic** (`HandoffBridge`, `AppLauncher`, `RpcClient`, the pure domain cores), never product SDK glue, so an SDK-specific engine stays with its app (`metashape_workflow`, `substance_scripts`, `marmoset_scripts`). Code that *also* has DCC consumers is vendored, byte-identical, guarded by `test/test_vendor_sync.py`: the Marmoset engine and the Substance engine with its Painter plugin (mayatk's the SSoT; edit there, never here). A host's half is injected, never vendored: `unity_scripts` (the one Unity panel) and `webxr_preview` take the host's engine class (`slots.engine`), whose rows and scene export the panel calls. `unity_scripts` also ships a Unity editor package (`unity_package/`, MIT, its C# held by `check_csharp.py`), which a person installs into their own project: it serves the panel's jobs in their open editor, visible and pausable there (CODE_STANDARD section 15); agents and tests drive it only in an owned editor or through a Python stand-in worker.

### Painter session safety — HARD BLOCK (protect user work)

`substance_scripts` reaches a Painter by its instance record (`substance_rpc`'s, `SubstanceScripts.pick_painter`): one it launched, or the person's own **only on their Run**, through the plugin they installed (*Install in Painter*) and ticked, each run one undo entry there (CODE_STANDARD section 15). A send never installs the plugin.

**AI agent rule**: the tooling only ever launches (`SubstanceConnection.open`, matched by the PID it launched; tests set `PYTHONTK_CACHE_ROOT` to a temp folder so they see no other record): never attach to a Painter you did not launch, never kill one, never run a test or an MCP call against a person's: an open Painter can hold hours of unsaved work.

## Structure

Each app is a self-contained subpackage:

```
extapps/<app>/
  __init__.py   # DEFAULT_INCLUDE: launcher -> <App>UI, slots -> <App>Slots (+ its engine)
  <app>.ui      # Qt Designer file; its stem is the entry-point name users' settings live under
  slots.py      # the Slots class: a plain class, or uitk's ParamPanelSlots (uitk names from `uitk`)
  launcher.py   # <App>UI, a `_panel_launcher.PanelLauncher` (data only)
```

Apps sharing a domain layer group under an umbrella (docstring-only
`__init__.py`): `texture_maps/` (compositor / converter / packer) and
`photogrammetry/` (metashape / realityscan / gaussian_splat + the CLI-only sugar_mesh,
sharing `Profile` / `WorkflowEngine` / `PrepStagesMixin` / `_panel_slots` /
`_process_runner` / `_shared_params` and `presets/`; app discovery is one chain,
`Profile.resolve_app`). Behaviour lives on classes; config data stays flat (an
app's `parameters.py`: `PARAMS` + a `uitk.ParamRegistry`). Exempt: `@register`
ops and `run_combined`. The root re-exports every app's UI + Slots pair
(`test_imports.py`); `<app>_ui.py` are gitignored uitk compile caches.

`substance_scripts` holds the vendored Painter engine (`_substance_engine.py`, `connection.py`, `parameters.py`, the built-in scripts in `templates/` and the `substance_rpc` plugin) and `SubstanceScripts`, its host-free door: a script on a mesh runs on the panel's Mesh File, and the rows only a host fills (`HOST_ROWS`) are hidden.
`marmoset_scripts` holds the vendored Toolbag engine and `MarmosetScripts`, its door; it lists the engine's scripts, bundled and the person's own, but for one that reads a host's scene (`HOST_ROWS`: the bake's Bake Source).

## Run

`python -m extapps [app]` (or the `extapps` gui-script); `--shortcut
desktop|start_menu` writes a launcher. `__main__.py` only declares `HUB` (a
`uitk.ExternalAppHub`). Usage: [docs](docs/README.md#launch-standalone). In Maya
and Blender, tentacle's menus open the apps by name. After editing
`pyproject.toml` entry points, refresh an editable install's metadata
(`pip install -e .`) so `ExternalAppHandler` reads the new table.

## Run tests

```powershell
& python test/run_tests.py webxr_preview_panel -k scope   # pointed (from extapps/)
& python test/run_tests.py                                # full: review / release
```

Live-DCC tests (a real, new, never-attached Painter / Metashape) are opt-in:

```powershell
$env:EXTAPPS_PAINTER_LIVE = '1'                 # live Substance Painter pass (an owned hidden Painter)
$env:METASHAPE_RUN_INTEGRATION = '1'            # live Metashape pipeline test
```

See [CHANGELOG.md](CHANGELOG.md) for history.
