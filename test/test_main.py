# !/usr/bin/python
# coding=utf-8
"""Tests for ``python -m extapps`` / the ``extapps`` command (``extapps/__main__.py``).

The program is uitk's ``ExternalAppHub``; extapps only declares it. These pin
the declaration and that the hub serves every panel the entry-point table
lists -- read from the table itself (metadata, else ``pyproject.toml``), never
a hand-kept list.
"""

import importlib
import os
import re
import unittest
from pathlib import Path

from qtpy.QtWidgets import QApplication

from uitk import ExternalAppHub
from uitk.testing import TestSandbox

# A direct `python test/test_main.py` loads no conftest, and the hub's
# switchboard and browser read and write QSettings: the sandbox is activated
# here too, before the first one. Idempotent.
TestSandbox.activate()

from extapps.__main__ import HUB  # noqa: E402

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
GROUP = "uitk.external_apps.in_process"


def _table(name: str) -> dict:
    """``key = "value"`` pairs of one ``pyproject.toml`` table, by header text."""
    text = PYPROJECT.read_text(encoding="utf-8")
    block = re.search(
        r"^\[%s\]\s*$(.*?)(?=^\[|\Z)" % re.escape(name), text, re.M | re.S
    )
    if not block:
        raise AssertionError(f"table [{name}] not found in pyproject.toml")
    return dict(re.findall(r'^\s*(\w+)\s*=\s*"([^"]+)"', block.group(1), re.M))


def _panel_names() -> set:
    """The in-process entry-point names: installed metadata, else pyproject."""
    from importlib.metadata import entry_points

    eps = entry_points()
    found = eps.select(group=GROUP) if hasattr(eps, "select") else eps.get(GROUP, [])
    names = {ep.name for ep in found}
    return names or set(_table(f'project.entry-points."{GROUP}"'))


class TestDeclaration(unittest.TestCase):
    def test_the_hub_is_extapps(self):
        self.assertEqual(HUB.package, "extapps")
        self.assertEqual(HUB.title, "extapps")
        self.assertEqual(HUB.app_id, "m3trik.extapps")
        self.assertTrue(os.path.isfile(HUB.icon), HUB.icon)

    def test_a_host_finds_it_as_the_providers_hub(self):
        self.assertIs(ExternalAppHub.of("extapps"), HUB)

    def test_the_command_runs_the_hub(self):
        target = _table("project.gui-scripts")["extapps"]
        module, _, attrs = target.partition(":")
        resolved = importlib.import_module(module)
        for attr in attrs.split("."):
            resolved = getattr(resolved, attr)
        self.assertEqual(resolved, HUB.run)

    def test_the_icon_ships_with_the_package(self):
        text = PYPROJECT.read_text(encoding="utf-8")
        svg = re.compile(r'^"\*" = \[[^\]]*"\*\.svg"', re.M)
        self.assertRegex(text, svg, "*.svg is declared package data")


class TestHub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.sb = HUB._switchboard()

    def test_the_browser_lists_every_panel(self):
        browser = HUB._browser(self.sb)  # built, never shown
        self.addCleanup(browser.deleteLater)
        self.assertEqual(set(browser._model._names), _panel_names())

    def test_every_panel_can_get_a_desktop_launcher_from_it(self):
        handler = self.sb.handlers.external_app
        for name in sorted(_panel_names()):
            with self.subTest(panel=name):
                self.assertIs(handler.hub_for(name), HUB)


if __name__ == "__main__":
    unittest.main()
