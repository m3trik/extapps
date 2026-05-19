# !/usr/bin/python
# coding=utf-8
"""Mesh Convert — FBX → glTF / GLB conversion.

Engine logic lives in :mod:`pythontk.file_utils.mesh_convert`; this
package holds only the Switchboard panel and launcher.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.mesh_convert"


DEFAULT_INCLUDE = {
    "launcher": ["MeshConvertUI"],
    "slots": ["MeshConvertSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["MeshConvertUI", "MeshConvertSlots"]
