# !/usr/bin/python
# coding=utf-8
"""Tests for the Unity Workflow panel (extapps.unity_workflow).

The panel is a file-driven :class:`uitk.bridge.BridgeSlotsBase` (the DCC-agnostic
sibling of mayatk/blendertk's ``unity_bridge``): pick a model file -> copy it into a
Unity project's ``Assets/`` via :class:`unitytk.FileToUnityBridge`. Build-time wiring
(param widgets, Model File + Unity Project rows, the single delivery mode), the
``set_model_path`` host hand-off, and b000 dispatch are exercised against the real
panel under the offscreen QPA without launching Unity.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from qtpy.QtWidgets import QApplication


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestUnityWorkflowParameters(unittest.TestCase):
    def _P(self):
        from extapps.unity_workflow import parameters as P
        return P

    def test_defaults_are_unity_side_only(self) -> None:
        P = self._P()
        self.assertEqual(
            set(P.defaults()),
            {
                "ASSETS_SUBDIR",
                "ASSET_NAME",
                "LAUNCH_MODE",
                "UNITY_VERSION",
                # Manage Unity Scripts mode's action combo — Unity-side too
                # (it manages the embedded unitytk package in the project).
                "SCRIPTS_ACTION",
            },
        )
        # No DCC export knobs (this panel takes an already-exported file).
        for export_key in ("SCOPE", "TRIANGULATE", "EMBED_TEXTURES", "INCLUDE_MATERIALS"):
            self.assertNotIn(export_key, P.PARAMS)

    def test_referenced_keys_is_token_based(self) -> None:
        # referenced_keys is the generic __KEY__ token scan; with no tokens in
        # the text it finds nothing (the panel drives visibility explicitly
        # from _relevant_param_keys() instead — see the panel-load test).
        P = self._P()
        self.assertEqual(P.referenced_keys("plain text"), set())
        self.assertEqual(P.referenced_keys("uses __ASSET_NAME__"), {"ASSET_NAME"})


class TestUnityWorkflowPanelLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.unity_workflow import UnityWorkflowUI
        self.ui = UnityWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_param_widgets_built_for_every_spec(self) -> None:
        from extapps.unity_workflow import parameters as P
        for key in P.PARAMS:
            self.assertIn(key, self.slots._param_widgets, f"no widget for {key}")

    def test_model_and_project_rows_exist(self) -> None:
        self.assertIsNotNone(self.slots._model_edit, "Model File row not built")
        self.assertIsNotNone(self.slots._output_dir_edit, "Unity Project row not built")

    def test_delivery_combo_shows_friendly_label(self) -> None:
        self.assertGreaterEqual(self.ui.cmb000.findText("Copy to Project"), 0)

    def test_copy_mode_shows_every_delivery_param(self) -> None:
        # Copy-to-assets shows every delivery param and hides the action combo
        # that only Manage Unity Scripts uses.
        from extapps.unity_workflow import parameters as P

        self.assertEqual(
            self.slots._relevant_param_keys(),
            set(P.PARAMS) - {"SCRIPTS_ACTION"},
        )

    def test_manage_mode_shows_only_the_action_combo(self) -> None:
        # The other half of the same gate: delivery params hide in manage mode.
        with mock.patch.object(
            self.slots,
            "_selected_template_mode",
            return_value=(self.slots.MODE_MANAGE, None),
        ):
            self.assertEqual(self.slots._relevant_param_keys(), {"SCRIPTS_ACTION"})

    def test_set_model_path_prefills_field(self) -> None:
        self.slots.set_model_path("C:/scan/robot.fbx")
        self.assertEqual(self.slots.resolved_model_path(), "C:/scan/robot.fbx")


class TestUnityWorkflowVersionPopulate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def test_unity_version_combo_appends_installed_newest_first(self) -> None:
        from extapps.unity_workflow import UnityWorkflowUI
        editors = {"2021.3.1f1": "C:/U/2021/Unity.exe", "6000.0.5f1": "C:/U/6000/Unity.exe"}
        with mock.patch("unitytk.UnityFinder.find_editors", return_value=editors):
            ui = UnityWorkflowUI()
        try:
            slots = ui.sb.get_slots_instance(ui)
            cmb = slots._param_widgets["UNITY_VERSION"]
            texts = [cmb.itemText(i) for i in range(cmb.count())]
            self.assertEqual(texts[0], "Auto (newest)")
            # Discovered versions appended newest-first after the auto default.
            self.assertEqual(texts[1:], ["6000.0.5f1", "2021.3.1f1"])
        finally:
            ui.deleteLater()
            self.app.processEvents()


class TestUnityWorkflowDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.unity_workflow import UnityWorkflowUI
        self.tmp = tempfile.mkdtemp(prefix="unity_workflow_")
        self.project = os.path.join(self.tmp, "Proj")
        os.makedirs(os.path.join(self.project, "Assets"))
        self.model = os.path.join(self.tmp, "robot.fbx")
        with open(self.model, "wb") as fh:
            fh.write(b"FBX")
        self.ui = UnityWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        # Stub the engine's send so nothing is copied/launched; capture the call.
        self.captured: dict = {}

        def fake_send(model_path=None, template=None, mode=None, params=None):
            self.captured["model_path"] = model_path
            self.captured["project"] = self.slots.bridge.project_path
            self.captured["params"] = params
            return {"asset": "ok"}

        self.slots.bridge.send = fake_send

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_b000_dispatches_with_model_and_project(self) -> None:
        self.slots.set_model_path(self.model)
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertEqual(self.captured.get("model_path"), self.model)
        self.assertEqual(self.captured.get("project"), self.project)
        self.assertIn("ASSETS_SUBDIR", self.captured.get("params", {}))

    def test_b000_aborts_without_model(self) -> None:
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)

    def test_b000_aborts_without_project(self) -> None:
        self.slots.set_model_path(self.model)
        self.slots._output_dir_edit.setText("")
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)

    def test_b000_aborts_on_missing_model_file(self) -> None:
        self.slots.set_model_path(os.path.join(self.tmp, "gone.fbx"))
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)


if __name__ == "__main__":
    unittest.main()
