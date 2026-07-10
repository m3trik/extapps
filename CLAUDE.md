# extapps

**Role**: Standalone Switchboard panels for content-pipeline workflows. Each app is a uitk external app discovered via the `uitk.external_apps.in_process` entry-point group.

**Nav**: [← root](../CLAUDE.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · **Used by**: [tentacle](../tentacle/CLAUDE.md) (via ExternalAppHandler discovery)

## API surface

**Before adding a helper, check the registry** (navigation rules: [root](../CLAUDE.md)):

- [`API_INDEX.md`](API_INDEX.md) (compact — read first) · [`API_REGISTRY.md`](API_REGISTRY.md) (grep, don't Read whole) · [`API_CHANGES.md`](API_CHANGES.md)
- Upstream: [pythontk](../pythontk/API_INDEX.md) · [uitk](../uitk/API_INDEX.md)
- Cross-package shadows: [`m3trik/docs/API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md)

This is the package-level public API. `substance_workflow`'s internal `registry.py` op registry (below) is a separate thing.

## Scope

Tools that belong here:
- Standalone Switchboard panels.
- Depend on `pythontk` for domain logic and `uitk` for UI.
- DCC-agnostic (run from any host that loads uitk).

Tools that do NOT belong here:
- CLI-only utilities → `m3trik/scripts/`.
- Full applications with their own release cadence and distribution model → own repo.
- Library code that doesn't ship a UI panel → `pythontk` or another upstream package.

## Hard rules

- **All apps register via `uitk.external_apps.in_process` entry points.** No host (tentacle, mayatk, etc.) directly imports an app's slot class. Hosts launch apps through uitk's `ExternalAppHandler`.
- **Engine / domain logic lives in `pythontk`.** Slot classes here only do UI wiring + dispatch. **Exception**: *SDK-specific* engines that are not generally reusable stay bundled with their panel (`metashape_workflow._metashape_workflow` for the Metashape SDK; `substance_workflow`'s op registry + `PainterConnection` + bridge plugin for the Painter API; `marmoset_workflow._marmoset_engine` + `templates/` + `_toolbag_helpers` for Marmoset Toolbag). Generic carve-outs still go upstream to `pythontk`. A bundled engine that *also* has a Maya consumer is vendored into both layers (mayatk can't import extapps and vice-versa) — `marmoset_workflow`'s engine is kept byte-identical to `mayatk.mat_utils.marmoset_bridge`'s copy.

### Painter session safety — HARD BLOCK (protect user work)

`substance_workflow`'s `PainterConnection.connect()` defaults to `force_new_instance=True`: every connection launches a **fresh** Painter on an unused port; the user's open session is never touched. `force_new_instance=False` is **rejected**.

**AI agent rule**: never bypass `force_new_instance`. Never kill a Painter process you did not launch. Never attach to a live command port. Connecting to an open Painter can lose hours of unsaved work. Process spawn/teardown routes through `pythontk.AppLauncher` — do not bypass with raw `subprocess`.

## Structure

Each tool is a self-contained subpackage:

```
extapps/<tool>/
  __init__.py          # exposes <Tool>UI as the entry point
  slots.py             # Switchboard slot class
  <tool>.ui            # Qt Designer file
  launcher.py          # <Tool>UI class (Switchboard wiring)
```

`substance_workflow` additionally bundles its Painter engine: `registry.py`
(`@register` — the SSoT for callable ops; check it before adding a helper),
`*_utils.py` op modules (lazy-import `substance_painter` inside function bodies
so they stay import-safe outside Painter), `env_utils/` (`PainterConnection`,
`PainterFinder`), `job.py` (`run_batch`), and `plugins/substance_workflow_bridge/`
— the in-Painter JSON-RPC server, loaded via `SUBSTANCE_PAINTER_PLUGINS_PATH`.

## Run

Direct launch:

```powershell
python -c "from extapps.texture_maps.compositor import CompositorUI; CompositorUI().show(pos='screen', app_exec=True)"
python -c "from extapps.substance_workflow import SubstanceWorkflowUI; SubstanceWorkflowUI().show(pos='screen', app_exec=True)"
```

Via tentacle / mayatk: tools auto-discover through their entry-point group.
After editing `pyproject.toml` entry points, reinstall (`pip install -e .`) so
new entries surface in the package metadata `ExternalAppHandler` reads.

## Run tests

```powershell
& python -m pytest o:\Cloud\Code\_scripts\extapps\test
```

Live-DCC integration tests are gated — they launch a real Painter / a real
(new, never-attached) Metashape, so they stay opt-in:

```powershell
$env:SUBSTANCE_WORKFLOW_RUN_INTEGRATION = '1'   # live Substance Painter tests
$env:METASHAPE_RUN_INTEGRATION = '1'            # live Metashape pipeline test
& python -m pytest o:\Cloud\Code\_scripts\extapps\test
```

See [CHANGELOG.md](CHANGELOG.md) for history.
