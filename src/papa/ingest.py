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
# Hugo shortcodes ({{< >}}, {{% %}}), Liquid and Jinja tags ({% %}), and {{ }} variables.
_TEMPLATE = re.compile(r"\{\{[<%].*?[%>]\}\}|\{%.*?%\}|\{\{.*?\}\}", re.DOTALL)
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
    templates = _templates(text, _code_spans(text)) if fmt == "md" else []
    # A "|" inside a Liquid filter is not a table cell boundary.
    for row in _TABLE_ROW.finditer(_mask(text, [t.span() for t in templates], "x")):
        starts += [row.start() + i for i, ch in enumerate(row.group()) if ch == "|"]
    if fmt == "md":
        for tag in templates:
            line_start = text.rfind("\n", 0, tag.start()) + 1
            line_end = text.find("\n", tag.end())
            # Only a tag alone on its line ends a block; one inside a wrapped sentence does not.
            if not text[line_start:tag.start()].strip() and not text[tag.end():line_end if line_end != -1 else None].strip():
                starts += [tag.start(), tag.end()]
    if fmt == "mdx":
        esm = [(m.start(), m.end()) for m in _MDX_IMPORT.finditer(text)]
        tags = _jsx_spans(text, _merge(_code_spans(text) + esm))
    else:
        tags = [m.span() for m in _TAG.finditer(text)]
    for start, end in tags:
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        rest = text[end:line_end if line_end != -1 else None]
        # An {expression} that wraps into prose, like "{name} on your machine", is inline.
        if not text[line_start:start].strip() and (text[start] == "<" or not rest.strip()):
            starts += [start, end]
    return {offset_map.to_clean(pos) for pos in starts}


def _code_spans(text: str) -> list[tuple[int, int]]:
    code: list[tuple[int, int]] = []
    frontmatter = _FRONTMATTER.match(text)
    if frontmatter:
        code.append((frontmatter.start(), frontmatter.end()))
    for pattern in (_FENCED, _SVG):
        code.extend((m.start(), m.end()) for m in pattern.finditer(text))
    blocks = _merge(list(code))  # don't strip inline backticks that live inside a fence/svg
    code += [(m.start(), m.end()) for m in _INLINE.finditer(text) if not _inside(m.start(), blocks)]
    return _merge(code)


def _strip_spans(text: str, fmt: str) -> list[tuple[int, int]]:
    code = _code_spans(text)

    markup: list[tuple[int, int]] = []
    whole = [_COMMENT, _TAG, _LINKED_IMAGE, _IMAGE, _LINK_DEFINITION, _URL, _EMPHASIS,
             _HEADING, _SETEXT, _LIST_ITEM, _QUOTE, _CALLOUT, _RULE, _TABLE_DIVIDER]
    if fmt == "mdx":
        # JSX props hold real JavaScript, so a scanner finds their ends, not a regex.
        whole = [_MDX_IMPORT, *(p for p in whole if p is not _TAG)]
    templates = [m.span() for m in _templates(text, code)] if fmt == "md" else []
    if fmt == "mdx":
        esm = [(m.start(), m.end()) for m in _MDX_IMPORT.finditer(text)]
        markup += _jsx_spans(text, _merge(code + esm))
    # Match the rest on a copy where each template tag is plain filler, so a
    # {{< ref >}} in a link target or a "|" filter in a table cell reads as one token.
    scan = _mask(text, templates, "x")
    for pattern in whole:
        markup += [(m.start(), m.end()) for m in pattern.finditer(scan)]
    markup += templates
    for link in _LINK.finditer(scan):
        markup += [(link.start(), link.start() + 1), (link.start(2) - 1, link.end())]
    for row in _TABLE_ROW.finditer(scan):
        markup += [(row.start() + i, row.start() + i + 1) for i, ch in enumerate(row.group()) if ch == "|"]

    return _merge(code + [span for span in markup if not _inside(span[0], code)])


_TAG_NAME = re.compile(r"</?[A-Za-z$_][\w$.:-]*(?=[\s/>])|<>|</>")


def _jsx_spans(text: str, code: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Spans of JSX tags and {expressions} in MDX, outside code."""
    # Scan a copy with code blanked out, so braces and quotes in code never count.
    text = _mask(text, code, " ")
    spans, i, n = [], 0, len(text)
    while i < n:
        end = -1
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "{":
            end = _brace_end(text, i)
        elif text[i] == "<":
            end = _tag_end(text, i)
        if end == -1:
            i += 1
            continue
        spans.append((i, end))
        i = end
    return spans


def _tag_end(text: str, i: int) -> int:
    name = _TAG_NAME.match(text, i)
    if not name:
        return -1
    if name.group() in ("<>", "</>"):
        return name.end()
    k = name.end()
    while k < len(text):
        ch = text[k]
        if ch == ">":
            return k + 1
        if text.startswith("/>", k):
            return k + 2
        if ch == "<" or text.startswith("\n\n", k):
            return -1
        if ch in "\"'":
            # JSX attribute strings have no escapes: "C:\" ends at its second quote.
            close = text.find(ch, k + 1)
            k = len(text) if close == -1 else close + 1
        elif ch == "{":
            k = _brace_end(text, k)
            if k == -1:
                return -1
        else:
            k += 1
    return -1


def _element_end(text: str, i: int) -> int:
    """End of the JSX element that opens at ``i``, children and closing tag included."""
    end = _tag_end(text, i)
    if end == -1 or text[i + 1] == "/" or text[end - 2:end] == "/>":
        return end
    depth, k = 1, end
    while k < len(text):
        if text[k] == "{":
            close = _brace_end(text, k)
            k = close if close != -1 else k + 1
        elif text[k] == "<" and (tag := _tag_end(text, k)) != -1:
            if text[k + 1] == "/":
                depth -= 1
            elif text[tag - 2:tag] != "/>":
                depth += 1
            k = tag
            if depth == 0:
                return k
        else:
            k += 1
    return -1


def _brace_end(text: str, i: int) -> int:
    depth, k = 0, i
    while k < len(text):
        ch = text[k]
        if ch in "\"'":
            k = _string_end(text, k, stop_at_newline=True)
            continue
        if ch == "`":
            k = _template_literal_end(text, k)
            continue
        if ch == "<" and _TAG_NAME.match(text, k):
            # JSX inside an expression: its text is not JavaScript, so an apostrophe is not a quote.
            end = _element_end(text, k)
            if end != -1:
                k = end
                continue
        if text.startswith("//", k):
            close = text.find("\n", k)
            k = len(text) if close == -1 else close
            continue
        if text.startswith("/*", k):
            close = text.find("*/", k + 2)
            k = len(text) if close == -1 else close + 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    return -1


def _string_end(text: str, i: int, stop_at_newline: bool) -> int:
    quote, k = text[i], i + 1
    while k < len(text):
        if text[k] == "\\":
            k += 2
        elif text[k] == quote:
            return k + 1
        elif text[k] == "\n" and stop_at_newline:
            return k
        else:
            k += 1
    return len(text)


def _template_literal_end(text: str, i: int) -> int:
    k = i + 1
    while k < len(text):
        if text[k] == "\\":
            k += 2
        elif text[k] == "`":
            return k + 1
        elif text.startswith("${", k):
            end = _brace_end(text, k + 1)
            k = len(text) if end == -1 else end
        else:
            k += 1
    return len(text)


def _templates(text: str, code: list[tuple[int, int]]) -> list[re.Match]:
    # Blank out code first, so a literal "{{" in inline code cannot open a match.
    return list(_TEMPLATE.finditer(_mask(text, code, " ")))


def _mask(text: str, spans: list[tuple[int, int]], fill: str) -> str:
    """Replace each span's characters with ``fill``, keeping offsets and newlines."""
    chars = list(text)
    for start, end in spans:
        chars[start:end] = [c if c == "\n" else fill for c in text[start:end]]
    return "".join(chars)


def _inside(pos: int, merged: list[tuple[int, int]]) -> bool:
    i = bisect_right(merged, pos, key=lambda span: span[0]) - 1
    return i >= 0 and pos < merged[i][1]


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
