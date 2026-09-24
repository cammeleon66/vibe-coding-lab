from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from collab.app import create_app
from collab.journey import ReferralJourney, ReferralJourneyError
from collab.models import EnterRoleAction, JourneyRole, SelectPatientAction
from collab.persistence import JsonStateStore


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
