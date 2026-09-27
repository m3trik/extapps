# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.env_utils.painter_finder.PainterFinder."""
import os
import sys
import unittest
from unittest.mock import patch

try:
    from .base_test import SubstanceWorkflowTestCase
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_test import SubstanceWorkflowTestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from extapps.substance_workflow import PainterFinder


class TestDefaultInstallRoots(SubstanceWorkflowTestCase):

    def test_windows_includes_adobe_program_files(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_finder.platform.system",
            return_value="Windows",
        ):
            roots = PainterFinder.default_install_roots()
        self.assertIn(r"C:\Program Files\Adobe", roots)

    def test_darwin_returns_applications(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_finder.platform.system",
            return_value="Darwin",
        ):
            roots = PainterFinder.default_install_roots()
        self.assertEqual(roots, ["/Applications"])

    def test_linux_includes_opt(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_finder.platform.system",
            return_value="Linux",
        ):
            roots = PainterFinder.default_install_roots()
        self.assertIn("/opt", roots)
        self.assertIn("/opt/Adobe", roots)  # where Adobe's Linux installer puts it

    def test_unknown_platform_returns_empty(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_finder.platform.system",
            return_value="Plan9",
        ):
            roots = PainterFinder.default_install_roots()
        self.assertEqual(roots, [])


class TestFindInstalls(SubstanceWorkflowTestCase):

    def test_empty_when_no_roots_exist(self) -> None:
        with patch.object(
            PainterFinder, "default_install_roots", return_value=["/no/such/dir"]
        ):
            with patch(
                "extapps.substance_workflow.env_utils.painter_finder.AppLauncher.find_app",
                return_value=None,
            ):
                self.assertEqual(PainterFinder.find_installs(), {})

    def test_picks_painter_subdirs_with_exe(self) -> None:
        tmp = self.create_temp_dir()
        for label in (
            "Adobe Substance 3D Painter 2024",
            "Adobe Substance 3D Painter",
        ):
            install = os.path.join(tmp, label)
            os.makedirs(install)
            exe = os.path.join(install, "Adobe Substance 3D Painter.exe")
            with open(exe, "w", encoding="utf-8"):
                pass

        with patch.object(PainterFinder, "default_install_roots", return_value=[tmp]):
            with patch(
                "extapps.substance_workflow.env_utils.painter_finder.platform.system",
                return_value="Windows",
            ):
                installs = PainterFinder.find_installs()

        self.assertEqual(len(installs), 2)
        self.assertIn("Adobe Substance 3D Painter 2024", installs)

    def test_finds_the_linux_install_spelled_with_underscores(self) -> None:
        # /opt/Adobe/Adobe_Substance_3D_Painter/Adobe_Substance_3D_Painter: the
        # space-spelled globs never matched it, so Linux read "not installed".
        tmp = self.create_temp_dir()
        install = os.path.join(tmp, "Adobe_Substance_3D_Painter")
        os.makedirs(install)
        exe = os.path.join(install, "Adobe_Substance_3D_Painter")
        with open(exe, "w", encoding="utf-8"):
            pass

        with patch.object(PainterFinder, "default_install_roots", return_value=[tmp]):
            with patch(
                "extapps.substance_workflow.env_utils.painter_finder.platform.system",
                return_value="Linux",
            ):
                installs = PainterFinder.find_installs()

        self.assertEqual(list(installs.values()), [exe])

    def test_orders_installs_newest_first_by_version_not_string(self) -> None:
        # A plain string sort ranks "Painter 9.1" above "Painter 10.0" ('9' > '1'),
        # so resolve() with no argument handed back the OLDER install.
        tmp = self.create_temp_dir()
        for label in (
            "Adobe Substance 3D Painter 9.1",
            "Adobe Substance 3D Painter 10.0",
        ):
            install = os.path.join(tmp, label)
            os.makedirs(install)
            exe = os.path.join(install, "Adobe Substance 3D Painter.exe")
            with open(exe, "w", encoding="utf-8"):
                pass

        with patch.object(PainterFinder, "default_install_roots", return_value=[tmp]):
            with patch(
                "extapps.substance_workflow.env_utils.painter_finder.platform.system",
                return_value="Windows",
            ):
                installs = PainterFinder.find_installs()
                newest = PainterFinder.resolve()

        self.assertEqual(
            list(installs),
            ["Adobe Substance 3D Painter 10.0", "Adobe Substance 3D Painter 9.1"],
        )
        self.assertIn("Painter 10.0", newest)

    def test_ignores_non_painter_dirs(self) -> None:
        tmp = self.create_temp_dir()
        os.makedirs(os.path.join(tmp, "Adobe Photoshop 2025"))
        os.makedirs(os.path.join(tmp, "Some Other Thing"))

        with patch.object(PainterFinder, "default_install_roots", return_value=[tmp]):
            with patch(
                "extapps.substance_workflow.env_utils.painter_finder.AppLauncher.find_app",
                return_value=None,
            ):
                installs = PainterFinder.find_installs()

        self.assertEqual(installs, {})

    def test_falls_back_to_path_lookup(self) -> None:
        with patch.object(PainterFinder, "default_install_roots", return_value=[]):
            with patch(
                "extapps.substance_workflow.env_utils.painter_finder.AppLauncher.find_app",
                return_value="/usr/local/bin/painter",
            ):
                installs = PainterFinder.find_installs()
        self.assertEqual(installs, {"default": "/usr/local/bin/painter"})


class TestResolve(SubstanceWorkflowTestCase):

    def test_absolute_path_passthrough(self) -> None:
        tmp = self.create_temp_dir()
        exe = os.path.join(tmp, "painter.exe")
        with open(exe, "w", encoding="utf-8"):
            pass
        self.assertEqual(PainterFinder.resolve(exe), exe)

    def test_version_fragment_match(self) -> None:
        with patch.object(
            PainterFinder,
            "find_installs",
            return_value={
                "Adobe Substance 3D Painter 2023": "/p/2023.exe",
                "Adobe Substance 3D Painter 2024": "/p/2024.exe",
            },
        ):
            self.assertEqual(PainterFinder.resolve("2023"), "/p/2023.exe")
            self.assertEqual(PainterFinder.resolve("2024"), "/p/2024.exe")

    def test_no_arg_returns_first_install(self) -> None:
        with patch.object(
            PainterFinder,
            "find_installs",
            return_value={
                "Adobe Substance 3D Painter 2024": "/p/2024.exe",
                "Adobe Substance 3D Painter 2023": "/p/2023.exe",
            },
        ):
            # find_installs() sorts entries reverse; first item is the newest label.
            self.assertEqual(PainterFinder.resolve(), "/p/2024.exe")

    def test_returns_none_when_no_installs(self) -> None:
        with patch.object(PainterFinder, "find_installs", return_value={}):
            self.assertIsNone(PainterFinder.resolve())

    def test_version_fragment_no_match_returns_first(self) -> None:
        with patch.object(
            PainterFinder,
            "find_installs",
            return_value={
                "Adobe Substance 3D Painter 2024": "/p/2024.exe",
            },
        ):
            # Asked for 9999, nothing matches — falls back to first.
            self.assertEqual(PainterFinder.resolve("9999"), "/p/2024.exe")


if __name__ == "__main__":
    unittest.main()
