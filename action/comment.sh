#!/usr/bin/env bash
# Post the papa report on the PR, or update the comment from an earlier run.
set -euo pipefail

marker="<!-- papa-readability -->"
# papa writes no report on a config or usage error; keep the last good comment then.
[ -s "$REPORT" ] || { echo "papa: no report to post"; exit 0; }
body="$(printf '%s\n%s' "$marker" "$(head -c 60000 "$REPORT")")"

existing=$(gh api "repos/$GITHUB_REPOSITORY/issues/$PR/comments" --paginate \
  --jq ".[] | select(.body | startswith(\"$marker\")) | .id" | head -n 1)

# A PR from a fork gets a read-only token, so a failed post must not fail the job.
if [ -n "$existing" ]; then
  gh api -X PATCH "repos/$GITHUB_REPOSITORY/issues/comments/$existing" -f body="$body" >/dev/null \
    || echo "::warning title=papa::Could not update the PR comment. The token may be read-only."
else
  gh api "repos/$GITHUB_REPOSITORY/issues/$PR/comments" -f body="$body" >/dev/null \
    || echo "::warning title=papa::Could not post the PR comment. The token may be read-only."
fi
