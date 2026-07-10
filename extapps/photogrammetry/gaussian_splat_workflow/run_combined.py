# !/usr/bin/python
# coding=utf-8
"""Driver for the gaussian-splat track: Brush splat training + engine publish.

Usage::

    # Brush splat only:
    python -m extapps.photogrammetry.gaussian_splat_workflow.run_combined \
        --colmap-dir <dataset_dir> --name my_splat
    # Brush splat + engine-ready delivery (Unity .spz + web viewer), then open it:
    python -m extapps.photogrammetry.gaussian_splat_workflow.run_combined \
        --colmap-dir <dataset_dir> --name my_splat --publish --preview
    # Publish an already-trained splat (no retrain):
    python -m extapps.photogrammetry.gaussian_splat_workflow.run_combined \
        --skip-brush --input-ply <trained.ply> --name my_splat --publish

Brush consumes a COLMAP dataset (``images/`` + ``sparse/0/``, typically from
Metashape's ``--export-colmap``) and trains a 3D Gaussian Splat → ``.ply``.
``--publish`` then cleans the splat (floater removal/crop — the top VRAM-free
quality lever) and converts it to engine formats (Unity ``.spz``; web
``.sog``/``.compressed.ply`` + a self-contained ``.html`` viewer) via
splat-transform (``npm i -g @playcanvas/splat-transform``).
Outputs go to a **local** scratch dir (the profile's ``scratch_root/gsplat_out``)
— the multi-hundred-MB checkpoints must not churn inside a cloud-sync folder;
copy finals to the synced comparison dir afterwards.

For a UV-textured **mesh** instead of a splat, the experimental SuGaR track is a
separate runner — see :mod:`extapps.photogrammetry.sugar_mesh_workflow.run_combined`.

Roots + tuning defaults come from the photogrammetry **profile** (see
:mod:`extapps.photogrammetry.profile`; override with ``--profile``).
"""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

from ._gaussian_splat_workflow import GaussianSplatWorkflow
from ._splat_publish import SplatPublishWorkflow
from ..profile import QUALITY_TIERS, get_preset, get_profile, init_user_profile


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
                     help="Quality preset (profile default if omitted) → Brush "
                          "total-steps: draft 7k / balanced 30k / max 50k. More "
                          "steps is a VRAM-free quality lever on an 8-10 GB card. "
                          "Explicit --total-steps wins.")
    pre.add_argument("--preset", default=None,
                     help="Opt-in run template from the shared preset store (e.g. "
                          "a splat-tuning template). Lays its knobs (total_steps, "
                          "max_resolution, max_splats, sh_degree) over the defaults; "
                          "explicit flags still win. See TUNING.md.")
    preargs, _ = pre.parse_known_args(argv)
    if preargs.init_profile:
        ready = init_user_profile(preargs.profile)
        print(f"Profile ready at: {ready}  (edit it, or point --profile / "
              "$PHOTOGRAMMETRY_PROFILE elsewhere; existing files are left intact)")
        return 0
    prof = get_profile(preargs.profile)
    gs_cfg = prof.get("gsplat", {})
    publish_cfg = prof.get("publish", {})
    try:
        preset = get_preset(preargs.preset, "gaussian_splat")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if preset:
        print(f"[preset] '{preargs.preset}' applied over defaults "
              f"(explicit flags still override).")
    # Quality preset -> Brush training steps. More steps costs time, not VRAM,
    # so 'max' trains longer (50k) for higher fidelity on a VRAM-capped GPU.
    # Precedence: explicit --total-steps > --preset total_steps > explicit
    # --quality tier > profile gsplat.total_steps > profile-quality tier.
    quality = preargs.quality or prof.get("quality", "balanced")
    if quality not in QUALITY_TIERS:
        # argparse validates only CLI-passed values — a typo'd profile quality
        # would otherwise KeyError.
        print(f"error: unknown quality {quality!r} (from profile); expected "
              f"one of {list(QUALITY_TIERS)}.", file=sys.stderr)
        return 2
    brush_steps = {"draft": 7000, "balanced": 30000, "max": 50000}[quality]
    if preargs.quality is None:
        # No explicit --quality: a USER-SET gsplat.total_steps wins over the
        # tier table. The packaged default ships None ("derive from tier") —
        # keying on mere presence made the profile-quality tier unreachable
        # (get_profile deep-merges the packaged block, so the key always
        # exists; a profile with only {"quality": "draft"} silently trained
        # the balanced 30k instead of 7k).
        profile_steps = gs_cfg.get("total_steps")
        if profile_steps is not None:
            brush_steps = int(profile_steps)
    brush_steps = preset.get("total_steps", brush_steps)

    p = argparse.ArgumentParser(description=__doc__, parents=[pre])
    p.add_argument("--colmap-dir", default=None,
                   help="COLMAP dataset dir (images/ + sparse/0/), e.g. from "
                        "Metashape's --export-colmap. Required for Brush; omit "
                        "only for a publish-only run (--skip-brush --input-ply).")
    p.add_argument("--output-root", default=prof["gsplat_scratch_root"],
                   help="Local scratch for the splat .ply (NOT a cloud-sync "
                        "folder). Publish the final splat to the cloud separately.")
    p.add_argument("--name", default="splat", help="Project / export basename.")
    p.add_argument("--total-steps", type=int, default=brush_steps,
                   help="Brush training steps (preset-derived from --quality).")
    p.add_argument("--max-resolution", type=int,
                   default=preset.get("max_resolution", gs_cfg.get("max_resolution", 1920)),
                   help="Input long-edge cap. 1920 — A/B showed no gain from "
                        "3840 at the gaussian budget an 8 GB GPU holds.")
    p.add_argument("--max-splats", type=int,
                   default=preset.get("max_splats", gs_cfg.get("max_splats", 10_000_000)),
                   help="Upper bound; brush's stock growth settles ~2.5-3M on "
                        "8 GB. Raising the growth aggressiveness OOM-crashed.")
    p.add_argument("--sh-degree", type=int,
                   default=preset.get("sh_degree", gs_cfg.get("sh_degree", 3)))
    p.add_argument("--growth-grad-threshold", type=float, default=None,
                   help="Advanced: lower = denser. Left at brush default; "
                        "lowering it OOM-crashed the 8 GB GPU in testing.")
    p.add_argument("--growth-select-fraction", type=float, default=None,
                   help="Advanced: higher = grow more aggressively (OOM risk).")
    p.add_argument("--eval-split-every", type=int, default=None,
                   help="Hold out every Nth view for eval PSNR (e.g. 20). "
                        "Omit for a production splat trained on all frames.")
    p.add_argument("--eval-every", type=int, default=None)
    p.add_argument("--eval-save-to-disk", action="store_true",
                   help="Save rendered held-out views to the export path.")
    p.add_argument("--brush-exe", default=None, help="Override Brush exe path.")
    p.add_argument("--skip-brush", action="store_true",
                   help="Skip Brush splat training (e.g. publish an existing .ply).")
    # --- Publish stage (engine delivery: clean + convert via splat-transform) ---
    p.add_argument("--publish", action="store_true",
                   help="After (optional) Brush, clean the splat and convert it to "
                        "engine formats (Unity .spz / web .sog+.html). Wraps "
                        "splat-transform (npm i -g @playcanvas/splat-transform).")
    p.add_argument("--input-ply", default=None,
                   help="Publish an existing splat .ply (pair with --skip-brush). "
                        "Defaults to the freshly trained Brush .ply when omitted.")
    p.add_argument("--publish-targets",
                   default=preset.get(
                       "publish_targets",
                       ",".join(publish_cfg.get("targets", ["unity", "web"]))),
                   help="Comma-separated engine targets: unity,web (default both).")
    p.add_argument("--rotate", default=publish_cfg.get("rotate"),
                   help="Fix the up-axis: XYZ euler degrees applied before crop so "
                        "every viewer/target is identically Y-up. SfM has no up, so "
                        "eyeball it in SuperSplat then set profile publish.rotate. "
                        "Use '=' for negative angles: --rotate=-90,0,0. "
                        "Common: 180,0,0 or 90,0,0.")
    p.add_argument("--filter-floaters", action=argparse.BooleanOptionalAction,
                   default=bool(publish_cfg.get("filter_floaters", True)),
                   help="Remove isolated 'floater' gaussians during cleanup - "
                        "the top VRAM-free quality lever for an env. On by "
                        "default; --no-filter-floaters keeps them (and, unlike "
                        "the old negative-only flag, --filter-floaters can "
                        "re-enable over a profile that turned it off).")
    p.add_argument("--min-opacity", type=float,
                   default=publish_cfg.get("min_opacity"),
                   help="Cull gaussians below this raw opacity (e.g. 0.1). Off by default.")
    p.add_argument("--crop-box", default=None,
                   help="Crop to a bounding box 'x,y,z,X,Y,Z' (bounds the environment). "
                        "Use the '=' form for negative bounds: --crop-box=-2,-2,-2,2,2,2 "
                        "(argparse treats a leading '-' as a flag otherwise).")
    p.add_argument("--crop-sphere", default=None,
                   help="Crop to a sphere 'x,y,z,radius'. Use '=' for negative "
                        "centers: --crop-sphere=-1,0,-1,3.")
    p.add_argument("--decimate", default=None,
                   help="Thin the splat to N gaussians or N%% (e.g. 2000000 or 50%%).")
    p.add_argument("--web-format", choices=("sog", "compressed-ply"),
                   default=(preset.get("web_format")
                            if preset.get("web_format") in ("sog", "compressed-ply")
                            else publish_cfg.get("web_format", "sog")),
                   help="Browser data format (default sog).")
    p.add_argument("--spz-version", type=int, choices=(3, 4),
                   default=(int(preset["spz_version"])
                            if str(preset.get("spz_version")) in ("3", "4")
                            else publish_cfg.get("spz_version", 4)),
                   help="SPZ format version for the Unity .spz (default 4).")
    p.add_argument("--viewer", dest="with_viewer",
                   action=argparse.BooleanOptionalAction,
                   default=bool(publish_cfg.get("with_viewer", True)),
                   help="Emit the self-contained .html web viewer (on by "
                        "default; --no-viewer skips it, --viewer re-enables "
                        "over a profile that turned it off).")
    p.add_argument("--preview", action="store_true",
                   help="After publishing, open the generated .html viewer in your "
                        "default browser (needs the 'web' target; skipped in --mock).")
    p.add_argument("--mock", action="store_true",
                   help="Force mock mode — no Brush/splat-transform subprocess; "
                        "validate plumbing.")
    args = p.parse_args(argv)

    if args.skip_brush and not args.publish:
        print("Nothing to do: --skip-brush given without --publish.",
              file=sys.stderr)
        return 1

    # COLMAP is consumed only by Brush; a publish-only run works off an existing
    # .ply and needs none.
    if not args.skip_brush and not args.colmap_dir:
        print("--colmap-dir is required for Brush training (omit only for a "
              "publish-only run: --skip-brush --input-ply ... --publish).",
              file=sys.stderr)
        return 1

    project_dir = os.path.join(args.output_root, args.name)
    ply = None
    published = None

    try:
        # --- Brush splat (handles the full camera set efficiently) ---
        if not args.skip_brush:
            gs = GaussianSplatWorkflow(
                project_path=project_dir,
                name=args.name,
                brush_exe=args.brush_exe,
                mock_mode=True if args.mock else None,
            )
            print(gs.get_brush_info())
            if gs.mock_mode:
                reason = "forced via --mock" if args.mock else "Brush not found"
                print(f"Brush MOCK MODE ({reason}). No splat produced.")
            try:
                ply = gs.train(
                    colmap_dir=args.colmap_dir,
                    total_steps=args.total_steps,
                    max_resolution=args.max_resolution,
                    max_splats=args.max_splats,
                    sh_degree=args.sh_degree,
                    growth_grad_threshold=args.growth_grad_threshold,
                    growth_select_fraction=args.growth_select_fraction,
                    export_path=project_dir,
                    export_name=f"{args.name}_{{iter}}.ply",
                    eval_split_every=args.eval_split_every,
                    eval_every=args.eval_every,
                    eval_save_to_disk=args.eval_save_to_disk,
                )
                if ply is None and not gs.mock_mode:
                    # Brush exited 0 but the expected .ply isn't on disk (e.g.
                    # export step-naming mismatch). Reporting success here made
                    # the run look healthy while delivering nothing.
                    gs.finalize_run(success=False)
                    print(
                        "error: Brush finished but the expected splat .ply was "
                        "not found - failing the run (a later --publish would "
                        "only mislead with '--publish needs a splat').",
                        file=sys.stderr,
                    )
                    return 1
                gs.finalize_run(success=True)
                print(f"Splat: {ply}")
            except Exception:
                gs.finalize_run(success=False)
                raise

        # --- Publish (engine delivery): clean + convert the splat for Unity/web ---
        if args.publish:
            publish_in = args.input_ply or ply
            if not publish_in:
                print("--publish needs a splat: run Brush, or pass --input-ply.",
                      file=sys.stderr)
                return 1
            targets = tuple(t.strip() for t in args.publish_targets.split(",")
                            if t.strip())
            sp = SplatPublishWorkflow(
                project_path=os.path.join(project_dir, "publish"),
                name=args.name,
                mock_mode=True if args.mock else None,
            )
            print(sp.get_publish_info())
            if sp.mock_mode:
                reason = "forced via --mock" if args.mock else "splat-transform not found"
                print(f"Publish MOCK MODE ({reason}). No engine assets produced.")
            try:
                published = sp.publish(
                    in_ply=publish_in,
                    targets=targets,
                    rotate=args.rotate,
                    filter_floaters=args.filter_floaters,
                    min_opacity=args.min_opacity,
                    crop_box=args.crop_box,
                    crop_sphere=args.crop_sphere,
                    decimate=args.decimate,
                    spz_version=args.spz_version,
                    web_format=args.web_format,
                    with_viewer=args.with_viewer,
                )
                sp.finalize_run(success=True)
                print(f"Published: {published}")
            except Exception:
                sp.finalize_run(success=False)
                raise

            if args.preview and not args.mock:
                web = published.get("web") if published else None
                viewer = web.get("viewer") if web else None
                if viewer and os.path.isfile(viewer):
                    uri = Path(viewer).resolve().as_uri()
                    print(f"Opening preview: {viewer}")
                    # Best-effort: a browser-open hiccup must never fail a run
                    # whose deliverables are already written.
                    try:
                        opened = webbrowser.open(uri)
                    except Exception as e:
                        print(f"  (preview open failed: {e})", file=sys.stderr)
                        opened = False
                    if not opened:
                        print(f"  Open it manually: {uri}", file=sys.stderr)
                else:
                    print("--preview: no .html viewer to open (enable the 'web' "
                          "target without --no-viewer).", file=sys.stderr)

        print(f"\nDone. Splat: {ply}  Published: {published}")
        return 0
    except Exception as e:
        print(f"\nWorkflow failed: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())
