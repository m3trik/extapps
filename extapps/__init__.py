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
__version__ = "0.1.15"

# Base of every panel's "detailed docs" link (``BridgeSlotsBase.DOCS_URL`` on
# the bridge panels, the compositor's intro, Substance's startup line): the
# public repo at ``main``, so each panel appends only its repo-relative doc
# path -- one place to repoint at a fork, a docs site, or a release tag.
DOCS_BASE_URL = "https://github.com/m3trik/extapps/blob/main/"


DEFAULT_INCLUDE = {
    "texture_maps.compositor.launcher": ["CompositorUI"],
    "texture_maps.compositor.slots": ["CompositorSlots"],
    "photogrammetry.metashape_workflow.launcher": ["MetashapeWorkflowUI"],
    "photogrammetry.metashape_workflow.slots": ["MetashapeWorkflowSlots"],
    "photogrammetry.metashape_workflow._metashape_workflow": ["MetashapeWorkflow"],
    "photogrammetry.realityscan_workflow.launcher": ["RealityScanWorkflowUI"],
    "photogrammetry.realityscan_workflow.slots": ["RealityscanWorkflowSlots"],
    "photogrammetry.gaussian_splat_workflow.launcher": ["GaussianSplatWorkflowUI"],
    "photogrammetry.gaussian_splat_workflow.slots": ["GaussianSplatWorkflowSlots"],
    "substance_workflow.launcher": ["SubstanceWorkflowUI"],
    "substance_workflow.slots": ["SubstanceWorkflowSlots"],
    "substance_workflow.env_utils.painter_connection": ["PainterConnection"],
    "substance_workflow.env_utils.painter_finder": ["PainterFinder"],
    "substance_workflow.job": ["Call", "Job", "Result"],
    "texture_maps.converter.launcher": ["ConverterUI"],
    "texture_maps.converter.slots": ["ConverterSlots"],
    "texture_maps.packer.launcher": ["PackerUI"],
    "texture_maps.packer.slots": ["PackerSlots"],
    "mesh_convert.launcher": ["MeshConvertUI"],
    "mesh_convert.slots": ["MeshConvertSlots"],
    "marmoset_workflow.launcher": ["MarmosetWorkflowUI"],
    "marmoset_workflow.slots": ["MarmosetWorkflowSlots"],
    "unity_workflow.launcher": ["UnityWorkflowUI"],
    "unity_workflow.slots": ["UnityWorkflowSlots"],
}


# ``bootstrap_package`` derives ``__all__`` from the resolved panel surface
# (DEFAULT_INCLUDE) and unions in anything declared here first — so only the
# non-derivable ``__version__`` needs listing by hand.
__all__ = ["__version__", "DOCS_BASE_URL"]

bootstrap_package(globals(), include=DEFAULT_INCLUDE)
