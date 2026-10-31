# !/usr/bin/python
# coding=utf-8
"""Tests for ``python -m extapps`` / the ``extapps`` command (``extapps/__main__.py``).

The program is uitk's ``ExternalAppHub``; extapps only declares it. These pin
the declaration and that the hub serves every app the entry-point table lists --
read from the table itself (``test_panel_launcher.entry_points``), never a
hand-kept list -- as their provider, naming no other.
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
from test_panel_launcher import entry_points  # noqa: E402

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _table(name: str) -> dict:
    """``key = "value"`` pairs of one ``pyproject.toml`` table, by header text."""
    text = PYPROJECT.read_text(encoding="utf-8")
    block = re.search(
        r"^\[%s\]\s*$(.*?)(?=^\[|\Z)" % re.escape(name), text, re.M | re.S
    )
    if not block:
        raise AssertionError(f"table [{name}] not found in pyproject.toml")
    return dict(re.findall(r'^\s*(\w+)\s*=\s*"([^"]+)"', block.group(1), re.M))


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

    def test_it_is_its_own_apps_provider_and_names_no_other(self):
        """A checkout on PYTHONPATH has no installed entry points: the hub names
        extapps itself as their provider, so its pyproject table is read; it
        names no other package (tentacle is no provider of apps). Rows other
        installed packages declare are theirs, not the hub's."""
        self.assertEqual(HUB.providers, ())
        providers = self.sb.handlers.external_app._providers
        self.assertEqual(providers["extapps"]["probe_module"], "extapps")

    def test_the_browser_lists_every_app(self):
        browser = HUB._browser(self.sb)  # built, never shown
        self.addCleanup(browser.deleteLater)
        self.assertLessEqual(set(entry_points()), set(browser._model._names))

    def test_every_app_resolves_to_its_own_module(self):
        """Launched by name (a host's menu, ``python -m extapps <app>``), each app
        resolves to the module its entry point names."""
        handler = self.sb.handlers.external_app
        for name, (module, entry, _extras) in sorted(entry_points().items()):
            with self.subTest(app=name):
                self.assertTrue(handler.is_registered(name))
                self.assertEqual(handler._apps[name]["module"], module)
                self.assertEqual(handler._apps[name]["entry"], entry)

    def test_every_app_can_get_a_desktop_launcher_from_it(self):
        handler = self.sb.handlers.external_app
        for name in sorted(entry_points()):
            with self.subTest(app=name):
                self.assertIs(handler.hub_for(name), HUB)


if __name__ == "__main__":
    unittest.main()
