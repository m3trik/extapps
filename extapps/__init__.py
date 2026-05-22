# !/usr/bin/python
# coding=utf-8
"""extapps — standalone Switchboard panels for content-pipeline workflows.

Each subpackage is a self-contained app registered via the
``uitk.external_apps.in_process`` entry-point group (see ``pyproject.toml``).
Hosts (tentacle, mayatk, etc.) discover and launch them through uitk's
``ExternalAppHandler`` — no host-side knowledge required.
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps"
__version__ = "0.1.3"


DEFAULT_INCLUDE = {
    "map_compositor.launcher": ["MapCompositorUI"],
    "map_compositor.slots": ["MapCompositorSlots"],
    "metashape_workflow.launcher": ["MetashapeWorkflowUI"],
    "metashape_workflow.slots": ["MetashapeWorkflowSlots"],
    "metashape_workflow._metashape_workflow": [
        "MetashapeWorkflow",
        "get_image_filepaths",
        "get_metashape_version",
        "is_license_valid",
        "is_metashape_available",
    ],
    "map_converter.launcher": ["MapConverterUI"],
    "map_converter.slots": ["MapConverterSlots"],
    "map_packer.launcher": ["MapPackerUI"],
    "map_packer.slots": ["MapPackerSlots"],
    "mesh_convert.launcher": ["MeshConvertUI"],
    "mesh_convert.slots": ["MeshConvertSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "MapCompositorUI",
    "MapCompositorSlots",
    "MetashapeWorkflowUI",
    "MetashapeWorkflowSlots",
    "MetashapeWorkflow",
    "get_image_filepaths",
    "get_metashape_version",
    "is_license_valid",
    "is_metashape_available",
    "MapConverterUI",
    "MapConverterSlots",
    "MapPackerUI",
    "MapPackerSlots",
    "MeshConvertUI",
    "MeshConvertSlots",
    "__version__",
]
