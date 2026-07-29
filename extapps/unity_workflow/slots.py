# !/usr/bin/python
# coding=utf-8
"""Slots for the standalone Unity Workflow panel.

A DCC-agnostic sibling of mayatk's / blendertk's ``UnityBridgeSlots``: all three
subclass uitk's :class:`BridgeSlotsBase` (parameter widgets, presets, log routing,
the relabeled 'Unity Project' row, the project-actions menu), but this one is driven
by a picked **model file** instead of a live DCC selection — so it runs from any host
that loads uitk (tentacle, a bare ``python -c`` launch) and is the panel the Blender
'Unity Bridge' reuses (export the selection to FBX, then :meth:`set_model_path`).

Delivery is the single copy-to-Assets target via :class:`unitytk.FileToUnityBridge`
(the file-input engine sharing ``unitytk.CopyToAssetsDeliverer`` with the DCC
bridges): copy the model into the project's ``Assets/`` and optionally launch the
chosen Editor. The launcher actions (set / open / create a project) live on the
'Unity Project' field's option menu, co-located with the field they act on.

Note: *Unity Studio* is a separate paid, browser-based product (assets enter it via
Unity Cloud's Asset Manager), not this desktop FBX hand-off -- this panel does not
target it.
"""
from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

from qtpy import QtCore, QtWidgets

from uitk.bridge import BridgeSlotsBase


from extapps.unity_workflow import parameters as _params


_PKG_DIR = Path(__file__).resolve().parent

# Unity-importable model formats offered in the file picker.
_MODEL_FILE_TYPES = [
    "*.fbx", "*.obj", "*.usd", "*.usdc", "*.usda",
    "*.abc", "*.gltf", "*.glb", "*.ply",
]


class UnityWorkflowSlots(BridgeSlotsBase):
    """Switchboard slots wired to ``unity_workflow.ui`` via :class:`BridgeSlotsBase`.

    Picks a model file, then copies it into a Unity project's ``Assets/`` via
    :class:`unitytk.FileToUnityBridge` (optionally launching the chosen Editor).
    """

    UI_NAME = "unity_workflow"
    PRESETS_ROOT = Path("extapps/unity_workflow")
    LOG_TAG = "unity_workflow"

    # The required path row IS the Unity project (folder with Assets/).
    REQUIRE_OUTPUT_DIR = True
    OUTPUT_DIR_LABEL = "Unity Project:"
    OUTPUT_DIR_PLACEHOLDER = "(folder containing Assets/)"
    OUTPUT_DIR_TOOLTIP = (
        "Path to the target Unity project -- the folder that contains the\n"
        "'Assets/' directory. The model file is copied into\n"
        "Assets/<subfolder>; Unity imports it on its next window focus.\n"
        "No project yet? Create one via 'New Unity Project...' in the field menu."
    )

    # Single delivery target: copy the file into the Unity project's Assets/.
    # Matches the shared CopyToAssetsDeliverer's one mode; the combo shows it
    # under a friendly label.
    MODE_COPY = "copy_to_assets"
    MODE_LABELS = {MODE_COPY: "Copy to Project"}

    # The project actions (Set / Open / New) live on the Unity Project field's
    # option menu (see _configure_output_dir_options); the header keeps just
    # Clear Log (no templates folder to open — this panel renders no scripts).
    HEADER_MENU_ITEMS = (
        ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
    )
    HELP_SPEC = {
        "title": "Unity Workflow",
        "body": "Copy a model file (FBX / OBJ / USD / glTF) into a Unity project's "
        "<b>Assets/</b> folder. Unity imports the asset automatically on its next "
        "window focus -- no script, no fresh-instance launch, your open editor is "
        "never disturbed.",
        "steps": [
            "Pick a <b>Model File</b> to send.",
            "Set the <b>Unity Project</b> folder (or create one via the field menu).",
            "Tweak the parameters, then click <b>Send to Unity</b>.",
        ],
        "sections": [
            ("Parameters", [
                "<b>Assets Subfolder</b> — where under Assets/ the file lands.",
                "<b>Asset Name</b> — optional; blank uses the file's name.",
                "<b>Launch Unity</b> — after copying: <i>Don't launch</i> (Unity "
                "imports on focus), <i>Open Editor</i> (windowed), or "
                "<i>Headless</i> (batch import).",
            ]),
        ],
        "notes": [
            "The Blender 'Unity Bridge' opens this panel with the exported "
            "selection pre-filled in Model File.",
            "Copying into Assets/ is non-destructive to a running Unity session.",
        ],
    }

    # ------------------------------------------------------------------ init
    def __init__(self, switchboard, **kwargs):
        self._initial_model: str = kwargs.get("model_path", "") or ""
        self._model_edit: Optional[QtWidgets.QLineEdit] = None
        super().__init__(switchboard)
        self._build_model_row()
        self._populate_unity_versions()

    # ------------------------------------------------------------------ base-class hooks
    @property
    def params_module(self):
        return _params

    @property
    def template_dir(self) -> Path:
        # No script templates (copy-to-assets renders nothing); the package dir is
        # a harmless stand-in for the (no-op) per-template description lookup.
        return _PKG_DIR

    def make_bridge(self):
        """Build the unitytk engine, offering to install it if absent.

        ``unitytk`` is optional (``pip install extapps[unity]``) -- imported
        here rather than at module scope so a missing one becomes a prompt
        instead of an import error the panel can't report.
        """
        if not self.ensure_optional_package("unitytk", feature="Unity Workflow"):
            return None

        from unitytk import FileToUnityBridge

        return FileToUnityBridge()

    def list_template_modes(self) -> List[Tuple[str, str]]:
        return [(self.MODE_COPY, "")]

    def _format_combo_label(self, template, mode):
        # Friendly label over the internal stem.
        return self.MODE_LABELS.get(template, template)

    def _relevant_param_keys(self):
        # Copy-to-assets is template-free, so every parameter stays visible (no
        # per-template gating).
        return None

    def _configure_output_dir_options(self, edit) -> None:
        """Unity Project field: recent-history button + an option menu of project
        actions (Set Project / Open / New), co-located with the field they act on.
        Overrides the base browse-button default.
        """
        self._add_recent_output_dir_option(edit)
        menu = edit.option_box.menu  # the option-menu (▾) button + its Menu
        for label, name, tooltip, handler in (
            (
                "Set Project…", "btn_set_project",
                "Browse for the Unity project folder (the one containing 'Assets/').",
                self._pick_output_dir,
            ),
            (
                "Open Unity Project", "btn_open_project",
                "Reveal the configured Unity project folder in Explorer.",
                self._open_project_folder,
            ),
            (
                "New Unity Project…", "btn_new_project",
                "Create a new Unity project (pick a version + location) and load it\n"
                "into the field above. Uses the selected Unity Version.",
                self._new_unity_project,
            ),
            (
                "Install/Update Unity Scripts", "btn_deploy_scripts",
                "Deploy unitytk's C# import automation into the project above as\n"
                "the embedded com.m3trik.unitytk package (under Packages/).\n"
                "Run again any time to update it in place.",
                self._deploy_unity_scripts,
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
        ``BridgeSlotsBase._build_output_dir_row`` for the rationale).
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
            "glTF, or a polygon-mesh PLY). The Blender 'Unity Bridge' pre-fills\n"
            "this with the exported selection."
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
        """Pre-fill the Model File field (public hand-off point for hosts).

        The Blender 'Unity Bridge' exports the selection to FBX and calls this
        before showing the panel."""
        self._initial_model = path or ""
        if self._model_edit is not None:
            self._model_edit.setText(self._initial_model)
            self._record_recent(self._model_edit, self._initial_model)

    # ------------------------------------------------------------------ Unity helpers
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
            # Numeric ordering (2020.3.10f1 > 2020.3.9f1); a plain lexicographic
            # sort misorders same-major versions. Inside the try so an import
            # failure keeps the graceful empty-combo fallback.
            ordered = sorted(editors, key=UnityFinder.version_sort_key, reverse=True)
        except Exception:  # noqa: BLE001
            ordered = []
        for ver in ordered:
            widget.addItem(ver, ver)

    def _open_project_folder(self) -> None:
        """Reveal the configured Unity project folder."""
        self.reveal_folder(self.resolved_output_dir())

    def _deploy_unity_scripts(self) -> None:
        """Deploy/update the unitytk C# template package into the project.

        Writes the full compile-coupled set as the embedded
        ``Packages/com.m3trik.unitytk`` UPM package -- visible in Unity's
        Package Manager, configurable under Project Settings > unitytk.
        """
        # reask: an explicit install button must re-prompt even after a
        # declined implicit ask memoized the miss.
        if not self.ensure_optional_package(
            "unitytk", feature="Unity Workflow", reask=True
        ):
            return
        from unitytk import TemplateDeployer

        project = self.resolved_output_dir()
        if not project:
            self.bridge.logger.error(
                "Set the Unity Project folder first (the one containing 'Assets/')."
            )
            return
        try:
            written = TemplateDeployer.deploy_package(project)
        except Exception as e:  # noqa: BLE001
            self.bridge.logger.error(f"Unity script deploy failed: {e}")
            return
        self.bridge.logger.info(
            f"Deployed the com.m3trik.unitytk package ({len(written)} files) "
            f"into {project} -- Unity picks it up on its next focus."
        )

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
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            created = launcher.create_project(target)
        except Exception as e:  # noqa: BLE001
            self.bridge.logger.error(f"Project creation failed: {e}")
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        if created and self._output_dir_edit is not None:
            self._output_dir_edit.setText(target)
            self._record_output_dir(target)
            self.bridge.logger.info(f"Created project at {target}")
        elif not created:
            self.bridge.logger.error(f"Project creation did not complete at {target}.")

    # ------------------------------------------------------------------ b000 -- send
    def b000(self) -> None:
        """Copy the picked model into the Unity project (+ optional Editor launch)."""
        model = self.resolved_model_path()
        if not model:
            self.bridge.logger.warning(
                "Pick a model file first (use the Model File field's browse button), "
                "or send the selection from your DCC's 'Unity Bridge'."
            )
            return
        if not os.path.isfile(model):
            self.bridge.logger.error(f"Model file not found: {model}")
            return

        project = self.resolved_output_dir()
        if not project:
            self.bridge.logger.error(
                "Set the Unity Project folder above (the one containing 'Assets/'), "
                "or create one via 'New Unity Project…'."
            )
            if self._output_dir_edit is not None:
                self._output_dir_edit.setFocus()
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


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    from extapps.unity_workflow.launcher import UnityWorkflowUI

    ui = UnityWorkflowUI()
    ui.show(pos="screen", app_exec=True)
