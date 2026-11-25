"""Merge findings and build the document score (spec §6)."""

from __future__ import annotations

from .models import (
    ADVERB,
    COMPLEX,
    HARD,
    PASSIVE,
    PRIORITY,
    VERY_HARD,
    DocumentScore,
    Finding,
)
from .scoring import reading_grade

_SENTENCE_CATS = {HARD, VERY_HARD}


def _overlaps(a: Finding, b: Finding) -> bool:
    return a.start < b.end and b.start < a.end


def merge_findings(findings: list[Finding]) -> list[Finding]:
    """Sentence highlights are their own layer (they nest word spans); for
    overlapping word-level spans, keep the higher-priority one."""
    sentence = [f for f in findings if f.category in _SENTENCE_CATS]
    word = sorted(
        (f for f in findings if f.category not in _SENTENCE_CATS),
        key=lambda f: (f.start, -PRIORITY[f.category]),
    )
    kept: list[Finding] = []
    for finding in word:
        if kept and _overlaps(kept[-1], finding):
            if PRIORITY[finding.category] > PRIORITY[kept[-1].category]:
                kept[-1] = finding
            continue
        kept.append(finding)
    return sorted(sentence + kept, key=lambda f: (f.start, -f.end))


def build_score(
    findings: list[Finding],
    sentence_count: int,
    grades: tuple[float, float, float, float],
    max_grade: float | None,
    baseline: float | None = None,
    max_regression: float = 1.0,
) -> DocumentScore:
    ari, fk, fog, consensus = grades
    label, _ = reading_grade(consensus)  # rounded grade is display-only
    # Gate on the consensus as JSON reports it (4 decimals), not the rounded
    # display grade: 10.4 is harder than 10 and must fail even though it
    # displays as "Grade 10".
    shown = round(consensus, 4)
    if baseline is not None:
        verdict = "fail" if round(shown - baseline, 4) > max_regression else "pass"
        threshold = {"baseline": baseline, "max_regression": _clean(max_regression)}
    elif max_grade is not None:
        verdict = "fail" if shown > max_grade else "pass"
        threshold = {"max_grade": _clean(max_grade)}
    else:
        verdict, threshold = "pass", None

    return DocumentScore(
        # Adding 0.0 turns a rounded -0.0 into 0.0.
        ari=round(ari, 1) + 0.0,
        flesch_kincaid=round(fk, 1) + 0.0,
        gunning_fog=round(fog, 1) + 0.0,
        consensus=round(consensus, 4),
        reading_grade=label,
        sentences=sentence_count,
        hard_sentences=_count(findings, HARD),
        very_hard_sentences=_count(findings, VERY_HARD),
        adverbs=_count(findings, ADVERB),
        passive=_count(findings, PASSIVE),
        complex_phrases=_count(findings, COMPLEX),
        verdict=verdict,
        threshold=threshold,
    )


def _clean(value: float) -> float:
    return int(value) if float(value).is_integer() else value


def _count(findings: list[Finding], category: str) -> int:
    return sum(1 for f in findings if f.category == category)
