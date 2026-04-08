import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from omlx_benchmark.runner import BenchmarkRunner


class RunnerTests(unittest.TestCase):
    def test_current_mcp_config_path_reads_settings_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_path = root / "settings.json"
            settings_path.write_text(
                json.dumps({"mcp": {"config_path": "/tmp/example.json"}}),
                encoding="utf-8",
            )
            runner = BenchmarkRunner(
                root,
                settings_path=settings_path,
                model_settings_path=root / "model_settings.json",
                app_config_path=root / "config.json",
                fallback_mcp_path=root / "mcp.toml",
            )
            self.assertEqual(runner.current_mcp_config_path(), Path("/tmp/example.json"))

    def test_restore_global_sampling_returns_none_without_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = BenchmarkRunner(
                root,
                settings_path=root / "settings.json",
                model_settings_path=root / "model_settings.json",
                app_config_path=root / "config.json",
                fallback_mcp_path=root / "mcp.toml",
            )
            self.assertIsNone(runner.restore_global_sampling())

    def test_repair_mcp_config_writes_runtime_json_without_embedding_secret_in_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_path = root / "settings.json"
            settings_path.write_text(
                json.dumps({"mcp": {"config_path": str(root / "mcp.toml")}}),
                encoding="utf-8",
            )
            (root / "mcp.toml").write_text(
                "[mcp_servers.omlx]\ncommand='uv'\nargs=['run','omlx-mcp-server']\n[mcp_servers.omlx.env]\nOMLX_BASE_URL='http://127.0.0.1:8000/v1'\n",
                encoding="utf-8",
            )
            runner = BenchmarkRunner(
                root,
                settings_path=settings_path,
                model_settings_path=root / "model_settings.json",
                app_config_path=root / "config.json",
                fallback_mcp_path=root / "mcp.toml",
            )
            runner.admin.update_global_settings = MagicMock(return_value={"success": True})
            result = runner.repair_mcp_config()
            runtime_path = Path(result["config_path"])
            self.assertTrue(runtime_path.exists())
            payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            self.assertIn("mcpServers", payload)
