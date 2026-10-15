import pytest

from papa.aggregate import build_score
from papa.models import Analysis
from papa.reporters.cli import render as render_cli
from papa.reporters.html import render as render_html


def _analysis(score, path="doc.md"):
    return Analysis(path=path, source="", clean="", score=score, findings=[])


def _score(consensus, max_grade=None, sentences=5):
    return build_score([], sentences, (consensus,) * 4, max_grade)


@pytest.mark.parametrize(
    "consensus, max_grade, shown",
    [
        (6.3, 6, 6.3),
        (5.8, 6, 5.8),
        (6.04, 6, 6.1),  # fails, so never shows 6.0
        (6.0, 6, 6.0),
        (6.26, 6.26, 6.2),  # passes, so never shows 6.3
        (-3.0, None, 0.0),
    ],
)
def test_grade_is_one_decimal_and_agrees_with_verdict(consensus, max_grade, shown):
    assert _score(consensus, max_grade).grade == shown


def test_cli_shows_decimal_grade_and_limit():
    out = render_cli(_analysis(_score(6.3, 6)))
    assert out.splitlines()[0] == "doc.md  ·  Grade 6.3 · limit 6 ✗"
    out = render_cli(_analysis(_score(5.8, 6)))
    assert out.splitlines()[0] == "doc.md  ·  Grade 5.8 · limit 6 ✓"


def test_cli_without_limit_keeps_integer_label():
    out = render_cli(_analysis(_score(6.3)))
    assert out.splitlines()[0] == "doc.md  ·  Grade 6, easy to read"


def test_html_shows_decimal_grade_and_limit():
    html = render_html(_analysis(_score(6.3, 6)))
    assert '<div class="grade">Grade 6.3 · limit 6 ✗</div>' in html
    html = render_html(_analysis(_score(6.3)))
    assert '<div class="grade">Grade 6, easy to read</div>' in html


def _counted(**counts):
    score = _score(5.0, sentences=counts.pop("sentences", 5))
    for name, value in counts.items():
        setattr(score, name, value)
    return _analysis(score)


def test_cli_counts_use_singular_for_one():
    out = render_cli(_counted(sentences=1, adverbs=1, hard_sentences=1))
    assert "1 hard · 0 very hard · 0 passive · 1 adverb · 0 complex" in out
    assert "(1 sentence)" in out


def test_cli_counts_use_plural_otherwise():
    out = render_cli(_counted(sentences=2, adverbs=0))
    assert "0 adverbs" in out and "(2 sentences)" in out


def test_html_counts_agree_with_number():
    html = render_html(_counted(sentences=1, adverbs=1, complex_phrases=2, passive=2))
    assert "<br>1 sentence</div>" in html
    assert 'Adverb<span class="count">1</span>' in html
    assert 'Complex phrases<span class="count">2</span>' in html
    assert 'Passive voice<span class="count">2</span>' in html
    assert 'Very hard sentences<span class="count">0</span>' in html
