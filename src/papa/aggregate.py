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
    return sorted(sentence + kept, key=lambda f: (f.start, f.end))


def build_score(
    findings: list[Finding],
    sentence_count: int,
    grades: tuple[float, float, float, float],
    max_grade: float | None,
) -> DocumentScore:
    ari, fk, fog, consensus = grades
    label, grade = reading_grade(consensus)
    if max_grade is None:
        verdict, threshold = "pass", None
    else:
        verdict = "fail" if grade > max_grade else "pass"
        clean_max = int(max_grade) if float(max_grade).is_integer() else max_grade
        threshold = {"max_grade": clean_max}

    return DocumentScore(
        ari=round(ari, 1),
        flesch_kincaid=round(fk, 1),
        gunning_fog=round(fog, 1),
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


def _count(findings: list[Finding], category: str) -> int:
    return sum(1 for f in findings if f.category == category)
