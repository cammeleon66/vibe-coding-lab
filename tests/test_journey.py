from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from collab.app import create_app
from collab.federation import FederatedSourceError, local_milan_sources
from collab.journey import ReferralJourney, ReferralJourneyError
from collab.models import (
    AdvanceSceneAction,
    ApproveRegionalExchangeAction,
    FederatedSourceId,
    JourneyRole,
    QueryRegionalSourceAction,
    QuerySourceAction,
    RegionalSourceId,
    SceneId,
    SelectPatientAction,
    SourceCheckResult,
)
from collab.persistence import JsonStateStore

FIXTURES = Path(__file__).parents[1] / "src" / "collab" / "fixtures" / "milan"
ASSESSMENT = (
    "Giulia has liver-limited metastatic colorectal cancer with response after conversion "
    "therapy. Please assess resectability and the next multidisciplinary step."
)


def act(client: TestClient, payload: dict[str, Any], expected: int = 200) -> dict[str, Any]:
    response = client.post("/api/journey/actions", json=payload)
    assert response.status_code == expected, response.text
    result: dict[str, Any] = response.json()
    return result


def advance(client: TestClient, scene: SceneId) -> dict[str, Any]:
    return act(client, {"type": "advance_scene", "from_scene": scene.value})


def open_cross_border(client: TestClient) -> None:
    advance(client, SceneId.LOCAL_PROBLEM)
    for source_id in RegionalSourceId:
        act(client, {"type": "query_regional_source", "source_id": source_id.value})
    advance(client, SceneId.LOCAL_SEARCH)
    act(client, {"type": "approve_regional_exchange"})
    advance(client, SceneId.LOCAL_APPROVAL)
    advance(client, SceneId.LOCAL_RESULT)
    advance(client, SceneId.SCALE_NETWORK)


def open_cross_border_direct(journey: ReferralJourney) -> None:
    journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_PROBLEM))
    for source_id in RegionalSourceId:
        journey.apply(QueryRegionalSourceAction(source_id=source_id))
    journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_SEARCH))
    journey.apply(ApproveRegionalExchangeAction())
    for scene in (SceneId.LOCAL_APPROVAL, SceneId.LOCAL_RESULT, SceneId.SCALE_NETWORK):
        journey.apply(AdvanceSceneAction(from_scene=scene))


def approve_case_version_one_from_patient(client: TestClient) -> dict[str, Any]:
    advance(client, SceneId.CROSS_PATIENT)
    for source_id in FederatedSourceId:
        act(client, {"type": "query_source", "source_id": source_id.value})
    advance(client, SceneId.CROSS_SOURCES)
    act(
        client,
        {
            "type": "confirm_referral_question",
            "question": "Please assess response to conversion therapy and liver resectability.",
        },
    )
    advance(client, SceneId.CROSS_QUESTION)
    matches = act(client, {"type": "query_expert_directory"})
    assert matches["destinations"][0]["centre_id"] == "utrecht-crc"
    act(
        client,
        {"type": "select_destination", "centre_id": "utrecht-crc", "clinician_id": "eva-van-dijk"},
    )
    advance(client, SceneId.CROSS_DESTINATION)
    act(client, {"type": "query_requirements"})
    prepared = act(client, {"type": "prepare_referral_package"})
    assert prepared["package"]["approved"] is False
    return act(client, {"type": "approve_referral_package", "referral_assessment": ASSESSMENT})


def approve_case_version_one(client: TestClient) -> dict[str, Any]:
    open_cross_border(client)
    act(client, {"type": "select_patient", "patient_id": "CRC-EU-001"})
    return approve_case_version_one_from_patient(client)


def request_imaging_after_acknowledgement(client: TestClient) -> dict[str, Any]:
    act(
        client,
        {
            "type": "record_provisional_opinion",
            "opinion": (
                "The response appears sufficient to discuss liver-directed treatment, but "
                "original baseline CT and current liver MRI are needed first."
            ),
        },
    )
    return act(
        client,
        {
            "type": "request_evidence",
            "requested_evidence": ["Original baseline liver CT", "Restaging liver MRI"],
            "clinical_reason": (
                "Original lesion sites and current vessel relationships must be reviewed "
                "before the multidisciplinary resectability decision."
            ),
        },
    )


def request_missing_imaging(client: TestClient) -> dict[str, Any]:
    approve_case_version_one(client)
    advance(client, SceneId.CROSS_PACKAGE)
    act(client, {"type": "acknowledge_case_version", "case_version": 1})
    return request_imaging_after_acknowledgement(client)


def test_initial_snapshot_opens_the_storyline_on_the_local_problem(tmp_path: Path) -> None:
    journey = ReferralJourney(JsonStateStore(tmp_path / "state.json"))

    snapshot = journey.snapshot()
    story = snapshot.storyline

    assert story.current_scene == SceneId.LOCAL_PROBLEM
    assert story.current_index == 0
    assert [chapter.status for chapter in story.chapters] == ["current", "upcoming", "upcoming"]
    assert len(story.scenes) == 14
    assert story.scenes[0].status == "current"
    assert all(scene.status == "upcoming" for scene in story.scenes[1:])
    assert story.actor.name == "Dr Sophie Bakker"
    assert story.can_advance is True
    assert story.handoff is None
    assert story.system_calls == []
    assert story.agent is not None
    assert story.agent.name == "Utrecht exchange agent"
    assert [step.status for step in story.agent.steps][:2] == ["done", "pending"]
    assert "Clinicians approve" in story.agent.boundary
    assert snapshot.active_role is None
    assert [patient.case_id for patient in snapshot.patients if patient.referral_candidate] == [
        "CRC-EU-001"
    ]


def test_clinical_actions_only_run_in_their_own_scene(tmp_path: Path) -> None:
    journey = ReferralJourney(JsonStateStore(tmp_path / "state.json"))

    with pytest.raises(ReferralJourneyError, match="not part of the current step"):
        journey.apply(QueryRegionalSourceAction(source_id=RegionalSourceId.UTRECHT_IMAGING))
    with pytest.raises(ReferralJourneyError, match="not part of the current step"):
        journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))
    with pytest.raises(ReferralJourneyError, match="not open yet"):
        journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_SEARCH))


def test_regional_exchange_shows_search_approval_payoff_and_scale(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    journey = ReferralJourney(JsonStateStore(state_path))

    searching = journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_PROBLEM))
    with pytest.raises(ReferralJourneyError, match="both Stadshaven systems"):
        journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_SEARCH))
    journey.apply(QueryRegionalSourceAction(source_id=RegionalSourceId.UTRECHT_PATIENT_SUMMARY))
    searched = journey.apply(QueryRegionalSourceAction(source_id=RegionalSourceId.UTRECHT_IMAGING))
    approval = journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_SEARCH))
    with pytest.raises(ReferralJourneyError, match="Dr Noor Jansen must approve"):
        journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_APPROVAL))
    approved = journey.apply(ApproveRegionalExchangeAction())
    result = journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_APPROVAL))
    scale = journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_RESULT))
    cross = journey.apply(AdvanceSceneAction(from_scene=SceneId.SCALE_NETWORK))

    assert searching.storyline.current_scene == SceneId.LOCAL_SEARCH
    assert searching.storyline.can_advance is False
    assert searched.storyline.can_advance is True
    assert [call.system for call in searched.storyline.system_calls] == [
        "Stadshaven patient-summary service",
        "Stadshaven imaging archive",
    ]
    assert searched.storyline.agent is not None
    assert searched.storyline.agent.steps[2].call is not None
    assert approval.storyline.actor.name == "Dr Noor Jansen"
    assert approval.storyline.handoff is not None
    assert approval.storyline.handoff.from_actor.name == "Dr Sophie Bakker"
    assert approval.regional_exchange.stays_at_source == [
        "Original MRI images",
        "Complete Stadshaven patient record",
    ]
    assert approved.regional_exchange.approved_by == "Dr Noor Jansen"
    assert approved.regional_exchange.shared_result is not None
    assert "No new lesions" in approved.regional_exchange.shared_result.finding
    assert result.storyline.current_scene == SceneId.LOCAL_RESULT
    assert scale.storyline.chapters[1].status == "current"
    assert scale.storyline.agent is None
    assert cross.storyline.current_scene == SceneId.CROSS_PATIENT
    assert cross.active_role == JourneyRole.MILAN
    assert [event.kind for event in cross.activity][-2:] == [
        "international_referral_opened",
        "workspace_opened",
    ]
    restored = ReferralJourney(JsonStateStore(state_path)).snapshot()
    assert restored.storyline.current_scene == SceneId.CROSS_PATIENT


def test_advancing_from_an_earlier_scene_is_idempotent(tmp_path: Path) -> None:
    journey = ReferralJourney(JsonStateStore(tmp_path / "state.json"))
    first = journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_PROBLEM))

    repeated = journey.apply(AdvanceSceneAction(from_scene=SceneId.LOCAL_PROBLEM))

    assert repeated.storyline.current_scene == SceneId.LOCAL_SEARCH
    assert len(repeated.activity) == len(first.activity)


def test_patient_selection_requires_a_referral_candidate(tmp_path: Path) -> None:
    journey = ReferralJourney(JsonStateStore(tmp_path / "state.json"))
    open_cross_border_direct(journey)

    with pytest.raises(ReferralJourneyError, match="does not currently need"):
        journey.apply(SelectPatientAction(patient_id="CRC-EU-014"))
    with pytest.raises(ReferralJourneyError, match="Select the patient"):
        journey.apply(AdvanceSceneAction(from_scene=SceneId.CROSS_PATIENT))

    selected = journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))

    assert selected.selected_patient_id == "CRC-EU-001"
    assert selected.storyline.can_advance is True
    assert selected.activity[-1].kind == "patient_selected"


def test_three_federated_source_queries_complete_the_agent_check(tmp_path: Path) -> None:
    journey = ReferralJourney(
        JsonStateStore(tmp_path / "state.json"), local_milan_sources(FIXTURES)
    )
    open_cross_border_direct(journey)
    journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))
    journey.apply(AdvanceSceneAction(from_scene=SceneId.CROSS_PATIENT))

    for source_id in FederatedSourceId:
        snapshot = journey.apply(QuerySourceAction(source_id=source_id))

    assert all(check.status == "complete" for check in snapshot.source_checks)
    assert snapshot.storyline.can_advance is True
    assert snapshot.storyline.agent is not None
    assert all(step.status == "done" for step in snapshot.storyline.agent.steps)
    assert "Missing:" in snapshot.storyline.agent.steps[2].detail
    assert [call.scene for call in snapshot.storyline.system_calls][-3:] == [
        SceneId.CROSS_SOURCES
    ] * 3


def test_failed_source_query_remains_visible_and_blocks_the_story(tmp_path: Path) -> None:
    class FailingSource:
        source_id = FederatedSourceId.MILAN_EHR
        source_label = "Milan electronic health record"
        endpoint = "GET /milan/ehr/patients/CRC-EU-001"

        def query(self, patient_id: str) -> SourceCheckResult:
            raise FederatedSourceError(f"EHR unavailable for {patient_id}.")

    journey = ReferralJourney(
        JsonStateStore(tmp_path / "state.json"),
        {FederatedSourceId.MILAN_EHR: FailingSource()},
    )
    open_cross_border_direct(journey)
    journey.apply(SelectPatientAction(patient_id="CRC-EU-001"))
    journey.apply(AdvanceSceneAction(from_scene=SceneId.CROSS_PATIENT))

    snapshot = journey.apply(QuerySourceAction(source_id=FederatedSourceId.MILAN_EHR))

    assert snapshot.source_checks[0].error == "EHR unavailable for CRC-EU-001."
    assert snapshot.storyline.can_advance is False
    assert "all three Milan sources" in (snapshot.storyline.blocked_reason or "")
    assert snapshot.storyline.system_calls[-1].status == "Failed"
    assert snapshot.activity[-1].kind == "source_query_failed"


def test_legacy_state_without_journey_fields_loads_with_safe_defaults(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text('{"current_referral": null}', encoding="utf-8")

    restored = ReferralJourney(JsonStateStore(state_path)).snapshot()

    assert restored.active_role is None
    assert restored.storyline.current_scene == SceneId.LOCAL_PROBLEM
    assert restored.activity == []


def test_journey_http_interface_and_reset(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        open_cross_border(client)
        selected = act(client, {"type": "select_patient", "patient_id": "CRC-EU-001"})
        reset = client.post("/api/reset")
        clean = client.get("/api/journey").json()

    assert selected["selected_patient_id"] == "CRC-EU-001"
    assert reset.status_code == 204
    assert clean["active_role"] is None
    assert clean["selected_patient_id"] is None
    assert clean["activity"] == []
    assert clean["storyline"]["current_scene"] == "local_problem"


def test_milan_approves_the_package_before_utrecht_takes_over(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    with TestClient(create_app(state_path)) as client:
        open_cross_border(client)
        act(client, {"type": "select_patient", "patient_id": "CRC-EU-001"})
        premature = act(
            client,
            {"type": "approve_referral_package", "referral_assessment": ASSESSMENT},
            expected=409,
        )
        approved = approve_case_version_one_from_patient(client)
        handover = advance(client, SceneId.CROSS_PACKAGE)

    restored = ReferralJourney(JsonStateStore(state_path), local_milan_sources(FIXTURES)).snapshot()

    assert "not part of the current step" in premature["detail"]
    assert [item["status"] for item in approved["requirements"]] == [
        "missing",
        "missing",
        "present",
        "missing",
        "present",
    ]
    assert approved["package"]["approved"] is True
    assert approved["package"]["provenance_links"] > 0
    assert "Original CT and MRI image files" in approved["package"]["retained_in_milan"]
    assert approved["storyline"]["can_advance"] is True
    assert handover["storyline"]["current_scene"] == "utrecht_review"
    assert handover["active_role"] == "utrecht"
    assert handover["storyline"]["handoff"]["from_actor"]["name"] == "Dr Luca Bianchi"
    assert handover["storyline"]["handoff"]["to_actor"]["name"] == "Dr Eva van Dijk"
    assert restored.package is not None
    assert restored.package.referral_assessment == ASSESSMENT


def test_utrecht_acknowledges_v1_records_opinion_and_requests_imaging(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        approve_case_version_one(client)
        advance(client, SceneId.CROSS_PACKAGE)
        premature = act(
            client,
            {
                "type": "record_provisional_opinion",
                "opinion": "The available evidence supports multidisciplinary review.",
            },
            expected=409,
        )
        acknowledged = act(client, {"type": "acknowledge_case_version", "case_version": 1})
        requested = request_imaging_after_acknowledgement(client)

    assert "Acknowledge case version 1" in premature["detail"]
    assert acknowledged["acknowledged_versions"] == [1]
    assert requested["evidence_request"]["requested_by"] == "Dr Eva van Dijk"
    assert requested["evidence_request"]["case_version"] == 1
    assert requested["storyline"]["can_advance"] is True
    assert requested["activity"][-1]["kind"] == "evidence_requested"


def test_version_two_and_mdo_outcome_close_the_story(tmp_path: Path) -> None:
    event = {"event_id": "journey-imaging-001", "occurred_at": "2026-09-24T09:30:00Z"}
    with TestClient(create_app(tmp_path / "state.json")) as client:
        request_missing_imaging(client)
        wrong_scene = client.post("/api/evidence-arrivals", json=event)
        advance(client, SceneId.UTRECHT_REVIEW)
        arrived = client.post("/api/evidence-arrivals", json=event).json()
        duplicate = client.post("/api/evidence-arrivals", json=event).json()
        approved = act(client, {"type": "approve_evidence_update", "case_version": 2})
        advance(client, SceneId.MILAN_UPDATE)
        premature = act(
            client,
            {
                "type": "record_final_opinion",
                "opinion": "Case version 2 supports multidisciplinary liver review.",
            },
            expected=409,
        )
        act(client, {"type": "acknowledge_case_version", "case_version": 2})
        final = act(
            client,
            {
                "type": "record_final_opinion",
                "opinion": (
                    "Case version 2 accounts for the original lesion sites and current vessel "
                    "relationships. The case is appropriate for Utrecht liver MDO review."
                ),
            },
        )
        outcome = act(
            client,
            {
                "type": "accept_mdo_outcome",
                "scheduled_for": "29 September 2026 at 14:00 CEST",
                "next_action": (
                    "Discuss the Utrecht opinion and MDO schedule with Giulia and confirm "
                    "attendance."
                ),
            },
        )
        closing = advance(client, SceneId.UTRECHT_MDO)
        beyond = act(
            client,
            {"type": "advance_scene", "from_scene": "closing_outcome"},
            expected=409,
        )

    assert wrong_scene.status_code == 409
    assert arrived["prepared_case"]["version"] == 2
    assert duplicate["duplicate"] is True
    assert approved["update_approved_versions"] == [2]
    assert approved["storyline"]["system_calls"][-1]["id"] == "evidence-arrival"
    assert "Acknowledge case version 2" in premature["detail"]
    assert "original lesion sites" in final["final_opinion"]
    assert outcome["mdo_outcome"]["case_version"] == 2
    assert closing["storyline"]["current_scene"] == "closing_outcome"
    assert closing["storyline"]["can_advance"] is False
    assert closing["active_role"] == "milan"
    assert closing["mdo_outcome"]["next_responsible_actor"] == "Dr Luca Bianchi"
    assert "story is complete" in beyond["detail"]
