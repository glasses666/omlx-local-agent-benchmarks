from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VALID_STATUSES = {"open", "closed", "all"}


def load_issues(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(issues, key=lambda item: (-int(item["priority"]), str(item["title"]).lower()))


def filter_issues(issues: list[dict[str, Any]], status: str = "all") -> list[dict[str, Any]]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported status: {status}")
    if status == "all":
        return list(issues)
    return [issue for issue in issues if issue["status"] == status]


def summarize_issues(issues: list[dict[str, Any]], status: str = "all") -> str:
    lines = []
    for issue in sort_issues(filter_issues(issues, status=status)):
        lines.append(f"- [{issue['status']}] P{issue['priority']} {issue['title']}")
    return "\n".join(lines)


def export_issues(issues: list[dict[str, Any]], status: str = "all") -> str:
    filtered = sort_issues(filter_issues(issues, status=status))
    return json.dumps(filtered, ensure_ascii=False)

