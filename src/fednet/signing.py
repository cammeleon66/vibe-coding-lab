"""Directional HMAC-SHA256 request signing over a canonical envelope.

Every cross-service call carries: signer, audience, key ID, timestamp, nonce,
correlation ID and the body digest. A key is bound to one direction
(signer -> audience), so a message can never be valid the other way round.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode

from fednet.storage import DocumentStore

MAX_SKEW_SECONDS = 300
NONCE_RETENTION_SECONDS = 600

HEADER_SIGNER = "x-fed-signer"
HEADER_AUDIENCE = "x-fed-audience"
HEADER_KEY_ID = "x-fed-key-id"
HEADER_TIMESTAMP = "x-fed-timestamp"
HEADER_NONCE = "x-fed-nonce"
HEADER_CORRELATION = "x-fed-correlation-id"
HEADER_SIGNATURE = "x-fed-signature"

# name -> (signer, audience). Workstation and admin keys are separate namespaces.
KEY_SPECS: dict[str, tuple[str, str]] = {
    "nl-hub": ("nl", "hub"),
    "hub-nl": ("hub", "nl"),
    "de-hub": ("de", "hub"),
    "hub-de": ("hub", "de"),
    "ws-nl": ("hub-bff", "nl"),
    "ws-de": ("hub-bff", "de"),
    "admin-nl": ("hub-admin", "nl"),
    "admin-de": ("hub-admin", "de"),
}

SITE_KEYS: dict[str, tuple[str, ...]] = {
    "nl": ("nl-hub", "hub-nl", "ws-nl", "admin-nl"),
    "de": ("de-hub", "hub-de", "ws-de", "admin-de"),
    "hub": tuple(KEY_SPECS),
}


class SignatureError(Exception):
    pass


@dataclass(frozen=True)
class SigningKey:
    name: str
    signer: str
    audience: str
    secret: bytes

    @property
    def key_id(self) -> str:
        return f"{self.name}.v1"


def env_var_for(name: str) -> str:
    return "FED_KEY_" + name.upper().replace("-", "_")


def load_keys(service: str, *, allow_dev_keys: bool) -> dict[str, SigningKey]:
    keys: dict[str, SigningKey] = {}
    for name in SITE_KEYS[service]:
        value = os.getenv(env_var_for(name))
        if not value:
            if not allow_dev_keys:
                raise RuntimeError(f"Missing signing key {env_var_for(name)}.")
            # Local-only deterministic keys; Azure always injects secrets.
            value = hashlib.sha256(f"local-dev-only:{name}".encode()).hexdigest()
        signer, audience = KEY_SPECS[name]
        keys[name] = SigningKey(name, signer, audience, value.encode())
    return keys


def _canonical_query(query: str) -> str:
    return urlencode(sorted(parse_qsl(query, keep_blank_values=True)))


def canonical_envelope(
    *,
    signer: str,
    audience: str,
    key_id: str,
    method: str,
    path: str,
    query: str,
    timestamp: str,
    nonce: str,
    correlation_id: str,
    content_type: str,
    body: bytes,
) -> bytes:
    lines = [
        "fednet-v1",
        signer,
        audience,
        key_id,
        method.upper(),
        path,
        _canonical_query(query),
        timestamp,
        nonce,
        correlation_id,
        content_type.split(";")[0].strip().lower(),
        hashlib.sha256(body).hexdigest(),
    ]
    return "\n".join(lines).encode()


def sign(
    key: SigningKey,
    *,
    method: str,
    path: str,
    query: str = "",
    body: bytes = b"",
    correlation_id: str,
    content_type: str = "application/json",
    now: float | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    timestamp = str(int(now if now is not None else time.time()))
    nonce_value = nonce or secrets.token_hex(16)
    envelope = canonical_envelope(
        signer=key.signer,
        audience=key.audience,
        key_id=key.key_id,
        method=method,
        path=path,
        query=query,
        timestamp=timestamp,
        nonce=nonce_value,
        correlation_id=correlation_id,
        content_type=content_type,
        body=body,
    )
    return {
        HEADER_SIGNER: key.signer,
        HEADER_AUDIENCE: key.audience,
        HEADER_KEY_ID: key.key_id,
        HEADER_TIMESTAMP: timestamp,
        HEADER_NONCE: nonce_value,
        HEADER_CORRELATION: correlation_id,
        HEADER_SIGNATURE: hmac.new(key.secret, envelope, hashlib.sha256).hexdigest(),
        "content-type": content_type,
    }


class NonceStore:
    """Nonces persisted in the receiver's own store so replay survives restarts."""

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    def remember(self, signer: str, nonce: str, timestamp: int) -> bool:
        return self._store.create(f"nonces/{signer}/{nonce}", str(timestamp).encode())

    def purge_expired(self, now: float) -> None:
        for key in self._store.list("nonces/"):
            raw = self._store.read(key)
            if raw is not None and int(raw) < now - NONCE_RETENTION_SECONDS:
                self._store.delete_prefix(key)


@dataclass(frozen=True)
class VerifiedCall:
    signer: str
    key_name: str
    correlation_id: str


def verify(
    *,
    keys: list[SigningKey],
    audience: str,
    method: str,
    path: str,
    query: str,
    headers: dict[str, str],
    body: bytes,
    nonces: NonceStore,
    now: float | None = None,
) -> VerifiedCall:
    """Verify against the keys acceptable for this route; raises SignatureError."""
    lowered = {name.lower(): value for name, value in headers.items()}
    try:
        signer = lowered[HEADER_SIGNER]
        claimed_audience = lowered[HEADER_AUDIENCE]
        key_id = lowered[HEADER_KEY_ID]
        timestamp = lowered[HEADER_TIMESTAMP]
        nonce = lowered[HEADER_NONCE]
        correlation_id = lowered[HEADER_CORRELATION]
        signature = lowered[HEADER_SIGNATURE]
    except KeyError as error:
        raise SignatureError(f"Missing signature header {error.args[0]}.") from error
    key = next((candidate for candidate in keys if candidate.key_id == key_id), None)
    if key is None:
        raise SignatureError("Unknown or unacceptable key for this route.")
    if key.signer != signer or key.audience != audience or claimed_audience != audience:
        raise SignatureError("Signer or audience does not match the key direction.")
    current = now if now is not None else time.time()
    try:
        signed_at = int(timestamp)
    except ValueError as error:
        raise SignatureError("Invalid timestamp.") from error
    if abs(current - signed_at) > MAX_SKEW_SECONDS:
        raise SignatureError("Request timestamp outside the allowed window.")
    envelope = canonical_envelope(
        signer=signer,
        audience=audience,
        key_id=key_id,
        method=method,
        path=path,
        query=query,
        timestamp=timestamp,
        nonce=nonce,
        correlation_id=correlation_id,
        content_type=lowered.get("content-type", ""),
        body=body,
    )
    expected = hmac.new(key.secret, envelope, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise SignatureError("Signature mismatch.")
    if not nonces.remember(signer, nonce, signed_at):
        raise SignatureError("Replayed request.")
    return VerifiedCall(signer=signer, key_name=key.name, correlation_id=correlation_id)
