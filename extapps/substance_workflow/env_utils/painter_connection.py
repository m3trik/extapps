"""Painter Connection Module.

Live JSON-RPC connection to a freshly launched Substance 3D Painter session.
Mirrors the design of :class:`mayatk.MayaConnection`: every connection
launches a NEW Painter instance on an unused port — the user's session is
never touched. ``force_new_instance=False`` is rejected.

The wire is the shared one: :attr:`PainterConnection.client` is a
:class:`pythontk.RpcClient` bound to the launched bridge, and the bridge is a
:class:`pythontk.RpcPlugin` (``extapps.substance_workflow.registry.PLUGIN``).
What this class adds is the Painter launch -- the hard block, a bind-probed
port pinned through ``SUBSTANCE_WORKFLOW_PORT``, the plugin root on
``SUBSTANCE_PAINTER_PLUGINS_PATH`` -- and teardown of exactly that process.
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, List, Optional

from pythontk import AppLauncher, NetUtils, RpcClient

from .painter_finder import PainterFinder

logger = logging.getLogger(__name__)

_HARD_BLOCK = (
    "[PainterConnection] HARD BLOCK: refusing to connect to an existing "
    "Painter session. Unsaved work could be lost. "
    "force_new_instance=True is required."
)


class PainterConnection:
    """Live JSON-RPC connection to a Substance 3D Painter session.

    Launch stays routed through ``pythontk.AppLauncher`` (never raw subprocess)
    and the caller is always ``connect(force_new_instance=True)`` — see the
    module docstring's session-safety block.
    """

    #: The bridge plugin's module name inside Painter.
    BRIDGE = "substance_workflow_bridge"

    @staticmethod
    def op_timeout() -> float:
        """Seconds the bridge lets one op run (its main-thread marshaller's
        limit): what a long op -- a bake -- waits for, past :meth:`invoke`'s
        60 s default (``invoke(op, timeout=PainterConnection.op_timeout())``)."""
        from ..registry import PLUGIN

        return PLUGIN.marshaller.timeout

    @staticmethod
    def plugins_dir() -> str:
        """Absolute path to the plugin root, ``substance_workflow/plugins``.

        Painter reads each ``SUBSTANCE_PAINTER_PLUGINS_PATH`` entry as a root
        holding ``plugins/``, ``startup/`` and ``modules/``; the bridge is
        ``startup/substance_workflow_bridge``, which Painter starts at every
        launch (a ``plugins/`` module waits for its menu setting, off by
        default). No global install.
        """
        here = Path(__file__).resolve().parent
        return str((here.parent / "plugins").resolve())

    @staticmethod
    def build_painter_env(port: int = 0) -> dict:
        """Compose the environment block passed to a Painter launch.

        Prepends the plugin root to ``SUBSTANCE_PAINTER_PLUGINS_PATH`` and pins
        ``SUBSTANCE_WORKFLOW_PORT`` so the plugin's HTTP server binds where
        the client expects it. A set ``SUBSTANCE_PAINTER_STARTUP_PLUGINS``
        replaces Painter's whole startup list, so it gains the bridge; an
        unset one stays unset (Painter then starts every startup module).
        """
        env = os.environ.copy()
        existing = env.get("SUBSTANCE_PAINTER_PLUGINS_PATH", "")
        plug = PainterConnection.plugins_dir()
        env["SUBSTANCE_PAINTER_PLUGINS_PATH"] = (
            f"{plug}{os.pathsep}{existing}" if existing else plug
        )
        startup = env.get("SUBSTANCE_PAINTER_STARTUP_PLUGINS")
        if startup is not None:  # Painter splits it on ":" (not os.pathsep)
            names = [name for name in startup.split(":") if name]
            if PainterConnection.BRIDGE not in names:
                names.append(PainterConnection.BRIDGE)
            env["SUBSTANCE_PAINTER_STARTUP_PLUGINS"] = ":".join(names)
        if port:
            env["SUBSTANCE_WORKFLOW_PORT"] = str(port)
        return env

    #: Qt platforms that open no window.
    _WINDOWLESS = ("offscreen", "minimal")

    @staticmethod
    def launch_painter(
        exe: str,
        env: dict,
        gui: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> subprocess.Popen:
        """Spawn a detached Painter process via ``pythontk.AppLauncher``.

        Painter has no headless option (its own option list has none, and an
        unknown one such as ``--no-display`` makes it exit), so ``gui=False``
        runs it on Qt's offscreen platform: no window, with project create,
        bake and save as a windowed Painter does them (verified 2026-10-19).
        ``gui=True`` drops a windowless platform the caller's own process
        carries (a test run's), so the window shows; *env* is not modified.
        """
        env = dict(env)
        platform = env.get("QT_QPA_PLATFORM", "").split(":")[0]
        if not gui:
            env["QT_QPA_PLATFORM"] = "offscreen"
        elif platform in PainterConnection._WINDOWLESS:
            env.pop("QT_QPA_PLATFORM")
        args: List[str] = list(extra_args or [])

        logger.info(f"[PainterConnection] Launching: {exe} {args}")
        process = AppLauncher.launch(exe, args=args, env=env, detached=True)
        if process is None:
            raise RuntimeError(f"AppLauncher failed to launch Painter at {exe!r}")
        return process

    _instance: "PainterConnection | None" = None

    @classmethod
    def get_instance(cls) -> "PainterConnection":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # The IPv4 loopback the bridge binds: "localhost" resolves to ::1 first
        # on Windows, and every request would wait out a refused IPv6 attempt.
        self.host: str = "127.0.0.1"
        self.port: int = 0
        self.process: Optional[subprocess.Popen] = None
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        """Connected to the bridge of a Painter that is still running.

        Read from the process, not only the flag set at launch: a Painter quit
        from its own window reads False (and the flag clears). With no process
        to ask (a test's fake bridge), the flag stands.
        """
        if self._connected and self.process is not None and self.process.poll() is not None:
            self._connected = False
        return self._connected

    @is_connected.setter
    def is_connected(self, value: bool) -> None:
        self._connected = bool(value)

    # ---- port helpers ----------------------------------------------------

    @staticmethod
    def get_available_port(start_port: int = 5050, max_check: int = 100) -> int:
        """Return the lowest TCP port a NEW bridge server could bind on localhost.

        Bind-probed, not connect-probed: a hung process can hold a port bound
        without listening -- a connect check reads that as free, but the
        bridge launched on it could never bind (it would wait out its whole
        startup timeout). ``NetUtils.is_port_bindable`` answers the actual
        question being asked here.
        """
        for p in range(start_port, start_port + max_check):
            if NetUtils.is_port_bindable(p):
                return p
        raise RuntimeError(f"No free port in {start_port}..{start_port + max_check}")

    # ---- lifecycle -------------------------------------------------------

    def connect(
        self,
        force_new_instance: bool = True,
        gui: bool = False,
        port: int = 5050,
        app_path: Optional[str] = None,
        launch_args: Optional[List[str]] = None,
        timeout: float = 180.0,
    ) -> bool:
        """Launch a fresh Painter and connect over the bridge HTTP server.

        Parameters:
            force_new_instance: HARD-CODED safe default. ``False`` is rejected.
            gui: Show Painter's window. Default ``False``: windowless, on Qt's
                offscreen platform (Painter has no headless option).
            port: Starting port for auto-negotiation.
            app_path: Override Painter executable.
            launch_args: Extra CLI args forwarded to Painter.
            timeout: Seconds to wait for the bridge to come up.

        Returns:
            True on success, False on bridge timeout.
        """
        if not force_new_instance:
            raise RuntimeError(_HARD_BLOCK)
        if self.is_connected:
            # The Painter THIS connection launched is still up: another launch
            # would orphan it. (The user's own sessions stay refused above.)
            return True

        exe = app_path or PainterFinder.resolve()
        if not exe:
            raise FileNotFoundError("Substance 3D Painter not found. Pass app_path=...")

        chosen_port = self.get_available_port(start_port=port)
        env = self.build_painter_env(port=chosen_port)

        self.process = self.launch_painter(exe, env, gui=gui, extra_args=launch_args)
        self.host = "127.0.0.1"
        self.port = chosen_port

        print(
            f"[PainterConnection] Painter launched "
            f"(pid {self.process.pid}). Waiting for bridge on port {chosen_port}..."
        )

        if not self._wait_for_health(timeout=timeout):
            print("[PainterConnection] Bridge did not become ready in time.")
            self.shutdown(force=True)
            return False

        self.is_connected = True
        print(
            f"[OK] Connected to Painter bridge on {self.host}:{self.port} "
            f"(pid {self.process.pid})"
        )
        return True

    def _wait_for_health(self, timeout: float) -> bool:
        start = time.time()
        client = self.client
        while time.time() - start < timeout:
            if self.process and self.process.poll() is not None:
                return False
            if client.ping(timeout=1.0):
                return True
            time.sleep(0.5)
        return False

    # ---- RPC -------------------------------------------------------------

    @property
    def client(self) -> RpcClient:
        """The shared JSON-RPC client, bound to this connection's bridge.

        Built from the current ``host`` / ``port`` on each access (cheap: no
        socket until a call), so it always addresses the bridge this connection
        launched. It never launches or closes anything itself: lifecycle stays
        here, behind the hard block.
        """
        return RpcClient(host=self.host, port=self.port, app_label="Painter")

    def invoke(self, op: str, timeout: float = 60.0, **kwargs: Any) -> Any:
        """Call a registered op over the bridge and return its value.

        Raises:
            RuntimeError: Not connected, or the op ran and failed.
            ConnectionError: The bridge did not answer.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")
        return self.client.invoke(op, timeout=timeout, **kwargs)

    def describe(self, op: str = "") -> Any:
        """The registry's ``{name, doc, params}`` for *op*, or a list for all."""
        return self.client.describe(op)

    # ---- shutdown --------------------------------------------------------

    def shutdown(self, force: bool = False) -> None:
        """Close the bridge and terminate the Painter process we launched."""
        if not self.is_connected and self.process is None:
            return
        # A Painter that already exited is not killed: its PID may be another
        # process's by now (POSIX ``poll()`` reaped it).
        if self.process is not None and self.process.poll() is None:
            try:
                AppLauncher.close_process(self.process.pid, force=force)
            except Exception as e:
                logger.warning(
                    f"[PainterConnection] Failed to close pid {self.process.pid}: {e}"
                )
        self.process = None
        self.is_connected = False
        print("[OK] Painter session closed")

    def __enter__(self) -> "PainterConnection":
        if not self.is_connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.shutdown(force=True)
