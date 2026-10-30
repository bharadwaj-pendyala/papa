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
        if pyproject.is_file() and "papa" in _read(pyproject).get("tool", {}):
            return pyproject
        if (directory / ".git").exists():
            return None
    return None


def load(path: Path) -> Config:
    data = _read(path)
    table = data.get("tool", {}).get("papa", {}) if path.name == "pyproject.toml" else data.get("papa", {})
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
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ConfigError(f"{label} must be a finite number >= 0, got {value!r}")
    return float(value)


def _read(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: invalid TOML: {error}") from None
