"""Entry point: `SITE=nl|de|hub uvicorn fednet.main:app`."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from fednet.common import Runtime, configure_telemetry
from fednet.hub import create_hub_app
from fednet.signing import SigningKey, load_keys
from fednet.site import create_site_app
from fednet.storage import DocumentStore, FileDocumentStore, create_blob_store
from fednet.transport import SignedClient

DEFAULT_URLS = {"hub": "http://127.0.0.1:8100", "nl": "http://127.0.0.1:8101",
                "de": "http://127.0.0.1:8102"}


def _store(service: str) -> DocumentStore:
    account_url = os.getenv("STORAGE_ACCOUNT_URL")
    if account_url:
        return create_blob_store(account_url, os.environ["STORAGE_CONTAINER"],
                                 os.getenv("AZURE_CLIENT_ID"))
    root = Path(os.getenv("FED_DATA_DIR", "data")) / f"fed-{service}"
    return FileDocumentStore(root)


def _url(service: str) -> str:
    return os.getenv(f"{service.upper()}_URL", DEFAULT_URLS[service])


def _clients(keys: dict[str, SigningKey], prefix: str) -> dict[str, SignedClient]:
    return {site: SignedClient(site, _url(site), keys[f"{prefix}-{site}"]) for site in ("nl", "de")}


def create_from_env() -> FastAPI:
    service = os.getenv("SITE", "hub")
    if service not in DEFAULT_URLS:
        raise RuntimeError("SITE must be nl, de or hub.")
    azure = os.getenv("FED_RUNTIME", "local") == "azure"
    keys = load_keys(service, allow_dev_keys=not azure)
    runtime = Runtime(service=service, store=_store(service), keys=keys)
    configure_telemetry(service)
    if service != "hub":
        hub = SignedClient("hub", _url("hub"), keys[f"{service}-hub"])
        return create_site_app(service, runtime, hub)
    frontend = os.getenv("FRONTEND_DIST")
    repository_root = Path(__file__).resolve().parents[2]
    return create_hub_app(
        runtime,
        workstation=_clients(keys, "ws"),
        federation=_clients(keys, "hub"),
        admin=_clients(keys, "admin"),
        frontend_dist=Path(frontend) if frontend else repository_root / "frontend" / "dist",
        access_code=os.getenv("DEMO_ACCESS_CODE"),
        session_secret=os.getenv("DEMO_SESSION_SECRET"),
    )


def __getattr__(name: str) -> FastAPI:
    # Lazily build so importing the module (tests, tooling) has no side effects.
    if name == "app":
        application = create_from_env()
        globals()["app"] = application
        return application
    raise AttributeError(name)
