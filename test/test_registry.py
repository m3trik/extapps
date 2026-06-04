# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.registry — the @register decorator + lookup."""
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


class _RegistryIsolated(SubstanceWorkflowTestCase):
    """Snapshot / restore the global registry so tests don't pollute each other."""

    def setUp(self) -> None:
        super().setUp()
        self._saved = dict(registry._REGISTRY)

    def tearDown(self) -> None:
        registry._REGISTRY.clear()
        registry._REGISTRY.update(self._saved)
        super().tearDown()


class TestRegister(_RegistryIsolated):

    def test_register_explicit_name(self) -> None:
        @registry.register("test_ns.explicit")
        def fn() -> int:
            return 1

        self.assertIs(registry.get("test_ns.explicit"), fn)
        self.assertEqual(fn._op_name, "test_ns.explicit")

    def test_register_derived_name_strips_utils_suffix(self) -> None:
        def fn() -> int:
            return 1

        fn.__module__ = "fake_utils"
        wrapped = registry.register()(fn)
        self.assertEqual(wrapped._op_name, "fake.fn")

    def test_register_derived_name_preserves_module_when_no_utils_suffix(self) -> None:
        def fn() -> int:
            return 1

        fn.__module__ = "plain_module"
        wrapped = registry.register()(fn)
        self.assertEqual(wrapped._op_name, "plain_module.fn")

    def test_register_warns_on_duplicate(self) -> None:
        @registry.register("test_ns.dup")
        def fn1() -> int:
            return 1

        with self.assertLogs("extapps.substance_workflow.registry", level="WARNING") as ctx:
            @registry.register("test_ns.dup")
            def fn2() -> int:
                return 2

        self.assertTrue(
            any("re-registered" in msg for msg in ctx.output),
            "Expected re-registration warning",
        )
        # Override takes effect.
        self.assertIs(registry.get("test_ns.dup"), fn2)


class TestGet(_RegistryIsolated):

    def test_get_unknown_returns_none(self) -> None:
        self.assertIsNone(registry.get("nonexistent.op"))

    def test_get_returns_registered_callable(self) -> None:
        @registry.register("test_ns.x")
        def fn() -> None:
            pass

        self.assertIs(registry.get("test_ns.x"), fn)


class TestAllOps(_RegistryIsolated):

    def test_all_ops_returns_copy(self) -> None:
        all1 = registry.all_ops()
        all1["spurious"] = lambda: None
        self.assertNotIn("spurious", registry.all_ops())

    def test_all_ops_reflects_registrations(self) -> None:
        before = set(registry.all_ops())

        @registry.register("test_ns.reflective")
        def fn() -> None:
            pass

        after = set(registry.all_ops())
        self.assertEqual(after - before, {"test_ns.reflective"})


class TestDescribe(_RegistryIsolated):

    def test_describe_empty_returns_all_ops(self) -> None:
        @registry.register("test_ns.alpha")
        def a() -> int:
            return 0

        @registry.register("test_ns.beta")
        def b() -> int:
            return 0

        all_d = registry.describe("")
        self.assertIn("test_ns.alpha", all_d)
        self.assertIn("test_ns.beta", all_d)
        # each entry is itself a description dict
        self.assertEqual(all_d["test_ns.alpha"]["name"], "test_ns.alpha")

    def test_describe_unknown_returns_empty(self) -> None:
        self.assertEqual(registry.describe("nonexistent.op"), {})

    def test_describe_includes_docstring(self) -> None:
        @registry.register("test_ns.doc")
        def fn() -> int:
            """One-liner docstring."""
            return 1

        self.assertEqual(registry.describe("test_ns.doc")["doc"], "One-liner docstring.")

    def test_describe_no_docstring_is_empty(self) -> None:
        @registry.register("test_ns.nodoc")
        def fn() -> int:
            return 1

        self.assertEqual(registry.describe("test_ns.nodoc")["doc"], "")

    def test_describe_parameter_default_repr(self) -> None:
        @registry.register("test_ns.default")
        def fn(x: int = 42) -> int:
            return x

        d = registry.describe("test_ns.default")
        self.assertEqual(d["parameters"]["x"]["default"], "42")

    def test_describe_parameter_no_default_is_none(self) -> None:
        @registry.register("test_ns.nodefault")
        def fn(x: int) -> int:
            return x

        d = registry.describe("test_ns.nodefault")
        self.assertIsNone(d["parameters"]["x"]["default"])

    def test_describe_return_annotation_builtin(self) -> None:
        @registry.register("test_ns.ret_builtin")
        def fn() -> dict:
            return {}

        self.assertEqual(registry.describe("test_ns.ret_builtin")["return"], "dict")

    def test_describe_return_annotation_missing_is_any(self) -> None:
        @registry.register("test_ns.ret_missing")
        def fn():
            pass

        self.assertEqual(registry.describe("test_ns.ret_missing")["return"], "Any")

    def test_describe_parameter_annotation_string_for_typing(self) -> None:
        from typing import Optional

        @registry.register("test_ns.optional_arg")
        def fn(x: Optional[str] = None) -> None:
            pass

        d = registry.describe("test_ns.optional_arg")
        # Typing constructs serialize via str() — we don't assert exact form,
        # only that something non-empty is recorded.
        self.assertTrue(d["parameters"]["x"]["annotation"])
        self.assertNotEqual(d["parameters"]["x"]["annotation"], "Any")


if __name__ == "__main__":
    unittest.main()
