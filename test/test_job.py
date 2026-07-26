# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.job — Call / Job / Result / run_batch."""

import json
import os
import sys
import unittest
from unittest.mock import patch

try:
    from .base_test import SubstanceWorkflowTestCase
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_test import SubstanceWorkflowTestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from extapps.substance_workflow import Call, Job, Result


class TestCall(SubstanceWorkflowTestCase):
    def test_to_dict_includes_op_and_kwargs(self) -> None:
        c = Call("project.info", kwargs={"path": "/tmp/x.spp"})
        self.assertEqual(
            c.to_dict(),
            {"op": "project.info", "kwargs": {"path": "/tmp/x.spp"}},
        )

    def test_default_kwargs_is_empty_dict(self) -> None:
        c = Call("project.close")
        self.assertEqual(c.kwargs, {})

    def test_distinct_calls_have_distinct_kwargs(self) -> None:
        """Guard against the classic mutable-default-arg bug."""
        a = Call("op")
        b = Call("op")
        a.kwargs["leaked"] = True
        self.assertNotIn("leaked", b.kwargs)


class TestResult(SubstanceWorkflowTestCase):
    def test_defaults(self) -> None:
        r = Result(index=0, op="x", ok=True)
        self.assertIsNone(r.value)
        self.assertIsNone(r.error)

    def test_failure_record(self) -> None:
        r = Result(index=3, op="x", ok=False, error="boom")
        self.assertEqual(r.error, "boom")
        self.assertIsNone(r.value)


class TestJob(SubstanceWorkflowTestCase):
    def test_add_chains(self) -> None:
        j = Job().add("project.info").add("project.save")
        self.assertEqual([c.op for c in j.calls], ["project.info", "project.save"])

    def test_add_passes_kwargs(self) -> None:
        j = Job().add("export.textures", preset="PBR", path="/out")
        self.assertEqual(j.calls[0].kwargs, {"preset": "PBR", "path": "/out"})

    def test_json_round_trip(self) -> None:
        j = Job().add("a").add("b", x=1)
        encoded = json.dumps({"calls": [c.to_dict() for c in j.calls]})
        decoded = json.loads(encoded)
        self.assertEqual(decoded["calls"][1]["kwargs"]["x"], 1)

    def test_run_delegates_to_run_batch(self) -> None:
        with patch("extapps.substance_workflow.job.Job.run_batch") as mock_batch:
            mock_batch.return_value = [Result(index=0, op="x", ok=True)]
            j = Job().add("x")
            j.run(gui=True)

        mock_batch.assert_called_once()
        kwargs = mock_batch.call_args.kwargs
        self.assertTrue(kwargs["gui"])


class TestRunBatch(SubstanceWorkflowTestCase):
    def test_collects_successful_results(self) -> None:
        captured: list = []

        def fake_invoke(op, timeout=60.0, **kw):
            captured.append((op, kw))
            return {"op": op, "kw": kw}

        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance = MockConn.return_value
            instance.connect.return_value = True
            instance.invoke.side_effect = fake_invoke

            results = Job.run_batch([Call("a"), Call("b", kwargs={"x": 1})])

        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.ok for r in results))
        self.assertEqual(results[0].value, {"op": "a", "kw": {}})
        self.assertEqual(results[1].value, {"op": "b", "kw": {"x": 1}})

    def test_records_op_failure_without_aborting_batch(self) -> None:
        invoked = []

        def fake_invoke(op, timeout=60.0, **kw):
            invoked.append(op)
            if op == "fails":
                raise RuntimeError("boom")
            return None

        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance = MockConn.return_value
            instance.connect.return_value = True
            instance.invoke.side_effect = fake_invoke

            results = Job.run_batch([Call("ok1"), Call("fails"), Call("ok2")])

        self.assertEqual(invoked, ["ok1", "fails", "ok2"])
        self.assertTrue(results[0].ok)
        self.assertFalse(results[1].ok)
        self.assertIn("RuntimeError: boom", results[1].error)
        self.assertTrue(results[2].ok)

    def test_raises_when_connect_fails(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            MockConn.return_value.connect.return_value = False
            with self.assertRaises(RuntimeError):
                Job.run_batch([Call("never_called")])

    def test_always_shuts_down_on_success(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance = MockConn.return_value
            instance.connect.return_value = True
            instance.invoke.return_value = None
            Job.run_batch([Call("x")])
        instance.shutdown.assert_called_once_with(force=True)

    def test_shuts_down_on_baseexception(self) -> None:
        """KeyboardInterrupt isn't caught — but cleanup must still run."""
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance = MockConn.return_value
            instance.connect.return_value = True
            instance.invoke.side_effect = KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):
                Job.run_batch([Call("x")])
        instance.shutdown.assert_called_once_with(force=True)

    def test_invoke_timeout_passed_through(self) -> None:
        with patch("extapps.substance_workflow.job.PainterConnection") as MockConn:
            instance = MockConn.return_value
            instance.connect.return_value = True
            instance.invoke.return_value = None
            Job.run_batch([Call("x")], invoke_timeout=42.0)
        kwargs = instance.invoke.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 42.0)


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
