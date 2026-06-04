# extapps — API Registry

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_api_registry.py`._

_Generated: 2026-05-30_

## Index

- [`map_compositor/launcher.py`](#map_compositor--launcher) — Application shell for the Map Compositor UI.
- [`map_compositor/slots.py`](#map_compositor--slots) — UI slot bindings for the map_compositor window.
- [`map_converter/launcher.py`](#map_converter--launcher) — Application shell for the Map Converter UI.
- [`map_converter/slots.py`](#map_converter--slots) — Map Converter UI — slot file for ``map_converter.ui``.
- [`map_packer/launcher.py`](#map_packer--launcher) — Application shell for the Map Packer UI.
- [`map_packer/slots.py`](#map_packer--slots)
- [`marmoset_workflow/launcher.py`](#marmoset_workflow--launcher) — Application shell for the Marmoset Workflow UI.
- [`marmoset_workflow/parameters.py`](#marmoset_workflow--parameters) — Tunable parameters surfaced in the Marmoset Workflow panel.
- [`marmoset_workflow/slots.py`](#marmoset_workflow--slots) — Slots for the standalone Marmoset Workflow panel.
- [`mesh_convert/launcher.py`](#mesh_convert--launcher) — Application shell for the Mesh Convert UI.
- [`mesh_convert/slots.py`](#mesh_convert--slots)
- [`photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py`](#photogrammetry--gaussian_splat_workflow--_gaussian_splat_workflow) — Brush gaussian-splat workflow engine.
- [`photogrammetry/gaussian_splat_workflow/_sugar_mesh.py`](#photogrammetry--gaussian_splat_workflow--_sugar_mesh) — SuGaR mesh-extraction workflow engine.
- [`photogrammetry/gaussian_splat_workflow/run_combined.py`](#photogrammetry--gaussian_splat_workflow--run_combined) — Driver for the gaussian-splat track: Brush splat and/or SuGaR mesh.
- [`photogrammetry/metashape_workflow/_metashape_connection.py`](#photogrammetry--metashape_workflow--_metashape_connection) — Headless launch connection for Agisoft Metashape.
- [`photogrammetry/metashape_workflow/_metashape_workflow.py`](#photogrammetry--metashape_workflow--_metashape_workflow)
- [`photogrammetry/metashape_workflow/launcher.py`](#photogrammetry--metashape_workflow--launcher) — Application shell for the Metashape Workflow UI.
- [`photogrammetry/metashape_workflow/run_combined.py`](#photogrammetry--metashape_workflow--run_combined) — Driver script for multi-session combined runs.
- [`photogrammetry/metashape_workflow/slots.py`](#photogrammetry--metashape_workflow--slots)
- [`photogrammetry/prep_stages.py`](#photogrammetry--prep_stages) — Shared, SDK-agnostic input-prep stages for the photogrammetry engines.
- [`photogrammetry/profile.py`](#photogrammetry--profile) — Photogrammetry I/O + tuning **profile** — site/personal config kept out of source.
- [`photogrammetry/realityscan_workflow/_realityscan_connection.py`](#photogrammetry--realityscan_workflow--_realityscan_connection) — Launch connection for RealityScan / RealityCapture.
- [`photogrammetry/realityscan_workflow/_realityscan_workflow.py`](#photogrammetry--realityscan_workflow--_realityscan_workflow) — RealityCapture / RealityScan workflow engine.
- [`photogrammetry/realityscan_workflow/run_combined.py`](#photogrammetry--realityscan_workflow--run_combined) — Driver script for multi-session combined RealityCapture runs.
- [`substance_workflow/bake_utils.py`](#substance_workflow--bake_utils) — Bake operations — iray-backed mesh-map bakes and lighting composites.
- [`substance_workflow/channel_utils.py`](#substance_workflow--channel_utils) — Channel operations — query and modify per-channel state on a texture set.
- [`substance_workflow/env_utils/painter_connection.py`](#substance_workflow--env_utils--painter_connection) — Painter Connection Module.
- [`substance_workflow/env_utils/painter_finder.py`](#substance_workflow--env_utils--painter_finder) — Locate installed Substance 3D Painter.
- [`substance_workflow/export_utils.py`](#substance_workflow--export_utils) — Texture export operations — drive ``substance_painter.export``.
- [`substance_workflow/job.py`](#substance_workflow--job) — Job spec + batch convenience wrapper.
- [`substance_workflow/launcher.py`](#substance_workflow--launcher) — Application shell for the Substance Workflow UI.
- [`substance_workflow/layer_utils.py`](#substance_workflow--layer_utils) — Layer stack operations — list, add, remove, reorder, set properties.
- [`substance_workflow/material_utils.py`](#substance_workflow--material_utils) — Smart-material / preset operations — apply shelf materials onto layers.
- [`substance_workflow/plugins/substance_workflow_bridge/__init__.py`](#substance_workflow--plugins--substance_workflow_bridge--__init__) — substance_workflow_bridge — Painter-side Python plugin.
- [`substance_workflow/plugins/substance_workflow_bridge/server.py`](#substance_workflow--plugins--substance_workflow_bridge--server) — Live-mode HTTP bridge — runs inside Painter, dispatches ops on the main thread.
- [`substance_workflow/project_utils.py`](#substance_workflow--project_utils) — Project-level operations — open, save, close, info, mesh swap.
- [`substance_workflow/registry.py`](#substance_workflow--registry) — Op registry — single source of truth for callable Painter operations.
- [`substance_workflow/resource_utils.py`](#substance_workflow--resource_utils) — Shelf / resource operations — query and import shelf assets.
- [`substance_workflow/slots.py`](#substance_workflow--slots) — Switchboard slots for the Substance Workflow UI.
- [`substance_workflow/texture_set_utils.py`](#substance_workflow--texture_set_utils) — Texture set operations — list, resolution, channel inventory.

---

<a id="map_compositor--launcher"></a>
### `map_compositor/launcher.py`

Application shell for the Map Compositor UI.

- **[`class MapCompositorUI`](extapps/extapps/map_compositor/launcher.py#L18)**

<a id="map_compositor--slots"></a>
### `map_compositor/slots.py`

UI slot bindings for the map_compositor window.

- **[`class MapCompositorSlots`](extapps/extapps/map_compositor/slots.py#L50)** — UI slot handler.
  - `MapCompositorSlots.removeNormalMap(self) -> bool` *(property)*
  - `MapCompositorSlots.removeNormalMap(self, value: bool) -> None`
  - `MapCompositorSlots.input_dir(self) -> str` *(property)*
  - `MapCompositorSlots.output_dir(self) -> str` *(property)*
  - `MapCompositorSlots.map_name(self) -> str` *(property)*
  - `MapCompositorSlots.header_init(self, widget)` — Populate the header menu with global options.
  - `MapCompositorSlots.txt000_init(self, widget)` — Init Source Directory
  - `MapCompositorSlots.txt001_init(self, widget)` — Init Destination Directory
  - `MapCompositorSlots.txt002_init(self, widget)` — Init Map Name
  - `MapCompositorSlots.b002(self)` — Combine Maps
  - `MapCompositorSlots.process(self, images, input_dir, output_dir, map_name=None)` — Validate dirs, prepare sorted-image groups, and drive the engine.

<a id="map_converter--launcher"></a>
### `map_converter/launcher.py`

Application shell for the Map Converter UI.

- **[`class MapConverterUI`](extapps/extapps/map_converter/launcher.py#L18)** — Standalone launcher.

<a id="map_converter--slots"></a>
### `map_converter/slots.py`

Map Converter UI — slot file for ``map_converter.ui``.

- **[`class MapConverterSlots(ImgUtils)`](extapps/extapps/map_converter/slots.py#L32)** — Switchboard slots for ``map_converter.ui``.
  - `MapConverterSlots.source_dir(self)` *(property)* — Get the starting directory for file dialogs.
  - `MapConverterSlots.source_dir(self, value)` — Set the starting directory for file dialogs.
  - `MapConverterSlots.texture_provider(self)` *(property)* — Callable returning a list of texture paths from the host DCC selection.
  - `MapConverterSlots.texture_provider(self, fn)`
  - `MapConverterSlots.footer_init(self, widget)` — Add the global Use-Selection toggle to the footer.
  - `MapConverterSlots.tb000_init(self, widget)` — Populate the Optimize toolbutton's option menu (format, clamp, modifier).
  - `MapConverterSlots.tb000(self, widget)` — Optimize a texture map(s)
  - `MapConverterSlots.tb001_init(self, widget)`
  - `MapConverterSlots.tb001(self, widget)` — Batch converts Spec/Gloss maps to PBR Metal/Rough using MapFactory.
  - `MapConverterSlots.tb003_init(self, widget)` — Initialize a 'Bump to Normal' toolbutton with options.
  - `MapConverterSlots.tb003(self, widget)` — Bump/Height to Normal converter (single entry point with options).
  - `MapConverterSlots.b000(self)` — Convert DirectX to OpenGL
  - `MapConverterSlots.b001(self)` — Convert OpenGL to DirectX
  - `MapConverterSlots.b004(self)` — Batch pack Transparency into Albedo across texture sets.
  - `MapConverterSlots.b005(self)` — Batch pack Smoothness or Roughness into Metallic across texture sets.
  - `MapConverterSlots.b006(self)` — Unpack Metallic and Smoothness maps from MetallicSmoothness textures.
  - `MapConverterSlots.b007(self)` — Unpack Specular and Gloss maps from SpecularGloss textures.
  - `MapConverterSlots.b008_init(self, widget)` — Populate the MSAO pack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b008(self, widget)` — Batch pack Metallic, AO, and Smoothness/Roughness into an MSAO texture.
  - `MapConverterSlots.b009_init(self, widget)` — Populate the MSAO unpack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b009(self, widget)` — Unpack Metallic, AO, and Smoothness maps from MSAO textures.
  - `MapConverterSlots.b013_init(self, widget)` — Populate the MRAO pack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b013(self, widget)` — Batch pack Metallic, Roughness/Smoothness, and AO into an MRAO texture.
  - `MapConverterSlots.b014_init(self, widget)` — Populate the MRAO unpack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b014(self, widget)` — Unpack Metallic, Roughness, and AO from MRAO textures.
  - `MapConverterSlots.b015(self)` — Batch pack AO, Roughness/Smoothness, and Metallic into an ORM texture.
  - `MapConverterSlots.b016(self)` — Unpack AO, Roughness, and Metallic from ORM textures.
  - `MapConverterSlots.b010(self)` — Convert Smoothness maps to Roughness maps.
  - `MapConverterSlots.b011(self)` — Convert Roughness maps to Smoothness maps.
  - `MapConverterSlots.b012(self)` — Batch prepare textures for PBR workflow using MapFactory.

<a id="map_packer--launcher"></a>
### `map_packer/launcher.py`

Application shell for the Map Packer UI.

- **[`class MapPackerUI`](extapps/extapps/map_packer/launcher.py#L17)**

<a id="map_packer--slots"></a>
### `map_packer/slots.py`

- **[`class MapPackerSlots(ImgUtils)`](extapps/extapps/map_packer/slots.py#L9)**
  - `MapPackerSlots.header_init(self, widget)` — Configure the header menu with presets for common packed map types.
  - `MapPackerSlots.source_dir(self)` *(property)*
  - `MapPackerSlots.source_dir(self, value)`
  - `MapPackerSlots.b000(self)` — Batch pack up to 4 channels into RGBA maps across texture sets.
  - `MapPackerSlots.b001(self)` — Open the last output directory in the system file explorer.

<a id="marmoset_workflow--launcher"></a>
### `marmoset_workflow/launcher.py`

Application shell for the Marmoset Workflow UI.

- **[`class MarmosetWorkflowUI`](extapps/extapps/marmoset_workflow/launcher.py#L19)**

<a id="marmoset_workflow--parameters"></a>
### `marmoset_workflow/parameters.py`

Tunable parameters surfaced in the Marmoset Workflow panel.

- [`referenced_keys(script_text: str) -> 'set[str]'`](extapps/extapps/marmoset_workflow/parameters.py#L63) — Registered keys present in *script_text* (delegates to uitk.bridge).
- [`defaults() -> 'dict[str, Any]'`](extapps/extapps/marmoset_workflow/parameters.py#L68) — Return ``{key: default}`` for every registered parameter.
- [`render_context(values: 'dict[str, Any]') -> 'dict[str, str]'`](extapps/extapps/marmoset_workflow/parameters.py#L73) — Format *values* for ``StrUtils.replace_delimited`` using Python literals.

<a id="marmoset_workflow--slots"></a>
### `marmoset_workflow/slots.py`

Slots for the standalone Marmoset Workflow panel.

- **[`class MarmosetWorkflowSlots(BridgeSlotsBase)`](extapps/extapps/marmoset_workflow/slots.py#L45)** — Switchboard slots wired to ``marmoset_workflow.ui``.
  - `MarmosetWorkflowSlots.params_module(self)` *(property)*
  - `MarmosetWorkflowSlots.template_dir(self) -> Path` *(property)*
  - `MarmosetWorkflowSlots.make_bridge(self) -> MarmosetEngine`
  - `MarmosetWorkflowSlots.list_template_modes(self) -> List[Tuple[str, str]]` — Engine templates filtered to the 'set up a project' subset.
  - `MarmosetWorkflowSlots.select_initial_template_index(self, pairs: List[Tuple[str, str]]) -> int` — Prefer 'lookdev (send_to)', else first entry.
  - `MarmosetWorkflowSlots.resolved_model_path(self) -> str`
  - `MarmosetWorkflowSlots.header_init(self, widget) -> None` — Configure the header menu with utilities + help text.
  - `MarmosetWorkflowSlots.b000(self) -> None` — Set up the picked model in Toolbag using the chosen template + mode.

<a id="mesh_convert--launcher"></a>
### `mesh_convert/launcher.py`

Application shell for the Mesh Convert UI.

- **[`class MeshConvertUI`](extapps/extapps/mesh_convert/launcher.py#L17)**

<a id="mesh_convert--slots"></a>
### `mesh_convert/slots.py`

- **[`class MeshConvertSlots(MeshConvert)`](extapps/extapps/mesh_convert/slots.py#L13)** — Switchboard slots for the Mesh Converter UI.
  - `MeshConvertSlots.source_dir(self) -> str` *(property)* — Starting directory for the FBX file dialog.
  - `MeshConvertSlots.source_dir(self, value: str) -> None`
  - `MeshConvertSlots.fbx_provider(self) -> Optional[Callable[[], Iterable[str]]]` *(property)* — Callable returning FBX paths from the host DCC selection.
  - `MeshConvertSlots.fbx_provider(self, fn: Optional[Callable[[], Iterable[str]]]) -> None`
  - `MeshConvertSlots.header_init(self, widget) -> None` — Add the From-FBX-references toggle to the header menu.
  - `MeshConvertSlots.tb000_init(self, widget) -> None` — Set up the FBX -> GLB tool button option box.
  - `MeshConvertSlots.tb000(self, widget) -> None` — Convert the selected FBX file(s) to GLB beside their source.

<a id="photogrammetry--gaussian_splat_workflow--_gaussian_splat_workflow"></a>
### `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py`

Brush gaussian-splat workflow engine.

- [`find_brush_exe() -> Optional[str]`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L39) — Return the Brush executable path or None.
- [`is_brush_available() -> bool`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L55)
- [`read_splat_count(ply_path: str) -> Optional[int]`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L59) — Gaussian count from a splat ``.ply`` header (``element vertex N``).
- **[`class GaussianSplatWorkflow`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py#L74)** — Wrapper around Brush's CLI for COLMAP-dataset -> 3DGS ``.ply``.
  - `GaussianSplatWorkflow.get_brush_info(self) -> str`
  - `GaussianSplatWorkflow.train(self, colmap_dir: str, total_steps: int = 30000, max_resolution: int = 1920, max_splats: int = 10000000, sh_degree: int = 3, growth_grad_threshold: Optional[float] = None, growth_select_fraction: Optional[float] = None, export_path: Optional[str] = None, export_name: Optional[str] = None, export_every: Optional[int] = None, eval_split_every: Optional[int] = None, eval_every: Optional[int] = None, eval_save_to_disk: bool = False) -> Optional[str]` — Train a splat from a COLMAP dataset;
  - `GaussianSplatWorkflow.finalize_run(self, success: bool = True) -> str`

<a id="photogrammetry--gaussian_splat_workflow--_sugar_mesh"></a>
### `photogrammetry/gaussian_splat_workflow/_sugar_mesh.py`

SuGaR mesh-extraction workflow engine.

- [`find_sugar_dir() -> Optional[str]`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_sugar_mesh.py#L50) — Return the SuGaR repo dir or None.
- [`is_sugar_available() -> bool`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_sugar_mesh.py#L69)
- **[`class SugarMeshWorkflow`](extapps/extapps/photogrammetry/gaussian_splat_workflow/_sugar_mesh.py#L73)** — COLMAP dataset → SuGaR refined textured ``.obj`` mesh.
  - `SugarMeshWorkflow.get_sugar_info(self) -> str`
  - `SugarMeshWorkflow.extract_mesh(self, colmap_dir: str, regularization: str = 'dn_consistency', high_poly: bool = True, refinement_time: str = 'short', surface_level: float = 0.3, export_obj: bool = True, export_ply: bool = False, use_eval_split: bool = False, gpu: int = 0, white_background: bool = False) -> Optional[str]` — Run SuGaR's full pipeline on a COLMAP dataset;
  - `SugarMeshWorkflow.finalize_run(self, success: bool = True) -> str`

<a id="photogrammetry--gaussian_splat_workflow--run_combined"></a>
### `photogrammetry/gaussian_splat_workflow/run_combined.py`

Driver for the gaussian-splat track: Brush splat and/or SuGaR mesh.

- [`main(argv=None) -> int`](extapps/extapps/photogrammetry/gaussian_splat_workflow/run_combined.py#L40)

<a id="photogrammetry--metashape_workflow--_metashape_connection"></a>
### `photogrammetry/metashape_workflow/_metashape_connection.py`

Headless launch connection for Agisoft Metashape.

- **[`class MetashapeConnection`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_connection.py#L34)** — Discover + headlessly drive ``metashape.exe -r <script>`` from any host.
  - `MetashapeConnection.find_exe() -> Optional[str]` *(static)* — Locate ``metashape.exe``: ``$METASHAPE_EXE`` → :meth:`AppLauncher.find_app`
  - `MetashapeConnection.is_available(self) -> bool` — True if a metashape.exe was found (i.e.
  - `MetashapeConnection.run_script(self, script_path: str, args: Optional[Sequence[str]] = None, cwd: Optional[str] = None, timeout: Optional[float] = None, log_file: Optional[str] = None, env: Optional[dict] = None)` — Run a Python *script* inside Metashape headless via ``-r``.
  - `MetashapeConnection.run_combined(self, args: Optional[Sequence[str]] = None, **kwargs)` — Convenience: drive this package's ``run_combined`` workflow headless.

<a id="photogrammetry--metashape_workflow--_metashape_workflow"></a>
### `photogrammetry/metashape_workflow/_metashape_workflow.py`

- [`is_metashape_available() -> bool`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L38) — True if the Metashape Python module imported successfully.
- [`is_license_valid() -> bool`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L43) — True if a valid Metashape license is reachable.
- [`get_metashape_version() -> str`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L53)
- [`get_image_filepaths(directory: str) -> List[str]`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L1108) — Return absolute paths to all images in `directory` (non-recursive).
- **[`class MetashapeWorkflow(PrepStagesMixin)`](extapps/extapps/photogrammetry/metashape_workflow/_metashape_workflow.py#L62)** — Wrapper around Agisoft Metashape's Python API for the standard
  - `MetashapeWorkflow.get_license_info(self) -> str`
  - `MetashapeWorkflow.create_chunk(self, label: str = 'New Chunk')`
  - `MetashapeWorkflow.add_images(self, image_sources: Union[str, Sequence[str]])` — Add images from a directory path (non-recursive) or list of paths.
  - `MetashapeWorkflow.add_image_dirs(self, dirs: Sequence[str])` — Add images from multiple directories — flattens to one chunk.
  - `MetashapeWorkflow.clean_mesh_advanced(self, exported_model_path: Optional[str] = None, decimate_target_faces: int = 0) -> Optional[str]` — PyMeshLab post-export polish on the exported mesh file.
  - `MetashapeWorkflow.triage_images(self, quality_threshold: float = 0.5)` — Run ``analyzePhotos`` and disable cameras below ``quality_threshold``.
  - `MetashapeWorkflow.align_photos(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 100000, tiepoint_limit: int = 10000, filter_mask: bool = False)`
  - `MetashapeWorkflow.align_photos_with_retry(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 100000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0)` — Run ``align_photos``;
  - `MetashapeWorkflow.refine_alignment(self, uncertainty_threshold: float = 15.0, reprojection_threshold: float = 0.5, projection_accuracy_threshold: float = 3.0)` — Gradual-selection cleanup: iteratively filter tie points by
  - `MetashapeWorkflow.dedupe_cameras_by_pose(self, translation_threshold: float = 0.02, rotation_threshold_deg: float = 2.0)` — Cluster aligned cameras by pose and disable redundants.
  - `MetashapeWorkflow.calibrate_colors(self, source_data=None, white_balance: bool = True)` — Run ``chunk.calibrateColors`` to equalize white-balance across
  - `MetashapeWorkflow.generate_masks(self, source_dir: str, masks_dir: Optional[str] = None, model_name: str = 'u2net') -> Optional[str]` — Run rembg on ``source_dir`` → write per-image alpha masks.
  - `MetashapeWorkflow.import_masks(self, masks_dir: str, mask_source: str = 'file', template: str = '{filename}_mask.png')` — Import per-camera masks from a directory.
  - `MetashapeWorkflow.generate_depth_maps(self, downscale: int = 2, filter_mode=None)`
  - `MetashapeWorkflow.build_model(self, source_data=None, surface_type=None, interpolation=None, face_count=None)`
  - `MetashapeWorkflow.clean_mesh(self, remove_components_face_threshold: int = 100, close_holes_level: int = 30, smooth_strength: int = 0)` — Mesh cleanup chain: ``removeComponents → closeHoles → smoothModel``.
  - `MetashapeWorkflow.reduce_overlap(self, target_overlap: int = 9)` — Thin redundant cameras for texture bake while preserving
  - `MetashapeWorkflow.build_texture(self, texture_size: int = 4096, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter: bool = True)`
  - `MetashapeWorkflow.save_project(self)`
  - `MetashapeWorkflow.export_model(self, export_format=None, binary: bool = True, precision: int = 6, texture_format=None, save_texture: bool = True, save_normals: bool = True, save_colors: bool = True, save_cameras: bool = False, overwrite: bool = True)`
  - `MetashapeWorkflow.export_colmap(self, output_dir: str, convert_to_pinhole: bool = True, binary: bool = True, max_cameras: int = 0) -> Optional[str]` — Export the aligned chunk as a COLMAP dataset to feed the splat track.
  - `MetashapeWorkflow.export_qc(self)` — Write Metashape's processing report PDF + finalize the JSON sidecar.
  - `MetashapeWorkflow.finalize_run(self, success: bool = True) -> str` — Write the QC JSON sidecar.

<a id="photogrammetry--metashape_workflow--launcher"></a>
### `photogrammetry/metashape_workflow/launcher.py`

Application shell for the Metashape Workflow UI.

- **[`class MetashapeWorkflowUI`](extapps/extapps/photogrammetry/metashape_workflow/launcher.py#L19)**

<a id="photogrammetry--metashape_workflow--run_combined"></a>
### `photogrammetry/metashape_workflow/run_combined.py`

Driver script for multi-session combined runs.

- [`main(argv=None) -> int`](extapps/extapps/photogrammetry/metashape_workflow/run_combined.py#L65)

<a id="photogrammetry--metashape_workflow--slots"></a>
### `photogrammetry/metashape_workflow/slots.py`

- **[`class MetashapeWorkflowSlots(ptk.LoggingMixin)`](extapps/extapps/photogrammetry/metashape_workflow/slots.py#L194)** — Switchboard slots for the Metashape Workflow UI.
  - `MetashapeWorkflowSlots.header_init(self, widget) -> None`
  - `MetashapeWorkflowSlots.txt000_init(self, widget) -> None` — Project Directory
  - `MetashapeWorkflowSlots.txt000(self, widget) -> None`
  - `MetashapeWorkflowSlots.txt001_init(self, widget) -> None` — Project Name
  - `MetashapeWorkflowSlots.txt002_init(self, widget) -> None` — Frames Directory
  - `MetashapeWorkflowSlots.txt002(self, widget) -> None`
  - `MetashapeWorkflowSlots.cmb000_init(self, widget) -> None` — Preset
  - `MetashapeWorkflowSlots.btn_stages_init(self, widget) -> None` — Pipeline-stages popup — QMenu of checkboxes attached to the button.
  - `MetashapeWorkflowSlots.btn_advanced_init(self, widget) -> None` — Advanced-params popup — labeled form inside a QMenu via QWidgetAction.
  - `MetashapeWorkflowSlots.b000(self) -> None` — Run Workflow
  - `MetashapeWorkflowSlots.cmb003(self, widget) -> None` — Log level changed
  - `MetashapeWorkflowSlots.btn_browse_project(self) -> None`
  - `MetashapeWorkflowSlots.btn_explore_project(self) -> None`
  - `MetashapeWorkflowSlots.btn_browse_frames(self) -> None`
  - `MetashapeWorkflowSlots.btn_explore_frames(self) -> None`
  - `MetashapeWorkflowSlots.btn_extract_frames(self) -> None` — Extract frames from a video file into the frames directory.

<a id="photogrammetry--prep_stages"></a>
### `photogrammetry/prep_stages.py`

Shared, SDK-agnostic input-prep stages for the photogrammetry engines.

- **[`class PrepStagesMixin`](extapps/extapps/photogrammetry/prep_stages.py#L23)** — Curate + equalize stages shared by both photogrammetry engines.
  - `PrepStagesMixin.curate_input_set(self, source_dirs: Sequence[str], output_root: Optional[str] = None, hash_threshold: int = 5, sharpness_floor: float = 0.0, sharpness_floor_percentile: Optional[float] = None, min_sharpness_fraction_of_median: float = 0.0, keep_per_cluster: int = 1) -> List[str]` — Pre-SfM content + sharpness culling via :class:`pythontk.ImageCurator`.
  - `PrepStagesMixin.preview_curation(self, source_dirs: Sequence[str], hash_thresholds: Sequence[int] = (5, 8, 10, 12, 15), keep_per_cluster: int = 1, sharpness_floor_percentile: Optional[float] = None, min_sharpness_fraction_of_median: float = 0.0)` — Dry-run curation QC — report survivor counts per dHash threshold + the
  - `PrepStagesMixin.equalize_exposures(self, source_dirs: Sequence[str], output_root: Optional[str] = None, reference_dir: Optional[str] = None, strength: float = 1.0, reference_strategy: str = 'first') -> List[str]` — Cross-set exposure / WB equalization via :class:`pythontk.ExposureEqualizer`.

<a id="photogrammetry--profile"></a>
### `photogrammetry/profile.py`

Photogrammetry I/O + tuning **profile** — site/personal config kept out of source.

- [`get_profile(path=None) -> dict`](extapps/extapps/photogrammetry/profile.py#L142) — Resolve the active photogrammetry profile (fully interpolated).
- [`init_user_profile(path: Optional[str] = None, force: bool = False) -> str`](extapps/extapps/photogrammetry/profile.py#L160) — Write :data:`EXAMPLE_PROFILE` to the user-config location (or *path*).
- [`discover_source_dirs(input_root: str) -> List[str]`](extapps/extapps/photogrammetry/profile.py#L178) — Return immediate subdirs of ``input_root`` that contain images.

<a id="photogrammetry--realityscan_workflow--_realityscan_connection"></a>
### `photogrammetry/realityscan_workflow/_realityscan_connection.py`

Launch connection for RealityScan / RealityCapture.

- **[`class RealityScanInteractiveError(RuntimeError)`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_connection.py#L32)** — An RC run needs an interactive, Epic-signed-in desktop session that is not
- **[`class RealityScanConnection`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_connection.py#L37)** — Discover + drive the RealityScan/RealityCapture CLI, interactive-aware.
  - `RealityScanConnection.is_available(self) -> bool`
  - `RealityScanConnection.is_interactive() -> bool` *(static)* — True if the current process can host RC's window (session != 0).
  - `RealityScanConnection.epic_signin_active() -> bool` *(static)* — Heuristic: True if Epic sign-in helpers are running (RC is waiting on
  - `RealityScanConnection.run(self, commands: Sequence[str], log_path: str, timeout: Optional[float] = None, session: Optional[int] = None, poll_interval: float = 5.0) -> subprocess.CompletedProcess` — Run RC as ``[exe] + commands`` (the caller supplies the full CLI tail,

<a id="photogrammetry--realityscan_workflow--_realityscan_workflow"></a>
### `photogrammetry/realityscan_workflow/_realityscan_workflow.py`

RealityCapture / RealityScan workflow engine.

- [`find_realitycapture_exe() -> Optional[str]`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L62) — Return the RealityCapture.exe path or None.
- [`is_realitycapture_available() -> bool`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L83)
- [`get_realitycapture_version() -> str`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L105) — Read RC's FileVersion from Windows binary metadata.
- [`get_image_filepaths(directory: str) -> List[str]`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L117) — Return absolute paths to all images in ``directory`` (non-recursive).
- **[`class RealityCaptureWorkflow(PrepStagesMixin)`](extapps/extapps/photogrammetry/realityscan_workflow/_realityscan_workflow.py#L131)** — Wrapper around RealityCapture's CLI for the standard photogrammetry
  - `RealityCaptureWorkflow.get_license_info(self) -> str`
  - `RealityCaptureWorkflow.create_chunk(self, label: str = 'New Chunk')` — Start a fresh RC scene.
  - `RealityCaptureWorkflow.add_images(self, image_sources: Union[str, Sequence[str]])` — Add images from a directory (non-recursive) or list of paths.
  - `RealityCaptureWorkflow.add_image_dirs(self, dirs: Sequence[str])` — Add images from multiple directories — RC keeps them in one scene.
  - `RealityCaptureWorkflow.triage_images(self, quality_threshold: float = 0.5)` — No direct RC equivalent.
  - `RealityCaptureWorkflow.align_photos(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 100000, tiepoint_limit: int = 10000, filter_mask: bool = False)` — Run RC alignment (SfM).
  - `RealityCaptureWorkflow.align_photos_with_retry(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 100000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0)` — Run alignment;
  - `RealityCaptureWorkflow.refine_alignment(self, *args, **kwargs)` — RC performs alignment refinement internally during ``-align``;
  - `RealityCaptureWorkflow.dedupe_cameras_by_pose(self, *args, **kwargs)` — No direct RC equivalent.
  - `RealityCaptureWorkflow.calibrate_colors(self, *args, **kwargs)` — RC applies color correction inside ``-calculateTexture`` via
  - `RealityCaptureWorkflow.generate_masks(self, source_dir: str, masks_dir: Optional[str] = None, model_name: str = 'u2net') -> Optional[str]` — Run rembg on ``source_dir`` → write per-image alpha masks.
  - `RealityCaptureWorkflow.import_masks(self, masks_dir: str, mask_source: str = 'alpha')` — RC accepts per-image masks named ``<image>.png`` next to the
  - `RealityCaptureWorkflow.generate_depth_maps(self, *args, **kwargs)` — RC does not expose depth maps as a separate stage — mesh calc
  - `RealityCaptureWorkflow.build_model(self, source_data=None, surface_type=None, interpolation=None, face_count: Optional[str] = None)` — Build a polygon mesh.
  - `RealityCaptureWorkflow.clean_mesh(self, remove_components_face_threshold: int = 100, close_holes_level: int = 30, smooth_strength: int = 0)` — Mesh cleanup.
  - `RealityCaptureWorkflow.simplify_model(self, target_face_count: int = 20000000)` — Simplify the densest model to ~``target_face_count`` triangles.
  - `RealityCaptureWorkflow.reduce_overlap(self, *args, **kwargs)` — No RC equivalent.
  - `RealityCaptureWorkflow.import_model(self, mesh_path: str)` — Import an external low-poly mesh into the project (Maya-authored
  - `RealityCaptureWorkflow.build_texture(self, texture_size: int = 4096, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter: bool = True)` — Unwrap (when no mesh was imported) + bake texture from solved
  - `RealityCaptureWorkflow.save_project(self)` — RC saves on every CLI call (``-save`` is appended);
  - `RealityCaptureWorkflow.export_model(self, export_format: Optional[str] = None, binary: bool = True, precision: int = 6, texture_format=None, save_texture: bool = True, save_normals: bool = True, save_colors: bool = True, save_cameras: bool = False, overwrite: bool = True)` — Export the current model.
  - `RealityCaptureWorkflow.export_qc(self)` — Export RC's processing report XML and append to the QC log.
  - `RealityCaptureWorkflow.finalize_run(self, success: bool = True) -> str` — Flush the QC JSON sidecar.

<a id="photogrammetry--realityscan_workflow--run_combined"></a>
### `photogrammetry/realityscan_workflow/run_combined.py`

Driver script for multi-session combined RealityCapture runs.

- [`main(argv=None) -> int`](extapps/extapps/photogrammetry/realityscan_workflow/run_combined.py#L66)

<a id="substance_workflow--bake_utils"></a>
### `substance_workflow/bake_utils.py`

Bake operations — iray-backed mesh-map bakes and lighting composites.

- [`lighting_to_diffuse(texture_set: Optional[str] = None, bake_resolution: int = 1024, ao_intensity: float = 1.0, ao_secondary_rays: int = 64, ao_max_distance: float = 1.0, ao_min_distance: float = 0.0, ao_spread_angle: float = 162.0, ao_subsample: int = 1, include_curvature: bool = False, curvature_intensity: float = 0.3, layer_name: str = 'iray AO Lighting', blend_mode: str = 'Multiply', skip_existing_bakes: bool = False, save_project: bool = False) -> dict`](extapps/extapps/substance_workflow/bake_utils.py#L138) — Bake iray-backed AO (+ optional curvature) and composite onto base color.
- [`mesh_maps(texture_set: str, maps: Optional[List[str]] = None, high_poly: Optional[str] = None) -> dict`](extapps/extapps/substance_workflow/bake_utils.py#L257) — Bake the named mesh maps.
- [`all_texture_sets(maps: Optional[List[str]] = None) -> dict`](extapps/extapps/substance_workflow/bake_utils.py#L270) — Bake mesh maps for every texture set in the project.
- [`set_resolution(texture_set: str, width: int, height: int) -> None`](extapps/extapps/substance_workflow/bake_utils.py#L276) — Set the baking resolution for the named texture set.

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

- [`plugins_dir() -> str`](extapps/extapps/substance_workflow/env_utils/painter_connection.py#L36) — Absolute path to the ``substance_workflow/plugins`` directory.
- [`build_painter_env(port: int = 0) -> dict`](extapps/extapps/substance_workflow/env_utils/painter_connection.py#L47) — Compose the environment block passed to a Painter launch.
- [`launch_painter(exe: str, env: dict, gui: bool = False, extra_args: Optional[List[str]] = None) -> subprocess.Popen`](extapps/extapps/substance_workflow/env_utils/painter_connection.py#L65) — Spawn a detached Painter process via ``pythontk.AppLauncher``.
- **[`class PainterConnection`](extapps/extapps/substance_workflow/env_utils/painter_connection.py#L86)** — Live JSON-RPC connection to a Substance 3D Painter session.
  - `PainterConnection.get_instance(cls) -> 'PainterConnection'` *(class)*
  - `PainterConnection.get_available_port(start_port: int = 5050, max_check: int = 100) -> int` *(static)* — Return the lowest unused TCP port in the requested range on localhost.
  - `PainterConnection.connect(self, force_new_instance: bool = True, gui: bool = False, port: int = 5050, app_path: Optional[str] = None, launch_args: Optional[List[str]] = None, timeout: float = 180.0) -> bool` — Launch a fresh Painter and connect over the bridge HTTP server.
  - `PainterConnection.invoke(self, op: str, timeout: float = 60.0, **kwargs: Any) -> Any` — Call a registered op over the bridge and return its value.
  - `PainterConnection.describe(self, op: str = '') -> dict` — Fetch the registry's signature description for agent self-discovery.
  - `PainterConnection.shutdown(self, force: bool = False) -> None` — Close the bridge and terminate the Painter process we launched.

<a id="substance_workflow--env_utils--painter_finder"></a>
### `substance_workflow/env_utils/painter_finder.py`

Locate installed Substance 3D Painter.

- **[`class PainterFinder`](extapps/extapps/substance_workflow/env_utils/painter_finder.py#L16)** — Helper to locate Substance 3D Painter installations.
  - `PainterFinder.default_install_roots() -> List[str]` *(static)*
  - `PainterFinder.find_installs() -> Dict[str, str]` *(static)* — Return ``{label: exe_path}`` for every Painter install found.
  - `PainterFinder.resolve(version_or_path: Optional[str] = None) -> Optional[str]` *(static)* — Resolve an executable path.

<a id="substance_workflow--export_utils"></a>
### `substance_workflow/export_utils.py`

Texture export operations — drive ``substance_painter.export``.

- [`list_presets() -> List[str]`](extapps/extapps/substance_workflow/export_utils.py#L9) — Return user + built-in export preset names.
- [`textures(output_path: str, preset: str, texture_sets: Optional[List[str]] = None, file_format: str = 'png', bit_depth: int = 8) -> dict`](extapps/extapps/substance_workflow/export_utils.py#L15) — Export textures using ``preset``.
- [`preset_to_dict(preset: str) -> dict`](extapps/extapps/substance_workflow/export_utils.py#L30) — Return the export-preset definition as a dict for inspection.

<a id="substance_workflow--job"></a>
### `substance_workflow/job.py`

Job spec + batch convenience wrapper.

- [`run_batch(calls: List[Call], gui: bool = False, app_path: Optional[str] = None, timeout: float = 180.0, launch_args: Optional[List[str]] = None, invoke_timeout: float = 60.0) -> List[Result]`](extapps/extapps/substance_workflow/job.py#L49) — Launch Painter, execute ``calls`` in order over the bridge, shut down.
- **[`class Call`](extapps/extapps/substance_workflow/job.py#L18)**
  - `Call.to_dict(self) -> dict`
- **[`class Result`](extapps/extapps/substance_workflow/job.py#L27)**
- **[`class Job`](extapps/extapps/substance_workflow/job.py#L36)** — Convenience builder — ``Job().add("project.info").run()``.
  - `Job.add(self, op: str, **kwargs: Any) -> 'Job'`
  - `Job.run(self, **launch_kwargs: Any) -> List[Result]`

<a id="substance_workflow--launcher"></a>
### `substance_workflow/launcher.py`

Application shell for the Substance Workflow UI.

- **[`class SubstanceWorkflowUI`](extapps/extapps/substance_workflow/launcher.py#L18)**

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

<a id="substance_workflow--plugins--substance_workflow_bridge--__init__"></a>
### `substance_workflow/plugins/substance_workflow_bridge/__init__.py`

substance_workflow_bridge — Painter-side Python plugin.

- [`start_plugin() -> None`](extapps/extapps/substance_workflow/plugins/substance_workflow_bridge/__init__.py#L56) — Painter plugin entry point — start the JSON-RPC bridge server.
- [`close_plugin() -> None`](extapps/extapps/substance_workflow/plugins/substance_workflow_bridge/__init__.py#L70) — Painter plugin teardown.

<a id="substance_workflow--plugins--substance_workflow_bridge--server"></a>
### `substance_workflow/plugins/substance_workflow_bridge/server.py`

Live-mode HTTP bridge — runs inside Painter, dispatches ops on the main thread.

- [`call_on_main_thread(func, *args, **kwargs)`](extapps/extapps/substance_workflow/plugins/substance_workflow_bridge/server.py#L26) — Marshal ``func`` onto Painter's main Qt event loop and block until done.
- [`dispatch_request(path: str, payload: dict, executor=None) -> tuple`](extapps/extapps/substance_workflow/plugins/substance_workflow_bridge/server.py#L51) — Pure dispatch: route ``(path, payload)`` and return ``(status, body)``.
- **[`class BridgeServer`](extapps/extapps/substance_workflow/plugins/substance_workflow_bridge/server.py#L106)**
  - `BridgeServer.start(self) -> int`
  - `BridgeServer.stop(self) -> None`

<a id="substance_workflow--project_utils"></a>
### `substance_workflow/project_utils.py`

Project-level operations — open, save, close, info, mesh swap.

- [`info() -> dict`](extapps/extapps/substance_workflow/project_utils.py#L14) — Return basic info about the current project, or ``{'open': False}``.
- [`open_(path: str) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L28) — Open an existing ``.spp`` project.
- [`save() -> dict`](extapps/extapps/substance_workflow/project_utils.py#L37) — Save the current project to its existing path.
- [`save_as(path: str) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L46) — Save the current project to ``path``.
- [`close() -> dict`](extapps/extapps/substance_workflow/project_utils.py#L55) — Close the current project without saving.
- [`create(mesh_path: str, template_path: Optional[str] = None) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L64) — Create a new project from a mesh.
- [`reload_mesh(mesh_path: str) -> dict`](extapps/extapps/substance_workflow/project_utils.py#L77) — Reimport the project's mesh from ``mesh_path``.

<a id="substance_workflow--registry"></a>
### `substance_workflow/registry.py`

Op registry — single source of truth for callable Painter operations.

- [`register(name: Optional[str] = None) -> Callable`](extapps/extapps/substance_workflow/registry.py#L19) — Decorator: register a function as an op.
- [`get(name: str) -> Optional[Callable]`](extapps/extapps/substance_workflow/registry.py#L39)
- [`all_ops() -> Dict[str, Callable]`](extapps/extapps/substance_workflow/registry.py#L43)
- [`describe(name: str = '') -> dict`](extapps/extapps/substance_workflow/registry.py#L47) — Return op signature + docstring for agent self-discovery.

<a id="substance_workflow--resource_utils"></a>
### `substance_workflow/resource_utils.py`

Shelf / resource operations — query and import shelf assets.

- [`list_shelves() -> List[str]`](extapps/extapps/substance_workflow/resource_utils.py#L9) — Return the names of all configured shelves.
- [`list_assets(shelf: str, kind: str = 'smartmaterial') -> List[dict]`](extapps/extapps/substance_workflow/resource_utils.py#L15) — List assets of ``kind`` on ``shelf``.
- [`import_(path: str, shelf: str = 'your_assets', kind: str = 'smartmaterial') -> str`](extapps/extapps/substance_workflow/resource_utils.py#L21) — Import an asset file into the named shelf.

<a id="substance_workflow--slots"></a>
### `substance_workflow/slots.py`

Switchboard slots for the Substance Workflow UI.

- **[`class SubstanceWorkflowSlots(ptk.LoggingMixin)`](extapps/extapps/substance_workflow/slots.py#L91)** — Switchboard slots for the Substance Workflow UI.
  - `SubstanceWorkflowSlots.header_init(self, widget) -> None`
  - `SubstanceWorkflowSlots.txt000_init(self, widget) -> None` — Mesh File
  - `SubstanceWorkflowSlots.txt001_init(self, widget) -> None` — Template (optional)
  - `SubstanceWorkflowSlots.txt002_init(self, widget) -> None` — Project Save Path
  - `SubstanceWorkflowSlots.cmb000_init(self, widget) -> None` — Painter install picker
  - `SubstanceWorkflowSlots.btn_stages_init(self, widget) -> None` — Stages popup — QMenu of checkboxes attached to the button.
  - `SubstanceWorkflowSlots.btn_advanced_init(self, widget) -> None` — Advanced-params popup — labeled form inside a QMenu via QWidgetAction.
  - `SubstanceWorkflowSlots.cmb003(self, widget) -> None` — Log level changed
  - `SubstanceWorkflowSlots.btn_launch(self, widget) -> None` — Toggle the Painter session.
  - `SubstanceWorkflowSlots.b000(self) -> None` — Run Workflow
  - `SubstanceWorkflowSlots.btn_browse_mesh(self) -> None`
  - `SubstanceWorkflowSlots.btn_browse_template(self) -> None`
  - `SubstanceWorkflowSlots.btn_browse_project(self) -> None`

<a id="substance_workflow--texture_set_utils"></a>
### `substance_workflow/texture_set_utils.py`

Texture set operations — list, resolution, channel inventory.

- [`list_() -> List[str]`](extapps/extapps/substance_workflow/texture_set_utils.py#L9) — Return the names of all texture sets in the current project.
- [`resolution(name: str) -> List[int]`](extapps/extapps/substance_workflow/texture_set_utils.py#L15) — Return ``[width, height]`` of the named texture set.
- [`set_resolution(name: str, width: int, height: int) -> None`](extapps/extapps/substance_workflow/texture_set_utils.py#L21) — Set the texture set resolution.
- [`channels(name: str) -> List[str]`](extapps/extapps/substance_workflow/texture_set_utils.py#L27) — Return the channel identifiers active on the named texture set.
- [`add_channel(name: str, channel: str, fmt: str = 'sRGB8') -> None`](extapps/extapps/substance_workflow/texture_set_utils.py#L33) — Add a channel to the texture set (``BaseColor``, ``Roughness``, ...).
