# eyes: a UX harness that agents can run

`tools/eyes.py` lets a coding agent see Papa the way a user sees it. It runs
the CLI in real situations, checks the output against UX contracts, and writes
a report that tells the agent what to fix and where.

The engine is stdlib-only and has no Papa imports. Papa-specific parts live in
`tests/ux/`. A later step can move the engine to its own package, so other
CLIs can use it.

## Run it

```bash
python tools/eyes.py run                    # all cases
python tools/eyes.py run --case hints       # one case (repeatable)
python tools/eyes.py run --browser          # also drive the HTML in Chromium
python tools/eyes.py approve --case hints   # accept the output you inspected
python tools/eyes.py list
```

`run` exits 1 when a check fails. It writes these files:

| File | Use |
|---|---|
| `artifacts/eyes/report.json` | Read this first. Every check, with failures listed first in `failures`. |
| `artifacts/eyes/report.txt` | The same report for people. |
| `artifacts/eyes/cases/<id>/stdout.txt` | Output without color codes. |
| `artifacts/eyes/cases/<id>/stdout.ansi` | Raw output, with color codes. |
| `artifacts/eyes/cases/<id>/snapshot.diff` | How the output changed from the reviewed snapshot. |
| `artifacts/eyes/cases/<id>/*.png` | Screenshots from `--browser`. Open them to see the page or terminal. |

Each failure in `report.json` has these fields:

- `check`: the name of the check that failed.
- `detail`: what is wrong.
- `expected` and `actual`: the evidence.
- `source`: the file that most likely needs the edit.
- `reproduce.shell`: a command that runs the case by hand.

## What it checks

For every case:

- The exit code and that no Python traceback reaches the user.
- The expected text on stdout and stderr, given as plain text or as a regex.
- No color codes in piped output or under `NO_COLOR`, and color in a real TTY.
- Line width in terminal cells, at the width of the case (80 when piped).
- Count and noun agree, so the output never says "1 sentences".
- Strict JSON (no `NaN`) and the Papa JSON contract (`tests/ux/papa_checks.py`).
- The HTML is one document that loads nothing from the network: no scripts,
  external links, `url()`, meta refresh or `on*` handlers.
- The output matches the reviewed snapshot in `tests/ux/snapshots/`.

With `--browser`, Playwright opens each HTML report at 1280 px and 390 px wide.
It also checks:

- Network requests. The page must not try to load anything.
- Horizontal overflow, and elements that go past the right edge.
- Console errors.
- Text contrast below WCAG AA.
- Highlights without a hover title.

It also turns colored TTY output into a PNG, so you can see the colors.
Without Playwright, eyes uses Chrome for screenshots only. A `browser-engine`
row says why.

To install Playwright:

```bash
pip install -e ".[eyes]"
python -m playwright install chromium
```

## Add a case

Add an object to `cases` in `tests/ux/eyes.json`. Each case runs in
`tests/ux/corpora/`, unless it sets `cwd`.

```json
{"id": "gate-fail", "argv": ["hard.md", "--max-grade", "8"], "exit": 1,
 "stdout_contains": ["FAIL"], "stdout_absent": ["Traceback"]}
```

| Key | Meaning |
|---|---|
| `argv` | Arguments after the command. `{out}` is the case artifact folder. |
| `exit` | The expected exit code (default 0). |
| `tty`, `cols` | Run in a real terminal of this width. |
| `stdin`, `stdin_file` | Text or a file for stdin. |
| `env`, `cwd` | Extra environment variables and a working folder. |
| `stdout_contains`, `stdout_absent`, `stdout_regex` | Text checks on stdout. The same keys exist for stderr. |
| `stdout_empty` | Stdout must be empty. |
| `expect_ansi` | Color codes must appear. |
| `json` | Stdout must be strict JSON that follows the plugin contract. |
| `html`, `html_contains` | The case writes this HTML file, and its visible text must contain these strings. |
| `check_width` | Set to `false` for machine formats such as `--report concise`. |

Write the case before you change the code. Run it and make sure it fails.

## The agent loop

1. Run `python tools/eyes.py run --browser`.
2. Read `artifacts/eyes/report.json`. Start with `failures`.
3. Open the screenshots and the `stdout.txt` files for the failing cases.
   Read them as a first-time user would.
4. Fix the file in `source`. Do not change a check to make it pass, unless the
   check is wrong.
5. Run again until no check fails except `snapshot`.
6. Read each `snapshot.diff`. When every change is an improvement, approve it.
   `approve` copies the output you inspected. It does not run the case again.
7. Run `pytest` and commit.

### Prompt for a UX improvement loop

```text
Improve the UX of this CLI with tools/eyes.py as your eyes.
1. Run `python tools/eyes.py run --browser`. Read artifacts/eyes/report.json.
2. Open the screenshots and stdout.txt files. List what a first-time user and
   a CI user would find confusing, noisy, or missing.
3. For each problem, add a case to tests/ux/eyes.json that fails today.
4. Fix the product, not the check. Keep each fix small.
5. Rerun until only snapshot checks fail. Review every snapshot.diff, then
   approve only the changes that improve the output.
6. Ask a second agent to review the diff and the snapshots. Fix real findings.
7. Run pytest, then commit with a message that says why.
Stop when a full review finds no problem worth a change.
```
