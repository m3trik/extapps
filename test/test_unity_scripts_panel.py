# !/usr/bin/python
# coding=utf-8
"""Tests for Unity Scripts (``extapps/unity_scripts``).

The one Unity panel, a :class:`uitk.bridge.ParamPanelSlots` script manager:
its scripts (the built-in ``templates/*.cs`` and a person's own, which shadow
them), the project's connection (the editor package it installs, the job
queue the package serves), the delivery (a file copied into ``Assets/``, then
the script handed to Unity), and the panel (the rows a script names, the
Source a host's injected engine adds, the run and its report). Unity itself is
stood in for by a Python worker serving the same ``ptk.JobQueue``: no editor,
no DCC, the offscreen QPA.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct `python test/test_unity_scripts_panel.py` loads no conftest, so the
# sandbox is activated here too -- before the first QSettings or user folder.
TestSandbox.activate()

import pythontk as ptk  # noqa: E402

PKG = Path(__file__).resolve().parents[1] / "extapps" / "unity_scripts"


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def _project(root: str) -> str:
    """A Unity project folder: ``Assets/`` and ``ProjectSettings/``."""
    project = os.path.join(root, "Proj")
    for sub in ("Assets", "ProjectSettings"):
        os.makedirs(os.path.join(project, sub))
    return project


class _Unity:
    """A stand-in for the editor package: a Python worker serving the
    project's queue (``ptk.JobQueue``), answering each ``script.run`` as the
    C# worker does (``result``: the script, its report lines, the console)."""

    def __init__(self, project: str, answer=None):
        from extapps.unity_scripts.unity_connection import UnityConnection

        self.queue = UnityConnection(project).queue
        self.jobs = []
        self.answer = answer or (lambda job: {"script": job.get("script"), "report": ["ok"], "console": []})
        self._thread = threading.Thread(
            target=self.queue.serve, args=(self._handle,), kwargs={"poll": 0.02, "beat": 0.05}, daemon=True
        )

    def _handle(self, job):
        self.jobs.append(job)
        return self.answer(job)

    def __enter__(self):
        self._thread.start()
        for _ in range(200):  # until it beats
            if self.queue.alive(5):
                break
            threading.Event().wait(0.01)
        return self

    def __exit__(self, *exc):
        self.queue.stop()
        self._thread.join(10)


def _host_engine(objects=("|pCube1",)):
    """A host's Unity engine as the panel reaches it (``mtk`` / ``btk``
    ``UnityBridge``): its export rows, its Scope, a send through the delivery
    the panel attaches. Records what it is asked."""
    from uitk import Parameters, ParamRegistry

    class _HostRows(ParamRegistry):
        PARAMS = {"SCOPE": Parameters.scope_spec()}

    class _Engine:
        built, sent, scoped = [], [], []

        def __init__(self, deliverer=None, decide_check_failure=None):
            self.deliverer = deliverer
            self.decide_check_failure = decide_check_failure
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
            return {"job": None}

    return _Engine


# ---------------------------------------------------------------------- the scripts
class TestUnityScripts(unittest.TestCase):
    """The built-in scripts and a person's own: what the panel lists, what each
    takes, and the header contract the editor package compiles against."""

    def setUp(self):
        from extapps.unity_scripts.unity_deliverer import UnityDeliverer

        self.D = UnityDeliverer
        self.mine = ptk.ScriptTemplate.user_dir(UnityDeliverer.SCRIPTS_APP)
        self.addCleanup(shutil.rmtree, self.mine, True)

    def test_the_built_ins_are_listed_by_their_names(self):
        names = [name for name, _mode in self.D.list_template_modes()]
        self.assertEqual(names, ["MakePrefab", "ReimportFolder", "SendToUnity"])
        self.assertEqual(self.D.label("SendToUnity"), "Send to Unity")
        self.assertEqual(self.D.label("ReimportFolder"), "Reimport Folder")

    def test_each_built_in_declares_what_it_takes(self):
        self.assertEqual(self.D.sources("SendToUnity"), ("scene", "file"))
        self.assertEqual(self.D.sources("MakePrefab"), ("scene", "file"))
        self.assertEqual(self.D.sources("ReimportFolder"), (), "it runs on the project alone")

    def test_a_built_in_is_a_compilable_script_the_panel_reads(self):
        """Its class is named as its file, it has a ``[UnityScript]`` method,
        and every row token it names is a row the panel declares."""
        from extapps.unity_scripts import parameters as P

        for path in sorted((PKG / "templates").glob("*.cs")):
            with self.subTest(script=path.stem):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, rf"\bclass {path.stem}\b")
                self.assertIn("[UnityScript]", text)
                self.assertIn("using M3trik.UnityScripts;", text)
                tokens = set(re.findall(r"__([A-Z][A-Z0-9_]*)__", text))
                self.assertTrue(tokens <= set(P.PARAMS), tokens - set(P.PARAMS))
                self.assertIsNotNone(ptk.ScriptTemplate.declared_values(path, self.D.SOURCES_FIELD))

    def test_a_persons_script_shadows_the_built_in_of_its_name(self):
        os.makedirs(self.mine, exist_ok=True)
        mine = Path(self.mine, "SendToUnity.cs")
        mine.write_text('// Mine.\n// SOURCES = ("file",)\n', encoding="utf-8")
        Path(self.mine, "MyTool.cs").write_text("// Mine too.\n", encoding="utf-8")
        self.assertEqual(self.D.template_path("SendToUnity"), mine)
        self.assertEqual(self.D.sources("SendToUnity"), ("file",))
        self.assertEqual(self.D.sources("MyTool"), ("scene", "file"), "no SOURCES line: both")
        names = [name for name, _ in self.D.list_template_modes()]
        self.assertEqual(names.count("SendToUnity"), 1)
        self.assertIn("MyTool", names)


# ---------------------------------------------------------------------- the connection
class TestUnityConnection(unittest.TestCase):
    """A project's connection: the editor package installed, updated and
    removed, and the queue the package serves."""

    def setUp(self):
        from extapps.unity_scripts.unity_connection import UnityConnection

        self.tmp = tempfile.mkdtemp(prefix="unity_connection_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = _project(self.tmp)
        self.C = UnityConnection
        self.connection = UnityConnection(self.project)

    def test_a_project_is_a_folder_with_assets_and_settings(self):
        self.assertTrue(self.C.is_project(self.project))
        self.assertFalse(self.C.is_project(self.tmp))
        self.assertFalse(self.C.is_project(""))

    def test_install_update_and_remove(self):
        c = self.connection
        self.assertEqual(c.state(), "missing")
        written = c.install()
        self.assertTrue(written)
        self.assertEqual(c.state(), "installed")
        self.assertEqual(c.installed_version(), self.C.bundled_version())
        worker = c.installed_dir / "Editor" / "ScriptWorker.cs"
        meta = Path(str(worker) + ".meta")
        meta.write_text("guid: kept", encoding="utf-8")  # what Unity made for it
        stale = c.installed_dir / "Editor" / "Gone.cs"
        stale.write_text("// no longer shipped", encoding="utf-8")
        worker.write_text("// edited", encoding="utf-8")
        self.assertEqual(c.state(), "outdated")
        c.install()
        self.assertEqual(c.state(), "installed")
        self.assertEqual(meta.read_text(encoding="utf-8"), "guid: kept", "a kept file keeps its GUID")
        self.assertFalse(stale.exists(), "a file no longer shipped goes")
        scripts = Path(self.project, "Assets", "M3trikScripts")
        scripts.mkdir()
        (scripts / "SendToUnity.cs").write_text("// a copy", encoding="utf-8")
        self.assertTrue(c.remove())
        self.assertEqual(c.state(), "missing")
        self.assertFalse(scripts.exists(), "its copies would not compile without it")

    def test_the_package_is_versioned_on_its_own_and_judged_by_content(self):
        """Its version is the package's (a release that leaves the C# alone
        prompts no update); whether a project's copy is current is its files."""
        self.assertRegex(self.C.bundled_version(), r"^\d+\.\d+\.\d+$")
        self.connection.install()
        self.assertEqual(self.connection.state(), "installed")
        script = self.connection.installed_dir / "Editor" / "ScriptWorker.cs"
        script.write_text(script.read_text(encoding="utf-8") + "\n// edited", encoding="utf-8")
        self.assertEqual(self.connection.state(), "outdated", "a file differs: same version or not")

    def test_the_cancel_suffix_is_the_packages(self):
        worker = (PKG / "unity_package" / "Editor" / "ScriptWorker.cs").read_text(encoding="utf-8")
        self.assertIn(f'CancelSuffix = "{self.C.CANCEL_SUFFIX}"', worker)
        self.assertIn('Folder = "Library/M3trikUnityScripts"', worker)
        self.assertEqual(self.C.QUEUE[:2], ("Library", "M3trikUnityScripts"))

    def test_status_says_what_the_project_can_do(self):
        c = self.connection
        self.assertIn("not installed", c.status())
        c.install()
        self.assertIn("open the project in Unity", c.status())
        with _Unity(self.project):
            self.assertTrue(c.serving())
            self.assertIn("is serving this project", c.status())

    def test_a_script_runs_in_the_serving_editor_and_answers(self):
        script = PKG / "templates" / "SendToUnity.cs"
        with _Unity(self.project) as unity:
            job = self.connection.run(str(script), {"PLACE_IN_SCENE": True}, asset="Assets/Imported/Crate.fbx")
            record = self.connection.wait(job, timeout=10)
        self.assertEqual(record["state"], "done")
        self.assertEqual(record["result"]["report"], ["ok"])
        (sent,) = unity.jobs
        self.assertEqual(sent["op"], "script.run")
        self.assertEqual(sent["script"], "SendToUnity")
        self.assertEqual(sent["source"], script.read_text(encoding="utf-8").replace("\r\n", "\n"))
        self.assertEqual(sent["args"], {"PLACE_IN_SCENE": True})
        self.assertEqual(sent["asset"], "Assets/Imported/Crate.fbx")

    def test_a_failed_script_returns_its_error(self):
        def fail(job):
            raise RuntimeError("did not compile")

        with _Unity(self.project, fail):
            job = self.connection.run(str(PKG / "templates" / "SendToUnity.cs"))
            record = self.connection.wait(job, timeout=10)
        self.assertEqual(record["state"], "failed")
        self.assertIn("did not compile", record["error"])

    def test_a_queued_script_cancels_and_a_running_one_is_asked(self):
        c = self.connection
        job = c.run(str(PKG / "templates" / "ReimportFolder.cs"))
        c.cancel(job)
        self.assertIsNone(c.queue.status(job), "withdrawn before it ran")
        running = c.queue.submit({"op": "script.run"})
        os.replace(
            os.path.join(c.queue.root, running + ptk.JobQueue.SUFFIXES["queued"]),
            os.path.join(c.queue.root, running + ptk.JobQueue.SUFFIXES["running"]),
        )
        c.cancel(running)
        self.assertTrue(os.path.isfile(os.path.join(c.queue.root, running + self.C.CANCEL_SUFFIX)))

    def test_an_editor_that_stops_serving_is_said(self):
        c = self.connection
        c.GONE_GRACE = 0.1
        job = c.run(str(PKG / "templates" / "ReimportFolder.cs"))
        with self.assertRaisesRegex(RuntimeError, "stopped serving"):
            c.wait(job, timeout=5)

    def test_a_heartbeat_missing_a_moment_is_not_a_closed_editor(self):
        """The package replaces its heartbeat file every beat, so a look can
        find none: the wait goes on until Unity has been unheard a while.
        (Measured live: a script reported lost while Unity ran it.)"""
        c = self.connection
        job = c.run(str(PKG / "templates" / "ReimportFolder.cs"))
        unity = _Unity(self.project)
        timer = threading.Timer(0.5, unity.__enter__)
        timer.start()
        self.addCleanup(unity.__exit__)
        record = c.wait(job, timeout=10, poll=0.02)
        self.assertEqual(record["state"], "done")

    def _heartbeat(self, **fields):
        """Unity's heartbeat as the package writes it, fresh now."""
        import time

        os.makedirs(self.connection.queue.root, exist_ok=True)
        beat = {"pid": 1, "state": "serving", "paused": False, "job": None, "beat": time.time()}
        beat.update(fields)
        with open(os.path.join(self.connection.queue.root, ptk.JobQueue.WORKER), "w", encoding="utf-8") as f:
            json.dump(beat, f)

    def test_a_script_cancelled_while_it_waits_its_turn_returns(self):
        """Unity serving but busy (compiling, importing, in Play mode): the
        queued script is withdrawn and the wait answers at once."""
        c = self.connection
        self._heartbeat()
        job = c.run(str(PKG / "templates" / "ReimportFolder.cs"))
        record = c.wait(job, timeout=3, poll=0.02, cancelled=lambda: True)
        self.assertEqual(record["state"], "failed")
        self.assertIn("Cancelled before Unity ran it", record["error"])
        self.assertIsNone(c.queue.status(job))

    def test_a_script_unity_will_not_take_is_withdrawn_not_left(self):
        """Paused (or closed) before it took the script: nothing waits to run on
        the next resume or open, against whatever scene Unity restored."""
        c = self.connection
        c.GONE_GRACE = 0.1
        self._heartbeat(state="stopped", paused=True)
        job = c.run(str(PKG / "templates" / "ReimportFolder.cs"))
        with self.assertRaisesRegex(RuntimeError, "withdrawn"):
            c.wait(job, timeout=3, poll=0.02)
        self.assertIsNone(c.queue.status(job))

    def test_a_script_unity_is_running_is_waited_for_while_it_reloads_or_pauses(self):
        """Its heartbeat names the job: quiet through a domain reload, or saying
        "stopped" when paused mid-run, Unity still finishes it."""
        import threading

        c = self.connection
        job = c.run(str(PKG / "templates" / "ReimportFolder.cs"))
        root = c.queue.root
        os.replace(
            os.path.join(root, job + ptk.JobQueue.SUFFIXES["queued"]),
            os.path.join(root, job + ptk.JobQueue.SUFFIXES["running"]),
        )
        self._heartbeat(state="stopped", paused=True, job=job, beat=__import__("time").time() - 2 * c.STALE)

        def finish():
            with open(os.path.join(root, job + ptk.JobQueue.SUFFIXES["done"]), "w", encoding="utf-8") as f:
                json.dump({"result": {"report": ["done after a reload"]}}, f)
            os.remove(os.path.join(root, job + ptk.JobQueue.SUFFIXES["running"]))

        timer = threading.Timer(0.3, finish)
        timer.start()
        self.addCleanup(timer.cancel)
        record = c.wait(job, timeout=5, poll=0.02)
        self.assertEqual(record["state"], "done")
        self.assertEqual(record["result"]["report"], ["done after a reload"])


def _carrier_fbx(path: str, channels) -> str:
    """Write *path*: a binary FBX (7700 layout) holding a ``Crate`` model and
    a ``data_export`` carrier whose user properties are *channels*
    ``{record key: payload}`` (stored as JSON) -- what a DCC export hands the
    deliverer, written with no DCC."""
    import struct

    head_fmt, head_len = "<QQQ", 24

    def prop(value):
        if isinstance(value, int):
            return b"L" + struct.pack("<q", value)
        return b"S" + struct.pack("<I", len(value)) + value

    def record(name, props, children, offset):
        body_props = b"".join(prop(p) for p in props)
        head = head_len + 1 + len(name)
        body, at = b"", offset + head + len(body_props)
        for child in children:
            chunk = record(*child, at)
            body, at = body + chunk, at + len(chunk)
        if children:
            body += b"\0" * (head_len + 1)
        end = offset + head + len(body_props) + len(body)
        return (
            struct.pack(head_fmt, end, len(props), len(body_props))
            + bytes((len(name),)) + name + body_props + body
        )

    rows = [
        (b"P", [key.encode(), b"KString", b"", b"U", json.dumps(value).encode()], [])
        for key, value in channels.items()
    ]
    models = [
        (b"Model", [1001, b"Crate\x00\x01Model", b"Mesh"], []),
        (b"Model", [1002, b"data_export\x00\x01Model", b"Null"], [(b"Properties70", [], rows)]),
    ]
    roots = [
        (b"Objects", [], models),
        (b"Connections", [], [(b"C", [b"OO", m[1][0], 0], []) for m in models]),
    ]
    magic = b"Kaydara FBX Binary  \x00\x1a\x00"
    body, offset = b"", len(magic) + 4
    for root in roots:
        chunk = record(*root, offset)
        body, offset = body + chunk, offset + len(chunk)
    at = offset + head_len + 1 + 16
    pad = ((at + 15) & ~15) - at or 16
    tail = (
        b"\0" * (head_len + 1) + bytes(range(16)) + b"\0" * pad + b"\0" * 4
        + struct.pack("<I", 7700) + b"\0" * 120 + bytes(16)
    )
    with open(path, "wb") as fh:
        fh.write(magic + struct.pack("<I", 7700) + body + tail)
    return path



# ---------------------------------------------------------------------- the delivery
class TestUnityDeliverer(unittest.TestCase):
    """The delivery: a file into the project's Assets/, by the panel's keys,
    then the script handed to Unity when it serves the project."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="unity_deliverer_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = _project(self.tmp)
        self.model = os.path.join(self.tmp, "robot.obj")
        with open(self.model, "w", encoding="utf-8") as fh:
            fh.write("v 0 0 0\n")

    def _bridge(self):
        from extapps.unity_scripts.unity_deliverer import UnityDeliverer

        return ptk.FileDeliveryBridge(target_folder=self.project, deliverer=UnityDeliverer())

    def test_with_unity_closed_the_file_lands_and_no_job_waits(self):
        result = self._bridge().send(self.model, template="SendToUnity")
        self.assertEqual(result["file"], os.path.join(self.project, "Assets", "Imported", "robot.obj"))
        self.assertTrue(os.path.isfile(result["file"]))
        self.assertEqual(result["asset"], "Assets/Imported/robot.obj")
        self.assertIsNone(result["job"], "a job left for the next open would act on a restored scene")
        self.assertEqual(os.listdir(os.path.join(self.project, "Library", "M3trikUnityScripts", "queue"))
                         if os.path.isdir(os.path.join(self.project, "Library")) else [], [])

    def test_with_unity_serving_the_script_runs_on_the_file(self):
        with _Unity(self.project) as unity:
            result = self._bridge().send(self.model, template="SendToUnity", params={"ASSETS_SUBDIR": "Models"})
            self.assertIsNotNone(result["job"])
            from extapps.unity_scripts.unity_connection import UnityConnection

            UnityConnection(self.project).wait(result["job"], timeout=10)
        (job,) = unity.jobs
        self.assertEqual(job["asset"], "Assets/Models/robot.obj")
        self.assertEqual(job["args"]["ASSETS_SUBDIR"], "Models")

    def test_a_folder_without_assets_or_an_unknown_script_is_refused(self):
        from extapps.unity_scripts.unity_deliverer import UnityDeliverer

        no_project = ptk.FileDeliveryBridge(target_folder=self.tmp, deliverer=UnityDeliverer())
        self.assertIsNone(no_project.send(self.model, template="SendToUnity"))
        self.assertIsNone(self._bridge().send(self.model, template="NoSuchScript"))
        self.assertFalse(os.path.exists(os.path.join(self.project, "Assets", "Imported")))

    def test_a_dry_run_asks_before_the_copy_and_the_run(self):
        ctx = ptk.OpContext(dry_run=True)
        with _Unity(self.project) as unity:
            result = self._bridge().send(self.model, template="SendToUnity", ctx=ctx)
        self.assertFalse(os.path.exists(result["file"]))
        self.assertIsNone(result["job"])
        self.assertEqual(unity.jobs, [])
        self.assertEqual([c.kind for c in ctx.changes], ["write", "change"])

    def test_an_fbx_lands_carrying_the_files_its_records_name(self):
        """The real embed (``ptk.FbxMedia.embed_dependencies``): the FBX alone
        is the hand-off, nothing copied beside it, the source only read."""
        maps = os.path.join(self.tmp, "maps")
        os.makedirs(maps)
        files = {"Crate_Lightmap.exr": b"lightmap" * 8, "Room_Probe.exr": b"probe" * 8}
        for name, data in files.items():
            with open(os.path.join(maps, name), "wb") as fh:
                fh.write(data)
        records = {
            "lightmaps": {
                "version": 2,
                "unit_scale": 0.01,
                "objects": [{"name": "Crate", "map": "Crate_Lightmap.exr", "uvIndex": 1}],
                "probe": {"map": "Room_Probe.exr", "position": [0, 0, 0], "box": None},
            }
        }
        fbx = _carrier_fbx(os.path.join(self.tmp, "crate.fbx"), records)
        with open(fbx, "rb") as fh:
            source = fh.read()
        bridge = self._bridge()
        bridge.lightmap_search_dirs = lambda: [maps]
        result = bridge.send(fbx, template="SendToUnity")
        self.assertEqual(
            {row["name"]: row["bytes"] for row in ptk.FbxMedia.embedded(result["file"])},
            {name: len(data) for name, data in files.items()},
        )
        self.assertEqual(os.listdir(os.path.dirname(result["file"])), ["crate.fbx"])
        with open(fbx, "rb") as fh:
            self.assertEqual(fh.read(), source)


# ---------------------------------------------------------------------- the panel
class _PanelCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps.unity_scripts.launcher import UnityScriptsUI

        self.tmp = tempfile.mkdtemp(prefix="unity_scripts_panel_")
        self.project = _project(self.tmp)
        self.ui = UnityScriptsUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)

    def tearDown(self) -> None:
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        store.clear()
        store.sync()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _select(self, script):
        combo = self.ui.cmb000
        for i in range(combo.count()):
            if combo.itemData(i)[0] == script:
                combo.setCurrentIndex(i)
                return
        self.fail(f"{script} is not listed")

    def _sources(self):
        combo = self.slots._param_widgets["SOURCE"]
        return [combo.itemText(i) for i in range(combo.count())]

    def _log(self):
        return self.ui.txt000.toPlainText()


class TestUnityScriptsPanel(_PanelCase):
    """The panel standalone: the scripts, the rows each names, the run."""

    def test_it_opens_on_send_to_unity_with_its_rows(self):
        self.assertEqual(self.slots._selected_template(), "SendToUnity")
        labels = [self.ui.cmb000.itemText(i) for i in range(self.ui.cmb000.count())]
        self.assertEqual(labels, ["Make Prefab", "Reimport Folder", "Send to Unity"])
        keys = self.slots._relevant_param_keys()
        self.assertTrue({"ASSETS_SUBDIR", "ASSET_NAME", "PLACE_IN_SCENE", "FRAME_SELECTION"} <= keys, keys)
        self.assertNotIn("PREFAB_FOLDER", keys)
        self.assertNotIn("SOURCE", keys, "File on Disk alone is no choice")
        self.assertFalse(self.slots._model_row.isHidden())

    def test_a_project_only_script_shows_no_source(self):
        self._select("ReimportFolder")
        self.assertIsNone(self.slots._active_source())
        self.assertEqual(self.slots._relevant_param_keys(), {"ASSETS_SUBDIR"})
        self.assertTrue(self.slots._model_row.isHidden())

    def test_the_scripts_menu_copies_one_to_edit(self):
        self.assertIsNotNone(self.slots.user_scripts_dir)
        self.assertTrue(hasattr(self.ui.cmb000.menu, "btn_copy_to_my_scripts"))
        self.assertEqual(self.ui.cmb000.menu.btn_open_templates.text(), "Open My Scripts Folder")

    def test_a_run_without_a_project_asks_for_one(self):
        self.slots._output_dir_edit.setText("")
        self.ui.b000.click()
        self.assertIn("Set the Unity Project folder", self._log())

    def test_a_missing_connection_is_offered_and_installed(self):
        from extapps.unity_scripts.unity_connection import UnityConnection

        self.slots._output_dir_edit.setText(self.project)
        self.slots.set_model_path(os.path.join(self.tmp, "none.fbx"))
        with mock.patch.object(self.ui.sb, "confirm", return_value=True) as confirm:
            self.ui.b000.click()
        confirm.assert_called_once()
        self.assertEqual(UnityConnection(self.project).state(), "installed")

    def test_a_run_waits_for_unity_and_reports_what_it_said(self):
        from extapps.unity_scripts.unity_connection import UnityConnection

        UnityConnection(self.project).install()
        model = os.path.join(self.tmp, "crate.obj")
        Path(model).write_text("v 0 0 0\n", encoding="utf-8")
        self.slots._output_dir_edit.setText(self.project)
        self.slots.set_model_path(model)

        def answer(job):
            return {
                "script": job["script"],
                "report": ["Placed crate in Main."],
                "created": [job["asset"]],
                "console": [{"type": "Warning", "message": "a warning"}],
                "seconds": 0.5,
            }

        with _Unity(self.project, answer):
            self.ui.b000.click()
            for _ in range(500):
                self.app.processEvents()
                if self.slots._running is None:
                    break
                threading.Event().wait(0.02)
        log = self._log()
        self.assertIn("Placed crate in Main.", log)
        self.assertIn("Assets/Imported/crate.obj", log)
        self.assertIn("[Unity] a warning", log)
        self.assertIn("Send to Unity ran", log)


class TestUnityScriptsHostsTheScene(_PanelCase):
    """A host injects its engine (``launch(show=False)``, then ``engine =``):
    Current Scene joins the Source row for a script that takes it, the
    engine's export rows appear for it, and a run sends through the engine
    with this panel's delivery."""

    def setUp(self) -> None:
        super().setUp()
        self.engine = _host_engine()

    def test_an_injected_engine_offers_the_current_scene_first(self):
        self.slots.engine = self.engine
        self.assertEqual(self._sources(), ["Current Scene", "File on Disk"])
        self.assertEqual(self.slots._active_source(), "scene")
        keys = self.slots._relevant_param_keys()
        self.assertTrue({"SOURCE", "SCOPE"} <= keys, keys)
        self.assertTrue(self.slots._model_row.isHidden(), "nothing is picked")

    def test_file_on_disk_hides_the_hosts_rows(self):
        self.slots.engine = self.engine
        self.slots._write_param("SOURCE", "file")
        keys = self.slots._relevant_param_keys()
        self.assertNotIn("SCOPE", keys)
        self.assertIn("SOURCE", keys)
        self.assertFalse(self.slots._model_row.isHidden())

    def test_a_project_only_script_takes_no_scene(self):
        self.slots.engine = self.engine
        self._select("ReimportFolder")
        self.assertIsNone(self.slots._active_source())
        self.assertNotIn("SCOPE", self.slots._relevant_param_keys())

    def test_a_scene_run_goes_through_the_engine_with_the_panels_delivery(self):
        from extapps.unity_scripts.unity_connection import UnityConnection

        UnityConnection(self.project).install()
        self.slots.engine = self.engine
        self.slots._output_dir_edit.setText(self.project)
        self.slots._write_param("SCOPE", "visible")
        self.slots._write_param("ASSETS_SUBDIR", "Models")
        self.ui.b000.click()
        (sent,) = self.engine.sent
        self.assertEqual(self.engine.scoped, ["visible"])
        self.assertEqual(sent["objects"], ["|pCube1"])
        self.assertEqual(sent["template"], "SendToUnity")
        self.assertEqual(sent["project"], self.project)
        self.assertIs(sent["deliverer"], self.slots.bridge.deliverer)
        self.assertEqual(sent["params"]["ASSETS_SUBDIR"], "Models")
        self.assertEqual(len(self.engine.built), 1)

    def test_a_failed_check_is_asked_as_the_scene_exporter_asks(self):
        """The engine is built with the panel's decider: a check that fails
        while the scene exports asks the Scene Exporter's own question -- its
        words and its buttons, Cancel the default -- read from the send's
        exporter; with none under way, it stops."""
        self.slots.engine = self.engine
        engine = self.slots._host()
        self.assertEqual(engine.decide_check_failure, self.slots.decide_check_failure)
        self.assertEqual(self.slots.decide_check_failure("check_framerate", [], []), "abort")

        class _Exporter:
            CHECK_FAILURE_CHOICES = ptk.SceneExporterBase.CHECK_FAILURE_CHOICES

            @staticmethod
            def check_failure_html(check, messages, remaining):
                return f"asked: {check} {messages} {remaining}"

        engine.exporter = _Exporter()
        for button, answer in (("Override", "override"), ("Override All", "override_all"), ("Cancel", "abort"), (None, "abort")):
            with self.subTest(button=button), mock.patch.object(self.ui.sb, "message_box", return_value=button) as box:
                self.assertEqual(self.slots.decide_check_failure("check_framerate", ["24 fps"], ["check_paths"]), answer)
                self.assertEqual(box.call_args.args[0], "asked: check_framerate ['24 fps'] ['check_paths']")
                self.assertEqual(box.call_args.args[1:], tuple(_Exporter.CHECK_FAILURE_CHOICES))
                self.assertEqual(box.call_args.kwargs["default"], "Cancel")

    def test_an_empty_scope_sends_nothing_and_says_why(self):
        from extapps.unity_scripts.unity_connection import UnityConnection

        UnityConnection(self.project).install()
        engine = _host_engine(objects=())
        self.slots.engine = engine
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertEqual(engine.sent, [])
        self.assertIn("Nothing selected", self._log())


if __name__ == "__main__":
    unittest.main()
