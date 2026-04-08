from __future__ import annotations

import argparse
import json
import csv
from pathlib import Path

from omlx_benchmark.reporting import SUMMARY_COLUMNS, markdown_table


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate markdown report from screening results.")
    parser.add_argument("--workspace", default=Path(__file__).resolve().parent, type=Path)
    args = parser.parse_args()

    report = ["# oMLX Benchmark Report", ""]
    found = False
    for stem, title in (
        ("screening", "Screening"),
        ("full-baseline", "Full Baseline"),
        ("tuned", "Tuned"),
        ("qwen-cc", "Qwen Claude-Code-Style"),
    ):
        summary_path = args.workspace / "results" / f"{stem}-summary.json"
        csv_path = args.workspace / "results" / f"{stem}-summary.csv"
        if not summary_path.exists():
            continue
        found = True
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        report.extend(
            [
                f"## {title}",
                "",
                f"- Generated at: `{payload['generated_at']}`",
                f"- Models: `{', '.join(item['model_id'] for item in payload['summaries'])}`",
                "",
            ]
        )
        if csv_path.exists():
            report.append(markdown_table(read_csv_rows(csv_path), SUMMARY_COLUMNS))
            report.append("")
    if not found:
        raise SystemExit("No stage summary files found")
    (args.workspace / "reports" / "final-report.md").write_text("\n".join(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
