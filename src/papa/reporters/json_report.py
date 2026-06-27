"""JSON report — the LLM contract (spec §6, §8). Stable, versioned shape."""

from __future__ import annotations

import json

from ..models import Analysis

SCHEMA_VERSION = "0.1"


def payload(analysis: Analysis) -> dict:
    return {
        "version": SCHEMA_VERSION,
        "file": analysis.path,
        "score": analysis.score.to_dict(),
        "findings": [f.to_dict() for f in analysis.findings],
    }


def render(analysis: Analysis, *, color: bool = False) -> str:
    return json.dumps(payload(analysis), indent=2, ensure_ascii=False)
