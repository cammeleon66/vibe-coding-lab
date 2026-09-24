from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from collab.app import create_app
from collab.federation import FederatedSourceError, local_milan_sources
from collab.journey import ReferralJourney, ReferralJourneyError
from collab.models import (
    EnterRoleAction,
    FederatedSourceId,
    JourneyRole,
    QuerySourceAction,
    SelectPatientAction,
    SourceCheckResult,
)
from collab.persistence import JsonStateStore


def approve_case_version_one(client: TestClient) -> None:
    client.post("/api/journey/actions", json={"type": "enter_role", "role": "milan"})
    client.post(
        "/api/journey/actions",
        json={"type": "select_patient", "patient_id": "CRC-EU-001"},
    )
    for source_id in FederatedSourceId:
        client.post(
            "/api/journey/actions",
            json={"type": "query_source", "source_id": source_id.value},
        )
    client.post(
        "/api/journey/actions",
        json={
            "type": "confirm_referral_question",
            "question": "Please assess conversion response and liver resectability.",
        },
    )
    client.post("/api/journey/actions", json={"type": "query_expert_directory"})
    client.post(
        "/api/journey/actions",
        json={
            "type": "select_destination",
            "centre_id": "utrecht-crc",
            "clinician_id": "eva-van-dijk",
        },
    )
    client.post("/api/journey/actions", json={"type": "query_requirements"})
    client.post("/api/journey/actions", json={"type": "prepare_referral_package"})
    response = client.post(
        "/api/journey/actions",
        json={
            "type": "approve_referral_package",
            "referral_assessment": (
                "Response after conversion therapy requires specialist assessment "
                "of liver resectability and the next multidisciplinary step."
            ),
        },
    )
    assert response.status_code == 200


def test_initial_snapshot_defines_roles_patients_and_six_stages(tmp_path: Path) -> None:
    journey = ReferralJourney(JsonStateStore(tmp_path / "state.json"))

    snapshot = journey.snapshot()

    assert [role.id for role in snapshot.roles] == [
        JourneyRole.MILAN,
        JourneyRole.UTRECHT,
    ]
    assert snapshot.roles[0].available is True
    assert snapshot.roles[1].available is False
    assert len(snapshot.patients) == 3
    assert [patient.case_id for patient in snapshot.patients if patient.referral_candidate] == [
        "CRC-EU-001"
    ]
    assert [stage.label for stage in snapshot.stages] == [
        "Patient",
        "Local data",
        "Referral",
        "Utrecht review",
        "Evidence update",
        "MDO outcome",
    ]
    assert snapshot.stages[0].status == "current"
    assert all(stage.status == "locked" for stage in snapshot.stages[1:])


def test_patient_selection_requires_milan_and_a_referral_candidate(tmp_path: Path) -> None:
    journey = ReferralJourney(JsonStateStore(tmp_path / "state.json"))

    with pytest.raises(ReferralJourneyError, match="Open the Milan workspace"):
        journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))

    journey.apply(EnterRoleAction(role=JourneyRole.MILAN))

    with pytest.raises(ReferralJourneyError, match="does not currently need"):
        journey.apply(SelectPatientAction(patient_id="CRC-EU-014"))

    selected = journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))

    assert selected.active_role == JourneyRole.MILAN
    assert selected.selected_patient_id == "CRC-EU-001"
    assert selected.stages[1].status == "current"
    assert [event.kind for event in selected.activity] == [
        "workspace_opened",
        "patient_selected",
    ]


def test_journey_state_restores_from_the_shared_state_store(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    first = ReferralJourney(JsonStateStore(state_path))
    first.apply(EnterRoleAction(role=JourneyRole.MILAN))
    first.apply(SelectPatientAction(patient_id="CRC-EU-001"))

    restored = ReferralJourney(JsonStateStore(state_path)).snapshot()

    assert restored.active_role == JourneyRole.MILAN
    assert restored.selected_patient_id == "CRC-EU-001"
    assert len(restored.activity) == 2


def test_three_federated_source_queries_advance_to_referral(
    tmp_path: Path,
) -> None:
    fixture_root = Path(__file__).parents[1] / "src" / "collab" / "fixtures" / "milan"
    journey = ReferralJourney(
        JsonStateStore(tmp_path / "state.json"),
        local_milan_sources(fixture_root),
    )
    journey.apply(EnterRoleAction(role=JourneyRole.MILAN))
    journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))

    for source_id in FederatedSourceId:
        snapshot = journey.apply(QuerySourceAction(source_id=source_id))

    assert [check.source_id for check in snapshot.source_checks] == list(FederatedSourceId)
    assert all(check.status == "complete" for check in snapshot.source_checks)
    assert snapshot.stages[2].status == "current"
    assert [event.kind for event in snapshot.activity][-3:] == [
        "source_queried",
        "source_queried",
        "source_queried",
    ]
    pacs = next(
        check for check in snapshot.source_checks if check.source_id == FederatedSourceId.MILAN_PACS
    )
    assert [record.status for record in pacs.records] == [
        "available",
        "missing",
        "missing",
    ]


def test_failed_source_query_remains_visible_and_blocks_referral(
    tmp_path: Path,
) -> None:
    class FailingSource:
        source_id = FederatedSourceId.MILAN_EHR
        source_label = "Milan electronic health record"
        endpoint = "/api/journey/actions · source=milan_ehr"

        def query(self, patient_id: str) -> SourceCheckResult:
            raise FederatedSourceError(f"EHR unavailable for {patient_id}.")

    journey = ReferralJourney(
        JsonStateStore(tmp_path / "state.json"),
        {FederatedSourceId.MILAN_EHR: FailingSource()},
    )
    journey.apply(EnterRoleAction(role=JourneyRole.MILAN))
    journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))

    snapshot = journey.apply(QuerySourceAction(source_id=FederatedSourceId.MILAN_EHR))

    assert snapshot.source_checks[0].status == "failed"
    assert snapshot.source_checks[0].error == "EHR unavailable for CRC-EU-001."
    assert snapshot.stages[1].status == "current"
    assert snapshot.activity[-1].kind == "source_query_failed"


def test_legacy_state_without_journey_fields_loads_with_safe_defaults(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text('{"current_referral": null}', encoding="utf-8")

    restored = ReferralJourney(JsonStateStore(state_path)).snapshot()

    assert restored.active_role is None
    assert restored.selected_patient_id is None
    assert restored.stages[0].status == "current"
    assert restored.activity == []


def test_journey_http_interface_and_reset(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        initial = client.get("/api/journey")
        entered = client.post(
            "/api/journey/actions",
            json={"type": "enter_role", "role": "milan"},
        )
        selected = client.post(
            "/api/journey/actions",
            json={"type": "select_patient", "patient_id": "CRC-EU-001"},
        )
        reset = client.post("/api/reset")
        clean = client.get("/api/journey")

    assert initial.status_code == 200
    assert entered.status_code == 200
    assert selected.status_code == 200
    assert selected.json()["selected_patient_id"] == "CRC-EU-001"
    assert reset.status_code == 204
    assert clean.json()["active_role"] is None
    assert clean.json()["selected_patient_id"] is None
    assert clean.json()["activity"] == []


def test_utrecht_workspace_is_locked_until_a_referral_is_sent(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        response = client.post(
            "/api/journey/actions",
            json={"type": "enter_role", "role": "utrecht"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Utrecht has no incoming referral yet."


def test_milan_approves_source_linked_package_before_utrecht_can_enter(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    with TestClient(create_app(state_path)) as client:
        client.post("/api/journey/actions", json={"type": "enter_role", "role": "milan"})
        client.post(
            "/api/journey/actions",
            json={"type": "select_patient", "patient_id": "CRC-EU-001"},
        )
        for source_id in FederatedSourceId:
            client.post(
                "/api/journey/actions",
                json={"type": "query_source", "source_id": source_id.value},
            )

        premature = client.post(
            "/api/journey/actions",
            json={
                "type": "approve_referral_package",
                "referral_assessment": "Referral is appropriate for specialist review.",
            },
        )
        client.post(
            "/api/journey/actions",
            json={
                "type": "confirm_referral_question",
                "question": (
                    "Please assess response to conversion therapy and liver resectability."
                ),
            },
        )
        matches = client.post(
            "/api/journey/actions",
            json={"type": "query_expert_directory"},
        ).json()
        selected = client.post(
            "/api/journey/actions",
            json={
                "type": "select_destination",
                "centre_id": "utrecht-crc",
                "clinician_id": "eva-van-dijk",
            },
        )
        requirements = client.post(
            "/api/journey/actions",
            json={"type": "query_requirements"},
        ).json()
        prepared = client.post(
            "/api/journey/actions",
            json={"type": "prepare_referral_package"},
        ).json()
        approved = client.post(
            "/api/journey/actions",
            json={
                "type": "approve_referral_package",
                "referral_assessment": (
                    "Giulia has liver-limited metastatic colorectal cancer with response "
                    "after conversion therapy. Please assess resectability and the next "
                    "multidisciplinary step."
                ),
            },
        ).json()

    restored = ReferralJourney(
        JsonStateStore(state_path),
        local_milan_sources(
            Path(__file__).parents[1] / "src" / "collab" / "fixtures" / "milan"
        ),
    ).snapshot()

    assert premature.status_code == 409
    assert matches["destinations"][0]["centre_id"] == "utrecht-crc"
    assert selected.status_code == 200
    assert [item["status"] for item in requirements["requirements"]] == [
        "missing",
        "missing",
        "present",
        "missing",
        "present",
    ]
    assert prepared["package"]["case_version"] == 1
    assert prepared["package"]["approved"] is False
    assert prepared["package"]["provenance_links"] > 0
    assert "Original CT and MRI image files" in prepared["package"]["retained_in_milan"]
    assert approved["package"]["approved"] is True
    assert approved["next_role"] == "utrecht"
    assert approved["stages"][3]["status"] == "current"
    assert approved["roles"][1]["available"] is True
    assert restored.package is not None
    assert restored.package.referral_assessment is not None


def test_utrecht_acknowledges_v1_records_opinion_and_requests_imaging(
    tmp_path: Path,
) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        approve_case_version_one(client)
        client.post("/api/journey/actions", json={"type": "enter_role", "role": "utrecht"})

        premature = client.post(
            "/api/journey/actions",
            json={
                "type": "record_provisional_opinion",
                "opinion": "The available evidence supports multidisciplinary review.",
            },
        )
        acknowledged = client.post(
            "/api/journey/actions",
            json={"type": "acknowledge_case_version", "case_version": 1},
        ).json()
        opinion = client.post(
            "/api/journey/actions",
            json={
                "type": "record_provisional_opinion",
                "opinion": (
                    "The response appears sufficient to discuss liver-directed treatment, "
                    "but original baseline CT and current liver MRI are needed before a "
                    "definitive resectability opinion."
                ),
            },
        ).json()
        requested = client.post(
            "/api/journey/actions",
            json={
                "type": "request_evidence",
                "requested_evidence": [
                    "Original baseline liver CT",
                    "Restaging liver MRI",
                ],
                "clinical_reason": (
                    "Original lesion sites and current vessel relationships must be reviewed "
                    "before the multidisciplinary resectability decision."
                ),
            },
        ).json()

    assert premature.status_code == 409
    assert acknowledged["acknowledged_versions"] == [1]
    assert "original baseline CT" in opinion["provisional_opinion"]
    assert requested["evidence_request"]["requested_by"] == "Dr Eva van Dijk"
    assert requested["evidence_request"]["case_version"] == 1
    assert requested["stages"][4]["status"] == "current"
    assert requested["next_role"] == "milan"
    assert requested["activity"][-1]["kind"] == "evidence_requested"
