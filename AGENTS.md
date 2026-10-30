# Notes for coding agents

- Set up: `python -m venv .venv && .venv/bin/pip install -e ".[dev,eyes]"`.
- Use the venv for every command: `.venv/bin/pytest`, `.venv/bin/eyes run`.
  eyes runs papa with the interpreter that runs eyes, so an `eyes` from another
  environment without papa's dependencies fails every case.
- UX checks: `.venv/bin/eyes run`. Add `--browser` to see the HTML and
  terminal output as screenshots. Read `docs/eyes.md` before you change any
  user-facing output.
- When you change output, review each `artifacts/eyes/cases/*/snapshot.diff`,
  then run `.venv/bin/eyes approve --case <id>`.
- The JSON report is a contract (`docs/llm-contract.md`). Change its shape only
  with a version bump.
- No em dashes in prose. Keep comments few and about the why.
