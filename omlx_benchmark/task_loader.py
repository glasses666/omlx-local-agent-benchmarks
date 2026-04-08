from __future__ import annotations

import json
from pathlib import Path


def load_task_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_suite_tasks(path: Path, stage: str) -> dict[str, list[dict]]:
    payload = load_task_payload(path)
    return payload[stage]
