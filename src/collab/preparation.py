from __future__ import annotations

from collections.abc import Iterable

from collab.models import (
    CaseDelta,
    ClaimKind,
    ConflictFinding,
    EvidenceChange,
    EvidenceEnvelope,
    FindingChange,
    FindingSeverity,
    MissingFinding,
    PreparedCase,
    PreparedClaim,
    ProvenanceLink,
    Referral,
    SynthesisStatement,
    utc_now,
)
from collab.sources import InstitutionSource


class PreparationError(ValueError):
    pass


class DeterministicSynthesis:
    def synthesize(
        self,
        claims: list[PreparedClaim],
        conflicts: list[ConflictFinding],
        missing: list[MissingFinding],
    ) -> list[SynthesisStatement]:
        by_id = {claim.id: claim for claim in claims}
        statements: list[SynthesisStatement] = []
        for claim_id in ("diagnosis-1", "systemic-treatment-1", "baseline-imaging-1"):
            claim = by_id.get(claim_id)
            if claim is not None:
                value = claim.normalized_value or claim.raw_value
                statements.append(
                    SynthesisStatement(
                        text=f"{claim.label}: {value}.",
                        support_ids=[claim.id],
                    )
                )
        statements.extend(
            SynthesisStatement(text=item.description, support_ids=item.claim_ids)
            for item in conflicts
        )
        statements.extend(
            SynthesisStatement(text=item.description, support_ids=[item.id]) for item in missing
        )
        return statements


class CasePreparationService:
    def __init__(
        self,
        sources: Iterable[InstitutionSource],
        synthesis: DeterministicSynthesis | None = None,
    ) -> None:
        self._sources = list(sources)
        self._synthesis = synthesis or DeterministicSynthesis()

    def prepare(self, referral: Referral) -> PreparedCase:
        evidence = [
            envelope
            for source in self._sources
            for envelope in source.read_snapshot(referral.need.case_id)
        ]
        if not evidence:
            raise PreparationError("No institutional evidence is available for this case.")
        return self._build(referral, evidence, version=1)

    def refresh(
        self,
        referral: Referral,
        previous: PreparedCase,
        arrived_evidence: list[EvidenceEnvelope],
    ) -> PreparedCase:
        if previous.referral_id != referral.id:
            raise PreparationError("The prepared case does not belong to the current referral.")
        if not arrived_evidence:
            raise PreparationError("The evidence-arrival event contained no supported evidence.")
        existing_ids = {item.source_identifier for item in previous.evidence}
        additions = [
            item for item in arrived_evidence if item.source_identifier not in existing_ids
        ]
        if not additions:
            raise PreparationError("The evidence-arrival event contained no new evidence.")
        evidence = [*previous.evidence, *additions]
        prepared = self._build(referral, evidence, version=previous.version + 1)
        prepared.delta = self._delta(previous, prepared, additions)
        return prepared

    def _build(
        self,
        referral: Referral,
        evidence: list[EvidenceEnvelope],
        version: int,
    ) -> PreparedCase:
        claims = self._claims(evidence)
        conflicts = self._conflicts(claims)
        missing = self._missing(evidence)
        synthesis = self._synthesis.synthesize(claims, conflicts, missing)
        valid_support = {claim.id for claim in claims} | {item.id for item in missing}
        if any(not set(item.support_ids) <= valid_support for item in synthesis):
            raise PreparationError("Synthesis referenced evidence outside the prepared package.")

        return PreparedCase(
            case_id=referral.need.case_id,
            referral_id=referral.id,
            version=version,
            prepared_at=utc_now(),
            clinical_question=referral.need.decision_focus,
            evidence=evidence,
            claims=claims,
            conflicts=conflicts,
            missing=missing,
            warnings=[warning for item in evidence for warning in item.warnings],
            unmapped_values=[value for item in evidence for value in item.unmapped_values],
            synthesis=synthesis,
            limitations=[
                "Synthetic evidence preparation only; not clinically validated.",
                "Deterministic synthesis uses only values in this prepared evidence package.",
                "No treatment recommendation or resectability decision is produced.",
            ],
        )

    def _delta(
        self,
        previous: PreparedCase,
        current: PreparedCase,
        additions: list[EvidenceEnvelope],
    ) -> CaseDelta:
        previous_imaging = {
            claim.id: claim.normalized_value or claim.raw_value
            for claim in previous.claims
            if claim.category == "imaging"
        }
        current_by_key = {
            claim.id: claim.normalized_value or claim.raw_value
            for claim in current.claims
            if claim.category == "imaging"
        }
        baseline = next(
            (
                value
                for claim_id, value in current_by_key.items()
                if claim_id.startswith("original-lesion-sites-")
            ),
            "Original lesion sites are not available.",
        )
        restaging = next(
            (
                value
                for claim_id, value in current_by_key.items()
                if claim_id.startswith("restaging-lesion-findings-")
            ),
            "Restaging lesion findings are not available.",
        )
        changed_findings = [
            FindingChange(
                subject="Longitudinal liver lesion mapping",
                before=(
                    "No linked baseline lesion map or restaging MRI findings were available."
                    if not previous_imaging
                    else "; ".join(previous_imaging.values())
                ),
                after=f"Original sites: {baseline}. Restaging: {restaging}.",
                conclusion_requires_reassessment=True,
            ),
            FindingChange(
                subject="Imaging evidence completeness",
                before="Original baseline imaging and high-quality restaging MRI were missing.",
                after=(
                    "Baseline CT and restaging MRI metadata are now source-linked; "
                    "human image review remains required."
                ),
                conclusion_requires_reassessment=True,
            ),
        ]
        remaining_uncertainty = [item.description for item in current.missing] + [
            "DICOM pixels were not interpreted in this demonstration.",
            "Resectability remains a human multidisciplinary conclusion.",
        ]
        return CaseDelta(
            from_version=previous.version,
            to_version=current.version,
            added_evidence=[
                EvidenceChange(
                    evidence_id=item.source_identifier,
                    label=next(
                        (
                            fact.label
                            for fact in item.facts
                            if fact.key in {"baseline_imaging", "restaging_imaging"}
                        ),
                        item.source_format,
                    ),
                    source_format=item.source_format,
                    source_institution=item.source_institution,
                    observed_at=item.observed_at,
                )
                for item in additions
            ],
            changed_findings=changed_findings,
            remaining_uncertainty=remaining_uncertainty,
            affected_human_questions=[
                "Are all original lesion sites accounted for in the current review?",
                "How does the segment VIII relationship to the right hepatic vein affect planning?",
                "Do disappearing lesions require additional imaging correlation?",
                "Can resectability now be reconsidered by the multidisciplinary team?",
            ],
        )

    def _claims(self, evidence: list[EvidenceEnvelope]) -> list[PreparedClaim]:
        counters: dict[str, int] = {}
        claims: list[PreparedClaim] = []
        for envelope in evidence:
            for fact in envelope.facts:
                counters[fact.key] = counters.get(fact.key, 0) + 1
                claim_id = f"{fact.key.replace('_', '-')}-{counters[fact.key]}"
                claims.append(
                    PreparedClaim(
                        id=claim_id,
                        label=fact.label,
                        category=fact.category,
                        raw_value=fact.raw_value,
                        normalized_value=fact.normalized_value,
                        kind=(
                            ClaimKind.NORMALIZED_VALUE
                            if fact.normalized_value is not None
                            else ClaimKind.SOURCE_FACT
                        ),
                        transformation=fact.transformation,
                        provenance=[
                            ProvenanceLink(
                                evidence_id=envelope.source_identifier,
                                source_pointer=fact.source_pointer,
                                source_institution=envelope.source_institution,
                                source_format=envelope.source_format,
                                observed_at=envelope.observed_at,
                                transformation_status=envelope.transformation_status,
                            )
                        ],
                    )
                )
        return claims

    def _conflicts(self, claims: list[PreparedClaim]) -> list[ConflictFinding]:
        conflicts: list[ConflictFinding] = []
        for field in ("patient_identifier", "diagnosis_date"):
            matching = [claim for claim in claims if claim.id.startswith(field.replace("_", "-"))]
            values = {claim.normalized_value or claim.raw_value for claim in matching}
            if len(values) > 1:
                label = field.replace("_", " ")
                conflicts.append(
                    ConflictFinding(
                        id=f"conflict-{field.replace('_', '-')}",
                        field=field,
                        description=(
                            f"{label.capitalize()} differs across source institutions "
                            f"({', '.join(sorted(values))}); no value was selected "
                            "as authoritative."
                        ),
                        claim_ids=[claim.id for claim in matching],
                        resolution="Unresolved; requires source-owner confirmation.",
                    )
                )
        return conflicts

    def _missing(self, evidence: list[EvidenceEnvelope]) -> list[MissingFinding]:
        molecular_requirement = next(
            (
                (envelope, fact)
                for envelope in evidence
                for fact in envelope.facts
                if fact.key == "molecular_requirement"
            ),
            None,
        )
        present_molecular_results = {
            fact.key
            for envelope in evidence
            for fact in envelope.facts
            if fact.key in {"ras_status", "braf_status", "mmr_msi_status"}
        }
        required_molecular_results = {
            "ras_status": "RAS status",
            "braf_status": "BRAF status",
            "mmr_msi_status": "MMR/MSI status",
        }
        missing_results = {
            key: label
            for key, label in required_molecular_results.items()
            if key not in present_molecular_results
        }
        if molecular_requirement is None or not missing_results:
            return []
        envelope, fact = molecular_requirement
        return [
            MissingFinding(
                id=f"missing-{field.replace('_', '-')}",
                field=field,
                description=(
                    f"{label} is missing; the Utrecht molecular review requirement remains open."
                ),
                severity=FindingSeverity.REQUIRED,
                required_by=envelope.source_institution,
                provenance=[
                    ProvenanceLink(
                        evidence_id=envelope.source_identifier,
                        source_pointer=fact.source_pointer,
                        source_institution=envelope.source_institution,
                        source_format=envelope.source_format,
                        observed_at=envelope.observed_at,
                        transformation_status=envelope.transformation_status,
                    )
                ],
            )
            for field, label in missing_results.items()
        ]
