# !/usr/bin/python
# coding=utf-8
"""SuGaR mesh-extraction workflow engine.

Wraps SuGaR's ``train_full_pipeline.py`` (https://github.com/Anttwo/SuGaR)
through :class:`pythontk.AppLauncher`, mirroring the structure of
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
import sys
import glob
import time
from typing import Callable, List, Optional

from pythontk import AppLauncher

from .._workflow_engine import WorkflowEngine
from ..profile import Profile


class _SugarMeshWorkflowInternal:
    """Discovery helpers for :class:`SugarMeshWorkflow`.

    On a ``_<Class>Internal`` base per the encapsulation standard; the public
    class inherits them, so ``SugarMeshWorkflow.find_sugar_dir()`` is the
    supported call.
    """

    @staticmethod
    def _is_sugar_dir(path: "Optional[str]") -> bool:
        """True if *path* is a SuGaR repo dir (holds ``train_full_pipeline.py``)."""
        return bool(path) and os.path.isfile(
            os.path.join(path, "train_full_pipeline.py")
        )


class SugarMeshWorkflow(WorkflowEngine, _SugarMeshWorkflowInternal):
    """COLMAP dataset → SuGaR refined textured ``.obj`` mesh."""
    @staticmethod
    def find_sugar_dir() -> "Optional[str]":
        """Return the SuGaR repo dir or None.

        SuGaR is a cloned repo (its root holds ``train_full_pipeline.py``) with
        no canonical install location, so discovery runs the shared
        :func:`resolve_app` chain: the ``SUGAR_DIR`` env override (terminal —
        set-but-invalid returns None so the caller enters mock mode), then the
        profile's ``apps.sugar_dir`` (network / non-standard repo). Point
        ``SUGAR_DIR`` at the repo, or set ``apps.sugar_dir`` in the profile.

        Validated as a **directory** holding the train script, not as a file —
        hence the explicit *validate*.
        """
        return Profile.resolve_app(
            "SUGAR_DIR",
            "sugar_dir",
            validate=_SugarMeshWorkflowInternal._is_sugar_dir,
        )
    @staticmethod
    def is_sugar_available() -> bool:
        return SugarMeshWorkflow.find_sugar_dir() is not None

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
        self.timeout_sec = timeout_sec

        self.sugar_dir = sugar_dir or self.find_sugar_dir()
        # The env activator (sets the MSVC toolset + activates the conda env);
        # nvdiffrast JIT-compiles at the textured-mesh step, so the build env
        # must be live for the whole run.
        if env_bat is None and self.sugar_dir:
            cand = os.path.join(self.sugar_dir, self._ENV_SCRIPT)
            env_bat = cand if os.path.isfile(cand) else None
        self.env_bat = env_bat

        if mock_mode is None:
            mock_mode = self.sugar_dir is None
        self.mock_mode = bool(mock_mode)

        self._open_run(
            project_path,
            name,
            progress,
            qc_fields={"sugar_dir": self.sugar_dir or "", "env_bat": self.env_bat or ""},
        )

    # ----------------------------------------------------------- helpers

    def get_sugar_info(self) -> str:
        if self.sugar_dir is None:
            return "SuGaR not found (set SUGAR_DIR env or install)"
        env = self.env_bat or f"(no {self._ENV_SCRIPT} — env may be inactive)"
        return f"SuGaR ({self.sugar_dir}) via {env}"

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
        refinement_time: str = "medium",
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
        is ``short`` / ``medium`` / ``long`` (2k / 7k / 15k refinement iters);
        the default matches the runner's ``balanced`` tier (``medium``) so a
        direct engine call and a no-flag runner call produce the same mesh.
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
            run_script = self._write_run_bat(py_args)
            log_path = self._log_path("sugar_mesh")
            print(f"[sugar_mesh] {run_script}  >> {log_path}")
            shell = ["cmd", "/c"] if sys.platform == "win32" else ["bash"]
            completed = self._run_logged(
                shell + [run_script],
                "sugar_mesh",
                timeout=self.timeout_sec,
                header=f"cmd: {py_args}",
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

    #: The SuGaR env activator this OS runs first (MSVC toolset + conda env on
    #: Windows; the conda env on Linux, where SuGaR is native).
    _ENV_SCRIPT = "sugar_buildenv.bat" if sys.platform == "win32" else "sugar_buildenv.sh"

    def _write_run_bat(self, py_args: str) -> str:
        """Write the script that activates the SuGaR env and runs the pipeline --
        a batch file on Windows, a bash script elsewhere (the name predates
        Linux). Returns its path."""
        if sys.platform != "win32":
            lines = [f'source "{self.env_bat}"'] if self.env_bat else []
            lines += [f'cd "{self.sugar_dir}" || exit 1', py_args, "status=$?"]
            lines += ['echo "SUGAR_EXIT=$status"', 'exit "$status"']
            script = os.path.join(self._logs_dir, "run_sugar.sh")
            return AppLauncher.write_batch_script(script, lines, shell="bash")
        lines = ["@echo off"]
        if self.env_bat:
            lines.append(f'call "{self.env_bat}"')
        lines.append(f'cd /d "{self.sugar_dir}"')
        lines.append(py_args)
        lines.append("echo SUGAR_EXIT=%errorlevel%")
        # OEM codepage + exact CRLF (a non-ASCII SuGaR / env path must survive
        # for `cd /d`, or fail loudly): AppLauncher owns the .bat byte contract.
        bat = os.path.join(self._logs_dir, "run_sugar.bat")
        return AppLauncher.write_batch_script(bat, lines, shell="cmd")

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

