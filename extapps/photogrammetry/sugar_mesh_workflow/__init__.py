# !/usr/bin/python
# coding=utf-8
"""SuGaR mesh-extraction workflow — **EXPERIMENTAL**, separate from the splat track.

This is intentionally split out from the core gaussian-splat track
(:mod:`..gaussian_splat_workflow` — Brush splat training + engine publish). SuGaR
produces a UV-textured ``.obj`` **mesh** (a different deliverable than a splat),
and it is an **experimental** path that is *not* part of the normal workflow:

* :class:`._sugar_mesh.SugarMeshWorkflow` — wraps SuGaR's full pipeline
  (https://github.com/Anttwo/SuGaR): a COLMAP dataset (``images/`` + ``sparse/0/``,
  e.g. from Metashape's ``--export-colmap``) → SuGaR trains its own vanilla-3DGS →
  fits + refines a SuGaR model → extracts a UV-textured ``.obj`` mesh. Needs a
  *capped* COLMAP export + a free GPU (its bundled vanilla-3DGS is the bottleneck).

Drive via :mod:`extapps.photogrammetry.sugar_mesh_workflow.run_combined`.

No side effects on import (CLI-only engine, no Switchboard panel — mirrors
``gaussian_splat_workflow`` and ``realityscan_workflow``).
"""
