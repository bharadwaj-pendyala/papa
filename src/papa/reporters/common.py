"""Small helpers shared by the reporters."""

from __future__ import annotations

import re
from bisect import bisect_right


class LineIndex:
    """1-based line and column (in code points) of an offset in ``source``.

    Line starts are found once, so a file with many findings is not rescanned for each one.
    """

    def __init__(self, source: str):
        self._starts = [0] + [m.end() for m in re.finditer("\n", source)]

    def line_col(self, offset: int) -> tuple[int, int]:
        line = bisect_right(self._starts, offset)
        return line, offset - self._starts[line - 1] + 1


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


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
