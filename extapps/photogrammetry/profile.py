# !/usr/bin/python
# coding=utf-8
"""Photogrammetry I/O + tuning **profile** — site/personal config kept out of source.

The engines, prep stages, and runners in this package are generic and reusable;
what makes a pipeline *yours* (where inputs/outputs live, the per-project culling
and splat tuning) is configuration, not code. That configuration lives in a JSON
**profile** resolved via :class:`pythontk.UserConfig`:

* The package ships a generic, non-personal :func:`_packaged_default` fallback — a
  fresh clone works with zero setup, writing under the user's own config dir + temp.
  No profile file is committed to the repo; :data:`EXAMPLE_PROFILE` (a template) and
  :func:`init_user_profile` (writes it to the user-config dir) replace a shipped file.
* A user drops a **partial** ``photogrammetry.json`` at
  ``<user-config>/uitk/extapps/photogrammetry.json`` (the same consolidated root
  uitk's ``PresetManager`` uses — so the GUI panel and this headless path agree),
  or points ``$PHOTOGRAMMETRY_PROFILE`` at one. Only overridden keys are needed;
  the rest fall back to the default (deep-merge).

Path values support ``~`` / ``${ENV}`` expansion and two intra-document tokens —
``{graphics_root}`` and ``{scratch_root}`` — so the derived roots stay DRY.

Resolution is **Qt-free** (``pythontk.UserConfig`` uses plain ``os``/``json``), so
this module is import-safe in the headless Metashape (Python 3.9, no Qt) context.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from typing import List, Optional

from pythontk import PresetStore, UserConfig, user_config_root

PROFILE_NAME = "photogrammetry"
PROFILE_PACKAGE = "extapps"
PROFILE_ENV = "PHOTOGRAMMETRY_PROFILE"

# Opt-in **run templates** ship as built-in JSON presets under **per-engine**
# subdirs of this dir (``presets/<engine>/``), layered under a per-engine user
# tier via :class:`pythontk.PresetStore` (see :func:`preset_store` /
# :func:`get_preset`). Presets are **engine-scoped**: a Metashape tuning preset
# (align/depth downscale, matchPhotos limits, depth filter) is meaningless to
# RealityScan and vice-versa, so each engine has its own built-in + user dirs and
# nothing is shared (duplicate a template per engine to use it on both). They live
# beside the package (not in the profile) so the same presets are available
# headlessly (the runners) and in the UI panel.
PRESETS_NAME = "photogrammetry_presets"
PRESETS_DIR = os.path.join(os.path.dirname(__file__), "presets")

# Image extensions recognized when discovering capture subdirectories. Single
# source of truth for the photogrammetry I/O layer.
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")

# Reconstruction quality tiers, mapped per-engine by the runners. Single
# source of truth for the tier names: the runners use it for their --quality
# choices AND for validating preset/profile-supplied values (argparse only
# validates CLI-passed values, not defaults).
QUALITY_TIERS = ("draft", "balanced", "max")

# --- schema SSoT --------------------------------------------------------------
# Derived roots (interpolate ``{graphics_root}`` / ``{scratch_root}``) and the
# prep/splat tuning are defined exactly once here; both the packaged default and
# the copy-me example are built from them via :func:`_skeleton`, so the schema
# can't drift between the two.
_DERIVED_ROOTS = {
    "input_root": "{graphics_root}/input",
    "metashape_output_root": "{graphics_root}/metashape",
    # Synced deliverable root for RealityScan: RC works in local scratch
    # (realityscan_scratch_root) — its live multi-GB project I/O must not run in
    # a cloud-sync folder — then the finished deliverables are published here.
    "realityscan_output_root": "{graphics_root}/RealityScan/output",
    "photogrammetry_root": "{graphics_root}/comparison",
    "realityscan_scratch_root": "{scratch_root}/rc_out",
    "gsplat_scratch_root": "{scratch_root}/gsplat_out",
}
_DERIVED_ROOT_KEYS = tuple(_DERIVED_ROOTS)

_TUNING = {
    # Optional per-engine install paths. Point one at a NETWORK install (e.g.
    # "//server/share/Metashape/metashape.exe") or any non-standard location;
    # empty = auto-discover. Consulted by each engine's discovery AFTER its
    # *_EXE / *_DIR env var but BEFORE standard discovery, so a configured path
    # is preferred over an auto-found local install yet an env var still wins
    # for a one-off override. "~" / "${ENV}" are expanded on read. Keys:
    # metashape_exe / realityscan_exe / brush_exe (executables), sugar_dir
    # (the SuGaR repo dir holding train_full_pipeline.py).
    "apps": {
        "metashape_exe": "",
        "realityscan_exe": "",
        "brush_exe": "",
        "sugar_dir": "",
    },
    # Curation baseline is deliberately conservative — the primary ingest path
    # is continuous video (already thinned to sharpest-per-window at
    # extraction), where dHash dedup strips the small-baseline overlap SfM
    # triangulates from and a percentile blur cut ALWAYS deletes that share of
    # the set even when every frame is sharp (TUNING.md: a 2.3% over-cull cost
    # ~10 points of alignment coverage on the verified hard set). Only the
    # median-fraction guard stays on: it removes catastrophically defocused
    # frames without touching healthy ones. Raise hash_threshold/percentile
    # per-run (panel / preset / flags) for redundant static photo sets.
    "curate": {
        "hash_threshold": 0,
        "sharpness_floor": 0.0,
        "sharpness_percentile": 0,
        "min_sharpness_fraction_of_median": 0.15,
        "keep_per_cluster": 1,
    },
    "equalize": {"strength": 0.5, "reference": "median"},
    # Reconstruction / mesh-cleanup tuning shared by the mesh engines. These are
    # the few noise-control levers reachable from RealityScan's CLI; the stronger
    # ones (depth/image downscale, depth-map filtering strength, a tight
    # reconstruction region, subject masking) live in RC's per-project Settings or
    # the GUI and can't be set from the command line — see TUNING.md for the full
    # per-environment recipe (and the Metashape runner's own --depth-filter /
    # --align-downscale knobs, which DO reach those levers).
    "reconstruct": {
        # Mesh-cleanup floor: disconnected components smaller than this many
        # triangles are deleted (fed to clean_mesh -> RC -setMinComponentSize).
        # The main CLI-reachable lever against speckle / "snow" floaters. The
        # baseline keeps a conservative value (catches only dust) so a plain run
        # is unchanged. NOTE: on specular / low-texture metal do NOT crank this -
        # it strips real disconnected detail without fixing the depth-level noise
        # that warps geometry; the specular_metal preset denoises with a light
        # smooth pass (smooth_strength=1) instead and deliberately leaves this at
        # the baseline. See TUNING.md.
        "min_component_size": 100,
        # Triangle budget the dense model is decimated to before UV unwrap, so
        # the atlas fits the texture pages (the dense-mesh unwrap-overflow fix).
        # Texture detail is unaffected — it bakes from the source photos, not the
        # mesh.
        "simplify_target": 20_000_000,
    },
    "gsplat": {
        "max_resolution": 1920,
        # None = derive Brush training steps from the quality tier (profile
        # "quality" / --quality: draft 7k / balanced 30k / max 50k). Set a
        # number to pin the step count regardless of tier. Shipping a number
        # here would shadow the tier for EVERY profile (get_profile
        # deep-merges this block, so the key is always present).
        "total_steps": None,
        "max_splats": 10_000_000,
        "sh_degree": 3,
        # COLMAP-export camera cap (Metashape --export-colmap). 0 = export the
        # FULL aligned set — Brush handles it and camera coverage is a primary
        # splat-quality lever, so capping by default silently degraded every
        # splat. Set (or pass --colmap-max-cameras) ~300-400 ONLY when the
        # dataset feeds SuGaR: its bundled vanilla-3DGS stalls on an 8 GB GPU
        # past a few hundred views.
        "colmap_max_cameras": 0,
    },
    "sugar": {
        "regularization": "dn_consistency",  # sdf | density | dn_consistency
        "high_poly": True,
        "surface_level": 0.3,
    },
    # Engine-delivery (splat-transform): clean the trained .ply, then convert to
    # engine formats. unity -> .spz; web -> .sog/.compressed.ply + .html viewer.
    "publish": {
        "targets": ["unity", "web"],
        # Up-axis fix (XYZ euler degrees), applied in the clean step so every
        # target/viewer is identically oriented. Canonical Y-up; SfM has no
        # gravity reference, so dial this in once in SuperSplat (e.g. "180,0,0")
        # and lock it here. null = no rotation.
        "rotate": None,
        "filter_floaters": True,
        "min_opacity": None,
        "spz_version": 4,
        "web_format": "sog",  # sog | compressed-ply
        "with_viewer": True,
    },
}


def _skeleton(graphics_root: str, scratch_root: str) -> dict:
    """A full profile dict for the given bases — derived roots + tuning (deep
    copies, so callers never share nested state)."""
    prof = {"graphics_root": graphics_root, "scratch_root": scratch_root}
    prof.update(_DERIVED_ROOTS)
    # deepcopy (not dict(v)): tuning blocks now nest dicts/lists (presets,
    # publish.targets), so a shallow copy would share that nested state across
    # every profile instance.
    prof.update({k: copy.deepcopy(v) for k, v in _TUNING.items()})
    # Reconstruction quality preset, mapped per-engine by the runners:
    # draft (fast preview) / balanced (default) / max (highest quality).
    prof["quality"] = "balanced"
    return prof


# Copy-me template written by :func:`init_user_profile`. Friendly ``~`` /
# ``${TEMP}`` tokens + a schema note in ``_comment`` (deep-merge ignores unknown
# keys downstream). Replaces a committed ``*.example.json`` so the repo carries
# no profile artifact at all.
EXAMPLE_PROFILE = {
    "_comment": (
        "Photogrammetry profile. Only keys you change are needed - the rest fall "
        "back to packaged defaults (deep-merge). '~' and '${ENV}' are expanded; "
        "'{graphics_root}'/'{scratch_root}' interpolate into the derived *_root "
        "values. Keep multi-GB live project I/O (scratch_root) on a real local "
        "disk, NOT inside a cloud-sync folder. To use a network / non-standard "
        "engine install, set the matching path under 'apps' (e.g. apps."
        "metashape_exe); empty = auto-discover."
    ),
    **_skeleton("~/photogrammetry", "${TEMP}/photogrammetry"),
}


def _packaged_default() -> dict:
    """Generic, non-personal fallback profile.

    Lands under the user's own config dir + system temp so a clone with no
    profile still runs without touching any specific machine's drives.
    """
    base = str(user_config_root() / PROFILE_PACKAGE / "photogrammetry")
    scratch = os.path.join(tempfile.gettempdir(), "photogrammetry")
    return _skeleton(base, scratch)


def _interpolate_roots(cfg: dict) -> dict:
    """Expand ``~``/``${ENV}`` and the ``{graphics_root}`` / ``{scratch_root}``
    tokens in the derived root values. Returns a new dict (input untouched)."""
    out = dict(cfg)
    graphics = UserConfig.expand(str(out.get("graphics_root", "")))
    scratch = UserConfig.expand(str(out.get("scratch_root", "")))
    out["graphics_root"] = graphics
    out["scratch_root"] = scratch
    tokens = {"graphics_root": graphics, "scratch_root": scratch}
    for key in _DERIVED_ROOT_KEYS:
        val = out.get(key)
        if isinstance(val, str):
            for tk, tv in tokens.items():
                val = val.replace("{" + tk + "}", tv)
            out[key] = UserConfig.expand(val)
    return out


def get_profile(path=None) -> dict:
    """Resolve the active photogrammetry profile (fully interpolated).

    Discovery (via :meth:`pythontk.UserConfig.resolve`): explicit *path* →
    ``$PHOTOGRAMMETRY_PROFILE`` → ``<user-config>/uitk/extapps/photogrammetry.json``
    → packaged default; deep-merged so a partial user profile only overrides
    what it names.
    """
    cfg = UserConfig.resolve(
        PROFILE_NAME,
        package=PROFILE_PACKAGE,
        env=PROFILE_ENV,
        default=_packaged_default(),
        path=path,
    )
    return _interpolate_roots(cfg)


def configured_app_path(key: str, path=None) -> Optional[str]:
    """Return the profile-configured install path for an engine, or ``None``.

    Reads ``apps.<key>`` from the active profile (resolved like
    :func:`get_profile`; pass *path* to read a specific profile) and expands
    ``~`` / ``${ENV}``. This is the **network-install** hook: a user sets e.g.
    ``apps.metashape_exe`` to a UNC path and every front-end (the panel's
    availability check + the headless runners) finds it. Each engine's discovery
    consults this after its env var and before standard discovery, and validates
    existence itself (an exe is a file; ``sugar_dir`` is a dir holding
    ``train_full_pipeline.py``), so an unset / offline path simply falls through.

    Robust by design: a malformed / unreadable profile returns ``None`` (the
    caller falls through to standard discovery) rather than breaking app
    discovery — the availability check must never crash on a bad profile.
    """
    try:
        val = get_profile(path).get("apps", {}).get(key)
    except Exception:  # noqa: BLE001 - bad profile must not break discovery
        return None
    return UserConfig.expand(str(val)) if val else None


def preset_store(engine: str) -> PresetStore:
    """The run-template store for *engine*: shipped built-ins (``presets/<engine>/``)
    layered under a writable user tier at
    ``<user_config_root>/extapps/photogrammetry_presets/<engine>/``.

    Presets are **engine-scoped** — a Metashape tuning preset (align/depth
    downscale, matchPhotos limits, depth filter, ...) means nothing to RealityScan
    and vice-versa — so each engine keeps its own presets and nothing is shared
    (duplicate a template per engine to use it on both). The same per-engine store
    backs that engine's headless runner and (for Metashape) the UI panel, so a
    user-saved preset is reachable both ways yet never leaks into another engine's
    list. *engine* is the short id: ``"metashape"`` / ``"realityscan"`` /
    ``"gaussian_splat"`` / ``"sugar"``.
    """
    return PresetStore(
        f"{PRESETS_NAME}/{engine}",
        PROFILE_PACKAGE,
        builtin_dir=os.path.join(PRESETS_DIR, engine),
    )


def get_preset(name: Optional[str], engine: str) -> dict:
    """Return the named opt-in run-template overlay for *engine* (``_comment`` stripped).

    Resolves via :func:`preset_store` (user tier shadows the built-in of the same
    name). A runner pre-parses ``--preset`` and lays the returned knobs over its
    argparse defaults so explicit CLI flags still win; an absent / ``"none"`` /
    ``"default"`` preset is a no-op (``{}``). Each runner applies only the keys it
    understands. Unknown *name* raises ``ValueError`` (a typo shouldn't silently
    run with plain defaults).
    """
    if not name or str(name).lower() in ("none", "default"):
        return {}
    store = preset_store(engine)
    try:
        data = store.load(name)
    except KeyError:
        raise ValueError(
            f"unknown preset {name!r} for {engine!r}; "
            f"available: {store.list() or '(none)'}"
        )
    return {k: v for k, v in data.items() if not str(k).startswith("_")}


def init_user_profile(path: Optional[str] = None, force: bool = False) -> str:
    """Write :data:`EXAMPLE_PROFILE` to the user-config location (or *path*).

    The repo ships **no** profile file; this scaffolds an editable one on demand
    at ``<user-config>/uitk/extapps/photogrammetry.json`` (or *path*). Existing
    files are left intact unless *force*. Returns the path.
    """
    target = path or str(UserConfig.path_for(PROFILE_NAME, PROFILE_PACKAGE))
    if os.path.exists(target) and not force:
        return target
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(EXAMPLE_PROFILE, fh, indent=4)
    return target


def discover_source_dirs(input_root: str) -> List[str]:
    """Return immediate subdirs of ``input_root`` that contain images."""
    if not os.path.isdir(input_root):
        raise ValueError(f"input-root does not exist: {input_root}")
    results: List[str] = []
    for name in sorted(os.listdir(input_root)):
        full = os.path.join(input_root, name)
        if not os.path.isdir(full):
            continue
        if any(f.lower().endswith(IMAGE_EXTS) for f in os.listdir(full)):
            results.append(full)
    return results
