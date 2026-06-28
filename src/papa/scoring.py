"""Readability scoring via textstat: a consensus grade, not one gameable number.

A single formula is noisy and easy to game, so the document grade is the mean of
ARI, Flesch-Kincaid, and Gunning fog (spec §2.5, §6). Per-sentence grades use
ARI + FK (spec §5 table). All scoring runs on normalized text.
"""

from __future__ import annotations

import textstat

from .normalize import normalize


def _formula_grades(text: str) -> tuple[float, float, float]:
    return (
        textstat.automated_readability_index(text),
        textstat.flesch_kincaid_grade(text),
        textstat.gunning_fog(text),
    )


def document_grades(clean_text: str) -> tuple[float, float, float, float]:
    """Return (ari, flesch_kincaid, gunning_fog, consensus) on normalized text."""
    ari, fk, fog = _formula_grades(normalize(clean_text))
    return ari, fk, fog, (ari + fk + fog) / 3


def sentence_grade(sentence: str) -> float:
    """Per-sentence consensus grade (ARI + FK), on normalized text."""
    ari, fk, _ = _formula_grades(normalize(sentence))
    return (ari + fk) / 2


def reading_grade(consensus: float) -> tuple[str, int]:
    """Return the display label and the integer grade used for gating."""
    grade = max(0, round(consensus))
    if grade < 10:
        label = "easy to read"
    elif grade < 14:
        label = "hard to read"
    else:
        label = "very hard to read"
    return f"Grade {grade}, {label}", grade
