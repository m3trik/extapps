# !/usr/bin/python
# coding=utf-8
"""Headless entry point: download + install Brush via pythontk.AppInstaller.

Run as::

    python -m extapps.photogrammetry.gaussian_splat_workflow._install_brush

The Brush panel's "Download Brush" header action launches this in a child
process (so the ~160 MB download doesn't block the UI thread) and streams its
stdout into the log pane. Prints progress and the resulting path; exits
non-zero on failure.
"""
from __future__ import annotations

import sys


def main() -> int:
    from ._gaussian_splat_workflow import GaussianSplatWorkflow

    print("Downloading Brush from github.com/ArthurBrussee/brush ...", flush=True)
    try:
        path = GaussianSplatWorkflow.install_brush()
    except Exception as e:  # noqa: BLE001 — surface any failure to the log
        print(f"Brush install failed: {e}", flush=True)
        return 1
    print(f"Brush installed: {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
