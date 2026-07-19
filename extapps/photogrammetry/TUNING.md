# Photogrammetry tuning — reconstruction quality & noise control

Hard-won settings for the mesh engines (`metashape_workflow`, `realityscan_workflow`),
packaged so future runs build on them instead of rediscovering them. The knobs
ship as **opt-in run templates** — JSON files selected with `--preset NAME`; with no
preset the runners use their plain defaults (nothing here changes behavior unless you
ask for it).

Presets resolve through a two-tier `pythontk.PresetStore` (the same store that backs
uitk's `PresetManager`, so the headless and UI paths agree), and are **scoped
per engine** — a Metashape tuning preset (align/depth downscale, matchPhotos limits,
depth filter) means nothing to RealityScan and vice-versa, so each engine has its own
dirs and nothing is shared:

- **built-in** (read-only, shipped): [`presets/<engine>/`](presets/) next to this file — e.g. [`presets/metashape/specular_metal.json`](presets/metashape/specular_metal.json) and [`presets/realityscan/specular_metal.json`](presets/realityscan/specular_metal.json). `<engine>` is `metashape` / `realityscan` / `gaussian_splat` / `sugar`.
- **user** (writable, overrides a built-in of the same name): `<user-config>/uitk/extapps/photogrammetry_presets/<engine>/*.json`. A preset saved from the Metashape panel lands in `…/metashape/` and is therefore a *Metashape* preset — it never appears in another engine's `--preset` list.

Add a preset by dropping a JSON file in the relevant engine's dir — no runner code
changes. To use the "same" template on two engines, put a copy in each (with each
engine's reachable keys).

```powershell
# Difficult capture: lay each engine's specular-metal template over its defaults.
python -m extapps.photogrammetry.metashape_workflow.run_combined   --name job --preset specular_metal
python -m extapps.photogrammetry.realityscan_workflow.run_combined --name job --preset specular_metal
```

Explicit flags always win over a preset, and a preset always wins over `--quality`'s
derived values. The two `specular_metal` files describe the *same environment* but
carry only the keys each engine can actually reach (Metashape gets the depth/align +
matchPhotos levers; RealityScan's are mostly GUI-only, so its copy just flags masking
and points you at the GUI checklist).

---

## When reconstructions go noisy: diagnosis

| Symptom | Cause |
|:--|:--|
| "Snow" / speckle — small floating clusters in mid-air | Spurious depth from **specular highlights**, **low/repetitive texture**, and **out-of-subject background** that has no consistent multi-view match. |
| Ghosted / "melted" / doubled geometry | **View-dependent appearance** (shiny metal, reflections look different from each camera) breaks the photo-consistency assumption multi-view stereo relies on. |
| Holes / thin or missing surfaces on bright metal | Blown highlights and featureless areas yield no usable depth. |

The worked example below is a **reflective-metal subject**: shiny steel, painted
low-texture surfaces, bright/uneven lighting — close to a worst case for
photogrammetry. The result was usable in outline but too noisy to ship; the same
levers apply to any reflective-machinery / fabrication / polished-surface capture.

---

## The levers, and where each one lives

The strongest noise controls are **not** on either CLI. RealityScan in particular
exposes almost none of them to `-` commands — they're per-project Settings / GUI.
Plan around that: the CLI runs the pipeline, but the quality dials are set once in
the app and persist.

| Lever | Effect on noise | Metashape | RealityScan |
|:--|:--|:--|:--|
| **Capture: cut the specularity** (cross-polarized flash, polarizer, matte dulling spray, diffuse/overcast lighting) | Removes the root cause — the only true fix for shiny metal | capture-time | capture-time |
| **Subject masking** (exclude background) | Kills background floaters; sharpens silhouettes — and (since 2026-07) the masks also gate feature *matching* (`filter_mask`), not just depth | `--use-masks`: pre-generated rembg `_mask` files imported first (the panel's venv prep stage writes them, so masking works out of the box), else Metashape 2.2+ built-in AI masking (needs its model — run Generate Masks (AI) once in the GUI to download it), else in-process rembg → `generateMasks` import (Metashape 2.x removed `importMasks`) | GUI masks / `_mask` images; runner import **not wired** |
| **Tight reconstruction region** (crop the bbox to the subject) | Removes *all* out-of-region floaters — huge | set in GUI | set in GUI (Reconstruction Region box) |
| **Depth-map filtering strength** | Smooths noisy per-pixel depth before meshing | `--depth-filter moderate` | GUI: Reconstruction Settings → *Filtering strength* = **High** |
| **Image / depth downscale** | Higher downscale = smoother, less noisy (less detail). On specular metal **don't go to ds=1/Ultra — it over-fits the noise and *warps* geometry**; ds=2 is the sweet spot. | `--align-downscale`, `--depth-downscale` | GUI: *Image downscale factor* (depth) |
| **Alignment matching** (generic preselection + keypoint/tiepoint limits) | The lever that actually *aligns* featureless / specular subjects: generic preselection pairs images without camera coords, and a raised tiepoint limit builds a denser, more robust sparse cloud. Baseline: generic preselection **on** (Metashape's own default), keypoint `60000` (the verified value). | `--generic-preselection` / `--no-generic-preselection`, `--keypoint-limit`, `--tiepoint-limit` | GUI: Alignment Settings only (CLI ignores them) |
| **Triage** (disable low-quality cameras pre-align) | Drops blurry/noisy frames by Metashape's own `Image/quality` score before matching — a strong cull for genuinely messy input, but the score correlates with *texture*, so it wholesale-disables good frames of low-texture/specular subjects. **Opt-in** (`0` = off, the default); `0.5` is the usual value when you do want it. | `--triage-quality` | folded into RC alignment |
| **Min component size** (drop small disconnected islands) | Strips speckle islands — but it does **not** fix depth-level noise (warping/ghosting) and cranking it deletes real detail, so it's a last touch, not the lever. | `--clean-min-component` → `removeComponents` | `--clean-min-component` → `-setMinComponentSize` |
| **Mesh smoothing** (light Laplacian denoise) | A single pass denoises specular geometry without melting detail (high values do melt it). | `--smooth-strength` | not on CLI |
| **Exposure equalization** | Reduces ghosting from per-frame exposure drift | `equalize` prep stage (on by default) | same prep stage |
| **Quality / mesh density** | Higher = resolves *more* — including more noise | `--quality` / `--face-count` | `--quality` (preview/normal/high) |

**Rule of thumb for shiny/low-texture:** denoise the *depth* (filtering ↑, masking,
tight region) rather than chasing it with a denser mesh — a higher face count on
noisy depth just produces a higher-resolution mess.

---

## Shipped presets

| Preset | For | Sets |
|:--|:--|:--|
| `preview` | A fast, low-quality pass to check coverage / alignment before a full bake (pair with the panel's **Align only** run mode). | `quality=draft`, align/depth downscale `4`, `face_count=low`, `texture_size=2048`. |
| `high` | Highest quality on well-textured, matte subjects. Slow + memory-heavy. | `quality=max`, align/depth downscale `1` (Ultra), `face_count=high`, `texture_size=auto`, plus a denser tie cloud (`keypoint_limit=60000`, `tiepoint_limit=20000`). **Not** for specular/low-texture — use `specular_metal` (ds=1 over-fits there). |
| `specular_metal` | Reflective / low-texture surfaces (machinery, fabrication bays). | See the table below. |

The `quality` tier is what the RealityScan CLI reaches (`preview`/`normal`/`high`); the explicit downscale/filter/face/texture keys, the alignment-matching levers (`generic_preselection`/`keypoint_limit`/`tiepoint_limit`/`triage_quality`), and the mesh-cleanup levers (`min_component_size`/`smooth_strength`/`close_holes`) are what the Metashape runner and the panel widgets apply. All of these keys, plus the input pre-processing knobs below, are editable per-run in the Metashape panel and savable as a user preset.

There is no `default` preset: the balanced baseline *is* no preset (`--preset default`/`none` is a recognized CLI no-op), and the panel's **Reset to Defaults** button restores every widget to its registry baseline.

### Input image pre-processing (preset-controllable)

The pre-SfM culling + exposure-matching knobs are exposed in the panel and overridable by a preset in **both** engines' runners (profile is the fallback, explicit CLI flags still win):

| Key | Flag | Effect |
|:--|:--|:--|
| `curate_hash_threshold` | `--curate-hash-threshold` | dHash near-duplicate clustering distance. **Default `0` = keep all** (blur culling only — right for continuous video, the primary ingest path); raising it strips small-baseline overlap and can fragment alignment. |
| `curate_sharpness_percentile` | `--curate-sharpness-percentile` | Drop frames below this percentile of the set's own sharpness. **Default `0` = off** — a percentile cut always removes that share of the set, even when every frame is sharp (video frames are already sharpest-per-window at extraction). |
| `curate_min_sharpness_frac` | `--curate-min-sharpness-frac` | Drop frames below this fraction of the survivor-median sharpness — the guard that actually targets *broken* (catastrophically defocused) frames. Default `0.15`; `0` disables. |
| `keep_per_cluster` | `--keep-per-cluster` | Keep top-K sharpest per near-duplicate cluster. |
| `equalize_strength` | `--equalize-strength` | Cross-capture exposure-match blend `0-1` (only with 2+ captures; one transform **per capture**, so intra-capture lighting variation survives). |
| `equalize_reference` | `--equalize-reference` | Equalization target distribution (`first`/`median`/`global`). |
| `video_window_sec` | `--video-window-sec` (Metashape `--video` path; panel Source browser reads the widget) | Sharpest-frame extraction window. `1.0` (~1 fps) suits a slow orbit; drop to `0.25–0.5` on fast handheld moves. Re-extraction purges the clip's previous frames first, so stale frames can't accumulate across runs. |

**The no-preset baseline is deliberately non-destructive.** Frames reach the
engine as-shot except for the median-fraction blur guard and (multi-capture
only) gentle per-capture equalization. Dedup, the percentile cull, triage,
camera pose-dedupe, and Metashape `calibrateColors` are all **opt-in** — every
one of them deletes or mutates input, and the verified data (below) shows even
a 2.3% over-cull cost ~10 points of alignment coverage. Turn levers on
per-run/per-preset when a capture needs them, not by default.

**Metashape prep runs venv-side, via a two-stage chain.** `metashape.exe`'s
bundled Python (3.9) has **no cv2/PIL** — the prep stages can never execute
inside `metashape.exe -r` (they skip with a loud warning and `fallback:
cv2_missing` in the QC sidecar; verified live on 2.2.0). So the panel's
`MetashapeRunner` chains two processes: first `run_combined --prep-only` under
the **panel's own Python** (curation, equalization, and — with masking on —
rembg file masks), then `metashape.exe -r` on the prepared frames with
`--skip-curate --skip-equalize`. Prep QC lands in its own
`<name>_prep_qc.json` sidecar beside the engine's. Headless, the same split is
available manually: run `--prep-only` in a venv, then feed the printed dir to
the Metashape run (that is exactly what the runner automates). Direct
`MetashapeConnection` scripts still execute entirely inside `metashape.exe`
and therefore still skip prep. RealityScan/Brush runs execute in the venv, so
their prep stages run in-process. Both image-in panels also expose the
curation dry-run as a **Prep preview** run mode (`--curate-preview`): survivor
counts per dedup threshold + the sharpness distribution, no engine launch, no
files written.

## `specular_metal` preset — what it sets and why

Shipped at [`presets/metashape/specular_metal.json`](presets/metashape/specular_metal.json). Every key is
consumed by the **Metashape** runner; RealityScan can't reach these from its CLI (set
the equivalents in its GUI — see below).

| Key | Value | Rationale |
|:--|:--|:--|
| `align_downscale` | `2` | On reflective steel, **ds=2 aligned *better* and ~12× faster than ds=1** (verified by QC: 90.4% vs 73.8% cameras). Full-res matching over-fits specular noise. Do **not** use ds=1 / "max" here. |
| `depth_downscale` | `2` | Counter-intuitive but verified: full-res depth (ds=1/Ultra) **over-fits** the specular noise and produces *warped* geometry. ds=2 (with the moderate filter) is the sweet spot; add a light smooth if needed. |
| `depth_filter` | `moderate` | The key Metashape denoiser for specular/low-texture surfaces. `mild` (the default) reproduces per-pixel depth noise into the mesh. |
| `face_count` | `high` | Detail is worth keeping once the depth is denoised at the source. |
| `mask_background` | `true` | Exclude background so it can't seed floaters. RealityScan prints a note (its mask import isn't wired — do it in the GUI). |
| `generic_preselection` | `true` | Featureless metal gives reference preselection no coords to pair on; generic (low-res pairwise) preselection is what reaches a full alignment here. |
| `keypoint_limit` | `60000` | Retain more of the few features a low-texture surface yields. |
| `tiepoint_limit` | `20000` | The verified lever (with generic preselection) for a full 812-camera solution + dense tie cloud. |
| `smooth_strength` | `1` | A single light smoothing pass is the right denoise for the residual specular depth noise. |

Deliberately **not** set: `min_component_size`. Cranking the mesh-cleanup floor strips
real disconnected detail without addressing the depth-level noise that causes the
warping/ghosting — it's a last cosmetic touch (`--clean-min-component`), not the fix.
The light `smooth_strength=1` above is the denoise instead.

### Verified alignment notes (a hard specular-metal dataset)
- **812 clean frames aligned ~99–100%**; an over-curated 793-frame set dropped to ~90%. Aggressive dHash dedup strips the small-baseline overlap SfM needs — keep `--curate-hash-threshold` low (≤5) on hard captures.
- The biggest Metashape align lever was **`generic_preselection` + `tiepoint_limit≈20000`** to reach a full 812-camera solution with a dense tie cloud. These are now exposed as runner flags (`--generic-preselection` / `--tiepoint-limit` / `--keypoint-limit`) and panel params, and are baked into the `specular_metal` and `high` presets — bump them further if alignment still fragments.
- Alignment on this set is **non-deterministic** (613–812 cameras run to run); re-run if it fragments badly.

---

## RealityScan: the CLI can't reach the real dials

RealityScan has no Python API and its CLI ignores alignment/reconstruction tuning.
After the noise persisted across CLI runs, the fix is to set these **once in the GUI**
(they persist in the app / per-project Settings), then drive the pipeline via the
runner / RSNode as usual:

1. **Reconstruction Region** — draw a tight box around the subject. Single biggest win against mid-air snow.
2. **Reconstruction Settings → Filtering strength = High** (or *Ultra* if detail allows). Default *Medium* leaves specular speckle.
3. **Image downscale factor** — try `2` for depth on noisy specular before `1`.
4. **Masks** — paint/import per-image masks (background = excluded). RealityScan reads `<image>_mask.png` beside the source images; the runner's `import_masks` is currently a stub — wiring + verifying it on a live run is the open follow-up.
5. As a last cosmetic touch only, `--clean-min-component N` strips residual speckle islands (not a substitute for the GUI dials above). **Unverified semantics**: the runner feeds `-setMinComponentSize` a triangle floor, but historic RealityCapture CLI docs describe that command as the minimal *camera count per alignment component* — A/B it on a live RC before leaning on it (open follow-up, like the mask import).

The runner records the requested texture size and notes these GUI-only levers in the
QC sidecar, but does **not** apply them — they are not CLI-addressable.

### QC output template
`realityscan_workflow/qc_report_template.html` is the bundled, include-free report
template RealityScan's `-exportReport` renders (the stock templates fail headless).
It emits a compact `<qc>` XML the runner parses for aligned-camera %, component
count, and mesh part/triangle counts that drive the acceptance gates. Don't replace
it with a stock template without re-checking the parser in `_realityscan_workflow.py`.

---

## Adding a new template

Drop a JSON file in the relevant **engine's** preset dir — no runner code changes:

- **built-in** (ship it): `extapps/photogrammetry/presets/<engine>/my_environment.json`
- **user** (machine-local, overrides a built-in of the same name): `<user-config>/uitk/extapps/photogrammetry_presets/<engine>/my_environment.json`

`<engine>` is `metashape` / `realityscan` / `gaussian_splat` / `sugar`. Presets are
engine-scoped, so a Metashape template lists Metashape keys and is only offered to the
Metashape runner/panel; to use the same environment on RealityScan, add a sibling copy
under `realityscan/` carrying RC's reachable keys.

```jsonc
// presets/metashape/my_environment.json
{
  "_comment": "what this capture is and why these values",
  "depth_filter": "moderate",
  "depth_downscale": 2
  // ... any subset of the keys in the table above
}
```

Within an engine, keys it doesn't understand are still ignored; an unknown
`--preset NAME` is rejected with the list of that engine's available presets.
