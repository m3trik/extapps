# !/usr/bin/python
# coding=utf-8
"""Pack per-channel source maps into one RGBA texture, or unpack a packed one.

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
