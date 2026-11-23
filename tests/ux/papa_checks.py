"""papa-specific eyes checks: the JSON contract and offset round-trips."""

from __future__ import annotations

import json
import math
from pathlib import Path

from userlens import Check

SOURCE = "src/papa/reporters/json_report.py"
SCORE_NUMBERS = {"ari", "flesch_kincaid", "gunning_fog", "consensus"}
SCORE_INTS = {"sentences", "hard_sentences", "very_hard_sentences", "adverbs", "passive", "complex_phrases"}
FINDING_INTS = {"start", "end", "line", "column", "end_line", "end_column"}
FINDING_STRS = {"category", "color", "severity", "message", "hint", "excerpt", "analyzer"}
CATEGORIES = {"hard-sentence", "very-hard-sentence", "passive", "adverb", "complex-phrase"}
SUMMARY_KEYS = {"files", "analyzed", "passed", "failed", "skipped", "errors", "max_grade"}


def checks(result, project) -> list[Check]:
    if _report(result.case) == "sarif" and result.stdout.strip():
        return [_sarif_check(result.stdout)]
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


def _report(case: dict) -> str | None:
    argv = case.get("argv", [])
    return argv[argv.index("--report") + 1] if "--report" in argv[:-1] else None


def _sarif_check(stdout: str) -> Check:
    try:
        data = json.loads(stdout)
        run = data["runs"][0]
        rules = {rule["id"] for rule in run["tool"]["driver"]["rules"]}
        problems = [] if data["version"] == "2.1.0" else ["version must be 2.1.0"]
        for result in run["results"]:
            region = result["locations"][0]["physicalLocation"]["region"]
            if result["ruleId"] not in rules:
                problems.append(f"ruleId {result['ruleId']!r} is not a declared rule")
            if result["level"] not in ("error", "warning", "note"):
                problems.append(f"bad level {result['level']!r}")
            if region["startLine"] < 1 or region["startColumn"] < 1:
                problems.append(f"region must be 1-based, got {region}")
            if (region["endLine"], region["endColumn"]) < (region["startLine"], region["startColumn"]):
                problems.append(f"region ends before it starts: {region}")
    except (ValueError, KeyError, IndexError, TypeError) as error:
        problems = [f"not a SARIF 2.1.0 log: {error!r}"]
    return Check("papa-sarif", "fail" if problems else "pass", "; ".join(problems[:5]),
                 "SARIF 2.1.0 with declared rules and 1-based regions", source="src/papa/reporters/sarif.py")
