from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

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


class ReferralStatus(StrEnum):
    COLLABORATION_REQUESTED = "collaboration_requested"


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


class DemoState(BaseModel):
    current_referral: Referral | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)
