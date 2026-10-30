"""Project config: ``papa.toml`` (``[papa]``) or ``pyproject.toml`` (``[tool.papa]``)."""

from __future__ import annotations

import difflib
import math
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

KEYS = {"max-grade", "exclude"}


class ConfigError(Exception):
    pass


@dataclass
class Config:
    path: Path | None = None
    max_grade: float | None = None
    exclude: list[str] = field(default_factory=list)


def find(start: Path) -> Path | None:
    """Nearest papa.toml, or pyproject.toml with [tool.papa], up to the repo root."""
    for directory in [start, *start.parents]:
        candidate = directory / "papa.toml"
        if candidate.is_file():
            return candidate
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            tool = _read(pyproject).get("tool")
            if isinstance(tool, dict) and "papa" in tool:
                return pyproject
        if (directory / ".git").exists():
            return None
    return None


def load(path: Path) -> Config:
    data = _read(path)
    if path.name == "pyproject.toml":
        tool = data.get("tool", {})
        table = tool.get("papa", {}) if isinstance(tool, dict) else {}
        section = "[tool.papa]"
    else:
        table, section = data.get("papa", {}), "[papa]"
    if not isinstance(table, dict):
        raise ConfigError(f"{path}: {section} must be a table, like:\n\n  {section}\n  max-grade = 10")
    for key in table:
        if key not in KEYS:
            close = difflib.get_close_matches(key, KEYS, n=1)
            hint = f"; did you mean '{close[0]}'?" if close else f"; valid keys: {', '.join(sorted(KEYS))}"
            raise ConfigError(f"{path}: unknown key '{key}'{hint}")

    config = Config(path=path)
    if "max-grade" in table:
        config.max_grade = check_grade(table["max-grade"], f"{path}: max-grade")
    exclude = table.get("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(p, str) for p in exclude):
        raise ConfigError(f"{path}: exclude must be a list of glob strings")
    config.exclude = exclude
    return config


def check_grade(value, label: str) -> float:
    try:
        grade = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else math.nan
    except OverflowError:
        grade = math.inf
    if not math.isfinite(grade) or grade < 0:
        raise ConfigError(f"{label} must be a finite number >= 0, got {str(value)[:20]!r}")
    return grade


def _read(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_bytes().decode("utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read config {path}: {(error.strerror or str(error)).lower()}") from None
    except UnicodeDecodeError as error:
        raise ConfigError(f"cannot read config {path}: invalid UTF-8 at byte {error.start}") from None
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: invalid TOML: {error}") from None
