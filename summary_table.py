from __future__ import annotations

import argparse
import json
from pathlib import Path

from omlx_benchmark.reporting import SUMMARY_COLUMNS, markdown_table, write_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate final summary table artifacts.")
    parser.add_argument("--workspace", default=Path(__file__).resolve().parent, type=Path)
    args = parser.parse_args()

    screening_path = args.workspace / "results" / "screening-summary.json"
    if not screening_path.exists():
        raise SystemExit("Missing screening-summary.json")
    payload = json.loads(screening_path.read_text(encoding="utf-8"))

    rows = []
    for item in payload["summaries"]:
        dim = item["dimension_scores"]
        rows.append({
            "Model": item["model_id"],
            "Quantization / variant": item["variant"],
            "Type": item["type"],
            "Baseline speed summary": item["baseline_speed"],
            "Tuned speed summary": "pending",
            "Chat feel": dim.get("chat", 0.0),
            "Instruction following": dim.get("instruction", 0.0),
            "Code quality": dim.get("code", 0.0),
            "Tool / agent quality": dim.get("tool", "deferred"),
            "Vision quality": dim.get("vision", "n/a") if item["type"] == "vision" else "n/a",
            "Long-context usefulness": dim.get("long_context", 0.0),
            "Typical strengths": "Fast screening candidate" if item["overall_score"] >= 60 else "Needs deeper review",
            "Typical weaknesses": "Tool benchmark deferred" if item.get("screening_only") else "",
            "Best use case": "screening candidate",
            "Recommended oMLX settings": item["recommended_settings"],
            "Overall verdict": item["overall_score"],
        })

    write_csv(args.workspace / "results" / "summary-table.csv", rows)
    (args.workspace / "reports" / "summary-table.md").write_text(
        markdown_table(rows, SUMMARY_COLUMNS),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
