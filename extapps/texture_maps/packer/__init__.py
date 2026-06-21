# !/usr/bin/python
# coding=utf-8
"""Map Packer — channel-pack textures from per-channel source maps.

Engine logic lives in :class:`pythontk.ImgUtils` and
:class:`pythontk.MapFactory`; this package holds only the Switchboard
panel and launcher.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.texture_maps.packer"


DEFAULT_INCLUDE = {
    "launcher": ["PackerUI"],
    "slots": ["PackerSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["PackerUI", "PackerSlots"]
