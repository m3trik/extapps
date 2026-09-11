# !/usr/bin/python
# coding=utf-8
"""Application shell for the WebXR Preview UI.

The transport engine lives in :mod:`pythontk.net_utils.preview` (server,
deliverer, bridges) and the slot bindings in
:mod:`extapps.webxr_preview.slots`; this module only assembles the
Switchboard-driven UI and provides the script entry point.
"""

from uitk import Bootstrap

# Must run before QApplication is constructed, so before any import that
# touches Switchboard. No-ops inside DCC hosts that already own the
# QApplication.
Bootstrap.configure_high_dpi()


class WebXrPreviewUI:
    def __new__(cls, *args, **kwargs):
        from uitk import Switchboard
        from extapps import __version__
        from extapps.webxr_preview.slots import WebXrPreviewSlots

        sb = Switchboard(
            *args,
            ui_source="./webxr_preview.ui",
            slot_source=WebXrPreviewSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.webxr_preview
        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="bgWithBorder")

        ui.header.config_buttons("menu", "minimize", "fullscreen", "hide")
        ui.header.setVersion(__version__)

        ui.setWindowTitle(f"WebXR Preview v{__version__}")
        ui.resize(ui.sizeHint())
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ui = WebXrPreviewUI()
    ui.show(pos="screen", app_exec=True)
