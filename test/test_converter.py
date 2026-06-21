#!/usr/bin/python
# coding=utf-8
"""
Comprehensive tests for MapConverter with TextureMapFactory integration.

Tests cover:
- TextureMapFactory integration in tb001 (Spec/Gloss conversion)
- New b012 method for batch PBR workflow preparation
- All 7 workflow templates
- Error handling and fallback behavior
"""
import os
import tempfile
import shutil
import unittest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from PIL import Image

from pythontk import ImgUtils
from pythontk.img_utils.map_factory import MapFactory as TextureMapFactory
from pythontk.img_utils.map_registry import MapRegistry, WF

from extapps.texture_maps.converter.slots import ConverterSlots

# Check if Qt (PySide6/PyQt) is available via qtpy (for b012 tests)
try:
    from qtpy import QtWidgets  # noqa: F401

    QT_AVAILABLE = True
except Exception:
    QT_AVAILABLE = False

skip_if_no_qt = unittest.skipUnless(
    QT_AVAILABLE, "Qt not available - b012 tests require QInputDialog"
)

class TestMapConverterTextureFactory(unittest.TestCase):
    """Test MapConverter integration with TextureMapFactory."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Create temporary directory for test outputs
        cls.test_dir = tempfile.mkdtemp(prefix="converter_test_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

        # Create sample texture files for testing
        cls._create_test_textures()

    @classmethod
    def tearDownClass(cls):
        """Clean up test directory after all tests."""
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    @classmethod
    def _create_test_textures(cls):
        """Create sample texture files for testing."""
        # Define test texture set
        cls.test_textures = {
            "Base_Color": "material_BaseColor.png",
            "Metallic": "material_Metallic.png",
            "Roughness": "material_Roughness.png",
            "Normal_OpenGL": "material_Normal_OpenGL.png",
            "Ambient_Occlusion": "material_AO.png",
            "Opacity": "material_Opacity.png",
            "Specular": "material_Specular.png",
            "Glossiness": "material_Glossiness.png",
            "Diffuse": "material_Diffuse.png",
        }

        # Create actual image files
        cls.texture_paths = []
        for map_type, filename in cls.test_textures.items():
            filepath = os.path.join(cls.test_files_dir, filename)

            # Create appropriate test images based on type
            if "Normal" in map_type:
                img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 255))
            elif map_type in ["Metallic", "Roughness", "AO", "Opacity", "Glossiness"]:
                img = ImgUtils.create_image("L", (512, 512), 128)
            else:
                img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))

            ImgUtils.save_image(img, filepath)
            cls.texture_paths.append(filepath)

    def setUp(self):
        """Set up test fixtures for each test."""
        # Create mock switchboard
        self.mock_sb = Mock()
        self.mock_sb.file_dialog = Mock(return_value=None)

        # Create ConverterSlots instance
        self.converter = ConverterSlots(self.mock_sb)

        # Mock UI components
        self.mock_widget = Mock()
        self.mock_widget.option_box.menu = Mock()
        self.mock_widget.option_box.menu.chk000 = Mock()
        self.mock_widget.option_box.menu.chk000.isChecked = Mock(return_value=False)

    # -------------------------------------------------------------------------
    # Test tb001 with TextureMapFactory Integration
    # -------------------------------------------------------------------------

    def test_tb001_spec_gloss_conversion_basic(self):
        """Test tb001 Spec/Gloss conversion using TextureMapFactory."""
        # Setup file dialog mock to return spec/gloss textures
        spec_gloss_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
            os.path.join(self.test_files_dir, "material_Diffuse.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_gloss_textures

        # Run conversion
        self.converter.tb001(self.mock_widget)

        # Verify file dialog was called
        self.mock_sb.file_dialog.assert_called_once()

        # Check that processed files exist (TextureMapFactory should create outputs)
        # Note: Actual output verification depends on TextureMapFactory implementation

    def test_tb001_with_metallic_smoothness_packing(self):
        """Test tb001 with metallic smoothness packing enabled."""
        spec_gloss_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_gloss_textures
        self.mock_widget.option_box.menu.chk000.isChecked.return_value = True

        # Run conversion with packing enabled
        self.converter.tb001(self.mock_widget)

        # Verify checkbox was checked
        self.mock_widget.option_box.menu.chk000.isChecked.assert_called()

    def test_tb001_empty_selection(self):
        """Test tb001 handles empty file selection."""
        self.mock_sb.file_dialog.return_value = None

        # Should return early without error
        result = self.converter.tb001(self.mock_widget)

        # Verify it returns None (early exit)
        self.assertIsNone(result)

    def test_tb001_multiple_texture_sets(self):
        """Test tb001 processes multiple texture sets."""
        # Create second texture set
        set2_textures = []
        for map_type, filename in [
            ("Specular", "model2_Specular.png"),
            ("Glossiness", "model2_Glossiness.png"),
        ]:
            filepath = os.path.join(self.test_files_dir, filename)
            img = ImgUtils.create_image("L", (512, 512), 128)
            ImgUtils.save_image(img, filepath)
            set2_textures.append(filepath)

        all_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
        ] + set2_textures

        self.mock_sb.file_dialog.return_value = all_textures

        # Run conversion
        self.converter.tb001(self.mock_widget)

        # Should process both sets without error

    def test_tb001_fallback_on_factory_error(self):
        """Test tb001 falls back to legacy method if TextureMapFactory fails."""
        spec_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_textures

        # Mock MapFactory to raise exception
        with patch(
            "extapps.texture_maps.converter.slots.MapFactory.prepare_maps",
            side_effect=Exception("Factory error"),
        ):
            # Should fall back to legacy method without crashing
            self.converter.tb001(self.mock_widget)

    # -------------------------------------------------------------------------
    # Test b012 - Batch PBR Workflow Preparation
    # -------------------------------------------------------------------------

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_standard_pbr_workflow(self, mock_dialog):
        """Test b012 with standard PBR workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths[
            :5
        ]  # Subset of textures
        mock_dialog.return_value = (WF.STD, True)

        # Run batch workflow
        self.converter.b012()

        # Verify dialog was shown
        mock_dialog.assert_called_once()
        self.mock_sb.file_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unity_urp_workflow(self, mock_dialog):
        """Test b012 with Unity URP workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.URP, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unity_hdrp_workflow(self, mock_dialog):
        """Test b012 with Unity HDRP workflow (MSAO)."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.HDRP, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unreal_workflow(self, mock_dialog):
        """Test b012 with Unreal Engine workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.UE, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_gltf_workflow(self, mock_dialog):
        """Test b012 with glTF 2.0 workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.GLTF, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_godot_workflow(self, mock_dialog):
        """Test b012 with Godot workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.GODOT, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_specular_glossiness_workflow(self, mock_dialog):
        """Test b012 with Specular/Glossiness workflow."""
        spec_gloss_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
            os.path.join(self.test_files_dir, "material_Diffuse.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_gloss_textures
        mock_dialog.return_value = (WF.SPEC, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_user_cancels_workflow_selection(self, mock_dialog):
        """Test b012 handles user canceling workflow selection."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = ("Unity URP", False)  # User canceled

        # Should return early
        result = self.converter.b012()

        self.assertIsNone(result)

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_empty_texture_selection(self, mock_dialog):
        """Test b012 handles empty texture selection."""
        self.mock_sb.file_dialog.return_value = None

        # Should return early without showing workflow dialog
        result = self.converter.b012()

        self.assertIsNone(result)
        mock_dialog.assert_not_called()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unknown_workflow(self, mock_dialog):
        """Test b012 handles unknown workflow gracefully."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = ("Unknown Workflow", True)

        # Should handle gracefully
        self.converter.b012()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_multiple_texture_sets(self, mock_dialog):
        """Test b012 processes multiple texture sets correctly."""
        # Create second texture set
        set2_textures = []
        for map_type, filename in [
            ("BaseColor", "model2_BaseColor.png"),
            ("Metallic", "model2_Metallic.png"),
            ("Roughness", "model2_Roughness.png"),
        ]:
            filepath = os.path.join(self.test_files_dir, filename)
            img = ImgUtils.create_image(
                "RGB" if map_type == "BaseColor" else "L",
                (512, 512),
                (128, 128, 128) if map_type == "BaseColor" else 128,
            )
            ImgUtils.save_image(img, filepath)
            set2_textures.append(filepath)

        all_textures = self.texture_paths[:3] + set2_textures

        self.mock_sb.file_dialog.return_value = all_textures
        mock_dialog.return_value = (WF.STD, True)

        # Should process both sets
        self.converter.b012()

    @skip_if_no_qt
    @patch("pythontk.img_utils.map_factory.MapFactory.prepare_maps")
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_handles_factory_errors(self, mock_dialog, mock_prepare):
        """Test b012 handles TextureMapFactory errors gracefully."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.STD, True)
        mock_prepare.side_effect = Exception("Factory processing error")

        # Should catch and report error, not crash
        self.converter.b012()

    @skip_if_no_qt
    @patch("extapps.texture_maps.converter.slots.MapFactory.prepare_maps")
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_config_comes_from_registry(self, mock_dialog, mock_prepare):
        """b012 sources its workflow config from MapRegistry (SSoT), not a private copy.

        Guards against the two tools drifting: the config handed to
        ``prepare_maps`` must equal ``MapRegistry.resolve_config(name)`` (minus
        the description, plus the panel's default output format).
        """
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.URP, True)
        mock_prepare.return_value = []

        self.converter.b012()

        mock_prepare.assert_called_once()
        passed = dict(mock_prepare.call_args.kwargs)

        expected = MapRegistry().resolve_config(WF.URP)
        expected.pop("description", None)
        expected.setdefault("output_extension", "png")

        self.assertEqual(passed, expected)

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_offers_registry_workflow_names(self, mock_dialog):
        """The workflow picker is populated from MapRegistry, so both tools list
        the same named workflows."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.STD, True)

        self.converter.b012()

        offered = mock_dialog.call_args.args[3]
        self.assertEqual(
            sorted(offered), sorted(MapRegistry().get_workflow_presets())
        )

    @skip_if_no_qt
    def test_footer_button_no_slot_name_collision(self):
        """Regression: the 'Use Selection' footer toggle must not be stored under an
        attribute equal to its objectName.

        Switchboard resolves a widget's slot via ``getattr(slots, objectName)``; an
        attribute named 'btn_use_selection' returns the (non-callable) button itself
        and makes wiring its 'clicked' signal fail with 'is not a callable object'.
        """
        from qtpy import QtWidgets

        # A QApplication is required to instantiate the real footer button.
        QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        footer = Mock()

        self.converter.footer_init(footer)

        footer.add_widget.assert_called_once()
        btn = footer.add_widget.call_args.args[0]
        self.assertEqual(btn.objectName(), "btn_use_selection")

        # The slot instance must not shadow the objectName with the widget.
        resolved = getattr(self.converter, btn.objectName(), None)
        self.assertNotIsInstance(resolved, QtWidgets.QWidget)

        # The toggle is still readable on demand.
        btn.setChecked(True)
        self.assertTrue(self.converter._selection_enabled())
        btn.setChecked(False)
        self.assertFalse(self.converter._selection_enabled())

    # -------------------------------------------------------------------------
    # Integration Tests
    # -------------------------------------------------------------------------

    def test_texture_map_factory_import(self):
        """Test that MapFactory is properly imported."""
        from pythontk import MapFactory

        self.assertIsNotNone(MapFactory)
        self.assertTrue(hasattr(MapFactory, "prepare_maps"))

    def test_converter_has_all_methods(self):
        """Test that ConverterSlots has all expected methods."""
        self.assertTrue(hasattr(self.converter, "tb001"))
        self.assertTrue(hasattr(self.converter, "b012"))
        self.assertTrue(callable(self.converter.tb001))
        self.assertTrue(callable(self.converter.b012))

    def test_source_dir_property(self):
        """Test source_dir property getter/setter."""
        test_dir = "/test/directory"
        self.converter.source_dir = test_dir
        self.assertEqual(self.converter.source_dir, test_dir)

# =============================================================================
# Edge Cases
# =============================================================================

class TestMapConverterEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sb = Mock()
        self.converter = ConverterSlots(self.mock_sb)
        self.mock_widget = Mock()

    def test_tb001_with_corrupted_texture(self):
        """Test tb001 handles corrupted texture files."""
        # Create a corrupted file
        temp_dir = tempfile.mkdtemp()
        try:
            corrupted_file = os.path.join(temp_dir, "corrupted_spec.png")
            with open(corrupted_file, "w") as f:
                f.write("This is not a valid PNG")

            self.mock_sb.file_dialog.return_value = [corrupted_file]

            # Should handle gracefully
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_with_missing_texture_files(self, mock_dialog):
        """Test b012 handles missing texture files."""
        fake_paths = [
            "/nonexistent/texture1.png",
            "/nonexistent/texture2.png",
        ]

        self.mock_sb.file_dialog.return_value = fake_paths
        mock_dialog.return_value = (WF.STD, True)

        # Should handle gracefully
        self.converter.b012()

    def test_tb001_with_invalid_image_format(self):
        """Test tb001 handles unsupported image formats."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a text file with .png extension
            fake_png = os.path.join(temp_dir, "fake_spec.png")
            with open(fake_png, "wb") as f:
                f.write(b"Not an image")

            self.mock_sb.file_dialog.return_value = [fake_png]

            # Should handle gracefully without crashing
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_with_single_channel_specular(self):
        """Test tb001 handles grayscale specular maps correctly."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create grayscale specular map
            spec_file = os.path.join(temp_dir, "model_Specular.png")
            img = ImgUtils.create_image("L", (512, 512), 128)
            ImgUtils.save_image(img, spec_file)

            self.mock_sb.file_dialog.return_value = [spec_file]

            # Should process without error
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_workflow_config_passthrough(self):
        """Test tb001 correctly passes workflow config to TextureMapFactory."""
        temp_dir = tempfile.mkdtemp()
        try:
            spec_file = os.path.join(temp_dir, "test_Specular.png")
            img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))
            ImgUtils.save_image(img, spec_file)

            self.mock_sb.file_dialog.return_value = [spec_file]
            self.mock_widget.option_box.menu.chk000.isChecked.return_value = False

            with patch(
                "pythontk.img_utils.map_factory.MapFactory.prepare_maps"
            ) as mock_prepare:
                mock_prepare.return_value = [spec_file]

                self.converter.tb001(self.mock_widget)

                # Verify workflow_config was passed correctly
                if not mock_prepare.called:
                    print(
                        f"DEBUG: mock_prepare not called. file_dialog called: {self.mock_sb.file_dialog.called}"
                    )
                    if self.mock_sb.file_dialog.called:
                        print(
                            f"DEBUG: file_dialog return: {self.mock_sb.file_dialog.return_value}"
                        )
                    else:
                        print("DEBUG: file_dialog NOT called")

                self.assertTrue(mock_prepare.called)
                call_args = mock_prepare.call_args
                # workflow_config is now passed as kwargs
                kwargs = call_args[1]

                self.assertFalse(kwargs.get("albedo_transparency"))
                self.assertFalse(kwargs.get("metallic_smoothness"))
                self.assertEqual(kwargs.get("normal_type"), "OpenGL")

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_with_mixed_resolution_textures(self):
        """Test tb001 handles textures with different resolutions."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create textures with different sizes
            spec_512 = os.path.join(temp_dir, "model_Specular.png")
            gloss_1024 = os.path.join(temp_dir, "model_Glossiness.png")

            img_512 = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))
            img_1024 = ImgUtils.create_image("L", (1024, 1024), 128)

            ImgUtils.save_image(img_512, spec_512)
            ImgUtils.save_image(img_1024, gloss_1024)

            self.mock_sb.file_dialog.return_value = [spec_512, gloss_1024]

            # Should process (factory may handle resolution mismatch)
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_empty_texture_set(self):
        """Test tb001 with empty file list."""
        self.mock_sb.file_dialog.return_value = []

        # Should return early without error
        result = self.converter.tb001(self.mock_widget)
        self.assertIsNone(result)

    def test_source_dir_persistence(self):
        """Test source_dir is updated after tb001 processing."""
        temp_dir = tempfile.mkdtemp()
        try:
            spec_file = os.path.join(temp_dir, "test_Specular.png")
            img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))
            ImgUtils.save_image(img, spec_file)

            self.mock_sb.file_dialog.return_value = [spec_file]

            # Process and verify source_dir is set
            self.converter.tb001(self.mock_widget)

            # source_dir should be updated to the texture directory
            self.assertIsNotNone(self.converter.source_dir)

        finally:
            shutil.rmtree(temp_dir)

class TestMapConverterMethods(unittest.TestCase):
    """Tests for ConverterSlots individual button methods (b004-b010)."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="converter_methods_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        self.mock_sb = Mock()
        self.mock_sb.file_dialog = Mock(return_value=None)
        self.converter = ConverterSlots(self.mock_sb)

        # Mock UI
        self.mock_widget = Mock()
        self.mock_widget.option_box.menu = Mock()
        self.converter.ui = self.mock_widget

    def create_dummy_image(self, name, mode="RGB"):
        path = os.path.join(self.test_files_dir, name)
        img = ImgUtils.create_image(mode, (64, 64), 128)
        ImgUtils.save_image(img, path)
        return path

    def test_b004_pack_transparency(self):
        """Test b004: Pack Transparency into Albedo."""
        albedo = self.create_dummy_image("mat_Albedo.png")
        opacity = self.create_dummy_image("mat_Opacity.png", "L")

        self.mock_sb.file_dialog.return_value = [albedo, opacity]

        with patch.object(
            TextureMapFactory,
            "pack_transparency_into_albedo",
            return_value="packed.png",
        ) as mock_method:
            self.converter.b004()
            mock_method.assert_called()

    def test_b007_unpack_specular_gloss(self):
        """Test b007: Unpack SpecularGloss."""
        sg = self.create_dummy_image("mat_SpecularGloss.png", "RGBA")
        self.mock_sb.file_dialog.return_value = [sg]

        with patch.object(
            TextureMapFactory, "unpack_specular_gloss", return_value=("s.png", "g.png")
        ) as mock_method:
            self.converter.b007()
            mock_method.assert_called()

    def test_b010_convert_smoothness_roughness(self):
        """Test b010: Convert Smoothness to Roughness."""
        smooth = self.create_dummy_image("mat_Smoothness.png", "L")
        self.mock_sb.file_dialog.return_value = [smooth]

        with patch.object(
            TextureMapFactory,
            "convert_smoothness_to_roughness",
            return_value="rough.png",
        ) as mock_method:
            self.converter.b010()
            mock_method.assert_called()

    def test_b011_convert_roughness_smoothness(self):
        """Test b011: Convert Roughness to Smoothness."""
        rough = self.create_dummy_image("mat_Roughness.png", "L")
        self.mock_sb.file_dialog.return_value = [rough]

        with patch.object(
            TextureMapFactory,
            "convert_roughness_to_smoothness",
            return_value="smooth.png",
        ) as mock_method:
            self.converter.b011()
            mock_method.assert_called()

    def test_tb003_convert_bump_normal(self):
        """Test tb003: Convert Bump to Normal."""
        bump = self.create_dummy_image("mat_Bump.png", "L")
        self.mock_sb.file_dialog.return_value = [bump]

        # Mock UI elements used in tb003
        self.mock_widget.option_box.menu.tb003_cmb_format.currentText.return_value = "OpenGL"
        self.mock_widget.option_box.menu.tb003_dsb_intensity.value.return_value = 1.0

        with patch.object(
            TextureMapFactory, "convert_bump_to_normal", return_value="normal.png"
        ) as mock_method:
            self.converter.tb003(self.mock_widget)
            mock_method.assert_called()

class TestMapConverterIntegration(unittest.TestCase):
    """
    Integration tests for ConverterSlots running against the real TextureMapFactory.
    No mocks on the factory methods to ensure true end-to-end validity.
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="converter_integration_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        self.mock_sb = Mock()
        self.mock_sb.file_dialog = Mock(return_value=None)
        self.converter = ConverterSlots(self.mock_sb)

        # Mock UI (needed for parameter retrieval)
        self.mock_widget = Mock()
        self.mock_widget.option_box.menu = Mock()
        self.converter.ui = self.mock_widget

    def create_test_image(self, name, mode="RGB", color=128):
        path = os.path.join(self.test_files_dir, name)
        img = ImgUtils.create_image(mode, (64, 64), color)
        ImgUtils.save_image(img, path)
        return path

    def test_b004_pack_transparency_real(self):
        """Integration: Pack Transparency into Albedo (Real File I/O)."""
        albedo_path = self.create_test_image("mat_Albedo.png", "RGB", (255, 0, 0))
        opacity_path = self.create_test_image("mat_Opacity.png", "L", 128)

        self.mock_sb.file_dialog.return_value = [albedo_path, opacity_path]

        # Run the actual method
        self.converter.b004()

        # Verify output
        expected_output = os.path.join(
            self.test_files_dir, "mat_AlbedoTransparency.png"
        )
        self.assertTrue(os.path.exists(expected_output), "Packed file was not created")

        # Verify content
        with Image.open(expected_output) as img:
            self.assertEqual(img.mode, "RGBA")
            # Check alpha value (should be 128 from opacity map)
            alpha = img.split()[3]
            self.assertEqual(alpha.getpixel((0, 0)), 128)

    def test_b010_convert_smoothness_roughness_real(self):
        """Integration: Convert Smoothness to Roughness (Real File I/O)."""
        smoothness_path = self.create_test_image("mat_Smoothness.png", "L", 100)
        self.mock_sb.file_dialog.return_value = [smoothness_path]

        self.converter.b010()

        expected_output = os.path.join(self.test_files_dir, "mat_Roughness.png")
        self.assertTrue(os.path.exists(expected_output))

        with Image.open(expected_output) as img:
            # Roughness = 255 - Smoothness = 255 - 100 = 155
            self.assertEqual(img.getpixel((0, 0)), 155)

    def test_tb003_convert_bump_normal_real(self):
        """Integration: Convert Bump to Normal (Real File I/O)."""
        bump_path = self.create_test_image("mat_Bump.png", "L", 128)
        self.mock_sb.file_dialog.return_value = [bump_path]

        # Mock UI options
        self.mock_widget.option_box.menu.tb003_cmb_format.currentData.return_value = "opengl"
        self.mock_widget.option_box.menu.tb003_cmb_format.currentText.return_value = "OpenGL"
        self.mock_widget.option_box.menu.tb003_dsb_intensity.value.return_value = 1.0

        self.converter.tb003(self.mock_widget)

        expected_output = os.path.join(self.test_files_dir, "mat_Normal_OpenGL.png")
        self.assertTrue(os.path.exists(expected_output))

        with Image.open(expected_output) as img:
            self.assertEqual(img.mode, "RGB")
            # Flat bump (128) should result in flat normal (128, 128, 255) roughly
            # Exact values depend on filter implementation, but should be close to blue
            r, g, b = img.getpixel((32, 32))
            self.assertTrue(b > r and b > g)

class TestMapConverterFlipChannels(unittest.TestCase):
    """Tests for the Flip Channels tool (tb002) — invert / swizzle / constant-fill."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="converter_flip_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        # MagicMock so ``with sb.progress(...) as update:`` works out of the box.
        self.mock_sb = MagicMock()
        self.mock_sb.file_dialog = Mock(return_value=None)
        self.converter = ConverterSlots(self.mock_sb)

    def create_test_image(self, name, mode="RGB", color=128):
        path = os.path.join(self.test_files_dir, name)
        ImgUtils.save_image(ImgUtils.create_image(mode, (64, 64), color), path)
        return path

    def _widget(self, r="R", g="G", b="B", a="A", suffix=""):
        """Build a mock toolbutton whose option menu returns the given tokens."""
        widget = MagicMock()
        menu = widget.option_box.menu
        menu.cmb_r.currentData.return_value = r
        menu.cmb_g.currentData.return_value = g
        menu.cmb_b.currentData.return_value = b
        menu.cmb_a.currentData.return_value = a
        menu.txt_suffix.text.return_value = suffix
        return widget

    def test_tb002_init_identity_defaults(self):
        """The option menu builds 4 source combos + a suffix field, defaulting to identity."""
        widget = MagicMock()
        self.converter.tb002_init(widget)

        added = [c.args[0] for c in widget.option_box.menu.add.call_args_list]
        self.assertEqual(added.count("QComboBox"), 4)
        self.assertEqual(added.count("QLineEdit"), 1)

        for idx, ch in enumerate("rgba"):
            combo = getattr(widget.option_box.menu, f"cmb_{ch}")
            combo.setCurrentIndex.assert_called_once_with(idx)

    def test_tb002_invert_channel_with_suffix(self):
        """An inverted source ('-G') inverts that output channel; suffix saves a copy."""
        path = self.create_test_image("flip_N.png", "RGB", (10, 200, 30))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(g="-G", suffix="_flip"))

        out = os.path.join(self.test_files_dir, "flip_N_flip.png")
        self.assertTrue(os.path.exists(out))
        with Image.open(out) as img:
            self.assertEqual(img.getpixel((0, 0))[:3], (10, 55, 30))  # 255-200

    def test_tb002_swap_channels_overwrite(self):
        """Swizzling R↔B swaps those channels; empty suffix overwrites in place."""
        path = self.create_test_image("flip_Swap.png", "RGB", (10, 20, 30))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(r="B", b="R"))

        with Image.open(path) as img:
            self.assertEqual(img.getpixel((0, 0))[:3], (30, 20, 10))

    def test_tb002_constant_alpha_fill(self):
        """A '1' source writes a constant-white channel (e.g. force opaque alpha)."""
        path = self.create_test_image("flip_RGBA.png", "RGBA", (10, 20, 30, 40))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(a="1", suffix="_op"))

        out = os.path.join(self.test_files_dir, "flip_RGBA_op.png")
        with Image.open(out) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.getpixel((0, 0)), (10, 20, 30, 255))

    def test_tb002_identity_no_suffix_is_noop(self):
        """All-identity sources with no suffix short-circuits — no file is touched."""
        path = self.create_test_image("flip_Identity.png", "RGB", (10, 20, 30))
        self.mock_sb.file_dialog.return_value = [path]

        with patch.object(self.converter, "_flip_one") as mock_flip:
            self.converter.tb002(self._widget())
            mock_flip.assert_not_called()

    def test_tb002_add_alpha_to_rgb(self):
        """Pointing the A slot at a real source promotes an RGB map to RGBA."""
        path = self.create_test_image("flip_AddA.png", "RGB", (10, 20, 30))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(a="R", suffix="_rgba"))

        out = os.path.join(self.test_files_dir, "flip_AddA_rgba.png")
        with Image.open(out) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.getpixel((0, 0)), (10, 20, 30, 10))  # A ← R

    def test_tb002_invert_grayscale_stays_grayscale(self):
        """A pure invert preserves a grayscale map's mode (no RGB promotion)."""
        path = self.create_test_image("flip_Gray.png", "L", 100)
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(r="-R", suffix="_inv"))

        out = os.path.join(self.test_files_dir, "flip_Gray_inv.png")
        with Image.open(out) as img:
            self.assertEqual(img.mode, "L")
            self.assertEqual(img.getpixel((0, 0)), 155)  # 255-100


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
