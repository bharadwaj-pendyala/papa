"""Pre-score normalization (spec §2.5).

Numbers, dates, URLs, and identifiers mis-score in readability formulas: a long
URL counts as one enormous "word", a year inflates syllable counts, `snake_case`
identifiers read as multi-syllable nonsense. Collapse them to a neutral
one-syllable token *before* scoring so the grade reflects the prose, not the data.

This runs only on text fed to the readability formulas. Analyzers that need real
words (passive, adverbs, phrases) operate on the untouched clean text.
"""

from __future__ import annotations

import re

TOKEN = "thing"  # one syllable, one word, semantically neutral

# Order matters: URLs first (they contain dots/numbers), then dates, then bare
# numbers, then the various identifier shapes.
_PATTERNS = [
    re.compile(r"https?://\S+"),
    re.compile(r"www\.\S+"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),                 # ISO date
    re.compile(r"\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b"),     # numeric date
    re.compile(r"\b\w*\d\w*(?:\.\d+)?%?"),               # numbers, decimals, %, and digit-bearing identifiers
    re.compile(r"\b[A-Za-z]+_[A-Za-z0-9_]+\b"),          # snake_case
    re.compile(r"\b[a-z]+[A-Z]\w*\b"),                   # camelCase
    re.compile(r"\b[a-z0-9]+(?:\.[a-z0-9]+)+\b", re.IGNORECASE),  # dotted.path
    re.compile(r"\b[A-Z]{2,}\b"),                         # ALL_CAPS / acronyms
]


def normalize(text: str) -> str:
    for pattern in _PATTERNS:
        text = pattern.sub(TOKEN, text)
    return text
