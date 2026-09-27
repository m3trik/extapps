# !/usr/bin/python
# coding=utf-8
"""Map Converter — texture conversion, channel packing, PBR-workflow prep.

Image engine logic lives in :class:`pythontk.ImgUtils` and
:class:`pythontk.MapFactory`; this package holds the converter's own Qt-free
batch rules (:class:`MapConverter`), the Switchboard panel that drives them and
its launcher.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.texture_maps.converter"


DEFAULT_INCLUDE = {
    "_converter": ["MapConverter"],
    "launcher": ["ConverterUI"],
    "slots": ["ConverterSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["ConverterUI", "ConverterSlots", "MapConverter"]
