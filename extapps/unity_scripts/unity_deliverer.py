# !/usr/bin/python
# coding=utf-8
"""Unity Scripts' delivery and its scripts: a file copied into a project's
``Assets/``, then the chosen script run on it in Unity.

A script is a C# editor script (``templates/*.cs``, or the person's own in
``ptk.ScriptTemplate.user_dir("unity")``, which shadows a built-in of its
name), its class named as its file, with a header the panel reads without
compiling it::

    // Send to Unity: import the delivered model and show it in the open scene.
    // SOURCES = ("scene", "file")
    // Rows: __ASSETS_SUBDIR__ __PLACE_IN_SCENE__

The first line is its description; ``SOURCES`` says what it takes (``scene``:
a host's export, ``file``: a model file; ``()``: it runs on the project
alone); each ``__KEY__`` token shows that row, whose value the script reads
from its ``ScriptArgs``. The text runs as written (nothing is substituted), so
a script compiles once per project, not on every run.

:class:`UnityDeliverer` is pythontk's :class:`~pythontk.FolderDeliverer`
shaped for Unity (the project's ``Assets/``, the ``Imported`` subfolder by
default, the panel's keys), then hands the script to the project's
:class:`~extapps.unity_scripts.unity_connection.UnityConnection` when Unity
serves it; otherwise the copy alone is the hand-off (Unity imports it on its
next focus). Qt-free and host-free: the panel and a host's export bridge share
it. Nothing here knows what reads the delivered file once it landed.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pythontk as ptk

from .unity_connection import UnityConnection

_PKG_DIR = Path(__file__).resolve().parent


class UnityDeliverer(ptk.FolderDeliverer):
    """Copy into ``<project>/Assets/<subfolder>/``, then run the request's script.

    The project is the bridge's ``target_folder`` (the file bridge's) or its
    ``project_path`` (a host's export bridge); the script is the request's
    ``template``.
    """

    DEFAULT_SUBDIR = "Imported"
    SUBDIR_PARAM = "ASSETS_SUBDIR"
    NAME_PARAM = "ASSET_NAME"

    #: The bundled scripts.
    TEMPLATE_DIR = _PKG_DIR / "templates"
    #: The person's own scripts' folder: ``ptk.ScriptTemplate.user_dir(SCRIPTS_APP)``.
    SCRIPTS_APP = "unity"
    TEMPLATE_EXTENSION = ".cs"
    #: The header's declaration, read as ``ptk.ScriptTemplate`` reads a field. (A
    #: script runs one way, in the open editor, so it declares no modes.)
    SOURCES_FIELD = "// SOURCES"
    #: A script's sources: a host's export, a model file.
    SCENE, FILE = "scene", "file"
    #: What a script without a ``SOURCES`` line takes.
    DEFAULT_SOURCES = (SCENE, FILE)

    def __init__(self):
        # An FBX lands carrying the files its records name (lightmaps, shadow
        # maps), which a reader finds only beside the model.
        super().__init__(embed=ptk.FbxMedia.embed_dependencies)

    # ------------------------------------------------------------------ the scripts
    @classmethod
    def template_dirs(cls) -> Tuple[Path, ...]:
        """Where a script name resolves, first match winning: the person's own
        Unity scripts, then the bundled ``templates/``."""
        return ptk.ScriptTemplate.search_dirs(cls.TEMPLATE_DIR, cls.SCRIPTS_APP)

    @classmethod
    def template_path(cls, script: str) -> Path:
        """The file *script* runs from (:meth:`template_dirs`); a name found
        nowhere names the bundled path, which is then not a file."""
        found = ptk.ScriptTemplate.find(cls.template_dirs(), script, cls.TEMPLATE_EXTENSION)
        return found or cls.TEMPLATE_DIR / f"{script}{cls.TEMPLATE_EXTENSION}"

    @classmethod
    def list_template_modes(cls) -> List[Tuple[str, str]]:
        """``[(script, ""), ...]``: every script, the person's own first by name."""
        return [
            (path.stem, "")
            for path in ptk.ScriptTemplate.list_templates(cls.template_dirs(), cls.TEMPLATE_EXTENSION)
        ]

    @classmethod
    def sources(cls, script: str) -> Tuple[str, ...]:
        """What *script* takes (:attr:`SCENE`, :attr:`FILE`); ``()`` for one that
        runs on the project alone. A script declaring none takes both."""
        declared = ptk.ScriptTemplate.declared_values(cls.template_path(script), cls.SOURCES_FIELD)
        if declared is None:
            return cls.DEFAULT_SOURCES
        return tuple(s for s in declared if s in cls.DEFAULT_SOURCES)

    @staticmethod
    def label(script: str) -> str:
        """*script*'s name as the panel lists it: ``SendToUnity`` -> ``Send to Unity``."""
        words = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", script) or [script]
        small = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
        return " ".join(
            w if i == 0 else (w.lower() if w.lower() in small else w) for i, w in enumerate(words)
        )

    # ------------------------------------------------------------------ the delivery
    @staticmethod
    def project(bridge: Any) -> Optional[str]:
        """The bridge's Unity project folder, or ``None``."""
        return getattr(bridge, "target_folder", None) or getattr(bridge, "project_path", None)

    def target(self, bridge: Any) -> Optional[str]:
        """``<project>/Assets`` when the bridge names a Unity project."""
        project = self.project(bridge)
        assets = os.path.join(project, "Assets") if project else None
        return assets if assets and os.path.isdir(assets) else None

    def preflight(self, bridge: Any, request: ptk.HandoffRequest) -> bool:
        """Refuse before the export unless the bridge names a Unity project and
        the request a script that exists."""
        if self.target(bridge) is None:
            bridge.logger.error(
                "Set a valid Unity project (a folder containing an 'Assets/' "
                f"directory). Got: {self.project(bridge)!r}"
            )
            return False
        if not self.template_path(request.template).is_file():
            bridge.logger.error(f"No script '{request.template}' (Refresh the script list).")
            return False
        return True

    def after(self, bridge: Any, result: Dict[str, Any], request: ptk.HandoffRequest) -> Dict[str, Any]:
        """Hand the request's script to Unity, on the file that landed, when Unity
        serves the project (the operation context, ``extras["ctx"]``, asked
        first); else say what the copy alone does."""
        project = self.project(bridge)
        asset = os.path.relpath(result["file"], project).replace("\\", "/")
        job = self.run(bridge, project, request, asset)
        return dict(result, asset=asset, project=project, job=job)

    def run(self, bridge: Any, project: str, request: ptk.HandoffRequest, asset: Optional[str] = None) -> Optional[str]:
        """Queue the request's script in *project*'s Unity, on *asset* (a project
        path) when given. Returns the job's id, or ``None`` when Unity does not
        serve the project (said) or the context declined."""
        connection = UnityConnection(project)
        script = request.template
        if not connection.serving(settle=0.5):
            if asset:
                bridge.logger.info(
                    f"{asset} is in the project: Unity imports it when the project is next open "
                    f"or focused. {self.label(script)} runs with Unity open: {connection.status()}"
                )
            else:
                bridge.logger.warning(f"{self.label(script)} needs Unity: {connection.status()}")
            return None
        ctx = request.get("ctx")
        if ctx is not None and not ctx.should_change(project, f"run {self.label(script)} in Unity"):
            return None
        job = connection.run(str(self.template_path(script)), request.params or {}, asset=asset)
        bridge.logger.info(f"{self.label(script)} queued in Unity.")
        return job
