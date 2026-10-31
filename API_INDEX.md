# extapps — API Index

_Auto-generated. Do not edit by hand. Compact symbol index — grep this for a name; for full signatures/docs, slice [API_REGISTRY.md](API_REGISTRY.md) (never Read it whole)._

### `__init__.py` — extapps — the engines of the standalone content-pipeline tools.
- constants: DOCS_BASE_URL, DEFAULT_INCLUDE, MOVED_NAMES

### `marmoset_workflow/__init__.py` — Launch Marmoset Toolbag and set up an import or lookdev scene from a model file.
- constants: DEFAULT_INCLUDE

### `marmoset_workflow/_marmoset_engine.py` — Drive Marmoset Toolbag from the outside -- launch + templated automation.
- constants: APP, SEND_TO, ROUND_TRIP
- `class MarmosetEngine(pythontk.Deliverer, pythontk.LoggingMixin)`
  - methods: toolbag_path, toolbag_log_path, preflight, deliver, send, render_template, list_templates, template_modes, list_template_modes

### `marmoset_workflow/_marmoset_workflow.py` — The Toolbag engine as the standalone Marmoset Workflow panel drives it.
- `class MarmosetWorkflow(MarmosetEngine)`

### `marmoset_workflow/_toolbag_helpers.py` — Shared helpers for Marmoset Toolbag template scripts.
- constants: SLOT_MAP, MODULE_NEUTRAL_FIELDS, SUBROUTINE_FIXES
- `class ToolbagHelpers(_ToolbagHelpersInternal)`
  - methods: derive_per_run_log_path, begin_log, log, find_material, load_manifest, wire_materials_from_manifest, split_source_target, collect_mesh_objects, apply_sky_preset, frame_in_viewport

### `marmoset_workflow/template_params.py` — Plain default values + literal formatting for Marmoset template tokens.
- constants: DEFAULTS
- `class TemplateParams`
  - methods: derive_auto_maps, derive_bake_values, python_literal, defaults, to_context

### `marmoset_workflow/templates/import.py` — Open the model in Toolbag and wire materials from the manifest.
- `main()`
- constants: BRIDGE_MODES, MODEL_FILE, MANIFEST_FILE, SAVE_PATH, SHOULD_QUIT

### `marmoset_workflow/templates/lookdev.py` — Open the model in Toolbag, apply a Sky preset, and frame the model.
- `main()`
- constants: BRIDGE_MODES, MODEL_FILE, MANIFEST_FILE, SAVE_PATH, SHOULD_QUIT, SKY_PRESET, FRAME_SELECTION

### `marmoset_workflow/toolbag_log.py` — Marmoset Toolbag log-file resolution, classification, and live tailing.
- `class ToolbagLog`
  - methods: resolve_toolbag_log_path, classify_log_line, dispatch_log_lines, start_toolbag_log_tail

### `photogrammetry/_process_runner.py` — Async, log-streaming process runner shared by the photogrammetry panels.
- `class ProcessRunner(pythontk.LoggingMixin)`
  - methods: exe, is_available, is_running, start, cancel
- `class PyModuleRunner(ProcessRunner)`

### `photogrammetry/_progress_notify.py` — The one progress-notify shim the photogrammetry engines share.
- `class ProgressNotifyMixin`

### `photogrammetry/_workflow_engine.py` — The lifecycle every photogrammetry engine shares: one base, five engines.
- `class WorkflowEngine(ProgressNotifyMixin)`
  - methods: finalize_run

### `photogrammetry/gaussian_splat_workflow/__init__.py` — Train a Gaussian splat with Brush from COLMAP data and export it for Unity or web.
- constants: DEFAULT_INCLUDE

### `photogrammetry/gaussian_splat_workflow/_gaussian_splat_runner.py` — Local, async runner the Brush (gaussian-splat) panel dispatches to.
- `class GaussianSplatRunner(PyModuleRunner)`
  - methods: exe, is_available
- `class BrushInstallRunner(PyModuleRunner)`
  - methods: exe, is_available

### `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py` — Brush gaussian-splat workflow engine.
- constants: BRUSH_APP, BRUSH_DOWNLOAD, BRUSH_EXE_NAME
- `class GaussianSplatWorkflow(WorkflowEngine, _GaussianSplatWorkflowInternal)`
  - methods: find_brush_exe, is_brush_available, install_brush, read_splat_count, get_brush_info, train

### `photogrammetry/gaussian_splat_workflow/_install_brush.py` — Headless entry point: download + install Brush via pythontk.AppInstaller.
- `main() -> int`

### `photogrammetry/gaussian_splat_workflow/_splat_publish.py` — Engine-delivery stage for the splat track — clean + convert to engine formats.
- constants: SPLAT_TRANSFORM_APP
- `class SplatPublishWorkflow(WorkflowEngine, _SplatPublishWorkflowInternal)`
  - methods: find_splat_transform, is_splat_transform_available, get_publish_info, clean, to_unity, to_web, publish

### `photogrammetry/gaussian_splat_workflow/run_combined.py` — Driver for the gaussian-splat track: Brush splat training + engine publish.
- `main(argv=None) -> int`

### `photogrammetry/mesh_stages.py` — Shared, SDK-agnostic mesh post-processing stages (PyMeshLab-backed).
- `class MeshStagesMixin`
  - methods: measure_mesh, refine_mesh, bake_vertex_color, run_mesh_stages, clean_mesh_advanced

### `photogrammetry/metashape_workflow/__init__.py` — Turn photos or video frames into a textured mesh with headless Metashape.
- constants: DEFAULT_INCLUDE

### `photogrammetry/metashape_workflow/_metashape_connection.py` — Headless launch connection for Agisoft Metashape.
- constants: APP
- `class MetashapeConnection`
  - methods: find_exe, is_available, run_script, run_combined

### `photogrammetry/metashape_workflow/_metashape_runner.py` — Local, async runner the Metashape panel dispatches to.
- `class MetashapeRunner(ProcessRunner)`
  - methods: exe, is_available, start

### `photogrammetry/metashape_workflow/_metashape_workflow.py`
- constants: IMAGE_EXTS, DEFAULT_GATES
- `class MetashapeWorkflow(WorkflowEngine, PrepStagesMixin, MeshStagesMixin)`
  - methods: is_metashape_available, is_license_valid, get_metashape_version, get_image_filepaths, get_license_info, create_chunk, add_images, add_image_dirs, triage_images, align_photos, align_photos_with_retry, refine_alignment, dedupe_cameras_by_pose, calibrate_colors, generate_masks, generate_masks_native, import_masks, generate_depth_maps, build_model, clean_mesh, reduce_overlap, build_texture, save_project, export_model, export_colmap, export_qc

### `photogrammetry/metashape_workflow/run_combined.py` — Driver script for multi-session combined runs.
- `main(argv=None) -> int`
- constants: PREP_RESULT_PREFIX

### `photogrammetry/prep_stages.py` — Shared, SDK-agnostic pipeline stages for the photogrammetry engines.
- `class PrepStagesMixin`
  - methods: image_long_edge, extract_videos_to_dir, first_image_in_dirs, derive_texture_size, curate_input_set, preview_curation, equalize_exposures

### `photogrammetry/profile.py` — Photogrammetry I/O + tuning **profile** — site/personal config kept out of source.
- constants: PROFILE_NAME, PROFILE_PACKAGE, PROFILE_ENV, PRESETS_NAME, PRESETS_DIR, IMAGE_EXTS, QUALITY_TIERS, EXAMPLE_PROFILE
- `class Profile(_ProfileInternal)`
  - methods: get_profile, configured_app_path, resolve_app, preset_store, get_preset, init_user_profile, discover_source_dirs

### `photogrammetry/realityscan_workflow/__init__.py` — Turn photos or video frames into a textured mesh with headless RealityCapture.
- constants: DEFAULT_INCLUDE

### `photogrammetry/realityscan_workflow/_realityscan_connection.py` — Launch connection for RealityScan / RealityCapture.
- `class RealityScanInteractiveError(RuntimeError)`
- `class RealityScanConnection`
  - methods: is_available, is_interactive, epic_signin_active, run

### `photogrammetry/realityscan_workflow/_realityscan_runner.py` — Local, async runner the RealityCapture panel dispatches to.
- `class RealityScanRunner(PyModuleRunner)`
  - methods: exe, is_available

### `photogrammetry/realityscan_workflow/_realityscan_workflow.py` — RealityCapture / RealityScan workflow engine.
- constants: IMAGE_EXTS, QC_REPORT_TEMPLATE, APP, DEFAULT_GATES
- `class RealityCaptureWorkflow(WorkflowEngine, PrepStagesMixin, MeshStagesMixin, _RealityCaptureWorkflowInternal)`
  - methods: find_realitycapture_exe, is_realitycapture_available, get_realitycapture_version, get_image_filepaths, get_license_info, create_chunk, add_images, add_image_dirs, triage_images, align_photos, align_photos_with_retry, refine_alignment, dedupe_cameras_by_pose, calibrate_colors, generate_masks, import_masks, generate_depth_maps, build_model, clean_mesh, simplify_model, reduce_overlap, import_model, build_texture, save_project, export_model, export_qc, finalize_run

### `photogrammetry/realityscan_workflow/_rsnode_client.py` — RSNode REST client — drive a running RealityScan 2.1 over its REST API (headless).
- `class RsNodeError(RuntimeError)`
- `class RsNodeClient`
  - methods: normalize_commands, connect, node_status, create_session, run_commands, upload_file, list_files, download_file, project_status, tags, has_tag, wait_for_tag, tasks, wait_for_task, save_project, open_project, close_project

### `photogrammetry/realityscan_workflow/_rsnode_connection.py` — RSNode-backed connection — drive a running RealityScan 2.1 over REST.
- constants: DEFAULT_RSNODE_URL
- `class RsNodeConnection`
  - methods: is_available, close, run

### `photogrammetry/realityscan_workflow/run_combined.py` — Driver script for multi-session combined RealityCapture runs.
- `publish_outputs(project_dir: str, publish_dir: str)`
- `main(argv=None) -> int`

### `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py` — SuGaR mesh-extraction workflow engine.
- `class SugarMeshWorkflow(WorkflowEngine, _SugarMeshWorkflowInternal)`
  - methods: find_sugar_dir, is_sugar_available, get_sugar_info, extract_mesh

### `photogrammetry/sugar_mesh_workflow/run_combined.py` — Driver for the **EXPERIMENTAL** SuGaR mesh track: COLMAP dataset → textured ``.obj``.
- `main(argv=None) -> int`

### `substance_workflow/__init__.py` — Create a Substance Painter project from a mesh and bake lighting into base color.
- constants: DEFAULT_INCLUDE

### `substance_workflow/bake_utils.py` — Bake operations — iray-backed mesh-map bakes and lighting composites.
- `lighting_to_diffuse(texture_set: Optional[str] = None, bake_resolution: int = 1024, ao_intensity: float = 1.0, ao_secondary_rays: int = 64, ao_max_distance: float = 1.0, ao_min_distance: float = 0.0, ao_spread_angle: float = 162.0, ao_subsample: int = 1, include_curvature: bool = False, curvature_intensity: float = 0.3, layer_name: str = 'iray AO Lighting', blend_mode: str = 'Multiply', skip_existing_bakes: bool = False, save_project: bool = False) -> dict`
- `mesh_maps(texture_set: str, maps: Optional[List[str]] = None, high_poly: Optional[str] = None) -> dict`
- `all_texture_sets(maps: Optional[List[str]] = None) -> dict`
- `set_resolution(texture_set: str, width: int, height: int) -> None`

### `substance_workflow/channel_utils.py` — Channel operations — query and modify per-channel state on a texture set.
- `list_formats() -> List[str]`
- `format(texture_set: str, channel: str) -> str`
- `set_format(texture_set: str, channel: str, fmt: str) -> None`
- `export_path(texture_set: str, channel: str) -> str`

### `substance_workflow/env_utils/painter_connection.py` — Painter Connection Module.
- `class PainterConnection`
  - methods: op_timeout, plugins_dir, build_painter_env, launch_painter, get_instance, is_connected, get_available_port, connect, client, invoke, describe, shutdown

### `substance_workflow/env_utils/painter_finder.py` — Locate installed Substance 3D Painter.
- `class PainterFinder`
  - methods: default_install_roots, find_installs, resolve

### `substance_workflow/export_utils.py` — Texture export operations — drive ``substance_painter.export``.
- `list_presets() -> List[str]`
- `textures(output_path: str, preset: str, texture_sets: Optional[List[str]] = None, file_format: str = 'png', bit_depth: int = 8) -> dict`
- `preset_to_dict(preset: str) -> dict`

### `substance_workflow/job.py` — Batch convenience: launch Painter, run a call list over the bridge, shut down.
- `class Job`
  - methods: add, run, run_batch

### `substance_workflow/layer_utils.py` — Layer stack operations — list, add, remove, reorder, set properties.
- `list_(texture_set: str) -> List[dict]`
- `add_fill(texture_set: str, name: str, color: Optional[List[float]] = None) -> str`
- `add_paint(texture_set: str, name: str) -> str`
- `add_group(texture_set: str, name: str) -> str`
- `delete(texture_set: str, uid: str) -> None`
- `set_opacity(texture_set: str, uid: str, channel: str, opacity: float) -> None`
- `set_blend_mode(texture_set: str, uid: str, channel: str, mode: str) -> None`

### `substance_workflow/material_utils.py` — Smart-material / preset operations — apply shelf materials onto layers.
- `list_shelf() -> List[dict]`
- `apply_smart(texture_set: str, material_url: str, target_layer_uid: Optional[str] = None) -> str`
- `import_to_shelf(path: str, shelf_name: str = 'your_assets') -> str`

### `substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py` — substance_workflow_bridge — Painter-side Python plugin.
- `start_plugin() -> None`
- `close_plugin() -> None`
- constants: OP_MODULES

### `substance_workflow/project_utils.py` — Project-level operations — open, save, close, info, mesh swap.
- `info() -> dict`
- `open_(path: str) -> dict`
- `save() -> dict`
- `save_as(path: str) -> dict`
- `close() -> dict`
- `create(mesh_path: str, template_path: Optional[str] = None) -> dict`
- `reload_mesh(mesh_path: str) -> dict`

### `substance_workflow/registry.py` — Op registry — the callable Painter surface, on the shared RPC core.
- constants: PLUGIN

### `substance_workflow/resource_utils.py` — Shelf / resource operations — query and import shelf assets.
- `list_shelves() -> List[str]`
- `list_assets(shelf: str, kind: str = 'smartmaterial') -> List[dict]`
- `import_(path: str, shelf: str = 'your_assets', kind: str = 'smartmaterial') -> str`

### `substance_workflow/texture_set_utils.py` — Texture set operations — list, resolution, channel inventory.
- `list_() -> List[str]`
- `resolution(name: str) -> List[int]`
- `set_resolution(name: str, width: int, height: int) -> None`
- `channels(name: str) -> List[str]`
- `add_channel(name: str, channel: str, fmt: str = 'sRGB8') -> None`

### `texture_maps/converter/__init__.py` — The Map Converter's batch rules: plan, name and run one map at a time.
- constants: DEFAULT_INCLUDE

### `texture_maps/converter/_converter.py` — The Map Converter's batch engine: plan, name and run one map at a time.
- `class MapConverter`
  - methods: resolve_affix, is_abs_dest, folder_name, output_collisions, resolve_dest, rename_target_path, optimize_one, report_optimize_plan, flip_one
