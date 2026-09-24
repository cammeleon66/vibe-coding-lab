from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class MatchStatus(StrEnum):
    MATCH = "match"
    CONDITION = "condition"


class RequirementStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"


class Urgency(StrEnum):
    ROUTINE = "routine"
    EXPEDITED = "expedited"
    URGENT = "urgent"


class DemoAccessCreate(BaseModel):
    code: str = Field(min_length=1, max_length=128)


class JourneyRole(StrEnum):
    MILAN = "milan"
    UTRECHT = "utrecht"


class JourneyStageId(StrEnum):
    PATIENT = "patient"
    LOCAL_DATA = "local_data"
    REFERRAL = "referral"
    UTRECHT_REVIEW = "utrecht_review"
    EVIDENCE_UPDATE = "evidence_update"
    MDO_OUTCOME = "mdo_outcome"


class FederatedSourceId(StrEnum):
    MILAN_EHR = "milan_ehr"
    MILAN_DOCUMENTS = "milan_documents"
    MILAN_PACS = "milan_pacs"


class SourceRecordView(BaseModel):
    id: str
    label: str
    status: Literal["available", "missing"]
    detail: str


class SourceCheckResult(BaseModel):
    source_id: FederatedSourceId
    source_label: str
    endpoint: str
    patient_id: str
    status: Literal["complete", "failed"]
    records: list[SourceRecordView]
    checked_at: datetime
    error: str | None = None


class JourneyMatchReasonView(BaseModel):
    label: str
    detail: str
    status: Literal["match", "condition"]


class JourneyDestinationView(BaseModel):
    centre_id: str
    centre_name: str
    city: str
    country: str
    clinician_id: str
    clinician_name: str
    score: int
    reasons: list[JourneyMatchReasonView]
    limitations: list[str]


class JourneyRequirementView(BaseModel):
    key: str
    label: str
    rationale: str
    status: Literal["present", "missing"]


class ReferralPackageView(BaseModel):
    case_version: int
    clinical_question: str
    centre_name: str
    clinician_name: str
    requirements: list[JourneyRequirementView]
    structured_context: list[str]
    retained_in_milan: list[str]
    provenance_links: int
    missing_evidence: list[str]
    approved: bool = False
    approved_by: str | None = None
    referral_assessment: str | None = None


class EvidenceRequestView(BaseModel):
    case_version: int
    requested_evidence: list[str]
    clinical_reason: str
    requested_by: str
    requested_at: datetime


class JourneyActivity(BaseModel):
    id: str
    kind: Literal[
        "workspace_opened",
        "patient_selected",
        "source_queried",
        "source_query_failed",
        "question_confirmed",
        "directory_queried",
        "requirements_queried",
        "destination_selected",
        "package_prepared",
        "package_approved",
        "version_acknowledged",
        "provisional_opinion_recorded",
        "evidence_requested",
    ]
    actor: str
    institution: str
    title: str
    detail: str
    occurred_at: datetime


class ReferralJourneyState(BaseModel):
    active_role: JourneyRole | None = None
    selected_patient_id: str | None = None
    current_stage: JourneyStageId = JourneyStageId.PATIENT
    activity: list[JourneyActivity] = Field(default_factory=list)
    source_checks: dict[FederatedSourceId, SourceCheckResult] = Field(default_factory=dict)
    clinical_question: str | None = None
    destinations: list[JourneyDestinationView] = Field(default_factory=list)
    selected_centre_id: str | None = None
    requirements: list[JourneyRequirementView] = Field(default_factory=list)
    package: ReferralPackageView | None = None
    acknowledged_versions: list[int] = Field(default_factory=list)
    provisional_opinion: str | None = None
    evidence_request: EvidenceRequestView | None = None


class JourneyRoleView(BaseModel):
    id: JourneyRole
    clinician_name: str
    institution: str
    specialty: str
    responsibilities: list[str]
    available: bool
    unavailable_reason: str | None = None
    recommended: bool = False


class JourneyPatientView(BaseModel):
    case_id: str
    display_name: str
    age_band: str
    diagnosis: str
    care_status: str
    current_plan: str
    last_updated: str
    referral_candidate: bool
    synthetic: bool = True


class JourneyStageView(BaseModel):
    id: JourneyStageId
    label: str
    status: Literal["complete", "current", "available", "locked"]
    prerequisite: str | None = None


class ReferralJourneySnapshot(BaseModel):
    active_role: JourneyRole | None
    selected_patient_id: str | None
    roles: list[JourneyRoleView]
    patients: list[JourneyPatientView]
    stages: list[JourneyStageView]
    activity: list[JourneyActivity]
    source_checks: list[SourceCheckResult]
    clinical_question: str | None
    destinations: list[JourneyDestinationView]
    selected_centre_id: str | None
    requirements: list[JourneyRequirementView]
    package: ReferralPackageView | None
    next_role: JourneyRole | None = None
    acknowledged_versions: list[int]
    provisional_opinion: str | None
    evidence_request: EvidenceRequestView | None


class EnterRoleAction(BaseModel):
    type: Literal["enter_role"] = "enter_role"
    role: JourneyRole


class SelectPatientAction(BaseModel):
    type: Literal["select_patient"] = "select_patient"
    patient_id: str = Field(min_length=1)


class QuerySourceAction(BaseModel):
    type: Literal["query_source"] = "query_source"
    source_id: FederatedSourceId


class ConfirmReferralQuestionAction(BaseModel):
    type: Literal["confirm_referral_question"] = "confirm_referral_question"
    question: str = Field(min_length=10, max_length=500)


class QueryExpertDirectoryAction(BaseModel):
    type: Literal["query_expert_directory"] = "query_expert_directory"


class SelectDestinationAction(BaseModel):
    type: Literal["select_destination"] = "select_destination"
    centre_id: str = Field(min_length=1)
    clinician_id: str = Field(min_length=1)


class QueryRequirementsAction(BaseModel):
    type: Literal["query_requirements"] = "query_requirements"


class PrepareReferralPackageAction(BaseModel):
    type: Literal["prepare_referral_package"] = "prepare_referral_package"


class ApproveReferralPackageAction(BaseModel):
    type: Literal["approve_referral_package"] = "approve_referral_package"
    referral_assessment: str = Field(min_length=20, max_length=2000)


class AcknowledgeCaseVersionAction(BaseModel):
    type: Literal["acknowledge_case_version"] = "acknowledge_case_version"
    case_version: int = Field(ge=1)


class RecordProvisionalOpinionAction(BaseModel):
    type: Literal["record_provisional_opinion"] = "record_provisional_opinion"
    opinion: str = Field(min_length=20, max_length=2000)


class RequestEvidenceAction(BaseModel):
    type: Literal["request_evidence"] = "request_evidence"
    requested_evidence: list[str] = Field(min_length=1)
    clinical_reason: str = Field(min_length=20, max_length=1000)


ReferralJourneyAction = Annotated[
    EnterRoleAction
    | SelectPatientAction
    | QuerySourceAction
    | ConfirmReferralQuestionAction
    | QueryExpertDirectoryAction
    | SelectDestinationAction
    | QueryRequirementsAction
    | PrepareReferralPackageAction
    | ApproveReferralPackageAction
    | AcknowledgeCaseVersionAction
    | RecordProvisionalOpinionAction
    | RequestEvidenceAction,
    Field(discriminator="type"),
]


class ReferralStatus(StrEnum):
    COLLABORATION_REQUESTED = "collaboration_requested"


class TransformationStatus(StrEnum):
    ORIGINAL = "original"
    TRANSFORMED = "transformed"
    PARTIAL = "partial"


class ClaimKind(StrEnum):
    SOURCE_FACT = "source_fact"
    NORMALIZED_VALUE = "normalized_value"


class FindingSeverity(StrEnum):
    WARNING = "warning"
    REQUIRED = "required"


class ReviewConditionStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class ReviewConditionKind(StrEnum):
    REQUIRED_EVIDENCE = "required_evidence"
    REVIEW = "review"


class ClinicalNeed(BaseModel):
    case_id: str = "CRC-EU-001"
    diagnosis: str = "Metastatic colorectal cancer with liver-limited metastases"
    decision_focus: str = "Conversion therapy and liver-metastasis resectability"
    referring_country: str = "Italy"
    preferred_languages: list[str] = Field(default_factory=lambda: ["Italian", "English"])
    available_evidence: list[str] = Field(
        default_factory=lambda: ["pathology", "treatment_timeline", "current_ct_summary"]
    )


class ReferralRequirementDefinition(BaseModel):
    key: str
    label: str
    evidence_type: str
    rationale: str


class ExpertClinician(BaseModel):
    id: str
    name: str
    role: str
    specialties: list[str]
    languages: list[str]
    fictional: bool = True
    eligible: bool = True


class ExpertCentre(BaseModel):
    id: str
    name: str
    city: str
    country: str
    network_context: str
    profile_label: str
    expertise_tags: list[str]
    accepted_evidence: list[str]
    languages: list[str]
    synthetic_availability: str
    referral_pathway: str
    requirements: list[ReferralRequirementDefinition]
    clinicians: list[ExpertClinician]
    simulated: bool = True


class MatchReason(BaseModel):
    label: str
    detail: str
    status: MatchStatus


class ExpertMatch(BaseModel):
    centre: ExpertCentre
    score: int
    reasons: list[MatchReason]
    conditions: list[str]


class MatchResponse(BaseModel):
    need: ClinicalNeed
    matches: list[ExpertMatch]
    limitations: list[str]


class ReferralRequirement(BaseModel):
    key: str
    label: str
    rationale: str
    status: RequirementStatus


class ReferralSender(BaseModel):
    clinician_name: str
    institution: str
    country: str


class Responsibility(BaseModel):
    actor: str
    action: str


class ReferralCreate(BaseModel):
    need: ClinicalNeed
    centre_id: str
    clinician_id: str
    urgency: Urgency
    sender: ReferralSender


class Referral(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str
    version: int
    created_at: datetime
    need: ClinicalNeed
    urgency: Urgency
    sender: ReferralSender
    centre: ExpertCentre
    clinician: ExpertClinician
    requirements: list[ReferralRequirement]
    status: ReferralStatus
    responsibility: Responsibility
    limitations: list[str]


class EvidenceFact(BaseModel):
    key: str
    label: str
    category: str
    raw_value: str
    normalized_value: str | None = None
    transformation: str
    source_pointer: str


class EvidenceEnvelope(BaseModel):
    source_institution: str
    source_identifier: str
    source_format: str
    observed_at: datetime
    received_at: datetime
    content_hash: str
    transformation_status: TransformationStatus
    facts: list[EvidenceFact]
    warnings: list[str] = Field(default_factory=list)
    unmapped_values: list[str] = Field(default_factory=list)
    retrieval_reference: str
    original_media_type: str
    original_content: str


class ProvenanceLink(BaseModel):
    evidence_id: str
    source_pointer: str
    source_institution: str
    source_format: str
    observed_at: datetime
    transformation_status: TransformationStatus


class PreparedClaim(BaseModel):
    id: str
    label: str
    category: str
    raw_value: str
    normalized_value: str | None = None
    kind: ClaimKind
    transformation: str
    provenance: list[ProvenanceLink]


class ConflictFinding(BaseModel):
    id: str
    field: str
    description: str
    claim_ids: list[str]
    resolution: str


class MissingFinding(BaseModel):
    id: str
    field: str
    description: str
    severity: FindingSeverity
    required_by: str
    provenance: list[ProvenanceLink]


class SynthesisStatement(BaseModel):
    text: str
    support_ids: list[str]


class EvidenceChange(BaseModel):
    evidence_id: str
    label: str
    source_format: str
    source_institution: str
    observed_at: datetime


class FindingChange(BaseModel):
    subject: str
    before: str
    after: str
    conclusion_requires_reassessment: bool


class CaseDelta(BaseModel):
    from_version: int
    to_version: int
    added_evidence: list[EvidenceChange]
    changed_findings: list[FindingChange]
    remaining_uncertainty: list[str]
    affected_human_questions: list[str]


class PreparedCase(BaseModel):
    case_id: str
    referral_id: str
    version: int
    prepared_at: datetime
    clinical_question: str
    evidence: list[EvidenceEnvelope]
    claims: list[PreparedClaim]
    conflicts: list[ConflictFinding]
    missing: list[MissingFinding]
    warnings: list[str]
    unmapped_values: list[str]
    synthesis: list[SynthesisStatement]
    limitations: list[str]
    delta: CaseDelta | None = None


class EvidenceArrivalEvent(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = "Microsoft.Storage.BlobCreated"
    subject: str = "/synthetic/milan/CRC-EU-001/imaging"
    case_id: str = "CRC-EU-001"
    evidence_set: str = "baseline-and-restaging-imaging"
    occurred_at: datetime


class EvidenceArrivalResult(BaseModel):
    event_id: str
    duplicate: bool
    prepared_case: PreparedCase


class CaseUpdateError(BaseModel):
    event_id: str
    message: str
    occurred_at: datetime
    preserved_version: int


class ReviewConditionDecision(BaseModel):
    issue_id: str = Field(min_length=1)
    status: ReviewConditionStatus
    resolution: str = ""


class HumanOpinionCreate(BaseModel):
    case_version: int = Field(ge=1)
    reviewer: str = Field(min_length=1)
    opinion: str = Field(min_length=1)
    conditions: list[ReviewConditionDecision]
    next_responsibility: Responsibility


class ReviewCondition(BaseModel):
    issue_id: str
    kind: ReviewConditionKind
    description: str
    status: ReviewConditionStatus
    resolution: str


class HumanOpinion(BaseModel):
    id: str
    case_id: str
    case_version: int
    reviewer: str
    opinion: str
    conditions: list[ReviewCondition]
    next_responsibility: Responsibility
    recorded_at: datetime


class HumanReviewState(BaseModel):
    current_case_version: int
    opinion: HumanOpinion | None
    required_conditions: list[ReviewCondition]
    stale: bool
    handoff_ready: bool
    blockers: list[str]


class HandoffCreate(BaseModel):
    case_version: int = Field(ge=1)
    opinion_id: str = Field(min_length=1)


class HandoffManifest(BaseModel):
    id: str
    version: int
    case_id: str
    clinical_question: str
    evidence_version: int
    source_evidence_inventory: list[str]
    unresolved_issues: list[str]
    opinion_id: str
    responsibility: Responsibility
    created_at: datetime
    synthetic_labels: list[str]
    launch_url: str
    separate_backend: bool = True
    backend_notice: str = (
        "Version one launches the autonomous MDO demonstration with a narrative deep link. "
        "The MDO uses a separate backend and does not receive shared runtime state."
    )


class ResearchLineage(BaseModel):
    field: str
    prepared_claim_id: str
    source_record_id: str
    source_institution: str
    source_format: str
    source_pointer: str


class ResearchProjection(BaseModel):
    id: str
    purpose: str
    version: int
    schema_version: str
    case_version: int
    approved_fields: list[str]
    record: dict[str, str]
    lineage: list[ResearchLineage]
    excluded_categories: list[str]
    synthetic_only: bool = True


class ResearchPublicationReceipt(BaseModel):
    id: str
    projection_id: str
    projection_version: int
    adapter: str
    published_at: datetime


class ResearchPublication(BaseModel):
    projection: ResearchProjection
    receipt: ResearchPublicationReceipt


class ResearchAuthorizationCreate(BaseModel):
    authorization_code: str = Field(min_length=1)


class PreflightCheck(BaseModel):
    id: str
    label: str
    status: Literal["pass", "warning", "fail"]
    detail: str
    required: bool = True


class PreflightReport(BaseModel):
    ready: bool
    mode: str = "synthetic-rehearsal"
    checked_at: datetime
    checks: list[PreflightCheck]
    limitations: list[str]


class DemoState(BaseModel):
    referral_journey: ReferralJourneyState = Field(default_factory=ReferralJourneyState)
    pending_referral: Referral | None = None
    pending_prepared_case: PreparedCase | None = None
    current_referral: Referral | None = None
    current_prepared_case: PreparedCase | None = None
    prepared_case_versions: list[PreparedCase] = Field(default_factory=list)
    processed_evidence_events: dict[str, str] = Field(default_factory=dict)
    case_update_error: CaseUpdateError | None = None
    human_opinions: list[HumanOpinion] = Field(default_factory=list)
    handoff_manifests: list[HandoffManifest] = Field(default_factory=list)
    research_publication: ResearchPublication | None = None
    research_pending_projection: ResearchProjection | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)
