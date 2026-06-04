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


if __name__ == "__main__":
    unittest.main()
