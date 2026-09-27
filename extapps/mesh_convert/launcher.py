# !/usr/bin/python
# coding=utf-8
"""Application shell for the Mesh Convert UI.

Engine logic lives in :mod:`pythontk.file_utils.mesh_convert` and slot
bindings in :mod:`extapps.mesh_convert.slots`; this module only declares the
panel (:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides
the script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class MeshConvertUI(PanelLauncher):
    STYLE_CLASS = "translucentBgWithBorder"
    HEADER_BUTTONS = ("menu", "minimize", "hide")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    MeshConvertUI().show(pos="screen", app_exec=True)
