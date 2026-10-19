import json

import pytest

from papa import analyze
from papa.cli import main

NO_PROSE = {
    "empty": "",
    "whitespace": "  \n\n\t\n   \n",
    "code-only": "# Setup\n\n```bash\npip install papa-lint and run it now\n```\n",
    "frontmatter-only": "---\ntitle: A long title with many words\ntags: [a, b]\n---\n",
}


def _write(tmp_path, text):
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("text", NO_PROSE.values(), ids=NO_PROSE.keys())
def test_no_prose_is_skipped(text):
    score = analyze(text, max_grade=6).score
    assert score.verdict == "skip"
    assert score.reading_grade == "No prose found"


@pytest.mark.parametrize("text", NO_PROSE.values(), ids=NO_PROSE.keys())
def test_no_prose_does_not_fail_the_gate(tmp_path, capsys, text):
    assert main([_write(tmp_path, text), "--max-grade", "6"]) == 0
    out = capsys.readouterr().out
    assert "No prose found" in out
    assert "Grade" not in out


@pytest.mark.parametrize("text", NO_PROSE.values(), ids=NO_PROSE.keys())
def test_fail_on_empty_exits_one(tmp_path, capsys, text):
    assert main([_write(tmp_path, text), "--fail-on-empty"]) == 1


def test_fail_on_empty_ignores_files_with_prose(tmp_path, capsys):
    text = "The cat sat on the mat. The dog ran in the sun.\n"
    assert main([_write(tmp_path, text), "--fail-on-empty"]) == 0


def test_json_verdict_is_skip(tmp_path, capsys):
    main([_write(tmp_path, ""), "--report", "json", "--max-grade", "6"])
    score = json.loads(capsys.readouterr().out)["score"]
    assert score["verdict"] == "skip"
    assert score["threshold"] == {"max_grade": 6}


def test_html_says_no_prose_found(tmp_path):
    out = tmp_path / "report.html"
    main([_write(tmp_path, "# Title\n"), "--report", "html", "-o", str(out), "--max-grade", "6"])
    html = out.read_text(encoding="utf-8")
    assert '<div class="grade">No prose found</div>' in html
    assert '<span class="verdict skip">SKIP' in html
    assert "Grade" not in html
