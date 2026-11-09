# !/usr/bin/python
# coding=utf-8
"""The Painter engine as the standalone Substance Scripts panel drives it.

:class:`SubstanceScripts` is the vendored :class:`SubstanceEngine` (kept
byte-identical with the host bridges' copy, so never edited here) with no host:
a script on a mesh runs on a mesh file the panel names (``send(mesh=...)``,
used as it is), so the scene hooks a host bridge fills -- the export, the
selection, the material manifest, the bake source, the scene's record of its
last export -- answer "nothing" here. The panel is this package's (``slots.py``).
"""

import os
from typing import Any, Callable, Dict, List, Optional

from ._substance_engine import _TEMPLATE_DIR, APP, PAINTER_AUTO, SEND_TO, SubstanceEngine


class SubstanceScripts(SubstanceEngine):
    """The Painter engine with no host: its app and template folder on the
    class, and a send on a mesh file or a project."""

    #: The Painter install a send may launch (``APP.not_found_message`` when absent).
    APP = APP
    #: The bundled ``templates/*.py`` scripts.
    TEMPLATE_DIR = _TEMPLATE_DIR
    # Scratch namespace of a send with no Output Dir.
    payload_prefix = "extapps_substance_scripts"
    DEFAULT_FBX_OPTIONS: Dict[str, Any] = {}

    def send(
        self,
        mesh: Optional[str] = None,
        project: Optional[str] = None,
        template: str = "new_project",
        mode: str = SEND_TO,
        target: str = PAINTER_AUTO,
        params: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        painter_exe: Optional[str] = None,
        gui: bool = True,
        hidden: bool = False,
        ctx: Any = None,
        background: Optional[Callable[..., None]] = None,
        on_queued: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run *template* in Painter: on *mesh* (a file, for a script on a
        mesh) or *project* (an ``.spp``; else the Project row's, else the one
        open). *target* is the Painter row; the rest (*background* and
        *on_queued* among them: a panel's send waits off its UI thread) as the
        host bridges' ``send``. The result's ``job`` is the queued script (:meth:`wait`)."""
        return self._handoff(
            [],
            template=template,
            mode=mode,
            target=target,
            params=params,
            legacy_kwargs={},
            mesh=mesh,
            project=project,
            output_dir=output_dir,
            painter_exe=painter_exe,
            gui=gui,
            hidden=hidden,
            ctx=ctx,
            background=background,
            on_queued=on_queued,
        )

    # -- The scene hooks, with no scene ------------------------------------

    def _export_model_fbx(self, path, objects, request, fbx_options) -> None:
        raise RuntimeError("No host to export from: name a mesh file (Mesh File).")

    _export_model_usd = _export_model_fbx

    def _selected_objects(self) -> List[Any]:
        return []

    def _material_manifest(self, objects: List[Any]) -> Dict[str, Any]:
        return {"materials": {}}

    def _assigned_texture_paths(self, objects: List[Any]) -> List[str]:
        return []

    def _export_bake_source(self, fbx_path, fbx_options, referenced, request) -> Optional[str]:
        return None

    @staticmethod
    def _scene_base_name() -> str:
        return "untitled"

    @classmethod
    def _recorded_export_path(cls) -> Optional[str]:
        return None

    @classmethod
    def _record_export_path(cls, fbx_path: str) -> None:
        """No scene to record on: the mesh file is the panel's row."""

    @staticmethod
    def mesh_types() -> List[str]:
        """The mesh files Painter makes a project from, for a file picker."""
        return ["*.fbx", "*.obj", "*.abc", "*.gltf", "*.glb", "*.ply", "*.usd", "*.usda", "*.usdc"]

    @staticmethod
    def is_mesh(path: str) -> bool:
        return bool(path) and os.path.isfile(path) and f"*{os.path.splitext(path)[1].lower()}" in SubstanceScripts.mesh_types()

