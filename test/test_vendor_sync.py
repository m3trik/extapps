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
* Substance engine (``_substance_engine.py``: the DCC-free Painter half each
  ``SubstanceBridge`` subclasses; byte-identical, mayatk's copy is the SSoT) +
  connection + parameters + RPC client/installer/plugin + templates —
  ``mayatk.mat_utils.substance_bridge`` / ``blendertk.mat_utils.substance_bridge``
  (extapps' ``substance_workflow`` is a separate native in-Painter engine and
  is NOT a copy).
* Curtain drape engine — ``mayatk.edit_utils.curtain._curtain_drape`` /
  ``blendertk.edit_utils.curtain._curtain_drape``. Not app glue but a single tool's
  displacement math: pythontk keeps only the general primitives it composes
  (``RailSurface``/``Polyline``/``MathUtils``/``BandLimitedNoise``), so the
  curtain-specific remainder is vendored with its two consumers.
* Unity panel mixin — ``_unity_panel.py`` (``UnityPanelMixin``) in
  ``mayatk.env_utils.unity_bridge`` / ``blendertk.env_utils.unity_bridge`` /
  ``extapps.unity_workflow``: the project row, mode combo, Editor combo and
  script management all three Unity panels share. unitytk is optional in each
  host and Qt-free, and uitk carries no app vocabulary, so no importable home
  exists.

That duplication is only safe if a fix to one copy is mirrored into the
others; this test fails the moment the shared files diverge, so drift is
caught at test time instead of shipping.

Two comparison contracts:

* **extapps ↔ mayatk (Marmoset, Unity panel mixin)** — strict content equality
  (line-ending tolerant) over an explicit vendored-file manifest: the panel's
  copy is kept byte-identical to mayatk's (the Unity mixin: to blendertk's too).
* **mayatk ↔ blendertk** — *semantic twin* equality. A twin is "the same
  file except for which DCC it names", so the compare normalizes exactly
  that before asserting: docstrings collapse to a placeholder (they
  legitimately self-reference their own package), and the host vocabulary
  (Maya↔Blender, mayatk↔blendertk, mtk↔btk, …) folds to neutral tokens.
  Everything else — code, comments, formatting — stays guarded.

  Normalizing rather than exempting is what keeps this honest. The
  alternative, adding a per-case exemption each time a twin says "Maya" in
  a tooltip or a Lua comment, ends with a guard that no longer compares
  anything. These files are *declared* twins; a difference that is only
  "which DCC is named" is by construction fine, and any other difference
  still fails.

Every file in a guarded tree must be classified — vendored (compared),
intentionally divergent, or panel/DCC-specific — so a file added to one
copy fails the guard instead of silently escaping it.

Runs only in the monorepo layout (siblings checked out); skips cleanly in a
standalone extapps checkout.
"""

import ast
import os
import sys
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
#
# The normalizer is NOT defined here. It is the single source of truth in
# m3trik/scripts/check_dcc_twins.py, which m3trik's CI runs against the whole
# monorepo as a --check gate. It lived here first, and keeping a second copy
# beside it would be the exact drift this file exists to prevent -- on the one
# piece of code whose correctness decides whether every OTHER twin comparison
# means anything.
#
# m3trik is a sibling repo, so a standalone extapps checkout has no access to
# it. That is a SKIP, never an error: a collection error would take the whole
# module down, including the cases that need no siblings at all.
_M3TRIK_SCRIPTS = _repo_root() / "m3trik" / "scripts"
if str(_M3TRIK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_M3TRIK_SCRIPTS))
try:
    import check_dcc_twins as _twins
except ImportError as exc:  # pragma: no cover - standalone checkout
    raise unittest.SkipTest(
        "m3trik sibling not checked out; the twin normalizer lives in "
        "m3trik/scripts/check_dcc_twins.py (%s)" % exc
    )

_fold_hosts = _twins.fold_hosts
_collapse_docstrings = _twins.collapse_docstrings
_host_normalized = _twins.host_normalized
_comment_stripped = _twins.comment_stripped
_twin_normalized = _twins.twin_normalized


def _lines(path: Path):
    return path.read_text(encoding="utf-8").splitlines()


def _assert_code_identical(
    test: unittest.TestCase, a: Path, b: Path, rel: str, hint: str
):
    """Strict line compare, then one normalized re-compare.

    The normalizer removes exactly the categories a declared twin may legitimately
    differ in (docstrings, `--` comment blocks, host vocabulary in prose); anything
    left over is real drift.
    """
    a_lines, b_lines = _lines(a), _lines(b)
    if a_lines == b_lines:
        return
    if _twin_normalized(a_lines, rel) == _twin_normalized(b_lines, rel):
        return

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
                _lines(may_f),
                _lines(ext_f),
                f"vendored Marmoset file '{rel}' has drifted between "
                f"mayatk.mat_utils.marmoset_bridge and extapps.marmoset_workflow. "
                f"Mirror the change into both copies (extapps CLAUDE.md hard rule), "
                f"or reclassify it if the difference is by design.",
            )

    def test_panel_files_all_classified(self):
        classified = set(MARMOSET_PANEL_VENDORED) | INTENTIONALLY_DIVERGENT | PANEL_ONLY
        present = {
            rel
            for rel in _rel_files(self.ext_dir)
            if not rel.endswith("_ui.py")  # generated by the uitk loader
        }
        self.assertLessEqual(
            present,
            classified,
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

SUBSTANCE_ENGINE_TOP = ("_substance_engine.py", "connection.py", "parameters.py")
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
                _rel_files(may_sub),
                _rel_files(ble_sub),
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
                present,
                classified,
                f"unclassified top-level entries {sorted(present - classified)} in "
                f"{pkg}'s {'.'.join(self.subpath)} — vendor-mirror (add to the "
                f"engine lists) or ledger as DCC-half",
            )


class TestMarmosetEngineDccSync(
    _TopLevelLedgerMixin, _DccPairSyncMixin, unittest.TestCase
):
    subpath = ("mat_utils", "marmoset_bridge")
    top_files = MARMOSET_ENGINE_TOP
    subdirs = MARMOSET_ENGINE_DIRS
    dcc_half_files = MARMOSET_DCC_HALF


class TestSubstanceEngineDccSync(
    _TopLevelLedgerMixin, _DccPairSyncMixin, unittest.TestCase
):
    subpath = ("mat_utils", "substance_bridge")
    top_files = SUBSTANCE_ENGINE_TOP
    subdirs = SUBSTANCE_ENGINE_DIRS
    dcc_half_files = SUBSTANCE_DCC_HALF

    def test_engine_is_byte_identical(self):
        """The engine's header declares it byte-identical, so compare it strictly.

        The twin compare above tolerates host vocabulary in prose. The engine is
        the one file here with no DCC half at all -- it names both hosts or
        neither, and imports only relatively -- so any difference is drift (the
        ``_unity_panel.py`` contract).
        """
        rel = "_substance_engine.py"
        self.assertEqual(
            _lines(self.may_dir / rel),
            _lines(self.ble_dir / rel),
            f"vendored '{rel}' has drifted between {self.hint}. Edit mayatk's "
            f"copy (the SSoT) and mirror it byte-for-byte into blendertk.",
        )

    def test_engine_imports_no_host(self):
        """The engine ships verbatim to both hosts, so it imports neither.

        A byte-identical engine that imported ``mayatk`` (or ``bpy``) would pass
        the identity check above and still break the other package: the one
        drift two equal copies can carry. Siblings come in relatively.
        """
        rel = "_substance_engine.py"
        tree = ast.parse((self.may_dir / rel).read_text(encoding="utf-8"))
        hosts = {"maya", "mayatk", "pymel", "bpy", "blendertk"}
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                roots = [node.module.split(".")[0]]
            else:
                continue
            found.extend(f"line {node.lineno}: {r}" for r in roots if r in hosts)
        self.assertEqual(
            found,
            [],
            f"'{rel}' imports a host package; move that call behind a DCC hook "
            f"on SubstanceBridge instead",
        )


class TestCurtainEngineDccSync(_DccPairSyncMixin, unittest.TestCase):
    subpath = ("edit_utils", "curtain")
    top_files = ("_curtain_drape.py",)


# ------------------------------------------------------- rizom + unity bridges
# These two were never guarded, and both had already drifted. Their engines ARE
# genuine per-DCC ports (Maya API vs bpy) and are NOT compared — but each carries
# a shared half that is pure target-language data, which is exactly what a guard
# is for.
#
# RizomUV: the `scripts/*.lua` presets are the UV algorithms themselves. Nothing
# in them is Maya- or Blender-specific, so a fix applied to one DCC's copy and not
# the other means one host silently keeps the broken behaviour.
RIZOM_SHARED_DIRS = ("scripts",)
RIZOM_DCC_HALF = (
    "__init__.py",
    "_rizom_bridge.py",
    "parameters.py",
    "rizom_bridge.ui",
    "rizom_bridge_slots.py",
    # NOT shared: mayatk drives the one-way send from `templates/send_wrapper.lua`
    # while blendertk builds the same script in `build_send_script()`. A real
    # structural divergence, ledgered here rather than silently normalized —
    # unifying it changes a shipped send path and needs a live pass per DCC.
    "templates",
)

UNITY_SHARED_TOP = ("parameters.py", "unity_bridge.ui", "_unity_panel.py")
UNITY_DCC_HALF = ("__init__.py", "_unity_bridge.py", "unity_bridge_slots.py")

# The Unity panel mixin: ONE file, byte-identical in all three Unity panels (SSoT:
# mayatk's copy). Strict, not twin-normalized: it names no host, so any difference
# is drift. Each entry: (package, package-relative dir, panel module, panel class).
UNITY_PANEL_MIXIN = "_unity_panel.py"
UNITY_PANEL_HOSTS = (
    (
        "mayatk",
        ("env_utils", "unity_bridge"),
        "unity_bridge_slots.py",
        "UnityBridgeSlots",
    ),
    (
        "blendertk",
        ("env_utils", "unity_bridge"),
        "unity_bridge_slots.py",
        "UnityBridgeSlots",
    ),
    ("extapps", ("unity_workflow",), "slots.py", "UnityWorkflowSlots"),
)
# extapps' panel dir, classified like the Marmoset panel's: a file added there must
# be ledgered as the vendored mixin or as panel-own.
UNITY_WORKFLOW_PANEL_ONLY = {
    "__init__.py",
    "launcher.py",
    "parameters.py",
    "slots.py",
    "unity_workflow.ui",
}


class TestHostNormalizer(unittest.TestCase):
    """The normalizer's own contract: fold what a twin may differ in, nothing else.

    This guard is only as good as its blind spots are narrow. Folding whole lines
    would make ``import mayatk`` inside blendertk compare equal to blendertk's own
    import - a real cross-wiring bug reported as clean. So for Python the fold is
    restricted to STRING and COMMENT tokens.
    """

    def _equal(self, a, b, code_aware=True):
        return _host_normalized([a], code_aware) == _host_normalized([b], code_aware)

    def test_prose_may_name_the_other_dcc(self):
        self.assertTrue(
            self._equal("x = 1  # the Maya bridge", "x = 1  # the Blender bridge")
        )
        self.assertTrue(self._equal('"""Maya side."""', '"""Blender side."""'))
        self.assertTrue(self._equal("s = 'mayatk'", "s = 'blendertk'"))

    def test_code_may_not(self):
        self.assertFalse(self._equal("import mayatk", "import blendertk"))
        self.assertFalse(self._equal("mtk.export(o)", "btk.export(o)"))
        self.assertFalse(self._equal("import maya.cmds as cmds", "import bpy"))

    def test_real_drift_still_fails_after_folding(self):
        self.assertFalse(self._equal("x = 1  # Maya", "x = 2  # Blender"))

    def test_a_multiline_string_does_not_fold_the_code_around_its_quotes(self):
        """The first/last spanned lines carry code the fold must not reach."""
        a = ['x = mtk.f("""Maya', 'more Maya text""") + mtk.g()']
        b = ['x = btk.f("""Blender', 'more Blender text""") + btk.g()']
        folded_a, folded_b = _host_normalized(a, True), _host_normalized(b, True)
        self.assertNotEqual(folded_a, folded_b)  # mtk vs btk survives
        self.assertIn("<dccname>", folded_a[0])  # the prose inside DID fold
        self.assertIn("mtk", folded_a[1])  # the trailing call did NOT

    def test_unparseable_python_does_not_fold_at_all(self):
        """A tokenize failure must not crash the guard, nor mask a cross-wiring.

        This pinned the whole-line fold until 2026-09-17, back when the
        assertion ran against a vendored copy of the normalizer. That fallback
        folded ``import mayatk`` and ``import blendertk`` to the same
        placeholder, so a twin that was BOTH cross-wired and unparseable
        compared equal and its ledger entry reported ``ok`` -- the one failure
        this normalizer exists to prevent, reached through its own error path.
        It now returns the lines unfolded: the two sides differ on host
        vocabulary and report ``drift``, a false alarm a maintainer reads and
        dismisses instead of a false all-clear nobody sees.
        """
        self.assertFalse(self._equal("def f(  # Maya", "def f(  # Blender"))
        self.assertFalse(self._equal("def f(  # Maya", "def g(  # Blender"))
        # The load-bearing case the old fallback masked.
        self.assertFalse(
            self._equal("import mayatk\ndef f(:", "import blendertk\ndef f(:")
        )
        # Still does not raise -- the other half of the original contract.
        self.assertTrue(_host_normalized(["def f(:"], True))

    def test_non_python_folds_whole_lines(self):
        # .lua / .ui carry no imports to mask, so the coarse fold is safe there.
        self.assertTrue(
            self._equal("-- Maya pack", "-- Blender pack", code_aware=False)
        )


class TestRizomScriptsDccSync(
    _TopLevelLedgerMixin, _DccPairSyncMixin, unittest.TestCase
):
    """The Lua presets are shared data; the engines around them are ports."""

    subpath = ("uv_utils", "rizom_bridge")
    top_files = ()
    subdirs = RIZOM_SHARED_DIRS
    dcc_half_files = RIZOM_DCC_HALF


class TestUnityBridgeDccSync(
    _TopLevelLedgerMixin, _DccPairSyncMixin, unittest.TestCase
):
    """The parameter registry + panel layout are shared; the export halves are ports."""

    subpath = ("env_utils", "unity_bridge")
    top_files = UNITY_SHARED_TOP
    dcc_half_files = UNITY_DCC_HALF


class TestUnityPanelMixinVendorSync(unittest.TestCase):
    """The three Unity panels share one ``UnityPanelMixin``, byte-identical."""

    def setUp(self):
        self.dirs = {}
        for pkg, parts, _module, _cls in UNITY_PANEL_HOSTS:
            if pkg == "extapps":
                d = Path(extapps.__file__).resolve().parent.joinpath(*parts)
            else:
                d = _sibling(pkg, *parts)
            if d is None:
                self.skipTest(
                    f"{pkg} sibling not present (standalone extapps checkout)"
                )
            self.dirs[pkg] = d

    def test_mixin_copies_are_content_identical(self):
        ssot = self.dirs["mayatk"] / UNITY_PANEL_MIXIN
        self.assertTrue(ssot.is_file(), f"missing {ssot}")
        for pkg, d in self.dirs.items():
            copy = d / UNITY_PANEL_MIXIN
            self.assertTrue(copy.is_file(), f"missing {copy}")
            self.assertEqual(
                _lines(ssot),
                _lines(copy),
                f"vendored '{UNITY_PANEL_MIXIN}' has drifted between mayatk (the "
                f"SSoT) and {pkg}. Edit mayatk's copy and mirror it into all three.",
            )

    def test_each_panel_lists_the_mixin_first(self):
        """First base, so its hooks override ``BridgeSlotsBase``'s defaults.

        Listed after the base, the mixin's ``template_dir`` / ``TEMPLATE_MENU`` /
        ``default_output_dir`` would lose the MRO to the base's, silently.
        """
        for pkg, _parts, module, cls_name in UNITY_PANEL_HOSTS:
            path = self.dirs[pkg] / module
            tree = ast.parse(path.read_text(encoding="utf-8"))
            cls = next(
                (
                    n
                    for n in tree.body
                    if isinstance(n, ast.ClassDef) and n.name == cls_name
                ),
                None,
            )
            self.assertIsNotNone(cls, f"{cls_name} not found in {path}")
            first = cls.bases[0] if cls.bases else None
            self.assertEqual(
                getattr(first, "id", None),
                "UnityPanelMixin",
                f"{pkg}'s {cls_name} must list UnityPanelMixin as its first base",
            )

    def test_extapps_panel_files_all_classified(self):
        classified = UNITY_WORKFLOW_PANEL_ONLY | {UNITY_PANEL_MIXIN}
        present = {
            rel
            for rel in _rel_files(self.dirs["extapps"])
            if not rel.endswith("_ui.py")  # generated by the uitk loader
        }
        self.assertLessEqual(
            present,
            classified,
            "unclassified files in extapps.unity_workflow: "
            f"{sorted(present - classified)} — ledger them in "
            "UNITY_WORKFLOW_PANEL_ONLY or vendor-mirror them",
        )


if __name__ == "__main__":
    unittest.main()
