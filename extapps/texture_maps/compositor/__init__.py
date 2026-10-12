# !/usr/bin/python
# coding=utf-8
"""Merge several texture maps of each type into one image, converting normal formats.

Engine lives in :mod:`pythontk.core_utils.engines.textures.map_compositor`; this package
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
