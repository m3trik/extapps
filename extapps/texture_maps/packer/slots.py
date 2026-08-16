# !/usr/bin/python
# coding=utf-8
from typing import List
from pythontk.img_utils._img_utils import ImgUtils
from pythontk.core_utils.engines.textures.map_factory import MapFactory
from pythontk.file_utils._file_utils import FileUtils


class PackerSlots(ImgUtils):
    channels = ["R", "G", "B", "A"]
    grayscale_types = [
        "None",
        "Metallic",
        "Roughness",
        "Ambient_Occlusion",
        "Smoothness",
        "Opacity",
        "Height",
        "Thickness",
        "Glossiness",
        "Displacement",
    ]
    output_formats = ["PNG", "TGA", "JPG", "BMP", "TIFF", "EXR"]

    # Policy for a texture set whose requested maps aren't all resolvable.
    MISSING_SKIP = "skip"  # default: don't write an incomplete set
    MISSING_MULTI = "multi"  # write it only if 2+ channels resolved
    MISSING_FORCE = "force"  # always write; missing channels fill

    PRESET_DIR = "extapps/texture_maps/packer"

    # Built-in presets defined using human-readable names.
    # Resolved to combo indices at seed time via grayscale_types/output_formats.
    BUILTIN_PRESETS = {
        "ORM (Unreal, glTF)": {
            "R": "Ambient_Occlusion",
            "G": "Roughness",
            "B": "Metallic",
            "A": "None",
            "format": "PNG",
            "suffix": "_ORM",
        },
        "MRAO (Metallic, Roughness, AO)": {
            "R": "Metallic",
            "G": "Roughness",
            "B": "Ambient_Occlusion",
            "A": "None",
            "format": "PNG",
            "suffix": "_MRAO",
        },
        "MSAO (HDRP Mask Map)": {
            "R": "Metallic",
            "G": "Ambient_Occlusion",
            "B": "None",
            "A": "Smoothness",
            "format": "PNG",
            "suffix": "_MSAO",
        },
        "Metallic Smoothness (URP)": {
            "R": "Metallic",
            "G": "None",
            "B": "None",
            "A": "Smoothness",
            "format": "PNG",
            "suffix": "_MetallicSmoothness",
        },
    }

    def __init__(self, switchboard, **kwargs):
        super().__init__()

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.packer

        self._source_dir = kwargs.get("source_dir", "")

        # The switchboard can build this slots instance mid-load — even eagerly
        # during Switchboard construction (slot_source=) — *before* the child
        # widgets are registered onto self.ui. Touching any widget here would
        # raise and leave ``ui.slots = None`` (e.g. tentacle's materials b008
        # then crashes on ``ui.slots.source_dir``). Per-widget setup lives in
        # the ``*_init`` methods; cross-widget wiring that needs the whole UI
        # (presets, label colors, mode sync) runs once the UI is registered.
        self.ui.run_when_ready(self._initialize_ui)

    def _set_channel_label_colors(self):
        """Set background color for each channel label."""
        channel_colors = {
            "R": "#ef9a9a",  # Pastel Red
            "G": "#a5d6a7",  # Pastel Green
            "B": "#90caf9",  # Pastel Blue
            "A": "#bdbdbd",  # Pastel Gray
        }
        for c in self.channels:
            lbl = getattr(self.ui, f"lbl{c}", None)
            if lbl:
                lbl.setStyleSheet(
                    f"background-color: {channel_colors[c]}; color: white; border-radius: 3px;"
                )

    def _initialize_ui(self):
        """Cross-widget wiring, deferred until the whole UI is registered.

        Runs once after ``register_children`` (via ``on_first_show``), so every
        channel combo, the header menu, and the action buttons exist. Per-combo
        population/restore already ran in the ``*_init`` methods, so this only
        does the wiring that spans multiple widgets.
        """
        self._set_channel_label_colors()
        self.ui.b001.setEnabled(False)  # the open-output-dir button starts disabled
        self._setup_presets()
        # Sync the action-button text / option enablement to the restored mode.
        self._on_mode_changed(self.ui.header.menu.cmb_mode.currentText())

    def _setup_presets(self):
        """Register the channel/format/suffix widgets with the header preset menu."""
        presets = self.ui.header.menu.presets
        presets.preset_dir = self.PRESET_DIR
        # Seed built-in presets BEFORE setup so the combo is populated on first launch.
        self._seed_builtin_presets(presets)
        presets.setup(
            preset_dir=self.PRESET_DIR,
            widgets=[
                self.ui.cmbR,
                self.ui.cmbG,
                self.ui.cmbB,
                self.ui.cmbA,
                self.ui.cmbFormat,
                self.ui.txtSuffix,
            ],
        )

    def _init_channel_combo(self, widget):
        """Populate a channel combo with the grayscale map types.

        Runs inside the per-widget ``*_init`` (so during ``register_children``,
        before state restore) — the selection then persists across sessions.
        """
        widget.clear()
        widget.addItems(self.grayscale_types)
        widget.restore_state = True

    def cmbR_init(self, widget):
        self._init_channel_combo(widget)

    def cmbG_init(self, widget):
        self._init_channel_combo(widget)

    def cmbB_init(self, widget):
        self._init_channel_combo(widget)

    def cmbA_init(self, widget):
        self._init_channel_combo(widget)

    def txtSuffix_init(self, widget):
        """Output-suffix field — clearable back to the ``_Packed`` default."""
        widget.option_box.clear_option = True

    def cmbFormat_init(self, widget):
        """Populate the output-format combo and react to format changes."""
        widget.clear()
        widget.addItems(self.output_formats)
        widget.restore_state = True
        widget.currentTextChanged.connect(self._on_format_changed)

    def _on_format_changed(self, fmt: str):
        """Disable alpha combobox for formats without alpha support.

        Only constrains alpha in *pack* mode: there the alpha combo selects a
        source map to write into the output's alpha channel, so a format
        without alpha support (e.g. JPG) must clear it. In *unpack* mode the
        alpha combo selects which channel to *extract* from the input image,
        which is independent of the output format, so it stays enabled and its
        selection is left untouched (mirrors the invariant in
        :meth:`_on_mode_changed`). This handler is wired to the format combo's
        ``currentTextChanged``, so it fires in both modes.
        """
        if self._unpack_mode():
            self.ui.cmbA.setEnabled(True)
            return
        supports_alpha = fmt.upper() in {"PNG", "TGA", "TIFF", "EXR", "BMP"}
        self.ui.cmbA.setEnabled(supports_alpha)
        if not supports_alpha:
            self.ui.cmbA.setCurrentIndex(self.ui.cmbA.findText("None"))

    def header_init(self, widget):
        """Build the header menu's Pack/Unpack toggle and Missing Maps policy.

        The channel layout (R/G/B/A → map type) is direction-agnostic, so a
        single set of presets serves both packing and unpacking; those presets
        reference the channel combos, which register *after* the header, so they
        are wired in :meth:`_setup_presets` once the whole UI exists. The Mode
        toggle decides the direction (see :meth:`_on_mode_changed`); the
        Missing Maps combo decides what an incomplete set does when packing
        (see :meth:`_pack_set`).
        """
        widget.menu.setTitle("Map Packer Options")
        cmb_mode = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_mode",
            addItems=["Pack", "Unpack"],
            setToolTip=(
                "Pack: combine the per-channel source maps into one packed "
                "texture.\n"
                "Unpack: split a packed texture back into its per-channel maps "
                "(each channel's selected map type names the output file)."
            ),
        )
        cmb_mode.restore_state = True
        cmb_mode.currentTextChanged.connect(self._on_mode_changed)

        cmb_missing = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_missing",
            setToolTip=(
                "What to do with a texture set when one or more of the "
                "requested source maps is missing (and can't be derived from "
                "the maps that are present).\n"
                "Skip Set (default): nothing is written, so an incomplete set "
                "can't silently produce a packed map with blank channels.\n"
                "Pack If 2+ Maps: pack only when at least two channels "
                "resolved - enough that the result is still a useful packed "
                "map rather than a single map wearing a packed name.\n"
                "Pack Anyway: always pack; missing channels are filled with "
                "their default value (0 for R/G/B, 255 for A)."
            ),
        )
        cmb_missing.add(
            [
                ("Skip Set", self.MISSING_SKIP),
                ("Pack If 2+ Maps", self.MISSING_MULTI),
                ("Pack Anyway", self.MISSING_FORCE),
            ],
            prefix="Missing Maps:",
        )
        cmb_missing.restore_state = True

    def _unpack_mode(self) -> bool:
        """True when the header Mode toggle is set to Unpack.

        Defaults to False (Pack) when the header menu hasn't been built yet, so
        callers can read it safely at any point.
        """
        try:
            return self.ui.header.menu.cmb_mode.currentText() == "Unpack"
        except (AttributeError, RuntimeError):
            return False

    def _missing_map_rule(self) -> str:
        """The header's 'Missing Maps' policy for incomplete texture sets.

        Falls back to :attr:`MISSING_SKIP` when the header menu hasn't been
        built yet (or the combo has no selection), so callers can read it
        safely at any point and always get the safe default.
        """
        try:
            return self.ui.header.menu.cmb_missing.currentData() or self.MISSING_SKIP
        except (AttributeError, RuntimeError):
            return self.MISSING_SKIP

    def _on_mode_changed(self, mode: str):
        """Reflect the Pack/Unpack mode in the UI.

        Behavior is read live from :meth:`_unpack_mode` at action time, so this
        is purely cosmetic: relabel the action button and disable options that
        don't apply to the current direction.
        """
        unpack = mode == "Unpack"
        self.ui.b000.setText("Unpack" if unpack else "Pack")
        # The Suffix names the single packed output; when unpacking, each output
        # is auto-named by its channel's map type, so the field is irrelevant.
        self.ui.txtSuffix.setEnabled(not unpack)
        # The Missing Maps policy only governs the pack direction.
        cmb_missing = getattr(self.ui.header.menu, "cmb_missing", None)
        if cmb_missing is not None:
            cmb_missing.setEnabled(not unpack)
        # In pack mode the alpha channel's availability follows the output
        # format. In unpack mode the alpha combo selects what to extract from
        # the input image, so it must stay enabled regardless of format.
        if unpack:
            self.ui.cmbA.setEnabled(True)
        else:
            self._on_format_changed(self.ui.cmbFormat.currentText())

    def _seed_builtin_presets(self, preset_mgr):
        """Write built-in preset JSON files if they don't already exist.

        Converts human-readable BUILTIN_PRESETS (map-type/format names)
        into the index-based JSON format that PresetManager expects.
        """
        import json

        for name, preset in self.BUILTIN_PRESETS.items():
            filepath = preset_mgr._preset_path(name)
            if not filepath.exists():
                data = {
                    "_meta": {"version": 1},
                    "cmbR": self.grayscale_types.index(preset["R"]),
                    "cmbG": self.grayscale_types.index(preset["G"]),
                    "cmbB": self.grayscale_types.index(preset["B"]),
                    "cmbA": self.grayscale_types.index(preset["A"]),
                    "cmbFormat": self.output_formats.index(preset["format"]),
                    "txtSuffix": preset["suffix"],
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

    @property
    def source_dir(self):
        return self._source_dir

    @source_dir.setter
    def source_dir(self, value):
        self._source_dir = value

    def _channel_combos(self) -> List[str]:
        """The R/G/B/A map-type selections, in channel order.

        Read identically by both directions: packing treats the entry as the
        map to write *into* that channel, unpacking as the map that channel
        already holds.
        """
        return [getattr(self.ui, f"cmb{c}").currentText() for c in self.channels]

    def _require_channel_selection(self, combos) -> bool:
        """True when at least one channel names a map type; reports when not.

        With every channel on 'None' there is nothing to pack or unpack, and
        both batches would otherwise walk their whole selection to no effect —
        reporting every set as skipped, which reads like the files were at
        fault rather than the empty channel layout.
        """
        if any(c != "None" for c in combos):
            return True
        print("// No channels assigned. Set at least one channel's map type.")
        return False

    def _select_textures(self, title):
        """Open the texture file dialog seeded from the current source dir.

        On selection, re-seed ``source_dir`` from the chosen files so the next
        dialog reopens where the user last browsed. Without this the dialog
        stays pinned to the stale seed dir even after the user changes folders
        (``_finish_batch`` only updates it, to the output dir, on success).
        Mirrors :class:`ConverterSlots`, which re-seeds after every selection.
        """
        file_paths = self.sb.file_dialog(
            file_types=[f"*.{ext}" for ext in self.texture_file_types],
            title=title,
            start_dir=self.source_dir,
            allow_multiple=True,
        )
        if file_paths:
            self.source_dir = FileUtils.format_path(file_paths[0], "path")
        return file_paths

    def _finish_batch(self, success, file_paths):
        """Post-batch bookkeeping shared by pack/unpack: on success, point the
        source dir at the output and enable the 'open output' button; otherwise
        leave it disabled."""
        if success:
            self._last_output_dir = FileUtils.format_path(file_paths[0], "path")
            self.source_dir = self._last_output_dir
            self.ui.b001.setEnabled(True)
        else:
            self.ui.b001.setEnabled(False)

    def b000(self):
        """Run the configured channel operation: Pack (default) or Unpack."""
        if self._unpack_mode():
            self._unpack_files()
        else:
            self._pack_files()

    def _pack_files(self):
        """Batch pack up to 4 channels into RGBA maps across texture sets."""
        combos = self._channel_combos()
        if not self._require_channel_selection(combos):
            self.ui.b001.setEnabled(False)
            return

        file_paths = self._select_textures(
            "Select textures for batch packing (multiple sets allowed):"
        )
        if not file_paths:
            print("No files selected.")
            self.ui.b001.setEnabled(False)
            return

        texture_sets = MapFactory.group_textures_by_set(file_paths)
        suffix = self.ui.txtSuffix.text().strip() or "_Packed"
        if not suffix.startswith("_"):
            suffix = f"_{suffix}"
        ext = self.ui.cmbFormat.currentText().lower()
        fmt = self.ui.cmbFormat.currentText().upper()
        rule = self._missing_map_rule()

        success = False
        packed = 0
        total_sets = len(texture_sets)
        with self.sb.progress(
            total=total_sets, text=f"Packing 0/{total_sets} sets"
        ) as update:
            for i, (base_name, files) in enumerate(texture_sets.items()):
                result = self._pack_set(
                    base_name=base_name,
                    files=files,
                    combos=combos,
                    suffix=suffix,
                    ext=ext,
                    fmt=fmt,
                    rule=rule,
                )
                packed += bool(result)
                success = result or success
                # Skipped sets are the norm now, so the progress line has to
                # say which happened rather than claim every set was packed.
                update(
                    i + 1,
                    f"{'Packed' if result else 'Skipped'} set "
                    f"{i + 1}/{total_sets}: {base_name}",
                )

        if packed < total_sets:
            hint = (
                ""
                if rule == self.MISSING_FORCE
                else " Set 'Missing Maps' to 'Pack Anyway' to pack them regardless."
            )
            print(
                f"// Result: Packed {packed}/{total_sets} set(s); "
                f"{total_sets - packed} skipped (incomplete).{hint}"
            )

        self._finish_batch(success, file_paths)

    def _pack_set(
        self, *, base_name, files, combos, suffix, ext, fmt, rule=MISSING_SKIP
    ) -> bool:
        """Helper for ``b000`` — pack a single texture set. Returns True
        if the set was packed and the output written.

        A set is *complete* when every channel assigned a map type (anything
        but ``None``) resolves to a source file, either directly or by
        conversion from another map that is present. An incomplete set is
        skipped by default — packing it would write a map whose missing
        channels are silently filled with a constant, which is indistinguishable
        from a legitimately flat channel downstream.

        ``rule`` is the header's 'Missing Maps' policy, applied only when the
        set is incomplete: :attr:`MISSING_SKIP` writes nothing,
        :attr:`MISSING_MULTI` writes it if at least two channels resolved, and
        :attr:`MISSING_FORCE` always writes it. In both packing cases as many
        channels as possible are resolved and ``pack_channels`` fills the rest
        with its per-channel defaults.
        """
        assigned = {c: None for c in self.channels}
        requested = dict(zip(self.channels, combos))
        # Resolve each file's map type once: the per-channel search below would
        # otherwise re-derive every file's type for all four channels.
        file_types = [(f, MapFactory.resolve_map_type(f)) for f in files]
        available_map_types = {t: f for f, t in file_types}
        used_files = set()
        missing = []

        for channel in self.channels:
            map_type = requested[channel]
            if map_type == "None":
                continue
            file = next(
                (f for f, t in file_types if t == map_type and f not in used_files),
                None,
            )
            if file:
                assigned[channel] = file
                used_files.add(file)
                continue
            # Try conversion if not found
            converted = MapFactory.get_converted_map(map_type, available_map_types)
            if converted is not None:
                assigned[channel] = converted
                continue
            missing.append(f"{channel}:{map_type}")

        resolved = [c for c in self.channels if assigned[c]]

        if missing:
            # How many channels a packing rule needs before it will write an
            # incomplete set. MISSING_SKIP needs them all, i.e. never gets here.
            minimum = {self.MISSING_MULTI: 2, self.MISSING_FORCE: 1}.get(rule, 0)
            if not minimum or len(resolved) < minimum:
                print(
                    f"// Skipped '{base_name}': required map(s) "
                    f"{', '.join(missing)} not found and cannot be converted."
                )
                return False
            print(
                f"// Warning: '{base_name}' is missing {', '.join(missing)}. "
                "Packing with those channels filled by default values."
            )
        elif not resolved:  # every channel set to 'None' — nothing was asked for
            return False

        # Channel count follows the layout the user CONFIGURED, not just what
        # resolved: a force-packed set whose alpha map is missing still writes
        # RGBA (alpha filled), so one batch can't emit a mix of RGB and RGBA
        # files under a single suffix. A layout with A on 'None' stays RGB —
        # that is what makes ORM/MRAO 3-channel, and it is the whole point of
        # those formats (no alpha means BC1 rather than BC3/BC7).
        out_mode = "RGBA" if requested["A"] != "None" else "RGB"
        output_dir = FileUtils.format_path(files[0], "path")
        output_path = f"{output_dir}/{base_name}{suffix}.{ext}"
        self.pack_channels(
            channel_files=assigned,
            output_path=output_path,
            out_mode=out_mode,
            output_format=fmt,
        )
        print(f"// Result: Packed map saved: {output_path}")
        return True

    def _unpack_files(self):
        """Batch unpack packed textures into per-channel maps.

        The same R/G/B/A → map-type assignment used for packing now describes
        what each channel of the *input* holds; each assigned channel is
        extracted to ``<base>_<MapType>.<ext>`` beside the source.
        """
        combos = self._channel_combos()
        if not self._require_channel_selection(combos):
            self.ui.b001.setEnabled(False)
            return

        file_paths = self._select_textures(
            "Select packed textures to unpack into per-channel maps:"
        )
        if not file_paths:
            print("No files selected.")
            self.ui.b001.setEnabled(False)
            return

        ext = self.ui.cmbFormat.currentText().lower()
        fmt = self.ui.cmbFormat.currentText().upper()

        success = False
        total = len(file_paths)
        with self.sb.progress(total=total, text=f"Unpacking 0/{total}") as update:
            for i, file in enumerate(file_paths):
                success = (
                    self._unpack_one(file=file, combos=combos, ext=ext, fmt=fmt)
                    or success
                )
                update(
                    i + 1,
                    f"Unpacked {i + 1}/{total}: {FileUtils.format_path(file, 'name')}",
                )

        self._finish_batch(success, file_paths)

    def _unpack_one(self, *, file, combos, ext, fmt) -> bool:
        """Helper for ``_unpack_files`` — split one packed texture. Returns True
        if at least one channel was extracted and written.

        Channels set to ``None`` are skipped; channels absent from the source
        image (e.g. ``A`` on an RGB input) are skipped by ``extract_channels``.
        """
        channel_config = {
            channel: {"suffix": f"_{map_type}"}
            for channel, map_type in zip(self.channels, combos)
            if map_type != "None"
        }
        if not channel_config:
            return False

        output_dir = FileUtils.format_path(file, "path")
        results = self.extract_channels(
            file,
            channel_config,
            output_dir=output_dir,
            save=True,
            output_format=fmt,
            ext=ext,
        )
        written = [p for p in results.values() if p]
        for path in written:
            print(f"// Result: Extracted map saved: {path}")
        return bool(written)

    def b001(self):
        """Open the last output directory in the system file explorer."""
        import os

        output_dir = getattr(self, "_last_output_dir", None)
        if not output_dir or not os.path.isdir(output_dir):
            print("// No output directory available.")
            return
        # Delegate to the canonical, non-shell launcher. It passes the path as
        # a single argv entry (os.startfile / subprocess.Popen(["xdg-open", ...])),
        # so shell metacharacters in the directory name are inert — this avoids
        # the os.system shell-injection the interpolated command strings had.
        if not FileUtils.open_explorer(output_dir):
            print("// Unable to open output directory.")
