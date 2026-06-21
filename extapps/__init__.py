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
__version__ = "0.1.7"


DEFAULT_INCLUDE = {
    "texture_maps.compositor.launcher": ["CompositorUI"],
    "texture_maps.compositor.slots": ["CompositorSlots"],
    "photogrammetry.metashape_workflow.launcher": ["MetashapeWorkflowUI"],
    "photogrammetry.metashape_workflow.slots": ["MetashapeWorkflowSlots"],
    "photogrammetry.metashape_workflow._metashape_workflow": [
        "MetashapeWorkflow",
        "get_image_filepaths",
        "get_metashape_version",
        "is_license_valid",
        "is_metashape_available",
    ],
    "substance_workflow.launcher": ["SubstanceWorkflowUI"],
    "substance_workflow.slots": ["SubstanceWorkflowSlots"],
    "substance_workflow.env_utils.painter_connection": ["PainterConnection"],
    "substance_workflow.env_utils.painter_finder": ["PainterFinder"],
    "substance_workflow.job": ["Call", "Job", "Result", "run_batch"],
    "texture_maps.converter.launcher": ["ConverterUI"],
    "texture_maps.converter.slots": ["ConverterSlots"],
    "texture_maps.packer.launcher": ["PackerUI"],
    "texture_maps.packer.slots": ["PackerSlots"],
    "mesh_convert.launcher": ["MeshConvertUI"],
    "mesh_convert.slots": ["MeshConvertSlots"],
    "marmoset_workflow.launcher": ["MarmosetWorkflowUI"],
    "marmoset_workflow.slots": ["MarmosetWorkflowSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "CompositorUI",
    "CompositorSlots",
    "MetashapeWorkflowUI",
    "MetashapeWorkflowSlots",
    "MetashapeWorkflow",
    "get_image_filepaths",
    "get_metashape_version",
    "is_license_valid",
    "is_metashape_available",
    "SubstanceWorkflowUI",
    "SubstanceWorkflowSlots",
    "PainterConnection",
    "PainterFinder",
    "Call",
    "Job",
    "Result",
    "run_batch",
    "ConverterUI",
    "ConverterSlots",
    "PackerUI",
    "PackerSlots",
    "MeshConvertUI",
    "MeshConvertSlots",
    "MarmosetWorkflowUI",
    "MarmosetWorkflowSlots",
    "__version__",
]
