# !/usr/bin/python
# coding=utf-8
"""Smoke test — every tool subpackage importable, entry-points resolvable.

Most engine logic lives in pythontk and is imported indirectly via the slot
classes; the SDK-specific engines (substance Painter, Marmoset Toolbag) are
bundled with their panels. This test only guards the extapps surface.
"""
import importlib
from pathlib import Path

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

# Panels that log a docs link at open (a clickable anchor in the log pane —
# the compositor's "detailed docs" line, generalised as
# ``BridgeSlotsBase.DOCS_URL`` / ``SubstanceWorkflowSlots.DOCS_URL``). Each is
# a GitHub blob URL into THIS repo, so a doc rename fails here rather than
# 404-ing for users. RealityScan / Gaussian Splat inherit the photogrammetry
# base's TUNING.md link; Metashape and Substance point at their own pages.
DOCS_LINKED_SLOTS = [
    "MetashapeWorkflowSlots",
    "RealityscanWorkflowSlots",
    "GaussianSplatWorkflowSlots",
    "SubstanceWorkflowSlots",
]
_DOCS_URL_PREFIX = "https://github.com/m3trik/extapps/blob/main/"


@pytest.mark.parametrize("modname", TOOLS)
def test_tool_imports(modname):
    importlib.import_module(modname)


@pytest.mark.parametrize("slots_name", DOCS_LINKED_SLOTS)
def test_docs_url_points_at_a_file_in_this_repo(slots_name):
    import extapps

    cls = getattr(extapps, slots_name)
    url = cls.DOCS_URL
    assert url.startswith(_DOCS_URL_PREFIX), url
    assert cls.DOCS_LABEL.strip(), f"{slots_name}.DOCS_LABEL is empty"
    repo_root = Path(extapps.__file__).resolve().parents[1]
    target = repo_root / url[len(_DOCS_URL_PREFIX):]
    assert target.is_file(), f"{slots_name}.DOCS_URL -> missing {target}"


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
