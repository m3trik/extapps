"""Painter Connection Module.

Live JSON-RPC connection to a freshly launched Substance 3D Painter session.
Mirrors the design of :class:`mayatk.MayaConnection`: every connection
launches a NEW Painter instance on an unused port — the user's session is
never touched. ``force_new_instance=False`` is rejected.
"""

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, List, Optional

try:
    from pythontk import AppLauncher, NetUtils
except ImportError:
    from pythontk.core_utils.app_launcher import AppLauncher
    from pythontk.net_utils._net_utils import NetUtils

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

    @staticmethod
    def plugins_dir() -> str:
        """Absolute path to the ``substance_workflow/plugins`` directory.

        Painter's ``SUBSTANCE_PAINTER_PLUGINS_PATH`` should be set to this so
        the ``substance_workflow_bridge`` plugin is discovered without a global
        install.
        """
        here = Path(__file__).resolve().parent
        return str((here.parent / "plugins").resolve())

    @staticmethod
    def build_painter_env(port: int = 0) -> dict:
        """Compose the environment block passed to a Painter launch.

        Prepends the bridge plugin directory to ``SUBSTANCE_PAINTER_PLUGINS_PATH``
        and pins ``SUBSTANCE_WORKFLOW_PORT`` so the plugin's HTTP server binds
        where the client expects it.
        """
        env = os.environ.copy()
        existing = env.get("SUBSTANCE_PAINTER_PLUGINS_PATH", "")
        plug = PainterConnection.plugins_dir()
        env["SUBSTANCE_PAINTER_PLUGINS_PATH"] = (
            f"{plug}{os.pathsep}{existing}" if existing else plug
        )
        if port:
            env["SUBSTANCE_WORKFLOW_PORT"] = str(port)
        return env

    @staticmethod
    def launch_painter(
        exe: str,
        env: dict,
        gui: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> subprocess.Popen:
        """Spawn a detached Painter process via ``pythontk.AppLauncher``."""
        args: List[str] = []
        if not gui:
            # TODO: verify the correct headless flag for the installed Painter version.
            args.append("--no-display")
        if extra_args:
            args.extend(extra_args)

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
        self.host: str = "localhost"
        self.port: int = 0
        self.process: Optional[subprocess.Popen] = None
        self.is_connected: bool = False

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
        raise RuntimeError(
            f"No free port in {start_port}..{start_port + max_check}"
        )

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
            gui: Show Painter's UI. Default ``False``.
            port: Starting port for auto-negotiation.
            app_path: Override Painter executable.
            launch_args: Extra CLI args forwarded to Painter.
            timeout: Seconds to wait for the bridge to come up.

        Returns:
            True on success, False on bridge timeout.
        """
        if not force_new_instance:
            raise RuntimeError(_HARD_BLOCK)

        exe = app_path or PainterFinder.resolve()
        if not exe:
            raise FileNotFoundError(
                "Substance 3D Painter not found. Pass app_path=..."
            )

        chosen_port = self.get_available_port(start_port=port)
        env = self.build_painter_env(port=chosen_port)

        self.process = self.launch_painter(
            exe, env, gui=gui, extra_args=launch_args
        )
        self.host = "localhost"
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
        url = f"http://{self.host}:{self.port}/health"
        while time.time() - start < timeout:
            if self.process and self.process.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(url, timeout=1.0) as r:
                    if r.status == 200:
                        return True
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            time.sleep(0.5)
        return False

    # ---- RPC -------------------------------------------------------------

    def invoke(self, op: str, timeout: float = 60.0, **kwargs: Any) -> Any:
        """Call a registered op over the bridge and return its value."""
        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        url = f"http://{self.host}:{self.port}/"
        payload = json.dumps({"op": op, "kwargs": kwargs}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            raise ConnectionError(
                f"Painter plugin not reachable at {url!r}: {e}"
            ) from e

        if not body.get("ok"):
            raise RuntimeError(f"Op {op!r} failed: {body.get('error')}")
        return body.get("value")

    def describe(self, op: str = "") -> dict:
        """Fetch the registry's signature description for agent self-discovery."""
        url = f"http://{self.host}:{self.port}/describe"
        payload = json.dumps({"op": op}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8")).get("value", {})
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            raise ConnectionError(
                f"Painter plugin not reachable at {url!r}: {e}"
            ) from e

    # ---- shutdown --------------------------------------------------------

    def shutdown(self, force: bool = False) -> None:
        """Close the bridge and terminate the Painter process we launched."""
        if not self.is_connected and self.process is None:
            return
        if self.process is not None:
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
