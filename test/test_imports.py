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
    "extapps.map_compositor",
    "extapps.photogrammetry.metashape_workflow",
    "extapps.substance_workflow",
    "extapps.marmoset_workflow",
    "extapps.map_converter",
    "extapps.map_packer",
    "extapps.mesh_convert",
]


@pytest.mark.parametrize("modname", TOOLS)
def test_tool_imports(modname):
    importlib.import_module(modname)


def test_top_level_version():
    import extapps

    assert hasattr(extapps, "__version__")
