import json
import unittest

from omlx_benchmark.mcp_config import build_mcp_config


class MCPConfigTests(unittest.TestCase):
    def test_build_mcp_config_uses_json_shape_expected_by_omlx(self) -> None:
        config = build_mcp_config(
            server_name="omlx-tools",
            command="uv",
            args=["run", "omlx-mcp-server"],
            env={"OMLX_BASE_URL": "http://127.0.0.1:8000/v1"},
        )

        parsed = json.loads(json.dumps(config))
        self.assertIn("mcpServers", parsed)
        self.assertIn("omlx-tools", parsed["mcpServers"])
        self.assertEqual(parsed["mcpServers"]["omlx-tools"]["command"], "uv")
