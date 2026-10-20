# !/usr/bin/python
# coding=utf-8
"""Light a baked scene to match a reference image, by eye and region by region.

The panel over pythontk's look-match engine (``ptk.LookMatch``, ``ptk.LookLoop``,
``ptk.LookCapture``): the mix of light layers, a live comparison against the
reference, the regions that are off and the lights that own them, a WebXR
render, and a rig saved to the library a host builds from. The engine computes
every look; this package holds only the Switchboard panel and its launcher.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.look_match"


DEFAULT_INCLUDE = {
    "launcher": ["LookMatchUI"],
    "slots": ["LookMatchSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["LookMatchUI", "LookMatchSlots"]
