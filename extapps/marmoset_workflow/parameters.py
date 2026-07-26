# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the Marmoset Workflow panel.

Each entry maps a placeholder token (e.g. ``__SKY_PRESET__``) to an
``AttributeSpec`` widget spec. ``BridgeSlotsBase`` scans the selected
template for these tokens, shows only the matching widgets, and the slot
passes the collected values to :meth:`MarmosetEngine.send` as a plain
dict (the engine merges them over
:data:`extapps.marmoset_workflow.template_params.DEFAULTS` and substitutes
them into ``templates/*.py``).

This panel is scoped to "open + set up a project" (the ``import`` and
``lookdev`` templates), so it surfaces only the look-dev knobs. The full
bake parameter set lives with the Maya asset-pipeline panel in
:mod:`mayatk.mat_utils.marmoset_bridge.parameters`. Defaults mirror
:data:`extapps.marmoset_workflow.template_params.DEFAULTS` (the local copy
of the engine's token defaults).
"""

from __future__ import annotations

from typing import Any

from uitk.bridge import AttributeSpec, Formatters, Parameters as _BridgeParams


# Targets Python templates -- ``python_literal`` turns user values into
# Python source literals when the engine substitutes them.
_FORMATTER = Formatters.python_literal


# Display order is iteration order over this dict.
PARAMS: "dict[str, AttributeSpec]" = {
    "SKY_PRESET": AttributeSpec(
        key="SKY_PRESET",
        label="Sky",
        kind="choice",
        default="Marmoset Skies/Hangar.tbsky",
        choices=[
            ("Hangar", "Marmoset Skies/Hangar.tbsky"),
            ("Studio Light", "Marmoset Skies/Studio Light.tbsky"),
            ("Sunset", "Marmoset Skies/Sunset.tbsky"),
            ("Overcast", "Marmoset Skies/Overcast.tbsky"),
        ],
        tooltip="Built-in Toolbag sky preset to apply when the scene opens.",
    ),
    "FRAME_SELECTION": AttributeSpec(
        key="FRAME_SELECTION",
        label="Frame on Open",
        kind="bool",
        default=True,
        tooltip="Auto-frame the imported model in the viewport.",
    ),
}


def referenced_keys(script_text: str) -> "set[str]":
    """Registered keys present in *script_text* (delegates to uitk.bridge)."""
    return _BridgeParams.referenced_keys(script_text, PARAMS)


def defaults() -> "dict[str, Any]":
    """Return ``{key: default}`` for every registered parameter."""
    return _BridgeParams.defaults(PARAMS)


def render_context(values: "dict[str, Any]") -> "dict[str, str]":
    """Format *values* for ``StrUtils.replace_delimited`` using Python literals."""
    return _BridgeParams.render_context(values, PARAMS, formatter=_FORMATTER)
