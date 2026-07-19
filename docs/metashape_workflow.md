# metashape_workflow

Ships as part of the [extapps](../README.md) collection. Automate Agisoft Metashape photogrammetry pipelines from Python or a Qt GUI. Runs against Metashape's Python API when licensed; falls back to a print-only mock mode for development and CI.

## Install

Requires Python ≥ 3.9.

```bash
pip install extapps                            # brings in pythontk, uitk, qtpy
pip install opencv-python                      # only if you need frame extraction
```

Metashape Python API: install the wheel matching your interpreter, e.g.

```bash
pip install "https://download.agisoft.com/Metashape-2.2.1-cp37.cp38.cp39.cp310.cp311-none-win_amd64.whl"
```

A licensed Metashape Pro desktop install or a reachable license server is required for non-mock runs.

## Usage

### GUI

```python
from extapps.photogrammetry.metashape_workflow import MetashapeWorkflowUI
ui = MetashapeWorkflowUI()
ui.show(pos="screen", app_exec=True)
```

The package self-registers as a `uitk.external_apps.in_process` entry point, so any uitk host (e.g. tentacle) discovers it automatically — no host-side wiring needed.

### Programmatic

```python
from extapps.photogrammetry.metashape_workflow import MetashapeWorkflow

wf = MetashapeWorkflow(
    project_path="path/to/project",
    name="my_project",
    progress=lambda stage, frac: print(f"→ {stage}"),  # fired at each stage start
)
wf.create_chunk("Main Chunk")
wf.add_images("path/to/images")           # directory (non-recursive) or list of paths
wf.align_photos(downscale=2)
wf.generate_depth_maps(downscale=2)
wf.build_model()
wf.build_texture()
wf.save_project()
wf.export_model()                         # default OBJ; PLY/STL/FBX also supported
```

`mock_mode` is auto-enabled when Metashape is missing or unlicensed. Force it explicitly with `MetashapeWorkflow(..., mock_mode=True)`.

Module-level helpers: `is_metashape_available()`, `is_license_valid()`, `get_metashape_version()`, `get_image_filepaths(directory)`.

### Frame extraction

`FrameExtractor` lives in `pythontk` (it's a generic video → frames helper):

```python
from pythontk import FrameExtractor

ex = FrameExtractor()
info = ex.get_video_info("video.mp4")     # {filename, path, frame_count, fps, width, height, duration, size_mb}
frames = ex.extract_frames(
    video_path="video.mp4",
    output_folder="frames/",
    step=30, quality=95, max_frames=None,
)
```

## GUI controls

| Control | Purpose |
|---|---|
| Source | Frames folder, or video clip(s) to extract (sharpest-per-window, in the panel's Python). |
| Project Name | Project basename (`--name`). Outputs land in `<output-root>/<name>/`. |
| Output Root | Root the project is written under (blank = the photogrammetry profile's `metashape_output_root`). |
| Run mode combo | **Full pipeline** / **Align only** / **Refine only** (`--stop-after`) / **Prep preview** (`--curate-preview` — curation dry-run in the panel's Python; no Metashape launch). |
| Preset combo | Semantic run templates shared with `run_combined --preset` (`preview` / `high` / `specular_metal` + user-saved). Applied as defaults + overlay, exactly like the CLI. |
| Parameter rows | The `parameters.py` registry — input pre-processing, alignment, reconstruction, and mesh-cleanup knobs; rows show/hide per run mode. |
| Run Workflow | Streams the run into the log pane; header menu has Cancel / Open Output Folder / Clear Log. |

## Input pre-processing (two-stage runs)

`metashape.exe`'s bundled Python has no cv2/PIL, so curation / exposure
equalization / rembg masking can never execute inside `metashape.exe -r`. The
panel's runner therefore chains two processes: `run_combined --prep-only`
under the panel's own Python (curation, equalization, and — with masking on —
rembg file masks, all QC-logged to `<name>_prep_qc.json`), then
`metashape.exe -r` on the prepared frames with `--skip-curate
--skip-equalize`. Headless, the same split is manual: run `--prep-only` in a
venv and feed the printed dir to the Metashape run. Tuning guidance and the
non-destructive baseline philosophy: [`photogrammetry/TUNING.md`](../extapps/photogrammetry/TUNING.md).

## Quality tiers and presets

`--quality draft|balanced|max` maps to align/depth downscale 4/4, 2/2, 1/1 and
face count low/medium/high (`balanced` is the default). Shipped presets
(`presets/metashape/`) layer over that: see the preset table in
[`TUNING.md`](../extapps/photogrammetry/TUNING.md). Explicit flags beat a
preset; a preset beats `--quality`-derived values.

## API surface

`MetashapeWorkflow(project_path, name, mock_mode=None, progress=None)`
- `create_chunk(label)`
- `add_images(image_sources)` — str directory or sequence of paths; non-recursive
- `align_photos(downscale=2, generic_preselection=True, reference_preselection=True, keypoint_limit=60000, tiepoint_limit=10000, filter_mask=False)`
- `generate_depth_maps(downscale=2, filter_mode=None)` — `filter_mode` defaults to `Metashape.MildFiltering`
- `build_model(source_data=None, surface_type=None, interpolation=None, face_count=None)`
- `build_texture(texture_size=8192, texture_type=None, blending_mode=None, mapping_mode=None, ghosting_filter=True)`
- `save_project()`
- `export_model(export_format=None, binary=True, precision=6, texture_format=None, save_texture=True, save_normals=True, save_colors=True, save_cameras=False, overwrite=True)` — accepts `Metashape.ModelFormatOBJ/PLY/STL/FBX`

`FrameExtractor`
- `extract_frames(video_path, output_folder, step=5, quality=95, prefix="frame", max_frames=None) -> List[str]`
- `get_video_info(video_path) -> dict`

## Testing

```bash
pytest test/test_metashape_workflow.py                  # from the extapps/ root
```

Scope is intentionally narrow ([extapps/test/test_metashape_workflow.py](../test/test_metashape_workflow.py)): UI builds, declared widget names resolve, Run Workflow on empty inputs bails cleanly. Behavioral coverage of the photogrammetry pipeline is out of scope — that needs Metashape installed and real input.

## Adding a preset

Presets live at module scope. Edit [`PRESETS`](../extapps/photogrammetry/metashape_workflow/slots.py) directly:

```python
PRESETS["Ultra"] = {
    "align_downscale": 1,
    "depth_downscale": 1,
    "face_count": "High",       # one of FACE_COUNT_OPTIONS
    "texture_size": 16384,
}
```

`face_count` is a string key resolved against `Metashape.{Low,Medium,High}FaceCount` at run time by `MetashapeWorkflowSlots._resolve_face_count`.

## Layout

```
extapps/photogrammetry/metashape_workflow/
├── __init__.py                  # public API via pythontk bootstrap_package
├── _metashape_workflow.py       # MetashapeWorkflow + module-level helpers
├── slots.py                     # GUI slots (MetashapeWorkflowSlots)
├── launcher.py                  # MetashapeWorkflowUI (Switchboard wiring)
├── metashape_workflow_ui.py     # generated from .ui (do not edit)
└── metashape_workflow.ui        # Qt Designer source
```

`FrameExtractor` (generic video → frames helper) lives in
`pythontk.vid_utils.frame_extractor` — see [pythontk's
API_REGISTRY](../../pythontk/API_REGISTRY.md).

## License

MIT. See [LICENSE](../LICENSE).
