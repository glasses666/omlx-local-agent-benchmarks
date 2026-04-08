from __future__ import annotations

import argparse

from .core import summarize_entries
from .loader import load_entries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release-audit")
    parser.add_argument("path", help="Path to a JSON file containing release entries")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    entries = load_entries(args.path)
    print(summarize_entries(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
