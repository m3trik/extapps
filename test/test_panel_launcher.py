#!/usr/bin/python
# coding=utf-8
"""The panels' one launcher (``extapps/_panel_launcher.py``) and its roster.

The panels are frameless uitk windows whose controls live on the uitk Header (no
native OS frame). They must behave like uitk's ``WindowPanel`` (the editor-window
reference): a clean ``Qt.Window | FramelessWindowHint`` so that, when a host's
external-app handler parents them under a DCC (e.g. Maya), they're *normal*
host-owned windows -- NOT always-on-top. A plain ``QMainWindow`` defaults to the
native title-bar decoration hints, and left set on a frameless owned window they
make it float on top of its host.

The family is read from its roster -- the ``uitk.external_apps.in_process``
entry points in ``pyproject.toml``, how a host and the hub find an app -- never
from a hand-kept list (CODE_STANDARD section 6). The runtime cases build three
panels and compare real ``windowFlags()`` with the reference -- the only check
that proves the chrome; the rest cover the whole roster cheaply.
"""

import importlib
import os
import re
import runpy
import sys
import unittest
import warnings
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy import QtCore  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

from uitk.testing import TestSandbox  # noqa: E402

# A direct `python test/test_panel_launcher.py` loads no conftest: the panels
# read and write QSettings, so the sandbox is activated before the first one.
TestSandbox.activate()

from extapps import _panel_launcher  # noqa: E402
from extapps._panel_launcher import PanelLauncher  # noqa: E402

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
GROUP = "uitk.external_apps.in_process"

# Native title-bar decoration hints that must be cleared on a frameless window --
# the uitk Header supplies these controls instead.
_DECORATION_HINTS = (
    QtCore.Qt.WindowTitleHint
    | QtCore.Qt.WindowSystemMenuHint
    | QtCore.Qt.WindowMinimizeButtonHint
    | QtCore.Qt.WindowMaximizeButtonHint
    | QtCore.Qt.WindowCloseButtonHint
)


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def table(name: str) -> dict:
    """``key = "value"`` pairs of one ``pyproject.toml`` table, by header text.

    The source file, never installed metadata: an editable install's metadata
    is only as new as its last ``pip install -e``.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    block = re.search(
        r"^\[%s\]\s*$(.*?)(?=^\[|\Z)" % re.escape(name), text, re.M | re.S
    )
    if not block:
        raise AssertionError(f"table [{name}] not found in pyproject.toml")
    return dict(re.findall(r'^\s*(\w+)\s*=\s*"([^"]+)"', block.group(1), re.M))


def entry_points() -> dict:
    """``{app: (module, class, extras)}`` from the entry-point table."""
    out = {}
    for name, target in table(f'project.entry-points."{GROUP}"').items():
        module, _, rest = target.partition(":")
        cls, _, extras = rest.partition("[")
        out[name] = (module.strip(), cls.strip(), extras.rstrip("] ").strip())
    return out


def launchers() -> dict:
    """``{app: its <Tool>UI class}``, resolved from each entry point."""
    return {
        name: getattr(importlib.import_module(module), cls)
        for name, (module, cls, _extras) in entry_points().items()
    }


class TestRoster(unittest.TestCase):
    """Each entry point names a ``PanelLauncher`` that derives its app from where
    it lives."""

    def test_every_launcher_module_is_named_by_an_entry_point(self):
        """A ``launcher.py`` no entry point names is a panel no host or hub can
        open; an entry point without one opens nothing."""
        root = PYPROJECT.parent
        modules = {
            ".".join(path.relative_to(root).with_suffix("").parts)
            for path in (root / "extapps").rglob("launcher.py")
        }
        named = {module for module, _cls, _extras in entry_points().values()}
        self.assertEqual(modules, {f"{m}.launcher" for m in named})

    def test_every_entry_point_names_a_launcher(self):
        for name, cls in sorted(launchers().items()):
            with self.subTest(app=name):
                self.assertTrue(issubclass(cls, PanelLauncher), cls)
                self.assertIsNot(cls, PanelLauncher)

    def test_each_launcher_derives_its_panel_and_slots(self):
        """``<Tool>UI`` -> the ``<app>.ui`` beside its ``launcher.py``, named for
        its entry point (the stem users' settings live under), and the Slots
        class its package's ``DEFAULT_INCLUDE["slots"]`` names."""
        for name, cls in sorted(launchers().items()):
            with self.subTest(app=name):
                package, app, folder = cls._tool()
                self.assertEqual(app, name)
                self.assertEqual(cls.__module__, f"{package}.launcher")
                self.assertTrue(os.path.isfile(os.path.join(folder, f"{app}.ui")))
                slots = cls._slots_class(package)
                self.assertEqual(slots.__module__, f"{package}.slots")
                self.assertTrue(slots.__name__.endswith("Slots"), slots.__name__)

    def test_maya_hides_the_panels_it_serves_with_its_own_bridges(self):
        """Substance / Marmoset stay gated out of Maya: tentacle serves its own
        Substance and Marmoset bridges there."""
        extras = {name: e for name, (_m, _c, e) in entry_points().items()}
        for gated in ("substance_scripts", "marmoset_scripts"):
            self.assertIn("hide_maya", extras[gated])


class TestOneRecipe(unittest.TestCase):
    """Every panel is built by the ONE launcher recipe, which never ORs onto the
    ``QMainWindow`` defaults (``set_flags(FramelessWindowHint, ...)`` did: the
    fix once landed in three hand-written launchers and eight kept the bug)."""

    def test_no_launcher_rebuilds_the_recipe(self):
        stray = [name for name, cls in launchers().items() if "__new__" in vars(cls)]
        self.assertEqual(stray, [], "panels not built by PanelLauncher")

    def test_no_panel_offers_fullscreen(self):
        """Every panel is a parameter form over a log: fullscreen has nothing to
        show, and the DCC panels never offer it either."""
        offering = [
            name
            for name, cls in launchers().items()
            if "fullscreen" in cls.HEADER_BUTTONS
        ]
        self.assertEqual(offering, [])

    def test_the_recipe_sets_the_clean_flag_set(self):
        source = Path(_panel_launcher.__file__).read_text(encoding="utf-8")
        self.assertIn("setWindowFlags(", source)
        self.assertNotIn("set_flags(FramelessWindowHint", source)


class TestWindowChrome(unittest.TestCase):
    """Built panels match the ``WindowPanel`` reference chrome."""

    PANELS = ("metashape_workflow", "realityscan_workflow", "gaussian_splat_workflow")

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

    def _build(self, name):
        ui = launchers()[name]()
        self.addCleanup(self.app.processEvents)
        self.addCleanup(ui.deleteLater)
        return ui

    def test_panels_match_windowpanel_reference(self) -> None:
        reference = self._reference_flags()
        for name in self.PANELS:
            with self.subTest(panel=name):
                flags = int(self._build(name).windowFlags())
                self.assertEqual(
                    flags,
                    reference,
                    f"{name} window flags {hex(flags)} != WindowPanel reference "
                    f"{hex(reference)} -- frameless chrome drifted.",
                )

    def test_panels_are_normal_frameless_windows(self) -> None:
        Qt = QtCore.Qt
        for name in self.PANELS:
            with self.subTest(panel=name):
                flags = self._build(name).windowFlags()
                self.assertEqual(int(flags & Qt.WindowType_Mask), int(Qt.Window))
                self.assertTrue(bool(flags & Qt.FramelessWindowHint))
                self.assertFalse(bool(flags & Qt.WindowStaysOnTopHint))
                self.assertEqual(int(flags & _DECORATION_HINTS), 0)

    def test_a_titled_panel_shows_extapps_release(self) -> None:
        import extapps

        ui = self._build("metashape_workflow")
        self.assertEqual(ui.windowTitle(), f"Metashape Workflow v{extapps.__version__}")

    def test_the_panels_keep_their_saved_names(self) -> None:
        """A user's settings live under the window's name -- the ``.ui`` stem --
        and its presets under the folder the panels were published with."""
        ui = self._build("metashape_workflow")
        self.assertEqual(ui.objectName(), "metashape_workflow")
        self.assertEqual(PanelLauncher.PRESETS_FOLDER[0], "extapps")


RENAMED_GROUP = "uitk.external_apps.renamed"


class TestRenamedApps(unittest.TestCase):
    """An app renamed (``_panel_launcher.RENAMED_FROM``) keeps its users'
    values and its former name: the store and presets carry once, and the
    former name is declared to uitk's handler as an entry point naming the same
    launcher (a restatement, held equal here)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def test_every_former_name_is_declared_where_the_handler_reads_it(self):
        apps = entry_points()
        declared = {}
        try:
            declared = table(f'project.entry-points."{RENAMED_GROUP}"')
        except AssertionError:
            pass  # no app renamed yet
        expected = {
            former: f"{apps[app][0]}:{apps[app][1]}"
            for app, formers in _panel_launcher.RENAMED_FROM.items()
            for former in formers
        }
        self.assertEqual(declared, expected)
        for app in _panel_launcher.RENAMED_FROM:
            self.assertIn(app, apps, f"{app} is renamed but is no app")

    def test_a_former_store_and_its_presets_carry_once(self):
        from uitk import PresetManager, Switchboard

        former, app = "old_preview", "webxr_preview"
        Switchboard().settings.branch(former).setValue("probe/textChanged", "kept")
        root = PresetManager.get_presets_root()
        old = root / "extapps" / former / "mine.json"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("{}", encoding="utf-8")
        with mock.patch.dict(_panel_launcher.RENAMED_FROM, {app: {former: {}}}):
            ui = launchers()[app]()
            self.addCleanup(ui.deleteLater)
            self.assertEqual(ui.sb.settings.branch(app).value("probe/textChanged"), "kept")
            carried = root / Path(ui.slots.PRESETS_ROOT) / "mine.json"
            self.assertTrue(carried.is_file())
            carried.unlink()  # the user deletes it: a later launch never brings it back
            again = launchers()[app]()
            self.addCleanup(again.deleteLater)
            self.assertFalse(carried.exists())

    def test_the_unity_workflows_store_opens_unity_scripts_on_its_own_script(self):
        """The Unity Workflow's script combo saved a row into a list the app no
        longer has (copy_to_assets, manage_scripts): it is not carried, so the
        app opens on Send to Unity, not on whatever sorts first; that
        template's presets are Send to Unity's, and manage_scripts' stay behind."""
        from uitk import PresetManager, Switchboard

        former = Switchboard().settings.branch("unity_workflow")
        former.setValue("cmb000/currentIndexChanged", 0)
        former.setValue("unity_workflow_output_dir/textChanged", "C:/Proj")
        root = PresetManager.get_presets_root()
        for template in ("copy_to_assets", "manage_scripts"):
            path = root / "extapps" / "unity_workflow" / template / "mine.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        ui = launchers()["unity_scripts"]()
        self.addCleanup(ui.deleteLater)
        store = ui.sb.settings.branch("unity_scripts")
        self.assertIsNone(store.value("cmb000/currentIndexChanged"))
        self.assertEqual(store.value("unity_workflow_output_dir/textChanged"), "C:/Proj")
        presets = root / Path(ui.slots.PRESETS_ROOT)
        self.assertTrue((presets / "SendToUnity" / "mine.json").is_file())
        self.assertFalse((presets / "copy_to_assets").exists())
        self.assertFalse((presets / "manage_scripts").exists())
        self.assertEqual(ui.slots._selected_template(), "SendToUnity")


class TestLauncherMainBlocks(unittest.TestCase):
    """A ``launcher.py`` run as a program builds its own panel.

    Its ``__main__`` block calls ``<Tool>UI()``, and run that way the class's
    ``__module__`` is ``"__main__"``: ``PanelLauncher`` must find the app's
    package from the module's spec (``python -m``) or, run as a script, from
    the package folders above the file. Deriving it from ``__module__`` made
    every launcher raise ``ValueError: Empty module name``.

    ``MainWindow.show`` is stubbed, so the block builds the panel and never
    enters the event loop.
    """

    #: ``(launcher module, loaded-ui name, Slots class)``: a flat app and one
    #: nested under an umbrella package.
    LAUNCHERS = (
        ("extapps.mesh_convert.launcher", "mesh_convert", "MeshConvertSlots"),
        ("extapps.texture_maps.packer.launcher", "packer", "PackerSlots"),
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def _run_main(self, run, target, **kwargs) -> list:
        """``run(target, run_name="__main__", **kwargs)``; what it showed."""
        from uitk.widgets.mainWindow import MainWindow

        shown = []

        def show(window, pos=None, app_exec=False):
            shown.append((window.objectName(), type(window.slots).__name__))
            window.deleteLater()

        with mock.patch.object(MainWindow, "show", new=show):
            with warnings.catch_warnings():
                # runpy warns that an earlier test already imported the module.
                warnings.simplefilter("ignore", RuntimeWarning)
                run(target, run_name="__main__", **kwargs)
        self.app.processEvents()
        return shown

    def test_python_dash_m_builds_the_panel(self):
        """``python -m extapps.<app>.launcher``."""
        for module, name, slots in self.LAUNCHERS:
            with self.subTest(module=module):
                shown = self._run_main(runpy.run_module, module, alter_sys=True)
                self.assertEqual(shown, [(name, slots)])

    def test_running_the_file_builds_the_panel(self):
        """``python <app dir>/launcher.py``."""
        root = PYPROJECT.parent
        for module, name, slots in self.LAUNCHERS:
            path = root.joinpath(*module.split(".")).with_suffix(".py")
            with self.subTest(path=str(path.relative_to(root))):
                shown = self._run_main(runpy.run_path, str(path))
                self.assertEqual(shown, [(name, slots)])


class TestDocsLinks(unittest.TestCase):
    """A panel over an engine documented here links that page (logged at open, a
    clickable anchor in the log pane). Each is a GitHub blob URL into this repo,
    so a doc rename fails here rather than 404-ing for users. RealityScan /
    Brush inherit the photogrammetry base's TUNING.md link; Metashape and
    Substance point at their own pages."""

    APPS = (
        "metashape_workflow",
        "realityscan_workflow",
        "gaussian_splat_workflow",
        "substance_scripts",
    )

    def test_each_link_names_a_file_in_this_repo(self):
        import extapps

        prefix = extapps.DOCS_BASE_URL
        repo = Path(extapps.__file__).resolve().parents[1]
        for name in self.APPS:
            with self.subTest(app=name):
                ui = launchers()[name]
                cls = ui._slots_class(ui._tool()[0])
                self.assertTrue(cls.DOCS_URL.startswith(prefix), cls.DOCS_URL)
                self.assertTrue(cls.DOCS_LABEL.strip())
                target = repo / cls.DOCS_URL[len(prefix) :]
                self.assertTrue(target.is_file(), f"{cls.DOCS_URL} -> missing {target}")


if __name__ == "__main__":
    unittest.main()
