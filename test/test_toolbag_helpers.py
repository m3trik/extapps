#!/usr/bin/env python
# coding=utf-8
"""Regression tests for ``marmoset_workflow._toolbag_helpers``.

These helpers normally run inside Marmoset Toolbag's bundled Python (where
``mset`` exists). Outside Toolbag ``mset`` is ``None``, so the wiring loop
short-circuits; the tests below inject a lightweight fake ``mset`` to drive
:func:`wire_materials_from_manifest` through its per-slot body without a
live Toolbag session.

Run::

    pytest extapps/test/test_toolbag_helpers.py
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

from extapps.marmoset_workflow import _toolbag_helpers as tbh


class _FakeSub:
    """Minimal stand-in for a Toolbag material subroutine module."""

    def __init__(self, field_names):
        self._field_names = list(field_names)
        self.wired = {}

    def getFieldNames(self):
        return list(self._field_names)

    def setField(self, name, path):
        self.wired[name] = path

    def getField(self, name):  # no Texture-like object -> sRGB tag is a no-op
        return None


class _FakeMat:
    """Minimal stand-in for an ``mset.Material`` with named module attrs."""

    def __init__(self, name, **modules):
        self.name = name
        for attr, sub in modules.items():
            setattr(self, attr, sub)


class TestWireMaterialsNullTexturePath(unittest.TestCase):
    """A ``null`` texture path in the manifest must be skipped, not crash.

    Regression (fix_groups: mishandled-none): ``os.path.isfile(None)`` raises
    an uncaught ``TypeError`` that previously aborted the whole wiring pass,
    so a valid slot listed after a null one was never wired.
    """

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="tbh_test_")
        # A real file so os.path.isfile() returns True for the valid slot.
        self.normal_path = os.path.join(self._tmp, "wood_n.png")
        with open(self.normal_path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")
        self.manifest_path = os.path.join(self._tmp, "scene.materials.json")
        manifest = {
            "materials": {
                "wood": {"baseColor": None, "normal": self.normal_path},
            }
        }
        with open(self.manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)

    def tearDown(self):
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_null_slot_skipped_and_valid_slot_wired(self):
        surface = _FakeSub(["Normal Map"])
        mat = _FakeMat("wood", surface=surface)
        fake_mset = mock.Mock()
        fake_mset.getAllMaterials.return_value = [mat]

        with mock.patch.object(tbh, "mset", fake_mset):
            # Must not raise TypeError on the null baseColor slot.
            wired = tbh.ToolbagHelpers.wire_materials_from_manifest(
                self.manifest_path, verbose=False
            )

        # Only the valid 'normal' slot got wired; the null 'baseColor' was
        # skipped rather than aborting the pass. The binding is an
        # ``mset.Texture`` constructed from the path with its colorspace set
        # at construction (mutating ``sRGB`` on an already-bound texture
        # severs the binding -- verified on Toolbag 5.02).
        self.assertEqual(wired, 1)
        fake_mset.Texture.assert_called_once_with(self.normal_path)
        tex_obj = fake_mset.Texture.return_value
        self.assertEqual(surface.wired, {"Normal Map": tex_obj})
        self.assertIs(tex_obj.sRGB, False)  # normal maps load Linear


if __name__ == "__main__":
    unittest.main()
