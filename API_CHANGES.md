# extapps — API Changes

_Diff vs the last release (origin/main @ c868381)._

## Added (2)

- `webxr_preview/slots.py::WebXrPreviewSlots.check_share_link(self) -> None`
- `webxr_preview/slots.py::WebXrPreviewSlots.set_source_files(self, paths: List[str]) -> None`

## Deprecations (1)

_Live retirement debt, earliest deadline first. An **EXPIRED** row has outlived its window: delete the alias and its tests rather than moving the date. A **HELD** row is due by version, but its notice has not yet had its calendar window._

- `texture_maps/converter/slots.py::ConverterSlots.resolve_affix` — remove in 0.4.0, not before 2026-10-26

## Signature changed (3)

- `texture_maps/converter/_converter.py::MapConverter.optimize_one`
  - was: `(cls, texture_path, *, file_type, max_size, secondary_scale, mode, modifier, new_folder, old_folder, registry, dry_run=False, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None)`
  - now: `(cls, texture_path, *, file_type, max_size, secondary_scale, mode, modifier, new_folder, old_folder, registry, dry_run=False, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None, map_type=None, base_name=None)`
- `texture_maps/converter/_converter.py::MapConverter.rename_target_path`
  - was: `(cls, texture_path, *, file_type, mode, modifier, output_dir)`
  - now: `(cls, texture_path, *, file_type, mode, modifier, output_dir, base_name=None)`
- `texture_maps/converter/_converter.py::MapConverter.report_optimize_plan`
  - was: `(cls, texture_path, *, file_type, max_size, mode, modifier, output_dir, old_folder, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None)`
  - now: `(cls, texture_path, *, file_type, max_size, mode, modifier, output_dir, old_folder, output_profile=None, enforce_budget=False, lossy_quality=None, uastc_rdo=None, uastc_rdo_dictionary=None, map_type=None, base_name=None)`
