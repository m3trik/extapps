# extapps

**Role**: The standalone product: the host-free content-pipeline apps, each app's engine, panel (`.ui`) and Slots class together, on pythontk and uitk alone. Each is a uitk external app (`uitk.external_apps.in_process` entry points); tentacle's DCC menus open one BY NAME through uitk's `ExternalAppHandler`. Nothing imports extapps.

**Nav**: [← root](../CLAUDE.md) · [docs](docs/README.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · [unitytk](../unitytk/CLAUDE.md) (optional, `[unity]` extra; the Unity panel installs it on demand) · **Opened by**: [tentacle](../tentacle/CLAUDE.md) (by name, never an import)

## API surface

[`API_INDEX.md`](API_INDEX.md) · [`API_REGISTRY.md`](API_REGISTRY.md) · [`API_CHANGES.md`](API_CHANGES.md) · shadows [`API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md) — registry rules in [root](../CLAUDE.md). Upstream: [pythontk](../pythontk/API_INDEX.md) · [uitk](../uitk/API_INDEX.md) · [unitytk](../unitytk/API_INDEX.md) (optional).

Package-level public API; `substance_workflow`'s internal `registry.py` op registry (below) is separate.

## Scope

Belongs here: a host-free app -- no host half, needing no DCC to run (a host may open it in process and inject behaviour) -- whole: its app- or SDK-specific engine (Metashape, RealityScan, Brush, Painter, Toolbag), its `.ui`, Slots class and launcher. Not here: a tool with a host half, or one that needs a DCC to run (tentacle's panel over mayatk / blendertk); CLI-only utilities (`m3trik/scripts/`); a generic primitive (`pythontk`; generic Qt: `uitk`).

## Hard rules

- **No host and no tentacle import.** No module imports `maya`, `bpy`, `mayatk`, `blendertk` or `tentacle` (`test/test_imports.py`), and nothing imports extapps (`check_layers.py`: the product role). A host reaches an app only through uitk's `ExternalAppHandler`, by its entry-point name, and hands it context on the window it gets back (`launch(name, show=False)`, then a source folder, scopes, an `engine`).
- **Generic mechanism lives in `pythontk`; app-specific engines live with their apps.** pythontk is **app-agnostic** (`HandoffBridge`, `AppLauncher`, `RpcClient`, `process_stream`, the pure domain cores), never product SDK glue, so an SDK-specific engine stays with its app (`metashape_workflow._metashape_workflow`; `substance_workflow`'s op registry + `PainterConnection` + in-Painter plugin, distinct from the hosts' `substance_bridge`; `marmoset_workflow._marmoset_engine` + `templates/`). Code that *also* has DCC consumers is vendored, byte-identical, guarded by `test/test_vendor_sync.py`: the Marmoset engine (mayatk's the SSoT) and, until tentacle's Unity Bridge panel moves, `unity_workflow/_unity_panel.py` (tentacle's the SSoT).

### Painter session safety — HARD BLOCK (protect user work)

`substance_workflow`'s `PainterConnection.connect()` defaults to `force_new_instance=True`: every connection launches a **fresh** Painter on an unused port; the user's open session is never touched. `force_new_instance=False` is **rejected**.

**AI agent rule**: never bypass `force_new_instance`. Never kill a Painter process you did not launch. Never attach to a live command port. Connecting to an open Painter can lose hours of unsaved work. Process spawn/teardown routes through `pythontk.AppLauncher` — do not bypass with raw `subprocess`.

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

`substance_workflow` bundles its Painter engine: `registry.py`
(`@register` — the SSoT for callable ops; check it before adding a helper),
`*_utils.py` op modules (lazy-import `substance_painter` inside function bodies
so they stay import-safe outside Painter), `env_utils/` (`PainterConnection`,
`PainterFinder`), `job.py` (`run_batch`), and `plugins/startup/substance_workflow_bridge/`
(a startup module of the root on `SUBSTANCE_PAINTER_PLUGINS_PATH`), all on pythontk's RPC pair.
`marmoset_workflow` holds the vendored Toolbag engine and `MarmosetWorkflow`, its door.

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
$env:SUBSTANCE_WORKFLOW_RUN_INTEGRATION = '1'   # live Substance Painter tests
$env:METASHAPE_RUN_INTEGRATION = '1'            # live Metashape pipeline test
```

See [CHANGELOG.md](CHANGELOG.md) for history.
