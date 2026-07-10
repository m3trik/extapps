# !/usr/bin/python
# coding=utf-8
"""Regression tests for RealityCaptureWorkflow CLI command generation (mocked).

Guards the add-images bug observed 2026-05-30 in RealityScan.log:
RealityScan's ``-add`` adds a single *file*; a *directory* must use
``-addFolder``. Passing a directory to ``-add`` fails with
``Failed to add image <dir> [err:7134 File not found]`` and adds 0 images,
silently producing an empty reconstruction.
"""
import os
import shutil
import tempfile
import unittest
from unittest import mock

WF = "extapps.photogrammetry.realityscan_workflow._realityscan_workflow"
from extapps.photogrammetry.realityscan_workflow._realityscan_workflow import (  # noqa: E402
    RealityCaptureWorkflow,
    find_realitycapture_exe,
)
from extapps.photogrammetry.realityscan_workflow._realityscan_connection import (  # noqa: E402
    RealityScanConnection,
    RealityScanInteractiveError,
)
from extapps.photogrammetry.realityscan_workflow._rsnode_connection import (  # noqa: E402
    RsNodeConnection,
)


class FindExeVersionTest(unittest.TestCase):
    """RealityScan installs to RealityScan_<ver>\\; pick the HIGHEST version."""

    def test_picks_highest_version_numerically(self):
        fakes = [
            r"C:\Program Files\RealityScan_2.0\RealityScan.exe",
            r"C:\Program Files\RealityScan_2.10\RealityScan.exe",  # 2.10 > 2.1 (numeric)
            r"C:\Program Files\RealityScan_2.1\RealityScan.exe",
        ]
        with mock.patch.dict(os.environ), mock.patch("glob.glob", return_value=fakes):
            os.environ.pop("RC_EXE", None)
            self.assertEqual(
                find_realitycapture_exe(),
                r"C:\Program Files\RealityScan_2.10\RealityScan.exe",
            )

    def test_env_override_empty_forces_none(self):
        with mock.patch.dict(os.environ, {"RC_EXE": ""}):
            self.assertIsNone(find_realitycapture_exe())


class AddImagesCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Don't touch a real RC install during construction.
        ver = mock.patch(f"{WF}.get_realitycapture_version", return_value="test")
        ver.start()
        self.addCleanup(ver.stop)
        self.imgs = os.path.join(self.tmp, "imgs")
        os.makedirs(self.imgs)
        self.wf = RealityCaptureWorkflow(
            project_path=os.path.join(self.tmp, "proj"),
            name="t",
            rc_exe="C:/fake/RealityScan.exe",
            mock_mode=False,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_image_dirs_uses_addFolder(self):
        with mock.patch(f"{WF}.get_image_filepaths", return_value=["a.jpg", "b.jpg"]), \
             mock.patch.object(self.wf, "_run_rc", return_value=0) as run:
            self.wf.add_image_dirs([self.imgs])
        run.assert_called_once()
        args = run.call_args.args
        self.assertEqual(args[0], "-addFolder",
                         f"a directory must use -addFolder, got {args!r}")
        self.assertIn(self.imgs, args)

    def test_add_images_with_dir_uses_addFolder(self):
        with mock.patch(f"{WF}.get_image_filepaths", return_value=["a.jpg"]), \
             mock.patch.object(self.wf, "_run_rc", return_value=0) as run:
            self.wf.add_images(self.imgs)
        run.assert_called_once()
        args = run.call_args.args
        self.assertEqual(args[0], "-addFolder",
                         f"a directory must use -addFolder, got {args!r}")

    def test_add_images_with_file_list_uses_per_file_add(self):
        files = [os.path.join(self.imgs, "a.jpg"), os.path.join(self.imgs, "b.jpg")]
        with mock.patch.object(self.wf, "_run_rc", return_value=0) as run:
            self.wf.add_images(files)
        run.assert_called_once()
        args = list(run.call_args.args)
        # RC -add takes one file -> expect one -add per file, both paths present.
        self.assertEqual(args.count("-add"), 2, f"expected per-file -add, got {args!r}")
        for f in files:
            self.assertIn(f, args)


class ConnectionSelectionTest(unittest.TestCase):
    """Lazy transport selection: inject / auto-prefer RSNode / CLI fallback."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        ver = mock.patch(f"{WF}.get_realitycapture_version", return_value="test")
        ver.start()
        self.addCleanup(ver.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("RC_RSNODE", None)
        os.environ.pop("RC_RSNODE_URL", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _wf(self, **kw):
        return RealityCaptureWorkflow(
            project_path=os.path.join(self.tmp, "proj"), name="t",
            rc_exe="C:/fake/RealityScan.exe", mock_mode=False, **kw,
        )

    def test_injected_connection_is_used(self):
        sentinel = object()
        wf = self._wf(connection=sentinel)
        self.assertIs(wf._connection(), sentinel)

    def test_use_rsnode_false_selects_cli(self):
        wf = self._wf(use_rsnode=False)
        self.assertIsInstance(wf._connection(), RealityScanConnection)

    def test_auto_prefers_rsnode_when_available(self):
        wf = self._wf()  # auto
        with mock.patch.object(RsNodeConnection, "is_available", return_value=True):
            conn = wf._connection()
        self.assertIsInstance(conn, RsNodeConnection)

    def test_auto_falls_back_to_cli_when_unavailable(self):
        wf = self._wf()
        with mock.patch.object(RsNodeConnection, "is_available", return_value=False):
            conn = wf._connection()
        self.assertIsInstance(conn, RealityScanConnection)

    def test_forced_rsnode_raises_when_unavailable(self):
        wf = self._wf(use_rsnode=True)
        with mock.patch.object(RsNodeConnection, "is_available", return_value=False):
            with self.assertRaises(RealityScanInteractiveError):
                wf._connection()

    def test_connection_resolved_once_and_cached(self):
        wf = self._wf(use_rsnode=False)
        first = wf._connection()
        self.assertIs(wf._connection(), first)

    def test_finalize_run_tears_down_connection(self):
        closed = {"n": 0}

        class _Conn:
            def close(self):
                closed["n"] += 1

        wf = self._wf(connection=_Conn())
        wf.finalize_run(success=True)
        self.assertEqual(closed["n"], 1)

    def test_finalize_run_no_connection_is_noop(self):
        wf = self._wf(use_rsnode=False)  # never resolved (no _run_rc)
        wf.finalize_run(success=True)  # must not raise
        self.assertIsNone(wf._conn)

    def test_finalize_run_teardown_swallows_errors(self):
        class _Conn:
            def close(self):
                raise RuntimeError("teardown boom")

        wf = self._wf(connection=_Conn())
        # teardown failure must not mask the run's outcome
        self.assertEqual(wf.finalize_run(success=True), wf.qc.path)


class PublishOutputsTest(unittest.TestCase):
    """run_combined.publish_outputs copies deliverables (not the .rsproj) from
    local scratch to the synced output root — RC must scratch locally, so the
    finished deliverables are published to O: afterward."""

    def setUp(self):
        from extapps.photogrammetry.realityscan_workflow.run_combined import (
            publish_outputs,
        )
        self.publish_outputs = publish_outputs
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copies_deliverables_excluding_rsproj(self):
        proj = os.path.join(self.tmp, "scratch", "welding")
        os.makedirs(os.path.join(proj, "logs"))
        os.makedirs(os.path.join(proj, "reports"))
        for rel in ("welding.obj", "welding.mtl", "welding_u1_v1_diffuse.png",
                    "welding_qc.json", "welding.rsproj",
                    "logs/align.log", "reports/final.xml"):
            with open(os.path.join(proj, rel), "w") as fh:
                fh.write("x")
        # Prep-stage intermediates in the project dir must NOT publish:
        # curated/equalized are multi-GB frame copies, logs are droppings.
        os.makedirs(os.path.join(proj, "curated", "camA_curated"))
        os.makedirs(os.path.join(proj, "equalized", "camA_eq"))
        with open(os.path.join(proj, "curated", "camA_curated", "f.jpg"), "w") as fh:
            fh.write("x")
        pub = os.path.join(self.tmp, "synced", "welding")
        n = self.publish_outputs(proj, pub)
        self.assertEqual(n, 5)  # everything but .rsproj + logs/curated/equalized
        self.assertFalse(os.path.exists(os.path.join(pub, "curated")))
        self.assertFalse(os.path.exists(os.path.join(pub, "equalized")))
        self.assertFalse(os.path.exists(os.path.join(pub, "logs")))
        for rel in ("welding.obj", "welding.mtl", "welding_u1_v1_diffuse.png",
                    "welding_qc.json", "reports/final.xml"):
            self.assertTrue(os.path.isfile(os.path.join(pub, rel)), rel)
        # the RC working project is NOT published
        self.assertFalse(os.path.isfile(os.path.join(pub, "welding.rsproj")))

    def test_same_dir_is_noop(self):
        proj = os.path.join(self.tmp, "p")
        os.makedirs(proj)
        self.assertIsNone(self.publish_outputs(proj, proj))

    def test_inaccessible_source_does_not_raise(self):
        # A publish failure (e.g. synced share offline, or a missing source)
        # must be best-effort: return 0, never raise — so it can't flip a
        # successful run to a reported failure.
        missing = os.path.join(self.tmp, "nope")
        self.assertEqual(self.publish_outputs(missing, os.path.join(self.tmp, "pub")), 0)


class ReportMetricsTest(unittest.TestCase):
    """Parse the bundled QC ``<qc>`` report template's rendered output.

    Guards the 2026-05-31 silent-success bug: ``-exportReport`` 400'd over RSNode
    (one arg instead of ``outputFile templateFile``), so every align/model metric
    came back null and ALL acceptance gates skipped — the welding_prod run wrote
    ``success: true`` having verified nothing. Schema is the one verified live
    against RealityScan 2.1's RSNode (see ``qc_report_template.html``).
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        ver = mock.patch(f"{WF}.get_realitycapture_version", return_value="test")
        ver.start()
        self.addCleanup(ver.stop)
        self.wf = RealityCaptureWorkflow(
            project_path=os.path.join(self.tmp, "proj"), name="t", mock_mode=True
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _report(self, body):
        p = os.path.join(self.tmp, "r.xml")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
        return p

    def test_parses_single_component(self):
        # $Using lines render as leading blank lines before <qc> -> must be sliced.
        rep = self._report(
            '\n\n\n<qc images="24" comps="1">'
            '<c cams="24"><pts>56125</pts>'
            '<m tris="61534" verts="30755" parts="1"/></c></qc>\n'
        )
        m = self.wf._parse_report_metrics(rep)
        self.assertEqual(m["total_count"], 24)
        self.assertEqual(m["components"], 1)
        self.assertEqual(m["aligned_count"], 24)
        self.assertEqual(m["registered_count"], 24)
        self.assertEqual(m["faces"], 61534)
        self.assertEqual(m["vertices"], 30755)
        self.assertEqual(m["mesh_parts"], 1)

    def test_fragmented_aligned_count_is_largest_component(self):
        # The welding failure mode: most cameras register but fragment into
        # multiple components. aligned_count must be the LARGEST component (the
        # usable reconstruction), so aligned_pct exposes the fragmentation.
        rep = self._report(
            '<qc images="812" comps="3">'
            '<c cams="500"><pts>9</pts><m tris="900" verts="450" parts="1"/></c>'
            '<c cams="200"><pts>9</pts><m tris="300" verts="150" parts="2"/></c>'
            '<c cams="60"><pts>9</pts><m tris="50" verts="25" parts="1"/></c></qc>'
        )
        m = self.wf._parse_report_metrics(rep)
        self.assertEqual(m["total_count"], 812)
        self.assertEqual(m["aligned_count"], 500)        # largest component
        self.assertEqual(m["registered_count"], 760)     # 500+200+60
        self.assertEqual(m["faces"], 900)                # largest model
        self.assertEqual(m["components"], 3)

    def test_zero_aligned_is_measured_zero(self):
        # Report rendered but no <c> components: aligned_count must be a measured
        # 0 (not absent/None) so align_photos' "No cameras aligned" hard-fail
        # fires rather than degrading to a soft "not measured" warning.
        m = self.wf._parse_report_metrics(
            self._report('<qc images="812" comps="0"></qc>')
        )
        self.assertEqual(m["total_count"], 812)
        self.assertEqual(m["aligned_count"], 0)
        self.assertEqual(m["registered_count"], 0)

    def test_empty_or_garbage_returns_no_metrics(self):
        # No <qc> -> empty dict so gates skip ("not measured") rather than treat
        # missing values as zeros (a zero falsely passes max_* gates).
        self.assertEqual(self.wf._parse_report_metrics(self._report("garbage")), {})
        self.assertEqual(self.wf._parse_report_metrics(None), {})
        self.assertEqual(self.wf._parse_report_metrics("/no/such/file.xml"), {})

    def test_export_report_passes_template_as_second_arg(self):
        # Two params: outputFile + bundled template (one arg = the 400 bug).
        from extapps.photogrammetry.realityscan_workflow import (
            _realityscan_workflow as mod,
        )
        self.wf.mock_mode = False
        with mock.patch.object(self.wf, "_run_rc", return_value=0) as run:
            self.wf._export_report("align")
        args = run.call_args.args
        self.assertEqual(args[0], "-exportReport")
        self.assertEqual(args[2], mod.QC_REPORT_TEMPLATE)
        self.assertTrue(os.path.isfile(mod.QC_REPORT_TEMPLATE))


class CleanMeshCommandTest(unittest.TestCase):
    """The component floor must reach RC as ``-setMinComponentSize N`` — the one
    CLI-reachable noise lever the specular_metal preset turns up."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        ver = mock.patch(f"{WF}.get_realitycapture_version", return_value="test")
        ver.start()
        self.addCleanup(ver.stop)
        self.wf = RealityCaptureWorkflow(
            project_path=os.path.join(self.tmp, "proj"), name="t",
            rc_exe="C:/fake/RealityScan.exe", mock_mode=False,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_threshold_emits_setMinComponentSize(self):
        # Stub _mesh_metrics so the only _run_rc call captured is the clean one.
        with mock.patch.object(self.wf, "_run_rc", return_value=0) as run, \
             mock.patch.object(self.wf, "_mesh_metrics", return_value={}):
            self.wf.clean_mesh(remove_components_face_threshold=25000)
        args = list(run.call_args.args)
        self.assertIn("-setMinComponentSize", args)
        self.assertEqual(args[args.index("-setMinComponentSize") + 1], "25000")
        self.assertIn("-cleanModel", args)


class PresetRunOverlayTest(unittest.TestCase):
    """``--preset`` lays the profile template over run_combined's defaults,
    end-to-end (profile -> preset overlay -> arg default -> pipeline call)."""

    def setUp(self):
        from pythontk.core_utils.user_config import CONFIG_ROOT_ENV_VAR
        import extapps.photogrammetry.profile as pp

        self.tmp = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        # Isolate from any personal profile so the *packaged* preset is exercised.
        os.environ[CONFIG_ROOT_ENV_VAR] = os.path.join(self.tmp, "cfg")
        os.environ.pop(pp.PROFILE_ENV, None)
        ver = mock.patch(f"{WF}.get_realitycapture_version", return_value="test")
        ver.start()
        self.addCleanup(ver.stop)
        # One image-bearing capture subdir (extension-only; never opened in mock).
        self.inroot = os.path.join(self.tmp, "in")
        os.makedirs(os.path.join(self.inroot, "cap"))
        open(os.path.join(self.inroot, "cap", "f.jpg"), "wb").close()
        self.out = os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _save_user_preset(self, name, data):
        # Writes under the temp config root set in setUp (PresetStore user tier).
        import extapps.photogrammetry.profile as pp

        pp.preset_store("realityscan").save(name, data)

    def _run(self, *extra):
        from extapps.photogrammetry.realityscan_workflow import run_combined as rc_run

        argv = ["--name", "t", "--input-root", self.inroot, "--output-root", self.out,
                "--texture-size", "4096", "--mock", "--rsnode", "off",
                "--skip-curate", "--skip-equalize", *extra]
        captured = {}
        real_clean = RealityCaptureWorkflow.clean_mesh

        def spy(self, *a, **kw):
            captured["threshold"] = kw.get(
                "remove_components_face_threshold", a[0] if a else None
            )
            return real_clean(self, *a, **kw)

        with mock.patch.object(RealityCaptureWorkflow, "clean_mesh", spy):
            code = rc_run.main(argv)
        return code, captured

    def test_user_preset_floor_applied(self):
        # Full path: PresetStore user tier -> get_preset -> arg default -> clean_mesh.
        self._save_user_preset("t_floor", {"min_component_size": 25000})
        code, captured = self._run("--preset", "t_floor")
        self.assertEqual(code, 0)
        self.assertEqual(captured["threshold"], 25000)

    def test_builtin_preset_loads_and_is_accepted(self):
        # The shipped specular_metal resolves end-to-end; it intentionally does
        # NOT crank the RC component floor (its levers are Metashape/GUI), so the
        # floor stays at baseline.
        code, captured = self._run("--preset", "specular_metal")
        self.assertEqual(code, 0)
        self.assertEqual(captured["threshold"], 100)

    def test_no_preset_uses_baseline_floor(self):
        # No preset -> the stock baseline floor (unchanged from historic behavior).
        code, captured = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(captured["threshold"], 100)

    def test_explicit_flag_overrides_preset(self):
        self._save_user_preset("t_floor", {"min_component_size": 25000})
        code, captured = self._run(
            "--preset", "t_floor", "--clean-min-component", "500"
        )
        self.assertEqual(code, 0)
        self.assertEqual(captured["threshold"], 500)

    def test_unknown_preset_is_rejected(self):
        from extapps.photogrammetry.realityscan_workflow import run_combined as rc_run

        code = rc_run.main([
            "--name", "t", "--input-root", self.inroot, "--output-root", self.out,
            "--mock", "--rsnode", "off", "--preset", "nope",
        ])
        self.assertEqual(code, 2)

    def test_typoed_preset_quality_rejected(self):
        self._save_user_preset("t_badq", {"quality": "Draft "})
        code, _ = self._run("--preset", "t_badq")
        self.assertEqual(code, 2)

    def test_explicit_quality_rescues_typoed_preset_quality(self):
        """A valid explicit --quality wins over a typo'd preset value instead
        of exit 2 (mirrors the Metashape runner's pre-parse rescue)."""
        self._save_user_preset("t_badq", {"quality": "Draft "})
        code, _ = self._run("--preset", "t_badq", "--quality", "max")
        self.assertEqual(code, 0)

    def test_typoed_preset_gate_mode_rejected(self):
        """gate_mode fails fast like quality — a preset that meant 'halt'
        must not silently lose its hard stop to a typo."""
        self._save_user_preset("t_badg", {"gate_mode": "Halt"})
        code, _ = self._run("--preset", "t_badg")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
