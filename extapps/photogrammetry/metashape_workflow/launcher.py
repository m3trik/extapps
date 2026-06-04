# !/usr/bin/python
# coding=utf-8
"""Application shell for the Metashape Workflow UI.

The Metashape SDK wrapper lives in
:mod:`extapps.photogrammetry.metashape_workflow._metashape_workflow` (SDK-coupled,
not generic) and slot bindings in :mod:`extapps.photogrammetry.metashape_workflow.slots`;
this module only assembles the Switchboard-driven UI and provides the
script entry point.
"""
from uitk import configure_high_dpi

# Must run before QApplication is constructed, so before any import
# that touches Switchboard. No-ops inside DCC hosts that already own
# the QApplication.
configure_high_dpi()


class MetashapeWorkflowUI:
    def __new__(cls, *args, **kwargs):
        from qtpy import QtCore
        from uitk import Switchboard
        from extapps import __version__
        from extapps.photogrammetry.metashape_workflow.slots import MetashapeWorkflowSlots

        sb = Switchboard(
            *args,
            ui_source="./metashape_workflow.ui",
            slot_source=MetashapeWorkflowSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.metashape_workflow
        ui.set_attributes(WA_TranslucentBackground=True)
        # Frameless chromed window: the uitk Header supplies the window
        # controls in place of the native OS frame. Set the SAME clean flag
        # set as uitk's WindowPanel / editor reference rather than OR-ing
        # FramelessWindowHint onto a QMainWindow's defaults — those defaults
        # carry native decoration hints which, on a frameless host-owned
        # window, make it float always-on-top of its parent. With the clean
        # set it behaves as a normal window that parents to the host (e.g.
        # Maya, via the external-app handler) without staying on top.
        ui.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
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
