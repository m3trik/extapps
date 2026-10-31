# extapps — API Registry

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_api_registry.py`._

## Index

- [`__init__.py`](#__init__) — extapps — the engines of the standalone content-pipeline tools.
- [`marmoset_workflow/__init__.py`](#marmoset_workflow--__init__) — Launch Marmoset Toolbag and set up an import or lookdev scene from a model file.
- [`marmoset_workflow/_marmoset_engine.py`](#marmoset_workflow--_marmoset_engine) — Drive Marmoset Toolbag from the outside -- launch + templated automation.
- [`marmoset_workflow/_marmoset_workflow.py`](#marmoset_workflow--_marmoset_workflow) — The Toolbag engine as the standalone Marmoset Workflow panel drives it.
- [`marmoset_workflow/_toolbag_helpers.py`](#marmoset_workflow--_toolbag_helpers) — Shared helpers for Marmoset Toolbag template scripts.
- [`marmoset_workflow/template_params.py`](#marmoset_workflow--template_params) — Plain default values + literal formatting for Marmoset template tokens.
- [`marmoset_workflow/templates/import.py`](#marmoset_workflow--templates--import) — Open the model in Toolbag and wire materials from the manifest.
- [`marmoset_workflow/templates/lookdev.py`](#marmoset_workflow--templates--lookdev) — Open the model in Toolbag, apply a Sky preset, and frame the model.
- [`marmoset_workflow/toolbag_log.py`](#marmoset_workflow--toolbag_log) — Marmoset Toolbag log-file resolution, classification, and live tailing.
- [`photogrammetry/_process_runner.py`](#photogrammetry--_process_runner) — Async, log-streaming process runner shared by the photogrammetry panels.
- [`photogrammetry/_progress_notify.py`](#photogrammetry--_progress_notify) — The one progress-notify shim the photogrammetry engines share.
- [`photogrammetry/_workflow_engine.py`](#photogrammetry--_workflow_engine) — The lifecycle every photogrammetry engine shares: one base, five engines.
- [`photogrammetry/gaussian_splat_workflow/__init__.py`](#photogrammetry--gaussian_splat_workflow--__init__) — Train a Gaussian splat with Brush from COLMAP data and export it for Unity or web.
- [`photogrammetry/gaussian_splat_workflow/_gaussian_splat_runner.py`](#photogrammetry--gaussian_splat_workflow--_gaussian_splat_runner) — Local, async runner the Brush (gaussian-splat) panel dispatches to.
- [`photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py`](#photogrammetry--gaussian_splat_workflow--_gaussian_splat_workflow) — Brush gaussian-splat workflow engine.
- [`photogrammetry/gaussian_splat_workflow/_install_brush.py`](#photogrammetry--gaussian_splat_workflow--_install_brush) — Headless entry point: download + install Brush via pythontk.AppInstaller.
- [`photogrammetry/gaussian_splat_workflow/_splat_publish.py`](#photogrammetry--gaussian_splat_workflow--_splat_publish) — Engine-delivery stage for the splat track — clean + convert to engine formats.
- [`photogrammetry/gaussian_splat_workflow/run_combined.py`](#photogrammetry--gaussian_splat_workflow--run_combined) — Driver for the gaussian-splat track: Brush splat training + engine publish.
- [`photogrammetry/mesh_stages.py`](#photogrammetry--mesh_stages) — Shared, SDK-agnostic mesh post-processing stages (PyMeshLab-backed).
- [`photogrammetry/metashape_workflow/__init__.py`](#photogrammetry--metashape_workflow--__init__) — Turn photos or video frames into a textured mesh with headless Metashape.
- [`photogrammetry/metashape_workflow/_metashape_connection.py`](#photogrammetry--metashape_workflow--_metashape_connection) — Headless launch connection for Agisoft Metashape.
- [`photogrammetry/metashape_workflow/_metashape_runner.py`](#photogrammetry--metashape_workflow--_metashape_runner) — Local, async runner the Metashape panel dispatches to.
- [`photogrammetry/metashape_workflow/_metashape_workflow.py`](#photogrammetry--metashape_workflow--_metashape_workflow)
- [`photogrammetry/metashape_workflow/run_combined.py`](#photogrammetry--metashape_workflow--run_combined) — Driver script for multi-session combined runs.
- [`photogrammetry/prep_stages.py`](#photogrammetry--prep_stages) — Shared, SDK-agnostic pipeline stages for the photogrammetry engines.
- [`photogrammetry/profile.py`](#photogrammetry--profile) — Photogrammetry I/O + tuning **profile** — site/personal config kept out of source.
- [`photogrammetry/realityscan_workflow/__init__.py`](#photogrammetry--realityscan_workflow--__init__) — Turn photos or video frames into a textured mesh with headless RealityCapture.
- [`photogrammetry/realityscan_workflow/_realityscan_connection.py`](#photogrammetry--realityscan_workflow--_realityscan_connection) — Launch connection for RealityScan / RealityCapture.
- [`photogrammetry/realityscan_workflow/_realityscan_runner.py`](#photogrammetry--realityscan_workflow--_realityscan_runner) — Local, async runner the RealityCapture panel dispatches to.
- [`photogrammetry/realityscan_workflow/_realityscan_workflow.py`](#photogrammetry--realityscan_workflow--_realityscan_workflow) — RealityCapture / RealityScan workflow engine.
- [`photogrammetry/realityscan_workflow/_rsnode_client.py`](#photogrammetry--realityscan_workflow--_rsnode_client) — RSNode REST client — drive a running RealityScan 2.1 over its REST API (headless).
- [`photogrammetry/realityscan_workflow/_rsnode_connection.py`](#photogrammetry--realityscan_workflow--_rsnode_connection) — RSNode-backed connection — drive a running RealityScan 2.1 over REST.
- [`photogrammetry/realityscan_workflow/run_combined.py`](#photogrammetry--realityscan_workflow--run_combined) — Driver script for multi-session combined RealityCapture runs.
- [`photogrammetry/sugar_mesh_workflow/_sugar_mesh.py`](#photogrammetry--sugar_mesh_workflow--_sugar_mesh) — SuGaR mesh-extraction workflow engine.
- [`photogrammetry/sugar_mesh_workflow/run_combined.py`](#photogrammetry--sugar_mesh_workflow--run_combined) — Driver for the **EXPERIMENTAL** SuGaR mesh track: COLMAP dataset → textured ``.obj``.
- [`substance_workflow/__init__.py`](#substance_workflow--__init__) — Create a Substance Painter project from a mesh and bake lighting into base color.
- [`substance_workflow/bake_utils.py`](#substance_workflow--bake_utils) — Bake operations — iray-backed mesh-map bakes and lighting composites.
- [`substance_workflow/channel_utils.py`](#substance_workflow--channel_utils) — Channel operations — query and modify per-channel state on a texture set.
- [`substance_workflow/env_utils/painter_connection.py`](#substance_workflow--env_utils--painter_connection) — Painter Connection Module.
- [`substance_workflow/env_utils/painter_finder.py`](#substance_workflow--env_utils--painter_finder) — Locate installed Substance 3D Painter.
- [`substance_workflow/export_utils.py`](#substance_workflow--export_utils) — Texture export operations — drive ``substance_painter.export``.
- [`substance_workflow/job.py`](#substance_workflow--job) — Batch convenience: launch Painter, run a call list over the bridge, shut down.
- [`substance_workflow/layer_utils.py`](#substance_workflow--layer_utils) — Layer stack operations — list, add, remove, reorder, set properties.
- [`substance_workflow/material_utils.py`](#substance_workflow--material_utils) — Smart-material / preset operations — apply shelf materials onto layers.
- [`substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py`](#substance_workflow--plugins--startup--substance_workflow_bridge--__init__) — substance_workflow_bridge — Painter-side Python plugin.
- [`substance_workflow/project_utils.py`](#substance_workflow--project_utils) — Project-level operations — open, save, close, info, mesh swap.
- [`substance_workflow/registry.py`](#substance_workflow--registry) — Op registry — the callable Painter surface, on the shared RPC core.
- [`substance_workflow/resource_utils.py`](#substance_workflow--resource_utils) — Shelf / resource operations — query and import shelf assets.
- [`substance_workflow/texture_set_utils.py`](#substance_workflow--texture_set_utils) — Texture set operations — list, resolution, channel inventory.
- [`texture_maps/converter/__init__.py`](#texture_maps--converter--__init__) — The Map Converter's batch rules: plan, name and run one map at a time.
- [`texture_maps/converter/_converter.py`](#texture_maps--converter--_converter) — The Map Converter's batch engine: plan, name and run one map at a time.

---

<a id="__init__"></a>
### `__init__.py`

extapps — the engines of the standalone content-pipeline tools.

- [`DOCS_BASE_URL`](extapps/extapps/__init__.py#L25) — constant
- [`DEFAULT_INCLUDE`](extapps/extapps/__init__.py#L28) — constant
- [`MOVED_NAMES`](extapps/extapps/__init__.py#L51) — constant

<a id="marmoset_workflow--__init__"></a>
### `marmoset_workflow/__init__.py`

Launch Marmoset Toolbag and set up an import or lookdev scene from a model file.

- [`DEFAULT_INCLUDE`](extapps/extapps/marmoset_workflow/__init__.py#L19) — constant

<a id="marmoset_workflow--_marmoset_engine"></a>
### `marmoset_workflow/_marmoset_engine.py`

Drive Marmoset Toolbag from the outside -- launch + templated automation.

- [`APP`](extapps/extapps/marmoset_workflow/_marmoset_engine.py#L45) — constant
- [`SEND_TO`](extapps/extapps/marmoset_workflow/_marmoset_engine.py#L64) — constant
- [`ROUND_TRIP`](extapps/extapps/marmoset_workflow/_marmoset_engine.py#L65) — constant
- **[`class MarmosetEngine(pythontk.Deliverer, pythontk.LoggingMixin)`](extapps/extapps/marmoset_workflow/_marmoset_engine.py#L76)** — Export-agnostic Marmoset Toolbag automation -- a hand-off :class:`pythontk.Deliverer`.
  - `MarmosetEngine.toolbag_path(self) -> Optional[str]` *(property)* — Resolve the Toolbag executable path.
  - `MarmosetEngine.toolbag_log_path(self) -> Optional[str]` *(property)* — Resolve Toolbag's application log file (script prints + tracebacks).
  - `MarmosetEngine.preflight(self, bridge, request) -> bool` — Validate the (template, mode) before the bridge produces its payload.
  - `MarmosetEngine.deliver(self, bridge, payload, request) -> Optional[Dict[str, Any]]` — Hand the produced model + manifests to Toolbag via :meth:`send`.
  - `MarmosetEngine.send(self, model_path: str, manifest_path: Optional[str] = None, pairs_path: Optional[str] = None, source_model_path: Optional[str] = None, output_dir: Optional[str] = None, texture_dir: Optional[str] = None, texture_set_aliases: Optional[Dict[str, str]] = None, output_name: Optional[str] = None, toolbag_exe: Optional[str] = None, template: str = 'import', mode: str = SEND_TO, params: Optional[Dict[str, Any]] = None, scene_dir: Optional[str] = None) -> Optional[Dict[str, Any]]` — Render *template* in *mode* against *model_path* and hand off to Toolbag.
  - `MarmosetEngine.render_template(self, template: str, model_path: str, manifest_path: str, output_dir: str, mode: str = SEND_TO, params: Optional[Dict[str, Any]] = None, headless: Optional[bool] = None, pairs_path: Optional[str] = None, source_model_path: Optional[str] = None, save_dir: Optional[str] = None) -> Optional[str]` — Return the rendered Toolbag Python script body, or *None* on miss.
  - `MarmosetEngine.list_templates() -> List[Path]` *(static)* — Return user-visible templates in ``templates/`` (skips underscore-prefixed).
  - `MarmosetEngine.template_modes(template_path: Path) -> Tuple[str, ...]` *(static)* — Return the modes declared by *template_path*'s ``BRIDGE_MODES`` constant.
  - `MarmosetEngine.list_template_modes() -> List[Tuple[str, str]]` *(static)* — Return ``[(stem, mode), ...]`` for every (template, mode) pairing.

<a id="marmoset_workflow--_marmoset_workflow"></a>
### `marmoset_workflow/_marmoset_workflow.py`

The Toolbag engine as the standalone Marmoset Workflow panel drives it.

- **[`class MarmosetWorkflow(MarmosetEngine)`](extapps/extapps/marmoset_workflow/_marmoset_workflow.py#L15)** — The Toolbag engine with its app and template folder on the class.

<a id="marmoset_workflow--_toolbag_helpers"></a>
### `marmoset_workflow/_toolbag_helpers.py`

Shared helpers for Marmoset Toolbag template scripts.

- [`SLOT_MAP`](extapps/extapps/marmoset_workflow/_toolbag_helpers.py#L656) — constant
- [`MODULE_NEUTRAL_FIELDS`](extapps/extapps/marmoset_workflow/_toolbag_helpers.py#L679) — constant
- [`SUBROUTINE_FIXES`](extapps/extapps/marmoset_workflow/_toolbag_helpers.py#L692) — constant
- **[`class ToolbagHelpers(_ToolbagHelpersInternal)`](extapps/extapps/marmoset_workflow/_toolbag_helpers.py#L200)** — ToolbagHelpers — module namespace.
  - `ToolbagHelpers.derive_per_run_log_path(manifest_path)` *(static)* — Return the ``<base>.toolbag.log`` path next to *manifest_path*.
  - `ToolbagHelpers.begin_log(reference_path)` *(static)* — Start a fresh log file alongside *reference_path*.
  - `ToolbagHelpers.log(msg)` *(static)* — Print *msg* and (best-effort) append it to the active log file.
  - `ToolbagHelpers.find_material(name, scene_mats)` *(static)* — Return the Toolbag material whose name matches *name*.
  - `ToolbagHelpers.load_manifest(manifest_path)` *(static)* — Return the ``materials`` dict from a MatManifest JSON sidecar.
  - `ToolbagHelpers.wire_materials_from_manifest(manifest_path, verbose=True, srgb_colors=True)` *(static)* — Wire every texture slot in *manifest_path* onto matching Toolbag mats.
  - `ToolbagHelpers.split_source_target(objects, high_suffix, low_suffix, pre_classified=None, include_children=True)` *(static)* — Group *objects* into ``(sources, targets, others)`` by name suffix.
  - `ToolbagHelpers.collect_mesh_objects(root)` *(static)* — Recursively gather ``mset.MeshObject`` descendants of *root*.
  - `ToolbagHelpers.apply_sky_preset(preset_path)` *(static)* — Load a ``.tbsky`` preset onto the scene's existing SkyObject.
  - `ToolbagHelpers.frame_in_viewport()` *(static)* — Frame the imported scene in the viewport (best-effort).

<a id="marmoset_workflow--template_params"></a>
### `marmoset_workflow/template_params.py`

Plain default values + literal formatting for Marmoset template tokens.

- [`DEFAULTS`](extapps/extapps/marmoset_workflow/template_params.py#L26) — constant
- **[`class TemplateParams`](extapps/extapps/marmoset_workflow/template_params.py#L101)** — TemplateParams — module namespace.
  - `TemplateParams.derive_auto_maps(manifest: Dict[str, Any]) -> Dict[str, bool]` *(static)* — Return the ``{MAP_*: bool}`` roster *manifest*'s textures imply.
  - `TemplateParams.derive_bake_values(values: Dict[str, Any]) -> Dict[str, Any]` *(static)* — Return the managed bake tokens derived from *values*.
  - `TemplateParams.python_literal(value: Any) -> str` *(static)* — Format *value* as a Python source literal for template substitution.
  - `TemplateParams.defaults() -> Dict[str, Any]` *(static)* — Return a copy of :data:`DEFAULTS`.
  - `TemplateParams.to_context(values: Dict[str, Any]) -> Dict[str, str]` *(static)* — Map ``{KEY: value}`` to ``{KEY: python-literal-string}``.

<a id="marmoset_workflow--templates--import"></a>
### `marmoset_workflow/templates/import.py`

Open the model in Toolbag and wire materials from the manifest.

- [`main()`](extapps/extapps/marmoset_workflow/templates/import.py#L35)
- [`BRIDGE_MODES`](extapps/extapps/marmoset_workflow/templates/import.py#L12) — constant
- [`MODEL_FILE`](extapps/extapps/marmoset_workflow/templates/import.py#L25) — constant
- [`MANIFEST_FILE`](extapps/extapps/marmoset_workflow/templates/import.py#L26) — constant
- [`SAVE_PATH`](extapps/extapps/marmoset_workflow/templates/import.py#L27) — constant
- [`SHOULD_QUIT`](extapps/extapps/marmoset_workflow/templates/import.py#L28) — constant

<a id="marmoset_workflow--templates--lookdev"></a>
### `marmoset_workflow/templates/lookdev.py`

Open the model in Toolbag, apply a Sky preset, and frame the model.

- [`main()`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L38)
- [`BRIDGE_MODES`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L12) — constant
- [`MODEL_FILE`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L25) — constant
- [`MANIFEST_FILE`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L26) — constant
- [`SAVE_PATH`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L27) — constant
- [`SHOULD_QUIT`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L28) — constant
- [`SKY_PRESET`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L30) — constant
- [`FRAME_SELECTION`](extapps/extapps/marmoset_workflow/templates/lookdev.py#L31) — constant

<a id="marmoset_workflow--toolbag_log"></a>
### `marmoset_workflow/toolbag_log.py`

Marmoset Toolbag log-file resolution, classification, and live tailing.

- **[`class ToolbagLog`](extapps/extapps/marmoset_workflow/toolbag_log.py#L30)** — ToolbagLog — module namespace.
  - `ToolbagLog.resolve_toolbag_log_path(toolbag_exe: Optional[str]) -> Optional[str]` *(static)* — Return the path to Toolbag's application log, robust to version bumps.
  - `ToolbagLog.classify_log_line(line: str) -> Optional[Tuple[str, str]]` *(static)* — Map a Toolbag log line to ``(level, line)`` for routing into a logger.
  - `ToolbagLog.dispatch_log_lines(lines, logger) -> None` *(static)* — Forward each classified line to *logger* at its routed level.
  - `ToolbagLog.start_toolbag_log_tail(log_path: str, start_offset: int, process, logger, poll_interval: float = 0.4, file_wait_timeout: float = 60.0)` *(static)* — Tail *log_path* from *start_offset* in a daemon thread.

<a id="photogrammetry--_process_runner"></a>
### `photogrammetry/_process_runner.py`

Async, log-streaming process runner shared by the photogrammetry panels.

- **[`class ProcessRunner(pythontk.LoggingMixin)`](extapps/extapps/photogrammetry/_process_runner.py#L42)** — Launch + asynchronously stream a child process into Qt callbacks.
  - `ProcessRunner.exe(self) -> Optional[str]` *(property)* — Path of the engine executable used (display / diagnostics).
  - `ProcessRunner.is_available(self) -> bool` — True when a real run is possible (the engine was discovered).
  - `ProcessRunner.is_running(self) -> bool` — True from launch until *on_done* has been delivered (the output tail
  - `ProcessRunner.start(self, argv: Sequence[str], on_line: Optional[Callable[[str], None]] = None, on_done: Optional[Callable[[int], None]] = None, cwd: Optional[str] = None) -> None` — Launch the engine command asynchronously.
  - `ProcessRunner.cancel(self) -> None` — Kill an in-flight run (no-op when idle).
- **[`class PyModuleRunner(ProcessRunner)`](extapps/extapps/photogrammetry/_process_runner.py#L221)** — ``ProcessRunner`` for engines whose headless driver is a normal-Python

<a id="photogrammetry--_progress_notify"></a>
### `photogrammetry/_progress_notify.py`

The one progress-notify shim the photogrammetry engines share.

- **[`class ProgressNotifyMixin`](extapps/extapps/photogrammetry/_progress_notify.py#L40)** — Supplies ``_notify`` to an engine that carries a ``progress`` callback.

<a id="photogrammetry--_workflow_engine"></a>
### `photogrammetry/_workflow_engine.py`

The lifecycle every photogrammetry engine shares: one base, five engines.

- **[`class WorkflowEngine(ProgressNotifyMixin)`](extapps/extapps/photogrammetry/_workflow_engine.py#L35)** — Run lifecycle shared by the photogrammetry engines.
  - `WorkflowEngine.finalize_run(self, success: bool = True) -> str` — Write the QC JSON sidecar and return its path.

<a id="photogrammetry--gaussian_splat_workflow--__init__"></a>
### `photogrammetry/gaussian_splat_workflow/__init__.py`

Train a Gaussian splat with Brush from COLMAP data and export it for Unity or web.

- [`DEFAULT_INCLUDE`](extapps/extapps/photogrammetry/gaussian_splat_workflow/__init__.py#L34) — constant

<a id="photogrammetry--gaussian_splat_workflow--_gaussian_splat_runner"></a>
### `photogrammetry/gaussian_splat_workflow/_gaussian_splat_runner.py`

Local, async runner the Brush (gaussian-splat) panel dispatches to.

- **[`class GaussianSplatRunner(PyModuleRunner)`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_runner.py#L21)** — Discover Brush + asynchronously drive its ``run_combined``.
  - `GaussianSplatRunner.exe(self) -> Optional[str]` *(property)*
  - `GaussianSplatRunner.is_available(self) -> bool` — True when a Brush executable was found (set BRUSH_EXE or install).
- **[`class BrushInstallRunner(PyModuleRunner)`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_runner.py#L41)** — Stream the Brush downloader (pythontk.AppInstaller) in a child process.
  - `BrushInstallRunner.exe(self) -> Optional[str]` *(property)*
  - `BrushInstallRunner.is_available(self) -> bool`

<a id="photogrammetry--gaussian_splat_workflow--_gaussian_splat_workflow"></a>
### `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py`

Brush gaussian-splat workflow engine.

- [`BRUSH_APP`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L35) — constant
- [`BRUSH_DOWNLOAD`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L43) — constant
- [`BRUSH_EXE_NAME`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L60) — constant
- **[`class GaussianSplatWorkflow(WorkflowEngine, _GaussianSplatWorkflowInternal)`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L96)** — Wrapper around Brush's CLI for COLMAP-dataset -> 3DGS ``.ply``.
  - `GaussianSplatWorkflow.find_brush_exe() -> Optional[str]` *(static)* — Return the Brush executable path or None.
  - `GaussianSplatWorkflow.is_brush_available() -> bool` *(static)*
  - `GaussianSplatWorkflow.install_brush(progress_callback: Optional[Callable[[int, int], None]] = None) -> str` *(static)* — Download + install Brush via :class:`pythontk.AppInstaller`;
  - `GaussianSplatWorkflow.read_splat_count(ply_path: str) -> Optional[int]` *(static)* — Gaussian count from a splat ``.ply`` header (``element vertex N``).
  - `GaussianSplatWorkflow.get_brush_info(self) -> str`
  - `GaussianSplatWorkflow.train(self, colmap_dir: str, total_steps: int = 30000, max_resolution: int = 1920, max_splats: int = 10000000, sh_degree: int = 3, growth_grad_threshold: Optional[float] = None, growth_select_fraction: Optional[float] = None, export_path: Optional[str] = None, export_name: Optional[str] = None, export_every: Optional[int] = None, eval_split_every: Optional[int] = None, eval_every: Optional[int] = None, eval_save_to_disk: bool = False) -> Optional[str]` — Train a splat from a COLMAP dataset;

<a id="photogrammetry--gaussian_splat_workflow--_install_brush"></a>
### `photogrammetry/gaussian_splat_workflow/_install_brush.py`

Headless entry point: download + install Brush via pythontk.AppInstaller.

- [`main() -> int`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_install_brush.py#L19)

<a id="photogrammetry--gaussian_splat_workflow--_splat_publish"></a>
### `photogrammetry/gaussian_splat_workflow/_splat_publish.py`

Engine-delivery stage for the splat track — clean + convert to engine formats.

- [`SPLAT_TRANSFORM_APP`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_splat_publish.py#L66) — constant
- **[`class SplatPublishWorkflow(WorkflowEngine, _SplatPublishWorkflowInternal)`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_splat_publish.py#L81)** — Clean a trained 3DGS ``.ply`` and convert it to engine-ready formats.
  - `SplatPublishWorkflow.find_splat_transform() -> 'Optional[str]'` *(static)* — Return the ``splat-transform`` executable path or None.
  - `SplatPublishWorkflow.is_splat_transform_available() -> bool` *(static)*
  - `SplatPublishWorkflow.get_publish_info(self) -> str`
  - `SplatPublishWorkflow.clean(self, in_ply: str, out_ply: Optional[str] = None, rotate: Optional[Union[str, Sequence[float]]] = None, filter_floaters: bool = True, filter_nan: bool = True, min_opacity: Optional[float] = None, crop_box: Optional[Union[str, Sequence[float]]] = None, crop_sphere: Optional[Union[str, Sequence[float]]] = None, decimate: Optional[Union[str, int]] = None) -> str` — Clean a trained splat ``.ply``;
  - `SplatPublishWorkflow.to_unity(self, clean_ply: str, out_path: Optional[str] = None, spz_version: int = 4) -> str` — Convert a (cleaned) ``.ply`` to Unity-ready ``.spz``;
  - `SplatPublishWorkflow.to_web(self, clean_ply: str, out_dir: Optional[str] = None, web_format: str = 'sog', with_viewer: bool = True) -> Dict[str, Optional[str]]` — Convert a (cleaned) ``.ply`` for the browser;
  - `SplatPublishWorkflow.publish(self, in_ply: str, targets: Sequence[str] = ('unity', 'web'), out_dir: Optional[str] = None, spz_version: int = 4, web_format: str = 'sog', with_viewer: bool = True, **clean_kwargs) -> Dict[str, object]` — Clean *in_ply* once, then emit each requested target from the result.

<a id="photogrammetry--gaussian_splat_workflow--run_combined"></a>
### `photogrammetry/gaussian_splat_workflow/run_combined.py`

Driver for the gaussian-splat track: Brush splat training + engine publish.

- [`main(argv=None) -> int`](extapps/extapps/photogrammetry/gaussian_splat_workflow/run_combined.py#L46)

<a id="photogrammetry--mesh_stages"></a>
### `photogrammetry/mesh_stages.py`

Shared, SDK-agnostic mesh post-processing stages (PyMeshLab-backed).

- **[`class MeshStagesMixin`](extapps/extapps/photogrammetry/mesh_stages.py#L33)** — Measure / refine / bake / repair stages shared by both photogrammetry engines.
  - `MeshStagesMixin.measure_mesh(self, model_path: Optional[str] = None) -> Optional[Dict[str, Any]]` — QC metrics for the exported mesh file, evaluated against the
  - `MeshStagesMixin.refine_mesh(self, model_path: Optional[str] = None, output_path: Optional[str] = None, remesh_target_pct: float = 0.0, decimate_target_faces: int = 0, curvature_weighted: bool = True, compare_deviation: bool = True) -> Optional[str]` — Isotropic remesh and/or curvature-weighted decimation on the
  - `MeshStagesMixin.bake_vertex_color(self, model_path: Optional[str] = None, output_path: Optional[str] = None, texture_size: int = 1024) -> Optional[Tuple[str, str]]` — Bake per-vertex color to a texture on auto-generated UVs
  - `MeshStagesMixin.run_mesh_stages(self, model_path: Optional[str] = None, remesh_target_pct: float = 0.0, decimate_target_faces: int = 0, bake_texture_size: int = 0) -> Optional[str]` — The file-level stages in pipeline order: repair → refine (when a
  - `MeshStagesMixin.clean_mesh_advanced(self, exported_model_path: Optional[str] = None, decimate_target_faces: int = 0) -> Optional[str]` — PyMeshLab repair pass on the exported mesh file (duplicate/close

<a id="photogrammetry--metashape_workflow--__init__"></a>
### `photogrammetry/metashape_workflow/__init__.py`

Turn photos or video frames into a textured mesh with headless Metashape.

- [`DEFAULT_INCLUDE`](extapps/extapps/photogrammetry/metashape_workflow/__init__.py#L16) — constant

<a id="photogrammetry--metashape_workflow--_metashape_connection"></a>
### `photogrammetry/metashape_workflow/_metashape_connection.py`

Headless launch connection for Agisoft Metashape.

- [`APP`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_connection.py#L36) — constant
- **[`class MetashapeConnection`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_connection.py#L51)** — Discover + headlessly drive ``metashape.exe -r <script>`` from any host.
  - `MetashapeConnection.find_exe() -> Optional[str]` *(static)* — Locate ``metashape.exe`` via the shared :func:`resolve_app` chain:
  - `MetashapeConnection.is_available(self) -> bool` — True if a metashape.exe was found (i.e.
  - `MetashapeConnection.run_script(self, script_path: str, args: Optional[Sequence[str]] = None, cwd: Optional[str] = None, timeout: Optional[float] = None, log_file: Optional[str] = None, env: Optional[dict] = None)` — Run a Python *script* inside Metashape headless via ``-r``.
  - `MetashapeConnection.run_combined(self, args: Optional[Sequence[str]] = None, **kwargs)` — Convenience: drive this package's ``run_combined`` workflow headless.

<a id="photogrammetry--metashape_workflow--_metashape_runner"></a>
### `photogrammetry/metashape_workflow/_metashape_runner.py`

Local, async runner the Metashape panel dispatches to.

- **[`class MetashapeRunner(ProcessRunner)`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_runner.py#L58)** — Discover + asynchronously drive ``run_combined`` in the local Metashape.
  - `MetashapeRunner.exe(self) -> Optional[str]` *(property)*
  - `MetashapeRunner.is_available(self) -> bool` — True when a local ``metashape.exe`` was found (a real run is possible).
  - `MetashapeRunner.start(self, argv: Sequence[str], on_line: Optional[Callable[[str], None]] = None, on_done: Optional[Callable[[int], None]] = None, cwd: Optional[str] = None) -> None`

<a id="photogrammetry--metashape_workflow--_metashape_workflow"></a>
### `photogrammetry/metashape_workflow/_metashape_workflow.py`

- [`IMAGE_EXTS`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L21) — constant
- [`DEFAULT_GATES`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L27) — constant
- **[`class MetashapeWorkflow(WorkflowEngine, PrepStagesMixin, MeshStagesMixin)`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L49)** — Wrapper around Agisoft Metashape's Python API for the standard
  - `MetashapeWorkflow.is_metashape_available() -> bool` *(static)* — True if the Metashape Python module imported successfully.
  - `MetashapeWorkflow.is_license_valid() -> bool` *(static)* — True if a valid Metashape license is reachable.
  - `MetashapeWorkflow.get_metashape_version() -> str` *(static)*
  - `MetashapeWorkflow.get_image_filepaths(directory: str) -> List[str]` *(static)* — Return absolute paths to all images in `directory` (non-recursive).
  - `MetashapeWorkflow.get_license_info(self) -> str`
  - `MetashapeWorkflow.create_chunk(self, label: str = 'New Chunk')`
  - `MetashapeWorkflow.add_images(self, image_sources: Union[str, Sequence[str]])` — Add images from a directory path (non-recursive) or list of paths.
  - `MetashapeWorkflow.add_image_dirs(self, dirs: Sequence[str])` — Add images from multiple directories — flattens to one chunk.
  - `MetashapeWorkflow.triage_images(self, quality_threshold: float = 0.5)` — Run ``analyzePhotos`` and disable cameras below ``quality_threshold``.
  - `MetashapeWorkflow.align_photos(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, filter_mask: bool = False)`
  - `MetashapeWorkflow.align_photos_with_retry(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0, filter_mask: bool = False)` — Run ``align_photos``;
  - `MetashapeWorkflow.refine_alignment(self, uncertainty_threshold: float = 15.0, reprojection_threshold: float = 0.5, projection_accuracy_threshold: float = 3.0)` — Gradual-selection cleanup: iteratively filter tie points by
  - `MetashapeWorkflow.dedupe_cameras_by_pose(self, translation_threshold: float = 0.02, rotation_threshold_deg: float = 2.0)` — Cluster aligned cameras by pose and disable redundants.
  - `MetashapeWorkflow.calibrate_colors(self, source_data=None, white_balance: bool = True)` — Run ``chunk.calibrateColors`` to equalize white-balance across
  - `MetashapeWorkflow.generate_masks(self, source_dir: str, masks_dir: Optional[str] = None, model_name: str = 'u2net') -> Optional[str]` — Run rembg on ``source_dir`` → write per-image alpha masks.
  - `MetashapeWorkflow.generate_masks_native(self, tolerance: int = 10) -> bool` — Background-mask every camera with Metashape's built-in AI masking
  - `MetashapeWorkflow.import_masks(self, masks_dir: str, mask_source: str = 'file', template: str = '{filename}_mask.png')` — Import per-camera masks from a directory.
  - `MetashapeWorkflow.generate_depth_maps(self, downscale: int = 2, filter_mode=None)`
  - `MetashapeWorkflow.build_model(self, source_data=None, surface_type=None, interpolation=None, face_count=None)`
  - `MetashapeWorkflow.clean_mesh(self, remove_components_face_threshold: int = 100, close_holes_level: int = 30, smooth_strength: int = 0)` — Mesh cleanup chain: ``removeComponents → closeHoles → smoothModel``.
  - `MetashapeWorkflow.reduce_overlap(self, target_overlap: int = 9)` — Thin redundant cameras for texture bake while preserving
  - `MetashapeWorkflow.build_texture(self, texture_size: int = 8192, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter: bool = True)`
  - `MetashapeWorkflow.save_project(self)`
  - `MetashapeWorkflow.export_model(self, export_format=None, binary: bool = True, precision: int = 6, texture_format=None, save_texture: bool = True, save_normals: bool = True, save_colors: bool = True, save_cameras: bool = False, overwrite: bool = True, save_usdz: bool = True)`
  - `MetashapeWorkflow.export_colmap(self, output_dir: str, convert_to_pinhole: bool = True, binary: bool = True, max_cameras: int = 0) -> Optional[str]` — Export the aligned chunk as a COLMAP dataset to feed the splat track.
  - `MetashapeWorkflow.export_qc(self)` — Write Metashape's processing report PDF + finalize the JSON sidecar.

<a id="photogrammetry--metashape_workflow--run_combined"></a>
### `photogrammetry/metashape_workflow/run_combined.py`

Driver script for multi-session combined runs.

- [`main(argv=None) -> int`](extapps/extapps/photogrammetry/metashape_workflow/run_combined.py#L271)
- [`PREP_RESULT_PREFIX`](extapps/extapps/photogrammetry/metashape_workflow/run_combined.py#L43) — constant

<a id="photogrammetry--prep_stages"></a>
### `photogrammetry/prep_stages.py`

Shared, SDK-agnostic pipeline stages for the photogrammetry engines.

- **[`class PrepStagesMixin`](extapps/extapps/photogrammetry/prep_stages.py#L27)** — Curate / equalize / export-sidecar stages shared by both photogrammetry engines.
  - `PrepStagesMixin.image_long_edge(image_path: str) -> Optional[int]` *(static)* — Long edge (px) of an image, or ``None`` if unreadable.
  - `PrepStagesMixin.extract_videos_to_dir(videos: Sequence[str], output_dir: str, *, window_sec: float = 1.0, quality: int = 95, log: Optional[Callable[[str], None]] = None) -> List[str]` *(static)* — Extract frames from one or more videos into a single ``output_dir``.
  - `PrepStagesMixin.first_image_in_dirs(dirs: Sequence[str]) -> Optional[str]` *(static)* — First image file (sorted) across ``dirs``, or ``None``.
  - `PrepStagesMixin.derive_texture_size(image_path: Optional[str], floor: int = 2048, cap: int = 8192, default: int = 8192) -> int` *(static)* — Texture page size from a source image: next power-of-two ≥ its long edge,
  - `PrepStagesMixin.curate_input_set(self, source_dirs: Sequence[str], output_root: Optional[str] = None, hash_threshold: int = 0, sharpness_floor: float = 0.0, sharpness_floor_percentile: Optional[float] = None, min_sharpness_fraction_of_median: float = 0.0, keep_per_cluster: int = 1, overcuration_warn_pct: float = 30.0) -> List[str]` — Pre-SfM content + sharpness culling via :class:`pythontk.ImageCurator`.
  - `PrepStagesMixin.preview_curation(self, source_dirs: Sequence[str], hash_thresholds: Sequence[int] = (5, 8, 10, 12, 15), keep_per_cluster: int = 1, sharpness_floor_percentile: Optional[float] = None, min_sharpness_fraction_of_median: float = 0.0)` — Dry-run curation QC — report survivor counts per dHash threshold + the
  - `PrepStagesMixin.equalize_exposures(self, source_dirs: Sequence[str], output_root: Optional[str] = None, reference_dir: Optional[str] = None, strength: float = 0.5, reference_strategy: str = 'median') -> List[str]` — Cross-set exposure / WB equalization via :class:`pythontk.ExposureEqualizer`.

<a id="photogrammetry--profile"></a>
### `photogrammetry/profile.py`

Photogrammetry I/O + tuning **profile** — site/personal config kept out of source.

- [`PROFILE_NAME`](extapps/extapps/photogrammetry/profile.py#L36) — constant
- [`PROFILE_PACKAGE`](extapps/extapps/photogrammetry/profile.py#L37) — constant
- [`PROFILE_ENV`](extapps/extapps/photogrammetry/profile.py#L38) — constant
- [`PRESETS_NAME`](extapps/extapps/photogrammetry/profile.py#L49) — constant
- [`PRESETS_DIR`](extapps/extapps/photogrammetry/profile.py#L50) — constant
- [`IMAGE_EXTS`](extapps/extapps/photogrammetry/profile.py#L54) — constant
- [`QUALITY_TIERS`](extapps/extapps/photogrammetry/profile.py#L60) — constant
- [`EXAMPLE_PROFILE`](extapps/extapps/photogrammetry/profile.py#L432) — constant
- **[`class Profile(_ProfileInternal)`](extapps/extapps/photogrammetry/profile.py#L231)** — Resolution + lookup entry points for the photogrammetry profile.
  - `Profile.get_profile(path=None) -> dict` *(static)* — Resolve the active photogrammetry profile (fully interpolated).
  - `Profile.configured_app_path(key: str, path=None) -> Optional[str]` *(static)* — Return the profile-configured install path for an engine, or ``None``.
  - `Profile.resolve_app(env_var: str, config_key: Optional[str] = None, *, validate: Optional[Callable[[str], bool]] = None, spec=None, fallbacks: Sequence[Callable[[], Optional[str]]] = (), path=None) -> Optional[str]` *(static)* — Resolve an engine's install location; the first hit wins.
  - `Profile.preset_store(engine: str) -> PresetStore` *(static)* — The run-template store for *engine*: shipped built-ins (``presets/<engine>/``)
  - `Profile.get_preset(name: Optional[str], engine: str) -> dict` *(static)* — Return the named opt-in run-template overlay for *engine* (``_comment`` stripped).
  - `Profile.init_user_profile(path: Optional[str] = None, force: bool = False) -> str` *(static)* — Write :data:`EXAMPLE_PROFILE` to the user-config location (or *path*).
  - `Profile.discover_source_dirs(input_root: str) -> List[str]` *(static)* — Return immediate subdirs of ``input_root`` that contain images.

<a id="photogrammetry--realityscan_workflow--__init__"></a>
### `photogrammetry/realityscan_workflow/__init__.py`

Turn photos or video frames into a textured mesh with headless RealityCapture.

- [`DEFAULT_INCLUDE`](extapps/extapps/photogrammetry/realityscan_workflow/__init__.py#L21) — constant

<a id="photogrammetry--realityscan_workflow--_realityscan_connection"></a>
### `photogrammetry/realityscan_workflow/_realityscan_connection.py`

Launch connection for RealityScan / RealityCapture.

- **[`class RealityScanInteractiveError(RuntimeError)`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_connection.py#L32)** — An RC run needs an interactive, Epic-signed-in desktop session that is not
- **[`class RealityScanConnection`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_connection.py#L37)** — Discover + drive the RealityScan/RealityCapture CLI, interactive-aware.
  - `RealityScanConnection.is_available(self) -> bool`
  - `RealityScanConnection.is_interactive() -> bool` *(static)* — True if the current process can host RC's window (session != 0).
  - `RealityScanConnection.epic_signin_active() -> bool` *(static)* — Heuristic: True if Epic sign-in helpers are running (RC is waiting on
  - `RealityScanConnection.run(self, commands: Sequence[str], log_path: str, timeout: Optional[float] = None, session: Optional[int] = None, poll_interval: float = 5.0) -> subprocess.CompletedProcess` — Run RC as ``[exe] + commands`` (the caller supplies the full CLI tail,

<a id="photogrammetry--realityscan_workflow--_realityscan_runner"></a>
### `photogrammetry/realityscan_workflow/_realityscan_runner.py`

Local, async runner the RealityCapture panel dispatches to.

- **[`class RealityScanRunner(PyModuleRunner)`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_runner.py#L25)** — Discover RealityScan + asynchronously drive its ``run_combined``.
  - `RealityScanRunner.exe(self) -> Optional[str]` *(property)*
  - `RealityScanRunner.is_available(self) -> bool` — True when a RealityScan / RealityCapture exe was found, or a remote

<a id="photogrammetry--realityscan_workflow--_realityscan_workflow"></a>
### `photogrammetry/realityscan_workflow/_realityscan_workflow.py`

RealityCapture / RealityScan workflow engine.

- [`IMAGE_EXTS`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L33) — constant
- [`QC_REPORT_TEMPLATE`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L44) — constant
- [`APP`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L51) — constant
- [`DEFAULT_GATES`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L67) — constant
- **[`class RealityCaptureWorkflow(WorkflowEngine, PrepStagesMixin, MeshStagesMixin, _RealityCaptureWorkflowInternal)`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L116)** — Wrapper around RealityCapture's CLI for the standard photogrammetry
  - `RealityCaptureWorkflow.find_realitycapture_exe() -> Optional[str]` *(static)* — Return the RealityCapture.exe path or None.
  - `RealityCaptureWorkflow.is_realitycapture_available() -> bool` *(static)*
  - `RealityCaptureWorkflow.get_realitycapture_version() -> str` *(static)* — Read RC's FileVersion from Windows binary metadata.
  - `RealityCaptureWorkflow.get_image_filepaths(directory: str) -> List[str]` *(static)* — Return absolute paths to all images in ``directory`` (non-recursive).
  - `RealityCaptureWorkflow.get_license_info(self) -> str`
  - `RealityCaptureWorkflow.create_chunk(self, label: str = 'New Chunk')` — Start a fresh RC scene.
  - `RealityCaptureWorkflow.add_images(self, image_sources: Union[str, Sequence[str]])` — Add images from a directory (non-recursive) or list of paths.
  - `RealityCaptureWorkflow.add_image_dirs(self, dirs: Sequence[str])` — Add images from multiple directories — RC keeps them in one scene.
  - `RealityCaptureWorkflow.triage_images(self, quality_threshold: float = 0.5)` — No direct RC equivalent.
  - `RealityCaptureWorkflow.align_photos(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, filter_mask: bool = False)` — Run RC alignment (SfM).
  - `RealityCaptureWorkflow.align_photos_with_retry(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0)` — Run alignment;
  - `RealityCaptureWorkflow.refine_alignment(self, *args, **kwargs)` — RC performs alignment refinement internally during ``-align``;
  - `RealityCaptureWorkflow.dedupe_cameras_by_pose(self, *args, **kwargs)` — No direct RC equivalent.
  - `RealityCaptureWorkflow.calibrate_colors(self, *args, **kwargs)` — RC applies color correction inside ``-calculateTexture`` via
  - `RealityCaptureWorkflow.generate_masks(self, source_dir: str, masks_dir: Optional[str] = None, model_name: str = 'u2net') -> Optional[str]` — Run rembg on ``source_dir`` → write per-image alpha masks.
  - `RealityCaptureWorkflow.import_masks(self, masks_dir: str, mask_source: str = 'alpha')` — RC accepts per-image masks named ``<image>.png`` next to the
  - `RealityCaptureWorkflow.generate_depth_maps(self, *args, **kwargs)` — RC does not expose depth maps as a separate stage — mesh calc
  - `RealityCaptureWorkflow.build_model(self, source_data=None, surface_type=None, interpolation=None, face_count: Optional[str] = None)` — Build a polygon mesh.
  - `RealityCaptureWorkflow.clean_mesh(self, remove_components_face_threshold: int = 100, close_holes_level: int = 30, smooth_strength: int = 0)` — Mesh cleanup via ``-setMinComponentSize N`` + ``-cleanModel``.
  - `RealityCaptureWorkflow.simplify_model(self, target_face_count: int = 20000000)` — Simplify the densest model to ~``target_face_count`` triangles.
  - `RealityCaptureWorkflow.reduce_overlap(self, *args, **kwargs)` — No RC equivalent.
  - `RealityCaptureWorkflow.import_model(self, mesh_path: str)` — Import an external low-poly mesh into the project (Maya-authored
  - `RealityCaptureWorkflow.build_texture(self, texture_size: int = 4096, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter: bool = True)` — Unwrap (when no mesh was imported) + bake texture from solved
  - `RealityCaptureWorkflow.save_project(self)` — RC saves on every CLI call (``-save`` is appended);
  - `RealityCaptureWorkflow.export_model(self, export_format: Optional[str] = None, binary: bool = True, precision: int = 6, texture_format=None, save_texture: bool = True, save_normals: bool = True, save_colors: bool = True, save_cameras: bool = False, overwrite: bool = True, save_usdz: bool = True)` — Export the current model.
  - `RealityCaptureWorkflow.export_qc(self)` — Export RC's processing report XML and append to the QC log.
  - `RealityCaptureWorkflow.finalize_run(self, success: bool = True) -> str` — Flush the QC JSON sidecar + release the transport.

<a id="photogrammetry--realityscan_workflow--_rsnode_client"></a>
### `photogrammetry/realityscan_workflow/_rsnode_client.py`

RSNode REST client — drive a running RealityScan 2.1 over its REST API (headless).

- **[`class RsNodeError(RuntimeError)`](extapps/extapps/photogrammetry/realityscan_workflow/_rsnode_client.py#L40)** — An RSNode REST call failed (transport error or non-2xx apiError).
- **[`class RsNodeClient`](extapps/extapps/photogrammetry/realityscan_workflow/_rsnode_client.py#L48)** — Minimal stdlib REST client for the RSNode API of a running RealityScan.
  - `RsNodeClient.normalize_commands(commands: Sequence[CommandLike]) -> List[Dict[str, Any]]` *(static)* — Translate CLI-style command specs into RSNode ``commandCall`` dicts.
  - `RsNodeClient.connect(self) -> Dict[str, Any]` — ``GET /node/connection`` (localhost) — fetch + store the auth token.
  - `RsNodeClient.node_status(self) -> Dict[str, Any]`
  - `RsNodeClient.create_session(self) -> str` — ``GET /project/create`` — start a session;
  - `RsNodeClient.run_commands(self, commands: Sequence[CommandLike]) -> str` — ``POST /project/commandgroup`` — run a CLI command sequence;
  - `RsNodeClient.upload_file(self, name: str, data: bytes, folder: str = 'data', timeout: Optional[float] = None) -> int` — ``POST /project/upload`` — upload raw *data* into the session folder.
  - `RsNodeClient.list_files(self, folder: str = 'output') -> List[str]` — ``GET /project/list`` — names of files in the session ``output``/``data`` folder.
  - `RsNodeClient.download_file(self, name: str, folder: str = 'output', timeout: Optional[float] = None) -> bytes` — ``GET /project/download`` — fetch raw bytes of session file *name*.
  - `RsNodeClient.project_status(self) -> Dict[str, Any]`
  - `RsNodeClient.tags(self) -> List[str]`
  - `RsNodeClient.has_tag(self, tag: str) -> bool`
  - `RsNodeClient.wait_for_tag(self, tag: str, *, poll: float = 2.0, timeout: float = 7200.0, sleep=time.sleep, clock=time.monotonic) -> Dict[str, Any]` — Poll ``/project/status`` until *tag* fires;
  - `RsNodeClient.tasks(self, task_ids: Optional[Union[str, Sequence[str]]] = None) -> List[Dict[str, Any]]` — ``GET /project/tasks`` — task records ``{taskID, state, errorCode, ...}``.
  - `RsNodeClient.wait_for_task(self, task_id: str, *, poll: float = 1.0, timeout: float = 7200.0, sleep=time.sleep, clock=time.monotonic) -> Dict[str, Any]` — Poll ``/project/tasks`` until *task_id* reaches a terminal state.
  - `RsNodeClient.save_project(self, name: Optional[str] = None) -> None` — ``GET /project/save`` — persist the session project to disk (async).
  - `RsNodeClient.open_project(self, guid: str, name: Optional[str] = None) -> str` — ``GET /project/open`` — open an existing project by guid into a session.
  - `RsNodeClient.close_project(self) -> None` — ``GET /project/close`` — close the session's project (teardown).

<a id="photogrammetry--realityscan_workflow--_rsnode_connection"></a>
### `photogrammetry/realityscan_workflow/_rsnode_connection.py`

RSNode-backed connection — drive a running RealityScan 2.1 over REST.

- [`DEFAULT_RSNODE_URL`](extapps/extapps/photogrammetry/realityscan_workflow/_rsnode_connection.py#L68) — constant
- **[`class RsNodeConnection`](extapps/extapps/photogrammetry/realityscan_workflow/_rsnode_connection.py#L101)** — Run RealityScan CLI command tails over the RSNode REST API.
  - `RsNodeConnection.is_available(self) -> bool` — True if a RealityScan RSNode answers the token handshake at *base_url*.
  - `RsNodeConnection.close(self) -> None` — Best-effort teardown of this connection's own RSNode session.
  - `RsNodeConnection.run(self, commands: Sequence[str], log_path: str, timeout: Optional[float] = None, **_ignored: Any) -> subprocess.CompletedProcess` — Execute a CLI command tail over REST;

<a id="photogrammetry--realityscan_workflow--run_combined"></a>
### `photogrammetry/realityscan_workflow/run_combined.py`

Driver script for multi-session combined RealityCapture runs.

- [`publish_outputs(project_dir: str, publish_dir: str)`](extapps/extapps/photogrammetry/realityscan_workflow/run_combined.py#L68) — Copy finished deliverables from local scratch to the synced output root.
- [`main(argv=None) -> int`](extapps/extapps/photogrammetry/realityscan_workflow/run_combined.py#L116)

<a id="photogrammetry--sugar_mesh_workflow--_sugar_mesh"></a>
### `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py`

SuGaR mesh-extraction workflow engine.

- **[`class SugarMeshWorkflow(WorkflowEngine, _SugarMeshWorkflowInternal)`](extapps/extapps/photogrammetry/sugar_mesh_workflow/_sugar_mesh.py#L60)** — COLMAP dataset → SuGaR refined textured ``.obj`` mesh.
  - `SugarMeshWorkflow.find_sugar_dir() -> 'Optional[str]'` *(static)* — Return the SuGaR repo dir or None.
  - `SugarMeshWorkflow.is_sugar_available() -> bool` *(static)*
  - `SugarMeshWorkflow.get_sugar_info(self) -> str`
  - `SugarMeshWorkflow.extract_mesh(self, colmap_dir: str, regularization: str = 'dn_consistency', high_poly: bool = True, refinement_time: str = 'medium', surface_level: float = 0.3, export_obj: bool = True, export_ply: bool = False, use_eval_split: bool = False, gpu: int = 0, white_background: bool = False) -> Optional[str]` — Run SuGaR's full pipeline on a COLMAP dataset;

<a id="photogrammetry--sugar_mesh_workflow--run_combined"></a>
### `photogrammetry/sugar_mesh_workflow/run_combined.py`

Driver for the **EXPERIMENTAL** SuGaR mesh track: COLMAP dataset → textured ``.obj``.

- [`main(argv=None) -> int`](extapps/extapps/photogrammetry/sugar_mesh_workflow/run_combined.py#L37)

<a id="substance_workflow--__init__"></a>
### `substance_workflow/__init__.py`

Create a Substance Painter project from a mesh and bake lighting into base color.

- [`DEFAULT_INCLUDE`](extapps/extapps/substance_workflow/__init__.py#L29) — constant

<a id="substance_workflow--bake_utils"></a>
### `substance_workflow/bake_utils.py`

Bake operations — iray-backed mesh-map bakes and lighting composites.

- [`lighting_to_diffuse(texture_set: Optional[str] = None, bake_resolution: int = 1024, ao_intensity: float = 1.0, ao_secondary_rays: int = 64, ao_max_distance: float = 1.0, ao_min_distance: float = 0.0, ao_spread_angle: float = 162.0, ao_subsample: int = 1, include_curvature: bool = False, curvature_intensity: float = 0.3, layer_name: str = 'iray AO Lighting', blend_mode: str = 'Multiply', skip_existing_bakes: bool = False, save_project: bool = False) -> dict`](extapps/extapps/substance_workflow/bake_utils.py#L301) — Bake iray-backed AO (+ optional curvature) and composite onto base color.
- [`mesh_maps(texture_set: str, maps: Optional[List[str]] = None, high_poly: Optional[str] = None) -> dict`](extapps/extapps/substance_workflow/bake_utils.py#L425) — Bake the named mesh maps.
- [`all_texture_sets(maps: Optional[List[str]] = None) -> dict`](extapps/extapps/substance_workflow/bake_utils.py#L438) — Bake mesh maps for every texture set in the project.
- [`set_resolution(texture_set: str, width: int, height: int) -> None`](extapps/extapps/substance_workflow/bake_utils.py#L444) — Set the baking resolution for the named texture set.

<a id="substance_workflow--channel_utils"></a>
### `substance_workflow/channel_utils.py`

Channel operations — query and modify per-channel state on a texture set.

- [`list_formats() -> List[str]`](extapps/extapps/substance_workflow/channel_utils.py#L9) — Return the channel format names supported by Painter (``sRGB8``, ``L16``, ...).
- [`format(texture_set: str, channel: str) -> str`](extapps/extapps/substance_workflow/channel_utils.py#L15) — Return the storage format of the named channel.
- [`set_format(texture_set: str, channel: str, fmt: str) -> None`](extapps/extapps/substance_workflow/channel_utils.py#L21) — Set the storage format of the named channel.
- [`export_path(texture_set: str, channel: str) -> str`](extapps/extapps/substance_workflow/channel_utils.py#L27) — Return the channel's user-defined export path template, if any.

<a id="substance_workflow--env_utils--painter_connection"></a>
### `substance_workflow/env_utils/painter_connection.py`

Painter Connection Module.

- **[`class PainterConnection`](extapps/extapps/substance_workflow/env_utils/painter_connection.py#L36)** — Live JSON-RPC connection to a Substance 3D Painter session.
  - `PainterConnection.op_timeout() -> float` *(static)* — Seconds the bridge lets one op run (its main-thread marshaller's
  - `PainterConnection.plugins_dir() -> str` *(static)* — Absolute path to the plugin root, ``substance_workflow/plugins``.
  - `PainterConnection.build_painter_env(port: int = 0) -> dict` *(static)* — Compose the environment block passed to a Painter launch.
  - `PainterConnection.launch_painter(exe: str, env: dict, gui: bool = False, extra_args: Optional[List[str]] = None) -> subprocess.Popen` *(static)* — Spawn a detached Painter process via ``pythontk.AppLauncher``.
  - `PainterConnection.get_instance(cls) -> 'PainterConnection'` *(class)*
  - `PainterConnection.is_connected(self) -> bool` *(property)* — Connected to the bridge of a Painter that is still running.
  - `PainterConnection.get_available_port(start_port: int = 5050, max_check: int = 100) -> int` *(static)* — Return the lowest TCP port a NEW bridge server could bind on localhost.
  - `PainterConnection.connect(self, force_new_instance: bool = True, gui: bool = False, port: int = 5050, app_path: Optional[str] = None, launch_args: Optional[List[str]] = None, timeout: float = 180.0) -> bool` — Launch a fresh Painter and connect over the bridge HTTP server.
  - `PainterConnection.client(self) -> RpcClient` *(property)* — The shared JSON-RPC client, bound to this connection's bridge.
  - `PainterConnection.invoke(self, op: str, timeout: float = 60.0, **kwargs: Any) -> Any` — Call a registered op over the bridge and return its value.
  - `PainterConnection.describe(self, op: str = '') -> Any` — The registry's ``{name, doc, params}`` for *op*, or a list for all.
  - `PainterConnection.shutdown(self, force: bool = False) -> None` — Close the bridge and terminate the Painter process we launched.

<a id="substance_workflow--env_utils--painter_finder"></a>
### `substance_workflow/env_utils/painter_finder.py`

Locate installed Substance 3D Painter.

- **[`class PainterFinder`](extapps/extapps/substance_workflow/env_utils/painter_finder.py#L10)** — Helper to locate Substance 3D Painter installations.
  - `PainterFinder.default_install_roots() -> List[str]` *(static)*
  - `PainterFinder.find_installs() -> Dict[str, str]` *(static)* — Return ``{label: exe_path}`` for every Painter install found, newest first.
  - `PainterFinder.resolve(version_or_path: Optional[str] = None) -> Optional[str]` *(static)* — Resolve an executable path.

<a id="substance_workflow--export_utils"></a>
### `substance_workflow/export_utils.py`

Texture export operations — drive ``substance_painter.export``.

- [`list_presets() -> List[str]`](extapps/extapps/substance_workflow/export_utils.py#L9) — Return user + built-in export preset names.
- [`textures(output_path: str, preset: str, texture_sets: Optional[List[str]] = None, file_format: str = 'png', bit_depth: int = 8) -> dict`](extapps/extapps/substance_workflow/export_utils.py#L15) — Export textures using ``preset``.
- [`preset_to_dict(preset: str) -> dict`](extapps/extapps/substance_workflow/export_utils.py#L30) — Return the export-preset definition as a dict for inspection.

<a id="substance_workflow--job"></a>
### `substance_workflow/job.py`

Batch convenience: launch Painter, run a call list over the bridge, shut down.

- **[`class Job`](extapps/extapps/substance_workflow/job.py#L24)** — Convenience builder — ``Job().add("project.info").run()``.
  - `Job.add(self, op: str, **kwargs: Any) -> 'Job'`
  - `Job.run(self, **launch_kwargs: Any) -> List[Result]`
  - `Job.run_batch(calls: List[Call], gui: bool = False, app_path: Optional[str] = None, timeout: float = 180.0, launch_args: Optional[List[str]] = None, invoke_timeout: Optional[float] = None) -> List[Result]` *(static)* — Launch Painter, execute ``calls`` in order over the bridge, shut down.

<a id="substance_workflow--layer_utils"></a>
### `substance_workflow/layer_utils.py`

Layer stack operations — list, add, remove, reorder, set properties.

- [`list_(texture_set: str) -> List[dict]`](extapps/extapps/substance_workflow/layer_utils.py#L9) — Return the layer stack for ``texture_set`` as a list of ``{name, uid, kind}`` dicts.
- [`add_fill(texture_set: str, name: str, color: Optional[List[float]] = None) -> str`](extapps/extapps/substance_workflow/layer_utils.py#L15) — Add a fill layer.
- [`add_paint(texture_set: str, name: str) -> str`](extapps/extapps/substance_workflow/layer_utils.py#L21) — Add a paint layer.
- [`add_group(texture_set: str, name: str) -> str`](extapps/extapps/substance_workflow/layer_utils.py#L27) — Add a folder/group node.
- [`delete(texture_set: str, uid: str) -> None`](extapps/extapps/substance_workflow/layer_utils.py#L33) — Delete the layer identified by ``uid``.
- [`set_opacity(texture_set: str, uid: str, channel: str, opacity: float) -> None`](extapps/extapps/substance_workflow/layer_utils.py#L39) — Set per-channel opacity (0.0 - 1.0).
- [`set_blend_mode(texture_set: str, uid: str, channel: str, mode: str) -> None`](extapps/extapps/substance_workflow/layer_utils.py#L45) — Set per-channel blend mode (``Normal``, ``Multiply``, ``Screen``, ...).

<a id="substance_workflow--material_utils"></a>
### `substance_workflow/material_utils.py`

Smart-material / preset operations — apply shelf materials onto layers.

- [`list_shelf() -> List[dict]`](extapps/extapps/substance_workflow/material_utils.py#L9) — Return shelf-bound smart materials as ``[{name, url, tags}, ...]``.
- [`apply_smart(texture_set: str, material_url: str, target_layer_uid: Optional[str] = None) -> str`](extapps/extapps/substance_workflow/material_utils.py#L15) — Apply a smart material.
- [`import_to_shelf(path: str, shelf_name: str = 'your_assets') -> str`](extapps/extapps/substance_workflow/material_utils.py#L28) — Import an ``.spsm`` smart material into the named shelf.

<a id="substance_workflow--plugins--startup--substance_workflow_bridge--__init__"></a>
### `substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py`

substance_workflow_bridge — Painter-side Python plugin.

- [`start_plugin() -> None`](extapps/extapps/substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py#L114) — Painter plugin entry point — start the JSON-RPC bridge server.
- [`close_plugin() -> None`](extapps/extapps/substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py#L126) — Painter plugin teardown.
- [`OP_MODULES`](extapps/extapps/substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py#L90) — constant

<a id="substance_workflow--project_utils"></a>
### `substance_workflow/project_utils.py`

Project-level operations — open, save, close, info, mesh swap.

- [`info() -> dict`](extapps/extapps/substance_workflow/project_utils.py#L14) — Return basic info about the current project, or ``{'open': False}``.
- [`open_(path: str) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L28) — Open an existing ``.spp`` project.
- [`save() -> dict`](extapps/extapps/substance_workflow/project_utils.py#L37) — Save the current project to its existing path.
- [`save_as(path: str) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L46) — Save the current project to ``path``.
- [`close() -> dict`](extapps/extapps/substance_workflow/project_utils.py#L55) — Close the current project without saving.
- [`create(mesh_path: str, template_path: Optional[str] = None) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L64) — Create a new project from a mesh.
- [`reload_mesh(mesh_path: str) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L81) — Reimport the project's mesh from ``mesh_path``.

<a id="substance_workflow--registry"></a>
### `substance_workflow/registry.py`

Op registry — the callable Painter surface, on the shared RPC core.

- [`PLUGIN`](extapps/extapps/substance_workflow/registry.py#L32) — constant

<a id="substance_workflow--resource_utils"></a>
### `substance_workflow/resource_utils.py`

Shelf / resource operations — query and import shelf assets.

- [`list_shelves() -> List[str]`](extapps/extapps/substance_workflow/resource_utils.py#L9) — Return the names of all configured shelves.
- [`list_assets(shelf: str, kind: str = 'smartmaterial') -> List[dict]`](extapps/extapps/substance_workflow/resource_utils.py#L15) — List assets of ``kind`` on ``shelf``.
- [`import_(path: str, shelf: str = 'your_assets', kind: str = 'smartmaterial') -> str`](extapps/extapps/substance_workflow/resource_utils.py#L21) — Import an asset file into the named shelf.

<a id="substance_workflow--texture_set_utils"></a>
### `substance_workflow/texture_set_utils.py`

Texture set operations — list, resolution, channel inventory.

- [`list_() -> List[str]`](extapps/extapps/substance_workflow/texture_set_utils.py#L9) — Return the names of all texture sets in the current project.
- [`resolution(name: str) -> List[int]`](extapps/extapps/substance_workflow/texture_set_utils.py#L15) — Return ``[width, height]`` of the named texture set.
- [`set_resolution(name: str, width: int, height: int) -> None`](extapps/extapps/substance_workflow/texture_set_utils.py#L21) — Set the texture set resolution.
- [`channels(name: str) -> List[str]`](extapps/extapps/substance_workflow/texture_set_utils.py#L27) — Return the channel identifiers active on the named texture set.
- [`add_channel(name: str, channel: str, fmt: str = 'sRGB8') -> None`](extapps/extapps/substance_workflow/texture_set_utils.py#L33) — Add a channel to the texture set (``BaseColor``, ``Roughness``, ...).

<a id="texture_maps--converter--__init__"></a>
### `texture_maps/converter/__init__.py`

The Map Converter's batch rules: plan, name and run one map at a time.

- [`DEFAULT_INCLUDE`](extapps/extapps/texture_maps/converter/__init__.py#L16) — constant

<a id="texture_maps--converter--_converter"></a>
### `texture_maps/converter/_converter.py`

The Map Converter's batch engine: plan, name and run one map at a time.

- **[`class MapConverter`](extapps/extapps/texture_maps/converter/_converter.py#L31)** — Batch rules of the Map Converter panel (stateless;
  - `MapConverter.resolve_affix(mode: str, modifier: str) -> Tuple[str, str]` *(static)* — Resolve the Affix mode against the modifier text.
  - `MapConverter.is_abs_dest(text: str) -> bool` *(static)* — True when *text* names a full destination rather than a subdirectory.
  - `MapConverter.folder_name(cls, text: str) -> str` *(class)* — Normalize a destination field to a subdirectory name or full path.
  - `MapConverter.output_collisions(cls, paths, file_type, folder, profile=None)` *(class)* — ``[(name, [path, ...]), ...]`` for inputs resolving to ONE file in *folder*.
  - `MapConverter.resolve_dest(cls, directory: str, folder: str) -> str` *(class)* — Destination directory for a *folder* field against a texture's *directory*.
  - `MapConverter.rename_target_path(cls, texture_path, *, file_type, mode, modifier, output_dir, base_name=None)` *(class)* — Output path for rename mode — modifier between base and map-type suffix.
  - `MapConverter.optimize_one(cls, texture_path, *, file_type, max_size, secondary_scale, mode, modifier, new_folder, old_folder, registry, dry_run=False, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None, map_type=None, base_name=None)` *(class)* — ``ConverterSlots.tb000``'s per-map step — optimize (or, when *dry_run*, assess) one path.
  - `MapConverter.report_optimize_plan(cls, texture_path, *, file_type, max_size, mode, modifier, output_dir, old_folder, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None, map_type=None, base_name=None)` *(class)* — Print what optimizing *texture_path* would do, touching nothing.
  - `MapConverter.flip_one(cls, path, *, swizzle_map, invert_dests, suffix)` *(class)* — ``ConverterSlots.tb002``'s per-map step — flip/swizzle one texture path.
