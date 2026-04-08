from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any


def build_mcp_config(
    *,
    server_name: str,
    command: str,
    args: list[str],
    env: dict[str, str],
    max_tool_calls: int = 10,
    default_timeout: float = 30.0,
) -> dict:
    return {
        "mcpServers": {
            server_name: {
                "transport": "stdio",
                "command": command,
                "args": args,
                "env": env,
                "enabled": True,
                "timeout": default_timeout,
            }
        },
        "max_tool_calls": max_tool_calls,
        "default_timeout": default_timeout,
    }


def write_mcp_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_legacy_toml_config(path: Path) -> dict[str, Any]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    servers = payload.get("mcp_servers", {})
    if not servers:
        raise ValueError(f"No mcp_servers found in {path}")
    server_name, config = next(iter(servers.items()))
    return {
        "server_name": server_name,
        "command": config["command"],
        "args": config.get("args", []),
        "env": {key: str(value) for key, value in config.get("env", {}).items()},
    }
