# !/usr/bin/python
# coding=utf-8
"""Regression tests for
:mod:`extapps.photogrammetry.realityscan_workflow.run_combined`.

The engine-level publish behavior is covered by ``PublishOutputsTest`` in
``test_realityscan_workflow.py``; this module holds regressions keyed to the
``run_combined`` driver module itself.
"""
import os
import shutil
import tempfile
import unittest


class PublishExcludesLegacyProjectTest(unittest.TestCase):
    """publish_outputs must exclude the RC working project file for BOTH the
    RealityScan (.rsproj) and the legacy RealityCapture (.rcproj) extension.

    The engine picks project_ext = 'rcproj' whenever the RC exe basename lacks
    'realityscan' (legacy install), so a --save-project run leaves <name>.rcproj
    in the scratch project dir. Publishing it would push RC working state into
    the cloud-synced deliverable root — exactly what the exclusion prevents.
    """

    def setUp(self):
        from extapps.photogrammetry.realityscan_workflow.run_combined import (
            publish_outputs,
        )

        self.publish_outputs = publish_outputs
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rcproj_is_not_published(self):
        proj = os.path.join(self.tmp, "scratch", "welding")
        os.makedirs(proj)
        for rel in ("welding.obj", "welding.mtl", "welding.rcproj"):
            with open(os.path.join(proj, rel), "w") as fh:
                fh.write("x")
        pub = os.path.join(self.tmp, "synced", "welding")

        n = self.publish_outputs(proj, pub)

        self.assertEqual(n, 2)  # obj + mtl, but NOT the .rcproj working project
        self.assertTrue(os.path.isfile(os.path.join(pub, "welding.obj")))
        self.assertTrue(os.path.isfile(os.path.join(pub, "welding.mtl")))
        self.assertFalse(
            os.path.isfile(os.path.join(pub, "welding.rcproj")),
            "legacy RealityCapture .rcproj working project must not be published",
        )

    def test_rcproj_exclusion_is_case_insensitive(self):
        proj = os.path.join(self.tmp, "scratch2", "welding")
        os.makedirs(proj)
        with open(os.path.join(proj, "welding.RCPROJ"), "w") as fh:
            fh.write("x")
        pub = os.path.join(self.tmp, "synced2", "welding")

        n = self.publish_outputs(proj, pub)

        self.assertEqual(n, 0)
        self.assertFalse(os.path.isfile(os.path.join(pub, "welding.RCPROJ")))


if __name__ == "__main__":
    unittest.main()
