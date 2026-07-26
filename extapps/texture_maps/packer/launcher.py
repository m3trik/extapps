# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Packer UI.

Engine logic lives in :class:`pythontk.ImgUtils` / :class:`pythontk.MapFactory`
and slot bindings in :mod:`extapps.texture_maps.packer.slots`; this module only
assembles the Switchboard-driven UI and provides the script entry point.
"""

from uitk import Bootstrap

# Must run before QApplication is constructed, so before any import
# that touches Switchboard. No-ops inside DCC hosts that already own
# the QApplication.
Bootstrap.configure_high_dpi()


class PackerUI:
    def __new__(cls):
        from uitk import Switchboard
        from extapps.texture_maps.packer.slots import PackerSlots

        sb = Switchboard(ui_source="packer.ui", slot_source=PackerSlots)
        ui = sb.loaded_ui.packer
        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="translucentBgWithBorder")
        ui.header.config_buttons("menu", "minimize", "hide")
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    PackerUI().show(pos="screen", app_exec=True)
