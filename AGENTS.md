# Notes for coding agents

- Set up: `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`.
- Unit tests: `pytest`.
- UX checks: `python tools/eyes.py run`. Add `--browser` to see the HTML and
  terminal output as screenshots. Read `docs/eyes.md` before you change any
  user-facing output.
- When you change output, review each `artifacts/eyes/cases/*/snapshot.diff`,
  then run `python tools/eyes.py approve --case <id>`.
- The JSON report is a contract (`docs/llm-contract.md`). Change its shape only
  with a version bump.
- No em dashes in prose. Keep comments few and about the why.
