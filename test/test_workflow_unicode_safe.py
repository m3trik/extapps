#!/usr/bin/python
# coding=utf-8
"""Regression guard: photogrammetry engines/drivers must not emit non-ASCII
in ``print()`` calls.

Windows consoles default to cp1252; a stray ``→`` / ``—`` inside a printed
string raises UnicodeEncodeError mid-pipeline and aborts an otherwise good
run (observed crashing ``equalize_exposures`` on a real combined run).
Docstrings and comments are exempt — only string *literals passed to
``print``* are checked, since those are the bytes that hit stdout.
"""
import ast
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.normpath(os.path.join(HERE, "..", "extapps", "photogrammetry"))

TARGETS = [
    os.path.join(PKG, "prep_stages.py"),
    os.path.join(PKG, "metashape_workflow", "_metashape_workflow.py"),
    os.path.join(PKG, "metashape_workflow", "_metashape_connection.py"),
    os.path.join(PKG, "metashape_workflow", "run_combined.py"),
    os.path.join(PKG, "realityscan_workflow", "_realityscan_workflow.py"),
    os.path.join(PKG, "realityscan_workflow", "_realityscan_connection.py"),
    os.path.join(PKG, "realityscan_workflow", "run_combined.py"),
]


def _non_ascii_print_strings(path):
    """Return (lineno, text) for every non-ASCII str literal inside a
    top-level ``print(...)`` call (including f-string literal parts)."""
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    hits = []

    def scan_value(node):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if not sub.value.isascii():
                    hits.append((getattr(sub, "lineno", "?"), sub.value))

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            for arg in node.args:
                scan_value(arg)
    return hits


class TestWorkflowUnicodeSafePrints(unittest.TestCase):
    def test_no_non_ascii_in_prints(self):
        problems = {}
        for path in TARGETS:
            if not os.path.isfile(path):
                continue
            hits = _non_ascii_print_strings(path)
            if hits:
                problems[path] = hits
        self.assertEqual(
            problems,
            {},
            "Non-ASCII string literals found inside print() calls "
            "(crashes on cp1252 Windows consoles): "
            + "; ".join(
                f"{os.path.basename(p)}:{ln}={s!r}"
                for p, hh in problems.items()
                for ln, s in hh
            ),
        )


if __name__ == "__main__":
    unittest.main()
