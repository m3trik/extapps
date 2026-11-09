# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the Marmoset Scripts panel.

Each entry maps a placeholder token (e.g. ``__SKY_PRESET__``) to an
``AttributeSpec`` widget spec. ``ParamPanelSlots`` scans the selected
script for these tokens, shows only the matching widgets, and the slot
passes the collected values to :meth:`MarmosetEngine.send` as a plain
dict (the engine merges them over its ``template_params.DEFAULTS`` and
substitutes them into the script). A person's own script shows these rows
by naming their tokens.

The panel runs scripts on a model file, so it surfaces the look-dev knobs the
bundled ``import`` and ``lookdev`` read. The bake parameter set lives with the
host Marmoset Bridge, whose bake reads a scene's Bake Source. Defaults mirror
the engine's token defaults (``template_params.py`` beside this module).
"""

from __future__ import annotations

from uitk import AttributeSpec, ParamRegistry


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


class Parameters(ParamRegistry):
    """The Marmoset Scripts panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

    Handed to the slot as its ``params_module``: :data:`PARAMS` plus
    ``referenced_keys`` / ``defaults`` / ``render_context`` (Python literals).
    """

    PARAMS = PARAMS
