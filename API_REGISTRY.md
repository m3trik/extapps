# extapps — API Registry

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_api_registry.py`._

_Generated: 2026-05-19_

## Index

- [`map_compositor/launcher.py`](#map_compositor--launcher) — Application shell for the Map Compositor UI.
- [`map_compositor/slots.py`](#map_compositor--slots) — UI slot bindings for the map_compositor window.
- [`map_converter/launcher.py`](#map_converter--launcher) — Application shell for the Map Converter UI.
- [`map_converter/slots.py`](#map_converter--slots) — Map Converter UI — slot file for ``map_converter.ui``.
- [`map_packer/launcher.py`](#map_packer--launcher) — Application shell for the Map Packer UI.
- [`map_packer/slots.py`](#map_packer--slots)
- [`mesh_convert/launcher.py`](#mesh_convert--launcher) — Application shell for the Mesh Convert UI.
- [`mesh_convert/slots.py`](#mesh_convert--slots)
- [`metashape_workflow/_metashape_workflow.py`](#metashape_workflow--_metashape_workflow)
- [`metashape_workflow/launcher.py`](#metashape_workflow--launcher) — Application shell for the Metashape Workflow UI.
- [`metashape_workflow/slots.py`](#metashape_workflow--slots)

---

<a id="map_compositor--launcher"></a>
### `map_compositor/launcher.py`

Application shell for the Map Compositor UI.

- **[`class MapCompositorUI`](extapps/extapps/map_compositor/launcher.py#L27)**

<a id="map_compositor--slots"></a>
### `map_compositor/slots.py`

UI slot bindings for the map_compositor window.

- **[`class MapCompositorSlots`](extapps/extapps/map_compositor/slots.py#L50)** — UI slot handler.
  - `MapCompositorSlots.removeNormalMap(self) -> bool` *(property)*
  - `MapCompositorSlots.removeNormalMap(self, value: bool) -> None`
  - `MapCompositorSlots.input_dir(self) -> str` *(property)*
  - `MapCompositorSlots.output_dir(self) -> str` *(property)*
  - `MapCompositorSlots.map_name(self) -> str` *(property)*
  - `MapCompositorSlots.header_init(self, widget)` — Populate the header menu with global options.
  - `MapCompositorSlots.txt000_init(self, widget)` — Init Source Directory
  - `MapCompositorSlots.txt001_init(self, widget)` — Init Destination Directory
  - `MapCompositorSlots.txt002_init(self, widget)` — Init Map Name
  - `MapCompositorSlots.b002(self)` — Combine Maps
  - `MapCompositorSlots.process(self, images, input_dir, output_dir, map_name=None)` — Validate dirs, prepare sorted-image groups, and drive the engine.

<a id="map_converter--launcher"></a>
### `map_converter/launcher.py`

Application shell for the Map Converter UI.

- **[`class MapConverterUI`](extapps/extapps/map_converter/launcher.py#L12)** — Standalone launcher.

<a id="map_converter--slots"></a>
### `map_converter/slots.py`

Map Converter UI — slot file for ``map_converter.ui``.

- **[`class MapConverterSlots(ImgUtils)`](extapps/extapps/map_converter/slots.py#L29)** — Switchboard slots for ``map_converter.ui``.
  - `MapConverterSlots.source_dir(self)` *(property)* — Get the starting directory for file dialogs.
  - `MapConverterSlots.source_dir(self, value)` — Set the starting directory for file dialogs.
  - `MapConverterSlots.texture_provider(self)` *(property)* — Callable returning a list of texture paths from the host DCC selection.
  - `MapConverterSlots.texture_provider(self, fn)`
  - `MapConverterSlots.header_init(self, widget)` — Add the global Use-Selection toggle to the header menu.
  - `MapConverterSlots.tb000_init(self, widget)` — Populate the Optimize toolbutton's option menu (format, clamp, modifier).
  - `MapConverterSlots.tb000(self, widget)` — Optimize a texture map(s)
  - `MapConverterSlots.tb001_init(self, widget)`
  - `MapConverterSlots.tb001(self, widget)` — Batch converts Spec/Gloss maps to PBR Metal/Rough using MapFactory.
  - `MapConverterSlots.tb003_init(self, widget)` — Initialize a 'Bump to Normal' toolbutton with options.
  - `MapConverterSlots.tb003(self, widget)` — Bump/Height to Normal converter (single entry point with options).
  - `MapConverterSlots.b000(self)` — Convert DirectX to OpenGL
  - `MapConverterSlots.b001(self)` — Convert OpenGL to DirectX
  - `MapConverterSlots.b004(self)` — Batch pack Transparency into Albedo across texture sets.
  - `MapConverterSlots.b005(self)` — Batch pack Smoothness or Roughness into Metallic across texture sets.
  - `MapConverterSlots.b006(self)` — Unpack Metallic and Smoothness maps from MetallicSmoothness textures.
  - `MapConverterSlots.b007(self)` — Unpack Specular and Gloss maps from SpecularGloss textures.
  - `MapConverterSlots.b008_init(self, widget)` — Populate the MSAO pack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b008(self, widget)` — Batch pack Metallic, AO, and Smoothness/Roughness into an MSAO texture.
  - `MapConverterSlots.b009_init(self, widget)` — Populate the MSAO unpack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b009(self, widget)` — Unpack Metallic, AO, and Smoothness maps from MSAO textures.
  - `MapConverterSlots.b013_init(self, widget)` — Populate the MRAO pack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b013(self, widget)` — Batch pack Metallic, Roughness/Smoothness, and AO into an MRAO texture.
  - `MapConverterSlots.b014_init(self, widget)` — Populate the MRAO unpack toolbutton's option menu (channel layout).
  - `MapConverterSlots.b014(self, widget)` — Unpack Metallic, Roughness, and AO from MRAO textures.
  - `MapConverterSlots.b015(self)` — Batch pack AO, Roughness/Smoothness, and Metallic into an ORM texture.
  - `MapConverterSlots.b016(self)` — Unpack AO, Roughness, and Metallic from ORM textures.
  - `MapConverterSlots.b010(self)` — Convert Smoothness maps to Roughness maps.
  - `MapConverterSlots.b011(self)` — Convert Roughness maps to Smoothness maps.
  - `MapConverterSlots.b012(self)` — Batch prepare textures for PBR workflow using MapFactory.

<a id="map_packer--launcher"></a>
### `map_packer/launcher.py`

Application shell for the Map Packer UI.

- **[`class MapPackerUI`](extapps/extapps/map_packer/launcher.py#L11)**

<a id="map_packer--slots"></a>
### `map_packer/slots.py`

- **[`class MapPackerSlots(ImgUtils)`](extapps/extapps/map_packer/slots.py#L9)**
  - `MapPackerSlots.header_init(self, widget)` — Configure the header menu with presets for common packed map types.
  - `MapPackerSlots.source_dir(self)` *(property)*
  - `MapPackerSlots.source_dir(self, value)`
  - `MapPackerSlots.b000(self)` — Batch pack up to 4 channels into RGBA maps across texture sets.
  - `MapPackerSlots.b001(self)` — Open the last output directory in the system file explorer.

<a id="mesh_convert--launcher"></a>
### `mesh_convert/launcher.py`

Application shell for the Mesh Convert UI.

- **[`class MeshConvertUI`](extapps/extapps/mesh_convert/launcher.py#L11)**

<a id="mesh_convert--slots"></a>
### `mesh_convert/slots.py`

- **[`class MeshConvertSlots(MeshConvert)`](extapps/extapps/mesh_convert/slots.py#L13)** — Switchboard slots for the Mesh Converter UI.
  - `MeshConvertSlots.source_dir(self) -> str` *(property)* — Starting directory for the FBX file dialog.
  - `MeshConvertSlots.source_dir(self, value: str) -> None`
  - `MeshConvertSlots.fbx_provider(self) -> Optional[Callable[[], Iterable[str]]]` *(property)* — Callable returning FBX paths from the host DCC selection.
  - `MeshConvertSlots.fbx_provider(self, fn: Optional[Callable[[], Iterable[str]]]) -> None`
  - `MeshConvertSlots.header_init(self, widget) -> None` — Add the From-FBX-references toggle to the header menu.
  - `MeshConvertSlots.tb000_init(self, widget) -> None` — Set up the FBX -> GLB tool button option box.
  - `MeshConvertSlots.tb000(self, widget) -> None` — Convert the selected FBX file(s) to GLB beside their source.

<a id="metashape_workflow--_metashape_workflow"></a>
### `metashape_workflow/_metashape_workflow.py`

- [`is_metashape_available() -> bool`](extapps/extapps/metashape_workflow/_metashape_workflow.py#L15) — True if the Metashape Python module imported successfully.
- [`is_license_valid() -> bool`](extapps/extapps/metashape_workflow/_metashape_workflow.py#L20) — True if a valid Metashape license is reachable.
- [`get_metashape_version() -> str`](extapps/extapps/metashape_workflow/_metashape_workflow.py#L30)
- [`get_image_filepaths(directory: str) -> List[str]`](extapps/extapps/metashape_workflow/_metashape_workflow.py#L331) — Return absolute paths to all images in `directory` (non-recursive).
- **[`class MetashapeWorkflow`](extapps/extapps/metashape_workflow/_metashape_workflow.py#L39)** — Wrapper around Agisoft Metashape's Python API for the standard
  - `MetashapeWorkflow.get_license_info(self) -> str`
  - `MetashapeWorkflow.create_chunk(self, label: str = 'New Chunk')`
  - `MetashapeWorkflow.add_images(self, image_sources: Union[str, Sequence[str]])` — Add images from a directory path (non-recursive) or list of paths.
  - `MetashapeWorkflow.align_photos(self, downscale: int = 2, generic_preselection: bool = False, reference_preselection: bool = True, keypoint_limit: int = 100000, tiepoint_limit: int = 10000, filter_mask: bool = False)`
  - `MetashapeWorkflow.generate_depth_maps(self, downscale: int = 2, filter_mode=None)`
  - `MetashapeWorkflow.build_model(self, source_data=None, surface_type=None, interpolation=None, face_count=None)`
  - `MetashapeWorkflow.build_texture(self, texture_size: int = 4096, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter: bool = True)`
  - `MetashapeWorkflow.save_project(self)`
  - `MetashapeWorkflow.export_model(self, export_format=None, binary: bool = True, precision: int = 6, texture_format=None, save_texture: bool = True, save_normals: bool = True, save_colors: bool = True, save_cameras: bool = False, overwrite: bool = True)`

<a id="metashape_workflow--launcher"></a>
### `metashape_workflow/launcher.py`

Application shell for the Metashape Workflow UI.

- **[`class MetashapeWorkflowUI`](extapps/extapps/metashape_workflow/launcher.py#L13)**

<a id="metashape_workflow--slots"></a>
### `metashape_workflow/slots.py`

- **[`class MetashapeWorkflowSlots(ptk.LoggingMixin)`](extapps/extapps/metashape_workflow/slots.py#L90)** — Switchboard slots for the Metashape Workflow UI.
  - `MetashapeWorkflowSlots.header_init(self, widget) -> None`
  - `MetashapeWorkflowSlots.txt000_init(self, widget) -> None` — Project Directory
  - `MetashapeWorkflowSlots.txt000(self, widget) -> None`
  - `MetashapeWorkflowSlots.txt001_init(self, widget) -> None` — Project Name
  - `MetashapeWorkflowSlots.txt002_init(self, widget) -> None` — Frames Directory
  - `MetashapeWorkflowSlots.txt002(self, widget) -> None`
  - `MetashapeWorkflowSlots.cmb000_init(self, widget) -> None` — Preset
  - `MetashapeWorkflowSlots.btn_stages_init(self, widget) -> None` — Pipeline-stages popup — QMenu of checkboxes attached to the button.
  - `MetashapeWorkflowSlots.btn_advanced_init(self, widget) -> None` — Advanced-params popup — labeled form inside a QMenu via QWidgetAction.
  - `MetashapeWorkflowSlots.b000(self) -> None` — Run Workflow
  - `MetashapeWorkflowSlots.btn_instructions(self) -> None`
  - `MetashapeWorkflowSlots.cmb003(self, widget) -> None` — Log level changed
  - `MetashapeWorkflowSlots.btn_browse_project(self) -> None`
  - `MetashapeWorkflowSlots.btn_explore_project(self) -> None`
  - `MetashapeWorkflowSlots.btn_browse_frames(self) -> None`
  - `MetashapeWorkflowSlots.btn_explore_frames(self) -> None`
  - `MetashapeWorkflowSlots.btn_extract_frames(self) -> None` — Extract frames from a video file into the frames directory.
