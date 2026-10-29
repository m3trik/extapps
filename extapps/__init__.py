# !/usr/bin/python
# coding=utf-8
"""extapps — the engines of the standalone content-pipeline tools.

The logic tentacle's standalone panels drive (``tentacle/tcl_standalone.py``):
the photogrammetry workflows (Metashape, RealityCapture, Brush splats), the
Substance Painter and Marmoset Toolbag engines, and the Map Converter's batch
rules. The panels themselves -- their ``.ui`` files, Slots classes, parameter
registries and launchers -- are tentacle's (``MOVED_NAMES``). ``python -m
extapps [panel]`` still opens them (``__main__.py``: tentacle named as their
provider, as data), from an installed tentacle or a source checkout, installing
tentacletk where it is missing -- so launchers written before they moved keep
working.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps"
__version__ = "0.7.0"

# Base of the "detailed docs" link a panel shows for an engine documented here
# (the photogrammetry ``TUNING.md``, ``docs/*.md``, the README): the public repo
# at ``main``, so each panel appends only its repo-relative doc path -- one place
# to repoint at a fork, a docs site, or a release tag.
DOCS_BASE_URL = "https://github.com/m3trik/extapps/blob/main/"


DEFAULT_INCLUDE = {
    "photogrammetry.profile": ["Profile", "IMAGE_EXTS", "QUALITY_TIERS"],
    "photogrammetry.prep_stages": ["PrepStagesMixin"],
    "photogrammetry.metashape_workflow._metashape_workflow": ["MetashapeWorkflow"],
    "photogrammetry.metashape_workflow._metashape_runner": ["MetashapeRunner"],
    "photogrammetry.realityscan_workflow._realityscan_runner": ["RealityScanRunner"],
    "photogrammetry.gaussian_splat_workflow._gaussian_splat_runner": [
        "GaussianSplatRunner",
        "BrushInstallRunner",
    ],
    "substance_workflow.env_utils.painter_connection": ["PainterConnection"],
    "substance_workflow.env_utils.painter_finder": ["PainterFinder"],
    "substance_workflow.job": ["Job"],
    "texture_maps.converter._converter": ["MapConverter"],
    "marmoset_workflow._marmoset_workflow": ["MarmosetWorkflow"],
}


#: Public names that left this package (CODE_STANDARD section 5): no alias, so a
#: read raises MovedNameError naming the new home. ``{name: (new home, version)}``;
#: a move adds its names here in the same change set. The panels are tentacle's:
#: each ``<Tool>UI`` is ``tentacle.tcl_standalone``'s and each Slots class its
#: ``slots/tools/<tool>.py``'s.
MOVED_NAMES = {
    "CompositorUI": ("tentacle.tcl_standalone.CompositorUI", "0.7.0"),
    "CompositorSlots": (
        "tentacle.slots.tools.compositor.CompositorSlots",
        "0.7.0",
    ),
    "ConverterUI": ("tentacle.tcl_standalone.ConverterUI", "0.7.0"),
    "ConverterSlots": (
        "tentacle.slots.tools.converter.ConverterSlots",
        "0.7.0",
    ),
    "PackerUI": ("tentacle.tcl_standalone.PackerUI", "0.7.0"),
    "PackerSlots": (
        "tentacle.slots.tools.packer.PackerSlots",
        "0.7.0",
    ),
    "MeshConvertUI": ("tentacle.tcl_standalone.MeshConvertUI", "0.7.0"),
    "MeshConvertSlots": (
        "tentacle.slots.tools.mesh_convert.MeshConvertSlots",
        "0.7.0",
    ),
    "MetashapeWorkflowUI": ("tentacle.tcl_standalone.MetashapeWorkflowUI", "0.7.0"),
    "MetashapeWorkflowSlots": (
        "tentacle.slots.tools.metashape_workflow.MetashapeWorkflowSlots",
        "0.7.0",
    ),
    "RealityScanWorkflowUI": ("tentacle.tcl_standalone.RealityScanWorkflowUI", "0.7.0"),
    "RealityscanWorkflowSlots": (
        "tentacle.slots.tools.realityscan_workflow.RealityscanWorkflowSlots",
        "0.7.0",
    ),
    "GaussianSplatWorkflowUI": ("tentacle.tcl_standalone.GaussianSplatWorkflowUI", "0.7.0"),
    "GaussianSplatWorkflowSlots": (
        "tentacle.slots.tools.gaussian_splat_workflow.GaussianSplatWorkflowSlots",
        "0.7.0",
    ),
    "SubstanceWorkflowUI": ("tentacle.tcl_standalone.SubstanceWorkflowUI", "0.7.0"),
    "SubstanceWorkflowSlots": (
        "tentacle.slots.tools.substance_workflow.SubstanceWorkflowSlots",
        "0.7.0",
    ),
    "MarmosetWorkflowUI": ("tentacle.tcl_standalone.MarmosetWorkflowUI", "0.7.0"),
    "MarmosetWorkflowSlots": (
        "tentacle.slots.tools.marmoset_workflow.MarmosetWorkflowSlots",
        "0.7.0",
    ),
    "UnityWorkflowUI": ("tentacle.tcl_standalone.UnityWorkflowUI", "0.7.0"),
    "UnityWorkflowSlots": (
        "tentacle.slots.tools.unity_workflow.UnityWorkflowSlots",
        "0.7.0",
    ),
    "WebXrPreviewUI": ("tentacle.tcl_standalone.WebXrPreviewUI", "0.7.0"),
    "WebXrPreviewSlots": (
        "tentacle.slots.tools.webxr_preview.WebXrPreviewSlots",
        "0.7.0",
    ),
    "LookMatchUI": ("tentacle.tcl_standalone.LookMatchUI", "0.7.0"),
    "LookMatchSlots": (
        "tentacle.slots.tools.look_match.LookMatchSlots",
        "0.7.0",
    ),
    # The one launcher every panel is built by, and the panels' module-level data.
    "PanelLauncher": (
        "tentacle.tcl_standalone.PanelLauncher",
        "0.7.0",
    ),
    "DEFAULT_INCLUDE": (
        "tentacle.tcl_standalone (a removed panel subpackage's own table; the panels are tentacle's entry points)",
        "0.7.0",
    ),
    "DOCS_URL": (
        "tentacle.slots.tools.look_match.DOCS_URL",
        "0.7.0",
    ),
    "FILE_SOURCE": (
        "tentacle.slots.tools.webxr_preview.FILE_SOURCE",
        "0.7.0",
    ),
    "ADVANCED_PARAMS": (
        "tentacle.slots.tools.substance_workflow.ADVANCED_PARAMS",
        "0.7.0",
    ),
    "BAKE_RESOLUTIONS": (
        "tentacle.slots.tools.substance_workflow.BAKE_RESOLUTIONS",
        "0.7.0",
    ),
    "BLEND_MODES": (
        "tentacle.slots.tools.substance_workflow.BLEND_MODES",
        "0.7.0",
    ),
    "MESH_EXTS": (
        "tentacle.slots.tools.substance_workflow.MESH_EXTS",
        "0.7.0",
    ),
    "PIPELINE_STAGES": (
        "tentacle.slots.tools.substance_workflow.PIPELINE_STAGES",
        "0.7.0",
    ),
    # Each panel's parameter registry (one name per panel: ``_<tool>/parameters.py``,
    # the photogrammetry three ``_photogrammetry/<engine>_parameters.py``).
    "Parameters": (
        "tentacle.slots.tools._<tool>.parameters.Parameters (photogrammetry: tentacle.slots.tools._photogrammetry.<engine>_parameters.Parameters)",
        "0.7.0",
    ),
    "PARAMS": (
        "tentacle.slots.tools._<tool>.parameters.PARAMS (photogrammetry: tentacle.slots.tools._photogrammetry.<engine>_parameters.PARAMS)",
        "0.7.0",
    ),
    "AUTHORED_EXTENSION": (
        "tentacle.slots.tools._webxr_preview.parameters.AUTHORED_EXTENSION",
        "0.7.0",
    ),
    "EXPORT_KEYS": (
        "tentacle.slots.tools._webxr_preview.parameters.EXPORT_KEYS",
        "0.7.0",
    ),
    "FILE_KEYS": (
        "tentacle.slots.tools._webxr_preview.parameters.FILE_KEYS",
        "0.7.0",
    ),
    "GLB_KEYS": (
        "tentacle.slots.tools._webxr_preview.parameters.GLB_KEYS",
        "0.7.0",
    ),
    "KTX2_KEYS": (
        "tentacle.slots.tools._webxr_preview.parameters.KTX2_KEYS",
        "0.7.0",
    ),
    "SOURCE_FILE_TYPES": (
        "tentacle.slots.tools._webxr_preview.parameters.SOURCE_FILE_TYPES",
        "0.7.0",
    ),
    "TEXTURE_KEYS": (
        "tentacle.slots.tools._webxr_preview.parameters.TEXTURE_KEYS",
        "0.7.0",
    ),
    # The panels' shared bases and mixins.
    "UnityPanelMixin": (
        "tentacle.slots.tools._unity_bridge._unity_panel.UnityPanelMixin",
        "0.7.0",
    ),
    "PhotogrammetryPanelSlots": (
        "tentacle.slots.tools._photogrammetry.panel_slots.PhotogrammetryPanelSlots",
        "0.7.0",
    ),
    "FramesSourceMixin": (
        "tentacle.slots.tools._photogrammetry.panel_slots.FramesSourceMixin",
        "0.7.0",
    ),
    "SharedParams": (
        "tentacle.slots.tools._photogrammetry.shared_parameters.SharedParams",
        "0.7.0",
    ),
    "PREPROCESS_MASTER_KEY": (
        "tentacle.slots.tools._photogrammetry.shared_parameters.PREPROCESS_MASTER_KEY",
        "0.7.0",
    ),
    "PREPROCESSING_KEYS": (
        "tentacle.slots.tools._photogrammetry.shared_parameters.PREPROCESSING_KEYS",
        "0.7.0",
    ),
    "PREPROCESSING_KNOB_KEYS": (
        "tentacle.slots.tools._photogrammetry.shared_parameters.PREPROCESSING_KNOB_KEYS",
        "0.7.0",
    ),
    "PREPROCESSING_PARAMS": (
        "tentacle.slots.tools._photogrammetry.shared_parameters.PREPROCESSING_PARAMS",
        "0.7.0",
    ),
    "PREPROCESSING_STORE_TRUE_FLAGS": (
        "tentacle.slots.tools._photogrammetry.shared_parameters.PREPROCESSING_STORE_TRUE_FLAGS",
        "0.7.0",
    ),
    "PREPROCESSING_VALUE_FLAGS": (
        "tentacle.slots.tools._photogrammetry.shared_parameters.PREPROCESSING_VALUE_FLAGS",
        "0.7.0",
    ),
}


# ``bootstrap_package`` derives ``__all__`` from the resolved surface
# (DEFAULT_INCLUDE) and unions in anything declared here first — so only the
# non-derivable ``__version__`` needs listing by hand.
__all__ = ["__version__", "DOCS_BASE_URL"]

bootstrap_package(globals(), include=DEFAULT_INCLUDE, moved=MOVED_NAMES)
