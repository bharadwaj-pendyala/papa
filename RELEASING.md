# Releasing Papa

Papa publishes to PyPI as `papa-lint` through
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/). No API token is
stored in the repo. The `Release` workflow (`.github/workflows/release.yml`)
builds the sdist and wheel, runs `twine check`, and uploads them when a GitHub
Release is published.

## One-time setup

Do these once, before the first release.

1. **Add a pending publisher on PyPI.** Sign in to PyPI, open
   [Your account > Publishing](https://pypi.org/manage/account/publishing/),
   and add a new pending publisher under "GitHub":
   - PyPI Project Name: `papa-lint`
   - Owner: `bharadwaj-pendyala`
   - Repository name: `papa`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

   PyPI creates the project on the first successful upload.
2. **Create the `pypi` environment on GitHub.** In the repo, open
   Settings > Environments > New environment and name it `pypi`. Optionally add
   yourself as a required reviewer so every upload waits for approval.

## Every release

1. Bump the version in both places, keeping them equal:
   - `pyproject.toml`: `version = "X.Y.Z"`
   - `src/papa/__init__.py`: `__version__ = "X.Y.Z"`
2. Open a PR with the bump, wait for CI to pass, and merge it to `main`.
3. Optionally check the build locally:

   ```bash
   python -m pip install build twine
   python -m build
   twine check --strict dist/*
   ```

4. On GitHub, open Releases > Draft a new release. Create the tag `vX.Y.Z` on
   `main`, add notes, and click **Publish release**.
5. Watch the `Release` workflow in the Actions tab. When it finishes, confirm
   the new version at <https://pypi.org/project/papa-lint/> and run
   `pipx install papa-lint` in a clean shell.

## After the first release only

Flip the README back to PyPI installs:

- Quickstart: replace `pipx install git+https://github.com/bharadwaj-pendyala/papa`
  with `pipx install papa-lint`, and drop the "not on PyPI yet" sentences.
- CI usage: replace `python -m pip install git+https://github.com/bharadwaj-pendyala/papa`
  with `python -m pip install papa-lint`, and drop the "After the first PyPI
  release" line.
- Optionally restore the PyPI version badge:
  `[![PyPI](https://img.shields.io/pypi/v/papa-lint.svg)](https://pypi.org/project/papa-lint/)`
