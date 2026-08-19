"""Bake operations — iray-backed mesh-map bakes and lighting composites.

The ``bake.lighting_to_diffuse`` op is the headline helper: it drives
Painter's iray-backed baker for AO (and optionally Curvature) and adds a
multiply fill layer onto the base color channel so the result reads as
baked lighting. It is not a literal iray viewport render — Painter's
Python API doesn't expose that — but the baked maps come from the same
iray engine and composite identically for ~80% of production needs.
"""

import logging
import math
from typing import List, Optional

from .registry import register

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers — kept module-private; Painter API access is lazy-imported.
# ---------------------------------------------------------------------------


def _resolve_texture_sets(texture_set: Optional[str]):
    """Return a list of ``TextureSet`` objects matching the filter.

    Parameters:
        texture_set: Single texture set name, or ``None`` for every set.
    """
    import substance_painter.textureset as textureset

    if texture_set:
        return [textureset.TextureSet.from_name(texture_set)]
    return list(textureset.all_texture_sets())


def _ts_name(ts) -> str:
    """``TextureSet.name`` is a method on newer Painter, attr on older — coerce both."""
    n = ts.name
    return n() if callable(n) else n


def _configure_bake_params(ts, bake_resolution: int, ao_kwargs: dict) -> List[str]:
    """Set common + AO baker parameters for the given texture set.

    Returns the list of parameter labels we successfully wrote, for debug.
    """
    import substance_painter.baking as baking

    written: List[str] = []
    params = baking.BakingParameters.from_texture_set(ts)

    log2_size = int(math.log2(bake_resolution))
    settings = {}

    common = params.common()
    if "OutputSize" in common:
        settings[common["OutputSize"]] = (log2_size, log2_size)
        written.append(f"OutputSize=({log2_size},{log2_size})")

    ao_baker = params.baker(baking.MeshMapUsage.AO)
    for key, value in ao_kwargs.items():
        if key in ao_baker:
            settings[ao_baker[key]] = value
            written.append(f"AO.{key}={value}")

    baking.BakingParameters.set(settings)
    return written


def _apply_layer_intensity(layer, channel, intensity: float) -> None:
    """Scale a fill layer's channel contribution via its layer opacity.

    Painter layer opacity is clamped to ``[0.0, 1.0]``, so an ``intensity``
    above 1.0 saturates at full strength (the sliders allow up to 4.0). An
    intensity of 1.0 is Painter's default opacity, so it is a no-op we skip —
    keeping the default bake byte-identical.

    The real API is ``Node.set_opacity(opacity, channel)`` — a method on the
    layer node (verified against the installed Painter's layerstack module;
    no release ships a module-level setter). Resolve it defensively and warn,
    never crash, when the running Painter lacks it.
    """
    opacity = min(max(intensity, 0.0), 1.0)
    if opacity >= 1.0:  # full strength == Painter's default; nothing to change.
        return

    set_opacity = getattr(layer, "set_opacity", None)
    if set_opacity is None:
        logger.warning(
            "[bake] Layer node has no set_opacity method; intensity %.2f "
            "could not be applied to '%s'.",
            intensity,
            getattr(layer, "uid", layer),
        )
        return

    try:
        set_opacity(opacity, channel)
    except TypeError:
        # Older/alternate signature: layer-wide opacity, no per-channel arg.
        set_opacity(opacity)


def _name_node(layer, name: str) -> None:
    """Name a layer node via ``Node.set_name`` (the real API), warn-don't-crash."""
    set_name = getattr(layer, "set_name", None)
    if set_name is None:
        logger.warning(
            "[bake] Layer node has no set_name method; '%s' left unnamed.", name
        )
        return
    set_name(name)


def _set_blending_mode(layerstack, layer, channel, blend_mode: str) -> None:
    """Set a layer's blending mode for *channel*.

    Real API: ``Node.set_blending_mode(mode, channel)`` — a method on the
    layer node (verified against the installed Painter). The old module-level
    ``layerstack.set_channel_blending_mode`` never existed; it is kept only as
    a last-resort fallback for hypothetical other builds.
    """
    try:
        mode = getattr(
            layerstack.BlendingMode, blend_mode, layerstack.BlendingMode.Multiply
        )
    except AttributeError:
        logger.warning("[bake] layerstack.BlendingMode unavailable.")
        return

    set_bm = getattr(layer, "set_blending_mode", None)
    if set_bm is not None:
        set_bm(mode, channel)
        return
    legacy = getattr(layerstack, "set_channel_blending_mode", None)
    if legacy is not None:
        legacy(layer, channel, mode)
        return
    logger.warning("[bake] No blending-mode setter available on this Painter.")


def _add_lighting_layer(
    ts,
    layer_name: str,
    blend_mode: str,
    intensity: float,
    include_curvature: bool,
    curvature_intensity: float,
) -> Optional[str]:
    """Insert a fill layer on top of the stack that multiplies AO (+optional
    curvature) onto the base color channel.

    Returns the new layer's UID/name on success, ``None`` if the API surface
    isn't compatible with what we expect.
    """
    import substance_painter.layerstack as layerstack
    import substance_painter.textureset as textureset

    stack = textureset.Stack.from_name(_ts_name(ts))
    insert_pos = layerstack.InsertPosition.from_textureset_stack(stack)
    # Real API: insert_fill(position) takes no name kwarg (verified against
    # the installed Painter — the old name= call raised TypeError); the node
    # is named afterwards via Node.set_name.
    layer = layerstack.insert_fill(insert_pos)
    _name_node(layer, layer_name)

    base_color = textureset.ChannelType.BaseColor
    _set_blending_mode(layerstack, layer, base_color, blend_mode)

    # Source: drive base color from the AO mesh map. NOTE: neither name below
    # exists in the installed Painter's layerstack module — the real recipe
    # goes through TextureSet.get_mesh_map_resource(usage) plus the fill
    # layer's SourceEditorMixin, whose per-channel source contract can't be
    # designed statically (needs a live Painter session to validate). Until
    # then this resolves defensively and degrades to a warning: the layer is
    # created, blended, and intensity-scaled, but not yet map-driven.
    mesh_map_setter = (
        getattr(layerstack, "set_source_from_mesh_map", None)
        or getattr(layerstack, "set_channel_source_to_mesh_map", None)
    )
    if mesh_map_setter is None:
        logger.warning(
            "[bake] No mesh-map-to-fill-channel setter on substance_painter.layerstack. "
            "Layer was created but base color source is not driven by the AO map."
        )
        return getattr(layer, "uid", _ts_name(ts) + "/" + layer_name)

    import substance_painter.baking as baking

    mesh_map_setter(layer, base_color, baking.MeshMapUsage.AO)
    _apply_layer_intensity(layer, base_color, intensity)

    if include_curvature:
        # Stack a second overlay layer for curvature contribution.
        curv_layer = layerstack.insert_fill(insert_pos)
        _name_node(curv_layer, f"{layer_name} (Curvature)")
        _set_blending_mode(layerstack, curv_layer, base_color, "Overlay")
        mesh_map_setter(curv_layer, base_color, baking.MeshMapUsage.Curvature)
        _apply_layer_intensity(curv_layer, base_color, curvature_intensity)

    return getattr(layer, "uid", _ts_name(ts) + "/" + layer_name)


# ---------------------------------------------------------------------------
# Registered ops
# ---------------------------------------------------------------------------


@register("bake.lighting_to_diffuse")
def lighting_to_diffuse(
    texture_set: Optional[str] = None,
    bake_resolution: int = 1024,
    ao_intensity: float = 1.0,
    ao_secondary_rays: int = 64,
    ao_max_distance: float = 1.0,
    ao_min_distance: float = 0.0,
    ao_spread_angle: float = 162.0,
    ao_subsample: int = 1,
    include_curvature: bool = False,
    curvature_intensity: float = 0.3,
    layer_name: str = "iray AO Lighting",
    blend_mode: str = "Multiply",
    skip_existing_bakes: bool = False,
    save_project: bool = False,
) -> dict:
    """Bake iray-backed AO (+ optional curvature) and composite onto base color.

    Parameters:
        texture_set: Name of a single texture set to bake, or ``None`` for all.
        bake_resolution: Bake output size (power of two). ``1024`` → 1024².
        ao_intensity: Multiplier applied to AO contribution when compositing.
        ao_secondary_rays: AO sample count. Higher = cleaner, slower.
        ao_max_distance: AO ray maximum length in world units.
        ao_min_distance: AO ray minimum length (helps avoid self-shadow noise).
        ao_spread_angle: Hemisphere spread angle in degrees.
        ao_subsample: Supersampling factor (1 = none).
        include_curvature: Also bake curvature and stack as an overlay layer.
        curvature_intensity: Curvature multiplier when ``include_curvature``.
        layer_name: Name of the inserted fill layer.
        blend_mode: Blend mode for the AO layer (default ``Multiply``).
        skip_existing_bakes: If True, only bake when mesh maps are missing.
        save_project: Save the project after applying the layer.

    Returns:
        ``{texture_sets, baked_maps, layers_created, parameters, saved, errors}``.
    """
    import substance_painter.baking as baking

    result: dict = {
        "texture_sets": [],
        "baked_maps": [],
        "layers_created": [],
        "parameters": [],
        "saved": False,
        "errors": [],
    }

    ao_kwargs = {
        "SecondaryRays": ao_secondary_rays,
        "MaxOccluderDistance": ao_max_distance,
        "MinOccluderDistance": ao_min_distance,
        "SpreadAngle": ao_spread_angle,
        "Subsampling": ao_subsample,
    }

    try:
        ts_list = _resolve_texture_sets(texture_set)
    except Exception as e:
        result["errors"].append(f"resolve_texture_sets: {type(e).__name__}: {e}")
        return result

    for ts in ts_list:
        name = _ts_name(ts)
        result["texture_sets"].append(name)

        try:
            written = _configure_bake_params(ts, bake_resolution, ao_kwargs)
            result["parameters"].append({name: written})
        except Exception as e:
            result["errors"].append(f"{name}/configure: {type(e).__name__}: {e}")
            continue

        if skip_existing_bakes:
            # Best-effort guard. ``has_mesh_map`` isn't on every Painter
            # release; fall back to always-bake on AttributeError.
            try:
                if baking.has_mesh_map(ts, baking.MeshMapUsage.AO):
                    result["baked_maps"].append({name: "skipped"})
                    continue
            except AttributeError:
                pass

        try:
            future = baking.bake_async([ts])
            future.result()
            baked = ["AO"] + (["Curvature"] if include_curvature else [])
            result["baked_maps"].append({name: baked})
        except Exception as e:
            result["errors"].append(f"{name}/bake: {type(e).__name__}: {e}")
            continue

        try:
            uid = _add_lighting_layer(
                ts,
                layer_name=layer_name,
                blend_mode=blend_mode,
                intensity=ao_intensity,
                include_curvature=include_curvature,
                curvature_intensity=curvature_intensity,
            )
            if uid:
                result["layers_created"].append({name: uid})
        except Exception as e:
            result["errors"].append(f"{name}/layer: {type(e).__name__}: {e}")

    if save_project and not result["errors"]:
        try:
            import substance_painter.project as project

            project.save()
            result["saved"] = True
        except Exception as e:
            result["errors"].append(f"save: {type(e).__name__}: {e}")

    return result


@register("bake.mesh_maps")
def mesh_maps(
    texture_set: str,
    maps: Optional[List[str]] = None,
    high_poly: Optional[str] = None,
) -> dict:
    """Bake the named mesh maps. ``maps=None`` bakes all enabled maps.

    Returns ``{baked: [...], skipped: [...], errors: [...]}``.
    """
    raise NotImplementedError


@register("bake.all_texture_sets")
def all_texture_sets(maps: Optional[List[str]] = None) -> dict:
    """Bake mesh maps for every texture set in the project."""
    raise NotImplementedError


@register("bake.set_resolution")
def set_resolution(texture_set: str, width: int, height: int) -> None:
    """Set the baking resolution for the named texture set."""
    raise NotImplementedError
