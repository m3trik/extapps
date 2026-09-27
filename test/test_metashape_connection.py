# !/usr/bin/python
# coding=utf-8
"""Tests for the headless MetashapeConnection launch driver (no real Metashape)."""
import os
import tempfile
import unittest
from unittest import mock

from extapps.photogrammetry.metashape_workflow._metashape_connection import MetashapeConnection


class MetashapeConnectionTest(unittest.TestCase):
    def test_find_exe_env_override(self):
        fd, fake = tempfile.mkstemp(suffix="metashape.exe")
        os.close(fd)
        prev = os.environ.get("METASHAPE_EXE")
        try:
            os.environ["METASHAPE_EXE"] = fake
            self.assertEqual(MetashapeConnection.find_exe(), fake)
            self.assertTrue(MetashapeConnection(exe=fake).is_available())
        finally:
            os.remove(fake)
            if prev is None:
                os.environ.pop("METASHAPE_EXE", None)
            else:
                os.environ["METASHAPE_EXE"] = prev

    def test_unavailable_and_raises_without_exe(self):
        # Force the not-found state (the test host may actually have Metashape).
        conn = MetashapeConnection(exe="placeholder")
        conn.exe = None
        self.assertFalse(conn.is_available())
        with self.assertRaises(FileNotFoundError):
            conn.run_script("whatever.py")

    def test_run_script_builds_headless_argv_no_offscreen(self):
        # The Windows rule: that bundle ships no Qt offscreen plugin.
        conn = MetashapeConnection(exe="C:/fake/metashape.exe")
        with mock.patch(
            "extapps.photogrammetry.metashape_workflow._metashape_connection.AppLauncher.run"
        ) as run, mock.patch("sys.platform", "win32"):
            conn.run_script("M:/x/script.py", args=["--name", "t"], log_file="L.log")
            (called_exe,), kwargs = run.call_args
            self.assertEqual(called_exe, "C:/fake/metashape.exe")
            argv = kwargs["args"]
            self.assertEqual(argv[:2], ["-r", "M:/x/script.py"])
            self.assertIn("--name", argv)
            self.assertNotIn("-platform", argv)  # never the offscreen path
            self.assertNotIn("offscreen", argv)
            self.assertEqual(kwargs["output_file"], "L.log")

    def test_linux_without_a_display_runs_offscreen(self):
        # metashape.sh on SSH / a render node: its xcb platform would abort.
        # With a display (a desktop session) the argv stays the plain form.
        conn = MetashapeConnection(exe="/opt/metashape-pro/metashape.sh")
        target = (
            "extapps.photogrammetry.metashape_workflow._metashape_connection"
            ".AppLauncher.run"
        )
        headless = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        with mock.patch(target) as run, mock.patch("sys.platform", "linux"):
            with mock.patch.dict(os.environ, headless, clear=True):
                conn.run_script("/x/script.py")
            self.assertEqual(
                run.call_args.kwargs["args"][:4],
                ["-platform", "offscreen", "-r", "/x/script.py"],
            )
            with mock.patch.dict(os.environ, {"DISPLAY": ":0"}):
                conn.run_script("/x/script.py")
            self.assertEqual(run.call_args.kwargs["args"], ["-r", "/x/script.py"])

    def test_run_combined_targets_runner_module(self):
        conn = MetashapeConnection(exe="C:/fake/metashape.exe")
        with mock.patch.object(conn, "run_script") as rs:
            conn.run_combined(args=["--input-root", "X"])
            (script_path,), kwargs = rs.call_args
            self.assertTrue(script_path.replace("\\", "/").endswith(
                "metashape_workflow/run_combined.py"))
            self.assertEqual(kwargs["args"], ["--input-root", "X"])

    def test_run_combined_runner_executes_as_top_level_script(self):
        # Regression: run_combined.py is what `metashape.exe -r` executes, i.e.
        # as __main__ with no package. Package-relative imports raise ImportError
        # there; the self-bootstrap guard must let it run standalone. Exercise it
        # the way Metashape would (run the file by path, not via `-m`).
        import subprocess
        import sys
        from extapps.photogrammetry.metashape_workflow import run_combined as rc_mod

        proc = subprocess.run(
            [sys.executable, rc_mod.__file__, "--help"],
            capture_output=True, text=True, timeout=180,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotIn("attempted relative import", out)
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("usage", out.lower())


if __name__ == "__main__":
    unittest.main()
