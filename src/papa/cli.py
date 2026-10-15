"""papa command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from . import __version__, analyze
from .reporters import REPORTERS
from .reporters.json_report import payload

ISSUES_URL = "https://github.com/bharadwaj-pendyala/papa/issues"

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_INTERNAL = 0, 1, 2, 3

EPILOG = """\
exit codes:
  0  every file passed (or no --max-grade was set)
  1  a file is harder than --max-grade
  2  usage or file error (bad option, missing or unreadable file)
  3  internal error in papa (set PAPA_DEBUG=1 for a traceback)
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="papa",
        description="Hemingway-grade readability for prose.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    try:
        return _run(args)
    except Exception as error:
        return _internal_error(error)


def _run(args: argparse.Namespace) -> int:
    analyses = []
    for path in args.files:
        try:
            source = _read(path)
        except OSError as error:
            print(f"papa: cannot read {path}: {error}", file=sys.stderr)
            return EXIT_USAGE
        fmt = _detect_format(path, args.format)
        analyses.append(analyze(source, path=path, fmt=fmt, max_grade=args.max_grade))

    color = _color_enabled(args.report, bool(args.output))
    rendered = _render(args.report, analyses, color)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    return EXIT_FAIL if any(a.score.verdict == "fail" for a in analyses) else EXIT_PASS


def _internal_error(error: Exception) -> int:
    if os.environ.get("PAPA_DEBUG") == "1":
        traceback.print_exc()
    print(f"papa: internal error: {type(error).__name__}: {error}", file=sys.stderr)
    print(f"papa: this is a bug, please report it at {ISSUES_URL}", file=sys.stderr)
    return EXIT_INTERNAL


def _read(path: str) -> str:
    # newline="" keeps CRLF intact so finding offsets index the bytes on disk.
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


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
