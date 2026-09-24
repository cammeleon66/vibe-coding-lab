"""Immutable per-event audit. One create-only document per event, per service."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from fednet.storage import DocumentStore

STRUCTURAL_KEYS = {"resourceType", "type", "category", "title", "profile", "arm", "label", "site"}
MASK = "•••"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def body_digest(payload: Any) -> str:
    raw = payload if isinstance(payload, bytes) else canonical_json(payload)
    return hashlib.sha256(raw).hexdigest()


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def redact(value: Any, key: str | None = None) -> Any:
    """Keep structure; mask clinical values."""
    if isinstance(value, dict):
        return {name: redact(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if key in STRUCTURAL_KEYS or isinstance(value, bool) or value is None:
        return value
    return MASK


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: "evt_" + uuid4().hex[:12])
    timestamp: str = Field(default_factory=utc_now)
    service: str
    source: str
    destination: str
    correlation_id: str
    operation: str
    step: str
    status: str
    detail: str = ""
    policy: dict[str, Any] | None = None
    manifest: dict[str, int] = Field(default_factory=dict)
    body_sha256: str | None = None
    snapshot: Any = None
    generation: int = 0


class AuditLog:
    def __init__(self, store: DocumentStore, service: str) -> None:
        self._store = store
        self._service = service

    def record(self, generation: int, **fields: Any) -> AuditEvent:
        payload = fields.pop("payload", None)
        if payload is not None:
            fields.setdefault("body_sha256", body_digest(payload))
            fields.setdefault("snapshot", redact(payload))
        event = AuditEvent(service=self._service, generation=generation, **fields)
        key = f"audit/{generation:06d}/{event.timestamp.replace(':', '')}-{event.event_id}.json"
        if not self._store.create(key, event.model_dump_json().encode()):
            raise RuntimeError("Audit events are immutable.")
        return event

    def events(self, generation: int, correlation_id: str | None = None) -> list[AuditEvent]:
        items: list[AuditEvent] = []
        for key in self._store.list(f"audit/{generation:06d}/"):
            raw = self._store.read(key)
            if raw is None:
                continue
            event = AuditEvent.model_validate_json(raw)
            if correlation_id is None or event.correlation_id == correlation_id:
                items.append(event)
        return sorted(items, key=lambda item: item.timestamp)
