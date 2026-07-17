#!/usr/bin/python
# coding=utf-8
import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

# QC primitives live upstream now — see pythontk.core_utils.qc_log.
# Re-exported below for back-compat with extapps.photogrammetry.metashape_workflow imports.
from pythontk import GateError, QcGate, QcLog

from ..prep_stages import PrepStagesMixin

try:
    import Metashape as _Metashape
except ImportError:
    _Metashape = None


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif")


# Acceptance-gate defaults — Metashape-specific thresholds matching the
# "Acceptable" column from the proposal. ``QcGate`` is the engine-agnostic
# evaluator; these defaults are this engine's contribution.
DEFAULT_GATES: Dict[str, Dict[str, float]] = {
    "align": {
        "min_aligned_pct": 75.0,
        "max_rms_reproj_px": 1.0,
    },
    "model": {
        "min_largest_component_pct": 85.0,
    },
    "texture": {
        "min_coverage_pct": 90.0,
    },
}


def is_metashape_available() -> bool:
    """True if the Metashape Python module imported successfully."""
    return _Metashape is not None


def is_license_valid() -> bool:
    """True if a valid Metashape license is reachable. Never mutates state."""
    if _Metashape is None:
        return False
    try:
        return bool(_Metashape.license.valid)
    except Exception:
        return False


def get_metashape_version() -> str:
    if _Metashape is None:
        return "n/a"
    try:
        return str(_Metashape.app.version)
    except Exception:
        return "unknown"


class MetashapeWorkflow(PrepStagesMixin):
    """Wrapper around Agisoft Metashape's Python API for the standard
    photogrammetry pipeline. Supports a `mock_mode` for dry-runs without a
    valid license, and a `progress` callback for UI integration.

    The SDK-agnostic input-prep stages (``curate_input_set`` /
    ``equalize_exposures``) come from :class:`PrepStagesMixin`, shared with
    ``RealityCaptureWorkflow`` so the two engines can't drift apart.
    """

    PROJECT_EXT = "psx"

    def __init__(
        self,
        project_path: str = "./metashape_project",
        name: str = "metashape_project",
        mock_mode: Optional[bool] = None,
        progress: Optional[Callable[[str, float], None]] = None,
        gates: Optional[Dict[str, Dict[str, float]]] = None,
        gate_mode: str = "warn",
        checkpoint_each_stage: bool = True,
        save_project: bool = False,
    ):
        """
        Parameters:
            project_path: Filesystem directory for the project + outputs.
            name: Project basename (no extension).
            mock_mode: Force-enable mock mode. When None, mock mode is selected
                automatically if Metashape is unavailable or unlicensed.
            progress: Callback `fn(stage: str, fraction: float)` invoked at the
                start of each pipeline stage. `fraction` is in [0, 1].
            gates: Override acceptance-gate thresholds. See DEFAULT_GATES.
            gate_mode: ``"warn"`` (default, logs+continues) or ``"halt"`` (raises
                GateError on first failed gate).
            checkpoint_each_stage: When True, save the .psx after each major
                pipeline stage so runs are resumable.
            save_project: When True, produce a **reopenable** project — the .psx
                path is established at chunk creation (before depth maps/model)
                so Metashape streams all dense data into <name>.files; a late
                first save can leave .files empty. Default False (deliverables
                only — no .psx). Enables reopening to re-run later stages (e.g.
                re-texture) without redoing alignment/depth.
        """
        self.project_path = project_path
        self.name = name
        self.progress = progress
        self.gates = {**DEFAULT_GATES, **(gates or {})}
        self.gate_mode = gate_mode
        self.checkpoint_each_stage = bool(checkpoint_each_stage)
        self.save_project_enabled = bool(save_project)

        if mock_mode is None:
            mock_mode = not (is_metashape_available() and is_license_valid())
        self.mock_mode = bool(mock_mode)

        if self.mock_mode:
            self.doc = None
            self.chunk = None
        else:
            self.doc = _Metashape.Document()
            self.chunk = None

        self.qc = QcLog(os.path.join(project_path, f"{name}_qc.json"))
        self.qc.set("project_name", name)
        self.qc.set("project_path", project_path)
        self.qc.set("metashape_version", get_metashape_version())
        self.qc.set("licensed", is_license_valid())
        self.qc.set("mock_mode", self.mock_mode)
        self.gate = QcGate(self.gates, self.qc, mode=self.gate_mode)

    # ------------------------------------------------------------------ helpers

    def get_license_info(self) -> str:
        if _Metashape is None:
            return "Metashape module not installed"
        return f"Metashape {get_metashape_version()} ({'Licensed' if is_license_valid() else 'No valid license'})"

    def _notify(self, stage: str, fraction: float = 0.0) -> None:
        if self.progress is None:
            return
        try:
            self.progress(stage, float(fraction))
        except Exception as e:
            import sys
            print(f"[MetashapeWorkflow] progress callback raised: {e}", file=sys.stderr)

    @staticmethod
    def _camera_quality(cam: Any, default: Optional[float] = None) -> Optional[float]:
        """Per-camera ``Image/quality`` score (set by analyzeImages), or *default*.

        ``cam.meta`` is a ``Metashape.MetaData`` object: it supports ``[]`` but
        **not** ``.get()`` (calling ``.get`` raises ``AttributeError`` — a real
        bug that silently disabled dedupe). Read via subscript and fall back to
        *default* when the key is missing or unparseable.
        """
        try:
            return float(cam.meta["Image/quality"])
        except (KeyError, AttributeError, ValueError, TypeError):
            return default

    def _require_chunk(self) -> None:
        if self.mock_mode:
            return
        if self.chunk is None:
            raise RuntimeError("No chunk. Call create_chunk() first.")

    def _evaluate_gate(self, gate_name: str, metrics: Dict[str, Any]) -> bool:
        """Thin delegate to :class:`pythontk.QcGate`. Kept as a method for
        back-compat with existing engine call-sites + tests."""
        return self.gate.check(gate_name, metrics)

    @property
    def _project_file(self) -> str:
        """Absolute path of the ``.psx`` project (derives from project_path+name)."""
        return os.path.join(self.project_path, f"{self.name}.{self.PROJECT_EXT}")

    def _checkpoint(self, label: str) -> Optional[str]:
        """Idempotent .psx save. No-op in mock mode or when disabled."""
        if not self.checkpoint_each_stage or self.mock_mode:
            return None
        os.makedirs(self.project_path, exist_ok=True)
        out = self._project_file
        self.doc.save(path=out)
        print(f"[checkpoint:{label}] {out}")
        return out

    # ------------------------------------------------------------------ pipeline

    def create_chunk(self, label: str = "New Chunk"):
        self._notify("create_chunk", 0.0)
        if self.mock_mode:
            print(f"[mock] create_chunk('{label}')")
            return
        self.chunk = self.doc.addChunk()
        self.chunk.label = label
        if self.save_project_enabled:
            # Establish the project path NOW — before depth maps/model exist — so
            # Metashape streams all dense data into <name>.files as it computes.
            # A late first save can leave .files holding only metadata (empty
            # reopened project), which is exactly what we hit before.
            os.makedirs(self.project_path, exist_ok=True)
            self.doc.save(path=self._project_file)
            print(f"[project] established {self._project_file} (reopenable; incremental save on)")

    def add_images(self, image_sources: Union[str, Sequence[str]]):
        """Add images from a directory path (non-recursive) or list of paths."""
        self._notify("add_images", 0.0)
        self._require_chunk()

        with self.qc.stage("add_images") as st:
            if isinstance(image_sources, str):
                src_dir = image_sources
                st["source_dir"] = src_dir
                if self.mock_mode:
                    print(f"[mock] add_images from '{src_dir}'")
                    return
                if not os.path.isdir(src_dir):
                    raise ValueError(f"Directory not found: {src_dir}")
                files = [
                    os.path.join(src_dir, f)
                    for f in sorted(os.listdir(src_dir))
                    if f.lower().endswith(IMAGE_EXTS)
                ]
                if not files:
                    raise ValueError(f"No images found in directory: {src_dir}")
            else:
                files = list(image_sources)
                if not all(isinstance(p, str) for p in files):
                    raise TypeError("image_sources must be a path or list of paths")
                if self.mock_mode:
                    st["image_count"] = len(files)
                    print(f"[mock] add_images: {len(files)} file(s)")
                    return

            self.chunk.addPhotos(filenames=files)
            st["image_count"] = len(files)
            print(f"Added {len(files)} images to chunk.")

    def add_image_dirs(self, dirs: Sequence[str]):
        """Add images from multiple directories — flattens to one chunk."""
        self._notify("add_image_dirs", 0.0)
        self._require_chunk()
        with self.qc.stage("add_image_dirs") as st:
            st["dirs"] = list(dirs)
            files: List[str] = []
            for d in dirs:
                # Enumerate even in mock mode — listdir is cheap and the
                # QC sidecar gets a useful dry-run preview of input sizes.
                if not os.path.isdir(d):
                    if self.mock_mode:
                        st.setdefault("per_dir", []).append({"dir": d, "count": 0})
                        continue
                    raise ValueError(f"Directory not found: {d}")
                here = [
                    os.path.join(d, f)
                    for f in sorted(os.listdir(d))
                    if f.lower().endswith(IMAGE_EXTS)
                ]
                files.extend(here)
                st.setdefault("per_dir", []).append({"dir": d, "count": len(here)})
            st["total_image_count"] = len(files)
            if self.mock_mode:
                print(f"[mock] add_image_dirs: {len(dirs)} dir(s), {len(files)} images")
                return
            if not files:
                raise ValueError(f"No images found in any of: {dirs}")
            self.chunk.addPhotos(filenames=files)
            print(f"Added {len(files)} images from {len(dirs)} directories.")

    # curate_input_set / equalize_exposures are inherited from PrepStagesMixin.

    def clean_mesh_advanced(
        self,
        exported_model_path: Optional[str] = None,
        decimate_target_faces: int = 0,
    ) -> Optional[str]:
        """PyMeshLab post-export polish on the exported mesh file. Returns
        the cleaned mesh path (or None when PyMeshLab unavailable)."""
        self._notify("clean_mesh_advanced", 0.0)
        with self.qc.stage("clean_mesh_advanced") as st:
            if exported_model_path is None:
                exported_model_path = os.path.join(
                    self.project_path, f"{self.name}.obj"
                )
            st["input"] = exported_model_path
            try:
                from pythontk import MeshCleaner
            except ImportError:
                self.qc.warn("MeshCleaner not importable")
                return None
            cleaner = MeshCleaner()
            if not cleaner.is_available():
                self.qc.warn("pymeshlab not installed; skipping advanced cleanup.")
                print("pymeshlab not installed; skipping clean_mesh_advanced.")
                return None
            if self.mock_mode and not os.path.exists(exported_model_path):
                print(f"[mock] clean_mesh_advanced('{exported_model_path}')")
                return None
            result = cleaner.clean(
                exported_model_path, decimate_target_faces=decimate_target_faces
            )
            st["output"] = result
            return result

    def triage_images(self, quality_threshold: float = 0.5):
        """Run ``analyzePhotos`` and disable cameras below ``quality_threshold``.

        Metashape returns an image-quality score in [0, 1] per camera as
        ``camera.meta["Image/quality"]``; disabling low-quality cameras
        before alignment is the single highest-leverage step for noisy /
        blurry input sets.
        """
        self._notify("triage_images", 0.0)
        self._require_chunk()

        with self.qc.stage("triage") as st:
            st["quality_threshold"] = quality_threshold
            if self.mock_mode:
                print(f"[mock] triage_images(threshold={quality_threshold})")
                st["disabled"] = 0
                st["kept"] = 0
                return

            cameras = list(self.chunk.cameras)
            if not cameras:
                raise RuntimeError("No cameras to triage. Run add_images() first.")

            # Metashape 2.x renamed analyzePhotos -> analyzeImages; support both.
            analyze = getattr(self.chunk, "analyzeImages", None) or getattr(
                self.chunk, "analyzePhotos", None
            )
            if analyze is None:
                self.qc.warn(
                    "No analyzeImages/analyzePhotos on this Metashape version; "
                    "skipping triage (all cameras kept)."
                )
                st["skipped_reason"] = "no analyze API"
                return
            analyze(cameras=cameras)
            disabled = 0
            for cam in cameras:
                score = self._camera_quality(cam)
                if score is None:
                    continue
                if score < quality_threshold:
                    cam.enabled = False
                    disabled += 1
            kept = sum(1 for c in cameras if c.enabled)
            st["disabled"] = disabled
            st["kept"] = kept
            st["total"] = len(cameras)
            print(
                f"Triage: kept {kept}/{len(cameras)} cameras "
                f"(disabled {disabled} below quality {quality_threshold})."
            )
            self._checkpoint("triage")

    def align_photos(
        self,
        downscale: int = 2,
        generic_preselection: bool = True,
        reference_preselection: bool = True,
        keypoint_limit: int = 60000,
        tiepoint_limit: int = 10000,
        filter_mask: bool = False,
    ):
        # Baselines follow the verified-good recipe (TUNING.md), not Metashape's
        # stock minimums: generic_preselection matches the SDK/GUI default (True
        # — the lever that fully aligns featureless/specular captures), and
        # keypoint 60000 is the value verified on the hard 812-frame set (the
        # pre-2026-06 pipeline ran 100000; stock 40000 measurably under-aligns
        # low-texture subjects).
        self._notify("align_photos", 0.0)
        self._require_chunk()
        with self.qc.stage("align") as st:
            st["downscale"] = downscale
            # Record the matchPhotos levers so a QC sidecar captures exactly what
            # produced a given alignment (essential when A/B-ing hard captures).
            st["generic_preselection"] = generic_preselection
            st["keypoint_limit"] = keypoint_limit
            st["tiepoint_limit"] = tiepoint_limit
            st["filter_mask"] = filter_mask
            if self.mock_mode:
                print(f"[mock] align_photos(downscale={downscale})")
                return

            self.chunk.matchPhotos(
                downscale=downscale,
                generic_preselection=generic_preselection,
                reference_preselection=reference_preselection,
                keypoint_limit=keypoint_limit,
                tiepoint_limit=tiepoint_limit,
                filter_mask=filter_mask,
            )
            self.chunk.alignCameras()

            metrics = self._alignment_metrics()
            st.update(metrics)
            if not metrics["aligned_count"]:
                raise RuntimeError(
                    "No cameras aligned. Check image overlap or alignment params."
                )
            rms = metrics["rms_reproj_px"]
            rms_str = f"{rms:.3f}" if rms is not None else "n/a"
            print(
                f"Aligned {metrics['aligned_count']}/{metrics['total_count']} cameras "
                f"(RMS reproj {rms_str} px, "
                f"{metrics['tie_point_count']} tie points)."
            )

        self._evaluate_gate("align", metrics)
        self._checkpoint("align")

    def _alignment_metrics(self) -> Dict[str, Any]:
        """Snapshot of current chunk alignment quality.

        ``rms_reproj_px`` is left None unless the SDK exposes a direct
        accessor — computing it ad-hoc from projection scales is the
        wrong number (those are feature sizes, not residuals). Honest
        None lets the gate code skip the metric instead of firing on
        garbage.
        """
        if self.mock_mode or self.chunk is None:
            return {
                "aligned_count": 0,
                "total_count": 0,
                "aligned_pct": 0.0,
                "rms_reproj_px": None,
                "tie_point_count": 0,
            }
        aligned = [c for c in self.chunk.cameras if c.transform is not None]
        total = len(self.chunk.cameras)
        point_count = 0
        try:
            tie_points = self.chunk.tie_points or self.chunk.point_cloud
            point_count = len(tie_points.points) if tie_points else 0
        except Exception:
            pass
        return {
            "aligned_count": len(aligned),
            "total_count": total,
            "aligned_pct": round(100.0 * len(aligned) / total, 2) if total else 0.0,
            "rms_reproj_px": None,
            "tie_point_count": point_count,
        }

    def align_photos_with_retry(
        self,
        downscale: int = 2,
        generic_preselection: bool = True,
        reference_preselection: bool = True,
        keypoint_limit: int = 60000,
        tiepoint_limit: int = 10000,
        min_aligned_pct: float = 50.0,
        filter_mask: bool = False,
    ):
        """Run ``align_photos``; if the result fails ``min_aligned_pct``,
        retry once with the verified rescue levers: generic preselection on
        and doubled keypoint+tiepoint limits, at the **same** downscale.

        The retry deliberately does not drop to full-res matching: on the
        specular/low-texture captures where alignment actually fails,
        full-res (ds=1) measurably *over-fits* the specular noise and
        aligned worse than ds=2 (TUNING.md — 73.8% vs 90.4%); the levers
        that recovered a full solution were generic preselection + raised
        limits. The retry result replaces the first pass in-place, so the
        QC ``align_retry`` stage records both percentages — if the retry
        came out worse, re-run (alignment on hard sets is
        non-deterministic) rather than trusting the last solve.
        """
        self.align_photos(
            downscale=downscale,
            generic_preselection=generic_preselection,
            reference_preselection=reference_preselection,
            keypoint_limit=keypoint_limit,
            tiepoint_limit=tiepoint_limit,
            filter_mask=filter_mask,
        )
        if self.mock_mode:
            return

        metrics = self._alignment_metrics()
        if metrics["aligned_pct"] >= min_aligned_pct:
            return

        print(
            f"Align retry: {metrics['aligned_pct']:.1f}% < {min_aligned_pct}% - "
            f"retrying at downscale={downscale}, generic_preselection=True, "
            f"keypoint_limit={keypoint_limit * 2}, tiepoint_limit={tiepoint_limit * 2}."
        )
        with self.qc.stage("align_retry") as st:
            st["reason"] = (
                f"first-pass aligned_pct {metrics['aligned_pct']:.1f}% "
                f"< {min_aligned_pct}%"
            )
            st["first_pass_aligned_pct"] = metrics["aligned_pct"]
            self.chunk.matchPhotos(
                downscale=downscale,
                generic_preselection=True,
                reference_preselection=reference_preselection,
                keypoint_limit=keypoint_limit * 2,
                tiepoint_limit=tiepoint_limit * 2,
                filter_mask=filter_mask,
            )
            self.chunk.alignCameras()
            retry_metrics = self._alignment_metrics()
            st.update(retry_metrics)
            if retry_metrics["aligned_pct"] < metrics["aligned_pct"]:
                self.qc.warn(
                    f"align retry regressed: {metrics['aligned_pct']:.1f}% -> "
                    f"{retry_metrics['aligned_pct']:.1f}% aligned. The retry "
                    f"solve replaced the first pass; alignment on hard sets is "
                    f"non-deterministic - re-run rather than shipping this solve."
                )

    def refine_alignment(
        self,
        uncertainty_threshold: float = 15.0,
        reprojection_threshold: float = 0.5,
        projection_accuracy_threshold: float = 3.0,
    ):
        """Gradual-selection cleanup: iteratively filter tie points by
        Reconstruction Uncertainty → Reprojection Error → Projection
        Accuracy, with ``optimizeCameras(adaptive_fitting=True)`` between
        each pass. Standard Metashape QC.

        Thresholds are sane defaults for object-scale scenes; loosen for
        wide outdoor / drone captures.
        """
        self._notify("refine_alignment", 0.0)
        self._require_chunk()

        with self.qc.stage("refine_alignment") as st:
            if self.mock_mode:
                print(
                    f"[mock] refine_alignment(uncert={uncertainty_threshold}, "
                    f"reproj={reprojection_threshold}, "
                    f"proj_acc={projection_accuracy_threshold})"
                )
                st["passes"] = []
                return

            tie_points = self.chunk.tie_points or self.chunk.point_cloud
            if tie_points is None:
                raise RuntimeError(
                    "No tie points. Run align_photos() before refine_alignment()."
                )

            F = _Metashape.TiePoints.Filter
            passes = [
                ("ReconstructionUncertainty", F.ReconstructionUncertainty, uncertainty_threshold),
                ("ReprojectionError",         F.ReprojectionError,         reprojection_threshold),
                ("ProjectionAccuracy",        F.ProjectionAccuracy,        projection_accuracy_threshold),
            ]
            # Safety rails: a single absolute-threshold pass can decimate a sparse
            # cloud (e.g. ReprojectionError@0.5 removing 95% of points), after
            # which optimizeCameras drops *all* cameras and the alignment is gone.
            # Skip any pass that would remove too large a fraction or push the
            # cloud below a floor, and abort refine if the aligned-camera count
            # collapses. Dense sets clear these guards easily; sparse ones are
            # protected. ``max_removal_fraction`` / ``min_points_floor`` are
            # instance-overridable for callers that want a different risk profile.
            max_removal_fraction = getattr(self, "refine_max_removal_fraction", 0.5)
            min_points_floor = getattr(self, "refine_min_points_floor", 1000)
            n_aligned0 = sum(1 for c in self.chunk.cameras if c.transform is not None)
            results = []
            for label, criterion, threshold in passes:
                if threshold is None:
                    continue
                f = F()
                f.init(tie_points, criterion=criterion)
                total = len(tie_points.points)
                # Count points the threshold *would* remove without mutating yet.
                try:
                    vals = list(f.values)
                    n_remove = sum(1 for v in vals if v > threshold)
                except Exception:
                    vals, n_remove = None, None
                if n_remove is not None and total and (
                    n_remove / total > max_removal_fraction
                    or total - n_remove < min_points_floor
                ):
                    msg = (f"refine[{label}@{threshold}]: would remove "
                           f"{n_remove}/{total} ({100*n_remove/total:.0f}%) - "
                           f"skipped to protect the alignment")
                    self.qc.warn(msg)
                    print("  " + msg)
                    results.append({"filter": label, "threshold": threshold,
                                    "removed": 0, "kept": total, "skipped": True})
                    continue
                before = total
                f.removePoints(threshold)
                after = len(tie_points.points)
                self.chunk.optimizeCameras(
                    fit_f=True, fit_cx=True, fit_cy=True,
                    fit_b1=True, fit_b2=True,
                    fit_k1=True, fit_k2=True, fit_k3=True, fit_k4=False,
                    fit_p1=True, fit_p2=True,
                    adaptive_fitting=True,
                    tiepoint_covariance=False,
                )
                n_aligned = sum(1 for c in self.chunk.cameras if c.transform is not None)
                results.append({
                    "filter": label,
                    "threshold": threshold,
                    "removed": before - after,
                    "kept": after,
                    "aligned_after": n_aligned,
                })
                print(f"  refine[{label}@{threshold}]: removed {before - after}, "
                      f"kept {after} ({n_aligned} cameras aligned)")
                if n_aligned0 and n_aligned < 0.5 * n_aligned0:
                    self.qc.warn(
                        f"refine[{label}]: aligned cameras collapsed "
                        f"{n_aligned0}->{n_aligned}; aborting further refinement."
                    )
                    print(f"  refine: aligned cameras collapsed -> aborting refine.")
                    break
            st["passes"] = results
            st.update(self._alignment_metrics())

        self._checkpoint("refine_alignment")

    def dedupe_cameras_by_pose(
        self,
        translation_threshold: float = 0.02,
        rotation_threshold_deg: float = 2.0,
    ):
        """Cluster aligned cameras by pose and disable redundants.

        Two cameras within ``translation_threshold`` (in chunk units) AND
        ``rotation_threshold_deg`` of each other are considered duplicates;
        the one with higher image quality is kept. Speeds up dense /
        texture stages on noisy video where adjacent frames don't add
        SfM signal.

        CAVEAT — ``translation_threshold`` is in **chunk units**, and an
        unreferenced SfM solve's scale is arbitrary (it varies run to run),
        so the same 0.02 can cull nothing on one solve and real coverage on
        the next. Disabled cameras are excluded from depth mapping, not just
        texture. That's why the runner treats this stage as opt-in
        (``--dedupe-cameras``): only enable it on captures with genuinely
        redundant static footage, and check the QC ``disabled`` count.
        """
        self._notify("dedupe_cameras_by_pose", 0.0)
        self._require_chunk()

        with self.qc.stage("dedupe_cameras") as st:
            st["translation_threshold"] = translation_threshold
            st["rotation_threshold_deg"] = rotation_threshold_deg
            if self.mock_mode:
                print(
                    f"[mock] dedupe_cameras_by_pose(t={translation_threshold}, "
                    f"r={rotation_threshold_deg})"
                )
                st["disabled"] = 0
                return

            try:
                import math
                aligned = [c for c in self.chunk.cameras if c.transform and c.enabled]
                cos_thresh = math.cos(math.radians(rotation_threshold_deg))
                disabled = 0
                for i, cam_a in enumerate(aligned):
                    if not cam_a.enabled:
                        continue
                    ca = cam_a.transform.translation()
                    ra = cam_a.transform.rotation()
                    for cam_b in aligned[i + 1:]:
                        if not cam_b.enabled:
                            continue
                        cb = cam_b.transform.translation()
                        if (cb - ca).norm() > translation_threshold:
                            continue
                        rb = cam_b.transform.rotation()
                        # Relative rotation R_a^T R_b → trace gives cos(theta).
                        rel = ra.t() * rb
                        trace = rel[0, 0] + rel[1, 1] + rel[2, 2]
                        cos_angle = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
                        if cos_angle < cos_thresh:
                            continue
                        qa = self._camera_quality(cam_a, 1.0)
                        qb = self._camera_quality(cam_b, 1.0)
                        drop = cam_b if qa >= qb else cam_a
                        drop.enabled = False
                        disabled += 1
                        if drop is cam_a:
                            break
                st["disabled"] = disabled
                st["kept"] = sum(1 for c in aligned if c.enabled)
                print(f"Dedupe: disabled {disabled} redundant cameras.")
            except Exception as e:
                # Defensive: Vector/Matrix API surprises shouldn't crash
                # the rest of the pipeline. Surface as warning + skip.
                self.qc.warn(f"dedupe_cameras_by_pose skipped: {e}")
                st["skipped_reason"] = str(e)
                print(f"Dedupe skipped: {e}")
        self._checkpoint("dedupe_cameras")

    def calibrate_colors(self, source_data=None, white_balance: bool = True):
        """Run ``chunk.calibrateColors`` to equalize white-balance across
        cameras before texture bake. Cheap; meaningfully improves seam
        quality on mixed-lighting captures.
        """
        self._notify("calibrate_colors", 0.0)
        self._require_chunk()
        with self.qc.stage("calibrate_colors") as st:
            st["white_balance"] = white_balance
            if self.mock_mode:
                print(f"[mock] calibrate_colors(white_balance={white_balance})")
                return
            if source_data is None:
                # Sparse tie points are the right source pre-texture; the
                # model often doesn't exist yet at this pipeline point.
                source_data = _Metashape.DataSource.TiePointsData
            self.chunk.calibrateColors(
                source_data=source_data, white_balance=white_balance
            )
            print("Color calibration applied.")
        self._checkpoint("calibrate_colors")

    def generate_masks(
        self,
        source_dir: str,
        masks_dir: Optional[str] = None,
        model_name: str = "u2net",
    ) -> Optional[str]:
        """Run rembg on ``source_dir`` → write per-image alpha masks.

        Returns the masks directory path (or None when rembg/PIL unavailable).
        Suffix is ``_mask`` so it pairs with ``import_masks(template=...)``.
        Engine call only; UI wires this before :meth:`import_masks`.
        """
        self._notify("generate_masks", 0.0)
        masks_dir = masks_dir or os.path.join(self.project_path, "masks")
        with self.qc.stage("generate_masks") as st:
            st["source_dir"] = source_dir
            st["masks_dir"] = masks_dir
            st["model"] = model_name
            if self.mock_mode:
                print(
                    f"[mock] generate_masks('{source_dir}', model={model_name})"
                )
                return masks_dir
            try:
                from pythontk import MaskGenerator
            except ImportError:
                self.qc.warn("MaskGenerator not importable (pythontk missing?)")
                print("MaskGenerator import failed.")
                return None
            gen = MaskGenerator(model_name=model_name)
            if not gen.is_available():
                self.qc.warn(
                    "rembg+PIL not installed; install with "
                    "`pip install rembg pillow` to enable masks."
                )
                print("rembg not installed; skipping mask generation.")
                return None
            written = gen.generate_masks(source_dir, masks_dir)
            st["count"] = len(written)
            print(f"Generated {len(written)} masks -> {masks_dir}")
            return masks_dir if written else None

    def generate_masks_native(self, tolerance: int = 10) -> bool:
        """Background-mask every camera with Metashape's built-in AI masking
        (``generateMasks(masking_mode=MaskingModeAI)``, 2.2+).

        This is the preferred masking path when available: it runs entirely
        inside the SDK, so it works in the production headless context
        (``metashape.exe -r``) where the rembg file pipeline cannot —
        Metashape's bundled Python has no rembg/PIL/cv2. It does require the
        AI masking **neural model**, which Metashape downloads on first GUI
        use; on a machine that has never run AI masking interactively the
        call fails (verified live on 2.2.0: "Can't open file" while
        "Creating model from config") and this method degrades gracefully.
        Returns True when masks were generated (mock mode included); False
        when the SDK predates ``MaskingModeAI`` or the model is absent — the
        caller then falls back to :meth:`generate_masks` +
        :meth:`import_masks` (file-based; verified live: 20/20 masks paired
        via the path template on 2.2.0).
        """
        self._notify("generate_masks_native", 0.0)
        self._require_chunk()
        with self.qc.stage("masks_native") as st:
            st["backend"] = "MaskingModeAI"
            st["tolerance"] = tolerance
            if self.mock_mode:
                print("[mock] generate_masks_native()")
                return True
            mode = getattr(
                getattr(_Metashape, "MaskingMode", None), "MaskingModeAI", None
            )
            if mode is None:
                self.qc.warn(
                    "This Metashape has no MaskingModeAI (needs 2.2+); "
                    "use the file-based mask pipeline instead."
                )
                st["fallback"] = "no_MaskingModeAI"
                return False
            try:
                # path='' — the default ('{filename}_mask.png') is a FILE
                # template, and in AI mode 2.2.0 misreads it as the neural
                # model config path ("Can't open file: {filename}_mask.png",
                # verified live).
                self.chunk.generateMasks(
                    path="",
                    masking_mode=mode,
                    mask_operation=_Metashape.MaskOperation.MaskOperationReplacement,
                    tolerance=tolerance,
                )
            except Exception as e:  # noqa: BLE001 — masking must not kill a run
                self.qc.warn(
                    f"native AI masking failed ({e}). Metashape downloads its "
                    f"AI masking model on first GUI use - run Generate Masks "
                    f"(AI) once in the GUI on this machine, or use the "
                    f"file-based pipeline (rembg masks + import_masks)."
                )
                st["fallback"] = f"generateMasks_failed: {e}"
                return False
            applied = sum(1 for c in self.chunk.cameras if c.mask is not None)
            st["applied"] = applied
            print(f"AI masks generated: {applied}/{len(self.chunk.cameras)} cameras.")
        self._checkpoint("masks_native")
        return True

    def import_masks(
        self,
        masks_dir: str,
        mask_source: str = "file",
        template: str = "{filename}_mask.png",
    ):
        """Import per-camera masks from a directory.

        ``template`` must match the per-image mask filenames written by
        :class:`pythontk.MaskGenerator` (default: ``{filename}_mask.png``).
        Without a correct template Metashape can't pair masks to cameras.

        ``mask_source`` is one of ``"file"`` (separate mask file — the
        common rembg case), ``"alpha"`` (alpha channel of the source),
        or ``"background"`` (Metashape's auto-background).

        Metashape 2.x removed ``importMasks`` (and the ``MaskSource`` enum);
        file/alpha/background import is now ``generateMasks`` with the
        matching ``MaskingMode`` and ``path`` as the directory-qualified
        filename template (verified live on 2.2.0).
        """
        self._notify("import_masks", 0.0)
        self._require_chunk()
        with self.qc.stage("masks") as st:
            st["masks_dir"] = masks_dir
            st["mask_source"] = mask_source
            st["template"] = template
            if self.mock_mode:
                print(
                    f"[mock] import_masks('{masks_dir}', source={mask_source}, "
                    f"template={template})"
                )
                return
            if not os.path.isdir(masks_dir):
                raise ValueError(f"Masks directory not found: {masks_dir}")
            modes = {
                "alpha":      _Metashape.MaskingMode.MaskingModeAlpha,
                "file":       _Metashape.MaskingMode.MaskingModeFile,
                "background": _Metashape.MaskingMode.MaskingModeBackground,
            }
            mode = modes.get(mask_source.lower())
            if mode is None:
                raise ValueError(
                    f"Unsupported mask_source: {mask_source}. "
                    f"Supported: {list(modes)}"
                )
            kwargs = dict(
                path=os.path.join(masks_dir, template),
                masking_mode=mode,
                mask_operation=_Metashape.MaskOperation.MaskOperationReplacement,
            )
            # MaskOperationReplacement over ALL cameras could clear masks a
            # previous per-source dir's call just applied (multi-capture
            # --input-root runs call this once per dir) — scope the call to
            # the cameras whose mask file actually lives in THIS dir when the
            # template lets us resolve it.
            run_call = True
            if mode == _Metashape.MaskingMode.MaskingModeFile and (
                "{filename}" in template
            ):
                matched = []
                for cam in self.chunk.cameras:
                    photo_path = getattr(
                        getattr(cam, "photo", None), "path", None
                    )
                    if not photo_path:
                        continue
                    stem = os.path.splitext(os.path.basename(photo_path))[0]
                    candidate = template.replace("{filename}", stem)
                    if "{" not in candidate and os.path.isfile(
                        os.path.join(masks_dir, candidate)
                    ):
                        matched.append(cam)
                st["matched"] = len(matched)
                if matched:
                    kwargs["cameras"] = matched
                else:
                    print(
                        f"No mask files in {masks_dir} match this chunk's "
                        f"cameras; skipping (masks from other dirs kept)."
                    )
                    run_call = False
            if run_call:
                self.chunk.generateMasks(**kwargs)
            applied = sum(1 for c in self.chunk.cameras if c.mask is not None)
            st["applied"] = applied
            print(f"Masks imported: {applied}/{len(self.chunk.cameras)} cameras.")
        self._checkpoint("masks")

    def generate_depth_maps(self, downscale: int = 2, filter_mode=None):
        self._notify("generate_depth_maps", 0.0)
        self._require_chunk()
        with self.qc.stage("depth") as st:
            st["downscale"] = downscale
            # Accept a portable string preset so callers (the runner) need not
            # import Metashape enums: mild / moderate / aggressive / none. Mirrors
            # build_model's face_count string handling. Recorded in QC either way.
            if isinstance(filter_mode, str):
                st["depth_filter"] = filter_mode.lower()
            if self.mock_mode:
                print(f"[mock] generate_depth_maps(downscale={downscale}, "
                      f"filter_mode={filter_mode})")
                return

            if isinstance(filter_mode, str):
                filter_mode = {
                    "mild": _Metashape.MildFiltering,
                    "moderate": _Metashape.ModerateFiltering,
                    "aggressive": _Metashape.AggressiveFiltering,
                    "none": _Metashape.NoFiltering,
                }.get(filter_mode.lower(), _Metashape.MildFiltering)
            if filter_mode is None:
                filter_mode = _Metashape.MildFiltering

            if not any(c.transform is not None for c in self.chunk.cameras):
                raise RuntimeError("No cameras aligned. Run align_photos() first.")

            self.chunk.buildDepthMaps(
                downscale=downscale, filter_mode=filter_mode, reuse_depth=False
            )
            print("Depth maps generated.")
        self._checkpoint("depth")

    def build_model(
        self,
        source_data=None,
        surface_type=None,
        interpolation=None,
        face_count=None,
    ):
        self._notify("build_model", 0.0)
        self._require_chunk()
        with self.qc.stage("model") as st:
            st["face_count"] = face_count
            if self.mock_mode:
                print(f"[mock] build_model(face_count={face_count})")
                return

            if source_data is None:
                source_data = _Metashape.DataSource.DepthMapsData
            if surface_type is None:
                surface_type = _Metashape.SurfaceType.Arbitrary
            if interpolation is None:
                interpolation = _Metashape.Interpolation.EnabledInterpolation
            # Accept a portable string preset so callers (the runner) need not
            # import Metashape enums: low / medium / high (Metashape's FaceCount).
            if isinstance(face_count, str):
                face_count = {
                    "low": _Metashape.LowFaceCount,
                    "medium": _Metashape.MediumFaceCount,
                    "high": _Metashape.HighFaceCount,
                }.get(face_count.lower(), _Metashape.MediumFaceCount)
            elif face_count is None:
                face_count = _Metashape.MediumFaceCount

            if source_data == _Metashape.DataSource.DepthMapsData and not self.chunk.depth_maps:
                raise RuntimeError("Depth maps not found. Run generate_depth_maps() first.")

            self.chunk.buildModel(
                source_data=source_data,
                surface_type=surface_type,
                interpolation=interpolation,
                face_count=face_count,
            )
            metrics = self._mesh_metrics()
            st.update(metrics)
            lpct = metrics["largest_component_pct"]
            lpct_str = f"{lpct:.1f}%" if lpct is not None else "n/a"
            print(
                f"Model built: {metrics['faces']} faces, "
                f"{metrics['components']} components, "
                f"largest {lpct_str} of total."
            )

        self._evaluate_gate("model", metrics if not self.mock_mode else {})
        self._checkpoint("model")

    def _mesh_metrics(self) -> Dict[str, Any]:
        """Snapshot of current chunk mesh quality.

        ``components`` / ``largest_component_pct`` are left None unless
        we wire a proper connected-components walk — the SDK statistics
        object doesn't expose them in 2.x. Returning honest None is
        better than defaulting to "1 component / 100%" which would mute
        the mesh gate entirely.
        """
        if self.mock_mode or self.chunk is None or self.chunk.model is None:
            return {
                "faces": 0,
                "vertices": 0,
                "components": None,
                "largest_component_pct": None,
            }
        model = self.chunk.model
        return {
            "faces": len(model.faces),
            "vertices": len(model.vertices),
            "components": None,
            "largest_component_pct": None,
        }

    def clean_mesh(
        self,
        remove_components_face_threshold: int = 100,
        close_holes_level: int = 30,
        smooth_strength: int = 0,
    ):
        """Mesh cleanup chain: ``removeComponents → closeHoles → smoothModel``.

        Defaults are conservative — drop floater islands smaller than 100
        faces, close holes up to 30% of mesh, no smoothing. Skip individual
        steps by passing 0.
        """
        self._notify("clean_mesh", 0.0)
        self._require_chunk()
        with self.qc.stage("clean_mesh") as st:
            st["remove_components_face_threshold"] = remove_components_face_threshold
            st["close_holes_level"] = close_holes_level
            st["smooth_strength"] = smooth_strength
            if self.mock_mode:
                print(
                    f"[mock] clean_mesh(remove<{remove_components_face_threshold}, "
                    f"closeHoles={close_holes_level}, smooth={smooth_strength})"
                )
                return

            if not self.chunk.model:
                raise RuntimeError("No model to clean. Run build_model() first.")

            before = self._mesh_metrics()
            st["before"] = before

            if remove_components_face_threshold > 0:
                self.chunk.model.removeComponents(remove_components_face_threshold)
            if close_holes_level > 0:
                self.chunk.model.closeHoles(level=close_holes_level)
            if smooth_strength > 0:
                self.chunk.smoothModel(strength=smooth_strength)

            after = self._mesh_metrics()
            st["after"] = after
            print(
                f"Mesh cleaned: {before['faces']}->{after['faces']} faces, "
                f"{before['components']}->{after['components']} components."
            )
        self._checkpoint("clean_mesh")

    def reduce_overlap(self, target_overlap: int = 9):
        """Thin redundant cameras for texture bake while preserving
        geometric coverage. Faster bake, cleaner mosaic.
        """
        self._notify("reduce_overlap", 0.0)
        self._require_chunk()
        with self.qc.stage("reduce_overlap") as st:
            st["target_overlap"] = target_overlap
            if self.mock_mode:
                print(f"[mock] reduce_overlap(target={target_overlap})")
                return
            if not self.chunk.model:
                raise RuntimeError("No model. Run build_model() before reduce_overlap.")
            try:
                self.chunk.reduceOverlap(overlap=target_overlap)
            except (AttributeError, TypeError) as e:
                self.qc.warn(
                    f"chunk.reduceOverlap not available / signature mismatch: {e}"
                )
                print(f"reduceOverlap skipped: {e}")
                return
            enabled = sum(1 for c in self.chunk.cameras if c.enabled)
            st["enabled_cameras"] = enabled
            print(f"reduce_overlap: {enabled} cameras left enabled.")
        self._checkpoint("reduce_overlap")

    def build_texture(
        self,
        texture_size: int = 8192,
        texture_type=None,
        blending_mode=None,
        mapping_mode=None,
        ghosting_filter: bool = True,
    ):
        # 8192 matches the documented pipeline default (the runner's
        # ``--texture-size auto`` fallback and derive_texture_size cap); the
        # old 4096 only ever bit direct engine callers.
        self._notify("build_texture", 0.0)
        self._require_chunk()
        with self.qc.stage("texture") as st:
            st["size"] = texture_size
            if self.mock_mode:
                print(f"[mock] build_texture(size={texture_size})")
                return

            if not self.chunk.model:
                raise RuntimeError("No model. Run build_model() first.")

            if texture_type is None:
                texture_type = _Metashape.Model.TextureType.DiffuseMap
            if blending_mode is None:
                blending_mode = _Metashape.BlendingMode.MosaicBlending
            if mapping_mode is None:
                mapping_mode = _Metashape.MappingMode.GenericMapping

            if not getattr(self.chunk.model, "uv_sets", None):
                print("UV mapping missing - generating...")
                self.chunk.buildUV(mapping_mode=mapping_mode)

            self.chunk.buildTexture(
                texture_type=texture_type,
                blending_mode=blending_mode,
                texture_size=texture_size,
                ghosting_filter=ghosting_filter,
            )
            metrics = self._texture_metrics()
            st.update(metrics)
            print(
                f"Texture built: {texture_size}px, coverage "
                f"{metrics.get('coverage_pct', 'n/a')}%"
            )

        self._evaluate_gate("texture", metrics if not self.mock_mode else {})
        self._checkpoint("texture")

    def _texture_metrics(self) -> Dict[str, Any]:
        """Texture coverage isn't readable through the documented Image
        API without copying the full buffer; leave the measurement to
        a future Phase that exports the texture to disk and runs cv2
        over it. The gate code already skips ``None``-valued metrics
        with an honest warning.
        """
        return {"coverage_pct": None}

    def save_project(self):
        self._notify("save_project", 0.0)
        with self.qc.stage("save") as st:
            if self.mock_mode:
                print("[mock] save_project")
                return

            os.makedirs(self.project_path, exist_ok=True)
            out = self._project_file
            self.doc.save(path=out)
            st["path"] = out
            print(f"Saved project: {out}")

    def export_model(
        self,
        export_format=None,
        binary: bool = True,
        precision: int = 6,
        texture_format=None,
        save_texture: bool = True,
        save_normals: bool = True,
        save_colors: bool = True,
        save_cameras: bool = False,
        overwrite: bool = True,
        save_usdz: bool = True,
    ):
        self._notify("export_model", 0.0)
        with self.qc.stage("export") as st:
            if self.mock_mode:
                print("[mock] export_model")
                return

            if not self.chunk:
                raise RuntimeError("No active chunk.")
            if not self.chunk.model:
                raise RuntimeError("No model. Build the model before exporting.")

            if export_format is None:
                export_format = _Metashape.ModelFormatOBJ
            if texture_format is None:
                texture_format = _Metashape.ImageFormat.ImageFormatPNG

            format_extensions = {
                _Metashape.ModelFormatOBJ: "obj",
                _Metashape.ModelFormatPLY: "ply",
                _Metashape.ModelFormatSTL: "stl",
                _Metashape.ModelFormatFBX: "fbx",
            }
            if export_format not in format_extensions:
                raise ValueError(
                    f"Unsupported export format: {export_format}. "
                    f"Supported: {list(format_extensions.values())}"
                )

            extension = format_extensions[export_format]
            export_path = os.path.join(self.project_path, f"{self.name}.{extension}")

            if not overwrite and os.path.exists(export_path):
                raise FileExistsError(
                    f"'{export_path}' exists. Pass overwrite=True to replace it."
                )

            self.chunk.exportModel(
                path=export_path,
                binary=binary,
                precision=precision,
                texture_format=texture_format,
                save_texture=save_texture,
                save_normals=save_normals,
                save_colors=save_colors,
                save_cameras=save_cameras,
                format=export_format,
            )
            st["path"] = export_path
            print(f"Exported model: {export_path}")

            # AR/QuickLook review sidecar beside the OBJ — authored zero-dep
            # by pythontk (no DCC, no extra SDK), so it lands in project_path
            # and rides the existing publish copy. Best-effort: a sidecar
            # failure never fails the export stage.
            if save_usdz and extension == "obj":
                st["usdz"] = self._export_usdz_sidecar(export_path)

    def export_colmap(
        self,
        output_dir: str,
        convert_to_pinhole: bool = True,
        binary: bool = True,
        max_cameras: int = 0,
    ) -> Optional[str]:
        """Export the aligned chunk as a COLMAP dataset to feed the splat track.

        Produces the layout Brush and SuGaR's ``train_full_pipeline.py -s <dir>``
        consume::

            <output_dir>/images/                      copied source frames
            <output_dir>/sparse/0/cameras.bin         (single pinhole model)
            <output_dir>/sparse/0/images.bin          camera poses + keypoints
            <output_dir>/sparse/0/points3D.bin        sparse cloud (3DGS init)

        Implementation matches the verified Metashape 2.2.0 behaviour:

        * ``exportCameras(format=CamerasFormatColmap)`` **rejects a bare directory**
          as ``path`` (``OSError: Access is denied``). It wants a *file* path inside
          the target dir and lays the COLMAP tree out beside it — so we pass
          ``<output_dir>/colmap.txt`` and let it create ``images/`` + ``sparse/0/``.
        * ``convert_to_pinhole=True`` maps Metashape's distortion model onto a COLMAP
          pinhole camera, which the 3DGS dataset loaders require.
        * ``binary=True`` writes ``*.bin`` (smaller; loaders read both).

        ``max_cameras`` (>0) evenly strides the aligned cameras down to roughly that
        many before export — the gaussian-splat trainers (esp. SuGaR's bundled
        vanilla-3DGS on an 8 GB GPU) bog down badly past a few hundred views, so a
        capped export keeps the splat track tractable without disabling cameras on
        the chunk (the ``cameras=`` arg is non-destructive). Returns ``output_dir``.
        """
        self._notify("export_colmap", 0.0)
        self._require_chunk()
        with self.qc.stage("export_colmap") as st:
            st["output_dir"] = output_dir
            st["convert_to_pinhole"] = convert_to_pinhole
            st["binary"] = binary
            st["max_cameras"] = max_cameras
            if self.mock_mode:
                print(f"[mock] export_colmap -> {output_dir} (images/ + sparse/0/)")
                return output_dir

            os.makedirs(output_dir, exist_ok=True)
            aligned = [c for c in self.chunk.cameras if c.transform is not None and c.enabled]
            st["aligned_cameras"] = len(aligned)
            if not aligned:
                raise RuntimeError(
                    "No aligned cameras to export. Run align_photos() first."
                )

            export_cameras = aligned
            if max_cameras and len(aligned) > max_cameras:
                # Even index selection to *exactly* the cap. A ceil-stride
                # slice under-shoots badly (812 cams, cap 350 -> stride 3 ->
                # 271 exported, ~23% below the budget the trainer could use);
                # picking round(i * N / cap) indices spends the whole cap
                # while staying evenly spread over the capture.
                n = len(aligned)
                indices = sorted({
                    min(n - 1, int(round(i * n / float(max_cameras))))
                    for i in range(max_cameras)
                })
                export_cameras = [aligned[i] for i in indices]
                print(
                    f"COLMAP export: evenly sampling {len(aligned)} aligned "
                    f"cameras -> {len(export_cameras)} (cap {max_cameras})."
                )
            st["exported_cameras"] = len(export_cameras)

            # path must be a FILE inside output_dir; the COLMAP tree is created
            # alongside it. The colmap.txt itself is an incidental index file.
            nominal = os.path.join(output_dir, "colmap.txt")
            kwargs = dict(
                path=nominal,
                format=_Metashape.CamerasFormat.CamerasFormatColmap,
                convert_to_pinhole=convert_to_pinhole,
                binary=binary,
            )
            if max_cameras and len(export_cameras) != len(aligned):
                kwargs["cameras"] = export_cameras
            self.chunk.exportCameras(**kwargs)

            sparse0 = os.path.join(output_dir, "sparse", "0")
            cam_file = os.path.join(sparse0, "cameras.bin" if binary else "cameras.txt")
            ok = os.path.isdir(sparse0) and os.path.isfile(cam_file)
            st["sparse_dir"] = sparse0
            st["images_dir"] = os.path.join(output_dir, "images")
            st["ok"] = ok
            if not ok:
                self.qc.warn(
                    f"COLMAP export did not produce {cam_file}; "
                    f"check write permissions on {output_dir}."
                )
            print(f"COLMAP dataset -> {output_dir} (sparse/0 present={ok})")
            return output_dir

    def export_qc(self):
        """Write Metashape's processing report PDF + finalize the JSON sidecar.

        Safe to call at the end of any pipeline (success or failure path) —
        ``finalize_run`` is what commits the sidecar to disk.
        """
        self._notify("export_qc", 0.0)
        with self.qc.stage("report") as st:
            if self.mock_mode:
                print("[mock] export_qc")
                return
            if self.chunk is None:
                return
            report_path = os.path.join(self.project_path, f"{self.name}_report.pdf")
            try:
                self.chunk.exportReport(path=report_path, title=self.name)
                st["report_pdf"] = report_path
                print(f"Report: {report_path}")
            except Exception as e:
                self.qc.warn(f"exportReport failed: {e}")
                print(f"exportReport failed: {e}")

    def finalize_run(self, success: bool = True) -> str:
        """Write the QC JSON sidecar. Returns the sidecar path.

        Always call this in the slot's ``finally`` block so even failed
        runs leave a usable diagnostic on disk.
        """
        self.qc.finalize(success)
        print(f"QC sidecar: {self.qc.path}")
        return self.qc.path


def get_image_filepaths(directory: str) -> List[str]:
    """Return absolute paths to all images in `directory` (non-recursive)."""
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")
    return [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.lower().endswith(IMAGE_EXTS)
    ]


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Metashape workflow.")
    parser.add_argument("--frames", required=True, help="Source frames directory.")
    parser.add_argument("--project", required=True, help="Project output directory.")
    parser.add_argument("--name", default=None, help="Project basename.")
    args = parser.parse_args()

    name = args.name or os.path.basename(os.path.normpath(args.project))
    mp = MetashapeWorkflow(args.project, name=name)
    print(mp.get_license_info())
    try:
        mp.create_chunk(f"{name} Chunk")
        mp.add_images(args.frames)
        mp.triage_images()
        mp.align_photos(downscale=2)
        mp.refine_alignment()
        mp.generate_depth_maps(downscale=2)
        mp.build_model()
        mp.build_texture()
        mp.save_project()
        mp.export_model()
        mp.export_qc()
        mp.finalize_run(success=True)
    except Exception:
        mp.finalize_run(success=False)
        raise
