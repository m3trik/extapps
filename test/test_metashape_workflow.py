#!/usr/bin/env python
# coding=utf-8
"""Tests for the Metashape Workflow panel.

UI smoke tests cover the build-time wiring (no Metashape needed). Engine
tests run the pipeline in mock mode and assert structure of the QC
sidecar + behavior of acceptance gates. Anything requiring a live
Metashape license is out of scope here.

Run::

    pytest extapps/test/test_metashape_workflow.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

from qtpy import QtCore
from qtpy.QtWidgets import QApplication


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestMetashapeWorkflowLoads(unittest.TestCase):
    """Smoke checks against a freshly-built MetashapeWorkflow UI.

    The panel is a :class:`uitk.bridge.BridgeSlotsBase` subclass that drives the
    local ``metashape.exe`` headless (no in-process-SDK mock path) and uses the
    shared semantic preset store.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import metashape_workflow as m
        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        # Drop the window; QApplication persists for the next test.
        self.ui.deleteLater()
        self.app.processEvents()

    # ------------------------------------------------------------------

    def test_ui_builds(self) -> None:
        self.assertEqual(self.ui.objectName(), "metashape_workflow")

        from uitk.widgets.header import Header
        from uitk.widgets.footer import Footer
        self.assertIsInstance(self.ui.header, Header)
        self.assertIsInstance(self.ui.footer, Footer)

        self.assertTrue(
            bool(self.ui.windowFlags() & QtCore.Qt.FramelessWindowHint),
            "FramelessWindowHint is not set — OS frame would be visible",
        )

    def test_run_modes_populate_template_combo(self) -> None:
        labels = [self.ui.cmb000.itemText(i) for i in range(self.ui.cmb000.count())]
        self.assertEqual(
            labels, ["Full pipeline", "Align only", "Refine only", "Prep preview"]
        )

    def test_param_widgets_built_for_every_spec(self) -> None:
        """Each semantic AttributeSpec gets a widget the panel can read/write."""
        from extapps.photogrammetry.metashape_workflow import parameters as P
        for key in P.PARAMS:
            self.assertIn(
                key, self.slots._param_widgets,
                f"param widget {key!r} not built from PARAMS",
            )

    def test_param_visibility_is_dynamic_per_run_mode(self) -> None:
        """Switching the run mode shows/hides params per stage relevance —
        the panel is no longer static across modes.

        ``isHidden()`` (not ``isVisible()``) reflects the explicit setVisible
        flag independently of the unshown top-level window.
        """
        rows = self.slots._param_rows
        cmb = self.ui.cmb000

        # Set the mode explicitly each time — the combo's value persists across
        # panel instances (uitk widget-state), so we can't assume a default.
        # Full pipeline: every param row is shown.
        cmb.setCurrentIndex(cmb.findText("Full pipeline"))
        self.assertFalse(rows["depth_filter"].isHidden())
        self.assertFalse(rows["texture_size"].isHidden())

        # Align only: depth/mesh/texture + post-align knobs are irrelevant.
        cmb.setCurrentIndex(cmb.findText("Align only"))
        self.assertTrue(rows["depth_filter"].isHidden())
        self.assertTrue(rows["face_count"].isHidden())
        self.assertTrue(rows["texture_size"].isHidden())
        self.assertTrue(rows["skip_refine"].isHidden())
        self.assertTrue(rows["dedupe_cameras"].isHidden())
        self.assertTrue(rows["calibrate_colors"].isHidden())
        self.assertFalse(rows["align_downscale"].isHidden())  # align stage param
        self.assertFalse(rows["skip_curate"].isHidden())      # pre-align param

        # Refine only re-enables skip_refine (refine runs in this mode).
        cmb.setCurrentIndex(cmb.findText("Refine only"))
        self.assertFalse(rows["skip_refine"].isHidden())
        self.assertTrue(rows["depth_filter"].isHidden())

        # Prep preview (curation dry-run): only the pre-processing knobs apply.
        cmb.setCurrentIndex(cmb.findText("Prep preview"))
        self.assertFalse(rows["curate_hash_threshold"].isHidden())
        self.assertFalse(rows["preprocess_input"].isHidden())
        self.assertTrue(rows["align_downscale"].isHidden())
        self.assertTrue(rows["depth_filter"].isHidden())
        self.assertTrue(rows["min_component_size"].isHidden())

        # Back to Full pipeline: everything visible again.
        cmb.setCurrentIndex(cmb.findText("Full pipeline"))
        self.assertFalse(rows["depth_filter"].isHidden())
        self.assertFalse(rows["texture_size"].isHidden())

    def test_param_sections_have_dividers_that_track_mode(self) -> None:
        """Category dividers (uitk Separator) group the params, and a divider
        hides when its whole section is hidden for the active run mode."""
        seps = self.slots._section_separators
        self.assertIn("Input Pre-processing", seps)
        self.assertIn("Alignment", seps)
        self.assertIn("Mesh Cleanup", seps)
        cmb = self.ui.cmb000

        cmb.setCurrentIndex(cmb.findText("Full pipeline"))
        self.assertFalse(seps["Input Pre-processing"].isHidden())
        self.assertFalse(seps["Alignment"].isHidden())
        self.assertFalse(seps["Mesh Cleanup"].isHidden())

        # Align only: pre-processing + the alignment-quality levers apply (their
        # dividers stay), but Mesh Cleanup is a post-build stage that never runs
        # -> its whole section, and thus its divider, hides.
        cmb.setCurrentIndex(cmb.findText("Align only"))
        self.assertFalse(seps["Input Pre-processing"].isHidden())
        self.assertFalse(seps["Alignment"].isHidden())
        self.assertTrue(seps["Mesh Cleanup"].isHidden())

    def test_preprocessing_master_toggle_collapses_knobs(self) -> None:
        """The Input Pre-processing master toggle (preprocess_input) collapses
        its knobs when off — only the toggle + section divider stay — and
        restores them when on. (The section leads the panel, order of ops.)"""
        from uitk.bridge.spec import set_value
        rows = self.slots._param_rows
        seps = self.slots._section_separators
        cmb = self.ui.cmb000
        cmb.setCurrentIndex(cmb.findText("Full pipeline"))

        # On (default): the knobs are visible.
        self.assertFalse(rows["curate_hash_threshold"].isHidden())
        self.assertFalse(rows["equalize_strength"].isHidden())
        self.assertFalse(rows["preprocess_input"].isHidden())

        # Off: the knobs collapse, but the master toggle + its divider remain
        # (so the stage can be re-enabled).
        set_value(self.slots._param_widgets["preprocess_input"], False)
        self.assertTrue(rows["curate_hash_threshold"].isHidden())
        self.assertTrue(rows["skip_equalize"].isHidden())
        self.assertFalse(rows["preprocess_input"].isHidden())
        self.assertFalse(seps["Input Pre-processing"].isHidden())

        # On again: the knobs are restored.
        set_value(self.slots._param_widgets["preprocess_input"], True)
        self.assertFalse(rows["curate_hash_threshold"].isHidden())

    def test_semantic_preset_mode_active(self) -> None:
        # The panel uses the shared semantic PresetStore (not widget-state),
        # so the shipped built-in run-template shows in the preset combo.
        self.assertTrue(self.slots._semantic_presets)
        self.assertIsNotNone(self.slots._preset_mgr)
        self.assertIn("specular_metal", self.slots._preset_mgr.list())

    def test_builtin_preset_loads_into_param_widgets(self) -> None:
        from uitk.bridge.spec import read_value
        self.slots._preset_mgr.load("specular_metal")
        w = self.slots._param_widgets
        self.assertEqual(read_value(w["depth_filter"]), "moderate")
        self.assertEqual(read_value(w["face_count"]), "high")
        self.assertTrue(read_value(w["mask_background"]))

    def test_quality_presets_load_into_param_widgets(self) -> None:
        """preview / default / high each apply their explicit knobs to the
        widgets (the `quality` key is ignored — no widget for it)."""
        from uitk.bridge.spec import read_value
        w = self.slots._param_widgets

        self.slots._preset_mgr.load("preview")
        self.assertEqual(read_value(w["align_downscale"]), 4)
        self.assertEqual(read_value(w["face_count"]), "low")
        self.assertEqual(read_value(w["texture_size"]), "2048")

        self.slots._preset_mgr.load("high")
        self.assertEqual(read_value(w["align_downscale"]), 1)
        self.assertEqual(read_value(w["depth_downscale"]), 1)
        self.assertEqual(read_value(w["face_count"]), "high")

    def test_missing_exe_reports_instead_of_mocking(self) -> None:
        """No silent mock fallback: with no exe, b000 logs + leaves UI usable."""
        self.slots.bridge.is_available = lambda: False
        self.slots._name_edit.setText("proj")
        try:
            self.ui.b000.click()
        except Exception as exc:  # noqa: BLE001
            self.fail(f"b000 raised with missing exe: {type(exc).__name__}: {exc}")
        self.assertTrue(self.ui.b000.isEnabled())

    def test_run_empty_inputs_bails_gracefully(self) -> None:
        try:
            self.ui.b000.click()
        except Exception as exc:  # noqa: BLE001
            self.fail(f"b000 click raised: {type(exc).__name__}: {exc}")
        self.assertTrue(
            self.ui.b000.isEnabled(),
            "Run Workflow button left disabled after empty-input bail",
        )


class TestParametersReferencedKeys(unittest.TestCase):
    """``parameters.referenced_keys(mode)`` is the relevance SSoT the panel +
    bridge base consume (the run-mode analogue of the DCC bridges' placeholder
    scan). Pinned at the data layer, not just via the integrated UI test."""

    def _P(self):
        from extapps.photogrammetry.metashape_workflow import parameters as P
        return P

    def test_full_pipeline_returns_all_keys(self) -> None:
        P = self._P()
        self.assertEqual(P.referenced_keys(""), set(P.PARAMS))

    def test_align_mode_drops_post_align_stage_knobs(self) -> None:
        P = self._P()
        keys = P.referenced_keys("align")
        for hidden in ("depth_downscale", "depth_filter", "face_count",
                       "texture_size", "dedupe_cameras", "skip_refine",
                       "calibrate_colors",
                       # mesh cleanup is a post-build stage -> full pipeline only
                       "min_component_size", "smooth_strength", "close_holes"):
            self.assertNotIn(hidden, keys, f"{hidden} should not apply in align-only")
        for shown in ("align_downscale", "skip_curate", "skip_equalize",
                      "mask_background", "gate_mode", "save_project",
                      # alignment-quality levers (pre-align triage + matchPhotos)
                      "triage_quality", "generic_preselection",
                      "keypoint_limit", "tiepoint_limit",
                      # input pre-processing runs before align -> applies here too
                      "curate_hash_threshold", "curate_sharpness_percentile",
                      "curate_min_sharpness_frac", "keep_per_cluster",
                      "equalize_strength", "equalize_reference"):
            self.assertIn(shown, keys, f"{shown} should apply in align-only")

    def test_refine_mode_adds_skip_refine(self) -> None:
        P = self._P()
        keys = P.referenced_keys("refine")
        self.assertIn("skip_refine", keys)
        self.assertNotIn("depth_filter", keys)

    def test_unknown_mode_falls_back_to_all_keys(self) -> None:
        P = self._P()
        self.assertEqual(P.referenced_keys("bogus"), set(P.PARAMS))

    def test_preprocessing_values_render_to_cli_flags(self) -> None:
        P = self._P()
        argv = P.to_argv({
            "curate_hash_threshold": 0,          # 0 = disable dedup; must still emit
            "curate_sharpness_percentile": 12.5,
            "curate_min_sharpness_frac": 0.2,
            "keep_per_cluster": 2,
            "equalize_strength": 0.8,
            "equalize_reference": "global",
        })
        self.assertEqual(argv[argv.index("--curate-hash-threshold") + 1], "0")
        self.assertEqual(argv[argv.index("--keep-per-cluster") + 1], "2")
        self.assertEqual(argv[argv.index("--equalize-reference") + 1], "global")
        self.assertIn("--curate-sharpness-percentile", argv)
        self.assertIn("--curate-min-sharpness-frac", argv)
        self.assertIn("--equalize-strength", argv)

    def test_alignment_and_cleanup_values_render_to_cli_flags(self) -> None:
        """The newly-exposed Metashape levers map to their run_combined flags:
        value flags always emit; generic_preselection is a BooleanOptionalAction
        pair (--flag / --no-flag), so unchecking it can override the on-by-default
        runner baseline."""
        P = self._P()
        argv = P.to_argv({
            "triage_quality": 0.3,
            "generic_preselection": True,
            "keypoint_limit": 60000,
            "tiepoint_limit": 20000,
            "min_component_size": 25000,
            "smooth_strength": 1,
            "close_holes": 10,
        })
        self.assertEqual(argv[argv.index("--triage-quality") + 1], "0.3")
        self.assertEqual(argv[argv.index("--keypoint-limit") + 1], "60000")
        self.assertEqual(argv[argv.index("--tiepoint-limit") + 1], "20000")
        self.assertEqual(argv[argv.index("--clean-min-component") + 1], "25000")
        self.assertEqual(argv[argv.index("--smooth-strength") + 1], "1")
        self.assertEqual(argv[argv.index("--close-holes") + 1], "10")
        self.assertIn("--generic-preselection", argv)
        # bool flag: falsey emits the explicit --no- form (the runner default is
        # ON, so omission could never turn it off)
        off = P.to_argv({"generic_preselection": False})
        self.assertNotIn("--generic-preselection", off)
        self.assertIn("--no-generic-preselection", off)

    def test_preprocessing_section_leads_param_order(self) -> None:
        """Input pre-processing runs first in the pipeline, so it leads the
        panel (order of operations): the master toggle is the first param and
        every pre-processing key precedes the engine-specific ones."""
        from extapps.photogrammetry._shared_params import PREPROCESSING_KEYS
        P = self._P()
        keys = list(P.PARAMS)
        self.assertEqual(keys[0], "preprocess_input")
        last_pre = max(keys.index(k) for k in PREPROCESSING_KEYS)
        first_engine = min(
            keys.index(k) for k in ("align_downscale", "depth_filter", "face_count")
        )
        self.assertLess(last_pre, first_engine,
                        "pre-processing must precede the engine params")

    def test_preprocessing_master_off_skips_whole_stage(self) -> None:
        """preprocess_input=False renders the wholesale skip (both stages) and
        omits the now-moot knob flags; True renders the knobs and emits no
        skip (with the per-stage skips left off)."""
        P = self._P()
        off = P.to_argv({"preprocess_input": False,
                         "curate_hash_threshold": 7, "equalize_strength": 0.9})
        self.assertIn("--skip-curate", off)
        self.assertIn("--skip-equalize", off)
        self.assertNotIn("--curate-hash-threshold", off)
        self.assertNotIn("--equalize-strength", off)
        on = P.to_argv({"preprocess_input": True,
                        "curate_hash_threshold": 7, "equalize_strength": 0.9})
        self.assertEqual(on[on.index("--curate-hash-threshold") + 1], "7")
        self.assertNotIn("--skip-curate", on)


class TestBuiltinPresets(unittest.TestCase):
    """The shipped quality presets (preview/high/specular_metal) are available,
    well-formed, and consistent between the panel store and the CLI get_preset."""

    def _profile(self):
        from extapps.photogrammetry import profile
        return profile

    def test_quality_presets_available_and_well_formed(self) -> None:
        P = self._profile()
        listed = set(P.preset_store("metashape").list())
        self.assertTrue(
            {"preview", "high", "specular_metal"} <= listed,
            f"missing built-in presets; got {sorted(listed)}",
        )
        prev = P.get_preset("preview", "metashape")
        self.assertEqual(prev.get("align_downscale"), 4)
        self.assertEqual(prev.get("face_count"), "low")
        self.assertNotIn("_comment", prev, "_comment must be stripped by get_preset")
        hq = P.get_preset("high", "metashape")
        self.assertEqual(hq.get("depth_downscale"), 1)
        self.assertEqual(hq.get("face_count"), "high")

    def test_alignment_presets_carry_match_levers(self) -> None:
        """The hard-capture levers we just exposed are baked into the presets
        that need them (otherwise exposing them buys nothing)."""
        P = self._profile()
        spec = P.get_preset("specular_metal", "metashape")
        # Featureless metal: generic preselection + a raised tie cloud + a light
        # smooth (NOT a component-removal crank, per the tuning findings).
        self.assertTrue(spec.get("generic_preselection"))
        self.assertEqual(spec.get("tiepoint_limit"), 20000)
        self.assertEqual(spec.get("smooth_strength"), 1)
        self.assertNotIn("min_component_size", spec,
                         "specular_metal must NOT crank component removal")
        # High quality: denser tie cloud, but generic preselection left off.
        hq = P.get_preset("high", "metashape")
        self.assertEqual(hq.get("tiepoint_limit"), 20000)
        self.assertNotIn("generic_preselection", hq)

    def test_default_keyword_is_cli_noop_and_not_shipped(self) -> None:
        P = self._profile()
        # "default" (like "none") is a recognized no-op on the CLI -> plain
        # defaults; there is no shipped 'default' preset (the panel's Reset to
        # Defaults button restores the baseline instead).
        self.assertEqual(P.get_preset("default", "metashape"), {})
        self.assertNotIn("default", P.preset_store("metashape").list())


class TestMetashapeWorkflowEngine(unittest.TestCase):
    """Mock-mode engine tests — exercise the pipeline without an SDK."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_engine_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _new_workflow(self, **kwargs):
        from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow
        return MetashapeWorkflow(
            project_path=self.tmp, name="test_run", **kwargs
        )

    def test_full_pipeline_runs_mock_mode(self) -> None:
        mp = self._new_workflow()
        self.assertTrue(mp.mock_mode, "Test env should not have a real license")
        mp.create_chunk("Test")
        mp.add_images(["a.jpg", "b.jpg", "c.jpg"])
        mp.triage_images(quality_threshold=0.4)
        mp.align_photos(downscale=2)
        mp.refine_alignment()
        mp.generate_depth_maps()
        mp.build_model()
        mp.build_texture()
        mp.save_project()
        mp.export_model()
        mp.export_qc()
        sidecar_path = mp.finalize_run(success=True)

        self.assertTrue(os.path.exists(sidecar_path), "QC sidecar not written")
        with open(sidecar_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        expected_stages = {
            "add_images", "triage", "align", "refine_alignment",
            "depth", "model", "texture", "save", "export", "report",
        }
        self.assertTrue(
            expected_stages.issubset(data["stages"].keys()),
            f"Missing stages: {expected_stages - data['stages'].keys()}",
        )
        for stage in expected_stages:
            self.assertIn("duration_sec", data["stages"][stage])
        self.assertTrue(data["success"])
        self.assertIn("metashape_version", data)
        self.assertIn("mock_mode", data)
        self.assertTrue(data["mock_mode"])

    def test_failure_path_finalizes_qc_with_success_false(self) -> None:
        mp = self._new_workflow()
        mp.create_chunk("X")
        sidecar = mp.finalize_run(success=False)
        with open(sidecar, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertFalse(data["success"])
        self.assertIn("total_duration_sec", data)

    def test_gate_warn_mode_records_warnings_and_continues(self) -> None:
        mp = self._new_workflow(gate_mode="warn")
        passed = mp._evaluate_gate(
            "align",
            {"aligned_pct": 50.0, "rms_reproj_px": 2.0, "tie_point_count": 10},
        )
        self.assertFalse(passed)
        gate_log = mp.qc.data["gates"]["align"]
        self.assertFalse(gate_log["passed"])
        self.assertTrue(any("aligned_pct" in w for w in gate_log["warnings"]))
        self.assertTrue(any("rms_reproj_px" in w for w in gate_log["warnings"]))

    def test_gate_halt_mode_raises_on_failure(self) -> None:
        from extapps.photogrammetry.metashape_workflow import GateError
        mp = self._new_workflow(gate_mode="halt")
        with self.assertRaises(GateError):
            mp._evaluate_gate("align", {"aligned_pct": 10.0, "rms_reproj_px": 5.0})

    def test_gate_pass_when_metrics_satisfy_thresholds(self) -> None:
        mp = self._new_workflow()
        ok = mp._evaluate_gate(
            "align",
            {"aligned_pct": 95.0, "rms_reproj_px": 0.3, "tie_point_count": 50000},
        )
        self.assertTrue(ok)
        self.assertTrue(mp.qc.data["gates"]["align"]["passed"])

    def test_gate_skips_when_metric_unmeasured(self) -> None:
        mp = self._new_workflow()
        ok = mp._evaluate_gate("texture", {"coverage_pct": None})
        # Missing metric → warned-but-passed (no real failure to act on).
        self.assertTrue(ok)
        warnings = mp.qc.data["gates"]["texture"]["warnings"]
        self.assertTrue(any("not measured" in w for w in warnings))

    def test_custom_gate_thresholds_override_defaults(self) -> None:
        mp = self._new_workflow(gates={"align": {"min_aligned_pct": 99.0}})
        passed = mp._evaluate_gate(
            "align", {"aligned_pct": 95.0, "rms_reproj_px": 0.3}
        )
        self.assertFalse(passed, "custom 99% floor should reject 95%")


class TestMetashapeWorkflowPhase2(unittest.TestCase):
    """Mock-mode tests for Phase 2 engine additions."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_phase2_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _new_workflow(self, **kwargs):
        from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow
        return MetashapeWorkflow(
            project_path=self.tmp, name="phase2", **kwargs
        )

    def test_full_phase2_pipeline_runs_mock_mode(self) -> None:
        mp = self._new_workflow()
        mp.create_chunk("P2")
        mp.add_images(["a.jpg", "b.jpg"])
        mp.generate_masks(source_dir=self.tmp)  # rembg likely unavailable → noop
        mp.triage_images()
        mp.align_photos_with_retry()
        mp.refine_alignment()
        mp.dedupe_cameras_by_pose()
        mp.calibrate_colors()
        mp.generate_depth_maps()
        mp.build_model()
        mp.clean_mesh()
        mp.reduce_overlap()
        mp.build_texture()
        mp.save_project()
        mp.export_model()
        mp.export_qc()
        sidecar = mp.finalize_run(success=True)
        with open(sidecar) as f:
            data = json.load(f)
        expected = {
            "generate_masks", "triage", "align", "refine_alignment",
            "dedupe_cameras", "calibrate_colors", "depth", "model",
            "clean_mesh", "reduce_overlap", "texture", "save", "export", "report",
        }
        missing = expected - data["stages"].keys()
        self.assertFalse(missing, f"Missing Phase 2 stages: {missing}")
        self.assertTrue(data["success"])

    def test_align_retry_skipped_when_already_above_floor(self) -> None:
        """Mock-mode returns immediately from align_photos; the retry
        branch is unreachable. This just confirms the surface is callable."""
        mp = self._new_workflow()
        mp.create_chunk("ar")
        mp.add_images(["x.jpg"])
        mp.align_photos_with_retry(min_aligned_pct=99.0)
        # No retry stage should be recorded in mock mode.
        self.assertNotIn("align_retry", mp.qc.data["stages"])

    def test_generate_masks_records_stage_even_when_rembg_missing(self) -> None:
        mp = self._new_workflow()
        mp.create_chunk("mg")
        mp.generate_masks(source_dir=self.tmp)
        self.assertIn("generate_masks", mp.qc.data["stages"])
        stage = mp.qc.data["stages"]["generate_masks"]
        self.assertEqual(stage["source_dir"], self.tmp)
        self.assertIn("model", stage)

    def test_camera_quality_reads_metadata_without_get(self) -> None:
        """Regression: ``cam.meta`` is a ``Metashape.MetaData`` — subscriptable
        but with **no** ``.get()`` (calling it raised AttributeError, which
        silently disabled dedupe_cameras_by_pose). ``_camera_quality`` must read
        via ``[]`` and fall back to *default* on a missing key."""
        from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow

        class _Meta:  # mimics Metashape.MetaData: [] works, .get does NOT exist
            def __init__(self, d):
                self._d = d

            def __getitem__(self, k):
                return self._d[k]  # raises KeyError when absent

        class _Cam:
            def __init__(self, q=None):
                self.meta = _Meta({"Image/quality": q} if q is not None else {})

        self.assertFalse(hasattr(_Meta({}), "get"))  # guard: the fake has no .get
        self.assertAlmostEqual(MetashapeWorkflow._camera_quality(_Cam("0.75")), 0.75)
        self.assertIsNone(MetashapeWorkflow._camera_quality(_Cam()))  # missing -> default
        self.assertEqual(MetashapeWorkflow._camera_quality(_Cam(), 1.0), 1.0)

    def test_save_project_defaults_off(self) -> None:
        """--save-project must default OFF (deliverables only, no reopenable
        .psx); only an explicit opt-in enables it."""
        from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow
        self.assertFalse(MetashapeWorkflow(project_path=self.tmp, name="d").save_project_enabled)
        self.assertTrue(
            MetashapeWorkflow(project_path=self.tmp, name="d", save_project=True).save_project_enabled
        )


class TestMetashapeWorkflowPhase3(unittest.TestCase):
    """Phase 3: multi-dir intake, exposure equalization, PyMeshLab polish."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_phase3_")
        self.src_a = os.path.join(self.tmp, "session_a")
        self.src_b = os.path.join(self.tmp, "session_b")
        os.makedirs(self.src_a)
        os.makedirs(self.src_b)
        # Tiny placeholder files so add_image_dirs has *something* to find
        # in non-mock mode. (Mock mode short-circuits before listing.)
        for d in (self.src_a, self.src_b):
            for name in ("a.jpg", "b.jpg"):
                open(os.path.join(d, name), "w").close()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _new_workflow(self, **kwargs):
        from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow
        return MetashapeWorkflow(
            project_path=self.tmp, name="phase3", **kwargs
        )

    def test_add_image_dirs_records_per_dir_counts(self) -> None:
        mp = self._new_workflow()
        mp.create_chunk("p3")
        mp.add_image_dirs([self.src_a, self.src_b])
        stage = mp.qc.data["stages"]["add_image_dirs"]
        self.assertEqual(stage["dirs"], [self.src_a, self.src_b])
        # mock mode records dirs even if it doesn't enumerate files
        self.assertIn("per_dir", stage)

    def test_equalize_exposures_falls_back_when_cv2_missing(self) -> None:
        # cv2 is in the project .venv; this test confirms the stage is
        # recorded and the source-dir fallback returns. When cv2 is
        # missing, the workflow returns source_dirs unchanged.
        mp = self._new_workflow()
        out = mp.equalize_exposures([self.src_a, self.src_b])
        self.assertEqual(len(out), 2)
        self.assertIn("equalize_exposures", mp.qc.data["stages"])

    def test_curate_input_set_records_before_after(self) -> None:
        mp = self._new_workflow()
        # session dirs from setUp already exist with two placeholder files
        # each; cv2 can't read them as images so the curator records zero
        # kept, but the stage payload must still be present.
        result = mp.curate_input_set([self.src_a, self.src_b])
        stage = mp.qc.data["stages"]["curate_input_set"]
        self.assertEqual(stage["source_dirs"], [self.src_a, self.src_b])
        self.assertIn("before", stage)
        self.assertIn("after", stage)
        self.assertIn("output_dirs", stage)
        # Returns a list (curator's output dirs, or source_dirs on fallback).
        self.assertIsInstance(result, list)

    def test_curate_input_set_warns_on_overcuration(self) -> None:
        """Aggressive dedup that strips most frames must raise a QC warning so
        silent overlap loss (the parallax SfM needs) can't pass unnoticed."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("cv2/numpy not available")
        src = os.path.join(self.tmp, "burst")
        os.makedirs(src)
        # 12 near-identical real frames -> dedup collapses to one cluster.
        base = np.full((64, 64, 3), 120, np.uint8)
        base[20:40, 20:40] = 200
        for i in range(12):
            cv2.imwrite(os.path.join(src, f"f_{i:02d}.jpg"), base)
        mp = self._new_workflow()
        mp.curate_input_set([src], hash_threshold=64, keep_per_cluster=1)
        stage = mp.qc.data["stages"]["curate_input_set"]
        self.assertGreaterEqual(stage["removed_pct"], 30.0)
        self.assertTrue(
            any("curation removed" in w for w in mp.qc.data["warnings"]),
            f"expected over-curation warning, got {mp.qc.data['warnings']}",
        )

    def test_curate_input_set_records_fallback_when_unavailable(self) -> None:
        """If pythontk or cv2 is missing, the stage payload must mark the
        fallback explicitly rather than silently returning the inputs as
        though curation happened."""
        import sys
        from unittest import mock as umock
        mp = self._new_workflow()
        # Simulate ImageCurator import failure deterministically.
        with umock.patch.dict(sys.modules, {"pythontk": umock.MagicMock(
                spec_set=["ImageCurator"], ImageCurator=property(
                    lambda self_: (_ for _ in ()).throw(ImportError("synthetic"))
                ))}):
            # An ImportError on `from pythontk import ImageCurator` would
            # really require the module to lack the attribute; we can't
            # truly simulate that without removing pythontk. Instead,
            # directly call the engine with cv2 force-disabled via patching
            # is_available.
            pass
        # Simpler path: patch ImageCurator.is_available to return False
        # and confirm the engine records the cv2_missing fallback.
        try:
            from pythontk import ImageCurator
        except ImportError:
            self.skipTest("pythontk not importable")
        with umock.patch.object(ImageCurator, "is_available", return_value=False):
            result = mp.curate_input_set([self.src_a, self.src_b])
        stage = mp.qc.data["stages"]["curate_input_set"]
        self.assertEqual(stage.get("fallback"), "cv2_missing")
        # On fallback we return source_dirs unchanged — no false "after" claim.
        self.assertEqual(result, [self.src_a, self.src_b])
        self.assertNotIn("before", stage,
                         "fallback path should not log a before/after that "
                         "implies curation happened")

    def test_clean_mesh_advanced_unavailable_is_noop(self) -> None:
        mp = self._new_workflow()
        result = mp.clean_mesh_advanced(
            exported_model_path=os.path.join(self.tmp, "missing.obj")
        )
        # When pymeshlab is missing OR the input doesn't exist, returns
        # None; in either case the stage is logged for diagnostic value.
        self.assertIsNone(result)
        self.assertIn("clean_mesh_advanced", mp.qc.data["stages"])


class TestMetashapePanelDispatch(unittest.TestCase):
    """b000 assembles ``run_combined`` argv from the inputs + active preset +
    run mode and hands it to the runner — without launching a real process."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import metashape_workflow as m
        self.tmp = tempfile.mkdtemp(prefix="mw_dispatch_")
        self.frames = os.path.join(self.tmp, "frames")
        os.makedirs(self.frames)
        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)

        # Capture the dispatched argv; never launch a real metashape.exe.
        self.captured: dict = {}
        self.slots.bridge.is_available = lambda: True
        self.slots.bridge.is_running = lambda: False

        def fake_start(argv, on_line=None, on_done=None, cwd=None):
            self.captured["argv"] = list(argv)
            self.captured["cwd"] = cwd

        self.slots.bridge.start = fake_start

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _set_inputs(self, name: str = "proj") -> None:
        self.slots._name_edit.setText(name)
        self.slots._frames_edit.setText(self.frames)
        self.slots._output_dir_edit.setText(self.tmp)

    def test_argv_includes_name_frames_output(self) -> None:
        self._set_inputs()
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch to the runner")
        self.assertEqual(argv[argv.index("--name") + 1], "proj")
        self.assertEqual(argv[argv.index("--frames-dir") + 1], self.frames)
        self.assertEqual(argv[argv.index("--output-root") + 1], self.tmp)

    def test_launch_captures_output_dir_for_open_action(self) -> None:
        """b000 records <output-root>/<name> at launch so 'Open Output Folder'
        targets the run that actually ran, even if the fields change after."""
        self._set_inputs()
        self.ui.b000.click()
        self.assertEqual(
            self.slots._last_output_dir, os.path.join(self.tmp, "proj")
        )
        # Editing the name afterward must not move the captured path.
        self.slots._name_edit.setText("renamed")
        self.assertEqual(
            self.slots._last_output_dir, os.path.join(self.tmp, "proj")
        )

    def test_success_logs_clickable_output_link(self) -> None:
        """On success the completion message embeds a clickable ``action://open``
        link to the output dir (the log pane is a QTextBrowser with openLinks
        off + anchorClicked wired to the base's open handler), not plain text —
        so a click reveals the folder. The link round-trips back to the dir."""
        import re
        from unittest import mock as umock
        from urllib.parse import parse_qs, urlparse

        self._set_inputs()
        self.ui.b000.click()  # captures _last_output_dir at launch
        with umock.patch.object(self.slots.bridge.logger, "info") as info:
            self.slots._on_run_done(0)
        msg = info.call_args[0][0]
        match = re.search(r'href="(action://[^"]+)"', msg)
        self.assertIsNotNone(match, f"no action:// link in completion msg: {msg}")
        url = urlparse(match.group(1))
        self.assertEqual(url.netloc, "open")
        self.assertEqual(
            parse_qs(url.query)["path"][0], os.path.join(self.tmp, "proj")
        )

    def test_active_preset_values_flow_into_argv(self) -> None:
        self.slots._preset_mgr.load("specular_metal")
        self._set_inputs()
        self.ui.b000.click()
        argv = self.captured["argv"]
        self.assertEqual(argv[argv.index("--depth-filter") + 1], "moderate")
        self.assertEqual(argv[argv.index("--face-count") + 1], "high")
        self.assertIn("--use-masks", argv)  # mask_background -> store_true flag

    def test_align_only_mode_adds_stop_after(self) -> None:
        self._set_inputs()
        idx = self.ui.cmb000.findText("Align only")
        self.ui.cmb000.setCurrentIndex(idx)
        self.ui.b000.click()
        argv = self.captured["argv"]
        self.assertEqual(argv[argv.index("--stop-after") + 1], "align")

    def test_prep_preview_mode_adds_curate_preview(self) -> None:
        self._set_inputs()
        idx = self.ui.cmb000.findText("Prep preview")
        self.ui.cmb000.setCurrentIndex(idx)
        self.ui.b000.click()
        argv = self.captured["argv"]
        self.assertIn("--curate-preview", argv)
        self.assertNotIn("--stop-after", argv)

    def test_missing_frames_dir_does_not_dispatch(self) -> None:
        self.slots._name_edit.setText("proj")
        self.slots._frames_edit.setText(os.path.join(self.tmp, "does_not_exist"))
        self.ui.b000.click()
        self.assertNotIn("argv", self.captured)
        self.assertTrue(self.ui.b000.isEnabled())


class _FakeProc:
    """Stand-in for the runner's QProcess, exercising its completion callbacks
    without spawning a real metashape.exe (the actual launch + bake is a
    desktop-only verification step, like the rest of this package)."""

    def __init__(self, out: bytes = b"", error: str = "process error"):
        self._out = out
        self._error = error

    def readAllStandardOutput(self) -> bytes:
        out, self._out = self._out, b""
        return out

    def errorString(self) -> str:
        return self._error


class TestMetashapeRunnerCallbacks(unittest.TestCase):
    """Runner completion/error wiring: exit code passthrough, streamed-output
    flush, and the single-fire guard (a stray ``finished`` after an error, or a
    double ``finished``, must not call ``on_done`` twice)."""

    def _runner(self, proc):
        from extapps.photogrammetry.metashape_workflow._metashape_runner import (
            MetashapeRunner,
        )
        r = MetashapeRunner.__new__(MetashapeRunner)  # skip exe discovery
        r._proc = proc
        self.lines: list = []
        self.codes: list = []
        r._on_line = self.lines.append
        r._on_done = self.codes.append
        return r

    def test_finished_flushes_output_and_reports_int_code_once(self) -> None:
        r = self._runner(_FakeProc(b"hello-from-runner\n"))
        r._on_finished(0)
        self.assertEqual(self.codes, [0])
        self.assertIn("hello-from-runner", "".join(self.lines))
        r._on_finished(0)  # a stray second finished must not double-fire
        self.assertEqual(self.codes, [0])

    def test_nonzero_exit_propagates(self) -> None:
        r = self._runner(_FakeProc(b""))
        r._on_finished(3)
        self.assertEqual(self.codes, [3])

    def test_error_reports_minus_one_and_suppresses_later_finished(self) -> None:
        r = self._runner(_FakeProc(b"", error="FailedToStart"))
        r._on_error(None)
        self.assertEqual(self.codes, [-1])
        self.assertTrue(any("process error" in ln for ln in self.lines))
        r._on_finished(0)  # late finished after error -> no second callback
        self.assertEqual(self.codes, [-1])


class TestMetashapeRunnerPrepChain(unittest.TestCase):
    """The two-stage prep chain: pre-processing can never run inside
    metashape.exe (no cv2 in its bundled Python), so the runner executes
    ``run_combined --prep-only`` under the panel's Python first and hands the
    prepared frames to the metashape.exe stage. These tests exercise the mode
    routing, argv rewrite, sentinel parsing, and the stage-1 → stage-2
    continuation without spawning real processes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def _runner(self):
        from extapps.photogrammetry._process_runner import ProcessRunner
        from extapps.photogrammetry.metashape_workflow._metashape_runner import (
            MetashapeRunner,
        )
        r = MetashapeRunner.__new__(MetashapeRunner)  # skip exe discovery
        ProcessRunner.__init__(r)
        r._prep_text = ""
        return r

    # ---------------------------------------------------------- mode routing
    def test_prep_mode_routing(self) -> None:
        from extapps.photogrammetry.metashape_workflow._metashape_runner import (
            MetashapeRunner as R,
        )
        # Preview always runs venv-only.
        self.assertEqual(R._prep_mode(["--curate-preview", "--frames-dir", "x"]),
                         "preview")
        # Default panel argv (prep on) chains.
        self.assertEqual(R._prep_mode(["--frames-dir", "x"]), "chain")
        # Master pre-processing off + no masks: nothing for a venv stage to do.
        self.assertIsNone(R._prep_mode(
            ["--frames-dir", "x", "--skip-curate", "--skip-equalize"]))
        # ...but masks alone still warrant the venv stage (rembg pre-generation).
        self.assertEqual(R._prep_mode(
            ["--frames-dir", "x", "--skip-curate", "--skip-equalize",
             "--use-masks"]), "chain")
        # No single --frames-dir source: straight to Metashape (CLI multi-capture).
        self.assertIsNone(R._prep_mode(["--input-root", "x"]))

    def test_argv_rewrite_points_at_prepped_dir_and_skips_prep(self) -> None:
        from extapps.photogrammetry.metashape_workflow._metashape_runner import (
            MetashapeRunner as R,
        )
        out = R._argv_with_prepped_source(
            ["--name", "n", "--frames-dir", "orig", "--gate-mode", "warn"],
            "prepped",
        )
        self.assertEqual(out[out.index("--frames-dir") + 1], "prepped")
        self.assertIn("--skip-curate", out)
        self.assertIn("--skip-equalize", out)
        self.assertIsNone(R._argv_with_prepped_source(["--name", "n"], "p"))

    def test_parse_prep_result_last_wins_and_tolerates_garbage(self) -> None:
        from extapps.photogrammetry.metashape_workflow._metashape_runner import (
            MetashapeRunner as R,
        )
        from extapps.photogrammetry.metashape_workflow.run_combined import (
            PREP_RESULT_PREFIX,
        )
        text = (
            "noise\n"
            f"{PREP_RESULT_PREFIX}{{\"dirs\": [\"a\"], \"masks\": 0}}\n"
            f"{PREP_RESULT_PREFIX}{{\"dirs\": [\"b\"], \"masks\": 2}}\n"
        )
        self.assertEqual(R._parse_prep_result(text)["dirs"], ["b"])
        self.assertIsNone(R._parse_prep_result(f"{PREP_RESULT_PREFIX}not json"))
        self.assertIsNone(R._parse_prep_result("no sentinel at all"))

    # ---------------------------------------------------------- continuation
    def _continuation_case(self, code, prep_text, cancelled=False):
        r = self._runner()
        r._prep_text = prep_text
        r._cancelled = cancelled
        launched, done_codes, lines = [], [], []
        r._command = lambda argv: ("metashape.exe", ["-r", "runner", *argv])
        r._launch = lambda prog, args, cwd=None, extra_env=None: launched.append(
            (prog, list(args))
        )
        argv = ["--name", "n", "--frames-dir", "orig"]
        cont = r._prep_continuation(argv, lines.append, done_codes.append, None)
        cont(code)
        self.app.processEvents()  # flush the deferred stage-2 launch
        return launched, done_codes, lines

    def test_successful_prep_launches_metashape_on_prepped_dir(self) -> None:
        from extapps.photogrammetry.metashape_workflow.run_combined import (
            PREP_RESULT_PREFIX,
        )
        prepped = tempfile.mkdtemp(prefix="mw_prepped_")
        self.addCleanup(shutil.rmtree, prepped, True)
        text = PREP_RESULT_PREFIX + json.dumps({"dirs": [prepped], "masks": 0})
        launched, done_codes, _ = self._continuation_case(0, text)
        self.assertEqual(len(launched), 1)
        prog, args = launched[0]
        self.assertEqual(prog, "metashape.exe")
        self.assertEqual(args[args.index("--frames-dir") + 1], prepped)
        self.assertIn("--skip-curate", args)
        self.assertEqual(done_codes, [])  # on_done fires after stage 2, not now

    def test_failed_prep_falls_back_to_original_argv(self) -> None:
        launched, _codes, lines = self._continuation_case(1, "no sentinel")
        self.assertEqual(len(launched), 1)
        _prog, args = launched[0]
        self.assertEqual(args[args.index("--frames-dir") + 1], "orig")
        self.assertNotIn("--skip-curate", args)
        self.assertTrue(any("continuing with the original frames" in ln
                            for ln in lines))

    def test_cancelled_prep_does_not_launch_metashape(self) -> None:
        launched, done_codes, _ = self._continuation_case(
            62097, "", cancelled=True
        )
        self.assertEqual(launched, [])
        self.assertEqual(done_codes, [62097])


class TestRunCombinedStopAfter(unittest.TestCase):
    """``run_combined --stop-after`` must short-circuit the pipeline after the
    named stage (so input-prep A/B runs are minutes, not the full bake) yet
    still emit the QC sidecar + report."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_stopafter_")
        self.in_root = os.path.join(self.tmp, "in")
        self.out_root = os.path.join(self.tmp, "out")
        for d in ("a", "b"):
            sub = os.path.join(self.in_root, d)
            os.makedirs(sub)
            for name in ("0.jpg", "1.jpg"):
                open(os.path.join(sub, name), "w").close()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra):
        from extapps.photogrammetry.metashape_workflow import run_combined
        rc = run_combined.main([
            "--input-root", self.in_root,
            "--output-root", self.out_root,
            "--name", "sa",
            "--skip-curate", "--skip-equalize",
            *extra,
        ])
        sidecar = os.path.join(self.out_root, "sa", "sa_qc.json")
        with open(sidecar, "r", encoding="utf-8") as f:
            data = json.load(f)
        return rc, data

    def test_stop_after_align_skips_refine_and_mesh(self) -> None:
        rc, data = self._run("--stop-after", "align")
        self.assertEqual(rc, 0)
        stages = data["stages"].keys()
        self.assertIn("align", stages)
        # Everything downstream of alignment must be absent.
        for downstream in ("refine_alignment", "depth", "model", "texture", "export"):
            self.assertNotIn(downstream, stages,
                             f"--stop-after align should not run '{downstream}'")
        # _stop_after must still report (the report PDF is the point) — but a
        # .psx is only persisted when --save-project asked for one.
        self.assertNotIn("save", stages)
        self.assertIn("report", stages)
        self.assertTrue(data["success"])

    def test_stop_after_saves_only_with_save_project(self) -> None:
        rc, data = self._run("--stop-after", "align", "--save-project")
        self.assertEqual(rc, 0)
        self.assertIn("save", data["stages"].keys())

    def test_stop_after_refine_runs_refine_but_no_mesh(self) -> None:
        rc, data = self._run("--stop-after", "refine")
        self.assertEqual(rc, 0)
        stages = data["stages"].keys()
        self.assertIn("align", stages)
        self.assertIn("refine_alignment", stages)
        for downstream in ("depth", "model", "texture", "export"):
            self.assertNotIn(downstream, stages,
                             f"--stop-after refine should not run '{downstream}'")
        self.assertNotIn("save", stages)
        self.assertIn("report", stages)


class TestRunCombinedFramesDir(unittest.TestCase):
    """``--frames-dir`` uses a single prepared capture directly (the panel's
    single-capture path), skipping ``--input-root`` subdir discovery."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_framesdir_")
        self.frames = os.path.join(self.tmp, "cap")
        os.makedirs(self.frames)
        for name in ("0.jpg", "1.jpg"):
            open(os.path.join(self.frames, name), "w").close()
        self.out_root = os.path.join(self.tmp, "out")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_frames_dir_single_capture_runs(self) -> None:
        from extapps.photogrammetry.metashape_workflow import run_combined
        rc = run_combined.main([
            "--frames-dir", self.frames,
            "--output-root", self.out_root, "--name", "fd",
            "--skip-curate", "--skip-equalize", "--stop-after", "align",
        ])
        self.assertEqual(rc, 0)
        sidecar = os.path.join(self.out_root, "fd", "fd_qc.json")
        self.assertTrue(os.path.exists(sidecar), "QC sidecar not written")

    def test_missing_frames_dir_errors(self) -> None:
        from extapps.photogrammetry.metashape_workflow import run_combined
        rc = run_combined.main([
            "--frames-dir", os.path.join(self.tmp, "nope"),
            "--output-root", self.out_root, "--name", "fd",
        ])
        self.assertEqual(rc, 1)


def _cv2_or_none():
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
        return cv2
    except ImportError:
        return None


class TestRunCombinedPrepOnly(unittest.TestCase):
    """``--prep-only`` is the venv half of the panel's two-stage run: it must
    run the pre-processing for real (this interpreter has cv2), write its own
    ``<name>_prep_qc.json`` sidecar (the engine run's sidecar would overwrite a
    shared one), print the machine-readable ``PREP_RESULT_JSON`` line the
    runner parses, and never touch any engine stage."""

    @classmethod
    def setUpClass(cls) -> None:
        if _cv2_or_none() is None:
            raise unittest.SkipTest("cv2/numpy not installed")

    def setUp(self) -> None:
        import numpy as np
        cv2 = _cv2_or_none()
        self.tmp = tempfile.mkdtemp(prefix="mw_preponly_")
        self.frames = os.path.join(self.tmp, "cap")
        os.makedirs(self.frames)
        rng = np.random.default_rng(0)
        for i in range(4):
            img = (rng.random((120, 160, 3)) * 255).astype("uint8")
            cv2.imwrite(os.path.join(self.frames, f"{i}.jpg"), img)
        # One catastrophically defocused frame — the default 0.15×median
        # sharpness guard (the only destructive baseline stage) must cull it.
        blur = (rng.random((120, 160, 3)) * 255).astype("uint8")
        for _ in range(2):
            blur = cv2.GaussianBlur(blur, (31, 31), 15)
        cv2.imwrite(os.path.join(self.frames, "blurry.jpg"), blur)
        self.out_root = os.path.join(self.tmp, "out")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_prep_only_curates_and_prints_result(self) -> None:
        import io
        from contextlib import redirect_stdout
        from extapps.photogrammetry.metashape_workflow import run_combined

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = run_combined.main([
                "--prep-only",
                "--frames-dir", self.frames,
                "--output-root", self.out_root, "--name", "po",
            ])
        self.assertEqual(rc, 0)
        out = buf.getvalue()

        # The sentinel line parses and names one existing curated dir.
        result = None
        for line in out.splitlines():
            if line.startswith(run_combined.PREP_RESULT_PREFIX):
                result = json.loads(line[len(run_combined.PREP_RESULT_PREFIX):])
        self.assertIsNotNone(result, f"no PREP_RESULT_JSON line in:\n{out}")
        self.assertEqual(len(result["dirs"]), 1)
        prepped = result["dirs"][0]
        self.assertTrue(os.path.isdir(prepped))
        kept = sorted(os.listdir(prepped))
        self.assertNotIn("blurry.jpg", kept, "median-frac guard did not cull")
        self.assertEqual(len(kept), 4)

        # Prep QC goes to its OWN sidecar; no engine sidecar, no engine stages.
        proj = os.path.join(self.out_root, "po")
        self.assertTrue(os.path.exists(os.path.join(proj, "po_prep_qc.json")))
        self.assertFalse(os.path.exists(os.path.join(proj, "po_qc.json")))
        with open(os.path.join(proj, "po_prep_qc.json"), encoding="utf-8") as f:
            qc = json.load(f)
        self.assertIn("curate_input_set", qc["stages"])
        self.assertNotIn("align", qc["stages"])
        self.assertTrue(qc["success"])

    def test_curate_preview_writes_prep_sidecar_not_engine_sidecar(self) -> None:
        """A preview is a prep artifact: its QC must land in
        ``<name>_prep_qc.json`` — writing ``<name>_qc.json`` would clobber a
        previous real run's engine sidecar under the same project name."""
        from extapps.photogrammetry.metashape_workflow import run_combined

        rc = run_combined.main([
            "--curate-preview",
            "--frames-dir", self.frames,
            "--output-root", self.out_root, "--name", "pv",
        ])
        self.assertEqual(rc, 0)
        proj = os.path.join(self.out_root, "pv")
        self.assertTrue(os.path.exists(os.path.join(proj, "pv_prep_qc.json")))
        self.assertFalse(os.path.exists(os.path.join(proj, "pv_qc.json")))
        with open(os.path.join(proj, "pv_prep_qc.json"), encoding="utf-8") as f:
            qc = json.load(f)
        self.assertIn("preview_curation", qc["stages"])
        # The sweep reports survivor counts per threshold, 0 included.
        rows = qc["stages"]["preview_curation"]["report"]["thresholds"]
        self.assertIn(0, [r["hash_threshold"] for r in rows])

    def test_prep_only_respects_skip_curate(self) -> None:
        """With curation skipped (and a single capture, so equalize skips too)
        the sentinel hands back the ORIGINAL dir — the runner then feeds the
        as-shot frames to Metashape, not an empty prep artifact."""
        import io
        from contextlib import redirect_stdout
        from extapps.photogrammetry.metashape_workflow import run_combined

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = run_combined.main([
                "--prep-only", "--skip-curate",
                "--frames-dir", self.frames,
                "--output-root", self.out_root, "--name", "po2",
            ])
        self.assertEqual(rc, 0)
        result = None
        for line in buf.getvalue().splitlines():
            if line.startswith(run_combined.PREP_RESULT_PREFIX):
                result = json.loads(line[len(run_combined.PREP_RESULT_PREFIX):])
        self.assertEqual(result["dirs"], [self.frames])


class TestRunCombinedPregeneratedMasks(unittest.TestCase):
    """``--use-masks`` must import pre-generated per-source mask files (written
    by the panel's venv prep stage or a manual ``--prep-only`` run) instead of
    re-deriving masks — the only masking path guaranteed to work under
    ``metashape.exe -r`` (no rembg, and native AI masking needs its model)."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_premask_")
        self.frames = os.path.join(self.tmp, "cap")
        os.makedirs(self.frames)
        for name in ("0.jpg", "1.jpg"):
            open(os.path.join(self.frames, name), "w").close()
        self.out_root = os.path.join(self.tmp, "out")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self):
        from extapps.photogrammetry.metashape_workflow import run_combined
        rc = run_combined.main([
            "--frames-dir", self.frames,
            "--output-root", self.out_root, "--name", "pm",
            "--skip-curate", "--skip-equalize", "--use-masks",
            "--stop-after", "align",
        ])
        with open(os.path.join(self.out_root, "pm", "pm_qc.json"),
                  encoding="utf-8") as f:
            return rc, json.load(f)

    def test_pre_generated_masks_are_imported_not_regenerated(self) -> None:
        # Same per-source dir naming the prep stage / rembg fallback use.
        mask_dir = os.path.join(self.out_root, "pm", "masks", "00_cap")
        os.makedirs(mask_dir)
        for name in ("0_mask.png", "1_mask.png"):
            open(os.path.join(mask_dir, name), "w").close()
        rc, qc = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("masks", qc["stages"], "pre-generated masks not imported")
        self.assertEqual(qc["stages"]["masks"]["masks_dir"], mask_dir)
        self.assertNotIn("masks_native", qc["stages"],
                         "native masking ran despite pre-generated file masks")

    def test_without_pregenerated_masks_native_path_runs(self) -> None:
        rc, qc = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("masks_native", qc["stages"])


class TestRunCombinedAlignmentLevers(unittest.TestCase):
    """The newly-exposed Metashape levers must actually reach the engine — proved
    by the values landing in the QC sidecar (recorded even in mock mode)."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_levers_")
        self.frames = os.path.join(self.tmp, "cap")
        os.makedirs(self.frames)
        for name in ("0.jpg", "1.jpg"):
            open(os.path.join(self.frames, name), "w").close()
        self.out_root = os.path.join(self.tmp, "out")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra):
        from extapps.photogrammetry.metashape_workflow import run_combined
        rc = run_combined.main([
            "--frames-dir", self.frames,
            "--output-root", self.out_root, "--name", "lv",
            "--skip-curate", "--skip-equalize", *extra,
        ])
        sidecar = os.path.join(self.out_root, "lv", "lv_qc.json")
        with open(sidecar, "r", encoding="utf-8") as f:
            return rc, json.load(f)

    def test_typoed_preset_gate_mode_rejected(self) -> None:
        """gate_mode fails fast like quality — a preset that meant 'halt'
        must not silently lose its hard stop to a typo (exit 2, no run)."""
        import extapps.photogrammetry.profile as pp
        from extapps.photogrammetry.metashape_workflow import run_combined

        store = pp.preset_store("metashape")
        store.save("t_badg", {"gate_mode": "Halt"})
        self.addCleanup(lambda: getattr(store, "delete", lambda n: None)("t_badg"))
        rc = run_combined.main([
            "--frames-dir", self.frames,
            "--output-root", self.out_root, "--name", "lv",
            "--skip-curate", "--skip-equalize", "--preset", "t_badg",
        ])
        self.assertEqual(rc, 2)

    def test_match_levers_reach_align_stage(self) -> None:
        rc, data = self._run(
            "--stop-after", "align",
            "--generic-preselection",
            "--keypoint-limit", "60000",
            "--tiepoint-limit", "20000",
            "--triage-quality", "0.3",
        )
        self.assertEqual(rc, 0)
        align = data["stages"]["align"]
        self.assertTrue(align["generic_preselection"])
        self.assertEqual(align["keypoint_limit"], 60000)
        self.assertEqual(align["tiepoint_limit"], 20000)
        self.assertEqual(data["stages"]["triage"]["quality_threshold"], 0.3)

    def test_triage_quality_zero_skips_triage(self) -> None:
        rc, data = self._run("--stop-after", "align", "--triage-quality", "0")
        self.assertEqual(rc, 0)
        self.assertNotIn("triage", data["stages"],
                         "--triage-quality 0 must skip the triage stage entirely")

    def test_cleanup_levers_reach_clean_mesh_stage(self) -> None:
        rc, data = self._run(
            "--clean-min-component", "25000",
            "--smooth-strength", "1",
            "--close-holes", "10",
        )
        self.assertEqual(rc, 0)
        clean = data["stages"]["clean_mesh"]
        self.assertEqual(clean["remove_components_face_threshold"], 25000)
        self.assertEqual(clean["smooth_strength"], 1)
        self.assertEqual(clean["close_holes_level"], 10)


class TestMetashapeVideoInput(unittest.TestCase):
    """A single Source browser handles both inputs: picking video clip(s)
    extracts them (in the panel's full Python — Metashape's bundled Python has
    no cv2) into one frames dir; picking a frame uses its containing folder."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import metashape_workflow as m
        self.tmp = tempfile.mkdtemp(prefix="mw_video_")
        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_source_browser_extracts_all_selected_clips(self) -> None:
        from unittest import mock as umock
        from extapps.photogrammetry import prep_stages

        v1 = os.path.join(self.tmp, "a.mp4")
        v2 = os.path.join(self.tmp, "b.mp4")
        for v in (v1, v2):
            open(v, "w").close()
        out = os.path.join(self.tmp, "frames")
        self.slots._frames_edit.setText(out)

        captured: dict = {}

        def fake_extract(videos, output_dir, **kw):
            captured["videos"] = list(videos)
            captured["out"] = output_dir
            return ["f1.jpg", "f2.jpg"]

        # The single '...' browser returns BOTH video clips -> extraction path.
        with umock.patch.object(self.slots.sb, "file_dialog",
                                lambda **kw: [v1, v2]), \
             umock.patch.object(prep_stages, "extract_videos_to_dir",
                                fake_extract):
            self.slots._pick_source()

        self.assertEqual(captured.get("videos"), [v1, v2],
                         "both selected videos must reach the extractor")
        self.assertEqual(captured.get("out"), out)

    def test_source_browser_uses_folder_of_a_picked_frame(self) -> None:
        from unittest import mock as umock

        frames_dir = os.path.join(self.tmp, "cap")
        os.makedirs(frames_dir)
        img = os.path.join(frames_dir, "0.jpg")
        open(img, "w").close()

        # The same browser returns a frame image -> use its containing folder,
        # no extraction.
        with umock.patch.object(self.slots.sb, "file_dialog",
                                lambda **kw: [img]):
            self.slots._pick_source()

        self.assertEqual(self.slots._frames_edit.text(), frames_dir)


class TestExtractVideosToDir(unittest.TestCase):
    """prep_stages.extract_videos_to_dir: one shared frames dir, a unique
    per-clip filename prefix (so multiple sources never collide), and a clean
    empty return when OpenCV is unavailable."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_extract_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unique_prefix_per_video_and_creates_dir(self) -> None:
        from unittest import mock as umock
        import pythontk
        from extapps.photogrammetry import prep_stages

        calls: list = []

        class _FakeFE:
            def extract_frames_sharpest(self, video_path, output_folder,
                                        prefix="frame", **kw):
                calls.append(prefix)
                p = os.path.join(output_folder, f"{prefix}_0.jpg")
                open(p, "w").close()
                return [p]

        out = os.path.join(self.tmp, "frames")
        # Two clips sharing a stem — the index prefix must still disambiguate.
        videos = [os.path.join(self.tmp, "clip.mp4"),
                  os.path.join(self.tmp, "sub", "clip.mp4")]
        with umock.patch.object(pythontk, "FrameExtractor", _FakeFE):
            written = prep_stages.extract_videos_to_dir(videos, out)

        self.assertEqual(len(written), 2)
        self.assertEqual(len(set(calls)), 2, "prefixes must be unique per clip")
        self.assertTrue(os.path.isdir(out), "output dir should be created")

    def test_empty_when_cv2_unavailable(self) -> None:
        from unittest import mock as umock
        import pythontk
        from extapps.photogrammetry import prep_stages

        class _NoCV2FE:
            def extract_frames_sharpest(self, *a, **k):
                return []  # FrameExtractor returns [] when cv2 is missing

        with umock.patch.object(pythontk, "FrameExtractor", _NoCV2FE):
            written = prep_stages.extract_videos_to_dir(
                [os.path.join(self.tmp, "a.mp4")], os.path.join(self.tmp, "f")
            )
        self.assertEqual(written, [])


class TestRunCombinedVideo(unittest.TestCase):
    """``run_combined --video`` extracts frame(s) from the clip(s) into one
    dir and runs them as the sole source (the API-side multi-video path)."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_video_cli_")
        self.out_root = os.path.join(self.tmp, "out")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_video_extracts_then_runs(self) -> None:
        from unittest import mock as umock
        from extapps.photogrammetry.metashape_workflow import run_combined

        vid = os.path.join(self.tmp, "clip.mp4")
        open(vid, "w").close()

        def fake_extract(videos, output_dir, **kw):
            os.makedirs(output_dir, exist_ok=True)
            paths = []
            for i in range(2):
                p = os.path.join(output_dir, f"f{i}.jpg")
                open(p, "w").close()
                paths.append(p)
            return paths

        # run_combined binds the name at import time -> patch it there.
        with umock.patch.object(run_combined, "extract_videos_to_dir",
                                fake_extract):
            rc = run_combined.main([
                "--video", vid, "--output-root", self.out_root, "--name", "vid",
                "--skip-curate", "--skip-equalize", "--stop-after", "align",
            ])
        self.assertEqual(rc, 0)
        sidecar = os.path.join(self.out_root, "vid", "vid_qc.json")
        self.assertTrue(os.path.exists(sidecar), "QC sidecar not written")

    def test_video_and_frames_dir_mutually_exclusive(self) -> None:
        from extapps.photogrammetry.metashape_workflow import run_combined
        rc = run_combined.main([
            "--video", os.path.join(self.tmp, "x.mp4"),
            "--frames-dir", self.tmp,
            "--output-root", self.out_root, "--name", "z",
        ])
        self.assertEqual(rc, 2)

    def test_video_no_frames_extracted_errors(self) -> None:
        from unittest import mock as umock
        from extapps.photogrammetry.metashape_workflow import run_combined

        vid = os.path.join(self.tmp, "clip.mp4")
        open(vid, "w").close()
        with umock.patch.object(run_combined, "extract_videos_to_dir",
                                lambda *a, **k: []):
            rc = run_combined.main([
                "--video", vid, "--output-root", self.out_root, "--name", "z",
            ])
        self.assertEqual(rc, 1)


class TestExtractVideosPurgesStaleFrames(unittest.TestCase):
    """extract_videos_to_dir keys frames to their SOURCE FILE (stem + path
    digest) and purges exactly that clip's previous frames on re-extraction —
    otherwise re-runs feed alignment the union of every extraction ever made,
    while same-named clips from different folders must NOT clobber each other
    (the panel's Source browser extracts each pick in a separate call)."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_purge_")
        self.out = os.path.join(self.tmp, "frames")
        os.makedirs(self.out)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _fake_extractor(index):
        """FrameExtractor stand-in writing the REAL naming shape
        ({prefix}_{idx:06d}.jpg) with a fixed winning frame index."""
        class FakeExtractor:
            def extract_frames_sharpest(self, video_path, output_folder,
                                        window_sec, quality, prefix):
                path = os.path.join(output_folder, f"{prefix}_{index:06d}.jpg")
                open(path, "w").close()
                return [path]
        return FakeExtractor

    def _extract(self, videos, index, logs):
        from unittest import mock as umock
        import pythontk
        from extapps.photogrammetry.prep_stages import extract_videos_to_dir
        with umock.patch.object(pythontk, "FrameExtractor",
                                self._fake_extractor(index)):
            return extract_videos_to_dir(videos, self.out, log=logs.append)

    def test_reextraction_purges_only_this_clips_frames(self) -> None:
        vid = os.path.join(self.tmp, "clip.mp4")
        open(vid, "w").close()
        foreign = os.path.join(self.out, "reference_photo.jpg")
        open(foreign, "w").close()
        # Pre-digest-scheme leftover ({ii}_{stem}_NNNNNN.jpg) — an upgrade
        # re-extraction must purge it too, or it rides along forever.
        legacy = os.path.join(self.out, "00_clip_000042.jpg")
        open(legacy, "w").close()

        logs: list = []
        first = self._extract([vid], 123, logs)
        self.assertFalse(os.path.exists(legacy),
                         "old-scheme frame of this clip must be purged")
        second = self._extract([vid], 456, logs)  # window changed -> new index
        self.assertFalse(os.path.exists(first[0]),
                         "previous extraction's frame must be purged")
        self.assertTrue(os.path.exists(second[0]))
        self.assertTrue(os.path.exists(foreign),
                        "non-extraction files are not ours to delete")
        joined = " ".join(logs)
        self.assertIn("purged", joined)
        self.assertIn("WARNING", joined)

    def test_same_stem_different_folders_do_not_clobber(self) -> None:
        dir_a = os.path.join(self.tmp, "capA")
        dir_b = os.path.join(self.tmp, "capB")
        for d in (dir_a, dir_b):
            os.makedirs(d)
            open(os.path.join(d, "clip.mp4"), "w").close()
        logs: list = []
        # Two separate calls, like two panel browses (indices restart each call).
        a = self._extract([os.path.join(dir_a, "clip.mp4")], 1, logs)
        b = self._extract([os.path.join(dir_b, "clip.mp4")], 2, logs)
        self.assertTrue(os.path.exists(a[0]),
                        "capA frames deleted by capB's same-stem extraction")
        self.assertTrue(os.path.exists(b[0]))
        self.assertNotEqual(os.path.basename(a[0]), os.path.basename(b[0]))

    def test_stem_extension_sibling_not_purged(self) -> None:
        """'clip' must not purge 'clip_final' frames (prefix-shape match)."""
        v1 = os.path.join(self.tmp, "clip.mp4")
        v2 = os.path.join(self.tmp, "clip_final.mp4")
        for v in (v1, v2):
            open(v, "w").close()
        logs: list = []
        final = self._extract([v2], 5, logs)
        self._extract([v1], 9, logs)
        self.assertTrue(os.path.exists(final[0]),
                        "sibling clip's frames were wrongly purged")


class TestStopAfterStillExportsColmap(unittest.TestCase):
    """--export-colmap must produce the splat dataset on --stop-after runs —
    align-only + dataset is the natural cheap invocation and used to exit
    without exporting."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="mw_colmap_")
        self.frames = os.path.join(self.tmp, "frames")
        os.makedirs(self.frames)
        open(os.path.join(self.frames, "a.jpg"), "w").close()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_stop_after_align_exports_colmap(self) -> None:
        from extapps.photogrammetry.metashape_workflow import run_combined
        rc = run_combined.main([
            "--name", "cm", "--frames-dir", self.frames,
            "--output-root", os.path.join(self.tmp, "out"),
            "--skip-curate", "--skip-equalize",
            "--stop-after", "align",
            "--export-colmap", os.path.join(self.tmp, "colmap"),
        ])
        self.assertEqual(rc, 0)
        sidecar = os.path.join(self.tmp, "out", "cm", "cm_qc.json")
        with open(sidecar, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("export_colmap", data["stages"])


class TestPanelPresetResetsUnnamedKeys(unittest.TestCase):
    """Panel presets apply as defaults + overlay (CLI semantics): keys a
    preset does not name reset to registry defaults instead of keeping
    session-persisted leftovers from a previously applied preset."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import metashape_workflow as m
        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_unnamed_keys_reset_to_defaults(self) -> None:
        from extapps.photogrammetry.metashape_workflow import parameters as P
        # Simulate residue from an earlier preset/session.
        self.slots._write_param("smooth_strength", 3)
        self.slots._write_param("depth_filter", "aggressive")
        # Apply a preset that names neither key.
        self.slots._apply_param_dict({"align_downscale": 4})
        self.assertEqual(self.slots._read_param("align_downscale"), 4)
        self.assertEqual(self.slots._read_param("smooth_strength"),
                         P.PARAMS["smooth_strength"].default)
        self.assertEqual(self.slots._read_param("depth_filter"),
                         P.PARAMS["depth_filter"].default)

    def test_widgetless_preset_keys_are_logged(self) -> None:
        from unittest import mock as umock
        with umock.patch.object(self.slots.bridge.logger, "warning") as warn:
            self.slots._apply_param_dict({"align_downscale": 2,
                                          "no_such_key": True})
        self.assertTrue(warn.called)
        self.assertIn("no_such_key", str(warn.call_args))


if __name__ == "__main__":
    unittest.main(verbosity=2)
