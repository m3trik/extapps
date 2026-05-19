<!-- short_description_start -->
Standalone Switchboard panels for content-pipeline workflows.
<!-- short_description_end -->

# extapps

Each app is a self-contained subpackage that registers itself with uitk's
`ExternalAppHandler` via the `uitk.external_apps.in_process` entry-point
group. Hosts (tentacle, mayatk, etc.) discover and launch them automatically
— no host-side imports required.

## Tools

| Tool | Purpose | Engine | Docs |
|---|---|---|---|
| `map_compositor` | Multi-layer texture compositing | `pythontk.img_utils.map_compositor` | [→](map_compositor.md) |
| `metashape_workflow` | Agisoft Metashape photogrammetry automation | bundled (SDK-specific) | [→](metashape_workflow.md) |
| `map_converter` | Texture conversion, channel packing, PBR prep | `pythontk.ImgUtils` / `MapFactory` | _TBD_ |
| `map_packer` | Channel-pack textures from per-channel sources | `pythontk.ImgUtils` / `MapFactory` | _TBD_ |
| `mesh_convert` | FBX → glTF / GLB conversion | `pythontk.file_utils.mesh_convert` | _TBD_ |

## Install

```powershell
pip install extapps
```

## Launch (standalone)

```powershell
python -c "from extapps.map_compositor import MapCompositorUI; MapCompositorUI().show(pos='screen', app_exec=True)"
```

## Launch (from a host)

Hosts that load uitk's `ExternalAppHandler` discover apps automatically:

```python
sb.handlers.external_app.launch("map_compositor")
```

## Dependencies

- `pythontk` — domain logic
- `uitk` — UI framework
- `qtpy` — Qt abstraction

The `metashape_workflow` tool additionally requires the Agisoft Metashape Python module to be importable (installed alongside Metashape itself).
