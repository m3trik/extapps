#!/usr/bin/python
# coding=utf-8
"""Tests for PackerSlots channel packing.

Regression guard for the conversion branch of ``_pack_set``: when a
requested channel map is absent but derivable from another present map
(e.g. Smoothness from Roughness), the slot must convert and pack it.
The line that did this called ``self.get_converted_map`` — a static that
lives on ``MapFactory``, not on ``ImgUtils`` (the slot's base) — so it
raised ``AttributeError`` and the conversion path never worked.

The heavy UI wiring in ``__init__`` is bypassed (``__new__``); ``_pack_set``
touches no UI, so it is exercised directly.
"""
import io
import os
import types
import tempfile
import shutil
import unittest
import contextlib
from unittest import mock

from PIL import Image

from pythontk import ImgUtils

from extapps.texture_maps.packer.slots import PackerSlots


class TestMapPackerConversion(unittest.TestCase):
    """``_pack_set`` derives missing channels from convertible maps."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="packer_test_")
        # Only a Roughness map is present; Smoothness must be derived from it.
        cls.roughness = os.path.join(cls.test_dir, "mat_Roughness.png")
        ImgUtils.save_image(
            ImgUtils.create_image("L", (8, 8), 64), cls.roughness
        )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def test_pack_set_converts_missing_channel(self):
        """Smoothness absent → converted from Roughness, packed, file written."""
        inst = self._bare_slots()
        # R=Smoothness (must convert), G/B/A=None.
        combos = ["Smoothness", "None", "None", "None"]
        result = inst._pack_set(
            base_name="mat",
            files=[self.roughness],
            combos=combos,
            suffix="_Test",
            ext="png",
            fmt="PNG",
        )
        self.assertTrue(result)
        out = os.path.join(self.test_dir, "mat_Test.png")
        self.assertTrue(os.path.isfile(out), f"expected packed output at {out}")

    def test_pack_set_no_assignable_channels(self):
        """All channels None → nothing assigned, returns False, no file."""
        inst = self._bare_slots()
        combos = ["None", "None", "None", "None"]
        result = inst._pack_set(
            base_name="mat",
            files=[self.roughness],
            combos=combos,
            suffix="_Empty",
            ext="png",
            fmt="PNG",
        )
        self.assertFalse(result)
        self.assertFalse(
            os.path.isfile(os.path.join(self.test_dir, "mat_Empty.png"))
        )


class TestMapPackerCompleteness(unittest.TestCase):
    """``_pack_set`` only packs complete sets unless the Missing Maps rule allows it.

    Regression: an unresolvable channel map used to be reported and skipped,
    but whatever had already been assigned was still packed — writing a map
    whose missing channels are filled with a constant, indistinguishable
    downstream from a legitimately flat channel. The default is now to skip
    the whole set; the header's 'Missing Maps' policy opts back in, either
    always (``force``) or only when 2+ channels resolved (``multi``).
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="packer_complete_")
        # Roughness only — Metallic is neither present nor derivable from it.
        # Smoothness IS derivable from Roughness (inversion), so a set asking
        # for Roughness+Smoothness+Metallic resolves 2 of 3 channels.
        cls.roughness = os.path.join(cls.test_dir, "mat_Roughness.png")
        ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), 64), cls.roughness)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def _pack(self, suffix, combos, **kwargs):
        return self._bare_slots()._pack_set(
            base_name="mat",
            files=[self.roughness],
            combos=combos,
            suffix=suffix,
            ext="png",
            fmt="PNG",
            **kwargs,
        )

    def _path(self, suffix):
        return os.path.join(self.test_dir, f"mat{suffix}.png")

    def _written(self, suffix):
        return os.path.isfile(self._path(suffix))

    # One channel resolves, one doesn't. Channel ORDER is load-bearing here:
    # the old code stopped at the first unresolvable channel and packed
    # whatever preceded it, so only the resolvable-first layout exposes the
    # partial write. The missing-first layout instead proves the packing rules
    # keep resolving channels *past* the gap (the old break never did).
    RESOLVABLE_FIRST = ["Roughness", "Metallic", "None", "None"]
    MISSING_FIRST = ["Metallic", "Roughness", "None", "None"]
    # Two resolve (Roughness directly, Smoothness by conversion), one doesn't.
    TWO_OF_THREE = ["Roughness", "Smoothness", "Metallic", "None"]

    def test_incomplete_set_skipped_by_default(self):
        """Caller omits the rule → safe default, nothing written."""
        self.assertFalse(self._pack("_Default", self.RESOLVABLE_FIRST))
        self.assertFalse(self._written("_Default"))

    def test_incomplete_set_skipped_under_skip_rule(self):
        self.assertFalse(
            self._pack("_Skip", self.RESOLVABLE_FIRST, rule=PackerSlots.MISSING_SKIP)
        )
        self.assertFalse(self._written("_Skip"))

    def test_incomplete_set_packed_under_force_rule(self):
        """Pack Anyway → resolution continues past the gap, missing channels fill."""
        self.assertTrue(
            self._pack("_Forced", self.MISSING_FIRST, rule=PackerSlots.MISSING_FORCE)
        )
        self.assertTrue(self._written("_Forced"))

    def test_multi_rule_skips_single_resolved_channel(self):
        """Pack If 2+ Maps → one resolved channel isn't enough."""
        self.assertFalse(
            self._pack(
                "_MultiOne", self.RESOLVABLE_FIRST, rule=PackerSlots.MISSING_MULTI
            )
        )
        self.assertFalse(self._written("_MultiOne"))

    def test_multi_rule_packs_two_resolved_channels(self):
        """Pack If 2+ Maps → two resolved channels pack despite the third missing."""
        self.assertTrue(
            self._pack("_MultiTwo", self.TWO_OF_THREE, rule=PackerSlots.MISSING_MULTI)
        )
        self.assertTrue(self._written("_MultiTwo"))

    def test_complete_set_packs_under_every_rule(self):
        """A set with no missing maps is unaffected by the policy."""
        for rule in (
            PackerSlots.MISSING_SKIP,
            PackerSlots.MISSING_MULTI,
            PackerSlots.MISSING_FORCE,
        ):
            with self.subTest(rule=rule):
                suffix = f"_Complete_{rule}"
                self.assertTrue(
                    self._pack(suffix, ["Roughness", "None", "None", "None"], rule=rule)
                )
                self.assertTrue(self._written(suffix))

    def test_wholly_unresolvable_set_is_reported_not_silent(self):
        """No channel resolves → skipped WITH a reason, under every rule.

        The empty-assignment early-out used to return before the missing-map
        report, so a set whose *only* requested map was absent dropped out
        with no per-set explanation at all. 'Pack Anyway' must also land here
        rather than in ``pack_channels``, which raises on an empty assignment.
        """
        for rule in (
            PackerSlots.MISSING_SKIP,
            PackerSlots.MISSING_MULTI,
            PackerSlots.MISSING_FORCE,
        ):
            with self.subTest(rule=rule):
                suffix = f"_NoneResolved_{rule}"
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    result = self._pack(
                        suffix, ["Metallic", "None", "None", "None"], rule=rule
                    )
                self.assertFalse(result)
                self.assertFalse(self._written(suffix))
                self.assertIn("Metallic", buf.getvalue())
                self.assertIn("mat", buf.getvalue())

    def test_output_mode_follows_the_configured_layout(self):
        """Channel count comes from the layout, not from what happened to resolve.

        A 3-channel layout (ORM / MRAO — A on 'None') must stay RGB, which is
        the point of those formats. Conversely a force-packed set whose alpha
        map is missing still writes RGBA, so one batch can't emit a mix of RGB
        and RGBA files under a single suffix.
        """
        self.assertTrue(
            self._pack("_RGB", ["Metallic", "Roughness", "Smoothness", "None"],
                       rule=PackerSlots.MISSING_FORCE)
        )
        self.assertEqual(Image.open(self._path("_RGB")).mode, "RGB")

        # A requested but unresolvable (Metallic) -> still RGBA, alpha filled.
        self.assertTrue(
            self._pack("_RGBA", ["Roughness", "Smoothness", "None", "Metallic"],
                       rule=PackerSlots.MISSING_FORCE)
        )
        self.assertEqual(Image.open(self._path("_RGBA")).mode, "RGBA")

    def test_rule_reads_header_combo(self):
        """``_missing_map_rule`` mirrors the header combo; safe default if absent."""
        inst = self._bare_slots()
        # Header menu not built yet (bare instance) → safe default.
        inst.ui = types.SimpleNamespace()
        self.assertEqual(inst._missing_map_rule(), PackerSlots.MISSING_SKIP)

        combo = _FakeDataCombo(PackerSlots.MISSING_FORCE)
        inst.ui = types.SimpleNamespace(
            header=types.SimpleNamespace(
                menu=types.SimpleNamespace(cmb_missing=combo)
            )
        )
        self.assertEqual(inst._missing_map_rule(), PackerSlots.MISSING_FORCE)
        # No selection (currentData() -> None) must not disable the guard.
        combo.data = None
        self.assertEqual(inst._missing_map_rule(), PackerSlots.MISSING_SKIP)


class TestMapPackerChannelSelection(unittest.TestCase):
    """The channel layout is read once, in channel order, and gates both batches."""

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def test_channel_combos_read_in_channel_order(self):
        inst = self._bare_slots()
        picks = ["Metallic", "Roughness", "Ambient_Occlusion", "Smoothness"]
        inst.ui = types.SimpleNamespace(
            **{f"cmb{c}": _FakeCombo(current=p) for c, p in zip("RGBA", picks)}
        )
        self.assertEqual(inst._channel_combos(), picks)

    def test_empty_selection_is_reported_and_blocks_the_batch(self):
        """All channels 'None' → the run stops before the file dialog.

        Otherwise both batches walk the whole selection to no effect and
        report every set as skipped, blaming the files for an empty layout.
        """
        inst = self._bare_slots()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            allowed = inst._require_channel_selection(["None"] * 4)
        self.assertFalse(allowed)
        self.assertIn("No channels assigned", buf.getvalue())

    def test_partial_selection_passes(self):
        inst = self._bare_slots()
        self.assertTrue(
            inst._require_channel_selection(["None", "Roughness", "None", "None"])
        )


class TestMapPackerUnpack(unittest.TestCase):
    """``_unpack_one`` splits a packed texture into per-channel maps."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="packer_unpack_")
        # An RGB packed map (no alpha), distinct per channel so outputs differ.
        cls.packed = os.path.join(cls.test_dir, "mat_ORM.png")
        ImgUtils.save_image(
            ImgUtils.create_image("RGB", (8, 8), (10, 120, 240)), cls.packed
        )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def test_unpack_one_extracts_assigned_channels(self):
        """Each non-None channel → a per-channel map named by its map type;
        an absent channel (A on an RGB input) is skipped without error."""
        inst = self._bare_slots()
        combos = ["Ambient_Occlusion", "Roughness", "Metallic", "Smoothness"]
        result = inst._unpack_one(
            file=self.packed, combos=combos, ext="png", fmt="PNG"
        )
        self.assertTrue(result)
        for suffix in ("_Ambient_Occlusion", "_Roughness", "_Metallic"):
            out = os.path.join(self.test_dir, f"mat{suffix}.png")
            self.assertTrue(os.path.isfile(out), f"expected {out}")
        # A was requested (Smoothness) but the source is RGB → no alpha output.
        self.assertFalse(
            os.path.isfile(os.path.join(self.test_dir, "mat_Smoothness.png"))
        )

    def test_unpack_one_all_none(self):
        """All channels None → nothing extracted, returns False."""
        inst = self._bare_slots()
        result = inst._unpack_one(
            file=self.packed,
            combos=["None", "None", "None", "None"],
            ext="png",
            fmt="PNG",
        )
        self.assertFalse(result)


class TestMapPackerSelectRemembersDir(unittest.TestCase):
    """``_select_textures`` re-seeds ``source_dir`` from the picked files.

    Regression: the packer only rewrote ``source_dir`` in ``_finish_batch``
    (to the *output* dir, on success), so after the user browsed to a new
    folder the next dialog reopened at the stale seed dir. The sibling
    ``ConverterSlots`` re-seeds after every selection; the packer must too.
    """

    class _FakeSwitchboard:
        def __init__(self, returns):
            self._returns = returns
            self.start_dir = None

        def file_dialog(self, *, file_types, title, start_dir, allow_multiple):
            self.start_dir = start_dir
            return self._returns

    @classmethod
    def _bare_slots(cls, returns):
        inst = PackerSlots.__new__(PackerSlots)
        inst._source_dir = "O:/seed/dir"
        inst.sb = cls._FakeSwitchboard(returns)
        return inst

    def test_selection_updates_source_dir(self):
        picked = ["O:/new/folder/mat_Roughness.png"]
        inst = self._bare_slots(picked)
        result = inst._select_textures("pick")
        self.assertEqual(result, picked)
        # Dialog opened at the old seed; source_dir now points at the pick.
        self.assertEqual(inst.sb.start_dir, "O:/seed/dir")
        self.assertEqual(inst.source_dir.replace("\\", "/"), "O:/new/folder")

    def test_cancel_leaves_source_dir_unchanged(self):
        inst = self._bare_slots([])
        inst._select_textures("pick")
        self.assertEqual(inst.source_dir, "O:/seed/dir")


class TestMapPackerPresets(unittest.TestCase):
    """Built-in presets cover the standard grayscale channel layouts."""

    def test_grayscale_pack_presets_present(self):
        names = list(PackerSlots.BUILTIN_PRESETS)
        for expected in (
            "ORM (Unreal, glTF)",
            "MRAO (Metallic, Roughness, AO)",
            "MSAO (HDRP Mask Map)",
            "Metallic Smoothness (URP)",
        ):
            self.assertIn(expected, names)

    def test_mrao_preset_layout(self):
        mrao = PackerSlots.BUILTIN_PRESETS["MRAO (Metallic, Roughness, AO)"]
        self.assertEqual(
            (mrao["R"], mrao["G"], mrao["B"], mrao["A"]),
            ("Metallic", "Roughness", "Ambient_Occlusion", "None"),
        )

    def test_three_channel_presets_pack_to_the_declared_layout(self):
        """ORM / MRAO round-trip: 3-channel RGB, each map in its named channel.

        Locks the layouts against ``pythontk.MapRegistry``'s ``MapType.channels``
        (the ecosystem SSoT that blendertk's material builder also reads), and
        that they stay RGB — no alpha is what lets these compress as BC1 rather
        than BC3/BC7, and it is the whole point of the format.
        """
        expected = {  # preset -> (R, G, B) source values, per the SSoT layout
            "ORM (Unreal, glTF)": (50, 100, 200),  # AO, Roughness, Metallic
            "MRAO (Metallic, Roughness, AO)": (200, 100, 50),  # M, R, AO
        }
        values = {"Metallic": 200, "Roughness": 100, "Ambient_Occlusion": 50}

        test_dir = tempfile.mkdtemp(prefix="packer_preset_")
        self.addCleanup(shutil.rmtree, test_dir, ignore_errors=True)
        files = []
        for map_type, value in values.items():
            path = os.path.join(test_dir, f"mat_{map_type}.png")
            ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), value), path)
            files.append(path)

        inst = PackerSlots.__new__(PackerSlots)
        for name, rgb in expected.items():
            with self.subTest(preset=name):
                preset = PackerSlots.BUILTIN_PRESETS[name]
                self.assertTrue(
                    inst._pack_set(
                        base_name="mat",
                        files=files,
                        combos=[preset[c] for c in "RGBA"],
                        suffix=preset["suffix"],
                        ext=preset["format"].lower(),
                        fmt=preset["format"],
                    )
                )
                out = os.path.join(test_dir, f"mat{preset['suffix']}.png")
                with Image.open(out) as img:
                    self.assertEqual(img.mode, "RGB")
                    self.assertEqual(img.getpixel((0, 0)), rgb)


class _FakeCombo:
    """Minimal QComboBox stand-in for exercising slot handlers off-screen."""

    def __init__(self, items=None, current="None"):
        self._items = list(items or [])
        self._current = current
        self._enabled = True

    def currentText(self):
        return self._current

    def setEnabled(self, value):
        self._enabled = bool(value)

    def isEnabled(self):
        return self._enabled

    def findText(self, text):
        return self._items.index(text) if text in self._items else -1

    def setCurrentIndex(self, index):
        if 0 <= index < len(self._items):
            self._current = self._items[index]


class _FakeDataCombo:
    """Minimal data-carrying QComboBox stand-in for the Missing Maps option."""

    def __init__(self, data=None):
        self.data = data

    def currentData(self):
        return self.data


class _FakeUI:
    """Bare namespace exposing the widgets ``_on_format_changed`` touches."""

    def __init__(self, cmbA, mode):
        self.cmbA = cmbA
        header = types.SimpleNamespace()
        header.menu = types.SimpleNamespace()
        header.menu.cmb_mode = _FakeCombo(items=["Pack", "Unpack"], current=mode)
        self.header = header


class TestMapPackerFormatAlphaGuard(unittest.TestCase):
    """``_on_format_changed`` must not clear the alpha combo while unpacking.

    Regression: the format combo's ``currentTextChanged`` fires in both modes.
    Selecting an alpha-less output format (JPG) disabled cmbA and reset it to
    'None' unconditionally — silently dropping the channel the user chose to
    *extract* in Unpack mode. The guard mirrors ``_on_mode_changed``: format
    only constrains alpha in Pack mode.
    """

    @staticmethod
    def _slots(mode, alpha_choice):
        inst = PackerSlots.__new__(PackerSlots)
        cmbA = _FakeCombo(items=PackerSlots.grayscale_types, current=alpha_choice)
        inst.ui = _FakeUI(cmbA, mode)
        return inst, cmbA

    def test_unpack_mode_keeps_alpha_selection_on_jpg(self):
        inst, cmbA = self._slots("Unpack", "Smoothness")
        inst._on_format_changed("JPG")
        # Alpha combo stays enabled and its extraction choice is untouched.
        self.assertTrue(cmbA.isEnabled())
        self.assertEqual(cmbA.currentText(), "Smoothness")

    def test_pack_mode_clears_alpha_on_jpg(self):
        inst, cmbA = self._slots("Pack", "Smoothness")
        inst._on_format_changed("JPG")
        # Pack mode still constrains alpha to the output format's capabilities.
        self.assertFalse(cmbA.isEnabled())
        self.assertEqual(cmbA.currentText(), "None")

    def test_pack_mode_keeps_alpha_on_png(self):
        inst, cmbA = self._slots("Pack", "Smoothness")
        inst._on_format_changed("PNG")
        self.assertTrue(cmbA.isEnabled())
        self.assertEqual(cmbA.currentText(), "Smoothness")


class TestMapPackerOpenOutputDirSafety(unittest.TestCase):
    """``b001`` opens the output dir via a non-shell launcher (no injection).

    Regression: the old handler built ``os.system(f'open "{output_dir}"')`` /
    ``xdg-open`` strings, so a directory named e.g. ``foo$(touch pwned)`` was
    passed through /bin/sh. The fix delegates to ``FileUtils.open_explorer``,
    which passes the path as a single argv entry — shell metacharacters are
    inert and ``os.system`` is never used.
    """

    def test_open_output_dir_delegates_to_non_shell_launcher(self):
        inst = PackerSlots.__new__(PackerSlots)
        malicious = 'O:/foo$(touch pwned)/out'
        inst._last_output_dir = malicious

        with mock.patch("os.path.isdir", return_value=True), mock.patch(
            "os.system"
        ) as system_mock, mock.patch(
            "extapps.texture_maps.packer.slots.FileUtils.open_explorer",
            return_value=True,
        ) as open_mock:
            inst.b001()

        # No shell was spawned; the raw path went to the safe launcher intact.
        system_mock.assert_not_called()
        open_mock.assert_called_once_with(malicious)

    def test_open_output_dir_noop_without_output(self):
        inst = PackerSlots.__new__(PackerSlots)
        # No _last_output_dir set at all → guarded early-return, no launcher call.
        with mock.patch("os.system") as system_mock, mock.patch(
            "extapps.texture_maps.packer.slots.FileUtils.open_explorer"
        ) as open_mock:
            inst.b001()
        system_mock.assert_not_called()
        open_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
