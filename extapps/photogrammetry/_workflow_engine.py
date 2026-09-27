# !/usr/bin/python
# coding=utf-8
"""The lifecycle every photogrammetry engine shares: one base, five engines.

``MetashapeWorkflow``, ``RealityCaptureWorkflow``, ``GaussianSplatWorkflow``,
``SplatPublishWorkflow`` and ``SugarMeshWorkflow`` each opened a run the same
way -- bind ``project_path`` / ``name`` / ``progress``, make the project and
``logs/`` folders, open a :class:`pythontk.QcLog` sidecar seeded with the run's
identity and ``mock_mode`` -- ran their external tool the same way (argv to
``logs/<label>.log``, merged output), and closed the same way (finalize the
sidecar, print its path). Five hand-kept copies, four of them calling
``subprocess`` directly past the rule that every launch routes through
:class:`pythontk.AppLauncher`. This base owns all three phases once:

* :meth:`WorkflowEngine._open_run` -- identity, folders, the QC sidecar.
* :meth:`WorkflowEngine._run_logged` -- a blocking tool run through
  ``AppLauncher.run``, its merged output streamed into ``logs/<label>.log``
  under a ``# <header>`` first line.
* :meth:`WorkflowEngine.finalize_run` -- flush the sidecar and return its path;
  an engine with resources to release extends it (RealityScan's transport).

Progress reporting stays :class:`ProgressNotifyMixin`'s (this base inherits it).
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Callable, Dict, Optional, Sequence

from pythontk import AppLauncher, QcLog

from ._progress_notify import ProgressNotifyMixin


class WorkflowEngine(ProgressNotifyMixin):
    """Run lifecycle shared by the photogrammetry engines.

    Host contract: set ``self.mock_mode`` before calling :meth:`_open_run`
    (the sidecar records it).
    """

    #: The sidecar's file name after the run name: ``<name><QC_SUFFIX>``.
    QC_SUFFIX = "_qc.json"

    mock_mode: bool = False

    def _open_run(
        self,
        project_path: str,
        name: str,
        progress: Optional[Callable[[str, float], None]] = None,
        qc_fields: Optional[Dict[str, Any]] = None,
        make_dirs: bool = True,
    ) -> None:
        """Bind the run's identity, make its folders and open its QC sidecar.

        Parameters:
            project_path: The run's folder (project + outputs + ``logs/``).
            name: Run basename; names the sidecar.
            progress: ``fn(stage, fraction)`` progress callback, or ``None``.
            qc_fields: Engine-specific sidecar fields, recorded (in order)
                between ``project_name`` and ``mock_mode``.
            make_dirs: Create ``project_path`` and ``logs/`` now. An engine
                that creates its folder on first write (Metashape) passes
                ``False``; :meth:`_run_logged` still makes ``logs/`` on use.
        """
        self.project_path = project_path
        self.name = name
        self.progress = progress
        self._logs_dir = os.path.join(project_path, "logs")
        if make_dirs:
            os.makedirs(self._logs_dir, exist_ok=True)
        self.qc = QcLog(os.path.join(project_path, f"{name}{self.QC_SUFFIX}"))
        self.qc.set("project_name", name)
        for key, value in (qc_fields or {}).items():
            self.qc.set(key, value)
        self.qc.set("mock_mode", self.mock_mode)

    def _log_path(self, label: str) -> str:
        """``logs/<label>.log`` (the folder is created on demand)."""
        os.makedirs(self._logs_dir, exist_ok=True)
        return os.path.join(self._logs_dir, f"{label}.log")

    def _run_logged(
        self,
        argv: Sequence[str],
        label: str,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        header: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Run *argv* to completion, its merged output streamed to the run log.

        Routed through :meth:`pythontk.AppLauncher.run` (the ecosystem's one
        subprocess boundary). The log opens with ``# <header>`` -- by default
        ``# argv: [...]`` -- then every line the tool prints, flushed as it
        arrives, so a long run can be tailed live.

        Parameters:
            argv: ``[program, *args]``.
            label: Log name (``logs/<label>.log``).
            timeout: Seconds before ``subprocess.TimeoutExpired``; ``None`` =
                no limit.
            cwd: Working directory for the tool.
            header: The log's first line (without the ``#``).

        Returns:
            The ``subprocess.CompletedProcess``; ``returncode`` is the tool's.

        Raises:
            FileNotFoundError: The program cannot be found.
            subprocess.TimeoutExpired: *timeout* was exceeded.
        """
        argv = [str(a) for a in argv]
        log_path = self._log_path(label)
        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            log.write(f"# {header if header is not None else f'argv: {argv}'}\n")
            log.flush()

            def _write(line: Optional[str]) -> None:
                if line is not None:  # None = an idle tick, nothing to write
                    log.write(line + "\n")
                    log.flush()

            return AppLauncher.run(
                argv[0], args=argv[1:], cwd=cwd, timeout=timeout, on_output=_write
            )

    def finalize_run(self, success: bool = True) -> str:
        """Write the QC JSON sidecar and return its path.

        Always call this in the caller's ``finally`` so even a failed run leaves
        a usable diagnostic on disk.
        """
        self.qc.finalize(success)
        print(f"QC sidecar: {self.qc.path}")
        return self.qc.path
