# !/usr/bin/python
# coding=utf-8
"""Tests for RsNodeConnection — the RSNode REST transport for the RC workflow.

Uses a fake RsNodeClient (no HTTP) to verify the CLI-tail translation: ``-load``
and ``-quit`` are dropped (the REST session is persistent and must never quit the
user's app), ``-save`` maps to a save call, and the remaining stage commands run
as one awaited command group.
"""
import os
import tempfile
import shutil
import unittest

from extapps.photogrammetry.realityscan_workflow._rsnode_client import RsNodeError
from extapps.photogrammetry.realityscan_workflow._rsnode_connection import (  # noqa: E402
    RsNodeConnection,
)


class _FakeClient:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.auth_token = None
        self.session = None
        self.connected = 0
        self.created = 0
        self.groups = []   # command groups posted via run_commands
        self.saved = []    # save_project name args
        self.closed = 0
        self.task_status = {"state": "finished", "errorCode": 0}
        self.connect_raises = None
        self.uploaded = []           # relative names passed to upload_file
        self.uploaded_detail = []    # (name, folder) pairs passed to upload_file
        self.downloaded = []         # relative names passed to download_file
        self.list_calls = 0
        self.output_files_pre = []   # list_files() result before the run
        self.output_files_post = []  # list_files() result after the run

    def connect(self):
        if self.connect_raises:
            raise self.connect_raises
        self.auth_token = "TOK"
        self.connected += 1
        return {"authToken": "TOK"}

    def create_session(self):
        self.session = "SESS"
        self.created += 1
        return "SESS"

    def run_commands(self, commands):
        self.groups.append(list(commands))
        return "TASK-1"

    def wait_for_task(self, task_id, timeout=None):
        return dict(self.task_status)

    def save_project(self, name=None):
        self.saved.append(name)

    def close_project(self):
        self.closed += 1

    def upload_file(self, name, data, folder="data", timeout=None):
        self.uploaded.append(name)
        self.uploaded_detail.append((name, folder))
        return 200

    def list_files(self, folder="output"):
        self.list_calls += 1
        return list(self.output_files_pre) if self.list_calls == 1 else list(self.output_files_post)

    def download_file(self, name, folder="output", timeout=None):
        self.downloaded.append(name)
        return b"DATA:" + name.encode()


class RsNodeConnectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = os.path.join(self.tmp, "stage.log")
        self.fc = _FakeClient()
        self.conn = RsNodeConnection(client=self.fc, exe="C:/fake/RealityScan.exe")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # tail mirrors RealityCaptureWorkflow._run_rc output
    TAIL = ["-load", "C:/p.rsproj", "-addFolder", "C:/imgs",
            "-save", "C:/p.rsproj", "-quit"]

    def test_is_available_true(self):
        self.assertTrue(self.conn.is_available())
        self.assertEqual(self.fc.auth_token, "TOK")

    def test_is_available_false_on_error(self):
        self.fc.connect_raises = RsNodeError("refused")
        self.assertFalse(self.conn.is_available())

    def test_run_drops_lifecycle_and_posts_stage(self):
        cp = self.conn.run(self.TAIL, log_path=self.log, timeout=60)
        self.assertEqual(cp.returncode, 0)
        # exactly the stage command, lifecycle stripped
        self.assertEqual(self.fc.groups, [[("addFolder", ["C:/imgs"])]])
        # save mapped to the save endpoint with the project path
        self.assertEqual(self.fc.saved, ["C:/p.rsproj"])
        # session was created once
        self.assertEqual(self.fc.created, 1)
        # log written for traceability
        self.assertTrue(os.path.isfile(self.log))

    def test_run_never_sends_quit_or_load(self):
        self.conn.run(self.TAIL, log_path=self.log)
        flat = [name for grp in self.fc.groups for (name, _) in grp]
        self.assertNotIn("quit", flat)
        self.assertNotIn("load", flat)

    def test_run_failure_returns_errorcode_and_skips_save(self):
        self.fc.task_status = {"state": "failed", "errorCode": 7134,
                               "errorMessage": "boom"}
        cp = self.conn.run(self.TAIL, log_path=self.log)
        self.assertEqual(cp.returncode, 7134)
        self.assertEqual(self.fc.saved, [])  # no save on failure
        with open(self.log) as fh:
            self.assertIn("boom", fh.read())

    def test_run_transport_error_returns_nonzero(self):
        def boom(commands):
            raise RsNodeError("connection lost", code=500)
        self.fc.run_commands = boom
        cp = self.conn.run(self.TAIL, log_path=self.log)
        self.assertEqual(cp.returncode, 500)

    def test_run_no_taskid_fails_fast(self):
        # A 202 without a taskID must not trigger a full-timeout poll.
        waited = {"n": 0}

        def no_task(commands):
            return ""

        def tracker(task_id, timeout=None):
            waited["n"] += 1
            return {"state": "finished"}

        self.fc.run_commands = no_task
        self.fc.wait_for_task = tracker
        cp = self.conn.run(self.TAIL, log_path=self.log)
        self.assertEqual(cp.returncode, 1)
        self.assertEqual(waited["n"], 0)  # never waited
        self.assertEqual(self.fc.saved, [])  # no save on failure

    def test_run_only_lifecycle_still_saves(self):
        cp = self.conn.run(["-load", "C:/p.rsproj", "-save", "C:/p.rsproj", "-quit"],
                           log_path=self.log)
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self.fc.groups, [])     # nothing to run
        self.assertEqual(self.fc.saved, ["C:/p.rsproj"])

    def test_run_reuses_session_across_calls(self):
        self.conn.run(self.TAIL, log_path=self.log)
        self.conn.run(["-align", "-save", "C:/p.rsproj", "-quit"], log_path=self.log)
        self.assertEqual(self.fc.created, 1)     # one session, reused
        self.assertEqual(self.fc.connected, 1)
        self.assertEqual(self.fc.groups[-1], [("align", [])])

    def test_close_calls_close_project_and_clears_session(self):
        self.conn.run(self.TAIL, log_path=self.log)  # establishes session
        self.assertEqual(self.fc.session, "SESS")
        self.conn.close()
        self.assertEqual(self.fc.closed, 1)
        self.assertIsNone(self.fc.session)  # so a later run() starts fresh

    def test_close_is_best_effort_when_close_project_fails(self):
        self.conn.run(self.TAIL, log_path=self.log)

        def boom():
            raise RsNodeError("Failed to close project")

        self.fc.close_project = boom
        self.conn.close()  # must not raise
        self.assertIsNone(self.fc.session)

    # -- input upload (RSNode sandboxes inputs to the session _data folder) ----
    def test_addfolder_uploads_images_and_relativizes(self):
        d = os.path.join(self.tmp, "clipA")
        os.makedirs(d)
        for n in ("a.jpg", "b.JPG", "notimg.txt"):
            open(os.path.join(d, n), "wb").close()
        cp = self.conn.run(
            ["-newScene", "-addFolder", d, "-save", "C:/p.rsproj", "-quit"],
            log_path=self.log,
        )
        self.assertEqual(cp.returncode, 0)
        # only images uploaded, namespaced under the source dir's basename
        self.assertEqual(sorted(self.fc.uploaded), ["clipA/a.jpg", "clipA/b.JPG"])
        # addFolder param rewritten from abs path to the relative dir name
        self.assertEqual(
            self.fc.groups[-1], [("newScene", []), ("addFolder", ["clipA"])]
        )

    def test_add_single_file_uploads_and_relativizes(self):
        f = os.path.join(self.tmp, "shot.jpg")
        open(f, "wb").close()
        self.conn.run(["-add", f, "-save", "C:/p.rsproj", "-quit"], log_path=self.log)
        self.assertEqual(self.fc.uploaded, ["shot.jpg"])
        self.assertEqual(self.fc.groups[-1], [("add", ["shot.jpg"])])

    def test_relative_add_param_left_untouched(self):
        # A non-path param (already a relative/uploaded name) is not uploaded.
        self.conn.run(["-addFolder", "clipA", "-save", "C:/p.rsproj", "-quit"],
                      log_path=self.log)
        self.assertEqual(self.fc.uploaded, [])
        self.assertEqual(self.fc.groups[-1], [("addFolder", ["clipA"])])

    # -- success detection (finished task may carry a benign positive code) ----
    def test_finished_with_positive_errorcode_is_success(self):
        self.fc.task_status = {"state": "finished", "errorCode": 1, "errorMessage": ""}
        cp = self.conn.run(self.TAIL, log_path=self.log)
        self.assertEqual(cp.returncode, 0)        # NOT treated as failure
        self.assertEqual(self.fc.saved, ["C:/p.rsproj"])  # save ran (success path)

    def test_failed_state_with_negative_hresult_is_failure(self):
        self.fc.task_status = {"state": "failed", "errorCode": -2147467259,
                               "errorMessage": "Operation failed"}
        cp = self.conn.run(self.TAIL, log_path=self.log)
        self.assertEqual(cp.returncode, -2147467259)
        self.assertEqual(self.fc.saved, [])

    # -- export output retrieval (RSNode writes exports to its session folder) -
    def test_export_relativized_and_new_outputs_downloaded(self):
        out = os.path.join(self.tmp, "proj")
        os.makedirs(out)
        target = os.path.join(out, "welding.obj")
        self.fc.output_files_pre = ["stale.obj"]
        self.fc.output_files_post = ["stale.obj", "welding.obj", "welding.mtl",
                                     "welding_u1_v1.png"]
        cp = self.conn.run(
            ["-load", "C:/p.rsproj", "-exportSelectedModel", target,
             "-save", "C:/p.rsproj", "-quit"],
            log_path=self.log,
        )
        self.assertEqual(cp.returncode, 0)
        # export path rewritten to a basename RSNode resolves in its output folder
        self.assertEqual(self.fc.groups[-1], [("exportSelectedModel", ["welding.obj"])])
        # only files NEW since the pre-run snapshot are pulled back
        self.assertEqual(sorted(self.fc.downloaded),
                         ["welding.mtl", "welding.obj", "welding_u1_v1.png"])
        for n in ("welding.obj", "welding.mtl", "welding_u1_v1.png"):
            self.assertTrue(os.path.isfile(os.path.join(out, n)))
        self.assertFalse(os.path.isfile(os.path.join(out, "stale.obj")))

    def test_export_report_uploads_template_to_output_and_relativizes(self):
        # exportReport <report> <template>: the report path is rewritten to a
        # basename + downloaded back; the template (param2) is uploaded to the
        # OUTPUT folder and referenced by basename (RSNode resolves command
        # auxiliary files there). The template is NOT pulled back as an output.
        out = os.path.join(self.tmp, "proj", "reports")
        os.makedirs(out)
        report = os.path.join(out, "align.xml")
        tpl = os.path.join(self.tmp, "qc_report_template.html")
        with open(tpl, "w") as fh:
            fh.write("<qc/>")
        # the uploaded template is present in output before the run completes
        self.fc.output_files_pre = ["qc_report_template.html"]
        self.fc.output_files_post = ["qc_report_template.html", "align.xml"]
        cp = self.conn.run(
            ["-load", "C:/p.rsproj", "-exportReport", report, tpl,
             "-save", "C:/p.rsproj", "-quit"],
            log_path=self.log,
        )
        self.assertEqual(cp.returncode, 0)
        # both params rewritten to basenames RSNode resolves in its output folder
        self.assertEqual(
            self.fc.groups[-1],
            [("exportReport", ["align.xml", "qc_report_template.html"])],
        )
        # template uploaded specifically to the OUTPUT folder (not data)
        self.assertIn(("qc_report_template.html", "output"), self.fc.uploaded_detail)
        # only the rendered report is pulled back; the template stays put
        self.assertEqual(self.fc.downloaded, ["align.xml"])
        self.assertTrue(os.path.isfile(report))


if __name__ == "__main__":
    unittest.main()
