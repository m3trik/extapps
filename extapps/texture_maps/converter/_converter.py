# !/usr/bin/python
# coding=utf-8
"""The Map Converter's batch engine: plan, name and run one map at a time.

Qt-free on purpose. :class:`~extapps.texture_maps.converter.slots.ConverterSlots`
owns the panel (widgets, scope picker, progress) and HOLDS one of these; it
used to *be* an :class:`pythontk.ImgUtils` and carry this logic inline, which
tied a 1,700-line Qt module to the image engine's surface and left the batch
rules testable only through a built panel. The per-map image work itself stays
upstream (:class:`pythontk.MapOptimizer` / :class:`pythontk.ImgUtils`); what
lives here is the converter's own policy around it -- how the destination and
archive fields resolve, what a rename-mode output is called, which inputs
would collide on one output, and the dry-run report that must agree with the
real run.
"""
import os
import tempfile
from typing import Dict, List, Tuple

from pythontk import (
    FileUtils,
    ImgUtils,
    MapFactory,
    MapOptimizer,
    OutputTemplates,
    StrUtils,
)


class MapConverter:
    """Batch rules of the Map Converter panel (stateless; every method is a
    class-level call, and the panel holds an instance so a test can stand in
    for one step)."""

    @staticmethod
    def resolve_affix(mode: str, modifier: str) -> Tuple[str, str]:
        """Resolve the Affix mode against the modifier text.

        In ``auto`` mode the modifier's own underscore says where it attaches —
        the way the name is typed is already the intent, so it doesn't have to
        be restated on the picker: ``"LD_"`` prefixes, ``"_LD"`` suffixes,
        and an unmarked (or doubly-marked) ``"LD"`` suffixes, matching the
        pre-Auto default.

        Parameters:
            mode (str): "auto", "suffix", or "prefix". Anything else (e.g. a
                stale value) is treated as "auto".
            modifier (str): Raw text from the modifier field.

        Returns:
            tuple: ``(mode, modifier)`` — mode resolved to "prefix"/"suffix",
                modifier stripped of whitespace and its marker underscores.
        """
        text = (modifier or "").strip()
        if mode not in ("prefix", "suffix"):
            # Same underscore rule, already a primitive upstream. Its library
            # default is "prefix" (asset-naming convention); this panel's
            # pre-Auto default was suffix, so an undecidable modifier keeps
            # suffixing rather than silently switching sides.
            mode = StrUtils.infer_affix_mode(text, default="suffix")
        return mode, text.strip("_")

    @staticmethod
    def is_abs_dest(text: str) -> bool:
        """True when *text* names a full destination rather than a subdirectory.

        Deliberately stricter than ``os.path.isabs``, which calls a rooted but
        driveless ``"/new"`` absolute on Windows. These fields have always
        accepted ``"/new/"`` as a typed-with-separators spelling of the
        subdirectory ``"new"``, so a destination counts as absolute only with a
        drive or UNC share (Windows), or a leading ``/`` (POSIX).

        One definition, shared with every other "subdirectory or full path"
        field in the ecosystem (the lightmap bakers' Output Directory among
        them) -- a second copy is a second chance to get the driveless case
        wrong.
        """
        return FileUtils.is_rooted_path(text)

    @classmethod
    def folder_name(cls, text: str) -> str:
        """Normalize a destination field to a subdirectory name or full path.

        A bare entry names a subdirectory of the texture's own folder, so
        leading or trailing separators (typed, or pasted off a path) are
        stripped — ``"/new/"`` and ``"new"`` mean the same folder.

        A full path (see :meth:`is_abs_dest`) is kept intact and normalized:
        it names one shared destination for the whole run, which is how a batch
        spread across several source folders gets collected into a single
        output (or archive) folder — the capability the Material Updater's
        Output / Archive fields carried before optimization consolidated here.
        """
        text = (text or "").strip()
        if cls.is_abs_dest(text):
            return os.path.normpath(text)
        return text.strip("/\\").strip()

    @classmethod
    def output_collisions(cls, paths, file_type, folder, profile=None):
        """``[(name, [path, ...]), ...]`` for inputs resolving to ONE file in *folder*.

        Destination-agnostic on purpose -- ``ConverterSlots.tb000`` asks it twice, once of the
        OUTPUT folder (where a forced container can merge two maps) and once of
        the ARCHIVE folder (where the move keeps each source's own name, so it
        is asked with neither a forced extension nor a profile).

        Same-stem inputs are harmless while each keeps its own extension --
        ``rock_BaseColor.tga`` and ``rock_BaseColor.png`` write two files. A
        format CONVERSION is what merges them: under ``Format: PNG`` both
        resolve to ``rock_BaseColor.png`` and ``optimize_map``'s writer
        defaults to overwriting, so one optimized result is lost while the
        summary still counts two maps. The archive's version of the same thing
        is two identically named sources moved into one shared folder.

        Keyed on the RESOLVED output (destination + stem + target extension)
        rather than on the bare stem, which is what makes refusing safe: a run
        that cannot lose anything is never rejected, so the folders users
        process today keep working. Only the EXTENSION is derived here -- the
        rest of the filename comes from the stem, equal by construction for
        anything that could collide (``resolve_map_type(key=False)`` keeps the
        source's own spelling, so ``rock_Diffuse`` and ``rock_BaseColor`` stay
        apart), and re-deriving the whole name would duplicate
        ``optimize_map``'s naming and drift from it.

        *profile* is load-bearing, not optional detail. Choosing a workflow
        target leaves the Format field on its sentinel, so ``file_type`` is
        empty and the PROFILE decides the container per map type -- and every
        built-in profile names a concrete one (png, or tga for Unreal). Reading
        only ``file_type`` would let each source keep its own extension here
        and miss exactly the merge this guard exists for, with nothing in the
        Format field to hint at why.

        Parameters:
            paths: The inputs about to be processed.
            file_type: A container the UI forces on every map, or ``""``.
            folder: The destination field to resolve against, per
                :meth:`resolve_dest` (bare name = per texture, full path =
                shared by the run, empty = each source's own directory).
            profile: The active workflow target, consulted only when
                *file_type* is empty.
        """
        by_output: Dict[Tuple[str, str, str], Tuple[str, List[str]]] = {}
        for path in paths:
            dest = cls.resolve_dest(os.path.dirname(path), folder)
            stem = FileUtils.format_path(path, "name")
            out_ext = (file_type or "").lower().lstrip(".")
            if not out_ext and profile:
                spec = OutputTemplates.resolve(
                    MapFactory.resolve_map_type(path, key=True), profile
                )
                out_ext = (spec.ext or "").lower().lstrip(".")
            if not out_ext:  # nothing forces a container: each keeps its own
                out_ext = FileUtils.format_path(path, "ext").lower().lstrip(".")
            key = (os.path.normcase(dest), os.path.normcase(stem), out_ext)
            _, hits = by_output.setdefault(key, (f"{stem}.{out_ext}", []))
            hits.append(path)
        return [entry for entry in by_output.values() if len(entry[1]) > 1]

    @classmethod
    def resolve_dest(cls, directory: str, folder: str) -> str:
        """Destination directory for a *folder* field against a texture's *directory*.

        Bare names resolve per texture (a subdirectory of its own folder); full
        paths resolve to themselves, shared by the whole run.
        """
        if not folder:
            return directory
        return folder if cls.is_abs_dest(folder) else os.path.join(directory, folder)

    @classmethod
    def rename_target_path(
        cls, texture_path, *, file_type, mode, modifier, output_dir
    ):
        """Output path for rename mode — modifier between base and map-type suffix.

        Only meaningful with a non-empty *modifier*; without one the filename is
        whatever ``optimize_map`` resolves, which callers read off the run
        itself rather than re-deriving here.
        """
        base_name = ImgUtils.get_base_texture_name(texture_path)
        map_type = MapFactory.resolve_map_type(texture_path, key=False) or ""
        out_ext = (
            (file_type or FileUtils.format_path(texture_path, "ext"))
            .lower()
            .lstrip(".")
        )
        new_base = (
            f"{modifier}_{base_name}" if mode == "prefix" else f"{base_name}_{modifier}"
        )
        out_filename = (
            f"{new_base}_{map_type}.{out_ext}" if map_type else f"{new_base}.{out_ext}"
        )
        return os.path.join(output_dir, out_filename)

    @classmethod
    def optimize_one(
        cls,
        texture_path,
        *,
        file_type,
        max_size,
        secondary_scale,
        mode,
        modifier,
        new_folder,
        old_folder,
        registry,
        dry_run=False,
        output_profile=None,
        enforce_budget=False,
        lossy_quality=None,
        uastc_rdo=None,
        uastc_rdo_dictionary=None,
    ):
        """``ConverterSlots.tb000``'s per-map step — optimize (or, when *dry_run*, assess) one path.

        Returns:
            tuple: ``(size_before, size_after)`` in bytes — either measured
                (real run) or projected (dry run); ``(None, None)`` when the
                sizes couldn't be determined. ``tb000`` totals these.
        """
        print(f"{'Assessing' if dry_run else 'Optimizing'}: {texture_path} ..")

        # Apply the secondary scale to non-critical maps so masks/roughness/
        # etc. shrink relative to base color and normals.
        effective_max_size = max_size
        if max_size and secondary_scale != 1.0:
            map_type_key = MapFactory.resolve_map_type(texture_path, key=True)
            if not registry.is_resolution_critical(map_type_key):
                effective_max_size = max(1, int(max_size * secondary_scale))
                print(
                    f"// Secondary scale {secondary_scale:g}x -> clamp "
                    f"{effective_max_size} ({map_type_key or 'unknown type'})"
                )

        directory = FileUtils.format_path(texture_path, "path")
        # Where this run writes: the texture's own folder, the 'New folder'
        # subdirectory under it, or — for an absolute entry — one shared folder
        # for the whole batch. Resolved once so the real run and the dry run
        # report the same destination.
        output_dir = cls.resolve_dest(directory, new_folder)

        # The target-driven arguments are identical across the dry run and all
        # three write branches below, so they are resolved once — a branch that
        # quietly missed one would make the run disagree with its own preview.
        target_kwargs = {
            "output_profile": output_profile,
            "enforce_budget": enforce_budget,
            "lossy_quality": lossy_quality,
            "uastc_rdo": uastc_rdo,
            "uastc_rdo_dictionary": uastc_rdo_dictionary,
        }

        if dry_run:
            return cls.report_optimize_plan(
                texture_path,
                file_type=file_type,
                max_size=effective_max_size,
                mode=mode,
                modifier=modifier,
                output_dir=output_dir,
                old_folder=old_folder,
                **target_kwargs,
            )

        size_before = (
            os.path.getsize(texture_path) if os.path.isfile(texture_path) else None
        )

        # Branch on the resolved destination, not on whether the field was
        # filled: an absolute 'New folder' can name the texture's OWN folder,
        # and taking the new-folder path there would write over the source and
        # then archive the *optimized* map, leaving nothing behind.
        writes_in_place = os.path.normcase(os.path.normpath(output_dir)) == (
            os.path.normcase(os.path.normpath(directory))
        )

        if not modifier and writes_in_place:
            # Overwrite mode: optimize in place. The write lands on the source,
            # so the original has to be archived *first* — which is exactly what
            # optimize_map's old_files_folder does (relative to the output dir,
            # here the source's own folder).
            optimized_map_path = MapOptimizer.optimize_map(
                texture_path,
                output_type=file_type,
                max_size=effective_max_size,
                old_files_folder=old_folder or None,
                optimize_bit_depth=True,
                **target_kwargs,
            )
        else:
            os.makedirs(output_dir, exist_ok=True)
            if modifier:
                # Rename mode: place the modifier between base name and
                # map-type suffix. optimize_map names its own output, so it
                # writes to a temp dir first; same-drive (inside output_dir)
                # so the final replace is a fast rename that overwrites
                # cleanly on re-run.
                with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
                    temp_result = MapOptimizer.optimize_map(
                        texture_path,
                        output_dir=temp_dir,
                        output_type=file_type,
                        max_size=effective_max_size,
                        optimize_bit_depth=True,
                        **target_kwargs,
                    )
                    # Name the destination AFTER the run, from the extension
                    # optimize_map actually wrote. Deriving it from *file_type*
                    # was a second guess at a decision made elsewhere: an output
                    # profile resolves the container from its own OutputSpec, so
                    # with Format "Original" and a TGA-producing target this
                    # renamed TGA bytes onto a .png name -- a file whose content
                    # and extension disagree.
                    optimized_map_path = cls.rename_target_path(
                        texture_path,
                        file_type=FileUtils.format_path(temp_result, "ext"),
                        mode=mode,
                        modifier=modifier,
                        output_dir=output_dir,
                    )
                    FileUtils.replace_file(temp_result, optimized_map_path)
            else:
                # New folder, original name: a distinct destination (the
                # in-place case branched above), so optimize_map writes
                # straight into it.
                optimized_map_path = MapOptimizer.optimize_map(
                    texture_path,
                    output_dir=output_dir,
                    output_type=file_type,
                    max_size=effective_max_size,
                    optimize_bit_depth=True,
                    **target_kwargs,
                )

            # Archived here rather than by optimize_map, whose old_files_folder
            # is relative to the *output* dir — that would bury the original in
            # the new folder, or in the temp dir where cleanup deletes it.
            if old_folder:
                FileUtils.move_file(
                    texture_path, cls.resolve_dest(directory, old_folder)
                )

        size_after = (
            os.path.getsize(optimized_map_path)
            if os.path.isfile(optimized_map_path)
            else None
        )
        print(
            f"// Result: {optimized_map_path}  "
            f"[{FileUtils.format_bytes_delta(size_before, size_after)}]"
        )
        return size_before, size_after

    @classmethod
    def report_optimize_plan(
        cls,
        texture_path,
        *,
        file_type,
        max_size,
        mode,
        modifier,
        output_dir,
        old_folder,
        output_profile=None,
        enforce_budget=False,
        lossy_quality=None,
        uastc_rdo=None,
        uastc_rdo_dictionary=None,
    ):
        """Print what optimizing *texture_path* would do, touching nothing.

        Backed by :meth:`MapOptimizer.assess` — the read-only twin of
        ``optimize_map`` — so the planned ops reported here are the same ops
        the real run would execute.
        """
        report = MapOptimizer.assess(
            texture_path,
            max_size=max_size,
            optimize_bit_depth=True,
            output_type=file_type,
            predict_size=True,
            output_profile=output_profile,
            enforce_budget=enforce_budget,
            lossy_quality=lossy_quality,
            uastc_rdo=uastc_rdo,
            uastc_rdo_dictionary=uastc_rdo_dictionary,
        )
        if report.get("error"):
            print(f"// {report['error']}")
            return None, None

        current, predicted = report["current"], report["predicted"]
        target = (
            cls.rename_target_path(
                texture_path,
                # Same rule as the real run: the extension comes from what the
                # optimizer resolved (an output profile picks its own
                # container), never from *file_type*. Re-deriving it here made
                # the preview contradict the no-modifier branch beside it.
                file_type=FileUtils.format_path(predicted["path"], "ext"),
                mode=mode,
                modifier=modifier,
                output_dir=output_dir,
            )
            if modifier
            # assess resolves the filename the way optimize_map does; re-root it
            # into the run's output dir so a 'New folder' is reflected.
            else os.path.join(output_dir, os.path.basename(predicted["path"]))
        )

        dims = f"{current['width']}x{current['height']}"
        if (predicted["width"], predicted["height"]) != (
            current["width"],
            current["height"],
        ):
            dims = f"{dims} -> {predicted['width']}x{predicted['height']}"
        depth = current["bit_depth"]
        if predicted["bit_depth"] != depth:
            depth = f"{depth} -> {predicted['bit_depth']}"

        size_before, size_after = current["size_bytes"], predicted["size_bytes"]
        sizes = (
            FileUtils.format_bytes_delta(size_before, size_after)
            if size_after is not None
            else f"{FileUtils.format_bytes(size_before)} -> "
            f"(size unavailable: {predicted.get('size_error', 'unknown')})"
        )

        if not report["recommended"]:
            print("// No changes needed - already optimal for these settings.")
        for reason in report["reasons"]:
            print(f"// {reason}")
        # Warnings are what the run would NOT do (a declined lossy request, an
        # over-budget result) — the half of the preview a caller is most likely
        # to be surprised by later, so it cannot be reasons-only.
        for warning in report.get("warnings", ()):
            print(f"// ! {warning}")
        # Naming what gets clobbered is the main thing a dry run is asked for:
        # with no modifier and no archive folder the source is overwritten,
        # which the (identical) path alone states only implicitly.
        clobbers = os.path.normcase(os.path.normpath(target)) == os.path.normcase(
            os.path.normpath(texture_path)
        )
        note = (
            " (overwrites the original in place)" if clobbers and not old_folder else ""
        )
        print(f"// Would write: {target}{note}  [{dims}, {depth}, {sizes}]")
        if old_folder:
            # A subdirectory reads as "old/"; a full path is shown as typed.
            shown = (
                old_folder if cls.is_abs_dest(old_folder) else f"{old_folder}/"
            )
            print(f"// Would move the original into: {shown}")

        return size_before, size_after

    @classmethod
    def flip_one(cls, path, *, swizzle_map, invert_dests, suffix):
        """``ConverterSlots.tb002``'s per-map step — flip/swizzle one texture path."""
        print(f"Flipping channels: {path} ..")
        # Skip the swizzle for a pure invert so the input's mode is preserved
        # exactly (a grayscale map stays grayscale instead of promoting to RGB).
        image = (
            ImgUtils.swizzle_channels(path, swizzle_map)
            if swizzle_map
            else ImgUtils.ensure_image(path)
        )
        if invert_dests:
            image = ImgUtils.invert_channels(image, invert_dests)

        directory = FileUtils.format_path(path, "path")
        stem = FileUtils.format_path(path, "name")
        ext = FileUtils.format_path(path, "ext").lstrip(".")
        out_name = f"{stem}{suffix}.{ext}" if suffix else f"{stem}.{ext}"
        output_path = os.path.join(directory, out_name)
        ImgUtils.save_image(image, output_path)
        print(f"// Result: {output_path}")
