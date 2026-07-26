# !/usr/bin/python
# coding=utf-8
"""Application shell for the Map Converter UI.

Engine logic lives in :class:`pythontk.ImgUtils` / :class:`pythontk.MapFactory`
and slot bindings in :mod:`extapps.texture_maps.converter.slots`; this module
only assembles the Switchboard-driven UI and provides the script
entry point.
"""

from uitk import Bootstrap

# Must run before QApplication is constructed, so before any import
# that touches Switchboard. No-ops inside DCC hosts that already own
# the QApplication.
Bootstrap.configure_high_dpi()


class ConverterUI:
    """Standalone launcher. Constructing the class returns a configured UI.

    ``__new__`` is overridden to return the wired Switchboard UI directly,
    so ``ConverterUI()`` yields the UI (not an instance). Use this when
    running outside a host DCC. Hosts that need to inject a
    ``texture_provider`` should register :class:`ConverterSlots`
    themselves rather than going through this launcher.
    """

    def __new__(cls):
        from uitk import Switchboard
        from extapps.texture_maps.converter.slots import ConverterSlots

        sb = Switchboard(ui_source="converter.ui", slot_source=ConverterSlots)
        ui = sb.loaded_ui.converter

        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="translucentBgWithBorder")
        ui.header.config_buttons("menu", "minimize", "hide")
        return ui


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    ConverterUI().show(pos="screen", app_exec=True)
