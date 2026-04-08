from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path

from release_audit.cli import main


FIXTURE = Path(__file__).parent / "fixtures" / "releases.json"


class VisibleReleaseAuditTests(unittest.TestCase):
    def run_cli(self, *args: str) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = main(list(args))
        self.assertEqual(exit_code, 0)
        return buffer.getvalue().strip()

    def test_default_text_output_is_sorted_by_severity_then_component(self) -> None:
        output = self.run_cli(str(FIXTURE))
        self.assertEqual(
            output.splitlines(),
            [
                "- [stable] S5 api: Fix auth regressions",
                "- [beta] S5 cli: Improve dry-run diagnostics",
                "- [stable] S4 api: Add bulk export",
                "- [stable] S3 ui: Polish release banner",
                "- [beta] S2 docs: Add migration guide",
            ],
        )

    def test_channel_filter_stable_only(self) -> None:
        output = self.run_cli(str(FIXTURE), "--channel", "stable")
        self.assertEqual(
            output.splitlines(),
            [
                "- [stable] S5 api: Fix auth regressions",
                "- [stable] S4 api: Add bulk export",
                "- [stable] S3 ui: Polish release banner",
            ],
        )

    def test_json_output_for_beta_channel(self) -> None:
        output = self.run_cli(str(FIXTURE), "--channel", "beta", "--format", "json")
        payload = json.loads(output)
        self.assertEqual([entry["title"] for entry in payload], ["Improve dry-run diagnostics", "Add migration guide"])
        self.assertEqual(payload[0]["component"], "cli")
