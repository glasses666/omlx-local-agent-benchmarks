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
    screening = json.loads(screening_path.read_text(encoding="utf-8"))
    tuned_path = args.workspace / "results" / "tuned-summary.json"
    tuned_lookup = {}
    if tuned_path.exists():
        tuned = json.loads(tuned_path.read_text(encoding="utf-8"))
        tuned_lookup = {item["model_id"]: item for item in tuned["summaries"]}

    rows = []
    for item in screening["summaries"]:
        final = tuned_lookup.get(item["model_id"], item)
        dim = final["dimension_scores"]
        rows.append({
            "Model": final["model_id"],
            "Quantization / variant": final["variant"],
            "Type": final["type"],
            "Baseline speed summary": item.get("baseline_speed", "n/a"),
            "Tuned speed summary": final.get("tuned_speed", final.get("baseline_speed", "pending")),
            "Chat feel": dim.get("chat", 0.0),
            "Instruction following": dim.get("instruction", 0.0),
            "Code quality": dim.get("code", 0.0),
            "Tool / agent quality": dim.get("tool", "deferred"),
            "Vision quality": dim.get("vision", "n/a") if final["type"] == "vision" else "n/a",
            "Long-context usefulness": dim.get("long_context", 0.0),
            "Typical strengths": final.get("typical_strengths", "Fast screening candidate" if final["overall_score"] >= 60 else "Needs deeper review"),
            "Typical weaknesses": final.get("typical_weaknesses", "Tool benchmark deferred" if final.get("screening_only") else ""),
            "Best use case": final.get("best_use_case", "screening candidate"),
            "Recommended oMLX settings": final["recommended_settings"],
            "Overall verdict": final["overall_score"],
        })

    write_csv(args.workspace / "results" / "summary-table.csv", rows)
    (args.workspace / "reports" / "summary-table.md").write_text(
        markdown_table(rows, SUMMARY_COLUMNS),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
