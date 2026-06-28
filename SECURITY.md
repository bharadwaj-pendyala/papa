# Security Policy

## Supported versions

Papa is pre 1.0. Security fixes land on the latest released version and on `main`.

## Reporting a vulnerability

Please do not open a public issue for security problems.

Report privately through GitHub's [security advisories](https://github.com/bharadwaj-pendyala/papa/security/advisories/new),
or email the maintainer at bharadwajpendyala@gmail.com.

Include a description, reproduction steps, and the impact you expect. You will
get an acknowledgement within a few days, and a fix or mitigation plan once the
report is confirmed.

## Scope

Papa reads local files and, only with `--suggest`, sends text to a configured
LLM provider. It does not run untrusted code from the documents it analyzes.
Reports about untrusted input causing code execution, file writes outside the
target path, or leaking content to a network when `--suggest` is off are
in scope and valued.
