# extapps — API Changes

_Diff vs the last release (origin/main @ 64ea3b7)._

## Removed (1)

- `texture_maps/packer/slots.py::PackerSlots.header_init` — was `(self, widget)`

## Added (2)

- `texture_maps/packer/slots.py::PackerSlots.cmbMissing_init(self, widget)`
- `texture_maps/packer/slots.py::PackerSlots.cmbMode_init(self, widget)`

## Deprecations (1)

_Live retirement debt, earliest deadline first. An **EXPIRED** row has outlived its window: delete the alias and its tests rather than moving the date. A **HELD** row is due by version, but its notice has not yet had its calendar window._

- **HELD** `texture_maps/converter/slots.py::ConverterSlots.resolve_affix` — remove in 0.4.0, not before 2026-10-26
