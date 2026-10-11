[![Tests](https://img.shields.io/badge/Tests-792%20passed-brightgreen.svg)](../test/)

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

Installing extapps adds an `extapps` command (`python -m extapps` runs the same
program):

| Command | Opens |
|---|---|
| `extapps` | A browser listing every panel: search, filter by tag, double-click to open |
| `extapps compositor` | One panel, by its name in the Tools table (`metashape_workflow`, `mesh_convert`, ...) |
| `extapps --shortcut desktop` | Writes a desktop shortcut that opens the browser, then exits (`--shortcut start_menu`: the Start menu, or the Linux applications menu) |
| `extapps compositor --shortcut desktop` | Writes a shortcut that opens one panel (named "extapps Compositor") |

The command opens no console window, and quits once its last window is closed
or hidden. It is uitk's `ExternalAppHub`; `extapps/__main__.py` only declares its
name, icon and taskbar identity.

### Desktop and Start-menu shortcuts

Three ways to get one; run any of them again to refresh a shortcut (after moving
or upgrading the Python it runs, say):

- **From the browser:** its menu, *Launch from the desktop:* section,
  *Create desktop shortcut* / *Add to Start menu*.
- **From inside Maya or Blender (tentacle):** open the UI Browser, right-click a
  panel's row, *Create desktop shortcut* / *Add to Start menu*. The shortcut runs
  the host's own Python (`mayapy`, Blender's `python`) without opening the host.
- **From a terminal:** `extapps --shortcut desktop`.

Before writing anything, the shortcut is tried: extapps has to import in that
Python as the desktop starts it, without the host's startup scripts. When it does
not (extapps reaches the host only through `userSetup.py` or `Maya.env`), no
shortcut is written and the message says why. Fix it by installing extapps into
that Python with pip, or by putting the extapps folder on a `PYTHONPATH` saved in
your user environment.

A shortcut into a host's Python (which has no console-free twin, unlike a
python.org or venv Python's `pythonw`) opens a console window for a moment; the
program closes it as it starts.

### When nothing seems to happen

A program started from the desktop has no console, so its output goes to a log:
`%LOCALAPPDATA%\uitk\extapps\extapps.log` on Windows (the previous run's is
`extapps.log.1`); on Linux the desktop session's journal. An uncaught error also
shows in a message box.

### From Python

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
- `unitytk` — Unity project bridge (used by `unity_workflow`)

The `metashape_workflow` tool additionally requires the Agisoft Metashape Python module to be importable (installed alongside Metashape itself). The `substance_workflow` tool requires an Adobe Substance 3D Painter install (auto-detected) to launch sessions.
