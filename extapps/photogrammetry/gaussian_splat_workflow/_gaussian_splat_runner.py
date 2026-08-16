# !/usr/bin/python
# coding=utf-8
"""Local, async runner the Brush (gaussian-splat) panel dispatches to.

A thin :class:`extapps.photogrammetry._process_runner.PyModuleRunner` subclass:
the base owns the :class:`~qtpy.QtCore.QProcess` machinery, and ``PyModuleRunner``
launches the headless driver as ``sys.executable -m ...run_combined`` (Brush's
``run_combined`` is a normal-Python driver that spawns ``brush.exe`` /
splat-transform itself, so it runs in the panel's own interpreter). This class
only supplies Brush exe discovery so the panel reports a missing install instead
of silently mocking.
"""
from __future__ import annotations

from typing import Optional

from .._process_runner import PyModuleRunner
from ._gaussian_splat_workflow import GaussianSplatWorkflow


class GaussianSplatRunner(PyModuleRunner):
    """Discover Brush + asynchronously drive its ``run_combined``."""

    MODULE = "extapps.photogrammetry.gaussian_splat_workflow.run_combined"

    @property
    def exe(self) -> Optional[str]:
        return GaussianSplatWorkflow.find_brush_exe()

    def is_available(self) -> bool:
        """True when a Brush executable was found (set BRUSH_EXE or install)."""
        return GaussianSplatWorkflow.is_brush_available()

    def _unavailable_message(self) -> str:
        return (
            "Brush not found. Install Brush (github.com/ArthurBrussee/brush) or "
            "set $BRUSH_EXE to its path."
        )


class BrushInstallRunner(PyModuleRunner):
    """Stream the Brush downloader (pythontk.AppInstaller) in a child process.

    Always reports *available* — running it is what *makes* Brush available —
    so it bypasses the engine-discovery gate the training runner enforces. The
    download lands in pythontk's managed-install catalog, which the parent's
    next :meth:`GaussianSplatWorkflow.find_brush_exe` then discovers (the catalog persists to disk, so
    the cross-process re-discovery needs no extra wiring).
    """

    MODULE = "extapps.photogrammetry.gaussian_splat_workflow._install_brush"

    @property
    def exe(self) -> Optional[str]:
        return None

    def is_available(self) -> bool:
        return True
