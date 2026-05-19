# !/usr/bin/python
# coding=utf-8
"""Metashape Workflow — Agisoft Metashape photogrammetry automation.

The Metashape SDK wrapper lives here (SDK-specific, not generic). The
generic ``FrameExtractor`` carve-out lives in
:mod:`pythontk.vid_utils.frame_extractor`.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.metashape_workflow"


DEFAULT_INCLUDE = {
    "_metashape_workflow": [
        "MetashapeWorkflow",
        "get_metashape_version",
        "is_license_valid",
        "is_metashape_available",
    ],
    "launcher": ["MetashapeWorkflowUI"],
    "slots": ["MetashapeWorkflowSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "MetashapeWorkflow",
    "MetashapeWorkflowUI",
    "MetashapeWorkflowSlots",
    "get_metashape_version",
    "is_license_valid",
    "is_metashape_available",
]
