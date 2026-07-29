#!/usr/bin/python
# coding=utf-8
"""Tests for CompositorSlots source resolution.

Covers the dir-*or*-image-files source field added so the user can point
the compositor at a directory of maps OR hand-pick individual image files.
The heavy UI wiring in ``__init__`` is bypassed (``__new__``) — these tests
exercise the pure source-resolution helpers and ``_resolve_source``.
"""
import os

# UI-wiring tests below construct the real panel; force the offscreen Qt
# platform so they run headless (and never flash a window on a dev display).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re
import sys
import tempfile
import shutil
import unittest
from unittest import mock
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

from qtpy.QtCore import QUrl
from qtpy.QtWidgets import QApplication, QPushButton, QTextBrowser

from pythontk import ImgUtils, MapCompositor

from extapps.texture_maps.compositor.slots import CompositorSlots


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestMapCompositorSourceResolution(unittest.TestCase):
    """Source field accepts a directory or an explicit image-file selection."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="compositor_test_")
        cls.maps_dir = os.path.join(cls.test_dir, "maps")
        os.makedirs(cls.maps_dir, exist_ok=True)
        # A small set of recognizably-named maps in one directory.
        cls.files = {}
        for name in ("mat_BaseColor.png", "mat_Roughness.png", "mat_Metallic.png"):
            path = os.path.join(cls.maps_dir, name)
            ImgUtils.save_image(ImgUtils.create_image("RGB", (8, 8), (128, 128, 128)), path)
            cls.files[name] = path

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    # -- helpers ----------------------------------------------------------

    def _slots_with_source(self, text):
        """Bare slots instance whose source field resolves to *text*.

        ``_resolve_source`` reads the field's data-aware ``value()`` (which a
        real ``uitk.LineEdit`` returns as its data payload, or its text when
        none is set), so the mock mirrors a plain field by returning *text*
        from both ``value()`` and ``text()``.
        """
        inst = CompositorSlots.__new__(CompositorSlots)
        inst.ui = Mock()
        inst.ui.txt000.value.return_value = text
        inst.ui.txt000.text.return_value = text
        return inst

    @property
    def joined(self):
        return os.pathsep.join(self.files.values())

    # -- _split_source ----------------------------------------------------

    def test_split_source_directory_is_empty(self):
        """A single existing directory is directory mode (no file parts)."""
        self.assertEqual(CompositorSlots._split_source(self.maps_dir), [])

    def test_split_source_single_file(self):
        path = self.files["mat_BaseColor.png"]
        self.assertEqual(CompositorSlots._split_source(path), [path])

    def test_split_source_multiple_files(self):
        self.assertEqual(
            CompositorSlots._split_source(self.joined), list(self.files.values())
        )

    def test_split_source_empty(self):
        self.assertEqual(CompositorSlots._split_source(""), [])

    # -- _field_dir -------------------------------------------------------

    def test_field_dir_directory(self):
        self.assertEqual(CompositorSlots._field_dir(self.maps_dir), self.maps_dir)

    def test_field_dir_single_file(self):
        path = self.files["mat_Roughness.png"]
        self.assertEqual(CompositorSlots._field_dir(path), self.maps_dir)

    def test_field_dir_joined_files(self):
        self.assertEqual(CompositorSlots._field_dir(self.joined), self.maps_dir)

    def test_field_dir_empty(self):
        self.assertEqual(CompositorSlots._field_dir(""), "")

    # -- _validate_source -------------------------------------------------

    def test_validate_source_directory(self):
        self.assertTrue(CompositorSlots._validate_source(self.maps_dir))

    def test_validate_source_single_file(self):
        self.assertTrue(
            CompositorSlots._validate_source(self.files["mat_Metallic.png"])
        )

    def test_validate_source_multiple_files(self):
        self.assertTrue(CompositorSlots._validate_source(self.joined))

    def test_validate_source_nonexistent(self):
        self.assertFalse(
            CompositorSlots._validate_source(os.path.join(self.maps_dir, "nope.png"))
        )

    def test_validate_source_mixed_valid_and_missing(self):
        text = os.pathsep.join(
            [self.files["mat_BaseColor.png"], os.path.join(self.maps_dir, "nope.png")]
        )
        self.assertFalse(CompositorSlots._validate_source(text))

    def test_validate_source_empty(self):
        self.assertFalse(CompositorSlots._validate_source(""))

    # -- _source_valid_tooltip --------------------------------------------

    def test_valid_tooltip_directory_is_path(self):
        """Directory mode shows the folder path verbatim."""
        self.assertEqual(
            CompositorSlots._source_valid_tooltip(self.maps_dir), self.maps_dir
        )

    def test_valid_tooltip_single_file(self):
        tip = CompositorSlots._source_valid_tooltip(self.files["mat_BaseColor.png"])
        self.assertIn("1 image file<", tip)  # singular, no trailing 's'
        self.assertIn("mat_BaseColor.png", tip)
        # Renders the basename, not the raw full path.
        self.assertNotIn(self.maps_dir, tip)

    def test_valid_tooltip_multiple_files(self):
        tip = CompositorSlots._source_valid_tooltip(self.joined)
        self.assertIn(f"{len(self.files)} image files", tip)
        for name in self.files:
            self.assertIn(name, tip)
        # The three mat_* files collapse into one texture set ("mat"), so the
        # header advertises a single set and the set name is shown.
        self.assertIn("1 texture set", tip)
        self.assertIn("<b>mat</b>", tip)

    # -- _source_display --------------------------------------------------

    def test_source_display_groups_into_set_names(self):
        """The field's compact display lists one name per texture set."""
        self.assertEqual(
            CompositorSlots._source_display(list(self.files.values())), "mat"
        )

    def test_source_display_multiple_sets(self):
        names = CompositorSlots._source_display(
            [
                os.path.join(self.maps_dir, "brick_BaseColor.png"),
                os.path.join(self.maps_dir, "brick_Normal.png"),
                os.path.join(self.maps_dir, "wood_BaseColor.png"),
            ]
        )
        self.assertEqual(sorted(names.split(", ")), ["brick", "wood"])

    # -- _resolve_source --------------------------------------------------

    def test_resolve_source_directory(self):
        """Directory mode loads every image in the directory."""
        inst = self._slots_with_source(self.maps_dir)
        images, source_dir = inst._resolve_source()
        self.assertEqual(source_dir, self.maps_dir)
        self.assertEqual(
            sorted(os.path.basename(p) for p in images), sorted(self.files)
        )

    def test_resolve_source_files(self):
        """File mode loads exactly the selected files; dir is their parent."""
        chosen = [self.files["mat_BaseColor.png"], self.files["mat_Roughness.png"]]
        inst = self._slots_with_source(os.pathsep.join(chosen))
        images, source_dir = inst._resolve_source()
        self.assertEqual(source_dir, self.maps_dir)
        self.assertEqual(sorted(images), sorted(chosen))
        # Values are loaded image objects (the shape the engine expects).
        for img in images.values():
            self.assertIsNotNone(img)

    def test_resolve_source_single_file(self):
        path = self.files["mat_Metallic.png"]
        inst = self._slots_with_source(path)
        images, source_dir = inst._resolve_source()
        self.assertEqual(source_dir, self.maps_dir)
        self.assertEqual(list(images), [path])

    def test_resolve_source_empty(self):
        inst = self._slots_with_source("")
        self.assertEqual(inst._resolve_source(), ({}, ""))


class TestCompositorOptionMenus(unittest.TestCase):
    """The source/destination fields expose their path actions as a single
    option-box dropdown menu (Add files / Choose folder, with Open this
    location last), and the log panel is a link-clickable QTextBrowser."""

    @classmethod
    def setUpClass(cls):
        from extapps.texture_maps.compositor import CompositorUI

        cls.app = _ensure_app()
        cls.ui = CompositorUI()
        cls.ui.show()  # offscreen — drives the deferred *_init / option-box wrap
        for _ in range(20):
            cls.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ui.deleteLater()
        cls.app.processEvents()

    @staticmethod
    def _menu_button_labels(line_edit):
        """Visible QPushButton labels in a field's option-box menu (or None)."""
        menu = line_edit.option_box.get_menu(create=False)
        if menu is None:
            return None
        return [
            w.text() for w in menu.get_items() if isinstance(w, QPushButton)
        ]

    def test_log_panel_is_clickable_text_browser(self):
        """The log pane must be a QTextBrowser so action:// links are clickable."""
        self.assertIsInstance(self.ui.txt003, QTextBrowser)
        self.assertTrue(hasattr(self.ui.txt003, "anchorClicked"))

    def test_source_field_menu_items(self):
        # Source can be files or a folder; reveal ("Open this location") last.
        self.assertEqual(
            self._menu_button_labels(self.ui.txt000),
            ["Add files…", "Choose folder…", "Open this location"],
        )

    def test_dest_field_menu_items(self):
        self.assertEqual(
            self._menu_button_labels(self.ui.txt001),
            ["Choose folder…", "Open this location"],
        )

    def test_fields_have_rich_color_tooltips(self):
        """Each path field installs a formatted (colored) fmt tooltip, not the
        plain .ui fallback."""
        for widget, marker in (
            (self.ui.txt000, "Source maps to combine"),
            (self.ui.txt001, "Destination directory"),
            (self.ui.txt002, "Map name prefix"),
        ):
            tip = widget.toolTip()
            self.assertIn(marker, tip)
            self.assertIn("color:", tip)  # fmt palette applied

    def test_source_choose_folder_sets_directory_mode(self):
        """Choosing a folder for the source stores a plain directory value
        (clearing any prior file-selection payload) so it resolves as a dir."""
        import os
        from unittest import mock as umock

        slots = self.ui.slots
        # Pre-seed a file-selection payload, then pick a folder over it.
        slots.ui.txt000.set_value("a.png;b.png", display="set")
        folder = tempfile.mkdtemp(prefix="compositor_srcdir_")
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        # Mock the dialog result and the recent-values record so the test
        # doesn't persist a temp path into the user's real QSettings history.
        with umock.patch(
            "qtpy.QtWidgets.QFileDialog.getExistingDirectory",
            return_value=folder,
        ), umock.patch.object(slots._recent_input_dirs, "record"):
            slots._browse_directory(
                slots.ui.txt000, "t", recent_attr="_recent_input_dirs"
            )
        # Payload cleared → value is the folder, and it's directory mode.
        self.assertEqual(slots.ui.txt000.value(), folder)
        self.assertEqual(slots.ui.txt000.data(), None)
        self.assertEqual(CompositorSlots._split_source(folder), [])  # dir mode


class TestCompositorOutputLink(unittest.TestCase):
    """Link routing + the clickable output-dir link logged on completion."""

    def _bare_slots(self):
        inst = CompositorSlots.__new__(CompositorSlots)
        inst.engine = MapCompositor()
        inst.ui = Mock()
        return inst

    def test_action_open_link_routes_to_open_dir(self):
        """An ``action://open?path=…`` anchor reveals that path via _open_dir."""
        inst = self._bare_slots()
        opened = []
        inst._open_dir = lambda p: opened.append(p)  # type: ignore[method-assign]
        target = r"C:\some\output dir"
        link = inst.engine.logger.log_link(target, "open", path=target)
        href = re.search(r'href="([^"]+)"', link).group(1)
        inst._on_log_link_clicked(QUrl(href))
        self.assertEqual(opened, [target])

    def test_http_link_opens_in_browser_not_explorer(self):
        """A plain http(s) anchor opens in the browser (QDesktopServices), and
        is never mistaken for a filesystem path. QDesktopServices is mocked so
        the test never actually spawns a browser (openUrl hits the OS shell
        even under the offscreen platform)."""
        inst = self._bare_slots()
        opened = []
        inst._open_dir = lambda p: opened.append(p)  # type: ignore[method-assign]
        url = QUrl("https://github.com/m3trik/extapps#readme")
        with mock.patch("qtpy.QtGui.QDesktopServices") as qds:
            inst._on_log_link_clicked(url)
        self.assertEqual(opened, [])  # not routed to the file explorer
        qds.openUrl.assert_called_once_with(url)

    def test_success_logs_clickable_output_link(self):
        """On success, a completion message embeds a clickable action://open
        link to the output dir (so a click reveals the results folder)."""
        inst = self._bare_slots()
        out = tempfile.mkdtemp(prefix="compositor_out_")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        src = tempfile.mkdtemp(prefix="compositor_src_")
        self.addCleanup(shutil.rmtree, src, ignore_errors=True)
        # Skip the real compositing; any non-MASK_FAILURE result is "success".
        inst.engine.process_batch = Mock(return_value=Mock())

        with mock.patch.object(inst.engine.logger, "info") as info:
            inst.process({}, src, out, "mymap")

        link_msgs = [
            c.args[0]
            for c in info.call_args_list
            if c.args and "action://open" in c.args[0]
        ]
        self.assertTrue(link_msgs, "no action:// output link logged on success")
        url = urlparse(re.search(r'href="(action://[^"]+)"', link_msgs[-1]).group(1))
        self.assertEqual(url.netloc, "open")
        self.assertEqual(parse_qs(url.query)["path"][0], out)


    def _estimated_map_count(self, inst, images, src, out):
        """The pre-flight 'Sorting N images, into M maps' estimate."""
        inst.engine.process_batch = Mock(return_value=Mock())
        with mock.patch.object(inst.engine.logger, "info") as info:
            inst.process(images, src, out, "mymap")
        line = next(
            c.args[0]
            for c in info.call_args_list
            if c.args and "Sorting" in str(c.args[0])
        )
        return int(re.search(r"into <b>(\d+)</b> maps", line).group(1))

    def _normal_images(self, directory, *types):
        from PIL import Image

        images = {}
        for typ in types:
            path = os.path.join(directory, f"src_{typ}.png")
            Image.new("RGB", (4, 4), (127, 127, 255)).save(path)
            with Image.open(path) as im:
                images[path] = im.copy()
        return images

    def test_estimate_adds_the_complement_only_when_one_format_is_present(self):
        """+1 is owed when the engine will synthesize the missing counterpart.

        ``contains_map_types`` is an *any* test, so the old ``has_normal_pair``
        flag added the complement whenever any normal map was present —
        including when the batch already carried both formats, where nothing
        is generated.
        """
        inst = self._bare_slots()
        src = tempfile.mkdtemp(prefix="compositor_src_")
        self.addCleanup(shutil.rmtree, src, ignore_errors=True)
        out = tempfile.mkdtemp(prefix="compositor_out_")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)

        one = self._normal_images(src, "Normal_OpenGL")
        self.assertEqual(self._estimated_map_count(inst, one, src, out), 2)  # 1 + 1

        both = self._normal_images(src, "Normal_OpenGL", "Normal_DirectX")
        self.assertEqual(self._estimated_map_count(inst, both, src, out), 2)  # 2 + 0

    def test_success_reports_actual_written_count(self):
        """The completion message counts what the engine wrote.

        ``total_maps`` is a pre-flight estimate that adds one for the
        auto-generated normal complement — which the engine skips when the
        batch already carries that format — so it over-reports. The engine's
        ``written_paths`` is the post-run ground truth.
        """
        inst = self._bare_slots()
        out = tempfile.mkdtemp(prefix="compositor_out_")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        src = tempfile.mkdtemp(prefix="compositor_src_")
        self.addCleanup(shutil.rmtree, src, ignore_errors=True)

        written = [
            os.path.join(out, f"mymap_{t}.png") for t in ("Base_Color", "Metallic")
        ]

        def _fake_batch(*_args, **_kwargs):
            inst.engine._written_paths = list(written)
            return Mock()

        inst.engine.process_batch = _fake_batch

        with mock.patch.object(inst.engine.logger, "info") as info:
            inst.process({}, src, out, "mymap")

        wrote = [
            c.args[0]
            for c in info.call_args_list
            if c.args and "map(s) to" in str(c.args[0])
        ]
        self.assertTrue(wrote, "no completion count logged on success")
        self.assertIn(f"Wrote {len(written)} map(s)", wrote[-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
