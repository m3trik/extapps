# !/usr/bin/python
# coding=utf-8
"""The unified --quality preset must drive each engine's mesh-density knob
(verified through the QC sidecar in mock mode — no real SDK)."""
import json
import os
import shutil
import tempfile
import unittest

import numpy as np
import cv2

from extapps.photogrammetry.metashape_workflow import run_combined as meta_run
from extapps.photogrammetry.realityscan_workflow import run_combined as rc_run


class RunnerQualityPresetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qpreset_")
        cap = os.path.join(self.tmp, "input", "cap")
        os.makedirs(cap)
        for i in range(2):  # discover_source_dirs needs image-bearing subdirs
            cv2.imwrite(os.path.join(cap, f"f{i}.jpg"),
                        np.full((32, 32, 3), 100, np.uint8))
        self.inp = os.path.join(self.tmp, "input")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _model_stage(self, out_sub):
        qc = os.path.join(self.tmp, out_sub, "t", "t_qc.json")
        with open(qc, encoding="utf-8") as fh:
            return json.load(fh)["stages"]["model"]

    def _stage(self, out_sub, name):
        qc = os.path.join(self.tmp, out_sub, "t", "t_qc.json")
        with open(qc, encoding="utf-8") as fh:
            return json.load(fh)["stages"][name]

    def test_metashape_quality_drives_face_count(self):
        for quality, expected in (("max", "high"), ("balanced", "medium")):
            out = f"meta_{quality}"
            rc = meta_run.main([
                "--input-root", self.inp, "--output-root",
                os.path.join(self.tmp, out), "--name", "t",
                "--quality", quality, "--skip-curate", "--skip-equalize",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(self._model_stage(out)["face_count"], expected)

    def test_metashape_depth_filter_flows_to_depth_stage(self):
        # --depth-filter is independent of --quality and must reach the depth
        # stage (the lever that denoises specular/low-texture geometry).
        out = "meta_filter"
        rc = meta_run.main([
            "--input-root", self.inp, "--output-root",
            os.path.join(self.tmp, out), "--name", "t",
            "--quality", "max", "--depth-filter", "moderate",
            "--skip-curate", "--skip-equalize",
        ])
        self.assertEqual(rc, 0)
        self.assertEqual(self._stage(out, "depth")["depth_filter"], "moderate")

    def test_realityscan_quality_maps_to_rc_preset(self):
        for quality, expected in (("max", "high"), ("balanced", "normal"),
                                  ("draft", "preview")):
            out = f"rc_{quality}"
            rc = rc_run.main([
                "--input-root", self.inp, "--output-root",
                os.path.join(self.tmp, out), "--name", "t", "--mock",
                "--quality", quality, "--skip-curate", "--skip-equalize",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(self._model_stage(out)["quality"], expected)


if __name__ == "__main__":
    unittest.main()
