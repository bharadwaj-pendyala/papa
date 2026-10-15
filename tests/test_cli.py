import json

import pytest

from papa import analyze
from papa.cli import main

EASY = "The cat sat on the mat. The dog ran in the sun. We had fun today.\n"
HARD = (
    "The multifaceted implementation demonstrates considerable architectural "
    "sophistication notwithstanding the numerous interdependent complications "
    "that consistently undermine long-term maintainability across the entire "
    "distributed organization and its many downstream consumers.\n"
)


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_no_gate_exits_zero(tmp_path, capsys):
    assert main([_write(tmp_path, "easy.md", EASY)]) == 0


def test_gate_fails_on_hard_text(tmp_path, capsys):
    assert main([_write(tmp_path, "hard.md", HARD), "--max-grade", "8"]) == 1


def test_gate_passes_on_easy_text(tmp_path, capsys):
    assert main([_write(tmp_path, "easy.md", EASY), "--max-grade", "12"]) == 0


def test_missing_file_returns_two(tmp_path):
    assert main([str(tmp_path / "nope.md")]) == 2


def test_json_report_has_stable_shape(tmp_path, capsys):
    main([_write(tmp_path, "doc.md", HARD), "--report", "json"])
    data = json.loads(capsys.readouterr().out)
    assert set(data) == {"version", "file", "score", "findings"}
    assert set(data["score"]) == {
        "ari", "flesch_kincaid", "gunning_fog", "reading_grade", "sentences",
        "hard_sentences", "very_hard_sentences", "adverbs", "passive",
        "complex_phrases", "verdict", "threshold",
    }


def test_html_report_is_written_and_self_contained(tmp_path):
    out = tmp_path / "report.html"
    main([_write(tmp_path, "doc.md", HARD), "--report", "html", "-o", str(out)])
    html = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "<script" not in html and "<link" not in html and "src=" not in html
    assert "http" not in html


def test_cli_report_shows_grade_and_counts(tmp_path, capsys):
    main([_write(tmp_path, "doc.md", HARD)])
    out = capsys.readouterr().out
    assert "Grade" in out
    assert "passive" in out and "adverbs" in out


def test_offsets_round_trip_through_a_code_block():
    md = "```\nignored = 1\n```\n\nThe report was written by the team.\n"
    findings = [f for f in analyze(md, path="t.md").findings if f.category == "passive"]
    assert findings
    assert md[findings[0].start:findings[0].end] == "was written"


def _boom(*args, **kwargs):
    raise RuntimeError("kaboom")


def test_exit_codes_listed_in_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for line in ("0  every file passed", "1  a file is harder", "2  usage or file error",
                 "3  internal error"):
        assert line in out


def test_bad_option_exits_two(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--no-such-flag", "x.md"])
    assert exc.value.code == 2


def test_internal_error_exits_three(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("papa.cli.analyze", _boom)
    monkeypatch.delenv("PAPA_DEBUG", raising=False)
    assert main([_write(tmp_path, "easy.md", EASY)]) == 3
    err = capsys.readouterr().err
    assert err.splitlines()[0] == "papa: internal error: RuntimeError: kaboom"
    assert "https://github.com/bharadwaj-pendyala/papa/issues" in err
    assert "Traceback" not in err


def test_internal_error_traceback_with_papa_debug(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("papa.cli.analyze", _boom)
    monkeypatch.setenv("PAPA_DEBUG", "1")
    assert main([_write(tmp_path, "easy.md", EASY)]) == 3
    err = capsys.readouterr().err
    assert "Traceback" in err
    assert "papa: internal error: RuntimeError: kaboom" in err
