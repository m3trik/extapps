# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.job — the Painter batch wrapper.

The call/result types and the batch loop are pythontk's (``Call`` / ``Result``
/ ``RpcJob``, tested there); what is pinned here is the Painter lifecycle
around them and the retired re-exports.
"""

import os
import sys
import unittest
import warnings
from unittest.mock import patch

try:
    from .base_test import SubstanceWorkflowTestCase
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_test import SubstanceWorkflowTestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pythontk as ptk
from pythontk import Call, Result

from extapps.substance_workflow import Job


def _connected(MockConn):
    """The mocked connection's shared client: reachable, invoke configurable."""
    instance = MockConn.return_value
    instance.connect.return_value = True
    client = instance.client
    client.ping.return_value = True
    return instance, client


class TestJob(SubstanceWorkflowTestCase):
    def test_add_chains(self) -> None:
        j = Job().add("project.info").add("project.save")
        self.assertEqual([c.op for c in j.calls], ["project.info", "project.save"])

    def test_add_builds_shared_calls(self) -> None:
        j = Job().add("export.textures", preset="PBR", path="/out")
        self.assertIsInstance(j.calls[0], ptk.Call)
        self.assertEqual(j.calls[0].kwargs, {"preset": "PBR", "path": "/out"})

    def test_run_delegates_to_run_batch(self) -> None:
        with patch("extapps.substance_workflow.job.Job.run_batch") as mock_batch:
            mock_batch.return_value = [Result(op="x", ok=True)]
            Job().add("x").run(gui=True)
        mock_batch.assert_called_once()
        self.assertTrue(mock_batch.call_args.kwargs["gui"])


class TestRunBatch(SubstanceWorkflowTestCase):
    def test_runs_the_shared_batch_over_the_connections_client(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance, client = _connected(MockConn)
            client.invoke.side_effect = lambda op, timeout=60.0, **kw: {"op": op, **kw}
            results = Job.run_batch([Call("a"), Call("b", kwargs={"x": 1})])

        self.assertEqual([r.op for r in results], ["a", "b"])
        self.assertTrue(all(isinstance(r, ptk.Result) and r.ok for r in results))
        self.assertEqual(results[1].value, {"op": "b", "x": 1})

    def test_records_op_failure_without_aborting_batch(self) -> None:
        invoked = []

        def fake_invoke(op, timeout=60.0, **kw):
            invoked.append(op)
            if op == "fails":
                raise RuntimeError("Op 'fails' failed: ValueError: boom")
            return None

        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            _, client = _connected(MockConn)
            client.invoke.side_effect = fake_invoke
            results = Job.run_batch([Call("ok1"), Call("fails"), Call("ok2")])

        self.assertEqual(invoked, ["ok1", "fails", "ok2"])
        self.assertEqual([r.ok for r in results], [True, False, True])
        self.assertIn("ValueError: boom", results[1].error)

    def test_raises_when_connect_fails(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            MockConn.return_value.connect.return_value = False
            with self.assertRaises(RuntimeError):
                Job.run_batch([Call("never_called")])
            MockConn.return_value.client.invoke.assert_not_called()

    def test_always_shuts_down_on_success(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance, client = _connected(MockConn)
            client.invoke.return_value = None
            Job.run_batch([Call("x")])
        instance.shutdown.assert_called_once_with(force=True)

    def test_shuts_down_on_baseexception(self) -> None:
        """KeyboardInterrupt isn't caught — but cleanup must still run."""
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance, client = _connected(MockConn)
            client.invoke.side_effect = KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):
                Job.run_batch([Call("x")])
        instance.shutdown.assert_called_once_with(force=True)

    def test_invoke_timeout_overrides_every_call(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            _, client = _connected(MockConn)
            client.invoke.return_value = None
            Job.run_batch([Call("x", timeout=5.0)], invoke_timeout=42.0)
        self.assertEqual(client.invoke.call_args.kwargs["timeout"], 42.0)

    def test_without_invoke_timeout_each_call_keeps_its_own(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            _, client = _connected(MockConn)
            client.invoke.return_value = None
            Job.run_batch([Call("x", timeout=7.0)])
        self.assertEqual(client.invoke.call_args.kwargs["timeout"], 7.0)


class TestRetiredReexports(SubstanceWorkflowTestCase):
    """``Call`` / ``Result`` are pythontk's; the extapps roots only alias them
    for one release, with a notice."""

    def test_package_aliases_resolve_to_pythontk_with_a_warning(self) -> None:
        import extapps
        import extapps.substance_workflow as sw

        for module in (sw, extapps):
            for name, target in (("Call", ptk.Call), ("Result", ptk.Result)):
                with self.subTest(module=module.__name__, name=name):
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        self.assertIs(getattr(module, name), target)
                    self.assertTrue(
                        any(issubclass(w.category, DeprecationWarning) for w in caught)
                    )


@unittest.skipUnless(
    os.environ.get("SUBSTANCE_WORKFLOW_RUN_INTEGRATION") == "1",
    "Set SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1 to run live Painter integration tests",
)
class TestRunBatchIntegration(SubstanceWorkflowTestCase):
    def test_run_batch(self) -> None:
        results = Job.run_batch([Call("project.info")], gui=False, timeout=240)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok, f"Op failed: {results[0].error}")
        self.assertIsInstance(results[0].value, dict)


if __name__ == "__main__":
    unittest.main()
