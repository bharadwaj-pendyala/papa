import pytest

pytest.importorskip("mcp")

import anyio  # noqa: E402

from papa.mcp_server import grade_files, grade_text, server  # noqa: E402

PASSIVE = "The plan was approved by the board.\n"


def test_grade_text_returns_the_json_contract():
    result = grade_text(PASSIVE)
    assert result["version"] == "0.2"
    assert [f["category"] for f in result["files"][0]["findings"]] == ["passive"]


def test_grade_text_gives_a_verdict_with_max_grade():
    assert grade_text(PASSIVE, max_grade=0)["files"][0]["score"]["verdict"] == "fail"


def test_grade_text_grades_against_10_by_default():
    hard = "The multifaceted implementation demonstrates considerable architectural sophistication. " * 3
    result = grade_text(hard)
    assert result["summary"]["max_grade"] == 10
    assert result["files"][0]["score"]["verdict"] == "fail"


def test_grade_files_grades_against_10_without_config(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text(PASSIVE)
    monkeypatch.chdir(tmp_path)
    assert grade_files(["a.md"])["summary"]["max_grade"] == 10


def test_grade_text_skips_code_only_drafts():
    result = grade_text("```\nx = 1\n```\n")
    assert result["files"] == [] and result["skipped"][0]["file"] == "draft.md"


def test_grade_files_reads_config_and_reports_missing_files(tmp_path, monkeypatch):
    (tmp_path / "papa.toml").write_text("[papa]\nmax-grade = 0\n")
    (tmp_path / "a.md").write_text(PASSIVE)
    monkeypatch.chdir(tmp_path)
    result = grade_files(["a.md", "missing.md"])
    assert result["files"][0]["score"]["verdict"] == "fail"
    assert result["errors"][0]["file"] == "missing.md"


def test_grade_files_reports_an_unmatched_glob(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert grade_files(["nope/*.md"])["errors"]


def test_server_lists_both_tools_as_read_only():
    tools = anyio.run(server.list_tools)
    assert {t.name for t in tools} == {"grade_text", "grade_files"}
    assert all(t.annotations.read_only_hint for t in tools)
