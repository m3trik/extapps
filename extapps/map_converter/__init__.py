# !/usr/bin/python
# coding=utf-8
"""Map Converter — texture conversion, channel packing, PBR-workflow prep.

Engine logic lives in :class:`pythontk.ImgUtils` and
:class:`pythontk.MapFactory`; this package holds only the Switchboard
panel and launcher.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.map_converter"


DEFAULT_INCLUDE = {
    "launcher": ["MapConverterUI"],
    "slots": ["MapConverterSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["MapConverterUI", "MapConverterSlots"]
