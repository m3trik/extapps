# !/usr/bin/python
# coding=utf-8
"""Application shell for the Marmoset Workflow UI.

The DCC-agnostic Toolbag engine is bundled in this subpackage
(:mod:`extapps.marmoset_workflow._marmoset_engine`), the parameter specs in
:mod:`extapps.marmoset_workflow.parameters`, and the slot bindings in
:mod:`extapps.marmoset_workflow.slots`; this module only assembles the
Switchboard-driven UI and provides the script entry point.
"""
from uitk import configure_high_dpi

# Must run before QApplication is constructed, so before any import that
# touches Switchboard. No-ops inside DCC hosts that already own the
# QApplication.
configure_high_dpi()


class MarmosetWorkflowUI:
    def __new__(cls, *args, **kwargs):
        from uitk import Switchboard
        from extapps import __version__
        from extapps.marmoset_workflow.slots import MarmosetWorkflowSlots

        sb = Switchboard(
            *args,
            ui_source="./marmoset_workflow.ui",
            slot_source=MarmosetWorkflowSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.marmoset_workflow
        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="bgWithBorder")

        ui.header.config_buttons("menu", "minimize", "fullscreen", "hide")
        ui.header.setVersion(__version__)

        ui.setWindowTitle(f"Marmoset Workflow v{__version__}")
        ui.resize(ui.sizeHint())
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ui = MarmosetWorkflowUI()
    ui.show(pos="screen", app_exec=True)
