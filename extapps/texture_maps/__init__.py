# !/usr/bin/python
# coding=utf-8
"""Texture-maps umbrella: the texture/material-map tools' own rules.

The map panels (compositor / converter / packer) are tentacle's standalone
panels; their engines are ``pythontk.core_utils.engines.textures``
(``MapCompositor``, ``MapFactory``) plus :class:`pythontk.ImgUtils` for the
generic raster ops. What stays here is the one engine no other package needs:

* :mod:`~extapps.texture_maps.converter` -- the Map Converter's batch rules
  (:class:`MapConverter`).

No side effects on import; the root ``extapps`` ``DEFAULT_INCLUDE`` publishes
:class:`MapConverter`.
"""
