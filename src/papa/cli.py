"""papa command-line entry point."""

from __future__ import annotations

import argparse
import difflib
import math
import os
import shutil
import sys
from pathlib import Path

from . import __version__, analyze, config, inputs
from .models import Run
from .reporters import REPORTERS

EXAMPLES = """\
Examples:
  papa post.md                         check one file
  papa docs/ --max-grade 10            check a folder, fail above grade 10
  papa 'docs/**/*.md' --exclude 'docs/generated/**'
  cat post.md | papa --stdin-filename post.md
  papa post.md --report concise        file:line:col lines for editors
  papa post.md --report json           findings for scripts and LLMs
  papa post.md --report html -o report.html

Config:
  papa reads [papa] from the nearest papa.toml, or [tool.papa] from
  pyproject.toml. Keys: max-grade, exclude. Flags override config.

Exit codes:
  0  no file failed --max-grade (findings alone never fail a run)
  1  at least one file is harder than --max-grade
  2  usage, config, or input error, or no input had prose to check
     (files with no prose are skipped with a note on stderr)
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        if message.startswith("unrecognized arguments:"):
            message += _suggest(self, message.split(":", 1)[1].split())
        self.exit(2, f"papa: error: {message}\nRun 'papa --help' for examples.\n")


def _suggest(parser: argparse.ArgumentParser, unknown: list[str]) -> str:
    options = [o for action in parser._actions for o in action.option_strings if o.startswith("--")]
    for arg in unknown:
        close = difflib.get_close_matches(arg.split("=")[0], options, n=1)
        if close:
            return f"; did you mean '{close[0]}'?"
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="papa",
        description="Hemingway-style readability linting for Markdown and plain text.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="*", metavar="PATH",
                        help="files, folders, or quoted globs; '-' or a pipe reads stdin")
    parser.add_argument("--report", choices=list(REPORTERS), default="cli",
                        help="output format (default: cli)")
    parser.add_argument("-o", "--output", metavar="FILE", help="write the report to FILE")
    parser.add_argument("--max-grade", type=_grade, metavar="N",
                        help="exit 1 if a file's consensus grade is above N")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="skip paths that match GLOB (repeatable)")
    parser.add_argument("--format", choices=["md", "txt"], help="override format detection")
    parser.add_argument("--stdin-filename", metavar="NAME",
                        help="name to show for stdin; its suffix picks the format")
    parser.add_argument("--summary", action="store_true",
                        help="show grades and counts only, without each finding")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="print nothing to stdout; -o files are still written")
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto",
                        help="color terminal output (default: auto)")
    parser.add_argument("--config", metavar="FILE", help="read settings from FILE")
    parser.add_argument("--no-config", action="store_true", help="ignore papa.toml and pyproject.toml")
    parser.add_argument("--version", action="version", version=f"papa {__version__}")
    return parser


def _grade(value: str) -> float:
    try:
        grade = float(value)
    except ValueError:
        grade = math.nan
    if not math.isfinite(grade) or grade < 0:
        raise argparse.ArgumentTypeError(f"must be a finite number >= 0, got '{value}'")
    return grade


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.summary and args.report != "cli":
        parser.error(f"--summary only works with --report cli, not --report {args.report}")

    if not args.files and sys.stdin.isatty():
        parser.print_help()
        return 0

    try:
        settings = _settings(args)
        paths, input_errors = inputs.expand(args.files or [inputs.STDIN], settings.exclude)
    except (config.ConfigError, inputs.InputError) as error:
        return _fail(str(error))

    run = Run(analyses=[], skipped=[], errors=input_errors, max_grade=settings.max_grade,
              config=_display_path(settings.path) if settings.path else None)
    for path in paths:
        _check_one(path, args, run)

    for path, message in run.errors:
        print(f"papa: {path}: {message}", file=sys.stderr)
    for path, reason in run.skipped:
        print(f"papa: skipped {path}: {reason}", file=sys.stderr)

    if (not args.quiet or args.output) and (run.analyses or args.report in ("json", "html")):
        try:
            _emit(args, run)
        except OSError as error:
            return _fail(f"cannot write {args.output}: {(error.strerror or str(error)).lower()}")

    if run.errors or not run.analyses:
        return 2
    return 1 if any(a.score.verdict == "fail" for a in run.analyses) else 0


def _settings(args: argparse.Namespace) -> config.Config:
    cwd = Path.cwd()
    if args.no_config:
        settings = config.Config()
    else:
        path = Path(args.config) if args.config else config.find(cwd)
        if args.config and not path.is_file():
            raise config.ConfigError(f"config file not found: {args.config}")
        settings = config.load(path) if path else config.Config()

    base = settings.path.parent if settings.path else cwd
    settings.exclude = [inputs.anchor(p, base) for p in settings.exclude]
    settings.exclude += [inputs.anchor(p, cwd) for p in args.exclude]
    if args.max_grade is not None:
        settings.max_grade = args.max_grade
    return settings


def _check_one(path: str, args: argparse.Namespace, run: Run) -> None:
    label = (args.stdin_filename or "<stdin>") if path == inputs.STDIN else path
    try:
        source = _read(path)
    except OSError as error:
        run.errors.append((label, (error.strerror or str(error)).lower()))
        return
    except UnicodeDecodeError as error:
        run.errors.append((label, f"invalid UTF-8 at byte {error.start}; re-save it as UTF-8"))
        return

    if not source.strip():
        reason = "no prose on stdin; pass a file or pipe text" if path == inputs.STDIN else "no prose found"
        run.skipped.append((label, reason))
        return
    analysis = analyze(source, path=label, fmt=_detect_format(label, args.format), max_grade=run.max_grade)
    if not analysis.clean.strip():
        run.skipped.append((label, "no prose found (only code or markup)"))
        return
    run.analyses.append(analysis)


def _read(path: str) -> str:
    if path == inputs.STDIN:
        return sys.stdin.buffer.read().decode("utf-8")
    return Path(path).read_bytes().decode("utf-8")


def _detect_format(path: str, override: str | None) -> str:
    if override:
        return override
    return "txt" if Path(path).suffix.lower() == ".txt" else "md"


def _emit(args: argparse.Namespace, run: Run) -> None:
    to_file = bool(args.output)
    color = args.report == "cli" and not to_file and _color_enabled(args.color)
    width = shutil.get_terminal_size((80, 24)).columns if sys.stdout.isatty() else 80
    rendered = REPORTERS[args.report](run, color=color, width=width, details=not args.summary)
    if to_file:
        Path(args.output).write_text(rendered, encoding="utf-8")
        if not args.quiet:
            print(f"papa: wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(rendered)


def _color_enabled(choice: str) -> bool:
    if choice != "auto":
        return choice == "always"
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _fail(message: str) -> int:
    print(f"papa: {message}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
