from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_issues(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(issues, key=lambda item: item["title"].lower())


def summarize_issues(issues: list[dict[str, Any]]) -> str:
    lines = []
    for issue in sort_issues(issues):
        lines.append(f"- [{issue['status']}] P{issue['priority']} {issue['title']}")
    return "\n".join(lines)


def export_issues(issues: list[dict[str, Any]]) -> str:
    return json.dumps(sort_issues(issues), ensure_ascii=False)

