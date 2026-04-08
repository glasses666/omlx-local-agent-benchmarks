from __future__ import annotations

import json
from typing import Any

from .core import sort_entries


def render_json(entries: list[dict[str, Any]]) -> str:
    return json.dumps(sort_entries(entries), ensure_ascii=False)
