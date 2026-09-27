# !/usr/bin/python
# coding=utf-8
"""Tests for the in-Painter bridge plugin: the shared RPC core, served for real.

The bridge is ``extapps.substance_workflow.registry.PLUGIN`` (a
``pythontk.RpcPlugin``), so these drive it over an actual loopback socket with
the client ``PainterConnection`` uses -- the same wire Painter serves. Main-thread
marshalling is disabled through the plugin's own env switch (no pumped Qt loop
here); the marshaller itself is pythontk's, tested there.
"""
import os
import sys
import unittest
from unittest import mock

try:
    from .base_test import SubstanceWorkflowTestCase
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_test import SubstanceWorkflowTestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from extapps.substance_workflow import registry
from extapps.substance_workflow.env_utils.painter_connection import PainterConnection

_NO_MARSHAL = {"SUBSTANCE_WORKFLOW_DISABLE_MAIN_THREAD": "1"}


class TestServedOverTheWire(SubstanceWorkflowTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        env = mock.patch.dict(os.environ, _NO_MARSHAL)
        env.start()
        cls.addClassCleanup(env.stop)
        ops = mock.patch.dict(registry.PLUGIN.registry._ops)
        ops.start()
        cls.addClassCleanup(ops.stop)

        @registry.register("test.add")
        def add(a: int, b: int) -> int:
            """Sum."""
            return a + b

        @registry.register("test.fails")
        def fails() -> None:
            raise ValueError("kaboom")

        host, port = registry.PLUGIN.start(port=0, host="127.0.0.1")
        cls.addClassCleanup(registry.PLUGIN.stop)
        cls.conn = PainterConnection()
        cls.conn.host, cls.conn.port = host, port
        cls.conn.is_connected = True

    def test_health(self) -> None:
        self.assertTrue(self.conn.client.ping(timeout=5.0))

    def test_op_round_trip(self) -> None:
        self.assertEqual(self.conn.invoke("test.add", a=2, b=3), 5)

    def test_op_failure_carries_the_remote_type(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            self.conn.invoke("test.fails")
        self.assertIn("ValueError: kaboom", str(ctx.exception))

    def test_unknown_op(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            self.conn.invoke("no.such.op")
        self.assertIn("Unknown op", str(ctx.exception))

    def test_describe_route(self) -> None:
        d = self.conn.describe("test.add")
        self.assertEqual((d["name"], d["doc"]), ("test.add", "Sum."))
        self.assertEqual([p["name"] for p in d["params"]], ["a", "b"])
        self.assertIn("test.add", [x["name"] for x in self.conn.describe()])

    def test_real_ops_are_served(self) -> None:
        """The bridge package's op modules register onto the served table."""
        import extapps.substance_workflow.plugins.substance_workflow_bridge as bridge

        self.assertTrue(bridge.OP_MODULES)
        self.assertIn("project.info", self.conn.client.list_ops())


class TestPluginLifecycle(SubstanceWorkflowTestCase):
    """Painter's enable/disable hooks drive the shared core's gated start."""

    def setUp(self) -> None:
        super().setUp()
        import extapps.substance_workflow.plugins.substance_workflow_bridge as bridge

        self.bridge = bridge
        self.addCleanup(registry.PLUGIN.stop)
        env = mock.patch.dict(os.environ, {"SUBSTANCE_WORKFLOW_PORT": "0", **_NO_MARSHAL})
        env.start()
        self.addCleanup(env.stop)

    def test_start_plugin_binds_only_inside_painter(self) -> None:
        with mock.patch.object(registry.PLUGIN, "is_hosted", return_value=False):
            self.bridge.start_plugin()
        self.assertFalse(registry.PLUGIN.is_running())

        with mock.patch.object(registry.PLUGIN, "is_hosted", return_value=True):
            self.bridge.start_plugin()
        self.assertTrue(registry.PLUGIN.is_running())

        self.bridge.close_plugin()
        self.assertFalse(registry.PLUGIN.is_running())

    def test_autostart_opt_out(self) -> None:
        with mock.patch.dict(os.environ, {"SUBSTANCE_WORKFLOW_AUTOSTART": "0"}), \
             mock.patch.object(registry.PLUGIN, "is_hosted", return_value=True):
            self.bridge.start_plugin()
        self.assertFalse(registry.PLUGIN.is_running())


if __name__ == "__main__":
    unittest.main()
