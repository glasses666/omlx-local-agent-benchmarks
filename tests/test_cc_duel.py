import tempfile
import unittest
from pathlib import Path

from omlx_benchmark.cc_duel import constraint_violations, extract_json_payload, normalize_generated_files


class CCDuelTests(unittest.TestCase):
    def test_extract_json_payload_handles_fenced_output(self) -> None:
        payload = extract_json_payload("```json\n{\"files\": {\"issue_digest/core.py\": \"x\"}}\n```")
        self.assertEqual(payload["files"]["issue_digest/core.py"], "x")

    def test_normalize_generated_files_accepts_list_payload(self) -> None:
        normalized = normalize_generated_files(
            {
                "files": [
                    {"path": "issue_digest/core.py", "content": "alpha"},
                    {"path": "issue_digest/cli.py", "content": "beta"},
                ]
            }
        )
        self.assertEqual(
            normalized,
            {"issue_digest/core.py": "alpha", "issue_digest/cli.py": "beta"},
        )

    def test_constraint_violations_flags_non_whitelisted_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template"
            repo = root / "repo"
            (template / "issue_digest").mkdir(parents=True)
            (repo / "issue_digest").mkdir(parents=True)
            (template / "issue_digest" / "core.py").write_text("one", encoding="utf-8")
            (repo / "issue_digest" / "core.py").write_text("two", encoding="utf-8")
            (template / "README.md").write_text("unchanged", encoding="utf-8")
            (repo / "README.md").write_text("changed", encoding="utf-8")

            violations = constraint_violations(template, repo, ["issue_digest/core.py"])
            self.assertEqual(violations, ["README.md"])

