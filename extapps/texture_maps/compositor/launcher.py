# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Compositor UI.

Declares the panel (:class:`extapps._panel_launcher.PanelLauncher` builds
it) and provides the script entry point; slot bindings live in
:mod:`extapps.texture_maps.compositor.slots`. The header title ("MAP
COMPOSITOR") is set declaratively in the ``.ui`` file -- edit it in Qt
Designer; only the version (release-dependent) is wired in at runtime.
"""

from extapps._panel_launcher import PanelLauncher


class CompositorUI(PanelLauncher):
    TITLE = "Map Compositor"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    CompositorUI().show(pos="screen", app_exec=True)
