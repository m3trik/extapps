# !/usr/bin/python
# coding=utf-8
"""Marmoset Workflow — launch Marmoset Toolbag and set up a project.

A standalone Switchboard panel over the DCC-agnostic Toolbag engine
bundled in this subpackage (:mod:`._marmoset_engine`). The engine is
Toolbag SDK glue rather than a generic pythontk utility, so it lives with
its consumer (mirroring ``substance_workflow``); the Maya bridge in
``mayatk.mat_utils.marmoset_bridge`` keeps its own copy. Picks a model
file (FBX / OBJ / USD / glTF) and runs the ``import`` or ``lookdev``
template to drop the user into a ready-to-render Toolbag scene -- no DCC
required.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.marmoset_workflow"


DEFAULT_INCLUDE = {
    "launcher": ["MarmosetWorkflowUI"],
    "slots": ["MarmosetWorkflowSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "MarmosetWorkflowUI",
    "MarmosetWorkflowSlots",
]
