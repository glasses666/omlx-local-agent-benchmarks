from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from release_audit.cli import main

def hidden_entries() -> list[dict]:
    return [
        {
            "channel": "stable",
            "severity": 4,
            "component": "api",
            "title": "Add bulk export",
            "notes": "Adds batched export endpoints.",
        },
        {
            "channel": "stable",
            "severity": 5,
            "component": "api",
            "title": "Fix auth regressions",
            "notes": "Restores legacy token refresh behavior.",
        },
        {
            "channel": "beta",
            "severity": 2,
            "component": "docs",
            "title": "Add migration guide",
            "notes": "Documents migration caveats for beta adopters.",
        },
        {
            "channel": "beta",
            "severity": 5,
            "component": "cli",
            "title": "Improve dry-run diagnostics",
            "notes": "Shows the exact impacted resources before apply.",
        },
        {
            "channel": "stable",
            "severity": 3,
            "component": "ui",
            "title": "Polish release banner",
            "notes": "Improves spacing and readability on narrow screens.",
        },
    ]


class HiddenReleaseAuditTests(unittest.TestCase):
    def run_cli(self, *args: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "releases.json"
            source.write_text(json.dumps(hidden_entries()), encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exit_code = main([str(source), *args])
        self.assertEqual(exit_code, 0)
        return buffer.getvalue().strip()

    def test_default_matches_explicit_all_text(self) -> None:
        implicit = self.run_cli()
        explicit = self.run_cli("--channel", "all", "--format", "text")
        self.assertEqual(implicit, explicit)

    def test_sorting_uses_title_as_third_key(self) -> None:
        output = self.run_cli("--channel", "stable")
        self.assertEqual(
            output.splitlines(),
            [
                "- [stable] S5 api: Fix auth regressions",
                "- [stable] S4 api: Add bulk export",
                "- [stable] S3 ui: Polish release banner",
            ],
        )

    def test_json_output_preserves_extra_fields(self) -> None:
        payload = json.loads(self.run_cli("--format", "json"))
        self.assertIn("notes", payload[0])
        self.assertEqual(payload[0]["title"], "Fix auth regressions")
