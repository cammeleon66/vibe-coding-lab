from __future__ import annotations

from collections.abc import Mapping
from typing import Literal
from uuid import uuid4

from collab.directory import ExpertDiscovery
from collab.federation import FederatedPatientSource, FederatedSourceError
from collab.models import (
    AcknowledgeCaseVersionAction,
    ApproveReferralPackageAction,
    ClinicalNeed,
    ConfirmReferralQuestionAction,
    DemoState,
    EnterRoleAction,
    EvidenceRequestView,
    FederatedSourceId,
    JourneyActivity,
    JourneyDestinationView,
    JourneyMatchReasonView,
    JourneyPatientView,
    JourneyRequirementView,
    JourneyRole,
    JourneyRoleView,
    JourneyStageId,
    JourneyStageView,
    PrepareReferralPackageAction,
    QueryExpertDirectoryAction,
    QueryRequirementsAction,
    QuerySourceAction,
    RecordProvisionalOpinionAction,
    ReferralCreate,
    ReferralJourneyAction,
    ReferralJourneySnapshot,
    ReferralPackageView,
    ReferralSender,
    RequestEvidenceAction,
    RequirementStatus,
    SelectDestinationAction,
    SelectPatientAction,
    SourceCheckResult,
    Urgency,
    utc_now,
)
from collab.persistence import StateStore
from collab.preparation import CasePreparationService, PreparationError
from collab.referrals import ReferralError, ReferralService


class ReferralJourneyError(ValueError):
    pass


class ReferralJourney:
    def __init__(
        self,
        store: StateStore,
        sources: Mapping[FederatedSourceId, FederatedPatientSource] | None = None,
        directory: ExpertDiscovery | None = None,
        referral_service: ReferralService | None = None,
        preparation_service: CasePreparationService | None = None,
    ) -> None:
        self._store = store
        self._sources = dict(sources or {})
        self._directory = directory
        self._referral_service = referral_service
        self._preparation_service = preparation_service

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
            elif isinstance(action, ConfirmReferralQuestionAction):
                next_state = self._confirm_question(state, action)
            elif isinstance(action, QueryExpertDirectoryAction):
                next_state = self._query_directory(state)
            elif isinstance(action, SelectDestinationAction):
                next_state = self._select_destination(state, action)
            elif isinstance(action, QueryRequirementsAction):
                next_state = self._query_requirements(state)
            elif isinstance(action, PrepareReferralPackageAction):
                next_state = self._prepare_package(state)
            elif isinstance(action, ApproveReferralPackageAction):
                next_state = self._approve_package(state, action)
            elif isinstance(action, AcknowledgeCaseVersionAction):
                next_state = self._acknowledge_version(state, action)
            elif isinstance(action, RecordProvisionalOpinionAction):
                next_state = self._record_provisional_opinion(state, action)
            elif isinstance(action, RequestEvidenceAction):
                next_state = self._request_evidence(state, action)
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

    def _confirm_question(
        self,
        state: DemoState,
        action: ConfirmReferralQuestionAction,
    ) -> DemoState:
        self._require_milan_referral_stage(state)
        question = action.question.strip()
        if state.referral_journey.clinical_question == question:
            return state
        journey = state.referral_journey.model_copy(
            update={
                "clinical_question": question,
                "destinations": [],
                "selected_centre_id": None,
                "requirements": [],
                "package": None,
                "activity": [
                    *state.referral_journey.activity,
                    self._activity(
                        "question_confirmed",
                        "Dr Luca Bianchi",
                        "Confirmed the referral question",
                        question,
                    ),
                ],
            }
        )
        return state.model_copy(
            update={
                "referral_journey": journey,
                "pending_referral": None,
                "pending_prepared_case": None,
            }
        )

    def _acknowledge_version(
        self,
        state: DemoState,
        action: AcknowledgeCaseVersionAction,
    ) -> DemoState:
        self._require_utrecht_referral(state)
        prepared = state.current_prepared_case
        if prepared is None or action.case_version != prepared.version:
            current = prepared.version if prepared is not None else 0
            raise ReferralJourneyError(
                f"Case version {current} is current; acknowledge that version first."
            )
        journey = state.referral_journey
        if action.case_version in journey.acknowledged_versions:
            return state
        next_journey = journey.model_copy(
            update={
                "acknowledged_versions": [
                    *journey.acknowledged_versions,
                    action.case_version,
                ],
                "activity": [
                    *journey.activity,
                    self._utrecht_activity(
                        "version_acknowledged",
                        f"Acknowledged case version {action.case_version}",
                        "Dr van Dijk confirmed the exact source-linked package under review.",
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": next_journey})

    def _record_provisional_opinion(
        self,
        state: DemoState,
        action: RecordProvisionalOpinionAction,
    ) -> DemoState:
        self._require_utrecht_referral(state)
        prepared = state.current_prepared_case
        if prepared is None or prepared.version not in state.referral_journey.acknowledged_versions:
            raise ReferralJourneyError("Acknowledge case version 1 before recording an opinion.")
        opinion = action.opinion.strip()
        journey = state.referral_journey.model_copy(
            update={
                "provisional_opinion": opinion,
                "activity": [
                    *state.referral_journey.activity,
                    self._utrecht_activity(
                        "provisional_opinion_recorded",
                        "Recorded a provisional specialist opinion",
                        "The opinion is owned by Dr Eva van Dijk and applies to case version 1.",
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": journey})

    def _request_evidence(
        self,
        state: DemoState,
        action: RequestEvidenceAction,
    ) -> DemoState:
        self._require_utrecht_referral(state)
        journey = state.referral_journey
        prepared = state.current_prepared_case
        if prepared is None or prepared.version not in journey.acknowledged_versions:
            raise ReferralJourneyError("Acknowledge the current case version first.")
        if journey.provisional_opinion is None:
            raise ReferralJourneyError(
                "Record Dr van Dijk's provisional opinion before requesting evidence."
            )
        package = journey.package
        if package is None:
            raise ReferralJourneyError("The approved referral package is not available.")
        allowed = set(package.missing_evidence)
        requested = list(dict.fromkeys(action.requested_evidence))
        if not set(requested) <= allowed:
            raise ReferralJourneyError(
                "Request only evidence identified as missing in the package."
            )
        request = EvidenceRequestView(
            case_version=prepared.version,
            requested_evidence=requested,
            clinical_reason=action.clinical_reason.strip(),
            requested_by="Dr Eva van Dijk",
            requested_at=utc_now(),
        )
        next_journey = journey.model_copy(
            update={
                "evidence_request": request,
                "current_stage": JourneyStageId.EVIDENCE_UPDATE,
                "activity": [
                    *journey.activity,
                    self._utrecht_activity(
                        "evidence_requested",
                        "Requested missing imaging from Milan",
                        (
                            f"{', '.join(requested)}. "
                            f"Clinical reason: {request.clinical_reason}"
                        ),
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": next_journey})

    def _query_directory(self, state: DemoState) -> DemoState:
        self._require_milan_referral_stage(state)
        if state.referral_journey.clinical_question is None:
            raise ReferralJourneyError("Confirm the referral question first.")
        if self._directory is None:
            raise ReferralJourneyError("The expert directory is not configured.")
        response = self._directory.find_matches(
            self._clinical_need(state.referral_journey.clinical_question)
        )
        destinations = [
            JourneyDestinationView(
                centre_id=match.centre.id,
                centre_name=match.centre.name,
                city=match.centre.city,
                country=match.centre.country,
                clinician_id=next(
                    clinician.id for clinician in match.centre.clinicians if clinician.eligible
                ),
                clinician_name=next(
                    clinician.name for clinician in match.centre.clinicians if clinician.eligible
                ),
                score=match.score,
                reasons=[
                    JourneyMatchReasonView(
                        label=reason.label,
                        detail=reason.detail,
                        status=reason.status.value,
                    )
                    for reason in match.reasons
                ],
                limitations=response.limitations,
            )
            for match in response.matches
            if any(clinician.eligible for clinician in match.centre.clinicians)
        ]
        journey = state.referral_journey.model_copy(
            update={
                "destinations": destinations,
                "activity": [
                    *state.referral_journey.activity,
                    self._activity(
                        "directory_queried",
                        "European Oncology Exchange",
                        "Queried the synthetic expert directory",
                        f"{len(destinations)} bounded destination matches returned.",
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": journey})

    def _select_destination(
        self,
        state: DemoState,
        action: SelectDestinationAction,
    ) -> DemoState:
        self._require_milan_referral_stage(state)
        destination = next(
            (
                item
                for item in state.referral_journey.destinations
                if item.centre_id == action.centre_id
                and item.clinician_id == action.clinician_id
            ),
            None,
        )
        if destination is None:
            raise ReferralJourneyError("Query the directory before selecting this destination.")
        journey = state.referral_journey.model_copy(
            update={
                "selected_centre_id": destination.centre_id,
                "requirements": [],
                "package": None,
                "activity": [
                    *state.referral_journey.activity,
                    self._activity(
                        "destination_selected",
                        "Dr Luca Bianchi",
                        f"Selected {destination.centre_name}",
                        f"{destination.clinician_name} will receive the approved referral.",
                    ),
                ],
            }
        )
        return state.model_copy(
            update={
                "referral_journey": journey,
                "pending_referral": None,
                "pending_prepared_case": None,
            }
        )

    def _query_requirements(self, state: DemoState) -> DemoState:
        self._require_milan_referral_stage(state)
        centre_id = state.referral_journey.selected_centre_id
        if centre_id is None:
            raise ReferralJourneyError("Select the referral destination first.")
        if self._directory is None:
            raise ReferralJourneyError("The destination requirements adapter is not configured.")
        definitions = self._directory.get_requirements(centre_id)
        if not definitions:
            raise ReferralJourneyError("No referral requirements were found for this centre.")
        available = set(self._clinical_need("").available_evidence)
        requirements = [
            JourneyRequirementView(
                key=item.key,
                label=item.label,
                rationale=item.rationale,
                status=(
                    RequirementStatus.PRESENT.value
                    if item.evidence_type in available
                    else RequirementStatus.MISSING.value
                ),
            )
            for item in definitions
        ]
        journey = state.referral_journey.model_copy(
            update={
                "requirements": requirements,
                "activity": [
                    *state.referral_journey.activity,
                    self._activity(
                        "requirements_queried",
                        "European Oncology Exchange",
                        "Queried Utrecht referral requirements",
                        (
                            f"{sum(item.status == 'present' for item in requirements)} of "
                            f"{len(requirements)} requirements are currently present."
                        ),
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": journey})

    def _prepare_package(self, state: DemoState) -> DemoState:
        self._require_milan_referral_stage(state)
        journey = state.referral_journey
        if journey.clinical_question is None:
            raise ReferralJourneyError("Confirm the referral question first.")
        if journey.selected_centre_id is None or not journey.requirements:
            raise ReferralJourneyError("Select Utrecht and query its requirements first.")
        destination = next(
            item for item in journey.destinations if item.centre_id == journey.selected_centre_id
        )
        if self._referral_service is None or self._preparation_service is None:
            raise ReferralJourneyError("Referral package preparation is not configured.")
        try:
            referral = self._referral_service.create(
                ReferralCreate(
                    need=self._clinical_need(journey.clinical_question),
                    centre_id=destination.centre_id,
                    clinician_id=destination.clinician_id,
                    urgency=Urgency.EXPEDITED,
                    sender=ReferralSender(
                        clinician_name="Dr Luca Bianchi",
                        institution="Istituto Nazionale dei Tumori, Milan",
                        country="Italy",
                    ),
                )
            )
            prepared = self._preparation_service.prepare(referral)
        except (ReferralError, PreparationError) as error:
            raise ReferralJourneyError(str(error)) from error
        package = ReferralPackageView(
            case_version=prepared.version,
            clinical_question=prepared.clinical_question,
            centre_name=destination.centre_name,
            clinician_name=destination.clinician_name,
            requirements=journey.requirements,
            structured_context=[
                "Referral question and clinical summary",
                "Treatment and response timeline",
                "Evidence inventory and source provenance",
                "Available pathology and imaging summaries",
            ],
            retained_in_milan=[
                "Original pathology document",
                "Original CT and MRI image files",
                "Milan electronic health record",
            ],
            provenance_links=sum(len(claim.provenance) for claim in prepared.claims),
            missing_evidence=[
                item.label for item in journey.requirements if item.status == "missing"
            ],
        )
        next_journey = journey.model_copy(
            update={
                "package": package,
                "activity": [
                    *journey.activity,
                    self._activity(
                        "package_prepared",
                        "European Oncology Exchange",
                        "Prepared case version 1",
                        (
                            "Structured context and provenance are ready for approval; "
                            "original source files remain in Milan."
                        ),
                    ),
                ],
            }
        )
        return state.model_copy(
            update={
                "referral_journey": next_journey,
                "pending_referral": referral,
                "pending_prepared_case": prepared,
            }
        )

    def _approve_package(
        self,
        state: DemoState,
        action: ApproveReferralPackageAction,
    ) -> DemoState:
        self._require_milan_referral_stage(state)
        journey = state.referral_journey
        if journey.package is None or state.pending_referral is None:
            raise ReferralJourneyError("Prepare case version 1 before approving it.")
        if state.pending_prepared_case is None:
            raise ReferralJourneyError("The prepared case is not available.")
        assessment = action.referral_assessment.strip()
        package = journey.package.model_copy(
            update={
                "approved": True,
                "approved_by": "Dr Luca Bianchi",
                "referral_assessment": assessment,
            }
        )
        next_journey = journey.model_copy(
            update={
                "package": package,
                "current_stage": JourneyStageId.UTRECHT_REVIEW,
                "activity": [
                    *journey.activity,
                    self._activity(
                        "package_approved",
                        "Dr Luca Bianchi",
                        "Approved and sent case version 1",
                        "Utrecht can now acknowledge the source-linked referral package.",
                    ),
                ],
            }
        )
        return state.model_copy(
            update={
                "referral_journey": next_journey,
                "current_referral": state.pending_referral,
                "current_prepared_case": state.pending_prepared_case,
                "prepared_case_versions": [state.pending_prepared_case],
                "pending_referral": None,
                "pending_prepared_case": None,
            }
        )

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
            clinical_question=state.referral_journey.clinical_question,
            destinations=state.referral_journey.destinations,
            selected_centre_id=state.referral_journey.selected_centre_id,
            requirements=state.referral_journey.requirements,
            package=state.referral_journey.package,
            next_role=(
                JourneyRole.MILAN
                if state.referral_journey.evidence_request is not None
                else JourneyRole.UTRECHT
                if state.current_referral is not None
                else None
            ),
            acknowledged_versions=state.referral_journey.acknowledged_versions,
            provisional_opinion=state.referral_journey.provisional_opinion,
            evidence_request=state.referral_journey.evidence_request,
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
        if state.referral_journey.evidence_request is not None:
            return JourneyStageId.EVIDENCE_UPDATE
        if state.current_prepared_case and state.current_prepared_case.version > 1:
            return JourneyStageId.EVIDENCE_UPDATE
        if state.current_referral is not None:
            return JourneyStageId.UTRECHT_REVIEW
        return state.referral_journey.current_stage

    def _require_milan_referral_stage(self, state: DemoState) -> None:
        journey = state.referral_journey
        if journey.active_role != JourneyRole.MILAN:
            raise ReferralJourneyError("Open the Milan workspace first.")
        if not self._source_checks_complete(journey.source_checks):
            raise ReferralJourneyError("Complete the Milan data check first.")

    def _clinical_need(self, question: str) -> ClinicalNeed:
        return ClinicalNeed(
            decision_focus=question or "Conversion therapy and liver-metastasis resectability"
        )

    def _activity(
        self,
        kind: Literal[
            "question_confirmed",
            "directory_queried",
            "requirements_queried",
            "destination_selected",
            "package_prepared",
            "package_approved",
        ],
        actor: str,
        title: str,
        detail: str,
    ) -> JourneyActivity:
        return JourneyActivity(
            id=f"ACT-{uuid4().hex[:10].upper()}",
            kind=kind,
            actor=actor,
            institution="Istituto Nazionale dei Tumori, Milan",
            title=title,
            detail=detail,
            occurred_at=utc_now(),
        )

    def _require_utrecht_referral(self, state: DemoState) -> None:
        if state.referral_journey.active_role != JourneyRole.UTRECHT:
            raise ReferralJourneyError("Open the Utrecht workspace first.")
        if state.current_referral is None or state.current_prepared_case is None:
            raise ReferralJourneyError("Utrecht has no approved referral package.")

    def _utrecht_activity(
        self,
        kind: Literal[
            "version_acknowledged",
            "provisional_opinion_recorded",
            "evidence_requested",
        ],
        title: str,
        detail: str,
    ) -> JourneyActivity:
        return JourneyActivity(
            id=f"ACT-{uuid4().hex[:10].upper()}",
            kind=kind,
            actor="Dr Eva van Dijk",
            institution="UMC Utrecht",
            title=title,
            detail=detail,
            occurred_at=utc_now(),
        )

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
