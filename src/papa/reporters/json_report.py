"""JSON report: the LLM contract (spec §6, §8). Stable, versioned shape."""

from __future__ import annotations

import json

from ..models import Analysis, Run
from .common import line_col

SCHEMA_VERSION = "0.2"


def payload(run: Run) -> dict:
    failed = sum(1 for a in run.analyses if a.score.verdict == "fail")
    return {
        "version": SCHEMA_VERSION,
        "files": [file_payload(a) for a in run.analyses],
        "skipped": [{"file": path, "reason": reason} for path, reason in run.skipped],
        "errors": [{"file": path, "message": message} for path, message in run.errors],
        "summary": {
            "files": len(run.analyses) + len(run.skipped) + len(run.errors),
            "analyzed": len(run.analyses),
            "passed": len(run.analyses) - failed,
            "failed": failed,
            "skipped": len(run.skipped),
            "errors": len(run.errors),
            "max_grade": run.max_grade,
        },
    }


def file_payload(analysis: Analysis) -> dict:
    return {
        "file": analysis.path,
        "score": analysis.score.to_dict(),
        "findings": [_finding(analysis.source, f) for f in analysis.findings],
    }


def _finding(source: str, finding) -> dict:
    line, column = line_col(source, finding.start)
    end_line, end_column = line_col(source, finding.end)
    return {
        "start": finding.start,
        "end": finding.end,
        "line": line,
        "column": column,
        "end_line": end_line,
        "end_column": end_column,
        **{k: v for k, v in finding.to_dict().items() if k not in ("start", "end")},
    }


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True,
           show_all: bool = False) -> str:
    return json.dumps(payload(run), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
