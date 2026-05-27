# Changelog

## Unreleased

- **Metashape Workflow header help migrated to uitk's new `Header.set_help_text(...)` API** — replaces the buried `widget.menu.add("QPushButton", setText="Instructions", ...)` block with a one-liner that auto-adds a `?` button to the header. The dead `MetashapeWorkflowSlots.btn_instructions` no-op method was removed at the same time (the old QPushButton was tooltip-only, so the slot was always a `pass`). See [`m3trik/docs/HEADER_HELP_INVENTORY.md`](../m3trik/docs/HEADER_HELP_INVENTORY.md) for the ecosystem-wide rollout.
- Initial scaffold. Repo consolidates standalone Switchboard panels previously living in `map_compositor`, `metashape_workflow`, and inside `pythontk` (`map_converter`, `map_packer`, `mesh_convert`).
- Engine / domain logic carved out to `pythontk`:
  - `MapCompositor` → `pythontk.img_utils.map_compositor`
  - `FrameExtractor` → `pythontk.vid_utils.frame_extractor`
- Metashape SDK wrapper stays bundled here (SDK-specific, not generic).
