# !/usr/bin/python
# coding=utf-8
"""extapps — the standalone content-pipeline apps: each app's engine, panel and Slots class.

A product, not a library: no package imports it, and it imports no host (no
Maya, no Blender) and no tentacle -- only pythontk and uitk. Each app is a
self-contained subpackage (``<app>.ui``, ``slots.py``, ``launcher.py``, and its
engine where it has one of its own) registered via the
``uitk.external_apps.in_process`` entry-point group (see ``pyproject.toml``).
Hosts (tentacle's menus in Maya and Blender) open an app BY NAME through uitk's
``ExternalAppHandler`` -- no host-side knowledge required; ``python -m extapps``
(``__main__.py``) opens them outside any host.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps"
__version__ = "0.8.0"

# Base of every panel's "detailed docs" link (``BridgeSlotsBase.DOCS_URL`` on
# the bridge panels, the compositor's intro, Substance's startup line): the
# public repo at ``main``, so each panel appends only its repo-relative doc
# path -- one place to repoint at a fork, a docs site, or a release tag.
DOCS_BASE_URL = "https://github.com/m3trik/extapps/blob/main/"


DEFAULT_INCLUDE = {
    "texture_maps.compositor.launcher": ["CompositorUI"],
    "texture_maps.compositor.slots": ["CompositorSlots"],
    "photogrammetry.profile": ["Profile", "IMAGE_EXTS", "QUALITY_TIERS"],
    "photogrammetry.prep_stages": ["PrepStagesMixin"],
    "photogrammetry.metashape_workflow.launcher": ["MetashapeWorkflowUI"],
    "photogrammetry.metashape_workflow.slots": ["MetashapeWorkflowSlots"],
    "photogrammetry.metashape_workflow._metashape_workflow": ["MetashapeWorkflow"],
    "photogrammetry.metashape_workflow._metashape_runner": ["MetashapeRunner"],
    "photogrammetry.realityscan_workflow.launcher": ["RealityScanWorkflowUI"],
    "photogrammetry.realityscan_workflow.slots": ["RealityscanWorkflowSlots"],
    "photogrammetry.realityscan_workflow._realityscan_runner": ["RealityScanRunner"],
    "photogrammetry.gaussian_splat_workflow.launcher": ["GaussianSplatWorkflowUI"],
    "photogrammetry.gaussian_splat_workflow.slots": ["GaussianSplatWorkflowSlots"],
    "photogrammetry.gaussian_splat_workflow._gaussian_splat_runner": [
        "GaussianSplatRunner",
        "BrushInstallRunner",
    ],
    "substance_workflow.launcher": ["SubstanceWorkflowUI"],
    "substance_workflow.slots": ["SubstanceWorkflowSlots"],
    "substance_workflow.env_utils.painter_connection": ["PainterConnection"],
    "substance_workflow.env_utils.painter_finder": ["PainterFinder"],
    "substance_workflow.job": ["Job"],
    "texture_maps.converter.launcher": ["ConverterUI"],
    "texture_maps.converter.slots": ["ConverterSlots"],
    "texture_maps.converter._converter": ["MapConverter"],
    "texture_maps.packer.launcher": ["PackerUI"],
    "texture_maps.packer.slots": ["PackerSlots"],
    "mesh_convert.launcher": ["MeshConvertUI"],
    "mesh_convert.slots": ["MeshConvertSlots"],
    "marmoset_workflow.launcher": ["MarmosetWorkflowUI"],
    "marmoset_workflow.slots": ["MarmosetWorkflowSlots"],
    "marmoset_workflow._marmoset_workflow": ["MarmosetWorkflow"],
    "unity_workflow.launcher": ["UnityWorkflowUI"],
    "unity_workflow.slots": ["UnityWorkflowSlots"],
    "webxr_preview.launcher": ["WebXrPreviewUI"],
    "webxr_preview.slots": ["WebXrPreviewSlots"],
    "look_match.launcher": ["LookMatchUI"],
    "look_match.slots": ["LookMatchSlots"],
}


# ``bootstrap_package`` derives ``__all__`` from the resolved surface
# (DEFAULT_INCLUDE) and unions in anything declared here first — so only the
# non-derivable ``__version__`` needs listing by hand.
__all__ = ["__version__", "DOCS_BASE_URL"]

bootstrap_package(globals(), include=DEFAULT_INCLUDE)
