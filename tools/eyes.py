#!/usr/bin/env python3
"""eyes: let an agent see a CLI the way a user does, then tell it what to fix.

Runs each case from a project config (pipe or real PTY), captures stdout,
stderr, exit code and written files, runs UX checks, diffs reviewed
snapshots, and writes report.json (for agents) and report.txt (for humans).
Optional --browser screenshots HTML output and colored terminal output.

Stdlib only and project-agnostic: project specifics live in the config
(eyes.json) and in plugin files that add checks.

    python tools/eyes.py run [--config tests/ux/eyes.json] [--case ID] [--browser]
    python tools/eyes.py approve (--case ID ... | --all)
    python tools/eyes.py list
"""

from __future__ import annotations

import argparse
import difflib
import html
import importlib.util
import json
import os
import re
import select
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
DEFAULT_NOUNS = ["sentence", "file", "finding", "adverb", "error", "warning", "phrase", "issue", "line"]
CONFIG_CANDIDATES = ["eyes.json", "tests/ux/eyes.json", "tests/eyes/eyes.json"]
CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass
class Result:
    case: dict
    argv: list[str]
    cwd: Path
    out_dir: Path
    exit: int
    stdout_raw: str
    stderr: str
    tty: bool
    cols: int
    seconds: float
    harness_error: str = ""

    @property
    def stdout(self) -> str:
        return ANSI.sub("", self.stdout_raw)


@dataclass
class Check:
    check: str
    status: str
    detail: str = ""
    expected: str | None = None
    actual: str | None = None
    source: str | None = None
    extra: dict = field(default_factory=dict)


class Project:
    def __init__(self, config_path: Path):
        self.config_path = config_path.resolve()
        self.base = self.config_path.parent
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.root = _find_root(self.base)
        self.artifacts = Path(self.expand(self.config.get("artifacts", "{root}/artifacts/eyes")))
        self.snapshots = self.base / self.config.get("snapshots", "snapshots")
        self.sources = self.config.get("sources", {})
        self.nouns = self.config.get("plural_nouns", DEFAULT_NOUNS)
        self.plugins = [_load_plugin(self.base / p) for p in self.config.get("plugins", [])]
        self.timeout = self.config.get("timeout", 30)
        _validate_cases(self.config.get("cases", []))

    def expand(self, value: str, out_dir: Path | None = None) -> str:
        return (
            value.replace("{python}", sys.executable)
            .replace("{root}", str(self.root))
            .replace("{out}", str(out_dir or ""))
        )

    def cases(self, only: list[str] | None = None) -> list[dict]:
        cases = self.config["cases"]
        if not only:
            return cases
        unknown = set(only) - {c["id"] for c in cases}
        if unknown:
            sys.exit(f"eyes: unknown case(s): {', '.join(sorted(unknown))}")
        return [c for c in cases if c["id"] in only]


def _validate_cases(cases: list[dict]) -> None:
    seen = set()
    for case in cases:
        case_id = case.get("id", "")
        if not CASE_ID.fullmatch(case_id):
            sys.exit(f"eyes: case id {case_id!r} must match {CASE_ID.pattern} (it names a folder)")
        if case_id in seen:
            sys.exit(f"eyes: duplicate case id {case_id!r}")
        seen.add(case_id)


def _find_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / ".git").exists():
            return path
    return start


def _load_plugin(path: Path):
    spec = importlib.util.spec_from_file_location(f"eyes_plugin_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- running -----------------------------------------------------------------

def run_case(project: Project, case: dict) -> Result:
    out_dir = project.artifacts / "cases" / case["id"]
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)

    cwd = project.base / project.config.get("cwd", ".") / case.get("cwd", ".")
    command = [project.expand(part) for part in project.config["command"]]
    argv = [project.expand(arg, out_dir) for arg in case.get("argv", [])]
    env = _env(project, case, out_dir)
    stdin = _stdin(cwd, case)
    tty = case.get("tty", False)
    cols = case.get("cols", 80)

    started = time.monotonic()
    harness_error = ""
    try:
        if tty:
            code, stdout, stderr = _run_pty(command + argv, cwd, env, cols, stdin, project.timeout)
        else:
            proc = subprocess.run(
                command + argv, cwd=cwd, env=env, input=stdin if stdin is not None else b"",
                capture_output=True, timeout=project.timeout,
            )
            code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr = -1, error.stdout or b"", error.stderr or b""
        harness_error = f"timed out after {project.timeout}s"
    except OSError as error:
        code, stdout, stderr = -1, b"", b""
        harness_error = f"could not start {command[0]!r}: {error.strerror or error}"
    seconds = time.monotonic() - started

    result = Result(
        case=case, argv=argv, cwd=cwd, out_dir=out_dir, exit=code,
        stdout_raw=stdout.decode("utf-8", "replace"), stderr=stderr.decode("utf-8", "replace"),
        tty=tty, cols=cols, seconds=seconds, harness_error=harness_error,
    )
    (out_dir / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (out_dir / "stdout.ansi").write_text(result.stdout_raw, encoding="utf-8")
    (out_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    return result


def _env(project: Project, case: dict, out_dir: Path) -> dict:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TZ": "UTC",
        "TERM": "xterm-256color",
    }
    for source in (project.config.get("env", {}), case.get("env", {})):
        env.update({k: project.expand(v, out_dir) for k, v in source.items()})
    return env


def _stdin(cwd: Path, case: dict) -> bytes | None:
    if "stdin_file" in case:
        return (cwd / case["stdin_file"]).read_bytes()
    if "stdin" in case:
        return case["stdin"].encode("utf-8")
    return None


def _run_pty(cmd: list[str], cwd: Path, env: dict, cols: int, stdin: bytes | None,
             timeout: float) -> tuple[int, bytes, bytes]:
    import fcntl
    import pty
    import struct
    import termios

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, cols, 0, 0))
    # Given stdin, model `cat file | cmd` in a terminal: a pipe in, a terminal out.
    # Typing into the tty instead would hit the kernel's line limit (1024 bytes on macOS).
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=slave if stdin is None else subprocess.PIPE,
                            stdout=slave, stderr=subprocess.PIPE, close_fds=True)
    os.close(slave)
    stderr_chunks: list[bytes] = []
    drain = threading.Thread(target=lambda: stderr_chunks.append(proc.stderr.read()), daemon=True)
    drain.start()
    if stdin is not None:
        threading.Thread(target=_feed, args=(proc.stdin, stdin), daemon=True).start()

    chunks = []
    deadline = time.monotonic() + timeout
    while True:
        if time.monotonic() >= deadline:
            proc.kill()
            os.close(master)
            raise subprocess.TimeoutExpired(cmd, timeout, b"".join(chunks), b"")
        ready, _, _ = select.select([master], [], [], 0.2)
        if not ready:
            if proc.poll() is not None:
                break
            continue
        try:
            data = os.read(master, 65536)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    os.close(master)
    code = proc.wait(timeout=max(deadline - time.monotonic(), 1))
    drain.join(timeout=5)
    return code, b"".join(chunks).replace(b"\r\n", b"\n"), b"".join(stderr_chunks)


def _feed(pipe, data: bytes) -> None:
    try:
        pipe.write(data)
        pipe.close()
    except OSError:
        pass  # the command exited without reading all of its input


# ---- checks ------------------------------------------------------------------

def generic_checks(project: Project, result: Result) -> list[Check]:
    case = result.case
    src = project.sources
    if result.harness_error:
        return [Check("runs", "fail", result.harness_error, source=src.get("cli"),
                      actual=_tail(result.stderr) or None)]
    checks = [_check_exit(result, src.get("cli"))]
    checks.append(_check_no_traceback(result, src.get("cli")))
    checks.extend(_check_text_expectations(result, src.get("cli")))
    checks.append(_check_ansi(result, src.get("terminal")))
    if _is_terminal_text(result) and case.get("check_width", True):
        checks.append(_check_width(result, src.get("terminal")))
        checks.append(_check_plurals(result, project.nouns, src.get("terminal")))
    if case.get("json"):
        checks.append(_check_json_parses(result, src.get("json")))
    if case.get("html"):
        checks.extend(_check_html(result.out_dir / case["html"], src.get("html")))
        checks.extend(_check_html_contains(result.out_dir / case["html"], case.get("html_contains", []),
                                           src.get("html")))
    return checks


def _check_exit(result: Result, source) -> Check:
    want = result.case.get("exit", 0)
    ok = result.exit == want
    return Check("exit-code", "pass" if ok else "fail", "" if ok else "unexpected exit code",
                 str(want), str(result.exit), source)


def _check_no_traceback(result: Result, source) -> Check:
    leaked = "Traceback (most recent call last)" in result.stderr + result.stdout
    return Check("no-traceback", "fail" if leaked else "pass",
                 "a Python traceback reached the user; catch it and print a one-line error" if leaked else "",
                 source=source, actual=_tail(result.stderr) if leaked else None)


def _check_text_expectations(result: Result, source) -> list[Check]:
    case = result.case
    checks = []
    for stream, text in (("stdout", result.stdout), ("stderr", result.stderr)):
        for needle in case.get(f"{stream}_contains", []):
            ok = needle in text
            checks.append(Check(f"{stream}-contains", "pass" if ok else "fail",
                                "" if ok else f"{stream} is missing expected text",
                                needle, None if ok else _tail(text), source))
        for needle in case.get(f"{stream}_absent", []):
            ok = needle not in text
            checks.append(Check(f"{stream}-absent", "pass" if ok else "fail",
                                "" if ok else f"{stream} contains text that must not appear",
                                f"no {needle!r}", None if ok else _around(text, needle), source))
        for pattern in case.get(f"{stream}_regex", []):
            ok = re.search(pattern, text) is not None
            checks.append(Check(f"{stream}-regex", "pass" if ok else "fail",
                                "" if ok else f"no {stream} line matches the pattern",
                                pattern, None if ok else _tail(text), source))
    if case.get("stdout_empty"):
        ok = result.stdout.strip() == ""
        checks.append(Check("stdout-empty", "pass" if ok else "fail",
                            "" if ok else "stdout must be empty", "", None if ok else _tail(result.stdout), source))
    return checks


def _check_ansi(result: Result, source) -> Check:
    has_ansi = bool(ANSI.search(result.stdout_raw + result.stderr))
    want = result.case.get("expect_ansi", False)
    ok = has_ansi == want
    detail = ""
    if not ok:
        detail = "expected color codes" if want else "color codes leaked into non-color output (pipe or NO_COLOR)"
    return Check("ansi", "pass" if ok else "fail", detail, source=source)


def _is_terminal_text(result: Result) -> bool:
    case = result.case
    return not case.get("json") and not result.stdout.lstrip().startswith(("{", "[", "<"))


def _check_width(result: Result, source) -> Check:
    limit = result.cols
    too_wide = []
    for number, line in enumerate((result.stdout + result.stderr).splitlines(), 1):
        if cells(line) <= limit:
            continue
        if any(len(token) > limit // 2 for token in line.split()):
            continue  # an unbreakable token, such as a long path, is allowed to overflow
        too_wide.append((number, cells(line), line))
    if not too_wide:
        return Check("line-width", "pass", source=source)
    number, width, line = too_wide[0]
    return Check("line-width", "fail",
                 f"{len(too_wide)} line(s) wider than {limit} columns; first is line {number}",
                 f"<= {limit} columns", f"{width} columns: {line}", source,
                 {"artifact_line": number})


def cells(text: str) -> int:
    """Terminal columns used by ``text``: wide CJK and emoji take two, combining marks none."""
    return sum(0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in "WF" else 1
               for ch in text)


def _check_plurals(result: Result, nouns: list[str], source) -> Check:
    text = result.stdout + result.stderr
    words = "|".join(map(re.escape, nouns))
    one_plural = re.search(rf"(?<![\d.])\b1 ({words})s\b", text)
    many_singular = re.search(rf"(?<![\d.])\b(0|[2-9]|[1-9]\d+) ({words})\b(?!s)", text)
    bad = one_plural or many_singular
    if not bad:
        return Check("pluralization", "pass", source=source)
    return Check("pluralization", "fail", "count and noun disagree", None, bad.group(), source,
                 {"artifact_line": text.count("\n", 0, bad.start()) + 1})


def _check_json_parses(result: Result, source) -> Check:
    try:
        json.loads(result.stdout, parse_constant=_reject_constant)
    except ValueError as error:
        return Check("json-parses", "fail", f"stdout is not strict JSON: {error}",
                     source=source, actual=_tail(result.stdout))
    return Check("json-parses", "pass", source=source)


def _reject_constant(name: str):
    raise ValueError(f"non-standard JSON constant {name}")


class _HTMLScan(HTMLParser):
    LOADERS = {"script", "link", "img", "iframe", "object", "embed", "video", "audio", "source"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems: list[str] = []
        self.documents = 0
        self.text: list[str] = []
        self._skip = 0

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.documents += 1

    def handle_starttag(self, tag, attrs):
        if tag in self.LOADERS:
            self.problems.append(f"<{tag}> element loads or runs external content")
        attributes = dict(attrs)
        if tag == "meta" and (attributes.get("http-equiv") or "").lower() == "refresh":
            self.problems.append("<meta http-equiv=refresh> navigates away")
        for name, value in attrs:
            value = value or ""
            if name.startswith("on"):
                self.problems.append(f"<{tag} {name}> runs script")
            if name in ("src", "srcset") or (name == "href" and not value.startswith("#")):
                self.problems.append(f"<{tag} {name}={value!r}> references a resource")
            if name == "style" and ("url(" in value or "@import" in value):
                self.problems.append(f"<{tag} style> loads a resource")
        if tag in ("style", "head"):
            self._skip += 1
        if tag == "br":
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "head"):
            self._skip -= 1
        if tag in ("div", "p", "li", "h1", "h2", "section", "aside", "main", "tr"):
            self.text.append("\n")

    def handle_data(self, data):
        if self._skip:
            if "@import" in data or "url(" in data:
                self.problems.append("inline CSS loads a resource")
            return
        self.text.append(data)


def html_text(path: Path) -> str:
    scan = _HTMLScan()
    scan.feed(path.read_text(encoding="utf-8"))
    lines = [line.strip() for line in "".join(scan.text).splitlines()]
    return "\n".join(line for line in lines if line)


def _check_html(path: Path, source) -> list[Check]:
    if not path.exists():
        return [Check("html-written", "fail", f"{path.name} was not written", source=source)]
    scan = _HTMLScan()
    scan.feed(path.read_text(encoding="utf-8"))
    return [
        Check("html-written", "pass", source=source),
        Check("html-single-document", "pass" if scan.documents == 1 else "fail",
              "" if scan.documents == 1 else "output must be exactly one HTML document",
              "1", str(scan.documents), source),
        Check("html-offline", "fail" if scan.problems else "pass",
              "; ".join(sorted(set(scan.problems))), source=source),
    ]


def _check_html_contains(path: Path, needles: list[str], source) -> list[Check]:
    if not needles or not path.exists():
        return []
    text = html_text(path)
    return [Check("html-contains", "pass" if n in text else "fail",
                  "" if n in text else "visible page text is missing expected text", n, None, source)
            for n in needles]


# ---- snapshots ---------------------------------------------------------------

def snapshot_text(project: Project, result: Result) -> str:
    parts = [f"$ {' '.join(_shell_quote(a) for a in result.argv)}",
             f"[exit {result.exit}{' tty ' + str(result.cols) + ' cols' if result.tty else ''}]",
             "--- stdout", result.stdout.rstrip("\n"), "--- stderr", result.stderr.rstrip("\n")]
    if result.case.get("html"):
        path = result.out_dir / result.case["html"]
        if path.exists():
            parts += [f"--- {result.case['html']} (visible text)", html_text(path)]
    text = "\n".join(parts) + "\n"
    return text.replace(str(result.out_dir), "{out}").replace(str(project.root), "{root}")


def _check_snapshot(project: Project, result: Result, actual: str) -> Check:
    path = project.snapshots / f"{result.case['id']}.txt"
    (result.out_dir / "snapshot.txt").write_text(actual, encoding="utf-8")
    if not path.exists():
        return Check("snapshot", "fail", "new case: no reviewed snapshot yet. Read the output below; "
                     "if it is right, run approve --case " + result.case["id"],
                     "a reviewed snapshot at " + _rel(path), actual[:1500], None,
                     {"artifact": str(result.out_dir / "snapshot.txt")})
    expected = path.read_text(encoding="utf-8")
    if expected == actual:
        return Check("snapshot", "pass")
    diff = "".join(difflib.unified_diff(expected.splitlines(True), actual.splitlines(True),
                                        "snapshot", "actual"))
    (result.out_dir / "snapshot.diff").write_text(diff, encoding="utf-8")
    return Check("snapshot", "fail", "output changed; review the diff, then approve or fix",
                 actual=diff[:1500], extra={"artifact": str(result.out_dir / "snapshot.diff")})


def _shell_quote(arg: str) -> str:
    return arg if re.fullmatch(r"[\w@%+=:,./{}-]+", arg) else "'" + arg.replace("'", "'\\''") + "'"


# ---- browser eyes ------------------------------------------------------------

VIEWPORTS = {"desktop": (1280, 900), "mobile": (390, 844)}

# Runs inside the page. Reports horizontal overflow, low-contrast text (WCAG AA)
# and elements a selector says must carry a hover title.
_INSPECT_JS = """
(titled) => {
  const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
    const p = m[1].split(',').map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) {
    const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) return c; } return {r: 255, g: 255, b: 255, a: 1}; };
  const low = [], seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode() && seen.size < 3000) {
    const node = walker.currentNode, el = node.parentElement;
    if (!node.textContent.trim() || seen.has(el)) continue;
    seen.add(el);
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none') continue;
    const fg = parse(st.color), bg = bgOf(el);
    if (!fg) continue;
    const a = lum(fg), b = lum(bg), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const size = parseFloat(st.fontSize), large = size >= 24 || (size >= 18.66 && parseInt(st.fontWeight) >= 700);
    const need = large ? 3 : 4.5;
    if (ratio < need) low.push(`'${node.textContent.trim().slice(0, 40)}' ratio ${ratio.toFixed(2)} < ${need}`);
  }
  const doc = document.documentElement;
  const clipped = [...document.body.querySelectorAll('*')]
    .filter(e => e.getBoundingClientRect().right > doc.clientWidth + 1 && e.getClientRects().length)
    .map(e => e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : ''));
  return {
    overflow: doc.scrollWidth - doc.clientWidth,
    clipped: [...new Set(clipped)].slice(0, 8),
    low_contrast: low,
    untitled: titled ? [...document.querySelectorAll(titled)].filter(e => !e.title).length : 0,
    text_length: document.body.innerText.trim().length,
  };
}
"""


class PlaywrightEyes:
    """Drives real Chromium: blocks the network, inspects layout, saves screenshots."""

    name = "playwright"

    def __init__(self):
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch()

    def look(self, page_path: Path, png: Path, size: tuple[int, int], titled: str | None) -> dict:
        context = self._browser.new_context(viewport={"width": size[0], "height": size[1]})
        page = context.new_page()
        blocked, errors = [], []

        def route(request_route):
            url = request_route.request.url
            if url.startswith(("file:", "data:", "about:")):
                return request_route.continue_()
            blocked.append(url)
            return request_route.abort()

        page.route("**/*", route)
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(page_path.as_uri(), wait_until="load")
        facts = page.evaluate(_INSPECT_JS, titled)
        page.screenshot(path=str(png), full_page=True)
        context.close()
        return {**facts, "blocked": blocked, "errors": errors, "screenshot": str(png)}

    def close(self):
        self._browser.close()
        self._playwright.stop()


class ChromeEyes:
    """Fallback without Playwright: screenshots only, no in-page inspection."""

    name = "chrome"

    def __init__(self, binary: str):
        self.binary = binary

    def look(self, page_path: Path, png: Path, size: tuple[int, int], titled: str | None) -> dict:
        subprocess.run(
            [self.binary, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--host-resolver-rules=MAP * ~NOTFOUND", f"--window-size={size[0]},{size[1]}",
             f"--screenshot={png}", page_path.as_uri()],
            capture_output=True, timeout=60,
        )
        return {"screenshot": str(png)} if png.exists() else {}

    def close(self):
        pass


def open_eyes() -> tuple[object | None, str]:
    """Return (eyes, why) where ``why`` explains a downgrade, so it is never silent."""
    try:
        return PlaywrightEyes(), ""
    except Exception as error:  # missing package or browser build
        why = f"playwright unavailable ({str(error).splitlines()[0][:160]}); " \
              "fix: pip install playwright && python -m playwright install chromium"
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        if found := shutil.which(name):
            return ChromeEyes(found), why + "; using Chrome screenshots only, no layout checks"
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if Path(mac).exists():
        return ChromeEyes(mac), why + "; using Chrome screenshots only, no layout checks"
    return None, why + "; no Chrome found either"


_ANSI_CSS = {"30": "#555", "31": "#e5534b", "32": "#57ab5a", "33": "#c69026", "34": "#539bf5",
             "35": "#b083f0", "36": "#39c5cf", "37": "#ccc", "90": "#8b949e"}


def ansi_to_html(text: str, cols: int) -> str:
    out, open_spans = [], 0
    for piece in re.split(r"(\x1b\[[0-9;]*m)", text):
        match = re.fullmatch(r"\x1b\[([0-9;]*)m", piece)
        if not match:
            out.append(html.escape(piece))
            continue
        codes = match.group(1).split(";")
        if codes in (["0"], [""]):
            out.append("</span>" * open_spans)
            open_spans = 0
            continue
        style = ";".join("font-weight:bold" if c == "1" else f"color:{_ANSI_CSS[c]}"
                         for c in codes if c == "1" or c in _ANSI_CSS)
        out.append(f'<span style="{style}">')
        open_spans += 1
    out.append("</span>" * open_spans)
    return (f"<!doctype html><meta charset=utf-8><body style='margin:0;background:#0d1117'>"
            f"<pre style='margin:0;padding:12px;color:#c9d1d9;font:14px/1.4 Menlo,monospace;"
            f"width:{cols}ch'>{''.join(out)}</pre>")


def browser_checks(eyes, why: str, project: Project, result: Result) -> list[Check]:
    if not result.case.get("html") and not result.tty:
        return []
    if eyes is None:
        return [Check("browser-engine", "fail", f"--browser was requested but nothing can render: {why}")]
    checks = [Check("browser-engine", "skip", why)] if why else []
    shots = []
    source = project.sources.get("html")
    page = result.out_dir / result.case["html"] if result.case.get("html") else None
    if page and page.exists():
        for label, size in VIEWPORTS.items():
            facts = eyes.look(page, result.out_dir / f"html-{label}.png", size, project.config.get("titled"))
            shots += [facts["screenshot"]] if "screenshot" in facts else []
            checks += _page_checks(facts, label, size, source)
    if result.tty:
        page = result.out_dir / "terminal.html"
        page.write_text(ansi_to_html(result.stdout_raw, result.cols), encoding="utf-8")
        facts = eyes.look(page, result.out_dir / "terminal.png", (result.cols * 9 + 40, 600), None)
        shots += [facts["screenshot"]] if "screenshot" in facts else []
    expected = 2 * bool(result.case.get("html")) + bool(result.tty)
    if len(shots) < expected:
        checks.append(Check("screenshots", "fail", f"{eyes.name} saved {len(shots)} of {expected} screenshots"))
    if shots:
        checks.append(Check("screenshots", "pass", f"open these images to see the output ({eyes.name})",
                            extra={"screenshots": shots}))
    return checks


def _page_checks(facts: dict, label: str, size: tuple[int, int], source) -> list[Check]:
    if "overflow" not in facts:
        return []
    shot = {"artifact": facts.get("screenshot")}
    return [
        Check(f"browser-{label}-network", "fail" if facts["blocked"] else "pass",
              "page tried to load: " + ", ".join(facts["blocked"][:5]) if facts["blocked"] else "", source=source),
        Check(f"browser-{label}-overflow", "fail" if facts["overflow"] > 0 or facts["clipped"] else "pass",
              f"content is wider than {size[0]}px (scrolls by {facts['overflow']}px); "
              f"elements past the right edge: {', '.join(facts['clipped']) or 'none'}"
              if facts["overflow"] > 0 or facts["clipped"] else "",
              source=source, extra=shot),
        Check(f"browser-{label}-console", "fail" if facts["errors"] else "pass",
              "; ".join(facts["errors"][:5]), source=source),
        Check(f"browser-{label}-contrast", "fail" if facts["low_contrast"] else "pass",
              f"{len(facts['low_contrast'])} text element(s) below WCAG AA contrast",
              actual="\n".join(facts["low_contrast"][:8]) or None, source=source),
        Check(f"browser-{label}-titles", "fail" if facts["untitled"] else "pass",
              f"{facts['untitled']} highlighted element(s) have no hover title" if facts["untitled"] else "",
              source=source),
        Check(f"browser-{label}-visible-text", "pass" if facts["text_length"] > 0 else "fail",
              "" if facts["text_length"] else "page shows no text", source=source, extra=shot),
    ]


# ---- report ------------------------------------------------------------------

def run(project: Project, only: list[str] | None, browser_wanted: bool) -> int:
    eyes, why = open_eyes() if browser_wanted else (None, "")
    rows = []
    for case in project.cases(only):
        result = run_case(project, case)
        checks = generic_checks(project, result)
        for plugin in project.plugins:
            checks.extend(plugin.checks(result, project))
        checks.append(_check_snapshot(project, result, snapshot_text(project, result)))
        if browser_wanted:
            try:
                checks.extend(browser_checks(eyes, why, project, result))
            except Exception as error:  # one broken page must not lose the whole report
                checks.append(Check("browser-engine", "fail", f"browser crashed: {str(error)[:300]}"))
        for check in checks:
            row = {"case": case["id"], **{k: v for k, v in vars(check).items() if v not in (None, "", {})}}
            if check.status == "fail":
                row["reproduce"] = _reproduce(project, result)
                row["artifacts"] = _rel(result.out_dir)
            rows.append(row)
    if eyes:
        eyes.close()
    return _write_report(project, rows)


def _reproduce(project: Project, result: Result) -> dict:
    case = result.case
    command = [project.expand(part) for part in project.config["command"]] + result.argv
    env = {k: project.expand(v, result.out_dir)
           for source in (project.config.get("env", {}), case.get("env", {})) for k, v in source.items()}
    line = " ".join([*(f"{k}={_shell_quote(v)}" for k, v in env.items()), *(_shell_quote(a) for a in command)])
    if "stdin_file" in case:
        line += f" < {_shell_quote(case['stdin_file'])}"
    elif "stdin" in case:
        line = f"printf '%s' {_shell_quote(case['stdin'])} | {line}"
    elif not result.tty:
        line += " < /dev/null"
    return {
        "shell": f"cd {_shell_quote(str(result.cwd))} && {line}",
        "note": f"run this in a real terminal {result.cols} columns wide" if result.tty else None,
        "timeout": project.timeout,
    }


def _write_report(project: Project, rows: list[dict]) -> int:
    evaluated = [r for r in rows if r["status"] != "skip"]
    failures = [r for r in rows if r["status"] == "fail"]
    score = round(100 * (len(evaluated) - len(failures)) / max(len(evaluated), 1), 1)
    summary = {
        "score": score,
        "checks": len(evaluated),
        "failed": len(failures),
        "skipped": len(rows) - len(evaluated),
        "cases": len({r["case"] for r in rows}),
        "failing_cases": sorted({r["case"] for r in failures}),
        "screenshots": [s for r in rows for s in r.get("extra", {}).get("screenshots", [])],
    }
    report = {"summary": summary, "failures": failures, "checks": rows}
    project.artifacts.mkdir(parents=True, exist_ok=True)
    (project.artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [f"eyes: {summary['cases']} cases, {summary['checks']} checks, "
             f"{summary['failed']} failed, {summary['skipped']} skipped, score {score}"]
    for row in failures:
        lines.append(f"\nFAIL {row['case']} :: {row['check']}"
                     + (f"  ({row['source']})" if row.get("source") else ""))
        if row.get("detail"):
            lines.append(f"  {row['detail']}")
        if row.get("expected") is not None:
            lines.append(f"  expected: {row['expected']}")
        if row.get("actual"):
            lines.append("  actual:   " + row["actual"].replace("\n", "\n            "))
    if summary["screenshots"]:
        lines.append("\nscreenshots:")
        lines += [f"  {s}" for s in summary["screenshots"]]
    lines.append(f"\nfull report: {project.artifacts / 'report.json'}")
    text = "\n".join(lines) + "\n"
    (project.artifacts / "report.txt").write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 1 if failures else 0


def approve(project: Project, only: list[str] | None) -> int:
    """Accept the output that `run` captured and you inspected; never rerun."""
    project.snapshots.mkdir(parents=True, exist_ok=True)
    missing = []
    for case in project.cases(only):
        captured = project.artifacts / "cases" / case["id"] / "snapshot.txt"
        if not captured.exists():
            missing.append(case["id"])
            continue
        target = project.snapshots / f"{case['id']}.txt"
        shutil.copyfile(captured, target)
        print(f"approved {_rel(target)}")
    if missing:
        print(f"eyes: no captured run for {', '.join(missing)}; run them first", file=sys.stderr)
        return 1
    return 0


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _tail(text: str, limit: int = 600) -> str:
    return text if len(text) <= limit else "…" + text[-limit:]


def _around(text: str, needle: str, radius: int = 120) -> str:
    i = text.find(needle)
    return text[max(0, i - radius): i + len(needle) + radius]


def _find_config(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    for candidate in CONFIG_CANDIDATES:
        if Path(candidate).exists():
            return Path(candidate)
    sys.exit("eyes: no config found; pass --config PATH (looked for " + ", ".join(CONFIG_CANDIDATES) + ")")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eyes", description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", help="path to eyes.json")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run cases, check them, and write the report")
    run_p.add_argument("--case", action="append", help="run only this case (repeatable)")
    run_p.add_argument("--browser", action="store_true", help="screenshot HTML and terminal output")
    approve_p = sub.add_parser("approve", help="accept current output as the reviewed snapshot")
    group = approve_p.add_mutually_exclusive_group(required=True)
    group.add_argument("--case", action="append")
    group.add_argument("--all", action="store_true")
    sub.add_parser("list", help="list case ids")
    args = parser.parse_args(argv)

    project = Project(_find_config(args.config))
    if args.command == "list":
        for case in project.cases():
            print(case["id"])
        return 0
    if args.command == "approve":
        return approve(project, None if args.all else args.case)
    return run(project, args.case, args.browser)


if __name__ == "__main__":
    sys.exit(main())
