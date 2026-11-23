"""MCP server: lets an agent grade a draft, rewrite what papa flags, and grade it again.

Run it with ``papa-mcp`` after ``pip install 'papa-lint[mcp]'``. Both tools return
the same JSON as ``papa --report json`` (docs/llm-contract.md).
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, analyze, config, inputs
from .cli import _detect_format
from .models import Run
from .reporters.json_report import payload

DEFAULT_MAX_GRADE = 10.0

INSTRUCTIONS = """\
papa grades prose like the Hemingway editor. The grade is a US school grade:
under 10 is easy to read. Without a max_grade from the user or papa.toml, the
tools grade against 10. To improve a draft:
1. Call grade_text or grade_files.
2. Fix the findings, most severe first: very-hard-sentence, hard-sentence,
   passive, complex-phrase, adverb. Each finding has a hint.
3. Grade again. Stop when the verdict is "pass" or the findings stop changing.
Keep the meaning, facts, code, and links the same while you rewrite."""

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

server = MCPServer("papa", instructions=INSTRUCTIONS, version=__version__)


@server.tool(annotations=READ_ONLY)
def grade_text(text: str, filename: str = "draft.md", max_grade: float | None = None) -> dict:
    """Grade the readability of Markdown or plain text and list each hard sentence,
    passive verb, adverb, and complex phrase with its line, column, and a fix hint.

    filename only picks the format: .md, .mdx, or .txt. max_grade defaults to 10.
    """
    max_grade = DEFAULT_MAX_GRADE if max_grade is None else max_grade
    run = Run(analyses=[], skipped=[], errors=[], max_grade=max_grade)
    analysis = analyze(text, path=filename, fmt=_detect_format(filename, None), max_grade=max_grade)
    if analysis.clean.strip():
        run.analyses.append(analysis)
    else:
        run.skipped.append((filename, "no prose found (only code or markup)"))
    return payload(run)


@server.tool(annotations=READ_ONLY)
def grade_files(paths: list[str], max_grade: float | None = None) -> dict:
    """Grade Markdown and text files, folders, or globs, like the papa CLI.

    Uses max-grade and exclude from the nearest papa.toml or pyproject.toml.
    max_grade overrides the config. Without either, the max grade is 10.
    """
    found = config.find(Path.cwd())
    settings = config.load(found) if found else config.Config()
    base = settings.path.parent if settings.path else Path.cwd()
    excludes = [inputs.anchor(pattern, base) for pattern in settings.exclude]
    if max_grade is not None:
        settings.max_grade = max_grade
    elif settings.max_grade is None:
        settings.max_grade = DEFAULT_MAX_GRADE

    try:
        files, errors = inputs.expand([p for p in paths if p != inputs.STDIN], excludes)
    except inputs.InputError as error:
        files, errors = [], [(", ".join(paths), str(error))]
    run = Run(analyses=[], skipped=[], errors=errors, max_grade=settings.max_grade)
    for path in files:
        _grade_file(path, run)
    return payload(run)


def _grade_file(path: str, run: Run) -> None:
    try:
        source = Path(path).read_bytes().decode("utf-8")
    except OSError as error:
        run.errors.append((path, (error.strerror or str(error)).lower()))
        return
    except UnicodeDecodeError as error:
        run.errors.append((path, f"invalid UTF-8 at byte {error.start}; re-save it as UTF-8"))
        return
    analysis = analyze(source, path=path, fmt=_detect_format(path, None), max_grade=run.max_grade)
    if analysis.clean.strip():
        run.analyses.append(analysis)
    else:
        run.skipped.append((path, "no prose found"))


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
