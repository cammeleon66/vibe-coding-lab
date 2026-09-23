from __future__ import annotations

from uuid import uuid4

from collab.directory import ExpertDiscovery
from collab.models import (
    Referral,
    ReferralCreate,
    ReferralRequirement,
    ReferralStatus,
    RequirementStatus,
    Responsibility,
    utc_now,
)


class ReferralError(ValueError):
    pass


class ReferralService:
    def __init__(self, directory: ExpertDiscovery) -> None:
        self._directory = directory

    def create(self, command: ReferralCreate) -> Referral:
        centre = self._directory.get_centre(command.centre_id)
        if centre is None:
            raise ReferralError("Unknown expert centre.")

        clinician = next(
            (item for item in centre.clinicians if item.id == command.clinician_id),
            None,
        )
        if clinician is None:
            raise ReferralError("The selected clinician does not belong to this centre.")
        if not clinician.eligible:
            raise ReferralError("The selected clinician is not eligible for this referral.")

        available = set(command.need.available_evidence)
        requirements = [
            ReferralRequirement(
                key=requirement.key,
                label=requirement.label,
                rationale=requirement.rationale,
                status=(
                    RequirementStatus.PRESENT
                    if requirement.evidence_type in available
                    else RequirementStatus.MISSING
                ),
            )
            for requirement in centre.requirements
        ]

        return Referral(
            id=f"REF-{uuid4().hex[:8].upper()}",
            version=1,
            created_at=utc_now(),
            need=command.need,
            urgency=command.urgency,
            sender=command.sender,
            centre=centre,
            clinician=clinician,
            requirements=requirements,
            status=ReferralStatus.COLLABORATION_REQUESTED,
            responsibility=Responsibility(
                actor=command.sender.institution,
                action="Release the required synthetic evidence.",
            ),
            limitations=[
                "Synthetic demonstration referral; no real clinician was contacted.",
                (
                    "No credential, consent, reimbursement or cross-border authorization "
                    "was performed."
                ),
            ],
        )
