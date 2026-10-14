# extapps — API Changes

_Diff vs the last release (origin/main @ 080ac38)._

## Added (1)

- `texture_maps/packer/slots.py::PackerSlots.cmbPreset_init(self, widget)`

## Deprecations (1)

_Live retirement debt, earliest deadline first. An **EXPIRED** row has outlived its window: delete the alias and its tests rather than moving the date. A **HELD** row is due by version, but its notice has not yet had its calendar window._

- `texture_maps/converter/slots.py::ConverterSlots.resolve_affix` — remove in 0.4.0, not before 2026-10-26

## Signature changed (2)

- `marmoset_workflow/_marmoset_engine.py::MarmosetEngine.render_template`
  - was: `(self, template: str, model_path: str, manifest_path: str, output_dir: str, mode: str = SEND_TO, params: Optional[Dict[str, Any]] = None, headless: Optional[bool] = None, pairs_path: Optional[str] = None, source_model_path: Optional[str] = None) -> Optional[str]`
  - now: `(self, template: str, model_path: str, manifest_path: str, output_dir: str, mode: str = SEND_TO, params: Optional[Dict[str, Any]] = None, headless: Optional[bool] = None, pairs_path: Optional[str] = None, source_model_path: Optional[str] = None, save_dir: Optional[str] = None) -> Optional[str]`
- `marmoset_workflow/_marmoset_engine.py::MarmosetEngine.send`
  - was: `(self, model_path: str, manifest_path: Optional[str] = None, pairs_path: Optional[str] = None, source_model_path: Optional[str] = None, output_dir: Optional[str] = None, texture_dir: Optional[str] = None, texture_set_aliases: Optional[Dict[str, str]] = None, output_name: Optional[str] = None, toolbag_exe: Optional[str] = None, template: str = 'import', mode: str = SEND_TO, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]`
  - now: `(self, model_path: str, manifest_path: Optional[str] = None, pairs_path: Optional[str] = None, source_model_path: Optional[str] = None, output_dir: Optional[str] = None, texture_dir: Optional[str] = None, texture_set_aliases: Optional[Dict[str, str]] = None, output_name: Optional[str] = None, toolbag_exe: Optional[str] = None, template: str = 'import', mode: str = SEND_TO, params: Optional[Dict[str, Any]] = None, scene_dir: Optional[str] = None) -> Optional[Dict[str, Any]]`
