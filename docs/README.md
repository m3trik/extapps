[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
[![Tests](https://img.shields.io/badge/Tests-905%20passed-brightgreen.svg)](../test/)

<!-- short_description_start -->
The engines of the standalone content-pipeline tools — photogrammetry workflows, Substance / Marmoset automation and texture conversion rules — whose panels are tentacle's.
<!-- short_description_end -->

# extapps

The logic behind [tentacle](https://github.com/m3trik/tentacle)'s standalone
panels. Since 0.7.0 the panels themselves (their `.ui` files, Slots classes,
parameter registries and launchers) are tentacle's; a read of a moved name
(`extapps.CompositorUI`, ...) raises `MovedNameError` naming its new home.

## Engines

| Engine | Purpose | Panel (tentacle) | Docs |
|---|---|---|---|
| `photogrammetry` | End-to-end photogrammetry runs — frame extraction/curation → align → mesh → texture, with per-engine presets (`Profile`) | `metashape_workflow`, `realityscan_workflow`, `gaussian_splat_workflow` | [Metashape engine →](metashape_workflow.md) · [Tuning →](../extapps/photogrammetry/TUNING.md) |
| `substance_workflow` | Adobe Substance 3D Painter automation (JSON-RPC bridge) | `substance_workflow` | [→](substance_workflow.md) |
| `marmoset_workflow` | Open a model file in a new Marmoset Toolbag (import / lookdev templates; `MarmosetWorkflow`) | `marmoset_workflow` | _TBD_ |
| `texture_maps` | The Map Converter's batch rules (`MapConverter`) | `converter` | _TBD_ |

The other standalone panels drive pythontk's engines directly: `compositor`
([→](map_compositor.md)), `packer`, `mesh_convert`, `webxr_preview`,
`look_match` ([→](https://github.com/m3trik/pythontk/blob/main/docs/look_match.md)),
and `unity_workflow` (unitytk).

## Install

```powershell
pip install tentacletk     # the panels; brings in extapps
pip install extapps        # the engines alone
```

## Launch the panels

tentacle's `tentacle` command (`python -m tentacle`) opens the panels outside a
DCC, one by name or a browser of all of them, and writes desktop and Start-menu
shortcuts: [tentacle's docs](https://github.com/m3trik/tentacle/blob/main/docs/README.md#standalone-panels).

The `extapps` command (`python -m extapps [panel]`) is kept so launchers made
before the move keep working: it names tentacle as the panels' provider, so it
serves them from an installed tentacle or a source checkout on `PYTHONPATH`, and
installs `tentacletk` into that Python on the first panel asked for where tentacle
is missing (a Python that cannot run pip -- a DCC's own binary -- says so instead).
To make a new launcher, use `tentacle <panel> --shortcut desktop`. With editable
installs, re-run `pip install -e` for extapps and tentacle after updating, so the
installed metadata lists the panels under tentacle.

## Dependencies

- `pythontk` — domain logic
- `uitk`, `qtpy` — the runners' Qt process plumbing and the compatibility hub

The Metashape engine additionally requires the Agisoft Metashape Python module to be importable (installed alongside Metashape itself). The Substance engine requires an Adobe Substance 3D Painter install (auto-detected) to launch sessions. `extapps[mesh]` adds the photogrammetry mesh stages (PyMeshLab).

## License

LGPL-3.0-or-later — see [COPYING.LESSER](https://github.com/m3trik/extapps/blob/main/COPYING.LESSER) and [COPYING](https://github.com/m3trik/extapps/blob/main/COPYING).
