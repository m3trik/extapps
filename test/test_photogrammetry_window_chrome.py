#!/usr/bin/env python
# coding=utf-8
"""Window-chrome contract for the photogrammetry panels.

The panels are frameless uitk windows whose controls live on the uitk
Header (no native OS frame). They must behave like uitk's ``WindowPanel``
(the editor-window reference): a clean ``Qt.Window | FramelessWindowHint``
so that, when the external-app handler parents them under a DCC host
(e.g. Maya), they're *normal* host-owned windows — NOT always-on-top.

A plain ``QMainWindow`` defaults to carrying the native title-bar
decoration hints (title / system-menu / min / max / close button hints);
left set on a frameless owned window they make it float on top of its
host. These tests pin the launchers to the reference flag set so that
regression can't creep back.

Run::

    pytest extapps/test/test_photogrammetry_window_chrome.py
"""
from __future__ import annotations

import sys
import unittest

from qtpy import QtCore
from qtpy.QtWidgets import QApplication


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


# Native title-bar decoration hints that must be cleared on a frameless
# window — the uitk Header supplies these controls instead.
_DECORATION_HINTS = (
    QtCore.Qt.WindowTitleHint
    | QtCore.Qt.WindowSystemMenuHint
    | QtCore.Qt.WindowMinimizeButtonHint
    | QtCore.Qt.WindowMaximizeButtonHint
    | QtCore.Qt.WindowCloseButtonHint
)


def _build_ui(import_path: str, cls_name: str):
    import importlib

    mod = importlib.import_module(import_path)
    return getattr(mod, cls_name)()


class TestPhotogrammetryWindowChrome(unittest.TestCase):
    """Every photogrammetry panel matches the WindowPanel reference chrome."""

    PANELS = (
        ("extapps.photogrammetry.metashape_workflow", "MetashapeWorkflowUI"),
        ("extapps.photogrammetry.realityscan_workflow", "RealityScanWorkflowUI"),
        ("extapps.photogrammetry.gaussian_splat_workflow", "GaussianSplatWorkflowUI"),
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def _reference_flags(self) -> int:
        """The flag set uitk's editor windows use (WindowPanel default)."""
        from uitk.widgets.windowPanel import WindowPanel

        ref = WindowPanel(title="ref")
        flags = int(ref.windowFlags())
        ref.deleteLater()
        self.app.processEvents()
        return flags

    def test_panels_match_windowpanel_reference(self) -> None:
        reference = self._reference_flags()
        for import_path, cls_name in self.PANELS:
            with self.subTest(panel=cls_name):
                ui = _build_ui(import_path, cls_name)
                try:
                    flags = int(ui.windowFlags())
                    self.assertEqual(
                        flags,
                        reference,
                        f"{cls_name} window flags {hex(flags)} != WindowPanel "
                        f"reference {hex(reference)} — frameless chrome drifted.",
                    )
                finally:
                    ui.deleteLater()
                    self.app.processEvents()

    def test_panels_are_normal_frameless_windows(self) -> None:
        Qt = QtCore.Qt
        for import_path, cls_name in self.PANELS:
            with self.subTest(panel=cls_name):
                ui = _build_ui(import_path, cls_name)
                try:
                    flags = ui.windowFlags()
                    self.assertEqual(
                        int(flags & Qt.WindowType_Mask),
                        int(Qt.Window),
                        f"{cls_name} must be a normal top-level Window.",
                    )
                    self.assertTrue(
                        bool(flags & Qt.FramelessWindowHint),
                        f"{cls_name} must be frameless (controls on the Header).",
                    )
                    self.assertFalse(
                        bool(flags & Qt.WindowStaysOnTopHint),
                        f"{cls_name} must NOT be always-on-top.",
                    )
                    self.assertEqual(
                        int(flags & _DECORATION_HINTS),
                        0,
                        f"{cls_name} must clear native decoration hints "
                        "(they make a frameless owned window float on top).",
                    )
                finally:
                    ui.deleteLater()
                    self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
