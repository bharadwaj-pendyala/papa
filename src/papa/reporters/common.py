"""Display helpers shared by the terminal and HTML reporters."""

from __future__ import annotations

from ..models import DocumentScore


def fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def grade_label(score: DocumentScore) -> str:
    """``Grade 6.3 · limit 6 ✗`` when gated, else the rounded ``Grade 6, easy to read``."""
    if score.threshold is None:
        return score.reading_grade
    mark = "✓" if score.verdict == "pass" else "✗"
    return f"Grade {score.grade:.1f} · limit {fmt_number(score.threshold['max_grade'])} {mark}"
