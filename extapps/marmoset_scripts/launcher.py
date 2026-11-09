# !/usr/bin/python
# coding=utf-8
"""Application shell for the Marmoset Scripts UI.

The DCC-agnostic Toolbag engine is bundled in this subpackage
(:mod:`extapps.marmoset_scripts._marmoset_engine`), the parameter specs in
:mod:`extapps.marmoset_scripts.parameters`, and the slot bindings in
:mod:`extapps.marmoset_scripts.slots`; this module only declares the panel
(:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides the
script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class MarmosetScriptsUI(PanelLauncher):
    TITLE = "Marmoset Scripts"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    MarmosetScriptsUI().show(pos="screen", app_exec=True)
