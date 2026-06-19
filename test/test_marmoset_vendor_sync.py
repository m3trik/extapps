# !/usr/bin/python
# coding=utf-8
"""Guard: the vendored Marmoset Toolbag engine must not drift from its twin.

``marmoset_workflow``'s Toolbag engine is *vendored* — kept byte-identical to
``mayatk.mat_utils.marmoset_bridge``'s copy (extapps ``CLAUDE.md`` hard rule),
because neither package can import the other (mayatk can't import extapps and
vice-versa). That duplication is only safe if a fix to one copy is mirrored into
the other; nothing enforced it, so a refactor that updated only the mayatk copy
silently desynced them. This test fails the moment the shared SDK-glue files
diverge, so the drift is caught at test time instead of shipping.

It compares *content* (line-ending tolerant): the two trees already differ only
by EOL on some shared files, and that's an accepted steady state — only real
code drift should fail. Runs only in the monorepo layout (mayatk as a sibling);
skips cleanly in a standalone extapps checkout where the twin isn't present.
"""
import os
import unittest
from pathlib import Path

import extapps


# Shared SDK-glue files are kept identical across the two copies. These two are
# intentionally per-panel and must NOT be compared:
#   * parameters.py  — the Maya panel surfaces the full bake parameter set; the
#     standalone panel surfaces only the import/lookdev look-dev knobs.
#   * __init__.py    — different package: the bridge vs. the launcher+slots app.
INTENTIONALLY_DIVERGENT = {"parameters.py", "__init__.py"}


def _shared_dirs():
    """``(extapps_dir, mayatk_dir)`` for the vendored engine, or ``(ext, None)``
    when the mayatk sibling isn't checked out (standalone extapps)."""
    ext_pkg = Path(extapps.__file__).resolve().parent  # .../extapps/extapps
    ext_dir = ext_pkg / "marmoset_workflow"
    repo_root = ext_pkg.parents[1]                      # .../<repo root>
    may_dir = repo_root / "mayatk" / "mayatk" / "mat_utils" / "marmoset_bridge"
    return ext_dir, (may_dir if may_dir.is_dir() else None)


def _rel_files(root: Path):
    """Relative paths of real source files under *root* (no __pycache__/.pyc)."""
    out = set()
    for dirpath, _dirs, files in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for fn in files:
            if fn.endswith(".pyc"):
                continue
            out.add(os.path.relpath(os.path.join(dirpath, fn), root))
    return out


class TestMarmosetEngineVendorSync(unittest.TestCase):
    def setUp(self):
        self.ext_dir, self.may_dir = _shared_dirs()
        if self.may_dir is None:
            self.skipTest("mayatk sibling not present (standalone extapps checkout)")

    def test_shared_engine_files_are_content_identical(self):
        shared = _rel_files(self.ext_dir) & _rel_files(self.may_dir)
        shared -= INTENTIONALLY_DIVERGENT
        self.assertIn(
            "_marmoset_engine.py", shared,
            "the vendored engine file should exist in both copies",
        )
        for rel in sorted(shared):
            ext_lines = (self.ext_dir / rel).read_text(encoding="utf-8").splitlines()
            may_lines = (self.may_dir / rel).read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                may_lines, ext_lines,
                f"vendored Marmoset file '{rel}' has drifted between "
                f"mayatk.mat_utils.marmoset_bridge and extapps.marmoset_workflow. "
                f"Mirror the change into both copies (extapps CLAUDE.md hard rule), "
                f"or add it to INTENTIONALLY_DIVERGENT if the difference is by design.",
            )


if __name__ == "__main__":
    unittest.main()
