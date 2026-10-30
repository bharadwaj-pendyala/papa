# UX checks with agent-eyes

Papa's UX checks run on [agent-eyes](https://github.com/bharadwaj-pendyala/agent-eyes),
a separate tool that lets a coding agent see a CLI the way a user sees it. Read
its README for every config key, the report format, and the agent loop.

## Run them

```bash
pip install -e ".[dev,eyes]"
python -m playwright install chromium        # only for --browser

eyes --config tests/ux/eyes.json run              # all cases
eyes --config tests/ux/eyes.json run --case hints # one case
eyes --config tests/ux/eyes.json run --browser    # also screenshot the HTML report
eyes --config tests/ux/eyes.json approve --case hints
```

`eyes` finds `tests/ux/eyes.json` on its own when you run it from the repo
root, so `--config` is optional there.

## What lives in papa

| Path | What it is |
|---|---|
| `tests/ux/eyes.json` | Every case: the arguments, the expected exit code, and what the output must or must not contain. |
| `tests/ux/corpora/` | Input files the cases run on, including real-world Markdown and MDX patterns. |
| `tests/ux/snapshots/` | The reviewed output of each case. |
| `tests/ux/papa_checks.py` | A plugin that checks papa's JSON contract and offset round-trips. |

## Add a case

Add an object to `cases` in `tests/ux/eyes.json`. Cases run in
`tests/ux/corpora/` unless they set `cwd`.

```json
{"id": "gate-fail", "argv": ["hard.md", "--max-grade", "8"], "exit": 1,
 "stdout_contains": ["FAIL"]}
```

Write the case before you change papa, and watch it fail first. Then fix
papa, rerun, read each `snapshot.diff`, and approve the changes that improve
the output.
