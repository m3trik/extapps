# !/usr/bin/python
# coding=utf-8
"""The Unity Scripts panel's rows.

The **Source** (what a script that takes an asset is given), the **delivery**
(where under ``Assets/`` it lands, by what name) and the built-in scripts'
own rows. A script shows the rows its header names (``__KEY__`` tokens), and
reads their values from its ``ScriptArgs`` by key, so a person's own script
reuses any of these by naming it. The scene's export rows are not declared
here: a host that injects its engine brings them in its own registry
(``engine.params_registry()``: Scope, ...), shown only for the Current Scene
source (``UnityScriptsSlots._adopt_engine``).
"""

from __future__ import annotations

from uitk import AttributeSpec, ParamRegistry


#: The Source row's values: the host scene's Scope, exported (offered only when
#: a host injected its engine), or a model file copied as it is.
SCENE_SOURCE = "scene"
FILE_SOURCE = "file"
#: Their labels; File on Disk is the WebXR Preview's spelling of the same source.
SOURCE_LABELS = {SCENE_SOURCE: "Current Scene", FILE_SOURCE: "File on Disk"}


# Display order is iteration order over this dict.
PARAMS: "dict[str, AttributeSpec]" = {
    # The entries are the panel's (``_adopt_engine``): the sources the selected
    # script takes, Current Scene only with a host; one entry is no choice, so
    # the row hides. A mode, not a setting: never a preset value.
    "SOURCE": AttributeSpec(
        key="SOURCE",
        label="Source",
        kind="choice",
        default=FILE_SOURCE,
        choices=[(SOURCE_LABELS[FILE_SOURCE], FILE_SOURCE)],
        preset=False,
        tooltip=(
            "What the script is given, copied into the project first:\n"
            "• Current Scene — the host scene's Scope, exported by the Scene\n"
            "  Exporter as an FBX carrying the scene's records (lightmaps, shots,\n"
            "  audio, ...), with the Export rows below.\n"
            "• File on Disk — the Model File, copied as it is."
        ),
    ),
    "ASSETS_SUBDIR": AttributeSpec(
        key="ASSETS_SUBDIR",
        label="Assets Subfolder",
        kind="str",
        default="Imported",
        section="Unity",
        tooltip=(
            "The folder under the project's <b>Assets/</b> the script works in: where\n"
            "the Source lands (created if absent). Blank = <i>Imported</i>; <i>/</i> =\n"
            "Assets/ itself."
        ),
    ),
    "ASSET_NAME": AttributeSpec(
        key="ASSET_NAME",
        label="Asset Name",
        kind="str",
        default="",
        section="Unity",
        tooltip=(
            "Optional name for the delivered file (no extension). Blank = the\n"
            "model file's name (the scene: its first object's). A file of the same\n"
            "name is replaced, and its instances follow."
        ),
    ),
    "PLACE_IN_SCENE": AttributeSpec(
        key="PLACE_IN_SCENE",
        label="Place in Scene",
        kind="bool",
        default=True,
        section="Script",
        tooltip=(
            "Add an instance to the open scene when it holds none. A model sent\n"
            "again updates the instances it has, in place."
        ),
    ),
    "FRAME_SELECTION": AttributeSpec(
        key="FRAME_SELECTION",
        label="Frame in Scene View",
        kind="bool",
        default=True,
        section="Script",
        tooltip="Select the model's instance and frame it in the last active Scene view.",
    ),
    "PREFAB_FOLDER": AttributeSpec(
        key="PREFAB_FOLDER",
        label="Prefab Folder",
        kind="str",
        default="Prefabs",
        section="Script",
        tooltip=(
            "The folder under <b>Assets/</b> the prefab variant is saved in\n"
            "(created if absent). One already there is kept, with your overrides."
        ),
    ),
}


class Parameters(ParamRegistry):
    """The Unity Scripts panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

    Handed to the slot as its ``params_module`` (with a host engine, a
    subclass carrying the host's rows too): :data:`PARAMS` plus
    ``referenced_keys`` / ``defaults``.
    """

    PARAMS = PARAMS
