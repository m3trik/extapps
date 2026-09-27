# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Packer UI.

Declares the panel (:class:`extapps._panel_launcher.PanelLauncher` builds
it) and provides the script entry point; slot bindings live in
:mod:`extapps.texture_maps.packer.slots`.
"""

from extapps._panel_launcher import PanelLauncher


class PackerUI(PanelLauncher):
    STYLE_CLASS = "translucentBgWithBorder"
    HEADER_BUTTONS = ("menu", "minimize", "hide")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    PackerUI().show(pos="screen", app_exec=True)
