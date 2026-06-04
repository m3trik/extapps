# !/usr/bin/python
# coding=utf-8
"""Photogrammetry umbrella — the photogrammetry tools and their shared domain layer.

Groups the reconstruction workflows — ``metashape_workflow`` /
``realityscan_workflow`` (SfM → mesh), ``gaussian_splat_workflow`` (Brush splat +
engine publish), and the **experimental** ``sugar_mesh_workflow`` (SuGaR → textured
mesh, kept separate from the splat track) — with the domain-shared infrastructure
they all use:

* :mod:`~extapps.photogrammetry.profile` — JSON I/O + tuning **profile** (keeps
  personal/site config out of source; resolved via :class:`pythontk.UserConfig`)
  and the per-engine semantic **preset** store.
* :mod:`~extapps.photogrammetry.prep_stages` — :class:`PrepStagesMixin`
  (dHash + sharpness curation, exposure equalization) shared by both SfM engines.
* ``_panel_slots`` / ``_process_runner`` / ``_shared_params`` — the shared
  Switchboard-panel scaffolding (base slots + frames-source mixin, the async
  ``QProcess`` runner, and the common pre-processing param specs) the
  Metashape / RealityCapture / Brush panels are thin subclasses of.

Domain-specific by design: this shared layer is used only by the photogrammetry
tools, so it lives here rather than in a generic ``extapps`` core (the genuinely
generic config-resolution mechanism is upstream in ``pythontk.UserConfig``).

No side effects on import — the tool panels register via the root
``extapps`` ``DEFAULT_INCLUDE`` and the ``uitk.external_apps.in_process``
entry points (see ``pyproject.toml``).
"""
