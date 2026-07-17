# !/usr/bin/python
# coding=utf-8
"""Contract tests: every op module's ``@register`` decorators wire the
expected op names and parameters.

This is the agent-facing surface — changes here are intentional API edits.
"""
import os
import sys
import unittest

try:
    from .base_test import SubstanceWorkflowTestCase
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_test import SubstanceWorkflowTestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from extapps.substance_workflow import registry


class _OpsContractMixin:
    """Mixin (not a TestCase — so unittest doesn't try to instantiate)."""

    MODULE: str = ""
    EXPECTED_OPS: dict = {}

    def setUp(self) -> None:  # type: ignore[override]
        super().setUp()  # type: ignore[misc]
        if self.MODULE:
            __import__(self.MODULE)

    def test_all_expected_ops_registered(self) -> None:
        for op_name, expected_params in self.EXPECTED_OPS.items():
            with self.subTest(op=op_name):  # type: ignore[attr-defined]
                fn = registry.get(op_name)
                self.assertIsNotNone(  # type: ignore[attr-defined]
                    fn, f"{op_name} not registered"
                )
                d = registry.describe(op_name)
                params = d.get("parameters", {})
                for p in expected_params:
                    self.assertIn(  # type: ignore[attr-defined]
                        p, params, f"{op_name} missing param {p}"
                    )


class TestProjectOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.project_utils"
    EXPECTED_OPS = {
        "project.info": [],
        "project.open": ["path"],
        "project.save": [],
        "project.save_as": ["path"],
        "project.close": [],
        "project.create": ["mesh_path", "template_path"],
        "project.reload_mesh": ["mesh_path"],
    }


class TestTextureSetOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.texture_set_utils"
    EXPECTED_OPS = {
        "texture_set.list": [],
        "texture_set.resolution": ["name"],
        "texture_set.set_resolution": ["name", "width", "height"],
        "texture_set.channels": ["name"],
        "texture_set.add_channel": ["name", "channel", "fmt"],
    }


class TestLayerOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.layer_utils"
    EXPECTED_OPS = {
        "layer.list": ["texture_set"],
        "layer.add_fill": ["texture_set", "name", "color"],
        "layer.add_paint": ["texture_set", "name"],
        "layer.add_group": ["texture_set", "name"],
        "layer.delete": ["texture_set", "uid"],
        "layer.set_opacity": ["texture_set", "uid", "channel", "opacity"],
        "layer.set_blend_mode": ["texture_set", "uid", "channel", "mode"],
    }


class TestChannelOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.channel_utils"
    EXPECTED_OPS = {
        "channel.list_formats": [],
        "channel.format": ["texture_set", "channel"],
        "channel.set_format": ["texture_set", "channel", "fmt"],
        "channel.export_path": ["texture_set", "channel"],
    }


class TestMaterialOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.material_utils"
    EXPECTED_OPS = {
        "material.list_shelf": [],
        "material.apply_smart": ["texture_set", "material_url", "target_layer_uid"],
        "material.import_to_shelf": ["path", "shelf_name"],
    }


class TestBakeOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.bake_utils"
    EXPECTED_OPS = {
        "bake.lighting_to_diffuse": [
            "texture_set",
            "bake_resolution",
            "ao_intensity",
            "ao_secondary_rays",
            "ao_max_distance",
            "include_curvature",
            "curvature_intensity",
            "layer_name",
            "blend_mode",
            "save_project",
        ],
        "bake.mesh_maps": ["texture_set", "maps", "high_poly"],
        "bake.all_texture_sets": ["maps"],
        "bake.set_resolution": ["texture_set", "width", "height"],
    }


class TestExportOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.export_utils"
    EXPECTED_OPS = {
        "export.list_presets": [],
        "export.textures": [
            "output_path",
            "preset",
            "texture_sets",
            "file_format",
            "bit_depth",
        ],
        "export.preset_to_dict": ["preset"],
    }


class TestResourceOps(_OpsContractMixin, SubstanceWorkflowTestCase):
    MODULE = "extapps.substance_workflow.resource_utils"
    EXPECTED_OPS = {
        "resource.list_shelves": [],
        "resource.list_assets": ["shelf", "kind"],
        "resource.import": ["path", "shelf", "kind"],
    }


class TestBridgeOpModuleList(SubstanceWorkflowTestCase):
    """The bridge plugin's ``OP_MODULES`` list covers every op module on disk.

    An op module absent from ``OP_MODULES`` imports fine in tests but never
    loads inside Painter — its ops silently don't exist there.
    """

    def test_op_modules_match_disk(self) -> None:
        from extapps.substance_workflow.plugins import substance_workflow_bridge

        pkg_dir = os.path.join(REPO_ROOT, "extapps", "substance_workflow")
        on_disk = {
            f"extapps.substance_workflow.{f[:-3]}"
            for f in os.listdir(pkg_dir)
            if f.endswith("_utils.py")
        }
        self.assertEqual(set(substance_workflow_bridge.OP_MODULES), on_disk)


if __name__ == "__main__":
    unittest.main()
