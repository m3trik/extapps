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
    "extapps.substance_workflow",
    "extapps.marmoset_workflow",
    "extapps.texture_maps.converter",
    "extapps.texture_maps.packer",
    "extapps.mesh_convert",
]


@pytest.mark.parametrize("modname", TOOLS)
def test_tool_imports(modname):
    importlib.import_module(modname)


def test_top_level_version():
    import extapps

    assert hasattr(extapps, "__version__")
