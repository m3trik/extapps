# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Packer UI.

Engine logic lives in :class:`pythontk.ImgUtils` / :class:`pythontk.MapFactory`
and slot bindings in :mod:`extapps.map_packer.slots`; this module only
assembles the Switchboard-driven UI and provides the script entry point.
"""
from uitk import configure_high_dpi

# Must run before QApplication is constructed, so before any import
# that touches Switchboard. No-ops inside DCC hosts that already own
# the QApplication.
configure_high_dpi()


class MapPackerUI:
    def __new__(cls):
        from uitk import Switchboard
        from extapps.map_packer.slots import MapPackerSlots

        sb = Switchboard(ui_source="map_packer.ui", slot_source=MapPackerSlots)
        ui = sb.loaded_ui.map_packer
        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="translucentBgWithBorder")
        ui.header.config_buttons("menu", "minimize", "hide")
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    MapPackerUI().show(pos="screen", app_exec=True)
