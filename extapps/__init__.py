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
__version__ = "0.9.0"

# Base of every panel's "detailed docs" link (``ParamPanelSlots.DOCS_URL`` on
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
    "substance_scripts.launcher": ["SubstanceScriptsUI"],
    "substance_scripts.slots": ["SubstanceScriptsSlots"],
    "substance_scripts._substance_scripts": ["SubstanceScripts"],
    "texture_maps.converter.launcher": ["ConverterUI"],
    "texture_maps.converter.slots": ["ConverterSlots"],
    "texture_maps.converter._converter": ["MapConverter"],
    "texture_maps.packer.launcher": ["PackerUI"],
    "texture_maps.packer.slots": ["PackerSlots"],
    "mesh_convert.launcher": ["MeshConvertUI"],
    "mesh_convert.slots": ["MeshConvertSlots"],
    "marmoset_scripts.launcher": ["MarmosetScriptsUI"],
    "marmoset_scripts.slots": ["MarmosetScriptsSlots"],
    "marmoset_scripts._marmoset_scripts": ["MarmosetScripts"],
    "unity_scripts.launcher": ["UnityScriptsUI"],
    "unity_scripts.slots": ["UnityScriptsSlots"],
    "unity_scripts.unity_connection": ["UnityConnection"],
    "unity_scripts.unity_deliverer": ["UnityDeliverer"],
    "webxr_preview.launcher": ["WebXrPreviewUI"],
    "webxr_preview.slots": ["WebXrPreviewSlots"],
    "look_match.launcher": ["LookMatchUI"],
    "look_match.slots": ["LookMatchSlots"],
}


#: Public names merged away (CODE_STANDARD section 5): a read raises
#: ``MovedNameError`` naming the new home. ``{name: (new home, version)}``.
MOVED_NAMES = {
    # One Unity panel now: the behavior the two Unity panels shared through a
    # vendored mixin is the Unity panel's own.
    "UnityPanelMixin": ("extapps.UnityScriptsSlots", "0.8.0"),
    # The Unity Workflow became Unity Scripts, a script manager.
    "UnityWorkflowUI": ("extapps.UnityScriptsUI", "0.9.0"),
    "UnityWorkflowSlots": ("extapps.UnityScriptsSlots", "0.9.0"),
    # The Marmoset Workflow became Marmoset Scripts: the bundled scripts and a
    # person's own.
    "MarmosetWorkflowUI": ("extapps.MarmosetScriptsUI", "0.9.0"),
    "MarmosetWorkflowSlots": ("extapps.MarmosetScriptsSlots", "0.9.0"),
    "MarmosetWorkflow": ("extapps.MarmosetScripts", "0.9.0"),
    # The Substance Workflow became Substance Scripts: Python scripts run in
    # Painter on the one Painter engine and plugin the host bridges use (its
    # own Painter connection, finder, op registry and batch job went with it).
    "SubstanceWorkflowUI": ("extapps.SubstanceScriptsUI", "0.9.0"),
    "SubstanceWorkflowSlots": ("extapps.SubstanceScriptsSlots", "0.9.0"),
    "PainterConnection": ("extapps.SubstanceScripts", "0.9.0"),
    "PainterFinder": ("extapps.SubstanceScripts", "0.9.0"),
    "Job": ("extapps.SubstanceScripts", "0.9.0"),
    # The three subpackages themselves, renamed with their panels: a row naming
    # one covers every module, function and constant it held.
    "unity_workflow": ("extapps.unity_scripts", "0.9.0"),
    "marmoset_workflow": ("extapps.marmoset_scripts", "0.9.0"),
    "substance_workflow": ("extapps.substance_scripts", "0.9.0"),
}


# ``bootstrap_package`` derives ``__all__`` from the resolved surface
# (DEFAULT_INCLUDE) and unions in anything declared here first — so only the
# non-derivable ``__version__`` needs listing by hand.
__all__ = ["__version__", "DOCS_BASE_URL"]

bootstrap_package(globals(), include=DEFAULT_INCLUDE, moved=MOVED_NAMES)
