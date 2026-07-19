# !/usr/bin/python
# coding=utf-8
"""Tests for RealityScanConnection (interactive / PsExec / sign-in gate) — mocked."""
import os
import subprocess
import tempfile
import shutil
import unittest
from unittest import mock

CONN = "extapps.photogrammetry.realityscan_workflow._realityscan_connection"
from extapps.photogrammetry.realityscan_workflow._realityscan_connection import (  # noqa: E402
    RealityScanConnection,
    RealityScanInteractiveError,
)


class RealityScanConnectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = os.path.join(self.tmp, "rc.log")
        self.conn = RealityScanConnection(exe="C:/fake/RealityScan.exe")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unavailable_raises(self):
        c = RealityScanConnection(exe="x")
        c.exe = None
        self.assertFalse(c.is_available())
        with self.assertRaises(FileNotFoundError):
            c.run(["-quit"], log_path=self.log)

    def test_interactive_runs_via_applauncher(self):
        # Interactive path must route through AppLauncher.run (the ecosystem
        # subprocess boundary), streaming output to log_path via output_file.
        with mock.patch(f"{CONN}.AppLauncher.is_interactive_session", return_value=True), \
             mock.patch(f"{CONN}.AppLauncher.run") as run:
            run.return_value = subprocess.CompletedProcess(["x"], 0)
            cp = self.conn.run(["-align", "-quit"], log_path=self.log)
            self.assertEqual(cp.returncode, 0)
            (called_exe,), kwargs = run.call_args
            self.assertEqual(called_exe, "C:/fake/RealityScan.exe")
            self.assertIn("-align", kwargs["args"])
            self.assertEqual(kwargs["output_file"], self.log)

    def test_non_interactive_no_console_raises(self):
        with mock.patch(f"{CONN}.AppLauncher.is_interactive_session", return_value=False), \
             mock.patch(f"{CONN}.AppLauncher.active_console_session_id", return_value=None):
            with self.assertRaises(RealityScanInteractiveError):
                self.conn.run(["-quit"], log_path=self.log)

    def test_non_interactive_launches_in_session_and_reads_marker(self):
        def fake_launch(app, args=None, session=None, **kw):
            # Simulate the wrapper bat running in the console session.
            with open(self.log + ".done", "w") as fh:
                fh.write("0")
            return subprocess.CompletedProcess(["psexec"], 0)

        with mock.patch(f"{CONN}.AppLauncher.is_interactive_session", return_value=False), \
             mock.patch(f"{CONN}.AppLauncher.active_console_session_id", return_value=1), \
             mock.patch(f"{CONN}.AppLauncher.launch_in_session", side_effect=fake_launch):
            cp = self.conn.run(
                ["-align", "-quit"], log_path=self.log, poll_interval=0.02, timeout=30
            )
        self.assertEqual(cp.returncode, 0)
        bat = self.log + ".run.bat"
        self.assertTrue(os.path.exists(bat))  # wrapper written
        with open(bat, encoding="ascii") as fh:
            text = fh.read()
        # Guard the cmd redirection gotcha: `echo %errorlevel%>file` makes the
        # bare exit digit a file-handle redirect -> empty marker -> false
        # failure. The wrapper must use the leading-redirect form instead.
        self.assertNotIn("%errorlevel%>", text)
        self.assertIn("echo %errorlevel%", text)

    def test_non_interactive_bat_preserves_non_ascii_path(self):
        # Regression: the cross-session .bat was written encoding="ascii",
        # errors="replace", so a non-ASCII output path (e.g. C:\Users\José\...)
        # was mangled to '?'. cmd then redirected RC output + the .done marker
        # to the wrong file while Python polled the correct one -> 2h hang +
        # TimeoutError. The wrapper must preserve the non-ASCII path verbatim.
        try:
            "José".encode("oem")  # OEM codepage must be able to represent it
        except UnicodeEncodeError:  # pragma: no cover - depends on host codepage
            self.skipTest("host OEM codepage cannot represent the test path")

        log = os.path.join(self.tmp, "José", "align.log")
        os.makedirs(os.path.dirname(log), exist_ok=True)

        def fake_launch(app, args=None, session=None, **kw):
            with open(log + ".done", "w") as fh:
                fh.write("0")
            return subprocess.CompletedProcess(["psexec"], 0)

        with mock.patch(f"{CONN}.AppLauncher.is_interactive_session", return_value=False), \
             mock.patch(f"{CONN}.AppLauncher.active_console_session_id", return_value=1), \
             mock.patch(f"{CONN}.AppLauncher.launch_in_session", side_effect=fake_launch):
            cp = self.conn.run(
                ["-align", "-quit"], log_path=log, poll_interval=0.02, timeout=30
            )
        self.assertEqual(cp.returncode, 0)
        bat = log + ".run.bat"
        with open(bat, encoding="oem") as fh:
            text = fh.read()
        # The non-ASCII directory name must survive verbatim (not become 'Jos?').
        self.assertIn("José", text)
        self.assertNotIn("Jos?", text)

    def test_epic_signin_active_heuristic(self):
        with mock.patch(f"{CONN}.AppLauncher.get_running_processes", return_value=[123]):
            self.assertTrue(RealityScanConnection.epic_signin_active())
        with mock.patch(f"{CONN}.AppLauncher.get_running_processes", return_value=[]):
            self.assertFalse(RealityScanConnection.epic_signin_active())


if __name__ == "__main__":
    unittest.main()
