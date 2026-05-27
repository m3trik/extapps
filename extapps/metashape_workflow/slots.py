#!/usr/bin/python
# coding=utf-8
import os
import traceback
from typing import Any, Dict, Optional

import pythontk as ptk
from qtpy import QtCore, QtWidgets
from uitk import AttributeSpec, Signals, make_widget
from uitk.widgets.mixins.tooltip_mixin import fmt

from ._metashape_workflow import (
    MetashapeWorkflow,
    get_metashape_version,
    is_license_valid,
    is_metashape_available,
)

try:
    import Metashape as _Metashape  # type: ignore
except ImportError:
    _Metashape = None


# ---------------------------------------------------------------------------
# Pipeline stage definitions: (object_name, label, tooltip, default_on)
# Frame extraction is its own action triggered from the Frames-field option box.
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    ("stage_align", "Align Photos", "Detect features and align cameras.", True),
    ("stage_depth", "Generate Depth Maps", "Build per-image depth maps from aligned cameras.", True),
    ("stage_model", "Build 3D Model", "Reconstruct a polygon mesh from depth maps.", True),
    ("stage_texture", "Build Texture", "Bake a diffuse texture for the mesh.", True),
    ("stage_save", "Save Project", "Save the .psx project file.", True),
    ("stage_export", "Export Model", "Export the model to OBJ/PLY/STL/FBX.", True),
]

PRESETS: Dict[str, Dict[str, Any]] = {
    "High Quality": {"align_downscale": 1, "depth_downscale": 1, "face_count": "High", "texture_size": 8192},
    "Medium Quality": {"align_downscale": 2, "depth_downscale": 2, "face_count": "Medium", "texture_size": 4096},
    "Low Quality": {"align_downscale": 4, "depth_downscale": 4, "face_count": "Low", "texture_size": 2048},
    "Draft": {"align_downscale": 8, "depth_downscale": 8, "face_count": "Low", "texture_size": 1024},
}

FACE_COUNT_OPTIONS = ["Low", "Medium", "High"]
DEPTH_FILTER_OPTIONS = ["Mild", "Moderate", "Aggressive", "NoFiltering"]

# ---------------------------------------------------------------------------
# Advanced parameter table — one labeled row in the Advanced popup per spec.
# Consumed by btn_advanced_init via the uitk attributeFactory: each spec
# becomes a widget through make_widget(spec, parent); the slot only paints
# the per-row label and arranges the rows.
# ---------------------------------------------------------------------------
ADVANCED_PARAMS = [
    AttributeSpec(key="spn_texture_size",    label="Texture Size:",    kind="int",
                  default=4096, minimum=256, maximum=16384, step=256,
                  tooltip="Texture map resolution in pixels (square)."),
    AttributeSpec(key="cmb_face_count",      label="Face Count:",      kind="choice",
                  default="Medium", choices=FACE_COUNT_OPTIONS,
                  tooltip="Target face count for the reconstructed mesh."),
    AttributeSpec(key="cmb_depth_filter",    label="Depth Filter:",    kind="choice",
                  default="Mild",   choices=DEPTH_FILTER_OPTIONS,
                  tooltip="Depth map filtering strength."),
    AttributeSpec(key="spn_align_downscale", label="Align Downscale:", kind="int",
                  default=0, minimum=0, maximum=16,
                  tooltip="Override align downscale (0 = use preset)."),
    AttributeSpec(key="spn_depth_downscale", label="Depth Downscale:", kind="int",
                  default=0, minimum=0, maximum=16,
                  tooltip="Override depth downscale (0 = use preset)."),
    AttributeSpec(key="spn_frame_step",      label="Frame Step:",      kind="int",
                  default=30, minimum=1, maximum=1000,
                  tooltip="Extract every Nth frame from source video."),
    AttributeSpec(key="spn_frame_max",       label="Max Frames:",      kind="int",
                  default=0, minimum=0, maximum=100000,
                  tooltip="Max frames to extract (0 = no limit)."),
    AttributeSpec(key="spn_frame_quality",   label="Frame Quality:",   kind="int",
                  default=95, minimum=1, maximum=100,
                  tooltip="JPEG quality for extracted frames."),
]

VIDEO_EXTS = ["*.mp4", "*.avi", "*.mov", "*.mkv", "*.wmv", "*.flv", "*.m4v"]

_LOG_LEVELS = {
    "Log Level: DEBUG": 10,
    "Log Level: INFO": 20,
    "Log Level: WARNING": 30,
    "Log Level: ERROR": 40,
}


class MetashapeWorkflowSlots(ptk.LoggingMixin):
    """Switchboard slots for the Metashape Workflow UI."""

    def __init__(self, switchboard, log_level: int = 20):
        self.sb = switchboard
        self.ui = self.sb.loaded_ui.metashape_workflow

        self.logger.setLevel(log_level)
        self.logger.hide_logger_name(True)
        self.logger.setup_logging_redirect(self.ui.txt003)

        self.workflow: Optional[MetashapeWorkflow] = None
        self._busy: bool = False

        self._log_status()

    # ------------------------------------------------------------------ status

    def _log_status(self) -> None:
        if not is_metashape_available():
            self.logger.warning("Metashape module not installed — mock mode only.")
            return
        if is_license_valid():
            self.logger.info(f"Metashape {get_metashape_version()} ready (licensed).")
        else:
            self.logger.warning(
                f"Metashape {get_metashape_version()} installed but unlicensed — running in mock mode."
            )

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
                title="Metashape Workflow",
                body="Automate Agisoft Metashape photogrammetry processing "
                "from a single panel — project setup, source frames, quality "
                "preset, pipeline stages, and advanced tuning.",
                steps=[
                    "Set the <b>Project Directory</b> (where the .psx and "
                    "outputs go).",
                    "Set the <b>Frames Directory</b> (source images), or use "
                    "the field's option button (▸) to extract frames from a "
                    "video file.",
                    "Pick a <b>Quality Preset</b> (low / medium / high / "
                    "ultra-high).",
                    "Check which <b>Pipeline Stages</b> to run.",
                    "Tweak advanced parameters as needed.",
                    "Press <b>Run Workflow</b>.",
                ],
                sections=[
                    ("Header menu", [
                        "<b>Log Level</b> — DEBUG / INFO / WARNING / ERROR "
                        "verbosity for the embedded log panel.",
                    ]),
                ],
                notes=[
                    "Requires the Agisoft Metashape Python module to be "
                    "importable in this environment. The panel reports if "
                    "the SDK is missing or the license is invalid.",
                ],
            )
        )

    # ------------------------------------------------------------------ paths

    def txt000_init(self, widget) -> None:
        """Project Directory"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Project Directory:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.recent(
            "metashape_project_dirs", auto_record=True
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_project",
            setToolTip="Select a project directory.",
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Open in Explorer",
            setObjectName="btn_explore_project",
            setToolTip="Open the current project directory in Explorer.",
        )

    @Signals("editingFinished")
    def txt000(self, widget) -> None:
        self.logger.debug(f"Project directory: {widget.text()}")

    def txt001_init(self, widget) -> None:
        """Project Name"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Project Name:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.clear_option = True
        widget.option_box.recent(
            "metashape_project_names", auto_record=True
        )

    def txt002_init(self, widget) -> None:
        """Frames Directory"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Frames Directory:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.recent(
            "metashape_frame_dirs", auto_record=True
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_frames",
            setToolTip="Select a directory of source images.",
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Extract from Video...",
            setObjectName="btn_extract_frames",
            setToolTip="Extract frames from a video file into this directory.",
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Open in Explorer",
            setObjectName="btn_explore_frames",
            setToolTip="Open the current frames directory in Explorer.",
        )

    @Signals("editingFinished")
    def txt002(self, widget) -> None:
        self.logger.debug(f"Frames directory: {widget.text()}")

    # ------------------------------------------------------------------ presets

    def cmb000_init(self, widget) -> None:
        """Preset"""
        widget.add(list(PRESETS.keys()), clear=True)
        widget.setCurrentText("Medium Quality")

    # ------------------------------------------------------------------ tasks

    def btn_stages_init(self, widget) -> None:
        """Pipeline-stages popup — QMenu of checkboxes attached to the button.

        Each checkbox keeps its ``object_name`` from :data:`PIPELINE_STAGES` so
        ``self.ui.<name>`` lookup (used by :meth:`_collect_stages`) keeps
        working via ``QWidget.findChild`` walking into the menu's tree.
        """
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

        Row layout mirrors ``marmoset_bridge._build_param_widgets``: each row
        is a QWidget with a QHBoxLayout, a 90px right-aligned QLabel, and the
        field stretching to fill the remainder at a pinned 19px height.

        Field widgets come from :func:`uitk.make_widget` driven by the
        :class:`AttributeSpec` entries in :data:`ADVANCED_PARAMS` — same
        factory as marmoset_bridge / AttributeWindow, so spec changes here
        flow through without any per-kind switch.
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
            lbl.setMinimumWidth(90)
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

    def b000(self) -> None:
        """Run Workflow"""
        if self._busy:
            self.logger.warning("Workflow already running.")
            return
        self.ui.txt003.clear()
        self._run_workflow()

    def cmb003(self, widget) -> None:
        """Log level changed"""
        self.logger.setLevel(int(widget.currentData()))

    # Path option-box callbacks
    def btn_browse_project(self) -> None:
        d = self.sb.dir_dialog(
            title="Select Project Directory",
            start_dir=self.ui.txt000.text() or os.getcwd(),
        )
        if d:
            self.ui.txt000.setText(d)

    def btn_explore_project(self) -> None:
        self._open_in_explorer(self.ui.txt000.text())

    def btn_browse_frames(self) -> None:
        d = self.sb.dir_dialog(
            title="Select Frames Directory",
            start_dir=self.ui.txt002.text() or os.getcwd(),
        )
        if d:
            self.ui.txt002.setText(d)

    def btn_explore_frames(self) -> None:
        self._open_in_explorer(self.ui.txt002.text())

    def btn_extract_frames(self) -> None:
        """Extract frames from a video file into the frames directory."""
        video = self.sb.file_dialog(
            file_types=VIDEO_EXTS,
            title="Select Video File",
            start_dir=os.getcwd(),
            filter_description="Video Files",
            allow_multiple=False,
        )
        if not video:
            return

        out_dir = self.ui.txt002.text().strip()
        if not out_dir:
            out_dir = os.path.join(os.path.dirname(video), "frames")
            self.ui.txt002.setText(out_dir)

        step = int(self.ui.spn_frame_step.value())
        quality = int(self.ui.spn_frame_quality.value())
        max_frames = int(self.ui.spn_frame_max.value()) or None

        try:
            from pythontk import FrameExtractor

            extractor = FrameExtractor()
            self.logger.info(
                f"Extracting frames: '{os.path.basename(video)}' (step={step}, quality={quality}) → '{out_dir}'"
            )
            frames = extractor.extract_frames(
                video_path=video,
                output_folder=out_dir,
                step=step,
                quality=quality,
                max_frames=max_frames,
            )
            if frames:
                self.logger.info(f"Extracted {len(frames)} frames.")
            else:
                self.logger.warning("Frame extraction returned no files.")
        except Exception as e:
            self.logger.error(f"Frame extraction failed: {e}")
            self.logger.debug(traceback.format_exc())

    # ------------------------------------------------------------------ helpers

    def _open_in_explorer(self, path: str) -> None:
        path = (path or "").strip()
        if not path or not os.path.exists(path):
            self.logger.warning(f"Path does not exist: {path or '(empty)'}")
            return
        try:
            os.startfile(path)  # Windows
        except Exception as e:
            self.logger.error(f"Failed to open '{path}': {e}")

    def _collect_stages(self) -> Dict[str, bool]:
        return {
            name: bool(getattr(self.ui, name).isChecked())
            for name, _, _, _ in PIPELINE_STAGES
        }

    def _collect_params(self) -> Dict[str, Any]:
        preset_name = self.ui.cmb000.currentText() or "Medium Quality"
        preset = PRESETS.get(preset_name, PRESETS["Medium Quality"])

        align_override = int(self.ui.spn_align_downscale.value())
        depth_override = int(self.ui.spn_depth_downscale.value())

        return {
            "preset_name": preset_name,
            "align_downscale": align_override or preset["align_downscale"],
            "depth_downscale": depth_override or preset["depth_downscale"],
            "texture_size": int(self.ui.spn_texture_size.value()),
            "face_count": self.ui.cmb_face_count.currentText(),
            "depth_filter": self.ui.cmb_depth_filter.currentText(),
        }

    def _validate(self) -> bool:
        project_dir = self.ui.txt000.text().strip()
        frames_dir = self.ui.txt002.text().strip()

        if not project_dir:
            self.logger.error("Project directory is not set.")
            return False

        stages = self._collect_stages()
        needs_frames = any(stages[s] for s in ("stage_align", "stage_depth"))
        if needs_frames and not frames_dir:
            self.logger.error("Frames directory is required for the selected stages.")
            return False
        if needs_frames and not os.path.isdir(frames_dir):
            self.logger.error(f"Frames directory does not exist: {frames_dir}")
            return False

        try:
            os.makedirs(project_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Cannot create project directory: {e}")
            return False
        return True

    def _resolve_face_count(self, name: str):
        if _Metashape is None:
            return None
        mapping = {
            "Low": _Metashape.LowFaceCount,
            "Medium": _Metashape.MediumFaceCount,
            "High": _Metashape.HighFaceCount,
        }
        return mapping.get(name, _Metashape.MediumFaceCount)

    def _resolve_depth_filter(self, name: str):
        if _Metashape is None:
            return None
        mapping = {
            "Mild": _Metashape.MildFiltering,
            "Moderate": _Metashape.ModerateFiltering,
            "Aggressive": _Metashape.AggressiveFiltering,
            "NoFiltering": _Metashape.NoFiltering,
        }
        return mapping.get(name, _Metashape.MildFiltering)

    def _on_progress(self, stage: str, fraction: float) -> None:
        self.logger.info(f"[{stage}] {int(fraction * 100)}%")

    # ------------------------------------------------------------------ run

    def _run_workflow(self) -> None:
        if not self._validate():
            return

        stages = self._collect_stages()
        params = self._collect_params()

        project_dir = self.ui.txt000.text().strip()
        frames_dir = self.ui.txt002.text().strip()
        project_name = self.ui.txt001.text().strip() or os.path.basename(project_dir)

        self._busy = True
        self.ui.b000.setEnabled(False)
        try:
            self.logger.info(
                f"Starting workflow — preset '{params['preset_name']}', stages: "
                f"{[k for k, v in stages.items() if v]}"
            )

            # The Metashape SDK already drives ``self._on_progress``
            # with fine-grained (stage, fraction) updates. The footer's
            # indeterminate marquee gets ticked once per pipeline step
            # so users see motion even when no specific stage is active.
            with self.sb.progress(text="Working: Metashape Workflow") as tick:
                self.workflow = MetashapeWorkflow(
                    project_path=project_dir,
                    name=project_name,
                    progress=self._on_progress,
                )
                self.logger.info(self.workflow.get_license_info())
                if self.workflow.mock_mode:
                    self.logger.warning("Running in mock mode — no actual processing.")

                self.workflow.create_chunk(f"{project_name} — {params['preset_name']}")
                tick(text="Chunk created")

                if stages["stage_align"] or stages["stage_depth"] or stages["stage_model"]:
                    self.workflow.add_images(frames_dir)
                    tick(text="Images added")

                if stages["stage_align"]:
                    self.workflow.align_photos(downscale=params["align_downscale"])
                    tick(text="Photos aligned")

                if stages["stage_depth"]:
                    self.workflow.generate_depth_maps(
                        downscale=params["depth_downscale"],
                        filter_mode=self._resolve_depth_filter(params["depth_filter"]),
                    )
                    tick(text="Depth maps generated")

                if stages["stage_model"]:
                    self.workflow.build_model(
                        face_count=self._resolve_face_count(params["face_count"]),
                    )
                    tick(text="Model built")

                if stages["stage_texture"]:
                    self.workflow.build_texture(texture_size=params["texture_size"])
                    tick(text="Texture built")

                if stages["stage_save"]:
                    self.workflow.save_project()
                    tick(text="Project saved")

                if stages["stage_export"]:
                    self.workflow.export_model()
                    tick(text="Model exported")

            self.logger.info("Workflow completed successfully.")

        except Exception as e:
            self.logger.error(f"Workflow failed: {e}")
            self.logger.debug(traceback.format_exc())
        finally:
            self._busy = False
            self.ui.b000.setEnabled(True)
