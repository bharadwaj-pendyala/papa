"""Format-aware ingestion with a map back to the original source (spec §6).

Strips non-prose from Markdown and MDX so analyzers see prose only: frontmatter,
code, SVG, HTML/JSX tags, MDX imports, link and image syntax, URLs, emphasis,
and block markers for headings, lists, quotes and tables. An :class:`OffsetMap`
maps every finding back to original source offsets. Stripped regions are
removed (clean text is shorter), so the map does real translation work.

Removing a list marker or a table pipe also removes the boundary a reader sees,
so :func:`block_breaks` reports where one block ends and the next begins.
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

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_BRACES = r"\{(?:[^{}]|\{[^{}]*\})*\}"  # two levels: icon={<img width={20} />}
_TAG = re.compile(rf"</?[A-Za-z][\w.:-]*(?:\s(?:[^<>{{}}]|{_BRACES})*)?/?>", re.DOTALL)
_MDX_IMPORT = re.compile(r"^(?:import|export)\b.*?(?:;[ \t]*$|\n[ \t]*\n|\Z)", re.DOTALL | re.MULTILINE)
_MDX_EXPRESSION = re.compile(_BRACES)
_LINKED_IMAGE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
# A label may wrap onto the next line, but never across a blank line (a new paragraph).
_LINK = re.compile(r"\[((?:[^\]\n]|\n(?![ \t]*\n))*)\](\([^)\s]*(?:\s+\"[^\"]*\")?\))")
_LINK_DEFINITION = re.compile(r"^[ \t]{0,3}\[[^\]]+\]:[ \t]*\S.*$", re.MULTILINE)
_URL = re.compile(r"https?://[^\s)>\]]+")
_EMPHASIS = re.compile(r"\*\*|__|~~|(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])|(?<!\w)_(?=\S)|(?<=\S)_(?!\w)")
_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.MULTILINE)
_SETEXT = re.compile(r"^[ \t]{0,3}(?:=+|-+)[ \t]*$", re.MULTILINE)
_LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+(?:\[[ xX]\][ \t]+)?", re.MULTILINE)
_QUOTE = re.compile(r"^[ \t]{0,3}(?:>[ \t]?)+", re.MULTILINE)
_CALLOUT = re.compile(r"^[ \t]*:::[\w-]*", re.MULTILINE)  # Docusaurus-style :::info ... :::
_RULE = re.compile(r"^[ \t]{0,3}(?:[-*_][ \t]*){3,}$", re.MULTILINE)
_TABLE_ROW = re.compile(r"^[ \t]*\|.*$", re.MULTILINE)
_TABLE_DIVIDER = re.compile(r"^[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)+\|?[ \t]*$", re.MULTILINE)


class OffsetMap:
    """Maps a position in the cleaned text back to the original source."""

    def __init__(self, segments: list[tuple[int, int, int]]):
        # Each segment is (clean_start, orig_start, length), contiguous in clean space.
        self._segments = segments or [(0, 0, 0)]
        self._clean_starts = [seg[0] for seg in self._segments]
        self._orig_starts = [seg[1] for seg in self._segments]

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

    def to_clean(self, orig_pos: int) -> int:
        """Clean position of ``orig_pos``; a stripped position maps to where the next text starts."""
        i = max(0, bisect_right(self._orig_starts, orig_pos) - 1)
        clean_start, orig_start, length = self._segments[i]
        if orig_pos < orig_start + length:
            return clean_start + max(orig_pos - orig_start, 0)
        return clean_start + length

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
    for start, end in _strip_spans(text, fmt):
        if start > orig_pos:
            chunk = text[orig_pos:start]
            parts.append(chunk)
            segments.append((clean_pos, orig_pos, len(chunk)))
            clean_pos += len(chunk)
        orig_pos = max(orig_pos, end)
    if orig_pos < len(text):
        chunk = text[orig_pos:]
        parts.append(chunk)
        segments.append((clean_pos, orig_pos, len(chunk)))
    return "".join(parts), OffsetMap(segments)


def block_breaks(text: str, fmt: str, offset_map: OffsetMap) -> set[int]:
    """Clean-text positions where a new block starts: a list item, a heading,
    a table cell, or a tag on its own line. Sentences never span these."""
    if fmt == "txt":
        return set()
    starts = [m.start() for pattern in (_LIST_ITEM, _CALLOUT) for m in pattern.finditer(text)]
    for heading in _HEADING.finditer(text):
        line_end = text.find("\n", heading.end())
        starts += [heading.start(), line_end if line_end != -1 else len(text)]
    for row in _TABLE_ROW.finditer(text):
        starts += [row.start() + i for i, ch in enumerate(row.group()) if ch == "|"]
    for tag in _TAG.finditer(text):
        line_start = text.rfind("\n", 0, tag.start()) + 1
        if not text[line_start:tag.start()].strip():
            starts += [tag.start(), tag.end()]
    return {offset_map.to_clean(pos) for pos in starts}


def _strip_spans(text: str, fmt: str) -> list[tuple[int, int]]:
    code: list[tuple[int, int]] = []
    frontmatter = _FRONTMATTER.match(text)
    if frontmatter:
        code.append((frontmatter.start(), frontmatter.end()))
    for pattern in (_FENCED, _SVG):
        code.extend((m.start(), m.end()) for m in pattern.finditer(text))
    blocks = list(code)  # don't strip inline backticks that live inside a fence/svg
    code += [(m.start(), m.end()) for m in _INLINE.finditer(text) if not _inside(m.start(), blocks)]

    markup: list[tuple[int, int]] = []
    whole = [_COMMENT, _TAG, _LINKED_IMAGE, _IMAGE, _LINK_DEFINITION, _URL, _EMPHASIS,
             _HEADING, _SETEXT, _LIST_ITEM, _QUOTE, _CALLOUT, _RULE, _TABLE_DIVIDER]
    if fmt == "mdx":
        whole = [_MDX_IMPORT, _MDX_EXPRESSION, *whole]
    for pattern in whole:
        markup += [(m.start(), m.end()) for m in pattern.finditer(text)]
    for link in _LINK.finditer(text):
        markup += [(link.start(), link.start() + 1), (link.start(2) - 1, link.end())]
    for row in _TABLE_ROW.finditer(text):
        markup += [(row.start() + i, row.start() + i + 1) for i, ch in enumerate(row.group()) if ch == "|"]

    return _merge(code + [span for span in markup if not _inside(span[0], code)])


def _inside(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
