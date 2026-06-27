"""Passive voice: a be-verb followed (optionally past an adverb) by a past
participle. A ~40-line heuristic, in-language, no heavy deps (spec §5)."""

from __future__ import annotations

import re

from ..models import COLOR, PASSIVE, Finding
from . import AnalyzerContext, register

_WORD = re.compile(r"[A-Za-z']+")
_BE = {"is", "are", "was", "were", "be", "been", "being", "am", "get", "got", "gets", "gotten"}
_IRREGULAR = {
    "done", "made", "seen", "known", "given", "taken", "written", "said", "gone",
    "found", "held", "kept", "told", "brought", "bought", "caught", "taught",
    "thought", "sought", "built", "sent", "spent", "meant", "felt", "left", "lost",
    "paid", "read", "run", "cut", "put", "set", "hit", "let", "shut", "cost", "hurt",
    "shown", "drawn", "grown", "thrown", "blown", "flown", "broken", "chosen",
    "frozen", "spoken", "stolen", "driven", "risen", "ridden", "fallen", "eaten",
    "beaten", "forgotten", "hidden", "bitten", "worn", "torn", "born", "sworn",
    "won", "met", "sold", "dealt",
}


def _is_participle(word: str) -> bool:
    return word in _IRREGULAR or (len(word) > 3 and word.endswith("ed"))


@register("passive")
def analyze(ctx: AnalyzerContext) -> list[Finding]:
    tokens = [(m.group().lower(), m.start(), m.end()) for m in _WORD.finditer(ctx.clean)]
    findings = []
    for i, (word, start, _end) in enumerate(tokens):
        if word not in _BE:
            continue
        for nxt, _nstart, nend in tokens[i + 1 : i + 3]:
            if _is_participle(nxt):
                phrase = ctx.clean[start:nend]
                findings.append(
                    Finding(start, nend, PASSIVE, COLOR[PASSIVE], "warn",
                            f"Passive voice: '{phrase}'", "passive")
                )
                break
            if not nxt.endswith("ly"):  # only an adverb may sit between be-verb and participle
                break
    return findings
