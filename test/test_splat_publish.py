# !/usr/bin/python
# coding=utf-8
"""Engine-delivery (publish) stage — clean + convert the splat for Unity/web.

All mock-mode (no ``splat-transform`` install); the real CLI is verified on the
desktop. These lock the plumbing: the action lists handed to ``splat-transform``,
the output extensions per target, strict exe discovery, and that the runner
reaches the stage and records it in the QC sidecar.
"""
import json
import os
import shutil
import tempfile
import unittest

from extapps.photogrammetry.gaussian_splat_workflow._splat_publish import (
    SplatPublishWorkflow,
)
from extapps.photogrammetry.gaussian_splat_workflow import run_combined as gs_run


def _stages(sidecar):
    with open(sidecar, encoding="utf-8") as fh:
        return json.load(fh)["stages"]


def _stage(sidecar, name):
    return _stages(sidecar)[name]


class FindSplatTransformTest(unittest.TestCase):
    def test_env_override_strict(self):
        # A nonexistent SPLAT_TRANSFORM_EXE must resolve to None (-> mock), not
        # fall through to PATH.
        prev = os.environ.get("SPLAT_TRANSFORM_EXE")
        os.environ["SPLAT_TRANSFORM_EXE"] = os.path.join(
            tempfile.gettempdir(), "nope-splat-transform.cmd"
        )
        try:
            self.assertIsNone(SplatPublishWorkflow.find_splat_transform())
        finally:
            if prev is None:
                os.environ.pop("SPLAT_TRANSFORM_EXE", None)
            else:
                os.environ["SPLAT_TRANSFORM_EXE"] = prev


class SplatPublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="publish_")
        self.sp = SplatPublishWorkflow(
            project_path=os.path.join(self.tmp, "pub"), name="t", mock_mode=True
        )
        self.in_ply = os.path.join(self.tmp, "trained.ply")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_action_shape(self):
        out = self.sp.clean(
            self.in_ply, filter_floaters=True, min_opacity=0.1,
            crop_box=(0, 0, 0, 1, 1, 1), decimate="2000000",
        )
        self.assertTrue(out.endswith(".ply"))
        actions = _stage(self.sp.finalize_run(success=True), "splat_clean")["actions"]
        self.assertIn("-N", actions)              # filter NaN (default on)
        self.assertIn("-G", actions)              # filter floaters
        self.assertIn("-V", actions)
        self.assertIn("opacity,gt,0.1", actions)
        self.assertIn("-B", actions)
        self.assertIn("0,0,0,1,1,1", actions)
        self.assertIn("-F", actions)
        self.assertIn("2000000", actions)

    def test_no_filter_floaters_omits_flag(self):
        self.sp.clean(self.in_ply, filter_floaters=False)
        actions = _stage(self.sp.finalize_run(success=True), "splat_clean")["actions"]
        self.assertNotIn("-G", actions)

    def test_rotate_is_applied_first(self):
        # Up-axis fix must precede crop so the crop box is in the upright frame.
        self.sp.clean(self.in_ply, rotate="180,0,0", crop_box=(0, 0, 0, 1, 1, 1))
        actions = _stage(self.sp.finalize_run(success=True), "splat_clean")["actions"]
        self.assertEqual(actions[:2], ["-r", "180,0,0"])
        self.assertLess(actions.index("-r"), actions.index("-B"))

    def test_no_rotate_omits_flag(self):
        self.sp.clean(self.in_ply)
        actions = _stage(self.sp.finalize_run(success=True), "splat_clean")["actions"]
        self.assertNotIn("-r", actions)

    def test_to_unity_spz(self):
        spz = self.sp.to_unity(os.path.join(self.tmp, "clean.ply"), spz_version=4)
        self.assertTrue(spz.endswith(".spz"))
        st = _stage(self.sp.finalize_run(success=True), "publish_unity")
        self.assertEqual(st["spz_version"], 4)
        self.assertTrue(st["spz"].endswith(".spz"))

    def test_to_web_data_and_viewer(self):
        res = self.sp.to_web(os.path.join(self.tmp, "clean.ply"),
                             web_format="sog", with_viewer=True)
        self.assertTrue(res["data"].endswith(".sog"))
        self.assertTrue(res["viewer"].endswith(".html"))
        st = _stage(self.sp.finalize_run(success=True), "publish_web")
        self.assertEqual(st["web_format"], "sog")

    def test_to_web_compressed_ply_no_viewer(self):
        res = self.sp.to_web(os.path.join(self.tmp, "clean.ply"),
                             web_format="compressed-ply", with_viewer=False)
        self.assertTrue(res["data"].endswith(".compressed.ply"))
        self.assertIsNone(res["viewer"])

    def test_publish_fans_out_to_both_targets(self):
        res = self.sp.publish(self.in_ply, targets=("unity", "web"))
        self.assertTrue(res["clean"].endswith(".ply"))
        self.assertTrue(res["unity"].endswith(".spz"))
        self.assertTrue(res["web"]["data"].endswith(".sog"))
        stages = _stages(self.sp.finalize_run(success=True))
        self.assertIn("splat_clean", stages)
        self.assertIn("publish_unity", stages)
        self.assertIn("publish_web", stages)

    def test_publish_single_target(self):
        res = self.sp.publish(self.in_ply, targets=("unity",))
        self.assertIsNotNone(res["unity"])
        self.assertIsNone(res["web"])

    def test_publish_unknown_target_raises(self):
        # A typo'd target must error, not silently produce only a cleaned .ply.
        with self.assertRaises(ValueError):
            self.sp.publish(self.in_ply, targets=("unty",))


class RunnerPublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pubrun_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_publish_only_input_ply_skip_brush(self):
        # Publish an existing .ply with no colmap-dir / no Brush retrain.
        rc = gs_run.main([
            "--skip-brush", "--publish", "--mock",
            "--input-ply", os.path.join(self.tmp, "trained.ply"),
            "--output-root", os.path.join(self.tmp, "out"), "--name", "t",
        ])
        self.assertEqual(rc, 0)
        sidecar = os.path.join(self.tmp, "out", "t", "publish", "t_publish_qc.json")
        self.assertTrue(os.path.isfile(sidecar))
        stages = _stages(sidecar)
        self.assertIn("splat_clean", stages)
        self.assertIn("publish_unity", stages)
        self.assertIn("publish_web", stages)

    def test_publish_only_without_input_ply_errors(self):
        rc = gs_run.main([
            "--skip-brush", "--publish", "--mock",
            "--output-root", os.path.join(self.tmp, "out"), "--name", "t",
        ])
        self.assertEqual(rc, 1)

    def test_crop_box_negative_bounds_equals_form(self):
        # Centered scenes need negative crop bounds; the '=' form is required
        # (argparse reads a leading '-' as a flag) and must reach the -B action.
        rc = gs_run.main([
            "--skip-brush", "--publish", "--mock", "--publish-targets", "unity",
            "--input-ply", os.path.join(self.tmp, "trained.ply"),
            "--crop-box=-2,-2,-2,2,2,2",
            "--output-root", os.path.join(self.tmp, "out"), "--name", "c",
        ])
        self.assertEqual(rc, 0)
        sidecar = os.path.join(self.tmp, "out", "c", "publish", "c_publish_qc.json")
        actions = _stages(sidecar)["splat_clean"]["actions"]
        self.assertIn("-B", actions)
        self.assertIn("-2,-2,-2,2,2,2", actions)

    def test_preview_is_noop_in_mock(self):
        # --preview must not try to open a browser in mock mode (the .html is
        # never actually written), and the run must still succeed.
        import unittest.mock as mock
        with mock.patch("webbrowser.open") as opener:
            rc = gs_run.main([
                "--skip-brush", "--publish", "--preview", "--mock",
                "--input-ply", os.path.join(self.tmp, "trained.ply"),
                "--output-root", os.path.join(self.tmp, "out"), "--name", "p",
            ])
        self.assertEqual(rc, 0)
        opener.assert_not_called()

    def test_rotate_negative_angle_equals_form(self):
        # Negative euler angles need the '=' form (argparse reads leading '-' as
        # a flag) and must reach the -r action ahead of everything else.
        rc = gs_run.main([
            "--skip-brush", "--publish", "--mock", "--publish-targets", "unity",
            "--input-ply", os.path.join(self.tmp, "trained.ply"),
            "--rotate=-90,0,0",
            "--output-root", os.path.join(self.tmp, "out"), "--name", "r",
        ])
        self.assertEqual(rc, 0)
        sidecar = os.path.join(self.tmp, "out", "r", "publish", "r_publish_qc.json")
        actions = _stages(sidecar)["splat_clean"]["actions"]
        self.assertEqual(actions[:2], ["-r", "-90,0,0"])

    def test_publish_targets_subset(self):
        rc = gs_run.main([
            "--skip-brush", "--publish", "--mock", "--publish-targets", "unity",
            "--input-ply", os.path.join(self.tmp, "trained.ply"),
            "--output-root", os.path.join(self.tmp, "out"), "--name", "u",
        ])
        self.assertEqual(rc, 0)
        sidecar = os.path.join(self.tmp, "out", "u", "publish", "u_publish_qc.json")
        stages = _stages(sidecar)
        self.assertIn("publish_unity", stages)
        self.assertNotIn("publish_web", stages)


if __name__ == "__main__":
    unittest.main()
