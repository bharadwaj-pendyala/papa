"""papa command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__, analyze
from .reporters import REPORTERS
from .reporters.json_report import payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="papa", description="Hemingway-grade readability for prose."
    )
    parser.add_argument("files", nargs="+", help="prose file(s): .md or .txt")
    parser.add_argument(
        "--report", choices=list(REPORTERS), default="cli",
        help="output format (default: cli)",
    )
    parser.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    parser.add_argument(
        "--max-grade", type=float, metavar="N",
        help="exit 1 if the consensus grade is harder than N",
    )
    parser.add_argument("--format", choices=["md", "txt"], help="override format detection")
    parser.add_argument("--version", action="version", version=f"papa {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    analyses = []
    for path in args.files:
        try:
            source = Path(path).read_text(encoding="utf-8")
        except OSError as error:
            print(f"papa: cannot read {path}: {error}", file=sys.stderr)
            return 2
        fmt = _detect_format(path, args.format)
        analyses.append(analyze(source, path=path, fmt=fmt, max_grade=args.max_grade))

    color = _color_enabled(args.report, bool(args.output))
    rendered = _render(args.report, analyses, color)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    return 1 if any(a.score.verdict == "fail" for a in analyses) else 0


def _detect_format(path: str, override: str | None) -> str:
    if override:
        return override
    return "txt" if Path(path).suffix.lower() == ".txt" else "md"


def _color_enabled(report: str, to_file: bool) -> bool:
    return (
        report == "cli"
        and not to_file
        and sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
    )


def _render(report: str, analyses: list, color: bool) -> str:
    if report == "json":
        data = payload(analyses[0]) if len(analyses) == 1 else [payload(a) for a in analyses]
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    render = REPORTERS[report]
    return "\n".join(render(a, color=color) for a in analyses)


if __name__ == "__main__":
    sys.exit(main())
