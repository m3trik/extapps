# !/usr/bin/python
# coding=utf-8
"""Tests for ``python -m extapps`` / the ``extapps`` command (``extapps/__main__.py``).

The program is uitk's ``ExternalAppHub``; extapps only declares it. Since 0.7.0
the panels are tentacle's, and this hub stays so launchers written before the
move (``<python> -m extapps <panel>``) keep opening their panel: it serves the
panels the installed packages declare and declares none itself.
"""

import importlib
import importlib.util
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

    def test_it_declares_no_panels_of_its_own(self):
        text = PYPROJECT.read_text(encoding="utf-8")
        self.assertNotIn("uitk.external_apps", text)

    def test_it_names_the_panels_new_provider(self):
        """Its handler knows tentacle as the provider of the moved panels, as
        data: it reads tentacle's table from a checkout, and installs tentacletk
        when a panel is asked for and tentacle is missing."""
        self.assertIn(("tentacletk", "tentacle"), HUB.providers)
        provider = self.sb.handlers.external_app._providers.get("tentacletk")
        self.assertIsNotNone(provider)
        self.assertEqual(provider["probe_module"], "tentacle")

    @unittest.skipUnless(
        importlib.util.find_spec("tentacle"), "tentacle not installed beside extapps"
    )
    def test_an_old_launcher_still_opens_its_panel(self):
        """A launcher made before the move runs ``python -m extapps compositor``:
        this hub resolves the panel to tentacle's module, while a new launcher
        made from it is tentacle's (its hub)."""
        handler = self.sb.handlers.external_app
        self.assertTrue(handler.is_registered("compositor"))
        self.assertEqual(handler._apps["compositor"]["module"], "tentacle.tcl_standalone")
        self.assertEqual(handler.hub_for("compositor").package, "tentacle")


if __name__ == "__main__":
    unittest.main()
