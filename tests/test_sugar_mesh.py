# !/usr/bin/python
# coding=utf-8
"""SuGaR mesh track (EXPERIMENTAL) — COLMAP dataset → textured .obj.

All mock-mode (no SuGaR install); the real interface is verified on the desktop.
These lock the plumbing: the command shape handed to SuGaR's train_full_pipeline,
strict repo discovery, and that the runner maps --quality → refinement time and
records the stage in the QC sidecar.
"""
import json
import os
import shutil
import tempfile
import unittest

from extapps.photogrammetry.sugar_mesh_workflow._sugar_mesh import (
    SugarMeshWorkflow,
)
from extapps.photogrammetry.sugar_mesh_workflow import run_combined as sugar_run


class SugarMeshTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sugar_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_find_sugar_dir_env_override_strict(self):
        # A nonexistent SUGAR_DIR must resolve to None (-> mock), not fall
        # through to the default install path.
        prev = os.environ.get("SUGAR_DIR")
        os.environ["SUGAR_DIR"] = os.path.join(self.tmp, "nope")
        try:
            self.assertIsNone(SugarMeshWorkflow.find_sugar_dir())
        finally:
            if prev is None:
                os.environ.pop("SUGAR_DIR", None)
            else:
                os.environ["SUGAR_DIR"] = prev

    def test_extract_mesh_mock_command_shape(self):
        sm = SugarMeshWorkflow(
            project_path=os.path.join(self.tmp, "proj"), name="t", mock_mode=True
        )
        mesh = sm.extract_mesh(
            colmap_dir=os.path.join(self.tmp, "welding_colmap"),
            regularization="dn_consistency", high_poly=True,
            refinement_time="long", gpu=0,
        )
        self.assertTrue(mesh.endswith(".obj"))
        sidecar = sm.finalize_run(success=True)
        with open(sidecar, encoding="utf-8") as fh:
            stage = json.load(fh)["stages"]["sugar_mesh"]
        cmd = stage["command"]
        self.assertIn("train_full_pipeline.py", cmd)
        self.assertIn("-r dn_consistency", cmd)
        self.assertIn("--high_poly True", cmd)
        self.assertIn("--refinement_time long", cmd)

    @unittest.skipUnless(os.name == "nt", "cmd.exe .bat encoding is a Windows concern")
    def test_run_bat_is_written_in_the_console_oem_codepage(self):
        # cmd reads .bat text in the OEM codepage, so a UTF-8 .bat turns a
        # non-ASCII install path into mojibake and the `cd /d` misses (the
        # RealityScan runner documents the same trap).
        sugar_dir = os.path.join(self.tmp, "SuGaR_é")
        os.makedirs(sugar_dir)
        sm = SugarMeshWorkflow(
            project_path=os.path.join(self.tmp, "proj"),
            name="t",
            sugar_dir=sugar_dir,
            mock_mode=True,
        )
        bat = sm._write_run_bat("python train_full_pipeline.py")
        with open(bat, "rb") as fh:
            data = fh.read()
        self.assertIn(f'cd /d "{sugar_dir}"'.encode("oem"), data)

    @unittest.skipUnless(os.name == "nt", "cmd.exe .bat line ends are a Windows concern")
    def test_run_bat_line_ends_are_exact_crlf(self):
        # "\r\n".join written through a TEXT-mode handle doubled every CR
        # (CR CR LF): cmd tolerates it, but it is not the file the code meant
        # to write. AppLauncher.write_batch_script owns the line ends now.
        sm = SugarMeshWorkflow(
            project_path=os.path.join(self.tmp, "proj"), name="t", mock_mode=True
        )
        bat = sm._write_run_bat("python train_full_pipeline.py")
        with open(bat, "rb") as fh:
            data = fh.read()
        self.assertNotIn(b"\r\r\n", data)
        self.assertTrue(data.endswith(b"SUGAR_EXIT=%errorlevel%\r\n"), data)

    @unittest.skipIf(os.name == "nt", "the bash runner is the POSIX half")
    def test_the_posix_runner_sources_the_env_and_reports_the_pipelines_status(self):
        # SuGaR is Linux-native, but the runner was `cmd /c <.bat>` -- no such
        # program there. The bash runner sources sugar_buildenv.sh, starts in
        # the SuGaR folder, and exits with the pipeline's own status (a failed
        # run must raise, not pass as success).
        import subprocess

        sugar_dir = os.path.join(self.tmp, "SuGaR")
        os.makedirs(sugar_dir)
        env_script = os.path.join(sugar_dir, "sugar_buildenv.sh")
        with open(env_script, "w", encoding="utf-8") as fh:
            fh.write("export PTK_SUGAR_ENV=on\n")
        sm = SugarMeshWorkflow(
            project_path=os.path.join(self.tmp, "proj"),
            name="t",
            sugar_dir=sugar_dir,
            mock_mode=True,
        )
        self.assertEqual(sm.env_bat, env_script)
        here = os.path.realpath(sugar_dir)
        script = sm._write_run_bat(
            f"sh -c 'test \"$PTK_SUGAR_ENV\" = on && test \"$(pwd -P)\" = \"{here}\" && exit 3'"
        )
        proc = subprocess.run(["bash", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("SUGAR_EXIT=3", proc.stdout)

    def test_runner_quality_maps_refinement(self):
        colmap = os.path.join(self.tmp, "welding_colmap")
        os.makedirs(os.path.join(colmap, "images"))
        os.makedirs(os.path.join(colmap, "sparse", "0"))
        for quality, expected in (("max", "long"), ("balanced", "medium")):
            rc = sugar_run.main([
                "--colmap-dir", colmap,
                "--output-root", os.path.join(self.tmp, "out"),
                "--name", f"s_{quality}", "--quality", quality, "--mock",
            ])
            self.assertEqual(rc, 0)
            qc = os.path.join(self.tmp, "out", f"s_{quality}",
                              f"s_{quality}_qc.json")
            with open(qc, encoding="utf-8") as fh:
                stage = json.load(fh)["stages"]["sugar_mesh"]
            self.assertEqual(stage["refinement_time"], expected)


class SugarPresetOverlayTest(unittest.TestCase):
    """--preset lays shared run-template SuGaR knobs over the runner defaults."""

    def setUp(self):
        from pythontk import UserConfig
        from unittest import mock
        import extapps.photogrammetry.profile as pp

        self.tmp = tempfile.mkdtemp(prefix="sugar_preset_")
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ[UserConfig.CONFIG_ROOT_ENV_VAR] = os.path.join(self.tmp, "cfg")
        os.environ.pop(pp.PROFILE_ENV, None)
        pp.Profile.preset_store("sugar").save("t_mesh", {
            "refinement_time": "long", "regularization": "sdf",
            "surface_level": 0.5, "high_poly": False,
        })
        self.colmap = os.path.join(self.tmp, "welding_colmap")
        os.makedirs(os.path.join(self.colmap, "images"))
        os.makedirs(os.path.join(self.colmap, "sparse", "0"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_preset_overlays_sugar_knobs(self):
        rc = sugar_run.main([
            "--colmap-dir", self.colmap,
            "--output-root", os.path.join(self.tmp, "out"),
            "--name", "s", "--quality", "balanced",  # 'medium' without the preset
            "--preset", "t_mesh", "--mock",
        ])
        self.assertEqual(rc, 0)
        qc = os.path.join(self.tmp, "out", "s", "s_qc.json")
        with open(qc, encoding="utf-8") as fh:
            stage = json.load(fh)["stages"]["sugar_mesh"]
        self.assertEqual(stage["refinement_time"], "long")  # preset beat --quality
        cmd = stage["command"]
        self.assertIn("-r sdf", cmd)
        self.assertIn("--refinement_time long", cmd)
        self.assertIn("--high_poly False", cmd)

    def test_unknown_preset_rejected(self):
        rc = sugar_run.main([
            "--colmap-dir", self.colmap,
            "--output-root", os.path.join(self.tmp, "out"),
            "--name", "s", "--preset", "nope", "--mock",
        ])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
