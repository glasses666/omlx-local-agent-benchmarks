from __future__ import annotations

import argparse
import json
from pathlib import Path

from omlx_benchmark.reporting import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-emit score-focused screening summary.")
    parser.add_argument("--workspace", default=Path(__file__).resolve().parent, type=Path)
    args = parser.parse_args()

    screening_path = args.workspace / "results" / "screening-summary.json"
    if not screening_path.exists():
        raise SystemExit("Missing screening-summary.json")

    payload = json.loads(screening_path.read_text(encoding="utf-8"))
    score_rows = []
    for item in payload["summaries"]:
        row = {
            "model_id": item["model_id"],
            "overall_score": item["overall_score"],
            **item["dimension_scores"],
        }
        score_rows.append(row)
    write_json(args.workspace / "results" / "scores.json", {"rows": score_rows})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
