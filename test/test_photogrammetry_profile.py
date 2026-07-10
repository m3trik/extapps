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
        prof = pp.get_profile()
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
        prof = pp.get_profile(path)
        self.assertEqual(prof["input_root"], "Z:/g/input")
        self.assertEqual(prof["metashape_output_root"], "Z:/g/metashape")
        self.assertEqual(prof["realityscan_scratch_root"], "Y:/s/rc_out")
        self.assertEqual(prof["gsplat_scratch_root"], "Y:/s/gsplat_out")

    def test_partial_profile_deep_merges_over_default(self):
        path = self._write({"curate": {"hash_threshold": 13}})
        prof = pp.get_profile(path)
        self.assertEqual(prof["curate"]["hash_threshold"], 13)        # overridden
        self.assertEqual(prof["curate"]["sharpness_percentile"], 0)  # default kept
        self.assertEqual(prof["equalize"]["reference"], "median")     # default branch kept

    def test_env_pointer_resolves(self):
        path = self._write({"graphics_root": "E:/env"})
        os.environ[pp.PROFILE_ENV] = path
        prof = pp.get_profile()
        self.assertEqual(prof["graphics_root"], "E:/env")

    def test_configured_app_path_reads_and_expands_apps(self):
        """apps.<key> is the network-install hook: configured_app_path returns it
        expanded; an unset key is None; '${ENV}' is expanded on read."""
        exe = os.path.join(self.tmp, "net", "metashape.exe")
        path = self._write({"apps": {"metashape_exe": exe,
                                     "sugar_dir": "${SUGAR_TEST_ROOT}/repo"}})
        self.assertEqual(pp.configured_app_path("metashape_exe", path), exe)
        self.assertIsNone(pp.configured_app_path("brush_exe", path))  # unset -> None
        os.environ["SUGAR_TEST_ROOT"] = self.tmp
        try:
            got = pp.configured_app_path("sugar_dir", path)
        finally:
            os.environ.pop("SUGAR_TEST_ROOT", None)
        self.assertTrue(got.startswith(self.tmp))
        self.assertTrue(got.replace("\\", "/").endswith("/repo"))

    def test_configured_app_path_swallows_bad_profile(self):
        """A malformed / unreadable profile must not break app discovery —
        configured_app_path returns None so the caller falls through to standard
        discovery rather than crashing the availability check."""
        from unittest import mock
        with mock.patch.object(pp, "get_profile", side_effect=ValueError("boom")):
            self.assertIsNone(pp.configured_app_path("metashape_exe"))

    def test_discovery_consults_profile_app_override(self):
        """A discovery function (Brush here) falls back to apps.<key> when its env
        var is unset and the app isn't on PATH (the network-install path), and a
        configured-but-missing path falls through to mock mode (offline share)."""
        from unittest import mock
        from extapps.photogrammetry.gaussian_splat_workflow._gaussian_splat_workflow \
            import find_brush_exe
        fake = os.path.join(self.tmp, "brush_app.exe")
        open(fake, "wb").close()

        prof_path = self._write({"apps": {"brush_exe": fake}})
        with mock.patch.dict(os.environ), \
                mock.patch("shutil.which", return_value=None):
            os.environ.pop("BRUSH_EXE", None)        # env unset -> profile consulted
            os.environ[pp.PROFILE_ENV] = prof_path   # active profile = our temp one
            self.assertEqual(find_brush_exe(), fake)

        # Configured but missing -> falls through (here to PATH, mocked empty).
        prof_path = self._write(
            {"apps": {"brush_exe": os.path.join(self.tmp, "gone.exe")}}
        )
        with mock.patch.dict(os.environ), \
                mock.patch("shutil.which", return_value=None):
            os.environ.pop("BRUSH_EXE", None)
            os.environ[pp.PROFILE_ENV] = prof_path
            self.assertIsNone(find_brush_exe())

    def test_example_and_default_share_one_schema(self):
        # Lock the DRY refactor: the copy-me example and the packaged default are
        # both built from the same skeleton, so their derived roots + tuning must
        # match exactly (only the two base roots and the example's _comment differ).
        example = {k: v for k, v in pp.EXAMPLE_PROFILE.items() if k != "_comment"}
        default = pp._packaged_default()
        self.assertEqual(set(example), set(default))
        for k in pp._DERIVED_ROOT_KEYS:
            self.assertEqual(example[k], default[k])  # identical templates
        for block in ("apps", "curate", "equalize", "gsplat", "reconstruct"):
            self.assertEqual(example[block], default[block])  # identical tuning

    def test_get_preset_resolves_builtin_and_validates(self):
        # None / sentinel names are a no-op overlay (runners keep plain defaults).
        for noop in (None, "", "none", "None", "default"):
            self.assertEqual(pp.get_preset(noop, "metashape"), {})
        # The shipped built-in resolves (user tier is empty under the temp root)
        # with the _comment stripped, carrying the corrected specular values.
        sm = pp.get_preset("specular_metal", "metashape")
        self.assertNotIn("_comment", sm)
        self.assertEqual(sm["depth_filter"], "moderate")
        self.assertEqual(sm["align_downscale"], 2)
        self.assertEqual(sm["depth_downscale"], 2)  # ds2, not ds1 (ds1 over-fits)
        self.assertTrue(sm["mask_background"])
        self.assertNotIn("min_component_size", sm)  # cranking cleanup isn't the fix
        # A typo is rejected (not silently run with defaults); message lists names.
        with self.assertRaises(ValueError) as ctx:
            pp.get_preset("speculor_metl", "metashape")
        self.assertIn("specular_metal", str(ctx.exception))

    def test_user_preset_shadows_builtin(self):
        # A user-saved preset of the same name wins over the shipped built-in
        # (writes under the temp config root set in setUp).
        pp.preset_store("metashape").save("specular_metal", {"depth_filter": "aggressive"})
        self.assertEqual(
            pp.get_preset("specular_metal", "metashape")["depth_filter"], "aggressive"
        )

    def test_presets_are_engine_scoped(self):
        # A preset saved for one engine must NOT appear in another engine's store
        # (the whole point of per-engine scoping: a Metashape save isn't an RC one).
        pp.preset_store("metashape").save("my_rig", {"tiepoint_limit": 20000})
        self.assertIn("my_rig", pp.preset_store("metashape").list())
        self.assertNotIn("my_rig", pp.preset_store("realityscan").list())
        with self.assertRaises(ValueError):
            pp.get_preset("my_rig", "realityscan")

    def test_tuning_blocks_isolated_per_profile(self):
        # deepcopy in _skeleton: mutating one resolved profile's nested tuning
        # (e.g. the publish.targets list) must not bleed into another.
        a = pp.get_profile()
        b = pp.get_profile()
        a["publish"]["targets"].append("__leak__")
        self.assertNotIn("__leak__", b["publish"]["targets"])

    def test_init_user_profile_creates_then_preserves(self):
        target = os.path.join(self.tmp, "sub", "photogrammetry.json")
        # Creates (and makes parent dirs) when absent.
        out = pp.init_user_profile(target)
        self.assertEqual(out, target)
        self.assertTrue(os.path.isfile(target))
        with open(target, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["curate"]["sharpness_percentile"], 0)
        # Does NOT overwrite a user-edited profile on a second call.
        data["curate"]["sharpness_percentile"] = 99
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        pp.init_user_profile(target)  # force defaults False
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["curate"]["sharpness_percentile"], 99)
        # force=True rewrites the template.
        pp.init_user_profile(target, force=True)
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["curate"]["sharpness_percentile"], 0)

    def test_init_user_profile_default_location_under_config_root(self):
        # With no explicit path, it lands under the (temp) user-config root.
        out = pp.init_user_profile()
        self.assertTrue(out.startswith(self.tmp))
        self.assertTrue(os.path.isfile(out))

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


if __name__ == "__main__":
    unittest.main()
