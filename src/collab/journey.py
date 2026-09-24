from __future__ import annotations

from collections.abc import Mapping
from typing import Literal
from uuid import uuid4

from collab.federation import FederatedPatientSource, FederatedSourceError
from collab.models import (
    DemoState,
    EnterRoleAction,
    FederatedSourceId,
    JourneyActivity,
    JourneyPatientView,
    JourneyRole,
    JourneyRoleView,
    JourneyStageId,
    JourneyStageView,
    QuerySourceAction,
    ReferralJourneyAction,
    ReferralJourneySnapshot,
    SelectPatientAction,
    SourceCheckResult,
    utc_now,
)
from collab.persistence import StateStore


class ReferralJourneyError(ValueError):
    pass


class ReferralJourney:
    def __init__(
        self,
        store: StateStore,
        sources: Mapping[FederatedSourceId, FederatedPatientSource] | None = None,
    ) -> None:
        self._store = store
        self._sources = dict(sources or {})

    def snapshot(self) -> ReferralJourneySnapshot:
        return self._snapshot(self._store.load())

    def apply(self, action: ReferralJourneyAction) -> ReferralJourneySnapshot:
        with self._store.locked():
            state = self._store.load()
            if isinstance(action, EnterRoleAction):
                next_state = self._enter_role(state, action)
            elif isinstance(action, SelectPatientAction):
                next_state = self._select_patient(state, action)
            elif isinstance(action, QuerySourceAction):
                next_state = self._query_source(state, action)
            else:
                raise ReferralJourneyError("Unsupported referral journey action.")
            self._store.save(next_state)
            return self._snapshot(next_state)

    def _enter_role(self, state: DemoState, action: EnterRoleAction) -> DemoState:
        if action.role == JourneyRole.UTRECHT and state.current_referral is None:
            raise ReferralJourneyError("Utrecht has no incoming referral yet.")
        clinician, institution = (
            ("Dr Luca Bianchi", "Istituto Nazionale dei Tumori, Milan")
            if action.role == JourneyRole.MILAN
            else ("Dr Eva van Dijk", "UMC Utrecht")
        )
        if state.referral_journey.active_role == action.role:
            return state
        journey = state.referral_journey.model_copy(
            update={
                "active_role": action.role,
                "activity": [
                    *state.referral_journey.activity,
                    JourneyActivity(
                        id=f"ACT-{uuid4().hex[:10].upper()}",
                        kind="workspace_opened",
                        actor=clinician,
                        institution=institution,
                        title=f"Opened the {action.role.value.title()} workspace",
                        detail=(
                            "The synthetic role determines the hospital data and "
                            "clinical actions available in this demonstration."
                        ),
                        occurred_at=utc_now(),
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": journey})

    def _query_source(self, state: DemoState, action: QuerySourceAction) -> DemoState:
        journey = state.referral_journey
        if journey.active_role != JourneyRole.MILAN or journey.selected_patient_id is None:
            raise ReferralJourneyError("Select the referral patient in the Milan workspace first.")
        source = self._sources.get(action.source_id)
        if source is None:
            raise ReferralJourneyError(f"The {action.source_id.value} source is not configured.")
        existing = journey.source_checks.get(action.source_id)
        if existing is not None and existing.status == "complete":
            return state
        try:
            result = source.query(journey.selected_patient_id)
            event_kind: Literal["source_queried", "source_query_failed"] = "source_queried"
            title = f"Queried {result.source_label}"
            available_count = sum(record.status == "available" for record in result.records)
            detail = (
                f"{available_count} of {len(result.records)} expected records are available. "
                "Missing evidence remains visible."
            )
        except FederatedSourceError as error:
            result = SourceCheckResult(
                source_id=action.source_id,
                source_label=source.source_label,
                endpoint=source.endpoint,
                patient_id=journey.selected_patient_id,
                status="failed",
                records=[],
                checked_at=utc_now(),
                error=str(error),
            )
            event_kind = "source_query_failed"
            title = f"Could not query {source.source_label}"
            detail = str(error)
        checks = {**journey.source_checks, action.source_id: result}
        next_journey = journey.model_copy(
            update={
                "source_checks": checks,
                "current_stage": (
                    JourneyStageId.REFERRAL
                    if self._source_checks_complete(checks)
                    else JourneyStageId.LOCAL_DATA
                ),
                "activity": [
                    *journey.activity,
                    JourneyActivity(
                        id=f"ACT-{uuid4().hex[:10].upper()}",
                        kind=event_kind,
                        actor="European Oncology Exchange",
                        institution="Istituto Nazionale dei Tumori, Milan",
                        title=title,
                        detail=detail,
                        occurred_at=utc_now(),
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": next_journey})

    def _select_patient(
        self,
        state: DemoState,
        action: SelectPatientAction,
    ) -> DemoState:
        if state.referral_journey.active_role != JourneyRole.MILAN:
            raise ReferralJourneyError("Open the Milan workspace before selecting a patient.")
        patient = next(
            (item for item in self._patients() if item.case_id == action.patient_id),
            None,
        )
        if patient is None:
            raise ReferralJourneyError("The selected synthetic patient was not found.")
        if not patient.referral_candidate:
            raise ReferralJourneyError(
                f"{patient.display_name} does not currently need an external referral."
            )
        if state.referral_journey.selected_patient_id == patient.case_id:
            return state
        journey = state.referral_journey.model_copy(
            update={
                "selected_patient_id": patient.case_id,
                "current_stage": JourneyStageId.LOCAL_DATA,
                "activity": [
                    *state.referral_journey.activity,
                    JourneyActivity(
                        id=f"ACT-{uuid4().hex[:10].upper()}",
                        kind="patient_selected",
                        actor="Dr Luca Bianchi",
                        institution="Istituto Nazionale dei Tumori, Milan",
                        title=f"Selected {patient.display_name} for referral preparation",
                        detail=patient.current_plan,
                        occurred_at=utc_now(),
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": journey})

    def _snapshot(self, state: DemoState) -> ReferralJourneySnapshot:
        utrecht_available = state.current_referral is not None
        recommended_role = JourneyRole.UTRECHT if utrecht_available else JourneyRole.MILAN
        return ReferralJourneySnapshot(
            active_role=state.referral_journey.active_role,
            selected_patient_id=state.referral_journey.selected_patient_id,
            roles=[
                JourneyRoleView(
                    id=JourneyRole.MILAN,
                    clinician_name="Dr Luca Bianchi",
                    institution="Istituto Nazionale dei Tumori, Milan",
                    specialty="Medical oncology",
                    responsibilities=[
                        "Select the patient",
                        "Approve referral sharing",
                        "Approve later evidence updates",
                    ],
                    available=True,
                    recommended=recommended_role == JourneyRole.MILAN,
                ),
                JourneyRoleView(
                    id=JourneyRole.UTRECHT,
                    clinician_name="Dr Eva van Dijk",
                    institution="UMC Utrecht",
                    specialty="Colorectal oncology",
                    responsibilities=[
                        "Review incoming referral",
                        "Request missing evidence",
                        "Record the specialist opinion",
                    ],
                    available=utrecht_available,
                    unavailable_reason=(
                        None if utrecht_available else "Utrecht has no incoming referral yet."
                    ),
                    recommended=recommended_role == JourneyRole.UTRECHT,
                ),
            ],
            patients=self._patients(),
            stages=self._stages(state),
            activity=state.referral_journey.activity,
            source_checks=[
                state.referral_journey.source_checks[source_id]
                for source_id in FederatedSourceId
                if source_id in state.referral_journey.source_checks
            ],
        )

    def _stages(self, state: DemoState) -> list[JourneyStageView]:
        stages = [
            (JourneyStageId.PATIENT, "Patient", None),
            (
                JourneyStageId.LOCAL_DATA,
                "Local data",
                "Select the referral patient first.",
            ),
            (
                JourneyStageId.REFERRAL,
                "Referral",
                "Complete the Milan data check first.",
            ),
            (
                JourneyStageId.UTRECHT_REVIEW,
                "Utrecht review",
                "Dr Bianchi must approve and send case version 1 first.",
            ),
            (
                JourneyStageId.EVIDENCE_UPDATE,
                "Evidence update",
                "Dr van Dijk must request the missing imaging first.",
            ),
            (
                JourneyStageId.MDO_OUTCOME,
                "MDO outcome",
                "Dr Bianchi must approve case version 2 first.",
            ),
        ]
        current_stage = self._current_stage(state)
        current_index = next(
            index for index, (stage_id, _, _) in enumerate(stages) if stage_id == current_stage
        )
        return [
            JourneyStageView(
                id=stage_id,
                label=label,
                status=(
                    "complete"
                    if index < current_index
                    else "current"
                    if index == current_index
                    else "locked"
                ),
                prerequisite=None if index <= current_index else prerequisite,
            )
            for index, (stage_id, label, prerequisite) in enumerate(stages)
        ]

    def _current_stage(self, state: DemoState) -> JourneyStageId:
        if state.handoff_manifests:
            return JourneyStageId.MDO_OUTCOME
        if state.current_prepared_case and state.current_prepared_case.version > 1:
            return JourneyStageId.EVIDENCE_UPDATE
        if state.current_referral is not None:
            return JourneyStageId.REFERRAL
        return state.referral_journey.current_stage

    def _source_checks_complete(
        self,
        checks: Mapping[FederatedSourceId, SourceCheckResult],
    ) -> bool:
        return all(
            source_id in checks and checks[source_id].status == "complete"
            for source_id in FederatedSourceId
        )

    def _patients(self) -> list[JourneyPatientView]:
        return [
            JourneyPatientView(
                case_id="CRC-EU-001",
                display_name="Giulia Moretti",
                age_band="50-59",
                diagnosis="Metastatic colorectal cancer with liver-limited metastases",
                care_status="Referral decision due",
                current_plan="Review conversion therapy response and liver resectability.",
                last_updated="23 September 2026",
                referral_candidate=True,
            ),
            JourneyPatientView(
                case_id="CRC-EU-014",
                display_name="Paolo Ricci",
                age_band="60-69",
                diagnosis="Resected stage III colorectal cancer",
                care_status="Surveillance",
                current_plan="Continue local surveillance; no external referral is due.",
                last_updated="22 September 2026",
                referral_candidate=False,
            ),
            JourneyPatientView(
                case_id="CRC-EU-022",
                display_name="Anna Greco",
                age_band="40-49",
                diagnosis="Locally advanced rectal cancer",
                care_status="Local MDO review",
                current_plan="Complete local staging before considering an external referral.",
                last_updated="21 September 2026",
                referral_candidate=False,
            ),
        ]
