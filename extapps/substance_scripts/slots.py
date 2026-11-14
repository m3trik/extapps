# !/usr/bin/python
# coding=utf-8
"""Slots for the standalone Substance Scripts panel.

A DCC-agnostic sibling of the host Substance Bridge panel: both subclass uitk's
:class:`ParamPanelSlots` (script combo, parameter rows, presets, log routing),
but this one runs a script on a picked **mesh file** or a **project** instead
of a scene selection -- a standalone panel (``launcher.py``), so it runs
outside any DCC too. The engine is :class:`SubstanceScripts` (this package's
vendored Painter engine).

The scripts are the engine's: the bundled New Project, Update Mesh, Bake
Lighting to Diffuse, Bake Mesh Maps and Export Textures, and a person's own
(``ptk.ScriptTemplate.user_dir("substance")``, the folder every host's
Substance Bridge reads too), where one named like a bundled script runs in its
place. The rows only a host fills (:data:`HOST_ROWS`: its Scope, its textures,
its bake source) are not shown here.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

import pythontk as ptk
from qtpy import QtCore, QtWidgets
from uitk import ParamPanelSlots

from extapps import DOCS_BASE_URL

from . import parameters as _params
from ._substance_scripts import SubstanceScripts

#: The rows only a host's bridge fills, because they name its scene: hidden
#: here (a script that reads one still runs, on the mesh file).
HOST_ROWS = ("SCOPE", "CARRIER", "BAKE_SOURCE_SET", "PAINTER_INCLUDE_TEXTURES", "PAINTER_TEXTURE_AFFIX")


class SubstanceScriptsSlots(ParamPanelSlots):
    """Switchboard slots wired to ``substance_scripts.ui``.

    Runs the chosen script in Painter through :class:`SubstanceScripts`, on the
    Mesh File (a script on a mesh) or a project, and follows its job there off
    the UI thread.
    """

    UI_NAME = "substance_scripts"
    #: Saved data: the panel's presets, per script.
    PRESETS_ROOT = Path("extapps/substance_scripts")
    LOG_TAG = "substance_scripts"
    TRANSIENT_OUTPUT_MODES = (ptk.SEND_TO, ptk.ROUND_TRIP)
    OUTPUT_DIR_TOOLTIP = (
        "Directory a script's own files fall back to (its ``OUTPUT_DIR``).\n\n"
        "Leave blank and they go to a temp folder per run. The project itself\n"
        "is saved where Project names it, and Export Textures writes to its\n"
        "own Export Dir."
    )
    DOCS_URL = DOCS_BASE_URL + "docs/substance_scripts.md"
    DOCS_LABEL = "Detailed docs (scripts, finding Painter, the plugin)"

    # Install in Painter / Uninstall from Painter: uitk's, from the engine's RPC_PLUGIN.
    HEADER_MENU_ITEMS = ParamPanelSlots.HEADER_MENU_ITEMS + (
        (
            "Cancel Script",
            "btn_cancel_script",
            "Ask Painter to stop the running script: a queued one never starts, a bake "
            "under way stops.",
            "cancel_script",
        ),
    )

    HELP_SPEC = {
        "title": "Substance Scripts",
        "body": "Run a Substance 3D Painter script, a built-in one or your own: "
        "each is a Python file Painter runs as written. No DCC required.",
        "steps": [
            "Pick a script (its description is logged).",
            "For <b>New Project</b> or <b>Update Mesh</b>, pick a <b>Mesh File</b>; "
            "a script on a project runs on <b>Project</b>, else the one open in Painter.",
            "Set its rows; <b>Painter</b> picks where it runs (Auto: the Painter "
            "holding the project, else a new one).",
            "Click <b>Run in Painter</b>: the log follows the script to its end.",
        ],
        "sections": [
            (
                "Your scripts",
                [
                    "The script list's menu opens <b>My Scripts</b>; <b>Copy to My "
                    "Scripts</b> copies the selected one there to edit, and your copy "
                    "runs in its place. The Maya and Blender Substance Bridges list "
                    "them too.",
                    "A script reads its values from <code>args</code>; a "
                    "<code># Rows: __KEY__</code> line shows panel rows, a "
                    "<code># Row: __KEY__ int 4 \"Label\"</code> line declares its own.",
                ],
            ),
        ],
        "notes": [
            "<b>Your Painter</b>: <i>Install in Painter</i> (Utilities) puts the "
            "<i>substance_rpc</i> plugin in Painter's plugins folder, ticked in its "
            "<i>Python</i> menu; a Painter you open then runs a script only when you "
            "click Run, and its edits are in Painter's undo history, an entry per step named for the script. Untick it there "
            "to switch it off. A Painter this panel launches loads the plugin on its own.",
            "Unlike the Maya / Blender <b>Substance Bridge</b>, no scene is "
            "exported: the mesh file is used as it is (no staged textures, no bake source).",
        ],
    }

    def __init__(self, switchboard, **kwargs):
        self._initial_mesh: str = kwargs.get("mesh_path", "") or ""
        self._mesh_edit: Optional[QtWidgets.QLineEdit] = None
        self._running = None  # the send whose job the panel follows
        self._starting = False  # a send waiting on Painter (starting, opening the project)
        super().__init__(switchboard)
        self._build_mesh_row()
        self.refresh_painters()

    # ------------------------------------------------------------------
    # Required base-class hooks
    # ------------------------------------------------------------------

    @property
    def params_module(self):
        return _params.Parameters

    @property
    def template_dir(self) -> Path:
        return SubstanceScripts.TEMPLATE_DIR

    @property
    def template_dirs(self) -> Tuple[Path, ...]:
        """The engine's own folders (the person's scripts, then the bundled
        ones), so the panel reads the very file the engine runs."""
        return SubstanceScripts.template_dirs()

    #: The engine class: its ``RPC_PLUGIN`` gives the panel *Install in Painter*.
    bridge_class = SubstanceScripts

    def make_bridge(self) -> SubstanceScripts:
        return SubstanceScripts()

    def list_template_modes(self) -> List[Tuple[str, str]]:
        return SubstanceScripts.list_template_modes()

    def select_initial_template_index(self, pairs: List[Tuple[str, str]]) -> int:
        """Prefer 'new_project (send_to)', else the first entry."""
        pref = ("new_project", ptk.SEND_TO)
        return pairs.index(pref) if pref in pairs else 0

    def _relevant_param_keys(self) -> Optional[set]:
        """The script's rows but for the ones only a host fills (:data:`HOST_ROWS`)."""
        keys = super()._relevant_param_keys()
        return None if keys is None else set(keys) - set(HOST_ROWS)

    def _on_template_changed(self) -> None:
        super()._on_template_changed()
        self.refresh_painters()

    # ------------------------------------------------------------------
    # The Mesh File row (this panel's analogue of a DCC selection)
    # ------------------------------------------------------------------

    def _build_mesh_row(self) -> None:
        """Insert a 'Mesh File' line edit + browse at the top of grp_process."""
        layout = self.ui.grp_process.layout()
        row = QtWidgets.QWidget(self.ui.grp_process)
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)

        label = QtWidgets.QLabel("Mesh File:", row)
        label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        edit = QtWidgets.QLineEdit(row)
        edit.setPlaceholderText("(the mesh for New Project / Update Mesh)")
        edit.setMinimumHeight(19)
        edit.setMaximumHeight(19)
        edit.setToolTip(
            "The mesh a script on a mesh runs on (FBX, OBJ, Alembic, glTF, PLY, "
            "USD): New Project makes a project from it, Update Mesh reloads it "
            "in the Painter whose project was made from it."
        )
        if self._initial_mesh:
            edit.setText(self._initial_mesh)
        browse = QtWidgets.QPushButton("...", row)
        browse.setFixedWidth(22)
        browse.setMinimumHeight(19)
        browse.setMaximumHeight(19)
        browse.clicked.connect(self._pick_mesh)

        hbox.addWidget(label)
        hbox.addWidget(edit, 1)
        hbox.addWidget(browse)
        layout.insertWidget(0, row)
        self._mesh_edit = edit

    def _pick_mesh(self) -> None:
        current = self.resolved_mesh_path()
        try:
            paths = self.sb.file_dialog(
                file_types=SubstanceScripts.mesh_types(),
                title="Select a mesh file for the script:",
                start_dir=os.path.dirname(current) if current else str(Path.home()),
                allow_multiple=False,
            )
        except Exception:  # noqa: BLE001
            paths = None
        if not paths:
            return
        chosen = paths[0] if isinstance(paths, (list, tuple)) else paths
        if chosen and self._mesh_edit is not None:
            self._mesh_edit.setText(chosen)

    def resolved_mesh_path(self) -> str:
        return "" if self._mesh_edit is None else self._mesh_edit.text().strip()

    def set_mesh_path(self, path: str) -> None:
        """Pre-fill the Mesh File field (a host hands it a file it exported)."""
        self._initial_mesh = path or ""
        if self._mesh_edit is not None:
            self._mesh_edit.setText(self._initial_mesh)

    # ------------------------------------------------------------------
    # Painters
    # ------------------------------------------------------------------

    def refresh_painters(self) -> None:
        """The Painter row's entries: Auto, New Painter, and every running
        Painter serving the plugin, by the project it holds."""
        widget = self._param_widgets.get("PAINTER")
        if widget is not None:
            # By the Painter's id, never its row: the list is the Painters
            # running now, so a saved row would land on another one.
            widget.restore_by = "data"
            self._set_param_choices("PAINTER", SubstanceScripts.painter_choices())

    def cancel_script(self) -> None:
        """Ask Painter to stop the script this panel is following."""
        if self._running is None:
            self.bridge.logger.info("No script is running in Painter.")
            return
        self.bridge.cancel(self._running)

    # ------------------------------------------------------------------
    # b000 -- the run
    # ------------------------------------------------------------------

    def b000(self):
        """Run the chosen script in Painter, then follow its job off the UI thread."""
        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning("No script chosen. Pick one from the dropdown above.")
            return None
        template, mode = pair
        if self._starting:
            self.bridge.logger.warning("Painter is still starting or opening the project: Run again once the script is queued.")
            return None
        if self._running is not None:
            # The panel follows one job: a second would take its place, and
            # Cancel Script would reach the wrong one.
            self.bridge.logger.warning(
                "A script is still running in Painter: Run again when it ends, or stop it first (Cancel Script)."
            )
            return None
        meta = SubstanceScripts.parse_template(SubstanceScripts.template_path(template))
        mesh = None
        if meta["WORKS_ON"] in ("new", "mesh"):
            mesh = self.resolved_mesh_path()
            if not mesh:
                self.bridge.logger.warning("Pick a Mesh File first (the '...' button next to it).")
                return None
            if not os.path.isfile(mesh):
                self.bridge.logger.error(f"Mesh file not found: {mesh}")
                return None

        output_dir = self.require_output_dir(mode)
        if output_dir is None:
            return None
        params = self.collect_param_values()
        label = SubstanceScripts.label(template)
        on = os.path.basename(mesh) if mesh else (params.get("PAINTER_PROJECT") or "the open project")
        self.bridge.logger.info(f"--- {label} on {on} ---")
        try:
            with self.sb.progress(text=f"Working: {label}"):
                result = self.bridge.send(
                    mesh=mesh,
                    template=template,
                    mode=ptk.SEND_TO,  # queued here; the wait below is off the UI thread
                    target=params.get("PAINTER") or "auto",
                    params=params,
                    background=self._in_background,
                    on_queued=lambda queued: self._queued(queued, label),
                    output_dir=output_dir or None,
                )
        except Exception:
            self.bridge.logger.error("Engine raised:\n" + traceback.format_exc())
            return None
        if result and result.get("pending"):
            self._starting = True  # until _queued
            return None  # Painter is starting or opening the project: _queued follows
        return self._queued(result, label)

    def _in_background(self, work, then):
        """The engine's waits (a launched Painter serving, a project opening)
        off the UI thread; *then* gets what *work* returned, on it."""
        task = self.sb.BackgroundTask(work, "substance-deliver")
        task.when_done(self.ui, lambda: then(task.result()))

    def _queued(self, result, label):
        """Follow the queued script's job, when there is one."""
        self._starting = False
        if result and result.get("job"):
            return self._watch(result, label)
        return None

    def _watch(self, result, label):
        """Follow the job off the UI thread (the engine's ``follow`` says
        nothing there), then say how it ended, on the UI thread."""
        self._running = result
        footer = getattr(self.ui, "footer", None)
        if footer is not None:
            footer.start_progress(text=f"{label}: running in Painter…")
        task = self.sb.BackgroundTask(lambda: SubstanceScripts.follow(result), "substance-script")

        def done() -> None:
            if self._running is result:
                self._running = None
            status = self.bridge.conclude(task)
            if footer is not None:
                footer.finish_progress(f"{label}: {status.get('state', 'failed')} in Painter.")
            self.refresh_painters()

        task.when_done(self.ui, done)
        return task
