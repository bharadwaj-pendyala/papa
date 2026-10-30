"""Sentence segmentation that tracks offsets into the (clean) text."""

from __future__ import annotations

import re

# A sentence ends at .!? or at a blank line. The blank-line boundary keeps
# headings, list items, and the gaps left by stripped code blocks from being
# glued onto the prose around them.
_BOUNDARY = re.compile(r"[.!?]+(?=\s|$)|\n[ \t]*\n")


def split_sentences(text: str, breaks: set[int] | frozenset[int] = frozenset()) -> list[tuple[int, int, str]]:
    """Yield (start, end, text) for each sentence, offsets into ``text``.

    ``breaks`` are extra positions where a block (list item, table cell,
    heading) starts, so a sentence never runs across them.
    """
    cuts = sorted({m.end() for m in _BOUNDARY.finditer(text)} | {b for b in breaks if 0 < b < len(text)})
    sentences: list[tuple[int, int, str]] = []
    start = 0
    for cut in cuts:
        _append(sentences, text, start, cut)
        start = cut
    _append(sentences, text, start, len(text))
    return sentences


def _append(out: list, text: str, start: int, end: int) -> None:
    chunk = text[start:end]
    stripped = chunk.strip()
    if not stripped:
        return
    lead = len(chunk) - len(chunk.lstrip())
    real_start = start + lead
    out.append((real_start, real_start + len(stripped), stripped))
