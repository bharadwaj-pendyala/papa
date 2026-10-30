"""Small helpers shared by the reporters."""

from __future__ import annotations

import re


def line_col(source: str, offset: int) -> tuple[int, int]:
    """1-based line and column (in code points) of ``offset`` in ``source``."""
    line = source.count("\n", 0, offset) + 1
    return line, offset - (source.rfind("\n", 0, offset) + 1) + 1


def display_grade(value: float) -> float:
    """Formulas go negative on very simple text; a reader expects grade 0 there."""
    return max(value, 0.0)


def gate_grade(consensus: float, max_grade: float, failed: bool) -> str:
    """Show the grade with just enough decimals that it agrees with the verdict."""
    for digits in (1, 2, 3, 4):
        shown = f"{max(consensus, 0.0):.{digits}f}"
        if (float(shown) > max_grade) == failed:
            return shown
    return f"{consensus:.4f}"


_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MARKS = re.compile(r"\*\*|__|`")


def as_prose(source_text: str) -> str:
    """Source excerpt as a reader sees it: link text without URLs, no emphasis marks."""
    return " ".join(_MARKS.sub("", _LINK.sub(r"\1", source_text)).split())


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
