# !/usr/bin/python
# coding=utf-8
"""Application shell for the Marmoset Workflow UI.

The DCC-agnostic Toolbag engine is bundled in this subpackage
(:mod:`extapps.marmoset_workflow._marmoset_engine`), the parameter specs in
:mod:`extapps.marmoset_workflow.parameters`, and the slot bindings in
:mod:`extapps.marmoset_workflow.slots`; this module only declares the panel
(:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides the
script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class MarmosetWorkflowUI(PanelLauncher):
    TITLE = "Marmoset Workflow"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    MarmosetWorkflowUI().show(pos="screen", app_exec=True)
