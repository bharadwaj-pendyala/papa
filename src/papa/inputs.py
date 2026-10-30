"""Turn CLI arguments (files, directories, quoted globs, ``-``) into input paths."""

from __future__ import annotations

import fnmatch
import glob
import os
import re
from pathlib import Path

STDIN = "-"
PROSE_SUFFIXES = {".md", ".markdown", ".txt"}
_GLOB_CHARS = set("*?[")


class InputError(Exception):
    pass


def expand(args: list[str], excludes: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (paths, errors): display paths in argument order, deduplicated,
    with excludes removed, plus one error for each argument that matched nothing.

    Explicit files pass through untouched, even when missing, so the reader can
    report them. Directories and globs only yield prose files and skip hidden
    paths. Each exclude is an absolute glob pattern.
    """
    if args.count(STDIN) > 1:
        raise InputError("stdin ('-') can only be read once; pass it a single time")

    paths: list[str] = []
    errors: list[tuple[str, str]] = []
    seen: set[str] = set()
    for arg in args:
        try:
            expanded = _expand_one(arg)
        except InputError as error:
            errors.append((arg, str(error)))
            continue
        for path in expanded:
            key = path if path == STDIN else os.path.realpath(path)
            if key in seen or _excluded(path, excludes):
                continue
            seen.add(key)
            paths.append(path)
    if args and not paths and not errors:
        raise InputError("every input was excluded by --exclude or the config exclude list")
    return paths, errors


def _expand_one(arg: str) -> list[str]:
    if arg == STDIN:
        return [STDIN]
    if _GLOB_CHARS & set(arg) and not Path(arg).exists():
        matches = [m for m in glob.glob(arg, recursive=True) if _is_discoverable(m)]
        if not matches:
            raise InputError("no files match; check the pattern or the working directory")
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
            raise InputError("no .md or .txt files in this folder")
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
        elif pattern[i] == "[" and (close := _class_end(pattern, i)) != -1:
            out.append(_class_regex(pattern[i + 1:close]))
            i = close + 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def _class_end(pattern: str, start: int) -> int:
    # Like fnmatch: a ']' right after '[' or '[!' is a literal member, not the end.
    j = start + 1
    if j < len(pattern) and pattern[j] == "!":
        j += 1
    if j < len(pattern) and pattern[j] == "]":
        j += 1
    return pattern.find("]", j)


def _class_regex(body: str) -> str:
    # fnmatch owns the edge cases (leading '-', reversed ranges); a class never matches '/'.
    translated = fnmatch.translate(f"[{body}]")
    return "(?!/)" + re.fullmatch(r"\(\?s:(.*)\)\\[zZ]", translated, re.DOTALL).group(1)


def anchor(pattern: str, base: Path) -> str:
    """Make an exclude pattern absolute so it matches regardless of the cwd."""
    return pattern if os.path.isabs(pattern) else (Path(os.path.abspath(base)) / pattern).as_posix()
