# !/usr/bin/python
# coding=utf-8
"""WebXR Preview — the live browser / headset preview panel.

The single UI for the preview loop, for every source. Transport and build
logic live in :mod:`pythontk.net_utils.preview` (``PreviewServer``,
``PreviewDeliverer``, ``PreviewBridge``, ``FilePreviewBridge``); this package
holds only the Switchboard panel and launcher.

A DCC host opens it through uitk's ``ExternalAppHandler`` and injects its own
bridge, which grows the Source combo by that host's scopes. With no host it
previews an FBX or GLB from disk. Nothing here is host-specific.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.webxr_preview"


DEFAULT_INCLUDE = {
    "launcher": ["WebXrPreviewUI"],
    "slots": ["WebXrPreviewSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["WebXrPreviewUI", "WebXrPreviewSlots"]
