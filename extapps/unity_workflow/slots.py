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
That shared Unity-panel behavior (the project row + actions, the mode combo, the
Editor combo, script management) is :class:`UnityPanelMixin`, vendored beside this
file (``_unity_panel.py``) and in mayatk's / blendertk's ``unity_bridge``; this file
owns the Model File row, the engine and the ``b000`` send.

Note: *Unity Studio* is a separate paid, browser-based product (assets enter it via
Unity Cloud's Asset Manager), not this desktop FBX hand-off -- this panel does not
target it.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import Optional

from qtpy import QtCore, QtWidgets

from uitk.bridge import BridgeSlotsBase


from extapps.unity_workflow import parameters as _params
from extapps.unity_workflow._unity_panel import UnityPanelMixin


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


class UnityWorkflowSlots(UnityPanelMixin, BridgeSlotsBase):
    """Switchboard slots wired to ``unity_workflow.ui`` via :class:`BridgeSlotsBase`.

    Picks a model file, then copies it into a Unity project's ``Assets/`` via
    :class:`unitytk.FileToUnityBridge` (optionally launching the chosen Editor).
    """

    UI_NAME = "unity_workflow"
    PRESETS_ROOT = Path("extapps/unity_workflow")
    LOG_TAG = "unity_workflow"

    OUTPUT_DIR_TOOLTIP = (
        "Path to the target Unity project -- the folder that contains the\n"
        "'Assets/' directory. The model file is copied into\n"
        "Assets/<subfolder>; Unity imports it on its next window focus.\n"
        "No project yet? Create one via 'New Unity Project...' in the field menu."
    )
    UNITY_FEATURE = "Unity Workflow"  # names the unitytk install prompt

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
            (
                "Parameters",
                [
                    "<b>Assets Subfolder</b> — where under Assets/ the file lands.",
                    "<b>Asset Name</b> — optional; blank uses the file's name.",
                    "<b>Launch Unity</b> — after copying: <i>Don't launch</i> (Unity "
                    "imports on focus), <i>Open Editor</i> (windowed), or "
                    "<i>Headless</i> (batch import).",
                ],
            ),
        ],
        "notes": [
            "The Blender 'Unity Bridge' opens this panel with the exported "
            "selection pre-filled in Model File.",
            "Copying into Assets/ is non-destructive to a running Unity session.",
            "The <b>Manage Unity Scripts</b> template installs, updates, "
            "inspects or removes unitytk's C# import automation in the project "
            "(the embedded <i>com.m3trik.unitytk</i> package). Check the "
            "scripts to act on — one row per import channel, all on by "
            "default; the shared core files ride along with any install. "
            "Per-channel runtime toggles live in Unity under Project "
            "Settings ▸ unitytk.",
        ],
    }

    # ------------------------------------------------------------------ init
    def __init__(self, switchboard, **kwargs):
        self._initial_model: str = kwargs.get("model_path", "") or ""
        self._model_edit: Optional[QtWidgets.QLineEdit] = None
        super().__init__(switchboard)
        self._build_model_row()
        self._populate_unity_rows()  # UnityPanelMixin: Editor combo + SCRIPTS list

    # ------------------------------------------------------------------ base-class hooks
    @property
    def params_module(self):
        return _params.Parameters

    def make_bridge(self):
        """Build the unitytk engine, or ``None`` when it is absent.

        ``unitytk`` is optional (``pip install extapps[unity]``) -- imported
        here rather than at module scope so a missing one is a reportable
        state instead of an import error the panel can't survive. SILENT: this
        runs from ``__init__`` via the log wiring, and a modal raised from a
        constructor strands itself. Installing is an explicit action.
        """
        if not self.optional_package_available("unitytk"):
            return None

        from unitytk import FileToUnityBridge

        return FileToUnityBridge()

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

    # ------------------------------------------------------------------ b000 -- send
    def b000(self) -> None:
        """Run the selected template: copy the model, or script management."""
        if self._run_manage_mode():
            return

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
