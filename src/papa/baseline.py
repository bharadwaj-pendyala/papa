"""Read files as they were at a git ref, for the --baseline regression gate."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


class BaselineError(Exception):
    pass


def resolve(ref: str) -> str:
    """Return the commit SHA for ``ref``, so every file is read from the same commit."""
    try:
        proc = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                              capture_output=True, text=True)
    except FileNotFoundError:
        raise BaselineError("--baseline needs git, and git is not installed") from None
    if proc.returncode == 0:
        return proc.stdout.strip()
    if "not a git repository" in proc.stderr:
        raise BaselineError("--baseline needs a git repository; run papa inside one")
    raise BaselineError(f"--baseline: no commit '{ref}' in this repository\n"
                        f"  fetch it first: git fetch origin {ref}")


def source_at(commit: str, path: str) -> str | None:
    """The file's text at ``commit``, or None when the file is not in it."""
    file = Path(path)
    proc = subprocess.run(["git", "-C", str(file.parent), "show", f"{commit}:./{file.name}"], capture_output=True)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def short(ref: str) -> str:
    return ref[:12] if re.fullmatch(r"[0-9a-f]{40}", ref) else ref
