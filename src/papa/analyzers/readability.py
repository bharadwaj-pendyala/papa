"""Per-sentence readability: mark hard (>=10) and very-hard (>=14) sentences."""

from __future__ import annotations

import re

from ..models import COLOR, HARD, VERY_HARD, Finding
from ..scoring import sentence_grade
from . import AnalyzerContext, register

_WORD = re.compile(r"[A-Za-z]+")
MIN_WORDS = 4  # don't grade fragments (headings, nav, markup); README `sentences_under_words`


@register("readability")
def analyze(ctx: AnalyzerContext) -> list[Finding]:
    findings = []
    for start, end, text in ctx.sentences:
        if len(_WORD.findall(text)) < MIN_WORDS:
            continue
        grade = sentence_grade(text)
        if grade >= 14:
            findings.append(
                Finding(start, end, VERY_HARD, COLOR[VERY_HARD], "error",
                        f"Very hard to read (grade {round(grade)})", "readability")
            )
        elif grade >= 10:
            findings.append(
                Finding(start, end, HARD, COLOR[HARD], "warn",
                        f"Hard to read (grade {round(grade)})", "readability")
            )
    return findings
