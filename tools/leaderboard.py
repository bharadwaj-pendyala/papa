"""Rebuild site/leaderboard.json from local clones of each project.

    python tools/leaderboard.py <clones-dir>

Each project in the JSON names its repo, commit and scope. The clones dir
holds one checkout per project, named by its "project" key, at that commit.
"""

import json
import statistics
import subprocess
import sys
from datetime import date
from pathlib import Path

import papa

BOARD = Path(__file__).resolve().parent.parent / "site" / "leaderboard.json"


def grade_project(checkout: Path, scope: str) -> dict:
    out = subprocess.run([sys.executable, "-m", "papa", scope, "--report", "json", "--no-config"],
                         cwd=checkout, capture_output=True, text=True).stdout
    data = json.loads(out)
    files = data["files"]
    sentences = sum(f["score"]["sentences"] for f in files)
    grades = [f["score"]["consensus"] for f in files]
    weighted = sum(f["score"]["consensus"] * f["score"]["sentences"] for f in files) / sentences
    very_hard = sum(f["score"]["very_hard_sentences"] for f in files)
    hard = sum(f["score"]["hard_sentences"] for f in files)
    # A page under 20 sentences is too short to call the hardest page.
    worst = max(files, key=lambda f: f["score"]["consensus"] if f["score"]["sentences"] >= 20 else -1)
    return dict(
        files=len(files), sentences=sentences, grade=round(weighted, 1),
        median=round(statistics.median(grades), 1),
        over10=round(100 * sum(g > 10 for g in grades) / len(grades)),
        very_hard=round(100 * very_hard / sentences, 1), hard=round(100 * (hard + very_hard) / sentences, 1),
        passive=round(100 * sum(f["score"]["passive"] for f in files) / sentences, 1),
        adverbs=round(100 * sum(f["score"]["adverbs"] for f in files) / sentences, 1),
        worst=worst["file"], worst_grade=round(worst["score"]["consensus"], 1),
        skipped=len(data["skipped"]), errors=len(data["errors"]),
    )


def main(clones: Path) -> None:
    board = json.loads(BOARD.read_text())
    for project in board["projects"]:
        checkout = clones / project["project"]
        head = subprocess.run(["git", "-C", checkout, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head != project["commit"]:
            sys.exit(f"{checkout} is at {head or 'no commit'}, expected {project['commit']}")
        project.update(grade_project(checkout, project["scope"]))
    board["projects"].sort(key=lambda p: p["grade"])
    board.update(papa=papa.__version__, date=date.today().isoformat())
    BOARD.write_text(json.dumps(board, indent=1, ensure_ascii=False) + "\n")
    for p in board["projects"]:
        print(f"{p['name']:16}{p['grade']:>6}{p['median']:>6}{p['files']:>5}  {p['worst']} ({p['worst_grade']})")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
