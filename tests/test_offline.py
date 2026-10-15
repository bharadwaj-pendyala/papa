"""Papa must work with no network: no corpus downloads, no lookups."""

import socket
import sys

import pytest

import papa
from papa.cli import main


def _no_network(*args, **kwargs):
    raise AssertionError("papa tried to use the network")


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(socket, "socket", _no_network)
    monkeypatch.setattr(socket, "create_connection", _no_network)
    monkeypatch.setattr(socket, "getaddrinfo", _no_network)


TEXT = (
    "# Notes\n\n"
    "The committee deliberated extensively over the contentious proposal. "
    "It was quickly approved by the board. We went home happy.\n"
)


def test_analyze_needs_no_network(offline):
    result = papa.analyze(TEXT, max_grade=30)
    assert result.score.verdict == "pass"
    assert result.score.flesch_kincaid > 0
    assert result.score.reading_grade.startswith("Grade")


def test_cli_needs_no_network(offline, tmp_path, capsys):
    path = tmp_path / "doc.md"
    path.write_text(TEXT, encoding="utf-8")
    assert main([str(path), "--report", "json"]) == 0
    assert '"flesch_kincaid"' in capsys.readouterr().out


def test_scoring_imports_no_downloader():
    papa.analyze(TEXT)
    assert "nltk" not in sys.modules
    assert "textstat" not in sys.modules
