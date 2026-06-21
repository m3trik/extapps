# !/usr/bin/python
# coding=utf-8
from typing import List, Dict, Optional, Any
from pythontk.img_utils._img_utils import ImgUtils
from pythontk.img_utils.map_factory import MapFactory
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

    def cmbFormat_init(self, widget):
        """Populate the output-format combo and react to format changes."""
        widget.clear()
        widget.addItems(self.output_formats)
        widget.restore_state = True
        widget.currentTextChanged.connect(self._on_format_changed)

    def _on_format_changed(self, fmt: str):
        """Disable alpha combobox for formats without alpha support."""
        supports_alpha = fmt.upper() in {"PNG", "TGA", "TIFF", "EXR", "BMP"}
        self.ui.cmbA.setEnabled(supports_alpha)
        if not supports_alpha:
            self.ui.cmbA.setCurrentIndex(self.ui.cmbA.findText("None"))

    def header_init(self, widget):
        """Build the header menu's Pack/Unpack mode toggle.

        The channel layout (R/G/B/A → map type) is direction-agnostic, so a
        single set of presets serves both packing and unpacking; those presets
        reference the channel combos, which register *after* the header, so they
        are wired in :meth:`_setup_presets` once the whole UI exists. The Mode
        toggle decides the direction (see :meth:`_on_mode_changed`).
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

    def _unpack_mode(self) -> bool:
        """True when the header Mode toggle is set to Unpack.

        Defaults to False (Pack) when the header menu hasn't been built yet, so
        callers can read it safely at any point.
        """
        try:
            return self.ui.header.menu.cmb_mode.currentText() == "Unpack"
        except (AttributeError, RuntimeError):
            return False

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

        preset_dir = preset_mgr.preset_dir
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

    def _select_textures(self, title):
        """Open the texture file dialog seeded from the current source dir."""
        return self.sb.file_dialog(
            file_types=[f"*.{ext}" for ext in self.texture_file_types],
            title=title,
            start_dir=self.source_dir,
            allow_multiple=True,
        )

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
        file_paths = self._select_textures(
            "Select textures for batch packing (multiple sets allowed):"
        )
        if not file_paths:
            print("No files selected.")
            self.ui.b001.setEnabled(False)
            return

        texture_sets = MapFactory.group_textures_by_set(file_paths)
        combos = [
            self.ui.cmbR.currentText(),
            self.ui.cmbG.currentText(),
            self.ui.cmbB.currentText(),
            self.ui.cmbA.currentText(),
        ]
        suffix = self.ui.txtSuffix.text().strip() or "_Packed"
        if not suffix.startswith("_"):
            suffix = f"_{suffix}"
        ext = self.ui.cmbFormat.currentText().lower()
        fmt = self.ui.cmbFormat.currentText().upper()

        success = False
        total_sets = len(texture_sets)
        with self.sb.progress(
            total=total_sets, text=f"Packing 0/{total_sets} sets"
        ) as update:
            for i, (base_name, files) in enumerate(texture_sets.items()):
                success = (
                    self._pack_set(
                        base_name=base_name,
                        files=files,
                        combos=combos,
                        suffix=suffix,
                        ext=ext,
                        fmt=fmt,
                    )
                    or success
                )
                update(
                    i + 1,
                    f"Packed set {i + 1}/{total_sets}: {base_name}",
                )

        self._finish_batch(success, file_paths)

    def _pack_set(self, *, base_name, files, combos, suffix, ext, fmt) -> bool:
        """Helper for ``b000`` — pack a single texture set. Returns True
        if at least one channel was assigned and the output written.

        Matches the pre-refactor behavior: stop assigning at the first
        missing-and-unconvertible required map, but pack whatever
        partial assignment we have if anything stuck.
        """
        assigned = {c: None for c in self.channels}
        available_map_types = {MapFactory.resolve_map_type(f): f for f in files}
        used_files = set()

        for idx, channel in enumerate(self.channels):
            map_type = combos[idx]
            if map_type == "None":
                continue
            file = next(
                (
                    f
                    for f in files
                    if MapFactory.resolve_map_type(f) == map_type
                    and f not in used_files
                ),
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
            print(
                f"// Required map '{map_type}' for channel {channel} in '{base_name}' not found and cannot be converted. Skipping."
            )
            break  # skip remaining channels for this set

        if not any(assigned[c] for c in self.channels):
            return False

        out_mode = "RGBA" if assigned["A"] else "RGB"
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
        file_paths = self._select_textures(
            "Select packed textures to unpack into per-channel maps:"
        )
        if not file_paths:
            print("No files selected.")
            self.ui.b001.setEnabled(False)
            return

        combos = [
            self.ui.cmbR.currentText(),
            self.ui.cmbG.currentText(),
            self.ui.cmbB.currentText(),
            self.ui.cmbA.currentText(),
        ]
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
            channel: {"suffix": f"_{combos[idx]}"}
            for idx, channel in enumerate(self.channels)
            if combos[idx] != "None"
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
        import sys

        output_dir = getattr(self, "_last_output_dir", None)
        if not output_dir or not os.path.isdir(output_dir):
            print("// No output directory available.")
            return
        if sys.platform.startswith("darwin"):
            os.system(f'open "{output_dir}"')
        elif sys.platform.startswith("win"):
            os.startfile(output_dir)
        elif sys.platform.startswith("linux"):
            os.system(f'xdg-open "{output_dir}"')
        else:
            print("// Unsupported OS for opening directories.")
