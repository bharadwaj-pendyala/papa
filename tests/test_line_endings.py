import json
import re

import pytest

from papa import analyze
from papa.cli import main
from papa.sentences import split_sentences

LF = (
    "---\ntitle: Notes\n---\n\n"
    "# Heading\n\n"
    "This is extremely important.\n"
    "It is used by people who work here daily.\n\n"
    "```\nit was written badly\n```\n\n"
    "The report was written by the team quickly. "
    "We did this in order to help.\n"
)
CRLF = LF.replace("\n", "\r\n")
MIXED = "".join(
    line + ("\r\n" if i % 2 else "\n")
    for i, line in enumerate(LF.split("\n")[:-1])
)
_QUOTED = re.compile(r"'([^']+)'")


def _check_offsets(source, findings):
    quoted = [f for f in findings if _QUOTED.search(f.message)]
    assert quoted
    for finding in quoted:
        word = _QUOTED.search(finding.message).group(1)
        assert source[finding.start:finding.end] == word, finding


@pytest.mark.parametrize("source", [LF, CRLF, MIXED], ids=["lf", "crlf", "mixed"])
def test_offsets_index_the_exact_source(source):
    _check_offsets(source, analyze(source, path="t.md").findings)


@pytest.mark.parametrize("source", [CRLF, MIXED], ids=["crlf", "mixed"])
def test_same_findings_as_lf(source):
    lf = [(f.category, f.message) for f in analyze(LF).findings]
    other = [(f.category, f.message) for f in analyze(source).findings]
    assert other == lf


def test_crlf_code_and_frontmatter_still_stripped():
    messages = " ".join(f.message for f in analyze(CRLF).findings)
    assert "badly" not in messages
    assert "Notes" not in analyze(CRLF).clean


@pytest.mark.parametrize("source", [CRLF, MIXED], ids=["crlf", "mixed"])
def test_cli_reads_bytes_as_on_disk(tmp_path, capsys, source):
    path = tmp_path / "doc.md"
    path.write_bytes(source.encode("utf-8"))
    main([str(path), "--report", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["findings"]
    on_disk = path.read_bytes().decode("utf-8")
    for finding in data["findings"]:
        match = _QUOTED.search(finding["message"])
        if match:
            assert on_disk[finding["start"]:finding["end"]] == match.group(1)


def test_cli_line_numbers_match_crlf_lines(tmp_path, capsys):
    path = tmp_path / "doc.md"
    path.write_bytes(CRLF.encode("utf-8"))
    main([str(path)])
    out = capsys.readouterr().out
    assert re.search(r"L7\s+adverb\s+Adverb: 'extremely'", out)
    assert re.search(r"L8\s+passive\s+Passive voice: 'is used'", out)
    assert re.search(r"L14\s+passive\s+Passive voice: 'was written'", out)


def test_splitter_treats_crlf_blank_line_as_boundary():
    text = "A heading\r\n\r\nSome prose here"
    assert [s[2] for s in split_sentences(text)] == ["A heading", "Some prose here"]
