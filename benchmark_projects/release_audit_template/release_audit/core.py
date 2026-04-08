from __future__ import annotations

from typing import Any


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda item: (item["component"].lower(), item["title"].lower()))


def summarize_entries(entries: list[dict[str, Any]]) -> str:
    lines = []
    for entry in sort_entries(entries):
        lines.append(f"- [{entry['channel']}] S{entry['severity']} {entry['component']}: {entry['title']}")
    return "\n".join(lines)
