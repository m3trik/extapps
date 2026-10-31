# !/usr/bin/python
# coding=utf-8
"""User-tunable parameters for the Unity Workflow panel.

The panel's own rows: the **Source** (what Send to Unity copies) and the
**Unity-side** (copy-to-Assets + launch) knobs, read by
:class:`unitytk.CopyToAssetsDeliverer` for every source. The scene's export rows
are not declared here: a host that injects its engine brings them in its own
registry (``engine.params_registry()``: Scope, Include Materials, ...), and the
panel builds them between the Source row and these, shown only for the Current
Scene source (``UnityWorkflowSlots._adopt_engine``). Nothing is substituted into
a template (the deliverer copies the file), so visibility is the panel's
(``_relevant_param_keys``), never a template scan.
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
    # The entries are the panel's (``_adopt_engine``): File on Disk alone, where
    # the row hides -- one entry is no choice -- and Current Scene above it once
    # a host injected its engine. A mode, not a setting: never a preset value,
    # and Reset leaves it.
    "SOURCE": AttributeSpec(
        key="SOURCE",
        label="Source",
        kind="choice",
        default=FILE_SOURCE,
        choices=[(SOURCE_LABELS[FILE_SOURCE], FILE_SOURCE)],
        preset=False,
        tooltip=(
            "What Send to Unity copies into the project:\n"
            "• Current Scene — the host scene's Scope, exported as an FBX that\n"
            "  carries the scene's records (lightmaps, shots, audio, ...), with\n"
            "  the Export rows below.\n"
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
            "Subfolder under the project's <b>Assets/</b> the model is copied into\n"
            "(created if absent). Blank = <i>Imported</i>; <i>/</i> = Assets/ itself."
        ),
    ),
    "ASSET_NAME": AttributeSpec(
        key="ASSET_NAME",
        label="Asset Name",
        kind="str",
        default="",
        section="Unity",
        tooltip=(
            "Optional name for the copied file (no extension). Blank = use the\n"
            "model file's name (the scene: its first object's). Invalid filename\n"
            "characters are sanitized."
        ),
    ),
    "LAUNCH_MODE": AttributeSpec(
        key="LAUNCH_MODE",
        label="Launch Unity",
        kind="choice",
        default="",
        choices=[
            ("Don't launch", ""),
            ("Open Editor", "open"),
            ("Headless (batch)", "headless"),
        ],
        section="Unity",
        tooltip=(
            "What to do after the model is copied:\n"
            "• Don't launch — just copy; Unity imports on its next window focus\n"
            "  (smoothest when the project is already open).\n"
            "• Open Editor — launch a windowed Unity Editor on the project (the\n"
            "  chosen Unity Version, else the newest install).\n"
            "• Headless (batch) — run Unity '-batchmode -quit' to import then exit,\n"
            "  no window. Needs a batch-capable Editor license."
        ),
    ),
    "UNITY_VERSION": AttributeSpec(
        key="UNITY_VERSION",
        label="Unity Version",
        kind="choice",
        default="",
        # Just the auto-default here; the panel appends installed versions
        # discovered at runtime via unitytk.UnityFinder (dynamic).
        choices=[("Auto (newest)", "")],
        section="Unity",
        tooltip=(
            "Which installed Unity Editor to create/launch with (used by\n"
            "Launch Unity's Open Editor and Headless, and 'New Unity Project…').\n"
            "Auto uses the newest installed version."
        ),
    ),
    # Shown only when the 'Manage Unity Scripts' template is selected
    # (the slots' _relevant_param_keys gates it; delivery params hide).
    "SCRIPTS": AttributeSpec(
        key="SCRIPTS",
        label="Scripts",
        kind="check_list",
        # Entries + initial checks are filled at runtime from the installed
        # unitytk release (UnityWorkflowSlots._populate_script_components), the
        # same way UNITY_VERSION is filled from the installed Editors --
        # nothing about the C# set is duplicated here.
        default=[],
        choices=[],
        section="Unity Scripts",
        tooltip=(
            "Which of unitytk's C# scripts the action below applies to — one\n"
            "row per import channel, all checked by default. Right-click for\n"
            "Check All / Uncheck All; hover a row for what it does.\n"
            "The shared core files (the Project Settings ▸ unitytk page and\n"
            "the import gate every controller compiles against) always ride\n"
            "along with an install, and leave with the last script removed."
        ),
    ),
    "SCRIPTS_ACTION": AttributeSpec(
        key="SCRIPTS_ACTION",
        label="Action",
        kind="choice",
        default="status",
        choices=[
            ("Status", "status"),
            ("Install / Update", "install"),
            ("Uninstall", "uninstall"),
        ],
        section="Unity Scripts",
        tooltip=(
            "What to do with the scripts checked above, in the Unity project\n"
            "field (the embedded Packages/com.m3trik.unitytk package):\n"
            "• Status — report the deployed version vs this unitytk release,\n"
            "  and which scripts are in the project. Ignores the checkboxes.\n"
            "• Install / Update — deploy the checked scripts (updates in\n"
            "  place, leaves unchecked ones alone; configure per-channel\n"
            "  behavior in Unity under Project Settings ▸ unitytk).\n"
            "• Uninstall — remove the checked scripts. Removing the last one\n"
            "  takes the whole package folder with it."
        ),
    ),
}


class Parameters(ParamRegistry):
    """The Unity Workflow panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

    Handed to the slot as its ``params_module`` (with a host engine, a
    subclass carrying the host's rows too): :data:`PARAMS` plus
    ``referenced_keys`` / ``defaults``.
    """

    PARAMS = PARAMS
