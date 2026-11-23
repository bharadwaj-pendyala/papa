"""GitHub Actions workflow commands: findings show as annotations on the PR diff."""

from __future__ import annotations

from ..models import COMPLEX, Run
from .common import LineIndex, gate_grade

_COMMAND = {"error": "warning", "warn": "warning", "info": "notice"}


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True,
           show_all: bool = False) -> str:
    lines = []
    for analysis in run.analyses:
        score = analysis.score
        if score.verdict == "fail":
            max_grade = score.threshold["max_grade"]
            shown = gate_grade(score.consensus, max_grade, failed=True)
            lines.append(_command("error", analysis.path, (1, 1, 1, 1), "max-grade",
                                  f"Grade {shown} is above --max-grade {max_grade}. {score.reading_grade}."))
        index = LineIndex(analysis.source)
        for finding in analysis.findings:
            region = index.line_col(finding.start) + index.line_col(finding.end)
            # A complex-phrase message already names the plainer phrase.
            message = finding.message if finding.category == COMPLEX else f"{finding.message}. {finding.hint}"
            lines.append(_command(_COMMAND[finding.severity], analysis.path, region, finding.category, message))
    lines += [_command("error", path, None, "error", message) for path, message in run.errors]
    return "".join(line + "\n" for line in lines)


def _command(kind: str, path: str, region: tuple[int, int, int, int] | None, category: str, message: str) -> str:
    props = [f"file={_property(path.removeprefix('./'))}"]
    if region:
        line, col, end_line, end_col = region
        props += [f"line={line}", f"endLine={end_line}"]
        if line == end_line:
            # GitHub reads columns only on a one-line annotation, and its endColumn is inclusive.
            props += [f"col={col}", f"endColumn={max(end_col - 1, col)}"]
    props.append(f"title={_property('papa ' + category)}")
    return f"::{kind} {','.join(props)}::{_data(message)}"


def _data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _property(text: str) -> str:
    return _data(text).replace(":", "%3A").replace(",", "%2C")
