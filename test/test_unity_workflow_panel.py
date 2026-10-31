# !/usr/bin/python
# coding=utf-8
"""Tests for the Unity Workflow panel (``extapps/unity_workflow/slots.py``).

The one Unity panel, a :class:`uitk.bridge.ParamPanelSlots`: standalone it copies a
picked model file into a Unity project's ``Assets/`` via
:class:`unitytk.FileToUnityBridge`; a host that injects its engine
(``slots.engine = mtk.UnityBridge``) adds a Current Scene source, with the host's
export rows, sent through that engine with this panel's delivery attached.
Build-time wiring (param widgets, Model File + Unity Project rows, the modes), the
``set_model_path`` hand-off, the injected engine (a stand-in for a host's) and b000
dispatch are exercised against the real panel under the offscreen QPA without
launching Unity or a DCC.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct `python test/test_unity_workflow_panel.py` loads no conftest, so the sandbox is
# activated here too -- before the first QSettings, or tearDown's
# store.clear() would wipe the developer's live panel state. Idempotent.
TestSandbox.activate()


#: The panel's optional engine (installed on demand by Manage Unity Scripts).
UNITYTK = importlib.util.find_spec("unitytk") is not None
NO_UNITYTK = "unitytk is not installed (the panel installs it on demand)"


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def _host_engine(objects=("|pCube1",)):
    """A host's Unity engine as the panel reaches it (``mtk`` / ``btk``
    ``UnityBridge``): its export rows, its Scope, a send through the delivery
    the panel attaches, and the host's install route. Records what it is asked."""
    from uitk import AttributeSpec, Parameters, ParamRegistry

    class _HostRows(ParamRegistry):
        PARAMS = {
            "SCOPE": Parameters.scope_spec(),
            "INCLUDE_MATERIALS": AttributeSpec(
                key="INCLUDE_MATERIALS",
                label="Include Materials",
                kind="bool",
                default=True,
                section="Export",
            ),
            "TRIANGULATE": AttributeSpec(
                key="TRIANGULATE",
                label="Triangulate",
                kind="bool",
                default=False,
                section="Export",
            ),
        }

    class _Engine:
        built, sent, scoped, installed = [], [], [], []

        def __init__(self, deliverer=None):
            self.deliverer = deliverer
            self.project_path = None
            self.logger = logging.getLogger("test_unity_host_engine")
            type(self).built.append(self)

        @classmethod
        def params_registry(cls):
            return _HostRows

        def scope_objects(self, scope="selected"):
            type(self).scoped.append(scope)
            return list(objects)

        def send(self, objects=None, *, template, mode, params=None):
            type(self).sent.append(
                {
                    "objects": objects,
                    "template": template,
                    "params": dict(params or {}),
                    "project": self.project_path,
                    "deliverer": self.deliverer,
                }
            )
            return {"asset": "ok"}

        @staticmethod
        def install_package(spec):
            _Engine.installed.append(spec)

    return _Engine


class TestUnityWorkflowParameters(unittest.TestCase):
    def _P(self):
        from extapps.unity_workflow import parameters as P

        return P

    def test_defaults_are_unity_side_only(self) -> None:
        P = self._P()
        self.assertEqual(
            set(P.Parameters.defaults()),
            {
                # What Send to Unity copies: a mode, kept out of presets.
                "SOURCE",
                "ASSETS_SUBDIR",
                "ASSET_NAME",
                "LAUNCH_MODE",
                "UNITY_VERSION",
                # Manage Unity Scripts mode's script checklist + action combo —
                # Unity-side too (they manage the embedded unitytk package in
                # the project).
                "SCRIPTS",
                "SCRIPTS_ACTION",
            },
        )
        # No DCC export knobs: a host's engine brings its own.
        for export_key in (
            "SCOPE",
            "TRIANGULATE",
            "EMBED_TEXTURES",
            "INCLUDE_MATERIALS",
        ):
            self.assertNotIn(export_key, P.PARAMS)
        self.assertIs(P.PARAMS["SOURCE"].preset, False)
        self.assertEqual(P.PARAMS["SOURCE"].default, P.FILE_SOURCE)

    def test_referenced_keys_is_token_based(self) -> None:
        # referenced_keys is the generic __KEY__ token scan; with no tokens in
        # the text it finds nothing (the panel drives visibility explicitly
        # from _relevant_param_keys() instead — see the panel-load test).
        P = self._P()
        self.assertEqual(P.Parameters.referenced_keys("plain text"), set())
        self.assertEqual(
            P.Parameters.referenced_keys("uses __ASSET_NAME__"), {"ASSET_NAME"}
        )


class TestUnityWorkflowPanelLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.unity_workflow.launcher import UnityWorkflowUI

        self.ui = UnityWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        # Rows persist and the sandboxed store outlives the case: cleared once
        # the panel is gone, so the next case's fresh panel opens on defaults.
        store.clear()
        store.sync()

    def test_param_widgets_built_for_every_spec(self) -> None:
        from extapps.unity_workflow import parameters as P

        for key in P.PARAMS:
            self.assertIn(key, self.slots._param_widgets, f"no widget for {key}")

    def test_model_and_project_rows_exist(self) -> None:
        self.assertIsNotNone(self.slots._model_edit, "Model File row not built")
        self.assertIsNotNone(self.slots._output_dir_edit, "Unity Project row not built")

    def test_delivery_combo_shows_friendly_label(self) -> None:
        self.assertGreaterEqual(self.ui.cmb000.findText("Copy to Project"), 0)

    def test_copy_mode_shows_every_delivery_param(self) -> None:
        # Copy-to-assets shows every delivery param and hides the script
        # checklist + action combo that only Manage Unity Scripts uses -- and,
        # standalone, the Source row: one entry is no choice.
        from extapps.unity_workflow import parameters as P

        self.assertEqual(
            self.slots._relevant_param_keys(),
            set(P.PARAMS) - {"SCRIPTS", "SCRIPTS_ACTION", "SOURCE"},
        )
        self.assertFalse(self.slots._model_row.isHidden())

    def test_manage_mode_shows_only_the_script_params(self) -> None:
        # The other half of the same gate: delivery params hide in manage mode.
        with mock.patch.object(
            self.slots,
            "_selected_template_mode",
            return_value=(self.slots.MODE_MANAGE, None),
        ):
            self.assertEqual(
                self.slots._relevant_param_keys(), {"SCRIPTS", "SCRIPTS_ACTION"}
            )

    @unittest.skipUnless(UNITYTK, NO_UNITYTK)
    def test_script_checklist_populates_from_unitytk(self) -> None:
        """One checked row per optional unitytk component — discovered from
        the installed release, not hard-coded in the panel (core is implicit:
        it rides along with every install)."""
        from unitytk import TemplateDeployer

        expected = [c for c in TemplateDeployer.components() if not c.required]
        lw = self.slots._param_widgets["SCRIPTS"]
        self.assertEqual(
            [lw.item(i).text() for i in range(lw.count())],
            [c.label for c in expected],
        )
        self.assertNotIn("Core", [lw.item(i).text() for i in range(lw.count())])
        # All checked by default == the historical full-set deploy.
        self.assertEqual(self.slots._script_selection(), [c.key for c in expected])

    @unittest.skipUnless(UNITYTK, NO_UNITYTK)
    def test_action_runs_over_the_checked_scripts_only(self) -> None:
        """The action is applied to the checked components — the panel hands
        that selection straight to the engine."""
        keys = [c.key for c in self.slots._script_components]
        self.slots._write_param("SCRIPTS", keys[:1])
        self.slots._output_dir_edit.setText("C:/proj/MyUnityProject")
        with mock.patch("unitytk.TemplateDeployer.run_action", return_value=[]) as run:
            self.slots._manage_unity_scripts("install")
        run.assert_called_once_with("C:/proj/MyUnityProject", "install", keys[:1])

    def test_set_model_path_prefills_field(self) -> None:
        self.slots.set_model_path("C:/scan/robot.fbx")
        self.assertEqual(self.slots.resolved_model_path(), "C:/scan/robot.fbx")


@unittest.skipUnless(UNITYTK, NO_UNITYTK)
class TestUnityWorkflowVersionPopulate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def test_unity_version_combo_appends_installed_newest_first(self) -> None:
        from extapps.unity_workflow.launcher import UnityWorkflowUI

        editors = {
            "2021.3.1f1": "C:/U/2021/Unity.exe",
            "6000.0.5f1": "C:/U/6000/Unity.exe",
        }
        with mock.patch("unitytk.UnityFinder.find_editors", return_value=editors):
            ui = UnityWorkflowUI()
        try:
            slots = ui.sb.get_slots_instance(ui)
            cmb = slots._param_widgets["UNITY_VERSION"]
            texts = [cmb.itemText(i) for i in range(cmb.count())]
            self.assertEqual(texts[0], "Auto (newest)")
            # Discovered versions appended newest-first after the auto default.
            self.assertEqual(texts[1:], ["6000.0.5f1", "2021.3.1f1"])
        finally:
            ui.deleteLater()
            self.app.processEvents()


class TestUnityWorkflowHostsTheScene(unittest.TestCase):
    """A host injects its engine (``launch(show=False)``, then ``engine =``):
    Current Scene joins the Source row above File on Disk, the engine's export
    rows appear for it, and a send goes through the engine with this panel's
    delivery. The stand-in engine is :func:`_host_engine`. Added: 2026-10-31
    (one Unity app: tentacle's Unity Bridge panel folded in)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.unity_workflow.launcher import UnityWorkflowUI

        self.tmp = tempfile.mkdtemp(prefix="unity_workflow_host_")
        self.project = os.path.join(self.tmp, "Proj")
        os.makedirs(os.path.join(self.project, "Assets"))
        self.ui = UnityWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.engine = _host_engine()

    def tearDown(self) -> None:
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        store.clear()
        store.sync()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _sources(self):
        combo = self.slots._param_widgets["SOURCE"]
        return [combo.itemText(i) for i in range(combo.count())]

    def _group_index(self, key):
        layout = self.slots._param_group.layout()
        return layout.indexOf(self.slots._param_rows[key])

    def test_standalone_offers_no_source_choice(self) -> None:
        self.assertIsNone(self.slots.engine)
        self.assertEqual(self._sources(), ["File on Disk"])
        self.assertNotIn("SOURCE", self.slots._relevant_param_keys())
        self.assertNotIn("SCOPE", self.slots._param_widgets)

    def test_an_injected_engine_offers_the_current_scene_first(self) -> None:
        self.slots.engine = self.engine
        self.assertEqual(self._sources(), ["Current Scene", "File on Disk"])
        self.assertEqual(self.slots._read_param("SOURCE"), "scene")
        keys = self.slots._relevant_param_keys()
        self.assertTrue({"SOURCE", "SCOPE", "INCLUDE_MATERIALS"} <= keys, keys)
        self.assertTrue(self.slots._model_row.isHidden(), "nothing is picked")

    def test_the_hosts_rows_sit_between_the_source_and_the_unity_rows(self) -> None:
        self.slots.engine = self.engine
        self.assertLess(self._group_index("SOURCE"), self._group_index("SCOPE"))
        self.assertLess(
            self._group_index("TRIANGULATE"), self._group_index("ASSETS_SUBDIR")
        )
        self.assertIn("Export", self.slots._section_separators)

    def test_file_on_disk_hides_the_hosts_rows(self) -> None:
        self.slots.engine = self.engine
        self.slots._write_param("SOURCE", "file")
        keys = self.slots._relevant_param_keys()
        self.assertFalse({"SCOPE", "INCLUDE_MATERIALS", "TRIANGULATE"} & keys, keys)
        self.assertIn("SOURCE", keys)
        self.assertFalse(self.slots._model_row.isHidden())

    def test_the_same_engine_again_changes_nothing(self) -> None:
        self.slots.engine = self.engine
        rows = dict(self.slots._param_rows)
        self.slots.engine = self.engine
        self.slots.engine = _host_engine()  # another host: its rows, no copies
        self.assertEqual(set(self.slots._param_rows), set(rows))
        self.assertEqual(self._sources(), ["Current Scene", "File on Disk"])

    def _next_session(self, inject_before_show):
        """A new panel over the same store, the engine injected before or
        after its first show; the window is closed with the case."""
        from extapps.unity_workflow.launcher import UnityWorkflowUI

        ui = UnityWorkflowUI()
        self.addCleanup(ui.deleteLater)
        slots = ui.sb.get_slots_instance(ui)
        if inject_before_show:
            slots.engine = self.engine
        ui.show()
        self.app.processEvents()
        if not inject_before_show:
            slots.engine = self.engine
        return slots

    def test_a_host_rows_saved_value_restores_whenever_the_engine_arrives(
        self,
    ) -> None:
        """The host's rows are built after the panel: before its first show
        they restore with the rest, after it at once (``add_param_rows``) --
        so a carried or last-session value reaches them either way."""
        self.slots.engine = self.engine
        self.ui.show()
        self.app.processEvents()
        self.slots._write_param("INCLUDE_MATERIALS", False)
        self.slots._write_param("SCOPE", "visible")
        self.app.processEvents()
        for before in (True, False):
            with self.subTest(inject_before_show=before):
                slots = self._next_session(before)
                self.assertIs(slots._read_param("INCLUDE_MATERIALS"), False)
                self.assertEqual(slots._read_param("SCOPE"), "visible")

    def test_the_model_file_label_keeps_the_label_column(self) -> None:
        self.slots.engine = self.engine
        self.assertEqual(
            self.slots._model_label.minimumWidth(), self.slots.LABEL_MIN_WIDTH
        )

    def test_an_optional_package_installs_through_the_host(self) -> None:
        self.slots.engine = self.engine
        self.slots._install_optional_package("unitytk>=0.1.0")
        self.assertEqual(self.engine.installed, ["unitytk>=0.1.0"])

    @unittest.skipUnless(UNITYTK, NO_UNITYTK)
    def test_a_scene_send_goes_through_the_engine_with_the_panels_delivery(
        self,
    ) -> None:
        self.slots.engine = self.engine
        self.slots._output_dir_edit.setText(self.project)
        self.slots._write_param("SCOPE", "visible")
        self.slots._write_param("ASSETS_SUBDIR", "Models")
        self.ui.b000.click()
        (sent,) = self.engine.sent
        self.assertEqual(self.engine.scoped, ["visible"])
        self.assertEqual(sent["objects"], ["|pCube1"])
        self.assertEqual(sent["template"], "copy_to_assets")
        self.assertEqual(sent["project"], self.project)
        self.assertIs(sent["deliverer"], self.slots.bridge.deliverer)
        self.assertEqual(sent["params"]["ASSETS_SUBDIR"], "Models")
        self.assertEqual(sent["params"]["SCOPE"], "visible")
        self.assertEqual(len(self.engine.built), 1)

    @unittest.skipUnless(UNITYTK, NO_UNITYTK)
    def test_an_empty_scope_sends_nothing_and_says_why(self) -> None:
        engine = _host_engine(objects=())
        self.slots.engine = engine
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertEqual(engine.sent, [])
        self.assertIn("Nothing selected", self.ui.txt000.toPlainText())

    def test_without_unitytk_a_scene_send_says_what_it_needs(self) -> None:
        self.slots.engine = self.engine
        self.slots._output_dir_edit.setText(self.project)
        with mock.patch.object(type(self.slots), "peek_bridge", return_value=None):
            self.ui.b000.click()
        self.assertEqual(self.engine.sent, [])
        self.assertIn("Install / Update", self.ui.txt000.toPlainText())

    def test_a_scene_send_without_a_project_asks_for_one(self) -> None:
        self.slots.engine = self.engine
        self.slots._output_dir_edit.setText("")
        self.ui.b000.click()
        self.assertEqual(self.engine.sent, [])


@unittest.skipUnless(UNITYTK, NO_UNITYTK)
class TestUnityWorkflowVersionOrder(unittest.TestCase):
    def test_unity_version_combo_orders_same_major_numerically(self) -> None:
        """`_populate_unity_versions` must list editors newest-first *numerically*.

        A lexicographic sort ranks 2020.3.9f1 above 2020.3.10f1 (because '9' > '1'
        at the differing char), inverting the documented 'newest first' order for
        same-major versions. The fix routes ordering through
        UnityFinder.version_sort_key. Exercised against a stub `self` so no live
        Unity / full Qt UI construction is needed.
        """
        from extapps.unity_workflow.slots import UnityWorkflowSlots

        class _FakeCombo:
            def __init__(self):
                self.items = []

            def addItem(self, text, data):
                self.items.append(text)

        combo = _FakeCombo()
        # Older patch (2020.3.9f1) must end up BELOW the newer 2020.3.10f1 despite
        # sorting higher lexicographically.
        editors = {
            "2020.3.9f1": "C:/U/2020.3.9f1/Unity.exe",
            "2020.3.10f1": "C:/U/2020.3.10f1/Unity.exe",
        }
        stub = types.SimpleNamespace(_param_widgets={"UNITY_VERSION": combo})
        with mock.patch("unitytk.UnityFinder.find_editors", lambda: editors):
            UnityWorkflowSlots._populate_unity_versions(stub)

        self.assertEqual(combo.items, ["2020.3.10f1", "2020.3.9f1"])


@unittest.skipUnless(UNITYTK, NO_UNITYTK)  # stubs the engine's send
class TestUnityWorkflowDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.unity_workflow.launcher import UnityWorkflowUI

        self.tmp = tempfile.mkdtemp(prefix="unity_workflow_")
        self.project = os.path.join(self.tmp, "Proj")
        os.makedirs(os.path.join(self.project, "Assets"))
        self.model = os.path.join(self.tmp, "robot.fbx")
        with open(self.model, "wb") as fh:
            fh.write(b"FBX")
        self.ui = UnityWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        # Stub the engine's send so nothing is copied/launched; capture the call.
        self.captured: dict = {}

        def fake_send(model_path=None, template=None, mode=None, params=None):
            self.captured["model_path"] = model_path
            self.captured["project"] = self.slots.bridge.project_path
            self.captured["params"] = params
            return {"asset": "ok"}

        self.slots.bridge.send = fake_send

    def tearDown(self) -> None:
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        # Rows persist and the sandboxed store outlives the case: cleared once
        # the panel is gone, so the next case's fresh panel opens on defaults.
        store.clear()
        store.sync()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_b000_dispatches_with_model_and_project(self) -> None:
        self.slots.set_model_path(self.model)
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertEqual(self.captured.get("model_path"), self.model)
        self.assertEqual(self.captured.get("project"), self.project)
        self.assertIn("ASSETS_SUBDIR", self.captured.get("params", {}))

    def test_b000_aborts_without_model(self) -> None:
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)

    def test_b000_aborts_without_project(self) -> None:
        self.slots.set_model_path(self.model)
        self.slots._output_dir_edit.setText("")
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)

    def test_b000_aborts_on_missing_model_file(self) -> None:
        self.slots.set_model_path(os.path.join(self.tmp, "gone.fbx"))
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)


if __name__ == "__main__":
    unittest.main()
