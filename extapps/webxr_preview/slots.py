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
import traceback
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pythontk as ptk
from uitk.bridge import BridgeSlotsBase, Parameters as _BridgeParams

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
            "Set the delivery options (textures, format, viewer scripts).",
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
        self._initial_source_file: str = kwargs.get("source_file", "") or ""
        super().__init__(switchboard)
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

    def _deliverer(self):
        """The one deliverer this panel's pushes land on, whatever the source.

        A single read, not a choice: :meth:`_adopt_host_deliverer` has already
        made the file bridge share the host's. Anything that picked a deliverer
        a second way here could disagree with the push, which is precisely the
        failure that made the footer describe a different server than the one
        being written to.
        """
        return getattr(self.bridge, "deliverer", None)

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
        File on Disk is appended last, which also keeps the addition
        append-only for anyone whose combo index is already stored.
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
        """
        try:
            self.refresh_templates()
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
            return keys - self.params_module.EXPORT_KEYS
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
            pass  # a UI without a footer still works, it just says less

    def _status_text(self) -> str:
        """One line describing the live preview, for the footer."""
        deliverer = self._deliverer()
        server = getattr(deliverer, "server", None) if deliverer else None
        if server is None or not getattr(server, "url", ""):
            return "No preview server running."
        try:
            version = server.manifest().get("version", "?")
        except Exception:  # noqa: BLE001 - the footer must never raise
            version = "?"
        watching = "watching" if server.has_viewer() else "nothing watching"
        return f"v{version} · {watching} · {server.url}"

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
        deliverer = self._deliverer()
        server = getattr(deliverer, "server", None) if deliverer else None
        url = getattr(server, "url", "") if server is not None else ""
        if not url:
            self.panel_log(
                "Nothing is being served yet — push once to start the server.",
                "warning",
            )
            return
        webbrowser.open(url)

    def stop_server(self) -> None:
        """Stop serving and release the port."""
        deliverer = self._deliverer()
        server = getattr(deliverer, "server", None) if deliverer else None
        if server is None:
            self.panel_log("No preview server is running.", "warning")
            return
        server.stop()
        self.panel_log("Preview server stopped; the port is released.")
        self._refresh_status()

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
                return

    # ------------------------------------------------------------------ preflight
    def _texture_tool_ready(self, texture_format: str) -> bool:
        """Settle a missing KTX2 encoder BEFORE the push, offering the install.

        Only KTX2 needs an external tool. The bridge already refuses a KTX2
        push without ``toktx``, eagerly, before it pays for the sidecar and
        lightmap passes -- but it refuses by RAISING with an install URL, and a
        panel control that dead-ends in a URL is what the Scene Exporter's own
        KTX2 row stopped doing. A missing tool means *offer the managed
        install*, never *abort and go read a log*.

        Gated on the choice: WebP needs nothing, and probing for a tool the
        push will not use would ask about a control the user never touched.
        """
        if str(texture_format).upper() != "KTX2":
            return True
        try:
            installed = ptk.ImgUtils.ensure_ktx2_encoder(
                prompt=lambda question: (
                    self.sb.message_box(question, "Yes", "No") == "Yes"
                )
            )
        except FileNotFoundError as error:
            # Declined, or the install failed. The error is the fix-shaped one
            # naming the manual install, so it IS the message.
            self.sb.message_box(str(error))
            return False
        if installed:
            self.sb.message_box(f"Installed KTX-Software (toktx): <hl>{installed}</hl>")
        return True

    # ------------------------------------------------------------------ b000 — the push
    def b000(self) -> None:
        """Build the deliverable for the active source and publish it."""
        values = self.collect_param_values()
        source = self._active_source()

        texture_format = values.get("TEXTURE_FORMAT", "WEBP")
        if not self._texture_tool_ready(texture_format):
            return

        # An explicit list every push, never None: the checkboxes ARE the
        # answer, and None means "leave the server's set alone" -- which would
        # make an unticked box unable to turn a script back off.
        scripts = list(values.get("VIEWER_SCRIPTS") or [])

        try:
            if source == FILE_SOURCE:
                outcome = self._push_file(values, texture_format, scripts)
            else:
                outcome = self._push_scope(source, values, texture_format, scripts)
        except Exception:
            self.bridge.logger.error("Preview raised:\n" + traceback.format_exc())
            return

        if outcome is None:
            return  # the step settled the run and has already said why
        self._report(*outcome)

    def _push_file(self, values, texture_format, scripts):
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
                texture_format=texture_format,
                scripts=scripts,
                progress=lambda message: tick(text=message),
                EMBED_TEXTURES=bool(values.get("EMBED_TEXTURES", True)),
            )
        return result, [f"Source: <hl>{os.path.basename(path)}</hl>"]

    def _push_scope(self, scope, values, texture_format, scripts):
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
                texture_format=texture_format,
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
        ]

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
