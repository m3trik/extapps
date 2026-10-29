#!/usr/bin/python
# coding=utf-8
"""Tests for the Map Converter's batch rules (:class:`extapps.MapConverter`).

How the destination and archive fields resolve, what a rename-mode output is
called, which inputs would collide on one output. The panel that drives them is
tentacle's (``tentacle/test/test_converter_panel.py``).
"""
import contextlib
import io
import os
import shutil
import tempfile
import unittest

from PIL import Image

from pythontk import ImgUtils
from pythontk.core_utils.engines.textures.map_registry import MapRegistry, WF

from extapps import MapConverter


class TestMapConverter(unittest.TestCase):
    """The rules, called on the class: no panel."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="map_converter_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_resolve_affix_auto_reads_the_underscore(self):
        cases = [
            ("auto", "LD_", ("prefix", "LD")),      # trailing _ -> prefix
            ("auto", "_LD", ("suffix", "LD")),      # leading _ -> suffix
            ("auto", "LD", ("suffix", "LD")),       # unmarked -> legacy default
            ("auto", "_LD_", ("suffix", "LD")),     # ambiguous -> legacy default
            ("auto", "  LD_  ", ("prefix", "LD")),  # whitespace tolerated
            ("auto", "", ("suffix", "")),
            ("auto", None, ("suffix", "")),
        ]
        for mode, text, expected in cases:
            with self.subTest(modifier=text):
                self.assertEqual(MapConverter.resolve_affix(mode, text), expected)

    def test_resolve_affix_explicit_modes_override_the_underscore(self):
        self.assertEqual(MapConverter.resolve_affix("prefix", "_LD"), ("prefix", "LD"))
        self.assertEqual(MapConverter.resolve_affix("suffix", "LD_"), ("suffix", "LD"))

    def test_rename_keeps_a_lobe_named_set_whole(self):
        """The modifier lands after the set's whole name, never inside it."""
        target = MapConverter.rename_target_path(
            os.path.join(self.test_dir, "Hero_Coat_Roughness.png"),
            file_type="png",
            mode="suffix",
            modifier="LD",
            output_dir=self.test_dir,
            base_name="Hero_Coat",
        )
        self.assertEqual(os.path.basename(target), "Hero_Coat_LD_Roughness.png")

    def test_folder_name_strips_typed_separators(self):
        """A bare entry keeps only the name. What counts as "bare" is
        platform-dependent by design (see ``_is_abs_dest``): a leading ``/`` is
        a typed separator on Windows but a real root on POSIX, where the entry
        names one shared destination and must survive intact."""
        for text in ("/new/", "\\new", "  new  ", "new/"):
            with self.subTest(text=text):
                stripped = text.strip()
                expected = (
                    os.path.normpath(stripped)
                    if MapConverter.is_abs_dest(stripped)
                    else "new"
                )
                self.assertEqual(MapConverter.folder_name(text), expected)
        self.assertEqual(MapConverter.folder_name(""), "")

    def test_folder_name_keeps_a_full_path_intact(self):
        """A drive-rooted (or POSIX-rooted) entry names one shared destination,
        so it must survive the separator stripping that bare names get."""
        full = os.path.join(self.test_dir, "collected")
        self.assertEqual(MapConverter.folder_name(full), os.path.normpath(full))
        self.assertEqual(MapConverter.folder_name(f"  {full}  "), os.path.normpath(full))

    def test_output_collisions_key_on_the_RESOLVED_name(self):
        """The bare stem over-fires; the resolved output name does not."""
        pair = [
            os.path.join(self.test_dir, "rock_BaseColor.tga"),
            os.path.join(self.test_dir, "rock_BaseColor.png"),
        ]
        self.assertEqual(
            MapConverter.output_collisions(pair, "png", ""),
            [("rock_BaseColor.png", pair)],
        )
        self.assertEqual(MapConverter.output_collisions(pair, "", ""), [])

    def test_a_workflow_target_that_forces_ONE_container_is_caught(self):
        """Choosing a target leaves the Format field on its sentinel, so
        `file_type` is empty and the PROFILE picks the container per map type
        -- and every built-in profile names a concrete one. The `.tga` and
        `.png` sources still merge, with nothing in Format to hint at why.
        """
        pair = [
            os.path.join(self.test_dir, "rock_BaseColor.tga"),
            os.path.join(self.test_dir, "rock_BaseColor.png"),
        ]
        merged = MapConverter.output_collisions(pair, "", "", WF.GLTF)
        self.assertEqual(len(merged), 1, "the profile's container was not consulted")
        self.assertEqual(merged[0][1], pair)

    def test_no_target_and_no_format_leaves_each_container_alone(self):
        """Nothing forces a common extension, so nothing can be lost."""
        pair = [
            os.path.join(self.test_dir, "rock_BaseColor.tga"),
            os.path.join(self.test_dir, "rock_BaseColor.png"),
        ]
        self.assertEqual(MapConverter.output_collisions(pair, "", "", None), [])

    def test_output_collisions_see_a_shared_destination_folder(self):
        """Two folders collapsed onto one absolute output collide even when the
        extensions already agree."""
        shared = os.path.join(self.test_dir, "collected")
        pair = [
            os.path.join(self.test_dir, "a", "rock_BaseColor.png"),
            os.path.join(self.test_dir, "b", "rock_BaseColor.png"),
        ]
        self.assertEqual(
            MapConverter.output_collisions(pair, "", shared),
            [("rock_BaseColor.png", pair)],
        )
        # per-texture subdirectories keep them apart
        self.assertEqual(MapConverter.output_collisions(pair, "", "out"), [])


class TestRenameModeExtension(unittest.TestCase):
    """The name the converter writes must match the bytes it wrote.

    Rename mode (a non-empty Modifier) is the one path where the converter builds
    the destination itself and ``os.replace``s the optimizer's output onto it,
    so it is the one path that can disagree with the optimizer about the
    container.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rename_ext_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.src = os.path.join(self.tmp, "rock_BaseColor.png")
        ImgUtils.save_image(
            ImgUtils.create_image("RGB", (64, 64), (128, 96, 64)), self.src
        )

    def _run(self, **kwargs):
        base = dict(
            file_type=None,  # "Original" -- the profile picks the container
            max_size=None,
            secondary_scale=1.0,
            mode="suffix",
            modifier="LD",
            new_folder="out",
            old_folder=None,
            registry=MapRegistry(),
            output_profile="Unreal Engine",  # resolves Base_Color -> .tga
        )
        base.update(kwargs)
        with contextlib.redirect_stdout(io.StringIO()):
            MapConverter.optimize_one(self.src, **base)
        out_dir = os.path.join(self.tmp, "out")
        return [
            os.path.join(out_dir, f)
            for f in sorted(os.listdir(out_dir))
            if os.path.isfile(os.path.join(out_dir, f))
        ]

    def test_rename_mode_extension_matches_the_bytes_written(self):
        """Regression: the destination name came from *file_type*, not the run.

        ``optimize_map`` resolves the container from the output profile's
        ``OutputSpec``; the slot derived the extension from ``file_type``
        instead, which is ``None`` here ("Original"). Measured before the fix:
        a "Unreal Engine" target wrote TGA bytes (magic ``00 00 02 00``) into
        ``rock_LD_BaseColor.png``. Downstream tools resolve by extension, so a
        file whose name and content disagree is worse than a failed convert.
        """
        from pythontk.core_utils.engines.textures.output_template import (
            OutputTemplates,
        )

        # Stated, not assumed: the whole test rests on this profile choosing a
        # container the source does not use. If the registry ever changes it,
        # fail here with the reason rather than on a baffling extension match.
        self.assertEqual(
            OutputTemplates.resolve("Base_Color", "Unreal Engine").ext,
            "tga",
            "premise: the profile must differ from the source's .png",
        )

        written = self._run()
        self.assertEqual(len(written), 1, f"expected one output, got {written}")
        out = written[0]

        # The profile's container, not the source's.
        self.assertTrue(out.lower().endswith(".tga"), f"named wrong: {out}")
        # And the name is the one rename mode promises.
        self.assertIn("rock_LD_BaseColor", os.path.basename(out))

        # Pillow identifies by CONTENT, so this is the name-vs-bytes assertion.
        with Image.open(out) as img:
            self.assertEqual(
                (img.format or "").upper(),
                "TGA",
                f"{os.path.basename(out)} does not hold the format it is named for",
            )

    def test_an_explicit_file_type_still_wins(self):
        """The profile only fills a container the caller did not name."""
        written = self._run(file_type="png")
        self.assertEqual(len(written), 1, written)
        out = written[0]
        self.assertTrue(out.lower().endswith(".png"), f"named wrong: {out}")
        with Image.open(out) as img:
            self.assertEqual((img.format or "").upper(), "PNG")


if __name__ == "__main__":
    unittest.main(verbosity=2)
