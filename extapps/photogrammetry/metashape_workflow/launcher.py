# !/usr/bin/python
# coding=utf-8
"""Application shell for the Metashape Workflow UI.

The Metashape SDK wrapper lives in
:mod:`extapps.photogrammetry.metashape_workflow._metashape_workflow` (SDK-coupled,
not generic) and slot bindings in :mod:`extapps.photogrammetry.metashape_workflow.slots`;
this module only declares the panel (:class:`extapps._panel_launcher.PanelLauncher`
builds it) and provides the script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class MetashapeWorkflowUI(PanelLauncher):
    TITLE = "Metashape Workflow"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    MetashapeWorkflowUI().show(pos="screen", app_exec=True)
