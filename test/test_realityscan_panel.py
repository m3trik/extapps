#!/usr/bin/env python
# coding=utf-8
"""Tests for the RealityCapture Workflow panel + the runner's --frames-dir flag.

Mirrors the Metashape panel tests: build-time wiring (no RealityScan needed),
semantic-preset round-trip against the engine-scoped ``realityscan`` store, and
b000 argv assembly without launching a real process. Plus a mock-mode check that
``run_combined --frames-dir`` uses a single prepared capture directly.
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


class TestRealityScanPanelLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import realityscan_workflow as r

        self.ui = r.RealityScanWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_param_widgets_built_for_every_spec(self) -> None:
        from extapps.photogrammetry.realityscan_workflow import parameters as P

        for key in P.PARAMS:
            self.assertIn(key, self.slots._param_widgets, f"no widget for {key}")

    def test_run_mode_combo_has_full_pipeline(self) -> None:
        cmb = self.ui.cmb000
        self.assertGreaterEqual(cmb.count(), 1)
        self.assertGreaterEqual(
            cmb.findText("Full pipeline"), 0, "Full pipeline mode missing"
        )

    def test_prep_preview_mode_maps_to_curate_preview(self) -> None:
        """Parity with the Metashape panel: the shared Prep-preview run mode
        emits --curate-preview (RC's runner executes in the panel's Python, so
        the dry-run just works) and shows only the pre-processing knobs."""
        from extapps.photogrammetry.realityscan_workflow import parameters as P
        from extapps.photogrammetry._shared_params import PREPROCESSING_KEYS

        cmb = self.ui.cmb000
        idx = cmb.findText("Prep preview")
        self.assertGreaterEqual(idx, 0, "Prep preview mode missing")
        cmb.setCurrentIndex(idx)
        self.assertEqual(self.slots._mode_argv(), ["--curate-preview"])
        self.assertEqual(
            P.referenced_keys("prep_preview"), set(P.PARAMS) & PREPROCESSING_KEYS
        )

    def test_semantic_preset_mode_uses_realityscan_store(self) -> None:
        listed = set(self.slots._preset_mgr.list())
        self.assertTrue(
            {"preview", "high", "specular_metal"} <= listed,
            f"RC presets missing; got {sorted(listed)}",
        )

    def test_builtin_preset_loads_into_param_widgets(self) -> None:
        from uitk.bridge.spec import KindFactory

        self.slots._preset_mgr.load("high")
        self.assertEqual(
            KindFactory.read_value(self.slots._param_widgets["quality"]), "max"
        )

    def test_missing_exe_reports_instead_of_dispatching(self) -> None:
        self.slots.bridge.is_available = lambda: False
        captured = {}
        self.slots.bridge.start = lambda *a, **k: captured.setdefault("ran", True)
        self.slots._name_edit.setText("p")
        self.ui.b000.click()
        self.assertNotIn("ran", captured, "must not dispatch when exe is missing")


class TestRealityScanPanelDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import realityscan_workflow as r

        self.tmp = tempfile.mkdtemp(prefix="rc_dispatch_")
        self.frames = os.path.join(self.tmp, "frames")
        os.makedirs(self.frames)
        self.ui = r.RealityScanWorkflowUI()
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

    def test_argv_includes_name_frames_output_and_preset(self) -> None:
        self.slots._name_edit.setText("proj")
        self.slots._frames_edit.setText(self.frames)
        self.slots._output_dir_edit.setText(self.tmp)
        self.slots._preset_mgr.load("high")  # quality=max flows in
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch to the runner")
        self.assertEqual(argv[argv.index("--name") + 1], "proj")
        self.assertEqual(argv[argv.index("--frames-dir") + 1], self.frames)
        self.assertEqual(argv[argv.index("--output-root") + 1], self.tmp)
        self.assertEqual(argv[argv.index("--quality") + 1], "max")


class TestRCRunCombinedFramesDir(unittest.TestCase):
    """``run_combined --frames-dir`` uses a single prepared capture directly
    (the panel's path), skipping --input-root subdir discovery."""

    def setUp(self) -> None:
        from pythontk.core_utils.user_config import CONFIG_ROOT_ENV_VAR
        import extapps.photogrammetry.profile as pp

        self.tmp = tempfile.mkdtemp(prefix="rc_framesdir_")
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ[CONFIG_ROOT_ENV_VAR] = os.path.join(self.tmp, "cfg")
        os.environ.pop(pp.PROFILE_ENV, None)
        self.ver = mock.patch(
            "extapps.photogrammetry.realityscan_workflow._realityscan_workflow."
            "get_realitycapture_version",
            return_value="test",
        )
        self.ver.start()
        self.addCleanup(self.ver.stop)
        self.frames = os.path.join(self.tmp, "cap")
        os.makedirs(self.frames)
        open(os.path.join(self.frames, "f.jpg"), "wb").close()
        self.out = os.path.join(self.tmp, "out")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_frames_dir_single_capture_runs(self) -> None:
        from extapps.photogrammetry.realityscan_workflow import run_combined as rc_run

        code = rc_run.main(
            [
                "--frames-dir",
                self.frames,
                "--output-root",
                self.out,
                "--name",
                "fd",
                "--mock",
                "--rsnode",
                "off",
                "--skip-curate",
                "--skip-equalize",
                "--no-publish",
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(
            os.path.exists(os.path.join(self.out, "fd", "fd_qc.json")),
            "QC sidecar not written for --frames-dir run",
        )

    def test_missing_frames_dir_errors(self) -> None:
        from extapps.photogrammetry.realityscan_workflow import run_combined as rc_run

        code = rc_run.main(
            [
                "--frames-dir",
                os.path.join(self.tmp, "nope"),
                "--output-root",
                self.out,
                "--name",
                "fd",
                "--mock",
                "--rsnode",
                "off",
            ]
        )
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
