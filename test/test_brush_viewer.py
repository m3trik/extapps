#!/usr/bin/env python
# coding=utf-8
"""Tests for the Brush panel's viewer-launch actions.

Covers the header actions ("Open Brush Viewer" / "View Result in Brush"), the
latest-result resolution, and the exact Brush argv (a .ply needs an explicit
``--with-viewer`` to open in the viewer rather than headless-train) — all
without launching a real process.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from unittest import mock

from qtpy.QtWidgets import QApplication


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestBrushViewerActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import gaussian_splat_workflow as g
        self.ui = g.GaussianSplatWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots)
        # bridge.exe is a read-only property over find_brush_exe(); patch that so
        # the panel sees a known install without a real Brush on the machine.
        p = mock.patch(
            "extapps.photogrammetry.gaussian_splat_workflow."
            "_gaussian_splat_runner.find_brush_exe",
            return_value="/fake/brush.exe",
        )
        self.find_brush = p.start()
        self.addCleanup(p.stop)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    # ---- header wiring -----------------------------------------------------
    def test_header_has_viewer_actions(self) -> None:
        menu = self.ui.header.menu
        self.assertEqual(menu.btn_open_brush.text(), "Open Brush Viewer")
        self.assertEqual(menu.btn_view_result.text(), "View Result in Brush")

    # ---- open empty viewer -------------------------------------------------
    def test_open_brush_viewer_launches_empty(self) -> None:
        with mock.patch("pythontk.AppLauncher.launch", return_value=object()) as L:
            self.slots.open_brush_viewer()
        L.assert_called_once()
        self.assertEqual(L.call_args.args[0], "/fake/brush.exe")
        self.assertEqual(L.call_args.kwargs["args"], [])

    def test_launch_skipped_when_brush_missing(self) -> None:
        self.find_brush.return_value = None
        with mock.patch("pythontk.AppLauncher.launch") as L:
            self.slots.open_brush_viewer()
        L.assert_not_called()

    # ---- open the result ---------------------------------------------------
    def test_view_result_passes_ply_and_with_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            old = os.path.join(d, "splat_1000.ply")
            new = os.path.join(d, "splat_30000.ply")
            for p in (old, new):
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("ply\n")
            # Make `new` unambiguously newest.
            os.utime(old, (time.time() - 100, time.time() - 100))
            self.slots._last_output_dir = d

            with mock.patch(
                "pythontk.AppLauncher.launch", return_value=object()
            ) as L:
                self.slots.open_result_in_brush()
            L.assert_called_once()
            self.assertEqual(L.call_args.args[0], "/fake/brush.exe")
            self.assertEqual(L.call_args.kwargs["args"], [new, "--with-viewer"])

    def test_view_result_no_result_does_not_launch(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.slots._last_output_dir = d  # empty dir, no .ply
            with mock.patch("pythontk.AppLauncher.launch") as L:
                self.slots.open_result_in_brush()
            L.assert_not_called()

    def test_latest_result_picks_newest_ply_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "publish")
            os.makedirs(sub)
            a = os.path.join(d, "raw.ply")
            b = os.path.join(sub, "clean.ply")
            for p in (a, b):
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("ply\n")
            os.utime(a, (time.time() - 100, time.time() - 100))
            self.slots._last_output_dir = d
            self.assertEqual(self.slots._latest_result_splat(), b)


if __name__ == "__main__":
    unittest.main()
