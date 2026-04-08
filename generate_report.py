from __future__ import annotations

import argparse
import json
from pathlib import Path

from omlx_benchmark.reporting import SUMMARY_COLUMNS, markdown_table


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate markdown report from screening results.")
    parser.add_argument("--workspace", default=Path(__file__).resolve().parent, type=Path)
    args = parser.parse_args()

    screening_json = args.workspace / "results" / "screening-summary.json"
    screening_csv = args.workspace / "results" / "screening-summary.csv"
    if not screening_json.exists():
        raise SystemExit("Missing screening-summary.json")

    payload = json.loads(screening_json.read_text(encoding="utf-8"))
    if screening_csv.exists():
        rows = screening_csv.read_text(encoding="utf-8").splitlines()
    else:
        rows = []

    report = [
        "# oMLX Benchmark Report",
        "",
        "## Screening",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Finalists: `{', '.join(payload['finalists'])}`",
        "",
    ]
    if rows:
        table_rows = []
        header = rows[0].split(",")
        for line in rows[1:]:
            values = line.split(",")
            table_rows.append(dict(zip(header, values)))
        report.append(markdown_table(table_rows, SUMMARY_COLUMNS))
    (args.workspace / "reports" / "final-report.md").write_text("\n".join(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
