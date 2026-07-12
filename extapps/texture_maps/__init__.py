# !/usr/bin/python
# coding=utf-8
"""Texture-maps umbrella — the texture/material-map tools.

Groups the map-domain Switchboard panels that all sit on top of the
``pythontk.core_utils.engines.textures`` engines (plus ``pythontk.ImgUtils``
for the generic raster ops):

* :mod:`~extapps.texture_maps.compositor` — multi-layer texture compositing
  (engine: ``MapCompositor``).
* :mod:`~extapps.texture_maps.converter` — texture conversion / PBR-workflow prep
  (engine: ``MapFactory`` / :class:`pythontk.ImgUtils`).
* :mod:`~extapps.texture_maps.packer` — channel-pack textures from per-channel
  source maps (engine: ``MapFactory`` / :class:`pythontk.ImgUtils`).

No side effects on import — the tool panels register via the root ``extapps``
``DEFAULT_INCLUDE`` and the ``uitk.external_apps.in_process`` entry points
(see ``pyproject.toml``). The ``uitk`` app-ids are ``compositor`` /
``converter`` / ``packer``, matching the subpackage and slot-class names.
"""
