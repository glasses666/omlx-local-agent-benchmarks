from __future__ import annotations

from typing import Any


def filter_entries(entries: list[dict[str, Any]], channel: str | None = None) -> list[dict[str, Any]]:
    if not channel or channel == "all":
        return list(entries)
    return [entry for entry in entries if entry["channel"] == channel]


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        entries,
        key=lambda item: (-int(item["severity"]), item["component"].lower(), item["title"].lower()),
    )


def summarize_entries(entries: list[dict[str, Any]], channel: str | None = None) -> str:
    lines = []
    for entry in sort_entries(filter_entries(entries, channel)):
        lines.append(f"- [{entry['channel']}] S{entry['severity']} {entry['component']}: {entry['title']}")
    return "\n".join(lines)
