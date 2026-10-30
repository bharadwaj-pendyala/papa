"""Turn CLI arguments (files, directories, quoted globs, ``-``) into input paths."""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path

STDIN = "-"
PROSE_SUFFIXES = {".md", ".markdown", ".txt"}
_GLOB_CHARS = set("*?[")


class InputError(Exception):
    pass


def expand(args: list[str], excludes: list[str]) -> list[str]:
    """Return display paths in argument order, deduplicated, with excludes removed.

    Explicit files pass through untouched, even when missing, so the reader can
    report them. Directories and globs only yield prose files and skip hidden
    paths. Each exclude is an absolute fnmatch pattern.
    """
    if args.count(STDIN) > 1:
        raise InputError("stdin ('-') can only be read once; pass it a single time")

    paths: list[str] = []
    seen: set[str] = set()
    for arg in args:
        for path in _expand_one(arg):
            key = path if path == STDIN else os.path.realpath(path)
            if key in seen or _excluded(path, excludes):
                continue
            seen.add(key)
            paths.append(path)
    if args and not paths:
        raise InputError("every input was excluded by --exclude or the config exclude list")
    return paths


def _expand_one(arg: str) -> list[str]:
    if arg == STDIN:
        return [STDIN]
    if _GLOB_CHARS & set(arg) and not Path(arg).exists():
        matches = [m for m in glob.glob(arg, recursive=True) if _is_discoverable(m)]
        if not matches:
            raise InputError(f"no files match '{arg}'; check the pattern or the working directory")
        return sorted(os.path.normpath(m) for m in matches)
    if Path(arg).is_dir():
        found = []
        for root, dirs, files in os.walk(arg):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            found += [
                os.path.normpath(os.path.join(root, name)) for name in files
                if not name.startswith(".") and Path(name).suffix.lower() in PROSE_SUFFIXES
            ]
        if not found:
            raise InputError(f"no .md or .txt files in '{arg}'")
        return sorted(found)
    return [arg]


def _is_discoverable(path: str) -> bool:
    parts = Path(path).parts
    return (
        Path(path).is_file()
        and Path(path).suffix.lower() in PROSE_SUFFIXES
        and not any(p.startswith(".") and p not in (".", "..") for p in parts)
    )


def _excluded(path: str, excludes: list[str]) -> bool:
    if path == STDIN:
        return False
    absolute = Path(os.path.abspath(path)).as_posix()
    return any(_glob_regex(pattern).fullmatch(absolute) for pattern in excludes)


def _glob_regex(pattern: str) -> re.Pattern:
    """Glob with the same meaning discovery uses: ``**/`` spans zero or more folders."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def anchor(pattern: str, base: Path) -> str:
    """Make an exclude pattern absolute so it matches regardless of the cwd."""
    return pattern if os.path.isabs(pattern) else (Path(os.path.abspath(base)) / pattern).as_posix()
