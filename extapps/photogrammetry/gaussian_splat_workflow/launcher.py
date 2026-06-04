# !/usr/bin/python
# coding=utf-8
"""Application shell for the Brush (gaussian-splat) Workflow UI.

Assembles the Switchboard-driven panel and provides the script entry point;
slot bindings live in :mod:`extapps.photogrammetry.gaussian_splat_workflow.slots`.
"""
from uitk import configure_high_dpi

# Must run before QApplication is constructed. No-ops inside DCC hosts that
# already own the QApplication.
configure_high_dpi()


class GaussianSplatWorkflowUI:
    def __new__(cls, *args, **kwargs):
        from qtpy import QtCore
        from uitk import Switchboard
        from extapps import __version__
        from extapps.photogrammetry.gaussian_splat_workflow.slots import (
            GaussianSplatWorkflowSlots,
        )

        sb = Switchboard(
            *args,
            ui_source="./gaussian_splat_workflow.ui",
            slot_source=GaussianSplatWorkflowSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.gaussian_splat_workflow
        ui.set_attributes(WA_TranslucentBackground=True)
        # Frameless chromed window matching uitk's WindowPanel/editor
        # reference (see metashape_workflow.launcher for the rationale):
        # the clean flag set keeps the host-owned window normal, not
        # always-on-top.
        ui.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        ui.style.set(theme="dark", style_class="bgWithBorder")

        ui.header.config_buttons("menu", "minimize", "fullscreen", "hide")
        ui.header.setVersion(__version__)

        ui.setWindowTitle(f"Brush Splat Workflow v{__version__}")
        ui.resize(ui.sizeHint())
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ui = GaussianSplatWorkflowUI()
    ui.show(pos="screen", app_exec=True)
