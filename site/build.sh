#!/usr/bin/env bash
# Build the Pages site into site/: the papa wheel and a sample report.
set -euo pipefail
cd "$(dirname "$0")/.."

python -m pip install --quiet build
rm -rf site/assets && mkdir -p site/assets
python -m build --wheel --outdir site/assets >/dev/null
wheel=$(basename site/assets/papa_lint-*.whl)
printf '{"wheel": "%s"}\n' "$wheel" > site/assets/wheel.json

python -m pip install --quiet .
(cd tests/ux/corpora && papa all-findings.md --report html -o ../../../site/report.html -q)
