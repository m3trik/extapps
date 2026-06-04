# !/usr/bin/python
# coding=utf-8
"""Tests for the RSNode REST client (mocked HTTP) — RealityScan 2.1 headless driver."""
import json
import socket
import unittest
import urllib.error
from unittest import mock
from urllib.parse import urlsplit, parse_qs

from extapps.photogrammetry.realityscan_workflow._rsnode_client import (  # noqa: E402
    RsNodeClient,
    RsNodeError,
    normalize_commands,
)


class _FakeResp:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers or {}
        self._b = b"" if body is None else json.dumps(body).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _route(handler, captured=None):
    """Build a urlopen side_effect dispatching to handler(method, path, query, body)."""
    def _open(req, timeout=None):
        if captured is not None:
            captured.append(req)
        sp = urlsplit(req.full_url)
        body = json.loads(req.data) if req.data else None
        status, headers, out = handler(req.get_method(), sp.path, parse_qs(sp.query), body)
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "err", {}, _io(out))
        return _FakeResp(status, headers, out)
    return _open


def _io(obj):
    import io
    return io.BytesIO(b"" if obj is None else json.dumps(obj).encode())


class NormalizeCommandsTest(unittest.TestCase):
    def test_string_and_tuple_and_tokenlist(self):
        self.assertEqual(normalize_commands(["-align"]),
                         [{"commandName": "align", "parameters": []}])
        self.assertEqual(normalize_commands([("addFolder", ["C:/i"])]),
                         [{"commandName": "addFolder", "parameters": ["C:/i"]}])
        self.assertEqual(
            normalize_commands([["-addFolder", "C:/i", "-align", "-exportModel", "C:/o.obj"]]),
            [{"commandName": "addFolder", "parameters": ["C:/i"]},
             {"commandName": "align", "parameters": []},
             {"commandName": "exportModel", "parameters": ["C:/o.obj"]}],
        )

    def test_tokenlist_must_start_with_flag(self):
        with self.assertRaises(ValueError):
            normalize_commands([["oops", "-align"]])


class RsNodeClientFlowTest(unittest.TestCase):
    def setUp(self):
        self.c = RsNodeClient(base_url="http://127.0.0.1:8000", app_token="APP", client_id="CID")

    def test_connect_sets_token_no_bearer(self):
        cap = []
        def h(method, path, q, body):
            return 200, {}, {"authToken": "TOK", "port": "8000"}
        with mock.patch("urllib.request.urlopen", _route(h, cap)):
            info = self.c.connect()
        self.assertEqual(self.c.auth_token, "TOK")
        self.assertEqual(info["port"], "8000")
        req = cap[-1]
        self.assertEqual(req.get_header("Clientid"), "CID")   # urllib title-cases header keys
        self.assertEqual(req.get_header("Apptoken"), "APP")
        self.assertIsNone(req.get_header("Authorization"))    # /node/connection takes no bearer

    def test_create_session_reads_header_and_bearer_sent(self):
        self.c.auth_token = "TOK"
        cap = []
        def h(method, path, q, body):
            return 201, {"Session": "SESS-1"}, None
        with mock.patch("urllib.request.urlopen", _route(h, cap)):
            sess = self.c.create_session()
        self.assertEqual(sess, "SESS-1")
        self.assertEqual(self.c.session, "SESS-1")
        self.assertEqual(cap[-1].get_header("Authorization"), "Bearer TOK")

    def test_run_commands_posts_normalized_group_with_session(self):
        self.c.auth_token = "TOK"
        self.c.session = "SESS-1"
        seen = {}
        def h(method, path, q, body):
            seen["method"] = method
            seen["path"] = path
            seen["body"] = body
            return 202, {}, {"taskID": "abc-123"}
        cap = []
        with mock.patch("urllib.request.urlopen", _route(h, cap)):
            task = self.c.run_commands([["-addFolder", "C:/imgs", "-align"]])
        self.assertEqual(task, "abc-123")
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["path"], "/project/commandgroup")
        self.assertEqual(seen["body"], [
            {"commandName": "addFolder", "parameters": ["C:/imgs"]},
            {"commandName": "align", "parameters": []},
        ])
        self.assertEqual(cap[-1].get_header("Session"), "SESS-1")

    def test_run_commands_requires_session(self):
        self.c.auth_token = "TOK"  # no session
        with self.assertRaises(RsNodeError):
            self.c.run_commands(["-align"])

    def test_wait_for_tag_polls_until_set(self):
        self.c.auth_token = "TOK"
        self.c.session = "SESS-1"
        state = {"polls": 0}
        def h(method, path, q, body):
            if path == "/project/status":
                state["polls"] += 1
                return 200, {}, {"progress": 0.5 * state["polls"], "errorCode": 0}
            if path == "/project/testtag":
                return 200, {}, state["polls"] >= 2  # tag fires on 2nd poll
            raise AssertionError(path)
        with mock.patch("urllib.request.urlopen", _route(h)):
            st = self.c.wait_for_tag("DONE", poll=0, timeout=5, sleep=lambda s: None)
        self.assertGreaterEqual(state["polls"], 2)
        self.assertEqual(st["errorCode"], 0)

    def test_wait_for_tag_raises_on_errorcode(self):
        self.c.auth_token = "TOK"
        self.c.session = "SESS-1"
        def h(method, path, q, body):
            if path == "/project/status":
                return 200, {}, {"errorCode": 7134}
            return 200, {}, False
        with mock.patch("urllib.request.urlopen", _route(h)):
            with self.assertRaises(RsNodeError) as cm:
                self.c.wait_for_tag("DONE", poll=0, timeout=5, sleep=lambda s: None)
        self.assertEqual(cm.exception.code, 7134)

    def test_http_error_becomes_rsnodeerror(self):
        self.c.auth_token = "TOK"
        def h(method, path, q, body):
            return 401, {}, {"code": 401, "message": "bad token"}
        with mock.patch("urllib.request.urlopen", _route(h)):
            with self.assertRaises(RsNodeError) as cm:
                self.c.node_status()
        self.assertEqual(cm.exception.code, 401)
        self.assertIn("bad token", str(cm.exception))

    def test_socket_timeout_becomes_rsnodeerror(self):
        # socket.timeout is an OSError but NOT a URLError; it must still surface
        # as RsNodeError so is_available()/wait_for_task() never leak it.
        with mock.patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            with self.assertRaises(RsNodeError):
                self.c.node_status()

    def test_create_session_reads_lowercase_session_header(self):
        # HTTP header names are case-insensitive; tolerate any casing.
        self.c.auth_token = "TOK"
        def h(method, path, q, body):
            return 201, {"session": "SESS-LC"}, None
        with mock.patch("urllib.request.urlopen", _route(h)):
            sess = self.c.create_session()
        self.assertEqual(sess, "SESS-LC")


class RsNodeTaskLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.c = RsNodeClient(base_url="http://127.0.0.1:8000", app_token="APP", client_id="CID")
        self.c.auth_token = "TOK"
        self.c.session = "SESS-1"

    def test_wait_for_task_polls_until_finished(self):
        state = {"n": 0}
        def h(method, path, q, body):
            self.assertEqual(path, "/project/tasks")
            state["n"] += 1
            st = "finished" if state["n"] >= 2 else "started"
            return 200, {}, [{"taskID": "T-1", "state": st, "errorCode": 0}]
        with mock.patch("urllib.request.urlopen", _route(h)):
            res = self.c.wait_for_task("t-1", poll=0, timeout=5, sleep=lambda s: None)
        self.assertEqual(res["state"], "finished")
        self.assertGreaterEqual(state["n"], 2)

    def test_wait_for_task_returns_failed_state(self):
        def h(method, path, q, body):
            return 200, {}, [{"taskID": "T-1", "state": "failed",
                              "errorCode": 7134, "errorMessage": "boom"}]
        with mock.patch("urllib.request.urlopen", _route(h)):
            res = self.c.wait_for_task("T-1", poll=0, timeout=5, sleep=lambda s: None)
        self.assertEqual(res["state"], "failed")
        self.assertEqual(res["errorCode"], 7134)
        self.assertEqual(res["errorMessage"], "boom")

    def test_wait_for_task_times_out(self):
        def h(method, path, q, body):
            return 200, {}, [{"taskID": "T-1", "state": "started"}]
        clk = {"t": 0.0}
        def clock():
            clk["t"] += 3.0
            return clk["t"]
        with mock.patch("urllib.request.urlopen", _route(h)):
            with self.assertRaises(RsNodeError):
                self.c.wait_for_task("T-1", poll=0, timeout=5,
                                     sleep=lambda s: None, clock=clock)

    def test_tasks_sends_session_and_query(self):
        cap = []
        def h(method, path, q, body):
            return 200, {}, [{"taskID": "T-1", "state": "finished"}]
        with mock.patch("urllib.request.urlopen", _route(h, cap)):
            out = self.c.tasks("T-1")
        self.assertEqual(out[0]["taskID"], "T-1")
        self.assertEqual(cap[-1].get_header("Session"), "SESS-1")
        self.assertIn("taskIDs=T-1", cap[-1].full_url)

    def test_save_project_hits_save_endpoint_with_name(self):
        cap = []
        def h(method, path, q, body):
            return 202, {}, None
        with mock.patch("urllib.request.urlopen", _route(h, cap)):
            self.c.save_project(r"C:/proj/p.rsproj")
        self.assertEqual(urlsplit(cap[-1].full_url).path, "/project/save")
        self.assertIn("name=", cap[-1].full_url)
        self.assertEqual(cap[-1].get_header("Session"), "SESS-1")

    def test_open_project_reads_session_header(self):
        def h(method, path, q, body):
            return 200, {"Session": "SESS-OPEN"}, None
        with mock.patch("urllib.request.urlopen", _route(h)):
            sess = self.c.open_project("{GUID}", "scene")
        self.assertEqual(sess, "SESS-OPEN")
        self.assertEqual(self.c.session, "SESS-OPEN")

    def test_close_project_hits_close_endpoint(self):
        cap = []
        def h(method, path, q, body):
            return 200, {}, None
        with mock.patch("urllib.request.urlopen", _route(h, cap)):
            self.c.close_project()
        self.assertEqual(urlsplit(cap[-1].full_url).path, "/project/close")


if __name__ == "__main__":
    unittest.main()
