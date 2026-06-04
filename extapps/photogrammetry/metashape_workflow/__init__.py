# !/usr/bin/python
# coding=utf-8
"""Metashape Workflow — Agisoft Metashape photogrammetry automation.

The Metashape SDK wrapper lives here (SDK-specific, not generic). The
generic ``FrameExtractor`` carve-out lives in
:mod:`pythontk.vid_utils.frame_extractor`.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.photogrammetry.metashape_workflow"


DEFAULT_INCLUDE = {
    "_metashape_workflow": [
        "DEFAULT_GATES",
        "GateError",  # re-exported from pythontk.QcGate for back-compat
        "MetashapeWorkflow",
        "QcGate",     # re-exported from pythontk
        "QcLog",      # re-exported from pythontk
        "get_image_filepaths",
        "get_metashape_version",
        "is_license_valid",
        "is_metashape_available",
    ],
    "_metashape_connection": ["MetashapeConnection"],
    "launcher": ["MetashapeWorkflowUI"],
    "slots": ["MetashapeWorkflowSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "DEFAULT_GATES",
    "GateError",
    "MetashapeConnection",
    "MetashapeWorkflow",
    "MetashapeWorkflowUI",
    "MetashapeWorkflowSlots",
    "QcGate",
    "QcLog",
    "get_image_filepaths",
    "get_metashape_version",
    "is_license_valid",
    "is_metashape_available",
]
