from __future__ import annotations

from typing import Protocol

from collab.models import (
    PreparedCase,
    ResearchLineage,
    ResearchProjection,
    ResearchPublicationReceipt,
    utc_now,
)

RESEARCH_PURPOSE = (
    "Synthetic cohort feasibility for metastatic colorectal cancer collaboration research."
)
RESEARCH_SCHEMA_VERSION = "research-cohort-v1"
APPROVED_RESEARCH_FIELDS: dict[str, str] = {
    "diagnosis": "diagnosis-1",
    "histology": "histology-1",
    "systemic_treatment": "systemic-treatment-1",
}
EXCLUDED_RESEARCH_CATEGORIES = [
    "workflow notes",
    "direct source documents",
    "patient identifiers",
    "human opinions",
    "handoff responsibility",
]


class ResearchProjectionError(ValueError):
    pass


class ResearchPublicationError(RuntimeError):
    pass


class OneLakeProjectionAdapter(Protocol):
    """Seam for the local fake and a future separately approved OneLake adapter."""

    def publish(self, projection: ResearchProjection) -> ResearchPublicationReceipt: ...


class LocalFabricAdapterFake:
    def __init__(self, *, fail_publication: bool = False) -> None:
        self.fail_publication = fail_publication
        self.published: list[ResearchProjection] = []
        self._receipts: dict[str, ResearchPublicationReceipt] = {}

    def publish(self, projection: ResearchProjection) -> ResearchPublicationReceipt:
        existing = self._receipts.get(projection.id)
        if existing is not None:
            return existing
        if self.fail_publication:
            raise ResearchPublicationError(
                "The local Fabric publication simulation failed; no projection was published."
            )
        self.published.append(projection)
        receipt = ResearchPublicationReceipt(
            id=f"LOCAL-FABRIC-{projection.id}",
            projection_id=projection.id,
            projection_version=projection.version,
            adapter="local-fabric-fake",
            published_at=utc_now(),
        )
        self._receipts[projection.id] = receipt
        return receipt


class ResearchProjectionModule:
    def __init__(self, adapter: OneLakeProjectionAdapter) -> None:
        self._adapter = adapter

    def project(self, prepared: PreparedCase) -> ResearchProjection:
        claims = {claim.id: claim for claim in prepared.claims}
        record: dict[str, str] = {"synthetic_case_id": prepared.case_id}
        lineage: list[ResearchLineage] = []

        for field, claim_id in APPROVED_RESEARCH_FIELDS.items():
            claim = claims.get(claim_id)
            if claim is None or not claim.provenance:
                raise ResearchProjectionError(
                    f"Approved research field {field} has no source-linked prepared claim."
                )
            provenance = claim.provenance[0]
            record[field] = claim.normalized_value or claim.raw_value
            lineage.append(
                ResearchLineage(
                    field=field,
                    prepared_claim_id=claim.id,
                    source_record_id=provenance.evidence_id,
                    source_institution=provenance.source_institution,
                    source_format=provenance.source_format,
                    source_pointer=provenance.source_pointer,
                )
            )

        return ResearchProjection(
            id=f"RP-{prepared.case_id}-V{prepared.version}",
            purpose=RESEARCH_PURPOSE,
            version=prepared.version,
            schema_version=RESEARCH_SCHEMA_VERSION,
            case_version=prepared.version,
            approved_fields=["synthetic_case_id", *APPROVED_RESEARCH_FIELDS],
            record=record,
            lineage=lineage,
            excluded_categories=EXCLUDED_RESEARCH_CATEGORIES,
        )

    def publish(
        self, prepared: PreparedCase
    ) -> tuple[ResearchProjection, ResearchPublicationReceipt]:
        projection = self.project(prepared)
        return projection, self.publish_projection(projection)

    def publish_projection(self, projection: ResearchProjection) -> ResearchPublicationReceipt:
        return self._adapter.publish(projection)
