"""Colored terminal report: grade + counts + flagged lines (spec §7)."""

from __future__ import annotations

from ..models import (
    ADVERB,
    COLOR,
    COMPLEX,
    HARD,
    PASSIVE,
    VERY_HARD,
    Analysis,
    Finding,
)

_ANSI = {
    "yellow": "33", "red": "31", "blue": "34", "green": "32",
    "purple": "35", "grey": "90", "bold": "1",
}
_BADGE = {
    HARD: "hard", VERY_HARD: "very hard", PASSIVE: "passive",
    ADVERB: "adverb", COMPLEX: "complex",
}


def render(analysis: Analysis, *, color: bool = False) -> str:
    score = analysis.score
    lines = [_c(f"{analysis.path}  —  {score.reading_grade}", "bold", on=color)]

    if score.threshold is not None:
        passed = score.verdict == "pass"
        mark = "✓ passes" if passed else "✗ fails"
        lines.append(
            _c(f"  {mark} --max-grade {_fmt(score.threshold['max_grade'])}",
               "green" if passed else "red", on=color)
        )

    lines.append("")
    lines.append("  " + " · ".join([
        _c(f"{score.hard_sentences} hard", "yellow", on=color),
        _c(f"{score.very_hard_sentences} very hard", "red", on=color),
        _c(f"{score.passive} passive", "green", on=color),
        _c(f"{score.adverbs} adverbs", "blue", on=color),
        _c(f"{score.complex_phrases} complex", "purple", on=color),
    ]))
    lines.append(_c(
        f"  ARI {score.ari} · FK {score.flesch_kincaid} · Fog {score.gunning_fog}"
        f"  ({score.sentences} sentences)", "grey", on=color,
    ))

    if analysis.findings:
        lines.append("")
        for finding in analysis.findings:
            lines.append(_flagged_line(analysis.source, finding, color))

    return "\n".join(lines) + "\n"


def _flagged_line(source: str, finding: Finding, color: bool) -> str:
    line_no = source.count("\n", 0, finding.start) + 1
    badge = _c(f"{_BADGE[finding.category]:<10}", COLOR[finding.category], on=color)
    message = finding.message
    if finding.category in (HARD, VERY_HARD):
        quote = source[finding.start:finding.end].replace("\n", " ").strip()
        if len(quote) > 64:
            quote = quote[:63] + "…"
        message = f'{message}: "{quote}"'
    return f"  L{line_no:<4} {badge} {message}"


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _c(text: str, code: str, *, on: bool) -> str:
    if not on:
        return text
    return f"\033[{_ANSI[code]}m{text}\033[0m"
