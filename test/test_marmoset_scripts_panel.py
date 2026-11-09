# !/usr/bin/python
# coding=utf-8
"""Tests for Marmoset Scripts (``extapps/marmoset_scripts``).

The standalone Toolbag panel, a :class:`uitk.bridge.ParamPanelSlots` script
manager over the vendored engine: the scripts it lists (the bundled ``import``
and ``lookdev``, a person's own, which shadow them, never one that reads a
host's scene), the Output Dir a run's files land in, and the scripts menu.
Toolbag itself is never started: the engine's ``send`` is stood in for.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from qtpy import QtCore
from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct `python test/test_marmoset_scripts_panel.py` loads no conftest, so the
# sandbox is activated here too -- before the first QSettings or user folder.
TestSandbox.activate()

import pythontk as ptk  # noqa: E402


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class _PanelCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.marmoset_scripts._marmoset_engine import _SCRIPTS_APP

        self.tmp = tempfile.mkdtemp(prefix="marmoset_scripts_panel_")
        self.mine = ptk.ScriptTemplate.user_dir(_SCRIPTS_APP)
        self.addCleanup(shutil.rmtree, self.mine, True)

    def _open(self):
        from extapps.marmoset_scripts.launcher import MarmosetScriptsUI

        self.ui = MarmosetScriptsUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.addCleanup(self._close)
        return self.slots

    def _close(self) -> None:
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        store.clear()
        store.sync()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mine(self, name: str, text: str) -> Path:
        os.makedirs(self.mine, exist_ok=True)
        path = Path(self.mine, f"{name}.py")
        path.write_text(text, encoding="utf-8")
        return path

    def _listed(self):
        combo = self.ui.cmb000
        return [combo.itemData(i)[0] for i in range(combo.count())]


class TestMarmosetScriptsList(_PanelCase):
    """What the panel lists: every script the engine resolves, but for one
    that reads a host's scene."""

    def test_it_opens_on_lookdev_with_the_bundled_scripts(self):
        self._open()
        self.assertEqual(self._listed(), ["import", "lookdev"])
        self.assertEqual(self.slots._selected_template_mode(), ("lookdev", ptk.SEND_TO))
        self.assertEqual(self.slots.template_dirs[0], Path(self.mine))

    def test_a_persons_script_is_listed_and_shadows_the_bundled_one(self):
        self._mine("my_turntable", '"""Spin it."""\nBRIDGE_MODES = ("send_to",)\nSKY = __SKY_PRESET__\n')
        mine = self._mine("import", '"""My import."""\nBRIDGE_MODES = ("send_to",)\n')
        self._open()
        self.assertEqual(self._listed(), ["import", "lookdev", "my_turntable"])
        self.assertEqual(self.slots.template_path("import"), mine)
        self.assertEqual(self.slots.template_tier("import"), "user")
        # Marked as the person's own in italics and a tooltip, its label left as
        # it is: the selection persists by label (uitk's _TemplateCombo).
        self.assertEqual(self.ui.cmb000.itemText(0), "import (send_to)")
        self.assertTrue(self.ui.cmb000.itemData(0, QtCore.Qt.FontRole).italic())
        self.assertIn(str(mine), self.ui.cmb000.itemData(0, QtCore.Qt.ToolTipRole))

    def test_a_script_reading_a_hosts_bake_source_is_not_listed(self):
        """A bake reads the scene's Bake Source set, which only a host's bridge
        fills: a copy in the person's folder is listed there, not here."""
        self._mine(
            "bake",
            '"""Bake."""\nBRIDGE_MODES = ("send_to", "round_trip")\n'
            "# bake_source=__BAKE_SOURCE_SET__\n",
        )
        self._open()
        self.assertNotIn("bake", self._listed())
        from extapps.marmoset_scripts.slots import MarmosetScriptsSlots

        self.assertTrue(MarmosetScriptsSlots.needs_host("bake"))
        self.assertFalse(MarmosetScriptsSlots.needs_host("lookdev"))

    def test_the_scripts_menu_opens_your_folder_and_copies_one_to_edit(self):
        self._open()
        menu = self.ui.cmb000.menu
        self.assertEqual(menu.btn_open_templates.text(), "Open My Scripts Folder")
        with mock.patch.object(self.slots, "reveal_folder"):
            copy = self.slots.copy_to_my_scripts()
        self.assertEqual(copy, Path(self.mine, "lookdev.py"))
        self.assertTrue(copy.is_file())
        self.assertEqual(self.slots.template_tier("lookdev"), "user")


class TestMarmosetScriptsRun(_PanelCase):
    """The run: the model file, the chosen script and mode, and the Output Dir
    a run's files land in (blank: the engine's temp folder per send)."""

    def setUp(self) -> None:
        super().setUp()
        self._open()
        self.model = os.path.join(self.tmp, "crate.fbx")
        Path(self.model).write_bytes(b"fbx")
        self.slots.set_model_path(self.model)
        engine = type(self.slots.bridge)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(
            engine, "toolbag_path", new_callable=mock.PropertyMock, return_value="toolbag.exe"
        ).start()
        self.send = mock.patch.object(self.slots.bridge, "send", return_value={"script": "x"}).start()

    def test_a_blank_output_dir_leaves_the_folder_to_the_engine(self):
        self.slots._output_dir_edit.setText("")
        self.ui.b000.click()
        self.send.assert_called_once()
        kwargs = self.send.call_args.kwargs
        self.assertIsNone(kwargs["output_dir"])
        self.assertEqual((kwargs["model_path"], kwargs["template"]), (self.model, "lookdev"))
        self.assertEqual(kwargs["mode"], ptk.SEND_TO)

    def test_a_named_output_dir_keeps_the_runs_files(self):
        out = os.path.join(self.tmp, "out")
        self.slots._output_dir_edit.setText(out)
        self.ui.b000.click()
        self.assertEqual(self.send.call_args.kwargs["output_dir"], out)

    def test_a_missing_model_file_sends_nothing(self):
        self.slots.set_model_path(os.path.join(self.tmp, "gone.fbx"))
        self.ui.b000.click()
        self.send.assert_not_called()
        self.assertIn("Model file not found", self.ui.txt000.toPlainText())


if __name__ == "__main__":
    unittest.main()
