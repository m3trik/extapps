#!/usr/bin/python
# coding=utf-8
import os
from typing import Callable, List, Optional, Sequence, Union

try:
    import Metashape as _Metashape
except ImportError:
    _Metashape = None


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif")


def is_metashape_available() -> bool:
    """True if the Metashape Python module imported successfully."""
    return _Metashape is not None


def is_license_valid() -> bool:
    """True if a valid Metashape license is reachable. Never mutates state."""
    if _Metashape is None:
        return False
    try:
        return bool(_Metashape.license.valid)
    except Exception:
        return False


def get_metashape_version() -> str:
    if _Metashape is None:
        return "n/a"
    try:
        return str(_Metashape.app.version)
    except Exception:
        return "unknown"


class MetashapeWorkflow:
    """Wrapper around Agisoft Metashape's Python API for the standard
    photogrammetry pipeline. Supports a `mock_mode` for dry-runs without a
    valid license, and a `progress` callback for UI integration.
    """

    PROJECT_EXT = "psx"

    def __init__(
        self,
        project_path: str = "./metashape_project",
        name: str = "metashape_project",
        mock_mode: Optional[bool] = None,
        progress: Optional[Callable[[str, float], None]] = None,
    ):
        """
        Parameters:
            project_path: Filesystem directory for the project + outputs.
            name: Project basename (no extension).
            mock_mode: Force-enable mock mode. When None, mock mode is selected
                automatically if Metashape is unavailable or unlicensed.
            progress: Callback `fn(stage: str, fraction: float)` invoked at the
                start of each pipeline stage. `fraction` is in [0, 1].
        """
        self.project_path = project_path
        self.name = name
        self.progress = progress

        if mock_mode is None:
            mock_mode = not (is_metashape_available() and is_license_valid())
        self.mock_mode = bool(mock_mode)

        if self.mock_mode:
            self.doc = None
            self.chunk = None
        else:
            self.doc = _Metashape.Document()
            self.chunk = None

    # ------------------------------------------------------------------ helpers

    def get_license_info(self) -> str:
        if _Metashape is None:
            return "Metashape module not installed"
        return f"Metashape {get_metashape_version()} ({'Licensed' if is_license_valid() else 'No valid license'})"

    def _notify(self, stage: str, fraction: float = 0.0) -> None:
        if self.progress is None:
            return
        try:
            self.progress(stage, float(fraction))
        except Exception as e:
            import sys
            print(f"[MetashapeWorkflow] progress callback raised: {e}", file=sys.stderr)

    def _require_chunk(self) -> None:
        if self.mock_mode:
            return
        if self.chunk is None:
            raise RuntimeError("No chunk. Call create_chunk() first.")

    # ------------------------------------------------------------------ pipeline

    def create_chunk(self, label: str = "New Chunk"):
        self._notify("create_chunk", 0.0)
        if self.mock_mode:
            print(f"[mock] create_chunk('{label}')")
            return
        self.chunk = self.doc.addChunk()
        self.chunk.label = label

    def add_images(self, image_sources: Union[str, Sequence[str]]):
        """Add images from a directory path (non-recursive) or list of paths."""
        self._notify("add_images", 0.0)
        self._require_chunk()

        if isinstance(image_sources, str):
            src_dir = image_sources
            if self.mock_mode:
                print(f"[mock] add_images from '{src_dir}'")
                return
            if not os.path.isdir(src_dir):
                raise ValueError(f"Directory not found: {src_dir}")
            files = [
                os.path.join(src_dir, f)
                for f in sorted(os.listdir(src_dir))
                if f.lower().endswith(IMAGE_EXTS)
            ]
            if not files:
                raise ValueError(f"No images found in directory: {src_dir}")
        else:
            files = list(image_sources)
            if not all(isinstance(p, str) for p in files):
                raise TypeError("image_sources must be a path or list of paths")
            if self.mock_mode:
                print(f"[mock] add_images: {len(files)} file(s)")
                return

        self.chunk.addPhotos(filenames=files)
        print(f"Added {len(files)} images to chunk.")

    def align_photos(
        self,
        downscale: int = 2,
        generic_preselection: bool = False,
        reference_preselection: bool = True,
        keypoint_limit: int = 100000,
        tiepoint_limit: int = 10000,
        filter_mask: bool = False,
    ):
        self._notify("align_photos", 0.0)
        self._require_chunk()
        if self.mock_mode:
            print(f"[mock] align_photos(downscale={downscale})")
            return

        self.chunk.matchPhotos(
            downscale=downscale,
            generic_preselection=generic_preselection,
            reference_preselection=reference_preselection,
            keypoint_limit=keypoint_limit,
            tiepoint_limit=tiepoint_limit,
            filter_mask=filter_mask,
        )
        self.chunk.alignCameras()

        aligned = [c for c in self.chunk.cameras if c.transform is not None]
        if not aligned:
            raise RuntimeError(
                "No cameras aligned. Check image overlap or alignment params."
            )
        print(f"Aligned {len(aligned)}/{len(self.chunk.cameras)} cameras.")

    def generate_depth_maps(self, downscale: int = 2, filter_mode=None):
        self._notify("generate_depth_maps", 0.0)
        self._require_chunk()
        if self.mock_mode:
            print(f"[mock] generate_depth_maps(downscale={downscale})")
            return

        if filter_mode is None:
            filter_mode = _Metashape.MildFiltering

        if not any(c.transform is not None for c in self.chunk.cameras):
            raise RuntimeError("No cameras aligned. Run align_photos() first.")

        self.chunk.buildDepthMaps(
            downscale=downscale, filter_mode=filter_mode, reuse_depth=False
        )
        print("Depth maps generated.")

    def build_model(
        self,
        source_data=None,
        surface_type=None,
        interpolation=None,
        face_count=None,
    ):
        self._notify("build_model", 0.0)
        self._require_chunk()
        if self.mock_mode:
            print("[mock] build_model")
            return

        if source_data is None:
            source_data = _Metashape.DataSource.DepthMapsData
        if surface_type is None:
            surface_type = _Metashape.SurfaceType.Arbitrary
        if interpolation is None:
            interpolation = _Metashape.Interpolation.EnabledInterpolation
        if face_count is None:
            face_count = _Metashape.MediumFaceCount

        if source_data == _Metashape.DataSource.DepthMapsData and not self.chunk.depth_maps:
            raise RuntimeError("Depth maps not found. Run generate_depth_maps() first.")

        self.chunk.buildModel(
            source_data=source_data,
            surface_type=surface_type,
            interpolation=interpolation,
            face_count=face_count,
        )
        print("Model built.")

    def build_texture(
        self,
        texture_size: int = 4096,
        texture_type=None,
        blending_mode=None,
        mapping_mode=None,
        ghosting_filter: bool = True,
    ):
        self._notify("build_texture", 0.0)
        self._require_chunk()
        if self.mock_mode:
            print(f"[mock] build_texture(size={texture_size})")
            return

        if not self.chunk.model:
            raise RuntimeError("No model. Run build_model() first.")

        if texture_type is None:
            texture_type = _Metashape.Model.TextureType.DiffuseMap
        if blending_mode is None:
            blending_mode = _Metashape.BlendingMode.MosaicBlending
        if mapping_mode is None:
            mapping_mode = _Metashape.MappingMode.GenericMapping

        if not getattr(self.chunk.model, "uv_sets", None):
            print("UV mapping missing — generating...")
            self.chunk.buildUV(mapping_mode=mapping_mode)

        self.chunk.buildTexture(
            texture_type=texture_type,
            blending_mode=blending_mode,
            texture_size=texture_size,
            ghosting_filter=ghosting_filter,
        )
        print("Texture built.")

    def save_project(self):
        self._notify("save_project", 0.0)
        if self.mock_mode:
            print("[mock] save_project")
            return

        os.makedirs(self.project_path, exist_ok=True)
        out = os.path.join(self.project_path, f"{self.name}.{self.PROJECT_EXT}")
        self.doc.save(path=out)
        print(f"Saved project: {out}")

    def export_model(
        self,
        export_format=None,
        binary: bool = True,
        precision: int = 6,
        texture_format=None,
        save_texture: bool = True,
        save_normals: bool = True,
        save_colors: bool = True,
        save_cameras: bool = False,
        overwrite: bool = True,
    ):
        self._notify("export_model", 0.0)
        if self.mock_mode:
            print("[mock] export_model")
            return

        if not self.chunk:
            raise RuntimeError("No active chunk.")
        if not self.chunk.model:
            raise RuntimeError("No model. Build the model before exporting.")

        if export_format is None:
            export_format = _Metashape.ModelFormatOBJ
        if texture_format is None:
            texture_format = _Metashape.ImageFormat.ImageFormatPNG

        format_extensions = {
            _Metashape.ModelFormatOBJ: "obj",
            _Metashape.ModelFormatPLY: "ply",
            _Metashape.ModelFormatSTL: "stl",
            _Metashape.ModelFormatFBX: "fbx",
        }
        if export_format not in format_extensions:
            raise ValueError(
                f"Unsupported export format: {export_format}. "
                f"Supported: {list(format_extensions.values())}"
            )

        extension = format_extensions[export_format]
        export_path = os.path.join(self.project_path, f"{self.name}.{extension}")

        if not overwrite and os.path.exists(export_path):
            raise FileExistsError(
                f"'{export_path}' exists. Pass overwrite=True to replace it."
            )

        self.chunk.exportModel(
            path=export_path,
            binary=binary,
            precision=precision,
            texture_format=texture_format,
            save_texture=save_texture,
            save_normals=save_normals,
            save_colors=save_colors,
            save_cameras=save_cameras,
            format=export_format,
        )
        print(f"Exported model: {export_path}")


def get_image_filepaths(directory: str) -> List[str]:
    """Return absolute paths to all images in `directory` (non-recursive)."""
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")
    return [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.lower().endswith(IMAGE_EXTS)
    ]


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    project = "C5_Aileron_Well"
    project_root = (
        f"O:/Dropbox (Moth+Flame)/Moth+Flame Dropbox/Ryan Simpson/_photogrammetry/{project}"
    )
    frames_dir = os.path.join(project_root, "extracted_frames")

    mp = MetashapeWorkflow(project_root, name=project)
    print(mp.get_license_info())
    mp.create_chunk(f"{project} Chunk")
    mp.add_images(frames_dir)
    mp.align_photos(downscale=2)
    mp.generate_depth_maps(downscale=2)
    mp.build_model()
    mp.build_texture()
    mp.save_project()
    mp.export_model()
