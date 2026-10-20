# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.env_utils.painter_connection.PainterConnection.

Unit tests run standalone (no Painter, no Qt). The live spike at the bottom
is gated behind ``SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1``.
"""
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

try:
    from .base_test import SubstanceWorkflowTestCase
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_test import SubstanceWorkflowTestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pythontk import NetUtils
from extapps.substance_workflow import PainterConnection


class TestForceNewInstanceHardBlock(SubstanceWorkflowTestCase):

    def test_rejects_reuse(self) -> None:
        conn = PainterConnection()
        with self.assertRaises(RuntimeError):
            conn.connect(force_new_instance=False)


class TestSingleton(SubstanceWorkflowTestCase):

    def setUp(self) -> None:
        super().setUp()
        PainterConnection._instance = None

    def tearDown(self) -> None:
        PainterConnection._instance = None
        super().tearDown()

    def test_get_instance_returns_same_object(self) -> None:
        a = PainterConnection.get_instance()
        b = PainterConnection.get_instance()
        self.assertIs(a, b)

    def test_direct_construction_is_fresh(self) -> None:
        a = PainterConnection()
        b = PainterConnection()
        self.assertIsNot(a, b)

    def test_get_instance_and_direct_construction_are_distinct(self) -> None:
        single = PainterConnection.get_instance()
        fresh = PainterConnection()
        self.assertIsNot(single, fresh)


class TestPluginsDir(SubstanceWorkflowTestCase):

    def test_returns_absolute_path_to_plugins(self) -> None:
        p = PainterConnection.plugins_dir()
        self.assertTrue(os.path.isabs(p))
        self.assertTrue(p.endswith("plugins") or p.endswith("plugins" + os.sep))
        self.assertTrue(os.path.isdir(p))


class TestBuildPainterEnv(SubstanceWorkflowTestCase):

    def test_prepends_plugins_path(self) -> None:
        env = PainterConnection.build_painter_env()
        self.assertTrue(
            env["SUBSTANCE_PAINTER_PLUGINS_PATH"].startswith(PainterConnection.plugins_dir())
        )

    def test_preserves_existing_plugins_path(self) -> None:
        existing = "/some/other/plugins"
        with patch.dict(os.environ, {"SUBSTANCE_PAINTER_PLUGINS_PATH": existing}):
            env = PainterConnection.build_painter_env()
        parts = env["SUBSTANCE_PAINTER_PLUGINS_PATH"].split(os.pathsep)
        self.assertEqual(parts[0], PainterConnection.plugins_dir())
        self.assertEqual(parts[1], existing)

    def test_no_port_var_when_port_is_zero(self) -> None:
        env = PainterConnection.build_painter_env(port=0)
        self.assertNotIn("SUBSTANCE_WORKFLOW_PORT", env)

    def test_port_var_set_when_nonzero(self) -> None:
        env = PainterConnection.build_painter_env(port=5555)
        self.assertEqual(env["SUBSTANCE_WORKFLOW_PORT"], "5555")

    def test_does_not_mutate_os_environ(self) -> None:
        before = dict(os.environ)
        PainterConnection.build_painter_env(port=9999)
        self.assertEqual(dict(os.environ), before)

    def test_a_startup_list_override_keeps_the_bridge(self) -> None:
        """``SUBSTANCE_PAINTER_STARTUP_PLUGINS`` REPLACES Painter's startup list
        (``:``-separated names), so a set one gains the bridge and an unset one
        stays unset (setting it would drop Painter's own startup modules)."""
        with patch.dict(os.environ, {"SUBSTANCE_PAINTER_STARTUP_PLUGINS": "a:b"}):
            env = PainterConnection.build_painter_env()
        self.assertEqual(
            env["SUBSTANCE_PAINTER_STARTUP_PLUGINS"], f"a:b:{PainterConnection.BRIDGE}"
        )
        with patch.dict(os.environ):
            os.environ.pop("SUBSTANCE_PAINTER_STARTUP_PLUGINS", None)
            env = PainterConnection.build_painter_env()
        self.assertNotIn("SUBSTANCE_PAINTER_STARTUP_PLUGINS", env)


def _painter_plugins_module() -> str:
    """The installed Painter's own plugin-discovery module, or ``""``."""
    from extapps.substance_workflow.env_utils.painter_finder import PainterFinder

    exe = PainterFinder.resolve()
    path = os.path.join(
        os.path.dirname(exe or ""), "resources", "python", "modules", "substance_painter_plugins.py"
    )
    return path if exe and os.path.isfile(path) else ""


def _painter_discovery(env: dict) -> dict:
    """What Painter itself lists for *env*: its startup and plugins module names.

    Runs the install's ``substance_painter_plugins`` (``substance_painter.logging``
    stubbed) under a private name, and restores ``sys.path`` and the modules it
    added, so the suite sees no trace of it.
    """
    saved_path, saved_modules = list(sys.path), set(sys.modules)
    painter = types.ModuleType("substance_painter")
    painter.logging = types.ModuleType("substance_painter.logging")
    sys.modules.setdefault("substance_painter", painter)
    sys.modules.setdefault("substance_painter.logging", painter.logging)
    try:
        spec = importlib.util.spec_from_file_location("_painter_plugins", _painter_plugins_module())
        plugins = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugins)
        with patch.dict(os.environ, env, clear=True):
            plugins.update_sys_path()
            return {"startup": plugins.startup_module_names(), "plugins": plugins.plugin_module_names()}
    finally:
        sys.path[:] = saved_path
        for name in ("substance_painter", "substance_painter.logging", PainterConnection.BRIDGE):
            if name not in saved_modules:
                sys.modules.pop(name, None)


class TestPainterFindsTheBridge(SubstanceWorkflowTestCase):
    """Painter reads each ``SUBSTANCE_PAINTER_PLUGINS_PATH`` entry as a ROOT that
    holds ``plugins/``, ``startup/`` and ``modules/``, and starts only ``startup/``
    modules by itself: a ``plugins/`` one waits for its ``launch_at_start``
    setting in Painter's Python menu, off by default."""

    def test_the_bridge_is_a_startup_module_of_the_root(self) -> None:
        root = PainterConnection.plugins_dir()
        bridge = os.path.join(root, "startup", PainterConnection.BRIDGE, "__init__.py")
        self.assertTrue(os.path.isfile(bridge), bridge)

    def test_the_bridge_bootstrap_finds_the_checkout(self) -> None:
        """Inside Painter nothing is installed: the bridge walks up from its own
        folder to the directory holding the ``extapps`` package. A dev shell's
        PYTHONPATH hides a wrong depth, so the walk is pinned here."""
        from extapps.substance_workflow.plugins.startup import substance_workflow_bridge as bridge

        self.assertTrue(
            os.path.isfile(os.path.join(bridge._extapps_repo, "extapps", "__init__.py")),
            bridge._extapps_repo,
        )

    @unittest.skipUnless(_painter_plugins_module(), "Substance 3D Painter is not installed")
    def test_painters_own_discovery_starts_the_bridge(self) -> None:
        found = _painter_discovery(PainterConnection.build_painter_env(port=5050))
        self.assertIn(PainterConnection.BRIDGE, found["startup"])
        self.assertNotIn(PainterConnection.BRIDGE, found["plugins"])


class TestGetAvailablePort(SubstanceWorkflowTestCase):
    """Bind-probed (2026-07-10): the question is "can a NEW bridge server bind
    this port", not "is something listening" — a hung process's bound-but-not-
    listening socket must read as taken (see NetUtils.is_port_bindable)."""

    def test_returns_first_bindable_port(self) -> None:
        with patch.object(NetUtils, "is_port_bindable") as mock_bind:
            mock_bind.side_effect = lambda p, host="127.0.0.1": p != 5050
            port = PainterConnection.get_available_port(start_port=5050, max_check=10)
        self.assertEqual(port, 5051)

    def test_raises_when_no_port_free(self) -> None:
        with patch.object(NetUtils, "is_port_bindable", return_value=False):
            with self.assertRaises(RuntimeError):
                PainterConnection.get_available_port(start_port=5050, max_check=3)

    def test_uses_pythontk_netutils(self) -> None:
        """Verifies the refactor away from raw socket — pythontk integration."""
        with patch.object(NetUtils, "is_port_bindable", return_value=True) as mock_bind:
            PainterConnection.get_available_port(start_port=5050, max_check=1)
        mock_bind.assert_called_once_with(5050)

    def test_zombie_bind_is_skipped(self) -> None:
        """Regression: a real bound-but-not-listening socket must be skipped."""
        import socket

        squatter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        squatter.bind(("127.0.0.1", 0))  # bound, never listen()s
        squatted = squatter.getsockname()[1]
        try:
            picked = PainterConnection.get_available_port(start_port=squatted)
            self.assertNotEqual(picked, squatted)
        finally:
            squatter.close()


class TestLaunchPainter(SubstanceWorkflowTestCase):

    def _launched(self, **kwargs):
        """``(args, env)`` AppLauncher was handed for ``launch_painter(**kwargs)``."""
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = MagicMock()
            PainterConnection.launch_painter("/fake/painter.exe", **kwargs)
        call = MockAL.launch.call_args.kwargs
        return call["args"], call["env"]

    def test_no_gui_runs_painter_offscreen_not_with_an_unknown_flag(self) -> None:
        """Painter has no headless option: ``--no-display`` made it exit within
        6 s (live, 2026-10-19). Qt's offscreen platform runs it windowless --
        create, bake and save matched a windowed Painter."""
        caller_env = {"FOO": "bar"}
        args, env = self._launched(env=caller_env, gui=False)
        self.assertNotIn("--no-display", args)
        self.assertEqual(env["QT_QPA_PLATFORM"], "offscreen")
        self.assertEqual(caller_env, {"FOO": "bar"})  # the caller's env is not touched

    def test_gui_shows_a_window_even_from_an_offscreen_caller(self) -> None:
        _, env = self._launched(env={"QT_QPA_PLATFORM": "offscreen"}, gui=True)
        self.assertNotIn("QT_QPA_PLATFORM", env)
        _, env = self._launched(env={"QT_QPA_PLATFORM": "windows:darkmode=2"}, gui=True)
        self.assertEqual(env["QT_QPA_PLATFORM"], "windows:darkmode=2")  # a user's choice stays

    def test_appends_extra_args(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = MagicMock()
            PainterConnection.launch_painter(
                "/x.exe", env={}, gui=True, extra_args=["--foo", "bar"]
            )
        args = MockAL.launch.call_args.kwargs["args"]
        self.assertEqual(args[-2:], ["--foo", "bar"])

    def test_passes_env_through_to_app_launcher(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = MagicMock()
            PainterConnection.launch_painter("/x.exe", env={"FOO": "bar"}, gui=True)
        self.assertEqual(MockAL.launch.call_args.kwargs["env"], {"FOO": "bar"})

    def test_raises_when_app_launcher_fails(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = None
            with self.assertRaises(RuntimeError):
                PainterConnection.launch_painter("/x.exe", env={})


class TestInvokeNotConnected(SubstanceWorkflowTestCase):

    def test_raises_when_not_connected(self) -> None:
        conn = PainterConnection()
        with self.assertRaises(RuntimeError):
            conn.invoke("project.info")


class TestShutdown(SubstanceWorkflowTestCase):

    def test_idempotent_when_never_connected(self) -> None:
        conn = PainterConnection()
        conn.shutdown()  # no-op, no exception
        self.assertFalse(conn.is_connected)
        self.assertIsNone(conn.process)

    def test_kills_process_when_present(self) -> None:
        conn = PainterConnection()
        fake_proc = MagicMock(**{"poll.return_value": None})  # running, as Popen says
        fake_proc.pid = 12345
        conn.process = fake_proc
        conn.is_connected = True

        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            conn.shutdown(force=True)

        MockAL.close_process.assert_called_once_with(12345, force=True)
        self.assertIsNone(conn.process)
        self.assertFalse(conn.is_connected)

    def test_continues_when_close_fails(self) -> None:
        conn = PainterConnection()
        fake_proc = MagicMock(**{"poll.return_value": None})
        fake_proc.pid = 99
        conn.process = fake_proc
        conn.is_connected = True

        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.close_process.side_effect = OSError("permission denied")
            # Must not raise — state must still be reset.
            conn.shutdown(force=True)

        self.assertFalse(conn.is_connected)
        self.assertIsNone(conn.process)


class TestPainterQuitByItself(SubstanceWorkflowTestCase):
    """A connection answers from the Painter process, not from a flag set at
    launch: Painter quit from its own window left ``is_connected`` True, and
    shutdown then killed the PID it had recorded."""

    _AL = "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"

    def _conn(self, exit_code):
        conn = PainterConnection()
        conn.process = MagicMock(pid=4242, **{"poll.return_value": exit_code})
        conn.is_connected = True
        return conn

    def test_a_painter_that_quit_is_not_connected_and_a_running_one_is(self) -> None:
        self.assertFalse(self._conn(exit_code=0).is_connected)
        self.assertTrue(self._conn(exit_code=None).is_connected)

    def test_shutdown_never_kills_a_painter_that_already_exited(self) -> None:
        """POSIX ``poll()`` reaps the exited child and frees its PID for reuse."""
        conn = self._conn(exit_code=0)
        with patch(self._AL) as MockAL:
            conn.shutdown(force=True)
        MockAL.close_process.assert_not_called()
        self.assertIsNone(conn.process)

    def test_connecting_again_keeps_the_painter_it_launched(self) -> None:
        """A second connect launched another Painter and orphaned the first."""
        conn = self._conn(exit_code=None)
        first = conn.process
        with patch.object(PainterConnection, "launch_painter") as launch:
            self.assertTrue(conn.connect(app_path="/fake/painter.exe"))
        launch.assert_not_called()
        self.assertIs(conn.process, first)

    def test_connecting_after_a_quit_launches_a_fresh_painter(self) -> None:
        conn = self._conn(exit_code=0)
        fresh = MagicMock(pid=5151, **{"poll.return_value": None})
        with patch.object(PainterConnection, "launch_painter", return_value=fresh), patch.object(
            PainterConnection, "_wait_for_health", return_value=True
        ), patch.object(PainterConnection, "get_available_port", return_value=5050):
            self.assertTrue(conn.connect(app_path="/fake/painter.exe"))
        self.assertIs(conn.process, fresh)
        self.assertTrue(conn.is_connected)


class TestContextManager(SubstanceWorkflowTestCase):

    def test_exit_invokes_shutdown(self) -> None:
        conn = PainterConnection()
        conn.is_connected = True  # skip the connect path
        with patch.object(conn, "shutdown") as mock_shutdown:
            with conn:
                pass
        mock_shutdown.assert_called_once_with(force=True)

    def test_enter_connects_when_not_connected(self) -> None:
        conn = PainterConnection()
        conn.is_connected = False
        with patch.object(conn, "connect", return_value=True) as mock_connect:
            with patch.object(conn, "shutdown"):
                with conn:
                    pass
        mock_connect.assert_called_once()


class TestInvokeRoundTrip(SubstanceWorkflowTestCase):

    @staticmethod
    def _mock_response(body: bytes) -> MagicMock:
        """Return a MagicMock that supports ``with urlopen(...) as resp: resp.read()``.

        MagicMock's default ``__enter__`` returns a *new* child mock, so the
        configured ``read`` would be on the wrong object. Wire ``__enter__``
        to return the response itself.
        """
        resp = MagicMock()
        resp.__enter__.return_value = resp
        resp.read.return_value = body
        return resp

    def test_posts_json_and_parses_response(self) -> None:
        conn = PainterConnection()
        conn.host = "localhost"
        conn.port = 5050
        conn.is_connected = True

        fake_resp = self._mock_response(
            b'{"ok": true, "value": {"hello": "world"}}'
        )
        with patch(
            "pythontk.net_utils.rpc.client.urllib.request.urlopen",
            return_value=fake_resp,
        ):
            value = conn.invoke("project.info", path="/x.spp")

        self.assertEqual(value, {"hello": "world"})

    def test_raises_when_response_not_ok(self) -> None:
        conn = PainterConnection()
        conn.host = "localhost"
        conn.port = 5050
        conn.is_connected = True

        fake_resp = self._mock_response(b'{"ok": false, "error": "bad op"}')
        with patch(
            "pythontk.net_utils.rpc.client.urllib.request.urlopen",
            return_value=fake_resp,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                conn.invoke("no.such.op")
        self.assertIn("bad op", str(ctx.exception))


class TestInvokeConnectionRefused(SubstanceWorkflowTestCase):
    """Regression: a bridge socket refused mid-session must surface an actionable
    ConnectionError (matching pythontk.RpcClient semantics), not a raw URLError.

    urllib raises a plain ``URLError`` (not ``HTTPError``) on connection refused,
    so the old ``except urllib.error.HTTPError`` clause let it leak uncaught.
    """

    def _connected(self) -> PainterConnection:
        conn = PainterConnection()
        conn.host = "localhost"
        conn.port = 5050
        conn.is_connected = True
        return conn

    def test_invoke_reraises_urlerror_as_connectionerror(self) -> None:
        import urllib.error

        conn = self._connected()
        with patch(
            "pythontk.net_utils.rpc.client.urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            with self.assertRaises(ConnectionError) as ctx:
                conn.invoke("project.info")
        self.assertIn("not reachable", str(ctx.exception))

    def test_invoke_reraises_connectionrefusederror(self) -> None:
        conn = self._connected()
        with patch(
            "pythontk.net_utils.rpc.client.urllib.request.urlopen",
            side_effect=ConnectionRefusedError(111, "Connection refused"),
        ):
            with self.assertRaises(ConnectionError):
                conn.invoke("project.info")

    def test_describe_reraises_urlerror_as_connectionerror(self) -> None:
        import urllib.error

        conn = self._connected()
        with patch(
            "pythontk.net_utils.rpc.client.urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            with self.assertRaises(ConnectionError) as ctx:
                conn.describe()
        self.assertIn("not reachable", str(ctx.exception))


@unittest.skipUnless(
    os.environ.get("SUBSTANCE_WORKFLOW_RUN_INTEGRATION") == "1",
    "Set SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1 to run live Painter integration tests",
)
class TestLiveSpike(SubstanceWorkflowTestCase):
    """End-to-end: launch Painter, call project.info, expect {open: False}."""

    def test_connect_invoke_shutdown(self) -> None:
        conn = PainterConnection()
        ok = conn.connect(gui=False, timeout=180)
        try:
            self.assertTrue(ok, "Painter bridge did not come up")
            info = conn.invoke("project.info")
            self.assertIsInstance(info, dict)
            self.assertIn("open", info)
        finally:
            conn.shutdown(force=True)


if __name__ == "__main__":
    unittest.main()
