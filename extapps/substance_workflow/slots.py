#!/usr/bin/python
# coding=utf-8
"""Switchboard slots for the Substance Workflow UI.

The panel wires the UI to :class:`PainterConnection`: launch a fresh
Painter, then dispatch registered ops (``project.*``, ``bake.*``, …) over
the JSON-RPC bridge. Engine/domain logic lives in the op modules — these
slots only collect widget state and invoke ops by name.
"""
import os
import traceback
from typing import Any, Dict, Optional

import pythontk as ptk
from qtpy import QtCore, QtWidgets
from uitk import AttributeSpec, make_widget
from uitk.widgets.mixins.tooltip_mixin import fmt

from .env_utils.painter_connection import PainterConnection
from .env_utils.painter_finder import PainterFinder

# ---------------------------------------------------------------------------
# Mesh formats Painter accepts for project creation.
# ---------------------------------------------------------------------------
MESH_EXTS = ["*.fbx", "*.obj", "*.abc", "*.gltf", "*.glb", "*.ply", "*.usd", "*.usda", "*.usdc"]

# ---------------------------------------------------------------------------
# Workflow stages: (object_name, label, tooltip, default_on). Order here is
# both the menu order and the canonical execution order.
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    ("stage_open",   "Open / Create Project", "Open the .spp at the save path if it exists, else create a new project from the mesh file.", True),
    ("stage_bake",   "Bake Lighting → Diffuse", "iray-backed AO (+ optional curvature) composited onto the base color channel.", True),
    ("stage_save",   "Save Project",          "Save the project (save-as to the save path on first save).", True),
    ("stage_export", "Export Textures",       "Export textures via a preset. NOTE: export.* ops are not yet implemented.", False),
]

BLEND_MODES = ["Multiply", "Overlay", "Normal", "Darken", "LinearBurn"]
BAKE_RESOLUTIONS = ["256", "512", "1024", "2048", "4096"]

# ---------------------------------------------------------------------------
# Advanced bake parameters — one labeled row per spec in the Advanced popup.
# Field widgets come from uitk.make_widget driven by these AttributeSpecs
# (same factory as metashape_workflow). object_name == spec.key, so
# self.ui.<key> resolves each field via findChild.
# ---------------------------------------------------------------------------
ADVANCED_PARAMS = [
    AttributeSpec(key="cmb_bake_res",       label="Bake Resolution:",  kind="choice",
                  default="1024", choices=BAKE_RESOLUTIONS,
                  tooltip="Mesh-map bake output size (square, power of two)."),
    AttributeSpec(key="spn_ao_rays",        label="AO Rays:",          kind="int",
                  default=64, minimum=1, maximum=1024, step=8,
                  tooltip="AO secondary-ray sample count. Higher = cleaner, slower."),
    AttributeSpec(key="spn_ao_max",         label="AO Max Dist:",      kind="float",
                  default=1.0, minimum=0.0, maximum=100.0, step=0.1, decimals=3,
                  tooltip="AO ray maximum length in world units."),
    AttributeSpec(key="spn_ao_min",         label="AO Min Dist:",      kind="float",
                  default=0.0, minimum=0.0, maximum=100.0, step=0.1, decimals=3,
                  tooltip="AO ray minimum length (helps avoid self-shadow noise)."),
    AttributeSpec(key="spn_ao_spread",      label="AO Spread (deg):",  kind="float",
                  default=162.0, minimum=0.0, maximum=180.0, step=1.0, decimals=1,
                  tooltip="Hemisphere spread angle in degrees."),
    AttributeSpec(key="spn_ao_subsample",   label="AO Subsample:",     kind="int",
                  default=1, minimum=1, maximum=8,
                  tooltip="Supersampling factor (1 = none)."),
    AttributeSpec(key="spn_ao_intensity",   label="AO Intensity:",     kind="float",
                  default=1.0, minimum=0.0, maximum=4.0, step=0.05, decimals=2,
                  tooltip="Multiplier applied to the AO contribution when compositing."),
    AttributeSpec(key="cmb_blend",          label="Blend Mode:",       kind="choice",
                  default="Multiply", choices=BLEND_MODES,
                  tooltip="Blend mode for the inserted AO lighting layer."),
    AttributeSpec(key="chk_curvature",      label="Include Curvature:", kind="bool",
                  default=False,
                  tooltip="Also bake curvature and stack it as an overlay layer."),
    AttributeSpec(key="spn_curv_intensity", label="Curvature Intensity:", kind="float",
                  default=0.3, minimum=0.0, maximum=4.0, step=0.05, decimals=2,
                  tooltip="Curvature multiplier when 'Include Curvature' is on."),
    AttributeSpec(key="chk_skip_bakes",     label="Skip Existing Bakes:", kind="bool",
                  default=False,
                  tooltip="Only bake when the AO mesh map is missing."),
]

_LOG_LEVELS = {
    "Log Level: DEBUG": 10,
    "Log Level: INFO": 20,
    "Log Level: WARNING": 30,
    "Log Level: ERROR": 40,
}


class SubstanceWorkflowSlots(ptk.LoggingMixin):
    """Switchboard slots for the Substance Workflow UI."""

    def __init__(self, switchboard, log_level: int = 20):
        self.sb = switchboard
        self.ui = self.sb.loaded_ui.substance_workflow

        self.logger.setLevel(log_level)
        self.logger.hide_logger_name(True)
        self.logger.setup_logging_redirect(self.ui.txt003)

        self.conn: Optional[PainterConnection] = None
        self._busy: bool = False
        # Scan once at startup; reused by the Painter picker and status line.
        self._installs: Dict[str, str] = PainterFinder.find_installs()

        self._log_status()

    # ------------------------------------------------------------------ status

    def _log_status(self) -> None:
        if not self._installs:
            self.logger.warning(
                "No Substance 3D Painter install detected. Set the path via "
                "the Painter field or pass app_path."
            )
        else:
            self.logger.info(f"Found {len(self._installs)} Painter install(s).")

    @property
    def _connected(self) -> bool:
        return bool(self.conn and self.conn.is_connected)

    # ------------------------------------------------------------------ header

    def header_init(self, widget) -> None:
        if widget.is_initialized:
            return
        widget.menu.add(
            self.sb.registered_widgets.ComboBox,
            setObjectName="cmb003",
            add=_LOG_LEVELS,
            setCurrentIndex=1,
            setToolTip="Set the log level.",
        )
        widget.set_help_text(
            fmt(
                title="Substance Workflow",
                body="Drive Adobe Substance 3D Painter from a single panel. "
                "Each launch starts a NEW Painter instance over a JSON-RPC "
                "bridge — your open session is never touched.",
                steps=[
                    "Set the <b>Mesh File</b> (to create a project) and/or a "
                    "<b>Project Save Path</b> (.spp) to open or save to.",
                    "Pick which <b>Painter</b> install to launch.",
                    "Press <b>Launch Painter</b> (or let Run launch it).",
                    "Choose which <b>Stages</b> to run and tweak "
                    "<b>Advanced</b> bake parameters.",
                    "Press <b>Run Workflow</b>.",
                ],
                notes=[
                    "Painter launches fresh on an unused port every time "
                    "(force_new_instance is hard-coded on). Closing the panel "
                    "session terminates only the Painter this panel launched.",
                ],
            )
        )

    # ------------------------------------------------------------------ fields

    def txt000_init(self, widget) -> None:
        """Mesh File"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Mesh File:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.recent("substance_mesh_files", auto_record=True)
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_mesh",
            setToolTip="Select a mesh file to create a project from.",
        )

    def txt001_init(self, widget) -> None:
        """Template (optional)"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Template (optional):")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.clear_option = True
        widget.option_box.recent("substance_templates", auto_record=True)
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_template",
            setToolTip="Select a Painter project template (.spt).",
        )

    def txt002_init(self, widget) -> None:
        """Project Save Path"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Project Save Path:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.recent("substance_project_paths", auto_record=True)
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_project",
            setToolTip="Select where to save / open the .spp project.",
        )

    def cmb000_init(self, widget) -> None:
        """Painter install picker"""
        items = self._installs if self._installs else {"Auto-detect": None}
        widget.add(items, clear=True)

    # ------------------------------------------------------------------ stages

    def btn_stages_init(self, widget) -> None:
        """Stages popup — QMenu of checkboxes attached to the button."""
        if widget.is_initialized:
            return
        menu = QtWidgets.QMenu(widget)
        for object_name, label, tooltip, default_on in PIPELINE_STAGES:
            chk = QtWidgets.QCheckBox(label, menu)
            chk.setObjectName(object_name)
            chk.setChecked(default_on)
            chk.setToolTip(tooltip)
            action = QtWidgets.QWidgetAction(menu)
            action.setDefaultWidget(chk)
            menu.addAction(action)
        widget.setMenu(menu)

    # ------------------------------------------------------------------ advanced

    def btn_advanced_init(self, widget) -> None:
        """Advanced-params popup — labeled form inside a QMenu via QWidgetAction.

        Field widgets come from :func:`uitk.make_widget` driven by the
        :class:`AttributeSpec` entries in :data:`ADVANCED_PARAMS` — same
        factory as metashape_workflow, so spec changes flow through with no
        per-kind switch here.
        """
        if widget.is_initialized:
            return
        menu = QtWidgets.QMenu(widget)
        form_host = QtWidgets.QWidget(menu)
        vbox = QtWidgets.QVBoxLayout(form_host)
        vbox.setContentsMargins(2, 4, 2, 2)
        vbox.setSpacing(0)

        for spec in ADVANCED_PARAMS:
            row = QtWidgets.QWidget(form_host)
            hbox = QtWidgets.QHBoxLayout(row)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(2)

            lbl = QtWidgets.QLabel(spec.label, row)
            lbl.setMinimumWidth(110)
            lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            lbl.setToolTip(spec.tooltip)

            field = make_widget(spec, row)
            field.setMinimumHeight(19)
            field.setMaximumHeight(19)

            hbox.addWidget(lbl)
            hbox.addWidget(field, 1)
            vbox.addWidget(row)

        action = QtWidgets.QWidgetAction(menu)
        action.setDefaultWidget(form_host)
        menu.addAction(action)
        widget.setMenu(menu)

    # ------------------------------------------------------------------ buttons

    def cmb003(self, widget) -> None:
        """Log level changed"""
        self.logger.setLevel(int(widget.currentData()))

    def btn_launch(self, widget) -> None:
        """Toggle the Painter session."""
        if self._busy:
            self.logger.warning("Busy — wait for the current run to finish.")
            return
        if self._connected:
            self._close_painter()
        else:
            self._launch_painter()

    def b000(self) -> None:
        """Run Workflow"""
        if self._busy:
            self.logger.warning("Workflow already running.")
            return
        self.ui.txt003.clear()
        self._run_workflow()

    # Option-box browse callbacks
    def set_mesh_path(self, path: str) -> None:
        """Pre-fill the mesh field (e.g. a host exported the current selection to it).

        Public hand-off point for hosts that drive this panel — the Blender Substance *bridge*
        exports the selection to FBX and calls this before showing the panel."""
        self.ui.txt000.setText(path or "")

    def btn_browse_mesh(self) -> None:
        f = self.sb.file_dialog(
            file_types=MESH_EXTS,
            title="Select Mesh File",
            start_dir=os.path.dirname(self.ui.txt000.text()) or os.getcwd(),
            filter_description="Mesh Files",
            allow_multiple=False,
        )
        if f:
            self.ui.txt000.setText(f)

    def btn_browse_template(self) -> None:
        f = self.sb.file_dialog(
            file_types=["*.spt"],
            title="Select Project Template",
            start_dir=os.path.dirname(self.ui.txt001.text()) or os.getcwd(),
            filter_description="Painter Templates",
            allow_multiple=False,
        )
        if f:
            self.ui.txt001.setText(f)

    def btn_browse_project(self) -> None:
        # save_file_dialog (getSaveFileName) — a new project's .spp won't exist
        # yet, so an open dialog couldn't pick it.
        f = self.sb.save_file_dialog(
            file_types=["*.spp"],
            title="Select / Name Project File",
            start_dir=os.path.dirname(self.ui.txt002.text()) or os.getcwd(),
            filter_description="Painter Projects",
        )
        if f:
            self.ui.txt002.setText(f)

    # ------------------------------------------------------------------ session

    def _launch_painter(self) -> bool:
        exe = self.ui.cmb000.currentData()
        self.conn = PainterConnection.get_instance()
        try:
            with self.sb.progress(text="Launching Substance 3D Painter..."):
                ok = self.conn.connect(gui=True, app_path=exe)
            if ok:
                self.logger.info("Connected to the Painter bridge.")
                self.logger.info(f"Project: {self.conn.invoke('project.info')}")
            else:
                self.logger.error("Painter launched but the bridge never came up.")
            return ok
        except Exception as e:
            self.logger.error(f"Launch failed: {e}")
            self.logger.debug(traceback.format_exc())
            return False
        finally:
            self._sync_launch_button()

    def _close_painter(self) -> None:
        if self.conn is not None:
            try:
                self.conn.shutdown(force=True)
                self.logger.info("Painter session closed.")
            except Exception as e:
                self.logger.error(f"Failed to close Painter: {e}")
        self._sync_launch_button()

    def _sync_launch_button(self) -> None:
        """Keep the launch button's label in step with the session state."""
        self.ui.btn_launch.setText("Close Painter" if self._connected else "Launch Painter")

    # ------------------------------------------------------------------ helpers

    def _collect_stages(self) -> Dict[str, bool]:
        return {
            name: bool(getattr(self.ui, name).isChecked())
            for name, _, _, _ in PIPELINE_STAGES
        }

    def _collect_bake_params(self) -> Dict[str, Any]:
        return {
            "bake_resolution": int(self.ui.cmb_bake_res.currentText()),
            "ao_secondary_rays": int(self.ui.spn_ao_rays.value()),
            "ao_max_distance": float(self.ui.spn_ao_max.value()),
            "ao_min_distance": float(self.ui.spn_ao_min.value()),
            "ao_spread_angle": float(self.ui.spn_ao_spread.value()),
            "ao_subsample": int(self.ui.spn_ao_subsample.value()),
            "ao_intensity": float(self.ui.spn_ao_intensity.value()),
            "blend_mode": self.ui.cmb_blend.currentText() or "Multiply",
            "include_curvature": bool(self.ui.chk_curvature.isChecked()),
            "curvature_intensity": float(self.ui.spn_curv_intensity.value()),
            "skip_existing_bakes": bool(self.ui.chk_skip_bakes.isChecked()),
        }

    def _validate(self, stages: Dict[str, bool]) -> bool:
        mesh = self.ui.txt000.text().strip()
        save_path = self.ui.txt002.text().strip()
        if stages.get("stage_open") and not (mesh or os.path.isfile(save_path)):
            self.logger.error(
                "Provide a Mesh File to create a project, or an existing "
                ".spp Project Save Path to open."
            )
            return False
        if stages.get("stage_save"):
            creating_new = stages.get("stage_open") and not os.path.isfile(save_path)
            if creating_new and not save_path:
                self.logger.error(
                    "Set a Project Save Path to save the project — a newly "
                    "created project has no file yet, so 'Save Project' needs a "
                    "destination (or an existing .spp to open)."
                )
                return False
        return True

    # ------------------------------------------------------------------ run

    def _run_workflow(self) -> None:
        stages = self._collect_stages()
        if not self._validate(stages):
            return

        if not self._connected and not self._launch_painter():
            return

        mesh = self.ui.txt000.text().strip()
        template = self.ui.txt001.text().strip() or None
        save_path = self.ui.txt002.text().strip()

        self._busy = True
        self.ui.b000.setEnabled(False)
        try:
            self.logger.info(
                f"Starting workflow — stages: {[k for k, v in stages.items() if v]}"
            )
            with self.sb.progress(text="Working: Substance Workflow") as tick:
                if stages["stage_open"]:
                    if save_path and os.path.isfile(save_path):
                        self.logger.info(self.conn.invoke("project.open", path=save_path))
                        tick(text="Project opened")
                    else:
                        self.logger.info(
                            self.conn.invoke(
                                "project.create", mesh_path=mesh, template_path=template
                            )
                        )
                        tick(text="Project created")

                if stages["stage_bake"]:
                    result = self.conn.invoke(
                        "bake.lighting_to_diffuse", **self._collect_bake_params()
                    )
                    self.logger.info(f"Bake result: {result}")
                    tick(text="Lighting baked")

                if stages["stage_save"]:
                    if save_path and not os.path.isfile(save_path):
                        self.conn.invoke("project.save_as", path=save_path)
                    else:
                        self.conn.invoke("project.save")
                    tick(text="Project saved")

                if stages["stage_export"]:
                    try:
                        out = os.path.join(
                            os.path.dirname(save_path) or os.getcwd(), "export"
                        )
                        self.conn.invoke("export.textures", output_path=out, preset="")
                        tick(text="Textures exported")
                    except Exception as e:
                        self.logger.warning(f"Export skipped (not implemented): {e}")

            self.logger.info("Workflow completed successfully.")
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}")
            self.logger.debug(traceback.format_exc())
        finally:
            self._busy = False
            self.ui.b000.setEnabled(True)
