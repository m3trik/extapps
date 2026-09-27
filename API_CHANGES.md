# extapps — API Changes

_Diff vs the last release (origin/main @ 645d2e2)._

## Removed (27)

- `marmoset_workflow/parameters.py::defaults` — was `() -> 'dict[str, Any]'`
- `marmoset_workflow/parameters.py::referenced_keys` — was `(script_text: str) -> 'set[str]'`
- `marmoset_workflow/parameters.py::render_context` — was `(values: 'dict[str, Any]') -> 'dict[str, str]'`
- `photogrammetry/gaussian_splat_workflow/parameters.py::defaults` — was `() -> 'Dict[str, Any]'`
- `photogrammetry/gaussian_splat_workflow/parameters.py::referenced_keys` — was `(source: str = '') -> 'set[str]'`
- `photogrammetry/gaussian_splat_workflow/parameters.py::to_argv` — was `(values: 'Dict[str, Any]') -> 'List[str]'`
- `photogrammetry/metashape_workflow/parameters.py::defaults` — was `() -> 'Dict[str, Any]'`
- `photogrammetry/metashape_workflow/parameters.py::referenced_keys` — was `(source: str = '') -> 'set[str]'`
- `photogrammetry/metashape_workflow/parameters.py::to_argv` — was `(values: 'Dict[str, Any]') -> 'List[str]'`
- `photogrammetry/realityscan_workflow/parameters.py::defaults` — was `() -> 'Dict[str, Any]'`
- `photogrammetry/realityscan_workflow/parameters.py::referenced_keys` — was `(source: str = '') -> 'set[str]'`
- `photogrammetry/realityscan_workflow/parameters.py::to_argv` — was `(values: 'Dict[str, Any]') -> 'List[str]'`
- `substance_workflow/job.py::Call.to_dict` — was `(self) -> dict`
- `substance_workflow/plugins/substance_workflow_bridge/server.py::BridgeServer` — was `(class)`
- `substance_workflow/plugins/substance_workflow_bridge/server.py::BridgeServer.start` — was `(self) -> int`
- `substance_workflow/plugins/substance_workflow_bridge/server.py::BridgeServer.stop` — was `(self) -> None`
- `substance_workflow/plugins/substance_workflow_bridge/server.py::MARSHALLER` — was `(constant)`
- `substance_workflow/plugins/substance_workflow_bridge/server.py::call_on_main_thread` — was `(func, *args, **kwargs)`
- `substance_workflow/plugins/substance_workflow_bridge/server.py::dispatch_request` — was `(path: str, payload: dict, executor=None) -> tuple`
- `substance_workflow/registry.py::all_ops` — was `() -> Dict[str, Callable]`
- `substance_workflow/registry.py::describe` — was `(name: str = '') -> dict`
- `substance_workflow/registry.py::get` — was `(name: str) -> Optional[Callable]`
- `substance_workflow/registry.py::register` — was `(name: Optional[str] = None) -> Callable`
- `unity_workflow/parameters.py::defaults` — was `() -> 'dict[str, Any]'`
- `unity_workflow/parameters.py::referenced_keys` — was `(script_text: str) -> 'set[str]'`
- `unity_workflow/parameters.py::render_context` — was `(values: 'dict[str, Any]') -> 'dict[str, str]'`
- `webxr_preview/parameters.py::defaults` — was `() -> 'dict[str, Any]'`

## Added (35)

- `_panel_launcher.py::PanelLauncher(class)`
- `marmoset_workflow/parameters.py::Parameters(class)`
- `photogrammetry/_workflow_engine.py::WorkflowEngine(class)`
- `photogrammetry/_workflow_engine.py::WorkflowEngine.finalize_run(self, success: bool = True) -> str`
- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::BRUSH_APP(constant)`
- `photogrammetry/gaussian_splat_workflow/_splat_publish.py::SPLAT_TRANSFORM_APP(constant)`
- `photogrammetry/gaussian_splat_workflow/parameters.py::Parameters(class)`
- `photogrammetry/gaussian_splat_workflow/parameters.py::Parameters.referenced_keys(cls, source: str = '') -> 'set[str]'`
- `photogrammetry/gaussian_splat_workflow/parameters.py::Parameters.to_argv(values: 'Dict[str, Any]') -> 'List[str]'`
- `photogrammetry/metashape_workflow/_metashape_connection.py::APP(constant)`
- `photogrammetry/metashape_workflow/parameters.py::Parameters(class)`
- `photogrammetry/metashape_workflow/parameters.py::Parameters.referenced_keys(cls, source: str = '') -> 'set[str]'`
- `photogrammetry/metashape_workflow/parameters.py::Parameters.to_argv(values: 'Dict[str, Any]') -> 'List[str]'`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::APP(constant)`
- `photogrammetry/realityscan_workflow/parameters.py::Parameters(class)`
- `photogrammetry/realityscan_workflow/parameters.py::Parameters.referenced_keys(cls, source: str = '') -> 'set[str]'`
- `photogrammetry/realityscan_workflow/parameters.py::Parameters.to_argv(values: 'Dict[str, Any]') -> 'List[str]'`
- `substance_workflow/env_utils/painter_connection.py::PainterConnection.client(self) -> RpcClient`
- `substance_workflow/registry.py::PLUGIN(constant)`
- `texture_maps/converter/_converter.py::MapConverter(class)`
- `texture_maps/converter/_converter.py::MapConverter.flip_one(cls, path, *, swizzle_map, invert_dests, suffix)`
- `texture_maps/converter/_converter.py::MapConverter.folder_name(cls, text: str) -> str`
- `texture_maps/converter/_converter.py::MapConverter.is_abs_dest(text: str) -> bool`
- `texture_maps/converter/_converter.py::MapConverter.optimize_one(cls, texture_path, *, file_type, max_size, secondary_scale, mode, modifier, new_folder, old_folder, registry, dry_run=False, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None)`
- `texture_maps/converter/_converter.py::MapConverter.output_collisions(cls, paths, file_type, folder, profile=None)`
- `texture_maps/converter/_converter.py::MapConverter.rename_target_path(cls, texture_path, *, file_type, mode, modifier, output_dir)`
- `texture_maps/converter/_converter.py::MapConverter.report_optimize_plan(cls, texture_path, *, file_type, max_size, mode, modifier, output_dir, old_folder, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None)`
- `texture_maps/converter/_converter.py::MapConverter.resolve_affix(mode: str, modifier: str) -> Tuple[str, str]`
- `texture_maps/converter/_converter.py::MapConverter.resolve_dest(cls, directory: str, folder: str) -> str`
- `unity_workflow/_unity_panel.py::UnityPanelMixin(class)`
- `unity_workflow/_unity_panel.py::UnityPanelMixin.default_output_dir(self) -> str`
- `unity_workflow/_unity_panel.py::UnityPanelMixin.list_template_modes(self)`
- `unity_workflow/_unity_panel.py::UnityPanelMixin.template_dir(self) -> Path`
- `unity_workflow/parameters.py::Parameters(class)`
- `webxr_preview/parameters.py::Parameters(class)`

## Deprecations (1)

_Live retirement debt, earliest deadline first. An **EXPIRED** row has outlived its window: delete the alias and its tests rather than moving the date. A **HELD** row is due by version, but its notice has not yet had its calendar window._

- `texture_maps/converter/slots.py::ConverterSlots.resolve_affix` — remove in 0.4.0, not before 2026-10-26

## Moved (8)

_Still resolvable at the same call site -- hoisted to a base class or re-exported from another module. NOT a removal: no alias or minor bump is owed._

- `photogrammetry/gaussian_splat_workflow/_gaussian_splat_workflow.py::GaussianSplatWorkflow.finalize_run`
- `photogrammetry/gaussian_splat_workflow/_splat_publish.py::SplatPublishWorkflow.finalize_run`
- `photogrammetry/metashape_workflow/_metashape_workflow.py::MetashapeWorkflow.finalize_run`
- `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py::SugarMeshWorkflow.finalize_run`
- `substance_workflow/job.py::Call`
- `substance_workflow/job.py::Result`
- `unity_workflow/slots.py::UnityWorkflowSlots.list_template_modes`
- `unity_workflow/slots.py::UnityWorkflowSlots.template_dir`

## Signature changed (3)

- `photogrammetry/profile.py::Profile.resolve_app`
  - was: `(env_var: str, config_key: Optional[str] = None, *, validate: Optional[Callable[[str], bool]] = None, fallbacks: Sequence[Callable[[], Optional[str]]] = (), path=None) -> Optional[str]`
  - now: `(env_var: str, config_key: Optional[str] = None, *, validate: Optional[Callable[[str], bool]] = None, spec=None, fallbacks: Sequence[Callable[[], Optional[str]]] = (), path=None) -> Optional[str]`
- `substance_workflow/env_utils/painter_connection.py::PainterConnection.describe`
  - was: `(self, op: str = '') -> dict`
  - now: `(self, op: str = '') -> Any`
- `substance_workflow/job.py::Job.run_batch`
  - was: `(calls: List[Call], gui: bool = False, app_path: Optional[str] = None, timeout: float = 180.0, launch_args: Optional[List[str]] = None, invoke_timeout: float = 60.0) -> List[Result]`
  - now: `(calls: List[Call], gui: bool = False, app_path: Optional[str] = None, timeout: float = 180.0, launch_args: Optional[List[str]] = None, invoke_timeout: Optional[float] = None) -> List[Result]`
