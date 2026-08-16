# !/usr/bin/python
# coding=utf-8
"""Driver for the **EXPERIMENTAL** SuGaR mesh track: COLMAP dataset → textured ``.obj``.

Separate from the core gaussian-splat track (see
:mod:`extapps.photogrammetry.gaussian_splat_workflow.run_combined`, which trains a
Brush splat and publishes it to engine formats). This runs SuGaR's full pipeline to
extract a UV-textured mesh — a different, experimental deliverable.

Usage::

    python -m extapps.photogrammetry.sugar_mesh_workflow.run_combined \
        --colmap-dir <capped_dataset_dir> --name my_mesh --quality max

Consumes a COLMAP dataset (``images/`` + ``sparse/0/``, typically from Metashape's
``--export-colmap``). Outputs go to a **local** scratch dir (the profile's
``scratch_root/gsplat_out``) — copy finals to the synced comparison dir afterwards.

IMPORTANT: SuGaR's bundled vanilla-3DGS bogs to ~20 s/iter past a few hundred views
on an 8 GB GPU. Feed a **capped** COLMAP export (Metashape ``--colmap-max-cameras
300-400``) and keep the GPU free. (Brush, in the splat track, has no such limit.)
See :class:`._sugar_mesh.SugarMeshWorkflow`.

Roots + tuning defaults come from the photogrammetry **profile** (see
:mod:`extapps.photogrammetry.profile`; override with ``--profile``).
"""
from __future__ import annotations

import argparse
import os
import sys

from ._sugar_mesh import SugarMeshWorkflow
from ..profile import Profile, QUALITY_TIERS


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Pre-parse --profile so the active profile can supply argparse defaults;
    # explicit CLI flags below still override the profile values.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--profile", default=None,
                     help="Path to a photogrammetry profile JSON. Default: "
                          "$PHOTOGRAMMETRY_PROFILE / user-config / packaged.")
    pre.add_argument("--init-profile", action="store_true",
                     help="Write an editable example profile to the user-config "
                          "location (or --profile path) and exit.")
    pre.add_argument("--quality", choices=QUALITY_TIERS, default=None,
                     help="Quality preset (profile default if omitted): draft / "
                          "balanced / max → SuGaR refinement time short/medium/long; "
                          "explicit --sugar-refinement-time wins.")
    pre.add_argument("--preset", default=None,
                     help="Opt-in run template from the shared preset store. Lays "
                          "its SuGaR knobs (regularization, refinement_time, "
                          "surface_level, high_poly) over the defaults; explicit "
                          "flags still win. See TUNING.md.")
    preargs, _ = pre.parse_known_args(argv)
    if preargs.init_profile:
        ready = Profile.init_user_profile(preargs.profile)
        print(f"Profile ready at: {ready}  (edit it, or point --profile / "
              "$PHOTOGRAMMETRY_PROFILE elsewhere; existing files are left intact)")
        return 0
    prof = Profile.get_profile(preargs.profile)
    sugar_cfg = prof.get("sugar", {})
    try:
        preset = Profile.get_preset(preargs.preset, "sugar")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if preset:
        print(f"[preset] '{preargs.preset}' applied over defaults "
              f"(explicit flags still override).")
    # Quality preset -> SuGaR refinement time (short/medium/long = 2k/7k/15k iters).
    # A --preset's refinement_time overrides the quality-derived value.
    quality = preargs.quality or prof.get("quality", "balanced")
    if quality not in QUALITY_TIERS:
        # argparse validates only CLI-passed values — a typo'd profile quality
        # would otherwise KeyError.
        print(f"error: unknown quality {quality!r} (from profile); expected "
              f"one of {list(QUALITY_TIERS)}.", file=sys.stderr)
        return 2
    refinement_time = {"draft": "short", "balanced": "medium", "max": "long"}[quality]
    refinement_time = preset.get("refinement_time", refinement_time)

    p = argparse.ArgumentParser(description=__doc__, parents=[pre])
    p.add_argument("--colmap-dir", required=True,
                   help="COLMAP dataset dir (images/ + sparse/0/), e.g. from "
                        "Metashape's --export-colmap. Use a CAPPED export.")
    p.add_argument("--output-root", default=prof["gsplat_scratch_root"],
                   help="Local scratch for the run (NOT a cloud-sync folder). "
                        "Publish the final mesh to the cloud separately.")
    p.add_argument("--name", default="mesh", help="Project / output basename.")
    p.add_argument("--sugar-dir", default=None,
                   help="SuGaR repo dir (holds train_full_pipeline.py). "
                        "Default: the SUGAR_DIR env var.")
    p.add_argument("--sugar-regularization",
                   default=preset.get("regularization",
                                      sugar_cfg.get("regularization", "dn_consistency")),
                   choices=("sdf", "density", "dn_consistency"),
                   help="SuGaR coarse regularizer. dn_consistency = best mesh.")
    p.add_argument("--sugar-refinement-time", default=refinement_time,
                   choices=("short", "medium", "long"),
                   help="SuGaR refinement iters short/medium/long = 2k/7k/15k "
                        "(preset-derived from --quality).")
    p.add_argument("--sugar-surface-level", type=float,
                   default=preset.get("surface_level", sugar_cfg.get("surface_level", 0.3)),
                   help="Level set at which SuGaR extracts the mesh.")
    p.add_argument("--low-poly", dest="high_poly", action="store_false",
                   help="SuGaR low-poly mesh (200k verts) instead of high-poly (1M).")
    p.set_defaults(high_poly=preset.get("high_poly", sugar_cfg.get("high_poly", True)))
    p.add_argument("--gpu", type=int, default=0, help="GPU index for SuGaR.")
    p.add_argument("--mock", action="store_true",
                   help="Force mock mode — no SuGaR subprocess; validate plumbing.")
    args = p.parse_args(argv)

    project_dir = os.path.join(args.output_root, args.name)
    try:
        sm = SugarMeshWorkflow(
            project_path=project_dir,
            name=args.name,
            sugar_dir=args.sugar_dir,
            mock_mode=True if args.mock else None,
        )
        print(sm.get_sugar_info())
        if sm.mock_mode:
            reason = "forced via --mock" if args.mock else "SuGaR not found"
            print(f"SuGaR MOCK MODE ({reason}). No mesh produced.")
        try:
            mesh = sm.extract_mesh(
                colmap_dir=args.colmap_dir,
                regularization=args.sugar_regularization,
                high_poly=args.high_poly,
                refinement_time=args.sugar_refinement_time,
                surface_level=args.sugar_surface_level,
                gpu=args.gpu,
            )
            sm.finalize_run(success=True)
            print(f"Mesh: {mesh}")
        except Exception:
            sm.finalize_run(success=False)
            raise
        print(f"\nDone. Mesh: {mesh}")
        return 0
    except Exception as e:
        print(f"\nWorkflow failed: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())
