from __future__ import annotations

import argparse
from pathlib import Path

from omlx_benchmark.runner import BenchmarkRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run oMLX local model benchmarks.")
    parser.add_argument(
        "command",
        choices=["inspect", "backup", "repair-mcp", "screening", "baseline", "tuned", "all"],
        help="Benchmark action to run.",
    )
    parser.add_argument(
        "--workspace",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="Benchmark workspace root.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runner = BenchmarkRunner(args.workspace)

    if args.command == "inspect":
        runner.inspect_environment()
        return 0
    if args.command == "backup":
        runner.backup_relevant_files()
        return 0
    if args.command == "repair-mcp":
        runner.repair_mcp_config()
        return 0
    if args.command == "screening":
        runner.inspect_environment()
        runner.backup_relevant_files()
        try:
            runner.run_screening()
        finally:
            runner.restore_global_sampling()
        return 0
    if args.command == "baseline":
        runner.inspect_environment()
        try:
            runner.run_full_baseline()
        finally:
            runner.restore_global_sampling()
        return 0
    if args.command == "tuned":
        runner.inspect_environment()
        try:
            runner.run_tuned()
        finally:
            runner.restore_global_sampling()
        return 0
    if args.command == "all":
        runner.inspect_environment()
        runner.backup_relevant_files()
        try:
            runner.run_screening()
            runner.run_full_baseline()
            runner.run_tuned()
        finally:
            runner.restore_global_sampling()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
