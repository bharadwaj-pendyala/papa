"""Self-contained HTML report: Hemingway highlights + grade sidebar (spec §7).

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
    Run,
)
from .common import display_grade, line_col, plural

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
nav.index { max-width: 1100px; margin: 0 auto; padding: 24px 24px 0; }
nav.index h1 { font-size: 20px; margin: 0 0 8px; }
nav.index ol { margin: 0; padding-left: 20px; }
nav.index a { color: #1c5fb8; }
nav.index .fail { color: #c92a2a; font-weight: 600; }
.notice { max-width: 1100px; margin: 24px auto 0; padding: 12px 24px; background: #fff4e6; border: 1px solid #ffd8a8; border-radius: 10px; color: #7a3e00; }
.notice h2 { font-size: 16px; margin: 0 0 6px; }
.notice ul { margin: 0; padding-left: 20px; }
.findings { list-style: none; padding: 0; margin: 24px 0 0; border-top: 1px solid #e3e6ea; }
.findings li { padding: 10px 0; border-bottom: 1px solid #f1f3f5; font-size: 14px; }
.findings .loc { font: 13px ui-monospace, SFMono-Regular, Menlo, monospace; color: #495057; margin-right: 8px; }
.findings .tag { display: inline-block; padding: 0 6px; border-radius: 4px; font-size: 12px; font-weight: 600; color: #1a1a1a; margin-right: 6px; }
.findings .hint { display: block; color: #495057; margin-top: 2px; }
@media (max-width: 760px) {
  .wrap { flex-direction: column; padding: 16px; align-items: stretch; }
  aside { position: static; flex: none; }
  main { padding: 16px; }
  main pre { font-size: 14px; }
}
"""


def render(run: Run, *, color: bool = False, width: int = 80, details: bool = True) -> str:
    styles = "".join(f".hl-{cat}{{background:{bg};}}" for cat, bg in _BG.items())
    sections = "\n".join(
        f'<section class="wrap" id="file-{i}">\n<aside>{_sidebar(a)}</aside>\n'
        f"<main><pre>{_render_spans(a.source, a.findings)}</pre>{_findings_list(a)}</main>\n</section>"
        for i, a in enumerate(run.analyses, 1)
    )
    title = run.analyses[0].path if len(run.analyses) == 1 else plural(len(run.analyses), "file")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>papa · {_html.escape(title)}</title>
<style>{_CSS}{styles}</style>
</head>
<body>
{_notice(run)}
{_index(run.analyses)}
{sections}
</body>
</html>
"""


def _notice(run: Run) -> str:
    problems = [f"Could not read {_html.escape(p)}: {_html.escape(m)}" for p, m in run.errors]
    problems += [f"Skipped {_html.escape(p)}: {_html.escape(r)}" for p, r in run.skipped]
    if not problems:
        return ""
    items = "".join(f"<li>{p}</li>" for p in problems)
    return f'<div class="notice" role="alert"><h2>This report is incomplete</h2><ul>{items}</ul></div>'


def _findings_list(analysis: Analysis) -> str:
    if not analysis.findings:
        return ""
    items = []
    for finding in analysis.findings:
        line, col = line_col(analysis.source, finding.start)
        items.append(
            f'<li><span class="loc">{line}:{col}</span>'
            f'<span class="tag" style="background:{_BG[finding.category]}">{_LABEL[finding.category]}</span>'
            f"{_html.escape(finding.message)}"
            f'<span class="hint">{_html.escape(finding.hint)}</span></li>'
        )
    return f'<ol class="findings">{"".join(items)}</ol>'


def _index(analyses: list[Analysis]) -> str:
    if len(analyses) < 2:
        return ""
    items = "".join(
        f'<li><a href="#file-{i}">{_html.escape(a.path)}</a> · {_html.escape(a.score.reading_grade)}'
        + (' · <span class="fail">FAIL</span>' if a.score.verdict == "fail" else "")
        + "</li>"
        for i, a in enumerate(analyses, 1)
    )
    return f'<nav class="index"><h1>papa · {plural(len(analyses), "file")}</h1><ol>{items}</ol></nav>'


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
<div class="formulas">ARI {display_grade(score.ari)} · FK {display_grade(score.flesch_kincaid)} · Fog {display_grade(score.gunning_fog)}<br>{plural(score.sentences, 'sentence')}</div>
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
