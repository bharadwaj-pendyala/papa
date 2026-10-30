# Contributing to Papa

Thanks for helping make prose more readable. Papa is open source (MIT) and contributions of every size are welcome: bug reports, docs fixes, new analyzers, and reporters.

## Ways to contribute

- **Report a bug or request a feature** via [issues](https://github.com/bharadwaj-pendyala/papa/issues). Use the templates.
- **Pick a `good first issue`** if you are new. They are [labeled](https://github.com/bharadwaj-pendyala/papa/labels/good%20first%20issue).
- **Open a pull request** for a fix or a feature. Small, focused PRs get reviewed fastest.

## Development setup

Papa is a Python 3.11+ project.

```bash
git clone https://github.com/bharadwaj-pendyala/papa.git
cd papa
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

On macOS, if `papa` fails with `No module named 'papa'` after an install, a
sync tool such as iCloud may have hidden the editable `.pth` file. Python 3.13
skips hidden `.pth` files. Run `chflags nohidden .venv/lib/python*/site-packages/*.pth`.

Run the CLI against a file to see it work:

```bash
papa README.md
papa README.md --report json
```

## Check the UX with eyes

Papa ships a harness that runs the CLI like a user does and checks the output.
Run it before you open a PR that changes what users see:

```bash
python tools/eyes.py run              # terminal, JSON and HTML checks
python tools/eyes.py run --browser    # also screenshots and layout checks
```

See [docs/eyes.md](docs/eyes.md) for how to add a case and approve output
changes.

## Project layout

```
src/papa/
  ingest.py        format detection, code/SVG/frontmatter stripping, offset map
  normalize.py     neutralize numbers/dates/URLs/identifiers before scoring
  analyzers/       pluggable analyzers (readability, passive, adverbs, complex_phrase)
  aggregate.py     merge spans, compute the document score
  inputs.py        files, folders, globs, stdin, and excludes
  config.py        papa.toml and [tool.papa]
  reporters/       cli, concise, json, html
tests/             pytest suite (one file per area)
tests/ux/          eyes cases, corpora, reviewed snapshots
tools/eyes.py      the UX harness
```

The data flow is `Ingestor -> Analyzers -> Aggregator -> Reporters`. See `spec.md` for the full architecture.

## Adding an analyzer

1. Add a module under `src/papa/analyzers/` that returns a list of `Finding` objects.
2. Register it in `src/papa/analyzers/__init__.py`.
3. Add a test under `tests/`.
4. Keep core heuristics small and dependency-light. Heavy linters belong as optional plugins.

## Pull request checklist

- [ ] `pytest` passes locally.
- [ ] `python tools/eyes.py run` passes, and you reviewed any snapshot change.
- [ ] New behavior has a test.
- [ ] Public behavior changes are reflected in `README.md` or `spec.md`.
- [ ] Commit messages explain the why, not just the what.

## Code style

- Minimal comments. Let names carry meaning.
- Match the patterns already in the file you are editing.
- No em dashes in prose files. Use a comma, a period, or rewrite.

## Conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
