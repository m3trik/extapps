# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Converter UI.

Declares the panel (:class:`extapps._panel_launcher.PanelLauncher` builds
it) and provides the script entry point; slot bindings live in
:mod:`extapps.texture_maps.converter.slots`. A host that hands it its
selection opens it through its external-app handler
(``launch("converter", show=False)``) and sets the scopes on the window.
"""

from extapps._panel_launcher import PanelLauncher


class ConverterUI(PanelLauncher):
    STYLE_CLASS = "translucentBgWithBorder"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ConverterUI().show(pos="screen", app_exec=True)
