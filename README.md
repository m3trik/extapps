# extapps

Standalone [uitk](https://github.com/m3trik/uitk)-Switchboard panels for content-pipeline work — texture compositing and conversion, photogrammetry, mesh conversion, and DCC automation. Each app is a self-contained subpackage that registers via the `uitk.external_apps.in_process` entry-point group, so hosts like [tentacle](https://github.com/m3trik/tentacle) and [mayatk](https://github.com/m3trik/mayatk) discover and launch them with no host-side imports.

## Tools

- **compositor** — multi-layer texture-map compositing
- **converter** / **packer** — PBR map conversion (DX↔GL normals, spec→PBR, bump→normal, smoothness↔roughness) and channel pack/unpack (ORM / MRAO / MSAO templates)
- **photogrammetry** — end-to-end runs: frame extraction/curation → align → mesh → texture, with per-engine presets (Metashape, RealityScan, gaussian splat)
- **substance_workflow** — Substance 3D Painter automation over a bundled JSON-RPC bridge
- **marmoset_workflow** — Marmoset Toolbag automation (RPC bridge + render templates)
- **mesh_convert** — FBX → glTF / GLB conversion
- **unity_workflow** — Unity workflow panel

## Install & run

```bash
pip install extapps
python -c "from extapps.texture_maps.compositor import CompositorUI; CompositorUI().show(pos='screen', app_exec=True)"
```

From a uitk host: `sb.handlers.external_app.launch("compositor")`.

Full usage and per-tool docs: [docs/README.md](docs/README.md) · scope and structure: [CLAUDE.md](CLAUDE.md) · history: [CHANGELOG.md](CHANGELOG.md)
