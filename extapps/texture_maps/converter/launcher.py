# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Converter UI.

Declares the panel (:class:`extapps._panel_launcher.PanelLauncher` builds
it) and provides the script entry point; slot bindings live in
:mod:`extapps.texture_maps.converter.slots`. Hosts that need to inject a
``texture_provider`` register :class:`ConverterSlots` themselves rather than
going through this launcher.
"""

from extapps._panel_launcher import PanelLauncher


class ConverterUI(PanelLauncher):
    STYLE_CLASS = "translucentBgWithBorder"
    HEADER_BUTTONS = ("menu", "minimize", "hide")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ConverterUI().show(pos="screen", app_exec=True)
