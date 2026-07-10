# !/usr/bin/python
# coding=utf-8
"""Driver script for multi-session combined RealityCapture runs.

Usage::

    python -m extapps.photogrammetry.realityscan_workflow.run_combined --name my_project

Roots and prep defaults come from the photogrammetry **profile** (see
:mod:`extapps.photogrammetry.profile`; override with ``--profile``). ``--input-root``
defaults to the profile's input dir. ``--output-root`` defaults to the profile's
**local** scratch dir (``scratch_root/rc_out``): RealityScan's live multi-GB project
I/O must NOT run inside a cloud-sync folder, or the sync client and RC fight over the
files (placeholder/.new churn, "file not found" on save). Publish the finished export
to the synced comparison dir afterwards.

Discovers immediate subdirectories of ``--input-root`` as source captures,
optionally curates (dHash + sharpness) and equalizes exposures across them,
then runs the full RC pipeline into ``--output-root/<name>/``: align → model
at the ``--quality`` tier (draft/balanced/max → RC preview/normal/high) →
clean → simplify (to fit the UV budget) → unwrap + texture → export.

Mirrors :mod:`extapps.photogrammetry.metashape_workflow.run_combined` so the two engines
take identical CLI shape — easier to A/B compare.

``--preset NAME`` lays an opt-in run template (profile ``presets``) over the
defaults for difficult captures; see ``photogrammetry/TUNING.md`` for the templates
and the GUI-only levers RealityScan's CLI can't reach.
"""
from __future__ import annotations

import argparse
import os
import sys

if __package__ in (None, ""):
    # Executed directly as a top-level script (no package context) — package-
    # relative imports would ImportError. Put the package roots on sys.path and
    # use absolute imports. Mirrors metashape_workflow/run_combined.py; under
    # `python -m` (the normal entry) __package__ is set, so the else branch runs.
    # 4 dirnames up from this file = <repo>/extapps (holds the ``extapps`` pkg).
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
    from extapps.photogrammetry.realityscan_workflow._realityscan_workflow import (
        RealityCaptureWorkflow,
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
        first_image_in_dirs,
    )
else:
    from ._realityscan_workflow import RealityCaptureWorkflow
    from ..profile import (
        IMAGE_EXTS,
        QUALITY_TIERS,
        discover_source_dirs,
        get_preset,
        get_profile,
        init_user_profile,
    )
    from ..prep_stages import derive_texture_size, first_image_in_dirs


# Intermediate working dirs the prep stages write inside the project dir —
# multi-GB frame copies, not deliverables. Never published to the synced root.
_PUBLISH_EXCLUDE_DIRS = frozenset({"curated", "equalized", "logs", "masks"})


def publish_outputs(project_dir: str, publish_dir: str):
    """Copy finished deliverables from local scratch to the synced output root.

    RC must work in local scratch (cloud-sync fights its live multi-GB project
    I/O), so the static post-run deliverables are published separately. Copies
    everything in ``project_dir`` EXCEPT the ``.rsproj`` (RC working state, not
    a deliverable) and the prep-stage intermediates (``curated/`` /
    ``equalized/`` frame copies, ``masks/``, ``logs/`` — publishing those
    pushed multi-GB image trees into the cloud-sync root). Returns the item
    count copied, or ``None`` when the source and destination resolve to the
    same directory (nothing to do). Best-effort: a copy error is reported but
    doesn't fail the run (the scratch copy survives).
    """
    import shutil

    if os.path.abspath(project_dir) == os.path.abspath(publish_dir):
        return None
    try:
        os.makedirs(publish_dir, exist_ok=True)
        entries = sorted(os.listdir(project_dir))
    except OSError as e:
        # e.g. the synced share is offline/unwritable — best-effort: report and
        # return so a publish failure never turns a successful run into a
        # reported failure (the local scratch copy still has the deliverables).
        print(f"[publish] could not access {publish_dir}: {e}", file=sys.stderr)
        return 0
    count = 0
    for entry in entries:
        if entry.lower().endswith(".rsproj"):
            continue
        src = os.path.join(project_dir, entry)
        if entry.lower() in _PUBLISH_EXCLUDE_DIRS and os.path.isdir(src):
            continue
        dst = os.path.join(publish_dir, entry)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            count += 1
        except OSError as e:
            print(f"[publish] could not copy {entry}: {e}", file=sys.stderr)
    return count


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
    pre.add_argument("--preset", default=None,
                     help="Opt-in run template from the profile's 'presets' (e.g. "
                          "specular_metal). Lays a difficult environment's tuned "
                          "knobs over the defaults below; explicit flags still "
                          "win. Omit for plain defaults. See TUNING.md.")
    pre.add_argument("--quality", choices=QUALITY_TIERS, default=None,
                     help="Reconstruction quality preset (profile/--preset "
                          "default if omitted): draft / balanced / max. Maps to "
                          "RC's mesh preset (preview / normal / high). Ignored "
                          "with --blockout.")
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
        preset = get_preset(preargs.preset, "realityscan")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if preset:
        print(f"[preset] '{preargs.preset}' applied over defaults "
              f"(explicit flags still override).")
        if preset.get("mask_background"):
            # RC mask import isn't wired (import_masks is a stub); be explicit
            # rather than silently dropping a requested noise lever.
            print("[preset] note: mask_background is set, but RealityScan mask "
                  "import is not wired here - mask the subject / set a tight "
                  "reconstruction region in RealityScan's GUI (see TUNING.md).")

    p = argparse.ArgumentParser(description=__doc__, parents=[pre])
    p.add_argument(
        "--input-root", default=prof["input_root"],
        help="Root containing per-capture subdirectories of frames. "
             "Defaults to the profile's input root.",
    )
    p.add_argument(
        "--frames-dir", default=None,
        help="A single, already-prepared capture directory (images/). When "
             "given, it is the sole source and --input-root subdir discovery is "
             "skipped — the single-capture counterpart to --input-root (the UI "
             "panel passes this; multi-session CLI runs use --input-root).",
    )
    p.add_argument(
        "--output-root", default=prof["realityscan_scratch_root"],
        help="Root for the RC project + intermediate dirs. Defaults to the "
             "profile's LOCAL scratch (scratch_root/rc_out) — RC must not work "
             "in a cloud-sync folder. Publish the finished export separately.",
    )
    p.add_argument("--name", default="combined", help="Project basename.")
    p.add_argument(
        "--blockout", default=None,
        help="Optional path to a low-poly mesh; when given, build_model is "
             "skipped and the texture bakes onto the imported mesh.",
    )
    _quality_default = (
        preargs.quality or preset.get("quality") or prof.get("quality", "balanced")
    )
    if _quality_default not in QUALITY_TIERS:
        # argparse validates only CLI-passed values, not defaults; fail fast
        # instead of KeyErroring at build_model hours into the run. A valid
        # explicit --quality (pre-parsed above, mirroring the Metashape
        # runner) rescues a typo'd preset/profile value — flags still win.
        print(f"error: unknown quality {_quality_default!r} (from preset/"
              f"profile); expected draft/balanced/max.", file=sys.stderr)
        return 2
    # --quality itself is declared on the pre-parser (parents=[pre]) with
    # default None; install the resolved preset/profile default here.
    p.set_defaults(quality=_quality_default)
    p.add_argument(
        "--simplify", type=int,
        default=preset.get("simplify_target", rec.get("simplify_target", 20_000_000)),
        help="Simplify the high model to ~N triangles before unwrap so the UV "
             "atlas fits the texture budget (fixes RC's 'increase maximal "
             "texture count/resolution' unwrap failure). Texture quality is "
             "unaffected. Set 0 to disable. Default from the profile's "
             "reconstruct.simplify_target (or --preset).",
    )
    p.add_argument(
        "--clean-min-component", type=int,
        default=preset.get("min_component_size", rec.get("min_component_size", 100)),
        help="Mesh-cleanup floor: delete disconnected components smaller than N "
             "triangles (RC -setMinComponentSize). The main CLI-reachable lever "
             "against speckle / 'snow' floaters; raise it hard on specular / "
             "low-texture captures. Default from the profile's "
             "reconstruct.min_component_size (or --preset). 0 disables.",
    )
    # Panel-saved presets snapshot every widget, including the stage toggles —
    # honor them so a preset replayed via --preset reproduces the panel run
    # (preprocess_input=False is the panel's master off-switch for both).
    _preset_prep_off = not preset.get("preprocess_input", True)
    p.add_argument("--skip-curate", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("skip_curate", False)
                                or _preset_prep_off),
                   help="Skip pre-RC dHash + sharpness curation.")
    p.add_argument("--curate-preview", action="store_true",
                   help="Dry-run: report curation survivor counts per dHash "
                        "threshold + the sharpness distribution, then exit (no "
                        "reconstruction). Use to tune --curate-hash-threshold on "
                        "a real set before a long run.")
    p.add_argument("--skip-equalize", action=argparse.BooleanOptionalAction,
                   default=bool(preset.get("skip_equalize", False)
                                or _preset_prep_off),
                   help="Skip cross-session exposure equalization.")
    p.add_argument("--curate-hash-threshold", type=int,
                   default=preset.get("curate_hash_threshold",
                                      cur.get("hash_threshold", 0)),
                   help="dHash Hamming distance for content-dedup clustering. "
                        "Default 0 = no dedup (blur culling still applies) - the "
                        "right default for continuous video / single-pass "
                        "captures, whose near-identical frames carry the "
                        "small-baseline overlap SfM triangulates from. 5 = "
                        "near-identical only; raise past that only for redundant "
                        "static photo sets. Kept identical to the Metashape "
                        "runner so both engines receive the same prepped input.")
    p.add_argument("--curate-sharpness-floor", type=float,
                   default=cur.get("sharpness_floor", 0.0),
                   help="Reject any frame whose Laplacian variance is below this "
                        "absolute value (scene-dependent; prefer the percentile).")
    p.add_argument("--curate-sharpness-percentile", type=float,
                   default=preset.get("curate_sharpness_percentile",
                                      cur.get("sharpness_percentile", 0.0)),
                   help="Relative blur cutoff: drop frames below this percentile "
                        "of the set's own sharpness distribution. Default 0 = "
                        "off - a percentile cut ALWAYS removes that share of the "
                        "set, even when every frame is sharp; the "
                        "median-fraction guard below handles genuinely defocused "
                        "frames.")
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
                        "local contrast (RC re-balances during texturing). "
                        "1.0 = full Reinhard match.")
    p.add_argument("--equalize-reference", choices=("first", "median", "global"),
                   default=preset.get("equalize_reference",
                                      eq.get("reference", "median")),
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
                   help="Keep a reopenable RC project (.rsproj) so a later run "
                        "can reopen it and re-run only some stages. RC always "
                        "writes its project during the run (state persistence), "
                        "so by DEFAULT (off) the local .rsproj is removed after "
                        "export, leaving only the deliverables. Note: via --rsnode "
                        "the project lives in the node session and is never "
                        "downloaded, so reopening requires a local run (--rsnode off).")
    p.add_argument("--texture-size", default=preset.get("texture_size", "auto"),
                   help="'auto' (default) derives from source long edge (capped "
                        "8192). NOTE: RC's bake size is GUI/settings-controlled, "
                        "not CLI — this is RECORDED in QC but not applied; set it "
                        "once in RealityScan's texturing settings (it persists).")
    p.add_argument("--rc-exe", default=None,
                   help="Override RealityCapture.exe path. "
                        "Default: RC_EXE env or standard install.")
    p.add_argument("--rsnode", choices=("auto", "on", "off"), default="auto",
                   help="RSNode REST transport (drives a running, signed-in "
                        "RealityScan headlessly from any session): 'auto' uses it "
                        "when a node is reachable else falls back to the CLI "
                        "launcher; 'on' requires it; 'off' forces the CLI. "
                        "Env RC_RSNODE overrides 'auto'.")
    p.add_argument("--rsnode-url", default=None,
                   help="RSNode base URL (default RC_RSNODE_URL env or "
                        "http://127.0.0.1:8000).")
    p.add_argument("--publish-root", default=prof["realityscan_output_root"],
                   help="Synced output root for finished deliverables. RC works "
                        "in local scratch (--output-root), then on success the "
                        "deliverables (OBJ/MTL/textures/report/QC/logs — not the "
                        ".rsproj) are copied to <publish-root>/<name>. Default: the "
                        "profile's realityscan_output_root.")
    p.add_argument("--no-publish", action="store_true",
                   help="Skip publishing deliverables to the synced output root "
                        "(leave them only in local scratch).")
    p.add_argument("--mock", action="store_true",
                   help="Force mock mode — no RC subprocess fired. "
                        "Useful for validating plumbing on the real input set.")
    args = p.parse_args(argv)

    if args.frames_dir:
        # Single prepared capture (the panel's single-capture path): use it
        # directly, skip --input-root subdir discovery.
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

    if str(args.texture_size).lower() == "auto":
        sample = first_image_in_dirs(sources)
        texture_size = derive_texture_size(sample)
        print(f"Texture size: {texture_size} (auto, from {sample}; "
              f"RC bake size is GUI-set - recorded only)")
    else:
        texture_size = int(args.texture_size)

    project_dir = os.path.join(args.output_root, args.name)
    os.makedirs(project_dir, exist_ok=True)

    rc = RealityCaptureWorkflow(
        project_path=project_dir,
        name=args.name,
        rc_exe=args.rc_exe,
        mock_mode=True if args.mock else None,
        gate_mode=args.gate_mode,
        checkpoint_each_stage=args.save_project,
        use_rsnode={"auto": None, "on": True, "off": False}[args.rsnode],
        rsnode_url=args.rsnode_url,
    )
    print(rc.get_license_info())
    if rc.mock_mode:
        reason = "forced via --mock" if args.mock else "RealityScan/RealityCapture not found"
        print(
            f"Running in MOCK MODE ({reason}). "
            "QC sidecar will still be written; no scene produced."
        )

    if args.curate_preview:
        rc.preview_curation(
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
        rc.finalize_run(success=True)  # flush the preview stage to the sidecar
        return 0

    try:
        rc.create_chunk(f"{args.name} (combined)")

        if not args.skip_curate:
            sources = rc.curate_input_set(
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
            sources = rc.equalize_exposures(
                sources,
                strength=args.equalize_strength,
                reference_strategy=args.equalize_reference,
            )
        elif not args.skip_equalize:
            print(
                "[equalize] skipped: single capture - cross-set exposure matching "
                "needs >=2 captures; re-encoding a lone set only risks SfM feature "
                "quality for no benefit (the engine re-balances color at texture)."
            )

        rc.add_image_dirs(sources)
        rc.align_photos_with_retry(min_aligned_pct=50.0)

        if args.blockout:
            rc.import_model(args.blockout)
        else:
            # Map the unified quality preset to RC's mesh preset.
            rc_model = {"draft": "preview", "balanced": "normal", "max": "high"}
            rc.build_model(face_count=rc_model[args.quality])
            rc.clean_mesh(remove_components_face_threshold=args.clean_min_component)
            if args.simplify and args.simplify > 0:
                rc.simplify_model(args.simplify)

        rc.build_texture(texture_size=texture_size)
        if args.save_project:
            rc.save_project()
        rc.export_model()
        rc.export_qc()
        sidecar = rc.finalize_run(success=True)
        if not args.save_project:
            # RC writes its .rsproj during the run for state; with save-project
            # off, drop the local project file so only the deliverables remain
            # (exports are separate files, untouched). No-op for RSNode runs,
            # where the project lives in the node session, not on local disk.
            proj = getattr(rc, "_project_file", None)
            if proj and os.path.isfile(proj):
                try:
                    os.remove(proj)
                    print(f"[save-project off] removed local project {proj}")
                except OSError as e:
                    print(f"[save-project off] could not remove {proj}: {e}")
        if not args.no_publish and not rc.mock_mode:
            publish_dir = os.path.join(args.publish_root, args.name)
            published = publish_outputs(project_dir, publish_dir)
            if published is not None:
                print(f"Published {published} deliverable item(s) -> {publish_dir}")
        print(f"\nDone. QC sidecar: {sidecar}")
        return 0
    except Exception as e:
        print(f"\nWorkflow failed: {e}", file=sys.stderr)
        rc.finalize_run(success=False)
        raise


if __name__ == "__main__":
    sys.exit(main())
