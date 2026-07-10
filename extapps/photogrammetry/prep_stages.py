# !/usr/bin/python
# coding=utf-8
"""Shared, SDK-agnostic input-prep stages for the photogrammetry engines.

``curate_input_set`` (dHash + sharpness culling) and ``equalize_exposures``
(cross-set exposure/WB matching) are identical for RealityCapture and
Metashape — they only call :mod:`pythontk` primitives plus the engine's QC
log. Keeping them in one mixin both engines inherit makes the documented
RC↔Metashape "same public method shape" contract structural (the two cannot
drift apart again) and unifies their QC payloads.

Host requirements: ``self.qc`` (a ``pythontk.QcLog``), ``self.project_path``
(str), and ``self._notify(stage, fraction)``.
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional, Sequence

from .profile import IMAGE_EXTS


def _next_power_of_two(n: int) -> int:
    n = int(n)
    return 1 << max(0, n - 1).bit_length() if n > 1 else 1


def image_long_edge(image_path: str) -> Optional[int]:
    """Long edge (px) of an image, or ``None`` if unreadable.

    Delegates to :meth:`pythontk.ImgUtils.get_image_size`, whose stdlib-first
    JPEG/PNG header read works even in Metashape's bundled Python (no PIL/cv2) —
    so ``--texture-size auto`` resolves the true source resolution instead of
    silently using the 8192 default. Never raises: any failure (incl. an
    unexpected import problem) yields ``None`` so ``derive_texture_size`` falls
    back to its default rather than aborting the run.
    """
    try:
        from pythontk import ImgUtils
        size = ImgUtils.get_image_size(image_path)
    except Exception:
        return None
    return max(size) if size else None


def extract_videos_to_dir(
    videos: Sequence[str],
    output_dir: str,
    *,
    window_sec: float = 1.0,
    quality: int = 95,
    log: Optional[Callable[[str], None]] = None,
) -> List[str]:
    """Extract frames from one or more videos into a single ``output_dir``.

    Sharpest-per-window extraction (one sharpest frame per ``window_sec`` of
    source) — the right default for handheld clips, where fixed-step sampling
    wastes frames when the camera is still and starves overlap when it moves
    (see :meth:`pythontk.FrameExtractor.extract_frames_sharpest`). Each video's
    frames are prefixed with its stem + a digest of its absolute path, so
    several clips share one frames dir without colliding — including
    same-named clips from different folders picked in separate browses — and
    re-extracting a clip replaces exactly its own previous frames.

    Returns every written frame path (empty when OpenCV is unavailable — the
    caller decides how to surface that; e.g. the headless runner errors and the
    panel logs a hint). Never raises on a single unreadable video: it's logged
    via *log* and the remaining videos still process.

    cv2 is imported lazily (via ``FrameExtractor``) so this module stays
    importable in Metashape's bundled Python, where cv2 is typically absent —
    extraction itself only runs where cv2 is present (the UI process / a normal
    Python ``run_combined --video``).
    """
    import hashlib
    import re

    from pythontk import FrameExtractor

    os.makedirs(output_dir, exist_ok=True)
    extractor = FrameExtractor()
    written: List[str] = []
    total = len(videos)
    for i, video in enumerate(videos):
        stem = os.path.splitext(os.path.basename(video))[0]
        # The prefix keys frames to their SOURCE FILE: sanitized stem plus a
        # short digest of the absolute path. A positional index can't do this
        # job — the panel's Source browser restarts numbering every pick, so
        # same-named clips from different folders collided (and the purge
        # below would delete the other clip's frames), while re-picking the
        # same clip under a different index orphaned its old frames.
        norm = os.path.normcase(os.path.abspath(video))
        digest = hashlib.md5(norm.encode("utf-8")).hexdigest()[:8]
        safe_stem = "".join(c if c.isalnum() else "_" for c in stem)
        prefix = f"{safe_stem}_{digest}"
        # Purge this clip's frames from any previous extraction FIRST: the
        # filenames encode the winning frame index, which changes with
        # window_sec / source edits, so without the purge the dir becomes the
        # union of every extraction ever run — and downstream alignment
        # silently ingests stale frames the current settings would not have
        # picked (quality then degrades run over run with no code change).
        # Exact-shape match ({prefix}_NNNNNN.jpg, the FrameExtractor naming):
        # a bare startswith(prefix) would also purge a *different* clip whose
        # stem merely extends this one (clip vs clip_final). The legacy
        # alternative catches this clip's frames from the pre-digest scheme
        # ({ii}_{stem}_NNNNNN.jpg) so an upgrade re-extraction can't leave
        # them behind to be silently co-ingested.
        frame_re = re.compile(
            "(?:" + re.escape(prefix)
            + r"|\d{2}_" + re.escape(safe_stem)
            + r")_\d{6}\.(jpg|jpeg)$",
            re.IGNORECASE,
        )
        stale = [f for f in os.listdir(output_dir) if frame_re.match(f)]
        for f in stale:
            try:
                os.remove(os.path.join(output_dir, f))
            except OSError:
                pass
        if stale and log:
            log(f"  purged {len(stale)} stale frame(s) from a previous extraction")
        if log:
            log(f"[video {i + 1}/{total}] {os.path.basename(video)} …")
        try:
            frames = extractor.extract_frames_sharpest(
                video_path=video,
                output_folder=output_dir,
                window_sec=window_sec,
                quality=quality,
                prefix=prefix,
            )
        except Exception as e:  # noqa: BLE001 — one bad clip shouldn't abort the rest
            if log:
                log(f"  failed: {e}")
            continue
        if log:
            log(f"  {len(frames)} frame(s)")
        written.extend(frames)
    # Frames in the dir that this run did not write (a different clip list /
    # foreign files) still reach the engine via add_images — surface them.
    if written and log:
        written_names = {os.path.basename(p) for p in written}
        foreign = [
            f for f in os.listdir(output_dir)
            if f.lower().endswith(IMAGE_EXTS) and f not in written_names
        ]
        if foreign:
            log(
                f"  WARNING: {len(foreign)} other image(s) already in "
                f"'{output_dir}' will also be ingested (e.g. "
                f"'{foreign[0]}'). Clear the folder if they're stale."
            )
    return written


def first_image_in_dirs(dirs: Sequence[str]) -> Optional[str]:
    """First image file (sorted) across ``dirs``, or ``None``."""
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(IMAGE_EXTS):
                return os.path.join(d, f)
    return None


def derive_texture_size(
    image_path: Optional[str], floor: int = 2048, cap: int = 8192, default: int = 8192
) -> int:
    """Texture page size from a source image: next power-of-two ≥ its long edge,
    clamped to ``[floor, cap]``.

    Photogrammetry's multi-view bake holds roughly source-pixel detail (with a
    modest multi-view super-resolution bump), so matching the texture to the
    source avoids both under-resolving and upscaling noise into empty texels.
    16K is deliberately out of reach (``cap=8192``) — for ≤~4.5K-px frames it
    would only store interpolated data and bloats every downstream tool. Use
    UDIM/multiple pages for large objects rather than one oversized page.
    Examples: 4532px → 8192, 3840 → 4096, 1920 → 2048. Falls back to ``default``
    when the image is unreadable (no PIL/cv2, e.g. Metashape's bundled Python).
    """
    if not image_path:
        return default
    le = image_long_edge(image_path)
    if le is None:
        return default
    return max(floor, min(cap, _next_power_of_two(le)))


class PrepStagesMixin:
    """Curate + equalize stages shared by both photogrammetry engines."""

    def curate_input_set(
        self,
        source_dirs: Sequence[str],
        output_root: Optional[str] = None,
        hash_threshold: int = 0,
        sharpness_floor: float = 0.0,
        sharpness_floor_percentile: Optional[float] = None,
        min_sharpness_fraction_of_median: float = 0.0,
        keep_per_cluster: int = 1,
        overcuration_warn_pct: float = 30.0,
    ) -> List[str]:
        """Pre-SfM content + sharpness culling via :class:`pythontk.ImageCurator`.

        Cluster by dHash, keep the sharpest of each cluster, drop blurry images
        outright. ``sharpness_floor_percentile`` (0-100) derives the blur cutoff
        from the cluster-representative distribution (portable across scenes;
        near-duplicate blur can't dilute it). ``min_sharpness_fraction_of_median``
        (0-1) adds a median-relative guard that culls catastrophically defocused
        frames the percentile misses. Returns the curated source directories (one
        per input dir); on a missing dependency it marks the QC stage ``fallback``
        and returns the inputs unchanged rather than implying curation happened.

        **Curation is overlap-destroying when over-aggressive.** dHash dedup
        removes *perceptually* similar frames — but for SfM, near-identical-looking
        consecutive frames of a moving camera carry exactly the small-baseline
        parallax the solver triangulates from. Stripping them (high
        ``hash_threshold``) fragments alignment on hard / single-pass captures.
        ``overcuration_warn_pct`` raises a QC warning when the kept set drops below
        that much of the input, so silent over-thinning can't pass unnoticed (set
        ``hash_threshold=0`` to disable dedup entirely and keep blur culling only —
        the right default for continuous video walkthroughs).
        """
        self._notify("curate_input_set", 0.0)
        output_root = output_root or os.path.join(self.project_path, "curated")
        with self.qc.stage("curate_input_set") as st:
            st["source_dirs"] = list(source_dirs)
            st["output_root"] = output_root
            st["hash_threshold"] = hash_threshold
            st["sharpness_floor"] = sharpness_floor
            st["sharpness_floor_percentile"] = sharpness_floor_percentile
            st["min_sharpness_fraction_of_median"] = min_sharpness_fraction_of_median
            st["keep_per_cluster"] = keep_per_cluster
            try:
                from pythontk import ImageCurator
            except ImportError:
                self.qc.warn("ImageCurator not importable (pythontk missing)")
                st["fallback"] = "pythontk_missing"
                return list(source_dirs)
            curator = ImageCurator()
            if not curator.is_available():
                self.qc.warn(
                    "cv2 not available in this interpreter - INPUT CURATION "
                    "DID NOT RUN (frames pass through as-is). Metashape's "
                    "bundled Python has no cv2, so runs driven via "
                    "'metashape.exe -r' always take this path; to actually "
                    "curate, pre-process the frames dir under a Python with "
                    "opencv (e.g. the panel venv) first."
                )
                st["fallback"] = "cv2_missing"
                return list(source_dirs)
            before = sum(
                1
                for d in source_dirs if os.path.isdir(d)
                for f in os.listdir(d) if f.lower().endswith(IMAGE_EXTS)
            )
            out_dirs = curator.curate(
                source_dirs=list(source_dirs),
                output_root=output_root,
                hash_threshold=hash_threshold,
                sharpness_floor=sharpness_floor,
                sharpness_floor_percentile=sharpness_floor_percentile,
                min_sharpness_fraction_of_median=min_sharpness_fraction_of_median,
                keep_per_cluster=keep_per_cluster,
            )
            after = sum(
                1
                for d in out_dirs if os.path.isdir(d)
                for f in os.listdir(d) if f.lower().endswith(IMAGE_EXTS)
            )
            st["before"] = before
            st["after"] = after
            st["output_dirs"] = out_dirs
            removed_pct = round(100.0 * (before - after) / before, 1) if before else 0.0
            st["removed_pct"] = removed_pct
            print(f"Curated {before} -> {after} images ({removed_pct:.0f}% removed).")
            if before and removed_pct >= overcuration_warn_pct:
                self.qc.warn(
                    f"curation removed {removed_pct:.0f}% of frames "
                    f"({before} -> {after}). Aggressive dHash dedup strips the "
                    f"small-baseline overlap SfM triangulates from; on hard or "
                    f"single-pass captures this fragments alignment. Lower "
                    f"--curate-hash-threshold (0 disables dedup, keeping only blur "
                    f"culling) and verify alignment coverage."
                )
            return out_dirs or list(source_dirs)

    def preview_curation(
        self,
        source_dirs: Sequence[str],
        hash_thresholds: Sequence[int] = (5, 8, 10, 12, 15),
        keep_per_cluster: int = 1,
        sharpness_floor_percentile: Optional[float] = None,
        min_sharpness_fraction_of_median: float = 0.0,
    ):
        """Dry-run curation QC — report survivor counts per dHash threshold + the
        sharpness distribution **without copying any files**, so curation can be
        tuned on a real set before committing a long run (see
        :meth:`pythontk.ImageCurator.preview`). Records the report under QC stage
        ``preview_curation`` and returns it (``None`` if cv2/pythontk missing)."""
        self._notify("preview_curation", 0.0)
        with self.qc.stage("preview_curation") as st:
            st["source_dirs"] = list(source_dirs)
            st["hash_thresholds"] = list(hash_thresholds)
            try:
                from pythontk import ImageCurator
            except ImportError:
                self.qc.warn("ImageCurator not importable (pythontk missing)")
                st["fallback"] = "pythontk_missing"
                return None
            curator = ImageCurator()
            if not curator.is_available():
                self.qc.warn("cv2 not installed; curation preview skipped.")
                st["fallback"] = "cv2_missing"
                return None
            report = curator.preview(
                list(source_dirs),
                hash_thresholds=tuple(hash_thresholds),
                keep_per_cluster=keep_per_cluster,
                sharpness_floor_percentile=sharpness_floor_percentile,
                min_sharpness_fraction_of_median=min_sharpness_fraction_of_median,
            )
            st["report"] = report
            sh = report.get("sharpness", {})
            print(f"Curation preview: {report['n_scanned']} frames scanned.")
            if sh:
                print(
                    f"  sharpness  min={sh['min']:.0f} median={sh['median']:.0f} "
                    f"max={sh['max']:.0f}"
                )
            for row in report.get("thresholds", []):
                print(
                    f"  hash_threshold={row['hash_threshold']:<3} -> kept "
                    f"{row['n_kept']} ({row['reduction_pct']:.0f}% reduction)"
                )
            return report

    def equalize_exposures(
        self,
        source_dirs: Sequence[str],
        output_root: Optional[str] = None,
        reference_dir: Optional[str] = None,
        strength: float = 0.5,
        reference_strategy: str = "median",
    ) -> List[str]:
        """Cross-set exposure / WB equalization via :class:`pythontk.ExposureEqualizer`.

        ``strength`` (0-1) blends the match with each frame's original so local
        contrast is preserved (RealityCapture/Metashape re-balance during
        texturing, so a gentle nudge beats a full flatten); ``reference_strategy``
        (``first``/``median``/``global``) picks the target distribution without
        letting the first capture's color cast dominate. Returns the equalized
        directories — pass them to ``add_image_dirs`` in place of the originals.
        """
        self._notify("equalize_exposures", 0.0)
        output_root = output_root or os.path.join(self.project_path, "equalized")
        with self.qc.stage("equalize_exposures") as st:
            st["source_dirs"] = list(source_dirs)
            st["output_root"] = output_root
            st["strength"] = strength
            st["reference_strategy"] = reference_strategy
            try:
                from pythontk import ExposureEqualizer
            except ImportError:
                self.qc.warn("ExposureEqualizer not importable (pythontk missing)")
                st["fallback"] = "pythontk_missing"
                return list(source_dirs)
            eq = ExposureEqualizer()
            if not eq.is_available():
                self.qc.warn(
                    "cv2 not available in this interpreter - EXPOSURE "
                    "EQUALIZATION DID NOT RUN (frames pass through as-is; "
                    "always the case under 'metashape.exe -r', whose bundled "
                    "Python has no cv2). Equalize the capture dirs under a "
                    "Python with opencv first if cross-capture matching is "
                    "needed."
                )
                st["fallback"] = "cv2_missing"
                return list(source_dirs)
            out_dirs = eq.equalize_directories(
                list(source_dirs),
                output_root,
                reference_dir,
                strength=strength,
                reference_strategy=reference_strategy,
            )
            st["output_dirs"] = out_dirs
            fallbacks = getattr(eq, "last_fallback_count", 0)
            st["exif_fallback_count"] = fallbacks
            if fallbacks:
                self.qc.warn(
                    f"{fallbacks} equalized frame(s) lost EXIF (PIL save "
                    f"failed; cv2 fallback) - SfM loses focal-length priors "
                    f"and portrait frames may load sideways. Fix PIL before "
                    f"trusting this run."
                )
            print(f"Equalized {len(source_dirs)} dirs -> {output_root}")
            return out_dirs or list(source_dirs)
