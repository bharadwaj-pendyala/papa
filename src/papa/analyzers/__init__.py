"""Analyzer registry — plugin-ready (spec §6).

Each analyzer is a callable taking an :class:`AnalyzerContext` and returning
findings in *clean-text* coordinates; the pipeline maps them to original offsets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..models import Finding


@dataclass
class AnalyzerContext:
    clean: str
    sentences: list[tuple[int, int, str]]


Analyzer = Callable[[AnalyzerContext], list[Finding]]

ANALYZERS: dict[str, Analyzer] = {}


def register(name: str) -> Callable[[Analyzer], Analyzer]:
    def decorate(fn: Analyzer) -> Analyzer:
        ANALYZERS[name] = fn
        return fn

    return decorate


# Import for side effects: each module registers itself.
from . import adverbs, complex_phrase, passive, readability  # noqa: E402,F401
