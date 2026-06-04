# !/usr/bin/python
# coding=utf-8
"""Tests for the bridge plugin's HTTP dispatcher.

``dispatch_request`` is decoupled from Qt and HTTP, so we exercise the
routing logic synchronously here. Live HTTP + main-thread marshalling is
covered by the integration suite.
"""
import os
import sys
import unittest

try:
    from .base_test import SubstanceWorkflowTestCase
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_test import SubstanceWorkflowTestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from extapps.substance_workflow import registry
from extapps.substance_workflow.plugins.substance_workflow_bridge.server import dispatch_request


def _direct(fn, **kwargs):
    """Synchronous executor — calls the function directly, no Qt hop."""
    return fn(**kwargs)


class _RegistryIsolated(SubstanceWorkflowTestCase):

    def setUp(self) -> None:
        super().setUp()
        self._saved = dict(registry._REGISTRY)

    def tearDown(self) -> None:
        registry._REGISTRY.clear()
        registry._REGISTRY.update(self._saved)
        super().tearDown()


class TestHealth(_RegistryIsolated):

    def test_health_returns_ok(self) -> None:
        status, body = dispatch_request("/health", {})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])


class TestDescribeEndpoint(_RegistryIsolated):

    def test_describe_empty_returns_all_ops(self) -> None:
        @registry.register("test.x")
        def x() -> int:
            return 1

        status, body = dispatch_request("/describe", {"op": ""})
        self.assertEqual(status, 200)
        self.assertIn("test.x", body["value"])

    def test_describe_named_returns_signature(self) -> None:
        @registry.register("test.y")
        def y(arg: int) -> str:
            """Docs."""
            return ""

        status, body = dispatch_request("/describe", {"op": "test.y"})
        self.assertEqual(status, 200)
        self.assertEqual(body["value"]["doc"], "Docs.")
        self.assertIn("arg", body["value"]["parameters"])

    def test_describe_unknown_op_returns_empty_value(self) -> None:
        status, body = dispatch_request("/describe", {"op": "no.such.op"})
        self.assertEqual(status, 200)
        self.assertEqual(body["value"], {})


class TestOpDispatch(_RegistryIsolated):

    def test_unknown_op_returns_404(self) -> None:
        status, body = dispatch_request("/", {"op": "no.such.op"}, executor=_direct)
        self.assertEqual(status, 404)
        self.assertFalse(body["ok"])
        self.assertIn("Unknown op", body["error"])

    def test_op_success_returns_200_with_value(self) -> None:
        @registry.register("test.add")
        def add(a: int, b: int) -> int:
            return a + b

        status, body = dispatch_request(
            "/", {"op": "test.add", "kwargs": {"a": 2, "b": 3}}, executor=_direct
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["value"], 5)

    def test_op_failure_returns_500(self) -> None:
        @registry.register("test.fails")
        def fails() -> None:
            raise ValueError("kaboom")

        status, body = dispatch_request(
            "/", {"op": "test.fails"}, executor=_direct
        )
        self.assertEqual(status, 500)
        self.assertFalse(body["ok"])
        self.assertIn("ValueError: kaboom", body["error"])

    def test_arbitrary_path_falls_through_to_op_dispatch(self) -> None:
        @registry.register("test.found")
        def found() -> int:
            return 7

        status, body = dispatch_request(
            "/arbitrary", {"op": "test.found"}, executor=_direct
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["value"], 7)

    def test_empty_kwargs_works(self) -> None:
        @registry.register("test.noarg")
        def noarg() -> str:
            return "ok"

        status, body = dispatch_request(
            "/", {"op": "test.noarg"}, executor=_direct
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["value"], "ok")


if __name__ == "__main__":
    unittest.main()
