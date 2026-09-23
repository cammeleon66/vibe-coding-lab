from pathlib import Path

from fastapi.testclient import TestClient

from collab.app import create_app
from collab.research import APPROVED_RESEARCH_FIELDS, LocalFabricAdapterFake


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


def _prepare(client: TestClient) -> None:
    assert client.post("/api/referrals", json=_command()).status_code == 201
    assert client.post("/api/cases/current/prepare").status_code == 200


def _event() -> dict[str, str]:
    return {
        "event_id": "event-grid-research-update",
        "event_type": "Microsoft.Storage.BlobCreated",
        "subject": "/synthetic/milan/CRC-EU-001/imaging",
        "case_id": "CRC-EU-001",
        "evidence_set": "baseline-and-restaging-imaging",
        "occurred_at": "2026-09-23T10:25:00Z",
    }


def _authorize(client: TestClient) -> None:
    response = client.post(
        "/api/research/authorize",
        json={"authorization_code": "research-code"},
    )
    assert response.status_code == 204


def test_clinical_role_cannot_read_or_publish_research_projection(tmp_path: Path) -> None:
    with TestClient(
        create_app(
            tmp_path / "state.json",
            research_authorization_code="research-code",
        )
    ) as client:
        _prepare(client)
        read = client.get("/api/research/projection")
        publish = client.post(
            "/api/research/projection",
            headers={"X-Demo-Role": "synthetic-researcher"},
        )
        invalid = client.post(
            "/api/research/authorize",
            json={"authorization_code": "wrong-code"},
        )

    assert read.status_code == 403
    assert publish.status_code == 403
    assert invalid.status_code == 403
    assert "clinical access is not inherited" in read.json()["detail"]


def test_projection_uses_exact_allowlist_and_excludes_workflow_and_documents(
    tmp_path: Path,
) -> None:
    adapter = LocalFabricAdapterFake()
    with TestClient(
        create_app(
            tmp_path / "state.json",
            research_adapter=adapter,
            research_authorization_code="research-code",
        )
    ) as client:
        _prepare(client)
        _authorize(client)
        response = client.post("/api/research/projection")

    assert response.status_code == 201
    projection = response.json()["projection"]
    expected_fields = ["synthetic_case_id", *APPROVED_RESEARCH_FIELDS]
    assert projection["approved_fields"] == expected_fields
    assert list(projection["record"]) == expected_fields
    serialized = str(projection).lower()
    assert "awaiting evidence preparation" not in serialized
    assert "original_content" not in serialized
    assert "<clinicaldocument" not in serialized
    assert "patient_identifier" not in serialized
    assert projection["excluded_categories"] == [
        "workflow notes",
        "direct source documents",
        "patient identifiers",
        "human opinions",
        "handoff responsibility",
    ]
    assert adapter.published[0].record == projection["record"]


def test_projection_exposes_purpose_version_and_source_lineage(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    with TestClient(create_app(state_path, research_authorization_code="research-code")) as client:
        _prepare(client)
        _authorize(client)
        published = client.post("/api/research/projection").json()

    projection = published["projection"]
    assert projection["purpose"].startswith("Synthetic cohort feasibility")
    assert projection["version"] == 1
    assert projection["schema_version"] == "research-cohort-v1"
    assert projection["case_version"] == 1
    assert {item["field"] for item in projection["lineage"]} == set(APPROVED_RESEARCH_FIELDS)
    assert all(item["prepared_claim_id"] for item in projection["lineage"])
    assert all(item["source_record_id"] for item in projection["lineage"])
    assert all(item["source_pointer"] for item in projection["lineage"])

    with TestClient(create_app(state_path, research_authorization_code="research-code")) as client:
        _authorize(client)
        restored = client.get("/api/research/projection")

    assert restored.status_code == 200
    assert restored.json() == published


def test_failed_publication_returns_unavailable_and_persists_nothing(tmp_path: Path) -> None:
    adapter = LocalFabricAdapterFake(fail_publication=True)
    with TestClient(
        create_app(
            tmp_path / "state.json",
            research_adapter=adapter,
            research_authorization_code="research-code",
        )
    ) as client:
        _prepare(client)
        _authorize(client)
        failed = client.post("/api/research/projection")
        current = client.get("/api/research/projection")

    assert failed.status_code == 503
    assert "no projection was published" in failed.json()["detail"]
    assert current.status_code == 200
    assert current.json() is None
    assert adapter.published == []


def test_failed_republication_preserves_the_last_confirmed_projection(tmp_path: Path) -> None:
    adapter = LocalFabricAdapterFake()
    with TestClient(
        create_app(
            tmp_path / "state.json",
            research_adapter=adapter,
            research_authorization_code="research-code",
        )
    ) as client:
        _prepare(client)
        _authorize(client)
        confirmed = client.post("/api/research/projection")
        assert client.post("/api/evidence-arrivals", json=_event()).status_code == 200
        adapter.fail_publication = True
        failed = client.post("/api/research/projection")
        current = client.get("/api/research/projection")

    assert confirmed.status_code == 201
    assert failed.status_code == 503
    assert current.json() == confirmed.json()
    assert len(adapter.published) == 1


def test_publication_requires_a_prepared_case(tmp_path: Path) -> None:
    with TestClient(
        create_app(
            tmp_path / "state.json",
            research_authorization_code="research-code",
        )
    ) as client:
        _authorize(client)
        response = client.post("/api/research/projection")

    assert response.status_code == 409
    assert "Prepare the synthetic case" in response.json()["detail"]


def test_local_adapter_publication_is_idempotent_by_projection_id(tmp_path: Path) -> None:
    adapter = LocalFabricAdapterFake()
    with TestClient(
        create_app(
            tmp_path / "state.json",
            research_adapter=adapter,
            research_authorization_code="research-code",
        )
    ) as client:
        _prepare(client)
        _authorize(client)
        first = client.post("/api/research/projection")
        second = client.post("/api/research/projection")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["receipt"]["id"] == second.json()["receipt"]["id"]
    assert len(adapter.published) == 1


def test_reset_revokes_the_local_research_session(tmp_path: Path) -> None:
    with TestClient(
        create_app(
            tmp_path / "state.json",
            research_authorization_code="research-code",
        )
    ) as client:
        _authorize(client)
        assert client.get("/api/research/projection").status_code == 200
        assert client.post("/api/reset").status_code == 204
        denied = client.get("/api/research/projection")

    assert denied.status_code == 403


def test_reset_revokes_all_local_research_sessions(tmp_path: Path) -> None:
    application = create_app(
        tmp_path / "state.json",
        research_authorization_code="research-code",
    )
    with (
        TestClient(application) as first,
        TestClient(application) as second,
    ):
        _authorize(first)
        _authorize(second)
        assert first.get("/api/research/projection").status_code == 200
        assert second.get("/api/research/projection").status_code == 200

        assert second.post("/api/reset").status_code == 204

        assert first.get("/api/research/projection").status_code == 403
        assert second.get("/api/research/projection").status_code == 403
