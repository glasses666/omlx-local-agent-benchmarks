from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_entries(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
