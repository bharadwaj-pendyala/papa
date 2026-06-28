"""Format-aware ingestion with a map back to the original source (spec §6).

Strips non-prose (YAML frontmatter, fenced + inline code, SVG) from Markdown so
analyzers see prose only, while keeping an :class:`OffsetMap` so every finding
maps back to original source offsets, not the stripped text. Stripped regions
are removed (clean text is shorter), so the map does real translation work.
"""

from __future__ import annotations

import re
from bisect import bisect_right

_FRONTMATTER = re.compile(r"\A---\n.*?\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_FENCED = re.compile(
    r"(?:\A|\n)(`{3,}|~{3,})[^\n]*\n(?:.*?\n)?\1[ \t]*(?=\n|\Z)", re.DOTALL
)
_SVG = re.compile(r"<svg\b.*?</svg>", re.DOTALL | re.IGNORECASE)
_INLINE = re.compile(r"`[^`\n]+`")


class OffsetMap:
    """Maps a position in the cleaned text back to the original source."""

    def __init__(self, segments: list[tuple[int, int, int]]):
        # Each segment is (clean_start, orig_start, length), contiguous in clean space.
        self._segments = segments or [(0, 0, 0)]
        self._clean_starts = [seg[0] for seg in self._segments]

    def to_original(self, clean_pos: int) -> int:
        i = max(0, bisect_right(self._clean_starts, clean_pos) - 1)
        clean_start, orig_start, length = self._segments[i]
        offset = min(max(clean_pos - clean_start, 0), length)
        return orig_start + offset

    def to_original_end(self, clean_end: int) -> int:
        # Map the last included character so an exclusive end never jumps a strip.
        if clean_end <= 0:
            return self.to_original(0)
        return self.to_original(clean_end - 1) + 1

    @classmethod
    def identity(cls, length: int) -> "OffsetMap":
        return cls([(0, 0, length)])


def ingest(text: str, fmt: str) -> tuple[str, OffsetMap]:
    """Return (clean_text, offset_map). ``txt`` is treated as plain prose."""
    if fmt == "txt":
        return text, OffsetMap.identity(len(text))

    parts: list[str] = []
    segments: list[tuple[int, int, int]] = []
    clean_pos = orig_pos = 0
    for start, end in _strip_spans(text):
        if start > orig_pos:
            chunk = text[orig_pos:start]
            parts.append(chunk)
            segments.append((clean_pos, orig_pos, len(chunk)))
            clean_pos += len(chunk)
        orig_pos = end
    if orig_pos < len(text):
        chunk = text[orig_pos:]
        parts.append(chunk)
        segments.append((clean_pos, orig_pos, len(chunk)))
    return "".join(parts), OffsetMap(segments)


def _strip_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    frontmatter = _FRONTMATTER.match(text)
    if frontmatter:
        spans.append((frontmatter.start(), frontmatter.end()))
    for pattern in (_FENCED, _SVG):
        spans.extend((m.start(), m.end()) for m in pattern.finditer(text))

    blocked = list(spans)  # don't strip inline backticks that live inside a fence/svg
    for m in _INLINE.finditer(text):
        if not any(a <= m.start() < b for a, b in blocked):
            spans.append((m.start(), m.end()))
    return _merge(spans)


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
