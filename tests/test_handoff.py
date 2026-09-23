from pathlib import Path

from fastapi.testclient import TestClient

from collab.app import create_app


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


def _event() -> dict[str, str]:
    return {
        "event_id": "event-grid-local-handoff",
        "event_type": "Microsoft.Storage.BlobCreated",
        "subject": "/synthetic/milan/CRC-EU-001/imaging",
        "case_id": "CRC-EU-001",
        "evidence_set": "baseline-and-restaging-imaging",
        "occurred_at": "2026-09-23T10:25:00Z",
    }


def _prepare(client: TestClient) -> dict[str, object]:
    assert client.post("/api/referrals", json=_command()).status_code == 201
    prepared = client.post("/api/cases/current/prepare")
    assert prepared.status_code == 200
    return prepared.json()


def _review_payload(
    client: TestClient,
    version: int,
    *,
    resolve: bool,
) -> dict[str, object]:
    review = client.get("/api/cases/current/review").json()
    return {
        "case_version": version,
        "reviewer": "Dr Eva van Dijk",
        "opinion": (
            "The prepared evidence is suitable for multidisciplinary review; "
            "no treatment decision is made here."
        ),
        "conditions": [
            {
                "issue_id": condition["issue_id"],
                "status": "resolved" if resolve else "open",
                "resolution": (
                    "Reviewed against the source record and explicitly dispositioned."
                    if resolve
                    else ""
                ),
            }
            for condition in review["required_conditions"]
        ],
        "next_responsibility": {
            "actor": "Utrecht colorectal MDO coordinator",
            "action": "Schedule multidisciplinary review of the versioned synthetic case.",
        },
    }


def test_handoff_is_blocked_until_all_conditions_are_resolved(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        prepared = _prepare(client)
        review = client.post(
            "/api/cases/current/reviews",
            json=_review_payload(client, prepared["version"], resolve=False),
        )
        assert review.status_code == 201
        state = review.json()
        assert state["handoff_ready"] is False
        assert state["blockers"]
        assert state["opinion"]["next_responsibility"] == {
            "actor": "Utrecht colorectal MDO coordinator",
            "action": "Schedule multidisciplinary review of the versioned synthetic case.",
        }

        handoff = client.post(
            "/api/cases/current/handoffs",
            json={
                "case_version": prepared["version"],
                "opinion_id": state["opinion"]["id"],
            },
        )

    assert handoff.status_code == 422
    assert "Handoff is blocked" in handoff.json()["detail"]


def test_stale_opinion_cannot_approve_a_newer_case_version(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        prepared = _prepare(client)
        review = client.post(
            "/api/cases/current/reviews",
            json=_review_payload(client, prepared["version"], resolve=True),
        ).json()
        assert review["handoff_ready"] is True

        assert client.post("/api/evidence-arrivals", json=_event()).status_code == 200
        stale = client.get("/api/cases/current/review")
        handoff = client.post(
            "/api/cases/current/handoffs",
            json={"case_version": 2, "opinion_id": review["opinion"]["id"]},
        )
        stale_submission = client.post(
            "/api/cases/current/reviews",
            json=_review_payload(client, 1, resolve=True),
        )

    assert stale.status_code == 200
    assert stale.json()["stale"] is True
    assert stale.json()["handoff_ready"] is False
    assert "case v1" in stale.json()["blockers"][0]
    assert handoff.status_code == 422
    assert "case v1" in handoff.json()["detail"]
    assert stale_submission.status_code == 409
    assert "Case v2 is current" in stale_submission.json()["detail"]


def test_versioned_manifest_preserves_continuity_and_separate_backend_notice(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    with TestClient(
        create_app(state_path, mdo_base_url="https://mdo.example.test/review")
    ) as client:
        prepared = _prepare(client)
        assert client.post("/api/evidence-arrivals", json=_event()).status_code == 200
        review_response = client.post(
            "/api/cases/current/reviews",
            json=_review_payload(client, 2, resolve=True),
        )
        assert review_response.status_code == 201
        review = review_response.json()["opinion"]

        first = client.post(
            "/api/cases/current/handoffs",
            json={"case_version": 2, "opinion_id": review["id"]},
        )
        second = client.post(
            "/api/cases/current/handoffs",
            json={"case_version": 2, "opinion_id": review["id"]},
        )

    assert first.status_code == 201
    manifest = first.json()
    assert manifest["version"] == 1
    assert manifest["case_id"] == prepared["case_id"]
    assert manifest["clinical_question"] == prepared["clinical_question"]
    assert manifest["evidence_version"] == 2
    assert len(manifest["source_evidence_inventory"]) == len(prepared["evidence"]) + 2
    assert any("RAS status is missing" in item for item in manifest["unresolved_issues"])
    assert any("BRAF status is missing" in item for item in manifest["unresolved_issues"])
    assert any("MMR/MSI status is missing" in item for item in manifest["unresolved_issues"])
    assert (
        "DICOM pixels were not interpreted in this demonstration." in manifest["unresolved_issues"]
    )
    assert (
        "Resectability remains a human multidisciplinary conclusion."
        in manifest["unresolved_issues"]
    )
    assert manifest["responsibility"]["actor"] == "Utrecht colorectal MDO coordinator"
    assert manifest["synthetic_labels"] == [
        "synthetic-case",
        "demonstration-only",
        "not-for-clinical-use",
    ]
    assert manifest["separate_backend"] is True
    assert "separate backend" in manifest["backend_notice"]
    assert "case_id=CRC-EU-001" in manifest["launch_url"]
    assert "evidence_version=2" in manifest["launch_url"]
    assert second.status_code == 201
    assert second.json()["version"] == 2

    with TestClient(create_app(state_path)) as client:
        history = client.get("/api/cases/current/handoffs")
        reviews = client.get("/api/cases/current/reviews")

    assert [item["version"] for item in history.json()] == [1, 2]
    assert reviews.json()[0]["case_version"] == 2


def test_review_rejects_missing_conditions_and_blank_resolution(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        prepared = _prepare(client)
        payload = _review_payload(client, prepared["version"], resolve=True)
        conditions = payload["conditions"]
        assert isinstance(conditions, list)
        payload["conditions"] = conditions[:-1]
        missing = client.post("/api/cases/current/reviews", json=payload)

        blank_payload = _review_payload(client, prepared["version"], resolve=True)
        blank_conditions = blank_payload["conditions"]
        assert isinstance(blank_conditions, list)
        first_condition = blank_conditions[0]
        assert isinstance(first_condition, dict)
        first_condition["resolution"] = " "
        blank = client.post("/api/cases/current/reviews", json=blank_payload)

    assert missing.status_code == 422
    assert "explicitly address every current" in missing.json()["detail"]
    assert blank.status_code == 422
    assert blank.json()["detail"] == "Resolved conditions require a resolution note."


def test_review_rejects_whitespace_only_reviewer_and_opinion(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        prepared = _prepare(client)
        payload = _review_payload(client, prepared["version"], resolve=True)
        payload["reviewer"] = " "
        payload["opinion"] = "\t"
        response = client.post("/api/cases/current/reviews", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "The reviewer and considered opinion are required."


def test_review_and_handoff_require_a_prepared_case(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        review_state = client.get("/api/cases/current/review")
        review = client.post(
            "/api/cases/current/reviews",
            json={
                "case_version": 1,
                "reviewer": "Dr Eva van Dijk",
                "opinion": "Review.",
                "conditions": [],
                "next_responsibility": {"actor": "Coordinator", "action": "Schedule."},
            },
        )
        handoff = client.post(
            "/api/cases/current/handoffs",
            json={"case_version": 1, "opinion_id": "OP-NONE"},
        )

    assert review_state.status_code == 404
    assert review.status_code == 409
    assert handoff.status_code == 409
