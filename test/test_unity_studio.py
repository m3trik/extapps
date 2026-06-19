# !/usr/bin/python
# coding=utf-8
"""Tests for the Unity Studio launcher slots (extapps.unity_studio).

Driven through lightweight fake widgets so the slot logic is exercised without a Qt
panel load (deterministic, CI-safe): version population, launch wiring, project
validation, and recents persistence. The unitytk engine (UnityFinder / UnityLauncher)
is patched; persistence is redirected to a temp config root.
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock


class _Signal:
    def connect(self, *a, **k):
        pass


class _FakeCombo:
    def __init__(self):
        self._items = []  # (text, data)
        self._idx = 0
        self.currentIndexChanged = _Signal()

    def clear(self):
        self._items = []
        self._idx = 0

    def addItem(self, text, data=None):
        self._items.append((text, data))

    def itemText(self, i):
        return self._items[i][0]

    def itemData(self, i):
        return self._items[i][1]

    def count(self):
        return len(self._items)

    def currentData(self):
        return self._items[self._idx][1] if self._items else None

    def setCurrentIndex(self, i):
        self._idx = i

    def blockSignals(self, *_):
        pass


class _FakeLineEdit:
    def __init__(self, text=""):
        self._t = text

    def text(self):
        return self._t

    def setText(self, t):
        self._t = t

    def setFocus(self):
        pass


class _FakeLog:
    def __init__(self):
        self.lines = []
        self.anchorClicked = _Signal()

    def append(self, msg):
        self.lines.append(msg)


class _FakeUi:
    def __init__(self):
        self.cmb000 = _FakeCombo()
        self.cmb001 = _FakeCombo()
        self.project_field = _FakeLineEdit()
        self.txt000 = _FakeLog()


class _FakeLoadedUi:
    def __init__(self, ui):
        self.unity_studio = ui


class _FakeSb:
    def __init__(self, ui):
        self.loaded_ui = _FakeLoadedUi(ui)


def _make_slots():
    from extapps.unity_studio.slots import UnityStudioSlots

    ui = _FakeUi()
    return UnityStudioSlots(_FakeSb(ui)), ui


class UnityStudioSlotsTest(unittest.TestCase):
    def setUp(self):
        # Redirect recents persistence to a throwaway config root.
        from pythontk.core_utils.user_config import CONFIG_ROOT_ENV_VAR

        self._env_key = CONFIG_ROOT_ENV_VAR
        self._prev = os.environ.get(self._env_key)
        self.cfg = tempfile.mkdtemp(prefix="unity_studio_cfg_")
        os.environ[self._env_key] = self.cfg

    def tearDown(self):
        if self._prev is None:
            os.environ.pop(self._env_key, None)
        else:
            os.environ[self._env_key] = self._prev
        shutil.rmtree(self.cfg, ignore_errors=True)

    def test_cmb000_populates_versions_newest_first(self):
        slots, ui = _make_slots()
        editors = {"2021.3.1f1": "C:/U/2021/Unity.exe", "6000.0.5f1": "C:/U/6000/Unity.exe"}
        with mock.patch("unitytk.UnityFinder.find_editors", return_value=editors):
            slots.cmb000_init(ui.cmb000)
        self.assertEqual([ui.cmb000.itemText(i) for i in range(ui.cmb000.count())],
                         ["6000.0.5f1", "2021.3.1f1"])
        self.assertEqual(ui.cmb000.currentData(), "C:/U/6000/Unity.exe")

    def test_cmb000_handles_no_installs(self):
        slots, ui = _make_slots()
        with mock.patch("unitytk.UnityFinder.find_editors", return_value={}):
            slots.cmb000_init(ui.cmb000)
        self.assertEqual(ui.cmb000.count(), 1)
        self.assertIsNone(ui.cmb000.currentData())
        self.assertTrue(any("No Unity Editors" in m for m in ui.txt000.lines))

    def test_require_project_rejects_blank_and_non_project(self):
        slots, ui = _make_slots()
        self.assertFalse(slots._require_project(""))
        tmp = tempfile.mkdtemp()
        try:
            self.assertFalse(slots._require_project(tmp))  # no Assets/
            os.makedirs(os.path.join(tmp, "Assets"))
            self.assertTrue(slots._require_project(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_launch_editor_invokes_unitylauncher(self):
        slots, ui = _make_slots()
        project = tempfile.mkdtemp()
        os.makedirs(os.path.join(project, "Assets"))
        try:
            ui.project_field.setText(project)
            ui.cmb000.addItem("6000.0.5f1", "C:/U/6000/Unity.exe")
            fake_launcher = mock.Mock()
            fake_launcher.executable_path = "C:/U/6000/Unity.exe"
            fake_launcher.launch_editor.return_value = object()  # truthy proc
            with mock.patch("unitytk.UnityLauncher", return_value=fake_launcher) as ctor:
                slots.b000()
            ctor.assert_called_once_with(
                executable_path="C:/U/6000/Unity.exe", project_path=project
            )
            fake_launcher.launch_editor.assert_called_once()
            # Project is remembered after a successful launch.
            self.assertIn(os.path.normpath(project), slots._recents)
        finally:
            shutil.rmtree(project, ignore_errors=True)

    def test_launch_aborts_on_invalid_project(self):
        slots, ui = _make_slots()
        ui.project_field.setText("")  # blank
        with mock.patch("unitytk.UnityLauncher") as ctor:
            slots.b000()
        ctor.assert_not_called()

    def test_recents_persist_across_instances(self):
        slots, ui = _make_slots()
        project = os.path.normpath(tempfile.mkdtemp())
        try:
            slots._remember(project)
            # A fresh slots instance reads the persisted recents back.
            slots2, ui2 = _make_slots()
            self.assertIn(project, slots2._recents)
            # And the most-recent restores into the project field.
            self.assertEqual(os.path.normpath(ui2.project_field.text()), project)
        finally:
            shutil.rmtree(project, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
