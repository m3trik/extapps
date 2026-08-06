# !/usr/bin/python
# coding=utf-8
"""Base Test Class for extapps.substance_workflow Tests.

Provides common functionality for all extapps.substance_workflow test cases.
"""
import os
import shutil
import tempfile
import unittest

# NOTE: no ``sys.path`` bootstrap here. This used to insert a hardcoded
# ``O:\Cloud\Code\_scripts`` at position 0 — machine-specific (so it did
# nothing on any other checkout), unused (nothing in this suite imports a
# sibling repo by that route), and actively harmful: the monorepo root holds a
# bare directory per sibling, which Python then resolves as an empty
# **namespace** package outranking the real installed one. ``import unitytk``
# "succeeded" with ``__file__`` None and the Unity Workflow panel read its
# engine as not installed. Sibling packages are installed (editable) or on
# PYTHONPATH; that is the supported way to reach them.


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
