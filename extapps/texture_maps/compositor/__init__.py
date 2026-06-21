# !/usr/bin/python
# coding=utf-8
"""Map Compositor — multi-layer texture compositing tool.

Engine lives in :mod:`pythontk.img_utils.map_compositor`; this package
holds only the Switchboard panel and launcher.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.texture_maps.compositor"


DEFAULT_INCLUDE = {
    "launcher": ["CompositorUI"],
    "slots": ["CompositorSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["CompositorUI", "CompositorSlots"]
