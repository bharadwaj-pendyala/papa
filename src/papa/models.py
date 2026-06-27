"""Core data models shared across the pipeline (spec §6)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Highlight categories (the Hemingway view) and their colors — spec §5.
HARD = "hard-sentence"
VERY_HARD = "very-hard-sentence"
PASSIVE = "passive"
ADVERB = "adverb"
COMPLEX = "complex-phrase"

COLOR = {
    HARD: "yellow",
    VERY_HARD: "red",
    PASSIVE: "green",
    ADVERB: "blue",
    COMPLEX: "purple",
}

# When two word-level spans overlap, the higher value wins (spec §6 "resolve priority").
PRIORITY = {
    VERY_HARD: 5,
    HARD: 4,
    PASSIVE: 3,
    COMPLEX: 2,
    ADVERB: 1,
}


@dataclass
class Finding:
    """One flagged span, normalized so every analyzer emits the same shape."""

    start: int
    end: int
    category: str
    color: str
    severity: str
    message: str
    analyzer: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DocumentScore:
    """The grade panel. Field names match the spec §6 contract exactly."""

    ari: float
    flesch_kincaid: float
    gunning_fog: float
    reading_grade: str
    sentences: int
    hard_sentences: int
    very_hard_sentences: int
    adverbs: int
    passive: int
    complex_phrases: int
    verdict: str
    threshold: dict | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Analysis:
    path: str
    source: str
    clean: str
    score: DocumentScore
    findings: list[Finding]
