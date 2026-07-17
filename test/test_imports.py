# !/usr/bin/python
# coding=utf-8
"""Smoke test — every tool subpackage importable, entry-points resolvable.

Most engine logic lives in pythontk and is imported indirectly via the slot
classes; the SDK-specific engines (substance Painter, Marmoset Toolbag) are
bundled with their panels. This test only guards the extapps surface.
"""
import importlib

import pytest


TOOLS = [
    "extapps.texture_maps.compositor",
    "extapps.photogrammetry.metashape_workflow",
    "extapps.photogrammetry.realityscan_workflow",
    "extapps.photogrammetry.gaussian_splat_workflow",
    "extapps.photogrammetry.sugar_mesh_workflow",
    "extapps.substance_workflow",
    "extapps.marmoset_workflow",
    "extapps.texture_maps.converter",
    "extapps.texture_maps.packer",
    "extapps.mesh_convert",
    "extapps.unity_workflow",
]

# Every Switchboard panel's (UI, Slots) pair — the root package re-exports
# the full panel surface, mirroring each app's entry point.
PANEL_CLASSES = [
    ("CompositorUI", "CompositorSlots"),
    ("MetashapeWorkflowUI", "MetashapeWorkflowSlots"),
    ("RealityScanWorkflowUI", "RealityscanWorkflowSlots"),
    ("GaussianSplatWorkflowUI", "GaussianSplatWorkflowSlots"),
    ("SubstanceWorkflowUI", "SubstanceWorkflowSlots"),
    ("ConverterUI", "ConverterSlots"),
    ("PackerUI", "PackerSlots"),
    ("MeshConvertUI", "MeshConvertSlots"),
    ("MarmosetWorkflowUI", "MarmosetWorkflowSlots"),
    ("UnityWorkflowUI", "UnityWorkflowSlots"),
]


@pytest.mark.parametrize("modname", TOOLS)
def test_tool_imports(modname):
    importlib.import_module(modname)


@pytest.mark.parametrize("ui_name,slots_name", PANEL_CLASSES)
def test_root_exposes_panel_surface(ui_name, slots_name):
    """Guard against root DEFAULT_INCLUDE drifting from the app set."""
    import extapps

    assert ui_name in extapps.__all__
    assert slots_name in extapps.__all__
    # getattr resolves through the lazy bootstrap — catches a DEFAULT_INCLUDE
    # entry pointing at a wrong module, not just a missing __all__ name.
    assert getattr(extapps, ui_name) is not None
    assert getattr(extapps, slots_name) is not None


def test_top_level_version():
    import extapps

    assert hasattr(extapps, "__version__")
