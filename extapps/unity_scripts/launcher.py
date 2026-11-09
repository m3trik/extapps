# !/usr/bin/python
# coding=utf-8
"""Application shell for the Unity Scripts launcher UI.

The engine half (the script catalog and the copy into ``Assets/``) is
:mod:`extapps.unity_scripts.unity_deliverer`, the project's connection
:mod:`extapps.unity_scripts.unity_connection`, the slot bindings
:mod:`extapps.unity_scripts.slots`. This module only declares the panel
(:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides the
script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class UnityScriptsUI(PanelLauncher):
    TITLE = "Unity Scripts"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    UnityScriptsUI().show(pos="screen", app_exec=True)
