# !/usr/bin/python
# coding=utf-8
"""Process-wide isolation for the extapps test suite.

Two real per-user stores are reachable from these tests without it:

1. **QSettings** — the panel tests build real Switchboard UIs and write
   widget values (e.g. ``TestPanelPresetResetsUnnamedKeys`` applies a preset
   that resets every un-named param); uitk's state restore persists them to
   the shared ``HKCU\\Software\\uitk`` hive on Windows. A plain test run
   would silently reset the developer's live panel session values — the same
   incident class uitk's own conftest sandbox was built for (see
   ``uitk/test/conftest.py``, the canonical implementation this mirrors).
2. **pythontk user-config root** — preset stores / profiles under
   ``<user-config>/uitk/...``; tests that save presets or scaffold profiles
   must not touch the real ones.

Activated at import time (not via a pytest fixture) so it also protects
direct ``unittest`` runs, and runs before the first ``QSettings`` /
``PresetStore`` is constructed.
"""
import atexit
import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="extapps_test_sandbox_")
atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))

# --- pythontk user-config root (preset stores, photogrammetry profiles) ----
from pythontk.core_utils.user_config import CONFIG_ROOT_ENV_VAR  # noqa: E402

os.environ.setdefault(CONFIG_ROOT_ENV_VAR, os.path.join(_TMP, "cfg"))


def _sandbox_qsettings() -> str:
    """Steer every QSettings overload off the real per-user store.

    On Windows, ``QSettings(org, app)`` / ``QSettings(scope, org, app)``
    ALWAYS use NativeFormat (the registry) and ignore ``setDefaultFormat`` /
    ``setPath`` — the only reliable redirect is rewriting those overloads to
    the explicit IniFormat constructor. Mirror of uitk's conftest sandbox.
    """
    from qtpy import QtCore

    tmp = os.path.join(_TMP, "qsettings")
    os.makedirs(tmp, exist_ok=True)
    real = QtCore.QSettings
    ini, user = real.IniFormat, real.UserScope

    for scope in (real.UserScope, real.SystemScope):
        real.setPath(ini, scope, tmp)
    real.setDefaultFormat(ini)

    class _SandboxedQSettings(real):
        def __init__(self, *args, **kwargs):
            if (
                len(args) >= 2
                and isinstance(args[0], str)
                and isinstance(args[1], str)
            ):
                # (org, app[, parent]) -> (Ini, UserScope, org, app[, parent])
                super().__init__(ini, user, *args, **kwargs)
            elif (
                len(args) >= 3
                and isinstance(args[1], str)
                and isinstance(args[2], str)
            ):
                # (scope, org, app[, parent]) -> (Ini, scope, org, app[, parent])
                super().__init__(ini, *args, **kwargs)
            else:
                super().__init__(*args, **kwargs)

    QtCore.QSettings = _SandboxedQSettings
    return tmp


QSETTINGS_SANDBOX_DIR = _sandbox_qsettings()
