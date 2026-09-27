"""Batch convenience: launch Painter, run a call list over the bridge, shut down.

There is only one execution mode (live bridge). ``Job.run_batch`` exists for
ergonomics; for long-running agent sessions use :class:`PainterConnection`
directly. The batch loop itself is the shared one -- :meth:`pythontk.RpcJob.run_batch`
over the connection's :class:`pythontk.RpcClient`, taking :class:`pythontk.Call`
and returning :class:`pythontk.Result` -- so this module adds only the Painter
lifecycle around it.
"""

import dataclasses
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from pythontk import Call, Result, RpcJob

from .env_utils.painter_connection import PainterConnection

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Convenience builder — ``Job().add("project.info").run()``."""

    calls: List[Call] = field(default_factory=list)

    def add(self, op: str, **kwargs: Any) -> "Job":
        self.calls.append(Call(op=op, kwargs=kwargs))
        return self

    def run(self, **launch_kwargs: Any) -> List[Result]:
        return Job.run_batch(self.calls, **launch_kwargs)

    @staticmethod
    def run_batch(
        calls: List[Call],
        gui: bool = False,
        app_path: Optional[str] = None,
        timeout: float = 180.0,
        launch_args: Optional[List[str]] = None,
        invoke_timeout: Optional[float] = None,
    ) -> List[Result]:
        """Launch Painter, execute ``calls`` in order over the bridge, shut down.

        Parameters:
            calls: Sequence of :class:`pythontk.Call` to execute.
            gui: Show Painter's UI. Default ``False``.
            app_path: Override Painter executable.
            timeout: Seconds to wait for the bridge to come up.
            launch_args: Extra CLI args forwarded to Painter.
            invoke_timeout: Per-call HTTP timeout for every call; ``None`` keeps
                each :class:`pythontk.Call`'s own ``timeout``.

        Returns:
            One :class:`pythontk.Result` per call, in order; a failed call is a
            result with ``ok=False``, never a raise.

        Raises:
            RuntimeError: Painter failed to launch or the bridge never appeared.
        """
        if invoke_timeout is not None:
            calls = [dataclasses.replace(c, timeout=invoke_timeout) for c in calls]
        conn = PainterConnection()
        if not conn.connect(
            gui=gui, app_path=app_path, launch_args=launch_args, timeout=timeout
        ):
            raise RuntimeError("Failed to launch Painter or reach the bridge.")
        try:
            return RpcJob.run_batch(list(calls), client=conn.client)
        finally:
            conn.shutdown(force=True)
