"""Render the 1200x630 social preview cards in site/ with headless Chrome.

    python tools/og_cards.py

Run it after tools/leaderboard.py, so the leaderboard card shows current grades.
"""

import html
import json
import subprocess
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

HEAD = """<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,800&family=JetBrains+Mono:wght@400;600&family=Atkinson+Hyperlegible+Next:wght@400;600&display=block" rel="stylesheet">
<style>
  html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; }
  body { background: #f5f7fa; color: #141820; font-family: "Atkinson Hyperlegible Next", sans-serif; }
  .card { box-sizing: border-box; width: 1200px; height: 630px; padding: 56px 72px; display: flex; flex-direction: column; }
  .eyebrow { font: 600 20px/1 "JetBrains Mono", monospace; letter-spacing: 0.08em; text-transform: uppercase; color: #4a5261; }
  h1 { font: 800 60px/1.04 "Bricolage Grotesque", sans-serif; letter-spacing: -0.025em; margin: 18px 0 0; }
  .foot { margin-top: auto; display: flex; justify-content: space-between; font: 600 22px/1 "JetBrains Mono", monospace; color: #4a5261; }
  .foot b { color: #141820; }
  .rows { margin-top: 28px; border-top: 2px solid #141820; }
  .row { display: grid; grid-template-columns: 44px 250px 1fr 90px; align-items: center; gap: 20px; height: 52px; border-bottom: 1px solid #dfe3ea; }
  .rank { font: 600 20px "JetBrains Mono", monospace; color: #4a5261; }
  .name { font: 800 28px "Bricolage Grotesque", sans-serif; }
  .track { position: relative; height: 18px; }
  .bar { position: absolute; inset: 0 auto 0 0; border-radius: 3px; }
  .ten { position: absolute; top: -10px; bottom: -10px; width: 2px; background: #141820; }
  .grade { font: 800 34px "Bricolage Grotesque", sans-serif; text-align: right; }
  .gap { height: 22px; font: 600 20px/22px "JetBrains Mono", monospace; color: #4a5261; padding-left: 64px; border-bottom: 1px solid #dfe3ea; }
  .draft { margin-top: 40px; background: #fff; border: 1px solid #dfe3ea; border-radius: 14px; padding: 30px 36px; font: 400 34px/1.55 "JetBrains Mono", monospace; }
  .draft mark { border-radius: 4px; padding: 0 3px; color: inherit; }
  .chips { display: flex; gap: 14px; margin-top: 26px; font: 600 22px "JetBrains Mono", monospace; }
  .chips span { border-radius: 999px; padding: 8px 16px; }
  .mark { font: 800 44px/1 "Bricolage Grotesque", sans-serif; letter-spacing: -0.02em; }
</style>"""


def bar_color(grade: float) -> str:
    return "#b9ecc2" if grade < 10 else "#fff0a8" if grade < 11 else "#ffc4c4"


def row(rank: int, project: dict, scale: float) -> str:
    grade = project["grade"]
    return (
        f'<div class="row"><span class="rank">{rank}</span><span class="name">{html.escape(project["name"])}</span>'
        f'<span class="track"><span class="bar" style="width:{grade / scale:.1%};background:{bar_color(grade)}"></span>'
        f'<span class="ten" style="left:{10 / scale:.1%}"></span></span><span class="grade">{grade}</span></div>'
    )


def leaderboard_card() -> str:
    board = json.loads((SITE / "leaderboard.json").read_text())
    projects = board["projects"]
    scale = max(p["grade"] for p in projects) * 1.08
    top = "".join(row(i + 1, p, scale) for i, p in enumerate(projects[:3]))
    bottom = "".join(row(len(projects) - 1 + i, p, scale) for i, p in enumerate(projects[-2:]))
    return f"""{HEAD}<div class="card">
<div class="eyebrow">Docs readability leaderboard</div>
<h1>Which open-source docs are easiest to read?</h1>
<div class="rows">{top}<div class="gap">· · ·</div>{bottom}</div>
<div class="foot"><span><b>papa.bharad.dev</b>/leaderboard</span><span>{len(projects)} projects · US school grade · lower is easier</span></div>
</div>"""


def home_card() -> str:
    return f"""{HEAD}<div class="card">
<div class="mark">papa</div>
<h1>Hemingway-style readability checks for your docs.</h1>
<div class="draft">The new build <mark style="background:#b9ecc2">was shipped</mark> by the team
<mark style="background:#e9c6fb">in order to</mark> fix the bug. It <mark style="background:#b6dbff">really</mark> works.</div>
<div class="chips"><span style="background:#b9ecc2">passive</span><span style="background:#e9c6fb">complex</span><span style="background:#b6dbff">adverb</span><span style="background:#ffc4c4">very hard</span></div>
<div class="foot"><span><b>papa.bharad.dev</b></span><span>terminal · CI · every pull request</span></div>
</div>"""


def render(page: str, out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "card.html"
        source.write_text(page)
        subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--window-size=1200,630", "--virtual-time-budget=5000",
                        f"--screenshot={out}", source.as_uri()],
                       check=True, capture_output=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    render(leaderboard_card(), SITE / "og-leaderboard.png")
    render(home_card(), SITE / "og-home.png")
