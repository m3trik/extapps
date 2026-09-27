# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.photogrammetry._process_runner."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from extapps.photogrammetry._process_runner import PyModuleRunner


class _Runner(PyModuleRunner):
    MODULE = "extapps.photogrammetry.realityscan_workflow.run_combined"


class TestPyModuleRunnerInterpreter(unittest.TestCase):
    def test_a_dcc_hosted_panel_runs_the_hosts_python_not_the_host(self):
        """Inside Maya ``sys.executable`` is the GUI binary (``maya.exe``, or
        ``maya.bin`` on Linux): ``-m`` through it launched a second Maya instead
        of the run. The child gets the host's own python (``mayapy``)."""
        host, sibling = (
            ("maya.exe", "mayapy.exe")
            if sys.platform == "win32"
            else ("maya.bin", "mayapy")
        )
        with tempfile.TemporaryDirectory() as root:
            bin_dir = os.path.join(root, "bin")
            os.makedirs(bin_dir)
            for name in (host, sibling):
                open(os.path.join(bin_dir, name), "w").close()
            with patch.object(sys, "executable", os.path.join(bin_dir, host)):
                exe, argv = _Runner.__new__(_Runner)._command(["--x"])
        self.assertEqual(exe, os.path.join(bin_dir, sibling))
        self.assertEqual(argv, ["-m", _Runner.MODULE, "--x"])

    def test_a_plain_python_runs_itself(self):
        exe, _argv = _Runner.__new__(_Runner)._command([])
        self.assertEqual(exe, sys.executable)


class _Script(PyModuleRunner):
    """Runs ``python -c <CODE>`` -- a real child, no engine install needed."""

    CODE = "print('alpha'); print('beta')"

    def is_available(self) -> bool:
        return True

    @property
    def exe(self):
        return sys.executable

    def _command(self, argv):
        return sys.executable, ["-c", self.CODE, *argv]


class TestRealChild(unittest.TestCase):
    """The runner end to end: AppLauncher.spawn, the reader thread, and the
    event-loop delivery of output + exit code (a real child and a real Qt loop,
    since the handoff between the two threads is the part worth proving)."""

    @classmethod
    def setUpClass(cls):
        from qtpy import QtWidgets

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _run(self, runner, argv=(), cancel_after_ms=None, timeout_ms=30000, launches=True):
        from qtpy import QtCore

        loop = QtCore.QEventLoop()
        lines, codes = [], []

        def done(code):
            codes.append(code)
            loop.quit()

        QtCore.QTimer.singleShot(timeout_ms, loop.quit)
        runner.start(list(argv), on_line=lines.append, on_done=done)
        self.assertEqual(runner.is_running(), launches)
        if cancel_after_ms is not None:
            QtCore.QTimer.singleShot(cancel_after_ms, runner.cancel)
        loop.exec_() if hasattr(loop, "exec_") else loop.exec()
        return "".join(lines), codes

    def test_output_and_exit_code_arrive_on_the_event_loop(self):
        class _Exit3(_Script):
            CODE = "print('alpha'); print('beta', flush=True); raise SystemExit(3)"

        out, codes = self._run(_Exit3())
        self.assertEqual(codes, [3])
        self.assertEqual(out.splitlines(), ["alpha", "beta"])

    def test_the_child_is_spawned_through_app_launcher(self):
        import pythontk as ptk

        runner = _Script()
        with patch.object(
            ptk.AppLauncher, "spawn", wraps=ptk.AppLauncher.spawn
        ) as spawn:
            out, codes = self._run(runner)
        self.assertEqual(codes, [0])
        self.assertEqual(spawn.call_args.args[0], sys.executable)
        # The child env is the live one with the runner's overrides on top.
        self.assertEqual(spawn.call_args.kwargs["env"]["PYTHONUNBUFFERED"], "1")

    def test_a_launch_failure_is_a_minus_one_completion(self):
        class _Missing(_Script):
            def _command(self, argv):
                return os.path.join(tempfile.gettempdir(), "no_such_engine.exe"), []

        out, codes = self._run(_Missing(), launches=False)
        self.assertEqual(codes, [-1])
        self.assertIn("[runner] process error", out)

    def test_cancel_kills_the_child_and_completes(self):
        class _Sleeper(_Script):
            CODE = "import time; print('started', flush=True); time.sleep(60)"

        runner = _Sleeper()
        out, codes = self._run(runner, cancel_after_ms=1500)
        self.assertEqual(len(codes), 1)
        self.assertNotEqual(codes[0], 0)
        self.assertTrue(runner._cancelled)
        self.assertFalse(runner.is_running())


if __name__ == "__main__":
    unittest.main()
