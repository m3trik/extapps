# !/usr/bin/python
# coding=utf-8
"""Application shell for the Substance Workflow UI.

The Painter integration engine (``PainterConnection``, the op registry, and
the in-Painter bridge plugin) lives alongside this module; slot bindings are
in :mod:`extapps.substance_workflow.slots`. This module only assembles the
Switchboard-driven UI and provides the script entry point.
"""

from uitk import Bootstrap

# Must run before QApplication is constructed, so before any import that
# touches Switchboard. No-ops inside DCC hosts that already own the
# QApplication.
Bootstrap.configure_high_dpi()


class SubstanceWorkflowUI:
    def __new__(cls, *args, **kwargs):
        from uitk import Switchboard
        from extapps import __version__
        from extapps.substance_workflow.slots import SubstanceWorkflowSlots

        sb = Switchboard(
            *args,
            ui_source="./substance_workflow.ui",
            slot_source=SubstanceWorkflowSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.substance_workflow
        ui.set_attributes(WA_TranslucentBackground=True)
        # Use the uitk Header in place of the native OS frame so window
        # controls live on the header (matches the other extapps panels).
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="bgWithBorder")

        ui.header.config_buttons("menu", "minimize", "fullscreen", "hide")
        ui.header.setVersion(__version__)

        ui.setWindowTitle(f"Substance Workflow v{__version__}")
        ui.resize(ui.sizeHint())
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ui = SubstanceWorkflowUI()
    ui.show(pos="screen", app_exec=True)
