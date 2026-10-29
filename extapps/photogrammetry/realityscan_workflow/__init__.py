# !/usr/bin/python
# coding=utf-8
"""Turn photos or video frames into a textured mesh with headless RealityCapture.

Engine wrapper for RealityCapture / RealityScan, mirroring
:class:`extapps.photogrammetry.metashape_workflow._metashape_workflow.MetashapeWorkflow`
so the same panel scaffolding targets either engine. RC has no Python API, so the
wrapper drives the CLI / RSNode REST via :mod:`subprocess`. tentacle's RealityCapture
Workflow panel (``slots/tools/realityscan_workflow.py``) drives it through
:class:`RealityScanRunner`.

Exposed via :func:`pythontk.bootstrap_package` (lazy) so importing the headless
runner (``run_combined``) never eagerly pulls in Qt through the panel runner.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.photogrammetry.realityscan_workflow"


DEFAULT_INCLUDE = {
    "_realityscan_workflow": ["RealityCaptureWorkflow"],
    "_realityscan_connection": [
        "RealityScanConnection",
        "RealityScanInteractiveError",
    ],
    "_realityscan_runner": ["RealityScanRunner"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "RealityCaptureWorkflow",
    "RealityScanConnection",
    "RealityScanInteractiveError",
    "RealityScanRunner",
]
