from __future__ import annotations

from pathlib import Path
from typing import Protocol

from collab.models import (
    FederatedSourceId,
    SourceCheckResult,
    SourceRecordView,
    utc_now,
)


class FederatedSourceError(OSError):
    pass


class FederatedPatientSource(Protocol):
    source_id: FederatedSourceId
    source_label: str
    endpoint: str

    def query(self, patient_id: str) -> SourceCheckResult: ...


class LocalMilanSource:
    def __init__(
        self,
        *,
        source_id: FederatedSourceId,
        source_label: str,
        endpoint: str,
        fixture_root: Path,
        records: list[tuple[str, str, str | None, str]],
    ) -> None:
        self.source_id = source_id
        self.source_label = source_label
        self.endpoint = endpoint
        self._fixture_root = fixture_root
        self._records = records

    def query(self, patient_id: str) -> SourceCheckResult:
        if patient_id != "CRC-EU-001":
            raise FederatedSourceError(
                "The selected synthetic patient is not available from this source."
            )
        records = [
            SourceRecordView(
                id=record_id,
                label=label,
                status=(
                    "available"
                    if fixture_name is not None and (self._fixture_root / fixture_name).is_file()
                    else "missing"
                ),
                detail=(
                    available_detail
                    if fixture_name is not None and (self._fixture_root / fixture_name).is_file()
                    else "Not available to the referral workflow."
                ),
            )
            for record_id, label, fixture_name, available_detail in self._records
        ]
        return SourceCheckResult(
            source_id=self.source_id,
            source_label=self.source_label,
            endpoint=self.endpoint,
            patient_id=patient_id,
            status="complete",
            records=records,
            checked_at=utc_now(),
        )


def local_milan_sources(fixture_root: Path) -> dict[FederatedSourceId, FederatedPatientSource]:
    return {
        FederatedSourceId.MILAN_EHR: LocalMilanSource(
            source_id=FederatedSourceId.MILAN_EHR,
            source_label="Milan electronic health record",
            endpoint="/api/journey/actions · source=milan_ehr",
            fixture_root=fixture_root,
            records=[
                (
                    "referral-summary",
                    "Clinical referral summary",
                    "referral.cda.xml",
                    "CDA referral summary is available.",
                ),
                (
                    "treatment-history",
                    "Systemic treatment history",
                    "treatment.local.json",
                    "Local oncology treatment record is available.",
                ),
            ],
        ),
        FederatedSourceId.MILAN_DOCUMENTS: LocalMilanSource(
            source_id=FederatedSourceId.MILAN_DOCUMENTS,
            source_label="Milan document repository",
            endpoint="/api/journey/actions · source=milan_documents",
            fixture_root=fixture_root,
            records=[
                (
                    "pathology-report",
                    "Pathology report",
                    "pathology.pdf.txt",
                    "Pathology source document is available.",
                ),
                (
                    "molecular-profile",
                    "Extended molecular profile",
                    None,
                    "",
                ),
            ],
        ),
        FederatedSourceId.MILAN_PACS: LocalMilanSource(
            source_id=FederatedSourceId.MILAN_PACS,
            source_label="Milan imaging archive",
            endpoint="/api/journey/actions · source=milan_pacs",
            fixture_root=fixture_root,
            records=[
                (
                    "current-ct-summary",
                    "Current CT summary",
                    "referral.cda.xml",
                    "Current CT summary is referenced in the clinical record.",
                ),
                (
                    "baseline-liver-ct",
                    "Original baseline liver CT",
                    None,
                    "",
                ),
                (
                    "restaging-liver-mri",
                    "Restaging liver MRI",
                    None,
                    "",
                ),
            ],
        ),
    }
