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
from pathlib import Path
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
            # The page's switch outlives a test the same way.
            deliverer.locomotion = True

    def setUp(self) -> None:
        from extapps.webxr_preview.launcher import WebXrPreviewUI

        self._reset_servers()

        # Ephemeral ports: the default is the production one, where a preview
        # tab the user has open would start polling a test's server.
        port = mock.patch.object(ptk.PreviewServer, "DEFAULT_PORT", 0)
        port.start()
        self.addCleanup(port.stop)

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

        # Nor may a share reach a real tunnel provider: it would publish this
        # machine through the user's own tailnet or account. One did, once --
        # "Auto" resolved on the real machine spawned Tailscale Funnel, which
        # refused only because the user's own share held its port. Guarded at
        # what LAUNCHES, like the browser, and at the download settle offers.
        from pythontk.core_utils.app_installer import AppInstaller
        from pythontk.core_utils.app_launcher import AppLauncher

        tunnels = ("tailscale", "cloudflared")
        real_spawn, real_ensure = AppLauncher.spawn, AppInstaller.ensure

        def _guarded_spawn(executable, *args, **kwargs):
            stem = os.path.splitext(os.path.basename(str(executable)))[0].lower()
            if stem in tunnels:
                raise AssertionError(f"a test reached a real tunnel: {executable}")
            return real_spawn(executable, *args, **kwargs)

        def _guarded_ensure(name, *args, **kwargs):
            if name in tunnels:
                raise AssertionError(f"a test tried to download {name}")
            return real_ensure(name, *args, **kwargs)

        for guard in (
            mock.patch.object(AppLauncher, "spawn", side_effect=_guarded_spawn),
            mock.patch.object(AppInstaller, "ensure", side_effect=_guarded_ensure),
        ):
            guard.start()
            self.addCleanup(guard.stop)

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

        # A message box is modal too. A push that has to ASK -- a missing KTX2
        # encoder offers its managed install -- blocked the CI runner, which has
        # no toktx, until the 300s timeout killed pytest before it printed a
        # summary, and so kept the publish job red. Fail the case instead; a case
        # that expects a message replaces this, as TestTextureToolGate does.
        def _unexpected_message_box(*args, **kwargs):
            raise AssertionError(f"a test opened a modal message box: {args[:1]!r}")

        self.slots.sb.message_box = _unexpected_message_box

    def _record_log(self):
        """The panel's log lines from here on, as plain text."""
        logged = []
        real = self.slots.panel_log

        def record(text, *args, **kwargs):
            logged.append(str(text))
            return real(text, *args, **kwargs)

        self.slots.panel_log = record
        return logged

    def _pane_links(self):
        """Every link in the panel's log pane, by address."""
        links = set()
        block = self.slots.ui.txt000.document().begin()
        while block.isValid():
            fragments = block.begin()
            while not fragments.atEnd():
                fmt = fragments.fragment().charFormat()
                if fmt.isAnchor():
                    links.add(fmt.anchorHref())
                fragments += 1
            block = block.next()
        return links

    def _reopen(self, engine=None):
        """A second panel over the same QSettings store: the next DCC session."""
        from extapps.webxr_preview.launcher import WebXrPreviewUI

        ui = WebXrPreviewUI()
        self.addCleanup(ui.deleteLater)
        # The host injects its bridge AFTER the panel is built -- exactly what
        # tentacle's launch does (``launch(show=False)``, then ``engine =``).
        if engine is not None:
            ui.slots.engine = engine
        return ui.slots

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
        self.assertEqual(keys[-1], "file", "File on Disk stays last")

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


class TestGlbRowsMirrorTheExporter(_PanelTestCase):
    """The Textures and Lighting rows ARE the Scene Exporter's -- nothing to
    keep in sync.

    The preview used to offer WebP / KTX2 and nothing else, so every push was
    cut to the web ceiling (2048 px) whatever the export was set to.
    """

    def test_one_row_per_exporter_row_with_its_label_and_table(self):
        from extapps.webxr_preview import parameters as params

        options = ptk.ExportProfile.glb_options()
        self.assertEqual(
            list(params.GLB_KEYS.values()), list(ptk.ExportProfile.GLB_ROWS)
        )
        for key, row in params.GLB_KEYS.items():
            with self.subTest(row=row):
                spec = params.PARAMS[key]
                self.assertEqual(spec.label, ptk.ExportProfile.GLB_ROWS[row])
                self.assertEqual(list(spec.choices), list(options[row].items()))
                widget = self.slots._param_widgets[key]
                self.assertEqual(
                    [widget.itemText(i) for i in range(widget.count())],
                    list(options[row]),
                )

    def test_the_rows_default_to_the_exporters_defaults(self):
        """Where the Scene Exporter starts each row (the off state, and the
        lighting recipe's own level for Baked Reflections), so a fresh preview
        and a fresh export build the same texture pass and publish the same
        recipe. Pinned on the registry, not a live panel -- a panel restores
        its last session."""
        from extapps.webxr_preview import parameters as params

        exporter = ptk.ExportProfile.glb_defaults()
        defaults = params.defaults()
        for key, row in params.GLB_KEYS.items():
            with self.subTest(row=row):
                self.assertEqual(defaults[key], exporter[row])
        self.assertEqual(
            defaults["BAKED_REFLECTIONS"], ptk.ExportProfile.baked_reflections_default()
        )

    def test_the_texture_rows_answer_every_source(self):
        """Textures are the deliverer's, so a file source shows them too."""
        from extapps.webxr_preview import parameters as params

        textures = set(params.GLB_KEYS) - params.LIGHTING_KEYS
        self.slots._select_source("file")
        self.assertTrue(textures <= self.slots._relevant_param_keys())

    def test_the_lighting_rows_answer_a_host_source_only(self):
        """The recipe rides the scene sidecar, which a file push never builds:
        a Lighting row there would change nothing, so it is not offered."""
        from extapps.webxr_preview import parameters as params

        self.assertEqual(params.LIGHTING_KEYS, {"BAKED_REFLECTIONS"})
        self.assertEqual(params.PARAMS["BAKED_REFLECTIONS"].section, "Lighting")
        self.slots._select_source("file")
        self.assertFalse(params.LIGHTING_KEYS & self.slots._relevant_param_keys())
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.assertTrue(params.LIGHTING_KEYS <= self.slots._relevant_param_keys())


class TestPersistence(_PanelTestCase):
    """What a panel reopened in a NEW session restores, and what it must not.

    A second ``WebXrPreviewUI`` is a fresh Switchboard over the same (sandboxed)
    QSettings store -- the shape of the next DCC session (``_reopen``).
    """

    def test_the_source_choice_survives_a_new_session_with_a_host(self):
        """Regression: the combo restored before the host injected its scopes,
        so the stored choice was out of range, skipped -- and the repopulate
        that followed reset it to the first entry, every session."""
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("visible")

        reopened = self._reopen(engine=_FakeHostBridge)

        self.assertEqual(reopened._active_source(), "visible")

    def test_the_file_source_survives_a_new_session_with_a_host(self):
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("file")

        reopened = self._reopen(engine=_FakeHostBridge)

        self.assertEqual(reopened._active_source(), "file")

    def test_a_file_handed_over_before_the_host_is_not_overridden(self):
        """A hand-off selects File on Disk; re-applying last session's scope
        when the host's engine arrives would push the scene instead of the file
        the caller just handed over."""
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("visible")

        reopened = self._reopen()
        reopened.set_source_file(self.glb)
        reopened.engine = _FakeHostBridge

        self.assertEqual(reopened._active_source(), "file")

    def test_the_source_file_is_not_persisted(self):
        """The field names one hand-off, not a preference: a path restored from
        last session would be pushed by a press meant to ask for a file."""
        self.slots.set_source_file(self.glb)
        self.assertFalse(self.slots._source_edit().restore_state)

        reopened = self._reopen()

        self.assertEqual(reopened._source_text(), "")


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


class TestLocomotionSwitch(_PanelTestCase):
    """The Locomotion row is the page's switch, applied at once.

    The page reads it on every poll, so a headset mid-session -- a share's
    guests included -- follows the box within a second. Waiting for the next
    push would cost a re-export to stop someone walking about.
    """

    def _row(self):
        return self.slots._param_widgets["LOCOMOTION"]

    def tearDown(self) -> None:
        # The row persists, as every row here does: re-ticked before the panel
        # goes, so the next one -- the next test's -- opens on the default.
        self._row().setChecked(True)
        super().tearDown()

    def test_the_row_is_on_by_default_and_reaches_the_deliverer(self):
        self.slots.engine = _FakeHostBridge
        self.assertIs(self._row().isChecked(), True)
        self.assertIs(_FakeHostBridge.deliverer.locomotion, True)

    def test_unticking_stops_a_running_page_without_a_push(self):
        self.slots.engine = _FakeHostBridge
        server = _FakeHostBridge.deliverer.ensure_server()
        self._row().setChecked(False)
        self.assertIs(_FakeHostBridge.deliverer.locomotion, False)
        self.assertIs(server.manifest()["locomotion"], False)
        self._row().setChecked(True)
        self.assertIs(server.manifest()["locomotion"], True)

    def test_the_row_follows_the_deliverer_a_host_brings(self):
        # Unticked before any host: the file bridge's own deliverer takes it,
        # and adopting the host's hands the answer over rather than losing it.
        self._row().setChecked(False)
        self.slots.engine = _FakeHostBridge
        self.assertIs(_FakeHostBridge.deliverer.locomotion, False)

    def test_a_push_publishes_the_row_whatever_set_the_deliverer_last(self):
        self.slots.engine = _FakeHostBridge
        self._row().setChecked(False)
        _FakeHostBridge.deliverer.locomotion = True  # behind the panel's back
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        manifest = _FakeHostBridge.deliverer.server.manifest()
        self.assertIs(manifest["locomotion"], False)


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

    def test_a_push_logs_where_its_time_went(self):
        """The question after every slow push, answered in the panel rather
        than by a profiler: the result's stage timings, one line."""
        logged = self._record_log()
        self._push_file()
        self.assertTrue(any(line.startswith("Push took ") for line in logged), logged)

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

    KTX2 = {"texture_file_type": "ktx2"}

    def test_webp_asks_nothing(self):
        # Probing for a tool the push will not use would ask about a control
        # the user never touched -- Original is the web default, WebP too.
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder") as ensure:
            for rows in ({}, {"texture_file_type": ""}, {"texture_file_type": "webp"}):
                self.assertTrue(self.slots._texture_tool_ready(rows), rows)
        ensure.assert_not_called()

    def test_ktx2_with_its_twin_asks_too(self):
        """Both KTX2 entries encode with toktx; the twin only adds a copy."""
        with mock.patch(
            "pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None
        ) as ensure:
            self.assertTrue(
                self.slots._texture_tool_ready(
                    {"texture_file_type": ptk.ExportRun.KTX2_WITH_FALLBACK}
                )
            )
        ensure.assert_called_once()

    def test_ktx2_hands_the_primitive_the_panels_own_consent(self):
        seen = {}

        def _capture(prompt=None):
            seen["prompt"] = prompt
            return None

        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=_capture):
            self.assertTrue(self.slots._texture_tool_ready(self.KTX2))
        self.assertTrue(callable(seen["prompt"]))

    def test_an_accepted_install_reports_the_binary_it_landed(self):
        with mock.patch(
            "pythontk.ImgUtils.ensure_ktx2_encoder", return_value="C:/toktx.exe"
        ):
            self.assertTrue(self.slots._texture_tool_ready(self.KTX2))
        self.assertTrue(any("toktx.exe" in m for m in self.answers))

    def test_an_already_installed_toktx_says_nothing(self):
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None):
            self.assertTrue(self.slots._texture_tool_ready(self.KTX2))
        self.assertEqual(self.answers, [])

    def test_a_declined_install_stops_the_push_with_the_fix(self):
        error = FileNotFoundError(
            "toktx not found; install KTX-Software from https://…"
        )
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=error):
            self.assertFalse(self.slots._texture_tool_ready(self.KTX2))
        # The refusal names the manual install, so it IS the message.
        self.assertEqual(self.answers, [str(error)])

    def test_a_declined_install_leaves_its_install_page_in_the_log(self):
        """The dialog is a toast gone in seconds; the log keeps the install
        page, as a link."""
        page = "https://github.com/KhronosGroup/KTX-Software/releases"
        error = FileNotFoundError(f"toktx not found; install KTX-Software from {page}.")
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=error):
            self.assertFalse(self.slots._texture_tool_ready(self.KTX2))
        self.assertIn(page, self._pane_links())

    def test_a_declined_install_never_reaches_the_server(self):
        error = FileNotFoundError("toktx not found")
        self.slots.set_source_file(self.glb)
        self.slots._write_param("TEXTURE_FILE_TYPE", "ktx2")
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
        # The KTX2 tool gate is TestTextureToolGate's subject. Here every push
        # would otherwise ask the MACHINE: with KTX2 restored from an earlier
        # case and no toktx installed (the CI runner), each push opened the
        # install prompt -- green on a workstation, a timeout on CI.
        encoder = mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None)
        encoder.start()
        self.addCleanup(encoder.stop)

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

    def test_every_viewer_script_row_names_a_packaged_script(self):
        """A row whose value the server does not ship raises at push time, AFTER
        the export has been paid for -- so the registry is checked here."""
        from extapps.webxr_preview import parameters as params

        values = [choice[1] for choice in params.PARAMS["VIEWER_SCRIPTS"].choices]
        self.assertIn("snapshot", values, "the Export Image row is missing")
        self.assertEqual(sorted(set(values) - set(ptk.PreviewServer.SCRIPTS)), [])

    def test_the_glb_rows_reach_the_deliverer_as_the_export_names_them(self):
        """Every row, every push, keyed as the Scene Exporter keys it -- so the
        deliverer resolves them with the exporters' own methods."""
        self.slots._write_param("TEXTURE_FILE_TYPE", "ktx2")
        self.slots._write_param("OPTIMIZE_TEXTURES", 4096)
        self.slots._write_param("BAKED_REFLECTIONS", "half")
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertEqual(
            self.sent[0]["glb_options"],
            {
                "texture_file_type": "ktx2",
                "optimize_textures": 4096,
                "secondary_max_size": 0,
                "uastc_rdo": 0,
                "baked_reflections": "half",
            },
        )

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


#: The link the fake tunnel prints.
_FAKE_LINK = "https://panel-share.example.test"
#: The page a fake provider's one-time step names (``fake-step``).
_STEP_PAGE = "https://step.example.test/enable"


class TestShareLink(_PanelTestCase):
    """Sharing through the panel: one server, one link, view-only.

    The Sharing row is the switch -- a provider shares, Off stops -- and its
    option box carries Share Now, Copy Link and Stop Sharing.

    The tunnel is a fake provider -- a real child printing a link -- driven
    through pythontk's real ShareTunnel, so the path under test is the panel's
    wiring onto the server a push uses, not a mock of it.
    """

    def setUp(self):
        super().setUp()
        #: Created to take the ``fake-step-then-link`` provider's step.
        self.step_taken = self.temp.path(extension=".step")
        fake = {
            "label": "Fake tunnel",
            "executable": sys.executable,
            "args": [
                "-u",
                "-c",
                f"import time; print('{_FAKE_LINK}', flush=True); time.sleep(600)",
            ],
            "url": r"(https://panel-share\.example\.test)",
            "ready": None,
            "public": True,
            "install": "https://example.test/install",
        }
        providers = mock.patch.dict(
            ptk.ShareTunnel.PROVIDERS,
            {
                "fake": fake,
                "fake-exits": {**fake, "args": ["-c", "raise SystemExit(4)"]},
                # Prints the page a one-time step takes, then waits -- the way
                # Tailscale does with Funnel not yet enabled for the tailnet.
                "fake-step": {
                    **fake,
                    "args": [
                        "-u",
                        "-c",
                        f"import time; print('To enable, visit: {_STEP_PAGE}', "
                        "flush=True); time.sleep(600)",
                    ],
                    "action": r"https://step\.example\.test/\S+",
                },
                # The same step, then the link once it is taken -- here, once
                # the file ``self.step_taken`` names exists.
                "fake-step-then-link": {
                    **fake,
                    "args": [
                        "-u",
                        "-c",
                        "import os, time\n"
                        f"print('To enable, visit: {_STEP_PAGE}', flush=True)\n"
                        f"while not os.path.exists({self.step_taken!r}):\n"
                        "    time.sleep(0.05)\n"
                        f"print('{_FAKE_LINK}', flush=True)\n"
                        "time.sleep(600)",
                    ],
                    "action": r"https://step\.example\.test/\S+",
                },
            },
        )
        providers.start()
        self.addCleanup(providers.stop)
        # This machine's alias config must not leak into the case.
        env = mock.patch.dict(
            os.environ,
            {ptk.PreviewServer.ALIAS_ENV: "", ptk.PreviewServer.ALIAS_URL_ENV: ""},
        )
        env.start()
        self.addCleanup(env.stop)
        self.messages = []
        self.slots.sb.message_box = lambda text, *a, **k: self.messages.append(text)
        # These cases push for real: the share rides the server a push starts.
        # The panel restores its rows between cases, so a KTX2 row an earlier
        # case left (TestPushWiring writes one) sent the push through the KTX2
        # tool gate, which on a runner without toktx -- CI -- stopped it before
        # any server started. Textures are not this class's subject: the row
        # goes back to its default, which needs no tool.
        self.slots._write_param("TEXTURE_FILE_TYPE", "")

    def _share(self, provider="fake"):
        """Share Now, pressed on the row's option box -- the wiring included."""
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value=provider):
            self._action("btn_share_now").click()

    def _row(self):
        return self.slots._param_widgets["SHARE_VIA"]

    def _action(self, name):
        return getattr(self._row().option_box.menu, name)

    def _pump_until(self, condition, timeout=20.0):
        """Run the UI loop until *condition* holds; fail when it never does."""
        import time

        deadline = time.monotonic() + timeout
        while not condition():
            self.assertLess(time.monotonic(), deadline, "the panel never got there")
            self.app.processEvents()
            time.sleep(0.02)

    def _wait_on_the_step(self):
        """Share through a provider that stops on its step; the panel is free
        again while the share waits for it. The dialog is answered Not Now."""
        self.slots.sb.confirm = lambda *args, **kwargs: False
        self._share(provider="fake-step-then-link")
        self.assertTrue(self.slots._share_pending, "the share did not wait")
        self.assertIsNone(self.slots._server().share_info())

    def test_the_row_offers_every_provider_pythontk_drives(self):
        """A registry, not a list kept here: a provider added upstream
        arrives as an entry by itself."""
        from extapps.webxr_preview import parameters as params

        values = [entry[1] for entry in params.PARAMS["SHARE_VIA"].choices]
        self.assertEqual(values[:2], ["off", "auto"])
        self.assertEqual(
            set(values[2:]),
            {name for name in ptk.ShareTunnel.PROVIDERS if not name.startswith("fake")},
        )

    def test_the_row_answers_every_source(self):
        self.slots.set_source_file(self.glb)
        self.assertIn("SHARE_VIA", self.slots._relevant_param_keys())
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.assertIn("SHARE_VIA", self.slots._relevant_param_keys())

    def test_the_sharing_actions_live_on_the_rows_option_box(self):
        """Beside the switch they act on, not in the header menu."""
        handlers = {item[3] for item in self.slots.HEADER_MENU_ITEMS}
        self.assertFalse(handlers & {"share_link", "stop_sharing"})
        for name in ("btn_share_now", "btn_copy_share_link", "btn_stop_sharing"):
            self.assertIsNotNone(self._action(name), name)

    def test_the_row_starts_off_each_session(self):
        """A link is a door to this machine: a session opens it only when
        asked, so a row left on yesterday does not share today's first push."""
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        self.assertIsNotNone(self.slots._server().share_info())
        # Down with the row left on: what is left to restore is the setting.
        self.slots._server().unshare()

        reopened = self._reopen()

        self.assertEqual(reopened._sharing_choice(), "off")

    def test_a_panel_opened_on_a_live_share_shows_it_on_the_row(self):
        """The server outlives the panel: reopened while a share is up, the
        row shows its provider rather than Off beside a live link."""
        fake = ptk.ShareTunnel.PROVIDERS["fake"]
        with mock.patch.dict(ptk.ShareTunnel.PROVIDERS, {"cloudflared": fake}):
            with mock.patch.object(
                ptk.ShareTunnel, "settle", return_value="cloudflared"
            ):
                self.slots._write_param("SHARE_VIA", "cloudflared")
            self.assertEqual(self.slots._server().share_url, _FAKE_LINK)
            reopened = self._reopen()
            self.assertEqual(reopened._sharing_choice(), "cloudflared")
            self.assertEqual(self.slots._server().share_url, _FAKE_LINK)

    def test_picking_another_provider_while_one_waits_on_its_step_switches(self):
        """The wait was for one provider: asked for another, the panel ends
        it and shares there -- not the first one's page offered again."""
        self._wait_on_the_step()
        asked = []
        self.slots.sb.confirm = lambda question, *a, **k: asked.append(question)
        self.slots._share("fake", interactive=True)
        self.assertEqual(asked, [], "the first provider's step was offered again")
        self.assertEqual(self.slots._server().share_url, _FAKE_LINK)
        self.assertFalse(self.slots._share_pending)
        Path(self.step_taken).touch()  # the old wait's step, taken late
        self._pump_until(lambda: True)
        self.assertEqual(self.slots._server().share_url, _FAKE_LINK)

    def test_picking_a_provider_shares_at_once_and_off_takes_it_down(self):
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        server = self.slots._server()
        self.assertEqual(server.share_url, _FAKE_LINK)
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)

        self.slots._write_param("SHARE_VIA", "off")

        self.assertIsNone(server.share_info())
        self.assertTrue(server.is_running, "the owner's page lost its server")

    def test_with_sharing_on_every_push_keeps_the_link_up_and_logs_it(self):
        """The same link each push -- a guest's page picks the push up -- and a
        share whose client dropped is brought back by the next one."""
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
            logged = self._record_log()
            self.slots.b000()
            server = self.slots._server()
            self.assertTrue(any(_FAKE_LINK in line for line in logged), logged)
            first = server._tunnel._process

            first.kill()
            first.wait(timeout=10)
            self.assertIsNone(server.share_info())
            logged.clear()
            self.slots.b000()

        self.assertEqual(server.share_url, _FAKE_LINK)
        self.assertIsNot(
            server._tunnel._process, first, "the dropped share stayed down"
        )
        self.assertTrue(any("Shared, view-only" in line for line in logged), logged)
        self.assertEqual(self.messages, [], "a push put a share in a dialog")

    def test_with_sharing_off_a_push_shares_nothing(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertIsNone(self.slots._server().share_info())

    def test_a_push_share_that_fails_is_logged_not_put_in_a_dialog(self):
        """The row changed interactively; a push is not the moment to
        interrupt, and the next push tries again."""
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake-exits"):
            self.slots._write_param("SHARE_VIA", "auto")
            self.messages.clear()
            logged = self._record_log()
            self.slots.b000()
        self.assertEqual(self.messages, [])
        self.assertTrue(any("Sharing failed" in line for line in logged), logged)

    def test_stop_sharing_on_the_option_box_turns_the_row_off(self):
        self._share()
        server = self.slots._server()
        self._action("btn_stop_sharing").click()
        self.assertEqual(self.slots._sharing_choice(), "off")
        self.assertIsNone(server.share_info())

    def test_a_providers_one_time_step_is_offered_not_dead_ended(self):
        """Funnel not yet enabled for the tailnet: the page that enables it is
        offered and opened on a yes -- not an error dialog to copy a link from."""
        asked = []
        self.slots.sb.confirm = lambda question, *a, **k: asked.append(question) or True
        self._share(provider="fake-step")
        self.assertEqual(len(asked), 1)
        self.assertIn(_STEP_PAGE, self.opened)
        self.assertEqual(self.messages, [], "an offer, not an error")
        self.assertIsNone(self.slots._server().share_info())

    def test_a_push_logs_a_providers_step_and_asks_nothing(self):
        """The row asked once; a push is not the moment to ask again."""
        asked = []
        self.slots.sb.confirm = lambda question, *a, **k: (
            asked.append(question) or False
        )
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake-step"):
            self.slots._write_param("SHARE_VIA", "auto")
            logged = self._record_log()
            self.slots.b000()
        self.assertEqual(len(asked), 1, "the push asked again")
        self.assertTrue(any(_STEP_PAGE in line for line in logged), logged)
        self.assertNotIn(_STEP_PAGE, self.opened)

    def test_once_the_step_is_taken_the_link_comes_up_by_itself(self):
        """Reported: Funnel enabled in the browser, and still no link -- the
        share had given up on the step, and the retry it asked for was easy to
        miss. It waits on the step in the background now, the panel free
        meanwhile, and the link arrives with nothing pressed."""
        self._wait_on_the_step()
        self.assertIn(_STEP_PAGE, self._pane_links(), "the step page is not a link")
        Path(self.step_taken).touch()  # enabled, in the browser
        server = self.slots._server()
        self._pump_until(lambda: not self.slots._share_pending)
        self.assertEqual(server.share_url, _FAKE_LINK)
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)
        self.assertIn(_FAKE_LINK, self._pane_links())
        self.assertEqual(self.messages, [])

    def test_a_step_never_taken_ends_the_wait_and_names_the_page(self):
        """The wait is bounded; when it runs out the log says the share
        stopped waiting and where the step is -- no dialog, since whoever
        started it may be long gone."""
        with mock.patch.object(ptk.ShareTunnel, "_STEP_WAIT", 1.0):
            self._wait_on_the_step()
            logged = self._record_log()
            self._pump_until(lambda: not self.slots._share_pending, timeout=15)
        self.assertTrue(
            any("stopped waiting" in line and _STEP_PAGE in line for line in logged),
            logged,
        )
        self.assertIsNone(self.slots._server().share_info())
        self.assertEqual(self.messages, [])

    def test_turning_sharing_off_while_it_waits_on_the_step_ends_the_wait(self):
        self._wait_on_the_step()
        logged = self._record_log()
        self.slots._write_param("SHARE_VIA", "off")
        self._pump_until(lambda: not self.slots._share_pending, timeout=10)
        Path(self.step_taken).touch()  # taken after all: nothing comes up
        self.app.processEvents()
        self.assertIsNone(self.slots._server().share_info())
        self.assertFalse(any("failed" in line for line in logged), logged)
        self.assertEqual(self.messages, [])

    def test_a_push_while_the_share_waits_names_the_step_again(self):
        self.slots.set_source_file(self.glb)
        self._wait_on_the_step()
        logged = self._record_log()
        self.slots.b000()
        self.assertTrue(any(_STEP_PAGE in line for line in logged), logged)
        self.assertTrue(self.slots._share_pending, "the push dropped the wait")

    def test_copy_link_with_the_row_on_brings_the_link_up(self):
        """Reported: with the row on and its link down, Copy Link said to
        pick a provider -- the one already picked. It shares now, and the link
        is copied as it arrives."""
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake-exits"):
            self.slots._write_param("SHARE_VIA", "auto")  # on, but its share failed
        logged = self._record_log()
        QApplication.clipboard().setText("")
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self._action("btn_copy_share_link").click()
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)
        self.assertFalse(any("pick a provider" in line for line in logged), logged)

    def _open_as_guest(self, tab="guest-tab-1"):
        """A guest's page polling the share, the way the tunnel forwards it."""
        server = self.slots._server()
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.guest_port}/manifest.json?id={tab}",
            headers={"Host": _FAKE_LINK.split("://", 1)[1]},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.status, 200)

    def test_a_push_says_who_has_the_link_open_never_a_bare_zero(self):
        """Reported: "(0 watching)" read like a counter stuck at zero. It
        counts the guest tabs open right now -- a push resets nothing -- so
        with the link unopened the line says so, and a guest shows by count."""
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
            logged = self._record_log()
            self.slots.b000()
            live = [line for line in logged if line.startswith("Live at")]
            self.assertEqual(len(live), 1, logged)
            self.assertIn("no guest has it open", live[0])
            self.assertNotIn("0 watching", live[0])

            self._open_as_guest()
            logged.clear()
            self.slots.b000()
        live = [line for line in logged if line.startswith("Live at")]
        self.assertEqual(len(live), 1, logged)
        self.assertIn("(1 guest watching)", live[0])

    def test_the_footer_counts_a_guest_without_the_panel_doing_anything(self):
        """The footer's count moved only when the panel acted -- a guest who
        opened the link after the push stayed "0 guests" until the next one.
        It re-reads while the panel is open."""
        self._share()
        footer = self.slots.ui.footer
        self.assertIn("(0 guests)", footer.statusText())
        self.slots.ui.show()
        self.addCleanup(self.slots.ui.hide)
        self.slots._status_timer.setInterval(50)
        self._open_as_guest()
        self._pump_until(lambda: "(1 guest)" in footer.statusText(), timeout=5)

    def test_the_addresses_a_push_gives_are_links(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertIn(self.slots._server().url, self._pane_links())

    def test_a_refused_share_leaves_its_install_page_in_the_log(self):
        """The dialog is a toast gone in seconds; the log keeps the page."""
        absent = {
            **ptk.ShareTunnel.PROVIDERS["fake"],
            "executable": "no-such-tunnel-cli-xyz",
            "paths": (),
        }
        with mock.patch.dict(ptk.ShareTunnel.PROVIDERS, {"fake-absent": absent}):
            self.slots._share("fake-absent", interactive=True)
        self.assertEqual(len(self.messages), 1)
        self.assertIn("https://example.test/install", self._pane_links())

    def test_copy_link_copies_the_live_link(self):
        self._share()
        QApplication.clipboard().setText("")
        self._action("btn_copy_share_link").click()
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)

    def test_share_link_shares_the_one_server_and_copies_the_link(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()  # the server a push made
        pushed_to = self.slots._server()

        self._share()

        self.assertIs(
            self.slots._server(), pushed_to, "sharing started a second server"
        )
        self.assertEqual(pushed_to.share_url, _FAKE_LINK)
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)
        self.assertIn(f"shared at {_FAKE_LINK} (0 guests)", self.slots._status_text())
        self.assertEqual(self.messages, [])

    def test_share_link_before_any_push_starts_serving(self):
        """A link can go out before the first model does."""
        self._share()
        self.assertEqual(self.slots._server().share_url, _FAKE_LINK)
        self.assertEqual(self.opened, [], "sharing must not open a tab")

    def test_a_refused_provider_stops_before_anything_starts(self):
        """Declined install, or none possible: settle has already said why."""
        self._share(provider=None)
        self.assertIsNone(self.slots._server())

    def test_a_failed_share_leads_with_the_next_step(self):
        self._share(provider="fake-exits")
        self.assertEqual(len(self.messages), 1)
        self.assertIn("exited (code 4)", self.messages[0])
        self.assertNotIn("\n", self.messages[0], "the dialog carries the one line")
        self.assertIsNone(self.slots._server().share_info())

    def test_stop_sharing_takes_the_link_down_and_leaves_the_page(self):
        self._share()
        server = self.slots._server()
        self.slots.stop_sharing()
        self.assertIsNone(server.share_info())
        self.assertTrue(server.is_running, "the owner's page lost its server")
        self.assertNotIn("shared at", self.slots._status_text())

    def test_the_share_waits_off_the_ui_thread(self):
        """A share waits on its provider and then on public DNS -- 6-18 s for
        a quick tunnel's new name -- and on the UI thread that froze the panel,
        and the DCC hosting it, for the whole wait. It runs on a worker while
        the progress tick keeps the host's loop turning; a second press landing
        in that time (a tick is where one would) opens no second share."""
        import threading
        import time
        from contextlib import contextmanager

        calls, ticks = [], []

        def slow_share(**kwargs):
            calls.append(threading.current_thread())
            time.sleep(0.5)
            return {"url": _FAKE_LINK, "public": True, "alias_error": None}

        def tick(*args, **kwargs):
            ticks.append(threading.current_thread())
            if len(ticks) == 1:
                self.slots.share_link()  # a second press, mid-share
            return True

        @contextmanager
        def progress(*args, **kwargs):
            yield tick

        with (
            mock.patch.object(self.slots.bridge, "share", side_effect=slow_share),
            mock.patch.object(self.slots.sb, "progress", progress),
        ):
            self._share()

        self.assertEqual(len(calls), 1, "a second press opened a second share")
        self.assertIsNot(calls[0], threading.main_thread(), "shared on the UI thread")
        self.assertGreater(len(ticks), 3, "the panel was not kept turning")
        self.assertTrue(all(t is threading.main_thread() for t in ticks))
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)

    def test_stop_sharing_retires_a_share_whose_client_died(self):
        """A share whose tunnel client exited on its own reads as not shared,
        so Stop Sharing answered "Nothing is being shared" and left it be: the
        guest listener open, and the alias still sending guests to the dead
        link until the next share."""
        from pathlib import Path

        folder = Path(self.temp.dir_path())
        with mock.patch.dict(os.environ, {ptk.PreviewServer.ALIAS_ENV: str(folder)}):
            self._share()
        server = self.slots._server()
        process = server._tunnel._process
        process.kill()
        process.wait(timeout=10)
        self.assertIsNone(server.share_info())

        self.slots.stop_sharing()

        self.assertIsNone(server.guest_port, "the guest listener was left open")
        page = (folder / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(_FAKE_LINK, page)
        self.assertIn("Nothing is being shared right now", page)


if __name__ == "__main__":
    unittest.main()
