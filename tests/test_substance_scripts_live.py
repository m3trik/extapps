# !/usr/bin/python
# coding=utf-8
"""Live pass of Substance Scripts against a real Painter, opt-in.

Set ``EXTAPPS_PAINTER_LIVE=1`` to run it (Windows). It launches a Painter of its
own on a private desktop (``AppLauncher``'s hidden launch: a real GPU surface no
one sees; offscreen, Painter's Vulkan logs surface errors), with the instance
records, the plugin's launch root and the refresh's target in a
``ptk.TempArtifacts`` folder (``PYTHONTK_CACHE_ROOT``,
``SUBSTANCE_PAINTER_PLUGINS_PATH``), so it finds only the Painter it launched
(its PID), never sees, let alone reaches, one a person opened, and never
rewrites a person's installed plugin (its Painter serves the launch root's copy). Every built-in script
runs there in order; the test ends that Painter, and only that one.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

import pythontk as ptk


def _boxes_obj() -> str:
    """A slab with a small box resting on it, every face its own UV cell, as
    OBJ text: the box shades the slab around it, so a baked AO map is not
    plain white. (OBJ: Painter's importer reads no mesh from the FBX 2020 test
    asset, and its project then never finishes loading.)"""
    faces = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))
    points, uvs, polys = [], [], []
    for b, (centre, half) in enumerate((((0.0, 0.0, 0.0), (2.0, 0.5, 2.0)), ((0.0, 1.0, 0.0), (0.5, 0.5, 0.5)))):
        points += [
            f"v {centre[0] + x * half[0]} {centre[1] + y * half[1]} {centre[2] + z * half[2]}"
            for x in (-1, 1)
            for y in (-1, 1)
            for z in (-1, 1)
        ]
        for i, face in enumerate(faces):
            cell = b * 6 + i
            cu, cv = (cell % 4) / 4.0, (cell // 4) / 3.0
            uvs += [f"vt {cu + 0.01 + u * 0.23:.4f} {cv + 0.01 + v * 0.31:.4f}" for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))]
            polys.append("f " + " ".join(f"{b * 8 + c + 1}/{cell * 4 + k + 1}" for k, c in enumerate(face)))
    return "\n".join(points + uvs + polys) + "\n"


def _greys(path):
    """``(darkest, lightest, width)`` of an image, its pixels sampled on a grid."""
    from qtpy import QtGui

    image = QtGui.QImage(str(path))
    if image.isNull():
        raise AssertionError(f"not an image Qt reads: {path}")
    step = max(1, image.width() // 64)
    values = [
        QtGui.qGray(image.pixel(x, y)) for y in range(0, image.height(), step) for x in range(0, image.width(), step)
    ]
    return min(values), max(values), image.width()


@unittest.skipUnless(os.environ.get("EXTAPPS_PAINTER_LIVE"), "live Painter pass: set EXTAPPS_PAINTER_LIVE=1")
class TestSubstanceScriptsLive(unittest.TestCase):
    """In order: a new project from a mesh, a script of one's own with its own
    row, the lighting bake, the mesh-map bake, the texture export (the baked
    lighting in its Base Color), an export naming no preset, a failing script,
    a new project that would replace one on disk, and a run meant for another
    project refused."""

    @classmethod
    def setUpClass(cls):
        from extapps.substance_scripts._substance_scripts import SubstanceScripts

        if not SubstanceScripts.APP.resolve():
            raise unittest.SkipTest("no Substance Painter installed")
        cls.temp = ptk.TempArtifacts("spl", policy="scoped")  # short: Painter's paths sit under it
        cls.root = Path(cls.temp.dir_path())
        # The records, the launch root and the test's own scripts all stay in
        # the temp folder: never the person's cache or scripts folder.
        from extapps.substance_scripts.substance_rpc import Installer

        # A person's own install, which a send's refresh would rewrite: its
        # files' times now, to show the run never touched them.
        mine = Installer.user_plugin_dir()
        cls.persons_install = {p: p.stat().st_mtime_ns for p in (mine / "substance_rpc").rglob("*.py")} if mine else {}
        cls._env = {
            k: os.environ.get(k)
            for k in ("PYTHONTK_CACHE_ROOT", ptk.UserConfig.CONFIG_ROOT_ENV_VAR, "SUBSTANCE_PAINTER_PLUGINS_PATH")
        }
        os.environ["PYTHONTK_CACHE_ROOT"] = str(cls.root / "cache")
        os.environ[ptk.UserConfig.CONFIG_ROOT_ENV_VAR] = str(cls.root / "config")
        # The refresh's target: a folder of the test's, never the person's plugins.
        os.environ["SUBSTANCE_PAINTER_PLUGINS_PATH"] = str(cls.root / "painter")
        cls.engine = SubstanceScripts()
        cls.mesh = cls.root / "boxes.obj"
        cls.mesh.write_text(_boxes_obj(), encoding="utf-8")
        cls.project = cls.root / "live.spp"
        cls.result = None

    @classmethod
    def tearDownClass(cls):
        for conn in getattr(cls, "engine", None).instances if getattr(cls, "engine", None) else ():
            conn.close(terminate=True, timeout=30)  # this test's own Painter, by its process
        for key, value in cls._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls.temp.cleanup()

    def _run(self, template, timeout=1800, **kwargs):
        kwargs.setdefault("target", "auto")
        # Hidden, not offscreen: a real GPU surface (offscreen, Painter's Vulkan
        # logs surface errors).
        result = self.engine.send(template=template, hidden=True, **kwargs)
        self.assertIsNotNone(result, f"{template} stopped before Painter")
        self.assertTrue(result.get("job"), f"{template} was not queued: {result}")
        return result, self.engine.wait(result, timeout=timeout)

    def test_1_new_project_from_the_mesh_in_a_launched_painter(self):
        """As a panel sends: the launch is waited on off this thread, and the
        script is queued after (``background`` / ``on_queued``)."""
        import threading

        waits, queued = [], []

        def background(work, then):
            thread = threading.Thread(target=lambda: waits.append(work()))
            thread.start()
            waits.append((thread, then))

        pending = self.engine.send(
            template="new_project",
            mesh=str(self.mesh),
            target="new",
            hidden=True,
            params={"PAINTER_RESOLUTION": 1024, "PAINTER_PROJECT": str(self.project), "PAINTER_SAVE": True},
            background=background,
            on_queued=queued.append,
        )
        self.assertTrue(pending and pending.get("pending"), pending)
        (thread, then), *_ = waits
        thread.join(timeout=300)
        then(waits[-1])
        (result,) = queued
        self.assertTrue(result.get("job"), f"new_project was not queued: {result}")
        status = self.engine.wait(result, timeout=1800)
        self.assertEqual(status["state"], "done", status)
        conn = result["connection"]
        self.assertTrue(conn.launched)
        self.assertEqual(conn.record["pid"], conn.process.pid, "found by the PID it launched")
        held = conn.project()
        self.assertTrue(held and held["uuid"], held)
        self.assertTrue(self.project.is_file(), "saved as Project")
        record = next(r for r in self.engine.painters() if r["id"] == conn.record["id"])
        self.assertTrue(PainterPath.same(record["state"]["project"]["file_path"], self.project), record)
        # What Update Mesh finds its Painter by: Painter cannot say the mesh or
        # the UUID at its own save event (the record once kept them empty).
        self.assertTrue(PainterPath.same(record["state"]["project"]["mesh_path"], self.mesh), record)
        self.assertEqual(record["state"]["project"]["uuid"], held["uuid"], record)
        picked = self.engine.pick_painter("mesh", mesh=str(self.mesh), launch=False)
        self.assertIs(picked, conn, "Update Mesh's Painter, straight after New Project")

    def test_2_a_persons_script_runs_with_its_own_row(self):
        mine = ptk.ScriptTemplate.user_dir("substance")
        mine.mkdir(parents=True, exist_ok=True)
        script = mine / "live_probe.py"
        # It also gives every texture set a plain Base Color to light (a
        # fill layer paints nothing until a channel of it is switched on).
        script.write_text(
            '"""Live probe."""\nWORKS_ON = "project"\n'
            '# Row: __GREETING__ str "hello" "Greeting"\n'
            "import substance_painter.layerstack as layerstack\n"
            "import substance_painter.textureset as ts\n"
            "args.report(args['GREETING'] + ' ' + str(len(ts.all_texture_sets())))\n"
            "for texture_set in ts.all_texture_sets():\n"
            "    stack = ts.Stack.from_name(str(texture_set.name))\n"
            "    base = layerstack.insert_fill(layerstack.InsertPosition.from_textureset_stack(stack))\n"
            "    base.set_name('Base')\n"
            "    base.active_channels = {ts.ChannelType.BaseColor}\n",
            encoding="utf-8",
        )
        self.addCleanup(script.unlink)
        _result, status = self._run("live_probe", params={"GREETING": "sets:"})
        self.assertEqual(status["state"], "done", status)
        self.assertRegex(status["report"][0], r"^sets: [1-9]")

    def test_3_bake_lighting_on_the_open_project(self):
        _result, status = self._run(
            "bake_lighting", params={"BAKE_RESOLUTION": "512", "AO_RAYS": 16, "INCLUDE_CURVATURE": True}
        )
        self.assertEqual(status["state"], "done", status)
        said = "\n".join(status["report"])
        self.assertIn("baked AO, Curvature", said)
        self.assertIn("lighting laid over Base Color", said)

    def test_4_bake_mesh_maps(self):
        _result, status = self._run(
            "bake_mesh_maps",
            params={"MAP_BAKE_RESOLUTION": "512", "BAKE_POSITION": False, "BAKE_THICKNESS": False, "BAKE_ID": False},
        )
        self.assertEqual(status["state"], "done", status)
        self.assertIn("baked Normal, WorldSpaceNormal, AO, Curvature", "\n".join(status["report"]))

    def test_5_export_textures_and_the_baked_lighting_is_in_its_base_color(self):
        """The export runs straight after the scripts that changed the stack,
        in a Painter no one looks at: it must write what the stack holds NOW.
        (Run inside the job's undo entry it wrote the maps of before any edit;
        and the lighting layer the bake added once painted nothing.)"""
        out = self.root / "maps"
        _result, status = self._run(
            "export_textures",
            params={"EXPORT_DIR": str(out), "EXPORT_SIZE": "512", "EXPORT_PADDING": "diffusion", "EXPORT_DILATION": 8},
        )
        self.assertEqual(status["state"], "done", status)
        (base,) = list(out.rglob("*BaseColor.png"))
        darkest, lightest, width = _greys(base)
        self.assertEqual(width, 512, "Size")
        self.assertGreater(lightest, 200, "the plain Base Color where nothing shades it")
        self.assertLess(darkest, 150, f"no occlusion in the exported Base Color ({darkest}..{lightest})")

    def test_55_an_export_preset_painter_does_not_have_fails_naming_the_ones_it_has(self):
        """Shelf presets among them: PBR Metallic Roughness is one, not a
        predefined preset."""
        out = self.root / "refused"
        _result, status = self._run("export_textures", params={"EXPORT_DIR": str(out), "EXPORT_PRESET": "No Such Preset"})
        self.assertEqual(status["state"], "failed", status)
        self.assertIn("PBR Metallic Roughness", status["error"])
        self.assertIn("glTF PBR Metal Roughness", status["error"])
        self.assertFalse(out.exists(), "nothing is written, not even the folder")

    def test_56_a_float_export_writes_exr(self):
        out = self.root / "float"
        _result, status = self._run(
            "export_textures", params={"EXPORT_DIR": str(out), "EXPORT_FORMAT": "exr", "EXPORT_BIT_DEPTH": "32f", "EXPORT_SIZE": "512"}
        )
        self.assertEqual(status["state"], "done", status)
        self.assertTrue(any(out.rglob("*BaseColor.exr")), status)

    def test_6_a_failing_script_is_its_jobs_failure_and_painter_serves_on(self):
        mine = ptk.ScriptTemplate.user_dir("substance")
        mine.mkdir(parents=True, exist_ok=True)
        script = mine / "live_broken.py"
        script.write_text('"""Broken."""\nWORKS_ON = "project"\nraise ValueError("no such layer")\n', encoding="utf-8")
        self.addCleanup(script.unlink)
        _result, status = self._run("live_broken")
        self.assertEqual(status["state"], "failed")
        self.assertIn("no such layer", status["error"])
        _result, status = self._run("export_textures", params={"EXPORT_DIR": str(self.root / "again")})
        self.assertEqual(status["state"], "done", status)

    def test_65_new_project_never_replaces_a_project_on_disk(self):
        """Painter's ``save_as`` replaces a file without asking, and the
        Project row may still name the project the last script ran on."""
        from extapps.substance_scripts._substance_scripts import SubstanceScripts

        conn = self.engine.instances[-1]
        before = (self.project.stat().st_size, self.project.stat().st_mtime_ns)
        template = SubstanceScripts.template_path("new_project")
        job = conn.rpc.run_script(
            template.read_text(encoding="utf-8"),
            path=str(template),
            args={"MESH": str(self.mesh), "MESH_MAP_FILES": [], "PAINTER_SAVE": True, "PROJECT": str(self.project)},
        )
        status = conn.rpc.wait(job, timeout=120)
        self.assertEqual(status["state"], "failed", status)
        self.assertIn("already exists", status["error"])
        self.assertEqual((self.project.stat().st_size, self.project.stat().st_mtime_ns), before)

    def test_7_a_run_meant_for_another_project_is_refused(self):
        conn = self.engine.instances[-1]
        with self.assertRaises(RuntimeError) as ctx:
            conn.rpc.run_script("x = 1", path="p.py", expect={"uuid": "00000000-0000-0000-0000-000000000000"})
        self.assertIn("meant for", str(ctx.exception))

    def test_8_the_menu_in_painter_says_what_it_serves_and_pauses_it(self):
        """Last: nothing over RPC resumes a pause (that is the person's, in Painter)."""
        conn = self.engine.instances[-1]
        probe = (
            "import substance_painter.ui as ui\n"
            "import substance_rpc\n"
            "window = ui.get_main_window()  # held: its menu bar's wrapper dies with a temporary\n"
            "bar = window.menuBar()\n"
            "args.report(';'.join(a.text() for a in bar.actions()))\n"
            "args.report(substance_rpc.status_line())\n"
            "args.report(substance_rpc.__spec__.name)\n"
            "substance_rpc._MENU['pause'].setChecked(True)  # as a person ticks it\n"
        )
        status = conn.rpc.wait(conn.rpc.run_script(probe, path="menu_probe.py"), timeout=60)
        self.assertEqual(status["state"], "done", status)
        self.assertIn("M3trik Scripts", status["report"][0].split(";"))
        self.assertTrue(status["report"][1].startswith("Serving "), status["report"])
        self.assertEqual(status["report"][2], "substance_rpc_launched", "the launch root's copy serves, never a person's install")
        with self.assertRaises(RuntimeError) as ctx:
            conn.rpc.run_script("x = 1", path="p.py")
        self.assertIn("paused in Painter", str(ctx.exception))
        record = next(r for r in self.engine.painters() if r["id"] == conn.record["id"])
        self.assertIs(record["state"]["paused"], True)

    def test_9_a_persons_install_was_never_rewritten(self):
        changed = [str(p) for p, t in self.persons_install.items() if not p.is_file() or p.stat().st_mtime_ns != t]
        self.assertEqual(changed, [])


class PainterPath:
    @staticmethod
    def same(a, b):
        norm = lambda p: os.path.normcase(os.path.normpath(os.path.abspath(str(p))))  # noqa: E731
        return bool(a) and norm(a) == norm(b)


if __name__ == "__main__":
    unittest.main()
