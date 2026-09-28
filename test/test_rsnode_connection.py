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
from unittest import mock

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
        self.uploaded_data = {}      # node name -> the bytes uploaded under it
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
        self.uploaded_data[name] = data
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

    # tail mirrors RealityCaptureWorkflow._run_rc output; "imgs" is a bare node
    # name (already uploaded) -- a client path the client lacks never ships
    TAIL = ["-load", "C:/p.rsproj", "-addFolder", "imgs",
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
        self.assertEqual(self.fc.groups, [[("addFolder", ["imgs"])]])
        # save mapped to the save endpoint with the project's scene name
        self.assertEqual(self.fc.saved, ["p"])
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
        self.assertEqual(self.fc.saved, ["p"])

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
        self.assertEqual(self.fc.saved, ["p"])  # save ran (success path)

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

    def test_a_re_export_under_the_same_name_is_pulled_back_again(self):
        # The workflow re-exports reports/model.xml after build, clean and
        # simplify in one session. From the second export on, the name is in
        # the pre-run snapshot, so "new since the snapshot" alone skipped it and
        # the caller parsed the FIRST stage's report as the later stage's.
        report = os.path.join(self.tmp, "reports", "model.xml")
        os.makedirs(os.path.dirname(report))
        with open(report, "wb") as fh:
            fh.write(b"stale")
        self.fc.output_files_pre = ["model.xml", "stale.obj"]
        self.fc.output_files_post = ["model.xml", "stale.obj"]
        cp = self.conn.run(["-exportReport", report, "tpl.html"], log_path=self.log)
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self.fc.downloaded, ["model.xml"])  # never stale.obj
        with open(report, "rb") as fh:
            self.assertEqual(fh.read(), b"DATA:model.xml")

    # -- client paths never reach the node (no shared filesystem) ------------
    # A client that is not the node (a Linux host driving a Windows node)
    # spells paths in its own filesystem. The node sandboxes every command path
    # to its session folders and names a saved project by *scene name*, so no
    # client path may cross the wire, in either spelling.
    def _assert_no_client_path(self):
        sent = [p for grp in self.fc.groups for (_, params) in grp for p in params]
        sent += [n for n in self.fc.saved if n]
        self.assertTrue(sent, "nothing reached the node")
        for value in sent:
            self.assertNotRegex(
                value, r"[\\/]", f"client path shipped to the node: {value!r}"
            )

    def test_posix_client_paths_never_reach_the_node(self):
        tpl = os.path.join(self.tmp, "qc_report_template.html")
        open(tpl, "w").close()
        root = "/home/artist/rc_out/job"
        cp = self.conn.run(
            ["-load", f"{root}/job.rsproj",
             "-exportSelectedModel", f"{root}/job.obj",
             "-exportReport", f"{root}/reports/final.xml", tpl,
             "-save", f"{root}/job.rsproj", "-quit"],
            log_path=self.log,
        )
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(
            self.fc.groups[-1],
            [("exportSelectedModel", ["job.obj"]),
             ("exportReport", ["final.xml", "qc_report_template.html"])],
        )
        # /project/save takes a node-side scene name, not the client's path
        self.assertEqual(self.fc.saved, ["job"])
        self._assert_no_client_path()

    def test_relative_export_path_is_relativized_and_pulled_back(self):
        # A relative project dir (the workflow default is ./rc_project) is a
        # client path too: it is not sent, and the export lands beside it.
        self.fc.output_files_post = ["t.obj"]
        cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            cp = self.conn.run(
                ["-exportSelectedModel", os.path.join("rc_project", "t.obj"),
                 "-save", os.path.join("rc_project", "t.rsproj"), "-quit"],
                log_path=self.log,
            )
        finally:
            os.chdir(cwd)
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self.fc.groups[-1], [("exportSelectedModel", ["t.obj"])])
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "rc_project", "t.obj")))
        self._assert_no_client_path()

    def test_import_model_uploads_the_mesh_and_relativizes(self):
        mesh = os.path.join(self.tmp, "blockout", "wall.obj")
        os.makedirs(os.path.dirname(mesh))
        with open(mesh, "wb") as fh:
            fh.write(b"v 0 0 0\n")
        cp = self.conn.run(
            ["-importModel", mesh, "-save", "/home/artist/job.rsproj", "-quit"],
            log_path=self.log,
        )
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self.fc.groups[-1], [("importModel", ["wall.obj"])])
        # command-auxiliary file: uploaded to the session OUTPUT folder
        self.assertIn(("wall.obj", "output"), self.fc.uploaded_detail)
        self._assert_no_client_path()

    def test_missing_client_input_fails_instead_of_reaching_the_node(self):
        # A path this client doesn't have is still a client path: fail here with
        # the path named, not with the node's opaque sandbox "file not found".
        for tail in (["-importModel", "/home/artist/blockout/missing.obj"],
                     ["-addFolder", "/home/artist/frames/missing"]):
            self.fc.groups.clear()
            cp = self.conn.run(tail + ["-save", "/home/artist/job.rsproj", "-quit"],
                               log_path=self.log)
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(self.fc.groups, [])  # nothing posted
            self.assertEqual(self.fc.saved, [])   # no save on failure
            with open(self.log) as fh:
                self.assertIn("missing", fh.read())

    # -- same-named client files never overwrite each other on the node -------
    # Uploads land in one session folder under bare names, so two client files
    # sharing a name (frames from two capture folders) would overwrite each
    # other there and the run would silently lose images.
    SAVE = ["-save", "C:/p.rsproj", "-quit"]

    def _write(self, *parts, data=b""):
        path = os.path.join(self.tmp, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def _sent(self):
        return [params[0] for (_, params) in self.fc.groups[-1]]

    def test_add_same_basename_from_two_folders_gets_distinct_node_names(self):
        a = self._write("sessA", "shot.jpg", data=b"A")
        b = self._write("sessB", "shot.jpg", data=b"B")
        cp = self.conn.run(["-add", a, "-add", b] + self.SAVE, log_path=self.log)
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self._sent(), ["shot.jpg", "shot~2.jpg"])  # 1st keeps its name
        # each -add names exactly the bytes uploaded under that name
        self.assertEqual([self.fc.uploaded_data[n] for n in self._sent()], [b"A", b"B"])

    def test_same_named_folders_across_runs_get_distinct_node_folders(self):
        for sess, data in (("sessA", b"A"), ("sessB", b"B")):
            self._write(sess, "frames", "f_0001.jpg", data=data)
        for sess in ("sessA", "sessB"):  # the workflow adds one folder per run
            self.conn.run(["-addFolder", os.path.join(self.tmp, sess, "frames")]
                          + self.SAVE, log_path=self.log)
        self.assertEqual([g[0] for g in self.fc.groups],
                         [("addFolder", ["frames"]), ("addFolder", ["frames~2"])])
        self.assertEqual(self.fc.uploaded_data["frames/f_0001.jpg"], b"A")
        self.assertEqual(self.fc.uploaded_data["frames~2/f_0001.jpg"], b"B")

    def test_case_only_collision_is_a_collision_on_the_node(self):
        # The node is Windows: IMG.JPG and img.jpg are one file there.
        a = self._write("sessA", "IMG.JPG", data=b"A")
        b = self._write("sessB", "img.jpg", data=b"B")
        self.conn.run(["-add", a, "-add", b] + self.SAVE, log_path=self.log)
        self.assertEqual(self._sent(), ["IMG.JPG", "img~2.jpg"])

    def test_image_layers_follow_their_image_rename(self):
        # RealityScan pairs an image layer by the image's full name
        # (DSC_0001.jpg.mask.png), so a renamed image takes its layers along.
        paths = [self._write(sess, n, data=(sess + n).encode())
                 for sess in ("sessA", "sessB") for n in ("a.jpg", "a.jpg.mask.png")]
        tail = [tok for p in paths for tok in ("-add", p)]
        self.conn.run(tail + self.SAVE, log_path=self.log)
        self.assertEqual(self._sent(), ["a.jpg", "a.jpg.mask.png",
                                        "a~2.jpg", "a~2.jpg.mask.png"])
        self.assertEqual(self.fc.uploaded_data["a~2.jpg.mask.png"], b"sessBa.jpg.mask.png")

    def test_in_folder_case_collision_renames_an_image_with_its_layers(self):
        # A case-sensitive (Linux) client folder can hold A.jpg and a.jpg.
        listing = [self._write(sess, n) for sess, n in (
            ("sessA", "A.jpg"), ("sessA", "A.jpg.mask.png"),
            ("sessB", "a.jpg"), ("sessB", "a.jpg.mask.png"))]
        frames = os.path.join(self.tmp, "sessA")
        with mock.patch.object(RsNodeConnection, "_list_images", return_value=listing):
            self.conn.run(["-addFolder", frames] + self.SAVE, log_path=self.log)
        self.assertEqual(self.fc.uploaded, [
            "sessA/A.jpg", "sessA/A.jpg.mask.png",
            "sessA/a~2.jpg", "sessA/a~2.jpg.mask.png"])

    # -- sidecars RealityScan reads beside an image ride along ----------------
    # rshelp "XMP Metadata Files": <stem>.xmp pairs with the image of that stem
    # in the same folder, and _common.xmp applies to every image in its folder.
    def test_add_folder_carries_xmp_sidecars_and_common_xmp(self):
        for n in ("a.jpg", "a.xmp", "b.jpg", "_common.xmp", "notes.txt"):
            self._write("frames", n, data=n.encode())
        self.conn.run(["-addFolder", os.path.join(self.tmp, "frames")] + self.SAVE,
                      log_path=self.log)
        self.assertEqual(sorted(self.fc.uploaded), [
            "frames/_common.xmp", "frames/a.jpg", "frames/a.xmp", "frames/b.jpg"])
        self.assertEqual(self.fc.groups[-1], [("addFolder", ["frames"])])

    def test_single_add_carries_its_stem_xmp(self):
        shot = self._write("sessA", "shot.jpg")
        self._write("sessA", "shot.xmp", data=b"priors")
        self.conn.run(["-add", shot] + self.SAVE, log_path=self.log)
        self.assertEqual(self._sent(), ["shot.jpg"])
        self.assertEqual(self.fc.uploaded_data.get("shot.xmp"), b"priors")

    def test_stem_sidecar_follows_a_renamed_image(self):
        for sess in ("sessA", "sessB"):
            self._write(sess, "shot.jpg")
            self._write(sess, "shot.xmp", data=sess.encode())
        self.conn.run(["-add", os.path.join(self.tmp, "sessA", "shot.jpg"),
                       "-add", os.path.join(self.tmp, "sessB", "shot.jpg")] + self.SAVE,
                      log_path=self.log)
        self.assertEqual(self._sent(), ["shot.jpg", "shot~2.jpg"])
        self.assertEqual(self.fc.uploaded_data.get("shot.xmp"), b"sessA")
        self.assertEqual(self.fc.uploaded_data.get("shot~2.xmp"), b"sessB")

    def test_same_stem_from_another_folder_never_shares_a_sidecar(self):
        # a.jpg (sessA) and a.png (sessB) differ in name but share the stem an
        # XMP pairs by: side by side on the node, sessB's image would take
        # sessA's camera priors. The later stem is renamed with its sidecar.
        a = self._write("sessA", "a.jpg")
        self._write("sessA", "a.xmp", data=b"sessA")
        b = self._write("sessB", "a.png")
        self._write("sessB", "a.xmp", data=b"sessB")
        self.conn.run(["-add", a, "-add", b] + self.SAVE, log_path=self.log)
        self.assertEqual(self._sent(), ["a.jpg", "a~2.png"])
        self.assertEqual(self.fc.uploaded_data.get("a.xmp"), b"sessA")
        self.assertEqual(self.fc.uploaded_data.get("a~2.xmp"), b"sessB")

    def test_non_colliding_names_are_kept_and_a_reissue_reuses_its_name(self):
        a = self._write("sessA", "shot.jpg")
        self.conn.run(["-add", a] + self.SAVE, log_path=self.log)
        self.conn.run(["-add", a] + self.SAVE, log_path=self.log)
        self.assertEqual([g[0] for g in self.fc.groups], [("add", ["shot.jpg"])] * 2)
        # a new session starts a fresh data folder, so its names start fresh
        self.conn.close()
        b = self._write("sessB", "shot.jpg")
        self.conn.run(["-add", b] + self.SAVE, log_path=self.log)
        self.assertEqual(self._sent(), ["shot.jpg"])


if __name__ == "__main__":
    unittest.main()
