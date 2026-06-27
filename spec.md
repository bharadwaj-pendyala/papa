# Papa — Product & Technical Spec

> **Working name:** `papa` · **Tagline:** *The Old Man and the CI — Hemingway-grade readability for your docs pipeline.*
> Status: Draft v0.1 · Owner: Bharadwaj Pendyala

---

## 1. The one-sentence pitch

**Papa reads your writing the way the Hemingway Editor does — flagging dense sentences, passive voice, adverbs, and complex phrasing, plus a readability grade — but as a composable CLI / GitHub Action / library that runs in CI and emits machine-readable output an LLM can act on to rewrite the text.**

Hemingway is a closed desktop/web app. Papa is the open, automatable version: the same *experience*, wired into the place writing actually ships from (a repo, a pipeline, an editor).

---

## 2. Problem

1. The Hemingway Editor is beloved but **closed**: no API, no CI integration, no automation, copy-paste only. It also chokes on Markdown/MDX with code blocks and inline SVG.
2. The good open-source pieces already exist (`textstat`, `proselint`, `write-good`, `vale`, `alex`) but they are **fragmented** — different output shapes, no unified "Hemingway view," no shared grade panel, no LLM-ready contract.
3. Teams that publish docs/blogs/READMEs have **no readability gate** the way they have lint/test gates for code.
4. The emerging workflow — *LLM writes draft → human reviews → LLM revises* — has **no structured readability feedback** to close the loop. Papa is the missing measurement layer.

## 2.5 Prior art & where Papa wins (web research, 2026-06)

Researched the live landscape before locking scope. What's out there and the gap each leaves:

| Tool | What it does | What it lacks (Papa's wedge) |
|------|--------------|------------------------------|
| **Hemingway Editor** | The highlight UX everyone wants, plus a grade panel | Closed, $20, no API/CLI/CI, chokes on Markdown with code/SVG, "leaves you to fix the mess yourself" |
| **textlens** (npm) | Readability in CI: 7 formulas into a consensus grade, PR comments | No per-sentence highlights, no passive/adverb, no LLM rewrite. Scoring only |
| **Vale** | Fast, offline, markup-aware prose *rules* engine | No built-in Hemingway view (readability is custom-script only), no LLM revise loop. Composes with Papa |
| **proselint / write-good / alex** | Individual heuristics (weasel words, passive, inclusive language) | Fragmented, mismatched output, no shared grade panel, no LLM contract |

**Differentiation thesis (sharpened).** Papa does not compete on raw formula count (textlens already does seven). Papa owns three things nobody bundles:

1. the **Hemingway highlight view** (hard, very-hard, passive, adverb, complex spans) as an open artifact,
2. the **LLM revise loop** (structured JSON a model optimizes against), and
3. a **readability-regression gate**, the single most-cited unmet need: *"typos get flagged in CI, but PRs that make docs harder to read aren't."*

Papa composes with Vale and textstat rather than replacing them.

**Two correctness pitfalls the research flagged (now designed around):**

- **Single-formula scores are gameable and noisy.** Flesch-Kincaid rewards short monosyllabic sentences regardless of quality and is surface-only. Papa reports a **consensus grade** across multiple formulas (ARI, FK, Gunning fog, Coleman-Liau, SMOG) and warns on suspiciously low-variance "gamed" text, rather than trusting one number.
- **Raw numbers, dates, names, and URLs mis-score.** Textstat's own docs warn FK is wrong unless dates and names are normalized first. Papa runs a **pre-score normalization pass** (numbers, dates, URLs, identifiers become neutral one-syllable tokens) so the grade reflects the prose, not the data.

## 3. Who it's for

- Engineers who write blogs/docs and want a quality bar without leaving the repo.
- Docs/DevRel teams that want a readability gate in CI alongside spell-check.
- **LLM agents** that draft and iteratively improve prose and need numeric, structured feedback to optimize against.

---

## 4. Goals & non-goals

**Goals**
- One tool that produces the **Hemingway highlight experience** (colored spans + grade panel) from any prose file.
- Format-agnostic input (Markdown, MDX, txt, reStructuredText, HTML, AsciiDoc) with clean stripping of code/SVG/frontmatter.
- Multiple output surfaces from one analysis: **HTML report, JSON, SARIF, Markdown summary, terminal**.
- First-class **CI** story: GitHub Action, pre-commit hook, Docker, plus a generic CLI usable from Jenkins/GitLab/CircleCI.
- An **LLM-ready JSON contract** + an optional `--suggest` mode that asks an LLM to rewrite flagged spans.
- Configurable thresholds that can **fail the build** (`exit 1`) when readability drops below a bar.

**Non-goals (v1)**
- Grammar/spell checking (defer to LanguageTool/codespell; Papa can compose with them, not replace them).
- A hosted SaaS or web UI we operate (the HTML report is a static artifact, not a service).
- Reimplementing every linter — Papa **orchestrates and normalizes**, it doesn't rewrite the ecosystem.

---

## 5. The "Hemingway experience," reproduced

Papa maps each highlight category to an existing analyzer, normalizes findings into a common span model, merges them, and renders.

| Hemingway highlight        | Color  | Papa source signal                                  |
|----------------------------|--------|-----------------------------------------------------|
| Hard sentence (grade ≥10)  | yellow | `textstat` per-sentence grade (ARI / Flesch-Kincaid)|
| Very hard sentence (≥14)   | red    | `textstat` per-sentence grade                       |
| Adverb                     | blue   | `-ly` heuristic w/ exception list (write-good style)|
| Passive voice              | green  | be-verb + past-participle heuristic                 |
| Complex / weasel phrase    | purple | `proselint` + curated phrase list                   |
| Readability grade panel    | —      | `textstat` document-level (ARI, FK, Gunning fog)    |
| Inclusive-language (opt-in)| teal   | `alex`                                              |

Design choice: the few write-good heuristics (passive, adverbs) are **reimplemented in-language** (~40 lines) so the core has minimal cross-runtime deps; heavier analyzers (`proselint`, `alex`, `vale`) are **optional plugins** invoked only if installed/enabled.

---

## 6. Architecture

```
                 ┌─────────────┐
  input file ───▶│  Ingestor   │  detect format, strip code/SVG/frontmatter,
  (.md/.mdx/...) │  + OffsetMap │  keep a map back to original byte offsets
                 └──────┬──────┘
                        │ clean text + offset map
                        ▼
                 ┌─────────────┐   pluggable, each returns
                 │  Analyzers  │   List[Finding{start,end,category,color,msg,severity}]
                 │  (registry) │   • readability (textstat)
                 └──────┬──────┘   • passive • adverbs • complex-phrase
                        │          • proselint* • alex* • vale*  (*optional)
                        ▼
                 ┌─────────────┐   merge overlapping spans, resolve priority,
                 │ Aggregator  │   compute document scores + per-section rollups
                 └──────┬──────┘
                        │ Document model (scores + merged findings, re-mapped to original offsets)
            ┌───────────┼───────────┬───────────┬────────────┐
            ▼           ▼           ▼           ▼            ▼
        HTML report   JSON      SARIF      Markdown      Terminal
        (Hemingway    (LLM      (GitHub    (PR comment   (colored,
         highlights)  contract)  Code Scan) summary)      TTY)
```

**Core model**

```jsonc
// Finding (normalized, every analyzer emits this)
{ "start": 1423, "end": 1490, "category": "passive",
  "color": "green", "severity": "warn",
  "message": "Passive voice: 'was measured'", "analyzer": "passive" }

// Document score (the grade panel)
{ "ari": 11.2, "flesch_kincaid": 10.8, "gunning_fog": 12.1,
  "reading_grade": "Grade 11 — hard to read",
  "sentences": 142, "hard_sentences": 18, "very_hard_sentences": 4,
  "adverbs": 9, "passive": 6, "complex_phrases": 12,
  "verdict": "fail", "threshold": { "max_grade": 10 } }
```

**Stack:** Python 3.11+ core (so `textstat`/`proselint` are native), shipped as a `pipx`-installable CLI and a Docker image. A thin `npx` wrapper calls the Docker/pip binary so JS users get `npx papa` too.

---

## 7. Inputs & outputs

**Input:** any path or glob; stdin; a directory. Format detected by extension, overridable with `--format`. Ingestor preserves original offsets so highlights land on the *source*, not the stripped text.

**Outputs (any combination via `--report`):**
- `html` — self-contained, no-network, Hemingway-style highlighted document + grade sidebar. The showcase artifact.
- `json` — the LLM contract (see §8). Stable, versioned schema.
- `sarif` — GitHub code-scanning annotations inline on the PR diff.
- `md` — a compact summary for posting as a PR comment.
- `cli` — colored terminal output for local use.
- Exit code: `0` pass / `1` threshold violation, for CI gating.

**Two gate modes (research-driven):**
- **Absolute gate** (`--max-grade N`): fail if the document is harder than grade `N`. The baseline behavior.
- **Regression gate** (`--baseline <git-ref>`): compare each file against its version at `<git-ref>` (default the PR base) and fail if the consensus grade got **worse** by more than `--max-regression` (default 1.0), even when still under the absolute bar. This closes the most-cited gap: typos get caught in CI, but prose that quietly gets harder does not. textlens and friends only do absolute thresholds; the delta gate is Papa's.

---

## 8. The LLM loop (the differentiator)

Papa's JSON is a **contract designed to be fed to an LLM**, so the *draft → measure → revise* loop closes automatically.

1. LLM (or human) writes `post.md`.
2. `papa post.md --report json > findings.json`.
3. Agent feeds `findings.json` + the source to an LLM with the documented rewrite prompt.
4. LLM returns a revised draft targeting the flagged spans.
5. Re-run Papa; loop until `verdict: pass` or no improvement.

Optional built-in: `papa post.md --suggest` runs that loop for you via a pluggable provider (default: **Claude**, `claude-sonnet-4-6` for speed / `claude-opus-4-8` for quality; provider-agnostic adapter so others can wire OpenAI/local). The prompt contract ships in `docs/llm-contract.md` so the tool is useful even if you bring your own agent.

> This is the line that makes Papa more than "Hemingway in CI": it is **a measurement layer purpose-built for an LLM to optimize against.**

---

## 9. Distribution & CI surfaces

- **CLI:** `pipx install papa` / `brew install papa` (later) / `npx papa`.
- **GitHub Action:** composite action `pendyala/papa-action@v1`, annotates PRs (SARIF) and can comment the Markdown summary + gate on threshold.
- **pre-commit hook:** `repo: https://github.com/pendyala/papa  hook: papa`.
- **Docker:** `docker run --rm -v $PWD:/work pendyala/papa post.md` — the portable path for Jenkins/GitLab/Circle.
- **Library:** `from papa import analyze` for programmatic use.

**GitHub Action usage (example):**
```yaml
- uses: pendyala/papa-action@v1
  with:
    files: "content/posts/**/*.md"
    max-grade: 10           # fail if harder than grade 10
    report: sarif,md
    comment: true           # post summary on the PR
```

---

## 10. Naming

Recommended: **Papa** — Hemingway's nickname; short, warm, memorable; pairs with the tagline **"The Old Man and the CI."** Project strategy leans on the literary brand (see §12).

**Package-name reality (verified 2026-06):** `papa` is **taken on both PyPI and npm**, and `papa-lint` is **free on PyPI**. Resolution: keep the brand and the CLI command as `papa`, but **publish the distribution as `papa-lint`** (PyPI), with `papactl` as fallback. Users still type `papa`; only the install name differs (`pipx install papa-lint`). This is now locked, not open.

Alternatives if a clash forces it:
- **Lucid** — clarity-forward, professional, broad.
- **Cormac** — literary, distinctive, low collision risk.
- **Clarity / Prose / Readable** — descriptive but generic and likely taken.
- *(Avoid **Iceberg** — collides with Apache Iceberg despite the nice "Iceberg Theory" tie-in.)*

---

## 11. Roadmap

- **v0.1 (MVP):** ingest md/txt, **pre-score normalization pass** (numbers/dates/URLs/identifiers), readability **consensus grade** (ARI + FK + Gunning fog) + passive + adverbs + complex-phrase, HTML + JSON + CLI reports, absolute threshold exit code. Run it on the LLM blog post as the first real-world demo.
- **v0.2:** **regression gate** (`--baseline`, delta vs base ref); GitHub Action + SARIF + PR-comment reporter; MDX/HTML/rST ingestors; config file.
- **v0.3:** `--suggest` LLM loop with Claude adapter; `proselint`/`alex` plugins; pre-commit + Docker.
- **v1.0:** stable JSON schema, docs site, comparison benchmarks, plugin API for custom analyzers.

---

## 12. Positioning strategy (48 Laws of Power, applied tastefully)

Framing the open-source launch as a deliberate reputation play — useful for a portfolio / NIW-style "I build things people use" narrative.

- **Law 6 — Court attention at all cost.** The literary name + "The Old Man and the CI" tagline + a striking before/after HTML screenshot in the README hero. Memorable beats descriptive.
- **Law 9 — Win through actions, not argument.** Lead the README with a *demo GIF / before-after*, not adjectives. Let the highlighted report make the case.
- **Law 13 — Appeal to people's self-interest.** README copy is about what the *reader* gets ("ship clearer docs, gate your pipeline"), never about us.
- **Law 5 — Reputation is the cornerstone of power.** Treat the first 10 issues like gold: fast, gracious responses. Quality docs and tests signal seriousness.
- **Law 25 — Re-create yourself.** Don't be "another linter." Own a category: *readability-as-code, built for the LLM-revision loop.*
- **Law 28 — Enter action with boldness.** Ship v0.1 publicly early with a confident, finished-looking README rather than a timid "WIP."
- **Law 1 — Never outshine the master.** When integrating `textstat`/`proselint`/`vale`, credit them prominently. Standing on giants, generously attributed, builds goodwill and avoids ecosystem friction.

(Used as marketing/positioning heuristics — the engineering and attribution stay honest and collaborative.)

