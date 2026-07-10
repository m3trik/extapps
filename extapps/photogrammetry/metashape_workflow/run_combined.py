#!/usr/bin/python
# coding=utf-8
"""Driver script for multi-session combined runs.

Usage::

    python -m extapps.photogrammetry.metashape_workflow.run_combined --name my_project
    # ...or with an explicit profile:
    python -m extapps.photogrammetry.metashape_workflow.run_combined --profile /path/to/photogrammetry.json

Roots and prep defaults come from the photogrammetry **profile** (see
:mod:`extapps.photogrammetry.profile`): explicit ``--profile`` →
``$PHOTOGRAMMETRY_PROFILE`` → ``<user-config>/uitk/extapps/photogrammetry.json``
→ packaged default. Any CLI flag overrides the profile value.

Discovers immediate subdirectories of ``input-root`` as source captures,
equalizes exposures across them, then runs the full Phase 1+2+3 pipeline into
``output-root/<name>/``. Falls back to mock mode when the Metashape SDK isn't
importable so the plumbing exercises end-to-end on any environment.

``--preset NAME`` lays an opt-in run template (profile ``presets``) over the
align/depth/filter/masking defaults for difficult captures; see
``photogrammetry/TUNING.md``.
"""
from __future__ import annotations

import argparse
import os
import sys

if __package__ in (None, ""):
    # Executed directly as a top-level script — e.g. ``metashape.exe -r
    # run_combined.py`` inside Metashape's bundled Python (how MetashapeConnection
    # drives it headless). There is no package context, so package-relative
    # imports raise ImportError; put the package roots on sys.path and use
    # absolute imports instead. Under ``python -m`` __package__ is set, so the
    # else branch (normal relative imports) runs.
    # __file__ = <repo>/extapps/extapps/photogrammetry/metashape_workflow/run_combined.py
    # 4 dirnames up = <repo>/extapps (the dir holding the importable ``extapps``).
    _pkg_parent = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    )
    if _pkg_parent not in sys.path:
        sys.path.insert(0, _pkg_parent)
    _sibling_pythontk = os.path.join(os.path.dirname(_pkg_parent), "pythontk")
    if os.path.isdir(_sibling_pythontk) and _sibling_pythontk not in sys.path:
        sys.path.insert(0, _sibling_pythontk)
    from extapps.photogrammetry.metashape_workflow._metashape_workflow import (
        MetashapeWorkflow,
    )
    from extapps.photogrammetry.profile import (
        IMAGE_EXTS,
        QUALITY_TIERS,
        discover_source_dirs,
        get_preset,
        get_profile,
        init_user_profile,
    )
    from extapps.photogrammetry.prep_stages import (
        derive_texture_size,
        extract_videos_to_dir,
        first_image_in_dirs,
    )
else:
    from ._metashape_workflow import MetashapeWorkflow
    from ..profile import (
        IMAGE_EXTS,
        QUALITY_TIERS,
        discover_source_dirs,
        get_preset,
        get_profile,
        init_user_profile,
    )
    from ..prep_stages import (
        derive_texture_size,
        extract_videos_to_dir,
        first_image_in_dirs,
    )


def _stop_after(label, mp) -> int:
    """Finish an ``--stop-after`` run: emit the QC sidecar + processing-report
    PDF and finalize. The project is persisted only when ``--save-project`` was
    given — the "no .psx unless asked" contract holds for stop-after runs too
    (and a late first save is the documented empty-``.files`` trap)."""
    if mp.save_project_enabled:
        mp.save_project()
    else:
        print("(no .psx kept - pass --save-project to keep a reopenable project)")
    mp.export_qc()  # Metashape report PDF: sparse cloud, cameras, overlap, reproj.
    sidecar = mp.finalize_run(success=True)
    print(f"\nStopped after '{label}' (--stop-after). QC sidecar: {sidecar}")
    return 0


def main(argv=None) -> int:
    # Windows consoles default to cp1252; pipeline status lines and paths
    # may contain non-ASCII. Force UTF-8 so a stray char never aborts a run.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
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
                     help="Reconstruction quality preset (profile default if "
                          "omitted): draft (fast) / balanced / max (highest). Sets "
                          "align+depth downscale and mesh density; explicit "
                          "--align-downscale / --depth-downscale / --face-count win.")
    pre.add_argument("--preset", default=None,
                     help="Opt-in run template from the profile's 'presets' (e.g. "
                          "specular_metal). Lays a difficult environment's tuned "
                          "knobs (align/depth downscale, depth filter, face count, "
                          "masking) over the defaults; explicit flags still win. "
                          "Omit for plain defaults. See TUNING.md.")
    preargs, _ = pre.parse_known_args(argv)
    if preargs.init_profile:
        ready = init_user_profile(preargs.profile)
        print(f"Profile ready at: {ready}  (edit it, or point --profile / "
              "$PHOTOGRAMMETRY_PROFILE elsewhere; existing files are left intact)")
        return 0
    prof = get_profile(preargs.profile)
    cur = prof.get("curate", {})
    eq = prof.get("equalize", {})
    rec = prof.get("reconstruct", {})
    try:
        preset = get_preset(preargs.preset, "metashape")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if preset:
        print(f"[preset] '{preargs.preset}' applied over defaults "
              f"(explicit flags still override).")
    # Quality preset -> per-engine knobs (1 = highest-res align/depth; HighFaceCount).
    # A --preset may override any of these specific knobs (it wins over --quality's
    # derived value but loses to an explicit per-knob flag).
    quality = preargs.quality or preset.get("quality") or prof.get("quality", "balanced")
    if quality not in QUALITY_TIERS:
        # argparse validates only CLI-passed values — a typo'd quality in a
        # preset/profile would otherwise KeyError.
        print(f"error: unknown quality {quality!r} (from preset/profile); "
              f"expected one of {list(QUALITY_TIERS)}.", file=sys.stderr)
        return 2
    _tier_knobs = {
        "draft":    {"align": 4, "depth": 4, "faces": "low"},
        "balanced": {"align": 2, "depth": 2, "faces": "medium"},
        "max":      {"align": 1, "depth": 1, "faces": "high"},
    }
    qp = _tier_knobs[quality]
    qp = {
        "align": preset.get("align_downscale", qp["align"]),
        "depth": preset.get("depth_downscale", qp["depth"]),
        "faces": preset.get("face_count", qp["faces"]),
    }

    p = argparse.ArgumentParser(description=__doc__, parents=[pre])
    p.add_argument("--input-root", default=prof["input_root"])
    p.add_argument("--frames-dir", default=None,
                   help="A single, already-prepared capture directory (images/). "
                        "When given, it is used as the sole source and "
                        "--input-root subdir discovery is skipped — the "
                        "single-capture counterpart to --input-root (the UI panel "
                        "passes this; multi-session CLI runs use --input-root).")
    p.add_argument("--video", nargs="+", default=None, metavar="VIDEO",
                   help="One or more video files to extract source frames from "
                        "(sharpest-per-second) into a single frames dir, which is "
                        "then used as the sole source. The video counterpart to "
                        "--frames-dir (mutually exclusive with it). Requires "
                        "OpenCV in the running interpreter — absent in Metashape's "
                        "bundled Python, so use the UI panel (it extracts first) "
                        "or run this under a normal Python; otherwise pre-extract "
                        "and pass --frames-dir.")
    p.add_argument("--output-root", default=prof["metashape_output_root"])
    p.add_argument("--name", default="combined", help="Project basename.")
    # Panel-saved presets snapshot every widget, including the stage toggles —
    # honor them here so a preset replayed via --preset reproduces the panel
    # run (preprocess_input=False is the panel's master off-switch: it skips
    # both prep stages wholesale).
    _preset_prep_off = not preset.get("preprocess_input", True)
    p.add_argument("--skip-curate", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("skip_curate", False)
                                or _preset_prep_off),
                   help="Skip pre-Metashape dHash + sharpness curation.")
    p.add_argument("--curate-preview", action="store_true",
                   help="Dry-run: report curation survivor counts per dHash "
                        "threshold + the sharpness distribution, then exit (no "
                        "reconstruction). Use to tune --curate-hash-threshold on "
                        "a real set before a long run.")
    p.add_argument("--skip-equalize", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("skip_equalize", False)
                                or _preset_prep_off),
                   help="Skip cross-session exposure equalization.")
    p.add_argument("--dedupe-cameras", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("dedupe_cameras", False)),
                   help="Disable near-duplicate camera poses after alignment "
                        "(keeps the sharper of each pair). OPT-IN: the distance "
                        "threshold is in arbitrary chunk units, so the cull is "
                        "scale-dependent and varies run to run - and disabled "
                        "cameras are excluded from depth mapping, not just "
                        "texturing. Enable only on captures with genuinely "
                        "redundant static footage.")
    p.add_argument("--skip-refine", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("skip_refine", False)),
                   help="Skip gradual-selection alignment refinement. Refinement "
                        "is self-guarded (won't decimate sparse clouds), but this "
                        "lets you bypass it entirely.")
    p.add_argument("--stop-after", choices=("align", "refine"), default=None,
                   help="Stop after the named stage instead of running the full "
                        "depth/mesh/texture pipeline, then write the QC sidecar + "
                        "Metashape processing-report PDF (sparse cloud, camera "
                        "coverage, image-overlap, reprojection stats) and exit. "
                        "Use to A/B input-prep cheaply: alignment is where input "
                        "quality shows up, and an align-only run is minutes vs the "
                        "multi-hour full bake. 'align' = before refinement; "
                        "'refine' = after.")
    p.add_argument("--use-masks", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("mask_background", False)),
                   help="Mask the background before alignment — Metashape "
                        "2.2's native AI masking when available, else rembg + "
                        "generateMasks (needs rembg installed) — and apply the "
                        "masks at feature matching (filter_mask) so background "
                        "features can't drive the solve. A --preset with "
                        "mask_background set turns this on by default; "
                        "--no-use-masks overrides it back off.")
    p.add_argument("--curate-hash-threshold", type=int,
                   default=preset.get("curate_hash_threshold",
                                      cur.get("hash_threshold", 0)),
                   help="dHash Hamming distance for content-dedup clustering. "
                        "Default 0 = no dedup (blur culling still applies) - the "
                        "right default for the primary ingest path (continuous "
                        "video / single-pass captures), where near-identical "
                        "frames carry exactly the small-baseline overlap SfM "
                        "triangulates from. 5 = near-identical only; raise past "
                        "that only for redundant static photo sets, and check "
                        "the QC over-curation warning.")
    p.add_argument("--curate-sharpness-floor", type=float,
                   default=cur.get("sharpness_floor", 0.0),
                   help="Reject any frame whose Laplacian variance is below this "
                        "absolute floor (scene-dependent; prefer the percentile).")
    p.add_argument("--curate-sharpness-percentile", type=float,
                   default=preset.get("curate_sharpness_percentile",
                                      cur.get("sharpness_percentile", 0.0)),
                   help="Relative blur cutoff: drop frames below this percentile "
                        "of the set's own sharpness distribution. Default 0 = "
                        "off - a percentile cut ALWAYS removes that share of the "
                        "set, even when every frame is sharp (video frames are "
                        "already sharpest-per-window at extraction); the "
                        "median-fraction guard below handles genuinely defocused "
                        "frames. Kept identical to the RC runner so both engines "
                        "receive the same prepped input.")
    p.add_argument("--curate-min-sharpness-frac", type=float,
                   default=preset.get("curate_min_sharpness_frac",
                                      cur.get("min_sharpness_fraction_of_median", 0.15)),
                   help="Median-relative blur guard: also drop frames below this "
                        "fraction of the survivor-median sharpness. Catches "
                        "catastrophically defocused frames the percentile misses. "
                        "Set 0 to disable.")
    p.add_argument("--keep-per-cluster", type=int,
                   default=preset.get("keep_per_cluster",
                                      cur.get("keep_per_cluster", 1)),
                   help="Keep top-K sharpest per dHash cluster.")
    p.add_argument("--equalize-strength", type=float,
                   default=preset.get("equalize_strength", eq.get("strength", 0.5)),
                   help="Exposure-match blend 0–1. <1 preserves each frame's "
                        "local contrast. 1.0 = full Reinhard match.")
    p.add_argument("--equalize-reference", choices=("first", "median", "global"),
                   default=preset.get("equalize_reference", eq.get("reference", "median")),
                   help="Target distribution for equalization. 'median' avoids "
                        "letting the first capture's color cast dominate.")
    _gate_default = preset.get("gate_mode", "warn")
    if _gate_default not in ("warn", "halt"):
        # argparse validates only CLI-passed values, not defaults. Fail fast
        # (like quality) instead of silently coercing to "warn" — a preset
        # that meant "halt" must not lose its hard stop to a typo.
        print(f"error: unknown gate_mode {_gate_default!r} (from preset); "
              f"expected warn/halt.", file=sys.stderr)
        return 2
    p.add_argument("--gate-mode", choices=("warn", "halt"),
                   default=_gate_default)
    p.add_argument("--save-project", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("save_project", False)),
                   help="Save a reopenable Metashape project (.psx + full .files: "
                        "sparse cloud, depth maps, model, texture) so a later run "
                        "can reopen it and re-run only the stages you want (e.g. "
                        "re-texture) without redoing alignment/depth. Default off "
                        "(deliverables only — OBJ/texture/report/QC, no .psx). The "
                        "path is established at chunk creation so the dense data "
                        "actually persists.")
    p.add_argument("--align-downscale", type=int, default=qp["align"],
                   help="Match-photos downscale (1 = full res / highest quality). "
                        "Preset-derived from --quality.")
    p.add_argument("--depth-downscale", type=int, default=qp["depth"],
                   help="Depth-map downscale (1 = Ultra). Preset-derived from --quality.")
    p.add_argument("--face-count", choices=("low", "medium", "high"),
                   default=qp["faces"],
                   help="Mesh density (Metashape FaceCount). Preset-derived from --quality.")
    p.add_argument("--depth-filter",
                   choices=("mild", "moderate", "aggressive", "none"),
                   default=preset.get("depth_filter", "mild"),
                   help="Depth-map filtering aggressiveness (Metashape FilterMode). "
                        "Default 'mild' (highest detail) reproduces per-pixel depth "
                        "noise into the mesh on specular/low-texture surfaces (e.g. "
                        "reflective metal); raise to 'moderate' to denoise the "
                        "geometry while keeping full-res depth. Independent of --quality.")
    p.add_argument(
        "--texture-size", default=preset.get("texture_size", "auto"),
        help="Texture page resolution. 'auto' (default) derives it from the "
             "source frames' long edge — next power-of-two, capped at 8192 "
             "(4532px→8192, 3840→4096, 1920→2048); multi-view bake holds ~source "
             "detail so this avoids upscaling noise. Pass an int to force a size.",
    )
    p.add_argument("--triage-quality", type=float,
                   default=preset.get("triage_quality", 0.0),
                   help="Disable cameras below this Metashape Image/quality score "
                        "(analyzeImages) before alignment - a strong cull for "
                        "genuinely messy input (0.5 is the usual value). OPT-IN "
                        "(default 0 = off): Image/quality correlates with "
                        "texture, so on low-texture / specular subjects it "
                        "disables good frames wholesale, and it stacks on top of "
                        "the curation stage's blur culling.")
    p.add_argument("--generic-preselection", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("generic_preselection", True)),
                   help="Fast low-res pairwise image preselection before "
                        "matching (Metashape's own default). The key lever to "
                        "fully align featureless / specular captures, where "
                        "reference preselection has no camera coords to work "
                        "from. On by default; --no-generic-preselection turns it "
                        "off for well-textured, geo-referenced sets.")
    p.add_argument("--keypoint-limit", type=int,
                   default=preset.get("keypoint_limit", 60000),
                   help="matchPhotos keypoint limit (features detected per "
                        "photo). Default 60000 - the verified robust-alignment "
                        "value (TUNING.md); Metashape's stock 40000 under-aligns "
                        "low-texture / specular surfaces.")
    p.add_argument("--tiepoint-limit", type=int,
                   default=preset.get("tiepoint_limit", 10000),
                   help="matchPhotos tiepoint limit (tie points kept per photo; "
                        "0 = unlimited). Higher = denser cloud + more robust "
                        "alignment on hard sets.")
    p.add_argument("--clean-min-component", type=int,
                   default=preset.get("min_component_size",
                                      rec.get("min_component_size", 100)),
                   help="Delete disconnected mesh islands smaller than N faces "
                        "(removeComponents) - the main lever against floater "
                        "'snow'. 0 disables. On specular / low-texture metal do "
                        "NOT crank this (strips real detail without fixing depth "
                        "noise). Default from the profile's "
                        "reconstruct.min_component_size (or --preset). Parity "
                        "with the RC runner's flag of the same name.")
    p.add_argument("--smooth-strength", type=int,
                   default=preset.get("smooth_strength", 0),
                   help="Laplacian mesh-smoothing passes after cleanup (0 = "
                        "none). A light value (1) denoises specular geometry; "
                        "high values melt real detail.")
    p.add_argument("--close-holes", type=int,
                   default=preset.get("close_holes", 30),
                   help="Close mesh holes up to this percent of the total mesh "
                        "size (closeHoles). 0 disables.")
    p.add_argument("--calibrate-colors", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("calibrate_colors", False)),
                   help="Run Metashape's calibrateColors (incl. white balance) "
                        "before texturing. OPT-IN: with cross-capture exposure "
                        "equalization already applied to the source frames, this "
                        "stacks a second color transform into the deliverable "
                        "albedo. Enable for mixed-lighting captures that skip "
                        "equalization.")
    p.add_argument("--video-window-sec", type=float,
                   # Preset-controllable (TUNING.md lists it; panel-saved
                   # presets snapshot the widget) — a replayed preset must
                   # extract at its saved window, not silently at 1.0.
                   default=float(preset.get("video_window_sec", 1.0)),
                   help="With --video: extraction window in seconds - one "
                        "sharpest frame is kept per window. 1.0 (~1 fps) suits a "
                        "slow orbit; lower it (0.25-0.5) for fast handheld moves "
                        "so small-baseline overlap isn't starved. Default from "
                        "--preset when it carries video_window_sec.")
    p.add_argument(
        "--export-colmap", nargs="?", const="__AUTO__", default=None,
        help="Also export a COLMAP dataset (images/ + sparse/0/) for the "
             "gaussian-splat track (Brush / SuGaR). With no value, writes to "
             "<gsplat_scratch_root>/<name>_colmap. Exported right after "
             "alignment, before the long mesh stages.",
    )
    p.add_argument(
        "--colmap-max-cameras", type=int,
        default=prof.get("gsplat", {}).get("colmap_max_cameras", 0),
        help="Cap COLMAP-exported cameras to ~N (even stride). 0 = all aligned. "
             "The splat trainers (esp. SuGaR's vanilla-3DGS on an 8 GB GPU) bog "
             "down badly past a few hundred views; 300-400 is a sane cap.",
    )
    args = p.parse_args(argv)

    if args.video and args.frames_dir:
        print("error: --video and --frames-dir are mutually exclusive "
              "(both name the single source capture).", file=sys.stderr)
        return 2
    if args.video:
        # Video source(s): extract frames into one dir under the project, then
        # treat that dir as the single prepared capture.
        frames_dir = os.path.join(args.output_root, args.name, "_extracted_frames")
        print(f"Extracting frames from {len(args.video)} video(s) -> {frames_dir}")
        frames = extract_videos_to_dir(
            args.video, frames_dir, window_sec=args.video_window_sec, log=print
        )
        if not frames:
            print("error: no frames extracted - OpenCV is unavailable in this "
                  "interpreter (Metashape's bundled Python has no cv2) or the "
                  "videos were unreadable. Pre-extract frames and pass "
                  "--frames-dir, or run under a Python with opencv installed.",
                  file=sys.stderr)
            return 1
        sources = [frames_dir]
    elif args.frames_dir:
        # Single prepared capture: use it directly, skip subdir discovery.
        if not os.path.isdir(args.frames_dir):
            print(f"--frames-dir does not exist: {args.frames_dir}", file=sys.stderr)
            return 1
        sources = [args.frames_dir]
    else:
        sources = discover_source_dirs(args.input_root)
        if not sources:
            print(f"No image-bearing subdirs under {args.input_root}", file=sys.stderr)
            return 1
    print(f"Discovered {len(sources)} source dir(s):")
    for s in sources:
        count = sum(1 for f in os.listdir(s) if f.lower().endswith(IMAGE_EXTS))
        print(f"  - {s}  ({count} images)")

    # Resolve texture size (curation/equalize preserve resolution, so derive
    # from the original frames now). cv2/PIL may be absent in Metashape's
    # bundled Python -> derive_texture_size falls back to 8192.
    if str(args.texture_size).lower() == "auto":
        sample = first_image_in_dirs(sources)
        texture_size = derive_texture_size(sample)
        print(f"Texture size: {texture_size} (auto, from {sample})")
    else:
        texture_size = int(args.texture_size)
        print(f"Texture size: {texture_size} (explicit)")

    project_dir = os.path.join(args.output_root, args.name)
    os.makedirs(project_dir, exist_ok=True)

    mp = MetashapeWorkflow(
        project_path=project_dir,
        name=args.name,
        gate_mode=args.gate_mode,
        # Checkpointing only persists a useful project when we're keeping one;
        # both are driven by --save-project (default off = no .psx at all).
        checkpoint_each_stage=args.save_project,
        save_project=args.save_project,
    )
    print(mp.get_license_info())
    if mp.mock_mode:
        print(
            "Running in MOCK MODE - Metashape SDK not importable. "
            "QC sidecar will still be written; no mesh produced."
        )

    if args.curate_preview:
        mp.preview_curation(
            sources,
            # Sweep the standard thresholds plus the user's own value (and 0,
            # the no-dedup baseline) so the preview answers the question they
            # are actually tuning.
            hash_thresholds=sorted({0, 5, 8, 10, 12, 15,
                                    args.curate_hash_threshold}),
            sharpness_floor_percentile=(
                args.curate_sharpness_percentile
                if args.curate_sharpness_percentile > 0 else None
            ),
            min_sharpness_fraction_of_median=args.curate_min_sharpness_frac,
            keep_per_cluster=args.keep_per_cluster,
        )
        mp.finalize_run(success=True)  # flush the preview stage to the sidecar
        return 0

    try:
        mp.create_chunk(f"{args.name} (combined)")

        if not args.skip_curate:
            sources = mp.curate_input_set(
                sources,
                hash_threshold=args.curate_hash_threshold,
                sharpness_floor=args.curate_sharpness_floor,
                sharpness_floor_percentile=(
                    args.curate_sharpness_percentile
                    if args.curate_sharpness_percentile > 0 else None
                ),
                min_sharpness_fraction_of_median=args.curate_min_sharpness_frac,
                keep_per_cluster=args.keep_per_cluster,
            )

        if not args.skip_equalize and len(sources) > 1:
            sources = mp.equalize_exposures(
                sources,
                strength=args.equalize_strength,
                reference_strategy=args.equalize_reference,
            )
        elif not args.skip_equalize:
            print(
                "[equalize] skipped: single capture - cross-set exposure matching "
                "needs >=2 captures; re-encoding a lone set only risks SfM feature "
                "quality for no benefit (Metashape calibrates color internally)."
            )

        mp.add_image_dirs(sources)

        if args.use_masks:
            # Primary: Metashape 2.2+'s built-in AI background masking — runs
            # inside the SDK, so it works in the production headless context
            # (metashape.exe -r has no rembg/PIL/cv2). Fallback for older
            # SDKs: rembg file masks per source (needs rembg importable) —
            # each source gets its own index-prefixed subdir so same-basename
            # captures can't clobber each other, then a file import per dir.
            if not mp.generate_masks_native():
                masks_root = os.path.join(project_dir, "masks")
                for i, src in enumerate(sources):
                    per_src = os.path.join(
                        masks_root,
                        f"{i:02d}_{os.path.basename(os.path.normpath(src))}",
                    )
                    out = mp.generate_masks(source_dir=src, masks_dir=per_src)
                    if out:
                        mp.import_masks(out)

        if args.triage_quality > 0:
            mp.triage_images(quality_threshold=args.triage_quality)
        else:
            print("[triage] skipped (--triage-quality 0): all cameras kept.")
        def _maybe_export_colmap() -> None:
            # COLMAP export for the splat track — right after align/refine
            # (poses are finalized; the mesh stages don't affect cameras), so
            # the dataset is ready before the multi-hour depth/model work AND
            # on --stop-after runs (align-only + splat dataset is the natural
            # cheap invocation; it used to exit without exporting).
            if args.export_colmap is None:
                return
            colmap_dir = (
                args.export_colmap
                if args.export_colmap != "__AUTO__"
                else os.path.join(prof["gsplat_scratch_root"], f"{args.name}_colmap")
            )
            mp.export_colmap(colmap_dir, max_cameras=args.colmap_max_cameras)

        mp.align_photos_with_retry(
            downscale=args.align_downscale,
            generic_preselection=args.generic_preselection,
            keypoint_limit=args.keypoint_limit,
            tiepoint_limit=args.tiepoint_limit,
            min_aligned_pct=50.0,
            # Masks must also gate feature *matching*, or background features
            # still drive the solve and the masks only affect depth maps.
            filter_mask=args.use_masks,
        )
        if args.stop_after == "align":
            _maybe_export_colmap()
            return _stop_after("align", mp)
        if not args.skip_refine:
            mp.refine_alignment()
        _maybe_export_colmap()
        if args.stop_after == "refine":
            return _stop_after("refine", mp)

        if args.dedupe_cameras:
            mp.dedupe_cameras_by_pose()
        else:
            print("[dedupe] skipped (opt-in: --dedupe-cameras).")

        if args.calibrate_colors:
            mp.calibrate_colors()
        else:
            print("[calibrate-colors] skipped (opt-in: --calibrate-colors).")
        mp.generate_depth_maps(
            downscale=args.depth_downscale, filter_mode=args.depth_filter
        )
        mp.build_model(face_count=args.face_count)
        mp.clean_mesh(
            remove_components_face_threshold=args.clean_min_component,
            close_holes_level=args.close_holes,
            smooth_strength=args.smooth_strength,
        )
        mp.build_texture(texture_size=texture_size)
        if args.save_project:
            mp.save_project()  # final save of the reopenable project
        mp.export_model()
        mp.clean_mesh_advanced()  # PyMeshLab if installed
        mp.export_qc()
        sidecar = mp.finalize_run(success=True)
        print(f"\nDone. QC sidecar: {sidecar}")
        return 0
    except Exception as e:
        print(f"\nWorkflow failed: {e}", file=sys.stderr)
        mp.finalize_run(success=False)
        raise


if __name__ == "__main__":
    sys.exit(main())
