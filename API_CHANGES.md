# extapps — API Changes

_Diff vs the last release (origin/main @ 0649e41)._

## Added (12)

- `webxr_preview/launcher.py::WebXrPreviewUI(class)`
- `webxr_preview/parameters.py::defaults() -> 'dict[str, Any]'`
- `webxr_preview/slots.py::WebXrPreviewSlots(class)`
- `webxr_preview/slots.py::WebXrPreviewSlots.b000(self) -> None`
- `webxr_preview/slots.py::WebXrPreviewSlots.engine(self)`
- `webxr_preview/slots.py::WebXrPreviewSlots.list_template_modes(self) -> List[Tuple[str, str]]`
- `webxr_preview/slots.py::WebXrPreviewSlots.make_bridge(self)`
- `webxr_preview/slots.py::WebXrPreviewSlots.open_preview_page(self) -> None`
- `webxr_preview/slots.py::WebXrPreviewSlots.params_module(self)`
- `webxr_preview/slots.py::WebXrPreviewSlots.set_source_file(self, path: str) -> None`
- `webxr_preview/slots.py::WebXrPreviewSlots.stop_server(self) -> None`
- `webxr_preview/slots.py::WebXrPreviewSlots.template_dir(self) -> Path`
