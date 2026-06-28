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
from .ingest import OffsetMap, ingest
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
    sentences = split_sentences(clean)
    ctx = AnalyzerContext(clean=clean, sentences=sentences)

    raw = [finding for analyzer in ANALYZERS.values() for finding in analyzer(ctx)]
    raw = [_remap(finding, offset_map) for finding in raw]

    grades = document_grades(clean)
    score = build_score(raw, len(sentences), grades, max_grade)
    findings = merge_findings(raw)
    return Analysis(path=path, source=source, clean=clean, score=score, findings=findings)


def _remap(finding: Finding, offset_map: OffsetMap) -> Finding:
    return replace(
        finding,
        start=offset_map.to_original(finding.start),
        end=offset_map.to_original_end(finding.end),
    )
