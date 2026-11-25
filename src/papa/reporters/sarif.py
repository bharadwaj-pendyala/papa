"""SARIF 2.1.0 for GitHub code scanning and other SARIF viewers."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from .. import __version__
from ..models import ADVERB, COMPLEX, HARD, PASSIVE, VERY_HARD, Run
from .common import LineIndex, gate_message, gate_rule

GATE = "max-grade"
REGRESSION = "max-regression"

_RULES = {
    HARD: ("Hard sentence", "Split the sentence or cut words."),
    VERY_HARD: ("Very hard sentence", "Split the sentence or cut words. Aim for one idea per sentence."),
    PASSIVE: ("Passive voice", "Name who does the action and make them the subject."),
    ADVERB: ("Adverb", "Cut the adverb or use a stronger verb."),
    COMPLEX: ("Complex phrase", "Use the plainer phrase shown in the finding."),
    GATE: ("Readability gate", "Make the file easier to read, or raise --max-grade."),
    REGRESSION: ("Readability regression", "Make the file as easy to read as before, or raise --max-regression."),
}
# Findings are advice; only a failed gate is an error.
_LEVEL = {"error": "warning", "warn": "warning", "info": "note"}


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True,
           show_all: bool = False) -> str:
    results = []
    for analysis in run.analyses:
        uri = _uri(analysis.path)
        score = analysis.score
        if score.verdict == "fail":
            message = gate_message(score)
            results.append(_result(gate_rule(score), "error", f"{message[0].upper()}{message[1:]}.",
                                   uri, (1, 1, 1, 1)))
        index = LineIndex(analysis.source)
        for finding in analysis.findings:
            region = index.line_col(finding.start) + index.line_col(finding.end)
            results.append(_result(finding.category, _LEVEL[finding.severity], finding.message, uri, region))

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "papa",
                "version": __version__,
                "informationUri": "https://github.com/bharadwaj-pendyala/papa",
                "rules": [_rule(rule_id) for rule_id in _RULES],
            }},
            "columnKind": "unicodeCodePoints",
            "results": results,
            "invocations": [{
                "executionSuccessful": not run.errors,
                "toolExecutionNotifications": [
                    {"level": "error", "message": {"text": f"{path}: {message}"}} for path, message in run.errors
                ] + [
                    {"level": "note", "message": {"text": f"skipped {path}: {reason}"}} for path, reason in run.skipped
                ],
            }],
        }],
    }
    return json.dumps(sarif, indent=2, ensure_ascii=False) + "\n"


def _rule(rule_id: str) -> dict:
    name, help_text = _RULES[rule_id]
    return {
        "id": rule_id,
        "name": name.title().replace(" ", ""),
        "shortDescription": {"text": name},
        "help": {"text": help_text},
        "defaultConfiguration": {"level": "error" if rule_id in (GATE, REGRESSION) else "warning"},
    }


def _result(rule_id: str, level: str, message: str, uri: str, region: tuple[int, int, int, int]) -> dict:
    start_line, start_column, end_line, end_column = region
    return {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message},
        "locations": [{"physicalLocation": {
            "artifactLocation": {"uri": uri},
            "region": {"startLine": start_line, "startColumn": start_column,
                       "endLine": end_line, "endColumn": end_column},
        }}],
    }


def _uri(path: str) -> str:
    pure = Path(path)
    return pure.as_uri() if pure.is_absolute() else quote(pure.as_posix())
