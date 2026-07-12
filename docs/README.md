<!-- short_description_start -->
Standalone Switchboard panels for content-pipeline workflows — map compositing, texture conversion and channel packing, photogrammetry, mesh conversion, and Substance / Marmoset / Unity automation.
<!-- short_description_end -->

# extapps

Each app is a self-contained subpackage that registers itself with uitk's
`ExternalAppHandler` via the `uitk.external_apps.in_process` entry-point
group. Hosts (tentacle, mayatk, etc.) discover and launch them automatically
— no host-side imports required.

## Tools

| Tool | Purpose | Engine | Docs |
|---|---|---|---|
| `compositor` | Multi-layer texture compositing | `pythontk.core_utils.engines.textures.map_compositor` | [→](map_compositor.md) |
| `photogrammetry` | End-to-end photogrammetry runs — frame extraction/curation → align → mesh → texture, with per-engine presets | bundled runners (Metashape SDK, RealityScan RSNode, gaussian splat) | [Metashape engine →](metashape_workflow.md) · [Tuning →](../extapps/photogrammetry/TUNING.md) |
| `substance_workflow` | Adobe Substance 3D Painter automation (JSON-RPC bridge) | bundled (SDK-specific) | [→](substance_workflow.md) |
| `marmoset_workflow` | Marmoset Toolbag automation (RPC bridge + render templates) | bundled `_marmoset_engine` (SDK-specific) | _TBD_ |
| `unity_workflow` | Unity workflow panel | bundled | _TBD_ |
| `converter` | Texture conversion (normal DX↔GL, smoothness↔roughness, spec→PBR, bump→normal, optimize, flip/swizzle channels), color+alpha pack/unpack, PBR prep | `pythontk.ImgUtils` / `MapFactory` | _TBD_ |
| `packer` | Channel-pack **and unpack** textures via per-channel sources (ORM/MRAO/MSAO/MetallicSmoothness templates) | `pythontk.ImgUtils` / `MapFactory` | _TBD_ |
| `mesh_convert` | FBX → glTF / GLB conversion | `pythontk.file_utils.mesh_convert` | _TBD_ |

## Install

```powershell
pip install extapps
```

## Launch (standalone)

```powershell
python -c "from extapps.texture_maps.compositor import CompositorUI; CompositorUI().show(pos='screen', app_exec=True)"
```

## Launch (from a host)

Hosts that load uitk's `ExternalAppHandler` discover apps automatically:

```python
sb.handlers.external_app.launch("compositor")
```

## Dependencies

- `pythontk` — domain logic
- `uitk` — UI framework
- `qtpy` — Qt abstraction

The `metashape_workflow` tool additionally requires the Agisoft Metashape Python module to be importable (installed alongside Metashape itself). The `substance_workflow` tool requires an Adobe Substance 3D Painter install (auto-detected) to launch sessions.
