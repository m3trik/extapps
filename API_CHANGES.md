# extapps — API Changes

_Diff vs the last release (origin/main @ 29534a5)._

## Removed (4)

- `substance_workflow/plugins/substance_workflow_bridge/__init__.py::OP_MODULES` — was `(constant)`
- `substance_workflow/plugins/substance_workflow_bridge/__init__.py::close_plugin` — was `() -> None`
- `substance_workflow/plugins/substance_workflow_bridge/__init__.py::start_plugin` — was `() -> None`
- `webxr_preview/parameters.py::LIGHTING_KEYS` — was `(constant)`

## Added (54)

- `look_match/__init__.py::DEFAULT_INCLUDE(constant)`
- `look_match/launcher.py::LookMatchUI(class)`
- `look_match/slots.py::DOCS_URL(constant)`
- `look_match/slots.py::LookMatchSlots(class)`
- `look_match/slots.py::LookMatchSlots.b_accept(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_discard(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_draw_ellipse(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_draw_line(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_draw_poly(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_draw_rect(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_edit_regions(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_fit(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_fit_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.b_paint(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_redo(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_redo_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.b_region_delete(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_reload(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_render(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_save_rig(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_solve(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_undo(self) -> None`
- `look_match/slots.py::LookMatchSlots.b_undo_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.b_update(self) -> None`
- `look_match/slots.py::LookMatchSlots.brightness_text(value: Optional[float]) -> str`
- `look_match/slots.py::LookMatchSlots.browse_session(self) -> None`
- `look_match/slots.py::LookMatchSlots.chk_all_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.cmb_a_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.cmb_b_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.cmb_mix_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.cmb_mode_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.cmb_session_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.cmb_solve_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.cmp_view_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.delete_mix(self) -> None`
- `look_match/slots.py::LookMatchSlots.header_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.mix_key(mix) -> str`
- `look_match/slots.py::LookMatchSlots.open_session(self, path: str) -> bool`
- `look_match/slots.py::LookMatchSlots.save_mix(self) -> None`
- `look_match/slots.py::LookMatchSlots.save_mix_as(self) -> None`
- `look_match/slots.py::LookMatchSlots.status_glyph(row: Dict[str, Any]) -> str`
- `look_match/slots.py::LookMatchSlots.stop_service(self, wait: bool = True) -> None`
- `look_match/slots.py::LookMatchSlots.stop_worker(self) -> None`
- `look_match/slots.py::LookMatchSlots.tbl_mix_init(self, widget) -> None`
- `look_match/slots.py::LookMatchSlots.tbl_regions_init(self, widget) -> None`
- `substance_workflow/env_utils/painter_connection.py::PainterConnection.is_connected(self) -> bool`
- `substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py::OP_MODULES(constant)`
- `substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py::close_plugin() -> None`
- `substance_workflow/plugins/startup/substance_workflow_bridge/__init__.py::start_plugin() -> None`
- `webxr_preview/parameters.py::AUTHORED_EXTENSION(constant)`
- `webxr_preview/parameters.py::KTX2_KEYS(constant)`
- `webxr_preview/parameters.py::TEXTURE_KEYS(constant)`
- `webxr_preview/slots.py::WebXrPreviewSlots.add_scene(self, paths: Optional[List[str]] = None) -> _Scene`
- `webxr_preview/slots.py::WebXrPreviewSlots.remove_scene(self, scene: _Scene) -> None`

## Deprecations (1)

_Live retirement debt, earliest deadline first. An **EXPIRED** row has outlived its window: delete the alias and its tests rather than moving the date. A **HELD** row is due by version, but its notice has not yet had its calendar window._

- **HELD** `texture_maps/converter/slots.py::ConverterSlots.resolve_affix` — remove in 0.4.0, not before 2026-10-26
