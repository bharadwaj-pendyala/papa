"""Small helpers shared by the reporters."""

from __future__ import annotations


def line_col(source: str, offset: int) -> tuple[int, int]:
    """1-based line and column (in code points) of ``offset`` in ``source``."""
    line = source.count("\n", 0, offset) + 1
    return line, offset - (source.rfind("\n", 0, offset) + 1) + 1


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
