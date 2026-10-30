"""One ``path:line:col: severity: message [category]`` line per finding, for editors and grep."""

from __future__ import annotations

from ..models import Run
from .common import line_col

_SEVERITY = {"error": "error", "warn": "warning", "info": "note"}


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True) -> str:
    lines = []
    for analysis in run.analyses:
        for finding in analysis.findings:
            line, col = line_col(analysis.source, finding.start)
            lines.append(
                f"{analysis.path}:{line}:{col}: {_SEVERITY[finding.severity]}: "
                f"{finding.message} [{finding.category}]"
            )
    return "".join(line + "\n" for line in lines)
