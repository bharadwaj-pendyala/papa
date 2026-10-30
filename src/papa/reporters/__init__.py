"""Reporter registry. Pick one with ``--report``; each renders a whole :class:`Run`."""

from __future__ import annotations

from .cli import render as cli
from .concise import render as concise
from .html import render as html
from .json_report import render as json

REPORTERS = {"cli": cli, "concise": concise, "json": json, "html": html}
