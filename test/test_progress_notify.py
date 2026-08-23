# !/usr/bin/python
# coding=utf-8
"""Tests for the shared photogrammetry progress-notify shim.

``_notify`` was reimplemented verbatim in five engines. Unifying it onto
:class:`ProgressNotifyMixin` is only safe if the contract is pinned, so this
module locks the four properties the five copies agreed on — no-callback,
pass-through fraction (no clamping), float coercion, and a raising callback
never escaping — and then asserts every engine actually resolves to the one
implementation.
"""

import io
import unittest
from contextlib import redirect_stderr

from extapps.photogrammetry._progress_notify import ProgressNotifyMixin


class _Engine(ProgressNotifyMixin):
    """Minimal host: the mixin's only requirement is ``self.progress``."""

    def __init__(self, progress=None):
        self.progress = progress


class ProgressNotifyContractTest(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def _engine(self, cb=None):
        return _Engine(cb if cb is not None else self.calls.append)

    def test_forwards_stage_and_fraction(self):
        eng = _Engine(lambda s, f: self.calls.append((s, f)))
        eng._notify("align_photos", 0.25)
        self.assertEqual(self.calls, [("align_photos", 0.25)])

    def test_fraction_defaults_to_zero(self):
        # Every stage in every engine opens with a bare _notify("<stage>"),
        # relying on the default rather than passing 0.0.
        eng = _Engine(lambda s, f: self.calls.append((s, f)))
        eng._notify("build_model")
        self.assertEqual(self.calls, [("build_model", 0.0)])

    def test_none_callback_is_a_silent_no_op(self):
        """progress=None is the headless default — not an error path."""
        eng = _Engine(None)
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertIsNone(eng._notify("export_model", 0.5))
        self.assertEqual(err.getvalue(), "")

    def test_missing_progress_attribute_is_also_a_no_op(self):
        """The mixin declares progress=None at class level, so a host that
        never assigned it still no-ops instead of raising AttributeError."""

        class _Bare(ProgressNotifyMixin):
            pass

        self.assertIsNone(_Bare()._notify("stage"))

    def test_out_of_range_fractions_pass_through_unclamped(self):
        """Deliberate: the engines have no total to normalize against, so a
        value outside 0..1 is the caller's to interpret. Clamping here would
        silently rewrite it."""
        eng = _Engine(lambda s, f: self.calls.append(f))
        for value in (-1.0, -0.0001, 0.0, 1.0, 1.5, 42.0):
            eng._notify("stage", value)
        self.assertEqual(self.calls, [-1.0, -0.0001, 0.0, 1.0, 1.5, 42.0])

    def test_fraction_is_coerced_to_float(self):
        """A callback always sees a float, never the int/str it was handed."""
        eng = _Engine(lambda s, f: self.calls.append(f))
        eng._notify("stage", 1)
        eng._notify("stage", "0.75")
        self.assertEqual(self.calls, [1.0, 0.75])
        for got in self.calls:
            self.assertIsInstance(got, float)

    def test_raising_callback_is_swallowed_and_reported(self):
        """A broken UI progress bar must not lose an hours-long bake."""

        def boom(stage, fraction):
            raise RuntimeError("ui gone")

        eng = _Engine(boom)
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertIsNone(eng._notify("refine_mesh", 0.5))
        text = err.getvalue()
        self.assertIn("progress callback raised: ui gone", text)
        self.assertIn("[_Engine]", text)  # tagged with the reporting class

    def test_unconvertible_fraction_is_swallowed_too(self):
        """float() lives inside the same guard: a non-numeric fraction is a
        caller bug of the same kind and must not kill the run either."""
        eng = _Engine(lambda s, f: self.calls.append(f))
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertIsNone(eng._notify("stage", "not-a-number"))
        self.assertEqual(self.calls, [])
        self.assertIn("progress callback raised", err.getvalue())

    def test_notify_continues_after_a_failing_call(self):
        """One bad call must not latch the shim off."""
        state = {"fail": True}

        def flaky(stage, fraction):
            if state["fail"]:
                state["fail"] = False
                raise ValueError("transient")
            self.calls.append(stage)

        eng = _Engine(flaky)
        with redirect_stderr(io.StringIO()):
            eng._notify("first")
        eng._notify("second")
        self.assertEqual(self.calls, ["second"])


class ProgressNotifyUnificationTest(unittest.TestCase):
    """Every engine resolves ``_notify`` to the one shared implementation.

    Guards the de-duplication: a re-added local copy fails here rather than
    quietly drifting from the other four again.
    """

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

    def test_all_five_engines_share_one_implementation(self):
        for cls in self._engines():
            with self.subTest(engine=cls.__name__):
                self.assertTrue(issubclass(cls, ProgressNotifyMixin))
                self.assertIs(cls._notify, ProgressNotifyMixin._notify)
                self.assertNotIn("_notify", vars(cls))

    def test_stderr_tag_still_names_the_engine(self):
        """The five copies each hardcoded their own class name in the stderr
        tag; ``type(self).__name__`` has to reproduce every one of them."""

        def boom(stage, fraction):
            raise RuntimeError("x")

        for cls in self._engines():
            with self.subTest(engine=cls.__name__):
                eng = cls.__new__(cls)  # no __init__: engines touch the disk
                eng.progress = boom
                err = io.StringIO()
                with redirect_stderr(err):
                    eng._notify("stage", 0.0)
                self.assertIn(
                    f"[{cls.__name__}] progress callback raised", err.getvalue()
                )


if __name__ == "__main__":
    unittest.main()
