# !/usr/bin/python
# coding=utf-8
"""Run built-in and your own Python scripts in Substance 3D Painter, on a mesh file or a project.

A Switchboard panel (``SubstanceScriptsUI``) over :class:`SubstanceScripts`:
the Painter engine the Maya and Blender Substance Bridges use (vendored
byte-identical from the Maya library, so never edited here), with no host. A script is a
Python file Painter runs as written (``templates/*.py``, or the person's own in
``ptk.ScriptTemplate.user_dir("substance")``, which every host's bridge lists
too); the Painter it runs in is found by its instance record
(``substance_rpc``: a launched Painter, or the person's own once they
installed and ticked the plugin), never by a fixed port.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.substance_scripts"


DEFAULT_INCLUDE = {
    "launcher": ["SubstanceScriptsUI"],
    "slots": ["SubstanceScriptsSlots"],
    "_substance_scripts": ["SubstanceScripts"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["SubstanceScriptsUI", "SubstanceScriptsSlots", "SubstanceScripts"]
