# extapps

**Role**: Standalone Switchboard panels for content-pipeline workflows. Each app is a uitk external app discovered via the `uitk.external_apps.in_process` entry-point group.

**Nav**: [← root](../CLAUDE.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · **Used by**: [tentacle](../tentacle/CLAUDE.md) (via ExternalAppHandler discovery)

## Scope

Tools that belong here:
- Standalone Switchboard panels.
- Depend on `pythontk` for domain logic and `uitk` for UI.
- DCC-agnostic (run from any host that loads uitk).

Tools that do NOT belong here:
- CLI-only utilities → `m3trik/scripts/`.
- Full applications with their own release cadence and distribution model → own repo.
- Library code that doesn't ship a UI panel → `pythontk` or another upstream package.

## Hard rules

- **All apps register via `uitk.external_apps.in_process` entry points.** No host (tentacle, mayatk, etc.) directly imports an app's slot class. Hosts launch apps through uitk's `ExternalAppHandler`.
- **Engine / domain logic lives in `pythontk`.** Slot classes here only do UI wiring + dispatch to pythontk APIs.

## Structure

Each tool is a self-contained subpackage:

```
extapps/<tool>/
  __init__.py          # exposes <Tool>UI as the entry point
  slots.py             # Switchboard slot class
  <tool>.ui            # Qt Designer file
  launcher.py          # <Tool>UI class (Switchboard wiring)
```

## Run

Direct launch:

```powershell
python -c "from extapps.map_compositor import MapCompositorUI; MapCompositorUI().show(pos='screen', app_exec=True)"
```

Via tentacle / mayatk: tools auto-discover through their entry-point group.

## Run tests

```powershell
& python -m pytest o:\Cloud\Code\_scripts\extapps\test
```

See [CHANGELOG.md](CHANGELOG.md) for history.
