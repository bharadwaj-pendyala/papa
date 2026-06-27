"""Reporter registry. Pick one with ``--report``; all render from one Analysis."""

from __future__ import annotations

from .cli import render as cli
from .html import render as html
from .json_report import render as json

REPORTERS = {"cli": cli, "json": json, "html": html}
