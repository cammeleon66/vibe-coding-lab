from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fednet.common import Runtime
from fednet.hub import create_hub_app
from fednet.signing import load_keys
from fednet.site import create_site_app
from fednet.storage import MemoryDocumentStore
from fednet.transport import SignedClient


@dataclass
class Network:
    apps: dict[str, FastAPI] = field(default_factory=dict)
    runtimes: dict[str, Runtime] = field(default_factory=dict)
    down: set[str] = field(default_factory=set)
    captured: list[tuple[str, str, bytes]] = field(default_factory=list)
    browser: TestClient | None = None

    def ui(self) -> TestClient:
        assert self.browser is not None
        return self.browser


class _Route(httpx.BaseTransport):
    """Delivers a request to the named in-process service unless it is offline."""

    def __init__(self, network: Network, target: str) -> None:
        self._network = network
        self._target = target
        self._client: TestClient | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self._target in self._network.down:
            raise httpx.ConnectError("service offline", request=request)
        self._network.captured.append((self._target, request.url.path, request.read()))
        if self._client is None:
            self._client = TestClient(self._network.apps[self._target])
        response = self._client.request(
            request.method,
            str(request.url.copy_with(scheme="http", host="testserver")),
            content=request.content,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
        )
        return httpx.Response(response.status_code, headers=dict(response.headers),
                              content=response.content, request=request)


def _client(network: Network, target: str, key_owner: str, key: str) -> SignedClient:
    keys = network.runtimes[key_owner].keys
    return SignedClient(
        target,
        f"http://{target}",
        keys[key],
        client=httpx.Client(transport=_Route(network, target), base_url=f"http://{target}"),
    )


def build_network(access_code: str | None = None) -> Network:
    network = Network()
    for service in ("nl", "de", "hub"):
        network.runtimes[service] = Runtime(
            service=service,
            store=MemoryDocumentStore(),
            keys=load_keys(service, allow_dev_keys=True),
        )
    for site in ("nl", "de"):
        network.apps[site] = create_site_app(
            site, network.runtimes[site], _client(network, "hub", site, f"{site}-hub")
        )
    network.apps["hub"] = create_hub_app(
        network.runtimes["hub"],
        workstation={s: _client(network, s, "hub", f"ws-{s}") for s in ("nl", "de")},
        federation={s: _client(network, s, "hub", f"hub-{s}") for s in ("nl", "de")},
        admin={s: _client(network, s, "hub", f"admin-{s}") for s in ("nl", "de")},
        access_code=access_code,
        session_secret="session-secret" if access_code else None,
    )
    network.browser = TestClient(network.apps["hub"], base_url="https://hub")
    return network


@pytest.fixture
def net() -> Iterator[Network]:
    yield build_network()


DEFAULT_CATEGORIES = ["diagnosis", "treatment_history", "pathology", "molecular",
                      "relevant_imaging"]


def send_case(network: Network, categories: list[str] | None = None) -> dict[str, Any]:
    response = network.ui().post(
        "/api/nl/peer-reviews",
        json={"patient_id": "umcu-00482913", "expert_id": "exp-heidelberg-mueller",
              "categories": categories or DEFAULT_CATEGORIES,
              "question": "Later-line strategy for KRAS G12C mCRC?"},
    )
    assert response.status_code == 201, response.text
    return dict(response.json())
