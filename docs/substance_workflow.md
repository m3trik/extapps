# Substance Workflow

Adobe Substance 3D Painter automation: a headless engine here, and its panel in tentacle.

## What it is

`substance_workflow` drives Painter over a JSON-RPC bridge. An in-Painter plugin
(`plugins/startup/substance_workflow_bridge` -- a Painter *startup* module of the plugin
root the launch puts on `SUBSTANCE_PAINTER_PLUGINS_PATH`, so Painter always starts it)
loads the op **registry** and serves it over
HTTP; the client side (`PainterConnection`, `Job.run_batch`) launches a fresh Painter
and invokes ops by name. The RPC is pythontk's shared pair, not a private stack: the
registry is a `pythontk.RpcPlugin` (op table + main-thread marshaller + server), the
client a `pythontk.RpcClient`, the batch loop `pythontk.RpcJob` over `pythontk.Call` /
`pythontk.Result`, and `describe` returns the shared `{name, doc, params}` shape.

- **The Substance Workflow panel** — tentacle's (`SubstanceWorkflowUI`, `tentacle substance_workflow`). Set a mesh and/or project
  save path, pick which Painter to launch, choose stages (open/create → bake
  lighting→diffuse → save → export), tune advanced bake parameters, and Run.
  The stages run one at a time in the background, so the panel and its host stay
  responsive; Run reads **Cancel** while they run (holding Esc on the footer does
  the same), and a cancel stops before the next stage — an op Painter is already
  running (a bake) finishes first.
- **`PainterConnection`** — agent/session client: `connect()` then
  `invoke("project.info", ...)`.
- **`Job.run_batch([ptk.Call(...), ...])`** — one-shot pipelines (launch → run → shut down).

## Session safety (hard rule)

Every connection launches a **new** Painter instance on an unused port
(`force_new_instance=True`, hard-coded — `False` is rejected). Your open Painter
session is never touched. Process control routes through `pythontk.AppLauncher`.

## Op registry — single source of truth

`@register("ns.name")` in `registry.py` is the SSoT for callable ops (a duplicate
name raises). Op modules
(`project_utils`, `bake_utils`, …) lazy-import `substance_painter` inside function
bodies so they stay import-safe outside Painter (tests, registry inspection).
Check the registry before adding a helper.

## Run

```powershell
# UI panel (tentacle's)
tentacle substance_workflow
```

```python
# Batch
from pythontk import Call
from extapps.substance_workflow import Job
results = Job.run_batch([
    Call("project.create", kwargs={"mesh_path": "/path/mesh.fbx"}),
    Call("bake.lighting_to_diffuse", kwargs={"bake_resolution": 2048}),
    Call("project.save_as", kwargs={"path": "/path/out.spp"}),
])
```

## Tests

```powershell
& python -m pytest test                                 # from the extapps/ root (the engine)
& python tentacle/test/run_tests.py substance_workflow_panel   # the panel
# live-Painter integration (opt-in — launches a real Painter):
$env:SUBSTANCE_WORKFLOW_RUN_INTEGRATION = '1'
& python -m pytest test
```

## Known gaps (verify before relying on)

- Many ops beyond `project.*` and `bake.lighting_to_diffuse` are stubs
  (`NotImplementedError`) — `export.*`, `bake.mesh_maps`, etc.
- Painter has no headless option: `gui=False` (the `Job.run_batch` default) runs
  it on Qt's offscreen platform, with no window. Verified end-to-end in fresh
  Painters (2026-10-19), windowed and offscreen alike: the bridge starts,
  `project.create`, `bake.lighting_to_diffuse` (AO baked, its layer added) and
  `project.save_as` run. Only `project.*` and `bake.lighting_to_diffuse` have been
  run live.
