#!/usr/bin/env python
# coding=utf-8
"""Window-chrome contract for the extapps panels.

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

Two layers, on purpose. The runtime cases BUILD three panels and compare
real ``windowFlags()`` against the ``WindowPanel`` reference -- the only
check that proves the chrome. The source case covers the WHOLE roster
cheaply, because building eleven Qt panels per run is slow and fragile
while the defect itself is textual.

The roster is DERIVED from pyproject's entry-point table, never hand-listed.
This file used to pin three panels by name; the same fix had landed in those
three and in none of the other eight, and no test could see it. That is the
rule in CODE_STANDARD.md §6: a family's guard comes from the roster that
already lists the family.

Run::

    pytest extapps/test/test_window_chrome.py
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

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


def _roster_targets():
    """Entry-point targets (``module:Class``) from pyproject's table (roster SSoT).

    ``importlib.metadata`` first -- authoritative wherever extapps is installed,
    which is every CI run. A raw source checkout carries no entry-point metadata
    at all, so fall back to reading the table out of ``pyproject.toml``: same
    SSoT, one less layer.
    """
    group = "uitk.external_apps.in_process"
    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        found = (
            eps.select(group=group) if hasattr(eps, "select") else eps.get(group, [])
        )
        targets = {ep.value.strip() for ep in found}
        if targets:
            return targets
    except Exception:  # pragma: no cover - metadata shapes vary by version
        pass

    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    block = re.search(
        r'^\[project\.entry-points\."%s"\]\s*$(.*?)(?=^\[)' % re.escape(group),
        text,
        re.M | re.S,
    )
    if not block:
        raise AssertionError("entry-point table %r not found in pyproject.toml" % group)
    return {
        m.group(1).strip()
        for m in re.finditer(r'^\s*\w+\s*=\s*"([^"]+)"', block.group(1), re.M)
    }


def _split_target(target):
    """``"pkg.mod:ClassUI [extra]"`` -> ``("pkg.mod", "ClassUI")``.

    The ``[extra]`` suffix is packaging's optional-dependency marker (two panels
    carry ``[hide_maya]``); it is part of the entry point, not of the name.
    """
    module, _, cls = target.partition(":")
    return module.strip(), cls.split("[")[0].strip()


def _roster_module_names():
    """Just the module paths -- what the launcher/roster pairing checks."""
    return {_split_target(t)[0] for t in _roster_targets()}


def _roster_ui_classes():
    """Just the UI class names -- what the root package must re-export."""
    return {_split_target(t)[1] for t in _roster_targets()}


class TestEveryPanelUsesTheCleanFlagSet(unittest.TestCase):
    """Source-level, roster-wide: no launcher may OR onto QMainWindow defaults.

    ``AttributesMixin.set_flags`` ORs a hint onto ``self.windowFlags()``. On a
    ``QMainWindow`` root -- which every extapps ``.ui`` root is -- those defaults
    carry the native decoration hints, and on a frameless host-owned window they
    make it float always-on-top. The fix is to REPLACE the set, not extend it.
    """

    BAD = "set_flags(FramelessWindowHint"
    GOOD = "setWindowFlags("

    def _launchers(self):
        root = Path(__file__).resolve().parents[1] / "extapps"
        return sorted(root.rglob("launcher.py"))

    def test_roster_and_launchers_agree(self):
        """A panel with no launcher, or a launcher outside the roster, fails."""
        roster = _roster_module_names()
        self.assertTrue(roster, "roster resolved empty")
        pkg_root = Path(__file__).resolve().parents[1]
        launcher_mods = {
            ".".join(p.relative_to(pkg_root).with_suffix("").parts[:-1])
            for p in self._launchers()
        }
        self.assertEqual(
            launcher_mods,
            set(roster),
            "every rostered panel needs a launcher.py and vice versa",
        )

    def test_no_launcher_ors_frameless_onto_defaults(self):
        offenders = []
        for path in self._launchers():
            src = path.read_text(encoding="utf-8")
            if self.BAD in src:
                offenders.append(str(path.name and path))
        self.assertEqual(
            [],
            offenders,
            "these launchers still OR FramelessWindowHint onto "
            "QMainWindow defaults (always-on-top under a DCC host): %s" % offenders,
        )

    def test_every_launcher_sets_the_clean_set(self):
        missing = [
            p
            for p in self._launchers()
            if self.GOOD not in p.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            [], missing, "launchers not setting an explicit flag set: %s" % missing
        )


if __name__ == "__main__":
    unittest.main()
