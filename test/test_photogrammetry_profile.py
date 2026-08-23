# !/usr/bin/python
# coding=utf-8
"""Tests for the photogrammetry profile (config separated from source)."""
import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest

from unittest import mock

import pythontk as ptk
from pythontk.core_utils.user_config import CONFIG_ROOT_ENV_VAR
from extapps.photogrammetry import profile as pp


class PhotogrammetryProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._prev = {
            k: os.environ.get(k) for k in (CONFIG_ROOT_ENV_VAR, pp.PROFILE_ENV)
        }
        # Isolate from the developer's real profile: point the config root at a
        # temp dir and clear the env pointer so defaults/explicit paths govern.
        os.environ[CONFIG_ROOT_ENV_VAR] = self.tmp
        os.environ.pop(pp.PROFILE_ENV, None)

    def tearDown(self):
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, data):
        path = os.path.join(self.tmp, "prof.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def test_packaged_default_when_no_profile(self):
        prof = pp.Profile.get_profile()
        self.assertEqual(prof["curate"]["sharpness_percentile"], 0)
        self.assertEqual(prof["equalize"]["reference"], "median")
        self.assertEqual(prof["gsplat"]["max_resolution"], 1920)
        # Reconstruction tuning ships with the default. Baseline floor stays at
        # the stock value (the noise tuning is opt-in via presets, which now live
        # as shipped JSON files, not in the profile dict).
        self.assertEqual(prof["reconstruct"]["min_component_size"], 100)
        self.assertEqual(prof["reconstruct"]["simplify_target"], 20_000_000)
        self.assertNotIn("presets", prof)
        # Derived roots interpolate the bases (no leftover token) and land under
        # the (temp) config root, not any specific machine's drive.
        self.assertNotIn("{graphics_root}", prof["input_root"])
        self.assertTrue(prof["input_root"].replace("\\", "/").endswith("/input"))
        self.assertTrue(prof["input_root"].startswith(self.tmp))

    def test_token_interpolation_and_expand(self):
        path = self._write({"graphics_root": "Z:/g", "scratch_root": "Y:/s"})
        prof = pp.Profile.get_profile(path)
        self.assertEqual(prof["input_root"], "Z:/g/input")
        self.assertEqual(prof["metashape_output_root"], "Z:/g/metashape")
        self.assertEqual(prof["realityscan_scratch_root"], "Y:/s/rc_out")
        self.assertEqual(prof["gsplat_scratch_root"], "Y:/s/gsplat_out")

    def test_partial_profile_deep_merges_over_default(self):
        path = self._write({"curate": {"hash_threshold": 13}})
        prof = pp.Profile.get_profile(path)
        self.assertEqual(prof["curate"]["hash_threshold"], 13)        # overridden
        self.assertEqual(prof["curate"]["sharpness_percentile"], 0)  # default kept
        self.assertEqual(prof["equalize"]["reference"], "median")     # default branch kept

    def test_env_pointer_resolves(self):
        path = self._write({"graphics_root": "E:/env"})
        os.environ[pp.PROFILE_ENV] = path
        prof = pp.Profile.get_profile()
        self.assertEqual(prof["graphics_root"], "E:/env")

    def test_configured_app_path_reads_and_expands_apps(self):
        """apps.<key> is the network-install hook: configured_app_path returns it
        expanded; an unset key is None; '${ENV}' is expanded on read."""
        exe = os.path.join(self.tmp, "net", "metashape.exe")
        path = self._write({"apps": {"metashape_exe": exe,
                                     "sugar_dir": "${SUGAR_TEST_ROOT}/repo"}})
        self.assertEqual(pp.Profile.configured_app_path("metashape_exe", path), exe)
        self.assertIsNone(pp.Profile.configured_app_path("brush_exe", path))  # unset -> None
        os.environ["SUGAR_TEST_ROOT"] = self.tmp
        try:
            got = pp.Profile.configured_app_path("sugar_dir", path)
        finally:
            os.environ.pop("SUGAR_TEST_ROOT", None)
        self.assertTrue(got.startswith(self.tmp))
        self.assertTrue(got.replace("\\", "/").endswith("/repo"))

    def test_configured_app_path_swallows_bad_profile(self):
        """A malformed / unreadable profile must not break app discovery —
        configured_app_path returns None so the caller falls through to standard
        discovery rather than crashing the availability check."""
        with mock.patch.object(pp.Profile, "get_profile", side_effect=ValueError("boom")):
            self.assertIsNone(pp.Profile.configured_app_path("metashape_exe"))

    def test_discovery_consults_profile_app_override(self):
        """A discovery function (Brush here) falls back to apps.<key> when its env
        var is unset and the app isn't on PATH (the network-install path), and a
        configured-but-missing path falls through to mock mode (offline share)."""
        from extapps.photogrammetry.gaussian_splat_workflow._gaussian_splat_workflow \
            import GaussianSplatWorkflow
        fake = os.path.join(self.tmp, "brush_app.exe")
        open(fake, "wb").close()

        prof_path = self._write({"apps": {"brush_exe": fake}})
        with mock.patch.dict(os.environ), \
                mock.patch("shutil.which", return_value=None):
            os.environ.pop("BRUSH_EXE", None)        # env unset -> profile consulted
            os.environ[pp.PROFILE_ENV] = prof_path   # active profile = our temp one
            self.assertEqual(GaussianSplatWorkflow.find_brush_exe(), fake)

        # Configured but missing -> falls through (here to PATH, mocked empty).
        prof_path = self._write(
            {"apps": {"brush_exe": os.path.join(self.tmp, "gone.exe")}}
        )
        with mock.patch.dict(os.environ), \
                mock.patch("shutil.which", return_value=None):
            os.environ.pop("BRUSH_EXE", None)
            os.environ[pp.PROFILE_ENV] = prof_path
            self.assertIsNone(GaussianSplatWorkflow.find_brush_exe())

    def test_example_and_default_share_one_schema(self):
        # Lock the DRY refactor: the copy-me example and the packaged default are
        # both built from the same skeleton, so their derived roots + tuning must
        # match exactly (only the two base roots and the example's _comment differ).
        example = {k: v for k, v in pp.EXAMPLE_PROFILE.items() if k != "_comment"}
        default = pp.Profile._packaged_default()
        self.assertEqual(set(example), set(default))
        for k in pp._DERIVED_ROOT_KEYS:
            self.assertEqual(example[k], default[k])  # identical templates
        for block in ("apps", "curate", "equalize", "gsplat", "reconstruct"):
            self.assertEqual(example[block], default[block])  # identical tuning

    def test_get_preset_resolves_builtin_and_validates(self):
        # None / sentinel names are a no-op overlay (runners keep plain defaults).
        for noop in (None, "", "none", "None", "default"):
            self.assertEqual(pp.Profile.get_preset(noop, "metashape"), {})
        # The shipped built-in resolves (user tier is empty under the temp root)
        # with the _comment stripped, carrying the corrected specular values.
        sm = pp.Profile.get_preset("specular_metal", "metashape")
        self.assertNotIn("_comment", sm)
        self.assertEqual(sm["depth_filter"], "moderate")
        self.assertEqual(sm["align_downscale"], 2)
        self.assertEqual(sm["depth_downscale"], 2)  # ds2, not ds1 (ds1 over-fits)
        self.assertTrue(sm["mask_background"])
        self.assertNotIn("min_component_size", sm)  # cranking cleanup isn't the fix
        # A typo is rejected (not silently run with defaults); message lists names.
        with self.assertRaises(ValueError) as ctx:
            pp.Profile.get_preset("speculor_metl", "metashape")
        self.assertIn("specular_metal", str(ctx.exception))

    def test_user_preset_shadows_builtin(self):
        # A user-saved preset of the same name wins over the shipped built-in
        # (writes under the temp config root set in setUp).
        pp.Profile.preset_store("metashape").save("specular_metal", {"depth_filter": "aggressive"})
        self.assertEqual(
            pp.Profile.get_preset("specular_metal", "metashape")["depth_filter"], "aggressive"
        )

    def test_presets_are_engine_scoped(self):
        # A preset saved for one engine must NOT appear in another engine's store
        # (the whole point of per-engine scoping: a Metashape save isn't an RC one).
        pp.Profile.preset_store("metashape").save("my_rig", {"tiepoint_limit": 20000})
        self.assertIn("my_rig", pp.Profile.preset_store("metashape").list())
        self.assertNotIn("my_rig", pp.Profile.preset_store("realityscan").list())
        with self.assertRaises(ValueError):
            pp.Profile.get_preset("my_rig", "realityscan")

    def test_tuning_blocks_isolated_per_profile(self):
        # deepcopy in _skeleton: mutating one resolved profile's nested tuning
        # (e.g. the publish.targets list) must not bleed into another.
        a = pp.Profile.get_profile()
        b = pp.Profile.get_profile()
        a["publish"]["targets"].append("__leak__")
        self.assertNotIn("__leak__", b["publish"]["targets"])

    def test_init_user_profile_creates_then_preserves(self):
        target = os.path.join(self.tmp, "sub", "photogrammetry.json")
        # Creates (and makes parent dirs) when absent.
        out = pp.Profile.init_user_profile(target)
        self.assertEqual(out, target)
        self.assertTrue(os.path.isfile(target))
        with open(target, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["curate"]["sharpness_percentile"], 0)
        # Does NOT overwrite a user-edited profile on a second call.
        data["curate"]["sharpness_percentile"] = 99
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        pp.Profile.init_user_profile(target)  # force defaults False
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["curate"]["sharpness_percentile"], 99)
        # force=True rewrites the template.
        pp.Profile.init_user_profile(target, force=True)
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["curate"]["sharpness_percentile"], 0)

    def test_init_user_profile_default_location_under_config_root(self):
        # With no explicit path, it lands under the (temp) user-config root.
        out = pp.Profile.init_user_profile()
        self.assertTrue(out.startswith(self.tmp))
        self.assertTrue(os.path.isfile(out))

    def test_env_override_is_strict_across_every_finder(self):
        """A set-but-invalid app env var forces mock mode on EVERY engine.

        All five discovery functions document the same contract: the env var is
        the top of the chain and is *terminal* — setting it to an empty string
        or a nonexistent path yields None (the caller enters mock mode) rather
        than quietly falling through to the profile or a standard install. That
        is what makes ``FOO_EXE=`` a reliable way to force mock mode on a
        machine that has the real app installed.

        Pinned for all engines at once because they diverged: sugar used a
        truthy test (so ``SUGAR_DIR=`` fell through to ``apps.sugar_dir``) and
        Metashape used ``env and isfile(env)`` (so an invalid ``METASHAPE_EXE``
        silently resolved the real install).
        """
        from extapps.photogrammetry.gaussian_splat_workflow._gaussian_splat_workflow             import GaussianSplatWorkflow
        from extapps.photogrammetry.gaussian_splat_workflow._splat_publish             import SplatPublishWorkflow
        from extapps.photogrammetry.realityscan_workflow._realityscan_workflow             import RealityCaptureWorkflow
        from extapps.photogrammetry.sugar_mesh_workflow._sugar_mesh             import SugarMeshWorkflow
        from extapps.photogrammetry.metashape_workflow._metashape_connection             import MetashapeConnection

        # A profile whose apps.* all point at REAL paths — so any finder that
        # falls through instead of honoring the override returns non-None and
        # fails. sugar_dir must look like a SuGaR repo (holds the train script).
        real_exe = os.path.join(self.tmp, "real.exe")
        open(real_exe, "wb").close()
        sugar_repo = os.path.join(self.tmp, "sugar_repo")
        os.makedirs(sugar_repo, exist_ok=True)
        open(os.path.join(sugar_repo, "train_full_pipeline.py"), "wb").close()
        prof_path = self._write(
            {
                "apps": {
                    "brush_exe": real_exe,
                    "realityscan_exe": real_exe,
                    "metashape_exe": real_exe,
                    "sugar_dir": sugar_repo,
                }
            }
        )

        finders = {
            "BRUSH_EXE": GaussianSplatWorkflow.find_brush_exe,
            "SPLAT_TRANSFORM_EXE": SplatPublishWorkflow.find_splat_transform,
            "RC_EXE": RealityCaptureWorkflow.find_realitycapture_exe,
            "SUGAR_DIR": SugarMeshWorkflow.find_sugar_dir,
            "METASHAPE_EXE": MetashapeConnection.find_exe,
        }
        # Both flavours of "set but invalid" must terminate the chain.
        for bad in ("", os.path.join(self.tmp, "does_not_exist")):
            for env_var, finder in finders.items():
                with self.subTest(env=env_var, value=bad or "<empty>"):
                    with mock.patch.dict(os.environ), mock.patch(
                        "shutil.which", return_value=None
                    ):
                        os.environ[pp.PROFILE_ENV] = prof_path
                        os.environ[env_var] = bad
                        self.assertIsNone(finder())

    def test_no_personal_literals_in_shipped_source(self):
        # Lock the scrub: NOTHING shipped under photogrammetry/ (every .py module
        # AND the TUNING.md doc) may carry a machine / site / project-specific
        # literal. Scans the whole tree so a new module or doc can't quietly
        # reintroduce one (this is a public repo).
        import extapps
        pg = os.path.join(os.path.dirname(os.path.abspath(extapps.__file__)),
                          "photogrammetry")
        forbidden = (
            "O:/Cloud", "O:\\Cloud", "M:/photogrammetry", "M:\\photogrammetry",
            "M:/tools", "M:\\tools", "m3trik", "razer15", "Nextcloud", "Dropbox",
            "ComfyUI", "welding", "welded",
        )
        scanned = 0
        for root, _dirs, files in os.walk(pg):
            if "__pycache__" in root:
                continue
            for fn in files:
                if not (fn.endswith(".py") or fn.endswith(".md")):
                    continue
                path = os.path.join(root, fn)
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
                for bad in forbidden:
                    self.assertNotIn(
                        bad, text,
                        f"personal literal {bad!r} leaked into "
                        f"{os.path.relpath(path, pg)}",
                    )
                scanned += 1
        self.assertGreater(scanned, 8, "source scan unexpectedly found few files")

    def test_headless_import_pulls_no_qt(self):
        # The engine path runs inside Metashape's Qt-free Python 3.9; importing
        # the profile + prep stages must never drag in qtpy / PySide.
        code = (
            "import sys;"
            "import extapps.photogrammetry.profile;"
            "import extapps.photogrammetry.prep_stages;"
            "qt=[m for m in sys.modules if m.split('.')[0] in "
            "('qtpy','PySide2','PySide6','PyQt5','PyQt6')];"
            "sys.exit(1 if qt else 0)"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Qt imported by headless path:\n{proc.stderr}")


class ResolveAppPrecedenceTest(unittest.TestCase):
    """The ``Profile.resolve_app`` discovery chain, stage by stage.

    ``resolve_app`` is the single entry point for locating an external
    application (CLAUDE.md), and every engine's ``find_*`` is a thin declaration
    of what to feed it. The existing suite exercises it only *through* those
    engines, which pins the wiring but not the chain: ``config_key=None``, the
    fallback ordering, the validate/fallback asymmetry and the not-found tail
    have no coverage that way. This class drives the chain directly.

    Precedence, read off :meth:`Profile.resolve_app` (profile.py:317-331), is
    **env → profile → fallbacks**, with the env stage *terminal* — set at all
    decides the call, valid or not. There is no "explicit path" stage: the
    ``path`` parameter selects *which profile file* stage 2 reads, it does not
    supply a result.
    """

    def setUp(self):
        self._prev = {
            k: os.environ.get(k)
            for k in (CONFIG_ROOT_ENV_VAR, pp.PROFILE_ENV, "FAKE_APP_EXE")
        }
        # Managed scratch: allocation joins a swept prefix namespace, so an
        # abandoned dir (a hard kill mid-test) is reclaimed by age instead of
        # leaking. "scoped" — this test is the producer and outlives every
        # consumer, and a failure keeps the dir for inspection.
        self._tmp_store = ptk.TempArtifacts("extapps_test_profile", policy="scoped")
        self.tmp = self._tmp_store.dir_path()
        os.environ[CONFIG_ROOT_ENV_VAR] = self.tmp
        os.environ.pop(pp.PROFILE_ENV, None)
        os.environ.pop("FAKE_APP_EXE", None)
        self.calls = []

    def tearDown(self):
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp_store.cleanup()

    # ---------------------------------------------------------------- helpers
    def _file(self, name):
        """Create an existing file under the scratch dir; return its path."""
        path = os.path.join(self.tmp, name)
        with open(path, "wb"):
            pass
        return path

    def _profile_with(self, **apps):
        """Write a profile whose ``apps`` block carries *apps*; return its path."""
        path = os.path.join(self.tmp, "prof.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"apps": apps}, fh)
        return path

    def _recorder(self, tag, result):
        """A fallback that records that it ran, then returns *result*."""

        def _fallback():
            self.calls.append(tag)
            return result

        return _fallback

    # ------------------------------------------------------- stage 1: env var
    def test_env_wins_over_profile_and_fallbacks(self):
        env_exe = self._file("from_env.exe")
        prof = self._profile_with(fake_app_exe=self._file("from_profile.exe"))
        os.environ["FAKE_APP_EXE"] = env_exe
        got = pp.Profile.resolve_app(
            "FAKE_APP_EXE",
            "fake_app_exe",
            fallbacks=(self._recorder("fb", self._file("from_fallback.exe")),),
            path=prof,
        )
        self.assertEqual(got, env_exe)
        self.assertEqual(self.calls, [])  # later stages never consulted

    def test_env_set_but_invalid_is_terminal(self):
        """Set-but-invalid returns None instead of falling through — the
        property that lets ``FOO_EXE=`` force mock mode on a machine where the
        app is installed AND named in the profile."""
        prof = self._profile_with(fake_app_exe=self._file("real.exe"))
        for bad in ("", os.path.join(self.tmp, "nope.exe")):
            with self.subTest(value=bad or "<empty>"):
                self.calls.clear()
                os.environ["FAKE_APP_EXE"] = bad
                got = pp.Profile.resolve_app(
                    "FAKE_APP_EXE",
                    "fake_app_exe",
                    fallbacks=(self._recorder("fb", self._file("real.exe")),),
                    path=prof,
                )
                self.assertIsNone(got)
                self.assertEqual(self.calls, [])

    def test_unset_env_is_not_terminal(self):
        """Terminal means *set*, not *present-and-empty* — an unset var has to
        fall through, or no machine without the override could discover
        anything."""
        exe = self._file("configured.exe")
        prof = self._profile_with(fake_app_exe=exe)
        self.assertNotIn("FAKE_APP_EXE", os.environ)
        self.assertEqual(
            pp.Profile.resolve_app("FAKE_APP_EXE", "fake_app_exe", path=prof), exe
        )

    # -------------------------------------------------------- stage 2: profile
    def test_profile_value_wins_over_fallbacks(self):
        exe = self._file("configured.exe")
        prof = self._profile_with(fake_app_exe=exe)
        got = pp.Profile.resolve_app(
            "FAKE_APP_EXE",
            "fake_app_exe",
            fallbacks=(self._recorder("fb", self._file("standard.exe")),),
            path=prof,
        )
        self.assertEqual(got, exe)
        self.assertEqual(self.calls, [])

    def test_invalid_profile_value_falls_through_to_fallbacks(self):
        """The offline-network-share case: configured but not reachable, so
        discovery continues rather than reporting the app missing."""
        standard = self._file("standard.exe")
        prof = self._profile_with(fake_app_exe=os.path.join(self.tmp, "gone.exe"))
        got = pp.Profile.resolve_app(
            "FAKE_APP_EXE",
            "fake_app_exe",
            fallbacks=(self._recorder("fb", standard),),
            path=prof,
        )
        self.assertEqual(got, standard)
        self.assertEqual(self.calls, ["fb"])

    def test_no_config_key_skips_the_profile_stage_entirely(self):
        """``config_key=None`` (splat-transform has no profile key) must not
        read the profile at all — not read it and find nothing."""
        standard = self._file("standard.exe")
        with mock.patch.object(
            pp.Profile, "configured_app_path", side_effect=AssertionError("consulted")
        ):
            got = pp.Profile.resolve_app(
                "FAKE_APP_EXE", None, fallbacks=(self._recorder("fb", standard),)
            )
        self.assertEqual(got, standard)
        self.assertEqual(self.calls, ["fb"])

    def test_path_selects_which_profile_stage_two_reads(self):
        """*path* is forwarded to configured_app_path — it names a profile file,
        it is not itself a result."""
        a, b = self._file("a.exe"), self._file("b.exe")
        prof_a = os.path.join(self.tmp, "a.json")
        prof_b = os.path.join(self.tmp, "b.json")
        for target, exe in ((prof_a, a), (prof_b, b)):
            with open(target, "w", encoding="utf-8") as fh:
                json.dump({"apps": {"fake_app_exe": exe}}, fh)
        self.assertEqual(
            pp.Profile.resolve_app("FAKE_APP_EXE", "fake_app_exe", path=prof_a), a
        )
        self.assertEqual(
            pp.Profile.resolve_app("FAKE_APP_EXE", "fake_app_exe", path=prof_b), b
        )

    # ------------------------------------------------------ stage 3: fallbacks
    def test_fallbacks_run_in_order_and_stop_at_the_first_hit(self):
        second = self._file("second.exe")
        got = pp.Profile.resolve_app(
            "FAKE_APP_EXE",
            None,
            fallbacks=(
                self._recorder("first", None),
                self._recorder("second", second),
                self._recorder("third", self._file("third.exe")),
            ),
        )
        self.assertEqual(got, second)
        self.assertEqual(self.calls, ["first", "second"])  # third never ran

    def test_fallback_results_are_not_validated(self):
        """Documented asymmetry: *validate* guards stages 1-2 only. A fallback
        owns its own validation because what counts as valid differs per engine
        (a file for an exe, a dir holding a train script for SuGaR), so whatever
        it returns is taken as-is."""
        ghost = os.path.join(self.tmp, "never_existed.exe")
        self.assertFalse(os.path.exists(ghost))
        self.assertEqual(
            pp.Profile.resolve_app("FAKE_APP_EXE", None, fallbacks=(lambda: ghost,)),
            ghost,
        )

    def test_not_found_returns_none_after_exhausting_every_stage(self):
        prof = self._profile_with(fake_app_exe=os.path.join(self.tmp, "gone.exe"))
        got = pp.Profile.resolve_app(
            "FAKE_APP_EXE",
            "fake_app_exe",
            fallbacks=(self._recorder("a", None), self._recorder("b", None)),
            path=prof,
        )
        self.assertIsNone(got)
        self.assertEqual(self.calls, ["a", "b"])

    def test_no_fallbacks_is_a_valid_chain(self):
        self.assertIsNone(pp.Profile.resolve_app("FAKE_APP_EXE", None))

    # --------------------------------------------------------------- validate
    def test_custom_validate_governs_stages_one_and_two(self):
        """The SuGaR shape: the target is a *directory* holding a marker file,
        so isfile would reject it at both stages."""
        repo = os.path.join(self.tmp, "sugar_repo")
        os.makedirs(repo, exist_ok=True)
        with open(os.path.join(repo, "train_full_pipeline.py"), "wb"):
            pass
        is_repo = lambda p: os.path.isfile(  # noqa: E731
            os.path.join(p, "train_full_pipeline.py")
        )
        prof = self._profile_with(fake_app_dir=repo)

        # stage 2 accepts it with the custom predicate, rejects it with the default
        self.assertEqual(
            pp.Profile.resolve_app(
                "FAKE_APP_EXE", "fake_app_dir", validate=is_repo, path=prof
            ),
            repo,
        )
        self.assertIsNone(
            pp.Profile.resolve_app("FAKE_APP_EXE", "fake_app_dir", path=prof)
        )
        # stage 1 uses the same predicate
        os.environ["FAKE_APP_EXE"] = repo
        self.assertEqual(
            pp.Profile.resolve_app("FAKE_APP_EXE", None, validate=is_repo), repo
        )
        self.assertIsNone(pp.Profile.resolve_app("FAKE_APP_EXE", None))

    def test_default_validate_is_resolved_per_call_not_bound_at_import(self):
        """Documented: ``validate = validate or os.path.isfile`` runs per call,
        so a patched ``os.path.isfile`` is honoured. Binding it at import would
        make every engine's discovery unmockable."""
        ghost = os.path.join(self.tmp, "ghost.exe")
        os.environ["FAKE_APP_EXE"] = ghost
        self.assertIsNone(pp.Profile.resolve_app("FAKE_APP_EXE", None))
        with mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(pp.Profile.resolve_app("FAKE_APP_EXE", None), ghost)

    # ---------------------------------------------------------------- caching
    def test_resolution_is_not_cached(self):
        """There is no caching anywhere in the chain (``resolve_app`` reads
        ``os.environ`` per call and ``UserConfig.resolve`` re-reads the file), and
        the panels depend on that: 'Download Brush' installs into the managed
        catalog and the very next availability check has to see it. A cache here
        would make a freshly installed engine read as missing until restart."""
        exe = self._file("late.exe")
        prof_missing = self._profile_with(fake_app_exe=os.path.join(self.tmp, "x.exe"))
        self.assertIsNone(
            pp.Profile.resolve_app("FAKE_APP_EXE", "fake_app_exe", path=prof_missing)
        )
        # Same arguments, newly-appearing install -> found, no restart needed.
        prof_found = self._profile_with(fake_app_exe=exe)
        self.assertEqual(
            pp.Profile.resolve_app("FAKE_APP_EXE", "fake_app_exe", path=prof_found), exe
        )
        # And an env var set after the first call takes effect immediately.
        os.environ["FAKE_APP_EXE"] = ""
        self.assertIsNone(
            pp.Profile.resolve_app("FAKE_APP_EXE", "fake_app_exe", path=prof_found)
        )

    def test_bad_profile_does_not_break_the_chain(self):
        """A malformed profile must degrade to 'no configured path', not raise —
        the panel availability check runs this on every open."""
        prof = os.path.join(self.tmp, "broken.json")
        with open(prof, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        standard = self._file("standard.exe")
        got = pp.Profile.resolve_app(
            "FAKE_APP_EXE",
            "fake_app_exe",
            fallbacks=(self._recorder("fb", standard),),
            path=prof,
        )
        self.assertEqual(got, standard)


class DiscoverSourceDirsTest(unittest.TestCase):
    """``Profile.discover_source_dirs`` — the other I/O entry point in profile.py.

    Both ``run_combined`` drivers call it to expand ``--input-root`` into the
    per-capture subdirs of a batch run, so a silent miss there drops a capture
    from the batch.
    """

    def setUp(self):
        self._store = ptk.TempArtifacts("extapps_test_sources", policy="scoped")
        self.root = self._store.dir_path()

    def tearDown(self):
        self._store.cleanup()

    def _sub(self, name, *files):
        path = os.path.join(self.root, name)
        os.makedirs(path, exist_ok=True)
        for fn in files:
            with open(os.path.join(path, fn), "wb"):
                pass
        return path

    def test_returns_only_image_bearing_immediate_subdirs_sorted(self):
        b = self._sub("b_capture", "shot.JPG")  # extension match is case-insensitive
        a = self._sub("a_capture", "frame.png")
        self._sub("notes", "readme.txt")  # no images -> skipped
        with open(os.path.join(self.root, "loose.jpg"), "wb"):
            pass  # a file at the root is not a source dir
        self.assertEqual(pp.Profile.discover_source_dirs(self.root), [a, b])

    def test_does_not_recurse(self):
        """Only *immediate* subdirs: images one level deeper do not promote the
        parent, which is what keeps an already-processed output tree out of a
        batch."""
        outer = os.path.join(self.root, "outer")
        os.makedirs(os.path.join(outer, "inner"), exist_ok=True)
        with open(os.path.join(outer, "inner", "frame.jpg"), "wb"):
            pass
        self.assertEqual(pp.Profile.discover_source_dirs(self.root), [])

    def test_every_declared_extension_is_recognized(self):
        expected = []
        for i, ext in enumerate(pp.IMAGE_EXTS):
            expected.append(self._sub(f"cap{i}", f"frame{ext}"))
        self.assertEqual(pp.Profile.discover_source_dirs(self.root), sorted(expected))

    def test_missing_root_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            pp.Profile.discover_source_dirs(os.path.join(self.root, "absent"))
        self.assertIn("input-root does not exist", str(ctx.exception))

    def test_empty_root_is_empty_not_an_error(self):
        self.assertEqual(pp.Profile.discover_source_dirs(self.root), [])


if __name__ == "__main__":
    unittest.main()
