# !/usr/bin/python
# coding=utf-8
"""Marmoset Scripts: run Toolbag scripts, the bundled ones and your own, on a model file.

The DCC-agnostic Toolbag engine (:mod:`._marmoset_engine`), vendored
byte-identical with the host bridges' copy (``test_vendor_sync`` holds them
equal): Toolbag SDK glue rather than a generic pythontk utility, so it lives
with its consumers. :class:`MarmosetScripts` is its door for this package's
standalone panel (``slots.py``, ``launcher.py``): pick a model file (FBX / OBJ
/ USD / glTF) and run a script on it -- the bundled ``import`` or ``lookdev``,
or one of your own -- into a ready-to-render Toolbag scene, no DCC required.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.marmoset_scripts"


DEFAULT_INCLUDE = {
    "_marmoset_scripts": ["MarmosetScripts"],
    "launcher": ["MarmosetScriptsUI"],
    "slots": ["MarmosetScriptsSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["MarmosetScripts", "MarmosetScriptsUI", "MarmosetScriptsSlots"]
