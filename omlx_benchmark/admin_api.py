from __future__ import annotations

import http.cookiejar
import json
import urllib.error
import urllib.request
from typing import Any

from .omlx_api import OMLXClient


class OMLXAdminClient(OMLXClient):
    def __init__(self, *, base_url: str, api_key: str, timeout: int = 300) -> None:
        super().__init__(base_url=base_url, api_key=api_key, timeout=timeout)
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )
        self._logged_in = False

    def login(self) -> dict[str, Any]:
        payload = {"api_key": self.api_key, "remember": False}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}/admin/api/login",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                self._logged_in = True
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"POST /admin/api/login failed: {exc.code} {detail}") from exc

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._logged_in:
            self.login()
        data = None
        headers: dict[str, str] = {}
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
            with self.opener.open(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc

    def global_settings(self) -> dict[str, Any]:
        return self._request("GET", "/admin/api/global-settings")

    def update_global_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/admin/api/global-settings", payload)

    def update_model_settings(self, model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", f"/admin/api/models/{model_id}/settings", payload)

    def reload_models(self) -> dict[str, Any]:
        return self._request("POST", "/admin/api/reload", {})
