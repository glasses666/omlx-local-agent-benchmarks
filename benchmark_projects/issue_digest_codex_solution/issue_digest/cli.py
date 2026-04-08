from __future__ import annotations

import argparse

from .core import export_issues, load_issues, summarize_issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="issue-digest")
    parser.add_argument("path", help="Path to a JSON file containing issues")
    parser.add_argument("--status", choices=["open", "closed", "all"], default="all")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    issues = load_issues(args.path)
    if args.format == "json":
        print(export_issues(issues, status=args.status))
    else:
        print(summarize_issues(issues, status=args.status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

