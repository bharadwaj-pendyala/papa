from papa.cli import main
from papa.reporters.common import display_path

EASY = "The cat sat on the mat. The dog ran in the sun.\n"


def test_absolute_path_inside_cwd_is_made_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert display_path(str(tmp_path / "docs" / "a.md")) == "docs/a.md"


def test_paths_outside_cwd_or_relative_are_kept(tmp_path, monkeypatch):
    (tmp_path / "work").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    outside = str(tmp_path / "other" / "a.md")
    assert display_path(outside) == outside
    assert display_path("../other/a.md") == "../other/a.md"
    assert display_path("<string>") == "<string>"


def test_html_and_cli_show_relative_paths(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(EASY, encoding="utf-8")
    out = tmp_path / "report.html"

    main([str(doc), "--report", "html", "-o", str(out)])
    html = out.read_text(encoding="utf-8")
    assert "<title>papa · README.md</title>" in html
    assert '<div class="file">README.md</div>' in html
    assert str(tmp_path) not in html

    main([str(doc)])
    assert capsys.readouterr().out.startswith("README.md  ·  ")
