"""papa: Hemingway-grade readability for prose.

Public API:

    >>> from papa import analyze
    >>> result = analyze(open("post.md").read(), path="post.md", max_grade=10)
    >>> result.score.verdict
    'pass'
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import replace

from .aggregate import build_score, merge_findings
from .analyzers import ANALYZERS, AnalyzerContext
from .analyzers.readability import MIN_WORDS, WORD
from .ingest import OffsetMap, block_breaks, ingest
from .models import Analysis, DocumentScore, Finding
from .scoring import document_grades
from .sentences import split_sentences

__version__ = "0.3.0"
_SENTENCE_END = re.compile(r"[.!?][\"'\u201d\u2019)\]]*$")
__all__ = ["analyze", "Analysis", "DocumentScore", "Finding"]


def analyze(
    source: str,
    *,
    path: str = "<string>",
    fmt: str = "md",
    max_grade: float | None = None,
    baseline: float | None = None,
    max_regression: float = 1.0,
) -> Analysis:
    """Run the full Ingestor → Analyzers → Aggregator pipeline on ``source``.

    With ``baseline``, the file fails when its grade rises more than
    ``max_regression`` above that grade, and ``max_grade`` does not apply.
    """
    # Every Markdown pattern expects LF, so CRLF files run as LF and map back.
    text = source.replace("\r\n", "\n")
    clean, offset_map = ingest(text, fmt)
    sentences = split_sentences(clean, block_breaks(text, fmt, offset_map))
    ctx = AnalyzerContext(clean=clean, sentences=sentences)

    raw = [finding for analyzer in ANALYZERS.values() for finding in analyzer(ctx)]
    raw = [_remap(finding, clean, offset_map) for finding in raw]

    grades = document_grades(_as_sentences(_graded(sentences)))
    score = build_score(raw, len(sentences), grades, max_grade, baseline, max_regression)
    findings = merge_findings(raw)
    if text != source:
        findings = _to_crlf_offsets(findings, source)
    return Analysis(path=path, source=source, clean=clean, score=score, findings=findings)


def _graded(sentences: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    # A short heading or label like "Authentication configuration" has many
    # syllables and no sentence around it, so the formulas read it as grade 17.
    prose = [s for s in sentences if _SENTENCE_END.search(s[2]) or len(WORD.findall(s[2])) >= MIN_WORDS]
    return prose or sentences


def _as_sentences(sentences: list[tuple[int, int, str]]) -> str:
    # textstat finds sentences by punctuation; a list item or heading has none,
    # so end each one explicitly or it would merge with its neighbours.
    return " ".join(text if text[-1] in ".!?" else text + "." for _, _, text in sentences)


def _to_crlf_offsets(findings: list[Finding], source: str) -> list[Finding]:
    # Each LF newline before a position stood for a CRLF, one character longer.
    crlf_newlines = [i - n for n, i in enumerate(m.start() for m in re.finditer("\r\n", source))]

    def shift(pos: int) -> int:
        return pos + bisect_left(crlf_newlines, pos)

    return [replace(f, start=shift(f.start), end=shift(f.end)) for f in findings]


def _remap(finding: Finding, clean: str, offset_map: OffsetMap) -> Finding:
    return replace(
        finding,
        excerpt=" ".join(clean[finding.start:finding.end].split()),
        start=offset_map.to_original(finding.start),
        end=offset_map.to_original_end(finding.end),
    )
