# !/usr/bin/python
# coding=utf-8
"""Slots for the Unity Scripts panel -- the one Unity panel, in every host.

A script manager for a Unity project: the template combo lists the built-in
C# scripts and the person's own (``ptk.ScriptTemplate.user_dir("unity")``; its
menu copies a built-in there to edit), the rows a script's header names are
shown, and **Run in Unity** runs it in the Unity editor that has the project
open, through the connection installed in that project
(:class:`~extapps.unity_scripts.unity_connection.UnityConnection`, installed,
updated and removed from the 'Unity Project' field's menu). What Unity reports
-- the script's lines, the Console's, the assets it made -- comes back to the
log.

A script that takes an asset is given the **Source**, copied into
``Assets/`` first: a picked model file, or, when a host that opened the panel
injected its Unity engine (:attr:`UnityScriptsSlots.engine` -- ``mtk.UnityBridge``
/ ``btk.UnityBridge``, the shape of the WebXR Preview's ``engine``), the
**current scene**, exported by the host's Scene Exporter with the host's
export rows. Which source is active changes *which bridge produces the
payload* and nothing else: the delivery and the run are this panel's one
chain either way, so the panel carries no per-host branch.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import Optional

import pythontk as ptk
from qtpy import QtCore, QtWidgets
from uitk import ParamPanelSlots

from . import parameters as _params
from .unity_connection import UnityConnection
from .unity_deliverer import UnityDeliverer


# Unity-importable model formats offered in the file picker.
_MODEL_FILE_TYPES = [
    "*.fbx",
    "*.obj",
    "*.usd",
    "*.usdc",
    "*.usda",
    "*.abc",
    "*.gltf",
    "*.glb",
    "*.ply",
]

#: Console message types read as the panel's log levels.
_CONSOLE_LEVELS = {"Error": "error", "Exception": "error", "Assert": "error", "Warning": "warning"}


class UnityScriptsSlots(ParamPanelSlots):
    """Switchboard slots wired to ``unity_scripts.ui`` via :class:`ParamPanelSlots`.

    Runs the selected script in the Unity project, after delivering its Source
    (a model file, or the scope of the scene of a host that injected its
    :attr:`engine`) when it takes one.
    """

    UI_NAME = "unity_scripts"
    PRESETS_ROOT = Path("extapps/unity_scripts")
    #: Saved data: the template folders the panel's presets were kept under
    #: before it ran scripts (the Unity Workflow's, the Unity Bridge's), and
    #: the script each one's presets now belong to (``None``: no successor).
    #: Read by whatever carries those presets in (``carry_presets``).
    FORMER_TEMPLATES = {"copy_to_assets": "SendToUnity", "manage_scripts": None}
    #: Saved names: the widgets built from it (``<tag>_output_dir``,
    #: ``<tag>_model`` and their recent lists) keep the spelling they shipped
    #: under, from when the panel was the Unity Workflow.
    LOG_TAG = "unity_workflow"
    TEMPLATE_EXTENSION = UnityDeliverer.TEMPLATE_EXTENSION

    # The required path row IS the Unity project (folder with Assets/).
    REQUIRE_OUTPUT_DIR = True
    OUTPUT_DIR_LABEL = "Unity Project:"
    OUTPUT_DIR_PLACEHOLDER = "(folder containing Assets/)"
    OUTPUT_DIR_TOOLTIP = (
        "Path to the target Unity project -- the folder that contains the\n"
        "'Assets/' directory. Scripts run in the Unity editor that has it open,\n"
        "through the connection its menu installs; a Source is copied into\n"
        "Assets/<subfolder> first."
    )

    #: The script the combo opens on.
    DEFAULT_SCRIPT = "SendToUnity"

    HEADER_MENU_ITEMS = (
        ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
        (
            "Cancel Running Script",
            "btn_cancel_script",
            "Withdraw the script sent to Unity, or ask it to stop between steps.",
            "cancel_script",
        ),
    )

    HELP_SPEC = {
        "title": "Unity Scripts",
        "body": "Run built-in and your own C# editor scripts in a Unity project, with "
        "each script's settings as rows here. A script runs in the Unity editor "
        "that has the project open, as one undo step; what it and the Console "
        "report comes back to this log.",
        "steps": [
            "Set the <b>Unity Project</b> (the folder holding Assets/), and "
            "<b>Install Connection</b> from the field's menu (once per project).",
            "Pick a script: <b>Send to Unity</b>, <b>Make Prefab</b>, "
            "<b>Reimport Folder</b>, or your own.",
            "A script that takes an asset gets the <b>Source</b>: a <b>Model "
            "File</b>, or <i>from Maya or Blender</i> the <b>Current Scene</b>, "
            "exported by the Scene Exporter.",
            "Click <b>Run in Unity</b>.",
        ],
        "sections": [
            (
                "Your own scripts",
                [
                    "The script list's menu: <b>Copy to My Scripts</b> copies the "
                    "selected one to your folder to edit (yours runs in its place); "
                    "<b>Open My Scripts Folder</b> shows the folder.",
                    "A script is a C# file whose class is named as it, with a "
                    "<code>[UnityScript]</code> static method taking "
                    "<code>ScriptArgs</code>; its header's first line describes it, "
                    "and <code>__KEY__</code> tokens show the rows it reads.",
                    "A script that does not compile is taken out again, and its "
                    "errors land here: your project compiles as before.",
                ],
            ),
        ],
        "notes": [
            "With Unity closed, a Source is still copied in: Unity imports it when "
            "the project next opens. <b>Tools ▸ M3trik Scripts ▸ Pause</b> in Unity "
            "stops the connection.",
        ],
    }

    # ------------------------------------------------------------------ init
    def __init__(self, switchboard, **kwargs):
        #: The host's Unity engine CLASS, injected by whoever opened this panel
        #: (see :attr:`engine`). A class rather than an instance, so a host that
        #: opens the panel pays nothing until a scene is sent.
        self._engine = kwargs.get("engine", None)
        self._host_bridge = None
        self._registry = _params.Parameters
        self._initial_model: str = kwargs.get("model_path", "") or ""
        self._model_edit: Optional[QtWidgets.QLineEdit] = None
        self._model_row: Optional[QtWidgets.QWidget] = None
        self._model_label: Optional[QtWidgets.QLabel] = None
        #: The script waiting on Unity: ``(connection, job id, script)``, or None.
        self._running = None
        self._cancel_asked = False
        #: A host just injected its engine: open on Current Scene once.
        self._prefer_scene = False
        super().__init__(switchboard)
        self._build_model_row()
        source = self._param_widgets["SOURCE"]
        # By VALUE, not position: the list is script- and host-dependent, so a
        # stored index means a different source in each.
        source.restore_by = "data"
        self.sb.KindFactory.connect_changed(source, lambda _value: self._refresh_param_visibility())
        if self._engine is not None:
            self._adopt_engine(None)
        self._refresh_sources()
        if self._output_dir_edit is not None:
            self._output_dir_edit.editingFinished.connect(self._log_connection_status)

    # ------------------------------------------------------------------ base-class hooks
    @property
    def params_module(self):
        """The panel's registry, and with a host engine, the host's export rows
        (:meth:`_adopt_engine`)."""
        return self._registry

    @property
    def template_dir(self) -> Path:
        return UnityDeliverer.TEMPLATE_DIR

    @property
    def template_dirs(self):
        """The person's own Unity scripts, then the built-ins (the deliverer's)."""
        return UnityDeliverer.template_dirs()

    def make_bridge(self):
        """The file-input bridge, with the panel's one delivery: a scene sent
        through the host's engine is delivered by it too."""
        return ptk.FileDeliveryBridge(deliverer=UnityDeliverer())

    def list_template_modes(self):
        return UnityDeliverer.list_template_modes()

    def _format_combo_label(self, template, mode):
        return UnityDeliverer.label(template)

    def select_initial_template_index(self, pairs) -> int:
        names = [template for template, _mode in pairs]
        return names.index(self.DEFAULT_SCRIPT) if self.DEFAULT_SCRIPT in names else 0

    def default_output_dir(self) -> str:
        # No scene/workspace fallback -- a DCC scene dir isn't a Unity project.
        return ""

    def _on_template_changed(self) -> None:
        """A script changes the sources it takes, then the rows."""
        self._refresh_sources()
        super()._on_template_changed()

    # ------------------------------------------------------------------ sources
    @property
    def engine(self):
        """The host's Unity engine class this panel sends the scene through, or ``None``.

        The injection point for a host: launch the app with ``show=False``, set
        this, then show. The engine exports the Scope and hands the file to this
        panel's delivery; it answers ``params_registry()`` (the rows shown for
        Current Scene), ``scope_objects(scope)`` and ``send(...)``, and takes
        ``deliverer=`` when built. Assigning it offers Current Scene and builds
        the host's rows, so a host can hand the panel its engine at any point in
        the panel's life.
        """
        return self._engine

    @engine.setter
    def engine(self, value) -> None:
        if value is self._engine:
            return
        previous, self._engine = self._engine, value
        # Drop any bridge built from the previous engine -- keeping it would
        # send through the old host after the panel was re-pointed.
        self._host_bridge = None
        self._adopt_engine(previous)
        self._refresh_sources()

    def _adopt_engine(self, previous) -> None:
        """The registry and rows for the engine now set: the host's rows come off
        its engine's registry, built once between the Source row and the
        panel's own. A panel that just gained the scene source opens on it: the
        host opened this panel to send its scene."""
        self._registry = self._merged_registry()
        self.add_param_rows()
        # A host row's label can widen the label column; the Model File row,
        # built from it before, follows.
        if self._model_label is not None:
            self._model_label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        if self._engine is not None and previous is None:
            self._prefer_scene = True

    def _merged_registry(self):
        """The panel's registry, with the engine's rows after the Source row."""
        own = _params.PARAMS
        if self._engine is None:
            return _params.Parameters
        host = self._engine.params_registry().PARAMS
        merged = {"SOURCE": own["SOURCE"]}
        merged.update({key: spec for key, spec in host.items() if key not in own})
        merged.update({key: spec for key, spec in own.items() if key != "SOURCE"})
        return type("Parameters", (_params.Parameters,), {"PARAMS": merged})

    def _host_param_keys(self) -> set:
        """The rows the engine's registry brought (none without a host)."""
        return set(self.params_module.PARAMS) - set(_params.PARAMS)

    def _selected_template(self) -> str:
        """The selected script; the default before the combo populates."""
        pair = self._selected_template_mode()
        return pair[0] if pair else self.DEFAULT_SCRIPT

    def _script_sources(self) -> tuple:
        """The sources the selected script takes that this panel can give:
        Current Scene only with a host. ``()``: it runs on the project alone."""
        taken = UnityDeliverer.sources(self._selected_template())
        return tuple(
            s for s in (_params.SCENE_SOURCE, _params.FILE_SOURCE)
            if s in taken and (s != _params.SCENE_SOURCE or self._engine is not None)
        )

    def _refresh_sources(self) -> None:
        """The Source row's entries for the selected script, kept on the one
        chosen when it is still offered."""
        if "SOURCE" not in self._param_widgets:
            return
        offered = self._script_sources()
        current = self._read_param("SOURCE")
        self._set_param_choices(
            "SOURCE", [(_params.SOURCE_LABELS[s], s) for s in offered] or [(_params.SOURCE_LABELS[_params.FILE_SOURCE], _params.FILE_SOURCE)]
        )
        if self._prefer_scene and _params.SCENE_SOURCE in offered:
            self._prefer_scene = False
            self._write_param("SOURCE", _params.SCENE_SOURCE)
        elif current in offered:
            self._write_param("SOURCE", current)
        self._refresh_param_visibility()

    def _active_source(self) -> Optional[str]:
        """``SCENE_SOURCE`` or ``FILE_SOURCE``, or ``None`` for a script that
        runs on the project alone."""
        offered = self._script_sources()
        if not offered:
            return None
        chosen = self._read_param("SOURCE")
        return chosen if chosen in offered else offered[0]

    def _relevant_param_keys(self):
        """The rows the selected script names, the Source row while it offers a
        choice, and the host's export rows while Current Scene is the source."""
        keys = set(super()._relevant_param_keys() or ())
        source = self._active_source()
        if len(self._script_sources()) > 1:
            keys.add("SOURCE")
        if source == _params.SCENE_SOURCE:
            keys |= self._host_param_keys()
        return keys

    def _refresh_param_visibility(self) -> None:
        """The rows, and the Model File row: shown for a file copied in."""
        super()._refresh_param_visibility()
        if self._model_row is not None:
            self.sb.FieldVisibility.set_widget_visible(
                self._model_row, self._active_source() == _params.FILE_SOURCE
            )

    def _host(self):
        """The host's engine, built once with this panel's delivery attached, or
        ``None`` (no host)."""
        if self._engine is None:
            return None
        if self._host_bridge is None:
            self._host_bridge = self._engine(
                deliverer=self.bridge.deliverer, decide_check_failure=self.decide_check_failure
            )
            # A different logger from the file bridge's, which the base binds:
            # without this, what a scene send reports goes to the DCC's script editor.
            self._redirect_log_to_panel(self._host_bridge)
        return self._host_bridge

    def decide_check_failure(self, check: str, messages, remaining) -> str:
        """What to do when a Scene Exporter check fails while the scene is
        exported: the Scene Exporter's own question, asked as its panel asks it,
        before anything is written -- its words (``check_failure_html``: the
        check's label, what it reported, escaped and capped, the checks still to
        run) over its buttons (``CHECK_FAILURE_CHOICES``: Override All /
        Override / Cancel, Cancel the default). Read from the send's exporter
        (the engine's ``exporter``); with none under way there is nothing to
        carry past, so it stops."""
        exporter = getattr(self._host_bridge, "exporter", None)
        if exporter is None:
            return ptk.TaskFactory.CHECK_ABORT
        choices = exporter.CHECK_FAILURE_CHOICES
        answer = self.sb.message_box(
            exporter.check_failure_html(check, messages, remaining),
            *choices,
            default="Cancel",
            timeout=None,
        )
        return choices.get(answer, ptk.TaskFactory.CHECK_ABORT)

    # ------------------------------------------------------------------ the Unity Project field
    def _configure_output_dir_options(self, edit) -> None:
        """Unity Project field: recent-history button + an option menu of project
        actions, co-located with the field they act on."""
        self._add_recent_output_dir_option(edit)
        menu = edit.option_box.menu
        for label, name, tooltip, handler in (
            (
                "Set Project…",
                "btn_set_project",
                "Browse for the Unity project folder (the one containing 'Assets/').",
                self._pick_output_dir,
            ),
            (
                "Open Project Folder",
                "btn_open_project",
                "Reveal the configured Unity project folder in the file manager.",
                self._open_project_folder,
            ),
            (
                "Install / Update Connection",
                "btn_install_connection",
                "Copy the M3trik Unity Scripts package into the project's Packages/\n"
                "(or bring it up to date). It runs this panel's scripts while the\n"
                "project is open in Unity; Tools > M3trik Scripts > Pause stops it.",
                self.install_connection,
            ),
            (
                "Remove Connection",
                "btn_remove_connection",
                "Take the package out of the project, with the copies of scripts it\n"
                "wrote into Assets/M3trikScripts (your own stay in your scripts folder).",
                self.remove_connection,
            ),
        ):
            menu.add("QPushButton", setText=label, setObjectName=name, setToolTip=tooltip)
            getattr(menu, name).clicked.connect(handler)

    def _open_project_folder(self) -> None:
        self.reveal_folder(self.resolved_output_dir())

    def _connection(self, required: bool = True) -> Optional[UnityConnection]:
        """The Unity Project field's connection, or ``None`` -- said, with the
        field focused, when *required*."""
        project = self.resolved_output_dir()
        if UnityConnection.is_project(project):
            return UnityConnection(project)
        if required:
            self.panel_log(
                "Set the Unity Project folder above (the one containing 'Assets/' and 'ProjectSettings/').",
                "error",
            )
            if self._output_dir_edit is not None:
                self._output_dir_edit.setFocus()
        return None

    def _log_connection_status(self) -> None:
        connection = self._connection(required=False)
        if connection is not None:
            self.panel_log(connection.status(), "info")

    def install_connection(self) -> bool:
        """Install, or bring up to date, the project's connection. Returns
        whether it is current afterwards."""
        connection = self._connection()
        if connection is None:
            return False
        state = connection.state()
        if state == "installed":
            self.panel_log(f"The connection is current (v{connection.installed_version()}). {connection.status()}", "info")
            return True
        written = connection.install()
        verb = "Installed" if state == "missing" else "Updated"
        self.panel_log(
            f"{verb} the connection (v{connection.bundled_version()}, {len(written)} file(s)): Unity loads "
            "it on its next focus, and its Console says when it serves the project.",
            "success",
        )
        return True

    def remove_connection(self) -> None:
        connection = self._connection()
        if connection is None:
            return
        if connection.state() == "missing":
            self.panel_log("No connection is installed in this project.", "info")
            return
        if not self.sb.confirm(
            f"Remove the M3trik Unity Scripts package from {os.path.basename(connection.project)}, "
            "with the script copies it wrote into Assets/M3trikScripts?",
            yes="Remove",
            no="Keep",
        ):
            return
        connection.remove()
        self.panel_log("Removed the connection: Unity drops it on its next focus.", "success")

    def _offer_install(self, connection: UnityConnection) -> None:
        """A missing or older connection asks, installs, continues (CODE_STANDARD
        section 15): the run goes on either way, the copy at least landing."""
        state = connection.state()
        if state == "installed":
            return
        question = (
            f"Install the M3trik Unity Scripts package into {os.path.basename(connection.project)}? "
            "It runs this panel's scripts while the project is open in Unity "
            "(Tools > M3trik Scripts > Pause stops it)."
            if state == "missing"
            else f"Update the connection in {os.path.basename(connection.project)} "
            f"(v{connection.installed_version()} to v{connection.bundled_version()})?"
        )
        if self.sb.confirm(question, yes="Install" if state == "missing" else "Update", no="Not now"):
            self.install_connection()

    # ------------------------------------------------------------------ Model File row
    def _build_model_row(self) -> None:
        """Insert a 'Model File' row (option-box: recent history + browse) at the top.

        The edit is parented into the row layout (with stretch) before the option
        box wraps it, so the wrapping container fills the row (see
        ``ParamPanelSlots._build_output_dir_row`` for the rationale).
        """
        layout = self.ui.grp_process.layout()

        row = QtWidgets.QWidget(self.ui.grp_process)
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)

        label = QtWidgets.QLabel("Model File:", row)
        label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        edit = QtWidgets.QLineEdit(row)
        edit.setObjectName(f"{self.LOG_TAG}_model")
        edit.setPlaceholderText("(pick an FBX / OBJ / USD / glTF mesh to send)")
        edit.setMinimumHeight(19)
        edit.setMaximumHeight(19)
        edit.setToolTip(
            "Model file copied into the Unity project (FBX, OBJ, USD, Alembic,\n"
            "glTF, or a polygon-mesh PLY), as exported: nothing is re-exported."
        )
        if self._initial_model:
            edit.setText(self._initial_model)

        hbox.addWidget(label)
        hbox.addWidget(edit, 1)

        edit.option_box.recent(
            settings_key=f"{self.LOG_TAG}_model_recent",
            auto_record=True,
            display_format="auto",
        )
        edit.option_box.set_action(
            callback=self._pick_model,
            icon="folder",
            tooltip="Browse for a model file",
            settings_key=False,
        )

        layout.insertWidget(0, row)
        self._model_edit = edit
        self._model_row = row
        self._model_label = label

    def _model_start_dir(self) -> str:
        cur = self.resolved_model_path()
        if cur:
            return os.path.dirname(cur)
        return str(Path.home())

    def _pick_model(self) -> None:
        try:
            paths = self.sb.file_dialog(
                file_types=_MODEL_FILE_TYPES,
                title="Select a model file to send to Unity:",
                start_dir=self._model_start_dir(),
                allow_multiple=False,
            )
        except Exception:  # noqa: BLE001
            paths = None
        if not paths:
            return
        chosen = paths[0] if isinstance(paths, (list, tuple)) else paths
        if chosen and self._model_edit is not None:
            self._model_edit.setText(chosen)
            self._record_recent(self._model_edit, chosen)

    def resolved_model_path(self) -> str:
        if self._model_edit is None:
            return ""
        return self._model_edit.text().strip()

    def set_model_path(self, path: str) -> None:
        """Pre-fill the Model File field (public hand-off point for hosts)."""
        self._initial_model = path or ""
        if self._model_edit is not None:
            self._model_edit.setText(self._initial_model)
            self._record_recent(self._model_edit, self._initial_model)

    # ------------------------------------------------------------------ b000 -- run
    def b000(self) -> None:
        """Run the selected script in Unity, delivering its Source first."""
        if self._running is not None:
            self.panel_log(
                "A script is still running in Unity: wait for it, or Cancel Running Script (header menu).",
                "warning",
            )
            return
        script = self._selected_template()
        if not UnityDeliverer.template_path(script).is_file():
            self.panel_log(f"No script '{script}': Refresh the script list.", "error")
            return
        connection = self._connection()
        if connection is None:
            return
        self._offer_install(connection)
        source = self._active_source()
        if source is None:
            job = self._run_on_project(connection, script)
        elif source == _params.SCENE_SOURCE:
            job = self._send_scene(connection.project, script)
        else:
            job = self._send_file(connection.project, script)
        if job:
            self._watch(connection, job, script)

    def _run_on_project(self, connection: UnityConnection, script: str) -> Optional[str]:
        """A script that takes no asset, handed straight to Unity."""
        request = ptk.HandoffRequest(template=script, mode="", params=self.collect_param_values())
        self.bridge.logger.info(f"--- {UnityDeliverer.label(script)} -> {connection.project} ---")
        return self.bridge.deliverer.run(self.bridge, connection.project, request)

    def _send_file(self, project: str, script: str) -> Optional[str]:
        """Copy the Model File into the project, then run the script on it."""
        model = self.resolved_model_path()
        if not model:
            self.panel_log("Pick a model file first (the Model File field's browse button).", "warning")
            return None
        if not os.path.isfile(model):
            self.panel_log(f"Model file not found: {model}", "error")
            return None
        self.bridge.target_folder = project
        self.bridge.logger.info(f"--- {UnityDeliverer.label(script)} on {os.path.basename(model)} -> {project} ---")
        try:
            with self.sb.progress(text=f"Working: {UnityDeliverer.label(script)}"):
                result = self.bridge.send(model_path=model, template=script, mode="", params=self.collect_param_values())
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
            return None
        return (result or {}).get("job")

    def _send_scene(self, project: str, script: str) -> Optional[str]:
        """Export the host scene's Scope through its engine (the Scene Exporter),
        delivered by this panel's deliverer, then run the script on it."""
        bridge = self._host()
        if bridge is None:
            self.panel_log("No host scene to send: pick a Model File instead.", "error")
            return None
        params = self.collect_param_values()
        # Resolved here rather than left to the send, so an empty scope can be
        # REPORTED: "nothing selected" and "the scene is empty" are the user's
        # own next action, not a failed export.
        scope = params.get(ptk.HandoffScope.PARAM, ptk.HandoffScope.SELECTED)
        objects = bridge.scope_objects(scope)
        if not objects:
            self.panel_log(self.empty_scope_message(scope), "warning")
            return None
        bridge.project_path = project
        bridge.logger.info(
            f"--- {UnityDeliverer.label(script)} ({scope}) on {len(objects)} object(s) -> {project} ---"
        )
        try:
            with self.sb.progress(text=f"Working: {UnityDeliverer.label(script)}"):
                result = bridge.send(objects, template=script, mode="", params=params)
        except Exception:
            bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
            return None
        return (result or {}).get("job")

    # ------------------------------------------------------------------ waiting on Unity
    def _watch(self, connection: UnityConnection, job: str, script: str):
        """Wait for Unity's answer off the UI thread (a changed script compiles
        first: seconds), then report it. The panel and its host stay live."""
        label = UnityDeliverer.label(script)
        self._running = (connection, job, script)
        self._cancel_asked = False
        footer = getattr(self.ui, "footer", None)
        if footer is not None:
            footer.start_progress(text=f"{label}: running in Unity…")
        task = self.sb.BackgroundTask(
            lambda: connection.wait(job, cancelled=lambda: self._cancel_asked), "unity-script"
        )

        def done() -> None:
            self._running = None
            try:
                record = task.result()
            except Exception as error:  # noqa: BLE001 -- said in the panel, the panel stays up
                if footer is not None:
                    footer.finish_progress(f"{label}: no answer from Unity.")
                self.panel_log(str(error), "error")
                return
            ok = self.report(record, connection.project)
            if footer is not None:
                footer.finish_progress(f"{label}: {'done' if ok else 'failed'} in Unity.")

        task.when_done(self.ui, done)
        return task

    def report(self, record: dict, project: str) -> bool:
        """Log what Unity answered (:meth:`UnityConnection.outcome`): the script's
        lines, the assets it made (linked), the Console's lines. Returns whether
        it ran."""
        result = record.get("result") or {}
        for line in result.get("report") or ():
            self.panel_log(str(line), "info")
        for asset in result.get("created") or ():
            path = os.path.join(project, str(asset))
            self.panel_log(f'Made: <a href="action://open?path={path}">{asset}</a>', "info")
        for entry in result.get("console") or record.get("console") or ():
            level = _CONSOLE_LEVELS.get(str(entry.get("type")), "info")
            self.panel_log(f"[Unity] {entry.get('message', '')}", level)
        if record.get("state") == "done":
            seconds = result.get("seconds")
            took = f" in {seconds:.2f} s" if isinstance(seconds, (int, float)) else ""
            cancelled = " (stopped early, as asked)" if result.get("cancelled") else ""
            self.panel_log(f"{UnityDeliverer.label(result.get('script', ''))} ran{took}{cancelled}.", "success")
            return True
        self.panel_log(str(record.get("error") or "The script failed in Unity."), "error")
        return False

    def cancel_script(self) -> None:
        """Withdraw the script sent to Unity, or ask it to stop between steps."""
        if self._running is None:
            self.panel_log("No script is running in Unity.", "info")
            return
        self._cancel_asked = True
        self.panel_log("Asked Unity to stop the script.", "info")
