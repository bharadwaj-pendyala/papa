<div align="center">

# 📖 Papa

### The Old Man and the CI — Hemingway-grade readability for your docs pipeline.

Papa reads your writing the way the Hemingway Editor does — flagging dense sentences, passive voice, adverbs, and complex phrasing with a readability grade — but as an open, composable **CLI / GitHub Action / library** that runs in CI and speaks JSON an LLM can act on.

[![CI](https://img.shields.io/github/actions/workflow/status/pendyala/papa/ci.yml?branch=main)](https://github.com/pendyala/papa/actions)
[![PyPI](https://img.shields.io/pypi/v/papa.svg)](https://pypi.org/project/papa/)
[![Downloads](https://img.shields.io/pypi/dm/papa.svg)](https://pypi.org/project/papa/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/pendyala/papa?style=social)](https://github.com/pendyala/papa/stargazers)

[**Quickstart**](#-quickstart) · [**GitHub Action**](#-github-action) · [**LLM loop**](#-the-llm-loop) · [**How it works**](#-how-it-works) · [**Config**](#-configuration)

<img src="docs/assets/demo.gif" alt="Papa highlighting a Markdown post: hard sentences in red, passive voice in green, adverbs in blue, with a grade panel" width="760">

</div>

---

## Why Papa?

The [Hemingway Editor](https://hemingwayapp.com) is great — and completely closed. No API, no CI, copy-paste only, and it chokes on Markdown with code blocks and SVG. The open-source pieces (`textstat`, `proselint`, `write-good`, `vale`) exist but are scattered, with mismatched output and no shared "Hemingway view."

**Papa unifies them** into one tool that:

- 📊 **Scores readability** — ARI, Flesch-Kincaid, and Gunning fog, per document and per sentence.
- 🖍️ **Highlights like Hemingway** — hard sentences, passive voice, adverbs, and complex phrases, as colored spans.
- 🧩 **Reads any format** — Markdown, MDX, txt, reStructuredText, HTML — and cleanly ignores code blocks, SVG, and frontmatter.
- 🤖 **Talks to LLMs** — emits structured JSON so an agent can read the findings and rewrite the draft, then you re-run and watch the grade drop.
- ⛔ **Gates your build** — fail CI when prose drops below your readability bar, just like a failing test.

## ⚡ Quickstart

```bash
pipx install papa        # or: npx papa  ·  brew install papa

papa post.md             # colored report in your terminal
papa post.md --report html -o report.html   # the Hemingway-style highlighted page
papa post.md --max-grade 10                  # exit 1 if harder than grade 10
```

```text
post.md  —  Grade 11 (hard to read)   ✗ fails --max-grade 10

  18 hard sentences · 4 very hard · 6 passive · 9 adverbs · 12 complex phrases

  L42  very hard (grade 16):  "Because the detour squeezes the data through a
                               narrow middle, the low rank, the model can…"
  L58  passive:               "the error is measured" → measure the error
  …
```

## 🤖 The LLM loop

Papa's JSON is designed to be fed straight to an LLM, closing the *draft → measure → revise* loop:

```bash
papa post.md --report json > findings.json
# hand findings.json + post.md to your agent using docs/llm-contract.md
# …or let Papa run the loop for you:
papa post.md --suggest --model claude-sonnet-4-6 -o post.revised.md
```

```jsonc
{
  "score": { "ari": 11.2, "reading_grade": "Grade 11 — hard to read", "verdict": "fail" },
  "findings": [
    { "start": 1423, "end": 1490, "category": "passive",
      "message": "Passive voice: 'is measured'", "severity": "warn" }
  ]
}
```

## 🐙 GitHub Action

```yaml
# .github/workflows/readability.yml
name: readability
on: pull_request
jobs:
  papa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pendyala/papa-action@v1
        with:
          files: "content/posts/**/*.md"
          max-grade: 10        # fail the PR if harder than grade 10
          report: sarif,md     # inline annotations + a summary comment
          comment: true
```

Papa annotates each flagged sentence inline on the diff (via SARIF) and posts a readability summary as a PR comment. Works the same from Jenkins, GitLab, or CircleCI via the Docker image:

```bash
docker run --rm -v "$PWD:/work" pendyala/papa post.md --max-grade 10
```

## 🔍 How it works

```
input ─▶ Ingestor ─▶ Analyzers ─▶ Aggregator ─▶ Reporters
         strip code   readability   merge spans   html · json
         + SVG, keep  passive       + scores      sarif · md
         offset map   adverbs                     terminal
                      complex-phrase
```

1. **Ingest** — detect the format, strip non-prose (code, SVG, frontmatter), keep a map back to the source so highlights land on the original.
2. **Analyze** — pluggable analyzers each emit normalized findings (`textstat` for grades; built-in passive/adverb/phrase heuristics; optional `proselint`/`alex`/`vale` plugins).
3. **Aggregate** — merge overlapping spans, resolve priority, compute document and per-section scores.
4. **Report** — render to HTML, JSON, SARIF, Markdown, or terminal, and set the exit code.

## ⚙️ Configuration

```toml
# papa.toml
max_grade = 10
reports   = ["cli", "html"]

[analyzers]
passive = true
adverbs = true
proselint = true     # optional plugin
alex = false

[ignore]
sentences_under_words = 4   # don't grade very short lines
```

## 🆚 Comparison

| | Papa | Hemingway App | write-good | vale |
|---|:---:|:---:|:---:|:---:|
| Readability grade | ✅ | ✅ | ❌ | ❌ |
| Sentence highlights | ✅ | ✅ | ⚠️ | ⚠️ |
| Markdown/MDX/SVG-aware | ✅ | ❌ | ❌ | ✅ |
| CLI / CI / Action | ✅ | ❌ | ✅ | ✅ |
| LLM-ready JSON + revise loop | ✅ | ❌ | ❌ | ❌ |
| Open source | ✅ | ❌ | ✅ | ✅ |

## 🙏 Built on the shoulders of

Papa orchestrates and credits these excellent projects: [textstat](https://github.com/textstat/textstat), [proselint](https://github.com/amperser/proselint), [write-good](https://github.com/btford/write-good), [vale](https://github.com/errata-ai/vale), and [alex](https://github.com/get-alex/alex). It does not replace them — it gives them a shared, Hemingway-style face.

## 🤝 Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md). Good first issues are [labeled](https://github.com/pendyala/papa/labels/good%20first%20issue).

## 📄 License

MIT © Bharadwaj Pendyala

