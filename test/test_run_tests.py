# !/usr/bin/python
# coding=utf-8
"""Tests for ``test/run_tests.py`` — the badge-stamping suite runner.

The runner publishes a number. Two ways that number can lie are already known
failures in this ecosystem (m3trik/docs/TEST_BADGE_STANDARD.md): a scoped run
overwriting a full run's badge with its smaller green, and a tally that counts
something other than individual test cases. Both are pinned here.
"""

import importlib.util
import types
import unittest
from pathlib import Path
from unittest import mock

import pythontk as ptk
from pythontk.core_utils.status_badge import StatusBadge

TEST_DIR = Path(__file__).resolve().parent


def _load_runner():
    """Import ``run_tests.py`` by path (it is a script, not an importable pkg)."""
    spec = importlib.util.spec_from_file_location(
        "extapps_run_tests", TEST_DIR / "run_tests.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rt = _load_runner()


def _report(nodeid, when="call", outcome="passed", context=None):
    """A stand-in for a pytest ``TestReport`` — only the fields the tally reads."""
    return types.SimpleNamespace(
        nodeid=nodeid,
        when=when,
        passed=outcome == "passed",
        failed=outcome == "failed",
        skipped=outcome == "skipped",
        context=context,
    )


class CollectorTallyTest(unittest.TestCase):
    """The tally counts individual test cases, skips excluded from passed."""

    def setUp(self):
        self.c = rt.ExtappsTestRunner.Collector()

    def test_counts_call_phase_outcomes(self):
        self.c.pytest_runtest_logreport(_report("test/test_a.py::T::test_ok"))
        self.c.pytest_runtest_logreport(
            _report("test/test_a.py::T::test_bad", outcome="failed")
        )
        self.c.pytest_runtest_logreport(
            _report("test/test_b.py::T::test_gated", when="setup", outcome="skipped")
        )
        self.assertEqual((self.c.passed, self.c.failed, self.c.skipped), (1, 1, 1))

    def test_subtest_reports_do_not_inflate_the_count(self):
        """``pytest-subtests`` emits an extra report per subtest, tagged with a
        ``context``. This suite runs 80+ of them; counting them would publish a
        badge higher than ``pytest test`` prints for the same run."""
        self.c.pytest_runtest_logreport(_report("test/test_a.py::T::test_many"))
        for i in range(5):
            self.c.pytest_runtest_logreport(
                _report("test/test_a.py::T::test_many", context=("i", i))
            )
        self.assertEqual(self.c.passed, 1)

    def test_setup_error_counts_as_a_failure(self):
        """An error before the call phase means the case never ran; a tally that
        only reads call-phase reports would publish it as neither."""
        self.c.pytest_runtest_logreport(
            _report("test/test_a.py::T::test_x", when="setup", outcome="failed")
        )
        self.assertEqual((self.c.passed, self.c.failed), (0, 1))

    def test_module_names_come_from_the_nodeid(self):
        self.c.pytest_runtest_logreport(_report("test/test_alpha.py::T::test_x"))
        self.c.pytest_runtest_logreport(_report("test/test_beta.py::T::test_y"))
        self.assertEqual(self.c.modules_ran, {"test_alpha", "test_beta"})

    def test_collect_failure_fails_the_run_without_crediting_the_module(self):
        """A module that fails to import contributes zero cases. Crediting it
        would let the gate stamp a badge for a suite that partly never loaded."""
        self.c.pytest_collectreport(
            types.SimpleNamespace(failed=True, nodeid="test/test_broken.py")
        )
        self.assertEqual(self.c.failed, 1)
        self.assertNotIn("test_broken", self.c.modules_ran)


class BadgeGateTest(unittest.TestCase):
    """A partial run must never stamp — the clobber this guard exists to stop."""

    def setUp(self):
        # Allocated under test/temp_tests/ rather than the system temp dir: the
        # badge href is a relpath from the README to the test dir, and on
        # Windows that is undefined across drives (the repo lives on one drive,
        # %TEMP% on another). Same-drive here mirrors the real README/test-dir
        # pair; the cross-drive case is covered by its own test below.
        self._store = ptk.TempArtifacts(
            "extapps_test_badge", policy="scoped", dir=str(TEST_DIR / "temp_tests")
        )
        self.readme = Path(self._store.path(extension=".md"))
        self.readme.write_text("# extapps\n\nbody\n", encoding="utf-8")

    def tearDown(self):
        self._store.cleanup()

    @staticmethod
    def _collector(modules, passed=10, failed=0):
        c = rt.ExtappsTestRunner.Collector()
        c.passed, c.failed = passed, failed
        c.modules_ran = set(modules)
        return c

    def test_full_run_stamps_the_real_count(self):
        every = StatusBadge.discover_module_names(TEST_DIR)
        self.assertTrue(every, "no test modules discovered")
        ok = rt.ExtappsTestRunner.stamp_badge(
            self._collector(every, passed=636), readme=self.readme
        )
        self.assertTrue(ok)
        text = self.readme.read_text(encoding="utf-8")
        self.assertIn("img.shields.io/badge/Tests-636%20passed-brightgreen", text)
        self.assertIn("[![Tests]", text)

    def test_scoped_run_is_refused(self):
        with mock.patch.object(StatusBadge, "update_test_badge") as write:
            allowed = rt.ExtappsTestRunner.stamp_badge(
                self._collector({"test_progress_notify"}), readme=self.readme
            )
        self.assertFalse(allowed)
        write.assert_not_called()
        self.assertNotIn("shields.io", self.readme.read_text(encoding="utf-8"))

    def test_run_that_produced_nothing_is_refused(self):
        every = StatusBadge.discover_module_names(TEST_DIR)
        with mock.patch.object(StatusBadge, "update_test_badge") as write:
            allowed = rt.ExtappsTestRunner.stamp_badge(
                self._collector(every, passed=0, failed=0), readme=self.readme
            )
        self.assertFalse(allowed)
        write.assert_not_called()

    def test_a_badge_write_failure_never_fails_the_run(self):
        """Stamping is cosmetic. ``StatusBadge.update`` swallows I/O errors, but
        ``update_test_badge`` computes the href with ``os.path.relpath`` first,
        which raises ValueError across Windows drives -- so the runner guards the
        call instead of assuming it is total."""
        every = StatusBadge.discover_module_names(TEST_DIR)
        for boom in (ValueError("path is on mount 'O:'"), OSError("read-only")):
            with self.subTest(error=type(boom).__name__):
                with mock.patch.object(
                    StatusBadge, "update_test_badge", side_effect=boom
                ):
                    self.assertFalse(
                        rt.ExtappsTestRunner.stamp_badge(
                            self._collector(every), readme=self.readme
                        )
                    )

    def test_failures_are_published_not_hidden(self):
        every = StatusBadge.discover_module_names(TEST_DIR)
        self.assertTrue(
            rt.ExtappsTestRunner.stamp_badge(
                self._collector(every, passed=600, failed=2), readme=self.readme
            )
        )
        text = self.readme.read_text(encoding="utf-8")
        self.assertIn("600%20passed%2C%202%20failed-orange", text)


class TargetResolutionTest(unittest.TestCase):
    def test_no_modules_runs_the_whole_directory(self):
        self.assertEqual(rt.ExtappsTestRunner.targets([]), [str(TEST_DIR)])

    def test_bare_and_prefixed_names_both_resolve(self):
        expected = [str(TEST_DIR / "test_progress_notify.py")]
        self.assertEqual(rt.ExtappsTestRunner.targets(["progress_notify"]), expected)
        self.assertEqual(
            rt.ExtappsTestRunner.targets(["test_progress_notify"]), expected
        )

    def test_unknown_module_aborts(self):
        """A typo'd invocation must not exit 0 having run something else."""
        with self.assertRaises(SystemExit) as ctx:
            rt.ExtappsTestRunner.targets(["no_such_module"])
        self.assertIn("no_such_module", str(ctx.exception))

    def test_discovery_matches_the_files_on_disk(self):
        on_disk = sorted(p.stem for p in TEST_DIR.glob("test_*.py"))
        self.assertEqual(rt.ExtappsTestRunner.discover_modules(), on_disk)


if __name__ == "__main__":
    unittest.main()
