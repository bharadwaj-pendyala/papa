"""One ``path:line:col: severity: message [category]`` line per finding, for editors and grep."""

from __future__ import annotations

from ..models import Run
from .common import gate_grade, line_col

# Findings are advice; only a failed --max-grade gate is an error.
_SEVERITY = {"error": "warning", "warn": "warning", "info": "note"}


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True,
           show_all: bool = False) -> str:
    lines = []
    for analysis in run.analyses:
        score = analysis.score
        if score.verdict == "fail":
            max_grade = score.threshold["max_grade"]
            shown = gate_grade(score.consensus, max_grade, failed=True)
            lines.append(f"{analysis.path}:1:1: error: grade {shown} is above --max-grade {max_grade} [max-grade]")
        for finding in analysis.findings:
            line, col = line_col(analysis.source, finding.start)
            lines.append(
                f"{analysis.path}:{line}:{col}: {_SEVERITY[finding.severity]}: "
                f"{finding.message} [{finding.category}]"
            )
    return "".join(line + "\n" for line in lines)
