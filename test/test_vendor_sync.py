# !/usr/bin/python
# coding=utf-8
"""Guard: vendored engine copies must not drift from their twins.

The Marmoset Toolbag and Substance Painter engines are *app-specific* shells
(product discovery/launch, protocol dialect, in-app plugin, templates), so
they live with their consumers rather than in the app-agnostic pythontk —
pythontk keeps only the generic mechanism they compose (``HandoffBridge``,
``AppLauncher``, ``RpcClient``, ``process_stream``). Because the consumers
cannot import each other (mayatk ↔ blendertk ↔ extapps), each keeps a copy:

* Marmoset engine — ``mayatk.mat_utils.marmoset_bridge`` /
  ``blendertk.mat_utils.marmoset_bridge`` / ``extapps.marmoset_workflow``
  (the panel vendors the import/lookdev subset: no ``marmoset_rpc``, no bake
  template).
* Substance connection + RPC client + templates —
  ``mayatk.mat_utils.substance_bridge`` / ``blendertk.mat_utils.substance_bridge``
  (extapps' ``substance_workflow`` is a separate native in-Painter engine and
  is NOT a copy).
* Curtain drape engine — ``mayatk.edit_utils._curtain_drape`` /
  ``blendertk.edit_utils._curtain_drape``. Not app glue but a single tool's
  displacement math: pythontk keeps only the general primitives it composes
  (``RailSurface``/``Polyline``/``MathUtils``/``BandLimitedNoise``), so the
  curtain-specific remainder is vendored with its two consumers.

That duplication is only safe if a fix to one copy is mirrored into the
others; this test fails the moment the shared files diverge, so drift is
caught at test time instead of shipping.

Two comparison contracts:

* **extapps ↔ mayatk (Marmoset)** — strict content equality (line-ending
  tolerant) over an explicit vendored-file manifest: the panel's copy is
  kept byte-identical to mayatk's.
* **mayatk ↔ blendertk (both engines)** — *code* equality: docstrings may
  legitimately self-reference their own package (``marmoset_rpc``'s module
  docs do), so when the strict line compare differs, files are re-compared
  with each docstring collapsed to a placeholder. Comments and formatting
  outside docstrings stay guarded.

Every file in a guarded tree must be classified — vendored (compared),
intentionally divergent, or panel/DCC-specific — so a file added to one
copy fails the guard instead of silently escaping it.

Runs only in the monorepo layout (siblings checked out); skips cleanly in a
standalone extapps checkout.
"""
import ast
import os
import unittest
from pathlib import Path

import extapps


# ---------------------------------------------------------------- discovery
def _repo_root() -> Path:
    ext_pkg = Path(extapps.__file__).resolve().parent  # .../extapps/extapps
    return ext_pkg.parents[1]  # .../<monorepo root>


def _sibling(package: str, *parts: str):
    """``<root>/<pkg>/<pkg>/<parts...>`` if checked out, else ``None``."""
    d = _repo_root() / package / package
    for p in parts:
        d = d / p
    return d if d.is_dir() else None


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


# ---------------------------------------------------------------- comparison
def _lines(path: Path):
    return path.read_text(encoding="utf-8").splitlines()


def _docstring_normalized_lines(path: Path):
    """Source lines with each docstring collapsed to a one-line placeholder.

    Lets per-package docstrings (module-path self-references) diverge while
    keeping everything else — code, comments, formatting — line-comparable.
    """
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    drop = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                doc = body[0].value
                lines[doc.lineno - 1] = '"""<doc>"""'
                drop.update(range(doc.lineno, doc.end_lineno))
    return [ln for i, ln in enumerate(lines) if i not in drop]


def _assert_code_identical(test: unittest.TestCase, a: Path, b: Path, rel: str, hint: str):
    """Strict line compare; on mismatch, re-compare with docstrings collapsed."""
    a_lines, b_lines = _lines(a), _lines(b)
    if a_lines == b_lines:
        return
    if rel.endswith(".py"):
        try:
            if _docstring_normalized_lines(a) == _docstring_normalized_lines(b):
                return  # docstrings diverged, code/comments identical — accepted
        except SyntaxError:
            pass  # unparseable -> fall through to the strict failure
    test.fail(
        f"vendored file '{rel}' has drifted between {hint}. "
        f"Mirror the change into both copies (extapps CLAUDE.md hard rule)."
    )


# ------------------------------------------------- extapps <-> mayatk (strict)
# The vendored subset, ledgered explicitly — an intersection compare would
# silently unguard a file deleted from (or never mirrored into) one copy.
# extapps vendors the import/lookdev panel slice: no marmoset_rpc, no bake
# template.
MARMOSET_PANEL_VENDORED = (
    "_marmoset_engine.py",
    "_toolbag_helpers.py",
    "template_params.py",
    "toolbag_log.py",
    os.path.join("templates", "__init__.py"),
    os.path.join("templates", "import.py"),
    os.path.join("templates", "lookdev.py"),
)
# Same-named but per-panel by design, never compared:
#   * parameters.py  — the Maya panel surfaces the full bake parameter set; the
#     standalone panel surfaces only the import/lookdev look-dev knobs.
#   * __init__.py    — different package: the bridge vs. the launcher+slots app.
INTENTIONALLY_DIVERGENT = {"parameters.py", "__init__.py"}
# The panel's own (non-engine) files. A file added to the panel must be
# classified here or above, else the guard fails instead of ignoring it.
PANEL_ONLY = {"launcher.py", "slots.py", "marmoset_workflow.ui"}


class TestMarmosetEngineVendorSync(unittest.TestCase):
    """extapps' Marmoset engine subset stays byte-identical to mayatk's."""

    def setUp(self):
        self.ext_dir = Path(extapps.__file__).resolve().parent / "marmoset_workflow"
        self.may_dir = _sibling("mayatk", "mat_utils", "marmoset_bridge")
        if self.may_dir is None:
            self.skipTest("mayatk sibling not present (standalone extapps checkout)")

    def test_vendored_files_are_content_identical(self):
        for rel in MARMOSET_PANEL_VENDORED:
            may_f, ext_f = self.may_dir / rel, self.ext_dir / rel
            self.assertTrue(may_f.is_file(), f"missing {may_f}")
            self.assertTrue(ext_f.is_file(), f"missing {ext_f}")
            self.assertEqual(
                _lines(may_f), _lines(ext_f),
                f"vendored Marmoset file '{rel}' has drifted between "
                f"mayatk.mat_utils.marmoset_bridge and extapps.marmoset_workflow. "
                f"Mirror the change into both copies (extapps CLAUDE.md hard rule), "
                f"or reclassify it if the difference is by design.",
            )

    def test_panel_files_all_classified(self):
        classified = set(MARMOSET_PANEL_VENDORED) | INTENTIONALLY_DIVERGENT | PANEL_ONLY
        present = {
            rel for rel in _rel_files(self.ext_dir)
            if not rel.endswith("_ui.py")  # generated by the uitk loader
        }
        self.assertLessEqual(
            present, classified,
            "unclassified files in extapps.marmoset_workflow: "
            f"{sorted(present - classified)} — mirror into MARMOSET_PANEL_VENDORED "
            "or ledger as PANEL_ONLY/INTENTIONALLY_DIVERGENT",
        )


# --------------------------------------------- mayatk <-> blendertk (code-equal)
# The vendored (engine) slice of each subpackage, plus an explicit ledger of
# the DCC-specific half (expected to differ, never compared). Every top-level
# entry must land in one list or the other — an unclassified addition fails.
MARMOSET_ENGINE_TOP = (
    "_marmoset_engine.py",
    "_toolbag_helpers.py",
    "template_params.py",
    "toolbag_log.py",
    "parameters.py",
)
MARMOSET_ENGINE_DIRS = ("templates", "marmoset_rpc")
MARMOSET_DCC_HALF = (
    "__init__.py",
    "_marmoset_bridge.py",
    "marmoset_bridge.ui",
    "marmoset_bridge_slots.py",
    "manifest.py",  # mayatk-only tool manifest
)

SUBSTANCE_ENGINE_TOP = ("connection.py", "parameters.py")
SUBSTANCE_ENGINE_DIRS = ("templates", "substance_rpc")
SUBSTANCE_DCC_HALF = (
    "__init__.py",
    "_substance_bridge.py",
    "substance_bridge.ui",
    "substance_bridge_slots.py",
    "manifest.py",  # mayatk-only tool manifest
)


class _DccPairSyncMixin:
    """Compare the vendored engine slice of a subpackage across the DCC pair."""

    subpath: tuple  # package-relative dir, e.g. ("mat_utils", "marmoset_bridge")
    top_files: tuple
    subdirs: tuple = ()

    def setUp(self):
        self.may_dir = _sibling("mayatk", *self.subpath)
        self.ble_dir = _sibling("blendertk", *self.subpath)
        if self.may_dir is None or self.ble_dir is None:
            self.skipTest("mayatk/blendertk sibling not present")
        dotted = ".".join(self.subpath)
        self.hint = f"mayatk.{dotted} and blendertk.{dotted}"

    def test_engine_subtree_file_sets_match(self):
        # A file added to only one copy is drift too — compare the sets.
        for sub in self.subdirs:
            may_sub, ble_sub = self.may_dir / sub, self.ble_dir / sub
            self.assertTrue(may_sub.is_dir(), f"missing {may_sub}")
            self.assertTrue(ble_sub.is_dir(), f"missing {ble_sub}")
            self.assertEqual(
                _rel_files(may_sub), _rel_files(ble_sub),
                f"'{self.subpath[-1]}/{sub}/' file sets differ between {self.hint}",
            )

    def test_engine_files_are_code_identical(self):
        rels = list(self.top_files)
        for sub in self.subdirs:
            rels.extend(
                os.path.join(sub, rel) for rel in sorted(_rel_files(self.may_dir / sub))
            )
        for rel in rels:
            may_f, ble_f = self.may_dir / rel, self.ble_dir / rel
            self.assertTrue(may_f.is_file(), f"missing {may_f}")
            self.assertTrue(ble_f.is_file(), f"missing {ble_f}")
            _assert_code_identical(self, may_f, ble_f, rel, self.hint)


class _TopLevelLedgerMixin:
    """Every top-level entry must be classified: engine, subdir, or DCC-half.

    Only for subpackages that are bridge-shaped end to end; the curtain pair
    lives inside the mixed ``edit_utils`` package, so it doesn't opt in.
    """

    dcc_half_files: tuple

    def test_top_level_entries_all_classified(self):
        classified = set(self.top_files) | set(self.subdirs) | set(self.dcc_half_files)
        for pkg, root in (("mayatk", self.may_dir), ("blendertk", self.ble_dir)):
            present = {
                p.name
                for p in root.iterdir()
                if p.name != "__pycache__"
                and not p.name.endswith((".pyc", "_ui.py"))  # *_ui.py is generated
            }
            self.assertLessEqual(
                present, classified,
                f"unclassified top-level entries {sorted(present - classified)} in "
                f"{pkg}'s {'.'.join(self.subpath)} — vendor-mirror (add to the "
                f"engine lists) or ledger as DCC-half",
            )


class TestMarmosetEngineDccSync(_TopLevelLedgerMixin, _DccPairSyncMixin, unittest.TestCase):
    subpath = ("mat_utils", "marmoset_bridge")
    top_files = MARMOSET_ENGINE_TOP
    subdirs = MARMOSET_ENGINE_DIRS
    dcc_half_files = MARMOSET_DCC_HALF


class TestSubstanceEngineDccSync(_TopLevelLedgerMixin, _DccPairSyncMixin, unittest.TestCase):
    subpath = ("mat_utils", "substance_bridge")
    top_files = SUBSTANCE_ENGINE_TOP
    subdirs = SUBSTANCE_ENGINE_DIRS
    dcc_half_files = SUBSTANCE_DCC_HALF


class TestCurtainEngineDccSync(_DccPairSyncMixin, unittest.TestCase):
    subpath = ("edit_utils",)
    top_files = ("_curtain_drape.py",)


if __name__ == "__main__":
    unittest.main()
