#!/usr/bin/python
# coding=utf-8
"""Regression tests for extapps Switchboard slot `_validate` guards.

These call the plain `_validate` method against a minimal stand-in `self`
so no live Painter / full Qt UI construction is needed.
"""
import types

from extapps.substance_workflow.slots import SubstanceWorkflowSlots


# Default panel config: open + bake + save on, export off.
_DEFAULT_STAGES = {
    "stage_open": True,
    "stage_bake": True,
    "stage_save": True,
    "stage_export": False,
}


def _make_substance_slots_stub(mesh: str, save_path: str):
    """Minimal stand-in exposing only what `_validate` reads."""
    errors = []
    ui = types.SimpleNamespace(
        txt000=types.SimpleNamespace(text=lambda: mesh),
        txt002=types.SimpleNamespace(text=lambda: save_path),
    )
    logger = types.SimpleNamespace(error=lambda msg: errors.append(msg))
    return types.SimpleNamespace(ui=ui, logger=logger), errors


def test_substance_validate_rejects_save_of_new_project_without_save_path():
    """Create-from-mesh + Save with an empty Save Path must be rejected
    up front (before the expensive bake runs), not fail at save time."""
    stub, errors = _make_substance_slots_stub(mesh="C:/meshes/hero.fbx", save_path="")
    ok = SubstanceWorkflowSlots._validate(stub, dict(_DEFAULT_STAGES))
    assert ok is False
    assert errors, "an explanatory error should have been logged"
    assert "Save Path" in errors[-1]


def test_substance_validate_allows_new_project_with_save_target(tmp_path):
    """A not-yet-on-disk .spp save target is a valid save destination."""
    save_path = str(tmp_path / "hero.spp")  # does not exist yet
    stub, errors = _make_substance_slots_stub(
        mesh="C:/meshes/hero.fbx", save_path=save_path
    )
    ok = SubstanceWorkflowSlots._validate(stub, dict(_DEFAULT_STAGES))
    assert ok is True
    assert not errors


def test_substance_validate_allows_resave_of_existing_project(tmp_path):
    """Re-saving a project already on disk stays allowed even with no
    save-as target typed (project.save() has a path)."""
    spp = tmp_path / "existing.spp"
    spp.write_text("stub")
    stub, errors = _make_substance_slots_stub(mesh="", save_path=str(spp))
    ok = SubstanceWorkflowSlots._validate(stub, dict(_DEFAULT_STAGES))
    assert ok is True
    assert not errors


def test_substance_validate_ignores_save_gap_when_save_stage_off(tmp_path):
    """When Save is unchecked, an empty Save Path is fine even for a new
    project (nothing tries to save)."""
    stages = dict(_DEFAULT_STAGES, stage_save=False)
    stub, errors = _make_substance_slots_stub(
        mesh="C:/meshes/hero.fbx", save_path=""
    )
    ok = SubstanceWorkflowSlots._validate(stub, stages)
    assert ok is True
    assert not errors


# --------------------------------------------------------------------------
# Unity Workflow: version-combo ordering (unity_workflow/slots.py)
# --------------------------------------------------------------------------
def test_unity_version_combo_orders_same_major_numerically(monkeypatch):
    """`_populate_unity_versions` must list editors newest-first *numerically*.

    A lexicographic sort ranks 2020.3.9f1 above 2020.3.10f1 (because '9' > '1'
    at the differing char), inverting the documented 'newest first' order for
    same-major versions. The fix routes ordering through
    UnityFinder.version_sort_key. Exercised against a stub `self` so no live
    Unity / full Qt UI construction is needed.
    """
    from extapps.unity_workflow.slots import UnityWorkflowSlots

    class _FakeCombo:
        def __init__(self):
            self.items = []

        def addItem(self, text, data):
            self.items.append(text)

    combo = _FakeCombo()
    # Older patch (2020.3.9f1) must end up BELOW the newer 2020.3.10f1 despite
    # sorting higher lexicographically.
    editors = {
        "2020.3.9f1": "C:/U/2020.3.9f1/Unity.exe",
        "2020.3.10f1": "C:/U/2020.3.10f1/Unity.exe",
    }
    monkeypatch.setattr("unitytk.UnityFinder.find_editors", lambda: editors)

    stub = types.SimpleNamespace(_param_widgets={"UNITY_VERSION": combo})
    UnityWorkflowSlots._populate_unity_versions(stub)

    assert combo.items == ["2020.3.10f1", "2020.3.9f1"]


# --------------------------------------------------------------------------
# Texture Maps / Compositor: cross-platform folder reveal
# (texture_maps/compositor/slots.py)
# --------------------------------------------------------------------------
def test_compositor_open_dir_reveals_folder_off_windows(tmp_path, monkeypatch):
    """`_open_dir` must reveal a folder off-Windows, not crash.

    The old body called ``os.startfile`` unconditionally; that name only
    exists on Windows, so under Maya/Blender on Linux/macOS clicking a path
    field's 'Open this location' raised an uncaught AttributeError. The fix
    delegates to the platform-aware, non-shell ``FileUtils.open_explorer``
    (xdg-open on Linux). Simulate a non-Windows host and assert the reveal is
    dispatched without ever touching os.startfile.
    """
    import os
    import sys
    import subprocess

    from extapps.texture_maps.compositor.slots import CompositorSlots

    calls = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "Popen", lambda argv, *a, **k: calls.append(argv))
    # A regression to os.startfile would now blow up loudly instead of passing.
    monkeypatch.delattr(os, "startfile", raising=False)

    CompositorSlots._open_dir(str(tmp_path))  # must NOT raise

    assert calls == [["xdg-open", str(tmp_path)]]


def test_compositor_open_dir_noops_on_empty_path(monkeypatch):
    """An empty/None field resolves to '' via `_field_dir`; `_open_dir` must
    swallow it (no launcher call, no crash) rather than raising."""
    import subprocess

    from extapps.texture_maps.compositor.slots import CompositorSlots

    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda argv, *a, **k: calls.append(argv))

    CompositorSlots._open_dir("")  # must NOT raise
    CompositorSlots._open_dir(None)  # must NOT raise

    assert calls == []
