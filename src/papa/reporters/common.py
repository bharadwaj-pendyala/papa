"""Display helpers shared by the terminal and HTML reporters."""

from __future__ import annotations

from ..analyzers.readability import MIN_WORDS
from ..models import DocumentScore

SKIP_REASON = f"nothing to grade: no sentence has {MIN_WORDS} or more words"


def noun(count: int, singular: str, many: str | None = None) -> str:
    return singular if count == 1 else many or singular + "s"


def plural(count: int, singular: str, many: str | None = None) -> str:
    """``1 sentence`` / ``2 sentences``; pass ``many`` for irregular plurals."""
    return f"{count} {noun(count, singular, many)}"


def fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def grade_label(score: DocumentScore) -> str:
    """``Grade 6.3 · limit 6 ✗`` when gated, else the rounded ``Grade 6, easy to read``."""
    if score.verdict == "skip" or score.threshold is None:
        return score.reading_grade
    mark = "✓" if score.verdict == "pass" else "✗"
    return f"Grade {score.grade:.1f} · limit {fmt_number(score.threshold['max_grade'])} {mark}"
