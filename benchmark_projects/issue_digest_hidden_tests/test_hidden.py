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


def hidden_issues() -> list[dict]:
    return [
        {"title": "Refactor auth", "status": "open", "priority": 2},
        {"title": "Add docs", "status": "closed", "priority": 2},
        {"title": "Fix login", "status": "open", "priority": 3},
        {"title": "Audit logs", "status": "closed", "priority": 3},
    ]


class HiddenIssueDigestTests(unittest.TestCase):
    def test_default_matches_explicit_all_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            default_output = run_cli(Path(tmp), [], hidden_issues())
            explicit_output = run_cli(Path(tmp), ["--status", "all", "--format", "text"], hidden_issues())
        self.assertEqual(default_output, explicit_output)

    def test_sorting_is_priority_desc_then_title_asc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(Path(tmp), [], hidden_issues())
        self.assertEqual(
            output.splitlines(),
            [
                "- [closed] P3 Audit logs",
                "- [open] P3 Fix login",
                "- [closed] P2 Add docs",
                "- [open] P2 Refactor auth",
            ],
        )

    def test_json_output_preserves_issue_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(Path(tmp), ["--format", "json"], hidden_issues())
        self.assertEqual(
            json.loads(output),
            [
                {"title": "Audit logs", "status": "closed", "priority": 3},
                {"title": "Fix login", "status": "open", "priority": 3},
                {"title": "Add docs", "status": "closed", "priority": 2},
                {"title": "Refactor auth", "status": "open", "priority": 2},
            ],
        )

