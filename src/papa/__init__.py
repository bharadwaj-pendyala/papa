"""papa: Hemingway-grade readability for prose.

Public API:

    >>> from papa import analyze
    >>> result = analyze(open("post.md").read(), path="post.md", max_grade=10)
    >>> result.score.verdict
    'pass'
"""

from __future__ import annotations

from dataclasses import replace

from .aggregate import build_score, merge_findings
from .analyzers import ANALYZERS, AnalyzerContext
from .ingest import OffsetMap, block_breaks, ingest
from .models import Analysis, DocumentScore, Finding
from .scoring import document_grades
from .sentences import split_sentences

__version__ = "0.1.0"
__all__ = ["analyze", "Analysis", "DocumentScore", "Finding"]


def analyze(
    source: str,
    *,
    path: str = "<string>",
    fmt: str = "md",
    max_grade: float | None = None,
) -> Analysis:
    """Run the full Ingestor → Analyzers → Aggregator pipeline on ``source``."""
    clean, offset_map = ingest(source, fmt)
    sentences = split_sentences(clean, block_breaks(source, fmt, offset_map))
    ctx = AnalyzerContext(clean=clean, sentences=sentences)

    raw = [finding for analyzer in ANALYZERS.values() for finding in analyzer(ctx)]
    raw = [_remap(finding, clean, offset_map) for finding in raw]

    grades = document_grades(_as_sentences(sentences))
    score = build_score(raw, len(sentences), grades, max_grade)
    findings = merge_findings(raw)
    return Analysis(path=path, source=source, clean=clean, score=score, findings=findings)


def _as_sentences(sentences: list[tuple[int, int, str]]) -> str:
    # textstat finds sentences by punctuation; a list item or heading has none,
    # so end each one explicitly or it would merge with its neighbours.
    return " ".join(text if text[-1] in ".!?" else text + "." for _, _, text in sentences)


def _remap(finding: Finding, clean: str, offset_map: OffsetMap) -> Finding:
    return replace(
        finding,
        excerpt=" ".join(clean[finding.start:finding.end].split()),
        start=offset_map.to_original(finding.start),
        end=offset_map.to_original_end(finding.end),
    )
