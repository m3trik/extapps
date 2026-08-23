# !/usr/bin/python
# coding=utf-8
"""The one progress-notify shim the photogrammetry engines share.

Every engine in this package reports stage progress the same way: a caller
hands the constructor a ``progress(stage, fraction)`` callback, and each stage
opens with ``self._notify("<stage>", 0.0)``. The shim between the two was
reimplemented verbatim in five engines (``MetashapeWorkflow``,
``RealityCaptureWorkflow``, ``GaussianSplatWorkflow``, ``SplatPublishWorkflow``,
``SugarMeshWorkflow``) — identical bodies differing only in the class name
printed on a callback failure. One mixin, five bases.

The contract this pins (all of it deliberate, none of it incidental):

* **No callback is not an error.** ``progress=None`` is the headless default;
  ``_notify`` returns without doing anything.
* **The fraction is passed through, not clamped.** Stages report ``0.0`` at
  entry and the engines have no total to normalize against, so a value outside
  ``0..1`` is the caller's to interpret — clamping here would silently rewrite
  it. ``float()`` coercion only, so a callback always sees a float.
* **A raising callback never fails the run.** A photogrammetry bake is
  minutes-to-hours; a broken UI progress bar must not lose it. The exception is
  swallowed and reported on stderr, tagged with the engine that raised it.
  ``float(fraction)`` is inside the same guard on purpose — a non-numeric
  fraction is a caller bug of exactly the same kind.

The stderr tag is ``type(self).__name__``, which reproduces each engine's
previous hardcoded literal exactly and stays right if one is ever subclassed.

Host requirement: ``self.progress`` — an ``Optional[Callable[[str, float],
None]]`` set in the engine's ``__init__``.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional


class ProgressNotifyMixin:
    """Supplies ``_notify`` to an engine that carries a ``progress`` callback."""

    #: Set by the host engine's ``__init__``; ``None`` = nothing to report to.
    progress: Optional[Callable[[str, float], None]] = None

    def _notify(self, stage: str, fraction: float = 0.0) -> None:
        """Report *stage* at *fraction* to the host's progress callback.

        Parameters:
            stage (str): Stage id being entered (e.g. ``"align_photos"``).
            fraction (float): Progress within the run. Passed through as a
                float without clamping — see the module docstring.

        Returns:
            None: Never raises; a callback that does is reported on stderr.
        """
        if self.progress is None:
            return
        try:
            self.progress(stage, float(fraction))
        except Exception as e:  # noqa: BLE001 - a bad callback must not kill a bake
            print(
                f"[{type(self).__name__}] progress callback raised: {e}",
                file=sys.stderr,
            )
