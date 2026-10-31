# !/usr/bin/python
# coding=utf-8
"""Application shell for the WebXR Preview UI.

The transport engine lives in :mod:`pythontk.net_utils.preview` (server,
deliverer, bridges) and the slot bindings in
:mod:`extapps.webxr_preview.slots`; this module only declares the
panel (:class:`extapps._panel_launcher.PanelLauncher` builds it) and provides the
script entry point.
"""

from extapps._panel_launcher import PanelLauncher


class WebXrPreviewUI(PanelLauncher):
    TITLE = "WebXR Preview"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    WebXrPreviewUI().show(pos="screen", app_exec=True)
