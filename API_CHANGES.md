# extapps — API Changes

_Diff vs prior baseline. Generated 2026-07-10._

## Added (1)

- `photogrammetry/metashape_workflow/_metashape_workflow.py::MetashapeWorkflow.generate_masks_native(self, tolerance: int = 10) -> bool`

## Signature changed (9)

- `photogrammetry/_shared_params.py::render_flag_argv`
  - was: `(values: 'Dict[str, Any]', value_flags: 'Dict[str, str]', store_true_flags: 'Optional[Dict[str, str]]' = None) -> 'List[str]'`
  - now: `(values: 'Dict[str, Any]', value_flags: 'Dict[str, str]', store_true_flags: 'Optional[Dict[str, str]]' = None, bool_flags: 'Optional[Dict[str, str]]' = None) -> 'List[str]'`
- `photogrammetry/metashape_workflow/_metashape_workflow.py::MetashapeWorkflow.align_photos`
  - was: `(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 40000, tiepoint_limit: int = 10000, filter_mask: bool = False)`
  - now: `(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, filter_mask: bool = False)`
- `photogrammetry/metashape_workflow/_metashape_workflow.py::MetashapeWorkflow.align_photos_with_retry`
  - was: `(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 40000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0)`
  - now: `(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0, filter_mask: bool = False)`
- `photogrammetry/metashape_workflow/_metashape_workflow.py::MetashapeWorkflow.build_texture`
  - was: `(self, texture_size: int = 4096, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter: bool = True)`
  - now: `(self, texture_size: int = 8192, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter: bool = True)`
- `photogrammetry/prep_stages.py::PrepStagesMixin.curate_input_set`
  - was: `(self, source_dirs: Sequence[str], output_root: Optional[str] = None, hash_threshold: int = 5, sharpness_floor: float = 0.0, sharpness_floor_percentile: Optional[float] = None, min_sharpness_fraction_of_median: float = 0.0, keep_per_cluster: int = 1, overcuration_warn_pct: float = 30.0) -> List[str]`
  - now: `(self, source_dirs: Sequence[str], output_root: Optional[str] = None, hash_threshold: int = 0, sharpness_floor: float = 0.0, sharpness_floor_percentile: Optional[float] = None, min_sharpness_fraction_of_median: float = 0.0, keep_per_cluster: int = 1, overcuration_warn_pct: float = 30.0) -> List[str]`
- `photogrammetry/prep_stages.py::PrepStagesMixin.equalize_exposures`
  - was: `(self, source_dirs: Sequence[str], output_root: Optional[str] = None, reference_dir: Optional[str] = None, strength: float = 1.0, reference_strategy: str = 'first') -> List[str]`
  - now: `(self, source_dirs: Sequence[str], output_root: Optional[str] = None, reference_dir: Optional[str] = None, strength: float = 0.5, reference_strategy: str = 'median') -> List[str]`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::RealityCaptureWorkflow.align_photos`
  - was: `(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 100000, tiepoint_limit: int = 10000, filter_mask: bool = False)`
  - now: `(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, filter_mask: bool = False)`
- `photogrammetry/realityscan_workflow/_realityscan_workflow.py::RealityCaptureWorkflow.align_photos_with_retry`
  - was: `(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 100000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0)`
  - now: `(self, downscale: int = 2, generic_preselection: bool = True, reference_preselection: bool = True, keypoint_limit: int = 60000, tiepoint_limit: int = 10000, min_aligned_pct: float = 50.0)`
- `photogrammetry/sugar_mesh_workflow/_sugar_mesh.py::SugarMeshWorkflow.extract_mesh`
  - was: `(self, colmap_dir: str, regularization: str = 'dn_consistency', high_poly: bool = True, refinement_time: str = 'short', surface_level: float = 0.3, export_obj: bool = True, export_ply: bool = False, use_eval_split: bool = False, gpu: int = 0, white_background: bool = False) -> Optional[str]`
  - now: `(self, colmap_dir: str, regularization: str = 'dn_consistency', high_poly: bool = True, refinement_time: str = 'medium', surface_level: float = 0.3, export_obj: bool = True, export_ply: bool = False, use_eval_split: bool = False, gpu: int = 0, white_background: bool = False) -> Optional[str]`
