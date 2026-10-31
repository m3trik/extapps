# !/usr/bin/python
# coding=utf-8
"""Application shell for the Substance Workflow UI.

The Painter integration engine (``PainterConnection``, the op registry, and
the in-Painter bridge plugin) lives alongside this module; slot bindings are
in :mod:`extapps.substance_workflow.slots`. This module only declares the
panel (:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides
the script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class SubstanceWorkflowUI(PanelLauncher):
    TITLE = "Substance Workflow"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    SubstanceWorkflowUI().show(pos="screen", app_exec=True)
