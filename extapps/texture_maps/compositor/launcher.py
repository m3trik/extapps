# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Compositor UI.

The engine lives in :mod:`pythontk.core_utils.engines.textures.map_compositor` and the
slot bindings in :mod:`extapps.texture_maps.compositor.slots`; this module only
assembles the Switchboard-driven UI and provides the script entry point.
"""

from uitk import Bootstrap

# Must run before QApplication is constructed, so before any import
# that touches Switchboard. No-ops inside DCC hosts that already own
# the QApplication.
Bootstrap.configure_high_dpi()


class CompositorUI:
    def __new__(cls, *args, **kwargs):
        from uitk import Switchboard
        from extapps import __version__
        from extapps.texture_maps.compositor.slots import CompositorSlots

        sb = Switchboard(
            *args,
            ui_source="./compositor.ui",
            slot_source=CompositorSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.compositor

        ui.set_attributes(WA_TranslucentBackground=True)
        # Use the uitk Header in place of the native OS frame so the
        # options menu (and other header controls) stay visible.
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="bgWithBorder")

        # Expose the menu button (and standard window controls) on the header.
        # The title ("MAP COMPOSITOR") is set declaratively in the .ui file —
        # edit it via Qt Designer rather than here. Only the version
        # (release-dependent) is wired in at runtime.
        ui.header.config_buttons("menu", "minimize", "fullscreen", "hide")
        ui.header.setVersion(__version__)

        ui.setWindowTitle(f"Map Compositor v{__version__}")
        ui.resize(ui.sizeHint())
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ui = CompositorUI()
    ui.show(pos="screen", app_exec=True)
