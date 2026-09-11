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
"""

from __future__ import annotations

from typing import Any

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
    "EMBED_TEXTURES": AttributeSpec(
        key="EMBED_TEXTURES",
        label="Include Textures",
        kind="bool",
        default=True,
        section="Delivery",
        tooltip="Embed textures in the published GLB, downsized to the web "
        "delivery ceiling first.\n\n"
        "Unchecked is much smaller over the wire and skips the texture passes, "
        "but the preview shows flat materials -- and it is not much faster: "
        "the conversion's cost is the animation it bakes over every node, not "
        "the images. Measured on a production assembly, a 12 MB textureless "
        "export converted in the same minutes as the 366 MB one.",
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
    "TEXTURE_FORMAT": AttributeSpec(
        key="TEXTURE_FORMAT",
        label="Texture Format",
        kind="choice",
        default="WEBP",
        # WebP first: it is the deliverer's own default and the one that needs
        # no external tool.
        choices=[
            ("WebP", "WEBP"),
            ("KTX2 (GPU compressed)", "KTX2"),
        ],
        section="Delivery",
        tooltip="Container the textures are re-encoded to for delivery.\n\n"
        "WebP is small on the wire but decodes to plain RGBA on the GPU: a "
        "measured 9.5 MB delivery became roughly 740 MB of video memory with "
        "mipmaps, and on a headset that -- not the download -- is what caps "
        "how large a scene can be previewed.\n\n"
        "KTX2 stays block-compressed on the GPU (transcoded to ASTC on a "
        "standalone headset, BC7 on desktop). It costs encode time on the push "
        "and needs KTX-Software's toktx, which this panel offers to install "
        "when it is missing -- a push never quietly ships WebP instead.",
    ),
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
                "decides whether this scene needs the KTX2 format above.",
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
