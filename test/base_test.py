# !/usr/bin/python
# coding=utf-8
"""Base Test Class for extapps.substance_workflow Tests.

Provides common functionality for all extapps.substance_workflow test cases.
"""
import os
import shutil
import sys
import tempfile
import unittest

scripts_dir = r"O:\Cloud\Code\_scripts"
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)


class SubstanceWorkflowTestCase(unittest.TestCase):
    """Base class for all extapps.substance_workflow test cases."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up once for all tests in the class."""
        pass

    def setUp(self) -> None:
        """Set up for each test."""
        super().setUp()
        self.temp_dirs = []

    def tearDown(self) -> None:
        """Clean up after each test."""
        for d in self.temp_dirs:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d)
                except Exception as e:
                    print(f"Warning: Failed to remove temp dir {d}: {e}")
        super().tearDown()

    def create_temp_dir(self) -> str:
        """Create a temporary directory that cleans up automatically."""
        tmp = tempfile.mkdtemp()
        self.temp_dirs.append(tmp)
        return tmp
