from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from collab.app import create_app
from collab.arrivals import EvidenceArrivalError, EvidenceArrivalService
from collab.models import EvidenceArrivalEvent, PreparedCase, Referral
from collab.preparation import CasePreparationService
from collab.sources import MilanLateImagingSource, MilanLocalSource, UtrechtLocalSource


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


def _event(event_id: str = "event-grid-local-001") -> dict[str, str]:
    return {
        "event_id": event_id,
        "event_type": "Microsoft.Storage.BlobCreated",
        "subject": "/synthetic/milan/CRC-EU-001/imaging",
        "case_id": "CRC-EU-001",
        "evidence_set": "baseline-and-restaging-imaging",
        "occurred_at": "2026-09-23T10:25:00Z",
    }


def _prepare(client: TestClient) -> dict[str, object]:
    assert client.post("/api/referrals", json=_command()).status_code == 201
    response = client.post("/api/cases/current/prepare")
    assert response.status_code == 200
    return response.json()


def test_arrival_creates_one_new_version_and_complete_delta(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        before = _prepare(client)
        response = client.post("/api/evidence-arrivals", json=_event())

        assert response.status_code == 200
        result = response.json()
        after = result["prepared_case"]
        assert result["duplicate"] is False
        assert before["version"] == 1
        assert after["version"] == 2
        assert len(after["evidence"]) == len(before["evidence"]) + 2
        assert after["delta"]["from_version"] == 1
        assert after["delta"]["to_version"] == 2
        assert {item["label"] for item in after["delta"]["added_evidence"]} == {
            "Baseline imaging",
            "Restaging imaging",
        }
        assert all(
            item["conclusion_requires_reassessment"] for item in after["delta"]["changed_findings"]
        )
        assert any("molecular" in item.lower() for item in after["delta"]["remaining_uncertainty"])
        assert any(
            "right hepatic vein" in item for item in after["delta"]["affected_human_questions"]
        )


def test_duplicate_delivery_is_idempotent_and_persists_once(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    with TestClient(create_app(state_path)) as client:
        _prepare(client)
        first = client.post("/api/evidence-arrivals", json=_event()).json()
        duplicate_event = _event()
        duplicate_event["occurred_at"] = "2026-09-23T10:26:00Z"
        duplicate = client.post("/api/evidence-arrivals", json=duplicate_event)
        versions = client.get("/api/cases/current/versions").json()

    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["prepared_case"]["version"] == 2
    assert first["prepared_case"]["version"] == 2
    assert [item["version"] for item in versions] == [1, 2]

    with TestClient(create_app(state_path)) as client:
        assert client.get("/api/cases/current").json()["version"] == 2
        assert len(client.get("/api/cases/current/versions").json()) == 2


def test_prior_version_and_its_sources_remain_immutable_and_inspectable(
    tmp_path: Path,
) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        before = _prepare(client)
        source_id = before["evidence"][0]["source_identifier"]
        client.post("/api/evidence-arrivals", json=_event())

        prior = client.get("/api/cases/current/versions/1")
        prior_source = client.get(
            f"/api/cases/current/sources/{source_id}",
            params={"version": 1},
        )

    assert prior.status_code == 200
    assert prior.json()["version"] == 1
    assert prior.json()["delta"] is None
    assert all(
        item["source_identifier"]
        not in {
            "1.2.826.0.1.3680043.10.1000.1",
            "1.2.826.0.1.3680043.10.1000.2",
        }
        for item in prior.json()["evidence"]
    )
    assert prior_source.status_code == 200
    assert prior_source.json()["source_identifier"] == source_id


def test_reused_event_id_with_changed_payload_is_rejected_without_new_version(
    tmp_path: Path,
) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        _prepare(client)
        assert client.post("/api/evidence-arrivals", json=_event()).status_code == 200
        changed = _event()
        changed["subject"] = "/synthetic/milan/CRC-EU-001/other"
        response = client.post("/api/evidence-arrivals", json=changed)

        assert response.status_code == 409
        assert client.get("/api/cases/current").json()["version"] == 2
        assert len(client.get("/api/cases/current/versions").json()) == 2


def test_arrival_failure_preserves_previous_case_and_records_visible_error(
    tmp_path: Path,
) -> None:
    class FailingArrivalService:
        def apply(self, *_args: object) -> object:
            raise EvidenceArrivalError("Synthetic imaging parser failed.")

    with TestClient(
        create_app(
            tmp_path / "state.json",
            arrival_service=FailingArrivalService(),  # type: ignore[arg-type]
        )
    ) as client:
        _prepare(client)
        response = client.post("/api/evidence-arrivals", json=_event("failed-event"))
        current = client.get("/api/cases/current")
        versions = client.get("/api/cases/current/versions")
        update_error = client.get("/api/cases/current/update-error")

    assert response.status_code == 422
    assert response.json()["detail"] == "Synthetic imaging parser failed."
    assert current.json()["version"] == 1
    assert [item["version"] for item in versions.json()] == [1]
    assert update_error.json() == {
        "event_id": "failed-event",
        "message": "Synthetic imaging parser failed.",
        "occurred_at": "2026-09-23T10:25:00Z",
        "preserved_version": 1,
    }


def test_malformed_arrival_fixture_records_error_and_preserves_case(tmp_path: Path) -> None:
    fixture_root = tmp_path / "late-imaging"
    fixture_root.mkdir()
    (fixture_root / "baseline-ct.dicom-metadata.json").write_text("{", encoding="utf-8")
    arrival_service = EvidenceArrivalService(
        MilanLateImagingSource(fixture_root),
        CasePreparationService([MilanLocalSource(), UtrechtLocalSource()]),
    )

    with TestClient(create_app(tmp_path / "state.json", arrival_service=arrival_service)) as client:
        _prepare(client)
        response = client.post("/api/evidence-arrivals", json=_event("malformed-event"))
        current = client.get("/api/cases/current")
        update_error = client.get("/api/cases/current/update-error")

    assert response.status_code == 422
    assert "could not be parsed" in response.json()["detail"]
    assert current.json()["version"] == 1
    assert update_error.json()["event_id"] == "malformed-event"
    assert update_error.json()["preserved_version"] == 1


def test_concurrent_duplicate_delivery_creates_one_version(tmp_path: Path) -> None:
    class SlowArrivalService(EvidenceArrivalService):
        def apply(
            self,
            event: EvidenceArrivalEvent,
            referral: Referral,
            previous: PreparedCase,
        ) -> PreparedCase:
            sleep(0.05)
            return super().apply(event, referral, previous)

    service = SlowArrivalService(
        MilanLateImagingSource(),
        CasePreparationService([MilanLocalSource(), UtrechtLocalSource()]),
    )
    with TestClient(create_app(tmp_path / "state.json", arrival_service=service)) as client:
        _prepare(client)
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(
                    lambda _: client.post("/api/evidence-arrivals", json=_event()),
                    range(2),
                )
            )
        versions = client.get("/api/cases/current/versions").json()

    assert all(response.status_code == 200 for response in responses)
    assert sorted(response.json()["duplicate"] for response in responses) == [False, True]
    assert [item["version"] for item in versions] == [1, 2]


def test_arrival_requires_a_prepared_case_and_supported_case_id(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        no_case = client.post("/api/evidence-arrivals", json=_event())
        _prepare(client)
        wrong_case = _event("wrong-case")
        wrong_case["case_id"] = "OTHER"
        unsupported = client.post("/api/evidence-arrivals", json=wrong_case)

    assert no_case.status_code == 409
    assert unsupported.status_code == 422
