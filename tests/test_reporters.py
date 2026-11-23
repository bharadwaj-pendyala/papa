import json

import pytest

from papa import analyze
from papa.models import Run
from papa.reporters import REPORTERS
from papa.reporters.common import LineIndex


def _rescan(source: str, offset: int) -> tuple[int, int]:
    line = source.count("\n", 0, offset) + 1
    return line, offset - (source.rfind("\n", 0, offset) + 1) + 1


@pytest.mark.parametrize("source", ["", "one line", "a\nb\n", "\n\nx", "crlf\r\nline two\r\n", "é\nü ö\n"])
def test_line_index_agrees_with_a_rescan_at_every_offset(source):
    index = LineIndex(source)
    for offset in range(len(source) + 1):
        assert index.line_col(offset) == _rescan(source, offset)

PASSIVE_TWICE = "The plan was approved by the board.\nThe budget was cut.\n"


def _run(*analyses, errors=(), max_grade=None):
    return Run(analyses=list(analyses), skipped=[], errors=list(errors), max_grade=max_grade)


def _sarif(run):
    return json.loads(REPORTERS["sarif"](run))["runs"][0]


def test_sarif_uri_is_percent_encoded_and_relative():
    run = _run(analyze(PASSIVE_TWICE, path="docs/meeting notes.md"))
    uris = {r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for r in _sarif(run)["results"]}
    assert uris == {"docs/meeting%20notes.md"}


def test_sarif_absolute_path_becomes_a_file_uri():
    run = _run(analyze(PASSIVE_TWICE, path="/tmp/a b.md"))
    assert _sarif(run)["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "file:///tmp/a%20b.md"


def test_sarif_findings_are_warnings_and_only_the_gate_is_an_error():
    run = _run(analyze(PASSIVE_TWICE, path="a.md", max_grade=0), max_grade=0)
    levels = {r["ruleId"]: r["level"] for r in _sarif(run)["results"]}
    assert levels == {"max-grade": "error", "passive": "warning"}


def test_github_annotation_escapes_property_delimiters():
    out = REPORTERS["github"](_run(analyze(PASSIVE_TWICE, path="a,b:c%.md")))
    assert out.startswith("::warning file=a%2Cb%3Ac%25.md,line=1,")


def test_github_multiline_annotation_has_no_columns():
    source = "This sentence was\nwritten across two lines.\n"
    out = REPORTERS["github"](_run(analyze(source, path="a.txt", fmt="txt")))
    assert "line=1,endLine=2,title=papa passive::" in out


def test_github_reports_input_errors():
    out = REPORTERS["github"](_run(errors=[("missing.md", "no such file or directory")]))
    assert out == "::error file=missing.md,title=papa error::no such file or directory\n"


def test_markdown_escapes_table_breaking_text():
    source = "The value | of x was computed by `eval`.\n"
    out = REPORTERS["markdown"](_run(analyze(source, path="a|b.md")))
    assert "`a\\|b.md`" in out
    assert "| was computed |" in out


def test_markdown_caps_detailed_files():
    analyses = [analyze(PASSIVE_TWICE, path=f"f{i}.md") for i in range(25)]
    out = REPORTERS["markdown"](_run(*analyses))
    assert out.count("<details") == 20
    assert "5 more files with findings" in out
