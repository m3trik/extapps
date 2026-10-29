# !/usr/bin/python
# coding=utf-8
"""Launch Marmoset Toolbag and set up an import or lookdev scene from a model file.

The DCC-agnostic Toolbag engine (:mod:`._marmoset_engine`), vendored
byte-identical with ``mayatk.mat_utils.marmoset_bridge``'s copy: Toolbag SDK
glue rather than a generic pythontk utility, so it lives with its consumers.
:class:`MarmosetWorkflow` is its door for the standalone Marmoset Workflow
panel, which is tentacle's (``slots/tools/marmoset_workflow.py``): pick a model
file (FBX / OBJ / USD / glTF) and run the ``import`` or ``lookdev`` template
into a ready-to-render Toolbag scene -- no DCC required.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.marmoset_workflow"


DEFAULT_INCLUDE = {
    "_marmoset_workflow": ["MarmosetWorkflow"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = ["MarmosetWorkflow"]
