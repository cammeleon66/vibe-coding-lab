from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from typing import Any, Protocol, cast
from urllib.parse import unquote, urlparse

from azure.core import MatchConditions
from azure.core.credentials import TokenCredential
from azure.core.exceptions import (
    AzureError,
    ResourceExistsError,
    ResourceModifiedError,
    ResourceNotFoundError,
)
from azure.storage.blob import ContainerClient, ContentSettings

from collab.models import DemoState, EvidenceArrivalEvent, EvidenceEnvelope
from collab.persistence import StateConflictError
from collab.sources import MilanLateImagingSource, MilanLocalSource, UtrechtLocalSource

logger = logging.getLogger("collab.azure")


class DownloadStream(Protocol):
    properties: Any

    def readall(self) -> bytes: ...


class BlobClient(Protocol):
    def exists(self) -> bool: ...

    def download_blob(self) -> DownloadStream: ...

    def upload_blob(
        self,
        data: bytes | str,
        *,
        overwrite: bool = False,
        content_settings: ContentSettings | None = None,
        etag: str | None = None,
        match_condition: MatchConditions | None = None,
    ) -> Any: ...

    def delete_blob(self, *, delete_snapshots: str | None = None) -> Any: ...


class BlobItem(Protocol):
    name: str


class BlobContainer(Protocol):
    container_name: str
    url: str

    def get_blob_client(self, blob: str) -> BlobClient: ...

    def list_blobs(self, *, name_starts_with: str | None = None) -> Iterator[BlobItem]: ...


def create_container_client(
    account_url: str,
    container_name: str,
    credential: TokenCredential,
) -> BlobContainer:
    return cast(
        BlobContainer,
        ContainerClient(
            account_url=account_url,
            container_name=container_name,
            credential=credential,
        ),
    )


def _download(container: BlobContainer, blob_name: str) -> bytes:
    try:
        return container.get_blob_client(blob_name).download_blob().readall()
    except AzureError as error:
        raise OSError(f"Azure Blob read failed for {blob_name}: {error}") from error


def _azure_reference(container: BlobContainer, blob_name: str) -> str:
    return f"{container.url.rstrip('/')}/{blob_name}"


def _with_azure_references(
    evidence: list[EvidenceEnvelope],
    container: BlobContainer,
    mapping: dict[str, str],
) -> list[EvidenceEnvelope]:
    return [
        item.model_copy(
            update={
                "retrieval_reference": _azure_reference(
                    container,
                    mapping[item.retrieval_reference],
                )
            }
        )
        for item in evidence
    ]


def seed_synthetic_fixtures(
    milan_container: BlobContainer,
    utrecht_container: BlobContainer,
    fixture_root: Path,
) -> int:
    uploaded = 0
    for container, institution in (
        (milan_container, "milan"),
        (utrecht_container, "utrecht"),
    ):
        for path in sorted((fixture_root / institution).iterdir()):
            if not path.is_file():
                continue
            blob = container.get_blob_client(path.name)
            if blob.exists():
                continue
            content_type = (
                "application/json"
                if path.suffix == ".json"
                else "application/xml"
                if path.suffix == ".xml"
                else "text/plain"
            )
            blob.upload_blob(
                path.read_bytes(),
                overwrite=False,
                content_settings=ContentSettings(content_type=content_type),
            )
            uploaded += 1
    logger.info("synthetic_fixtures_seeded", extra={"uploaded_count": uploaded})
    return uploaded


class AzureMilanSource:
    _mapping = {
        "fixtures/milan/referral.cda.xml": "referral.cda.xml",
        "fixtures/milan/pathology.pdf.txt": "pathology.pdf.txt",
        "fixtures/milan/treatment.local.json": "treatment.local.json",
    }

    def __init__(self, container: BlobContainer) -> None:
        self._container = container

    def read_snapshot(self, case_id: str) -> list[EvidenceEnvelope]:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for blob_name in self._mapping.values():
                (root / blob_name).write_bytes(_download(self._container, blob_name))
            evidence = MilanLocalSource(root).read_snapshot(case_id)
        logger.info(
            "institution_source_read",
            extra={"source": "milan", "case_id": case_id, "evidence_count": len(evidence)},
        )
        return _with_azure_references(evidence, self._container, self._mapping)


class AzureUtrechtSource:
    _mapping = {
        "fixtures/utrecht/referral.fhir.json": "referral.fhir.json",
        "fixtures/utrecht/review-requirements.json": "review-requirements.json",
    }

    def __init__(self, container: BlobContainer) -> None:
        self._container = container

    def read_snapshot(self, case_id: str) -> list[EvidenceEnvelope]:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for blob_name in self._mapping.values():
                (root / blob_name).write_bytes(_download(self._container, blob_name))
            evidence = UtrechtLocalSource(root).read_snapshot(case_id)
        logger.info(
            "institution_source_read",
            extra={"source": "utrecht", "case_id": case_id, "evidence_count": len(evidence)},
        )
        return _with_azure_references(evidence, self._container, self._mapping)


class AzureLateImagingSource:
    _mapping = {
        "fixtures/milan/baseline-ct.dicom-metadata.json": ("baseline-ct.dicom-metadata.json"),
        "fixtures/milan/restaging-mri.dicom-metadata.json": ("restaging-mri.dicom-metadata.json"),
    }

    def __init__(self, container: BlobContainer) -> None:
        self._container = container

    def read_arrival(self, event: EvidenceArrivalEvent) -> list[EvidenceEnvelope]:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for blob_name in self._mapping.values():
                (root / blob_name).write_bytes(_download(self._container, blob_name))
            evidence = MilanLateImagingSource(root).read_arrival(event)
        logger.info(
            "late_evidence_source_read",
            extra={"event_id": event.event_id, "evidence_count": len(evidence)},
        )
        return _with_azure_references(evidence, self._container, self._mapping)


class AzureBlobStateStore:
    def __init__(self, container: BlobContainer, blob_name: str = "demo-state.json") -> None:
        self._blob = container.get_blob_client(blob_name)
        self._lock = RLock()
        self._etag: str | None = None

    def load(self) -> DemoState:
        with self._lock:
            try:
                download = self._blob.download_blob()
                content = download.readall()
                self._etag = str(download.properties.etag)
            except ResourceNotFoundError:
                self._etag = None
                return DemoState()
            except AzureError as error:
                raise OSError(f"Azure collaboration state could not be read: {error}") from error
            return DemoState.model_validate_json(content)

    def save(self, state: DemoState) -> None:
        with self._lock:
            try:
                if self._etag is not None:
                    result = self._blob.upload_blob(
                        state.model_dump_json(indent=2),
                        overwrite=True,
                        content_settings=ContentSettings(content_type="application/json"),
                        etag=self._etag,
                        match_condition=MatchConditions.IfNotModified,
                    )
                else:
                    result = self._blob.upload_blob(
                        state.model_dump_json(indent=2),
                        overwrite=False,
                        content_settings=ContentSettings(content_type="application/json"),
                    )
                self._etag = str(result["etag"])
            except (ResourceExistsError, ResourceModifiedError) as error:
                raise StateConflictError(
                    "Azure collaboration state changed concurrently; reload before retrying."
                ) from error
            except AzureError as error:
                raise OSError(f"Azure collaboration state could not be written: {error}") from error

    def check_writable(self) -> None:
        with self._lock:
            self.save(self.load())

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self._lock:
            yield


class AzureBlobEvidenceArrivalPublisher:
    def __init__(self, container: BlobContainer, prefix: str = "events/") -> None:
        self._container = container
        self._prefix = prefix

    def publish(self, event: EvidenceArrivalEvent) -> None:
        blob_name = f"{self._prefix}{event.event_id}.json"
        try:
            self._container.get_blob_client(blob_name).upload_blob(
                event.model_dump_json(),
                overwrite=False,
                content_settings=ContentSettings(content_type="application/json"),
            )
        except ResourceExistsError:
            return
        except AzureError as error:
            raise OSError(f"Azure evidence trigger could not be published: {error}") from error

    def read_event(self, blob_url: str) -> EvidenceArrivalEvent:
        parsed = urlparse(blob_url)
        path = unquote(parsed.path).lstrip("/")
        container_name, separator, blob_name = path.partition("/")
        if (
            not separator
            or container_name != self._container.container_name
            or not blob_name.startswith(self._prefix)
        ):
            raise ValueError("The Event Grid notification is outside the approved trigger path.")
        return EvidenceArrivalEvent.model_validate_json(_download(self._container, blob_name))

    def reset(self) -> None:
        try:
            for item in self._container.list_blobs(name_starts_with=self._prefix):
                self._container.get_blob_client(item.name).delete_blob(delete_snapshots="include")
        except AzureError as error:
            raise OSError(f"Azure evidence triggers could not be reset: {error}") from error


def event_grid_blob_url(event: dict[str, object]) -> str:
    data = event.get("data")
    if not isinstance(data, dict):
        raise ValueError("The Event Grid notification has no data object.")
    url = data.get("url")
    if not isinstance(url, str) or not url:
        raise ValueError("The Event Grid notification has no blob URL.")
    return url


def subscription_validation_code(events: list[dict[str, object]]) -> str | None:
    if len(events) != 1:
        return None
    event = events[0]
    if event.get("eventType") != "Microsoft.EventGrid.SubscriptionValidationEvent":
        return None
    data = event.get("data")
    if not isinstance(data, dict):
        return None
    code = data.get("validationCode")
    return code if isinstance(code, str) and code else None


def parse_event_grid_payload(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("Event Grid payload must be an array of event objects.")
    return cast(list[dict[str, object]], payload)
