# !/usr/bin/python
# coding=utf-8
"""COLMAP-export bridge (Metashape) — the splat track's input.

All mock-mode (no Metashape SDK); the real interface is verified on the desktop.
These lock the plumbing: that the Metashape runner reaches the COLMAP-export
stage and records the expected knobs in the QC sidecar. (The SuGaR mesh track
has its own tests in ``test_sugar_mesh.py``; the splat publish stage in
``test_splat_publish.py``.)
"""
import json
import os
import shutil
import tempfile
import unittest

import numpy as np
import cv2

from unittest import mock

from extapps.photogrammetry.metashape_workflow._metashape_workflow import (
    MetashapeWorkflow,
)
from extapps.photogrammetry.metashape_workflow import run_combined as meta_run
from extapps.photogrammetry.gaussian_splat_workflow._gaussian_splat_workflow import (
    GaussianSplatWorkflow,
)
from extapps.photogrammetry.gaussian_splat_workflow import run_combined as gsplat_run


class GsplatPresetOverlayTest(unittest.TestCase):
    """--preset lays shared run-template knobs over the gsplat runner defaults."""

    def setUp(self):
        from pythontk.core_utils.user_config import CONFIG_ROOT_ENV_VAR
        import extapps.photogrammetry.profile as pp

        self.tmp = tempfile.mkdtemp(prefix="gsplat_preset_")
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ[CONFIG_ROOT_ENV_VAR] = os.path.join(self.tmp, "cfg")
        os.environ.pop(pp.PROFILE_ENV, None)
        # A user preset in the gaussian_splat store sets splat-training knobs.
        pp.Profile.preset_store("gaussian_splat").save("t_splat", {
            "total_steps": 12345, "max_splats": 7, "max_resolution": 999, "sh_degree": 2,
        })
        self.colmap = os.path.join(self.tmp, "ds")
        os.makedirs(self.colmap)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_preset_overlays_training_knobs(self):
        captured = {}

        def spy(self, **kw):
            captured.update(kw)
            return os.path.join(self.project_path, "t_30000.ply")

        with mock.patch.object(GaussianSplatWorkflow, "train", spy):
            rc = gsplat_run.main([
                "--colmap-dir", self.colmap, "--name", "t",
                "--output-root", os.path.join(self.tmp, "out"),
                "--quality", "balanced",  # would be 30000 steps without the preset
                "--preset", "t_splat", "--mock",
            ])
        self.assertEqual(rc, 0)
        self.assertEqual(captured["total_steps"], 12345)   # preset beat --quality
        self.assertEqual(captured["max_splats"], 7)
        self.assertEqual(captured["max_resolution"], 999)
        self.assertEqual(captured["sh_degree"], 2)

    def test_explicit_flag_overrides_preset(self):
        captured = {}

        def spy(self, **kw):
            captured.update(kw)
            return os.path.join(self.project_path, "t_1.ply")

        with mock.patch.object(GaussianSplatWorkflow, "train", spy):
            rc = gsplat_run.main([
                "--colmap-dir", self.colmap, "--name", "t",
                "--output-root", os.path.join(self.tmp, "out"),
                "--preset", "t_splat", "--total-steps", "500", "--mock",
            ])
        self.assertEqual(rc, 0)
        self.assertEqual(captured["total_steps"], 500)  # explicit flag wins

    def test_unknown_preset_rejected(self):
        rc = gsplat_run.main([
            "--colmap-dir", self.colmap, "--name", "t",
            "--output-root", os.path.join(self.tmp, "out"),
            "--preset", "nope", "--mock",
        ])
        self.assertEqual(rc, 2)

    def _run_with_profile(self, profile_dict, extra_argv=()):
        import extapps.photogrammetry.profile as pp

        prof_path = os.path.join(self.tmp, "profile.json")
        with open(prof_path, "w", encoding="utf-8") as fh:
            json.dump(profile_dict, fh)
        captured = {}

        def spy(self, **kw):
            captured.update(kw)
            return os.path.join(self.project_path, "t_1.ply")

        with mock.patch.dict(os.environ, {pp.PROFILE_ENV: prof_path}):
            with mock.patch.object(GaussianSplatWorkflow, "train", spy):
                rc = gsplat_run.main([
                    "--colmap-dir", self.colmap, "--name", "t",
                    "--output-root", os.path.join(self.tmp, "out"),
                    "--mock", *extra_argv,
                ])
        return rc, captured

    def test_profile_quality_tier_reaches_brush_steps(self):
        """A profile setting ONLY the tier trains that tier's steps — the
        packaged gsplat block must not shadow it (regression: total_steps
        shipped as a number, so the deep-merged key always existed and the
        documented tier lever silently trained balanced 30k)."""
        rc, captured = self._run_with_profile({"quality": "draft"})
        self.assertEqual(rc, 0)
        self.assertEqual(captured["total_steps"], 7000)

    def test_profile_total_steps_pins_over_tier(self):
        """An explicit user gsplat.total_steps still beats the tier table."""
        rc, captured = self._run_with_profile(
            {"quality": "draft", "gsplat": {"total_steps": 11111}}
        )
        self.assertEqual(rc, 0)
        self.assertEqual(captured["total_steps"], 11111)


class ColmapExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="colmap_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_export_colmap_mock_records_stage(self):
        mp = MetashapeWorkflow(
            project_path=os.path.join(self.tmp, "proj"), name="t", mock_mode=True
        )
        mp.create_chunk("t")
        out = os.path.join(self.tmp, "ds")
        result = mp.export_colmap(out, max_cameras=300)
        self.assertEqual(result, out)
        sidecar = mp.finalize_run(success=True)
        with open(sidecar, encoding="utf-8") as fh:
            stage = json.load(fh)["stages"]["export_colmap"]
        self.assertEqual(stage["output_dir"], out)
        self.assertTrue(stage["convert_to_pinhole"])
        self.assertTrue(stage["binary"])
        self.assertEqual(stage["max_cameras"], 300)

    def test_runner_export_colmap_flag_runs_stage(self):
        cap = os.path.join(self.tmp, "input", "cap")
        os.makedirs(cap)
        for i in range(2):
            cv2.imwrite(os.path.join(cap, f"f{i}.jpg"),
                        np.full((32, 32, 3), 100, np.uint8))
        ds = os.path.join(self.tmp, "explicit_colmap")
        rc = meta_run.main([
            "--input-root", os.path.join(self.tmp, "input"),
            "--output-root", os.path.join(self.tmp, "out"), "--name", "t",
            "--quality", "max", "--export-colmap", ds,
            "--skip-curate", "--skip-equalize",
        ])
        self.assertEqual(rc, 0)
        with open(os.path.join(self.tmp, "out", "t", "t_qc.json"),
                  encoding="utf-8") as fh:
            stages = json.load(fh)["stages"]
        self.assertIn("export_colmap", stages)
        self.assertEqual(stages["export_colmap"]["output_dir"], ds)


if __name__ == "__main__":
    unittest.main()
