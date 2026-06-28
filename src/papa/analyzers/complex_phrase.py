"""Complex / weasel phrases: a curated wordy-phrase list with simpler swaps (spec §5)."""

from __future__ import annotations

import re

from ..models import COLOR, COMPLEX, Finding
from . import AnalyzerContext, register

_PHRASES = {
    "in order to": "to",
    "due to the fact that": "because",
    "in the event that": "if",
    "in spite of the fact that": "although",
    "with regard to": "about",
    "with respect to": "about",
    "for the purpose of": "for",
    "in conjunction with": "with",
    "a number of": "some / many",
    "a majority of": "most",
    "at this point in time": "now",
    "at the present time": "now",
    "subsequent to": "after",
    "prior to": "before",
    "in addition to": "besides",
    "in terms of": "in",
    "the fact that": "that",
    "on a regular basis": "regularly",
    "in a timely manner": "promptly",
    "take into consideration": "consider",
    "give consideration to": "consider",
    "make a decision": "decide",
    "has the ability to": "can",
    "is able to": "can",
    "are able to": "can",
    "utilize": "use",
    "utilization": "use",
    "facilitate": "help",
    "endeavor": "try",
}

# Longest first so multi-word phrases win over any shorter substring.
_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in sorted(_PHRASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


@register("complex-phrase")
def analyze(ctx: AnalyzerContext) -> list[Finding]:
    findings = []
    for match in _PATTERN.finditer(ctx.clean):
        suggestion = _PHRASES.get(match.group().lower(), "")
        message = f"Complex phrase: '{match.group()}'"
        if suggestion:
            message += f", consider '{suggestion}'"
        findings.append(
            Finding(match.start(), match.end(), COMPLEX, COLOR[COMPLEX], "warn",
                    message, "complex-phrase")
        )
    return findings
