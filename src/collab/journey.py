from __future__ import annotations

from uuid import uuid4

from collab.models import (
    DemoState,
    EnterRoleAction,
    JourneyActivity,
    JourneyPatientView,
    JourneyRole,
    JourneyRoleView,
    JourneyStageId,
    JourneyStageView,
    ReferralJourneyAction,
    ReferralJourneySnapshot,
    SelectPatientAction,
    utc_now,
)
from collab.persistence import StateStore


class ReferralJourneyError(ValueError):
    pass


class ReferralJourney:
    def __init__(self, store: StateStore) -> None:
        self._store = store

    def snapshot(self) -> ReferralJourneySnapshot:
        return self._snapshot(self._store.load())

    def apply(self, action: ReferralJourneyAction) -> ReferralJourneySnapshot:
        with self._store.locked():
            state = self._store.load()
            if isinstance(action, EnterRoleAction):
                next_state = self._enter_role(state, action)
            elif isinstance(action, SelectPatientAction):
                next_state = self._select_patient(state, action)
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
