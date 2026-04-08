from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from issue_digest.cli import main


def run_cli(tmp_path: Path, argv: list[str], issues: list[dict]) -> str:
    source = tmp_path / "issues.json"
    source.write_text(json.dumps(issues), encoding="utf-8")
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main([str(source), *argv])
    assert code == 0
    return buffer.getvalue().strip()


def sample_issues() -> list[dict]:
    return [
        {"title": "Refactor auth", "status": "open", "priority": 2},
        {"title": "Fix login", "status": "open", "priority": 3},
        {"title": "Add docs", "status": "closed", "priority": 2},
    ]


class VisibleIssueDigestTests(unittest.TestCase):
    def test_default_text_output_is_sorted_and_textual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(Path(tmp), [], sample_issues())
        self.assertEqual(
            output,
            "\n".join(
                [
                    "- [open] P3 Fix login",
                    "- [closed] P2 Add docs",
                    "- [open] P2 Refactor auth",
                ]
            ),
        )

    def test_status_filter_open_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(Path(tmp), ["--status", "open"], sample_issues())
        self.assertEqual(
            output,
            "\n".join(
                [
                    "- [open] P3 Fix login",
                    "- [open] P2 Refactor auth",
                ]
            ),
        )

    def test_json_output_for_closed_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(Path(tmp), ["--status", "closed", "--format", "json"], sample_issues())
        self.assertEqual(
            json.loads(output),
            [{"title": "Add docs", "status": "closed", "priority": 2}],
        )
