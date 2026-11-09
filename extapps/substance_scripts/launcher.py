# !/usr/bin/python
# coding=utf-8
"""Application shell for the Substance Scripts panel.

The Painter engine (:class:`SubstanceScripts`, the vendored
:class:`SubstanceEngine`) and its Painter-side plugin (``substance_rpc``) live
alongside this module; slot bindings are in
:mod:`extapps.substance_scripts.slots`. This module only declares the panel
(:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides the
script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class SubstanceScriptsUI(PanelLauncher):
    TITLE = "Substance Scripts"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    SubstanceScriptsUI().show(pos="screen", app_exec=True)
