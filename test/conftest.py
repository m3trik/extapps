# !/usr/bin/python
# coding=utf-8
"""Process-wide isolation for the extapps test suite.

Two real per-user stores are reachable from these tests without it:

1. **QSettings** — the panel tests build real Switchboard UIs and write
   widget values (e.g. ``TestPanelPresetResetsUnnamedKeys`` applies a preset
   that resets every un-named param); uitk's state restore persists them to
   the shared ``HKCU\\Software\\uitk`` hive on Windows. A plain test run
   would silently reset the developer's live panel session values.
2. **pythontk user-config root** — preset stores / profiles under
   ``<user-config>/uitk/...``; tests that save presets or scaffold profiles
   must not touch the real ones.

Both redirects come from the ecosystem SSoT, ``uitk.testing.TestSandbox``
(this file used to carry a hand-rolled mirror of its QSettings overload
rewrite — one of three copies of that subtle fix, now retired). Activated at
import time (not via a pytest fixture), so it runs before the first
``QSettings`` / ``PresetStore`` is constructed. A module run directly
(``python test/<module>.py``) loads no conftest: a module whose tearDown
clears a panel's store activates the sandbox itself.
"""
import os

from uitk.testing import TestSandbox

# Headless unless a GUI is the point (CODE_STANDARD section 9): the panel tests
# build real Switchboard UIs, and only 3 of the 16 Qt modules asked for the
# offscreen platform themselves -- set it before any test constructs Qt. An
# explicit value is honored.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TestSandbox.activate()
