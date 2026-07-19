# !/usr/bin/python
# coding=utf-8
"""Live Metashape integration test — launches a REAL (new) metashape.exe.

Gated like substance_workflow's live tests: set ``METASHAPE_RUN_INTEGRATION=1``
to run. Requires a licensed local Metashape (2.x). Total runtime ~2-4 minutes.

Covers what mock mode cannot:
- ``run_combined`` end-to-end inside Metashape's bundled Python (argparse
  BooleanOptionalAction, sys.path bootstrap, the cv2-missing prep fallback),
- live matchPhotos kwargs (generic_preselection / keypoint_limit /
  tiepoint_limit / filter_mask) and a full 24/24 alignment,
- the 2.x mask path: ``import_masks`` = generateMasks(MaskingModeFile) with a
  directory-qualified filename template (importMasks was removed in 2.x),
- ``--export-colmap`` on a ``--stop-after`` run (images/ + sparse/0/).

The synthetic capture is a textured plane sampled by a translating nadir
camera (70%/50% overlap) — standard drone-mapping geometry that aligns fully.
"""
import json
import os
import shutil
import tempfile
import textwrap
import unittest

try:
    from ._photogrammetry_live_scene import make_nadir_scene
except ImportError:  # bare pytest collection (test dir on sys.path, not a package)
    from _photogrammetry_live_scene import make_nadir_scene

RUN_LIVE = os.environ.get("METASHAPE_RUN_INTEGRATION") == "1"


@unittest.skipUnless(RUN_LIVE, "set METASHAPE_RUN_INTEGRATION=1 to run")
class MetashapeLiveIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from extapps.photogrammetry.metashape_workflow._metashape_connection import (
            MetashapeConnection,
        )
        cls.conn = MetashapeConnection()
        if not cls.conn.is_available():
            raise unittest.SkipTest("metashape.exe not found")
        cls.tmp = tempfile.mkdtemp(prefix="ms_live_")
        cls.frames, cls.masks = make_nadir_scene(cls.tmp, with_masks=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_align_colmap_and_masks_live(self):
        out_root = os.path.join(self.tmp, "out")
        colmap = os.path.join(self.tmp, "colmap")
        r = self.conn.run_combined(
            args=[
                "--name", "live", "--frames-dir", self.frames,
                "--output-root", out_root, "--quality", "draft",
                "--stop-after", "align",
                "--export-colmap", colmap,
            ],
            timeout=900,
        )
        self.assertEqual(r.returncode, 0, (r.stdout or "")[-2000:])
        with open(os.path.join(out_root, "live", "live_qc.json"),
                  encoding="utf-8") as f:
            qc = json.load(f)
        self.assertTrue(qc["success"])
        align = qc["stages"]["align"]
        self.assertGreaterEqual(align["aligned_pct"], 90.0)
        self.assertTrue(align["generic_preselection"])
        # cv2 is absent in Metashape's bundled Python: the prep stage must
        # record its skip honestly rather than pretending curation ran.
        self.assertEqual(
            qc["stages"]["curate_input_set"].get("fallback"), "cv2_missing")
        self.assertTrue(qc["stages"]["export_colmap"]["ok"])
        self.assertTrue(os.path.isdir(os.path.join(colmap, "sparse", "0")))

        # 2.x mask path: file-template import + filter_mask matching. The
        # embedded script boots sys.path exactly like run_combined does when
        # run via ``metashape.exe -r``: the extapps repo root (holding the
        # importable ``extapps``) plus the sibling pythontk repo.
        pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bootstrap = [
            pkg_parent,
            os.path.join(os.path.dirname(pkg_parent), "pythontk"),
        ]
        script = os.path.join(self.tmp, "mask_probe.py")
        verdict = os.path.join(self.tmp, "mask_probe.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(textwrap.dedent(f"""\
                import json, os, sys, traceback
                for p in {bootstrap!r}:
                    if os.path.isdir(p) and p not in sys.path:
                        sys.path.insert(0, p)
                # quit() in a finally: a probe error must not leave
                # metashape.exe running until the 900s timeout kills it,
                # burying the traceback in an opaque TimeoutExpired.
                try:
                    from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow
                    mp = MetashapeWorkflow(project_path={os.path.join(self.tmp, 'mask_proj')!r}, name="m")
                    mp.create_chunk("m")
                    mp.add_images({self.frames!r})
                    mp.import_masks({self.masks!r})
                    applied = sum(1 for c in mp.chunk.cameras if c.mask is not None)
                    mp.align_photos(downscale=4, filter_mask=True)
                    aligned = sum(1 for c in mp.chunk.cameras if c.transform is not None)
                    json.dump({{"applied": applied, "aligned": aligned,
                                "total": len(mp.chunk.cameras)}},
                              open({verdict!r}, "w"))
                except Exception:
                    traceback.print_exc()
                finally:
                    import Metashape
                    Metashape.app.quit()
            """))
        r2 = self.conn.run_script(script, timeout=900)
        self.assertEqual(r2.returncode, 0, (r2.stdout or "")[-2000:])
        # The finally-quit exits 0 even when the probe body raised — the
        # missing verdict (plus the printed traceback) is the failure signal.
        self.assertTrue(
            os.path.isfile(verdict),
            "probe wrote no verdict; probe output tail:\n"
            + (r2.stdout or "")[-2000:],
        )
        with open(verdict, encoding="utf-8") as f:
            v = json.load(f)
        self.assertEqual(v["applied"], v["total"],
                         "generateMasks(MaskingModeFile) paired no masks")
        self.assertGreaterEqual(v["aligned"], int(v["total"] * 0.9))


if __name__ == "__main__":
    unittest.main(verbosity=2)
