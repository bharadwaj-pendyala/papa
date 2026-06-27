"""Adverbs: words ending in -ly, minus a list of common non-adverbs (spec §5)."""

from __future__ import annotations

import re

from ..models import ADVERB, COLOR, Finding
from . import AnalyzerContext, register

_WORD = re.compile(r"[A-Za-z]+")
_NOT_ADVERBS = {
    "only", "family", "reply", "apply", "supply", "comply", "rely", "ally",
    "early", "ugly", "likely", "unlikely", "friendly", "unfriendly", "lovely",
    "lonely", "lively", "deadly", "daily", "weekly", "monthly", "yearly", "holy",
    "silly", "jolly", "ghastly", "ghostly", "italy", "july", "assembly", "anomaly",
    "belly", "jelly", "rally", "tally", "folly", "imply", "multiply", "monopoly",
    "panoply", "homily", "melancholy", "wobbly", "bubbly", "crumbly", "measly",
    "cuddly", "prickly", "gnarly", "bully", "fully",
}


@register("adverbs")
def analyze(ctx: AnalyzerContext) -> list[Finding]:
    findings = []
    for match in _WORD.finditer(ctx.clean):
        word = match.group().lower()
        if len(word) >= 4 and word.endswith("ly") and word not in _NOT_ADVERBS:
            findings.append(
                Finding(match.start(), match.end(), ADVERB, COLOR[ADVERB], "info",
                        f"Adverb: '{match.group()}'", "adverbs")
            )
    return findings
