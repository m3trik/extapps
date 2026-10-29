# !/usr/bin/python
# coding=utf-8
"""Train a Gaussian splat with Brush from COLMAP data and export it for Unity or web.

Engine wrappers for the splat track, plus a Switchboard panel (titled "Brush"):

* :class:`._gaussian_splat_workflow.GaussianSplatWorkflow` — the **Brush** splat
  trainer (https://github.com/ArthurBrussee/brush). Consumes a COLMAP dataset
  (``images/`` + ``sparse/0/``, e.g. from Metashape's ``--export-colmap``) and
  trains a splat → ``.ply``. Handles the full camera set efficiently.
* :class:`._splat_publish.SplatPublishWorkflow` — the engine-delivery stage: wraps
  PlayCanvas's **splat-transform** (https://github.com/playcanvas/splat-transform)
  to clean (floater removal/crop) and convert the Brush ``.ply`` to **Unity**
  ``.spz`` and **browser** ``.sog``/``.compressed.ply`` + a self-contained
  ``.html`` viewer.

Drive both via :mod:`extapps.photogrammetry.gaussian_splat_workflow.run_combined`,
or interactively from tentacle's Brush Splat Workflow panel
(``slots/tools/gaussian_splat_workflow.py``, through :class:`GaussianSplatRunner`).

For a UV-textured **mesh** deliverable instead of a splat, the **experimental**
SuGaR track is a *separate* package (clear separation of concerns) —
:mod:`extapps.photogrammetry.sugar_mesh_workflow`.

Exposed via :func:`pythontk.bootstrap_package` (lazy) so importing the headless
runner never eagerly pulls in Qt through the panel runners.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.photogrammetry.gaussian_splat_workflow"


DEFAULT_INCLUDE = {
    # Only the class: find_brush_exe / is_brush_available moved onto it, and
    # re-exporting them flat would recreate the module-level surface the
    # encapsulation standard removes. Call GaussianSplatWorkflow.<name>.
    "_gaussian_splat_workflow": ["GaussianSplatWorkflow"],
    "_gaussian_splat_runner": ["GaussianSplatRunner", "BrushInstallRunner"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "BrushInstallRunner",
    "GaussianSplatRunner",
    "GaussianSplatWorkflow",
]
