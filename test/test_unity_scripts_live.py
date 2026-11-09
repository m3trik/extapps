# !/usr/bin/python
# coding=utf-8
"""Live pass of Unity Scripts against a real Unity editor, opt-in.

Set ``EXTAPPS_UNITY_LIVE=1`` to run it (``EXTAPPS_UNITY_EDITOR`` names the
``Unity.exe``; default: the newest under the Hub's editors folder). It makes a
project of its own in a temp folder (``ptk.TempArtifacts``), installs the
connection as the panel installs it, and launches an editor of its own in batch
mode with ``-m3trikScriptsServe``: the C# worker the Python tests stand in for
(``test_unity_scripts_panel.py``). Only that editor is ever reached or ended
(its PID); an editor a person opened is never touched. Unity's license wall
(return code 198) skips it.
"""

from __future__ import annotations

import glob
import os
import subprocess
import time
import unittest
from pathlib import Path

import pythontk as ptk

PKG = Path(__file__).resolve().parents[1] / "extapps" / "unity_scripts"
FBX = Path(__file__).resolve().parents[2] / "pythontk" / "test" / "test_assets" / "fbx" / "maya_tangents.fbx"
LICENSE_WALL = 198


def _editor():
    named = os.environ.get("EXTAPPS_UNITY_EDITOR")
    if named:
        return named if os.path.isfile(named) else None
    found = sorted(glob.glob(r"C:\Program Files\Unity\Hub\Editor\*\Editor\Unity.exe"))
    return found[-1] if found else None


@unittest.skipUnless(os.environ.get("EXTAPPS_UNITY_LIVE"), "live Unity pass: set EXTAPPS_UNITY_LIVE=1")
class TestUnityScriptsLive(unittest.TestCase):
    """In order: a send, a new script across a domain reload, a script that does
    not compile, a second send, a script left compiling when Unity is killed,
    and the stop request ending the editor."""

    @classmethod
    def setUpClass(cls):
        from extapps.unity_scripts.unity_connection import UnityConnection

        cls.unity = _editor()
        if not cls.unity:
            raise unittest.SkipTest("no Unity editor installed")
        cls.temp = ptk.TempArtifacts("unity_scripts_live", policy="scoped")
        cls.root = Path(cls.temp.dir_path())
        cls.project = cls.root / "Proj"
        rc = subprocess.run(
            [cls.unity, "-batchmode", "-quit", "-createProject", str(cls.project), "-logFile", str(cls.root / "create.log")],
            timeout=900,
        ).returncode
        if rc == LICENSE_WALL:
            cls.temp.cleanup()
            raise unittest.SkipTest("Unity's license wall (rc 198): sign in to the Hub")
        assert rc == 0, f"project creation failed (rc {rc}): {cls.root / 'create.log'}"
        cls.connection = UnityConnection(str(cls.project))
        cls.connection.install()
        imported = cls.project / "Assets" / "Imported"
        imported.mkdir(parents=True, exist_ok=True)
        (imported / FBX.name).write_bytes(FBX.read_bytes())
        cls.editor = None
        cls._launch()

    @classmethod
    def _launch(cls):
        """An editor of this test's own, serving its project."""
        log = cls.log = cls.root / f"serve_{int(time.time())}.log"
        cls.editor = subprocess.Popen(
            [cls.unity, "-batchmode", "-projectPath", str(cls.project), "-m3trikScriptsServe", "-logFile", str(log)]
        )
        end = time.time() + 900
        # This editor's own heartbeat: a killed one's beat stays fresh a minute.
        while not (cls.connection.serving() and (cls.connection.worker() or {}).get("pid") == cls.editor.pid):
            if cls.editor.poll() is not None:
                raise AssertionError(f"the editor exited (rc {cls.editor.returncode}): {log}")
            if time.time() > end:
                raise AssertionError(f"the editor never served: {log}")
            time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        editor = getattr(cls, "editor", None)
        if editor is not None and editor.poll() is None:
            editor.kill()  # this test's own editor, by its PID
            editor.wait(60)
        if getattr(cls, "temp", None) is not None:
            cls.temp.cleanup()

    def _tail(self, lines=40):
        """The serving editor's log, last lines: what a failure here says."""
        try:
            return "\n".join(self.log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
        except OSError:
            return "(no log)"

    def _run(self, script, args=None, asset=None, timeout=420):
        job = self.connection.run(str(script), args or {}, asset)
        return self.connection.wait(job, timeout=timeout)

    def _script(self, name, body):
        path = self.root / f"{name}.cs"
        path.write_text(
            "using M3trik.UnityScripts;\nusing UnityEngine;\n\n"
            f"public static class {name}\n{{\n    [UnityScript]\n    public static void Run(ScriptArgs args)\n"
            f"    {{\n        {body}\n    }}\n}}\n",
            encoding="utf-8",
        )
        return path

    def test_1_send_to_unity_imports_and_places_the_model(self):
        record = self._run(
            PKG / "templates" / "SendToUnity.cs",
            {"PLACE_IN_SCENE": True, "FRAME_SELECTION": True},
            f"Assets/Imported/{FBX.name}",
        )
        self.assertEqual(record["state"], "done", record)
        self.assertEqual(record["result"]["created"], [f"Assets/Imported/{FBX.name}"])
        self.assertTrue(record["result"]["report"][0].startswith("Placed "), record)

    def test_2_a_new_script_compiles_across_the_reload_and_answers(self):
        script = self._script("LiveHello", 'args.Report("hello " + args.GetString("WHO", "nobody")); Debug.Log("LiveHello ran");')
        record = self._run(script, {"WHO": "live"})
        self.assertEqual(record["state"], "done", record)
        self.assertEqual(record["result"]["report"], ["hello live"])
        self.assertIn({"type": "Log", "message": "LiveHello ran"}, record["result"]["console"])

    def test_3_a_script_that_does_not_compile_is_reported_and_kept_out(self):
        record = self._run(self._script("LiveBroken", "this does not compile;"))
        self.assertEqual(record["state"], "failed", record)
        self.assertIn("did not compile", record["error"])
        self.assertFalse((self.project / "Assets" / "M3trikScripts" / "LiveBroken.cs").exists())

    def test_4_a_second_send_updates_the_instance_in_place(self):
        record = self._run(
            PKG / "templates" / "SendToUnity.cs",
            {"PLACE_IN_SCENE": True, "FRAME_SELECTION": False},
            f"Assets/Imported/{FBX.name}",
        )
        self.assertEqual(record["state"], "done", record)
        self.assertIn("updated in place", record["result"]["report"][0])

    def _kill_when(self, ready, seconds=120):
        """End this test's editor once *ready()* holds (or after *seconds*)."""
        end = time.time() + seconds
        while not ready() and time.time() < end:
            time.sleep(0.01)
        self.editor.kill()
        self.editor.wait(60)

    def test_5a_a_script_that_does_not_compile_never_enters_the_project(self):
        """Checked on the side before it is written: killed while it is checked,
        the project holds nothing of it, and the next editor opens it as before
        (a batch editor quits on a project whose scripts do not compile)."""
        written = self.project / "Assets" / "M3trikScripts" / "LiveLeft.cs"
        job = self.connection.run(str(self._script("LiveLeft", "this does not compile either;")))
        self._kill_when(lambda: self.connection.queue.status(job) == "running")
        self.assertFalse(written.exists())
        type(self)._launch()
        self.assertEqual(self.connection.wait(job, timeout=60)["state"], "failed", "its editor closed")
        again = self._run(self._script("LiveAfter", 'args.Report("still compiles");'))
        self.assertEqual(again["result"]["report"], ["still compiles"], self._tail())

    def test_5b_a_script_left_half_installed_is_put_back_when_unity_next_opens(self):
        """Killed after the checked script is written, before the project
        compiled it: the next editor puts the project back as it was."""
        pending = self.project / "Library" / "M3trikUnityScripts" / "pending"
        written = self.project / "Assets" / "M3trikScripts" / "LiveHalf.cs"
        job = self.connection.run(str(self._script("LiveHalf", 'args.Report("half");')))
        self._kill_when(pending.exists)
        if not written.exists():
            self.skipTest("the editor was killed before it wrote the script")
        type(self)._launch()
        end = time.time() + 300
        while (written.exists() or pending.exists()) and time.time() < end:
            time.sleep(1)
        self.assertFalse(written.exists(), f"the half-installed script was not put back:\n{self._tail()}")
        self.assertFalse(pending.exists())
        self.assertEqual(self.connection.wait(job, timeout=60)["state"], "failed", "its editor closed")

    def test_6_the_stop_request_ends_the_owned_editor(self):
        self.connection.queue.stop()
        self.assertEqual(self.editor.wait(120), 0)


if __name__ == "__main__":
    unittest.main()
