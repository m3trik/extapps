# !/usr/bin/python
# coding=utf-8
"""Application shell for the Metashape Workflow UI.

The Metashape SDK wrapper lives in
:mod:`extapps.metashape_workflow._metashape_workflow` (SDK-coupled,
not generic) and slot bindings in :mod:`extapps.metashape_workflow.slots`;
this module only assembles the Switchboard-driven UI and provides the
script entry point.
"""


class MetashapeWorkflowUI:
    def __new__(cls, *args, **kwargs):
        from uitk import Switchboard
        from extapps import __version__
        from extapps.metashape_workflow.slots import MetashapeWorkflowSlots

        sb = Switchboard(
            *args,
            ui_source="./metashape_workflow.ui",
            slot_source=MetashapeWorkflowSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.metashape_workflow
        ui.set_attributes(WA_TranslucentBackground=True)
        # Use the uitk Header in place of the native OS frame so window
        # controls live on the header (matches map_compositor pattern).
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="bgWithBorder")

        # Surface window controls on the header now that the OS frame is gone.
        ui.header.config_buttons("menu", "minimize", "fullscreen", "hide")
        ui.header.setVersion(__version__)

        ui.setWindowTitle(f"Metashape Workflow v{__version__}")
        ui.resize(ui.sizeHint())
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ui = MetashapeWorkflowUI()
    ui.show(pos="screen", app_exec=True)
