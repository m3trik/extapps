# extapps — API Changes

_Diff vs prior baseline. Generated 2026-05-30._

## Added (7)

- `photogrammetry/gaussian_splat_workflow/_sugar_mesh.py::SugarMeshWorkflow(class)`
- `photogrammetry/gaussian_splat_workflow/_sugar_mesh.py::SugarMeshWorkflow.extract_mesh(self, colmap_dir: str, regularization: str = 'dn_consistency', high_poly: bool = True, refinement_time: str = 'short', surface_level: float = 0.3, export_obj: bool = True, export_ply: bool = False, use_eval_split: bool = False, gpu: int = 0, white_background: bool = False) -> Optional[str]`
- `photogrammetry/gaussian_splat_workflow/_sugar_mesh.py::SugarMeshWorkflow.finalize_run(self, success: bool = True) -> str`
- `photogrammetry/gaussian_splat_workflow/_sugar_mesh.py::SugarMeshWorkflow.get_sugar_info(self) -> str`
- `photogrammetry/gaussian_splat_workflow/_sugar_mesh.py::find_sugar_dir() -> Optional[str]`
- `photogrammetry/gaussian_splat_workflow/_sugar_mesh.py::is_sugar_available() -> bool`
- `photogrammetry/metashape_workflow/_metashape_workflow.py::MetashapeWorkflow.export_colmap(self, output_dir: str, convert_to_pinhole: bool = True, binary: bool = True, max_cameras: int = 0) -> Optional[str]`
