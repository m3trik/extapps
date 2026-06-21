#!/usr/bin/python
# coding=utf-8
"""Tests for CompositorSlots source resolution.

Covers the dir-*or*-image-files source field added so the user can point
the compositor at a directory of maps OR hand-pick individual image files.
The heavy UI wiring in ``__init__`` is bypassed (``__new__``) — these tests
exercise the pure source-resolution helpers and ``_resolve_source``.
"""
import os
import tempfile
import shutil
import unittest
from unittest.mock import Mock

from pythontk import ImgUtils

from extapps.texture_maps.compositor.slots import CompositorSlots


class TestMapCompositorSourceResolution(unittest.TestCase):
    """Source field accepts a directory or an explicit image-file selection."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="compositor_test_")
        cls.maps_dir = os.path.join(cls.test_dir, "maps")
        os.makedirs(cls.maps_dir, exist_ok=True)
        # A small set of recognizably-named maps in one directory.
        cls.files = {}
        for name in ("mat_BaseColor.png", "mat_Roughness.png", "mat_Metallic.png"):
            path = os.path.join(cls.maps_dir, name)
            ImgUtils.save_image(ImgUtils.create_image("RGB", (8, 8), (128, 128, 128)), path)
            cls.files[name] = path

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    # -- helpers ----------------------------------------------------------

    def _slots_with_source(self, text):
        """Bare slots instance whose source field returns *text*."""
        inst = CompositorSlots.__new__(CompositorSlots)
        inst.ui = Mock()
        inst.ui.txt000.text.return_value = text
        return inst

    @property
    def joined(self):
        return os.pathsep.join(self.files.values())

    # -- _split_source ----------------------------------------------------

    def test_split_source_directory_is_empty(self):
        """A single existing directory is directory mode (no file parts)."""
        self.assertEqual(CompositorSlots._split_source(self.maps_dir), [])

    def test_split_source_single_file(self):
        path = self.files["mat_BaseColor.png"]
        self.assertEqual(CompositorSlots._split_source(path), [path])

    def test_split_source_multiple_files(self):
        self.assertEqual(
            CompositorSlots._split_source(self.joined), list(self.files.values())
        )

    def test_split_source_empty(self):
        self.assertEqual(CompositorSlots._split_source(""), [])

    # -- _field_dir -------------------------------------------------------

    def test_field_dir_directory(self):
        self.assertEqual(CompositorSlots._field_dir(self.maps_dir), self.maps_dir)

    def test_field_dir_single_file(self):
        path = self.files["mat_Roughness.png"]
        self.assertEqual(CompositorSlots._field_dir(path), self.maps_dir)

    def test_field_dir_joined_files(self):
        self.assertEqual(CompositorSlots._field_dir(self.joined), self.maps_dir)

    def test_field_dir_empty(self):
        self.assertEqual(CompositorSlots._field_dir(""), "")

    # -- _validate_source -------------------------------------------------

    def test_validate_source_directory(self):
        self.assertTrue(CompositorSlots._validate_source(self.maps_dir))

    def test_validate_source_single_file(self):
        self.assertTrue(
            CompositorSlots._validate_source(self.files["mat_Metallic.png"])
        )

    def test_validate_source_multiple_files(self):
        self.assertTrue(CompositorSlots._validate_source(self.joined))

    def test_validate_source_nonexistent(self):
        self.assertFalse(
            CompositorSlots._validate_source(os.path.join(self.maps_dir, "nope.png"))
        )

    def test_validate_source_mixed_valid_and_missing(self):
        text = os.pathsep.join(
            [self.files["mat_BaseColor.png"], os.path.join(self.maps_dir, "nope.png")]
        )
        self.assertFalse(CompositorSlots._validate_source(text))

    def test_validate_source_empty(self):
        self.assertFalse(CompositorSlots._validate_source(""))

    # -- _resolve_source --------------------------------------------------

    def test_resolve_source_directory(self):
        """Directory mode loads every image in the directory."""
        inst = self._slots_with_source(self.maps_dir)
        images, source_dir = inst._resolve_source()
        self.assertEqual(source_dir, self.maps_dir)
        self.assertEqual(
            sorted(os.path.basename(p) for p in images), sorted(self.files)
        )

    def test_resolve_source_files(self):
        """File mode loads exactly the selected files; dir is their parent."""
        chosen = [self.files["mat_BaseColor.png"], self.files["mat_Roughness.png"]]
        inst = self._slots_with_source(os.pathsep.join(chosen))
        images, source_dir = inst._resolve_source()
        self.assertEqual(source_dir, self.maps_dir)
        self.assertEqual(sorted(images), sorted(chosen))
        # Values are loaded image objects (the shape the engine expects).
        for img in images.values():
            self.assertIsNotNone(img)

    def test_resolve_source_single_file(self):
        path = self.files["mat_Metallic.png"]
        inst = self._slots_with_source(path)
        images, source_dir = inst._resolve_source()
        self.assertEqual(source_dir, self.maps_dir)
        self.assertEqual(list(images), [path])

    def test_resolve_source_empty(self):
        inst = self._slots_with_source("")
        self.assertEqual(inst._resolve_source(), ({}, ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
