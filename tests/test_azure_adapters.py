from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import ContentSettings
from fastapi.testclient import TestClient

from collab.app import create_app
from collab.azure_adapters import (
    AzureBlobEvidenceArrivalPublisher,
    AzureBlobStateStore,
    AzureLateImagingSource,
    AzureMilanSource,
    AzureUtrechtSource,
)
from collab.models import DemoState, EvidenceArrivalEvent
from collab.persistence import JsonStateStore
from collab.sources import MilanLateImagingSource, MilanLocalSource, UtrechtLocalSource


class FakeDownload:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def readall(self) -> bytes:
        return self._content


class FakeBlob:
    def __init__(self, blobs: dict[str, bytes], name: str) -> None:
        self._blobs = blobs
        self._name = name

    def download_blob(self) -> FakeDownload:
        if self._name not in self._blobs:
            raise ResourceNotFoundError("missing")
        return FakeDownload(self._blobs[self._name])

    def upload_blob(
        self,
        data: bytes | str,
        *,
        overwrite: bool = False,
        content_settings: ContentSettings | None = None,
    ) -> None:
        del content_settings
        if self._name in self._blobs and not overwrite:
            raise ResourceExistsError("exists")
        self._blobs[self._name] = data.encode() if isinstance(data, str) else data

    def delete_blob(self, *, delete_snapshots: str | None = None) -> None:
        del delete_snapshots
        self._blobs.pop(self._name, None)


class FakeContainer:
    def __init__(self, name: str, blobs: dict[str, bytes] | None = None) -> None:
        self.container_name = name
        self.url = f"https://synthetic.blob.core.windows.net/{name}"
        self.blobs = blobs or {}

    def get_blob_client(self, blob: str) -> FakeBlob:
        return FakeBlob(self.blobs, blob)

    def list_blobs(self, *, name_starts_with: str | None = None) -> Iterator[Any]:
        for name in list(self.blobs):
            if name_starts_with is None or name.startswith(name_starts_with):
                yield SimpleNamespace(name=name)


def _fixture_blobs(institution: str) -> dict[str, bytes]:
    root = Path(__file__).parents[1] / "src" / "collab" / "fixtures" / institution
    return {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}


def _command() -> dict[str, object]:
    return {
        "need": {},
        "centre_id": "utrecht-crc",
        "clinician_id": "eva-van-dijk",
        "urgency": "expedited",
        "sender": {
            "clinician_name": "Dr Luca Bianchi",
            "institution": "Istituto Nazionale dei Tumori, Milan",
            "country": "Italy",
        },
    }


def test_azure_blob_sources_preserve_cloud_retrieval_references() -> None:
    milan = FakeContainer("source", _fixture_blobs("milan"))
    utrecht = FakeContainer("source", _fixture_blobs("utrecht"))
    event = EvidenceArrivalEvent(
        event_id="azure-event",
        occurred_at="2026-09-23T10:25:00Z",
    )

    initial = [
        *AzureMilanSource(milan).read_snapshot("CRC-EU-001"),
        *AzureUtrechtSource(utrecht).read_snapshot("CRC-EU-001"),
    ]
    imaging = AzureLateImagingSource(milan).read_arrival(event)

    assert len(initial) == 5
    assert len(imaging) == 2
    assert all(
        item.retrieval_reference.startswith("https://synthetic.blob.core.windows.net/source/")
        for item in [*initial, *imaging]
    )


def test_azure_state_and_trigger_adapters_are_persistent_and_resettable() -> None:
    shared = FakeContainer("collaboration")
    state = AzureBlobStateStore(shared)
    state.save(DemoState(processed_evidence_events={"event-1": "fingerprint"}))

    assert state.load().processed_evidence_events == {"event-1": "fingerprint"}

    milan = FakeContainer("source")
    publisher = AzureBlobEvidenceArrivalPublisher(milan)
    event = EvidenceArrivalEvent(
        event_id="event-1",
        occurred_at="2026-09-23T10:25:00Z",
    )
    publisher.publish(event)
    publisher.publish(event)

    restored = publisher.read_event(
        "https://synthetic.blob.core.windows.net/source/events/event-1.json"
    )
    assert restored.event_id == "event-1"
    publisher.reset()
    assert milan.blobs == {}


def test_event_grid_endpoint_validates_secret_and_applies_blob_event(tmp_path: Path) -> None:
    class FakePublisher:
        def __init__(self, event: EvidenceArrivalEvent) -> None:
            self.event = event

        def publish(self, event: EvidenceArrivalEvent) -> None:
            self.event = event

        def read_event(self, blob_url: str) -> EvidenceArrivalEvent:
            assert blob_url.endswith("/events/event-grid-azure-001.json")
            return self.event

        def reset(self) -> None:
            return None

    event = EvidenceArrivalEvent(
        event_id="event-grid-azure-001",
        occurred_at="2026-09-23T10:25:00Z",
    )
    publisher = FakePublisher(event)
    with TestClient(
        create_app(
            runtime_mode="azure",
            state_store=JsonStateStore(tmp_path / "state.json"),
            institution_sources=[MilanLocalSource(), UtrechtLocalSource()],
            late_imaging_source=MilanLateImagingSource(),
            arrival_publisher=publisher,
            event_grid_webhook_secret="event-secret",
        )
    ) as client:
        assert client.post(
            "/api/event-grid/evidence-arrivals",
            json=[
                {
                    "eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
                    "data": {"validationCode": "validation-code"},
                }
            ],
        ).json() == {"validationResponse": "validation-code"}
        assert client.post("/api/referrals", json=_command()).status_code == 201
        assert client.post("/api/cases/current/prepare").status_code == 200
        delivery = [
            {
                "eventType": "Microsoft.Storage.BlobCreated",
                "data": {
                    "url": (
                        "https://synthetic.blob.core.windows.net/source/"
                        "events/event-grid-azure-001.json"
                    )
                },
            }
        ]
        assert client.post("/api/event-grid/evidence-arrivals", json=delivery).status_code == 403
        accepted = client.post(
            "/api/event-grid/evidence-arrivals",
            json=delivery,
            headers={"X-Event-Grid-Secret": "event-secret"},
        )
        duplicate = client.post(
            "/api/evidence-arrivals",
            json=event.model_dump(mode="json"),
        )

    assert accepted.status_code == 200
    assert accepted.json() == {"accepted_event_ids": ["event-grid-azure-001"]}
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["prepared_case"]["version"] == 2
