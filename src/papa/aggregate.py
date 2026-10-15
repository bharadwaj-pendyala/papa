"""Merge findings and build the document score (spec §6)."""

from __future__ import annotations

import math
import re

from .analyzers.readability import MIN_WORDS
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
_WORD = re.compile(r"[A-Za-z]+")

NO_PROSE = "No prose found"


def prose_sentences(sentences: list[tuple[int, int, str]]) -> int:
    """Sentences long enough to grade (the same MIN_WORDS bar as readability)."""
    return sum(1 for _, _, text in sentences if len(_WORD.findall(text)) >= MIN_WORDS)


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
    *,
    has_prose: bool = True,
) -> DocumentScore:
    """``verdict`` is "pass", "fail", or "skip" when there is no prose to grade."""
    ari, fk, fog, consensus = grades
    label, _ = reading_grade(consensus)  # rounded grade is display-only
    if max_grade is None:
        verdict, threshold = "pass", None
    else:
        # gate on the raw consensus, not the rounded display grade: 10.4 is
        # harder than 10 and must fail even though it displays as "Grade 10".
        verdict = "fail" if consensus > max_grade else "pass"
        clean_max = int(max_grade) if float(max_grade).is_integer() else max_grade
        threshold = {"max_grade": clean_max}
    grade = _display_grade(consensus, max_grade)
    if not has_prose:
        verdict, label, grade = "skip", NO_PROSE, 0.0

    return DocumentScore(
        ari=round(ari, 1),
        flesch_kincaid=round(fk, 1),
        gunning_fog=round(fog, 1),
        reading_grade=label,
        grade=grade,
        sentences=sentence_count,
        hard_sentences=_count(findings, HARD),
        very_hard_sentences=_count(findings, VERY_HARD),
        adverbs=_count(findings, ADVERB),
        passive=_count(findings, PASSIVE),
        complex_phrases=_count(findings, COMPLEX),
        verdict=verdict,
        threshold=threshold,
    )


def _display_grade(consensus: float, max_grade: float | None) -> float:
    # One decimal, nudged so 6.04 over a limit of 6 shows 6.1, never "6.0 fails 6".
    grade = round(max(consensus, 0.0), 1)
    if max_grade is None:
        return grade
    if consensus > max_grade and grade <= max_grade:
        return math.ceil(consensus * 10) / 10
    if consensus <= max_grade and grade > max_grade:
        return math.floor(consensus * 10) / 10
    return grade


def _count(findings: list[Finding], category: str) -> int:
    return sum(1 for f in findings if f.category == category)
