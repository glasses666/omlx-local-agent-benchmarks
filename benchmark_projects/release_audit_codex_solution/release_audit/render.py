from __future__ import annotations

import json
from typing import Any

from .core import filter_entries, sort_entries


def render_json(entries: list[dict[str, Any]], channel: str | None = None) -> str:
    return json.dumps(sort_entries(filter_entries(entries, channel)), ensure_ascii=False)
