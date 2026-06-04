"""Job spec + batch convenience wrapper.

There is only one execution mode (live bridge). ``run_batch`` exists for
ergonomics — it launches Painter, runs a sequence of calls, and shuts down.
For long-running agent sessions, use :class:`PainterConnection` directly.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .env_utils.painter_connection import PainterConnection

logger = logging.getLogger(__name__)


@dataclass
class Call:
    op: str
    kwargs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"op": self.op, "kwargs": self.kwargs}


@dataclass
class Result:
    index: int
    op: str
    ok: bool
    value: Any = None
    error: Optional[str] = None


@dataclass
class Job:
    """Convenience builder — ``Job().add("project.info").run()``."""

    calls: List[Call] = field(default_factory=list)

    def add(self, op: str, **kwargs: Any) -> "Job":
        self.calls.append(Call(op=op, kwargs=kwargs))
        return self

    def run(self, **launch_kwargs: Any) -> List[Result]:
        return run_batch(self.calls, **launch_kwargs)


def run_batch(
    calls: List[Call],
    gui: bool = False,
    app_path: Optional[str] = None,
    timeout: float = 180.0,
    launch_args: Optional[List[str]] = None,
    invoke_timeout: float = 60.0,
) -> List[Result]:
    """Launch Painter, execute ``calls`` in order over the bridge, shut down.

    Args:
        calls: Sequence of :class:`Call` to execute.
        gui: Show Painter's UI. Default ``False``.
        app_path: Override Painter executable.
        timeout: Seconds to wait for the bridge to come up.
        launch_args: Extra CLI args forwarded to Painter.
        invoke_timeout: Per-call HTTP timeout.

    Raises:
        RuntimeError: Painter failed to launch or the bridge never appeared.
    """
    conn = PainterConnection()
    if not conn.connect(
        gui=gui, app_path=app_path, launch_args=launch_args, timeout=timeout
    ):
        raise RuntimeError("Failed to launch Painter or reach the bridge.")

    results: List[Result] = []
    try:
        for i, call in enumerate(calls):
            try:
                value = conn.invoke(call.op, timeout=invoke_timeout, **call.kwargs)
                results.append(Result(index=i, op=call.op, ok=True, value=value))
            except Exception as e:
                results.append(
                    Result(
                        index=i,
                        op=call.op,
                        ok=False,
                        error=f"{type(e).__name__}: {e}",
                    )
                )
    finally:
        conn.shutdown(force=True)
    return results
