"""Pieces shared by the hospital services and the hub."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status

from fednet.audit import AuditLog, utc_now
from fednet.signing import NonceStore, SignatureError, SigningKey, VerifiedCall, verify
from fednet.storage import DocumentStore

ISOLATION_SWITCH_PATH = "/admin/connectivity"
SITE_LABELS = {"nl": "UMC Utrecht", "de": "Heidelberg", "hub": "Federation hub"}


def unavailable_detail(site: str) -> str:
    return f"{SITE_LABELS.get(site, site)} unavailable — federated result incomplete"


@dataclass
class Runtime:
    service: str
    store: DocumentStore
    keys: dict[str, SigningKey]
    version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "local"))
    started_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.audit = AuditLog(self.store, self.service)
        self.nonces = NonceStore(self.store)
        self._isolated: bool | None = None

    def read_json(self, key: str, default: Any = None) -> Any:
        raw = self.store.read(key)
        return default if raw is None else json.loads(raw)

    def write_json(self, key: str, value: Any) -> None:
        self.store.write(key, json.dumps(value, ensure_ascii=False).encode())

    @property
    def generation(self) -> int:
        return int(self.read_json("state/generation.json", {"generation": 1})["generation"])

    @generation.setter
    def generation(self, value: int) -> None:
        self.write_json("state/generation.json", {"generation": value})

    @property
    def isolated(self) -> bool:
        # Checked on every request, so cached in-process (one replica per service).
        if self._isolated is None:
            state = self.read_json("state/isolation.json", {"isolated": False})
            self._isolated = bool(state["isolated"])
        return self._isolated

    @isolated.setter
    def isolated(self, value: bool) -> None:
        self.write_json("state/isolation.json", {"isolated": value, "changed_at": utc_now()})
        self._isolated = value

    def record(self, **fields: Any) -> None:
        self.audit.record(self.generation, **fields)


def signed_dependency(
    runtime: Runtime, key_names: tuple[str, ...]
) -> Callable[[Request], Awaitable[VerifiedCall]]:
    acceptable = [runtime.keys[name] for name in key_names]

    async def dependency(request: Request) -> VerifiedCall:
        body = await request.body()
        try:
            call = verify(
                keys=acceptable,
                audience=runtime.service,
                method=request.method,
                path=request.url.path,
                query=request.url.query,
                headers=dict(request.headers),
                body=body,
                nonces=runtime.nonces,
            )
        except SignatureError as error:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error
        _annotate_span(call.correlation_id)
        return call

    return dependency


def _annotate_span(correlation_id: str) -> None:
    try:
        from opentelemetry import trace

        trace.get_current_span().set_attribute("fed.correlation_id", correlation_id)
    except ImportError:  # pragma: no cover
        return


def base_app(runtime: Runtime, title: str) -> FastAPI:
    application = FastAPI(title=title)

    @application.middleware("http")
    async def mark_service(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if (
            runtime.service != "hub"
            and request.url.path != ISOLATION_SWITCH_PATH
            and runtime.isolated
        ):
            # Network isolation at the site edge: answer like a dead upstream, without the
            # x-fed-service marker, so callers see exactly what an ingress outage looks like.
            return Response("upstream connect error", status_code=503,
                            media_type="text/plain")
        response = await call_next(request)
        response.headers["x-fed-service"] = runtime.service
        response.headers["cache-control"] = "no-store"
        return response

    return application


def configure_telemetry(service: str) -> None:
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        return
    from azure.monitor.opentelemetry import configure_azure_monitor

    os.environ.setdefault("OTEL_SERVICE_NAME", f"oncology-fed-{service}")
    configure_azure_monitor(connection_string=connection_string, logger_name="fednet")


def new_correlation_id() -> str:
    return f"corr_{int(time.time()):x}{os.urandom(3).hex()}"
