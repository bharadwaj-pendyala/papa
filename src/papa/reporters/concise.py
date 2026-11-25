"""One ``path:line:col: severity: message [category]`` line per finding, for editors and grep."""

from __future__ import annotations

from ..models import Run
from .common import LineIndex, gate_message, gate_rule

# Findings are advice; only a failed gate is an error.
_SEVERITY = {"error": "warning", "warn": "warning", "info": "note"}


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True,
           show_all: bool = False) -> str:
    lines = []
    for analysis in run.analyses:
        score = analysis.score
        if score.verdict == "fail":
            lines.append(f"{analysis.path}:1:1: error: {gate_message(score)} [{gate_rule(score)}]")
        index = LineIndex(analysis.source)
        for finding in analysis.findings:
            line, col = index.line_col(finding.start)
            lines.append(
                f"{analysis.path}:{line}:{col}: {_SEVERITY[finding.severity]}: "
                f"{finding.message} [{finding.category}]"
            )
    return "".join(line + "\n" for line in lines)
