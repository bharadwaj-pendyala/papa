"""Colored terminal report: grade + counts + flagged lines + fix tips (spec §7)."""

from __future__ import annotations

import re

from ..models import (
    ADVERB,
    COLOR,
    COMPLEX,
    HARD,
    PASSIVE,
    VERY_HARD,
    Analysis,
    Finding,
    Run,
)
from .common import display_grade as _grade, gate_grade, line_col, plural

_ANSI = {
    "yellow": "33", "red": "31", "blue": "34", "green": "32",
    "purple": "35", "grey": "90", "bold": "1",
}
_BADGE = {
    HARD: "hard", VERY_HARD: "very hard", PASSIVE: "passive",
    ADVERB: "adverb", COMPLEX: "complex",
}
_BADGE_WIDTH = 11
_TIP_ORDER = [VERY_HARD, HARD, PASSIVE, COMPLEX, ADVERB]


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True) -> str:
    blocks = [_file_block(a, color, width, details) for a in run.analyses]
    tail = []
    if details:
        tail += _tips(run.analyses, color, width)
    if len(run.analyses) + len(run.skipped) + len(run.errors) > 1:
        tail += ([""] if tail else []) + _summary(run, color)
    if run.config:
        tail.append(_c(f"Config: {run.config}", "grey", on=color))
    return "\n".join(blocks + (["\n".join(tail) + "\n"] if tail else []))


def _file_block(analysis: Analysis, color: bool, width: int, details: bool) -> str:
    score = analysis.score
    header = f"{analysis.path}  ·  {score.reading_grade}"
    if len(header) > width:
        header = f"{analysis.path}\n{score.reading_grade}"
    lines = [_c(header, "bold", on=color)]

    if score.threshold is not None:
        max_grade = _fmt(score.threshold["max_grade"])
        failed = score.verdict == "fail"
        shown = gate_grade(score.consensus, score.threshold["max_grade"], failed)
        if failed:
            lines.append(_c(f"  FAIL  grade {shown} is above --max-grade {max_grade}", "red", on=color))
        else:
            lines.append(_c(f"  PASS  grade {shown} is within --max-grade {max_grade}", "green", on=color))

    lines.append("")
    counts = [
        (plural(score.very_hard_sentences, "very hard sentence"), "red"),
        (plural(score.hard_sentences, "hard sentence"), "yellow"),
        (f"{score.passive} passive", "green"),
        (plural(score.complex_phrases, "complex phrase"), "purple"),
        (plural(score.adverbs, "adverb"), "blue"),
    ]
    flagged = [(text, code) for text, code in counts if not text.startswith("0 ")]
    lines += _wrap_parts(flagged, width, color) if flagged else [_c("  No issues found.", "green", on=color)]
    formulas = [
        (f"mean of ARI {_grade(score.ari)}, FK {_grade(score.flesch_kincaid)}, "
         f"Fog {_grade(score.gunning_fog)}", "grey"),
        (plural(score.sentences, "sentence"), "grey"),
    ]
    lines += _wrap_parts(formulas, width, color)

    if details and analysis.findings:
        locations = [line_col(analysis.source, f.start) for f in analysis.findings]
        loc_width = max(len(f"{line}:{col}") for line, col in locations)
        lines.append("")
        for finding, (line, col) in zip(analysis.findings, locations):
            lines.append(_flagged_line(analysis.source, finding, f"{line}:{col}", loc_width, color, width))

    return "\n".join(lines) + "\n"


def _flagged_line(source: str, finding: Finding, loc: str, loc_width: int, color: bool, width: int) -> str:
    prefix_len = 2 + loc_width + 2 + _BADGE_WIDTH
    badge = _c(f"{_BADGE[finding.category]:<{_BADGE_WIDTH}}", COLOR[finding.category], on=color)
    if finding.category in (HARD, VERY_HARD):
        grade = re.search(r"grade [\d+]+", finding.message).group()
        room = max(width - prefix_len - len(grade) - 4, 12)
        quote = " ".join(source[finding.start:finding.end].split())
        if len(quote) > room:
            quote = quote[:room - 1] + "…"
        message = f'{grade}  "{quote}"'
    else:
        message = finding.message.split(": ", 1)[-1]  # the badge already names the category
    lines = _wrap_text(message, width - prefix_len, first=f"  {loc:<{loc_width}}  {badge}", rest=" " * prefix_len)
    return "\n".join(lines)


def _tips(analyses: list[Analysis], color: bool, width: int) -> list[str]:
    hints = {}
    for analysis in analyses:
        for finding in analysis.findings:
            hints.setdefault(finding.category, finding.hint)
    if not hints:
        return []
    if COMPLEX in {f.category for a in analyses for f in a.findings}:
        hints[COMPLEX] = "Use the plainer phrase shown in each finding."
    indent = 2 + _BADGE_WIDTH
    lines = [_c("Tips", "bold", on=color)]
    for category in _TIP_ORDER:
        if category in hints:
            badge = _c(f"{_BADGE[category]:<{_BADGE_WIDTH}}", COLOR[category], on=color)
            lines += _wrap_text(hints[category], width - indent, first=f"  {badge}", rest=" " * indent)
    return lines


def _summary(run: Run, color: bool) -> list[str]:
    total = len(run.analyses) + len(run.skipped) + len(run.errors)
    parts = []
    if run.skipped or run.errors:
        parts.append(f"{len(run.analyses)} analyzed")
    if run.max_grade is not None:
        failed = sum(1 for a in run.analyses if a.score.verdict == "fail")
        parts += [f"{len(run.analyses) - failed} passed", f"{failed} failed"]
    if run.skipped:
        parts.append(f"{len(run.skipped)} skipped")
    if run.errors:
        parts.append(plural(len(run.errors), "error"))
    text = f"Checked {plural(total, 'file')}" + (": " + ", ".join(parts) if parts else "")
    if run.max_grade is not None:
        text += f" (--max-grade {_fmt(run.max_grade)})"
    bad = run.errors or any(a.score.verdict == "fail" for a in run.analyses)
    lines = [_c(text + ".", "red" if bad else "bold", on=color)]
    if len(run.analyses) > 1:
        hardest = max(run.analyses, key=lambda a: a.score.consensus)
        lines.append(f"Hardest: {hardest.path} (grade {_grade(round(hardest.score.consensus, 1))}).")
    return lines


def _wrap_parts(parts: list[tuple[str, str]], width: int, color: bool) -> list[str]:
    lines, current, used = [], [], 2
    for text, code in parts:
        needed = len(text) + (3 if current else 0)
        if current and used + needed > width:
            lines.append("  " + " · ".join(current))
            current, used = [], 2
            needed = len(text)
        current.append(_c(text, code, on=color))
        used += needed
    lines.append("  " + " · ".join(current))
    return lines


def _wrap_text(text: str, width: int, *, first: str, rest: str) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > max(width, 12):
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    lines.append(current)
    return [(first if i == 0 else rest) + line for i, line in enumerate(lines)]


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _c(text: str, code: str, *, on: bool) -> str:
    if not on:
        return text
    return f"\033[{_ANSI[code]}m{text}\033[0m"
