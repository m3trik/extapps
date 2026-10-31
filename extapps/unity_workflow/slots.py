# !/usr/bin/python
# coding=utf-8
"""Slots for the Unity Workflow panel -- the one Unity panel, in every host.

Standalone it copies a picked **model file** into a Unity project's ``Assets/``
through :class:`unitytk.FileToUnityBridge` and optionally launches the chosen
Editor, and there is no Source row -- one entry is no choice, so it hides. A
host that opened it injects its Unity engine (:attr:`UnityWorkflowSlots.engine`
-- ``mtk.UnityBridge`` / ``btk.UnityBridge``, the shape of the WebXR Preview's
``engine``), and the Source row offers **Current Scene** above File on Disk,
with the host's export rows (its engine's parameter registry: Scope, Include
Materials, ...) shown while that source is active. Which source is active
changes *which bridge produces the payload* and nothing else: the delivery --
unitytk's deliverer, the Unity Project, the Editor launch -- is this panel's
one chain either way, which is why the panel body carries no per-host branch.
The host half exports the scope (the FBX with its scene records) and hands the
file to the deliverer this panel attached.

The project actions (set / open / create a project) live on the 'Unity
Project' field's option menu, co-located with the field they act on; the
**Manage Unity Scripts** mode installs, updates or removes unitytk's C# import
scripts in the project. ``unitytk`` is optional (installed on demand, through
the host's install route when a host opened the panel), so it is imported
inside the methods that use it.

Note: *Unity Studio* is a separate paid, browser-based product (assets enter it via
Unity Cloud's Asset Manager), not this desktop FBX hand-off -- this panel does not
target it.
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

_PKG_DIR = Path(__file__).resolve().parent


class UnityWorkflowSlots(ParamPanelSlots):
    """Switchboard slots wired to ``unity_workflow.ui`` via :class:`ParamPanelSlots`.

    Copies the Source -- a model file, or the scope of the scene of a host that
    injected its :attr:`engine` -- into a Unity project's ``Assets/`` through
    unitytk's deliverer (optionally launching the chosen Editor), or runs the
    Manage Unity Scripts action on the project.
    """

    UI_NAME = "unity_workflow"
    #: Saved data: the folder the panel's presets have always been kept in.
    PRESETS_ROOT = Path("extapps/unity_workflow")
    LOG_TAG = "unity_workflow"

    # Manage Unity Scripts needs TemplateDeployer.components() / .run_action(), which
    # landed in unitytk 0.0.8, and 0.1.0 moved the templates into one folder per
    # component: an older deployer knows only the flat names, so its Install / Update
    # writes flat copies beside the moved ones (every class twice; the package's
    # assembly stops compiling). The floor rides on the requirement string so the
    # probe, the prompt and pip all read one value; `pyproject.toml`'s [unity] extra
    # only constrains a FRESH install, so a session carrying the older release would
    # otherwise keep using it.
    UNITYTK_REQ = "unitytk>=0.1.0"

    #: The feature named by the install prompt (Manage Unity Scripts -> Install).
    UNITY_FEATURE = "Unity Workflow"

    # The required path row IS the Unity project (folder with Assets/).
    REQUIRE_OUTPUT_DIR = True
    OUTPUT_DIR_LABEL = "Unity Project:"
    OUTPUT_DIR_PLACEHOLDER = "(folder containing Assets/)"
    OUTPUT_DIR_TOOLTIP = (
        "Path to the target Unity project -- the folder that contains the\n"
        "'Assets/' directory. The model file, or the scene's export, is copied\n"
        "into Assets/<subfolder>; Unity imports it on its next window focus.\n"
        "No project yet? Create one via 'New Unity Project...' in the field menu."
    )

    # The combo picks a MODE, not a template file, and ``template_dir`` is the
    # package's own directory -- so the template-management rows would offer to
    # re-scan nothing and to reveal source code.
    TEMPLATE_MENU = False

    # Two combo entries: the delivery (copy into Assets/), and the unitytk script
    # management flow (status / install-update / uninstall of the embedded
    # com.m3trik.unitytk package) -- panel-native, driven by its own
    # SCRIPTS_ACTION parameter rather than a buried menu button.
    MODE_COPY = "copy_to_assets"
    MODE_MANAGE = "manage_scripts"
    MODE_LABELS = {
        MODE_COPY: "Copy to Project",
        MODE_MANAGE: "Manage Unity Scripts",
    }

    #: Params owned by the Manage Unity Scripts template (hidden in copy mode).
    SCRIPT_PARAM_KEYS = frozenset({"SCRIPTS", "SCRIPTS_ACTION"})

    # The project actions (Set / Open / New) live on the Unity Project field's
    # option menu (see _configure_output_dir_options), co-located with the field
    # they act on; the header keeps just Clear Log.
    HEADER_MENU_ITEMS = (
        ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
    )

    # One card for both launches: a host-only line says so, since standalone
    # (and a host left on File on Disk) copies a file as it is.
    HELP_SPEC = {
        "title": "Unity Workflow",
        "body": "Copy a model into a Unity project's <b>Assets/</b> folder. "
        "Safe with Unity open: the copy lands whole, and Unity imports it on its "
        "next window focus. On its own it copies a model file; opened from Maya "
        "or Blender it can send the scene as well.",
        "steps": [
            "Pick a <b>Model File</b> (FBX, OBJ, USD, Alembic, glTF or PLY).",
            "<i>From Maya or Blender:</i> the <b>Source</b> row offers "
            "<b>Current Scene</b>: the <b>Scope</b> is exported (an FBX carrying "
            "the scene's records) with the <b>Export</b> rows, then copied in.",
            "Set the <b>Unity Project</b> (the folder holding Assets/); the "
            "field's menu also opens or creates one.",
            "With <b>Copy to Project</b> in the top combo, click <b>Send to Unity</b>.",
        ],
        "sections": [
            (
                "Parameters",
                [
                    "<b>Assets Subfolder</b> — where under Assets/ the model "
                    "lands (blank = <i>Imported</i>; <i>/</i> = Assets/ itself).",
                    "<b>Asset Name</b> — optional; blank uses the file's name "
                    "(the scene: its first object's). A same-named asset is "
                    "replaced.",
                    "<b>Launch Unity</b> — after copying: <i>Don't launch</i>, "
                    "<i>Open Editor</i>, or <i>Headless (batch)</i> (import, then "
                    "quit; needs a batch-capable license). <b>Unity Version</b> "
                    "picks the Editor.",
                ],
            ),
        ],
        "notes": [
            "<b>File on Disk</b> copies the file as it is; unitytk's import "
            "scripts act on <b>.fbx</b> files only. A scene's embedded textures "
            "ride inside its FBX, and the import scripts extract the maps its "
            "materials and channels use.",
            "<b>Manage Unity Scripts</b> (top combo): check the scripts, pick an "
            "<b>Action</b> (Status, Install / Update, Uninstall) for the "
            "project's embedded <i>com.m3trik.unitytk</i> package, and click "
            "Send to Unity. Per-channel import toggles: in Unity, Edit ▸ "
            "Project Settings ▸ unitytk.",
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
        super().__init__(switchboard)
        self._build_model_row()
        self._populate_unity_rows()  # Editor combo + SCRIPTS list
        source = self._param_widgets["SOURCE"]
        # By VALUE, not position: the list is host-dependent (File on Disk is
        # entry 0 without a host and entry 1 with one), so a stored index means
        # a different source in each.
        source.restore_by = "data"
        self.sb.KindFactory.connect_changed(
            source, lambda _value: self._refresh_param_visibility()
        )
        if self._engine is not None:
            self._adopt_engine(None)
        self._refresh_param_visibility()

    # ------------------------------------------------------------------ base-class hooks
    @property
    def params_module(self):
        """The panel's registry, and with a host engine, the host's export rows
        (:meth:`_adopt_engine`)."""
        return self._registry

    @property
    def template_dir(self) -> Path:
        # No script templates (copy-to-assets renders nothing); the package dir is
        # a harmless stand-in for the (no-op) per-template description lookup.
        return _PKG_DIR

    def make_bridge(self):
        """unitytk's file-input engine (``FileToUnityBridge``), or ``None`` while
        unitytk is absent -- a reportable state, not an import error the panel
        can't survive. SILENT, for a ``make_bridge`` that runs from ``__init__``
        (a modal raised from a constructor strands itself); installing is the
        explicit Manage Unity Scripts > Install. Its deliverer is the panel's one
        delivery: a scene sent through the host's engine is delivered by it too.
        """
        if not self.optional_package_available("unitytk"):
            return None

        from unitytk import FileToUnityBridge

        return FileToUnityBridge()

    def list_template_modes(self):
        return [(self.MODE_COPY, ""), (self.MODE_MANAGE, "")]

    def _format_combo_label(self, template, mode):
        # Friendly label over the internal stem.
        return self.MODE_LABELS.get(template, template)

    def default_output_dir(self) -> str:
        # No scene/workspace fallback -- a DCC scene dir isn't a Unity project.
        return ""

    def _install_optional_package(self, spec: str) -> None:
        """Install *spec* where this session imports from: through the host's
        engine when a host opened the panel (Blender keeps the user site off
        ``sys.path``, so the default ``pip install --user`` would succeed and
        stay unimportable), else uitk's default."""
        install = getattr(self._engine, "install_package", None)
        if install is not None:
            install(spec)
            return
        super()._install_optional_package(spec)

    # ------------------------------------------------------------------ sources
    @property
    def engine(self):
        """The host's Unity engine class this panel sends the scene through, or ``None``.

        The injection point for a host: launch the app with ``show=False``, set
        this, then show. The engine exports the Scope and hands the file to this
        panel's delivery; it answers ``params_registry()`` (the rows shown for
        Current Scene), ``scope_objects(scope)``, ``send(...)`` and, optionally,
        ``install_package(spec)``, and takes ``deliverer=`` when built.
        Assigning it offers Current Scene and builds the host's rows, so a host
        can hand the panel its engine at any point in the panel's life.
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
        self._refresh_param_visibility()

    def _adopt_engine(self, previous) -> None:
        """The registry, the rows and the Source entries for the engine now set.

        The host's rows come off its engine's registry rather than a list
        written here, so a host that adds an export row needs no edit of this
        panel; they are built once (``ParamPanelSlots.add_param_rows``) between
        the Source row and the Unity rows, and shown only for Current Scene.
        A panel that just gained the scene source opens on it: the host opened
        this panel to send its scene. A stored choice restores over it when the
        window first shows.
        """
        self._registry = self._merged_registry()
        self.add_param_rows()
        # A host row's label can widen the label column; the Model File row,
        # built from it before, follows.
        if self._model_label is not None:
            self._model_label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        choices = [(_params.SOURCE_LABELS[_params.FILE_SOURCE], _params.FILE_SOURCE)]
        if self._engine is not None:
            choices.insert(
                0, (_params.SOURCE_LABELS[_params.SCENE_SOURCE], _params.SCENE_SOURCE)
            )
        self._set_param_choices("SOURCE", choices)
        if self._engine is not None and previous is None:
            self._write_param("SOURCE", _params.SCENE_SOURCE)

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

    def _active_source(self) -> str:
        """``SCENE_SOURCE`` or ``FILE_SOURCE``: File on Disk without a host."""
        if self._engine is None:
            return _params.FILE_SOURCE
        return self._read_param("SOURCE") or _params.FILE_SOURCE

    def _host(self):
        """The host's engine, built once with this panel's delivery attached, or
        ``None`` (no host, or unitytk -- the delivery -- absent).

        Built lazily so the panel costs a DCC nothing until a scene is sent, and
        kept for the panel's life.
        """
        if self._engine is None:
            return None
        if self._host_bridge is None:
            files = self.peek_bridge()
            if files is None:
                return None
            self._host_bridge = self._engine(deliverer=files.deliverer)
            # A different logger from the file bridge's, which the base binds:
            # without this, what a scene send reports (the export, the copy,
            # the launch) goes to the DCC's script editor.
            self._redirect_log_to_panel(self._host_bridge)
        return self._host_bridge

    def _selected_template(self) -> str:
        """The combo's mode stem; :attr:`MODE_COPY` before the combo populates."""
        pair = self._selected_template_mode()
        return pair[0] if pair else self.MODE_COPY

    def _relevant_param_keys(self):
        """Which rows the send the panel would make now reads.

        Explicit (not file-driven) so visibility never silently depends on the
        absence of a template file in the package dir. Manage Unity Scripts
        shows its checklist + action combo; Copy to Project the delivery rows,
        the Source row while a host offers a choice, and the host's export
        rows while Current Scene is the source -- a file source exports nothing.
        """
        keys = set(self.params_module.PARAMS)
        if self._selected_template() == self.MODE_MANAGE:
            return keys & self.SCRIPT_PARAM_KEYS
        keys -= self.SCRIPT_PARAM_KEYS
        if self._engine is None:
            keys.discard("SOURCE")  # one entry is no choice
        if self._active_source() != _params.SCENE_SOURCE:
            keys -= self._host_param_keys()
        return keys

    def _refresh_param_visibility(self) -> None:
        """The rows, and the Model File row: shown for a file copied in."""
        super()._refresh_param_visibility()
        if self._model_row is not None:
            self.sb.FieldVisibility.set_widget_visible(
                self._model_row,
                self._selected_template() == self.MODE_COPY
                and self._active_source() == _params.FILE_SOURCE,
            )

    def _configure_output_dir_options(self, edit) -> None:
        """Unity Project field: recent-history button + an option menu of project
        actions (Set Project / Open / New), co-located with the field they act on.
        Overrides the base browse-button default.
        """
        self._add_recent_output_dir_option(edit)
        menu = edit.option_box.menu  # the option-menu (▾) button + its Menu
        for label, name, tooltip, handler in (
            (
                "Set Project…",
                "btn_set_project",
                "Browse for the Unity project folder (the one containing 'Assets/').",
                self._pick_output_dir,
            ),
            (
                "Open Unity Project",
                "btn_open_project",
                "Reveal the configured Unity project folder in Explorer.",
                self._open_project_folder,
            ),
            (
                "New Unity Project…",
                "btn_new_project",
                "Create a new Unity project (pick a version + location) and load it\n"
                "into the field above. Uses the selected Unity Version.",
                self._new_unity_project,
            ),
        ):
            menu.add(
                "QPushButton", setText=label, setObjectName=name, setToolTip=tooltip
            )
            getattr(menu, name).clicked.connect(handler)

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

    # ------------------------------------------------------------------ Unity helpers
    def _populate_unity_rows(self) -> None:
        """Fill the rows discovered at runtime from the installed unitytk release:
        the UNITY_VERSION combo and the SCRIPTS checklist. Called once from
        ``__init__``, after the base has built the parameter widgets.
        """
        # Components of the deployable C# set, discovered from the installed
        # unitytk release; empty when it is absent (see _populate_script_components).
        self._script_components = []
        self._populate_unity_versions()
        self._populate_script_components()

    def _populate_unity_versions(self) -> None:
        """Fill the UNITY_VERSION combo from the installed Editors (newest first).

        The 'Auto (newest)' entry (data "") is the registry default; discovered
        versions are appended so the user can pin which Editor creates/launches.
        """
        widget = self._param_widgets.get("UNITY_VERSION")
        if widget is None:
            return
        try:
            from unitytk import UnityFinder

            editors = UnityFinder.find_editors()
            # Numeric, not string, order: '2022.3.9f1' > '2022.3.10f1' as text.
            # Inside the try so an import failure keeps the empty-combo fallback.
            ranked = sorted(editors, key=UnityFinder.version_sort_key, reverse=True)
        except Exception:  # noqa: BLE001
            ranked = []
        for ver in ranked:
            widget.addItem(ver, ver)

    def _open_project_folder(self) -> None:
        """Reveal the configured Unity project folder."""
        self.reveal_folder(self.resolved_output_dir())

    def _populate_script_components(self) -> None:
        """Fill the SCRIPTS checklist from unitytk's deployable components.

        Dynamic like the version combo: one checkable row per import channel,
        read from the installed unitytk release — a controller added to the
        C# bundle appears here with no panel edit. Everything starts checked
        (the historical full-set deploy). The shared core files aren't listed:
        they ride along with every install and leave with the last script.

        Silent when unitytk is absent — the row stays empty and the actions
        fall back to the full set (see :meth:`_script_selection`).
        """
        widget = self._param_widgets.get("SCRIPTS")
        if widget is None:
            return
        try:
            from unitytk import TemplateDeployer

            components = [c for c in TemplateDeployer.components() if not c.required]
        except Exception:  # noqa: BLE001
            components = []
        if not components:
            return
        self._script_components = components
        self._set_param_choices(
            "SCRIPTS", [(c.label, c.key, c.summary) for c in components]
        )
        self._write_param("SCRIPTS", [c.key for c in components])

    def _script_selection(self):
        """The checked component keys, or ``None`` when the checklist never
        populated (unitytk absent at panel build) — ``None`` means the full
        set, so the action still does the obvious thing."""
        if not self._script_components:
            return None
        return list(self._read_param("SCRIPTS"))

    def _run_manage_mode(self) -> bool:
        """Run the Manage Unity Scripts action when that mode is selected.

        Returns:
            True when it ran (``b000`` is then done), False in the copy mode,
            where the send runs.
        """
        if self._selected_template() != self.MODE_MANAGE:
            return False
        action = self.collect_param_values().get("SCRIPTS_ACTION", "status")
        self._manage_unity_scripts(action)
        return True

    def _manage_unity_scripts(self, action: str) -> None:
        """Run the Manage Unity Scripts template's chosen *action* over the
        scripts checked in the panel.

        Status / install-update / uninstall of the embedded
        ``Packages/com.m3trik.unitytk`` UPM package in the configured project.
        The work and its reporting live in
        :meth:`unitytk.TemplateDeployer.run_action`; this owns the panel-side
        preconditions and logs via :meth:`panel_log` — every branch here must
        be able to report while the optional engine is missing.
        """
        project = self.resolved_output_dir()
        if not project:
            self.panel_log(
                "Set the Unity Project folder first (the one containing 'Assets/').",
                "error",
            )
            if self._output_dir_edit is not None:
                self._output_dir_edit.setFocus()
            return

        if action == "install":
            # Explicit action — prompting to install the unitytk package is
            # appropriate here (and only here).
            if not self.ensure_optional_package(
                self.UNITYTK_REQ, feature=self.UNITY_FEATURE
            ):
                return
            # Engine just arrived: fill the checklist that built empty, so the
            # run below deploys the real set. Guarded — a re-populate would
            # re-check every row and throw away the user's selection.
            if not self._script_components:
                self._populate_script_components()
        elif not self.optional_package_available(self.UNITYTK_REQ):
            self.panel_log(
                f"This panel needs {self.UNITYTK_REQ} — it is not installed in this "
                "session, or is older than that. Run the 'Install / Update' "
                "action first.",
                "error",
            )
            return
        from unitytk import TemplateDeployer

        for level, message in TemplateDeployer.run_action(
            project, action, self._script_selection()
        ):
            self.panel_log(message, level)

    def _new_unity_project(self) -> None:
        """Create a new Unity project (version + location) and load it into the field."""
        from unitytk import UnityLauncher

        version = (
            self._read_param("UNITY_VERSION")
            if "UNITY_VERSION" in self._param_widgets
            else ""
        ) or None
        launcher = UnityLauncher(executable_path=version)
        if not launcher.executable_path:
            self.bridge.logger.error(
                "No Unity Editor found to create a project. Install one via Unity Hub."
            )
            return

        parent = QtWidgets.QFileDialog.getExistingDirectory(
            self.ui, "Choose where to create the new project", str(Path.home())
        )
        if not parent:
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self.ui, "New Unity Project", "Project name:"
        )
        name = (name or "").strip()
        if not ok or not name:
            return
        target = os.path.join(parent, name)
        if os.path.exists(target):
            self.bridge.logger.error(f"Target already exists: {target}")
            return

        self.bridge.logger.info(
            f"Creating Unity project at {target} (batch mode; this can take a minute)…"
        )
        try:
            # Reached from a menu button, outside slot dispatch, so the busy
            # cursor is this method's (its own entry on the override stack).
            with self.sb.busy_cursor():
                created = launcher.create_project(target)
        except Exception as e:  # noqa: BLE001
            self.bridge.logger.error(f"Project creation failed: {e}")
            return

        if created and self._output_dir_edit is not None:
            self._output_dir_edit.setText(target)
            self._record_output_dir(target)
            self.bridge.logger.info(f"Created project at {target}")
        elif not created:
            self.bridge.logger.error(f"Project creation did not complete at {target}.")

    # ------------------------------------------------------------------ b000 -- send
    def b000(self) -> None:
        """Run the selected template: copy the Source, or script management."""
        if self._run_manage_mode():
            return
        if self._active_source() == _params.SCENE_SOURCE:
            self._send_scene()
        else:
            self._send_file()

    def _required_project(self) -> str:
        """The Unity Project field, or ``""`` -- said, with the field focused."""
        project = self.resolved_output_dir()
        if not project:
            self.panel_log(
                "Set the Unity Project folder above (the one containing 'Assets/'), "
                "or create one via 'New Unity Project…'.",
                "error",
            )
            if self._output_dir_edit is not None:
                self._output_dir_edit.setFocus()
        return project

    def _send_file(self) -> None:
        """Copy the Model File into the project, as it is."""
        model = self.resolved_model_path()
        if not model:
            self.bridge.logger.warning(
                "Pick a model file first (use the Model File field's browse button)."
            )
            return
        if not os.path.isfile(model):
            self.bridge.logger.error(f"Model file not found: {model}")
            return

        project = self._required_project()
        if not project:
            return

        self.bridge.project_path = project
        self.bridge.logger.info(
            f"--- Send to Unity on {os.path.basename(model)} -> {project} ---"
        )
        try:
            with self.sb.progress(text="Working: Send to Unity"):
                self.bridge.send(
                    model_path=model,
                    template=self.MODE_COPY,
                    mode="",
                    params=self.collect_param_values(),
                )
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())

    def _send_scene(self) -> None:
        """Export the host scene's Scope through its engine, delivered by this
        panel's deliverer into the project."""
        bridge = self._host()
        if bridge is None:
            self.panel_log(
                f"Sending the scene needs {self.UNITYTK_REQ}, which copies it into "
                "the project: run Manage Unity Scripts > 'Install / Update' first.",
                "error",
            )
            return
        project = self._required_project()
        if not project:
            return

        params = self.collect_param_values()
        # Resolved here rather than left to the send, so an empty scope can be
        # REPORTED: "nothing selected" and "the scene is empty" are the user's
        # own next action, not a failed export.
        scope = params.get(ptk.HandoffScope.PARAM, ptk.HandoffScope.SELECTED)
        objects = bridge.scope_objects(scope)
        if not objects:
            self.panel_log(self.empty_scope_message(scope), "warning")
            return

        bridge.project_path = project
        bridge.logger.info(
            f"--- Send to Unity ({scope}) on {len(objects)} object(s) -> {project} ---"
        )
        try:
            with self.sb.progress(text="Working: Send to Unity"):
                bridge.send(objects, template=self.MODE_COPY, mode="", params=params)
        except Exception:
            bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
