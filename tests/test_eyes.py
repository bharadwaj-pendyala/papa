import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import eyes  # noqa: E402


def _project(tmp_path, cases, **config):
    (tmp_path / ".git").mkdir(exist_ok=True)
    path = tmp_path / "eyes.json"
    path.write_text(json.dumps({"command": ["sh", "-c"], "cases": cases, **config}), encoding="utf-8")
    return eyes.Project(path)


def _checks(project, case_id):
    case = next(c for c in project.cases() if c["id"] == case_id)
    return {c.check: c for c in eyes.generic_checks(project, eyes.run_case(project, case))}


def test_slow_command_becomes_a_failed_check_not_a_crash(tmp_path):
    project = _project(tmp_path, [{"id": "slow", "argv": ["sleep 5"]}], timeout=0.5)
    assert _checks(project, "slow")["runs"].status == "fail"


def test_slow_tty_command_is_killed_at_the_timeout(tmp_path):
    project = _project(tmp_path, [{"id": "slow", "argv": ["sleep 5"], "tty": True}], timeout=0.5)
    assert "timed out" in _checks(project, "slow")["runs"].detail


def test_missing_executable_becomes_a_failed_check(tmp_path):
    path = tmp_path / "eyes.json"
    path.write_text(json.dumps({"command": ["no-such-binary-xyz"], "cases": [{"id": "x"}]}))
    project = eyes.Project(path)
    assert "could not start" in _checks(project, "x")["runs"].detail


def test_tty_case_receives_stdin(tmp_path):
    project = _project(tmp_path, [{"id": "echo", "argv": ["read line; echo got:$line"], "tty": True,
                                   "stdin": "hello\n", "expect_ansi": False,
                                   "stdout_contains": ["got:hello"]}])
    assert _checks(project, "echo")["stdout-contains"].status == "pass"


@pytest.mark.parametrize("bad_id", ["/tmp/x", "../up", "", "a b"])
def test_case_ids_that_could_escape_the_artifacts_folder_are_rejected(tmp_path, bad_id):
    with pytest.raises(SystemExit):
        _project(tmp_path, [{"id": bad_id}])


def test_duplicate_case_ids_are_rejected(tmp_path):
    with pytest.raises(SystemExit):
        _project(tmp_path, [{"id": "a"}, {"id": "a"}])


def test_approve_accepts_the_inspected_run_without_rerunning(tmp_path):
    project = _project(tmp_path, [{"id": "a", "argv": ["echo one"]}])
    eyes.run(project, None, browser_wanted=False)
    project.config["cases"][0]["argv"] = ["echo two"]
    assert eyes.approve(project, None) == 0
    assert "one" in (project.snapshots / "a.txt").read_text()


def test_approve_without_a_captured_run_fails(tmp_path):
    project = _project(tmp_path, [{"id": "a", "argv": ["echo one"]}])
    assert eyes.approve(project, None) == 1


def test_html_scan_flags_meta_refresh_and_inline_handlers(tmp_path):
    page = tmp_path / "p.html"
    page.write_text('<!doctype html><meta http-equiv="refresh" content="0;url=https://x">'
                    '<body onload="fetch(1)">hi</body>')
    offline = {c.check: c for c in eyes._check_html(page, None)}["html-offline"]
    assert offline.status == "fail"
    assert "refresh" in offline.detail and "onload" in offline.detail


def test_wide_characters_count_as_two_terminal_cells():
    assert eyes.cells("日本") == 4
    assert eyes.cells("abc") == 3


def test_tty_stdin_without_trailing_newline_still_reaches_eof(tmp_path):
    project = _project(tmp_path, [{"id": "cat", "argv": ["cat"], "tty": True, "stdin": "hello",
                                   "stdout_contains": ["hello"]}], timeout=3)
    checks = _checks(project, "cat")
    assert "runs" not in checks
    assert checks["stdout-contains"].status == "pass"


def test_browser_requested_but_unavailable_is_a_failure(tmp_path):
    project = _project(tmp_path, [{"id": "a", "argv": ["echo hi"], "tty": True}])
    result = eyes.run_case(project, project.cases()[0])
    checks = eyes.browser_checks(None, "no browser", project, result)
    assert any(c.status == "fail" for c in checks)


def test_first_run_of_a_new_case_points_at_the_captured_output(tmp_path):
    project = _project(tmp_path, [{"id": "new", "argv": ["echo hi"]}])
    result = eyes.run_case(project, project.cases()[0])
    check = eyes._check_snapshot(project, result, eyes.snapshot_text(project, result))
    assert check.status == "fail" and "hi" in check.actual


def test_reproduce_keeps_multiline_stdin_intact(tmp_path):
    project = _project(tmp_path, [{"id": "a", "argv": ["cat"], "stdin": "one\ntwo\n"}])
    result = eyes.run_case(project, project.cases()[0])
    import subprocess
    shell = eyes._reproduce(project, result)["shell"]
    out = subprocess.run(["sh", "-c", shell], capture_output=True, text=True, cwd=tmp_path).stdout
    assert out == "one\ntwo\n"
