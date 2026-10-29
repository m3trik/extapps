# extapps

**Role**: The standalone-app toolkit: the engines of the standalone content-pipeline tools (photogrammetry, Substance Painter, Marmoset Toolbag, the Map Converter's rules). Their panels are tentacle's (`tcl_standalone.py`, `slots/tools/`); extapps holds logic only and declares no panel.

**Nav**: [← root](../CLAUDE.md) · [docs](docs/README.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · **Used by**: [tentacle](../tentacle/CLAUDE.md) (its standalone panels import the root names)

## API surface

[`API_INDEX.md`](API_INDEX.md) · [`API_REGISTRY.md`](API_REGISTRY.md) · [`API_CHANGES.md`](API_CHANGES.md) · shadows [`API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md) — registry rules in [root](../CLAUDE.md). Upstream: [pythontk](../pythontk/API_INDEX.md) · [uitk](../uitk/API_INDEX.md).

Package-level public API; `substance_workflow`'s internal `registry.py` op registry (below) is separate.

## Scope

Belongs here: an app- or SDK-specific engine a standalone tool drives (Metashape, RealityScan, Brush, Painter, Toolbag), DCC-agnostic, importable without Qt where it can be. Not here: a panel, a `.ui` or a Slots class (tentacle's `ui/tools/`, `slots/tools/`); CLI-only utilities (`m3trik/scripts/`); a generic primitive (`pythontk`).

## Hard rules

- **No panel, no tentacle import.** The panels (and their entry points, hub and tests) are tentacle's; a name that moved there is in the root `MOVED_NAMES`. tentacle's Slots reach the engines through the root (`extapps.Profile`, `extapps.PainterConnection`, ...), never a `_` module, so a name a panel needs is a root `DEFAULT_INCLUDE` entry.
- **Generic mechanism lives in `pythontk`; app-specific engines live with their consumers.** pythontk is **app-agnostic** — it ships the generic mechanism (`HandoffBridge`, `AppLauncher`, `RpcClient`, `process_stream`) and the pure *domain* cores (`core_utils/engines/`: shots, instancing, textures), never product SDK glue. So *app/SDK-specific* engines stay bundled with their consumer (`metashape_workflow._metashape_workflow` for the Metashape SDK; `substance_workflow`'s op registry + `PainterConnection` + bridge plugin for the Painter API — a native in-Painter plugin, distinct from the mayatk/blendertk `substance_bridge`; `marmoset_workflow._marmoset_engine` + `templates/` + `_toolbag_helpers` for Marmoset Toolbag). Generic carve-outs still go upstream to `pythontk`. An app engine that *also* has DCC consumers is vendored into each layer (none can import the others): `marmoset_workflow`'s engine is kept byte-identical to `mayatk.mat_utils.marmoset_bridge`'s copy, enforced by `test/test_vendor_sync.py` (also the mayatk↔blendertk Marmoset/Substance copies).

### Painter session safety — HARD BLOCK (protect user work)

`substance_workflow`'s `PainterConnection.connect()` defaults to `force_new_instance=True`: every connection launches a **fresh** Painter on an unused port; the user's open session is never touched. `force_new_instance=False` is **rejected**.

**AI agent rule**: never bypass `force_new_instance`. Never kill a Painter process you did not launch. Never attach to a live command port. Connecting to an open Painter can lose hours of unsaved work. Process spawn/teardown routes through `pythontk.AppLauncher` — do not bypass with raw `subprocess`.

## Structure

Each engine is a subpackage; engines that share a domain layer group under an umbrella
(docstring-only `__init__.py`): `photogrammetry/` (metashape / realityscan /
gaussian_splat + the CLI-only, experimental sugar_mesh — sharing `Profile` /
`WorkflowEngine` / `PrepStagesMixin` / `_process_runner` and `presets/`) and
`texture_maps/` (the converter's `MapConverter`). Discovery is one chain,
`Profile.resolve_app`: terminal env override (set-but-invalid ⇒ mock), `apps.<key>`,
the engine's `AppSpec`, fallbacks. Behaviour lives on classes (helpers on
`_<Class>Internal`); config data stays flat. Exempt: `@register` ops and
`run_combined` (read as *module* attrs).

`substance_workflow` bundles its Painter engine: `registry.py`
(`@register` — the SSoT for callable ops; check it before adding a helper),
`*_utils.py` op modules (lazy-import `substance_painter` inside function bodies
so they stay import-safe outside Painter), `env_utils/` (`PainterConnection`,
`PainterFinder`), `job.py` (`run_batch`), and `plugins/startup/substance_workflow_bridge/`
(a startup module of the root on `SUBSTANCE_PAINTER_PLUGINS_PATH`), all on pythontk's RPC pair.
`marmoset_workflow` holds the vendored Toolbag engine and `MarmosetWorkflow`, its door.

## Run

The panels run from tentacle (`python -m tentacle [panel]`). `python -m extapps
[panel]` (the `extapps` gui-script) is kept for launchers made before they moved:
`__main__.py` declares a `uitk.ExternalAppHub` naming tentacle (`tentacletk`) as the
panels' provider -- data, never an import -- so it reads tentacle's table from an install
or a checkout and installs it where missing. Usage: [docs](docs/README.md#launch-the-panels).

## Run tests

```powershell
& python test/run_tests.py photogrammetry_profile -k preset   # pointed (from extapps/)
& python test/run_tests.py                                    # full: review / release
```

The panels' tests are tentacle's (`tentacle/test/test_<tool>_panel.py`).

Live-DCC tests (a real, new, never-attached Painter / Metashape) are opt-in:

```powershell
$env:SUBSTANCE_WORKFLOW_RUN_INTEGRATION = '1'   # live Substance Painter tests
$env:METASHAPE_RUN_INTEGRATION = '1'            # live Metashape pipeline test
```

See [CHANGELOG.md](CHANGELOG.md) for history.
