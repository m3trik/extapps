# !/usr/bin/python
# coding=utf-8
"""User-tunable parameters for the standalone Unity Workflow panel.

Only the **Unity-side** (copy-to-Assets + launch) knobs live here — the panel is
driven by an *already-exported* model file, so there are no DCC export params
(scope / triangulate / embed-textures) like the in-DCC ``unity_bridge`` has; the
host that exported the FBX owns those. Read by :class:`unitytk.CopyToAssetsDeliverer`
through :class:`unitytk.FileToUnityBridge`. Nothing is substituted into a template
(the deliverer copies the file), so the panel shows every param (no per-template
gating).

Mirrors the *Unity* section of :mod:`mayatk.env_utils.unity_bridge.parameters`
key-for-key so a preset/value reads the same in both panels.
"""
from __future__ import annotations

from typing import Any

from uitk.bridge import (
    AttributeSpec,
    python_literal,
    referenced_keys as _refkeys,
    defaults as _defaults,
    render_context as _render_context,
)


_FORMATTER = python_literal


# Display order is iteration order over this dict.
PARAMS: "dict[str, AttributeSpec]" = {
    "ASSETS_SUBDIR": AttributeSpec(
        key="ASSETS_SUBDIR",
        label="Assets Subfolder",
        kind="str",
        default="Imported",
        tooltip=(
            "Subfolder under the project's <b>Assets/</b> the model is copied into\n"
            "(created if absent). Blank = drop directly in Assets/."
        ),
    ),
    "ASSET_NAME": AttributeSpec(
        key="ASSET_NAME",
        label="Asset Name",
        kind="str",
        default="",
        tooltip=(
            "Optional name for the copied file (no extension). Blank = use the\n"
            "picked model file's name. Invalid filename characters are sanitized."
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
        tooltip=(
            "Which installed Unity Editor to create/launch with (used by\n"
            "'Launch Editor' and 'New Unity Project…'). Auto uses the newest\n"
            "installed version."
        ),
    ),
}


def referenced_keys(script_text: str) -> "set[str]":
    """Registered keys present in *script_text* (delegates to uitk.bridge)."""
    return _refkeys(script_text, PARAMS)


def defaults() -> "dict[str, Any]":
    """Return ``{key: default}`` for every registered parameter."""
    return _defaults(PARAMS)


def render_context(values: "dict[str, Any]") -> "dict[str, str]":
    """Format *values* for substitution (kept for API parity; Unity renders no script)."""
    return _render_context(values, PARAMS, formatter=_FORMATTER)
