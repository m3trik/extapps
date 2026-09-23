# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the WebXR Preview panel.

An ``AttributeSpec`` registry read by :class:`uitk.bridge.BridgeSlotsBase`,
which builds one row per entry, groups them by ``section`` and shows only the
keys the active source declares (:meth:`WebXrPreviewSlots._relevant_param_keys`).

The split that matters here is *export* versus *delivery*. An export param
travels in the bridge's param bag and only means something when a host is
producing the FBX, so it is hidden for a file source, which exports nothing.
A delivery param is answered by the deliverer for every source alike. Keeping
the distinction in the registry rather than in panel branches is what lets one
panel serve a DCC selection and a file on disk without a conditional.

The **Textures** and **Lighting** rows are not this panel's own: they are the
Scene Exporter's rows that decide a GLB deliverable
(:attr:`pythontk.ExportProfile.GLB_ROWS`) -- its images, and the lighting
recipe it publishes -- built from the same tables with the same labels and
defaults, and the push resolves them with the methods the exporters call. Set
them the same in both panels and the GLB texture pass and recipe are the same
in both. The flow is one way: nothing here is read by an export.
"""

from __future__ import annotations

from typing import Any, Dict

import pythontk as ptk
from uitk.bridge import AttributeSpec, Parameters as _BridgeParams


#: Source carriers the preview can build from. ``.fbx`` runs the full
#: conversion; ``.glb`` publishes as authored. Mirrors
#: ``pythontk.FilePreviewBridge.SOURCE_EXTENSIONS`` -- the bridge refuses
#: anything else, and this keeps the refusal out of the file dialog.
SOURCE_FILE_TYPES = ["*.fbx", "*.glb"]


#: Export params: meaningful only when a host is producing the export. Hidden
#: for the file source, whose "export" already happened.
EXPORT_KEYS = frozenset({"INCLUDE_ANIMATION", "SCENE_SIDECAR"})

#: Params the file source owns and no host scope has.
FILE_KEYS = frozenset({"SOURCE_FILE"})

#: This panel's key for each Scene Exporter GLB row -> the row's own key
#: (the one ``push(glb_options=...)`` takes). Upper-cased, the convention of
#: this registry; derived, so a row added upstream arrives by itself.
GLB_KEYS: Dict[str, str] = {row.upper(): row for row in ptk.ExportProfile.GLB_ROWS}

#: The lighting rows. The recipe they decide rides the scene sidecar's
#: envelope, which only a host push builds, so they are hidden for the file
#: source: there a row would change nothing.
LIGHTING_KEYS = frozenset(
    key for key, row in GLB_KEYS.items() if row in ptk.ExportProfile.GLB_LIGHTING_ROWS
)

#: What each GLB row does, in the preview's words. The rows themselves --
#: labels, choices, order, defaults -- come from the Scene Exporter's tables;
#: only this prose is the panel's own.
_ROW_TOOLTIPS: Dict[str, str] = {
    "texture_file_type": "The Scene Exporter's Texture File Type row, for the "
    "GLB: the container every embedded image is re-encoded to.\n\n"
    f"Original takes the web default ({ptk.MeshConvert.WEB_DELIVERY_FORMAT}), "
    "exactly as an exported GLB does.\n\n"
    "WebP is small on the wire but decodes to plain RGBA on the GPU: a "
    "measured 9.5 MB delivery became roughly 740 MB of video memory with "
    "mipmaps, and on a headset that -- not the download -- caps how large a "
    "scene can be previewed. KTX2 stays block-compressed on the GPU (ASTC on "
    "a standalone headset, BC7 on desktop); it costs encode time and needs "
    "KTX-Software's toktx, which this panel offers to install when it is "
    "missing -- a push never quietly ships WebP instead. KTX2 + PNG/JPEG adds "
    "a standard copy of every map so the GLB also opens in Blender, Unreal or "
    "stock Unity.\n\n"
    "Only the containers a GLB can carry are offered: a scene-side type "
    "(TGA, EXR ...) means the web default inside a GLB anyway.",
    "optimize_textures": "The Scene Exporter's Optimize Textures row, for the "
    "GLB: the longest edge its embedded images keep. Maps smaller than the "
    "ceiling are never grown.\n\n"
    "OFF sets no ceiling: every map keeps its own resolution, as in an "
    "exported GLB, unless Secondary Map Size caps the data maps. A plain "
    "Optimize names no ceiling, so it takes the web "
    f"delivery ceiling ({ptk.MeshConvert.WEB_DELIVERY_MAX_SIZE} px); "
    "Optimize + Max N caps at N.\n\n"
    "Template Budget is not offered: its ceiling comes from the export's "
    "Texture Template row, whose material conversion this push does not run. "
    "Pick that template's ceiling here instead.",
    "secondary_max_size": "The Scene Exporter's Secondary Map Size row: a lower "
    "ceiling for the packed data maps (metallic-roughness and occlusion), "
    "under the one Optimize Textures sets -- and applied with Optimize "
    "Textures OFF too, as a choice of its own. Colour and normal maps keep "
    "the primary ceiling.",
    "uastc_rdo": "The Scene Exporter's KTX2 RDO row: rate-distortion "
    "optimisation for the UASTC encodes (normal and data maps), trading a "
    "controlled quality cost for smaller files at 3-4x the encode time. Only "
    "with a KTX2 texture file type.",
    "baked_reflections": "The Scene Exporter's Baked Reflections row: how "
    "strongly a lightmapped material reflects the page's environment. The "
    "bake already holds its diffuse light, so a baked material takes only the "
    "environment's specular, at this level.\n\n"
    "The environment is a bright studio, not the room the bake lit: at Full "
    "its reflections lift every dark glossy baked surface (measured on a "
    "production room, the darkest read 0.06 of display baked alone, 0.22 at "
    "Full, 0.11 at Quarter). Off shows the pure bake.\n\n"
    "Published in the GLB's lighting recipe, where the page reads it -- set it "
    "as the export is set and the preview lights the bake the way the "
    "deliverable will be lit. Rides the scene sidecar, so it needs Scene "
    "Sidecar on.",
}


def _glb_rows(rows: Dict[str, str], section: str) -> "dict[str, AttributeSpec]":
    """One choice row per Scene Exporter GLB row in *rows*, from its own table.

    Each starts where the Scene Exporter starts it
    (:meth:`pythontk.ExportProfile.glb_defaults`), so an untouched panel runs
    the texture pass an untouched export runs and publishes the same recipe.
    """
    options = ptk.ExportProfile.glb_options()
    defaults = ptk.ExportProfile.glb_defaults()
    return {
        key: AttributeSpec(
            key=key,
            label=ptk.ExportProfile.GLB_ROWS[row],
            kind="choice",
            default=defaults[row],
            choices=list(options[row].items()),
            section=section,
            tooltip=_ROW_TOOLTIPS[row],
        )
        for key, row in GLB_KEYS.items()
        if row in rows
    }


# Display order is iteration order over this dict.
PARAMS: "dict[str, AttributeSpec]" = {
    "SOURCE_FILE": AttributeSpec(
        key="SOURCE_FILE",
        label="Source File",
        kind="file",
        default="",
        choices=SOURCE_FILE_TYPES,
        section="Source",
        # An empty field is the ordinary first state, and it is not idle:
        # pushing from it asks. Saying so on the row is what makes the empty
        # panel usable without reading a tooltip to find that out.
        placeholder="Leave empty and Push will ask for a file",
        tooltip="The file to preview.\n\n"
        "An FBX runs the full build -- conversion, lightmaps, texture pass -- "
        "so what you see is what a target platform would receive.\n\n"
        "A GLB is published exactly as authored: no re-encode, no sidecar, no "
        "lightmap rewiring. Those passes exist to repair what an FBX "
        "translation loses, and a finished GLB has already answered them. "
        "That makes this a plain viewer too -- open a vendor's asset, or "
        "re-open the GLB an exporter just wrote, on the same page and port a "
        "scene push uses.\n\n"
        "A lightmap manifest's maps are resolved against this file's own "
        "folder, so a bake that travelled with its asset needs nothing else.",
    ),
    "INCLUDE_ANIMATION": AttributeSpec(
        key="INCLUDE_ANIMATION",
        label="Include Animation",
        kind="bool",
        default=False,
        section="Delivery",
        tooltip="Bake the scene's animation into the pushed GLB so the preview "
        "can play it. The page grows a clip picker and transport, and an "
        "Export Playblast button that records the selected clip -- or the "
        "whole shot sequence -- to a movie beside the deliverable.\n\n"
        "Off by default because baking samples every frame of the scene range, "
        "which costs push time and file size on a scene you are previewing for "
        "its look. A scene with shots declared ships its takes either way.",
    ),
    "SCENE_SIDECAR": AttributeSpec(
        key="SCENE_SIDECAR",
        label="Scene Sidecar",
        kind="bool",
        default=True,
        section="Delivery",
        tooltip="Carry extended scene setup the FBX cannot express, applied to "
        "the preview after conversion.\n\n"
        "Uncheck to preview exactly what the FBX itself carried -- the way to "
        "tell something the exporter dropped from something it mistranslated.",
    ),
    "EMBED_TEXTURES": AttributeSpec(
        key="EMBED_TEXTURES",
        label="Include Textures",
        kind="bool",
        default=True,
        section="Textures",
        tooltip="Embed textures in the published GLB, at the container and "
        "size the rows below set.\n\n"
        "Unchecked is much smaller over the wire and skips the texture passes, "
        "but the preview shows flat materials -- and it is not much faster: "
        "the conversion's cost is the animation it bakes over every node, not "
        "the images. Measured on a production assembly, a 12 MB textureless "
        "export converted in the same minutes as the 366 MB one.",
    ),
    **_glb_rows(ptk.ExportProfile.GLB_TEXTURE_ROWS, "Textures"),
    **_glb_rows(ptk.ExportProfile.GLB_LIGHTING_ROWS, "Lighting"),
    "VIEWER_SCRIPTS": AttributeSpec(
        key="VIEWER_SCRIPTS",
        label="Viewer Scripts",
        kind="check_list",
        default=[],
        # A registry rather than a branch: a script added to pythontk's
        # ``PreviewServer.SCRIPTS`` becomes a row here by ONE entry, tooltip
        # included, so an addition cannot forget a second table.
        choices=[
            (
                "Turntable",
                "turntable",
                "Rotate the model hands-free in the page. Lives on the pivot, "
                "so it survives a push -- the model swaps underneath it and "
                "keeps turning.",
            ),
            (
                "Inspect",
                "inspect",
                "Overlay draw calls, material count and DECODED texture "
                "memory, read off the renderer. The last of those is the "
                "number a GLB's file size does not tell you, and the one that "
                "decides whether this scene needs a KTX2 texture file type.",
            ),
            (
                "Export Image",
                "snapshot",
                "An Export Image button in the page: saves the current view -- "
                "the camera where you left it, the pose on screen -- as a PNG, "
                "at the view's own size or rendered at 1080p / 1440p / 4K. The "
                "page's overlays are not in it.\n\n"
                "Lands beside the source file when there is one on disk, as "
                "<file>_view_001.png and up; a scene push has none, so the "
                "page downloads it instead.",
            ),
        ],
        section="Viewer",
        tooltip="ES modules the page imports on demand. These change the page "
        "looking at the asset, not the asset itself, so they apply to every "
        "source alike.\n\n"
        "The panel is authoritative: unticking a box turns that script off on "
        "the next push.",
    ),
}


def defaults() -> "dict[str, Any]":
    """Return ``{key: default}`` for every registered parameter."""
    return _BridgeParams.defaults(PARAMS)
