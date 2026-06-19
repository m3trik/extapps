# !/usr/bin/python
# coding=utf-8
"""Application shell for the Unity Studio launcher UI.

The engine half (editor discovery + launch + project creation) lives in ``unitytk``
(:class:`unitytk.UnityLauncher` / :class:`unitytk.UnityFinder`); the slot bindings in
:mod:`extapps.unity_studio.slots`. This module only assembles the Switchboard-driven
UI and provides the script entry point.
"""
from uitk import configure_high_dpi

# Must run before QApplication is constructed (before any Switchboard import).
# No-ops inside DCC hosts that already own the QApplication.
configure_high_dpi()


class UnityStudioUI:
    def __new__(cls, *args, **kwargs):
        from uitk import Switchboard
        from extapps import __version__
        from extapps.unity_studio.slots import UnityStudioSlots

        sb = Switchboard(
            *args,
            ui_source="./unity_studio.ui",
            slot_source=UnityStudioSlots,
            **kwargs,
        )
        ui = sb.loaded_ui.unity_studio
        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="bgWithBorder")

        ui.header.config_buttons("menu", "minimize", "fullscreen", "hide")
        ui.header.setVersion(__version__)

        ui.setWindowTitle(f"Unity Studio v{__version__}")
        ui.resize(ui.sizeHint())
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ui = UnityStudioUI()
    ui.show(pos="screen", app_exec=True)
