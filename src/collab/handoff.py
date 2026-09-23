from __future__ import annotations

from urllib.parse import urlencode
from uuid import uuid4

from collab.models import (
    FindingSeverity,
    HandoffManifest,
    HumanOpinion,
    HumanOpinionCreate,
    HumanReviewState,
    PreparedCase,
    ReviewCondition,
    ReviewConditionKind,
    ReviewConditionStatus,
    utc_now,
)


class HandoffError(ValueError):
    pass


class CollaborationWorkflow:
    def __init__(self, mdo_base_url: str) -> None:
        self._mdo_base_url = mdo_base_url.rstrip("/")

    def review_state(
        self,
        prepared: PreparedCase,
        opinion: HumanOpinion | None,
    ) -> HumanReviewState:
        required = self._required_conditions(prepared)
        stale = opinion is not None and opinion.case_version != prepared.version
        conditions = required if opinion is None or stale else opinion.conditions
        blockers: list[str] = []
        if opinion is None:
            blockers.append(f"Record a human opinion for case v{prepared.version}.")
        elif stale:
            blockers.append(
                f"Opinion {opinion.id} applies to case v{opinion.case_version}; "
                f"case v{prepared.version} requires a new review."
            )
        else:
            blockers.extend(
                f"Resolve {condition.kind.value.replace('_', ' ')} condition {condition.issue_id}."
                for condition in conditions
                if condition.status == ReviewConditionStatus.OPEN
            )
        return HumanReviewState(
            current_case_version=prepared.version,
            opinion=opinion,
            required_conditions=conditions,
            stale=stale,
            handoff_ready=not blockers,
            blockers=blockers,
        )

    def record_opinion(
        self,
        prepared: PreparedCase,
        command: HumanOpinionCreate,
    ) -> HumanOpinion:
        if command.case_version != prepared.version:
            raise HandoffError(
                f"Case v{prepared.version} is current; review case v{prepared.version} "
                "before recording an opinion."
            )
        if not command.reviewer.strip() or not command.opinion.strip():
            raise HandoffError("The reviewer and considered opinion are required.")
        required = self._required_conditions(prepared)
        required_by_id = {condition.issue_id: condition for condition in required}
        decisions_by_id = {decision.issue_id: decision for decision in command.conditions}
        if len(decisions_by_id) != len(command.conditions):
            raise HandoffError("Each review condition may be submitted only once.")
        if set(decisions_by_id) != set(required_by_id):
            raise HandoffError(
                "The opinion must explicitly address every current required evidence "
                "and review condition."
            )
        conditions = [
            condition.model_copy(
                update={
                    "status": decisions_by_id[condition.issue_id].status,
                    "resolution": decisions_by_id[condition.issue_id].resolution.strip(),
                }
            )
            for condition in required
        ]
        if any(
            condition.status == ReviewConditionStatus.RESOLVED and not condition.resolution
            for condition in conditions
        ):
            raise HandoffError("Resolved conditions require a resolution note.")
        if (
            not command.next_responsibility.actor.strip()
            or not command.next_responsibility.action.strip()
        ):
            raise HandoffError("The next responsible actor and action are required.")
        return HumanOpinion(
            id=f"OP-{uuid4().hex[:8].upper()}",
            case_id=prepared.case_id,
            case_version=prepared.version,
            reviewer=command.reviewer.strip(),
            opinion=command.opinion.strip(),
            conditions=conditions,
            next_responsibility=command.next_responsibility.model_copy(
                update={
                    "actor": command.next_responsibility.actor.strip(),
                    "action": command.next_responsibility.action.strip(),
                }
            ),
            recorded_at=utc_now(),
        )

    def create_manifest(
        self,
        prepared: PreparedCase,
        opinion: HumanOpinion | None,
        version: int,
    ) -> HandoffManifest:
        state = self.review_state(prepared, opinion)
        if not state.handoff_ready or opinion is None:
            raise HandoffError("Handoff is blocked: " + " ".join(state.blockers))
        unresolved_candidates = [
            *(finding.description for finding in prepared.missing),
            *(finding.description for finding in prepared.conflicts),
            *(prepared.delta.remaining_uncertainty if prepared.delta else []),
        ]
        unresolved = list(dict.fromkeys(unresolved_candidates))
        manifest_id = f"MDO-{prepared.case_id}-V{version}"
        query = urlencode(
            {
                "case_id": prepared.case_id,
                "evidence_version": prepared.version,
                "handoff_manifest": manifest_id,
            }
        )
        return HandoffManifest(
            id=manifest_id,
            version=version,
            case_id=prepared.case_id,
            clinical_question=prepared.clinical_question,
            evidence_version=prepared.version,
            source_evidence_inventory=[
                evidence.source_identifier for evidence in prepared.evidence
            ],
            unresolved_issues=unresolved,
            opinion_id=opinion.id,
            responsibility=opinion.next_responsibility,
            created_at=utc_now(),
            synthetic_labels=[
                "synthetic-case",
                "demonstration-only",
                "not-for-clinical-use",
            ],
            launch_url=f"{self._mdo_base_url}?{query}",
        )

    def _required_conditions(self, prepared: PreparedCase) -> list[ReviewCondition]:
        conditions = [
            ReviewCondition(
                issue_id=finding.id,
                kind=ReviewConditionKind.REQUIRED_EVIDENCE,
                description=finding.description,
                status=ReviewConditionStatus.OPEN,
                resolution="",
            )
            for finding in prepared.missing
            if finding.severity == FindingSeverity.REQUIRED
        ]
        conditions.extend(
            ReviewCondition(
                issue_id=finding.id,
                kind=ReviewConditionKind.REVIEW,
                description=finding.description,
                status=ReviewConditionStatus.OPEN,
                resolution="",
            )
            for finding in prepared.conflicts
        )
        return conditions
