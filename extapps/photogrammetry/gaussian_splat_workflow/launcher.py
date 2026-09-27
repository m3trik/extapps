# !/usr/bin/python
# coding=utf-8
"""Application shell for the Brush (gaussian-splat) Workflow UI.

Declares the panel (:class:`extapps._panel_launcher.PanelLauncher` builds
it) and provides the script entry point; slot bindings live in
:mod:`extapps.photogrammetry.gaussian_splat_workflow.slots`.
"""

from extapps._panel_launcher import PanelLauncher


class GaussianSplatWorkflowUI(PanelLauncher):
    TITLE = "Brush Splat Workflow"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    GaussianSplatWorkflowUI().show(pos="screen", app_exec=True)
