"""papa-specific eyes checks: the JSON contract and offset round-trips."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from eyes import Check  # noqa: E402

SOURCE = "src/papa/reporters/json_report.py"
SCORE_NUMBERS = {"ari", "flesch_kincaid", "gunning_fog", "consensus"}
SCORE_INTS = {"sentences", "hard_sentences", "very_hard_sentences", "adverbs", "passive", "complex_phrases"}
FINDING_INTS = {"start", "end", "line", "column", "end_line", "end_column"}
FINDING_STRS = {"category", "color", "severity", "message", "hint", "analyzer"}
CATEGORIES = {"hard-sentence", "very-hard-sentence", "passive", "adverb", "complex-phrase"}
SUMMARY_KEYS = {"files", "analyzed", "passed", "failed", "skipped", "errors", "max_grade"}


def checks(result, project) -> list[Check]:
    if not result.case.get("json"):
        return []
    try:
        data = json.loads(result.stdout)
    except ValueError:
        return []
    problems = _contract_problems(data)
    if not problems:
        problems = _offset_problems(data, result.cwd, result.case)
    return [Check("papa-json-contract", "fail" if problems else "pass",
                  "; ".join(problems[:5]), "JSON schema 0.2 (docs/llm-contract.md)", source=SOURCE)]


def _contract_problems(data) -> list[str]:
    if not isinstance(data, dict):
        return [f"top level must be an object, got {type(data).__name__}"]
    problems = []
    if data.get("version") != "0.2":
        problems.append(f"version must be '0.2', got {data.get('version')!r}")
    for key in ("files", "skipped", "errors"):
        if not isinstance(data.get(key), list):
            problems.append(f"'{key}' must be a list")
    summary = data.get("summary")
    if not isinstance(summary, dict) or set(summary) != SUMMARY_KEYS:
        problems.append(f"'summary' keys must be {sorted(SUMMARY_KEYS)}")
    for entry in data.get("files") or []:
        problems += _file_problems(entry)
    return problems


def _file_problems(entry: dict) -> list[str]:
    name = entry.get("file", "?")
    score = entry.get("score", {})
    problems = []
    for key in SCORE_NUMBERS:
        value = score.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            problems.append(f"{name}: score.{key} must be a finite number")
    for key in SCORE_INTS:
        if not isinstance(score.get(key), int):
            problems.append(f"{name}: score.{key} must be an integer")
    if score.get("verdict") not in ("pass", "fail"):
        problems.append(f"{name}: score.verdict must be 'pass' or 'fail'")
    for finding in entry.get("findings", []):
        missing = (FINDING_INTS | FINDING_STRS) - set(finding)
        if missing:
            problems.append(f"{name}: finding missing {sorted(missing)}")
            break
        if finding["category"] not in CATEGORIES:
            problems.append(f"{name}: unknown category {finding['category']!r}")
    return problems


def _offset_problems(data: dict, cwd: Path, case: dict) -> list[str]:
    problems = []
    for entry in data["files"]:
        path = cwd / entry["file"]
        if not path.is_file():
            continue
        source = path.read_bytes().decode("utf-8")
        for finding in entry["findings"]:
            start, end = finding["start"], finding["end"]
            if not 0 <= start < end <= len(source):
                problems.append(f"{entry['file']}: span {start}-{end} is outside the source")
                continue
            if (finding["line"], finding["column"]) != _line_col(source, start):
                problems.append(f"{entry['file']}: line/column {finding['line']}:{finding['column']} "
                                f"does not match offset {start} ({_line_col(source, start)})")
            if (finding["end_line"], finding["end_column"]) != _line_col(source, end):
                problems.append(f"{entry['file']}: end line/column does not match offset {end}")
    return problems


def _line_col(source: str, offset: int) -> tuple[int, int]:
    line = source.count("\n", 0, offset) + 1
    return line, offset - (source.rfind("\n", 0, offset) + 1) + 1
