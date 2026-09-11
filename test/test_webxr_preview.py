#!/usr/bin/env python
# coding=utf-8
"""Tests for the WebXR Preview panel.

UI smoke tests cover the build-time wiring; the delivery tests run a real
loopback :class:`pythontk.PreviewServer` against a tiny GLB fixture, because
the behaviour worth pinning here is what actually reaches the page. No DCC is
needed: the host bridge is faked, which is the point of the panel.

Run::

    pytest extapps/test/test_webxr_preview.py
"""

from __future__ import annotations

import hashlib
import os
import sys
import unittest
import urllib.request
from unittest import mock

import pythontk as ptk
from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QApplication

from pythontk.net_utils.preview import server as _preview_server


#: Browser CLASSES a launch can go through, mirroring ``TestSandbox``'s own
#: ``_LAUNCHER_TYPES``. A caller that wants a SPECIFIC browser cannot use the
#: module function -- it only ever opens the system default -- so it builds one
#: of these. Kept as the same SET the sandbox guards rather than just the one
#: the server happens to use today: that one changed under this suite once
#: already, and the failure looked like a bug in the panel.
_BROWSER_CLASSES = ("BackgroundBrowser", "GenericBrowser")


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class _FakeHostBridge(ptk.PreviewBridge):
    """A DCC bridge's shape without a DCC.

    Carries its own class-level deliverer exactly as ``mayatk.WebXrPreview``
    does, because that placement -- a class attribute, so the server outlives
    any one panel -- is what several of these tests are about.
    """

    payload_prefix = "test_fake_host"
    deliverer = ptk.PreviewDeliverer(title="Fake Host")
    scope_result: list = []

    def _resolve_objects(self, objects):
        return list(objects or [])

    def scope_objects(self, scope="selected"):
        return list(self.scope_result)


class _PanelTestCase(unittest.TestCase):
    """Shared fixture: a built panel, a GLB on disk, and no real browser."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    @staticmethod
    def _reset_servers() -> None:
        """Release every class-level deliverer's server between tests.

        A deliverer is a CLASS attribute on its bridge on purpose -- that is
        what keeps the port and the open tab alive across panel reopens for a
        whole session. It therefore also survives between TESTS, so without
        this the version counter carries over and a case asserting 'nothing is
        served yet' sees the previous case's server.
        """
        for deliverer in (_FakeHostBridge.deliverer, ptk.FilePreviewBridge.deliverer):
            server = getattr(deliverer, "server", None)
            if server is not None:
                try:
                    server.stop()
                except Exception:  # noqa: BLE001
                    pass
            deliverer.server = None

    def setUp(self) -> None:
        from extapps.webxr_preview.launcher import WebXrPreviewUI

        self._reset_servers()

        # A push opens a browser tab on the machine running the tests. Patch
        # what LAUNCHES, not the server method, so the "was a tab opened"
        # decision is still exercised.
        #
        # BOTH routes, because there are two: the module function opens the
        # system default, and a caller that wants a SPECIFIC browser has to
        # build a browser class directly -- which `open_in_browser` now does
        # when it can find one that can enter VR. Patching only the module
        # function left that route live, and it reached `ptk.TestSandbox`'s
        # guard and raised. That is the same pair the sandbox itself patches
        # (`_LAUNCHERS` / `_LAUNCHER_TYPES`); if a third route ever appears,
        # that tuple is where it will be named.
        # A push with an empty Source File reaches the ROW's browse button,
        # which opens a MODAL file dialog: under a test run that blocks the
        # process with no output and no failure -- the same class of hazard as
        # the browser launch above, and it cost one 300s hang to learn. Guarded
        # at the DIALOG, the way the browser is guarded at what launches it: a
        # case exercising the prompt patches the option instance over the top.
        # (Not at `BrowseOption.browse`: a plain MagicMock on that class
        # crashes the process when the row is built -- see BACKLOG.md.)
        for name in ("getOpenFileName", "getOpenFileNames", "getExistingDirectory"):
            guard = mock.patch.object(
                QtWidgets.QFileDialog, name, return_value=("", "")
            )
            guard.start()
            self.addCleanup(guard.stop)

        self.opened = []
        recorder = self.opened

        class _RecordingBrowser:
            def __init__(self, *args, **kwargs):
                pass

            def open(self, url, *args, **kwargs):
                recorder.append(url)
                return True

        self._real_open = _preview_server.webbrowser.open
        self._real_classes = {
            name: getattr(_preview_server.webbrowser, name) for name in _BROWSER_CLASSES
        }
        _preview_server.webbrowser.open = lambda url, *a, **k: (
            recorder.append(url),
            True,
        )[1]
        for name in _BROWSER_CLASSES:
            setattr(_preview_server.webbrowser, name, _RecordingBrowser)

        # Artifacts go through the shared store, which owns their teardown.
        self.temp = ptk.TempArtifacts("test_webxr_preview", policy="scoped")
        self.glb = self.temp.path(extension=".glb")
        # A GLB is published unchanged, so nothing here parses it; the bytes
        # only have to survive the trip intact.
        with open(self.glb, "wb") as handle:
            handle.write(b"glTF\x02\x00\x00\x00" + b"webxr-preview-fixture")
        self.digest = hashlib.md5(open(self.glb, "rb").read()).hexdigest()

        self.ui = WebXrPreviewUI()
        self.slots = self.ui.slots

    def tearDown(self) -> None:
        self._reset_servers()
        _preview_server.webbrowser.open = self._real_open
        for name, cls in self._real_classes.items():
            setattr(_preview_server.webbrowser, name, cls)
        self.temp.cleanup()
        self.ui.deleteLater()
        self.app.processEvents()


class TestSourceWiring(_PanelTestCase):
    """The Source combo and which rows each source answers."""

    def test_without_a_host_only_the_file_source_is_offered(self):
        self.assertEqual(
            [key for key, _label in self.slots._sources()],
            ["file"],
            "a panel with no host must not offer scopes it cannot resolve",
        )

    def test_injecting_a_host_grows_the_shared_scope_vocabulary(self):
        self.slots.engine = _FakeHostBridge
        keys = [key for key, _label in self.slots._sources()]
        # Read off Parameters.scope_spec, so this pins that the panel does not
        # keep a private copy of the vocabulary every other bridge shares.
        self.assertEqual(keys, ["selected", "all", "visible", "file"])
        self.assertEqual(
            keys[-1], "file", "File must stay last: combos persist by index"
        )

    def test_a_file_source_hides_the_export_rows(self):
        from extapps.webxr_preview import parameters as params

        self.slots._select_source("file")
        visible = self.slots._relevant_param_keys()
        # A file source exports nothing, so an export row would not merely be
        # unused -- it would be lying about what the push is going to do.
        self.assertFalse(visible & params.EXPORT_KEYS)
        self.assertTrue(params.FILE_KEYS <= visible)

    def test_a_scope_source_hides_the_file_rows(self):
        from extapps.webxr_preview import parameters as params

        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        visible = self.slots._relevant_param_keys()
        self.assertFalse(visible & params.FILE_KEYS)
        self.assertTrue(params.EXPORT_KEYS <= visible)


class TestOneServerPerPanel(_PanelTestCase):
    """Both sources must publish to ONE server.

    Regression: the file bridge used to adopt the host's deliverer inside the
    lazy host-bridge build, which a FILE push never reaches. Each source then
    started its own server, so a file push landed on a second port while the
    footer -- and the user's open tab -- were still on the first. The push
    reported success onto a page nobody was looking at.
    """

    def test_the_file_bridge_adopts_the_hosts_deliverer(self):
        self.slots.engine = _FakeHostBridge
        self.assertIs(self.slots.bridge.deliverer, _FakeHostBridge.deliverer)

    def test_adoption_does_not_construct_the_host_bridge(self):
        # Reading the deliverer off the CLASS is what lets the footer describe
        # a server a previous panel started without instantiating a DCC bridge.
        self.slots.engine = _FakeHostBridge
        self.assertIsNone(self.slots._host_bridge)

    def test_a_file_push_lands_on_the_hosts_server(self):
        self.slots.engine = _FakeHostBridge
        host_url = _FakeHostBridge.deliverer.ensure_server().url

        self.slots.set_source_file(self.glb)
        self.slots.b000()

        self.assertEqual(
            _FakeHostBridge.deliverer.server.url,
            host_url,
            "a file push started a second server; the open tab is on the first",
        )
        self.assertEqual(
            self.opened,
            [host_url],
            "the tab that opened points somewhere other than the live server",
        )

    def test_clearing_the_engine_releases_the_hosts_deliverer(self):
        # Symmetric with adoption. Keeping it would go on publishing through
        # the previous host's server -- the same footer/push disagreement,
        # reached from the other direction.
        self.slots.engine = _FakeHostBridge
        self.slots.engine = None
        self.assertIs(self.slots.bridge.deliverer, ptk.FilePreviewBridge.deliverer)

    def test_the_template_menu_is_off_for_a_source_combo(self):
        # `template_dir` is this package's own folder, so Refresh Templates
        # would re-scan nothing and Open Templates Folder would reveal source.
        self.assertFalse(self.slots.TEMPLATE_MENU)

    def test_adoption_leaves_other_users_of_the_class_alone(self):
        # An instance attribute shadows the class one, so a FilePreviewBridge
        # built anywhere else keeps its own deliverer.
        self.slots.engine = _FakeHostBridge
        self.assertIsNot(ptk.FilePreviewBridge().deliverer, _FakeHostBridge.deliverer)


class TestGlbIsPublishedAsAuthored(_PanelTestCase):
    """A GLB source short-circuits the build and is served byte-identical."""

    def _push_file(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        return self.slots._deliverer().server

    def test_the_served_bytes_are_the_source_bytes(self):
        server = self._push_file()
        served = urllib.request.urlopen(
            f"{server.url}/{server.manifest()['asset']}"
        ).read()
        self.assertEqual(hashlib.md5(served).hexdigest(), self.digest)

    def test_the_users_own_file_is_never_moved_or_rewritten(self):
        # The deliverer publishes with move=True because the GLB is normally
        # its own scratch artifact. On this path it is the user's file, so the
        # identity build MUST hand over a copy -- this is the assertion that
        # catches a regression there, and the failure would be unrecoverable.
        self._push_file()
        self.assertTrue(os.path.isfile(self.glb), "the source file was moved away")
        self.assertEqual(
            hashlib.md5(open(self.glb, "rb").read()).hexdigest(), self.digest
        )

    def test_the_sources_own_folder_is_searched_for_its_maps(self):
        """Why the panel no longer asks for a texture folder.

        A bake names its maps by basename plus the folder they were authored
        in, and that hint goes stale the moment the project moves -- so the
        field existed to repair it. The file being previewed is the one
        location that cannot be stale, and searching it unconditionally
        answers the case the field was added for without asking anything.
        """
        self._push_file()
        self.assertIn(
            os.path.normpath(os.path.dirname(self.glb)),
            [os.path.normpath(d) for d in self.slots.bridge.lightmap_search_dirs()],
        )

    def test_the_first_push_opens_exactly_one_tab(self):
        self._push_file()
        self.assertEqual(len(self.opened), 1)

    def test_a_second_push_reuses_the_watching_page(self):
        self._push_file()
        self._push_file()
        # "auto" opens only when nothing is watching; a fresh tab per push
        # would pile up and steal focus from the host.
        self.assertEqual(len(self.opened), 1)


class TestGuardsReportRatherThanPushBlind(_PanelTestCase):
    """Each refusal names its own cause, because they look identical on screen."""

    def test_a_dismissed_prompt_starts_no_server(self):
        # Cancelling the row's browse is an answer, not a failure: the push
        # stops where it stands, with nothing served and nothing to report.
        # A dismissal there is a no-op, so the field simply stays empty.
        from uitk import BrowseOption

        self.slots.set_source_file("")
        option = self.slots._source_edit().option_box.find_option(BrowseOption)
        with mock.patch.object(option, "browse"):
            self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)

    def test_a_missing_file_is_refused(self):
        self.slots.set_source_file(self.glb + ".nope")
        self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)

    def test_an_empty_scope_is_reported_not_exported(self):
        _FakeHostBridge.scope_result = []
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.slots.b000()
        # Pushing blind would collapse "nothing selected", "the scene is empty"
        # and "the export failed" into one message -- and the first two are the
        # user's own next action.
        self.assertIsNone(_FakeHostBridge.deliverer.server)

    def test_a_scope_push_without_a_host_is_reported(self):
        # Reachable when a host injects an engine, the user picks a scope, and
        # the engine is then cleared; the panel must not raise.
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.slots.engine = None
        self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)


class TestFooterReportsLiveState(_PanelTestCase):
    """The standing facts an option box had nowhere to put."""

    def test_it_says_so_when_nothing_is_served(self):
        self.assertIn("No preview server", self.slots._status_text())

    def test_it_names_the_version_and_url_after_a_push(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        text = self.slots._status_text()
        self.assertIn("v1", text)
        self.assertIn(self.slots._deliverer().server.url, text)


class TestTextureToolGate(_PanelTestCase):
    """KTX2's encoder must be OFFERED, never dead-end in a log line.

    Ported with the behaviour when the preview moved out of tentacle. The
    bridge already refuses a KTX2 push without ``toktx`` -- eagerly, before it
    pays for the sidecar and lightmap passes -- but it refuses by RAISING with
    an install URL, and a panel control that dead-ends in a URL is what the
    Scene Exporter's own KTX2 row stopped doing.
    """

    def setUp(self) -> None:
        super().setUp()
        self.answers = []
        self.slots.sb.message_box = lambda *a, **k: (
            self.answers.append(a[0]),
            "Yes" if len(a) > 1 else None,
        )[1]

    def test_webp_asks_nothing(self):
        # Probing for a tool the push will not use would ask about a control
        # the user never touched.
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder") as ensure:
            self.assertTrue(self.slots._texture_tool_ready("WEBP"))
        ensure.assert_not_called()

    def test_ktx2_hands_the_primitive_the_panels_own_consent(self):
        seen = {}

        def _capture(prompt=None):
            seen["prompt"] = prompt
            return None

        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=_capture):
            self.assertTrue(self.slots._texture_tool_ready("KTX2"))
        self.assertTrue(callable(seen["prompt"]))

    def test_an_accepted_install_reports_the_binary_it_landed(self):
        with mock.patch(
            "pythontk.ImgUtils.ensure_ktx2_encoder", return_value="C:/toktx.exe"
        ):
            self.assertTrue(self.slots._texture_tool_ready("KTX2"))
        self.assertTrue(any("toktx.exe" in m for m in self.answers))

    def test_an_already_installed_toktx_says_nothing(self):
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None):
            self.assertTrue(self.slots._texture_tool_ready("KTX2"))
        self.assertEqual(self.answers, [])

    def test_a_declined_install_stops_the_push_with_the_fix(self):
        error = FileNotFoundError(
            "toktx not found; install KTX-Software from https://…"
        )
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=error):
            self.assertFalse(self.slots._texture_tool_ready("KTX2"))
        # The refusal names the manual install, so it IS the message.
        self.assertEqual(self.answers, [str(error)])

    def test_a_declined_install_never_reaches_the_server(self):
        error = FileNotFoundError("toktx not found")
        self.slots.set_source_file(self.glb)
        self.slots._param_widgets["TEXTURE_FORMAT"].setCurrentIndex(1)
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=error):
            self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)


class TestPushWiring(_PanelTestCase):
    """What the panel actually sends, ported from the retired tentacle tests."""

    def setUp(self) -> None:
        super().setUp()
        self.sent = []
        self.slots.bridge.push = lambda **kwargs: (
            self.sent.append(kwargs),
            {"version": 1, "url": "http://x/", "asset": "a.glb"},
        )[1]

    def test_scripts_are_an_explicit_list_even_when_none_are_ticked(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        # None would mean "leave the server's set alone", which would make an
        # unticked box unable to turn a script back off.
        self.assertEqual(self.sent[0]["scripts"], [])

    def test_ticked_scripts_are_sent_by_their_registered_name(self):
        from extapps.webxr_preview import parameters as params

        widget = self.slots._param_widgets["VIEWER_SCRIPTS"]
        for i in range(widget.count()):
            widget.item(i).setCheckState(QtCore.Qt.Checked)
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        registered = [choice[1] for choice in params.PARAMS["VIEWER_SCRIPTS"].choices]
        self.assertEqual(sorted(self.sent[0]["scripts"]), sorted(registered))

    def test_the_texture_format_reaches_the_deliverer(self):
        self.slots._param_widgets["TEXTURE_FORMAT"].setCurrentIndex(1)
        self.slots.set_source_file(self.glb)
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None):
            self.slots.b000()
        self.assertEqual(self.sent[0]["texture_format"], "KTX2")

    def test_open_browser_is_always_auto(self):
        # "auto" reuses a page that can pick the version up -- including one
        # open in a headset -- rather than stealing focus with a fresh tab.
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertEqual(self.sent[0]["open_browser"], "auto")

    def test_a_progress_callback_travels_with_the_push(self):
        # Named on push() rather than swept into **params, which is the
        # EXPORT bag -- there it would reach the FBX write, never the build.
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertTrue(callable(self.sent[0]["progress"]))

    def _browse_option(self):
        from uitk import BrowseOption

        return self.slots._source_edit().option_box.find_option(BrowseOption)

    def _answer_the_prompt(self, path):
        """Stand in for the user picking *path* in the row's browse dialog."""
        option = self._browse_option()
        return mock.patch.object(
            option,
            "browse",
            side_effect=lambda: self.slots._source_edit().setText(path),
        )

    def test_an_empty_source_field_prompts_instead_of_refusing(self):
        """The first push has nothing chosen, and that is not an error.

        Refusing it sends the user to do by hand exactly what the dialog
        does, on the one press where what they want is unambiguous.
        """
        self.slots.set_source_file("")
        with self._answer_the_prompt(self.glb):
            self.slots.b000()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["objects"], [self.glb])

    def test_the_prompted_file_is_written_back_into_the_field(self):
        # Otherwise the next push prompts again -- the panel asking about the
        # file it is already previewing.
        self.slots.set_source_file("")
        with self._answer_the_prompt(self.glb):
            self.slots.b000()
        self.assertEqual(self.slots._source_text(), self.glb)

    def test_the_prompt_is_the_rows_own_browse(self):
        """One dialog, declared once, reached two ways.

        A second dialog opened from the push would carry its own copy of the
        filter, the title and the folder to start in -- three things that
        then have to be kept saying the same thing as the field's own browse
        button, and nothing would fail when they stopped.
        """
        self.slots.set_source_file("")
        with mock.patch.object(self._browse_option(), "browse") as browse:
            self.slots.b000()
        browse.assert_called_once()
        self.assertEqual(self.sent, [])  # nothing was chosen, so nothing pushed

    def test_the_row_offers_the_types_the_bridge_accepts(self):
        # A dialog that lets you pick a .obj only moves the refusal later.
        from extapps.webxr_preview import parameters as params

        file_types = self._browse_option()._file_types
        for pattern in params.SOURCE_FILE_TYPES:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, file_types)

    def test_a_chosen_file_does_not_prompt_again(self):
        self.slots.set_source_file(self.glb)
        with mock.patch.object(self._browse_option(), "browse") as browse:
            self.slots.b000()
        browse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
