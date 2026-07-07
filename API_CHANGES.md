# extapps — API Changes

_Diff vs prior baseline. Generated 2026-07-07._

## Signature changed (6)

- `marmoset_workflow/_marmoset_engine.py::MarmosetEngine.toolbag_path`
  - was: `(self, value: Optional[str]) -> None`
  - now: `(self) -> Optional[str]`
- `mesh_convert/slots.py::MeshConvertSlots.fbx_provider`
  - was: `(self, fn: Optional[Callable[[], Iterable[str]]]) -> None`
  - now: `(self) -> Optional[Callable[[], Iterable[str]]]`
- `mesh_convert/slots.py::MeshConvertSlots.source_dir`
  - was: `(self, value: str) -> None`
  - now: `(self) -> str`
- `texture_maps/converter/slots.py::ConverterSlots.source_dir`
  - was: `(self, value)`
  - now: `(self)`
- `texture_maps/converter/slots.py::ConverterSlots.texture_provider`
  - was: `(self, fn)`
  - now: `(self)`
- `texture_maps/packer/slots.py::PackerSlots.source_dir`
  - was: `(self, value)`
  - now: `(self)`
