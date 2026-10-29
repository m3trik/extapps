# !/usr/bin/python
# coding=utf-8
"""Smoke test — every engine subpackage importable, the root surface resolvable.

The panels are tentacle's since 0.7.0: their names are in ``MOVED_NAMES``, and a
read of one raises ``MovedNameError`` naming its new home.
"""

import importlib
import re

import pytest

from pythontk.core_utils.module_resolver import MovedNameError

TOOLS = [
    "extapps.photogrammetry.metashape_workflow",
    "extapps.photogrammetry.realityscan_workflow",
    "extapps.photogrammetry.gaussian_splat_workflow",
    "extapps.photogrammetry.sugar_mesh_workflow",
    "extapps.substance_workflow",
    "extapps.marmoset_workflow",
    "extapps.texture_maps.converter",
]


@pytest.mark.parametrize("modname", TOOLS)
def test_tool_imports(modname):
    importlib.import_module(modname)


def test_root_resolves_its_whole_surface():
    """Guard against a DEFAULT_INCLUDE entry pointing at a wrong module: getattr
    resolves through the lazy bootstrap, not just ``__all__``."""
    import extapps

    for name in extapps.__all__:
        assert getattr(extapps, name) is not None, name


@pytest.mark.parametrize("name", sorted(__import__("extapps").MOVED_NAMES))
def test_a_moved_name_says_where_it_went(name):
    import extapps

    home, version = extapps.MOVED_NAMES[name]
    assert home.startswith("tentacle."), home
    assert version == "0.7.0"
    assert name not in extapps.__all__
    if name in vars(extapps):
        # The root's own bootstrap table: a removed subpackage's table of the
        # same name is what the row accounts for, never resolved through it.
        assert name == "DEFAULT_INCLUDE"
        return
    with pytest.raises(MovedNameError, match=re.escape(home)):
        getattr(extapps, name)


def test_the_moved_panels_all_left():
    """No panel is left behind: extapps keeps no ``.ui`` file."""
    from pathlib import Path

    import extapps

    root = Path(extapps.__file__).resolve().parent
    assert sorted(p.name for p in root.rglob("*.ui")) == []


def test_top_level_version():
    import extapps

    assert hasattr(extapps, "__version__")
