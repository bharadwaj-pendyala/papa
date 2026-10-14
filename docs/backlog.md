# Papa backlog: findings from hands-on testing

Source: a hands-on test session on 2026-10-14. Papa 0.1.0 was installed in a fresh
virtualenv and used in five roles, on realistic documents (a blog post with
frontmatter, tables, lists, code, footnotes; a `docs/` tree; CRLF, empty,
code-only, Unicode and MDX files). The HTML report was opened in Chromium at
desktop and phone width, in light and dark mode.

Every item below was reproduced. The evidence column shows what a user sees today.

**Priority key**
- **P0 Blocker**: a new user cannot get value, or the tool gives wrong data to automation.
- **P1 Trust**: the result is wrong or misleading, so users stop believing the grade.
- **P2 Experience**: it works, but it doesn't feel good to use yet.

**Size key:** XS < 1h · S < 1 day · M 2 to 3 days · L about 1 week

---

## Epic A: First run (P0)

The first five minutes decide whether anyone uses Papa a second time.

| ID | Item | Evidence | Done when | Size |
|---|---|---|---|---|
| A1 | **Publish `papa-lint` to PyPI**, or change the README to install from git | `pypi.org/pypi/papa-lint/json` returns 404. The first Quickstart command, `pipx install papa-lint`, fails. The README's CI example and the PyPI badges are broken too. | The `pipx install papa-lint && papa --version` pipeline works on a clean machine. A CI job runs the README's Quickstart commands. | S |
| A2 | **Works offline on first run** | textstat ≥0.7.x downloads NLTK `cmudict` the first time it runs. Without network: a **105-line traceback**. `pyproject.toml` pins `textstat>=0.7.3` with no upper limit, so the behaviour changed underneath us. | Write ARI, Flesch-Kincaid and Fog in Papa itself, with a bundled syllable counter (or pin textstat to a version with no network access). Grades are byte-identical across dependency upgrades. A test runs with networking disabled. | M |
| A3 | **A crash must not look like a failed grade** | The offline crash exits **1**, the same code as "prose failed `--max-grade`". CI shows a red readability check when Papa itself is broken. | Exit codes: 0 pass · 1 over the limit · 2 usage/IO error · 3 internal error. Unexpected exceptions print one line plus a link for reporting it. Exit codes are documented in `--help`. | S |
| A4 | **Friendly errors** | `papa docs/` prints `[Errno 21] Is a directory`. `papa -` prints `No such file or directory: '-'`. | Every user error is one plain sentence that says what to do next. | XS |

## Epic B: Trust the grade (P1)

The grade is the product. Today Markdown syntax both inflates it and deflates it.

| ID | Item | Evidence | Done when | Size |
|---|---|---|---|---|
| B1 | **Parse Markdown properly** (markdown-it-py, which tracks where each piece came from in the source) instead of regex stripping | Papa's own README gets **Grade 13 (fail at 10)**; with the Markdown removed it gets **Grade 9**. The badge row is a red "very hard sentence (grade 30)", and the nav links score grade 26. Image syntax, tables, HTML tags/comments (`<!-- TODO -->`), `**`, `#` and footnotes `[^1]:` are all graded as prose. | Only prose text gets graded: link text is kept and URLs are dropped. Headings, list items and table cells are separate units. Papa's README and the sample post have fixture grades in tests. | L |
| B2 | **Sentence splitting** | `"Write it e.g. like this, i.e. short. Done."` becomes 4 sentences (should be 2). `"The U.S. team shipped v2.1 on Jan. 5 at 3 p.m. today."` becomes 4 (should be 1). The list markers `1.` `2.` `3.` each count as a sentence, which pulls the grade **down**. In the HTML, the sentence highlight visibly stops at "e.g.". | An abbreviation list and decimal/version handling; list markers are not sentences. The corpus (C1) covers 30 or more splitting cases. | M |
| B3 | **Inline code leaves broken sentences** | `` Pinning the cache key to `hashFiles(...)` per workspace. `` is graded as "Pinning the cache key to  per workspace." | Replace code with a neutral placeholder word instead of deleting it, keeping offsets correct. | S |
| B4 | **Explain the result near the limit** | `docs/api.md · Grade 6, easy to read · ✗ fails --max-grade 6`. The real score is 6.3, but the user sees "6 fails 6" and assumes a bug. | When a limit is set, show one decimal place: `Grade 6.3 · limit 6 ✗`. | XS |
| B5 | **Say when there's no prose** | An empty file gives "Grade 0, easy to read (0 sentences)". A code-only file gives "Grade 1". | "No prose found" is shown, and gating skips the file. A flag makes empty files fail if a team wants that. | S |
| B6 | **Reject or warn on unsupported input** | `.mdx` is silently treated as Markdown: `import X from "y"` and `<Callout>` get graded (grade 11 for 1 line of prose). `analyze(fmt="rst")` is accepted silently. French and Japanese text is graded with English formulas, with no warning. | Unknown format means a clear error or a warning. MDX: strip `import`/`export`/JSX, or warn. Non-English text produces a warning. | S/M |

## Epic C: Analyzer accuracy (P1)

Spot check: **9 of 16** labelled sentences classified correctly.

| ID | Item | Evidence | Done when | Size |
|---|---|---|---|---|
| C1 | **Hand-labelled test corpus plus precision/recall in CI** | No accuracy measurement exists today, so any heuristic change is a gamble. | `tests/corpus/` with 200+ labelled sentences. CI prints precision and recall per analyzer and fails on a regression. | M |
| C2 | **Passive voice false positives and misses** | Wrongly flagged: "She is tired", "I am interested", "We need to get started", "The team got excited". Missed: "tests were no longer parallelized". | Common adjectival participles and get-idioms are excluded. Negation/adverb phrases are allowed between the verb and participle. Measured with C1. | M |
| C3 | **Adverb false positives and misses** | Wrongly flagged: "Sicily", "costly". Missed: "very", "quite", which are Hemingway's main targets. | A larger exception list or a small POS lexicon. A qualifier list ("very", "quite", "rather", "somewhat"…). | S |

## Epic D: Feedback that tells you what to do (P2, but this sets Papa apart)

| ID | Item | Evidence | Done when | Size |
|---|---|---|---|---|
| D1 | **"Path to green"** | Findings are a flat list in file order, all with the same weight (33 lines for the README). Nothing tells the user where to start. | Rank sentences by how much fixing each would lower the document grade, and show "Fix these N sentences to pass". The full list goes behind `--all`. | M |
| D2 | **Messages you can act on** | `Very hard to read (grade 28)`: the number means nothing to a writer, and there's no fix. | `68 words, 4 clauses. Split after "runner pool".` Passive: "Say who did it." A structured `suggestion` field. | M |
| D3 | **Group findings under their sentence** | An adverb and a passive inside a hard sentence print as separate lines mixed in with others (see L11/L17 in the post). | Show the sentence once, with its word-level notes indented beneath it. | S |
| D4 | **Clickable `path:line:col`** | The output shows only `L42`. | Use the `post.md:42:9` format that terminals and editors already make clickable. | XS |
| D5 | **Multi-file summary** | Three files over the limit print three separate blocks, with no total and no "worst file". | Footer: `2 of 3 files over limit 6 · worst: docs/guide/deep.md (8.1)`. | S |
| D6 | **Folders, glob patterns, stdin, no arguments** | `papa docs/`, `papa 'docs/**/*.md'` and `papa -` all fail. Running `papa` alone prints a usage error. | Accept folders and patterns; `-` reads stdin; plain `papa` checks the repo's git-tracked `*.md`/`*.txt`. | M |
| D7 | **One bad file shouldn't stop the run** | `papa post.md missing.md` stops at the missing file, so `post.md` never gets checked. | Report the error, keep going, and exit 2 at the end. | S |
| D8 | Grammar: "(1 sentences)" | Shown in the code-only file output. | Use correct plurals. | XS |

## Epic E: The HTML report (P2)

Screenshots: desktop, phone (390px) and dark mode of the sample post, plus Papa's own README.

| ID | Item | Evidence | Done when | Size |
|---|---|---|---|---|
| E1 | **Several files produce broken HTML** | `papa a.md b.md --report html -o r.html` writes **two `<html>` documents joined in one file**. | One report with a file list (worst first), or a clear error. | M |
| E2 | **Show rendered prose, not raw Markdown** | The report shows frontmatter, `![...](https://…)` badge URLs and table pipes in monospace. It reads like source code, not writing. | Render Markdown to HTML, map highlights onto the rendered text, and fold away anything that isn't prose. | L |
| E3 | **Mobile layout** | At 390px the page is 653px wide: the text is cut off and scrolls sideways. | The sidebar stacks above the text below 760px, with no horizontal scrolling. | S |
| E4 | **Dark mode** | `prefers-color-scheme: dark` has no effect. | Define colour tokens, with highlight colours that keep enough contrast in both themes. | S |
| E5 | **Explanations people can find** | The explanation for each highlight lives only in a `title` tooltip: slow on desktop, invisible on touch screens. | Clicking or tapping a highlight opens a small card with the cause and fix. Legend rows turn categories on and off. | M |
| E6 | Relative paths | The sidebar shows `/home/user/papa/README.md`. | Show the path relative to the working directory. | XS |

## Epic F: CI and automation (P0 for agents, P2 for the rest)

| ID | Item | Evidence | Done when | Size |
|---|---|---|---|---|
| F1 | **CRLF files give wrong offsets** (P0) | The file is read with newline conversion, so on a CRLF file the adverb `extremely` maps to source text `'s extreme'` and passive `is used` maps to `'t is us'`. An agent editing by offset damages the file. | Read with `newline=""`. Tests check offsets on CRLF and mixed line endings. | XS |
| F2 | **Same JSON shape every time** | One file gives an object; two files give a list. Automation has to special-case the count. | `{version, files: [...]}` always. Add `line`, `col`, a stable `rule` id and `suggestion`. Publish a JSON Schema. | M |
| F3 | **Baseline / regression gate** | Only an absolute `--max-grade` exists, so existing documents block adoption on day one. | `--baseline <ref or file>` fails only when a file got harder. | L |
| F4 | **GitHub annotations** | No inline PR feedback without writing your own glue. | `--report github` emits `::warning file=…,line=…,col=…::`. | S |
| F5 | **Config file and ignore comments** | No way to set a project limit or skip a passage. | `[tool.papa]` in `pyproject.toml` / `.papa.toml`; `<!-- papa-ignore-next -->`. | M |
| F6 | pre-commit hook | Not available. | Add a `.pre-commit-hooks.yaml`. | XS |

## Epic G: Library API

| ID | Item | Evidence | Done when | Size |
|---|---|---|---|---|
| G1 | Clean public namespace | `dir(papa)` exposes `annotations` and `replace` (leaked imports). | Define `__all__`, and document the stable API. | XS |

---

## Suggested order

1. **Sprint 1, "it works and it tells the truth":** A1, A2, A3, A4, F1, B4, B5, D8, G1, E6. All small. This removes every blocker found.
2. **Sprint 2, "the grade is right":** B1, B2, B3, C1, then C2 and C3 measured against C1.
3. **Sprint 3, "it tells you what to do":** D1, D2, D3, D4, D5, D6, D7, F2.
4. **Sprint 4, "it fits your workflow":** E1 to E5, F3 to F6, B6.

Success check for sprints 1 and 2: Papa's own README passes `--max-grade 10`, and
`pipx install papa-lint && papa README.md` works on a laptop with no network access.
