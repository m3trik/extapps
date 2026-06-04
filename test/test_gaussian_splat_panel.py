#!/usr/bin/env python
# coding=utf-8
"""Tests for the Brush (gaussian-splat) Workflow panel.

Build-time wiring (no Brush needed), per-mode param relevance (Train only hides
the Publish section), semantic-preset round-trip against the engine-scoped
``gaussian_splat`` store, and b000 argv assembly (--colmap-dir + --publish in
Train + Publish) without launching a real process.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

from qtpy.QtWidgets import QApplication


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestParametersReferencedKeys(unittest.TestCase):
    def _P(self):
        from extapps.photogrammetry.gaussian_splat_workflow import parameters as P
        return P

    def test_train_only_hides_publish_keys(self) -> None:
        P = self._P()
        keys = P.referenced_keys("")
        for train in ("total_steps", "max_resolution", "max_splats", "sh_degree"):
            self.assertIn(train, keys)
        for pub in ("publish_targets", "web_format", "spz_version"):
            self.assertNotIn(pub, keys, f"{pub} should be hidden in Train only")

    def test_publish_mode_shows_publish_keys(self) -> None:
        P = self._P()
        keys = P.referenced_keys("publish")
        self.assertEqual(keys, set(P.PARAMS))

    def test_training_values_render_to_cli_flags(self) -> None:
        P = self._P()
        argv = P.to_argv({"total_steps": 50000, "sh_degree": 2, "web_format": "sog"})
        self.assertEqual(argv[argv.index("--total-steps") + 1], "50000")
        self.assertEqual(argv[argv.index("--sh-degree") + 1], "2")
        self.assertEqual(argv[argv.index("--web-format") + 1], "sog")


class TestBrushPanelLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import gaussian_splat_workflow as g
        self.ui = g.GaussianSplatWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_param_widgets_built_for_every_spec(self) -> None:
        from extapps.photogrammetry.gaussian_splat_workflow import parameters as P
        for key in P.PARAMS:
            self.assertIn(key, self.slots._param_widgets, f"no widget for {key}")

    def test_run_mode_combo_has_both_modes(self) -> None:
        cmb = self.ui.cmb000
        self.assertGreaterEqual(cmb.findText("Train only"), 0)
        self.assertGreaterEqual(cmb.findText("Train + Publish"), 0)

    def test_semantic_preset_mode_uses_gsplat_store(self) -> None:
        listed = set(self.slots._preset_mgr.list())
        self.assertTrue(
            {"preview", "high"} <= listed,
            f"gsplat presets missing; got {sorted(listed)}",
        )
        # No shipped 'default' preset — the Reset to Defaults button covers it.
        self.assertNotIn("default", listed)

    def test_high_preset_loads_into_param_widgets(self) -> None:
        from uitk.bridge.spec import read_value
        self.slots._preset_mgr.load("high")
        self.assertEqual(read_value(self.slots._param_widgets["total_steps"]), 50000)


class TestBrushPanelDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import gaussian_splat_workflow as g
        self.tmp = tempfile.mkdtemp(prefix="brush_dispatch_")
        self.colmap = os.path.join(self.tmp, "ds")
        os.makedirs(self.colmap)
        self.ui = g.GaussianSplatWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.captured: dict = {}
        self.slots.bridge.is_available = lambda: True
        self.slots.bridge.is_running = lambda: False

        def fake_start(argv, on_line=None, on_done=None, cwd=None):
            self.captured["argv"] = list(argv)

        self.slots.bridge.start = fake_start

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _set_inputs(self) -> None:
        self.slots._name_edit.setText("splat")
        self.slots._colmap_edit.setText(self.colmap)
        self.slots._output_dir_edit.setText(self.tmp)

    def test_train_only_argv_has_colmap_no_publish(self) -> None:
        self._set_inputs()
        self.ui.cmb000.setCurrentIndex(self.ui.cmb000.findText("Train only"))
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch")
        self.assertEqual(argv[argv.index("--colmap-dir") + 1], self.colmap)
        self.assertEqual(argv[argv.index("--name") + 1], "splat")
        self.assertNotIn("--publish", argv)

    def test_train_plus_publish_adds_publish_flag(self) -> None:
        self._set_inputs()
        self.ui.cmb000.setCurrentIndex(self.ui.cmb000.findText("Train + Publish"))
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch")
        self.assertIn("--publish", argv)

    def test_missing_colmap_dir_does_not_dispatch(self) -> None:
        self.slots._name_edit.setText("splat")
        self.slots._colmap_edit.setText(os.path.join(self.tmp, "nope"))
        self.slots._output_dir_edit.setText(self.tmp)
        self.ui.b000.click()
        self.assertNotIn("argv", self.captured, "must not dispatch with a bad dir")


if __name__ == "__main__":
    unittest.main()
