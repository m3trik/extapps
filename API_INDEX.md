# extapps — API Index

_Auto-generated. Do not edit by hand. Compact symbol index — grep this for a name; for full signatures/docs, slice [API_REGISTRY.md](API_REGISTRY.md) (never Read it whole)._

_Generated: 2026-07-18_

### `marmoset_workflow/_marmoset_engine.py` — Drive Marmoset Toolbag from the outside -- launch + templated automation.
- `list_templates() -> List[Path]`
- `template_modes(template_path: Path) -> Tuple[str, ...]`
- `list_template_modes() -> List[Tuple[str, str]]`
- `class MarmosetEngine(ptk.Deliverer, ptk.LoggingMixin)`
  - methods: toolbag_path, toolbag_log_path, preflight, deliver, send, render_template

### `marmoset_workflow/_toolbag_helpers.py` — Shared helpers for Marmoset Toolbag template scripts.
- `derive_per_run_log_path(manifest_path)`
- `begin_log(reference_path)`
- `log(msg)`
- `find_material(name, scene_mats)`
- `load_manifest(manifest_path)`
- `wire_materials_from_manifest(manifest_path, verbose=True)`
- `split_high_low(objects, high_suffix, low_suffix, pre_classified=None)`
- `collect_mesh_objects(root)`
- `apply_sky_preset(preset_path)`
- `frame_in_viewport()`

### `marmoset_workflow/launcher.py` — Application shell for the Marmoset Workflow UI.
- `class MarmosetWorkflowUI`

### `marmoset_workflow/parameters.py` — Tunable parameters surfaced in the Marmoset Workflow panel.
- `referenced_keys(script_text: str) -> 'set[str]'`
- `defaults() -> 'dict[str, Any]'`
- `render_context(values: 'dict[str, Any]') -> 'dict[str, str]'`

### `marmoset_workflow/slots.py` — Slots for the standalone Marmoset Workflow panel.
- `class MarmosetWorkflowSlots(BridgeSlotsBase)`
  - methods: params_module, template_dir, make_bridge, list_template_modes, select_initial_template_index, resolved_model_path, set_model_path, b000

### `marmoset_workflow/template_params.py` — Plain default values + literal formatting for Marmoset template tokens.
- `python_literal(value: Any) -> str`
- `defaults() -> Dict[str, Any]`
- `to_context(values: Dict[str, Any]) -> Dict[str, str]`

### `marmoset_workflow/templates/import.py` — Open the model in Toolbag and wire materials from the manifest.
- `main()`

### `marmoset_workflow/templates/lookdev.py` — Open the model in Toolbag, apply a Sky preset, and frame the model.
- `main()`

### `marmoset_workflow/toolbag_log.py` — Marmoset Toolbag log-file resolution, classification, and live tailing.
- `resolve_toolbag_log_path(toolbag_exe: Optional[str]) -> Optional[str]`
- `classify_log_line(line: str) -> Optional[Tuple[str, str]]`
- `dispatch_log_lines(lines, logger) -> None`
- `start_toolbag_log_tail(log_path: str, start_offset: int, process, logger, poll_interval: float = 0.4, file_wait_timeout: float = 60.0)`

### `mesh_convert/launcher.py` — Application shell for the Mesh Convert UI.
- `class MeshConvertUI`

### `mesh_convert/slots.py`
- `class MeshConvertSlots(MeshConvert)`
  - methods: source_dir, fbx_provider, header_init, tb000_init, tb000

### `photogrammetry/_panel_slots.py` — Shared scaffolding for the photogrammetry workflow panels.
- `class PhotogrammetryPanelSlots(BridgeSlotsBase)`
  - methods: header_menu_items, make_preset_store, resolved_project_name, cancel_run, open_output_folder, b000
- `class FramesSourceMixin`
  - methods: resolved_frames_dir

### `photogrammetry/_process_runner.py` — Async, log-streaming process runner shared by the photogrammetry panels.
- `class ProcessRunner(ptk.LoggingMixin)`
  - methods: exe, is_available, is_running, start, cancel
- `class PyModuleRunner(ProcessRunner)`

### `photogrammetry/_shared_params.py` — Input pre-processing parameter specs shared by the image-in engines.
- `render_flag_argv(values: 'Dict[str, Any]', value_flags: 'Dict[str, str]', store_true_flags: 'Optional[Dict[str, str]]' = None, bool_flags: 'Optional[Dict[str, str]]' = None) -> 'List[str]'`
- `preprocessing_argv(values: 'Dict[str, Any]') -> 'List[str]'`

### `photogrammetry/gaussian_splat_workflow/_gaussian_splat_runner.py` — Local, async runner the Brush (gaussian-splat) panel dispatches to.
- `class GaussianSplatRunner(PyModuleRunner)`
  - methods: exe, is_available
- `class BrushInstallRunner(PyModuleRunner)`
  - methods: exe, is_available

### `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py` — Brush gaussian-splat workflow engine.
- `find_brush_exe() -> Optional[str]`
- `is_brush_available() -> bool`
- `install_brush(progress_callback: Optional[Callable[[int, int], None]] = None) -> str`
- `read_splat_count(ply_path: str) -> Optional[int]`
- `class GaussianSplatWorkflow`
  - methods: get_brush_info, train, finalize_run

### `photogrammetry/gaussian_splat_workflow/_install_brush.py` — Headless entry point: download + install Brush via pythontk.AppInstaller.
- `main() -> int`

### `photogrammetry/gaussian_splat_workflow/_splat_publish.py` — Engine-delivery stage for the splat track — clean + convert to engine formats.
- `find_splat_transform() -> Optional[str]`
- `is_splat_transform_available() -> bool`
- `class SplatPublishWorkflow`
  - methods: get_publish_info, clean, to_unity, to_web, publish, finalize_run

### `photogrammetry/gaussian_splat_workflow/launcher.py` — Application shell for the Brush (gaussian-splat) Workflow UI.
- `class GaussianSplatWorkflowUI`

### `photogrammetry/gaussian_splat_workflow/parameters.py` — Tunable parameters surfaced in the Brush (gaussian-splat) Workflow panel.
- `to_argv(values: 'Dict[str, Any]') -> 'List[str]'`
- `referenced_keys(source: str = '') -> 'set[str]'`
- `defaults() -> 'Dict[str, Any]'`

### `photogrammetry/gaussian_splat_workflow/run_combined.py` — Driver for the gaussian-splat track: Brush splat training + engine publish.
- `main(argv=None) -> int`

### `photogrammetry/gaussian_splat_workflow/slots.py` — Slots for the Brush (gaussian-splat) Workflow panel.
- `class GaussianSplatWorkflowSlots(PhotogrammetryPanelSlots)`
  - methods: resolved_colmap_dir, params_module, template_dir, make_bridge, header_init, open_brush_viewer, open_result_in_brush, install_brush, cancel_run, list_template_modes, default_output_dir, help_spec

### `photogrammetry/metashape_workflow/_metashape_connection.py` — Headless launch connection for Agisoft Metashape.
- `class MetashapeConnection`
  - methods: find_exe, is_available, run_script, run_combined

### `photogrammetry/metashape_workflow/_metashape_runner.py` — Local, async runner the Metashape panel dispatches to.
- `class MetashapeRunner(ProcessRunner)`
  - methods: exe, is_available, start

### `photogrammetry/metashape_workflow/_metashape_workflow.py`
- `is_metashape_available() -> bool`
- `is_license_valid() -> bool`
- `get_metashape_version() -> str`
- `get_image_filepaths(directory: str) -> List[str]`
- `class MetashapeWorkflow(PrepStagesMixin)`
  - methods: get_license_info, create_chunk, add_images, add_image_dirs, clean_mesh_advanced, triage_images, align_photos, align_photos_with_retry, refine_alignment, dedupe_cameras_by_pose, calibrate_colors, generate_masks, generate_masks_native, import_masks, generate_depth_maps, build_model, clean_mesh, reduce_overlap, build_texture, save_project, export_model, export_colmap, export_qc, finalize_run

### `photogrammetry/metashape_workflow/launcher.py` — Application shell for the Metashape Workflow UI.
- `class MetashapeWorkflowUI`

### `photogrammetry/metashape_workflow/parameters.py` — Tunable parameters surfaced in the Metashape Workflow panel.
- `to_argv(values: 'Dict[str, Any]') -> 'List[str]'`
- `referenced_keys(source: str = '') -> 'set[str]'`
- `defaults() -> 'Dict[str, Any]'`

### `photogrammetry/metashape_workflow/run_combined.py` — Driver script for multi-session combined runs.
- `main(argv=None) -> int`

### `photogrammetry/metashape_workflow/slots.py` — Slots for the Metashape Workflow panel.
- `class MetashapeWorkflowSlots(FramesSourceMixin, PhotogrammetryPanelSlots)`
  - methods: params_module, template_dir, make_bridge, list_template_modes, default_output_dir, help_spec

### `photogrammetry/prep_stages.py` — Shared, SDK-agnostic pipeline stages for the photogrammetry engines.
- `image_long_edge(image_path: str) -> Optional[int]`
- `extract_videos_to_dir(videos: Sequence[str], output_dir: str, *, window_sec: float = 1.0, quality: int = 95, log: Optional[Callable[[str], None]] = None) -> List[str]`
- `first_image_in_dirs(dirs: Sequence[str]) -> Optional[str]`
- `derive_texture_size(image_path: Optional[str], floor: int = 2048, cap: int = 8192, default: int = 8192) -> int`
- `class PrepStagesMixin`
  - methods: curate_input_set, preview_curation, equalize_exposures

### `photogrammetry/profile.py` — Photogrammetry I/O + tuning **profile** — site/personal config kept out of source.
- `get_profile(path=None) -> dict`
- `configured_app_path(key: str, path=None) -> Optional[str]`
- `preset_store(engine: str) -> PresetStore`
- `get_preset(name: Optional[str], engine: str) -> dict`
- `init_user_profile(path: Optional[str] = None, force: bool = False) -> str`
- `discover_source_dirs(input_root: str) -> List[str]`

### `photogrammetry/realityscan_workflow/_realityscan_connection.py` — Launch connection for RealityScan / RealityCapture.
- `class RealityScanInteractiveError(RuntimeError)`
- `class RealityScanConnection`
  - methods: is_available, is_interactive, epic_signin_active, run

### `photogrammetry/realityscan_workflow/_realityscan_runner.py` — Local, async runner the RealityCapture panel dispatches to.
- `class RealityScanRunner(PyModuleRunner)`
  - methods: exe, is_available

### `photogrammetry/realityscan_workflow/_realityscan_workflow.py` — RealityCapture / RealityScan workflow engine.
- `find_realitycapture_exe() -> Optional[str]`
- `is_realitycapture_available() -> bool`
- `get_realitycapture_version() -> str`
- `get_image_filepaths(directory: str) -> List[str]`
- `class RealityCaptureWorkflow(PrepStagesMixin)`
  - methods: get_license_info, create_chunk, add_images, add_image_dirs, triage_images, align_photos, align_photos_with_retry, refine_alignment, dedupe_cameras_by_pose, calibrate_colors, generate_masks, import_masks, generate_depth_maps, build_model, clean_mesh, simplify_model, reduce_overlap, import_model, build_texture, save_project, export_model, export_qc, finalize_run

### `photogrammetry/realityscan_workflow/_rsnode_client.py` — RSNode REST client — drive a running RealityScan 2.1 over its REST API (headless).
- `normalize_commands(commands: Sequence[CommandLike]) -> List[Dict[str, Any]]`
- `class RsNodeError(RuntimeError)`
- `class RsNodeClient`
  - methods: connect, node_status, create_session, run_commands, upload_file, list_files, download_file, project_status, tags, has_tag, wait_for_tag, tasks, wait_for_task, save_project, open_project, close_project

### `photogrammetry/realityscan_workflow/_rsnode_connection.py` — RSNode-backed connection — drive a running RealityScan 2.1 over REST.
- `class RsNodeConnection`
  - methods: is_available, close, run

### `photogrammetry/realityscan_workflow/launcher.py` — Application shell for the RealityCapture Workflow UI.
- `class RealityScanWorkflowUI`

### `photogrammetry/realityscan_workflow/parameters.py` — Tunable parameters surfaced in the RealityCapture Workflow panel.
- `to_argv(values: 'Dict[str, Any]') -> 'List[str]'`
- `referenced_keys(source: str = '') -> 'set[str]'`
- `defaults() -> 'Dict[str, Any]'`

### `photogrammetry/realityscan_workflow/run_combined.py` — Driver script for multi-session combined RealityCapture runs.
- `publish_outputs(project_dir: str, publish_dir: str)`
- `main(argv=None) -> int`

### `photogrammetry/realityscan_workflow/slots.py` — Slots for the RealityCapture Workflow panel.
- `class RealityscanWorkflowSlots(FramesSourceMixin, PhotogrammetryPanelSlots)`
  - methods: params_module, template_dir, make_bridge, list_template_modes, default_output_dir, help_spec

### `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py` — SuGaR mesh-extraction workflow engine.
- `find_sugar_dir() -> Optional[str]`
- `is_sugar_available() -> bool`
- `class SugarMeshWorkflow`
  - methods: get_sugar_info, extract_mesh, finalize_run

### `photogrammetry/sugar_mesh_workflow/run_combined.py` — Driver for the **EXPERIMENTAL** SuGaR mesh track: COLMAP dataset → textured ``.obj``.
- `main(argv=None) -> int`

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
- `plugins_dir() -> str`
- `build_painter_env(port: int = 0) -> dict`
- `launch_painter(exe: str, env: dict, gui: bool = False, extra_args: Optional[List[str]] = None) -> subprocess.Popen`
- `class PainterConnection`
  - methods: get_instance, get_available_port, connect, invoke, describe, shutdown

### `substance_workflow/env_utils/painter_finder.py` — Locate installed Substance 3D Painter.
- `class PainterFinder`
  - methods: default_install_roots, find_installs, resolve

### `substance_workflow/export_utils.py` — Texture export operations — drive ``substance_painter.export``.
- `list_presets() -> List[str]`
- `textures(output_path: str, preset: str, texture_sets: Optional[List[str]] = None, file_format: str = 'png', bit_depth: int = 8) -> dict`
- `preset_to_dict(preset: str) -> dict`

### `substance_workflow/job.py` — Job spec + batch convenience wrapper.
- `run_batch(calls: List[Call], gui: bool = False, app_path: Optional[str] = None, timeout: float = 180.0, launch_args: Optional[List[str]] = None, invoke_timeout: float = 60.0) -> List[Result]`
- `class Call`
  - methods: to_dict
- `class Result`
- `class Job`
  - methods: add, run

### `substance_workflow/launcher.py` — Application shell for the Substance Workflow UI.
- `class SubstanceWorkflowUI`

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

### `substance_workflow/plugins/substance_workflow_bridge/__init__.py` — substance_workflow_bridge — Painter-side Python plugin.
- `start_plugin() -> None`
- `close_plugin() -> None`

### `substance_workflow/plugins/substance_workflow_bridge/server.py` — Live-mode HTTP bridge — runs inside Painter, dispatches ops on the main thread.
- `call_on_main_thread(func, *args, **kwargs)`
- `dispatch_request(path: str, payload: dict, executor=None) -> tuple`
- `class BridgeServer`
  - methods: start, stop

### `substance_workflow/project_utils.py` — Project-level operations — open, save, close, info, mesh swap.
- `info() -> dict`
- `open_(path: str) -> dict`
- `save() -> dict`
- `save_as(path: str) -> dict`
- `close() -> dict`
- `create(mesh_path: str, template_path: Optional[str] = None) -> dict`
- `reload_mesh(mesh_path: str) -> dict`

### `substance_workflow/registry.py` — Op registry — single source of truth for callable Painter operations.
- `register(name: Optional[str] = None) -> Callable`
- `get(name: str) -> Optional[Callable]`
- `all_ops() -> Dict[str, Callable]`
- `describe(name: str = '') -> dict`

### `substance_workflow/resource_utils.py` — Shelf / resource operations — query and import shelf assets.
- `list_shelves() -> List[str]`
- `list_assets(shelf: str, kind: str = 'smartmaterial') -> List[dict]`
- `import_(path: str, shelf: str = 'your_assets', kind: str = 'smartmaterial') -> str`

### `substance_workflow/slots.py` — Switchboard slots for the Substance Workflow UI.
- `class SubstanceWorkflowSlots(ptk.LoggingMixin)`
  - methods: header_init, txt000_init, txt001_init, txt002_init, cmb000_init, btn_stages_init, btn_advanced_init, cmb003, btn_launch, b000, set_mesh_path, btn_browse_mesh, btn_browse_template, btn_browse_project

### `substance_workflow/texture_set_utils.py` — Texture set operations — list, resolution, channel inventory.
- `list_() -> List[str]`
- `resolution(name: str) -> List[int]`
- `set_resolution(name: str, width: int, height: int) -> None`
- `channels(name: str) -> List[str]`
- `add_channel(name: str, channel: str, fmt: str = 'sRGB8') -> None`

### `texture_maps/compositor/launcher.py` — Application shell for the Map Compositor UI.
- `class CompositorUI`

### `texture_maps/compositor/slots.py` — UI slot bindings for the compositor window.
- `class CompositorSlots`
  - methods: output_dir, map_name, header_init, txt000_init, txt001_init, txt002_init, b002, process

### `texture_maps/converter/launcher.py` — Application shell for the Map Converter UI.
- `class ConverterUI`

### `texture_maps/converter/slots.py` — Map Converter UI — slot file for ``converter.ui``.
- `class ConverterSlots(ImgUtils)`
  - methods: source_dir, texture_provider, footer_init, tb000_init, tb000, tb001_init, tb001, tb003_init, tb003, tb002_init, tb002, b000, b001, b004, b007, b010, b011, b012

### `texture_maps/packer/launcher.py` — Application shell for the Map Packer UI.
- `class PackerUI`

### `texture_maps/packer/slots.py`
- `class PackerSlots(ImgUtils)`
  - methods: cmbR_init, cmbG_init, cmbB_init, cmbA_init, cmbFormat_init, header_init, source_dir, b000, b001

### `unity_workflow/launcher.py` — Application shell for the Unity Workflow launcher UI.
- `class UnityWorkflowUI`

### `unity_workflow/parameters.py` — User-tunable parameters for the standalone Unity Workflow panel.
- `referenced_keys(script_text: str) -> 'set[str]'`
- `defaults() -> 'dict[str, Any]'`
- `render_context(values: 'dict[str, Any]') -> 'dict[str, str]'`

### `unity_workflow/slots.py` — Slots for the standalone Unity Workflow panel.
- `class UnityWorkflowSlots(BridgeSlotsBase)`
  - methods: params_module, template_dir, make_bridge, list_template_modes, resolved_model_path, set_model_path, b000
