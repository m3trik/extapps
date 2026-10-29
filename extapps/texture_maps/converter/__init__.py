# !/usr/bin/python
# coding=utf-8
"""The Map Converter's batch rules: plan, name and run one map at a time.

Image engine logic lives in :class:`pythontk.ImgUtils` and
:class:`pythontk.MapFactory`; this package holds the converter's own Qt-free
batch rules (:class:`MapConverter`). The panel that drives them is tentacle's
(``tentacle/slots/tools/converter.py``).
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.texture_maps.converter"


DEFAULT_INCLUDE = {
    "_converter": ["MapConverter"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["MapConverter"]
