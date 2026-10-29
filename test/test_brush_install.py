#!/usr/bin/env python
# coding=utf-8
"""Tests for the engine behind the Brush panel's "Download Brush" action.

Covers the download template, the AppInstaller delegation and catalog-aware
discovery -- all without touching the network or launching a real download.
The panel's wiring (header action + dispatch) is tentacle's
(``test_gaussian_splat_workflow_panel.py``).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock


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


if __name__ == "__main__":
    unittest.main()
