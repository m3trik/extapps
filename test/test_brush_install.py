#!/usr/bin/env python
# coding=utf-8
"""Tests for the Brush panel's "Download Brush" action.

Covers the download template, the AppInstaller delegation, catalog-aware
discovery, and the panel wiring (header action + dispatch) — all without
touching the network or launching a real download.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from qtpy.QtWidgets import QApplication


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def _gsw():
    from extapps.photogrammetry.gaussian_splat_workflow import (
        _gaussian_splat_workflow as gsw,
    )
    return gsw


class TestBrushDownloadTemplate(unittest.TestCase):
    """The platforms dict AppInstaller consumes is well-formed + version-agnostic."""

    def test_template_platforms_urls_and_types(self) -> None:
        t = _gsw().BRUSH_DOWNLOAD
        self.assertEqual(set(t), {"windows", "linux", "darwin"})
        self.assertTrue(
            t["windows"]["url"].endswith("brush-app-x86_64-pc-windows-msvc.zip")
        )
        self.assertEqual(t["windows"]["type"], "zip")
        self.assertTrue(
            t["linux"]["url"].endswith("brush-app-x86_64-unknown-linux-gnu.tar.xz")
        )
        self.assertEqual(t["linux"]["type"], "tar.xz")
        self.assertTrue(
            t["darwin"]["url"].endswith("brush-app-aarch64-apple-darwin.tar.xz")
        )
        for info in t.values():
            # Version-agnostic "latest" URL so it tracks new releases.
            self.assertIn("releases/latest/download/", info["url"])

    def test_install_brush_delegates_to_appinstaller(self) -> None:
        gsw = _gsw()
        with mock.patch(
            "pythontk.AppInstaller.ensure", return_value="/fake/brush"
        ) as ens:
            path = gsw.GaussianSplatWorkflow.install_brush()
        self.assertEqual(path, "/fake/brush")
        self.assertEqual(ens.call_args.args[0], "brush")
        kw = ens.call_args.kwargs
        self.assertEqual(kw["platforms"], gsw.BRUSH_DOWNLOAD)
        # The brush-app crate's [[bin]] is named "brush", so the binary inside
        # every archive (and in the catalog) is "brush" — NOT "brush_app".
        self.assertEqual(kw["executable"], "brush")
        self.assertIsNotNone(kw["progress_callback"])


class TestFindBrushExeCatalog(unittest.TestCase):
    """A panel-installed Brush is discovered via the managed-install catalog."""

    def test_consults_catalog_as_last_resort(self) -> None:
        gsw = _gsw()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRUSH_EXE", None)
            # The profile stage now lives in the shared profile.resolve_app
            # chain, so patch it there rather than on this engine module.
            with mock.patch(
                     "extapps.photogrammetry.profile.Profile.configured_app_path",
                     return_value=None,
                 ), \
                 mock.patch("shutil.which", return_value=None), \
                 mock.patch(
                     "pythontk.AppInstaller.get_path",
                     return_value="/managed/brush.exe",
                 ) as gp:
                self.assertEqual(gsw.GaussianSplatWorkflow.find_brush_exe(), "/managed/brush.exe")
                gp.assert_called_once_with("brush", executable="brush")

    def test_env_override_still_wins_over_catalog(self) -> None:
        gsw = _gsw()
        with mock.patch.dict(os.environ, {"BRUSH_EXE": ""}, clear=False), \
             mock.patch("pythontk.AppInstaller.get_path") as gp:
            # An empty/invalid BRUSH_EXE is honored strictly (-> None), and the
            # catalog is NOT consulted (env is an explicit, deliberate signal).
            self.assertIsNone(gsw.GaussianSplatWorkflow.find_brush_exe())
            gp.assert_not_called()


class TestBrushInstallAction(unittest.TestCase):
    """Panel wiring: the header action exists and dispatches correctly."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.photogrammetry import gaussian_splat_workflow as g
        self.ui = g.GaussianSplatWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_header_has_download_brush_button(self) -> None:
        btn = self.ui.header.menu.btn_install_brush
        self.assertIsNotNone(btn)
        self.assertEqual(btn.text(), "Download Brush")

    def test_install_skipped_when_brush_available(self) -> None:
        self.slots.bridge.is_available = lambda: True
        with mock.patch.object(self.slots._install_runner, "start") as start:
            self.slots.install_brush()
        start.assert_not_called()

    def test_install_starts_runner_when_missing(self) -> None:
        self.slots.bridge.is_available = lambda: False
        self.slots._install_runner.is_running = lambda: False
        with mock.patch.object(self.slots._install_runner, "start") as start:
            self.slots.install_brush()
        start.assert_called_once()
        kw = start.call_args.kwargs
        # Bound methods compare equal (same instance + function) but aren't
        # identical objects, so use assertEqual.
        self.assertEqual(kw["on_line"], self.slots._append_output)
        self.assertEqual(kw["on_done"], self.slots._on_install_done)

    def test_cancel_run_cancels_inflight_install(self) -> None:
        self.slots._install_runner.is_running = lambda: True
        with mock.patch.object(self.slots._install_runner, "cancel") as cancel:
            self.slots.cancel_run()
        cancel.assert_called_once()

    def test_cancel_run_delegates_to_base_when_no_install(self) -> None:
        self.slots._install_runner.is_running = lambda: False
        self.slots.bridge.is_running = lambda: False
        with mock.patch.object(self.slots._install_runner, "cancel") as cancel:
            self.slots.cancel_run()  # falls through to base (training bridge)
        cancel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
