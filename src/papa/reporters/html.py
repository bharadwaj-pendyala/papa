"""Self-contained HTML report — Hemingway highlights + grade sidebar (spec §7).

No network: all CSS is inline, no external fonts or scripts. The original source
is rendered in a <pre> with colored <span>s; sentence spans nest word spans.
"""

from __future__ import annotations

import html as _html

from ..models import (
    ADVERB,
    COMPLEX,
    HARD,
    PASSIVE,
    VERY_HARD,
    Analysis,
    Finding,
)

_BG = {
    HARD: "#fff3bf",
    VERY_HARD: "#ffc9c9",
    PASSIVE: "#b2f2bb",
    ADVERB: "#a5d8ff",
    COMPLEX: "#eebefa",
}
_LABEL = {
    HARD: "Hard sentence",
    VERY_HARD: "Very hard sentence",
    PASSIVE: "Passive voice",
    ADVERB: "Adverb",
    COMPLEX: "Complex phrase",
}

_CSS = """
* { box-sizing: border-box; }
body { margin: 0; font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1a1a1a; background: #f6f7f9; }
.wrap { display: flex; gap: 24px; max-width: 1100px; margin: 0 auto; padding: 32px 24px; align-items: flex-start; }
main { flex: 1 1 auto; background: #fff; border: 1px solid #e3e6ea; border-radius: 10px; padding: 28px 32px; }
main pre { white-space: pre-wrap; word-wrap: break-word; font: 16px/1.7 ui-monospace, SFMono-Regular, Menlo, monospace; margin: 0; }
aside { flex: 0 0 240px; position: sticky; top: 32px; background: #fff; border: 1px solid #e3e6ea; border-radius: 10px; padding: 20px; }
aside h1 { font-size: 18px; margin: 0 0 4px; }
aside .file { color: #6b7280; font-size: 13px; margin-bottom: 16px; word-break: break-all; }
aside .grade { font-size: 22px; font-weight: 700; margin: 0 0 8px; }
aside .verdict { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }
aside .pass { background: #d3f9d8; color: #2b8a3e; }
aside .fail { background: #ffe3e3; color: #c92a2a; }
aside .formulas { color: #495057; font-size: 14px; margin: 14px 0; }
aside ul { list-style: none; padding: 0; margin: 14px 0 0; }
aside li { display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 3px 0; }
aside .swatch { width: 14px; height: 14px; border-radius: 3px; flex: 0 0 auto; }
aside .count { margin-left: auto; font-variant-numeric: tabular-nums; font-weight: 600; }
.hl { border-radius: 3px; padding: 0 1px; }
"""


def render(analysis: Analysis, *, color: bool = False) -> str:
    body = _render_spans(analysis.source, analysis.findings)
    styles = "".join(f".hl-{cat}{{background:{bg};}}" for cat, bg in _BG.items())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>papa — {_html.escape(analysis.path)}</title>
<style>{_CSS}{styles}</style>
</head>
<body>
<div class="wrap">
<aside>{_sidebar(analysis)}</aside>
<main><pre>{body}</pre></main>
</div>
</body>
</html>
"""


def _sidebar(analysis: Analysis) -> str:
    score = analysis.score
    verdict_html = ""
    if score.threshold is not None:
        cls = "pass" if score.verdict == "pass" else "fail"
        verdict_html = (
            f'<span class="verdict {cls}">{score.verdict.upper()}'
            f' · max {score.threshold["max_grade"]}</span>'
        )
    rows = "".join(
        f'<li><span class="swatch" style="background:{_BG[cat]}"></span>'
        f'{_LABEL[cat]}<span class="count">{count}</span></li>'
        for cat, count in [
            (VERY_HARD, score.very_hard_sentences),
            (HARD, score.hard_sentences),
            (PASSIVE, score.passive),
            (ADVERB, score.adverbs),
            (COMPLEX, score.complex_phrases),
        ]
    )
    return f"""
<h1>papa</h1>
<div class="file">{_html.escape(analysis.path)}</div>
<div class="grade">{_html.escape(score.reading_grade)}</div>
{verdict_html}
<div class="formulas">ARI {score.ari} · FK {score.flesch_kincaid} · Fog {score.gunning_fog}<br>{score.sentences} sentences</div>
<ul>{rows}</ul>
"""


def _render_spans(text: str, findings: list[Finding]) -> str:
    ordered = sorted(findings, key=lambda f: (f.start, -f.end))
    out: list[str] = []

    def emit(seg_start: int, seg_end: int, items: list[Finding]) -> None:
        pos = seg_start
        i = 0
        while i < len(items):
            finding = items[i]
            out.append(_html.escape(text[pos:finding.start]))
            children = []
            j = i + 1
            while j < len(items) and items[j].end <= finding.end:
                children.append(items[j])
                j += 1
            title = _html.escape(finding.message, quote=True)
            out.append(f'<span class="hl hl-{finding.category}" title="{title}">')
            emit(finding.start, finding.end, children)
            out.append("</span>")
            pos = finding.end
            i = j
        out.append(_html.escape(text[pos:seg_end]))

    emit(0, len(text), ordered)
    return "".join(out)
