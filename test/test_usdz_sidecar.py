#!/usr/bin/env python
# coding=utf-8
"""USDZ review-sidecar tests for the photogrammetry mesh workflows.

``export_model(save_usdz=True)`` authors ``<name>.usdz`` beside an exported
OBJ via ``pythontk.obj_to_usdz`` — pure file-level, so no Metashape / RC /
DCC is needed here. Covers both engines' ``_export_usdz_sidecar`` and the
never-fatal contract.

Run::

    pytest extapps/test/test_usdz_sidecar.py
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

import pythontk as ptk

# Minimal valid 1x1 PNG.
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fccfc0f01f0005050202b8bcf3ed0000000049454e44ae426082"
)

_OBJ = """mtllib scan.mtl
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
vt 0 0
vt 1 0
vt 1 1
vt 0 1
usemtl scan_mat
f 1/1 2/2 3/3 4/4
"""

_MTL = """newmtl scan_mat
map_Kd scan_diffuse.png
"""


class _SidecarCase(unittest.TestCase):
    workflow_cls = None  # set by subclasses

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="usdz_sidecar_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fixture_obj(self):
        obj = os.path.join(self.tmp, "scan.obj")
        with open(obj, "w") as fh:
            fh.write(_OBJ)
        with open(os.path.join(self.tmp, "scan.mtl"), "w") as fh:
            fh.write(_MTL)
        with open(os.path.join(self.tmp, "scan_diffuse.png"), "wb") as fh:
            fh.write(_PNG)
        return obj

    def _sidecar(self, path):
        # A PrepStagesMixin staticmethod (shared by both engines) — callable
        # on the class, so no SDK (Metashape module / RC transport) is needed.
        return self.workflow_cls._export_usdz_sidecar(path)

    def test_sidecar_authored_beside_obj(self):
        if self.workflow_cls is None:
            self.skipTest("base class")
        out = self._sidecar(self._fixture_obj())
        self.assertEqual(out, os.path.join(self.tmp, "scan.usdz"))
        self.assertTrue(os.path.isfile(out))
        report = ptk.UsdzPackager.verify(out)
        self.assertTrue(report["valid"], report["issues"])
        names = ptk.UsdFile.list_package(out)
        self.assertEqual(names[0], "scan.usda")
        self.assertIn("textures/scan_diffuse.png", names)

    def test_sidecar_failure_is_nonfatal(self):
        if self.workflow_cls is None:
            self.skipTest("base class")
        out = self._sidecar(os.path.join(self.tmp, "ghost.obj"))
        self.assertIsNone(out)  # reported to stderr, never raised


class TestMetashapeUsdzSidecar(_SidecarCase):
    @property
    def workflow_cls(self):
        from extapps.photogrammetry.metashape_workflow._metashape_workflow import (
            MetashapeWorkflow,
        )

        return MetashapeWorkflow


class TestRealityScanUsdzSidecar(_SidecarCase):
    @property
    def workflow_cls(self):
        from extapps.photogrammetry.realityscan_workflow._realityscan_workflow import (
            RealityCaptureWorkflow,
        )

        return RealityCaptureWorkflow


if __name__ == "__main__":
    unittest.main(verbosity=2)
