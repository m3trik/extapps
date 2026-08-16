# !/usr/bin/python
# coding=utf-8
"""Local, async runner the Metashape panel dispatches to.

A :class:`extapps.photogrammetry._process_runner.ProcessRunner` subclass: the
base owns the :class:`~qtpy.QtCore.QProcess` machinery (async launch, live
stdout streaming into the panel log, completion/error callbacks); this class
supplies the Metashape specifics — exe discovery via
:class:`MetashapeConnection` and the ``metashape.exe -r run_combined.py``
launch (the driver runs *inside* Metashape's bundled Python, which is why it
doesn't use the :class:`~extapps.photogrammetry._process_runner.PyModuleRunner`
variant the RealityScan / Brush panels do).

**Venv stage chain.** Metashape's bundled Python (3.9, no cv2/PIL/rembg,
no pymeshlab) can never run the input pre-processing stages *or* the
PyMeshLab mesh post-processing — a plain ``metashape.exe -r`` run silently
skips both. So the runner brackets the engine stage with venv stages under
**this** interpreter:

- **prep** (before): when a run wants pre-processing, :meth:`start` first
  executes ``run_combined --prep-only`` (cv2 lives here), parses the
  ``PREP_RESULT_JSON`` line it prints, and launches ``metashape.exe`` on
  the prepared frames with ``--skip-curate --skip-equalize``. A
  ``--curate-preview`` run is venv-only (Metashape is never launched).
- **post** (after): every full-pipeline run chains ``run_combined
  --post-only`` once the engine stage exits 0 — the PyMeshLab repair /
  refine / measure stages plus the ``"mesh"`` QC gate, written to their
  own ``<name>_post_qc.json`` sidecar. Skipped for ``--stop-after`` /
  prep-only / preview runs (no export exists) and after a failed or
  cancelled engine stage.

All stages stream into the same panel log; cancel kills whichever stage is
in flight and never launches the next one.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Callable, List, Optional, Sequence, Tuple

from qtpy import QtCore

from .._process_runner import ProcessRunner
from ._metashape_connection import MetashapeConnection
from .run_combined import PREP_RESULT_PREFIX

# Path to the headless pipeline driver run inside metashape.exe (and, for the
# venv prep stage, under this interpreter).
_RUNNER = os.path.join(os.path.dirname(__file__), "run_combined.py")

# The venv prep stage must run under a real Python — inside a DCC host (e.g.
# Maya) sys.executable is the DCC binary, which cannot execute a script path.
_PYTHON_EXE_RE = re.compile(r"^python(\d+(\.\d+)*)?w?(\.exe)?$", re.IGNORECASE)


class MetashapeRunner(ProcessRunner):
    """Discover + asynchronously drive ``run_combined`` in the local Metashape."""

    def __init__(self, exe: Optional[str] = None):
        super().__init__()
        self._conn = MetashapeConnection(exe=exe)
        self._prep_text: str = ""

    @property
    def exe(self) -> Optional[str]:
        return self._conn.exe

    def is_available(self) -> bool:
        """True when a local ``metashape.exe`` was found (a real run is possible)."""
        return self._conn.is_available()

    def _command(self, argv: Sequence[str]) -> Tuple[str, List[str]]:
        return self._conn.exe, ["-r", _RUNNER, *list(argv)]

    def _unavailable_message(self) -> str:
        return (
            "metashape.exe not found. Install Agisoft Metashape, or set "
            "$METASHAPE_EXE to its path."
        )

    # ------------------------------------------------------------ prep chain
    @staticmethod
    def _prep_mode(argv: Sequence[str]) -> Optional[str]:
        """How this argv wants the venv stage: ``"preview"`` (curation preview,
        venv-only — Metashape never launches), ``"chain"`` (prep in the venv,
        then metashape.exe on the result), or ``None`` (straight to Metashape:
        no single ``--frames-dir`` source, or every prep stage is skipped and
        masks aren't requested — nothing for a venv stage to do)."""
        argv = list(argv)
        if "--curate-preview" in argv:
            return "preview"
        if "--frames-dir" not in argv:
            return None
        if (
            "--skip-curate" in argv
            and "--skip-equalize" in argv
            and "--use-masks" not in argv
        ):
            return None
        return "chain"

    @staticmethod
    def _venv_python() -> Optional[str]:
        """This interpreter's executable when it is a plain Python, else None
        (a DCC-hosted panel can't exec a script path via its own binary)."""
        exe = sys.executable or ""
        return exe if _PYTHON_EXE_RE.match(os.path.basename(exe)) else None

    @staticmethod
    def _wants_post(argv: Sequence[str]) -> bool:
        """True when this argv describes a run that exports a model — the
        only runs a ``--post-only`` mesh stage can follow. Stop-after /
        prep-only / preview runs never export; an explicit ``--post-only``
        argv IS the post stage and must not chain another."""
        argv = list(argv)
        return not any(
            flag in argv
            for flag in ("--post-only", "--prep-only", "--curate-preview", "--stop-after")
        )

    @staticmethod
    def _argv_with_prepped_source(
        argv: Sequence[str], prepped_dir: str
    ) -> Optional[List[str]]:
        """Stage-2 argv: point ``--frames-dir`` at the prepared dir and skip the
        (already-run) prep stages engine-side. None when argv has no
        ``--frames-dir`` value to rewrite."""
        out = list(argv)
        try:
            i = out.index("--frames-dir")
            out[i + 1] = prepped_dir
        except (ValueError, IndexError):
            return None
        for flag in ("--skip-curate", "--skip-equalize"):
            if flag not in out:
                out.append(flag)
        return out

    @staticmethod
    def _parse_prep_result(text: str) -> Optional[dict]:
        """Last ``PREP_RESULT_JSON=...`` payload in the captured prep output,
        or None. Last one wins so a re-echoed/quoted earlier line can't shadow
        the real result."""
        result = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(PREP_RESULT_PREFIX):
                try:
                    result = json.loads(line[len(PREP_RESULT_PREFIX):])
                except ValueError:
                    result = None
        return result

    def _capture_on_line(
        self, on_line: Optional[Callable[[str], None]]
    ) -> Callable[[str], None]:
        """Tee streamed prep output into ``self._prep_text`` (tail-capped) for
        sentinel parsing while still forwarding to the panel log."""

        def wrapped(text: str) -> None:
            self._prep_text = (self._prep_text + text)[-65536:]
            if on_line is not None:
                on_line(text)

        return wrapped

    def _prep_continuation(
        self,
        argv: List[str],
        on_line: Optional[Callable[[str], None]],
        on_done: Optional[Callable[[int], None]],
        cwd: Optional[str],
    ) -> Callable[[int], None]:
        """The stage-1 (venv prep) completion handler: on success, launch
        metashape.exe on the prepared frames; on prep failure, fall back to the
        original argv (the engine-side stages then skip with their own
        warnings — no worse than the pre-chain behavior). A user cancel ends
        the run without launching stage 2."""

        def done(code: int) -> None:
            if self._cancelled:
                if on_done is not None:
                    on_done(code)
                return
            stage2 = None
            if code == 0:
                result = self._parse_prep_result(self._prep_text) or {}
                dirs = result.get("dirs") or []
                if len(dirs) == 1 and os.path.isdir(dirs[0]):
                    stage2 = self._argv_with_prepped_source(argv, dirs[0])
                    if stage2 is not None and on_line is not None:
                        on_line(
                            f"[prep] handing prepared frames to Metashape: "
                            f"{dirs[0]}\n"
                        )
            if stage2 is None:
                stage2 = argv
                if on_line is not None:
                    on_line(
                        "[prep] pre-processing unavailable or failed - "
                        "continuing with the original frames.\n"
                    )

            def launch() -> None:
                self._on_line = on_line
                self._on_done = on_done
                program, args = self._command(stage2)
                self._launch(program, args, cwd)

            # Deferred: reassigning self._proc synchronously here would drop
            # the last ref to the stage-1 QProcess from inside its own
            # finished handler (see ProcessRunner._on_finished).
            QtCore.QTimer.singleShot(0, launch)

        return done

    def _post_continuation(
        self,
        argv: List[str],
        on_line: Optional[Callable[[str], None]],
        on_done: Optional[Callable[[int], None]],
        cwd: Optional[str],
        python: str,
    ) -> Callable[[int], None]:
        """The engine-stage completion handler: on success, run the PyMeshLab
        mesh post-processing (``--post-only``) under the venv Python. A failed
        or user-cancelled engine stage reports its own code and never chains
        (there is no export to process)."""

        def done(code: int) -> None:
            if self._cancelled or code != 0:
                if on_done is not None:
                    on_done(code)
                return

            def launch() -> None:
                self._on_line = on_line
                self._on_done = on_done
                if on_line is not None:
                    on_line(
                        f"[post] running mesh post-processing under {python} ...\n"
                    )
                # Same PYTHONPATH propagation (and same venv-only scoping
                # rationale) as the prep stage.
                self._launch(
                    python,
                    [_RUNNER, "--post-only", *argv],
                    cwd,
                    extra_env={
                        "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)
                    },
                )

            # Deferred for the same last-QProcess-ref reason as the prep chain.
            QtCore.QTimer.singleShot(0, launch)

        return done

    # ------------------------------------------------------------ run
    def start(
        self,
        argv: Sequence[str],
        on_line: Optional[Callable[[str], None]] = None,
        on_done: Optional[Callable[[int], None]] = None,
        cwd: Optional[str] = None,
    ) -> None:
        argv = list(argv)
        # Post chain first: wrapping on_done here covers BOTH launch paths
        # below (direct engine launch and the prep-chain continuation, whose
        # engine stage inherits this wrapped on_done).
        post_python = self._venv_python()
        if post_python is not None and self._wants_post(argv):
            on_done = self._post_continuation(argv, on_line, on_done, cwd, post_python)
        mode = self._prep_mode(argv)
        python = post_python if mode else None
        if mode is None or python is None:
            if mode is not None and python is None and on_line is not None:
                on_line(
                    "[prep] host interpreter is not a plain Python "
                    f"({sys.executable or '?'}); skipping the venv "
                    "pre-processing stage - frames go to Metashape as-is.\n"
                )
            super().start(argv, on_line=on_line, on_done=on_done, cwd=cwd)
            return

        if self.is_running():
            raise RuntimeError("A run is already in progress.")
        if mode == "chain" and not self.is_available():
            raise FileNotFoundError(self._unavailable_message())

        self._cancelled = False
        self._prep_text = ""
        self._on_line = self._capture_on_line(on_line)
        self._on_done = (
            on_done
            if mode == "preview"
            else self._prep_continuation(argv, on_line, on_done, cwd)
        )
        prep_argv = argv if mode == "preview" else ["--prep-only", *argv]
        if on_line is not None:
            label = (
                "curation preview" if mode == "preview" else "input pre-processing"
            )
            on_line(f"[prep] running {label} under {python} ...\n")
        # Propagate this process's import path so the child resolves
        # extapps / pythontk regardless of install mode (as PyModuleRunner
        # does). Scoped to the venv stage only — metashape.exe's bundled
        # Python must never inherit the venv's (incompatible) site-packages.
        self._launch(
            python,
            [_RUNNER, *prep_argv],
            cwd,
            extra_env={"PYTHONPATH": os.pathsep.join(p for p in sys.path if p)},
        )
