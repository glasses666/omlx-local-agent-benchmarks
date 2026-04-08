import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TaskDefinitionTests(unittest.TestCase):
    def test_task_file_has_required_suites_and_unique_ids(self) -> None:
        task_file = ROOT / "tasks.json"
        self.assertTrue(task_file.exists())
        payload = json.loads(task_file.read_text(encoding="utf-8"))

        self.assertIn("screening", payload)
        self.assertIn("full", payload)

        ids: list[str] = []
        for section in payload.values():
            for suite in section.values():
                for task in suite:
                    ids.append(task["id"])

        self.assertEqual(len(ids), len(set(ids)))
