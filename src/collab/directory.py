from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from collab.models import (
    ClinicalNeed,
    ExpertCentre,
    ExpertMatch,
    MatchReason,
    MatchResponse,
    MatchStatus,
    ReferralRequirementDefinition,
)


class ExpertDiscovery(Protocol):
    def find_matches(self, need: ClinicalNeed) -> MatchResponse: ...

    def get_centre(self, centre_id: str) -> ExpertCentre | None: ...

    def get_requirements(self, centre_id: str) -> list[ReferralRequirementDefinition]: ...


class SyntheticExpertDirectory:
    def __init__(self, fixture_path: Path | None = None) -> None:
        path = fixture_path or Path(__file__).parent / "fixtures" / "expert_centres.json"
        raw_centres = json.loads(path.read_text(encoding="utf-8"))
        self._centres = [ExpertCentre.model_validate(item) for item in raw_centres]

    def get_centre(self, centre_id: str) -> ExpertCentre | None:
        return next((centre for centre in self._centres if centre.id == centre_id), None)

    def get_requirements(self, centre_id: str) -> list[ReferralRequirementDefinition]:
        centre = self.get_centre(centre_id)
        return [] if centre is None else centre.requirements

    def find_matches(self, need: ClinicalNeed) -> MatchResponse:
        matches = [self._score(centre, need) for centre in self._centres]
        matches.sort(key=lambda match: (-match.score, match.centre.name))
        return MatchResponse(
            need=need,
            matches=matches,
            limitations=[
                "This is a curated synthetic directory, not an exhaustive European registry.",
                "Credentials, permissions, availability and interoperability are simulated.",
                "A real referral would follow institutional and national authorization pathways.",
            ],
        )

    def _score(self, centre: ExpertCentre, need: ClinicalNeed) -> ExpertMatch:
        searchable = " ".join(centre.expertise_tags).casefold()
        diagnosis_terms = {"colorectal", "metastatic", "liver"}
        focus_terms = {"conversion", "resectability", "hepatobiliary"}

        diagnosis_hits = sorted(term for term in diagnosis_terms if term in searchable)
        focus_hits = sorted(term for term in focus_terms if term in searchable)
        evidence_hits = sorted(set(need.available_evidence) & set(centre.accepted_evidence))
        language_hits = sorted(set(need.preferred_languages) & set(centre.languages))

        score = len(diagnosis_hits) * 12
        score += len(focus_hits) * 15
        score += len(evidence_hits) * 5
        score += len(language_hits) * 4

        reasons = [
            MatchReason(
                label="Clinical fit",
                detail=(
                    f"Demonstration profile matches {', '.join(diagnosis_hits + focus_hits)}."
                    if diagnosis_hits or focus_hits
                    else "No direct disease-specific match in the demonstration profile."
                ),
                status=MatchStatus.MATCH
                if diagnosis_hits and focus_hits
                else MatchStatus.CONDITION,
            ),
            MatchReason(
                label="Evidence compatibility",
                detail=(
                    f"Can begin with {', '.join(evidence_hits)}."
                    if evidence_hits
                    else "No currently available evidence type matches the profile."
                ),
                status=MatchStatus.MATCH if evidence_hits else MatchStatus.CONDITION,
            ),
            MatchReason(
                label="Working language",
                detail=(
                    f"Shared language: {', '.join(language_hits)}."
                    if language_hits
                    else "Language support must be arranged."
                ),
                status=MatchStatus.MATCH if language_hits else MatchStatus.CONDITION,
            ),
            MatchReason(
                label="Synthetic availability",
                detail=centre.synthetic_availability,
                status=MatchStatus.MATCH,
            ),
        ]

        missing_requirements = [
            requirement.label
            for requirement in centre.requirements
            if requirement.evidence_type not in need.available_evidence
        ]
        conditions = [
            f"Provide {label} before final multidisciplinary review."
            for label in missing_requirements
        ]
        return ExpertMatch(
            centre=centre,
            score=score,
            reasons=reasons,
            conditions=conditions,
        )
