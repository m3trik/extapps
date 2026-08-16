# extapps — API Changes

_Diff vs the last release (origin/main @ 9c263b5). Generated 2026-08-16._

## Removed (29)

- `photogrammetry/_shared_params.py::preprocessing_argv` — was `(values: 'Dict[str, Any]') -> 'List[str]'`
- `photogrammetry/_shared_params.py::render_flag_argv` — was `(values: 'Dict[str, Any]', value_flags: 'Dict[str, str]', store_true_flags: 'Optional[Dict[str, str]]' = None, bool_flags: 'Optional[Dict[str, str]]' = None) -> 'List[str]'`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::find_brush_exe` — was `() -> Optional[str]`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::install_brush` — was `(progress_callback: Optional[Callable[[int, int], None]] = None) -> str`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::is_brush_available` — was `() -> bool`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::read_splat_count` — was `(ply_path: str) -> Optional[int]`
- `photogrammetry/gaussian_splat_workflow/_splat_publish.py::find_splat_transform` — was `() -> Optional[str]`
- `photogrammetry/gaussian_splat_workflow/_splat_publish.py::is_splat_transform_available` — was `() -> bool`
- `photogrammetry/metashape_workflow/_metashape_workflow.py::MetashapeWorkflow.clean_mesh_advanced` — was `(self, exported_model_path: Optional[str] = None, decimate_target_faces: int = 0) -> Optional[str]`
- `photogrammetry/prep_stages.py::derive_texture_size` — was `(image_path: Optional[str], floor: int = 2048, cap: int = 8192, default: int = 8192) -> int`
- `photogrammetry/prep_stages.py::extract_videos_to_dir` — was `(videos: Sequence[str], output_dir: str, *, window_sec: float = 1.0, quality: int = 95, log: Optional[Callable[[str], None]] = None) -> List[str]`
- `photogrammetry/prep_stages.py::first_image_in_dirs` — was `(dirs: Sequence[str]) -> Optional[str]`
- `photogrammetry/prep_stages.py::image_long_edge` — was `(image_path: str) -> Optional[int]`
- `photogrammetry/profile.py::configured_app_path` — was `(key: str, path=None) -> Optional[str]`
- `photogrammetry/profile.py::discover_source_dirs` — was `(input_root: str) -> List[str]`
- `photogrammetry/profile.py::get_preset` — was `(name: Optional[str], engine: str) -> dict`
- `photogrammetry/profile.py::get_profile` — was `(path=None) -> dict`
- `photogrammetry/profile.py::init_user_profile` — was `(path: Optional[str] = None, force: bool = False) -> str`
- `photogrammetry/profile.py::preset_store` — was `(engine: str) -> PresetStore`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::find_realitycapture_exe` — was `() -> Optional[str]`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::get_image_filepaths` — was `(directory: str) -> List[str]`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::get_realitycapture_version` — was `() -> str`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::is_realitycapture_available` — was `() -> bool`
- `photogrammetry/realityscan_workflow/_rsnode_client.py::normalize_commands` — was `(commands: Sequence[CommandLike]) -> List[Dict[str, Any]]`
- `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py::find_sugar_dir` — was `() -> Optional[str]`
- `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py::is_sugar_available` — was `() -> bool`
- `substance_workflow/env_utils/painter_connection.py::build_painter_env` — was `(port: int = 0) -> dict`
- `substance_workflow/env_utils/painter_connection.py::launch_painter` — was `(exe: str, env: dict, gui: bool = False, extra_args: Optional[List[str]] = None) -> subprocess.Popen`
- `substance_workflow/env_utils/painter_connection.py::plugins_dir` — was `() -> str`

## Added (37)

- `photogrammetry/_shared_params.py::SharedParams(class)`
- `photogrammetry/_shared_params.py::SharedParams.preprocessing_argv(values: 'Dict[str, Any]') -> 'List[str]'`
- `photogrammetry/_shared_params.py::SharedParams.render_flag_argv(values: 'Dict[str, Any]', value_flags: 'Dict[str, str]', store_true_flags: 'Optional[Dict[str, str]]' = None, bool_flags: 'Optional[Dict[str, str]]' = None) -> 'List[str]'`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::GaussianSplatWorkflow.find_brush_exe() -> Optional[str]`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::GaussianSplatWorkflow.install_brush(progress_callback: Optional[Callable[[int, int], None]] = None) -> str`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::GaussianSplatWorkflow.is_brush_available() -> bool`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::GaussianSplatWorkflow.read_splat_count(ply_path: str) -> Optional[int]`
- `photogrammetry/gaussian_splat_workflow/_splat_publish.py::SplatPublishWorkflow.find_splat_transform() -> 'Optional[str]'`
- `photogrammetry/gaussian_splat_workflow/_splat_publish.py::SplatPublishWorkflow.is_splat_transform_available() -> bool`
- `photogrammetry/mesh_stages.py::MeshStagesMixin(class)`
- `photogrammetry/mesh_stages.py::MeshStagesMixin.bake_vertex_color(self, model_path: Optional[str] = None, output_path: Optional[str] = None, texture_size: int = 1024) -> Optional[Tuple[str, str]]`
- `photogrammetry/mesh_stages.py::MeshStagesMixin.clean_mesh_advanced(self, exported_model_path: Optional[str] = None, decimate_target_faces: int = 0) -> Optional[str]`
- `photogrammetry/mesh_stages.py::MeshStagesMixin.measure_mesh(self, model_path: Optional[str] = None) -> Optional[Dict[str, Any]]`
- `photogrammetry/mesh_stages.py::MeshStagesMixin.refine_mesh(self, model_path: Optional[str] = None, output_path: Optional[str] = None, remesh_target_pct: float = 0.0, decimate_target_faces: int = 0, curvature_weighted: bool = True, compare_deviation: bool = True) -> Optional[str]`
- `photogrammetry/mesh_stages.py::MeshStagesMixin.run_mesh_stages(self, model_path: Optional[str] = None, remesh_target_pct: float = 0.0, decimate_target_faces: int = 0, bake_texture_size: int = 0) -> Optional[str]`
- `photogrammetry/prep_stages.py::PrepStagesMixin.derive_texture_size(image_path: Optional[str], floor: int = 2048, cap: int = 8192, default: int = 8192) -> int`
- `photogrammetry/prep_stages.py::PrepStagesMixin.extract_videos_to_dir(videos: Sequence[str], output_dir: str, *, window_sec: float = 1.0, quality: int = 95, log: Optional[Callable[[str], None]] = None) -> List[str]`
- `photogrammetry/prep_stages.py::PrepStagesMixin.first_image_in_dirs(dirs: Sequence[str]) -> Optional[str]`
- `photogrammetry/prep_stages.py::PrepStagesMixin.image_long_edge(image_path: str) -> Optional[int]`
- `photogrammetry/profile.py::Profile(class)`
- `photogrammetry/profile.py::Profile.configured_app_path(key: str, path=None) -> Optional[str]`
- `photogrammetry/profile.py::Profile.discover_source_dirs(input_root: str) -> List[str]`
- `photogrammetry/profile.py::Profile.get_preset(name: Optional[str], engine: str) -> dict`
- `photogrammetry/profile.py::Profile.get_profile(path=None) -> dict`
- `photogrammetry/profile.py::Profile.init_user_profile(path: Optional[str] = None, force: bool = False) -> str`
- `photogrammetry/profile.py::Profile.preset_store(engine: str) -> PresetStore`
- `photogrammetry/profile.py::Profile.resolve_app(env_var: str, config_key: Optional[str] = None, *, validate: Optional[Callable[[str], bool]] = None, fallbacks: Sequence[Callable[[], Optional[str]]] = (), path=None) -> Optional[str]`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::RealityCaptureWorkflow.find_realitycapture_exe() -> Optional[str]`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::RealityCaptureWorkflow.get_image_filepaths(directory: str) -> List[str]`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::RealityCaptureWorkflow.get_realitycapture_version() -> str`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::RealityCaptureWorkflow.is_realitycapture_available() -> bool`
- `photogrammetry/realityscan_workflow/_rsnode_client.py::RsNodeClient.normalize_commands(commands: Sequence[CommandLike]) -> List[Dict[str, Any]]`
- `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py::SugarMeshWorkflow.find_sugar_dir() -> 'Optional[str]'`
- `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py::SugarMeshWorkflow.is_sugar_available() -> bool`
- `substance_workflow/env_utils/painter_connection.py::PainterConnection.build_painter_env(port: int = 0) -> dict`
- `substance_workflow/env_utils/painter_connection.py::PainterConnection.launch_painter(exe: str, env: dict, gui: bool = False, extra_args: Optional[List[str]] = None) -> subprocess.Popen`
- `substance_workflow/env_utils/painter_connection.py::PainterConnection.plugins_dir() -> str`
