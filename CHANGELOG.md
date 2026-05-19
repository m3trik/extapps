# Changelog

## Unreleased

- Initial scaffold. Repo consolidates standalone Switchboard panels previously living in `map_compositor`, `metashape_workflow`, and inside `pythontk` (`map_converter`, `map_packer`, `mesh_convert`).
- Engine / domain logic carved out to `pythontk`:
  - `MapCompositor` → `pythontk.img_utils.map_compositor`
  - `FrameExtractor` → `pythontk.vid_utils.frame_extractor`
- Metashape SDK wrapper stays bundled here (SDK-specific, not generic).
