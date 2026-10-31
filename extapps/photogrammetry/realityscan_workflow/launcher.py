# !/usr/bin/python
# coding=utf-8
"""Application shell for the RealityCapture Workflow UI.

Declares the panel (:class:`extapps._panel_launcher.PanelLauncher` builds
it) and provides the script entry point; slot bindings live in
:mod:`extapps.photogrammetry.realityscan_workflow.slots`.
"""

from extapps._panel_launcher import PanelLauncher


class RealityScanWorkflowUI(PanelLauncher):
    TITLE = "RealityCapture Workflow"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    RealityScanWorkflowUI().show(pos="screen", app_exec=True)
