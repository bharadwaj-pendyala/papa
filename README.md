<div align="center">

# 📖 Papa

### Hemingway-style readability linting for Markdown and text.

Papa flags hard sentences, passive voice, adverbs, and complex phrasing with a
readability grade. It is an open-source **alpha** CLI and Python library that
can run locally or in CI, emit JSON for automation, and generate a self-contained
HTML report.

[![CI](https://img.shields.io/github/actions/workflow/status/bharadwaj-pendyala/papa/ci.yml?branch=main)](https://github.com/bharadwaj-pendyala/papa/actions)
[![PyPI](https://img.shields.io/pypi/v/papa-lint?label=pypi)](https://pypi.org/project/papa-lint/)
[![Downloads](https://img.shields.io/pypi/dm/papa-lint.svg)](https://pypi.org/project/papa-lint/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/bharadwaj-pendyala/papa?style=social)](https://github.com/bharadwaj-pendyala/papa/stargazers)

[**Quickstart**](#-quickstart) · [**CI usage**](#-ci-usage) · [**Agents**](#-agents) · [**How it works**](#-how-it-works) · [**Roadmap**](#-roadmap)

**[Try it in your browser](https://bharadwaj-pendyala.github.io/papa/#try)**
with no install. Or see a [sample HTML report](https://bharadwaj-pendyala.github.io/papa/report.html)
and the [docs readability leaderboard](https://bharadwaj-pendyala.github.io/papa/leaderboard.html)
for 14 open-source projects.

</div>

---

## Status

Papa is currently **alpha software**. The supported surface is intentionally
small:

- CLI command: `papa`
- Python package: `papa-lint`
- Input: Markdown, MDX, and plain text files, folders, quoted globs, and stdin
- Reports: terminal, concise (`file:line:col`), JSON, self-contained HTML,
  SARIF, GitHub annotations, and Markdown
- GitHub Action and pre-commit hook
- Config: `papa.toml` or `[tool.papa]` in `pyproject.toml`
- CI gating: use `--max-grade` and the process exit code

Optional external linters and built-in LLM rewriting are roadmap items.

## Why Papa?

The [Hemingway Editor](https://hemingwayapp.com) is useful, but it is closed,
manual, and not designed for docs pipelines. Other open-source writing tools
exist, but they tend to have separate output formats and workflows.

Papa focuses on a narrow first job: make prose readability checks scriptable.

- **Scores readability** with ARI, Flesch-Kincaid, and Gunning fog.
- **Highlights like Hemingway** by marking hard sentences, passive voice,
  adverbs, and complex phrases.
- **Handles Markdown and MDX** by ignoring frontmatter, code, tags, link URLs,
  and badges while preserving offsets back to the original file.
- **Emits JSON** so agents, scripts, or dashboards can consume the findings.
- **Gates CI** by exiting non-zero when prose is harder than your max grade.

## ⚡ Quickstart

```bash
pipx install papa-lint

papa post.md                          # check one file
papa docs/ --max-grade 10             # check a folder, fail above grade 10
cat post.md | papa                    # read stdin
papa post.md --report concise         # file:line:col lines for editors
papa post.md --report html -o report.html
papa --help                           # all flags, examples, exit codes
```

Example terminal output:

```text
all-findings.md  ·  Grade 15, very hard to read

  1 very hard sentence · 2 passive · 2 complex phrases · 3 adverbs
  mean of ARI 14.4, FK 13.4, Fog 16.7 · 6 sentences

  7:15    passive    'was shipped'
  7:39    complex    'in order to', consider 'to'
  8:4     adverb     'basically'
  15:1    very hard  grade 18+ "Due to the fact that the multifaceted impleme…"
  15:279  passive    'was postponed'

Tips
  very hard  Split the sentence or cut words. Aim for one idea per sentence.
  passive    Name who does the action and make them the subject.
  complex    Use the plainer phrase shown in each finding.
  adverb     Cut the adverb or use a stronger verb.
```

Each finding starts with `line:column`. The grade is the mean of three
readability formulas, shown as a US school grade.

Papa grades prose only. It ignores code, HTML and JSX tags, MDX imports, link
URLs, images, badges, and emphasis marks. Each list item, heading, and table
cell counts as its own unit, and short headings or labels are not graded.

Long output is capped. One file shows its 25 most severe findings. A run over
more than 10 files shows one line per file. Add `--all` to see every finding.
JSON and concise output always include every finding.

## ⚙️ Config

Put shared settings in `papa.toml` at the root of your repo:

```toml
[papa]
max-grade = 10
exclude = ["docs/generated/**", "CHANGELOG.md"]
```

You can also use `[tool.papa]` in `pyproject.toml`. Papa looks for the config
in the current folder and its parents, and stops at the repo root. Exclude
globs are relative to the config file. Command-line flags override the config.
Use `--config FILE` to pick a file, or `--no-config` to ignore it. The terminal
report names the config file that it used.

## 🚦 Exit codes

| Code | Meaning |
|---|---|
| `0` | No file failed `--max-grade`. Findings alone never fail a run. |
| `1` | At least one file is harder than `--max-grade`. |
| `2` | Usage, config, or input error, or no input had prose to check. |

Papa skips files that have no prose, such as a file with only code blocks. It
writes a note on stderr for each skipped file.

## 🧪 CI usage

### GitHub Action

Add one step to a workflow. Papa annotates hard sentences on the PR diff,
writes a report to the job summary, and fails the job above your max grade.

```yaml
name: readability
on: pull_request
permissions:
  contents: read
  pull-requests: write   # only for comment: true
jobs:
  papa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bharadwaj-pendyala/papa@v0
        with:
          paths: README.md docs/
          max-grade: 10
          comment: true
```

| Input | Default | What it does |
|---|---|---|
| `paths` | `.` | Files, folders, or quoted globs, separated by spaces or new lines. |
| `max-grade` | from `papa.toml` | Fail when a file's grade is above this number. |
| `args` | | Extra flags, such as `--exclude 'docs/generated/**'`. |
| `annotations` | `true` | Show findings on the PR diff. |
| `summary` | `true` | Write the Markdown report to the job summary. |
| `comment` | `false` | Post the report on the PR and update it on each push. |
| `sarif-file` | | Also write SARIF for GitHub code scanning. |
| `python-version` | `3.12` | Python that runs papa. |

The action sets two outputs: `exit-code` and `report`, the path to the
Markdown report. GitHub shows at most 10 warning annotations per step, so
the job summary is the full list.

To see findings in the **Security** tab, write SARIF and upload it. The
upload needs these permissions:

```yaml
permissions:
  contents: read
  actions: read
  security-events: write
steps:
  - uses: actions/checkout@v4
  - uses: bharadwaj-pendyala/papa@v0
    with:
      sarif-file: papa.sarif
  - uses: github/codeql-action/upload-sarif@v3
    if: always()
    with:
      sarif_file: papa.sarif
```

### pre-commit

```yaml
repos:
  - repo: https://github.com/bharadwaj-pendyala/papa
    rev: v0.2.3
    hooks:
      - id: papa
        args: [--report, concise, --allow-empty, --max-grade, "10"]
```

Without `--max-grade` here or in `papa.toml`, the hook prints findings and
never blocks a commit. The hook passes `--allow-empty`, so a commit with only
excluded or code-only files still goes through. Keep it when you set `args`.

### Any other CI

Install papa and let `--max-grade` set the exit code:

```bash
pipx run --spec papa-lint papa README.md docs/ --max-grade 10 --report concise
```

| Report | Use it for |
|---|---|
| `cli` | People in a terminal. |
| `concise` | Editors and grep: one `file:line:col: severity: message` line per finding. |
| `json` | Scripts and LLM agents. See [docs/llm-contract.md](docs/llm-contract.md). |
| `html` | A self-contained page with highlights. |
| `sarif` | GitHub code scanning and other SARIF viewers. |
| `github` | Annotations from any GitHub Actions step. |
| `markdown` | A job summary or PR comment. |

In every report, findings are advice. Only a failed `--max-grade` gate is an
error.

## 🤖 Agents

Papa gives coding agents a measurable target: grade the draft, fix what papa
flags, and grade it again until the file passes.

**Claude Code plugin.** It adds a `readability` skill and the papa MCP server:

```text
/plugin marketplace add bharadwaj-pendyala/papa
/plugin install papa@papa
```

On Claude Code 2.1.275 or later, one command does both:
`/plugin install papa --marketplace bharadwaj-pendyala/papa`.

**MCP server.** Any MCP client can run it. It needs `uv`:

```bash
claude mcp add papa -- uvx --from "papa-lint[mcp]" papa-mcp
```

```json
{ "mcpServers": { "papa": { "command": "uvx", "args": ["--from", "papa-lint[mcp]", "papa-mcp"] } } }
```

The server has two read-only tools. `grade_text` grades a draft that you pass
in. `grade_files` grades files, folders, or globs and reads `papa.toml`. Both
return the JSON report below.

**JSON.** Agents without MCP can read the same report from the CLI:

```bash
papa post.md --report json > findings.json
```

The JSON lists each file with its score and findings. Each finding has source
offsets, a line and column, and a hint:

```jsonc
{
  "version": "0.2",
  "files": [
    {
      "file": "post.md",
      "score": { "consensus": 11.4, "reading_grade": "Grade 11, hard to read", "verdict": "fail" },
      "findings": [
        {
          "start": 1423, "end": 1434, "line": 42, "column": 7,
          "category": "passive",
          "message": "Passive voice: 'is measured'",
          "hint": "Name who does the action and make them the subject."
        }
      ]
    }
  ],
  "skipped": [],
  "errors": [],
  "summary": { "files": 1, "analyzed": 1, "passed": 0, "failed": 1 }
}
```

The example above shows only some of the fields.
See [docs/llm-contract.md](docs/llm-contract.md) for a prompt pattern that uses
Papa findings to guide a rewrite.

## 🔍 How it works

```text
input -> Ingestor -> Analyzers -> Aggregator -> Reporters
         strip code  readability  merge spans  terminal
         + SVG       passive      + scores     json
         offset map  adverbs                  html
                     complex phrase
```

1. **Ingest**: detect Markdown or text, strip non-prose, and preserve an offset
   map back to the original source.
2. **Analyze**: run built-in analyzers for readability, passive voice, adverbs,
   and complex phrases.
3. **Aggregate**: merge overlapping findings, compute document scores, and apply
   the optional max-grade gate.
4. **Report**: render terminal, concise, JSON, or HTML output and set the exit
   code.

## Python API

```python
from papa import analyze

result = analyze(open("post.md", encoding="utf-8").read(), path="post.md", max_grade=10)
print(result.score.reading_grade)
print(result.score.verdict)
```

## 🗺️ Roadmap

- Built-in `--suggest` workflow for LLM-assisted rewrites
- MDX, HTML, and reStructuredText ingestion
- Optional integrations with tools such as `proselint`, `alex`, and `vale`
- npm, Homebrew, and Docker distribution

## 🆚 Comparison

| | Papa alpha | Hemingway App | write-good | vale |
|---|:---:|:---:|:---:|:---:|
| Readability grade | ✅ | ✅ | ❌ | ❌ |
| Sentence highlights | ✅ | ✅ | ⚠️ | ⚠️ |
| Markdown code-block awareness | ✅ | ❌ | ❌ | ✅ |
| CLI | ✅ | ❌ | ✅ | ✅ |
| CI gate via exit code | ✅ | ❌ | ✅ | ✅ |
| JSON for automation | ✅ | ❌ | ⚠️ | ✅ |
| Open source | ✅ | ❌ | ✅ | ✅ |

## 🙏 Built on the shoulders of

Papa currently uses [textstat](https://github.com/textstat/textstat) for
readability formulas and includes small built-in heuristics for the Hemingway
style findings. Future optional integrations may include
[proselint](https://github.com/amperser/proselint),
[write-good](https://github.com/btford/write-good),
[vale](https://github.com/errata-ai/vale), and
[alex](https://github.com/get-alex/alex).

## 🤝 Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md). Good first issues are
[labeled](https://github.com/bharadwaj-pendyala/papa/labels/good%20first%20issue).

## 📄 License

MIT © Bharadwaj Pendyala
