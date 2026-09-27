# !/usr/bin/python
# coding=utf-8
"""WorkflowEngine -- the run lifecycle the five photogrammetry engines share.

Pins the three phases (open: identity + folders + QC sidecar; run: a logged
tool run through AppLauncher; finalize: the sidecar) and guards the roster: no
engine keeps a private copy, and no engine module launches a process past
AppLauncher again.
"""
import ast
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from extapps.photogrammetry._workflow_engine import WorkflowEngine
from extapps.photogrammetry._progress_notify import ProgressNotifyMixin


class _Engine(WorkflowEngine):
    def __init__(self, project_path, name="run", mock_mode=True, make_dirs=True):
        self.mock_mode = mock_mode
        self._open_run(
            project_path,
            name,
            qc_fields={"tool_exe": "/x/tool", "tool_version": "1.2"},
            make_dirs=make_dirs,
        )


class TestOpenRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wfengine_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_binds_identity_makes_folders_and_seeds_the_sidecar_in_order(self):
        proj = os.path.join(self.tmp, "proj")
        eng = _Engine(proj, name="scan")
        self.assertEqual((eng.project_path, eng.name), (proj, "scan"))
        self.assertTrue(os.path.isdir(os.path.join(proj, "logs")))
        with open(eng.finalize_run(success=True), encoding="utf-8") as fh:
            data = json.load(fh)
        keys = [k for k in data if k in ("project_name", "tool_exe", "tool_version", "mock_mode")]
        self.assertEqual(keys, ["project_name", "tool_exe", "tool_version", "mock_mode"])
        self.assertEqual(data["project_name"], "scan")
        self.assertIs(data["mock_mode"], True)

    def test_sidecar_is_named_by_the_class_suffix(self):
        class _Publish(_Engine):
            QC_SUFFIX = "_publish_qc.json"

        eng = _Publish(os.path.join(self.tmp, "p"), name="splat")
        self.assertEqual(os.path.basename(eng.qc.path), "splat_publish_qc.json")

    def test_make_dirs_false_defers_the_folders(self):
        proj = os.path.join(self.tmp, "lazy")
        eng = _Engine(proj, make_dirs=False)
        self.assertFalse(os.path.exists(proj))
        log = eng._log_path("x")  # made on demand
        self.assertTrue(os.path.isdir(os.path.dirname(log)))


class TestRunLogged(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wfengine_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.eng = _Engine(os.path.join(self.tmp, "proj"))

    def test_real_run_streams_output_under_the_argv_header(self):
        argv = [sys.executable, "-c", "print('alpha'); print('beta')"]
        done = self.eng._run_logged(argv, "tool", timeout=60)
        self.assertEqual(done.returncode, 0)
        with open(self.eng._log_path("tool"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        self.assertTrue(lines[0].startswith("# argv: ["), lines[0])
        self.assertEqual(lines[1:], ["alpha", "beta"])

    def test_nonzero_exit_is_returned_not_raised(self):
        argv = [sys.executable, "-c", "import sys; sys.exit(3)"]
        self.assertEqual(self.eng._run_logged(argv, "fail").returncode, 3)

    def test_custom_header(self):
        self.eng._run_logged([sys.executable, "-c", "pass"], "h", header="cmd: x y")
        with open(self.eng._log_path("h"), encoding="utf-8") as fh:
            self.assertEqual(fh.readline(), "# cmd: x y\n")

    def test_routes_through_app_launcher(self):
        import subprocess

        with mock.patch(
            "extapps.photogrammetry._workflow_engine.AppLauncher.run",
            return_value=subprocess.CompletedProcess(["t"], 0),
        ) as run:
            self.eng._run_logged(["tool", "-a", 1], "t", timeout=5, cwd=self.tmp)
        args, kwargs = run.call_args
        self.assertEqual(args, ("tool",))
        self.assertEqual(kwargs["args"], ["-a", "1"])
        self.assertEqual((kwargs["timeout"], kwargs["cwd"]), (5, self.tmp))
        self.assertTrue(callable(kwargs["on_output"]))


class TestRoster(unittest.TestCase):
    """Derived from the engines themselves, never a hand-picked subset."""

    @staticmethod
    def _engines():
        from extapps.photogrammetry.gaussian_splat_workflow._gaussian_splat_workflow import (  # noqa: E501
            GaussianSplatWorkflow,
        )
        from extapps.photogrammetry.gaussian_splat_workflow._splat_publish import (
            SplatPublishWorkflow,
        )
        from extapps.photogrammetry.metashape_workflow._metashape_workflow import (
            MetashapeWorkflow,
        )
        from extapps.photogrammetry.realityscan_workflow._realityscan_workflow import (
            RealityCaptureWorkflow,
        )
        from extapps.photogrammetry.sugar_mesh_workflow._sugar_mesh import (
            SugarMeshWorkflow,
        )

        return (
            GaussianSplatWorkflow,
            SplatPublishWorkflow,
            MetashapeWorkflow,
            RealityCaptureWorkflow,
            SugarMeshWorkflow,
        )

    def test_every_progress_reporting_engine_is_a_workflow_engine(self):
        for cls in self._engines():
            with self.subTest(engine=cls.__name__):
                self.assertTrue(issubclass(cls, WorkflowEngine))
                self.assertNotIn("_open_run", vars(cls))
                self.assertNotIn("_run_logged", vars(cls))
        # Every ProgressNotifyMixin engine in the package is on the roster.
        subclasses = {
            c for c in ProgressNotifyMixin.__subclasses__() if c is not WorkflowEngine
        }
        stray = {c.__name__ for c in subclasses if c.__module__.startswith("extapps.")}
        self.assertEqual(stray, set(), "engines on the mixin but not the base")

    def test_no_engine_module_launches_a_process_past_app_launcher(self):
        launches = {"run", "Popen", "call", "check_call", "check_output"}
        for cls in self._engines():
            tree = ast.parse(inspect.getsource(sys.modules[cls.__module__]))
            hits = [
                f"{cls.__module__}:{node.lineno}"
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "subprocess"
                and node.attr in launches
            ]
            with self.subTest(engine=cls.__name__):
                self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
