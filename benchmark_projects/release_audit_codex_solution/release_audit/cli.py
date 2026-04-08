from __future__ import annotations

import argparse

from .core import summarize_entries
from .loader import load_entries
from .render import render_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release-audit")
    parser.add_argument("path", help="Path to a JSON file containing release entries")
    parser.add_argument("--channel", choices=["stable", "beta", "all"], default="all", help="Filter by release channel")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Select output format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    entries = load_entries(args.path)
    if args.format == "json":
        print(render_json(entries, args.channel))
    else:
        print(summarize_entries(entries, args.channel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
