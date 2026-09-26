# !/usr/bin/python
# coding=utf-8
"""Slots for the WebXR Preview panel — the single UI for the live preview.

One panel serves every source. A host that opened it injects its own bridge
(:attr:`WebXrPreviewSlots.engine` — ``mtk.WebXrPreview`` / ``btk.WebXrPreview``)
and the Source combo grows that host's scopes; with no host it offers a file on
disk, driven by :class:`pythontk.FilePreviewBridge`. Which source is active
changes *which bridge produces the payload* and nothing else: the build, the
texture pass, the version bump and the page are one chain either way, which is
why the panel body carries no per-host branch.

**Lookdev, not validation.** A push is the hand-off mixin's FBX write -- fast,
no export tasks or checks -- but the GLB is built by ``pythontk.GlbPipeline``,
the SAME chain a Scene Exporter's GLB goes through. What the page shows is what
the target platform receives for everything that lives in the file. To check an
exporter's whole run, export the GLB and pick it as the Source File.

The host injection point is the pattern uitk documents for this
(``ExternalAppHandler.launch(..., show=False)`` returns the widget so a caller
can set context before it is shown) and that the Map Converter panel already
uses: the panel owns the Source picker, the host owns what each scope means.
"""

from __future__ import annotations

import os
import threading
import traceback
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pythontk as ptk
from qtpy import QtCore
from uitk.bridge import BridgeSlotsBase, KindFactory, Parameters as _BridgeParams

from extapps.webxr_preview import parameters as _params


#: Source key for "publish a file already on disk". Not a scope in the shared
#: sense -- it resolves no host objects and no other hand-off could honour it --
#: which is exactly why it is NOT pushed into ``Parameters.scope_spec``.
FILE_SOURCE = "file"

#: Where the pipeline is documented, channel by channel. Deliberately NOT built
#: from ``extapps.DOCS_BASE_URL`` the way every other panel's docs link is: this
#: panel is a UI over an engine that lives in pythontk, and the document that
#: explains what survives the trip lives with that engine. Pointing at an
#: extapps path would mean either a stub to maintain or a broken link.
_DOCS_URL = (
    "https://github.com/m3trik/pythontk/blob/main/pythontk/docs/webxr_preview.md"
)


class _Worker:
    """*work* on a daemon thread, its outcome read back on the UI thread.

    A share waits on its provider for seconds -- a quick tunnel's new name
    takes 6-18 s to resolve -- and on a person for minutes when the provider
    stops on a one-time step. On the UI thread, either froze the panel and the
    DCC hosting it for the whole wait.
    """

    def __init__(self, work, name: str):
        self._outcome: Dict[str, Any] = {}
        self._thread = threading.Thread(
            target=self._run, args=(work,), name=name, daemon=True
        )
        self._thread.start()

    def _run(self, work) -> None:
        try:
            self._outcome["value"] = work()
        except BaseException as error:  # noqa: BLE001 -- re-raised by result()
            self._outcome["error"] = error

    @property
    def done(self) -> bool:
        return not self._thread.is_alive()

    def wait(self, seconds: float) -> None:
        self._thread.join(seconds)

    def result(self) -> Any:
        """What *work* returned; re-raises what it raised."""
        if "error" in self._outcome:
            raise self._outcome["error"]
        return self._outcome["value"]

    def when_done(self, parent, callback) -> None:
        """*callback* on the UI thread once *work* ends, off a timer *parent*
        owns -- nothing crosses threads but the outcome."""
        timer = QtCore.QTimer(parent)
        timer.setInterval(250)

        def check() -> None:
            if self.done:
                timer.stop()
                timer.deleteLater()
                callback()

        timer.timeout.connect(check)
        timer.start()


class WebXrPreviewSlots(BridgeSlotsBase):
    """Switchboard slots wired to ``webxr_preview.ui``."""

    UI_NAME = "webxr_preview"
    PRESETS_ROOT = Path("extapps/webxr_preview")
    LOG_TAG = "webxr_preview"

    # There is no user-facing artifact directory: the deliverable is served
    # from the preview's own root and the FBX is scratch the push consumes.
    REQUIRE_OUTPUT_DIR = False

    # The combo picks a MODE, not a template file, and ``template_dir`` is
    # this package's own directory -- so the template-management rows would
    # offer to re-scan nothing and to reveal source code.
    TEMPLATE_MENU = False

    DOCS_URL = _DOCS_URL
    DOCS_LABEL = "How the preview pipeline works"

    #: How often the footer re-reads who is watching while the panel shows.
    STATUS_REFRESH_MS = 2000

    HEADER_MENU_ITEMS = (
        (
            "Open Preview Page",
            "btn_open_page",
            "Open the preview in a browser tab.\n\n"
            "A push opens one for you when nothing is watching, so this is for "
            "getting a second view -- or getting the page back after closing "
            "it without paying for another push.",
            "open_preview_page",
        ),
        (
            "Stop Server",
            "btn_stop_server",
            "Stop serving and release the port.\n\n"
            "The server outlives every push on purpose, so a page left open in "
            "a headset keeps receiving them. Stop it only to free the port; "
            "the next push starts a new one, on a new port, and any page still "
            "open is then watching a closed socket.",
            "stop_server",
        ),
        ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
    )

    HELP_SPEC = {
        "title": "WebXR Preview",
        "body": "Push geometry to a live browser page and keep pushing. The "
        "page does not reload and needs no interaction -- a tab left open, "
        "including one in a PC-tethered headset, picks up each new version on "
        "its next poll. The loop is <b>change the scene, push, look up</b>.",
        "steps": [
            "Pick a <b>Source</b> -- a scope when a DCC opened this panel, or "
            "a file on disk.",
            "Set the delivery options and viewer scripts. The <b>Textures</b> "
            "and <b>Lighting</b> rows are the Scene Exporter's own: set them "
            "as the export is set and the preview's textures take the export's "
            "container and size, and its bake the export's reflections.",
            "Click <b>Push to Preview</b>. The first push opens a tab.",
        ],
        "sections": [
            (
                "Why it works in a headset",
                [
                    "The server binds <b>127.0.0.1</b>, and localhost is a "
                    "<i>secure context</i> -- which is the only reason "
                    "<b>navigator.xr</b> exists on the page at all. The same "
                    "page is an orbit preview on a desktop and a real "
                    "immersive-vr session with a headset attached.",
                    "Reaching the same server at a LAN address instead gives "
                    "no VR button and no error explaining why.",
                ],
            ),
            (
                "Sharing a link",
                [
                    "Pick a provider in the <b>Sharing</b> row and the preview "
                    "is published at an HTTPS link through a tunnel, which stays "
                    "up across pushes; <b>Off</b> takes it down. A guest needs "
                    "only a browser -- and a standalone headset gets its VR "
                    "button, because the link is a secure context. The row's "
                    "option box has <b>Share Now</b>, <b>Copy Link</b> and "
                    "<b>Stop Sharing</b>.",
                    "The share is a second, <b>view-only</b> door onto the same "
                    "server: guests see every push, and cannot save a setting, "
                    "record, or reach anything but the model and the page.",
                    "Each guest downloads the model and renders it on their "
                    "own device. The link IS the deliverable: a guest can save "
                    "the GLB. Stop sharing when the review is over.",
                ],
            ),
            (
                "What survives the trip",
                [
                    "The deliverable is self-describing: the lightmap "
                    "manifest and the scene sidecar ride inside the GLB's own "
                    "<b>extras</b>. There are no side files to keep together, "
                    "and a third-party glTF tool opens it and gets a sane, if "
                    "plainer, result.",
                    "A baked scene previews lit with no extra step, because "
                    "the bake's manifest travels with the export.",
                ],
            ),
        ],
        "notes": [
            "This is a lookdev push, not an export: it runs no export tasks "
            "or validation checks. To check an exporter's whole run, export "
            "the GLB and pick it as the Source File.",
            "A GLB source is published exactly as authored -- no re-encode, "
            "no sidecar, no lightmap rewiring -- so this doubles as a plain "
            "viewer on the same page and port.",
        ],
    }

    # ------------------------------------------------------------------ init
    def __init__(self, switchboard, **kwargs):
        #: The host's bridge CLASS, injected by whoever opened this panel.
        #: A class rather than an instance so construction stays lazy -- and so
        #: a host that opens the panel eagerly at startup pays nothing.
        self._engine = kwargs.get("engine", None)
        self._host_bridge = None
        self._status = None
        #: Counts stops, so a share's wait that a stop ended ends quietly; the
        #: share still opening, if any, is _clear_share_wait's to describe.
        self._share_stops = 0
        self._clear_share_wait()
        self._initial_source_file: str = kwargs.get("source_file", "") or ""
        super().__init__(switchboard)
        # By LABEL, not position. The list is host-dependent -- File on Disk is
        # entry 0 without a host and entry 3 with one -- so a stored index means
        # a different source in each, and the host's scopes arrive only after
        # this combo has already restored (see _populate_sources).
        self.ui.cmb000.restore_by = "text"
        # A hand-off, not a preference: a path restored from last session would
        # be pushed by the press that is meant to ask for a file, and it would
        # outrank a host's ``source_file``. Explicit, because registration
        # defaults every widget without the attribute to restoring.
        self._source_edit().restore_state = False
        KindFactory.connect_changed(
            self._param_widgets["LOCOMOTION"], self._apply_locomotion
        )
        self._build_sharing_row()
        self._adopt_host_deliverer()
        self._build_status_row()
        if self._initial_source_file:
            self.set_source_file(self._initial_source_file)

    # ------------------------------------------------------------------ base hooks
    @property
    def params_module(self):
        return _params

    @property
    def template_dir(self) -> Path:
        # No script templates -- this bridge renders nothing. The package dir
        # is a harmless stand-in for the (no-op) per-template description
        # lookup, matching the Unity panel's treatment of the same hook.
        return Path(__file__).resolve().parent

    def make_bridge(self):
        """The panel's own, host-free engine.

        Deliberately the FILE bridge rather than the host's, for two reasons.
        It is always constructible, so ``self.bridge`` is valid the moment the
        panel opens and the base's log redirect binds to a real logger. And it
        is the one bridge that exists in every host, so the panel's own plumbing
        never has to ask whether a DCC is present.

        The host's bridge is built separately (:meth:`_host`), on first use.
        """
        return ptk.FilePreviewBridge()

    # ------------------------------------------------------------------ sources
    @property
    def engine(self):
        """The host bridge class this panel pushes scopes through, or ``None``.

        The injection point for a host: launch the app with ``show=False``, set
        this, then show. Assigning it re-populates the Source combo, so a host
        can hand the panel its bridge at any point in the panel's life.
        """
        return self._engine

    @engine.setter
    def engine(self, value) -> None:
        if value is self._engine:
            return
        self._engine = value
        # Drop any bridge built from the previous engine -- keeping it would
        # push through the old host after the panel was re-pointed.
        self._host_bridge = None
        self._adopt_host_deliverer()
        self._populate_sources()
        self._refresh_status()

    def _host(self):
        """The host bridge, built once, or ``None`` when running host-free.

        Lazily constructed so the panel costs a DCC nothing until a scope is
        actually pushed, and kept for the panel's life so the host's own
        deliverer -- and therefore the port and the open tab -- survive.
        """
        if self._engine is None:
            return None
        if self._host_bridge is None:
            self._host_bridge = self._engine()
            self._bind_logger(self._host_bridge)
        return self._host_bridge

    def _adopt_host_deliverer(self) -> None:
        """Point the file bridge at the host's deliverer, so ONE server serves
        the panel.

        Done the moment the engine is known rather than when a scope is first
        pushed, and the difference is not cosmetic. Deferring it to the lazy
        host-bridge build was the first implementation and it was measurably
        wrong: a FILE push never reaches that build, so each source started its
        own server -- the file landed on one port while the footer, and the
        user's open tab, were still on the first. A push that reports success
        onto a page nobody is looking at is worse than one that fails.

        The HOST's deliverer wins rather than the reverse because it is a class
        attribute on its bridge, so it outlives this panel: that is what keeps
        the port and the open tab alive across panel reopens for the whole DCC
        session. Read off the CLASS, so no bridge is constructed to do it.
        """
        deliverer = getattr(self._engine, "deliverer", None) if self._engine else None
        if deliverer is not None:
            # An INSTANCE attribute, shadowing FilePreviewBridge's class-level
            # one: this panel's file bridge follows the host, and every other
            # user of that class keeps its own.
            self.bridge.deliverer = deliverer
        else:
            # Symmetric on the way out. A panel re-pointed at no host (or at
            # one with no deliverer) would otherwise keep publishing through
            # the PREVIOUS host's server -- the same disagreement between the
            # footer and the push, arrived at from the other direction.
            # Deleting the instance attribute re-exposes the class default
            # rather than inventing a new deliverer, so a server this panel
            # already started stays the one it uses.
            self.bridge.__dict__.pop("deliverer", None)
        # The Locomotion row follows the deliverer it now publishes through,
        # and the Sharing row shows a share that deliverer's server already has.
        self._apply_locomotion(
            KindFactory.read_value(self._param_widgets["LOCOMOTION"])
        )
        self._show_live_share()

    def _apply_locomotion(self, on) -> None:
        """The Locomotion row, applied at once rather than at the next push.

        The switch is the page's, read on every poll (``manifest.locomotion``),
        so a headset mid-session -- a share's guests included -- stops or
        starts going anywhere a second after the box changes, with no
        re-export: the running server takes it now, and the deliverer keeps it
        for every later publish, which re-applies it.
        """
        deliverer = self._deliverer()
        if deliverer is None:
            return
        deliverer.locomotion = bool(on)
        server = getattr(deliverer, "server", None)
        if server is not None:
            server.locomotion = bool(on)

    def _deliverer(self):
        """The one deliverer this panel's pushes land on, whatever the source.

        A single read, not a choice: :meth:`_adopt_host_deliverer` has already
        made the file bridge share the host's. Anything that picked a deliverer
        a second way here could disagree with the push, which is precisely the
        failure that made the footer describe a different server than the one
        being written to.
        """
        return getattr(self.bridge, "deliverer", None)

    def _server(self):
        """That deliverer's server, or ``None`` before anything started one."""
        deliverer = self._deliverer()
        return getattr(deliverer, "server", None) if deliverer else None

    def _bind_logger(self, bridge) -> None:
        """Route *bridge*'s logger into the panel's log pane.

        The base binds only ``self.bridge``'s logger, once, in its constructor.
        The host bridge is built later and is a different logger, so without
        this everything a scope push reports -- the sidecar outcome, the
        lightmap misses, the conversion's own errors -- would go to the DCC's
        script editor and the panel would look like it did nothing.
        """
        try:
            handler_cls = self.sb.registered_widgets.TextEditLogHandler
            logger = bridge.logger
            logger.hide_logger_name(True)
            logger.set_text_handler(handler_cls)
            logger.setup_logging_redirect(self.ui.txt000)
        except (AttributeError, RuntimeError):  # no redirect available
            pass

    def _sources(self) -> List[Tuple[str, str]]:
        """``(key, label)`` for every source this panel can offer right now.

        The host scopes come off the SHARED spec rather than a list written
        here: scope is the same control every other hand-off bridge offers, so
        reading the spec means this panel's vocabulary cannot fork from theirs.
        File on Disk is appended last. The combo persists by label, so neither
        the order nor a host's presence changes what a stored choice means.
        """
        entries: List[Tuple[str, str]] = []
        if self._engine is not None:
            for label, value in _BridgeParams.scope_spec().choices:
                entries.append((value, label))
        entries.append((FILE_SOURCE, "File on Disk"))
        return entries

    def list_template_modes(self) -> List[Tuple[str, str]]:
        """Sources, in the ``(template, mode)`` shape the base's combo reads."""
        return [(key, "") for key, _label in self._sources()]

    def _format_combo_label(self, template: str, mode: str) -> str:
        return dict(self._sources()).get(template, template)

    def _populate_sources(self) -> None:
        """Rebuild the Source combo after the host bridge changed.

        ``refresh_templates``, NOT ``cmb000_init``. The init hook is a
        Switchboard one-shot: it connects ``currentIndexChanged`` and adds the
        combo's menu chrome, so calling it again stacks a second connection and
        a second set of menu buttons. Measured before the fix -- one index
        change fired the change handler five times, and it would have grown
        with every host that re-pointed the panel. The base's own refresh does
        the repopulate half alone, which is all that changed here.

        The stored choice is re-applied afterwards, because it could not be
        before: the combo restores when the panel is built, and a host injects
        its scopes only after that (``launch(show=False)``, then ``engine =``).
        A stored scope missing from the list is skipped, and this repopulate
        then reset the combo to its first entry -- every session opened on
        Selected whatever was last picked. Every change is saved as it happens,
        so the store IS the last deliberate choice.
        """
        try:
            self.refresh_templates()
            restore = getattr(self.ui.cmb000, "perform_restore_state", None)
            if restore is not None:  # a combo not registered with a window
                restore(force=True)
        except Exception:  # noqa: BLE001 - a repopulate must never take the panel down
            self.sb.logger.debug("source combo repopulate failed", exc_info=True)

    def _active_source(self) -> str:
        pair = self._selected_template_mode()
        return pair[0] if pair else FILE_SOURCE

    def _relevant_param_keys(self) -> Optional[set]:
        """Which rows the active source actually answers.

        Explicit rather than file-driven: this panel renders no templates, and
        visibility must never depend on the absence of a file in the package
        dir. A file source exports nothing, so the export rows are not merely
        unused -- they would be lying.
        """
        keys = set(self.params_module.PARAMS)
        if self._active_source() == FILE_SOURCE:
            # The lighting recipe rides the scene sidecar, which a file push
            # never builds -- a row there would change nothing.
            return (
                keys - self.params_module.EXPORT_KEYS - self.params_module.LIGHTING_KEYS
            )
        return keys - self.params_module.FILE_KEYS

    # ------------------------------------------------------------------ status row
    def _build_status_row(self) -> None:
        """Bind the footer to a live description of what the page is showing.

        A push reports its outcome in the log, but the *standing* facts -- is
        anything watching, which version is live, on what port -- are state,
        not events, and an option box had nowhere to put them. This is the
        half of the feature that was previously invisible: 'no bake', 'bake
        not found' and 'nothing is watching' all render as the same dark room.
        """
        try:
            self._status = self.ui.footer.status_controller(
                resolver=self._status_text,
                default_text="No preview server running.",
            )
        except (AttributeError, RuntimeError):
            return  # a UI without a footer still works, it just says less
        # Who is watching changes with nothing done in the panel -- a guest
        # opens the link, the owner closes the tab -- so the line is re-read
        # while the panel shows. All of it is in memory.
        self._status_timer = QtCore.QTimer(self.ui)
        self._status_timer.setInterval(self.STATUS_REFRESH_MS)
        self._status_timer.timeout.connect(self._refresh_shown_status)
        self._status_timer.start()

    def _refresh_shown_status(self) -> None:
        if self.ui.isVisible():
            self._refresh_status()

    def _status_text(self) -> str:
        """One line describing the live preview, for the footer."""
        server = self._server()
        if server is None or not getattr(server, "url", ""):
            return "No preview server running."
        try:
            # Not manifest(): that reads the OpenXR runtime from the registry,
            # every time -- and the footer re-reads this every few seconds.
            version = server.version
            share = server.share_info()
        except Exception:  # noqa: BLE001 - the footer must never raise
            version, share = "?", None
        watching = "watching" if server.has_viewer() else "nothing watching"
        text = f"v{version} · {watching} · {server.url}"
        if share:
            guests = share["guests"]
            text += f" · shared at {share['url']} ({guests} guest{'s' * (guests != 1)})"
        elif self._share_step is not None:
            text += f" · sharing once {self._share_step.label} is enabled"
        return text

    def _refresh_status(self) -> None:
        """Re-run the footer resolver; a no-op on a UI without a footer."""
        if self._status is not None:
            try:
                self._status.update()
            except RuntimeError:  # the widget went away under us
                pass

    # ------------------------------------------------------------------ header actions
    def open_preview_page(self) -> None:
        """Open the live page in a browser, without paying for a push."""
        server = self._server()
        url = getattr(server, "url", "") if server is not None else ""
        if not url:
            self.panel_log(
                "Nothing is being served yet — push once to start the server.",
                "warning",
            )
            return
        webbrowser.open(url)

    def stop_server(self) -> None:
        """Stop serving and release the port -- ending any share."""
        server = self._server()
        if server is None:
            self.panel_log("No preview server is running.", "warning")
            return
        self._end_pending_share()  # the stop ends the share too
        server.stop()
        self.panel_log("Preview server stopped; the port is released.")
        self._refresh_status()

    # ------------------------------------------------------------------ sharing
    #: The Sharing row's option-box actions: ``(label, objectName, tooltip,
    #: handler)``. On the row rather than in the header menu, beside the switch
    #: they act on.
    SHARING_ACTIONS = (
        (
            "Share Now",
            "btn_share_now",
            "Bring the link up now, without a push -- and try again after a "
            "share failed. Picks Auto when the row is Off.",
            "share_link",
        ),
        (
            "Copy Link",
            "btn_copy_share_link",
            "Copy the live link to the clipboard -- bringing it up first when "
            "the row is on and it is not up.",
            "copy_share_link",
        ),
        (
            "Stop Sharing",
            "btn_stop_sharing",
            "Take the link down and set the row to Off. Your own page and the "
            "server are untouched.",
            "stop_sharing",
        ),
    )

    def _build_sharing_row(self) -> None:
        """The Sharing row as the switch, with its actions on its option box.

        Not restored from the last session: a link is a door to this machine,
        and a session opens it only when asked -- a switch left on yesterday
        would otherwise share the first push of the next day unprompted.
        """
        row = self._param_widgets["SHARE_VIA"]
        row.restore_state = False
        menu = row.option_box.menu
        menu.setTitle("Sharing")
        menu.add_defaults_button = False
        for text, name, tip, handler in self.SHARING_ACTIONS:
            button = menu.add(
                "QPushButton", setText=text, setObjectName=name, setToolTip=tip
            )
            button.clicked.connect(getattr(self, handler))
        KindFactory.connect_changed(row, self._sharing_changed)

    def _sharing_choice(self) -> str:
        """The Sharing row: ``"off"``, ``"auto"`` or a provider."""
        return KindFactory.read_value(self._param_widgets["SHARE_VIA"]) or "off"

    def _show_live_share(self) -> None:
        """A share already up shows on the row, never Off beside a live link.

        The server outlives the panel -- a panel reopened in the same session,
        or a host bringing its own deliverer, can find one sharing. The row's
        change then reports it rather than sharing again.
        """
        server = self._server()
        info = server.share_info() if server is not None else None
        if info is not None and self._sharing_choice() == "off":
            self._write_param("SHARE_VIA", info["provider"])

    def _sharing_changed(self, choice) -> None:
        """The row, applied at once: a provider shares now, Off stops."""
        if (choice or "off") == "off":
            self._unshare(announce_idle=False)
        else:
            self._share(choice, interactive=True)

    def share_link(self) -> None:
        """Share Now: bring the link up without a push, or retry a failed one.

        With the row Off it picks Auto, which shares through the row's own
        change -- the row stays the one switch, and says what is shared.
        """
        choice = self._sharing_choice()
        if choice == "off":
            self._write_param("SHARE_VIA", "auto")
        else:
            self._share(choice, interactive=True)

    def copy_share_link(self) -> None:
        """Copy Link: the live link to the clipboard, and to the log.

        With the row on and its link not up -- a share that failed, or one
        still waiting on a step -- it shares instead, which copies the link as
        it arrives or says what it waits on. Only Off has nothing to copy.
        """
        server = self._server()
        info = server.share_info() if server is not None else None
        if info is not None:
            self.panel_log(f"Share link: {info['url']}{self._copy(info['url'])}.")
            return
        choice = self._sharing_choice()
        if choice == "off":
            self.panel_log(
                "Nothing is being shared -- pick a provider in the Sharing row.",
                "warning",
            )
            return
        self._share(choice, interactive=True)

    @staticmethod
    def _copy(text: str) -> str:
        """*text* on the clipboard; the phrase to log after it, or ``""``."""
        try:
            from qtpy import QtWidgets

            QtWidgets.QApplication.clipboard().setText(text)
            return " -- copied to the clipboard"
        except Exception:  # noqa: BLE001 - no clipboard is not a failed share
            return ""

    def _share_after_push(self) -> None:
        """With sharing on, a push keeps the link up and says where it is.

        The same link each time -- a guest's page picks the push up by itself,
        and a new link per push would strand everyone holding the last one. A
        share that dropped (its client exited) is brought back up. A share that
        cannot come up is logged, not put in a dialog: a push is not the moment
        to interrupt, and the next push tries again.
        """
        choice = self._sharing_choice()
        if choice == "off":
            return
        server = self._server()
        info = server.share_info() if server is not None else None
        if info is not None:
            # The guest tabs open right now (polled within the viewer timeout)
            # -- a push resets nothing, so a bare "0" only read as stuck.
            guests = info["guests"]
            watching = (
                f"({guests} guest{'s' * (guests != 1)} watching)"
                if guests
                else "-- no guest has it open right now"
            )
            self.panel_log(f"Live at {info['url']} for guests too {watching}.")
            return
        self._share(choice, interactive=False)

    def _share(self, choice: str, interactive: bool) -> None:
        """Share the preview through *choice*, and report the link.

        The provider is settled first, the way a KTX2 push settles its
        encoder: a missing tunnel client is OFFERED (cloudflared downloads),
        never a dead end in a log line -- when *interactive*; a push's share
        asks nothing and logs what is missing instead. A provider that cannot
        produce a link -- a firewall that blocks the client -- says so, first
        line the next step, in a dialog when *interactive*; the client's own
        output follows in the log. A share already up through a fitting
        provider is reported, not restarted; one through another provider is
        replaced.

        The share runs off the UI thread (:class:`_Worker`): a provider takes
        seconds to bring a link up, and a quick tunnel's new name 6-18 s more
        to resolve, which on the UI thread froze the panel -- and the DCC
        hosting it -- for the whole wait. A provider that stops on a one-time
        step in a browser (Tailscale, until the tailnet enables Funnel) is
        offered (:meth:`_offer_step`) and waited on in the background, the
        panel free meanwhile: the step is a person's, and once it is taken the
        link arrives by itself (:meth:`_share_done`). Asked again while it
        waits, the panel names the step again; asked for another provider, it
        ends that wait and shares through the one asked for.
        """
        if self._share_pending:
            if self._share_step is None:
                if interactive:
                    self.panel_log("A link is already being opened.", "warning")
                return
            if choice in (self._share_choice, self._share_provider):
                self._offer_step(self._share_step, interactive, waiting=True)
                return
            self._unshare(announce_idle=False)  # another provider: that wait ends
        server = self._server()
        info = server.share_info() if server is not None else None
        if info is not None:
            if choice == "auto" or info["provider"] == choice:
                self.panel_log(f"Already shared at {info['url']}.")
                return
            server.unshare()
        provider = ptk.ShareTunnel.settle(
            choice,
            prompt=self.sb.confirm if interactive else (lambda _question: False),
            refused=lambda text: self._refused(f"Not shared: {text}", interactive),
            installed=lambda path: self.sb.message_box(
                f"Installed the tunnel client: <hl>{path}</hl>"
            ),
        )
        if provider is None:
            return
        self._share_pending = True
        self._share_choice, self._share_provider = choice, provider
        stops = self._share_stops
        reported = {}  # the provider's step, set on the share's own thread
        job = _Worker(
            lambda: self.bridge.share(
                provider=provider,
                on_step=lambda step: reported.setdefault("step", step),
            ),
            name="webxr-preview-share",
        )
        # The tick pumps the host's loop by the host's own input policy -- a
        # DCC admits no clicks mid-slot -- so the panel repaints and the host
        # stays responsive without a raw processEvents bypassing that policy.
        with self.sb.progress(text="Sharing: opening the link…") as tick:
            while not job.done and "step" not in reported:
                tick()
                job.wait(0.05)
        if job.done:
            self._share_done(job, stops, interactive, waited=False)
            return
        self._share_step = reported["step"]
        self._refresh_status()
        self._offer_step(self._share_step, interactive, waiting=True)
        job.when_done(
            self.ui, lambda: self._share_done(job, stops, interactive, waited=True)
        )

    def _share_done(self, job, stops: int, interactive: bool, waited: bool) -> None:
        """Report a share's outcome on the UI thread -- at once, or when one
        that *waited* on a step in the background ends.

        Silent when a stop ended it (*stops* is the count it began with): the
        stop has already said so, and a later share may be under way.
        """
        if self._share_stops != stops:
            return
        self._clear_share_wait()
        self._refresh_status()
        try:
            info = job.result()
        except ptk.ShareTunnel.StepRequired as step:
            if not waited:  # stopped at the step at once: offer it
                self._offer_step(step, interactive, waiting=False)
                return
            # Ran out, or the client stopped waiting: either way, not taken.
            self.panel_log(
                f"Sharing stopped waiting on {step.label}'s one-time step. "
                f"Enable it at {step.url}, then Share Now -- or just push again.",
                "warning",
            )
            return
        except (OSError, RuntimeError) as error:  # incl. TimeoutError
            detail = str(error)
            self.panel_log(f"Sharing failed:\n{detail}", "error")
            if interactive:
                self.sb.message_box(detail.splitlines()[0])
            return
        copied = self._copy(info["url"])
        reach = "anyone with it" if info["public"] else "your tailnet only"
        self.panel_log(
            f"Shared, view-only, at {info['url']}{copied}. Opens for "
            f"{reach}; every push reaches it."
        )
        if info.get("alias_error"):
            self.panel_log(
                f"The stable alias was not updated ({info['alias_error']}); "
                f"send the link above instead.",
                "warning",
            )

    def _offer_step(self, step, interactive: bool, waiting: bool) -> None:
        """A provider stopped on a one-time step in a browser -- Tailscale,
        before the tailnet enables Funnel -- offered, never a dead end.

        *waiting*: the share still waits on the step, so the link comes up by
        itself once it is taken; otherwise Share Now, or the next push, tries
        again. The page opens on a yes; a push's share asks nothing and logs
        the page instead.
        """
        then = (
            "the link comes up by itself once it is enabled"
            if waiting
            else "then Share Now -- or just push again"
        )
        self.panel_log(
            f"{step.label} needs a one-time step first: enable it at "
            f"{step.url} -- {then}.",
            "warning",
        )
        follows = ", and the link follows by itself" if waiting else ""
        if interactive and self.sb.confirm(
            f"{step.label} is not enabled for your network yet -- it takes one "
            f"step in your browser{follows}. Open that page now?",
            yes="Open Page",
            no="Not Now",
        ):
            webbrowser.open(step.url)

    def _refused(self, text: str, interactive: bool = True) -> None:
        """A tool is missing and was not installed: the fix-shaped message in
        the log -- where its install page stays, as a link -- and, when
        *interactive*, in a dialog too, which is gone in seconds."""
        self.panel_log(text, "warning")
        if interactive:
            self.sb.message_box(text)

    def stop_sharing(self) -> None:
        """Stop Sharing: the row to Off, which takes the link down."""
        if self._sharing_choice() != "off":
            self._write_param("SHARE_VIA", "off")  # its change unshares
        else:
            self._unshare()

    def _unshare(self, announce_idle: bool = True) -> None:
        """Take the link down; the owner's page and server are untouched.

        Unshares even when nothing reads as shared: a share whose client died
        on its own reads that way while it still holds its guest listener and
        an alias sending guests to the dead link; and a share still opening --
        waiting on a step, above all -- ends now. *announce_idle* says so when
        there was nothing to stop -- right for Stop Sharing pressed, noise for
        the row turned Off.
        """
        opening = self._end_pending_share()
        server = self._server()
        shared = server is not None and server.share_info() is not None
        if server is not None:
            server.unshare()
        if shared:
            self.panel_log("Stopped sharing; the link no longer opens.")
        elif opening:
            self.panel_log("Stopped the link being opened.")
        elif announce_idle:
            self.panel_log("Nothing is being shared.", "warning")
        self._refresh_status()

    def _end_pending_share(self) -> bool:
        """Forget a share still opening, which the stop about to run ends
        (:meth:`_share_done` then stays silent); whether there was one."""
        opening = self._share_pending
        self._share_stops += 1
        self._clear_share_wait()
        return opening

    def _clear_share_wait(self) -> None:
        """No share opening: not pending, and no row choice, provider or step
        it was opened for (a share waiting on its step is named by these)."""
        self._share_pending = False
        self._share_choice: Optional[str] = None
        self._share_provider: Optional[str] = None
        self._share_step = None

    # ------------------------------------------------------------------ public hand-off
    def set_source_file(self, path: str) -> None:
        """Pre-fill Source File and select the file source.

        The hand-off point for a host that already has a file to show -- an
        exporter that just wrote a GLB, say. Selecting the source too, because
        filling a field the active source does not read would look like the
        panel ignored the request.
        """
        edit = self._source_edit()
        if edit is not None:
            edit.setText(path or "")
        self._select_source(FILE_SOURCE)

    def _prompt_for_source(self) -> str:
        """Ask for the file to preview, and remember the answer. "" if declined.

        An empty field is not an error state, it is the first push -- the
        panel opens with nothing chosen. Answering that with "pick a file
        first" makes the user go and do the dialog's job by hand, on the one
        press where what they want is unambiguous. The choice is written back
        into the field, so the next push is the one-press loop this panel is
        for and the file is visible rather than remembered.
        """
        from uitk import BrowseOption

        edit = self._source_edit()
        option = edit.option_box.find_option(BrowseOption) if edit else None
        if option is None:  # a row built without its browse button
            self.panel_log("Pick a Source File first.", "warning")
            return ""
        # The ROW's own browse, not a second dialog beside it: the filter, the
        # title and the folder it opens on are declared once, on the field, so
        # the two ways into the same choice cannot answer differently. It
        # writes the pick back into the field itself.
        option.browse()
        return self._source_text()

    def _source_edit(self):
        """The Source File field's inner line edit; None before it is built."""
        return getattr(self._param_widgets.get("SOURCE_FILE"), "_line_edit", None)

    def _source_text(self) -> str:
        """Whatever that field holds, for anchoring the dialog. "" if empty."""
        edit = self._source_edit()
        return str(edit.text()).strip() if edit is not None else ""

    def _select_source(self, key: str) -> None:
        combo = self.ui.cmb000
        for i in range(combo.count()):
            data = combo.itemData(i)
            if isinstance(data, (tuple, list)) and data and data[0] == key:
                combo.setCurrentIndex(i)
                # Saved even when the index did not move -- File on Disk is
                # the only entry before a host arrives, so selecting it emits
                # nothing. Unsaved, the host's repopulate would re-apply last
                # session's scope over a file this call just handed over.
                state = getattr(self.ui, "state", None)
                if state is not None:
                    state.save(combo)
                return

    # ------------------------------------------------------------------ GLB rows
    @staticmethod
    def _glb_options(values: Dict[str, Any]) -> Dict[str, Any]:
        """The Scene Exporter rows of collected *values*, keyed as the push
        takes them.

        ``{row key: combo value}`` (:attr:`pythontk.ExportProfile.GLB_ROWS`) --
        handed to ``push(glb_options=...)``, which resolves them with the Scene
        Exporters' own methods. Nothing is interpreted here.
        """
        return {
            row: values[key] for key, row in _params.GLB_KEYS.items() if key in values
        }

    # ------------------------------------------------------------------ preflight
    def _texture_tool_ready(self, glb_options: Dict[str, Any]) -> bool:
        """Settle a missing KTX2 encoder BEFORE the push, offering the install.

        Only KTX2 needs an external tool. The bridge already refuses a KTX2
        push without ``toktx``, eagerly, before it pays for the export -- but it
        refuses by RAISING with an install URL, and a panel control that
        dead-ends in a URL is what the Scene Exporter's own KTX2 row stopped
        doing. A missing tool means *offer the managed install*, never *abort
        and go read a log*.

        Gated on the resolved container, read the way the push will read it
        (``ExportRun.for_glb``), so both KTX2 entries -- alone and
        with its twin -- ask and nothing else does: WebP needs no tool, and
        probing for one the push will not use would ask about a control the
        user never touched.
        """
        run, _notes = ptk.ExportRun.for_glb(glb_options)
        if run.texture_file_type != "ktx2":
            return True
        # Declined, or the install failed: the refusal is the fix-shaped
        # message naming the manual install, so it IS the dialog -- and stays
        # in the log, where its install page is a link.
        return ptk.ImgUtils.settle_ktx2_encoder(
            prompt=self.sb.confirm,
            refused=self._refused,
            installed=lambda path: self.sb.message_box(
                f"Installed KTX-Software (toktx): <hl>{path}</hl>"
            ),
        )

    # ------------------------------------------------------------------ b000 — the push
    def b000(self) -> None:
        """Build the deliverable for the active source and publish it."""
        values = self.collect_param_values()
        source = self._active_source()

        # Every row, every push: the panel IS the answer, so an untouched row
        # says "the Scene Exporter's default" rather than leaving the
        # deliverer's own setting in force.
        glb_options = self._glb_options(values)
        if not self._texture_tool_ready(glb_options):
            return

        # An explicit list every push, never None: the checkboxes ARE the
        # answer, and None means "leave the server's set alone" -- which would
        # make an unticked box unable to turn a script back off.
        scripts = list(values.get("VIEWER_SCRIPTS") or [])
        # The panel is the answer for the switch too, whatever set it last.
        self._apply_locomotion(values.get("LOCOMOTION", True))

        try:
            if source == FILE_SOURCE:
                outcome = self._push_file(values, glb_options, scripts)
            else:
                outcome = self._push_scope(source, values, glb_options, scripts)
        except Exception:
            self.bridge.logger.error("Preview raised:\n" + traceback.format_exc())
            return

        if outcome is None:
            return  # the step settled the run and has already said why
        self._report(*outcome)
        self._share_after_push()

    def _push_file(self, values, glb_options, scripts):
        """Push the chosen file. ``None`` when the run was settled here."""
        path = str(values.get("SOURCE_FILE") or "").strip()
        if not path:
            path = self._prompt_for_source()
            if not path:
                return None  # the dialog was dismissed; nothing to say
        if not os.path.isfile(path):
            self.panel_log(f"Source file not found: {path}", "error")
            return None

        with self.sb.progress(text="Preview: publishing…") as tick:
            result = self.bridge.push(
                objects=[path],
                scope=FILE_SOURCE,
                open_browser="auto",
                glb_options=glb_options,
                scripts=scripts,
                progress=lambda message: tick(text=message),
                EMBED_TEXTURES=bool(values.get("EMBED_TEXTURES", True)),
            )
        return result, [
            f"Source: {os.path.basename(path)}",
            self._timing_line(self.bridge, result),
        ]

    def _push_scope(self, scope, values, glb_options, scripts):
        """Export *scope* from the host and push it."""
        bridge = self._host()
        if bridge is None:
            self.panel_log(
                "No host is connected, so there is no scene to read. Pick "
                "'File on Disk' as the Source.",
                "warning",
            )
            return None

        # Resolved here rather than left to push(), so an empty result can be
        # REPORTED. Pushing blind collapses "nothing selected", "the scene is
        # empty" and "the export failed" into one message, and the first two
        # are the user's own next action.
        objects = bridge.scope_objects(scope)
        if not objects:
            self.panel_log(self.empty_scope_message(scope), "warning")
            return None

        with self.sb.progress(text="Preview: exporting…") as tick:
            result = bridge.push(
                objects=objects,
                scope=scope,
                open_browser="auto",
                glb_options=glb_options,
                scripts=scripts,
                progress=lambda message: tick(text=message),
                EMBED_TEXTURES=bool(values.get("EMBED_TEXTURES", True)),
                INCLUDE_ANIMATION=bool(values.get("INCLUDE_ANIMATION", False)),
                SCENE_SIDECAR=bool(values.get("SCENE_SIDECAR", True)),
            )
        # Reported, not left to the log: read nothing / matched nothing /
        # switched off all render the SAME unlit preview, and a bake whose maps
        # were not found renders exactly like no bake. Without these the
        # feature cannot be debugged from the panel.
        return result, [
            bridge.sidecar_summary(result),
            bridge.lightmap_summary(result),
            self._timing_line(bridge, result),
        ]

    @staticmethod
    def _timing_line(bridge, result) -> str:
        """Where the push's time went (``PreviewBridge.timing_summary``).

        The question after every slow push, answered by the push: FBX2glTF's
        share is moved by what the scene exports, the rest by the build. Read
        through ``getattr`` because it is a report rather than the push -- a
        pythontk that predates it costs the line, never the preview.
        """
        summary = getattr(bridge, "timing_summary", None)
        return summary(result) if callable(summary) else ""

    def _report(self, result: Optional[Dict[str, Any]], extra: List[str]) -> None:
        """Say what the page is showing now, or why it is not."""
        if not result:
            self.panel_log("Preview failed — see the log above for details.", "error")
            return
        lines = [f"Preview v{result['version']} live at {result['url']}", *extra]
        for line in lines:
            if line:
                self.panel_log(line)
        self._refresh_status()


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    from extapps.webxr_preview.launcher import WebXrPreviewUI

    WebXrPreviewUI().show(pos="screen", app_exec=True)
