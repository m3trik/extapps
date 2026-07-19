# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.bake_utils.

Unit tests run standalone (no Painter) — they verify registration and
signature contract. Integration tests open a real Painter scene and
exercise the iray-backed bake path; they are gated behind
``SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1``.
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


# A real Painter project (.spp) for the live integration tests below. No path is
# committed (public repo): set SUBSTANCE_WORKFLOW_TEST_SCENE to a local .spp to
# enable them; otherwise they skip (the file won't exist).
TEST_SCENE = os.environ.get("SUBSTANCE_WORKFLOW_TEST_SCENE", "")


class TestBakeUtilsRegistration(SubstanceWorkflowTestCase):
    """Standalone unit tests — verify the op is registered correctly."""

    def setUp(self) -> None:
        super().setUp()
        import extapps.substance_workflow.bake_utils  # noqa: F401

    def test_lighting_to_diffuse_registered(self) -> None:
        from extapps.substance_workflow import registry

        fn = registry.get("bake.lighting_to_diffuse")
        self.assertIsNotNone(fn)
        self.assertEqual(getattr(fn, "_op_name", None), "bake.lighting_to_diffuse")

    def test_lighting_to_diffuse_signature(self) -> None:
        """Every documented knob must be on the signature so agents can discover it."""
        from extapps.substance_workflow import registry

        d = registry.describe("bake.lighting_to_diffuse")
        params = d["parameters"]
        for expected in (
            "texture_set",
            "bake_resolution",
            "ao_intensity",
            "ao_secondary_rays",
            "ao_max_distance",
            "ao_min_distance",
            "ao_spread_angle",
            "ao_subsample",
            "include_curvature",
            "curvature_intensity",
            "layer_name",
            "blend_mode",
            "skip_existing_bakes",
            "save_project",
        ):
            self.assertIn(expected, params, f"missing parameter: {expected}")

    def test_lighting_to_diffuse_defaults(self) -> None:
        """Default values match the intent documented in the docstring."""
        from extapps.substance_workflow import registry

        d = registry.describe("bake.lighting_to_diffuse")
        p = d["parameters"]
        self.assertEqual(p["bake_resolution"]["default"], "1024")
        self.assertEqual(p["blend_mode"]["default"], "'Multiply'")
        self.assertEqual(p["include_curvature"]["default"], "False")
        self.assertEqual(p["save_project"]["default"], "False")


@unittest.skipUnless(
    os.environ.get("SUBSTANCE_WORKFLOW_RUN_INTEGRATION") == "1",
    "Set SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1 to run live Painter integration tests",
)
@unittest.skipUnless(
    os.path.exists(TEST_SCENE),
    f"Test scene not available: {TEST_SCENE}",
)
class TestLightingToDiffuseIntegration(SubstanceWorkflowTestCase):
    """End-to-end against the C130J Dubai demo scene.

    Launches Painter, opens ``power_cart_panel.spp``, bakes AO via iray,
    composites a multiply layer, asserts the result shape.
    """

    def test_default_bake(self) -> None:
        from extapps.substance_workflow import PainterConnection

        conn = PainterConnection()
        self.assertTrue(conn.connect(gui=False, timeout=240))
        try:
            opened = conn.invoke("project.open", path=TEST_SCENE, timeout=180)
            self.assertTrue(opened.get("open"))

            result = conn.invoke(
                "bake.lighting_to_diffuse",
                timeout=600,
                bake_resolution=512,  # smaller for test speed
                ao_secondary_rays=32,  # smaller for test speed
                include_curvature=False,
                save_project=False,
            )
            self.assertIsInstance(result, dict)
            self.assertGreater(
                len(result["texture_sets"]),
                0,
                "Expected at least one texture set to be processed.",
            )
            self.assertEqual(
                result["errors"],
                [],
                f"Unexpected errors during bake: {result['errors']}",
            )
            self.assertGreater(
                len(result["baked_maps"]),
                0,
                "No bakes recorded — AO output may have failed.",
            )
        finally:
            conn.shutdown(force=True)

    def test_curvature_variant(self) -> None:
        from extapps.substance_workflow import PainterConnection

        conn = PainterConnection()
        self.assertTrue(conn.connect(gui=False, timeout=240))
        try:
            conn.invoke("project.open", path=TEST_SCENE, timeout=180)
            result = conn.invoke(
                "bake.lighting_to_diffuse",
                timeout=900,
                bake_resolution=512,
                ao_secondary_rays=32,
                include_curvature=True,
                curvature_intensity=0.4,
                save_project=False,
            )
            self.assertEqual(
                result["errors"],
                [],
                f"Unexpected errors during curvature bake: {result['errors']}",
            )
        finally:
            conn.shutdown(force=True)


class TestLightingLayerIntensity(SubstanceWorkflowTestCase):
    """Regression: AO / Curvature Intensity must actually reach the layer stack.

    They used to be accepted by ``_add_lighting_layer`` and silently dropped,
    so the sliders had zero effect on output. These tests inject a fake
    ``substance_painter`` API (the real module only exists inside Painter) and
    assert the intensity is applied via the layer-opacity setter.
    """

    def _install_fake_painter(self, opacity_mode="method", with_opacity=True):
        """Install a fake ``substance_painter`` modeling the REAL API surface
        (verified against the installed Painter's layerstack module):
        ``insert_fill(position)`` takes no name kwarg, and opacity / naming /
        blending are METHODS on the layer node (``Node.set_opacity(opacity,
        channel)``, ``Node.set_name``, ``Node.set_blending_mode``) — there are
        no module-level setters. A fake that invents module functions would
        validate an API Painter never shipped.

        opacity_mode:
            "method"     -- Node.set_opacity(opacity, channel)   (current API)
            "layer_wide" -- Node.set_opacity(opacity)            (older builds)
        with_opacity=False omits set_opacity entirely (graceful-degrade path).
        """
        import types

        calls = {"opacity": [], "mesh_map": [], "blend": [], "names": []}

        baking = types.ModuleType("substance_painter.baking")

        class MeshMapUsage:
            AO = "AO"
            Curvature = "Curvature"

        baking.MeshMapUsage = MeshMapUsage

        textureset = types.ModuleType("substance_painter.textureset")

        class ChannelType:
            BaseColor = "BaseColor"

        class Stack:
            @staticmethod
            def from_name(name):
                return ("stack", name)

        textureset.ChannelType = ChannelType
        textureset.Stack = Stack

        layerstack = types.ModuleType("substance_painter.layerstack")

        class InsertPosition:
            @staticmethod
            def from_textureset_stack(stack):
                return ("pos", stack)

        class BlendingMode:
            Multiply = "Multiply"
            Overlay = "Overlay"

        class _Layer:
            def __init__(self):
                self.name = None
                self.uid = "uid::unnamed"

            def set_name(self, name):
                self.name = name
                self.uid = f"uid::{name}"
                calls["names"].append(name)

            def set_blending_mode(self, mode, channel=None):
                calls["blend"].append((self.name, mode, channel))

        if with_opacity:
            if opacity_mode == "method":

                def _set_opacity(self, opacity, channel=None):
                    calls["opacity"].append((self.name, channel, opacity))

            else:  # layer-wide: no channel parameter (TypeError fallback path)

                def _set_opacity(self, opacity):
                    calls["opacity"].append((self.name, None, opacity))

            _Layer.set_opacity = _set_opacity

        def insert_fill(pos):  # real signature: position only, no name kwarg
            return _Layer()

        def set_source_from_mesh_map(layer, channel, usage):
            calls["mesh_map"].append((getattr(layer, "name", layer), channel, usage))

        layerstack.InsertPosition = InsertPosition
        layerstack.BlendingMode = BlendingMode
        layerstack.insert_fill = insert_fill
        layerstack.set_source_from_mesh_map = set_source_from_mesh_map
        layerstack._Layer = _Layer  # exposed for direct-layer tests

        parent = types.ModuleType("substance_painter")
        parent.layerstack = layerstack
        parent.textureset = textureset
        parent.baking = baking

        keys = (
            "substance_painter",
            "substance_painter.layerstack",
            "substance_painter.textureset",
            "substance_painter.baking",
        )
        saved = {k: sys.modules.get(k) for k in keys}
        sys.modules["substance_painter"] = parent
        sys.modules["substance_painter.layerstack"] = layerstack
        sys.modules["substance_painter.textureset"] = textureset
        sys.modules["substance_painter.baking"] = baking

        def restore():
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

        self.addCleanup(restore)
        return calls, layerstack

    def test_add_lighting_layer_applies_both_intensities(self):
        """End-to-end: AO and curvature intensities reach the opacity setter."""
        import types

        from extapps.substance_workflow import bake_utils

        calls, _ = self._install_fake_painter()
        ts = types.SimpleNamespace(name="TS")

        uid = bake_utils._add_lighting_layer(
            ts,
            layer_name="AO",
            blend_mode="Multiply",
            intensity=0.5,
            include_curvature=True,
            curvature_intensity=0.3,
        )

        self.assertTrue(uid)
        # Both the AO and the curvature fill layer were sourced from a mesh map.
        self.assertEqual(len(calls["mesh_map"]), 2)
        applied = {name: op for (name, _ch, op) in calls["opacity"]}
        self.assertAlmostEqual(applied["AO"], 0.5)
        self.assertAlmostEqual(applied["AO (Curvature)"], 0.3)

    def test_apply_layer_intensity_partial_applies_clamped(self):
        from extapps.substance_workflow import bake_utils

        calls, layerstack = self._install_fake_painter()
        layer = layerstack.insert_fill(None)
        layer.set_name("L")
        bake_utils._apply_layer_intensity(layer, "BaseColor", 0.25)

        self.assertEqual(len(calls["opacity"]), 1)
        name, channel, opacity = calls["opacity"][0]
        self.assertEqual((name, channel), ("L", "BaseColor"))
        self.assertAlmostEqual(opacity, 0.25)

    def test_apply_layer_intensity_neutral_is_noop(self):
        """intensity == 1.0 is Painter's default opacity: no setter call."""
        from extapps.substance_workflow import bake_utils

        calls, layerstack = self._install_fake_painter()
        bake_utils._apply_layer_intensity(
            layerstack.insert_fill(None), "BaseColor", 1.0
        )
        self.assertEqual(calls["opacity"], [])

    def test_apply_layer_intensity_above_one_saturates(self):
        """intensity > 1.0 clamps to full opacity (a no-op), never crashes."""
        from extapps.substance_workflow import bake_utils

        calls, layerstack = self._install_fake_painter()
        bake_utils._apply_layer_intensity(
            layerstack.insert_fill(None), "BaseColor", 4.0
        )
        self.assertEqual(calls["opacity"], [])

    def test_apply_layer_intensity_layer_wide_setter_fallback(self):
        """An older layer-wide set_opacity(opacity) is reached via the
        TypeError fallback when the channel arg is rejected."""
        from extapps.substance_workflow import bake_utils

        calls, layerstack = self._install_fake_painter(opacity_mode="layer_wide")
        layer = layerstack.insert_fill(None)
        layer.set_name("L")
        bake_utils._apply_layer_intensity(layer, "BaseColor", 0.4)

        self.assertEqual(len(calls["opacity"]), 1)
        self.assertEqual(calls["opacity"][0][0], "L")
        self.assertAlmostEqual(calls["opacity"][0][-1], 0.4)

    def test_apply_layer_intensity_missing_setter_is_graceful(self):
        """No set_opacity on this Painter build: warn, don't crash, no-op."""
        from extapps.substance_workflow import bake_utils

        calls, layerstack = self._install_fake_painter(with_opacity=False)
        layer = layerstack.insert_fill(None)
        layer.set_name("L")
        bake_utils._apply_layer_intensity(layer, "BaseColor", 0.5)
        self.assertEqual(calls["opacity"], [])


if __name__ == "__main__":
    unittest.main()
