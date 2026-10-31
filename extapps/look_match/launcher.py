# !/usr/bin/python
# coding=utf-8
"""Application shell for the Look Match UI.

The engine lives in :mod:`pythontk.core_utils.engines.lighting.look_match` and
the slot bindings in :mod:`extapps.look_match.slots`; this module only declares
the panel (:class:`extapps._panel_launcher.PanelLauncher` builds it) and
provides the script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class LookMatchUI(PanelLauncher):
    TITLE = "Look Match"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    LookMatchUI().show(pos="screen", app_exec=True)
