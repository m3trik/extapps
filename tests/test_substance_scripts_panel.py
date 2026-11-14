# !/usr/bin/python
# coding=utf-8
"""Tests for Substance Scripts (``extapps/substance_scripts``).

The standalone Painter panel, a :class:`uitk.bridge.ParamPanelSlots` script
manager over the vendored engine: the scripts it lists (the bundled ones, a
person's own, which shadow them), the rows it shows (a script's own, never a
host's), the Mesh File a script on a mesh needs, the Painter row, and the job
it follows. No Painter is reached: the engine's ``send`` is stood in for, and
the engine itself is tested where it lives (the Maya library's
``test_substance_bridge.py``).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct `python tests/test_substance_scripts_panel.py` loads no conftest, so
# the sandbox is activated here too -- before the first QSettings or user folder.
TestSandbox.activate()

import pythontk as ptk  # noqa: E402

BUILT_IN = ["bake_lighting", "bake_mesh_maps", "export_textures", "new_project", "update_mesh"]


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class _PanelCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="substance_scripts_panel_")
        self.mine = ptk.ScriptTemplate.user_dir("substance")
        self.addCleanup(shutil.rmtree, self.mine, True)

    def _open(self):
        from extapps.substance_scripts.launcher import SubstanceScriptsUI

        self.ui = SubstanceScriptsUI()
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

    def _choose(self, script):
        combo = self.ui.cmb000
        index = next(i for i in range(combo.count()) if combo.itemData(i)[0] == script)
        combo.setCurrentIndex(index)
        self.slots._on_template_changed()

    def _shown(self):
        return {k for k, row in self.slots._param_rows.items() if not row.isHidden()}


class TestSubstanceScriptsList(_PanelCase):
    def test_it_opens_on_new_project_with_the_bundled_scripts(self):
        self._open()
        self.assertEqual(self._listed(), BUILT_IN)
        self.assertEqual(self.slots._selected_template_mode(), ("new_project", ptk.SEND_TO))
        self.assertEqual(self.slots.template_dirs[0], Path(self.mine))

    def test_a_persons_script_is_listed_and_shadows_the_bundled_one(self):
        self._mine("my_fill", '"""Add a fill layer."""\nWORKS_ON = "project"\n')
        mine = self._mine("export_textures", '"""My export."""\n')
        self._open()
        self.assertEqual(self._listed(), sorted(BUILT_IN + ["my_fill"]))
        self.assertEqual(self.slots.template_path("export_textures"), mine)
        self.assertEqual(self.slots.template_tier("export_textures"), "user")

    def test_a_persons_script_shows_the_rows_it_declares(self):
        self._mine(
            "my_fill",
            '"""Add a fill layer."""\nWORKS_ON = "project"\n'
            "# Rows: __PAINTER__\n"
            '# Row: __FILL_OPACITY__ float 0.5 "Fill Opacity" min=0 max=1\n',
        )
        self._open()
        self._choose("my_fill")
        self.assertIn("FILL_OPACITY", self._shown())
        self.assertEqual(self.slots.collect_param_values()["FILL_OPACITY"], 0.5)

    def test_a_hosts_rows_are_never_shown(self):
        """New Project reads the host's Scope, textures and bake source: with no
        host they mean nothing, so they stay hidden."""
        self._open()
        self._choose("new_project")
        shown = self._shown()
        from extapps.substance_scripts.slots import HOST_ROWS

        self.assertFalse(shown & set(HOST_ROWS), shown & set(HOST_ROWS))
        self.assertIn("PAINTER_RESOLUTION", shown)

    def test_the_bake_scripts_settings_are_its_own_rows(self):
        self._open()
        self._choose("bake_lighting")
        self.assertTrue({"AO_RAYS", "BAKE_RESOLUTION", "INCLUDE_CURVATURE"} <= self._shown())


class TestSubstanceScriptsPainters(_PanelCase):
    def test_the_painter_row_lists_running_painters(self):
        from extapps.substance_scripts._substance_scripts import SubstanceScripts

        records = [{"id": "r1", "pid": 5, "state": {"project": {"name": "crate"}}}]
        with mock.patch.object(SubstanceScripts, "painters", staticmethod(lambda: records)):
            self._open()
            self.slots.refresh_painters()
        widget = self.slots._param_widgets["PAINTER"]
        values = [widget.itemData(i) for i in range(widget.count())]
        self.assertEqual(values, ["auto", "new", "r1"])

    def test_install_in_painter_is_the_persons_action(self):
        """uitk's shared action, from the engine's ``RPC_PLUGIN``: in the
        header menu, and run by the shared installer on that spec."""
        from extapps.substance_scripts._substance_scripts import SubstanceScripts

        self._open()
        labels = {item[3]: item[0] for item in self.slots.header_menu_items()}
        self.assertEqual(labels["install_rpc_plugin"], "Install in Painter")
        with mock.patch.object(ptk.PluginInstaller, "install") as install:
            self.slots.install_rpc_plugin()
        install.assert_called_once_with(SubstanceScripts.RPC_PLUGIN, logger=self.slots.bridge.logger)


class TestSubstanceScriptsRun(_PanelCase):
    def setUp(self) -> None:
        super().setUp()
        self._open()
        self.mesh = os.path.join(self.tmp, "crate.fbx")
        Path(self.mesh).write_bytes(b"fbx")
        self.slots.set_mesh_path(self.mesh)
        self.addCleanup(mock.patch.stopall)
        self.send = mock.patch.object(self.slots.bridge, "send", return_value={"job": None}).start()

    def test_new_project_runs_on_the_mesh_file(self):
        self.ui.b000.click()
        kwargs = self.send.call_args.kwargs
        self.assertEqual((kwargs["mesh"], kwargs["template"], kwargs["target"]), (self.mesh, "new_project", "auto"))
        self.assertEqual(kwargs["mode"], ptk.SEND_TO)

    def test_a_script_on_a_project_needs_no_mesh(self):
        self.slots.set_mesh_path("")
        self._choose("export_textures")
        self.ui.b000.click()
        self.assertIsNone(self.send.call_args.kwargs["mesh"])

    def test_a_script_on_a_mesh_without_one_sends_nothing(self):
        self.slots.set_mesh_path(os.path.join(self.tmp, "gone.fbx"))
        self.ui.b000.click()
        self.send.assert_not_called()
        self.assertIn("Mesh file not found", self.ui.txt000.toPlainText())

    def test_the_job_is_followed_off_the_ui_thread_and_reported(self):
        self.send.return_value = {"job": "j1", "connection": object()}
        from extapps.substance_scripts._substance_scripts import SubstanceScripts

        import time

        done = {"state": "done", "label": "New Project", "report": ["made it"]}
        with mock.patch.object(SubstanceScripts, "follow", staticmethod(lambda result: done)):
            self.ui.b000.click()
            deadline = time.time() + 5
            while "finished in Painter" not in self.ui.txt000.toPlainText() and time.time() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
        self.assertIn("made it", self.ui.txt000.toPlainText())
        self.assertIn("New Project finished in Painter", self.ui.txt000.toPlainText())

    def test_while_painter_starts_the_panel_stays_live_then_follows_the_job(self):
        """The engine's waits run in the panel's BackgroundTask; the job is
        followed once it is queued, and Run meanwhile sends nothing more."""
        import threading
        import time

        from extapps.substance_scripts._substance_scripts import SubstanceScripts

        gate = threading.Event()

        def send(**kw):
            kw["background"](gate.wait, lambda _ok: kw["on_queued"]({"job": "j1", "connection": object()}))
            return {"pending": True}

        self.send.side_effect = send
        done = {"state": "done", "label": "New Project", "report": []}
        with mock.patch.object(SubstanceScripts, "follow", staticmethod(lambda result: done)):
            self.ui.b000.click()
            self.ui.b000.click()
            self.assertEqual(self.send.call_count, 1)
            self.assertIn("still starting", self.ui.txt000.toPlainText())
            gate.set()
            deadline = time.time() + 5
            while "finished in Painter" not in self.ui.txt000.toPlainText() and time.time() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
        self.assertIn("New Project finished in Painter", self.ui.txt000.toPlainText())


class TestOneFollowedJobAtATime(_PanelCase):
    """The panel follows one job: a second Run while it does replaced the one
    it followed, so Cancel Script reached the wrong job and the first one's
    end cleared the panel's state under the second."""

    def setUp(self) -> None:
        super().setUp()
        self._open()
        self._choose("export_textures")
        self.addCleanup(mock.patch.stopall)
        self.send = mock.patch.object(
            self.slots.bridge, "send", side_effect=lambda **kw: {"job": f"j{self.send.call_count}", "connection": object()}
        ).start()

    def test_a_run_while_a_job_is_followed_sends_nothing_and_cancel_still_reaches_it(self):
        import threading
        import time

        from extapps.substance_scripts._substance_scripts import SubstanceScripts

        gate = threading.Event()
        done = {"state": "done", "job": "j1", "label": "Export Textures", "report": []}
        with mock.patch.object(SubstanceScripts, "follow", staticmethod(lambda result: gate.wait(5) and done)):
            self.ui.b000.click()
            first = self.slots._running
            self.ui.b000.click()
            self.assertEqual(self.send.call_count, 1)
            self.assertIn("still running in Painter", self.ui.txt000.toPlainText())
            self.assertIs(self.slots._running, first, "Cancel Script still reaches the job under way")
            gate.set()
            deadline = time.time() + 5
            while self.slots._running is not None and time.time() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.ui.b000.click()  # the job ended: the next Run goes out
        self.assertEqual(self.send.call_count, 2)


class TestSubstanceWorkflowRenamed(unittest.TestCase):
    def test_the_old_names_say_where_they_went(self):
        import extapps

        for name, home in (
            ("SubstanceWorkflowUI", "SubstanceScriptsUI"),
            ("SubstanceWorkflowSlots", "SubstanceScriptsSlots"),
            ("PainterConnection", "SubstanceScripts"),
            ("Job", "SubstanceScripts"),
        ):
            with self.subTest(name):
                with self.assertRaises(Exception) as ctx:
                    getattr(extapps, name)
                self.assertIn(home, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
