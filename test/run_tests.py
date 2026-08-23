# !/usr/bin/python
# coding=utf-8
"""extapps test runner — run the suite and stamp the README test badge.

Usage:
    python test/run_tests.py                 # full suite, stamp the badge
    python test/run_tests.py profile slots   # scoped run (badge refused)
    python test/run_tests.py --list          # list test modules
    python test/run_tests.py --no-badge      # run, never stamp
    python test/run_tests.py --log           # also write test/temp_tests/run_tests.log

Why this exists at all, given CI already runs ``pytest test``: CI proves the
suite green but publishes nothing, and ``pythontk.StatusBadge`` — the documented
single writer for the ecosystem badge (m3trik/docs/TEST_BADGE_STANDARD.md) —
needs a caller. extapps was the only registry-set package with no badge, so a
reader comparing it against its siblings read "no tests" over 600 of them.

Why it is a *pytest* driver and not a unittest one, unlike some siblings:

* ``test/conftest.py`` activates ``uitk.testing.TestSandbox``, which redirects
  QSettings and the pythontk user-config root away from the developer's live
  ones. ``unittest`` discovery never loads a conftest, so a unittest runner here
  would quietly write panel state into ``HKCU\\Software\\uitk`` and save presets
  into the real config root. Driving pytest keeps that protection.
* CLAUDE.md documents ``python -m pytest test`` as *the* way to run this suite.
  A second, differently-discovering entry point is a drift risk; this one runs
  the same pytest over the same directory, so the two cannot disagree.

Everything load-bearing is upstream: :meth:`StatusBadge.gate` decides whether a
run may stamp (a scoped run must never publish its smaller green over a full
one), :meth:`StatusBadge.update_test_badge` renders and places the badge, and
``ptk.TeeStream`` mirrors output to the log file. This file is wiring.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Set

import pytest

import pythontk as ptk
from pythontk.core_utils.status_badge import StatusBadge

TEST_DIR = Path(__file__).resolve().parent
README = TEST_DIR.parent / "docs" / "README.md"


class _ExtappsTestRunnerInternal:
    """Result collection + badge gating for :class:`ExtappsTestRunner`."""

    class Collector:
        """A pytest plugin that tallies cases the way the badge standard counts.

        Counts **individual test cases**, skips excluded from ``passed``
        (m3trik/docs/TEST_BADGE_STANDARD.md). ``pytest-subtests`` emits an extra
        report per subtest, tagged with a ``context``; those are filtered out so
        this tally matches what ``pytest test`` prints as its own totals rather
        than silently inflating the badge by the subtest count.

        A module that fails to *collect* (an import error) is recorded as a
        failure and deliberately never joins ``modules_ran`` — it contributed
        zero cases, so the gate must refuse a badge for that run.
        """

        def __init__(self):
            self.passed = 0
            self.failed = 0
            self.skipped = 0
            self.modules_ran: Set[str] = set()

        @staticmethod
        def _module(nodeid: str) -> str:
            return Path(nodeid.split("::")[0]).stem

        def pytest_runtest_logreport(self, report):
            if getattr(report, "context", None) is not None:
                return  # a pytest-subtests report, not a test case
            self.modules_ran.add(self._module(report.nodeid))
            if report.when == "call":
                if report.passed:
                    self.passed += 1
                elif report.failed:
                    self.failed += 1
                elif report.skipped:
                    self.skipped += 1
            elif report.failed:  # error raised in setup / teardown
                self.failed += 1
            elif report.skipped and report.when == "setup":
                self.skipped += 1

        def pytest_collectreport(self, report):
            if report.failed:
                self.failed += 1

    @classmethod
    def stamp_badge(cls, collector, readme: Path = README) -> bool:
        """Stamp the README badge for *collector*, unless the run fell short.

        Parameters:
            collector: The finished :class:`Collector`.
            readme: Markdown file to stamp.

        Returns:
            True when the badge was written; otherwise the reason it was not is
            printed and False returned. Never raises: stamping is a cosmetic
            side effect of a test run and must not turn a green run red.
            ``StatusBadge.update`` already swallows I/O errors, but
            ``update_test_badge`` computes the badge href with
            ``os.path.relpath`` first, which raises ``ValueError`` on Windows
            when the README and the test dir sit on different drives — so the
            call is guarded here rather than assumed total.
        """
        allowed, reason = StatusBadge.gate(
            StatusBadge.discover_module_names(TEST_DIR),
            collector.modules_ran,
            collector.passed,
            collector.failed,
        )
        if not allowed:
            print(f"[INFO] Badge not updated ({reason}).")
            return False
        try:
            written = StatusBadge.update_test_badge(
                readme, collector.passed, collector.failed, test_dir=TEST_DIR
            )
        except (OSError, ValueError) as e:
            print(f"[WARNING] Badge not updated ({e}): {readme}")
            return False
        if not written:
            print(f"[WARNING] Badge not updated (missing or unwritable): {readme}")
            return False
        message, _ = StatusBadge.test_status(collector.passed, collector.failed)
        print(f"README badge updated: {message}  ({readme})")
        return True


class ExtappsTestRunner(_ExtappsTestRunnerInternal):
    """Run the extapps suite through pytest and report the badge-standard tally."""

    @staticmethod
    def discover_modules() -> List[str]:
        """Test module names on disk (``test_*.py`` stems), sorted."""
        return sorted(StatusBadge.discover_module_names(TEST_DIR))

    @classmethod
    def targets(cls, modules: Sequence[str]) -> List[str]:
        """Resolve *modules* (bare or ``test_``-prefixed) to pytest path args.

        Returns:
            Absolute paths to pass to pytest; the whole test dir when *modules*
            is empty.

        Raises:
            SystemExit: if a requested module does not exist — a typo'd
                invocation must not exit 0 having run something else.
        """
        if not modules:
            return [str(TEST_DIR)]
        available = set(cls.discover_modules())
        paths: List[str] = []
        unknown: List[str] = []
        for name in modules:
            stem = name if name.startswith("test_") else f"test_{name}"
            if stem in available:
                paths.append(str(TEST_DIR / f"{stem}.py"))
            else:
                unknown.append(name)
        if unknown:
            raise SystemExit(f"[FAIL] no such test module(s): {', '.join(unknown)}")
        return paths

    @classmethod
    def run(
        cls,
        modules: Sequence[str] = (),
        update_badge: bool = True,
        log: bool = False,
        extra: Optional[Sequence[str]] = None,
    ) -> int:
        """Run the suite; stamp the badge when the run covered every module.

        Parameters:
            modules: Module names to scope the run to (empty = the whole suite).
            update_badge: Attempt the badge stamp (still subject to the gate).
            log: Also write the captured output (the pytest report plus
                this runner's own tally and badge line) to
                ``test/temp_tests/run_tests.log``.
            extra: Additional raw pytest arguments.

        Returns:
            Process exit code — 0 only when nothing failed.
        """
        collector = cls.Collector()
        args = cls.targets(modules) + list(extra or [])

        buffer = io.StringIO()
        real_out, real_err = sys.stdout, sys.stderr
        if log:
            sys.stdout = ptk.TeeStream(real_out, buffer)
            sys.stderr = ptk.TeeStream(real_err, buffer)
        try:
            code = int(pytest.main(args, plugins=[collector]))
            print(
                f"\n{'PASSED' if not collector.failed else 'FAILED'}: "
                f"{collector.passed} passed, {collector.failed} failed, "
                f"{collector.skipped} skipped"
            )
            if update_badge:
                cls.stamp_badge(collector)
        finally:
            sys.stdout, sys.stderr = real_out, real_err
        if log:
            # test/temp_tests/ is the repo's sanctioned (and gitignored) home
            # for test artifacts -- CLAUDE.md, "Testing".
            log_dir = TEST_DIR / "temp_tests"
            log_dir.mkdir(exist_ok=True)
            log_path = log_dir / "run_tests.log"
            log_path.write_text(buffer.getvalue(), encoding="utf-8")
            print(f"Log written: {log_path}")
        # Defer to pytest's own exit code when the collector saw no failure:
        # a usage error, an internal error or "no tests collected" all leave the
        # tally empty, and returning 0 there would report a run that never
        # happened as green.
        return code if code else (1 if collector.failed else 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the extapps test suite")
    parser.add_argument("modules", nargs="*", help="Test modules to run (default: all)")
    parser.add_argument("--list", action="store_true", help="List test modules")
    parser.add_argument("--no-badge", action="store_true", help="Never stamp the badge")
    parser.add_argument(
        "--log",
        action="store_true",
        help="Write test/temp_tests/run_tests.log",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Extra raw pytest argument (repeatable), e.g. --pytest-arg=-q",
    )
    args = parser.parse_args()

    if args.list:
        for i, name in enumerate(ExtappsTestRunner.discover_modules(), 1):
            print(f"{i:>3}. {name}")
        return 0

    return ExtappsTestRunner.run(
        modules=args.modules,
        update_badge=not args.no_badge,
        log=args.log,
        extra=args.pytest_arg,
    )


if __name__ == "__main__":
    sys.exit(main())
