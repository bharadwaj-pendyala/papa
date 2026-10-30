import json

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
    assert set(data) == {"version", "files", "skipped", "errors", "summary"}
    assert data["version"] == "0.2"
    assert set(data["files"][0]["score"]) == {
        "ari", "flesch_kincaid", "gunning_fog", "consensus", "reading_grade", "sentences",
        "hard_sentences", "very_hard_sentences", "adverbs", "passive",
        "complex_phrases", "verdict", "threshold",
    }


def test_json_findings_carry_line_column_and_hint(tmp_path, capsys):
    main([_write(tmp_path, "doc.md", "Intro line.\n\nThe bug was fixed.\n"), "--report", "json"])
    finding = json.loads(capsys.readouterr().out)["files"][0]["findings"][0]
    assert (finding["line"], finding["column"]) == (3, 9)
    assert finding["hint"]


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
    assert "very hard sentence" in out and "adverb" in out


def test_offsets_round_trip_through_a_code_block():
    md = "```\nignored = 1\n```\n\nThe report was written by the team.\n"
    findings = [f for f in analyze(md, path="t.md").findings if f.category == "passive"]
    assert findings
    assert md[findings[0].start:findings[0].end] == "was written"


def test_unreadable_file_is_reported_and_others_still_run(tmp_path, capsys):
    code = main([_write(tmp_path, "easy.md", EASY), str(tmp_path / "nope.md")])
    captured = capsys.readouterr()
    assert code == 2
    assert "easy.md" in captured.out
    assert "nope.md" in captured.err


def test_directory_input_finds_prose_files(tmp_path, capsys):
    _write(tmp_path, "a.md", EASY)
    _write(tmp_path, "b.txt", EASY)
    _write(tmp_path, "skip.py", "print(1)")
    assert main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "a.md" in out and "b.txt" in out and "skip.py" not in out
    assert "Checked 2 files" in out


def test_config_sets_max_grade(tmp_path, monkeypatch, capsys):
    _write(tmp_path, "papa.toml", "[papa]\nmax-grade = 8\n")
    _write(tmp_path, "hard.md", HARD)
    monkeypatch.chdir(tmp_path)
    assert main(["hard.md"]) == 1


def test_unknown_config_key_suggests_the_right_one(tmp_path, monkeypatch, capsys):
    _write(tmp_path, "papa.toml", "[papa]\nmax-grde = 8\n")
    _write(tmp_path, "easy.md", EASY)
    monkeypatch.chdir(tmp_path)
    assert main(["easy.md"]) == 2
    assert "did you mean 'max-grade'" in capsys.readouterr().err


def test_exclude_accepts_any_valid_glob_class(tmp_path, capsys):
    path = _write(tmp_path, "easy.md", EASY)
    assert main([path, "--exclude", "[!]].txt", "--report", "json"]) == 0
    assert main([path, "--exclude", str(tmp_path / "[!x]asy.md")]) == 2


def test_exclude_classes_follow_fnmatch_rules(tmp_path, capsys):
    for name in ("A.txt", "-.txt", "x.txt"):
        _write(tmp_path, name, EASY)
    main([str(tmp_path), "--exclude", str(tmp_path / "[!-a].txt")])
    out = capsys.readouterr().out
    assert "-.txt" in out and "A.txt" not in out and "x.txt" not in out
    assert main([str(tmp_path), "--exclude", str(tmp_path / "[z-a].txt"), "--report", "json"]) == 0
