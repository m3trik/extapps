# !/usr/bin/python
# coding=utf-8
"""Application shell for the Unity Workflow launcher UI.

The engine half (editor discovery + launch + project creation) lives in ``unitytk``
(:class:`unitytk.UnityLauncher` / :class:`unitytk.UnityFinder`); the slot bindings in
:mod:`extapps.unity_workflow.slots`. This module only declares the panel
(:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides the script
entry point.
"""

from extapps._panel_launcher import PanelLauncher


class UnityWorkflowUI(PanelLauncher):
    TITLE = "Unity Workflow"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    UnityWorkflowUI().show(pos="screen", app_exec=True)
