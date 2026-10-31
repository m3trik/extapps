# !/usr/bin/python
# coding=utf-8
"""Smoke test — every app subpackage importable, the root surface resolvable,
and nothing above extapps' two dependencies imported.

extapps is a product: each host-free app keeps its engine, panel and Slots class
here, on pythontk and uitk alone. Nothing imports extapps (``check_layers.py``:
the product role), and extapps imports no host -- no Maya, no Blender -- and no
tentacle, whose DCC menus open the apps by name through uitk's external-app
handler instead.
"""

import ast
import importlib
from pathlib import Path

import pytest

from test_panel_launcher import entry_points

TOOLS = [
    "extapps.texture_maps.compositor",
    "extapps.texture_maps.converter",
    "extapps.texture_maps.packer",
    "extapps.mesh_convert",
    "extapps.photogrammetry.metashape_workflow",
    "extapps.photogrammetry.realityscan_workflow",
    "extapps.photogrammetry.gaussian_splat_workflow",
    "extapps.photogrammetry.sugar_mesh_workflow",
    "extapps.substance_workflow",
    "extapps.marmoset_workflow",
    "extapps.unity_workflow",
    "extapps.webxr_preview",
    "extapps.look_match",
]

#: Dotted roots no extapps module may import: the hosts (and their libraries) and
#: the product above them.
FORBIDDEN = (
    "tentacle",
    "mayatk",
    "blendertk",
    "maya",
    "bpy",
    "bmesh",
    "mathutils",
    "pymel",
)

PACKAGE = Path(__file__).resolve().parents[1] / "extapps"


@pytest.mark.parametrize("modname", TOOLS)
def test_tool_imports(modname):
    importlib.import_module(modname)


def test_root_resolves_its_whole_surface():
    """Guard against a DEFAULT_INCLUDE entry pointing at a wrong module: getattr
    resolves through the lazy bootstrap, not just ``__all__``."""
    import extapps

    for name in extapps.__all__:
        assert getattr(extapps, name) is not None, name


@pytest.mark.parametrize("app", sorted(entry_points()))
def test_root_exposes_each_apps_ui_and_slots(app):
    """Each entry point's ``<Tool>UI`` and the Slots class it builds are root
    names, read from the roster (pyproject's entry points), never a hand list."""
    import extapps

    _module, ui_name, _extras = entry_points()[app]
    ui = getattr(extapps, ui_name)
    package, _name, _folder = ui._tool()
    slots = ui._slots_class(package)
    assert ui_name in extapps.__all__
    assert getattr(extapps, slots.__name__) is slots


def _imports(path: Path):
    """``(line, dotted target)`` of every import in *path*, deferred ones too."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            yield node.lineno, node.module


def test_no_module_imports_a_host_or_tentacle():
    """Every module, exec-templates and the in-Painter plugin included: a host
    import here would make a host-free app need the host, and a tentacle import
    would put the product above its only consumer."""
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for line, target in _imports(path):
            if target.split(".")[0] in FORBIDDEN:
                found.append(f"{path.relative_to(PACKAGE)}:{line} imports {target}")
    assert found == []


def test_the_dependencies_name_no_host_and_no_tentacle():
    """pyproject declares pythontk, uitk and qtpy: no host library, no tentacle."""
    import re

    text = (PACKAGE.parent / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^dependencies = \[(.*?)\]", text, re.M | re.S).group(1)
    names = {re.match(r"[\w-]+", d).group(0) for d in re.findall(r'"([^"]+)"', block)}
    assert names == {"pythontk", "uitk", "qtpy"}


def test_top_level_version():
    import extapps

    assert hasattr(extapps, "__version__")
