# !/usr/bin/python
# coding=utf-8
"""Map Converter UI — slot file for ``converter.ui``.

Bundles texture-map conversion, channel packing, PBR-workflow prep, and bulk
optimization into a single Switchboard panel. The heavy lifting lives in
``MapFactory`` / ``ImgUtils`` (in pythontk) — this module is the UI wiring only.

This module exposes :class:`ConverterSlots` — the Switchboard slot class.
Method names map to widget ``objectName`` in the .ui file: ``tb*`` =
toolbutton (has an options menu populated by the matching ``*_init`` hook),
``b*`` = plain button. Host integrations can inject a ``texture_provider``
callable to read the DCC selection.

The standalone launcher :class:`ConverterUI` lives in the sibling
:mod:`extapps.texture_maps.converter.launcher` module.
"""
import os
import tempfile
from typing import Callable, Dict, Iterable, List, Optional, Tuple

# From this package:
from pythontk.img_utils._img_utils import ImgUtils
from pythontk.core_utils.engines.textures.map_factory import MapFactory
from pythontk.core_utils.engines.textures.map_registry import MapRegistry
from pythontk.core_utils.engines.textures.map_optimizer import MapOptimizer
from pythontk.file_utils._file_utils import FileUtils

class ConverterSlots(ImgUtils):
    """Switchboard slots for ``converter.ui``.

    Slot methods are bound to widgets by name. The ``Scope`` combobox in the
    header menu (installed by :meth:`header_init`) decides where *every* tool
    reads its texture paths from: the built-in :attr:`BROWSE_SCOPE` opens a
    file dialog, and any host-registered scope calls that host's provider.
    Set :attr:`source_dir` to seed the initial dialog directory.
    """

    #: Built-in scope — always present, always first, never host-provided.
    #: ASCII on purpose: scope labels get interpolated into ``print`` output,
    #: and a cp1252 console raises UnicodeEncodeError on a stray "…".
    BROWSE_SCOPE = "Browse..."

    def __init__(self, switchboard, **kwargs):
        super().__init__()

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.converter

        self._source_dir = kwargs.get("source_dir", "")
        # Insertion-ordered label -> provider. Excludes BROWSE_SCOPE, whose
        # "provider" is the file dialog (a None lookup in _get_texture_paths).
        self._scopes: Dict[str, Callable[[], Iterable[str]]] = {}
        # Scope a host asked to activate before the combobox existed. Hosts
        # register right after launch(show=False) and the header menu may not
        # be built until first show, so the request has to survive the gap.
        self._pending_scope: Optional[str] = None

        provider = kwargs.get("texture_provider", None)
        if provider:
            self.texture_provider = provider

    @property
    def source_dir(self):
        """Get the starting directory for file dialogs."""
        return self._source_dir

    @source_dir.setter
    def source_dir(self, value):
        """Set the starting directory for file dialogs."""
        self._source_dir = value

    # -------------------------------------------------------------------------
    # Scopes — where tools read their texture paths from
    # -------------------------------------------------------------------------

    @property
    def scopes(self) -> Tuple[str, ...]:
        """Scope labels currently offered, in combobox order.

        Always starts with :attr:`BROWSE_SCOPE`; the rest are whatever the
        host registered via :meth:`register_scope`. This is why the panel can
        stay app-agnostic — it owns the *mechanism* (a scope picker) and the
        host owns the *policy* (what "Selected Materials" means here).
        """
        return (self.BROWSE_SCOPE, *self._scopes)

    def register_scope(
        self,
        label: str,
        provider: Callable[[], Iterable[str]],
        *,
        select: bool = False,
    ) -> None:
        """Offer *label* in the Scope combobox, resolved by calling *provider*.

        Parameters:
            label (str): Combobox entry, e.g. "Selected Objects". Re-registering
                a label replaces its provider and keeps its position.
            provider (callable): ``() -> Iterable[str]`` returning texture file
                paths. Called fresh on every tool invocation, so it always sees
                the host's *current* selection. May open its own dialog (that's
                how a "Choose Materials…" scope is built).
            select (bool): Make this the active scope once registered.

        Hosts call this right after launching the panel — see the Maya
        integration in ``tentacle.slots.maya.materials.b016``.
        """
        if not callable(provider):
            raise TypeError(
                f"Scope {label!r} needs a callable provider, got {type(provider)}."
            )
        if label == self.BROWSE_SCOPE:
            # Shadowing it would leave two identically-labelled entries and
            # route the built-in one to the host, so 'Browse' would silently
            # stop opening the file dialog.
            raise ValueError(f"{label!r} is the built-in browse scope; pick another label.")
        self._scopes[label] = provider
        if select:
            self._pending_scope = label
        self._refresh_scope_combo()

    def unregister_scope(self, label: str) -> None:
        """Drop a previously registered scope (no-op if it isn't registered)."""
        if self._scopes.pop(label, None) is not None:
            self._refresh_scope_combo()

    @property
    def texture_provider(self) -> Optional[Callable[[], Iterable[str]]]:
        """Provider for the plain "Selected" scope.

        Back-compatible shorthand for hosts that only supply one selection
        source: setting it registers (or, when set to None, removes) a single
        "Selected" scope. Hosts with several selection kinds should call
        :meth:`register_scope` per kind instead.
        """
        return self._scopes.get("Selected")

    @texture_provider.setter
    def texture_provider(self, fn: Optional[Callable[[], Iterable[str]]]) -> None:
        if fn is None:
            self.unregister_scope("Selected")
        else:
            self.register_scope("Selected", fn)

    def header_init(self, widget):
        """Add the global Scope combobox to the header menu."""
        combo = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=(
                "Where every tool on this panel reads its texture paths from.\n"
                f"'{self.BROWSE_SCOPE}' opens a file browser; the remaining "
                "entries are provided by the host application and read its "
                "current selection when the tool runs.\n"
                "Only 'Browse' is available when running standalone."
            ),
        )
        # Populated through the just-created widget rather than a self.ui
        # lookup — during header_init the header isn't necessarily reachable
        # from the loaded ui yet.
        self._refresh_scope_combo(combo=combo)

    def _refresh_scope_combo(self, combo=None) -> None:
        """Rebuild the Scope combobox, keeping the active scope where possible.

        Called whenever the scope set changes — hosts register their scopes
        *after* the UI is built, so the combobox has to repopulate rather than
        being filled once in :meth:`header_init`.
        """
        if combo is None:
            try:
                combo = self.ui.header.menu.cmb_scope
            except (AttributeError, RuntimeError):
                return  # Header menu not built yet; header_init will populate it.

        target = self._pending_scope or self._current_scope()
        labels = self.scopes
        try:
            combo.add(
                [(label, label) for label in labels],
                prefix="Scope:",
            )
            combo.setCurrentIndex(labels.index(target) if target in labels else 0)
            # Only clear once it actually landed on a live combobox.
            self._pending_scope = None
            # Deliberately not persisted (``add`` turns restore_state back on):
            # the entries past 'Browse' come from whichever host launched the
            # panel, and combo state restores by *index* — a saved index would
            # resolve to a different scope under a different host, silently
            # retargeting which files a tool overwrites.
            combo.restore_state = False
        except (AttributeError, RuntimeError, TypeError):
            pass  # Mocked / torn-down combo — nothing to repopulate.

    def _current_scope(self) -> str:
        """Active scope label, falling back to :attr:`BROWSE_SCOPE`."""
        try:
            scope = self.ui.header.menu.cmb_scope.currentData()
        except (AttributeError, RuntimeError):
            return self.BROWSE_SCOPE
        return scope if scope in self.scopes else self.BROWSE_SCOPE

    def _get_texture_paths(self, *, title, map_type_filter=None, allow_multiple=True):
        """Resolve texture paths for the active scope.

        Parameters:
            title (str): Title shown if the file dialog is used.
            map_type_filter (Iterable[str], optional): When pulling from a host
                scope, restrict to these MapRegistry keys (e.g. ``["Normal",
                "Normal_DirectX"]``). Ignored when the file dialog is used —
                there the filter is the user's own selection.
            allow_multiple (bool): Forwarded to ``file_dialog``.

        Returns:
            List[str]: Existing absolute paths. Empty list when nothing valid.
        """
        scope = self._current_scope()
        provider = self._scopes.get(scope)

        if provider is not None:
            paths = list(provider() or [])
            if map_type_filter:
                wanted = set(map_type_filter)
                kept, dropped = [], []
                for p in paths:
                    key = MapFactory.resolve_map_type(p, key=True)
                    (kept if key in wanted else dropped).append(p)
                if dropped:
                    print(
                        f"// Skipping {len(dropped)} map(s) not in "
                        f"{sorted(wanted)} from '{scope}'."
                    )
                paths = kept
            if not paths:
                print(f"// No matching textures found for scope '{scope}'.")
                return []
        else:
            paths = self.sb.file_dialog(
                file_types=[f"*.{ext}" for ext in self.texture_file_types],
                title=title,
                start_dir=self.source_dir,
                allow_multiple=allow_multiple,
            )
            paths = list(paths or [])

        valid = [p for p in paths if p and os.path.isfile(p)]
        for missing in (p for p in paths if p not in valid):
            print(f"// Skipping (file not found): {missing}")
        return valid

    def tb000_init(self, widget):
        """Populate the Optimize toolbutton's option menu (format, clamp, modifier)."""
        widget.option_box.menu.setTitle("Optimize")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb001",
            setToolTip="Set the output file type. 'Original' keeps each texture's existing format.",
        )
        # Falsy sentinels (empty string / 0) — the prefix-mode combobox
        # replaces explicit None data with the label string, so use values
        # that still evaluate falsy in the ``if not file_type`` / ``if not
        # max_size`` checks below.
        widget.option_box.menu.cmb001.add(
            [("Original", "")] + [(ext.upper(), ext) for ext in self.writable],
            prefix="Format:",
        )

        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip="Maximum dimension (longest side). 'None' disables resizing.",
        )
        widget.option_box.menu.cmb000.add(
            [("None", 0)] + [(s, int(s)) for s in ("256", "512", "1024", "2048", "4096", "8192")],
            prefix="Clamp:",
        )

        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_secondary_scale",
            setToolTip=(
                "Downscale non-critical maps (roughness, metallic, AO, masks, "
                "height, etc.) by this fraction of the clamp. Resolution-critical "
                "maps (base color, normals, emissive) always use the full clamp."
            ),
        )
        widget.option_box.menu.cmb_secondary_scale.add(
            [("Full", 1.0), ("1/2", 0.5), ("1/4", 0.25), ("1/8", 0.125)],
            prefix="Secondary:",
        )

        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_affix",
            setToolTip=(
                "Where the modifier attaches to the base name (either way it "
                "sits before the map-type suffix).\n"
                "Auto: read it off the modifier's own underscore — 'LD_' is a "
                "prefix, '_LD' a suffix, bare 'LD' a suffix.\n"
                "Suffix / Prefix: force one regardless of how it's typed."
            ),
        )
        widget.option_box.menu.cmb_affix.add(
            [("Auto", "auto"), ("Suffix", "suffix"), ("Prefix", "prefix")],
            prefix="Affix:",
        )

        widget.option_box.menu.add(
            "QLineEdit",
            setObjectName="txt_modifier",
            setPlaceholderText="e.g. LD_ or _LD",
            setToolTip=(
                "Text inserted into the base name (before the map-type suffix). "
                "Empty = overwrite the original file.\n"
                "With Affix on Auto, a trailing underscore ('LD_') makes it a "
                "prefix and a leading one ('_LD') a suffix."
            ),
        )

        widget.option_box.menu.add(
            "QLineEdit",
            setObjectName="txt_old_folder",
            setText="old",
            setPlaceholderText="e.g. old",
            setToolTip=(
                "Subdirectory under the texture's folder to move the original into. "
                "Empty = don't move the original."
            ),
        )

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Dry run",
            setObjectName="chk_dry_run",
            setChecked=False,
            setToolTip=(
                "Report what each texture would become — resolution, bit "
                "depth, file size before → after, and the output path — "
                "without writing, overwriting, or archiving anything.\n"
                "The projected size comes from a real encode of the planned "
                "result, so it's the size you'd actually get, not an estimate."
            ),
        )

    def tb000(self, widget):
        """Optimize a texture map(s)"""
        texture_paths = self._get_texture_paths(
            title="Select texture map(s) to optimize:"
        )
        if not texture_paths:
            return

        # Falsy sentinels ("", 0) → None so optimize_map preserves
        # the original format / skips clamping respectively.
        file_type = widget.option_box.menu.cmb001.currentData() or None
        max_size = widget.option_box.menu.cmb000.currentData() or None
        secondary_scale = (
            widget.option_box.menu.cmb_secondary_scale.currentData() or 1.0
        )
        mode, modifier = self.resolve_affix(
            widget.option_box.menu.cmb_affix.currentData(),
            widget.option_box.menu.txt_modifier.text(),
        )
        old_folder = (
            widget.option_box.menu.txt_old_folder.text().strip().strip("/").strip("\\")
        )
        dry_run = widget.option_box.menu.chk_dry_run.isChecked()

        registry = MapRegistry()
        verb = "Assessing" if dry_run else "Optimizing"
        done = "Assessed" if dry_run else "Optimized"
        if dry_run:
            print("// Dry run - no files will be written, moved, or overwritten.")

        total = len(texture_paths)
        saved_before = saved_after = counted = 0
        with self.sb.progress(
            total=total, text=f"{verb} 0/{total}"
        ) as update:
            for i, texture_path in enumerate(texture_paths):
                before, after = self._optimize_one(
                    texture_path,
                    file_type=file_type,
                    max_size=max_size,
                    secondary_scale=secondary_scale,
                    mode=mode,
                    modifier=modifier,
                    old_folder=old_folder,
                    registry=registry,
                    dry_run=dry_run,
                )
                if before is not None and after is not None:
                    saved_before += before
                    saved_after += after
                    counted += 1
                update(
                    i + 1,
                    f"{done} {i + 1}/{total}: {os.path.basename(texture_path)}",
                )

        if saved_before:
            # Count the maps that actually contributed a size, not the whole
            # batch — a total labelled "5 map(s)" that summed 3 of them is a
            # wrong number, and size is the number being trusted here.
            skipped = f" ({total - counted} unmeasured)" if counted < total else ""
            print(
                f"// Total ({counted} map(s)){skipped}: "
                f"{FileUtils.format_bytes_delta(saved_before, saved_after)}"
            )
        self.source_dir = FileUtils.format_path(texture_paths[0], "path")

    @staticmethod
    def resolve_affix(mode: str, modifier: str) -> Tuple[str, str]:
        """Resolve the Affix mode against the modifier text.

        In ``auto`` mode the modifier's own underscore says where it attaches —
        the way the name is typed is already the intent, so it doesn't have to
        be restated in the combobox: ``"LD_"`` prefixes, ``"_LD"`` suffixes,
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
            leads, trails = text.startswith("_"), text.endswith("_")
            mode = "prefix" if (trails and not leads) else "suffix"
        return mode, text.strip("_")

    def _rename_target_path(self, texture_path, *, file_type, mode, modifier):
        """Output path for rename mode — modifier between base and map-type suffix.

        Shared by the real run and the dry run so the reported path is the one
        that would actually be written.
        """
        directory = FileUtils.format_path(texture_path, "path")
        base_name = self.get_base_texture_name(texture_path)
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
        return os.path.join(directory, out_filename)

    def _optimize_one(
        self,
        texture_path,
        *,
        file_type,
        max_size,
        secondary_scale,
        mode,
        modifier,
        old_folder,
        registry,
        dry_run=False,
    ):
        """Helper for ``tb000`` — optimize (or, when *dry_run*, assess) one path.

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

        if dry_run:
            return self._report_optimize_plan(
                texture_path,
                file_type=file_type,
                max_size=effective_max_size,
                mode=mode,
                modifier=modifier,
                old_folder=old_folder,
            )

        size_before = (
            os.path.getsize(texture_path) if os.path.isfile(texture_path) else None
        )

        if not modifier:
            # Overwrite mode: optimize in place. optimize_map handles
            # the optional move-to-old-folder for us.
            optimized_map_path = MapOptimizer.optimize_map(
                texture_path,
                output_type=file_type,
                max_size=effective_max_size,
                old_files_folder=old_folder or None,
                optimize_bit_depth=True,
            )
        else:
            # Rename mode: place the modifier between base name and
            # map-type suffix and save alongside the original.
            target_path = self._rename_target_path(
                texture_path, file_type=file_type, mode=mode, modifier=modifier
            )
            directory = FileUtils.format_path(texture_path, "path")

            # Same-drive temp dir so the final os.replace is a fast rename
            # and overwrites cleanly on re-run. We can't pass
            # old_files_folder here because optimize_map would archive
            # the original into the temp dir and lose it on cleanup.
            with tempfile.TemporaryDirectory(dir=directory) as temp_dir:
                temp_result = MapOptimizer.optimize_map(
                    texture_path,
                    output_dir=temp_dir,
                    output_type=file_type,
                    max_size=effective_max_size,
                    optimize_bit_depth=True,
                )
                os.replace(temp_result, target_path)

            if old_folder:
                FileUtils.move_file(
                    texture_path, os.path.join(directory, old_folder)
                )

            optimized_map_path = target_path

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

    def _report_optimize_plan(
        self,
        texture_path,
        *,
        file_type,
        max_size,
        mode,
        modifier,
        old_folder,
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
        )
        if report.get("error"):
            print(f"// {report['error']}")
            return None, None

        current, predicted = report["current"], report["predicted"]
        target = (
            self._rename_target_path(
                texture_path, file_type=file_type, mode=mode, modifier=modifier
            )
            if modifier
            else predicted["path"]  # assess resolves it the way optimize_map does
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
        # Naming what gets clobbered is the main thing a dry run is asked for:
        # with no modifier and no archive folder the source is overwritten,
        # which the (identical) path alone states only implicitly.
        clobbers = os.path.normcase(os.path.normpath(target)) == os.path.normcase(
            os.path.normpath(texture_path)
        )
        note = " (overwrites the original in place)" if clobbers and not old_folder else ""
        print(f"// Would write: {target}{note}  [{dims}, {depth}, {sizes}]")
        if old_folder:
            print(f"// Would move the original into: {old_folder}/")

        return size_before, size_after

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Spec Gloss to PBR")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Create MetallicSmoothness map",
            setObjectName="chk000",
            setToolTip="Also create a MetallicSmoothness map.",
        )

    def tb001(self, widget):
        """Batch converts Spec/Gloss maps to PBR Metal/Rough using MapFactory.

        User selects multiple texture sets. The function groups them per base name
        and converts them accordingly using the DRY MapFactory.

        Maps are saved as Metallic/Roughness maps in the same directory.
        """
        spec_map_paths = self._get_texture_paths(
            title="Select Specular, Gloss (optional), and Diffuse maps to convert:",
        )
        if not spec_map_paths:
            return

        create_metallic_smoothness = widget.option_box.menu.chk000.isChecked()

        # Use MapFactory for DRY conversion
        workflow_config = {
            "albedo_transparency": False,
            "metallic_smoothness": create_metallic_smoothness,
            "mask_map": False,
            "normal_type": "OpenGL",
            "output_extension": "png",
            "convert_specgloss_to_pbr": True,
        }

        print(f"Processing {len(spec_map_paths)} files...")

        try:
            results = MapFactory.prepare_maps(
                spec_map_paths,
                **workflow_config,
            )

            if isinstance(results, dict):
                print(f"Processed {len(results)} texture sets.")
                for base_name, maps in results.items():
                    print(f"Set: {base_name}")
                    for m in maps:
                        print(f"  - {m}")
            else:
                print("Processed single set.")
                for m in results:
                    print(f"  - {m}")

        except Exception as e:
            print(f"Error during batch processing: {e}")
            import traceback

            traceback.print_exc()

        try:
            self.source_dir = FileUtils.format_path(spec_map_paths[0], "path")
        except Exception:
            pass

    def tb003_init(self, widget):
        """Initialize a 'Bump to Normal' toolbutton with options."""
        widget.option_box.menu.setTitle("Bump to Normal")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="tb003_cmb_format",
            setToolTip="OpenGL: Y+ up, DirectX: Y+ down",
        )
        # Display-friendly items with data values
        cmb = widget.option_box.menu.tb003_cmb_format
        cmb.clear()
        cmb.addItem("Format: OpenGL", "opengl")
        cmb.addItem("Format: DirectX", "directx")

        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="tb003_dsb_intensity",
            setMinimum=0.1,
            setMaximum=5.0,
            setSingleStep=0.1,
            setValue=1.0,
            setDecimals=2,
            setPrefix="Intensity: ",
            setToolTip="Controls how deep the height values are interpreted",
        )

    def tb003(self, widget):
        """Bump/Height to Normal converter (single entry point with options)."""
        bump_map_paths = self._get_texture_paths(
            title="Select bump/height maps to convert:",
            map_type_filter=["Bump", "Height"],
        )
        if not bump_map_paths:
            return

        # Options
        try:
            output_format = (
                widget.option_box.menu.tb003_cmb_format.currentData() or "opengl"
            )
        except Exception:
            fmt_text = widget.option_box.menu.tb003_cmb_format.currentText().lower()
            output_format = "directx" if "directx" in fmt_text else "opengl"
        intensity = widget.option_box.menu.tb003_dsb_intensity.value()

        for bump_path in bump_map_paths:
            print(f"Converting bump to normal ({output_format.upper()}): {bump_path}")

            try:
                normal_path = MapFactory.convert_bump_to_normal(
                    bump_path,
                    output_format=output_format,
                    intensity=intensity,
                    smooth_filter=True,
                    filter_radius=0.5,
                )
                print(f"// Result: {normal_path}")

            except Exception as e:
                print(f"// Error converting {bump_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(bump_map_paths[0], "path")
        except Exception:
            pass

    # Output channel ← source choices for the Flip Channels tool. ``-X`` marks
    # an inverted source; ``0``/``1`` write a constant. Shared by the option-box
    # builder and (implicitly) the dispatch in :meth:`tb002`.
    _FLIP_SOURCES = [
        ("R", "R"),
        ("G", "G"),
        ("B", "B"),
        ("A", "A"),
        ("R (inv)", "-R"),
        ("G (inv)", "-G"),
        ("B (inv)", "-B"),
        ("A (inv)", "-A"),
        ("Black", "0"),
        ("White", "1"),
    ]

    def tb002_init(self, widget):
        """Populate the Flip Channels option menu (per-channel source + suffix)."""
        widget.option_box.menu.setTitle("Flip Channels")

        for idx, channel in enumerate("RGBA"):
            name = f"cmb_{channel.lower()}"
            widget.option_box.menu.add(
                "QComboBox",
                setObjectName=name,
                setToolTip=(
                    f"Source for the output {channel} channel. '(inv)' inverts "
                    "the source; Black/White write a constant. The default "
                    f"keeps the original {channel}."
                ),
            )
            combo = getattr(widget.option_box.menu, name)
            combo.add(self._FLIP_SOURCES, prefix=f"{channel} ← ")
            combo.setCurrentIndex(idx)  # identity default (R←R, G←G, …)

        widget.option_box.menu.add(
            "QLineEdit",
            setObjectName="txt_suffix",
            setPlaceholderText="empty = overwrite",
            setToolTip=(
                "Suffix appended to the base name (before the extension). "
                "Empty overwrites the source file."
            ),
        )

    def tb002(self, widget):
        """Flip/swizzle texture channels (per-channel invert, swap, or constant fill).

        Each output channel pulls from a chosen source via
        :meth:`ImgUtils.swizzle_channels`; the ``-`` (inverted) sources are
        applied afterward with :meth:`ImgUtils.invert_channels`, keeping both
        primitives pure and composable.
        """
        texture_paths = self._get_texture_paths(
            title="Select texture map(s) to flip/swizzle:",
        )
        if not texture_paths:
            return

        menu = widget.option_box.menu
        tokens = {
            channel: getattr(menu, f"cmb_{channel.lower()}").currentData()
            for channel in "RGBA"
        }
        suffix = menu.txt_suffix.text().strip()

        # Each token is a swizzle source, optionally inverted (the ``-`` prefix).
        # Only *non-identity* sources enter the swizzle map — so an untouched
        # ``A`` slot doesn't force an alpha channel onto an RGB image, and a
        # pure invert leaves the map empty (skipping the RGBA promotion below).
        # Inverts ride separately so the two pure primitives compose.
        swizzle_map = {}
        invert_dests = ""
        for dest, token in tokens.items():
            if token.startswith("-"):
                invert_dests += dest
            source = token.lstrip("-").upper()
            if source != dest:
                swizzle_map[dest] = source

        if not swizzle_map and not invert_dests and not suffix:
            print("// Flip Channels: identity selection, nothing to do.")
            return

        total = len(texture_paths)
        with self.sb.progress(total=total, text=f"Flipping 0/{total}") as update:
            for i, path in enumerate(texture_paths):
                self._flip_one(
                    path,
                    swizzle_map=swizzle_map,
                    invert_dests=invert_dests,
                    suffix=suffix,
                )
                update(
                    i + 1, f"Flipped {i + 1}/{total}: {os.path.basename(path)}"
                )

        self.source_dir = FileUtils.format_path(texture_paths[0], "path")

    def _flip_one(self, path, *, swizzle_map, invert_dests, suffix):
        """Helper for ``tb002`` — flip/swizzle one texture path."""
        print(f"Flipping channels: {path} ..")
        # Skip the swizzle for a pure invert so the input's mode is preserved
        # exactly (a grayscale map stays grayscale instead of promoting to RGB).
        image = (
            self.swizzle_channels(path, swizzle_map)
            if swizzle_map
            else self.ensure_image(path)
        )
        if invert_dests:
            image = self.invert_channels(image, invert_dests)

        directory = FileUtils.format_path(path, "path")
        stem = FileUtils.format_path(path, "name")
        ext = FileUtils.format_path(path, "ext").lstrip(".")
        out_name = f"{stem}{suffix}.{ext}" if suffix else f"{stem}.{ext}"
        output_path = os.path.join(directory, out_name)
        self.save_image(image, output_path)
        print(f"// Result: {output_path}")

    def b000(self):
        """Convert DirectX to OpenGL"""
        dx_map_paths = self._get_texture_paths(
            title="Select a DirectX normal map to convert:",
            map_type_filter=["Normal", "Normal_DirectX"],
        )
        if not dx_map_paths:
            return

        for dx_map_path in dx_map_paths:
            print(f"Converting: {dx_map_path} ..")
            gl_map_path = MapFactory.convert_normal_map_format(
                dx_map_path, target_format="opengl"
            )
            print(f"// Result: {gl_map_path}")
        self.source_dir = FileUtils.format_path(dx_map_paths[0], "path")

    def b001(self):
        """Convert OpenGL to DirectX"""
        gl_map_paths = self._get_texture_paths(
            title="Select an OpenGL normal map to convert:",
            map_type_filter=["Normal", "Normal_OpenGL"],
        )
        if not gl_map_paths:
            return

        for gl_map_path in gl_map_paths:
            print(f"Converting: {gl_map_path} ..")
            dx_map_path = MapFactory.convert_normal_map_format(
                gl_map_path, target_format="directx"
            )
            print(f"// Result: {dx_map_path}")
        self.source_dir = FileUtils.format_path(gl_map_paths[0], "path")

    def b004(self):
        """Batch pack Transparency into Albedo across texture sets."""
        paths = self._get_texture_paths(
            title="Select one or more sets of Albedo/Base Color and Transparency maps:",
        )
        if not paths:
            return

        texture_sets = MapFactory.group_textures_by_set(paths)

        for base_name, files in texture_sets.items():
            sorted_maps = MapFactory.sort_images_by_type(files)

            albedo_map_path = sorted_maps.get("Albedo_Transparency", [None])[0]
            base_color_path = sorted_maps.get("Base_Color", [None])[0]
            opacity_map_path = sorted_maps.get("Opacity", [None])[0]

            if not (albedo_map_path or base_color_path):
                print(f"Skipping {base_name}: No Albedo or Base Color map found.")
                continue

            if not opacity_map_path:
                print(f"Skipping {base_name}: No Transparency (Opacity) map found.")
                continue

            rgb_map_path = albedo_map_path or base_color_path

            print(
                f"Packing Transparency from: {opacity_map_path}\n\tinto: {rgb_map_path} .."
            )

            packed_path = MapFactory.pack_transparency_into_albedo(
                rgb_map_path,
                opacity_map_path,
                invert_alpha=False,
            )
            print(f"// Result: {packed_path}")

        try:
            self.source_dir = FileUtils.format_path(paths[0], "path")
        except Exception:
            pass

    def b007(self):
        """Unpack Specular and Gloss maps from SpecularGloss textures."""
        specular_gloss_paths = self._get_texture_paths(
            title="Select SpecularGloss maps to unpack:",
            map_type_filter=["Specular"],
        )
        if not specular_gloss_paths:
            return

        for specular_gloss_path in specular_gloss_paths:
            print(f"Unpacking: {specular_gloss_path} ..")

            try:
                specular_path, gloss_path = MapFactory.unpack_specular_gloss(
                    specular_gloss_path
                )
                print(f"// Specular map: {specular_path}")
                print(f"// Gloss map: {gloss_path}")

            except Exception as e:
                print(f"// Error unpacking {specular_gloss_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(specular_gloss_paths[0], "path")
        except Exception:
            pass

    def b010(self):
        """Convert Smoothness maps to Roughness maps."""
        smoothness_paths = self._get_texture_paths(
            title="Select Smoothness maps to convert to Roughness:",
            map_type_filter=["Smoothness"],
        )
        if not smoothness_paths:
            return

        for smoothness_path in smoothness_paths:
            print(f"Converting Smoothness to Roughness: {smoothness_path} ..")

            try:
                roughness_path = MapFactory.convert_smoothness_to_roughness(
                    smoothness_path
                )
                print(f"// Result: {roughness_path}")

            except Exception as e:
                print(f"// Error converting {smoothness_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(smoothness_paths[0], "path")
        except Exception:
            pass

    def b011(self):
        """Convert Roughness maps to Smoothness maps."""
        roughness_paths = self._get_texture_paths(
            title="Select Roughness maps to convert to Smoothness:",
            map_type_filter=["Roughness"],
        )
        if not roughness_paths:
            return

        for roughness_path in roughness_paths:
            print(f"Converting Roughness to Smoothness: {roughness_path} ..")

            try:
                smoothness_path = MapFactory.convert_roughness_to_smoothness(
                    roughness_path
                )
                print(f"// Result: {smoothness_path}")

            except Exception as e:
                print(f"// Error converting {roughness_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(roughness_paths[0], "path")
        except Exception:
            pass

    def b012(self):
        """Batch-prepare textures for a target PBR workflow using MapFactory.

        Workflow presets come from :class:`pythontk.MapRegistry` — the single
        source of truth the Maya "Update Materials" tool also reads — so a named
        workflow yields identical settings in both tools. (This method used to
        carry its own copy of the configs, which had drifted from the registry.)
        """
        # Get texture paths
        texture_paths = self._get_texture_paths(
            title="Select texture maps for PBR workflow preparation:",
        )
        if not texture_paths:
            return

        # Workflow presets are owned by MapRegistry (SSoT); offer its names.
        registry = MapRegistry()
        workflow_names = list(registry.get_workflow_presets())

        from qtpy.QtWidgets import QInputDialog

        workflow, ok = QInputDialog.getItem(
            None,
            "Select PBR Workflow",
            "Choose target workflow:",
            workflow_names,
            0,
            False,
        )
        if not ok:
            return

        # Resolve to a full MapFactory config (applies aliases, derives
        # resize/convert_format). Drop the human-readable description and keep
        # the panel's long-standing default output format.
        config = registry.resolve_config(workflow)
        if not config:
            print(f"Unknown workflow: {workflow}")
            return
        config.pop("description", None)
        config.setdefault("output_extension", "png")

        print(f"\n{'='*60}")
        print(f"Preparing textures for {workflow}")
        print(f"{'='*60}\n")

        try:
            results = MapFactory.prepare_maps(
                texture_paths,
                **config,
            )

            if isinstance(results, dict):
                print(f"Processed {len(results)} texture sets.")
                for base_name, maps in results.items():
                    print(f"\n[ok] Set: {base_name}")
                    for m in maps:
                        print(f"  - {FileUtils.format_path(m, 'name')}")
            else:
                print("\n[ok] Processed single set.")
                for m in results:
                    print(f"  - {FileUtils.format_path(m, 'name')}")

        except Exception as e:
            print(f"Error during batch processing: {e}")

        print(f"{'='*60}")
        print(f"Workflow preparation complete!")
        print(f"{'='*60}\n")

        try:
            self.source_dir = FileUtils.format_path(texture_paths[0], "path")
        except Exception:
            pass
