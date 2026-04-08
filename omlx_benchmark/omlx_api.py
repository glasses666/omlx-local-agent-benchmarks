from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class OMLXClient:
    def __init__(self, *, base_url: str, api_key: str, timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict:
        data = None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def models(self) -> dict:
        return self._request("GET", "/v1/models")

    def models_status(self) -> dict:
        return self._request("GET", "/v1/models/status")

    def unload_model(self, model_id: str) -> dict:
        return self._request("POST", f"/v1/models/{model_id}/unload", {})

    def chat_completion(self, payload: dict[str, Any]) -> dict:
        return self._request("POST", "/v1/chat/completions", payload)

    def responses(self, payload: dict[str, Any]) -> dict:
        return self._request("POST", "/v1/responses", payload)

    def mcp_servers(self) -> dict:
        return self._request("GET", "/v1/mcp/servers")

    def mcp_tools(self) -> dict:
        return self._request("GET", "/v1/mcp/tools")
