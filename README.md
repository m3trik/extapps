[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
![Platform](https://img.shields.io/badge/Platform-Windows%2C%20Linux-lightgrey.svg)

# extapps

Standalone [uitk](https://github.com/m3trik/uitk)-Switchboard panels for content-pipeline work — texture compositing and conversion, photogrammetry, mesh conversion, and DCC automation. Each app is a self-contained subpackage that registers via the `uitk.external_apps.in_process` entry-point group, so hosts like [tentacle](https://github.com/m3trik/tentacle) and [mayatk](https://github.com/m3trik/mayatk) discover and launch them with no host-side imports.

## Tools

- **compositor** — multi-layer texture-map compositing
- **converter** / **packer** — PBR map conversion (DX↔GL normals, spec→PBR, bump→normal, smoothness↔roughness) and channel pack/unpack (built-in ORM / MRAO / MSAO / Metallic Smoothness / glTF-pair templates)
- **photogrammetry** — end-to-end runs: frame extraction/curation → align → mesh → texture, with per-engine presets (Metashape, RealityScan, gaussian splat)
- **substance_workflow** — Substance 3D Painter automation over a bundled JSON-RPC bridge
- **marmoset_workflow** — open a model file in a new Marmoset Toolbag (import / lookdev templates)
- **mesh_convert** — FBX → glTF / GLB conversion
- **unity_workflow** — copy a model file into a Unity project's Assets; manage unitytk's import scripts

## Install & run

```bash
pip install extapps
extapps                             # a browser listing every panel
extapps compositor                  # one panel (python -m extapps compositor works too)
extapps --shortcut desktop          # a desktop shortcut (start_menu: the Start menu)
```

From a uitk host: `sb.handlers.external_app.launch("compositor")`; the host's UI
Browser also offers *Create desktop shortcut* on each panel's row.

Full usage and per-tool docs: [docs/README.md](docs/README.md) · scope and structure: [CLAUDE.md](CLAUDE.md) · history: [CHANGELOG.md](CHANGELOG.md)

## License

LGPL-3.0-or-later — see [COPYING.LESSER](https://github.com/m3trik/extapps/blob/main/COPYING.LESSER) and [COPYING](https://github.com/m3trik/extapps/blob/main/COPYING).
