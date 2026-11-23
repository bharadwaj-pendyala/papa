"""Run papa for the GitHub Action: annotations, job summary, SARIF, and the gate's exit code."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


def papa(*args: str) -> int:
    # -I keeps a papa.py in the checked-out repo from shadowing the installed papa.
    return subprocess.run([sys.executable, "-I", "-m", "papa", *args]).returncode


def main() -> None:
    env = os.environ
    # shlex keeps quoted globs and paths with spaces whole, and never expands a glob itself.
    paths = shlex.split(env.get("INPUT_PATHS", "")) or ["."]
    common = paths + shlex.split(env.get("INPUT_ARGS", ""))
    if env.get("INPUT_MAX_GRADE", "").strip():
        common += ["--max-grade", env["INPUT_MAX_GRADE"].strip()]

    if env.get("INPUT_ANNOTATIONS") == "true":
        papa(*common, "--report", "github")
    sarif_code = 0
    if env.get("INPUT_SARIF_FILE"):
        Path(env["INPUT_SARIF_FILE"]).parent.mkdir(parents=True, exist_ok=True)
        sarif_code = papa(*common, "--report", "sarif", "-o", env["INPUT_SARIF_FILE"], "-q")

    # One file per step, so a job that runs the action twice keeps both reports.
    fd, name = tempfile.mkstemp(prefix="papa-report-", suffix=".md", dir=env.get("RUNNER_TEMP"))
    os.close(fd)
    report = Path(name)
    code = papa(*common, "--report", "markdown", "-o", str(report), "-q")
    if sarif_code == 2:
        code = 2
    if env.get("INPUT_SUMMARY") == "true" and report.is_file() and env.get("GITHUB_STEP_SUMMARY"):
        with open(env["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
            summary.write(report.read_text(encoding="utf-8"))

    with open(env["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"exit-code={code}\nreport={report}\n")


if __name__ == "__main__":
    main()
