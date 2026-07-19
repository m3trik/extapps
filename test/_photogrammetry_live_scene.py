# !/usr/bin/python
# coding=utf-8
"""Shared synthetic-capture fixture for the gated live Metashape tests.

Not a ``test_*`` module (underscore-prefixed) so pytest never collects it.
Imported by ``test_metashape_live_integration`` (align + mask path) and
``test_metashape_usdz_live`` (full model/texture/export → USDZ sidecar) — one
scene builder so the two cannot drift. Needs ``numpy`` + ``cv2`` in the OUTER
runner process (not Metashape's bundled Python).
"""
import os


def make_nadir_scene(root, n_cols=6, n_rows=4, with_masks=False):
    """Textured plane sampled by overlapping nadir crops.

    Standard drone-mapping geometry (70%/50% overlap) that aligns fully.
    Writes ``<root>/frames/cam_NNN.jpg``; when *with_masks*, also writes
    matching all-white ``<root>/masks/cam_NNN_mask.png``. The RNG is seeded so
    the texture (and thus the alignment) is deterministic run to run.

    Returns ``(frames_dir, masks_dir)`` — *masks_dir* is only populated when
    *with_masks* is True (callers that don't need masks unpack ``frames, _``).
    """
    import numpy as np
    import cv2

    frames = os.path.join(root, "frames")
    masks = os.path.join(root, "masks")
    os.makedirs(frames)
    if with_masks:
        os.makedirs(masks)
    rng = np.random.default_rng(7)
    H, W = 3600, 4800
    tex = np.zeros((H, W, 3), np.float32)
    for scale, weight in ((8, 0.4), (32, 0.35), (128, 0.25)):
        layer = rng.random((H // scale + 2, W // scale + 2, 3)).astype(np.float32)
        tex += weight * cv2.resize(layer, (W, H), interpolation=cv2.INTER_CUBIC)
    span = float(tex.max() - tex.min()) + 1e-6
    tex = (255 * (tex - tex.min()) / span).astype(np.uint8)
    cw, ch = 1920, 1440
    xs = np.linspace(0, W - cw, n_cols).astype(int)
    ys = np.linspace(0, H - ch, n_rows).astype(int)
    n = 0
    for y in ys:
        for x in xs:
            name = f"cam_{n:03d}"
            cv2.imwrite(os.path.join(frames, name + ".jpg"),
                        tex[y:y + ch, x:x + cw],
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            if with_masks:
                cv2.imwrite(os.path.join(masks, name + "_mask.png"),
                            np.full((ch, cw), 255, np.uint8))
            n += 1
    return frames, masks
