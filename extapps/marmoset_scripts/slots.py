# !/usr/bin/python
# coding=utf-8
"""Slots for the standalone Marmoset Scripts panel.

A DCC-agnostic sibling of the host Marmoset Bridge panel: both subclass uitk's
:class:`ParamPanelSlots` (script combo, parameter widgets, presets, log
routing), but this one runs a script on a picked **model file** instead of a
scene selection -- a standalone panel (``launcher.py``), so it runs outside any
DCC too. The engine is :class:`MarmosetScripts` (this package's vendored
Toolbag engine).

The scripts are the engine's: the bundled ``import`` and ``lookdev``, and a
person's own (``ptk.ScriptTemplate.user_dir("marmoset")``, the folder every
host's Marmoset Bridge reads too), where one named like a bundled script runs
in its place. A script that reads a host's scene (:data:`HOST_ROWS`: the bake's
Bake Source set) runs from a host's bridge, so it is not listed here.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

import pythontk as ptk
from qtpy import QtCore, QtWidgets
from uitk import ParamPanelSlots

from . import parameters as _params
from ._marmoset_scripts import MarmosetScripts


#: The rows only a host's bridge fills, because they name what is in its scene:
#: a script that reads one (``__KEY__``) needs that host, so it is not listed.
HOST_ROWS = ("BAKE_SOURCE_SET",)

# Toolbag-importable model formats offered in the file picker.
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


class MarmosetScriptsSlots(ParamPanelSlots):
    """Switchboard slots wired to ``marmoset_scripts.ui``.

    Picks a model file, then launches Toolbag with the chosen script and mode
    via :class:`MarmosetScripts`.
    """

    UI_NAME = "marmoset_scripts"
    #: Saved data: the panel's presets (the former ``extapps/marmoset_workflow``
    #: folder's carry in once, ``_panel_launcher.RENAMED_FROM``).
    PRESETS_ROOT = Path("extapps/marmoset_scripts")
    #: Saved data: the widget names it builds (``<tag>_output_dir``, ...) are
    #: the ones the panel has always saved under, so it keeps its former name.
    LOG_TAG = "marmoset_workflow"
    # A blank Output Dir is never filled in: a run's files (the rendered script,
    # a round trip's maps and .tbscene) go to a fresh temp folder per send,
    # aged out after Toolbag has read them. A folder named here keeps them.
    TRANSIENT_OUTPUT_MODES = (ptk.SEND_TO, ptk.ROUND_TRIP)
    OUTPUT_DIR_TOOLTIP = (
        "Directory where a run's files land: the rendered script and, for a\n"
        "round trip, the maps it writes and its saved .tbscene.\n\n"
        "Leave blank and they go to a temp folder per send, aged out after\n"
        "Toolbag has read them. Name a folder here and every file stays in it."
    )

    # Uses the base's default header menu (Clear Log; the script rows are on
    # the script combo's context menu); only the help differs, so it's
    # declared as data. It says where this panel differs from the host
    # Marmoset Bridge, which a user may know first.
    HELP_SPEC = {
        "title": "Marmoset Scripts",
        "body": "Run a Marmoset Toolbag script on a model file from disk: the "
        "bundled ones set the model up for look-dev, and your own run beside "
        "them. No DCC required -- each click starts a new Toolbag.",
        "steps": [
            "Pick a <b>Model File</b> (FBX, OBJ, USD, Alembic, glTF / GLB, "
            "or a mesh PLY).",
            "Choose a script: <b>import</b> (the model only), <b>lookdev</b> "
            "(plus a sky and framing; the default), or one of yours.",
            "Set the rows the script shows (for lookdev, the <b>Sky</b> and "
            "<b>Frame on Open</b>).",
            "Click <b>Run in Marmoset</b>.",
        ],
        "sections": [
            (
                "Your scripts",
                [
                    "The script list's menu opens <b>My Scripts</b>: a Toolbag "
                    "Python script dropped there shows after a Refresh, and the "
                    "Maya and Blender Marmoset Bridges list it too.",
                    "<b>Copy to My Scripts</b> copies the selected script there "
                    "to edit; your copy then runs in its place.",
                    "A script shows the rows whose <b>__KEY__</b> tokens it "
                    "names; its <b>BRIDGE_MODES</b> line says how it runs "
                    "(send_to: Toolbag stays open; round_trip: hidden, then the "
                    "files it wrote are listed).",
                ],
            ),
        ],
        "notes": [
            "Nothing is saved for you in a send_to: save the scene in Toolbag.",
            "Unlike the Maya / Blender <b>Marmoset Bridge</b>, no textures are "
            "wired (the materials are what Toolbag's import of the file gives) "
            "and there is no bake: a bake reads a scene's Bake Source, so a "
            "script that does is listed in the bridge only.",
            "Gaussian-splat PLYs are not meshes and won't render in Toolbag.",
        ],
    }

    def __init__(self, switchboard, **kwargs):
        self._initial_model: str = kwargs.get("model_path", "") or ""
        self._model_edit: Optional[QtWidgets.QLineEdit] = None
        super().__init__(switchboard)
        self._build_model_row()

    # ------------------------------------------------------------------
    # Required base-class hooks
    # ------------------------------------------------------------------

    @property
    def params_module(self):
        return _params.Parameters

    @property
    def template_dir(self) -> Path:
        return MarmosetScripts.TEMPLATE_DIR

    @property
    def template_dirs(self) -> Tuple[Path, ...]:
        """The engine's own folders (the person's scripts, then the bundled
        ones), so the panel reads the very file the engine runs."""
        return MarmosetScripts.template_dirs()

    def make_bridge(self) -> MarmosetScripts:
        return MarmosetScripts()

    @staticmethod
    def needs_host(template: str) -> bool:
        """Whether *template* reads a row only a host's bridge fills
        (:data:`HOST_ROWS`), so this panel cannot run it."""
        path = MarmosetScripts.template_path(template)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return False
        return any(f"__{key}__" in text for key in HOST_ROWS)

    def list_template_modes(self) -> List[Tuple[str, str]]:
        """The engine's scripts, bundled and the person's own, but for those
        that read a host's scene (:meth:`needs_host`)."""
        pairs = MarmosetScripts.list_template_modes()
        hosted = {t for t in {t for t, _m in pairs} if self.needs_host(t)}
        return [(t, m) for (t, m) in pairs if t not in hosted]

    def select_initial_template_index(self, pairs: List[Tuple[str, str]]) -> int:
        """Prefer 'lookdev (send_to)', else first entry."""
        if ("lookdev", ptk.SEND_TO) in pairs:
            return pairs.index(("lookdev", ptk.SEND_TO))
        return 0

    # ------------------------------------------------------------------
    # Model-file row (this panel's analogue of a DCC selection)
    # ------------------------------------------------------------------

    def _build_model_row(self) -> None:
        """Insert a 'Model File' line edit + browse at the top of grp_process."""
        layout = self.ui.grp_process.layout()

        row = QtWidgets.QWidget(self.ui.grp_process)
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)

        label = QtWidgets.QLabel("Model File:", row)
        label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        edit = QtWidgets.QLineEdit(row)
        edit.setPlaceholderText("(pick an FBX / OBJ / USD / glTF mesh to import)")
        edit.setMinimumHeight(19)
        edit.setMaximumHeight(19)
        edit.setToolTip(
            "Model file the script runs on in Toolbag (FBX, OBJ, USD, Alembic, "
            "glTF, or a polygon-mesh PLY). Note: Gaussian-splat PLYs are not "
            "meshes and won't render in Toolbag."
        )
        if self._initial_model:
            edit.setText(self._initial_model)

        browse = QtWidgets.QPushButton("...", row)
        browse.setFixedWidth(22)
        browse.setMinimumHeight(19)
        browse.setMaximumHeight(19)
        browse.clicked.connect(self._pick_model)

        hbox.addWidget(label)
        hbox.addWidget(edit, 1)
        hbox.addWidget(browse)

        layout.insertWidget(0, row)
        self._model_edit = edit

    def _start_dir(self) -> str:
        cur = self.resolved_model_path()
        if cur:
            return os.path.dirname(cur)
        return str(Path.home())

    def _pick_model(self) -> None:
        try:
            paths = self.sb.file_dialog(
                file_types=_MODEL_FILE_TYPES,
                title="Select a model file to run a Marmoset script on:",
                start_dir=self._start_dir(),
                allow_multiple=False,
            )
        except Exception:  # noqa: BLE001
            paths = None
        if not paths:
            return
        chosen = paths[0] if isinstance(paths, (list, tuple)) else paths
        if chosen and self._model_edit is not None:
            self._model_edit.setText(chosen)

    def resolved_model_path(self) -> str:
        if self._model_edit is None:
            return ""
        return self._model_edit.text().strip()

    def set_model_path(self, path: str) -> None:
        """Pre-fill the Model File field (e.g. a host exported the current selection to it).

        Public hand-off point for a host that drives this panel. (Blender no
        longer does: it has a native Marmoset Bridge panel of its own.)"""
        self._initial_model = path or ""
        if self._model_edit is not None:
            self._model_edit.setText(self._initial_model)

    # ------------------------------------------------------------------
    # b000 -- the run
    # ------------------------------------------------------------------

    def b000(self) -> None:
        """Run the chosen script, in its chosen mode, on the picked model in Toolbag."""
        model = self.resolved_model_path()
        if not model:
            self.bridge.logger.warning(
                "Pick a model file first (use the '...' button next to Model File)."
            )
            return
        if not os.path.isfile(model):
            self.bridge.logger.error(f"Model file not found: {model}")
            return

        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning(
                "No script chosen. Pick one from the dropdown above."
            )
            return
        template, mode = pair

        if not self.bridge.toolbag_path:
            self.bridge.logger.error(MarmosetScripts.APP.not_found_msg)
            return

        output_dir = self.require_output_dir(mode)
        if output_dir is None:
            return

        self.bridge.logger.info(
            f"--- {template} ({mode}) on {os.path.basename(model)} ---"
        )

        try:
            with self.sb.progress(text=f"Working: Marmoset {template} ({mode})"):
                result = self.bridge.send(
                    model_path=model,
                    output_dir=output_dir or None,
                    template=template,
                    mode=mode,
                    params=self.collect_param_values(),
                )
        except Exception:
            self.bridge.logger.error("Engine raised:\n" + traceback.format_exc())
            return

        if result is None:
            return  # logger already explained why
