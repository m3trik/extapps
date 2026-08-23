# !/usr/bin/python
# coding=utf-8
"""Brush gaussian-splat workflow engine.

Brush has no Python API; this wraps its CLI via :mod:`subprocess`, mirroring
the structure of :class:`extapps.photogrammetry.realityscan_workflow._realityscan_workflow.RealityCaptureWorkflow`
(exe discovery, QC log, mock mode, per-stage logging).

Validated defaults (indoor scene dataset, 8 GB VRAM class GPU):

* ``max_resolution=1920`` — A/B testing showed **no PSNR gain** from 3840 vs
  1920 (25.2 dB both, even evaluated at 2800px): with the gaussian count the
  GPU can hold, splat density caps achievable detail, so 4K input only costs
  ~3x training time. Raise only if you also raise the gaussian budget on a
  bigger GPU.
* gaussian budget ~2.5-3M — brush's stock growth settles here at 30k steps,
  which is the practical ceiling on 8 GB. **Aggressive growth**
  (``growth_grad_threshold`` lowered / ``growth_select_fraction`` raised)
  OOM-crashed the GPU mid-run in testing, so the growth knobs default to
  brush's stock values; only push them on a larger-VRAM card.
"""
import os
import shutil
import subprocess
from typing import Callable, Dict, List, Optional

from pythontk import QcLog

from .._progress_notify import ProgressNotifyMixin
from ..profile import Profile

# Prebuilt Brush release binaries (github.com/ArthurBrussee/brush). cargo-dist
# publishes one archive per platform with stable asset names, so the version-
# agnostic ``releases/latest/download`` URL tracks new releases without pinning
# a version. The executable inside every archive is ``brush`` (the brush-app
# crate's ``[[bin]]`` name — ``brush.exe`` on Windows).
_BRUSH_RELEASE = "https://github.com/ArthurBrussee/brush/releases/latest/download"
BRUSH_DOWNLOAD: Dict[str, dict] = {
    "windows": {
        "url": f"{_BRUSH_RELEASE}/brush-app-x86_64-pc-windows-msvc.zip",
        "type": "zip",
    },
    "linux": {
        "url": f"{_BRUSH_RELEASE}/brush-app-x86_64-unknown-linux-gnu.tar.xz",
        "type": "tar.xz",
    },
    "darwin": {
        "url": f"{_BRUSH_RELEASE}/brush-app-aarch64-apple-darwin.tar.xz",
        "type": "tar.xz",
    },
}
# The binary name AppInstaller searches for inside the extracted archive — also
# the name it records in its managed-install catalog (see find_brush_exe).
BRUSH_EXE_NAME = "brush"


class _GaussianSplatWorkflowInternal:
    """Brush discovery / install / ply-introspection helpers.

    On a ``_<Class>Internal`` base per the encapsulation standard; the public
    :class:`GaussianSplatWorkflow` inherits them, so
    ``GaussianSplatWorkflow.find_brush_exe()`` is the supported call.
    """

    @staticmethod
    def _make_progress_printer() -> Callable[[int, int], None]:
        """A download progress callback that prints one line per ~10%.

        The panel streams the installer's stdout into its log pane, which appends
        rather than honoring ``\\r`` overwrite, so emit discrete newline updates
        instead of a single rewritten line.
        """
        state = {"next": 0}

        def _printer(downloaded: int, total: int) -> None:
            if not total:
                return
            pct = downloaded * 100 // total
            if pct >= state["next"]:
                state["next"] = (pct // 10 + 1) * 10
                print(
                    f"  downloading Brush... {pct}% "
                    f"({downloaded // 1048576} / {total // 1048576} MB)",
                    flush=True,
                )

        return _printer


class GaussianSplatWorkflow(ProgressNotifyMixin, _GaussianSplatWorkflowInternal):
    """Wrapper around Brush's CLI for COLMAP-dataset -> 3DGS ``.ply``."""
    @staticmethod
    def find_brush_exe() -> Optional[str]:
        """Return the Brush executable path or None.

        Brush ships as a single binary (``brush.exe`` — the unified app; the viewer
        is opt-in via ``--with-viewer``) with no canonical install location, so
        discovery runs the shared :func:`resolve_app` chain: the ``BRUSH_EXE`` env
        override (terminal — empty or nonexistent returns None so the caller enters
        mock mode), then the profile's ``apps.brush_exe`` (network / non-standard
        install), then ``PATH``, then pythontk's managed-install catalog (where the
        panel's "Download Brush" action installs it — that dir isn't on ``PATH``
        across sessions). Point ``BRUSH_EXE`` at the binary, set ``apps.brush_exe``,
        put it on ``PATH``, or install it via :meth:`install_brush`.
        """

        def _on_path() -> Optional[str]:
            # Probe the shipped binary name first; brush_app.exe is a legacy name
            # kept as a fallback for old manual installs.
            return shutil.which("brush") or shutil.which("brush_app.exe")

        def _managed() -> Optional[str]:
            try:
                from pythontk import AppInstaller

                return AppInstaller.get_path("brush", executable=BRUSH_EXE_NAME)
            except Exception:  # noqa: BLE001 — discovery must never raise
                return None

        return Profile.resolve_app("BRUSH_EXE", "brush_exe", fallbacks=(_on_path, _managed))
    @staticmethod
    def is_brush_available() -> bool:
        return GaussianSplatWorkflow.find_brush_exe() is not None
    @staticmethod
    def install_brush(
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Download + install Brush via :class:`pythontk.AppInstaller`; return the
        executable path.

        Fetches the prebuilt release binary for this platform into pythontk's
        per-user managed tools dir (``~/.pythontk/tools``) and records it in the
        install catalog, so subsequent :meth:`find_brush_exe` calls discover it.
        Re-runs are cheap — ``AppInstaller`` returns the cached path if Brush is
        already present. Raises ``LookupError`` on an unsupported platform and
        ``RuntimeError`` on a download / extraction failure.
        """
        from pythontk import AppInstaller

        return AppInstaller.ensure(
            "brush",
            platforms=BRUSH_DOWNLOAD,
            executable=BRUSH_EXE_NAME,
            progress_callback=progress_callback
            or _GaussianSplatWorkflowInternal._make_progress_printer(),
        )
    @staticmethod
    def read_splat_count(ply_path: str) -> Optional[int]:
        """Gaussian count from a splat ``.ply`` header (``element vertex N``)."""
        try:
            with open(ply_path, "rb") as fh:
                for _ in range(60):
                    line = fh.readline().decode("ascii", "replace").strip()
                    if line.startswith("element vertex"):
                        return int(line.split()[-1])
                    if line == "end_header":
                        break
        except Exception:
            pass
        return None

    def __init__(
        self,
        project_path: str = "./gsplat_project",
        name: str = "gsplat",
        brush_exe: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        progress: Optional[Callable[[str, float], None]] = None,
        timeout_sec: int = 14400,
    ):
        self.project_path = project_path
        self.name = name
        self.progress = progress
        self.timeout_sec = timeout_sec

        self.brush_exe = brush_exe or self.find_brush_exe()
        if mock_mode is None:
            mock_mode = self.brush_exe is None
        self.mock_mode = bool(mock_mode)

        os.makedirs(self.project_path, exist_ok=True)
        self._logs_dir = os.path.join(self.project_path, "logs")
        os.makedirs(self._logs_dir, exist_ok=True)

        self.qc = QcLog(os.path.join(self.project_path, f"{name}_qc.json"))
        self.qc.set("project_name", name)
        self.qc.set("brush_exe", self.brush_exe or "")
        self.qc.set("mock_mode", self.mock_mode)

    # ----------------------------------------------------------- helpers

    def get_brush_info(self) -> str:
        if self.brush_exe is None:
            return "Brush not found (set BRUSH_EXE env or install)"
        return f"Brush ({self.brush_exe})"

    def _run_brush(self, args: List[str], label: str = "train") -> int:
        """Invoke Brush; stream stdout/stderr to ``logs/<label>.log``."""
        if self.mock_mode:
            print(f"[mock:{label}] brush {' '.join(args)}")
            return 0
        if self.brush_exe is None:
            raise RuntimeError("Brush executable not found.")
        argv = [self.brush_exe] + args
        log_path = os.path.join(self._logs_dir, f"{label}.log")
        print(f"[brush:{label}] {' '.join(args)}  >> {log_path}")
        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            log.write(f"# argv: {argv}\n")
            log.flush()
            completed = subprocess.run(
                argv, timeout=self.timeout_sec, stdout=log,
                stderr=subprocess.STDOUT,
            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Brush failed (exit {completed.returncode}, label={label}). "
                f"A negative/0xC... code usually means a GPU/VRAM crash — "
                f"lower the gaussian budget or max_resolution. See {log_path}."
            )
        return completed.returncode

    # ----------------------------------------------------------- pipeline

    def train(
        self,
        colmap_dir: str,
        total_steps: int = 30000,
        max_resolution: int = 1920,
        max_splats: int = 10_000_000,
        sh_degree: int = 3,
        growth_grad_threshold: Optional[float] = None,
        growth_select_fraction: Optional[float] = None,
        export_path: Optional[str] = None,
        export_name: Optional[str] = None,
        export_every: Optional[int] = None,
        eval_split_every: Optional[int] = None,
        eval_every: Optional[int] = None,
        eval_save_to_disk: bool = False,
    ) -> Optional[str]:
        """Train a splat from a COLMAP dataset; return the final ``.ply`` path.

        ``colmap_dir`` holds ``images/`` + ``sparse/0/`` (cameras/images/
        points3D). See the module docstring for why ``max_resolution`` defaults
        to 1920 and why the growth knobs are left at brush's stock values.
        """
        self._notify("train", 0.0)
        export_path = export_path or self.project_path
        export_name = export_name or f"{self.name}_{{iter}}.ply"
        export_every = export_every or total_steps
        os.makedirs(export_path, exist_ok=True)

        with self.qc.stage("train") as st:
            st["colmap_dir"] = colmap_dir
            st["total_steps"] = total_steps
            st["max_resolution"] = max_resolution
            st["max_splats"] = max_splats
            st["sh_degree"] = sh_degree
            if not os.path.isdir(colmap_dir):
                raise ValueError(f"COLMAP dataset not found: {colmap_dir}")
            if not self.mock_mode:
                # Validate the dataset shape up front (mirrors the SuGaR
                # track) — a wrong dir otherwise fails minutes later inside
                # Brush with an opaque loader error.
                missing = [
                    d for d in ("images", os.path.join("sparse", "0"))
                    if not os.path.isdir(os.path.join(colmap_dir, d))
                ]
                if missing:
                    raise ValueError(
                        f"Not a COLMAP dataset (missing {', '.join(missing)}): "
                        f"{colmap_dir}"
                    )

            args = [
                colmap_dir,
                "--total-steps", str(total_steps),
                "--max-resolution", str(max_resolution),
                "--max-splats", str(max_splats),
                "--sh-degree", str(sh_degree),
                "--export-every", str(export_every),
                "--export-path", export_path,
                "--export-name", export_name,
            ]
            if growth_grad_threshold is not None:
                args += ["--growth-grad-threshold", str(growth_grad_threshold)]
            if growth_select_fraction is not None:
                args += ["--growth-select-fraction", str(growth_select_fraction)]
            if eval_split_every is not None:
                args += ["--eval-split-every", str(eval_split_every)]
            if eval_every is not None:
                args += ["--eval-every", str(eval_every)]
            if eval_save_to_disk:
                args += ["--eval-save-to-disk"]

            self._run_brush(args, label="train")

            final_ply = os.path.join(
                export_path, export_name.replace("{iter}", str(total_steps))
            )
            st["export_ply"] = final_ply
            if self.mock_mode:
                print(f"[mock] train -> {final_ply}")
                return final_ply
            if not os.path.isfile(final_ply):
                # Brush names exports by its own step counter, which can
                # differ from total_steps (padding / 0-index). Fall back to
                # the newest matching export instead of reporting nothing.
                import glob
                pattern = os.path.join(
                    export_path, export_name.replace("{iter}", "*")
                )
                candidates = [p for p in glob.glob(pattern) if os.path.isfile(p)]
                if candidates:
                    final_ply = max(candidates, key=os.path.getmtime)
                    st["export_ply"] = final_ply
                    print(f"(export name differed; using {final_ply})")
            count = self.read_splat_count(final_ply)
            st["gaussian_count"] = count
            if count:
                print(f"Trained splat: {count:,} gaussians -> {final_ply}")
            else:
                print(f"Trained splat -> {final_ply} (count unread)")
            return final_ply if os.path.isfile(final_ply) else None

    def finalize_run(self, success: bool = True) -> str:
        self.qc.finalize(success)
        print(f"QC sidecar: {self.qc.path}")
        return self.qc.path
