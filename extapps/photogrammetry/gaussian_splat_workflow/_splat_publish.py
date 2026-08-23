# !/usr/bin/python
# coding=utf-8
"""Engine-delivery stage for the splat track — clean + convert to engine formats.

Brush trains a raw INRIA-format 3DGS ``.ply`` (hundreds of MB). That is a
*research* artifact, not something you drop into Unity or a browser. This wraps
PlayCanvas's **splat-transform** CLI (https://github.com/playcanvas/splat-transform)
to turn the trained ``.ply`` into engine-ready deliverables, mirroring the
structure of :class:`._gaussian_splat_workflow.GaussianSplatWorkflow`
(exe discovery, QC log, mock mode, per-stage logging).

One Node CLI covers both the cleanup *and* every output target, so the splat
track gains exactly one new external dependency::

    npm install -g @playcanvas/splat-transform

Pipeline — **clean once, then fan out**:

* **clean** — the highest-ROI *production-quality* lever for an environment splat,
  and it costs no VRAM (unlike the gaussian budget, which is capped by the card).
  Orients (see below), removes NaN/inf gaussians, isolated **floaters**, and
  (optionally) an opacity floor; optionally crops to a bounding box/sphere and
  decimates. Floater removal defaults **on** because background junk is what makes
  a capture read as "scan" rather than "production".
* **Unity** — writes ``.spz`` (Scaniverse format, ~10x smaller than ``.ply`` with
  no perceptible loss), imported natively by ``aras-p/UnityGaussianSplatting``.
* **Browser** — writes ``.sog`` (or compressed ``.ply``) for engine integration
  **plus** a self-contained ``.html`` viewer for instant preview / drop-in embed.

ORIENTATION — keep the up-axis consistent across every viewer
-------------------------------------------------------------
SfM (COLMAP/Brush) reconstructs in an arbitrary gauge frame — there is *no*
gravity reference — so splats commonly load sideways/upside-down. We assert the
up-axis **once, here**, by rotating in the ``clean`` step: because every target
(``.spz``, ``.sog``, ``.html`` viewer, and the ``--preview`` pop-up) fans out from
that single cleaned/oriented ``.ply``, they are guaranteed identical.

Canonical convention is **Y-up** (both Unity and the web viewers are Y-up).
``rotate`` is XYZ euler degrees applied *before* cropping, so the crop box is
specified in the upright frame. The exact value is capture-dependent (the gauge
is arbitrary): the workflow is to eyeball it once in SuperSplat, then lock it into
the profile (``publish.rotate``). Common starting points: 180° about Z, or 90°
about X. (Blender is Z-up — a one-off ``--rotate`` differing by 90° about X — and
is intentionally not a maintained target here.)

QUALITY NOTE (3070 Ti / 3080, 8-10 GB)
--------------------------------------
Raw gaussian count is VRAM-capped on this GPU class — the very top fidelity tier
needs a 4090/A100. Quality effort here goes where it is *not* VRAM-bound: this
cleanup/crop stage, full camera coverage (Brush takes the whole set — the
``colmap_max_cameras`` stride exists only for SuGaR), and longer training. The
old "no PSNR gain at 4K" A/B was VRAM-bound at ~2.5-3M gaussians on 8 GB; a 10 GB
3080 holds more, so re-test ``--max-resolution 3840`` there before assuming 1920.
"""
import os
import shutil
import subprocess
from typing import Callable, Dict, List, Optional, Sequence, Union

from pythontk import QcLog

from .._progress_notify import ProgressNotifyMixin
from ..profile import Profile
from ._gaussian_splat_workflow import GaussianSplatWorkflow


class _SplatPublishWorkflowInternal:
    """Discovery + argv helpers for :class:`SplatPublishWorkflow` (encapsulation
    standard: helpers on a ``_<Class>Internal`` base the public class inherits)."""

    @staticmethod
    def _csv(value: "Union[str, Sequence[float]]") -> str:
        """Normalize a crop/box arg to the comma-joined string the CLI expects."""
        if isinstance(value, str):
            return value
        return ",".join(str(v) for v in value)


class SplatPublishWorkflow(ProgressNotifyMixin, _SplatPublishWorkflowInternal):
    """Clean a trained 3DGS ``.ply`` and convert it to engine-ready formats."""
    @staticmethod
    def find_splat_transform() -> "Optional[str]":
        """Return the ``splat-transform`` executable path or None.

        Runs the shared :func:`resolve_app` chain: the ``SPLAT_TRANSFORM_EXE``
        env override (terminal — empty or a nonexistent path returns None so the
        caller enters mock mode), then PATH. Unlike Brush/SuGaR (folder
        installs), splat-transform is an npm global on PATH — on Windows
        ``shutil.which`` resolves the ``.cmd`` shim. It has **no profile key**:
        there is no network-install story for an npm global, hence the ``None``
        config key.
        """
        return Profile.resolve_app(
            "SPLAT_TRANSFORM_EXE",
            None,
            fallbacks=(lambda: shutil.which("splat-transform"),),
        )
    @staticmethod
    def is_splat_transform_available() -> bool:
        return SplatPublishWorkflow.find_splat_transform() is not None

    def __init__(
        self,
        project_path: str = "./gsplat_project/publish",
        name: str = "splat",
        splat_transform_exe: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        progress: Optional[Callable[[str, float], None]] = None,
        timeout_sec: int = 3600,
    ):
        self.project_path = project_path
        self.name = name
        self.progress = progress
        self.timeout_sec = timeout_sec

        self.exe = splat_transform_exe or self.find_splat_transform()
        if mock_mode is None:
            mock_mode = self.exe is None
        self.mock_mode = bool(mock_mode)

        os.makedirs(self.project_path, exist_ok=True)
        self._logs_dir = os.path.join(self.project_path, "logs")
        os.makedirs(self._logs_dir, exist_ok=True)

        self.qc = QcLog(os.path.join(self.project_path, f"{name}_publish_qc.json"))
        self.qc.set("project_name", name)
        self.qc.set("splat_transform_exe", self.exe or "")
        self.qc.set("mock_mode", self.mock_mode)

    # ----------------------------------------------------------- helpers

    def get_publish_info(self) -> str:
        if self.exe is None:
            return ("splat-transform not found (npm i -g @playcanvas/splat-transform, "
                    "or set SPLAT_TRANSFORM_EXE)")
        return f"splat-transform ({self.exe})"

    def _run_transform(
        self,
        input_path: str,
        actions: List[str],
        output_path: str,
        label: str,
        globals_: Optional[List[str]] = None,
    ) -> str:
        """Invoke ``splat-transform``; stream output to ``logs/<label>.log``.

        CLI shape is ``splat-transform [GLOBAL] <input> [ACTIONS] <output>``;
        ``-w`` (overwrite) is passed as a leading global. Returns *output_path*.
        """
        argv = [self.exe or "splat-transform", "-w", *(globals_ or []),
                input_path, *actions, output_path]
        if self.mock_mode:
            print(f"[mock:{label}] {' '.join(argv[1:])}")
            return output_path
        if self.exe is None:
            raise RuntimeError("splat-transform executable not found.")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        log_path = os.path.join(self._logs_dir, f"{label}.log")
        print(f"[publish:{label}] {' '.join(argv[1:])}  >> {log_path}")
        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            log.write(f"# argv: {argv}\n")
            log.flush()
            completed = subprocess.run(
                argv, timeout=self.timeout_sec, stdout=log,
                stderr=subprocess.STDOUT,
            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"splat-transform failed (exit {completed.returncode}, "
                f"label={label}). See {log_path}."
            )
        if not os.path.isfile(output_path):
            self.qc.warn(
                f"splat-transform returned success but {output_path} is missing "
                f"(label={label}); check {log_path}."
            )
        return output_path

    @staticmethod
    def _clean_actions(
        rotate: Optional[Union[str, Sequence[float]]],
        filter_floaters: bool,
        filter_nan: bool,
        min_opacity: Optional[float],
        crop_box: Optional[Union[str, Sequence[float]]],
        crop_sphere: Optional[Union[str, Sequence[float]]],
        decimate: Optional[Union[str, int]],
    ) -> List[str]:
        """Build the ordered splat-transform action list for a cleanup pass.

        ``rotate`` (XYZ euler degrees) is applied *first* so the up-axis is fixed
        before any crop — the crop box is therefore in the upright (Y-up) frame.
        """
        actions: List[str] = []
        if rotate is not None:
            actions += ["-r", _SplatPublishWorkflowInternal._csv(rotate)]
        if filter_nan:
            actions.append("-N")
        if filter_floaters:
            actions.append("-G")
        if min_opacity is not None:
            actions += ["-V", f"opacity,gt,{min_opacity}"]
        if crop_box is not None:
            actions += ["-B", _SplatPublishWorkflowInternal._csv(crop_box)]
        if crop_sphere is not None:
            actions += ["-S", _SplatPublishWorkflowInternal._csv(crop_sphere)]
        if decimate is not None:
            actions += ["-F", str(decimate)]
        return actions

    # ----------------------------------------------------------- pipeline

    def clean(
        self,
        in_ply: str,
        out_ply: Optional[str] = None,
        rotate: Optional[Union[str, Sequence[float]]] = None,
        filter_floaters: bool = True,
        filter_nan: bool = True,
        min_opacity: Optional[float] = None,
        crop_box: Optional[Union[str, Sequence[float]]] = None,
        crop_sphere: Optional[Union[str, Sequence[float]]] = None,
        decimate: Optional[Union[str, int]] = None,
    ) -> str:
        """Clean a trained splat ``.ply``; return the cleaned ``.ply`` path.

        ``rotate`` (XYZ euler degrees, e.g. ``"180,0,0"``) fixes the up-axis to
        the canonical **Y-up** and is applied *before* cropping (see the module
        docstring); ``filter_floaters`` removes isolated gaussians (background
        junk); ``min_opacity`` (e.g. ``0.1``) culls near-transparent gaussians on
        the raw ``opacity`` column; ``crop_box`` / ``crop_sphere`` bound the
        environment (``x,y,z,X,Y,Z`` / ``x,y,z,r``); ``decimate`` (``N`` or
        ``N%``) thins the count. All optional knobs default off except floater +
        NaN removal.
        """
        self._notify("splat_clean", 0.0)
        out_ply = out_ply or os.path.join(self.project_path, f"{self.name}_clean.ply")
        actions = self._clean_actions(
            rotate, filter_floaters, filter_nan, min_opacity, crop_box,
            crop_sphere, decimate,
        )
        with self.qc.stage("splat_clean") as st:
            st["in_ply"] = in_ply
            st["out_ply"] = out_ply
            st["actions"] = actions
            if not self.mock_mode and not os.path.isfile(in_ply):
                raise ValueError(f"Input splat .ply not found: {in_ply}")
            st["gaussians_in"] = GaussianSplatWorkflow.read_splat_count(in_ply) if not self.mock_mode else None
            self._run_transform(in_ply, actions, out_ply, label="clean")
            if not self.mock_mode:
                count = GaussianSplatWorkflow.read_splat_count(out_ply)
                st["gaussians_out"] = count
                if count and st["gaussians_in"]:
                    print(f"Cleaned splat: {st['gaussians_in']:,} -> {count:,} "
                          f"gaussians -> {out_ply}")
            return out_ply

    def to_unity(
        self,
        clean_ply: str,
        out_path: Optional[str] = None,
        spz_version: int = 4,
    ) -> str:
        """Convert a (cleaned) ``.ply`` to Unity-ready ``.spz``; return its path.

        ``.spz`` is ~10x smaller than ``.ply`` and imported natively by
        ``aras-p/UnityGaussianSplatting``.
        """
        self._notify("publish_unity", 0.0)
        out_path = out_path or os.path.join(self.project_path, f"{self.name}.spz")
        with self.qc.stage("publish_unity") as st:
            st["clean_ply"] = clean_ply
            st["spz"] = out_path
            st["spz_version"] = spz_version
            self._run_transform(
                clean_ply, [], out_path, label="unity",
                globals_=["--spz-version", str(spz_version)],
            )
            print(f"Unity splat (.spz) -> {out_path}")
            return out_path

    def to_web(
        self,
        clean_ply: str,
        out_dir: Optional[str] = None,
        web_format: str = "sog",
        with_viewer: bool = True,
    ) -> Dict[str, Optional[str]]:
        """Convert a (cleaned) ``.ply`` for the browser; return the output paths.

        Writes ``web_format`` (``sog`` — bundled, recommended — or
        ``compressed-ply``) for engine integration, plus (``with_viewer``) a
        self-contained ``.html`` viewer for instant preview / drop-in embed.
        Returns ``{"data": <sog/ply path>, "viewer": <html path or None>}``.
        """
        self._notify("publish_web", 0.0)
        out_dir = out_dir or self.project_path
        ext = "compressed.ply" if web_format == "compressed-ply" else "sog"
        data_path = os.path.join(out_dir, f"{self.name}.{ext}")
        viewer_path = os.path.join(out_dir, f"{self.name}.html") if with_viewer else None
        with self.qc.stage("publish_web") as st:
            st["clean_ply"] = clean_ply
            st["web_format"] = web_format
            st["data"] = data_path
            st["viewer"] = viewer_path
            self._run_transform(clean_ply, [], data_path, label="web_data")
            print(f"Web splat ({ext}) -> {data_path}")
            if with_viewer:
                self._run_transform(clean_ply, [], viewer_path, label="web_viewer")
                print(f"Web viewer (.html) -> {viewer_path}")
            return {"data": data_path, "viewer": viewer_path}

    def publish(
        self,
        in_ply: str,
        targets: Sequence[str] = ("unity", "web"),
        out_dir: Optional[str] = None,
        spz_version: int = 4,
        web_format: str = "sog",
        with_viewer: bool = True,
        **clean_kwargs,
    ) -> Dict[str, object]:
        """Clean *in_ply* once, then emit each requested target from the result.

        ``targets`` is any subset of ``("unity", "web")``. ``clean_kwargs`` are
        forwarded to :meth:`clean` (``rotate`` for the up-axis, ``filter_floaters``,
        ``min_opacity``, ``crop_box``, ``crop_sphere``, ``decimate``). Returns
        ``{"clean": <ply>, "unity": <spz|None>, "web": <dict|None>}``.
        """
        unknown = [t for t in targets if t not in ("unity", "web")]
        if unknown:
            raise ValueError(
                f"Unknown publish target(s) {unknown}; choose from 'unity', 'web'."
            )
        out_dir = out_dir or self.project_path
        clean_ply = self.clean(
            in_ply,
            out_ply=os.path.join(out_dir, f"{self.name}_clean.ply"),
            **clean_kwargs,
        )
        result: Dict[str, object] = {"clean": clean_ply, "unity": None, "web": None}
        if "unity" in targets:
            result["unity"] = self.to_unity(
                clean_ply,
                out_path=os.path.join(out_dir, f"{self.name}.spz"),
                spz_version=spz_version,
            )
        if "web" in targets:
            result["web"] = self.to_web(
                clean_ply, out_dir=out_dir, web_format=web_format,
                with_viewer=with_viewer,
            )
        return result

    def finalize_run(self, success: bool = True) -> str:
        self.qc.finalize(success)
        print(f"QC sidecar: {self.qc.path}")
        return self.qc.path
