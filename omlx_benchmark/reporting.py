from __future__ import annotations

import csv
import json
from pathlib import Path


SUMMARY_COLUMNS = [
    "Model",
    "Quantization / variant",
    "Type",
    "Baseline speed summary",
    "Tuned speed summary",
    "Chat feel",
    "Instruction following",
    "Code quality",
    "Tool / agent quality",
    "Vision quality",
    "Long-context usefulness",
    "Typical strengths",
    "Typical weaknesses",
    "Best use case",
    "Recommended oMLX settings",
    "Overall verdict",
]


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join([header, separator, *body])
