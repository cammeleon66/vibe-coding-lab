from __future__ import annotations

from collections.abc import Mapping
from typing import Literal
from uuid import uuid4

from collab import storyline
from collab.arrivals import EvidenceArrivalError, EvidenceArrivalService
from collab.directory import ExpertDiscovery
from collab.federation import FederatedPatientSource, FederatedSourceError
from collab.models import (
    AcceptMdoOutcomeAction,
    AcknowledgeCaseVersionAction,
    AdvanceSceneAction,
    ApproveEvidenceUpdateAction,
    ApproveReferralPackageAction,
    ApproveRegionalExchangeAction,
    ClinicalNeed,
    ConfirmReferralQuestionAction,
    DemoState,
    EvidenceArrivalEvent,
    EvidenceRequestView,
    EvidenceUpdateView,
    FederatedSourceId,
    JourneyActivity,
    JourneyDestinationView,
    JourneyMatchReasonView,
    JourneyPatientView,
    JourneyRequirementView,
    JourneyRole,
    MdoOutcomeView,
    PrepareReferralPackageAction,
    QueryExpertDirectoryAction,
    QueryRegionalSourceAction,
    QueryRequirementsAction,
    QuerySourceAction,
    ReceiveEvidenceUpdateAction,
    RecordFinalOpinionAction,
    RecordProvisionalOpinionAction,
    ReferralCreate,
    ReferralJourneyAction,
    ReferralJourneySnapshot,
    ReferralPackageView,
    ReferralSender,
    RegionalResultView,
    RegionalSourceCheckView,
    RegionalSourceId,
    RequestEvidenceAction,
    RequirementStatus,
    SceneId,
    SelectDestinationAction,
    SelectPatientAction,
    SourceCheckResult,
    SourceRecordView,
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
        evidence_arrivals: EvidenceArrivalService | None = None,
    ) -> None:
        self._store = store
        self._sources = dict(sources or {})
        self._directory = directory
        self._referral_service = referral_service
        self._preparation_service = preparation_service
        self._evidence_arrivals = evidence_arrivals

    def snapshot(self) -> ReferralJourneySnapshot:
        return self._snapshot(self._store.load())

    def apply(self, action: ReferralJourneyAction) -> ReferralJourneySnapshot:
        with self._store.locked():
            state = self._store.load()
            current_scene = SceneId(state.referral_journey.scene)
            if not storyline.action_allowed(action.type, current_scene):
                raise ReferralJourneyError(
                    f"That action is not part of the current step: "
                    f"{storyline.scene(current_scene).title}."
                )
            if isinstance(action, AdvanceSceneAction):
                next_state = self._advance_scene(state, action)
            elif isinstance(action, QueryRegionalSourceAction):
                next_state = self._query_regional_source(state, action)
            elif isinstance(action, ApproveRegionalExchangeAction):
                next_state = self._approve_regional_exchange(state)
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
            elif isinstance(action, ReceiveEvidenceUpdateAction):
                next_state = self._receive_evidence_update(state, action)
            elif isinstance(action, ApproveEvidenceUpdateAction):
                next_state = self._approve_evidence_update(state, action)
            elif isinstance(action, RecordFinalOpinionAction):
                next_state = self._record_final_opinion(state, action)
            elif isinstance(action, AcceptMdoOutcomeAction):
                next_state = self._accept_mdo_outcome(state, action)
            else:
                raise ReferralJourneyError("Unsupported referral journey action.")
            self._store.save(next_state)
            return self._snapshot(next_state)

    def _query_regional_source(
        self,
        state: DemoState,
        action: QueryRegionalSourceAction,
    ) -> DemoState:
        exchange = state.referral_journey.regional_exchange
        if action.source_id in exchange.source_checks:
            return state
        if action.source_id == RegionalSourceId.UTRECHT_PATIENT_SUMMARY:
            source_label = "Stadshaven patient-summary service"
            endpoint = "GET /fhir/Patient/CRC-NL-042/$summary"
            records = [
                SourceRecordView(
                    id="diagnosis-summary",
                    label="Oncology diagnosis summary",
                    status="available",
                    detail="Structured colorectal cancer diagnosis and current treatment.",
                ),
                SourceRecordView(
                    id="consent-directive",
                    label="Regional sharing directive",
                    status="available",
                    detail="Permits clinician-approved regional care exchange.",
                ),
            ]
        else:
            source_label = "Stadshaven imaging archive"
            endpoint = "GET /dicom/studies?patient=CRC-NL-042&modality=MR"
            records = [
                SourceRecordView(
                    id="liver-mri-report",
                    label="Latest liver MRI report",
                    status="available",
                    detail="Report dated 24 September 2026 is available at the source.",
                ),
                SourceRecordView(
                    id="liver-mri-images",
                    label="Latest liver MRI images",
                    status="available",
                    detail="Images remain in the Stadshaven imaging archive.",
                ),
            ]
        check = RegionalSourceCheckView(
            source_id=action.source_id,
            source_label=source_label,
            endpoint=endpoint,
            owner_institution=exchange.source_institution,
            requesting_institution=exchange.requesting_institution,
            status="complete",
            records=records,
            checked_at=utc_now(),
        )
        checks = {**exchange.source_checks, action.source_id: check}
        journey = state.referral_journey.model_copy(
            update={
                "regional_exchange": exchange.model_copy(update={"source_checks": checks}),
                "activity": [
                    *state.referral_journey.activity,
                    JourneyActivity(
                        id=f"ACT-{uuid4().hex[:10].upper()}",
                        kind="regional_source_queried",
                        actor="Regional oncology exchange agent",
                        institution=exchange.requesting_institution,
                        title=f"Queried {source_label}",
                        detail=(
                            f"{len(records)} source-linked records found at "
                            f"{exchange.source_institution}; source files remain hospital-owned."
                        ),
                        occurred_at=utc_now(),
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": journey})

    def _approve_regional_exchange(self, state: DemoState) -> DemoState:
        exchange = state.referral_journey.regional_exchange
        if exchange.sharing_approved:
            return state
        if not all(source_id in exchange.source_checks for source_id in RegionalSourceId):
            raise ReferralJourneyError("Check both hospital sources before approving sharing.")
        approved = exchange.model_copy(
            update={
                "sharing_approved": True,
                "approved_by": exchange.source_clinician,
                "shared_result": RegionalResultView(
                    title="Liver MRI · 24 September 2026 · Stadshaven Hospital Utrecht",
                    finding=(
                        "Both liver metastases in segments VI and VII are smaller than on the "
                        "July MRI (largest 2.2 cm, previously 3.1 cm). No new lesions."
                    ),
                    impact=[
                        "No repeat MRI is needed in Utrecht.",
                        "Today's treatment review can decide with current imaging.",
                        "The original images stay at Stadshaven and can be viewed on request.",
                    ],
                ),
                "next_responsibility": (
                    "Utrecht Regional Oncology Centre reviews the source-linked MRI "
                    "before today's treatment meeting."
                ),
            }
        )
        events = [
            JourneyActivity(
                id=f"ACT-{uuid4().hex[:10].upper()}",
                kind="regional_sharing_approved",
                actor=exchange.source_clinician,
                institution=exchange.source_institution,
                title="Approved the regional sharing request",
                detail=(
                    "The diagnosis summary and MRI report may cross the institutional "
                    "boundary; the original images remain at the source hospital."
                ),
                occurred_at=utc_now(),
            ),
            JourneyActivity(
                id=f"ACT-{uuid4().hex[:10].upper()}",
                kind="regional_exchange_completed",
                actor="Regional oncology exchange agent",
                institution=exchange.requesting_institution,
                title="Completed the nearby-hospital exchange",
                detail=approved.next_responsibility or "",
                occurred_at=utc_now(),
            ),
        ]
        journey = state.referral_journey.model_copy(
            update={
                "regional_exchange": approved,
                "activity": [*state.referral_journey.activity, *events],
            }
        )
        return state.model_copy(update={"referral_journey": journey})

    def _advance_scene(self, state: DemoState, action: AdvanceSceneAction) -> DemoState:
        journey = state.referral_journey
        current = storyline.scene(SceneId(journey.scene))
        if action.from_scene != current.id:
            if storyline.scene_index(action.from_scene) < storyline.scene_index(current.id):
                return state
            raise ReferralJourneyError("That step is not open yet.")
        blocked = current.blocked_reason(state)
        if blocked is not None:
            raise ReferralJourneyError(blocked)
        following = storyline.next_scene(current.id)
        if following is None:
            raise ReferralJourneyError("The story is complete. Reset to start again.")
        events: list[JourneyActivity] = []
        if current.id == SceneId.LOCAL_RESULT:
            events.append(
                JourneyActivity(
                    id=f"ACT-{uuid4().hex[:10].upper()}",
                    kind="scale_reveal_opened",
                    actor="European Oncology Exchange",
                    institution="Federated care network",
                    title="Expanded the collaboration view to Europe",
                    detail=(
                        "Utrecht, the Netherlands, Germany and Italy reuse the same "
                        "source ownership, provenance and clinician-approval pattern."
                    ),
                    occurred_at=utc_now(),
                )
            )
        if current.id == SceneId.SCALE_NETWORK:
            events.append(
                JourneyActivity(
                    id=f"ACT-{uuid4().hex[:10].upper()}",
                    kind="international_referral_opened",
                    actor="European Oncology Exchange",
                    institution="Federated care network",
                    title="Opened the Milan-to-Utrecht referral",
                    detail=(
                        "The detailed international journey applies the same federated "
                        "pattern across borders."
                    ),
                    occurred_at=utc_now(),
                )
            )
        active_role = journey.active_role
        if following.workspace is not None and following.workspace != active_role:
            active_role = following.workspace
            events.append(
                JourneyActivity(
                    id=f"ACT-{uuid4().hex[:10].upper()}",
                    kind="workspace_opened",
                    actor=following.actor.name,
                    institution=following.actor.institution,
                    title=f"{following.actor.name} took over in {following.actor.institution}",
                    detail=storyline.HANDOFF_CARRIED.get(
                        following.id,
                        "The hospital workspace determines the data and clinical actions "
                        "available.",
                    ),
                    occurred_at=utc_now(),
                )
            )
        next_journey = journey.model_copy(
            update={
                "scene": following.id,
                "active_role": active_role,
                "activity": [*journey.activity, *events],
            }
        )
        return state.model_copy(update={"referral_journey": next_journey})

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
        if action.case_version > 1 and action.case_version not in journey.update_approved_versions:
            raise ReferralJourneyError("Milan must approve case version 2 before acknowledgement.")
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
                "activity": [
                    *journey.activity,
                    self._utrecht_activity(
                        "evidence_requested",
                        "Requested missing imaging from Milan",
                        (f"{', '.join(requested)}. Clinical reason: {request.clinical_reason}"),
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": next_journey})

    def _receive_evidence_update(
        self,
        state: DemoState,
        action: ReceiveEvidenceUpdateAction,
    ) -> DemoState:
        journey = state.referral_journey
        if journey.active_role != JourneyRole.MILAN:
            raise ReferralJourneyError("Open the Milan workspace to receive the evidence update.")
        if journey.evidence_request is None:
            raise ReferralJourneyError("Utrecht must request the missing evidence first.")
        if state.current_referral is None or state.current_prepared_case is None:
            raise ReferralJourneyError("The current referral package is not available.")
        if action.event_id in state.processed_evidence_events:
            return state
        if self._evidence_arrivals is None:
            raise ReferralJourneyError("The evidence-arrival adapter is not configured.")
        event = EvidenceArrivalEvent(
            event_id=action.event_id,
            occurred_at=action.occurred_at,
        )
        try:
            refreshed = self._evidence_arrivals.apply(
                event,
                state.current_referral,
                state.current_prepared_case,
            )
        except (EvidenceArrivalError, PreparationError) as error:
            raise ReferralJourneyError(str(error)) from error
        next_journey = journey.model_copy(
            update={
                "update_available_version": refreshed.version,
                "activity": [
                    *journey.activity,
                    self._activity(
                        "evidence_update_received",
                        "European Oncology Exchange",
                        f"Prepared case version {refreshed.version}",
                        (
                            "The requested baseline CT and restaging MRI were linked in Milan. "
                            "Dr Bianchi must approve sharing the new version."
                        ),
                    ),
                ],
            }
        )
        return state.model_copy(
            update={
                "referral_journey": next_journey,
                "current_prepared_case": refreshed,
                "prepared_case_versions": [*state.prepared_case_versions, refreshed],
                "processed_evidence_events": {
                    **state.processed_evidence_events,
                    action.event_id: "journey-evidence-update",
                },
                "case_update_error": None,
            }
        )

    def _approve_evidence_update(
        self,
        state: DemoState,
        action: ApproveEvidenceUpdateAction,
    ) -> DemoState:
        journey = state.referral_journey
        if journey.active_role != JourneyRole.MILAN:
            raise ReferralJourneyError("Open the Milan workspace to approve the update.")
        prepared = state.current_prepared_case
        if (
            prepared is None
            or journey.update_available_version is None
            or action.case_version != prepared.version
            or action.case_version != journey.update_available_version
        ):
            raise ReferralJourneyError("Review the current evidence update before approving it.")
        if action.case_version in journey.update_approved_versions:
            return state
        next_journey = journey.model_copy(
            update={
                "update_approved_versions": [
                    *journey.update_approved_versions,
                    action.case_version,
                ],
                "activity": [
                    *journey.activity,
                    self._activity(
                        "evidence_update_approved",
                        "Dr Luca Bianchi",
                        f"Approved case version {action.case_version}",
                        "The source-linked imaging update is now available to Utrecht.",
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": next_journey})

    def _record_final_opinion(
        self,
        state: DemoState,
        action: RecordFinalOpinionAction,
    ) -> DemoState:
        self._require_utrecht_referral(state)
        prepared = state.current_prepared_case
        journey = state.referral_journey
        if prepared is None or prepared.version not in journey.update_approved_versions:
            raise ReferralJourneyError("Milan must approve case version 2 first.")
        if prepared.version not in journey.acknowledged_versions:
            raise ReferralJourneyError("Acknowledge case version 2 before final review.")
        next_journey = journey.model_copy(
            update={
                "final_opinion": action.opinion.strip(),
                "activity": [
                    *journey.activity,
                    self._utrecht_activity(
                        "final_opinion_recorded",
                        "Recorded the final specialist opinion",
                        f"The opinion applies to case version {prepared.version}.",
                    ),
                ],
            }
        )
        return state.model_copy(update={"referral_journey": next_journey})

    def _accept_mdo_outcome(
        self,
        state: DemoState,
        action: AcceptMdoOutcomeAction,
    ) -> DemoState:
        self._require_utrecht_referral(state)
        prepared = state.current_prepared_case
        journey = state.referral_journey
        if prepared is None or journey.final_opinion is None:
            raise ReferralJourneyError("Record the final specialist opinion first.")
        outcome = MdoOutcomeView(
            case_version=prepared.version,
            specialist="Dr Eva van Dijk",
            final_opinion=journey.final_opinion,
            scheduled_for=action.scheduled_for.strip(),
            accepted_at=utc_now(),
            next_responsible_actor="Dr Luca Bianchi",
            next_action=action.next_action.strip(),
        )
        next_journey = journey.model_copy(
            update={
                "mdo_outcome": outcome,
                "activity": [
                    *journey.activity,
                    self._utrecht_activity(
                        "mdo_accepted",
                        f"Accepted case version {prepared.version} into Utrecht MDO",
                        (
                            f"Scheduled for {outcome.scheduled_for}. "
                            f"Next responsibility: {outcome.next_responsible_actor}."
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
                if item.centre_id == action.centre_id and item.clinician_id == action.clinician_id
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
        return ReferralJourneySnapshot(
            storyline=storyline.build_view(state),
            regional_exchange=state.referral_journey.regional_exchange,
            active_role=state.referral_journey.active_role,
            selected_patient_id=state.referral_journey.selected_patient_id,
            patients=self._patients(),
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
            acknowledged_versions=state.referral_journey.acknowledged_versions,
            provisional_opinion=state.referral_journey.provisional_opinion,
            evidence_request=state.referral_journey.evidence_request,
            update_available_version=state.referral_journey.update_available_version,
            update_approved_versions=state.referral_journey.update_approved_versions,
            final_opinion=state.referral_journey.final_opinion,
            mdo_outcome=state.referral_journey.mdo_outcome,
            evidence_update=self._evidence_update(state),
        )

    def _evidence_update(self, state: DemoState) -> EvidenceUpdateView | None:
        prepared = state.current_prepared_case
        if prepared is None or prepared.delta is None:
            return None
        return EvidenceUpdateView(
            case_version=prepared.version,
            previous_version=prepared.delta.from_version,
            added_evidence=[item.label for item in prepared.delta.added_evidence],
            changed_findings=[
                f"{item.subject}: {item.after}" for item in prepared.delta.changed_findings
            ],
            remaining_uncertainty=prepared.delta.remaining_uncertainty,
        )

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
            "evidence_update_received",
            "evidence_update_approved",
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
            "final_opinion_recorded",
            "mdo_accepted",
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
