"""GitHub-flavored Markdown for job summaries and PR comments."""

from __future__ import annotations

import html
import re

from ..models import Analysis, Run
from .cli import _BADGE, PER_FILE_LIMIT, SINGLE_FILE_LIMIT, _shown_findings, _summary
from .common import LineIndex, display_grade, gate_grades, plural

# A PR comment holds at most 65,536 characters; this keeps a large docs tree under it.
DETAILED_FILES_LIMIT = 20


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True,
           show_all: bool = False) -> str:
    ranked = sorted(run.analyses, key=lambda a: (a.score.verdict != "fail", -a.score.consensus))
    lines = ["## Papa readability", "", _summary(run, color=False)[0], ""]
    if run.analyses:
        lines += _table(ranked, run.max_grade is not None or run.baseline is not None) + [""]
    for path, message in run.errors:
        lines.append(f"- :warning: `{_code(path)}`: {_text(message)}")
    for path, reason in run.skipped:
        lines.append(f"- Skipped `{_code(path)}`: {_text(reason)}")

    with_findings = [a for a in ranked if a.findings]
    detailed = with_findings if show_all else with_findings[:DETAILED_FILES_LIMIT]
    limit = None if show_all else SINGLE_FILE_LIMIT if len(run.analyses) == 1 else PER_FILE_LIMIT
    for analysis in detailed:
        lines += ["", *_details(analysis, limit, open_=len(run.analyses) == 1)]
    if len(detailed) < len(with_findings):
        hidden = len(with_findings) - len(detailed)
        lines += ["", f"{plural(hidden, 'more file')} with findings. Run papa locally to see them."]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).rstrip() + "\n"


def _table(analyses: list[Analysis], gated: bool) -> list[str]:
    head = "| File | Grade | Result | Findings |" if gated else "| File | Grade | Findings |"
    rows = [head, "|---|---|---|---|" if gated else "|---|---|---|"]
    for analysis in analyses:
        score = analysis.score
        grade = gate_grades(score)[0] if score.threshold else f"{display_grade(round(score.consensus, 1))}"
        cells = [f"`{_code(analysis.path)}`", grade]
        if gated:
            cells.append(":x: fail" if score.verdict == "fail" else ":white_check_mark: pass")
        cells.append(str(len(analysis.findings)))
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def _details(analysis: Analysis, limit: int | None, open_: bool) -> list[str]:
    shown = _shown_findings(analysis.findings, limit)
    index = LineIndex(analysis.source)
    summary = (f"<code>{html.escape(analysis.path)}</code>: {analysis.score.reading_grade} · "
               f"{plural(len(analysis.findings), 'finding')}")
    lines = [f"<details{' open' if open_ else ''}><summary>{summary}</summary>", "",
             "| Line | Kind | Text | Tip |", "|---|---|---|---|"]
    for finding in shown:
        line, col = index.line_col(finding.start)
        text = finding.excerpt if len(finding.excerpt) <= 80 else finding.excerpt[:79] + "…"
        lines.append(f"| {line}:{col} | {_BADGE[finding.category]} | {_text(text)} | {_text(finding.hint)} |")
    if len(shown) < len(analysis.findings):
        lines += ["", f"{plural(len(analysis.findings) - len(shown), 'more finding')}. Add `--all` to see every finding."]
    return lines + ["", "</details>"]


def _text(value: str) -> str:
    escaped = html.escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\`*_\[\]|#~])", r"\\\1", escaped)


def _code(value: str) -> str:
    return value.replace("`", "'").replace("|", "\\|")
