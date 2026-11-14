# !/usr/bin/python
# coding=utf-8
"""Tests for the Brush gaussian-splat workflow engine (mock-mode + helpers)."""
import json
import os
import shutil
import tempfile
import unittest

from extapps.photogrammetry.gaussian_splat_workflow._gaussian_splat_workflow import (
    GaussianSplatWorkflow,
)
from extapps.photogrammetry.gaussian_splat_workflow import run_combined as gs_run


class GaussianSplatWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        # a fake COLMAP dataset dir (existence is all mock-mode needs)
        cls.colmap = os.path.join(cls.tmp, "gsplat_in")
        os.makedirs(os.path.join(cls.colmap, "sparse", "0"), exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.tmp):
            shutil.rmtree(cls.tmp, ignore_errors=True)

    def _wf(self):
        return GaussianSplatWorkflow(
            project_path=os.path.join(self.tmp, "proj"),
            name="welding_splat",
            mock_mode=True,
        )

    def test_find_brush_exe_env_override(self):
        # nonexistent path -> None (caller enters mock mode)
        prev = os.environ.get("BRUSH_EXE")
        try:
            os.environ["BRUSH_EXE"] = os.path.join(self.tmp, "nope.exe")
            self.assertIsNone(GaussianSplatWorkflow.find_brush_exe())
            self.assertFalse(GaussianSplatWorkflow.is_brush_available())
            # existing file -> returned
            fake = os.path.join(self.tmp, "brush_app.exe")
            open(fake, "w").close()
            os.environ["BRUSH_EXE"] = fake
            self.assertEqual(GaussianSplatWorkflow.find_brush_exe(), fake)
        finally:
            if prev is None:
                os.environ.pop("BRUSH_EXE", None)
            else:
                os.environ["BRUSH_EXE"] = prev

    def test_mock_train_records_qc_and_returns_ply(self):
        wf = self._wf()
        ply = wf.train(
            self.colmap, total_steps=30000, max_resolution=1920,
            export_path=os.path.join(self.tmp, "proj"),
            export_name="welding_splat_{iter}.ply",
        )
        self.assertTrue(ply.endswith("welding_splat_30000.ply"))
        stage = wf.qc.data["stages"]["train"]
        self.assertEqual(stage["max_resolution"], 1920)
        self.assertEqual(stage["total_steps"], 30000)
        self.assertEqual(stage["colmap_dir"], self.colmap)

    def test_train_rejects_missing_colmap_dir(self):
        wf = self._wf()
        with self.assertRaises(ValueError):
            wf.train(os.path.join(self.tmp, "does_not_exist"))

    def test_read_splat_count(self):
        ply = os.path.join(self.tmp, "tiny.ply")
        with open(ply, "wb") as fh:
            fh.write(b"ply\nformat binary_little_endian 1.0\n"
                     b"element vertex 12345\nproperty float x\nend_header\n")
        self.assertEqual(GaussianSplatWorkflow.read_splat_count(ply), 12345)


class RunnerQualityTest(unittest.TestCase):
    """The --quality preset maps to Brush total-steps (max trains longer)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gsq_")
        self.colmap = os.path.join(self.tmp, "ds")
        os.makedirs(os.path.join(self.colmap, "sparse", "0"))
        os.makedirs(os.path.join(self.colmap, "images"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_quality_maps_brush_steps(self):
        for quality, expected in (("draft", 7000), ("balanced", 30000), ("max", 50000)):
            rc = gs_run.main([
                "--colmap-dir", self.colmap,
                "--output-root", os.path.join(self.tmp, "out"),
                "--name", f"q_{quality}", "--quality", quality, "--mock",
            ])
            self.assertEqual(rc, 0)
            qc = os.path.join(self.tmp, "out", f"q_{quality}", f"q_{quality}_qc.json")
            with open(qc, encoding="utf-8") as fh:
                stage = json.load(fh)["stages"]["train"]
            self.assertEqual(stage["total_steps"], expected)


if __name__ == "__main__":
    unittest.main()
