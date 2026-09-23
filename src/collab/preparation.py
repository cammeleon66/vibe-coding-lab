from __future__ import annotations

from collections.abc import Iterable

from collab.models import (
    ClaimKind,
    ConflictFinding,
    EvidenceEnvelope,
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
            version=1,
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
