# Substance Workflow

Adobe Substance 3D Painter automation as a Switchboard panel + headless engine.

## What it is

`substance_workflow` drives Painter over a JSON-RPC bridge. An in-Painter plugin
(`plugins/substance_workflow_bridge`) loads the op **registry** and serves it over
HTTP; the client side (`PainterConnection`, `Job.run_batch`) launches a fresh Painter
and invokes ops by name.

- **`SubstanceWorkflowUI`** — the Switchboard panel. Set a mesh and/or project
  save path, pick which Painter to launch, choose stages (open/create → bake
  lighting→diffuse → save → export), tune advanced bake parameters, and Run.
- **`PainterConnection`** — agent/session client: `connect()` then
  `invoke("project.info", ...)`.
- **`Job.run_batch([Call(...), ...])`** — one-shot pipelines (launch → run → shut down).

## Session safety (hard rule)

Every connection launches a **new** Painter instance on an unused port
(`force_new_instance=True`, hard-coded — `False` is rejected). Your open Painter
session is never touched. Process control routes through `pythontk.AppLauncher`.

## Op registry — single source of truth

`@register("ns.name")` in `registry.py` is the SSoT for callable ops. Op modules
(`project_utils`, `bake_utils`, …) lazy-import `substance_painter` inside function
bodies so they stay import-safe outside Painter (tests, registry inspection).
Check the registry before adding a helper.

## Run

```powershell
# UI panel
python -c "from extapps.substance_workflow import SubstanceWorkflowUI; SubstanceWorkflowUI().show(pos='screen', app_exec=True)"
```

```python
# Batch
from extapps.substance_workflow import Call, Job
results = Job.run_batch([
    Call("project.create", kwargs={"mesh_path": "/path/mesh.fbx"}),
    Call("bake.lighting_to_diffuse", kwargs={"bake_resolution": 2048}),
    Call("project.save_as", kwargs={"path": "/path/out.spp"}),
])
```

## Tests

```powershell
& python -m pytest o:\Cloud\Code\_scripts\extapps\test
# live-Painter integration (opt-in — launches a real Painter):
$env:SUBSTANCE_WORKFLOW_RUN_INTEGRATION = '1'
& python -m pytest o:\Cloud\Code\_scripts\extapps\test
```

## Known gaps (verify before relying on)

- Many ops beyond `project.*` and `bake.lighting_to_diffuse` are stubs
  (`NotImplementedError`) — `export.*`, `bake.mesh_maps`, etc.
- Headless flag (`--no-display`) and Painter's Qt binding for main-thread
  dispatch are unverified against the installed Painter version. The in-Painter
  bridge path has not yet been validated end-to-end in a live Painter.
