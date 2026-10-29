[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
![Platform](https://img.shields.io/badge/Platform-Windows%2C%20Linux-lightgrey.svg)

# extapps

The engines behind [tentacle](https://github.com/m3trik/tentacle)'s standalone content-pipeline panels: photogrammetry workflows, Substance 3D Painter and Marmoset Toolbag automation, and texture-map conversion rules. The panels themselves (their `.ui` files and Slots classes) are tentacle's since extapps 0.7.0; extapps keeps the logic they drive, importable without them.

## Engines

- **photogrammetry** — end-to-end runs: frame extraction/curation → align → mesh → texture, with per-engine presets (`MetashapeWorkflow`, RealityScan, Brush gaussian splats; `run_combined` CLIs and the panels' runners)
- **substance_workflow** — Substance 3D Painter automation over a bundled JSON-RPC bridge (`PainterConnection`, `Job.run_batch`)
- **marmoset_workflow** — open a model file in a new Marmoset Toolbag (`MarmosetWorkflow`: import / lookdev templates)
- **texture_maps** — the Map Converter's batch rules (`MapConverter`)

## Install & run

```bash
pip install tentacletk              # the panels; brings in extapps
tentacle                            # a browser listing every panel
tentacle compositor                 # one panel
```

`extapps` / `python -m extapps [panel]` still opens the panels, so launchers made before the move keep working: it serves them from tentacle (installed, or a source checkout), and installs `tentacletk` into that Python on the first panel asked for where it is missing.

Full usage and per-engine docs: [docs/README.md](docs/README.md) · scope and structure: [CLAUDE.md](CLAUDE.md) · history: [CHANGELOG.md](CHANGELOG.md)

## License

LGPL-3.0-or-later — see [COPYING.LESSER](https://github.com/m3trik/extapps/blob/main/COPYING.LESSER) and [COPYING](https://github.com/m3trik/extapps/blob/main/COPYING).
