"""Signed service-to-service HTTP client with per-call timeouts and retries."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import httpx

from fednet.audit import canonical_json
from fednet.signing import SigningKey, sign

FIRST_CALL_TIMEOUT = 30.0
IDLE_AFTER_SECONDS = 300.0


class SiteUnavailable(Exception):
    def __init__(self, site: str, reason: str) -> None:
        super().__init__(f"{site} unavailable: {reason}")
        self.site = site
        self.reason = reason


class RemoteError(Exception):
    def __init__(self, site: str, status_code: int, detail: Any) -> None:
        super().__init__(f"{site} returned {status_code}: {detail}")
        self.site = site
        self.status_code = status_code
        self.detail = detail


class SignedClient:
    def __init__(
        self, site: str, base_url: str, key: SigningKey, client: httpx.Client | None = None
    ) -> None:
        self.site = site
        self._key = key
        self._client = client or httpx.Client(base_url=base_url)
        self._last_success = 0.0

    def call(
        self,
        method: str,
        path: str,
        *,
        correlation_id: str,
        payload: Any = None,
        params: dict[str, str] | None = None,
        timeout: float = 10.0,
        retries: int = 0,
        allow_cold_start: bool = True,
    ) -> Any:
        body = canonical_json(payload) if payload is not None else b""
        query = urlencode(params or {})
        if allow_cold_start and time.monotonic() - self._last_success > IDLE_AFTER_SECONDS:
            timeout = max(timeout, FIRST_CALL_TIMEOUT)
        last_error: Exception | None = None
        for _attempt in range(retries + 1):
            headers = sign(
                self._key,
                method=method,
                path=path,
                query=query,
                body=body,
                correlation_id=correlation_id,
            )
            try:
                response = self._client.request(
                    method,
                    path + (f"?{query}" if query else ""),
                    content=body if payload is not None else None,
                    headers=headers,
                    timeout=timeout,
                )
            except httpx.HTTPError as error:
                last_error = error
                continue
            if response.status_code in {502, 503, 504} and "x-fed-service" not in response.headers:
                # Platform ingress error: the site itself did not answer.
                last_error = RuntimeError(f"ingress returned {response.status_code}")
                continue
            if response.status_code == 404 and "x-fed-service" not in response.headers:
                last_error = RuntimeError("site ingress not reachable (404 from platform)")
                continue
            self._last_success = time.monotonic()
            if response.status_code >= 400:
                try:
                    detail = response.json().get("detail")
                except ValueError:
                    detail = response.text
                raise RemoteError(self.site, response.status_code, detail)
            return response.json() if response.content else None
        raise SiteUnavailable(self.site, str(last_error))

    def health(self, timeout: float = 5.0) -> tuple[dict[str, Any] | None, float, str | None]:
        started = time.monotonic()
        try:
            response = self._client.get("/api/health", timeout=timeout)
            elapsed = time.monotonic() - started
            if response.status_code != 200 or "x-fed-service" not in response.headers:
                return None, elapsed, f"HTTP {response.status_code}"
            self._last_success = time.monotonic()
            return response.json(), elapsed, None
        except httpx.HTTPError as error:
            return None, time.monotonic() - started, type(error).__name__
