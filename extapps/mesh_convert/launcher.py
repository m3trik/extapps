# !/usr/bin/python
# coding=utf-8
"""Application shell for the Mesh Convert UI.

Engine logic lives in :mod:`pythontk.file_utils.mesh_convert` and slot
bindings in :mod:`extapps.mesh_convert.slots`; this module only assembles
the Switchboard-driven UI and provides the script entry point.
"""
from uitk import configure_high_dpi

# Must run before QApplication is constructed, so before any import
# that touches Switchboard. No-ops inside DCC hosts that already own
# the QApplication.
configure_high_dpi()


class MeshConvertUI:
    def __new__(cls):
        from uitk import Switchboard
        from extapps.mesh_convert.slots import MeshConvertSlots

        sb = Switchboard(ui_source="mesh_convert.ui", slot_source=MeshConvertSlots)
        ui = sb.loaded_ui.mesh_convert

        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="translucentBgWithBorder")
        ui.header.config_buttons("menu", "minimize", "hide")
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    MeshConvertUI().show(pos="screen", app_exec=True)
