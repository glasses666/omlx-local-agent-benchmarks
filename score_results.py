from __future__ import annotations

import argparse
import json
from pathlib import Path

from omlx_benchmark.reporting import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-emit score-focused screening summary.")
    parser.add_argument("--workspace", default=Path(__file__).resolve().parent, type=Path)
    args = parser.parse_args()

    outputs = {}
    for stem in ("screening", "full-baseline", "tuned"):
        path = args.workspace / "results" / f"{stem}-summary.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        score_rows = []
        for item in payload["summaries"]:
            row = {
                "model_id": item["model_id"],
                "overall_score": item["overall_score"],
                **item["dimension_scores"],
            }
            score_rows.append(row)
        outputs[stem] = score_rows
    if not outputs:
        raise SystemExit("No summary files found")
    write_json(args.workspace / "results" / "scores.json", outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
