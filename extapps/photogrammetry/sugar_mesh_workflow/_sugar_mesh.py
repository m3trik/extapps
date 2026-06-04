# !/usr/bin/python
# coding=utf-8
"""SuGaR mesh-extraction workflow engine.

Wraps SuGaR's ``train_full_pipeline.py`` (https://github.com/Anttwo/SuGaR) via
:mod:`subprocess`, mirroring the structure of
:class:`extapps.photogrammetry.gaussian_splat_workflow._gaussian_splat_workflow.GaussianSplatWorkflow`
(dir/env discovery, QC log, mock mode, per-stage logging).

Pipeline: a **COLMAP dataset** (``images/`` + ``sparse/0/``) → SuGaR trains its
own vanilla 3DGS → fits + refines a SuGaR model → extracts a UV-textured ``.obj``
mesh (COLMAP-in / mesh-out).

PERFORMANCE — read before an unattended run
--------------------------------------------
SuGaR's *bundled vanilla-3DGS* (Inria reference impl) is memory-heavy. On an
8 GB GPU it bogs to ~20 s/iter once the view count climbs past a few hundred, so
a large camera set can ETA the 7k-iter vanilla stage at tens of hours. Two
requirements for the SuGaR mesh to complete overnight:

* **Cap the camera count.** Feed a *subsampled* COLMAP export — Metashape's
  ``--colmap-max-cameras 300-400`` strides the aligned cameras down. 300-400
  good views reconstruct the same surface; the extra thousand only thrash VRAM.
* **Free the GPU.** No other CUDA tenant (e.g. a concurrent training / inference
  job) during the run — contention is a prime cause of the 20 s/iter wall.

Brush, by contrast, handles the full camera set efficiently — use it for the
splat ``.ply``; use this for the mesh deliverable. (A Brush-splat → SuGaR-mesh
shortcut that skips vanilla-3DGS is *not* wired into SuGaR upstream, so it is
not an option here.)
"""
import os
import glob
import subprocess
import time
from typing import Callable, List, Optional

from pythontk import QcLog

from ..profile import configured_app_path


def _is_sugar_dir(path: Optional[str]) -> bool:
    """True if *path* is a SuGaR repo dir (holds ``train_full_pipeline.py``)."""
    return bool(path) and os.path.isfile(
        os.path.join(path, "train_full_pipeline.py")
    )


def find_sugar_dir() -> Optional[str]:
    """Return the SuGaR repo dir or None.

    SuGaR is a cloned repo (its root holds ``train_full_pipeline.py``) with no
    canonical install location, so discovery is the ``SUGAR_DIR`` env override
    (honored strictly: set-but-invalid returns None so the caller enters mock
    mode), then the profile's ``apps.sugar_dir`` (network / non-standard repo).
    Point ``SUGAR_DIR`` at the repo, or set ``apps.sugar_dir`` in the profile.
    """
    env = os.environ.get("SUGAR_DIR")
    if env:
        return env if _is_sugar_dir(env) else None
    configured = configured_app_path("sugar_dir")
    return configured if _is_sugar_dir(configured) else None


def is_sugar_available() -> bool:
    return find_sugar_dir() is not None


class SugarMeshWorkflow:
    """COLMAP dataset → SuGaR refined textured ``.obj`` mesh."""

    def __init__(
        self,
        project_path: str = "./sugar_project",
        name: str = "sugar",
        sugar_dir: Optional[str] = None,
        env_bat: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        progress: Optional[Callable[[str, float], None]] = None,
        timeout_sec: int = 86400,
    ):
        self.project_path = project_path
        self.name = name
        self.progress = progress
        self.timeout_sec = timeout_sec

        self.sugar_dir = sugar_dir or find_sugar_dir()
        # The env activator (sets the MSVC toolset + activates the conda env);
        # nvdiffrast JIT-compiles at the textured-mesh step, so the build env
        # must be live for the whole run.
        if env_bat is None and self.sugar_dir:
            cand = os.path.join(self.sugar_dir, "sugar_buildenv.bat")
            env_bat = cand if os.path.isfile(cand) else None
        self.env_bat = env_bat

        if mock_mode is None:
            mock_mode = self.sugar_dir is None
        self.mock_mode = bool(mock_mode)

        os.makedirs(self.project_path, exist_ok=True)
        self._logs_dir = os.path.join(self.project_path, "logs")
        os.makedirs(self._logs_dir, exist_ok=True)

        self.qc = QcLog(os.path.join(self.project_path, f"{name}_qc.json"))
        self.qc.set("project_name", name)
        self.qc.set("sugar_dir", self.sugar_dir or "")
        self.qc.set("env_bat", self.env_bat or "")
        self.qc.set("mock_mode", self.mock_mode)

    # ----------------------------------------------------------- helpers

    def get_sugar_info(self) -> str:
        if self.sugar_dir is None:
            return "SuGaR not found (set SUGAR_DIR env or install)"
        env = self.env_bat or "(no sugar_buildenv.bat — env may be inactive)"
        return f"SuGaR ({self.sugar_dir}) via {env}"

    def _notify(self, stage: str, fraction: float = 0.0) -> None:
        if self.progress is None:
            return
        try:
            self.progress(stage, float(fraction))
        except Exception as e:
            import sys
            print(f"[SugarMeshWorkflow] progress callback raised: {e}",
                  file=sys.stderr)

    @staticmethod
    def _b(value: bool) -> str:
        """SuGaR's argparse uses str2bool — pass explicit True/False tokens."""
        return "True" if value else "False"

    def _scene_name(self, colmap_dir: str) -> str:
        return os.path.basename(os.path.normpath(colmap_dir))

    # ----------------------------------------------------------- pipeline

    def extract_mesh(
        self,
        colmap_dir: str,
        regularization: str = "dn_consistency",
        high_poly: bool = True,
        refinement_time: str = "short",
        surface_level: float = 0.3,
        export_obj: bool = True,
        export_ply: bool = False,
        use_eval_split: bool = False,
        gpu: int = 0,
        white_background: bool = False,
    ) -> Optional[str]:
        """Run SuGaR's full pipeline on a COLMAP dataset; return the OBJ path.

        Mirrors SuGaR's documented ``train_full_pipeline.py`` invocation::

            python train_full_pipeline.py -s <colmap_dir> -r dn_consistency \\
                --high_poly True --refinement_time short --export_obj True \\
                --export_ply False --eval False --gpu 0

        ``regularization`` is one of ``sdf`` / ``density`` / ``dn_consistency``
        (the last is SuGaR's recommended best-mesh option). ``refinement_time``
        is ``short`` / ``medium`` / ``long`` (2k / 7k / 15k refinement iters).
        Outputs land under ``<sugar_dir>/output/`` (cwd-relative); the textured
        mesh is written below ``output/refined_mesh/<scene>/``.
        """
        self._notify("extract_mesh", 0.0)
        scene = self._scene_name(colmap_dir)
        with self.qc.stage("sugar_mesh") as st:
            st["colmap_dir"] = colmap_dir
            st["scene"] = scene
            st["regularization"] = regularization
            st["high_poly"] = high_poly
            st["refinement_time"] = refinement_time
            st["surface_level"] = surface_level

            py_args = (
                f'python train_full_pipeline.py '
                f'-s "{colmap_dir}" '
                f'-r {regularization} '
                f'--high_poly {self._b(high_poly)} '
                f'--refinement_time {refinement_time} '
                f'--surface_level {surface_level} '
                f'--export_obj {self._b(export_obj)} '
                f'--export_ply {self._b(export_ply)} '
                f'--eval {self._b(use_eval_split)} '
                f'--white_background {self._b(white_background)} '
                f'--gpu {gpu}'
            )
            st["command"] = py_args

            if self.mock_mode:
                print(f"[mock:sugar_mesh] {py_args}")
                fake = os.path.join(
                    self.project_path, f"{scene}_sugar.obj"
                )
                st["mesh_obj"] = fake
                return fake

            if not os.path.isdir(colmap_dir):
                raise ValueError(f"COLMAP dataset not found: {colmap_dir}")
            sparse0 = os.path.join(colmap_dir, "sparse", "0")
            if not os.path.isdir(sparse0):
                raise ValueError(
                    f"COLMAP dataset missing sparse/0/: {sparse0}. "
                    f"Export from Metashape with --export-colmap."
                )

            start = time.time()
            run_bat = self._write_run_bat(py_args)
            log_path = os.path.join(self._logs_dir, "sugar_mesh.log")
            print(f"[sugar_mesh] {run_bat}  >> {log_path}")
            with open(log_path, "w", encoding="utf-8", errors="replace") as log:
                log.write(f"# cmd: {py_args}\n")
                log.flush()
                completed = subprocess.run(
                    ["cmd", "/c", run_bat],
                    timeout=self.timeout_sec, stdout=log,
                    stderr=subprocess.STDOUT,
                )
            st["returncode"] = completed.returncode
            if completed.returncode != 0:
                raise RuntimeError(
                    f"SuGaR failed (exit {completed.returncode}). A vanilla-3DGS "
                    f"stall (~20 s/iter) usually means too many cameras for the "
                    f"GPU or a busy GPU — cap the COLMAP export and free the GPU. "
                    f"See {log_path}."
                )

            mesh = self._find_output_obj(scene, since=start)
            st["mesh_obj"] = mesh
            if mesh:
                print(f"SuGaR mesh -> {mesh}")
            else:
                self.qc.warn(
                    "SuGaR returned success but no .obj was found under "
                    f"{os.path.join(self.sugar_dir, 'output')} for scene '{scene}'."
                )
            return mesh

    def _write_run_bat(self, py_args: str) -> str:
        """Write a batch that activates the SuGaR env and runs the pipeline.
        Returns the batch path."""
        lines = ["@echo off"]
        if self.env_bat:
            lines.append(f'call "{self.env_bat}"')
        lines.append(f'cd /d "{self.sugar_dir}"')
        lines.append(py_args)
        lines.append("echo SUGAR_EXIT=%errorlevel%")
        bat = os.path.join(self._logs_dir, "run_sugar.bat")
        with open(bat, "w", encoding="utf-8") as fh:
            fh.write("\r\n".join(lines) + "\r\n")
        return bat

    def _find_output_obj(self, scene: str, since: float) -> Optional[str]:
        """Locate the textured OBJ SuGaR wrote for this scene.

        SuGaR writes refined meshes under ``output/refined_mesh/<scene>/``; we
        glob there first, then fall back to any ``.obj`` under ``output/``
        created after the run started, newest wins.
        """
        out_root = os.path.join(self.sugar_dir, "output")
        candidates: List[str] = []
        preferred = os.path.join(out_root, "refined_mesh", scene)
        if os.path.isdir(preferred):
            candidates += glob.glob(os.path.join(preferred, "**", "*.obj"),
                                    recursive=True)
        if not candidates and os.path.isdir(out_root):
            candidates += [
                p for p in glob.glob(os.path.join(out_root, "**", "*.obj"),
                                     recursive=True)
                if os.path.getmtime(p) >= since - 1
            ]
        if not candidates:
            return None
        return max(candidates, key=os.path.getmtime)

    def finalize_run(self, success: bool = True) -> str:
        self.qc.finalize(success)
        print(f"QC sidecar: {self.qc.path}")
        return self.qc.path
