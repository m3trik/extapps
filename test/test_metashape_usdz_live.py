# !/usr/bin/python
# coding=utf-8
"""Live Metashape USDZ-sidecar test — launches a REAL (new) metashape.exe.

Gated like ``test_metashape_live_integration``: set ``METASHAPE_RUN_INTEGRATION=1``
to run. Requires a licensed local Metashape (2.x). Runtime ~2-4 minutes.

Covers what the unit test (``test_usdz_sidecar``) cannot: that a texture atlas
authored by Metashape's **own** ``exportModel`` OBJ/MTL writer round-trips
through ``pythontk.obj_to_usdz`` — the real integration risk (Metashape's MTL
``map_Kd`` spelling and file layout, not a hand-written fixture). Drives the
full pipeline inside Metashape's bundled Python (align → build_model →
build_texture → ``export_model(save_usdz=True)``) on the same synthetic nadir
scene the sibling live test uses, then verifies the sidecar with pxr-free
``UsdzPackager.verify`` and confirms the atlas landed in the package.
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
class MetashapeUsdzLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from extapps.photogrammetry.metashape_workflow._metashape_connection import (
            MetashapeConnection,
        )
        cls.conn = MetashapeConnection()
        if not cls.conn.is_available():
            raise unittest.SkipTest("metashape.exe not found")
        cls.tmp = tempfile.mkdtemp(prefix="ms_usdz_")
        cls.frames, _ = make_nadir_scene(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_export_model_usdz_sidecar_live(self):
        proj = os.path.join(self.tmp, "proj")
        verdict = os.path.join(self.tmp, "verdict.json")
        # Same sys.path bootstrap the runner performs under ``metashape.exe -r``:
        # the extapps repo root (importable ``extapps``) + the sibling pythontk.
        pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bootstrap = [pkg_parent, os.path.join(os.path.dirname(pkg_parent), "pythontk")]
        script = os.path.join(self.tmp, "usdz_probe.py")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(textwrap.dedent(f"""\
                import json, os, sys, traceback
                for p in {bootstrap!r}:
                    if os.path.isdir(p) and p not in sys.path:
                        sys.path.insert(0, p)
                try:
                    from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow
                    import pythontk as ptk
                    mp = MetashapeWorkflow(project_path={proj!r}, name="scan")
                    mp.create_chunk("scan")
                    mp.add_images({self.frames!r})
                    # The real production model-track order (run_combined.py):
                    # align -> depth -> model -> texture -> export. build_model
                    # raises without depth maps, so generate_depth_maps is required.
                    mp.align_photos(downscale=4)
                    mp.generate_depth_maps(downscale=4)
                    mp.build_model(face_count="low")
                    mp.build_texture(texture_size=2048)
                    # The change under test: exportModel writes a real OBJ+MTL+atlas,
                    # then the sidecar authors <name>.usdz from Metashape's own output.
                    mp.export_model()  # save_usdz defaults True; OBJ default format
                    obj = os.path.join({proj!r}, "scan.obj")
                    usdz = os.path.join({proj!r}, "scan.usdz")
                    report = ptk.UsdzPackager.verify(usdz) if os.path.isfile(usdz) else None
                    names = ptk.UsdFile.list_package(usdz) if os.path.isfile(usdz) else []
                    json.dump({{
                        "obj_exists": os.path.isfile(obj),
                        "usdz_exists": os.path.isfile(usdz),
                        "usdz_valid": bool(report and report["valid"]),
                        "usdz_issues": (report or {{}}).get("issues", []),
                        "entries": names,
                        "has_texture_entry": any(n.startswith("textures/") for n in names),
                    }}, open({verdict!r}, "w"))
                except Exception:
                    # To stdout (run_script captures it) so a probe failure is
                    # visible in r.stdout, not buried on the child's stderr.
                    traceback.print_exc(file=sys.stdout)
                finally:
                    import Metashape
                    Metashape.app.quit()
            """))
        r = self.conn.run_script(script, timeout=1200)
        self.assertEqual(r.returncode, 0, (r.stdout or "")[-2000:])
        self.assertTrue(
            os.path.isfile(verdict),
            "probe wrote no verdict; output tail:\n" + (r.stdout or "")[-2000:],
        )
        with open(verdict, encoding="utf-8") as f:
            v = json.load(f)
        self.assertTrue(v["obj_exists"], "Metashape exportModel wrote no OBJ")
        self.assertTrue(v["usdz_exists"], "sidecar authored no .usdz")
        self.assertTrue(v["usdz_valid"], f"USDZ failed spec verify: {v['usdz_issues']}")
        self.assertEqual(v["entries"][0].split(".")[-1], "usda",
                         f"first package entry is not a layer: {v['entries']}")
        self.assertTrue(v["has_texture_entry"],
                        f"Metashape atlas not packaged: {v['entries']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
