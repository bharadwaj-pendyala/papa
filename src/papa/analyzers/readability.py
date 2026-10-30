"""Per-sentence readability: mark hard (>=10) and very-hard (>=14) sentences."""

from __future__ import annotations

import re

from ..models import COLOR, HARD, VERY_HARD, Finding
from ..scoring import sentence_grade
from . import AnalyzerContext, register

_WORD = re.compile(r"[A-Za-z]+")
_HINT = "Split the sentence or cut words. Aim for one idea per sentence."
# Grade formulas swing wildly on short sentences: "Interrogate before you
# generate." scores 15. Below this length a sentence is never "hard" to read,
# and headings, labels and table cells drop out too.
MIN_WORDS = 8


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
                        f"Very hard to read (grade {_shown(grade)})", "readability", _HINT)
            )
        elif grade >= 10:
            findings.append(
                Finding(start, end, HARD, COLOR[HARD], "warn",
                        f"Hard to read (grade {_shown(grade)})", "readability", _HINT)
            )
    return findings


def _shown(grade: float) -> str:
    # Past college level the number stops meaning anything to a reader.
    return "18+" if grade >= 18 else str(round(grade))
