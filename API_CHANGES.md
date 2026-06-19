# extapps — API Changes

_Diff vs prior baseline. Generated 2026-06-19._

## Removed (2)

- `marmoset_workflow/slots.py::MarmosetWorkflowSlots.header_init` — was `(self, widget) -> None`
- `photogrammetry/_panel_slots.py::PhotogrammetryPanelSlots.header_init` — was `(self, widget) -> None`

## Added (6)

- `marmoset_workflow/_marmoset_engine.py::MarmosetEngine.deliver(self, bridge, payload, request) -> Optional[Dict[str, Any]]`
- `marmoset_workflow/_marmoset_engine.py::MarmosetEngine.preflight(self, bridge, request) -> bool`
- `photogrammetry/_panel_slots.py::PhotogrammetryPanelSlots.header_menu_items(self)`
- `photogrammetry/gaussian_splat_workflow/slots.py::GaussianSplatWorkflowSlots.help_spec(self) -> dict`
- `photogrammetry/metashape_workflow/slots.py::MetashapeWorkflowSlots.help_spec(self) -> dict`
- `photogrammetry/realityscan_workflow/slots.py::RealityscanWorkflowSlots.help_spec(self) -> dict`
