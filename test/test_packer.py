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
import os
import tempfile
import shutil
import unittest

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
