import json
import tempfile
import unittest
from pathlib import Path

from omlx_benchmark.backup import backup_file


class BackupTests(unittest.TestCase):
    def test_backup_file_copies_and_records_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source.json"
            dst_dir = Path(tmp) / "backups"
            manifest = Path(tmp) / "manifest.json"
            src.write_text('{"hello":"world"}', encoding="utf-8")

            record = backup_file(src, dst_dir, manifest, "config")

            self.assertTrue((dst_dir / record["backup_name"]).exists())
            self.assertEqual(record["kind"], "config")

            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["records"]), 1)
            self.assertEqual(payload["records"][0]["sha256"], record["sha256"])
