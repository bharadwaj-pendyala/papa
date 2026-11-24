"""Turn CLI arguments (files, directories, quoted globs, ``-``) into input paths."""

from __future__ import annotations

import fnmatch
import glob
import os
import re
import subprocess
from pathlib import Path

STDIN = "-"
PROSE_SUFFIXES = {".md", ".markdown", ".mdx", ".txt"}
_GLOB_CHARS = set("*?[")
# Folder and glob scans skip these: they hold dependencies, config, or legal text, not docs.
_SKIP_DIRS = {"node_modules", "LICENSES"}
_NOT_DOCS = re.compile(
    r"(?:requirements|constraints)[\w.-]*\.txt|robots\.txt|cmakelists\.txt|(?:licen[cs]e(?:-\w+)?|copying|notices?|third[_-]party[_-](?:notices?|licen[cs]es?))(?:\.\w+)?",
    re.IGNORECASE,
)


class InputError(Exception):
    pass


class AllExcluded(InputError):
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
        raise AllExcluded("every input was excluded by --exclude or the config exclude list")
    return paths, errors


def _expand_one(arg: str) -> list[str]:
    if arg == STDIN:
        return [STDIN]
    if _GLOB_CHARS & set(arg) and not Path(arg).exists():
        matches = _not_git_ignored([m for m in glob.glob(arg, recursive=True) if _is_discoverable(m)])
        if not matches:
            raise InputError("no files match; check the pattern or the working directory")
        return sorted(os.path.normpath(m) for m in matches)
    if Path(arg).is_dir():
        found = []
        for root, dirs, files in os.walk(arg):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in _SKIP_DIRS]
            found += [os.path.normpath(os.path.join(root, name)) for name in files if _is_doc_name(name)]
        found = _not_git_ignored(found)
        if not found:
            raise InputError("no .md, .mdx or .txt docs in this folder")
        return sorted(found)
    return [arg]


def _is_discoverable(path: str) -> bool:
    parts = Path(path).parts
    return (
        Path(path).is_file()
        and _is_doc_name(Path(path).name)
        and not any((p.startswith(".") and p not in (".", "..")) or p in _SKIP_DIRS for p in parts)
    )


def _is_doc_name(name: str) -> bool:
    return not name.startswith(".") and Path(name).suffix.lower() in PROSE_SUFFIXES and not _NOT_DOCS.fullmatch(name)


def _not_git_ignored(paths: list[str]) -> list[str]:
    """Drop the paths that git ignores, such as build output. Outside a git repo, keep all."""
    if not paths:
        return paths
    absolute = [os.path.abspath(p) for p in paths]
    try:
        result = subprocess.run(
            ["git", "-C", os.path.commonpath([os.path.dirname(a) for a in absolute]), "check-ignore", "--no-index", "--stdin", "-z"],
            input="\0".join(absolute), capture_output=True, text=True, check=False,
        )
    except OSError:
        return paths
    # 0: some paths are ignored. 1: none are. Anything else: not a repo, or git failed.
    # --no-index also lets a path inside a submodule through instead of failing the batch.
    if result.returncode != 0:
        return paths
    ignored = set(result.stdout.split("\0"))
    return [p for p, a in zip(paths, absolute) if a not in ignored]


def _excluded(path: str, excludes: list[str]) -> bool:
    if path == STDIN:
        return False
    absolute = Path(os.path.abspath(path)).as_posix()
    return any(_glob_regex(pattern).fullmatch(absolute) for pattern in excludes)


def _glob_regex(pattern: str) -> re.Pattern:
    """Glob with the same meaning discovery uses: a whole ``**`` component spans
    zero or more folders. Anywhere else ``*`` stays inside one folder."""
    out, i = [], 0
    while i < len(pattern):
        whole_component = i == 0 or pattern[i - 1] == "/"
        if whole_component and pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif whole_component and pattern.startswith("**", i) and i + 2 == len(pattern):
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
    # normpath folds '..' the same way input paths are folded, so they still line up.
    return Path(os.path.normpath(os.path.join(os.path.abspath(base), pattern))).as_posix()
