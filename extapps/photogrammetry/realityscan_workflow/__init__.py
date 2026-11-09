# !/usr/bin/python
# coding=utf-8
"""Turn photos or video frames into a textured mesh with headless RealityScan.

Engine wrapper for RealityScan, mirroring
:class:`extapps.photogrammetry.metashape_workflow._metashape_workflow.MetashapeWorkflow`
so the same panel scaffolding targets either engine. RealityScan has no Python API, so the
wrapper drives the CLI / RSNode REST via :mod:`subprocess`. The RealityScan
Workflow panel (``slots.py``, ``launcher.py``) drives it through
:class:`RealityScanRunner`.

Exposed via :func:`pythontk.bootstrap_package` (lazy) so importing the headless
runner (``run_combined``) never eagerly pulls in Qt through the UI launcher.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.photogrammetry.realityscan_workflow"


DEFAULT_INCLUDE = {
    "_realityscan_workflow": ["RealityScanWorkflow"],
    "_realityscan_connection": [
        "RealityScanConnection",
        "RealityScanInteractiveError",
    ],
    "_realityscan_runner": ["RealityScanRunner"],
    "launcher": ["RealityScanWorkflowUI"],
    "slots": ["RealityscanWorkflowSlots"],
}


# RealityCapture is RealityScan since 2.0.
MOVED_NAMES = {
    "RealityCaptureWorkflow": ("extapps.photogrammetry.realityscan_workflow.RealityScanWorkflow", "0.9.0"),
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE, moved=MOVED_NAMES)


__all__ = [
    "RealityScanWorkflow",
    "RealityScanConnection",
    "RealityScanInteractiveError",
    "RealityScanRunner",
    "RealityScanWorkflowUI",
    "RealityscanWorkflowSlots",
]
