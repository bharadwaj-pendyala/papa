"""Reporter registry. Pick one with ``--report``; each renders a whole :class:`Run`."""

from __future__ import annotations

from .cli import render as cli
from .concise import render as concise
from .github import render as github
from .html import render as html
from .json_report import render as json
from .markdown import render as markdown
from .sarif import render as sarif

REPORTERS = {
    "cli": cli, "concise": concise, "json": json, "html": html,
    "sarif": sarif, "github": github, "markdown": markdown,
}
