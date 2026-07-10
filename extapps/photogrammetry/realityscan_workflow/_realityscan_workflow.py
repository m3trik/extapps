#!/usr/bin/python
# coding=utf-8
"""RealityCapture / RealityScan workflow engine.

Mirrors :class:`extapps.photogrammetry.metashape_workflow._metashape_workflow.MetashapeWorkflow`
public method shape so the same UI panel can target either engine.

RC has no Python API; this wrapper builds + runs CLI command chains via
:mod:`subprocess`. Project state persists in a ``.rcproj`` between calls
(each stage loads the project, runs its commands, saves, and quits).

Stages with no direct RC equivalent (depth maps, dedupe-by-pose, reduce
overlap) are no-ops here so a UI that drives both engines can present the
same surface without engine-specific branches.
"""
import functools
import glob
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from pythontk import QcGate, QcLog

from ..profile import configured_app_path
from ..prep_stages import PrepStagesMixin
from ._realityscan_connection import (
    RealityScanConnection,
    RealityScanInteractiveError,
)


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")

# Minimal RealityScan report template, bundled with the package. RC's
# ``-exportReport`` takes TWO params — ``outputFile templateFile`` — and renders
# the template via its ``$Using``/``$ExportProjectInfo``/``$(var)`` substitution
# engine. The stock templates (``<install>\Reports\*.html``) fail in the headless
# RSNode session because they ``$Include`` CSS + ``$SetLocalization`` by *relative*
# path (resolved against a working dir that doesn't exist there) — "Translation
# failed". This template has no includes/localization, so it renders anywhere, and
# emits a compact, deterministic ``<qc>`` XML the parser below reads exactly (no
# tag-guessing). Verified live against RealityScan 2.1's RSNode.
QC_REPORT_TEMPLATE = os.path.join(os.path.dirname(__file__), "qc_report_template.html")

# RealityScan (Epic's rebrand) installs to "C:\Program Files\RealityScan_<ver>\"
# (e.g. RealityScan_2.0, RealityScan_2.1, ...). Glob + pick the highest version so
# new releases are found without editing this file. RealityScan 2.x uses .rsproj;
# legacy RealityCapture uses .rcproj. The fixed list below is the legacy fallback.
_RC_INSTALL_GLOB = r"C:\Program Files\RealityScan_*\RealityScan.exe"
_RC_DEFAULT_EXES = (
    r"C:\Program Files\RealityScan\RealityScan.exe",
    r"C:\Program Files\Capturing Reality\RealityCapture\RealityCapture.exe",
)


def _rc_install_version_key(path: str):
    """Numeric sort key from the version in a ``RealityScan_<ver>`` path."""
    m = re.search(r"RealityScan_([0-9][0-9.]*)", path)
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split(".") if x.isdigit())


# Acceptance-gate defaults. RC's report metric names differ from Metashape's;
# the metric keys below match what _alignment_metrics() / _mesh_metrics() emit.
DEFAULT_GATES: Dict[str, Dict[str, float]] = {
    "align": {
        "min_aligned_pct": 75.0,
    },
    "model": {
        "min_largest_component_pct": 85.0,
    },
    "texture": {
        # RC reports don't expose per-texel coverage; gate left empty.
    },
}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
def find_realitycapture_exe() -> Optional[str]:
    """Return the RealityCapture.exe path or None.

    Lookup order:
        * ``RC_EXE`` env override — honored strictly. If set to an empty
          string or a path that does not exist, returns None (caller will
          enter mock mode) instead of falling through to the default. This
          lets users force mock mode by setting ``RC_EXE=`` or to a
          nonexistent path.
        * The profile's ``apps.realityscan_exe`` (network / non-standard
          install), if it exists.
        * Default install path.
        * PATH.
    """
    env = os.environ.get("RC_EXE")
    if env is not None:
        return env if env and os.path.isfile(env) else None
    configured = configured_app_path("realityscan_exe")
    if configured and os.path.isfile(configured):
        return configured
    installs = sorted(glob.glob(_RC_INSTALL_GLOB), key=_rc_install_version_key, reverse=True)
    if installs:
        return installs[0]
    for exe in _RC_DEFAULT_EXES:
        if os.path.isfile(exe):
            return exe
    return shutil.which("RealityScan.exe") or shutil.which("RealityCapture.exe")


def is_realitycapture_available() -> bool:
    return find_realitycapture_exe() is not None


@functools.lru_cache(maxsize=8)
def _version_from_exe(exe_path: str) -> str:
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f'(Get-Item -LiteralPath "{exe_path}").VersionInfo.FileVersion',
            ],
            text=True,
            timeout=10,
        ).strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def get_realitycapture_version() -> str:
    """Read RC's FileVersion from Windows binary metadata.

    RC's CLI is silent on ``-getVersion`` from non-interactive shells, so
    we fall back to ``Get-Item.VersionInfo``. Cached per exe path so
    repeated calls (e.g. from ``__init__`` + ``get_license_info``) don't
    re-spawn PowerShell.
    """
    exe = find_realitycapture_exe()
    return "n/a" if exe is None else _version_from_exe(exe)


def get_image_filepaths(directory: str) -> List[str]:
    """Return absolute paths to all images in ``directory`` (non-recursive)."""
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")
    return [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.lower().endswith(IMAGE_EXTS)
    ]


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
class RealityCaptureWorkflow(PrepStagesMixin):
    """Wrapper around RealityCapture's CLI for the standard photogrammetry
    pipeline. Mirrors :class:`MetashapeWorkflow`'s public method shape.

    The SDK-agnostic input-prep stages (``curate_input_set`` /
    ``equalize_exposures``) come from :class:`PrepStagesMixin`, shared with
    ``MetashapeWorkflow`` so the two engines can't drift apart.
    """

    PROJECT_EXT = "rcproj"

    def __init__(
        self,
        project_path: str = "./rc_project",
        name: str = "rc_project",
        rc_exe: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        progress: Optional[Callable[[str, float], None]] = None,
        gates: Optional[Dict[str, Dict[str, float]]] = None,
        gate_mode: str = "warn",
        checkpoint_each_stage: bool = True,
        rc_timeout_sec: int = 7200,
        connection: Optional[Any] = None,
        use_rsnode: Optional[bool] = None,
        rsnode_url: Optional[str] = None,
    ):
        """
        Parameters:
            project_path: Filesystem directory for the project + outputs.
            name: Project basename (no extension).
            rc_exe: Override the RC executable path. Defaults to ``RC_EXE``
                env var or the standard install location.
            mock_mode: Force-enable mock mode. When None, mock mode is
                selected automatically if RC is not found.
            progress: Callback ``fn(stage: str, fraction: float)`` invoked
                at the start of each pipeline stage.
            gates: Override acceptance-gate thresholds (see DEFAULT_GATES).
            gate_mode: ``"warn"`` (default) or ``"halt"``.
            checkpoint_each_stage: Per-stage ``.rcproj`` save (RC saves on
                every CLI invocation anyway; this flag is kept for API
                parity with MetashapeWorkflow).
            rc_timeout_sec: Per-CLI-invocation timeout. Long pipelines
                (mesh + texture on large frame sets) need generous values.
            connection: Inject a specific transport (duck-typed: ``is_available``
                + ``run(commands, log_path, timeout)``). When None, the transport
                is auto-selected lazily on first use.
            use_rsnode: Transport preference. ``None`` (default) auto-selects the
                RSNode REST transport when a running RealityScan is reachable,
                else the CLI launcher; ``True`` forces RSNode (raises if no node);
                ``False`` forces the CLI. Env ``RC_RSNODE`` (0/1) sets the default.
            rsnode_url: RSNode base URL (default ``RC_RSNODE_URL`` env or
                ``http://127.0.0.1:8000``).
        """
        self.project_path = project_path
        self.name = name
        self.progress = progress
        self.gates = {**DEFAULT_GATES, **(gates or {})}
        self.gate_mode = gate_mode
        self.checkpoint_each_stage = bool(checkpoint_each_stage)
        self.rc_timeout_sec = rc_timeout_sec

        self.rc_exe = rc_exe or find_realitycapture_exe()
        if mock_mode is None:
            mock_mode = self.rc_exe is None
        self.mock_mode = bool(mock_mode)

        # Transport is resolved lazily on first _run_rc so construction never
        # touches the network (unit tests stay hermetic). Auto-selection prefers
        # the RSNode REST transport when a signed-in RealityScan is reachable
        # (drives headlessly from any session), else the CLI launcher (which
        # handles interactive vs. PsExec-into-console + RealityScan's Epic gate).
        if use_rsnode is None:
            _env = os.environ.get("RC_RSNODE")
            if _env is not None:
                use_rsnode = _env.strip().lower() not in ("", "0", "false", "no")
        self._use_rsnode = use_rsnode
        self._rsnode_url = rsnode_url or os.environ.get("RC_RSNODE_URL")
        # An injected connection is active immediately; otherwise None until
        # _connection() resolves + memoizes the auto-selected transport.
        self._conn = connection

        # RealityScan writes .rsproj; legacy RealityCapture writes .rcproj.
        _exe_name = os.path.basename(self.rc_exe or "").lower()
        self.project_ext = "rsproj" if "realityscan" in _exe_name else self.PROJECT_EXT

        os.makedirs(self.project_path, exist_ok=True)
        self._project_file = os.path.join(
            self.project_path, f"{name}.{self.project_ext}"
        )
        self._reports_dir = os.path.join(self.project_path, "reports")
        self._logs_dir = os.path.join(self.project_path, "logs")
        os.makedirs(self._reports_dir, exist_ok=True)
        os.makedirs(self._logs_dir, exist_ok=True)

        self.qc = QcLog(os.path.join(self.project_path, f"{name}_qc.json"))
        self.gate = QcGate(self.gates, self.qc, mode=self.gate_mode)
        self.qc.set("project_name", name)
        self.qc.set("project_path", project_path)
        self.qc.set("rc_exe", self.rc_exe or "")
        self.qc.set("rc_version", get_realitycapture_version())
        self.qc.set("mock_mode", self.mock_mode)

        # True once the .rcproj has been written; subsequent _run_rc calls
        # then prefix with -load to pick up where the last one left off.
        self._project_initialized = False
        # True after import_model — build_texture must NOT re-unwrap, or
        # the user's authored UVs get destroyed.
        self._has_imported_mesh = False

    # ----------------------------------------------------------- helpers

    def get_license_info(self) -> str:
        if self.rc_exe is None:
            return "RealityScan/RealityCapture not found (set RC_EXE env or install)"
        product = (
            "RealityScan"
            if "realityscan" in os.path.basename(self.rc_exe).lower()
            else "RealityCapture"
        )
        return f"{product} {get_realitycapture_version()} ({self.rc_exe})"

    def _notify(self, stage: str, fraction: float = 0.0) -> None:
        if self.progress is None:
            return
        try:
            self.progress(stage, float(fraction))
        except Exception as e:
            import sys
            print(
                f"[RealityCaptureWorkflow] progress callback raised: {e}",
                file=sys.stderr,
            )

    def _connection(self):
        """Resolve (once) and return the execution transport.

        Prefers the RSNode REST transport when a signed-in RealityScan is
        reachable; otherwise the CLI launcher. See ``use_rsnode`` / ``RC_RSNODE``.
        """
        if self._conn is None:
            self._conn = self._resolve_connection()
        return self._conn

    def _resolve_connection(self):
        forced = self._use_rsnode is True
        if self._use_rsnode is not False:  # auto or forced -> try RSNode first
            reason = ""
            try:
                from ._rsnode_connection import RsNodeConnection

                conn = RsNodeConnection(base_url=self._rsnode_url, exe=self.rc_exe)
                if conn.is_available():
                    print(f"[rc] RSNode REST transport: {conn.base_url}")
                    return conn
                reason = f"no RealityScan node answered at {conn.base_url}"
            except Exception as e:  # import or transport failure
                reason = str(e)
            if forced:
                raise RealityScanInteractiveError(
                    "RSNode transport forced (use_rsnode=True) but unavailable: "
                    f"{reason}. Start RealityScan + its Real-time Assistance node, "
                    "or set RC_RSNODE_URL."
                )
        return RealityScanConnection(self.rc_exe)

    def _run_rc(self, *commands: str, label: str = "rc") -> int:
        """Invoke RC with the given command sequence via :class:`RealityScanConnection`.

        Builds the CLI tail ``[-load <proj>?] -<commands> -save <proj> -quit`` and
        delegates execution to the connection, which runs it directly when in an
        interactive session or launches it into the active console session
        (PsExec) when called from a non-interactive one — RealityScan 2.0 is
        window-station + Epic-sign-in gated and will not process in session 0.
        (No ``-headless``: the working RealityScan 2.0 invocations omit it; the
        connection handles the interactivity instead.) Output goes to
        ``logs/<label>.log``; non-zero exit raises ``RuntimeError`` with the tail.
        """
        if self.mock_mode:
            print(f"[mock:{label}] rc {' '.join(commands)}")
            return 0
        if self.rc_exe is None:
            raise RuntimeError("RealityCapture executable not found.")

        tail_cmds: List[str] = []
        if self._project_initialized and os.path.isfile(self._project_file):
            tail_cmds += ["-load", self._project_file]
        tail_cmds += list(commands)
        tail_cmds += ["-save", self._project_file, "-quit"]

        log_path = os.path.join(self._logs_dir, f"{label}.log")
        print(f"[rc:{label}] {' '.join(tail_cmds)}  >> {log_path}")
        completed = self._connection().run(
            tail_cmds, log_path=log_path, timeout=self.rc_timeout_sec
        )
        if completed.returncode != 0:
            tail = ""
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as log:
                    tail = log.read()[-2000:]
            except Exception:
                pass
            raise RuntimeError(
                f"RealityCapture failed (exit {completed.returncode}, label={label}). "
                f"Log tail:\n{tail}"
            )
        self._project_initialized = True
        return completed.returncode

    def _checkpoint(self, label: str) -> Optional[str]:
        """RC's -save runs on every CLI call, so this is informational only."""
        if not self.checkpoint_each_stage or self.mock_mode:
            return None
        print(f"[checkpoint:{label}] {self._project_file}")
        return self._project_file

    # -- Report parsing --------------------------------------------------
    def _export_report(self, label: str) -> Optional[str]:
        """Export a per-stage QC report (our ``<qc>`` template). Returns path.

        ``-exportReport`` takes ``outputFile templateFile`` (two params — passing
        one is the "Wrong parameters number and format combination" 400 the old
        code hit over RSNode). The template is :data:`QC_REPORT_TEMPLATE`; the
        RSNode transport uploads it into the session ``output`` folder and pulls
        the rendered report back, while the CLI transport reads both paths from
        disk directly.
        """
        if self.mock_mode:
            return None
        report_path = os.path.join(self._reports_dir, f"{label}.xml")
        try:
            self._run_rc(
                "-exportReport", report_path, QC_REPORT_TEMPLATE,
                label=f"report_{label}",
            )
            return report_path if os.path.isfile(report_path) else None
        except Exception as e:
            self.qc.warn(f"exportReport({label}) failed: {e}")
            return None

    def _parse_report_metrics(self, report_path: Optional[str]) -> Dict[str, Any]:
        """Extract metrics from a rendered :data:`QC_REPORT_TEMPLATE` report.

        The template emits one deterministic element::

            <qc images="N" comps="C">
              <c cams="K"><pts>P</pts><m tris="T" verts="V" parts="Q"/></c>
              ...
            </qc>

        so this parses an exact, self-authored schema (no tag-guessing). Returns
        empty when nothing parsed, so callers warn rather than treat missing keys
        as zeros (a zero falsely passes max_* gates). Keys produced:
        ``total_count`` (inputs), ``aligned_count`` (cameras in the **largest**
        component — the fraction that forms the usable reconstruction, catching
        both non-registration and SfM fragmentation), ``registered_count`` (sum
        across components), ``components``, ``faces`` / ``vertices`` (largest
        model), ``mesh_parts`` (disconnected parts of that model).
        """
        result: Dict[str, Any] = {}
        if not report_path or not os.path.isfile(report_path):
            return result
        try:
            with open(report_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            return result
        # The template's $Using lines emit leading blank lines before <qc>; slice
        # to the root element so ElementTree gets well-formed XML.
        start = text.find("<qc")
        end = text.rfind("</qc>")
        if start < 0 or end < 0:
            return result
        try:
            root = ET.fromstring(text[start:end + len("</qc>")])
        except ET.ParseError:
            return result

        def _int(el, attr):
            try:
                return int(el.get(attr))
            except (TypeError, ValueError):
                return None

        total = _int(root, "images")
        comps = _int(root, "comps")
        cam_counts, face_models = [], []
        for c in root.findall("c"):
            k = _int(c, "cams")
            if k is not None:
                cam_counts.append(k)
            for m in c.findall("m"):
                t = _int(m, "tris")
                if t is not None:
                    face_models.append((t, _int(m, "verts"), _int(m, "parts")))
        if total is not None:
            result["total_count"] = total
        if comps is not None:
            result["components"] = comps
        if cam_counts:
            result["aligned_count"] = max(cam_counts)
            result["registered_count"] = sum(cam_counts)
        elif total is not None:
            # Report rendered but no components: a *measured* zero alignment, not
            # an unmeasured gap — so align_photos' "No cameras aligned" hard-fail
            # fires instead of degrading to a soft "not measured" warning.
            result["aligned_count"] = 0
            result["registered_count"] = 0
        if face_models:
            tris, verts, parts = max(face_models, key=lambda x: x[0])
            result["faces"] = tris
            if verts is not None:
                result["vertices"] = verts
            if parts is not None:
                result["mesh_parts"] = parts
        return result

    def _warn_if_no_metrics(self, stage: str, metrics: Dict[str, Any]) -> None:
        """Emit a QC warning when a metric snapshot extracted nothing.

        Silent empty metrics cause gates to skip with "metric not measured"
        but leave no breadcrumb explaining *why*. This makes the gap explicit:
        the ``-exportReport`` call either failed (see the preceding warning) or
        produced a report the :data:`QC_REPORT_TEMPLATE` parser couldn't read —
        capture the report under ``reports/`` and check it against the template.
        """
        if not any(v is not None for v in metrics.values()):
            self.qc.warn(
                f"[{stage}] report parsing yielded no metrics. "
                f"exportReport failed or the rendered report didn't match the "
                f"QC template schema; inspect reports/{stage}.xml."
            )

    def _alignment_metrics(self) -> Dict[str, Any]:
        """Snapshot of current alignment quality from RC's report.

        Returns None values when metrics could not be extracted (rather
        than zeros) so gates can correctly skip with "not measured"
        instead of falsely failing/passing on zero.
        """
        if self.mock_mode:
            return {"aligned_count": None, "total_count": None, "aligned_pct": None}
        rep = self._export_report("align")
        raw = self._parse_report_metrics(rep)
        aligned = raw.get("aligned_count")
        total = raw.get("total_count")
        pct = (
            round(100.0 * aligned / total, 2)
            if (aligned is not None and total)
            else None
        )
        # aligned_count is the LARGEST component's camera count (the usable
        # reconstruction); registered_count/components expose SfM fragmentation
        # for diagnostics (many components or registered >> aligned = fragmented).
        metrics = {
            "aligned_count": aligned,
            "total_count": total,
            "aligned_pct": pct,
            "registered_count": raw.get("registered_count"),
            "components": raw.get("components"),
        }
        self._warn_if_no_metrics("align", metrics)
        return metrics

    def _mesh_metrics(self) -> Dict[str, Any]:
        """Snapshot of current mesh quality from RC's report.

        Returns None values when metrics could not be extracted.
        """
        if self.mock_mode:
            return {"faces": None, "vertices": None, "components": None,
                    "largest_component_pct": None}
        rep = self._export_report("model")
        raw = self._parse_report_metrics(rep)
        faces = raw.get("faces")
        parts = raw.get("mesh_parts")
        # The QC template exposes the model's disconnected-part count but not a
        # per-part face breakdown, so largest_component_pct is only *known* when
        # the mesh is a single part (= 100%). With >1 part it is left None
        # (gate skips with "not measured") rather than fabricating a passing
        # 100% — the prior code's silent-pass bug. SfM-level fragmentation is
        # already guarded upstream by the alignment gate.
        if faces and parts == 1:
            largest_pct = 100.0
        else:
            largest_pct = None
        metrics = {
            "faces": faces,
            "vertices": raw.get("vertices"),
            "components": raw.get("components"),
            "mesh_parts": parts,
            "largest_component_pct": largest_pct,
        }
        self._warn_if_no_metrics("model", metrics)
        return metrics

    # ----------------------------------------------------------- pipeline

    def create_chunk(self, label: str = "New Chunk"):
        """Start a fresh RC scene. RC has no notion of named chunks, but
        the selected component can be labeled.
        """
        self._notify("create_chunk", 0.0)
        with self.qc.stage("create_chunk") as st:
            st["label"] = label
            if self.mock_mode:
                print(f"[mock] create_chunk('{label}')")
                return
            # Force a new project on next _run_rc by clearing the flag and
            # deleting any pre-existing .rcproj for this name.
            self._project_initialized = False
            self._has_imported_mesh = False
            if os.path.isfile(self._project_file):
                os.remove(self._project_file)
            self._run_rc("-newScene", label="new_scene")

    def add_images(self, image_sources: Union[str, Sequence[str]]):
        """Add images from a directory (non-recursive) or list of paths."""
        self._notify("add_images", 0.0)
        with self.qc.stage("add_images") as st:
            if isinstance(image_sources, str):
                src_dir = image_sources
                st["source_dir"] = src_dir
                if not os.path.isdir(src_dir):
                    raise ValueError(f"Directory not found: {src_dir}")
                files = get_image_filepaths(src_dir)
                if not files:
                    raise ValueError(
                        f"No images found in directory: {src_dir}"
                    )
                st["image_count"] = len(files)
                if self.mock_mode:
                    print(f"[mock] add_images: {len(files)} file(s) from '{src_dir}'")
                else:
                    # A directory uses -addFolder; RC's -add is for a single
                    # file and fails ("Failed to add image <dir>") on a folder.
                    self._run_rc("-addFolder", src_dir, label="add_dir")
            else:
                files = list(image_sources)
                if not all(isinstance(p, str) for p in files):
                    raise TypeError(
                        "image_sources must be a path or list of paths"
                    )
                st["image_count"] = len(files)
                if self.mock_mode:
                    print(f"[mock] add_images: {len(files)} file(s)")
                    return
                # RC's -add takes a single file, so emit one -add per file
                # (all in one invocation): "-add f1 -add f2 ...".
                add_cmds: List[str] = []
                for f in files:
                    add_cmds += ["-add", f]
                self._run_rc(*add_cmds, label="add_files")
            print(f"Added {len(files)} images to scene.")

    def add_image_dirs(self, dirs: Sequence[str]):
        """Add images from multiple directories — RC keeps them in one scene."""
        self._notify("add_image_dirs", 0.0)
        with self.qc.stage("add_image_dirs") as st:
            st["dirs"] = list(dirs)
            per_dir: List[Dict[str, Any]] = []
            total = 0
            for d in dirs:
                if not os.path.isdir(d):
                    raise ValueError(f"Directory not found: {d}")
                here = get_image_filepaths(d)
                total += len(here)
                per_dir.append({"dir": d, "count": len(here)})
                if self.mock_mode:
                    print(f"[mock] add {len(here)} file(s) from '{d}'")
                else:
                    # -addFolder for a directory (-add is single-file only).
                    self._run_rc("-addFolder", d, label=f"add_dir:{os.path.basename(d)}")
            st["per_dir"] = per_dir
            st["total_image_count"] = total
            print(f"Added {total} images from {len(dirs)} directories.")

    # curate_input_set / equalize_exposures are inherited from PrepStagesMixin.

    def triage_images(self, quality_threshold: float = 0.5):
        """No direct RC equivalent. Externally pre-cull frames (sharpness,
        exposure) before calling :meth:`add_images`. Stage is a no-op kept
        for API parity with MetashapeWorkflow.
        """
        self._notify("triage_images", 0.0)
        with self.qc.stage("triage") as st:
            st["quality_threshold"] = quality_threshold
            st["note"] = "RC has no built-in triage; pre-cull externally."
            print(
                "[triage] no-op - RC has no built-in image triage. "
                "Pre-cull frames before add_images()."
            )

    def align_photos(
        self,
        downscale: int = 2,
        generic_preselection: bool = True,
        reference_preselection: bool = True,
        keypoint_limit: int = 60000,
        tiepoint_limit: int = 10000,
        filter_mask: bool = False,
    ):
        """Run RC alignment (SfM).

        NONE of these parameters reach RealityScan — the CLI has no alignment
        tuning flags (RC tunes via per-app/per-project settings), so the stage
        issues a bare ``-align``. The parameters exist for API parity with
        :meth:`MetashapeWorkflow.align_photos` (same signature/defaults) and
        are recorded in the QC sidecar for diagnostics only; ``filter_mask``
        included (mask import itself is not wired — see :meth:`import_masks`).
        """
        self._notify("align_photos", 0.0)
        with self.qc.stage("align") as st:
            st["downscale"] = downscale
            st["filter_mask"] = filter_mask
            st["params_note"] = (
                "RC CLI ignores keypoint/tiepoint/preselection params; "
                "tune via Settings/AlignmentSettings.xml on disk if needed."
            )
            if self.mock_mode:
                print(f"[mock] align_photos(downscale={downscale})")
                return
            self._run_rc("-align", label="align")
            metrics = self._alignment_metrics()
            # Cache for align_photos_with_retry: _alignment_metrics costs a
            # full RC -exportReport invocation, so the threshold check reuses
            # this measurement instead of re-running it.
            self._last_align_metrics = metrics
            st.update(metrics)
            if metrics["aligned_count"] == 0:
                raise RuntimeError(
                    "No cameras aligned. Check image overlap or input quality."
                )
            ac = metrics["aligned_count"]
            tc = metrics["total_count"]
            ap = metrics["aligned_pct"]
            if ac is None or tc is None:
                print("Aligned (metrics not extracted from RC report).")
            else:
                pct_str = f"{ap:.1f}%" if ap is not None else "?"
                print(f"Aligned {ac}/{tc} cameras ({pct_str}).")
        self.gate.check("align", metrics)
        self._checkpoint("align")

    def align_photos_with_retry(
        self,
        downscale: int = 2,
        generic_preselection: bool = True,
        reference_preselection: bool = True,
        keypoint_limit: int = 60000,
        tiepoint_limit: int = 10000,
        min_aligned_pct: float = 50.0,
    ):
        """Run alignment; warn if under ``min_aligned_pct``.

        Unlike :meth:`MetashapeWorkflow.align_photos_with_retry`, RC's CLI
        offers no meaningful retry knob — re-running ``-align`` on the
        same project produces the same result. So this method runs align
        once and emits a QC warning when the result is below the
        threshold; the caller can then capture a fresh frame set or tune
        RC's Settings/AlignmentSettings.xml on disk and re-run.
        """
        self.align_photos(
            downscale=downscale,
            generic_preselection=generic_preselection,
            reference_preselection=reference_preselection,
            keypoint_limit=keypoint_limit,
            tiepoint_limit=tiepoint_limit,
        )
        if self.mock_mode:
            return
        # Reuse align_photos' measurement — _alignment_metrics costs a full
        # RC -exportReport invocation per call.
        metrics = getattr(self, "_last_align_metrics", None)
        if metrics is None:
            metrics = self._alignment_metrics()
        pct = metrics.get("aligned_pct")
        if pct is None:
            self.qc.warn(
                "align_photos_with_retry: aligned_pct not measured; "
                "cannot evaluate min_aligned_pct threshold."
            )
            return
        if pct < min_aligned_pct:
            self.qc.warn(
                f"align_photos_with_retry: aligned_pct {pct:.1f}% "
                f"< {min_aligned_pct}% — no auto-retry available on RC; "
                f"adjust input or RC alignment settings and re-run."
            )

    def refine_alignment(self, *args, **kwargs):
        """RC performs alignment refinement internally during ``-align``;
        no separate CLI step. No-op kept for API parity. Args/kwargs are
        recorded in the QC log so a caller passing Metashape-style
        thresholds knows they were dropped.
        """
        self._notify("refine_alignment", 0.0)
        with self.qc.stage("refine_alignment") as st:
            st["note"] = "RC refines alignment as part of -align; no-op here."
            if args or kwargs:
                st["dropped_args"] = list(args)
                st["dropped_kwargs"] = dict(kwargs)

    def dedupe_cameras_by_pose(self, *args, **kwargs):
        """No direct RC equivalent. Stage left as a no-op."""
        with self.qc.stage("dedupe_cameras") as st:
            st["note"] = "Not implemented for RC."
            if args or kwargs:
                st["dropped_args"] = list(args)
                st["dropped_kwargs"] = dict(kwargs)

    def calibrate_colors(self, *args, **kwargs):
        """RC applies color correction inside ``-calculateTexture`` via
        its MosaicBlending. No separate stage needed.
        """
        with self.qc.stage("calibrate_colors") as st:
            st["note"] = "Folded into calculateTexture for RC."
            if args or kwargs:
                st["dropped_args"] = list(args)
                st["dropped_kwargs"] = dict(kwargs)

    def generate_masks(
        self,
        source_dir: str,
        masks_dir: Optional[str] = None,
        model_name: str = "u2net",
    ) -> Optional[str]:
        """Run rembg on ``source_dir`` → write per-image alpha masks.
        Identical contract to MetashapeWorkflow.generate_masks; same
        pythontk helper, so DRY by construction.
        """
        self._notify("generate_masks", 0.0)
        masks_dir = masks_dir or os.path.join(self.project_path, "masks")
        with self.qc.stage("generate_masks") as st:
            st["source_dir"] = source_dir
            st["masks_dir"] = masks_dir
            st["model"] = model_name
            try:
                from pythontk import MaskGenerator
            except ImportError:
                self.qc.warn("MaskGenerator not importable (pythontk missing?)")
                return None
            gen = MaskGenerator(model_name=model_name)
            if not gen.is_available():
                self.qc.warn(
                    "rembg+PIL not installed; install with "
                    "`pip install rembg pillow` to enable masks."
                )
                return None
            written = gen.generate_masks(source_dir, masks_dir)
            st["count"] = len(written)
            print(f"Generated {len(written)} masks -> {masks_dir}")
            return masks_dir if written else None

    def import_masks(self, masks_dir: str, mask_source: str = "alpha"):
        """RC accepts per-image masks named ``<image>.png`` next to the
        source images. This helper copies / symlinks masks from
        ``masks_dir`` into a layout RC will discover on next ``-add``.
        v1 implementation is a stub; wire when masking is enabled.
        """
        with self.qc.stage("masks") as st:
            st["masks_dir"] = masks_dir
            st["mask_source"] = mask_source
            st["note"] = (
                "RC mask import is stage-stubbed; populate masks alongside "
                "source images using RC's expected naming, then re-add."
            )

    def generate_depth_maps(self, *args, **kwargs):
        """RC does not expose depth maps as a separate stage — mesh calc
        produces them internally. No-op kept for API parity.
        """
        self._notify("generate_depth_maps", 0.0)
        with self.qc.stage("depth") as st:
            st["note"] = "Folded into calculate*Model for RC."
            if args or kwargs:
                st["dropped_args"] = list(args)
                st["dropped_kwargs"] = dict(kwargs)

    def build_model(
        self,
        source_data=None,   # ignored; RC uses internal depth maps
        surface_type=None,  # ignored
        interpolation=None, # ignored
        face_count: Optional[str] = None,  # "preview" | "normal" | "high"
    ):
        """Build a polygon mesh. ``face_count`` selects the RC quality
        preset (``preview`` / ``normal`` / ``high``); defaults to ``normal``.
        """
        self._notify("build_model", 0.0)
        with self.qc.stage("model") as st:
            quality = (face_count or "normal").lower()
            cmd = {
                "preview": "-calculatePreviewModel",
                "normal":  "-calculateNormalModel",
                "high":    "-calculateHighModel",
            }.get(quality)
            if cmd is None:
                raise ValueError(
                    f"face_count must be one of 'preview','normal','high'; got {face_count!r}"
                )
            st["quality"] = quality
            if self.mock_mode:
                print(f"[mock] build_model({quality})")
                # Auto-mesh replaces any imported mesh as the active model.
                self._has_imported_mesh = False
                return
            self._run_rc(cmd, label=f"model_{quality}")
            self._has_imported_mesh = False
            metrics = self._mesh_metrics()
            st.update(metrics)
            faces = metrics["faces"]
            comps = metrics["components"]
            lpct = metrics["largest_component_pct"]
            if faces is None:
                print("Model built (metrics not extracted from RC report).")
            else:
                lpct_str = f"{lpct:.1f}%" if lpct is not None else "?"
                print(
                    f"Model built: {faces} faces, {comps} components, "
                    f"largest {lpct_str} of total."
                )
        self.gate.check("model", metrics)
        self._checkpoint("model")

    def clean_mesh(
        self,
        remove_components_face_threshold: int = 100,
        close_holes_level: int = 30,
        smooth_strength: int = 0,
    ):
        """Mesh cleanup via ``-setMinComponentSize N`` + ``-cleanModel``.

        Only ``remove_components_face_threshold`` reaches RC.
        ``close_holes_level`` and ``smooth_strength`` have no RC CLI
        equivalent — both are accepted for API parity with
        :meth:`MetashapeWorkflow.clean_mesh`, QC-logged, and ignored.

        UNVERIFIED semantics note: this code treats ``-setMinComponentSize``
        as a mesh-island *triangle* floor; historic RealityCapture CLI docs
        describe it as the minimal *camera count per alignment component*.
        Verify against a live RC A/B before leaning on this stage for
        floater cleanup (see TUNING.md).
        """
        self._notify("clean_mesh", 0.0)
        with self.qc.stage("clean_mesh") as st:
            st["remove_components_face_threshold"] = remove_components_face_threshold
            st["close_holes_level"] = close_holes_level
            st["smooth_strength"] = smooth_strength
            if self.mock_mode:
                print(
                    f"[mock] clean_mesh(remove<{remove_components_face_threshold},"
                    f" closeHoles={close_holes_level})"
                )
                return
            commands: List[str] = []
            if remove_components_face_threshold > 0:
                commands += [
                    "-setMinComponentSize",
                    str(remove_components_face_threshold),
                ]
            if commands:
                self._run_rc(*commands, "-cleanModel", label="clean_mesh")
            metrics = self._mesh_metrics()
            st["after"] = metrics
        self._checkpoint("clean_mesh")

    def simplify_model(self, target_face_count: int = 20_000_000):
        """Simplify the densest model to ~``target_face_count`` triangles.

        This is the fix for the dense-mesh unwrap failure: the full high
        model overflows the UV-atlas budget, so ``-unwrap`` aborts with
        *"increase the maximal texture count or the maximal texture
        resolution."* Simplifying first keeps the layout within a few 8K
        pages. **Texture quality is unaffected** — the bake samples the
        source photos at 8K, not the mesh — only geometric density drops
        (20M tris is still highly detailed and comparable to the Metashape
        deliverable). Auto-skipped when a mesh was imported (its topology
        and UVs are authored, not ours to alter).
        """
        self._notify("simplify_model", 0.0)
        with self.qc.stage("simplify") as st:
            st["target_face_count"] = target_face_count
            if self._has_imported_mesh:
                st["note"] = "imported mesh — simplify skipped to preserve authored topology."
                print("[simplify] skipped (imported mesh).")
                return
            if self.mock_mode:
                print(f"[mock] simplify_model({target_face_count})")
                return
            # -simplify reduces the active model in place and leaves the simplified
            # result selected for unwrap. RealityScan auto-selects a freshly
            # calculated model, and exactly one model is built per run, so no
            # explicit model selection is needed. (`-selectMaximalModel` is not
            # exposed over the RSNode REST transport — it 400s as an unknown
            # command — and `-simplify` alone works on both transports.)
            self._run_rc("-simplify", str(target_face_count), label="simplify")
            metrics = self._mesh_metrics()
            st["after"] = metrics
            faces = metrics.get("faces")
            print(
                f"Simplified toward {target_face_count:,} tris "
                f"({faces if faces is not None else '?'} reported)."
            )
        self._checkpoint("simplify")

    def reduce_overlap(self, *args, **kwargs):
        """No RC equivalent. No-op kept for API parity."""
        with self.qc.stage("reduce_overlap") as st:
            st["note"] = "Not implemented for RC."
            if args or kwargs:
                st["dropped_args"] = list(args)
                st["dropped_kwargs"] = dict(kwargs)

    def import_model(self, mesh_path: str):
        """Import an external low-poly mesh into the project (Maya-authored
        blockout, etc.). Subsequent :meth:`build_texture` projects cameras
        onto this mesh using **its existing UVs** — the auto-unwrap is
        suppressed once an imported mesh is marked active.
        """
        self._notify("import_model", 0.0)
        with self.qc.stage("import_model") as st:
            st["mesh_path"] = mesh_path
            if self.mock_mode:
                print(f"[mock] import_model('{mesh_path}')")
                self._has_imported_mesh = True
                return
            if not os.path.isfile(mesh_path):
                raise ValueError(f"Mesh file not found: {mesh_path}")
            self._run_rc("-importModel", mesh_path, label="import_model")
            self._has_imported_mesh = True
            print(f"Imported model: {mesh_path}")
        self._checkpoint("import_model")

    def build_texture(
        self,
        texture_size: int = 4096,
        texture_type=None,    # accepted for parity; RC has no CLI hook here
        blending_mode=None,   # accepted for parity; RC uses internal blending
        mapping_mode=None,    # accepted for parity; controlled via RC settings
        ghosting_filter: bool = True,
    ):
        """Unwrap (when no mesh was imported) + bake texture from solved
        cameras onto the current mesh.

        ``texture_size`` is RECORDED in the QC log but **not passed to RC**
        — RC's texture size comes from app settings (Texturing.xml), not
        the CLI. To honor this caller-side, write the value into the
        per-project settings file before invoking. Same for blending /
        mapping modes.
        """
        self._notify("build_texture", 0.0)
        with self.qc.stage("texture") as st:
            st["size_request"] = texture_size
            st["ghosting_filter"] = ghosting_filter
            st["unwrap_skipped"] = self._has_imported_mesh
            st["params_note"] = (
                "texture_size / blending / mapping are not honored at the "
                "CLI level; configure via RC's Settings/*.xml on disk."
            )
            if self.mock_mode:
                print(
                    f"[mock] build_texture(size_request={texture_size}, "
                    f"unwrap={'skipped' if self._has_imported_mesh else 'on'})"
                )
                return
            commands: List[str] = []
            if not self._has_imported_mesh:
                commands.append("-unwrap")
            commands.append("-calculateTexture")
            self._run_rc(*commands, label="texture")
            st["completed"] = True
            print(
                f"Texture built (size_request={texture_size}; "
                f"unwrap={'skipped' if self._has_imported_mesh else 'on'})."
            )
        self.gate.check("texture", {"coverage_pct": None})
        self._checkpoint("texture")

    def save_project(self):
        """RC saves on every CLI call (``-save`` is appended); this is a
        no-op that records the project path for parity with Metashape.
        """
        self._notify("save_project", 0.0)
        with self.qc.stage("save") as st:
            st["path"] = self._project_file
            print(f"Project (auto-saved): {self._project_file}")

    def export_model(
        self,
        export_format: Optional[str] = None,  # 'obj' | 'ply' | 'fbx'
        binary: bool = True,
        precision: int = 6,
        texture_format=None,
        save_texture: bool = True,
        save_normals: bool = True,
        save_colors: bool = True,
        save_cameras: bool = False,
        overwrite: bool = True,
    ):
        """Export the current model. Defaults to OBJ with diffuse texture.

        Only ``export_format`` (the output extension) reaches RC — the
        command is a bare ``-exportSelectedModel <path>``, so ``binary`` /
        ``precision`` / ``texture_format`` / ``save_*`` / ``overwrite`` are
        parity-only (Metashape honors them; RC uses its GUI-persisted export
        settings). Configure RC's export settings once in the app if the
        defaults are wrong.
        """
        self._notify("export_model", 0.0)
        with self.qc.stage("export") as st:
            fmt = (export_format or "obj").lower()
            if fmt not in {"obj", "ply", "fbx"}:
                raise ValueError(
                    f"Unsupported export format: {export_format!r}. "
                    f"Supported: obj, ply, fbx"
                )
            export_path = os.path.join(self.project_path, f"{self.name}.{fmt}")
            if not overwrite and os.path.exists(export_path):
                raise FileExistsError(
                    f"'{export_path}' exists. Pass overwrite=True to replace."
                )
            st["path"] = export_path
            if self.mock_mode:
                print(f"[mock] export_model -> {export_path}")
                return
            self._run_rc("-exportSelectedModel", export_path, label="export")
            print(f"Exported model: {export_path}")

    def export_qc(self):
        """Export RC's processing report XML and append to the QC log."""
        self._notify("export_qc", 0.0)
        with self.qc.stage("report") as st:
            if self.mock_mode:
                print("[mock] export_qc")
                return
            rep = self._export_report("final")
            st["report_path"] = rep
            if rep:
                print(f"Report: {rep}")

    def _teardown_connection(self) -> None:
        """Release the resolved transport's resources at end of run.

        Duck-typed: the RSNode transport exposes ``close()`` (frees its session
        slot); the CLI transport has none, so this is a no-op. Only the resolved
        connection is touched — never resolves one just to tear it down (mock /
        unused runs leave ``self._conn`` None).
        """
        close = getattr(self._conn, "close", None)
        if callable(close):
            try:
                close()
            except Exception as e:  # teardown must never mask the run's outcome
                import sys
                print(f"[rc] connection teardown warning: {e}", file=sys.stderr)

    def finalize_run(self, success: bool = True) -> str:
        """Flush the QC JSON sidecar + release the transport. Returns the path."""
        self.qc.finalize(success)
        self._teardown_connection()
        print(f"QC sidecar: {self.qc.path}")
        return self.qc.path


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the RealityCapture workflow.")
    parser.add_argument("--frames", required=True, help="Source frames directory.")
    parser.add_argument("--project", required=True, help="Project output directory.")
    parser.add_argument("--name", default=None, help="Project basename.")
    parser.add_argument(
        "--quality", default="normal", choices=["preview", "normal", "high"],
        help="Mesh quality preset.",
    )
    parser.add_argument(
        "--blockout", default=None,
        help="Optional path to a low-poly mesh to bake the texture onto.",
    )
    args = parser.parse_args()

    name = args.name or os.path.basename(os.path.normpath(args.project))
    rc = RealityCaptureWorkflow(args.project, name=name)
    print(rc.get_license_info())
    try:
        rc.create_chunk(f"{name} Chunk")
        rc.add_images(args.frames)
        rc.align_photos()
        if args.blockout:
            rc.import_model(args.blockout)
        else:
            rc.build_model(face_count=args.quality)
            rc.clean_mesh()
            rc.simplify_model()
        rc.build_texture()
        rc.save_project()
        rc.export_model()
        rc.export_qc()
        rc.finalize_run(success=True)
    except Exception:
        rc.finalize_run(success=False)
        raise
