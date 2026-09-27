# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.registry — the op table on the shared core.

The table, decorator and ``describe`` contract are pythontk's ``OpRegistry``
(tested in pythontk's ``test_plugin_core.py``). Pinned here: that this module
IS that core rather than a second stack, and the Painter-specific data it
configures the plugin with.
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

import pythontk as ptk

from extapps.substance_workflow import registry


class _RegistryIsolated(SubstanceWorkflowTestCase):
    """Restore the plugin's op table after each test (test ops must not leak)."""

    def setUp(self) -> None:
        super().setUp()
        patcher = mock.patch.dict(registry.PLUGIN.registry._ops)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestSharedCore(SubstanceWorkflowTestCase):
    def test_the_registry_is_a_shared_rpc_plugin(self) -> None:
        self.assertIsInstance(registry.PLUGIN, ptk.RpcPlugin)
        self.assertIsInstance(registry.PLUGIN.registry, ptk.OpRegistry)

    def test_module_names_are_the_plugin_registrys_own_methods(self) -> None:
        reg = registry.PLUGIN.registry
        for name in ("register", "get", "all_ops", "describe"):
            with self.subTest(name=name):
                self.assertEqual(getattr(registry, name), getattr(reg, name))

    def test_painter_configuration(self) -> None:
        plugin = registry.PLUGIN
        self.assertEqual(plugin.host_module, "substance_painter")
        self.assertEqual(plugin.env_prefix, "SUBSTANCE_WORKFLOW")
        # The env names PainterConnection pins at launch.
        self.assertEqual(
            plugin.marshaller.disable_env, "SUBSTANCE_WORKFLOW_DISABLE_MAIN_THREAD"
        )
        with mock.patch.dict(os.environ, {"SUBSTANCE_WORKFLOW_PORT": "5123"}):
            self.assertEqual(plugin.port, 5123)
        with mock.patch.dict(os.environ, {"SUBSTANCE_WORKFLOW_PORT": ""}):
            self.assertEqual(plugin.port, 0)  # unset = OS-assigned

    def test_main_thread_bound_outlasts_a_long_bake(self) -> None:
        """A multi-texture-set 4K bake runs for many minutes: a bound near the
        core's 60 s default would turn working bakes into TimeoutErrors."""
        self.assertGreaterEqual(registry.PLUGIN.marshaller.timeout, 3600.0)

    def test_system_ops_come_from_the_core(self) -> None:
        for op in ("system.ping", "system.list_ops", "system.describe"):
            with self.subTest(op=op):
                self.assertIsNotNone(registry.get(op))


class TestRegister(_RegistryIsolated):
    def test_register_and_get(self) -> None:
        @registry.register("test_ns.explicit")
        def fn() -> None:
            pass

        self.assertIs(registry.get("test_ns.explicit"), fn)
        self.assertIn("test_ns.explicit", registry.all_ops())

    def test_duplicate_name_raises(self) -> None:
        """A typo that silently shadows a real op must not pass."""

        @registry.register("test_ns.dup")
        def fn1() -> None:
            pass

        with self.assertRaises(ValueError):

            @registry.register("test_ns.dup")
            def fn2() -> None:
                pass

        self.assertIs(registry.get("test_ns.dup"), fn1)

    def test_get_unknown_returns_none(self) -> None:
        self.assertIsNone(registry.get("nonexistent.op"))


class TestDescribe(_RegistryIsolated):
    """The shared ``{name, doc, params}`` contract (no private dialect)."""

    def test_describe_one(self) -> None:
        @registry.register("test_ns.doc")
        def fn(x: int = 42, y=None) -> dict:
            """One-liner docstring."""
            return {}

        d = registry.describe("test_ns.doc")
        self.assertEqual(d["name"], "test_ns.doc")
        self.assertEqual(d["doc"], "One-liner docstring.")
        self.assertEqual(
            d["params"], [{"name": "x", "default": "42"}, {"name": "y", "default": "None"}]
        )

    def test_describe_all_lists_every_op(self) -> None:
        @registry.register("test_ns.alpha")
        def a() -> None:
            pass

        names = [d["name"] for d in registry.describe()]
        self.assertIn("test_ns.alpha", names)
        self.assertEqual(names, sorted(names))

    def test_describe_unknown_is_none(self) -> None:
        self.assertIsNone(registry.describe("nonexistent.op"))


if __name__ == "__main__":
    unittest.main()
