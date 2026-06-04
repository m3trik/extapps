# !/usr/bin/python
# coding=utf-8
"""Tests for extapps.substance_workflow.env_utils.painter_connection.PainterConnection.

Unit tests run standalone (no Painter, no Qt). The live spike at the bottom
is gated behind ``SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1``.
"""
import os
import sys
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
from extapps.substance_workflow.env_utils.painter_connection import (
    build_painter_env,
    launch_painter,
    plugins_dir,
)


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
        p = plugins_dir()
        self.assertTrue(os.path.isabs(p))
        self.assertTrue(p.endswith("plugins") or p.endswith("plugins" + os.sep))
        self.assertTrue(os.path.isdir(p))


class TestBuildPainterEnv(SubstanceWorkflowTestCase):

    def test_prepends_plugins_path(self) -> None:
        env = build_painter_env()
        self.assertTrue(
            env["SUBSTANCE_PAINTER_PLUGINS_PATH"].startswith(plugins_dir())
        )

    def test_preserves_existing_plugins_path(self) -> None:
        existing = "/some/other/plugins"
        with patch.dict(os.environ, {"SUBSTANCE_PAINTER_PLUGINS_PATH": existing}):
            env = build_painter_env()
        parts = env["SUBSTANCE_PAINTER_PLUGINS_PATH"].split(os.pathsep)
        self.assertEqual(parts[0], plugins_dir())
        self.assertEqual(parts[1], existing)

    def test_no_port_var_when_port_is_zero(self) -> None:
        env = build_painter_env(port=0)
        self.assertNotIn("SUBSTANCE_WORKFLOW_PORT", env)

    def test_port_var_set_when_nonzero(self) -> None:
        env = build_painter_env(port=5555)
        self.assertEqual(env["SUBSTANCE_WORKFLOW_PORT"], "5555")

    def test_does_not_mutate_os_environ(self) -> None:
        before = dict(os.environ)
        build_painter_env(port=9999)
        self.assertEqual(dict(os.environ), before)


class TestGetAvailablePort(SubstanceWorkflowTestCase):

    def test_returns_first_free_port(self) -> None:
        with patch.object(NetUtils, "is_port_open") as mock_open:
            mock_open.side_effect = lambda h, p, timeout=0.3: p == 5050
            port = PainterConnection.get_available_port(start_port=5050, max_check=10)
        self.assertEqual(port, 5051)

    def test_raises_when_no_port_free(self) -> None:
        with patch.object(NetUtils, "is_port_open", return_value=True):
            with self.assertRaises(RuntimeError):
                PainterConnection.get_available_port(start_port=5050, max_check=3)

    def test_uses_pythontk_netutils(self) -> None:
        """Verifies the refactor away from raw socket — pythontk integration."""
        with patch.object(NetUtils, "is_port_open", return_value=False) as mock_open:
            PainterConnection.get_available_port(start_port=5050, max_check=1)
        mock_open.assert_called_once_with("localhost", 5050, timeout=0.3)


class TestLaunchPainter(SubstanceWorkflowTestCase):

    def test_appends_no_display_when_not_gui(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = MagicMock()
            launch_painter("/fake/painter.exe", env={}, gui=False)
        args = MockAL.launch.call_args.kwargs["args"]
        self.assertIn("--no-display", args)

    def test_omits_no_display_when_gui(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = MagicMock()
            launch_painter("/fake/painter.exe", env={}, gui=True)
        args = MockAL.launch.call_args.kwargs["args"]
        self.assertNotIn("--no-display", args)

    def test_appends_extra_args(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = MagicMock()
            launch_painter(
                "/x.exe", env={}, gui=True, extra_args=["--foo", "bar"]
            )
        args = MockAL.launch.call_args.kwargs["args"]
        self.assertEqual(args[-2:], ["--foo", "bar"])

    def test_passes_env_through_to_app_launcher(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = MagicMock()
            launch_painter("/x.exe", env={"FOO": "bar"})
        self.assertEqual(MockAL.launch.call_args.kwargs["env"], {"FOO": "bar"})

    def test_raises_when_app_launcher_fails(self) -> None:
        with patch(
            "extapps.substance_workflow.env_utils.painter_connection.AppLauncher"
        ) as MockAL:
            MockAL.launch.return_value = None
            with self.assertRaises(RuntimeError):
                launch_painter("/x.exe", env={})


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
        fake_proc = MagicMock()
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
        fake_proc = MagicMock()
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
            "extapps.substance_workflow.env_utils.painter_connection.urllib.request.urlopen",
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
            "extapps.substance_workflow.env_utils.painter_connection.urllib.request.urlopen",
            return_value=fake_resp,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                conn.invoke("no.such.op")
        self.assertIn("bad op", str(ctx.exception))


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
