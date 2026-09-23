from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from xml.etree import ElementTree

from collab.models import EvidenceEnvelope, EvidenceFact, TransformationStatus


class InstitutionSource(Protocol):
    def read_snapshot(self, case_id: str) -> list[EvidenceEnvelope]: ...


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class MilanLocalSource:
    institution = "Istituto Nazionale dei Tumori, Milan"

    def __init__(self, fixture_root: Path | None = None) -> None:
        self._root = fixture_root or Path(__file__).parent / "fixtures" / "milan"

    def read_snapshot(self, case_id: str) -> list[EvidenceEnvelope]:
        if case_id != "CRC-EU-001":
            return []
        return [
            self._read_cda(),
            self._read_pathology(),
            self._read_treatment(),
            self._read_dicom_metadata(),
        ]

    def _read_cda(self) -> EvidenceEnvelope:
        path = self._root / "referral.cda.xml"
        content = path.read_bytes()
        root = ElementTree.fromstring(content)
        fields = {node.attrib["name"]: (node.text or "") for node in root.findall(".//fact")}
        return EvidenceEnvelope(
            source_institution=self.institution,
            source_identifier=root.attrib["documentId"],
            source_format="CDA/XML",
            observed_at=_timestamp(root.attrib["observedAt"]),
            received_at=_timestamp(root.attrib["receivedAt"]),
            content_hash=_hash(content),
            transformation_status=TransformationStatus.TRANSFORMED,
            facts=[
                EvidenceFact(
                    key="patient_identifier",
                    label="Patient identifier",
                    category="identity",
                    raw_value=fields["patient_identifier"],
                    normalized_value=fields["patient_identifier"],
                    transformation="Copied from CDA extension value.",
                    source_pointer="/ClinicalDocument/recordTarget/patientRole/id",
                ),
                EvidenceFact(
                    key="diagnosis",
                    label="Diagnosis",
                    category="diagnosis",
                    raw_value=fields["diagnosis"],
                    normalized_value="Metastatic colorectal adenocarcinoma with liver metastases",
                    transformation="Expanded local clinical wording without changing meaning.",
                    source_pointer="/ClinicalDocument/component/problem/diagnosis",
                ),
                EvidenceFact(
                    key="diagnosis_date",
                    label="Diagnosis date",
                    category="diagnosis",
                    raw_value=fields["diagnosis_date"],
                    normalized_value="2025-02-14",
                    transformation="Converted DD/MM/YYYY to ISO 8601.",
                    source_pointer="/ClinicalDocument/component/problem/effectiveTime",
                ),
            ],
            warnings=["Italian date format was normalized; the original value is preserved."],
            retrieval_reference="fixtures/milan/referral.cda.xml",
            original_media_type="application/xml",
            original_content=content.decode("utf-8"),
        )

    def _read_pathology(self) -> EvidenceEnvelope:
        path = self._root / "pathology.pdf.txt"
        content = path.read_bytes()
        lines = dict(
            line.split(": ", 1) for line in content.decode("utf-8").splitlines() if ": " in line
        )
        return EvidenceEnvelope(
            source_institution=self.institution,
            source_identifier=lines["Report ID"],
            source_format="PDF-derived text",
            observed_at=_timestamp(lines["Observed"]),
            received_at=_timestamp(lines["Received"]),
            content_hash=_hash(content),
            transformation_status=TransformationStatus.PARTIAL,
            facts=[
                EvidenceFact(
                    key="histology",
                    label="Histology",
                    category="pathology",
                    raw_value=lines["Finding"],
                    normalized_value="Moderately differentiated colorectal adenocarcinoma",
                    transformation="Extracted from synthetic PDF text and normalized terminology.",
                    source_pointer="page 1 / Finding",
                ),
                EvidenceFact(
                    key="specimen",
                    label="Specimen",
                    category="pathology",
                    raw_value=lines["Specimen"],
                    normalized_value=None,
                    transformation="Extracted verbatim from synthetic PDF text.",
                    source_pointer="page 1 / Specimen",
                ),
            ],
            warnings=[
                "Text is a deterministic extraction from a synthetic PDF representation; "
                "layout was not interpreted."
            ],
            retrieval_reference="fixtures/milan/pathology.pdf.txt",
            original_media_type="text/plain",
            original_content=content.decode("utf-8"),
        )

    def _read_treatment(self) -> EvidenceEnvelope:
        path = self._root / "treatment.local.json"
        content = path.read_bytes()
        payload = json.loads(content)
        return EvidenceEnvelope(
            source_institution=self.institution,
            source_identifier=payload["record_id"],
            source_format="local JSON",
            observed_at=_timestamp(payload["observed_at"]),
            received_at=_timestamp(payload["received_at"]),
            content_hash=_hash(content),
            transformation_status=TransformationStatus.PARTIAL,
            facts=[
                EvidenceFact(
                    key="systemic_treatment",
                    label="Systemic treatment",
                    category="treatment",
                    raw_value=payload["regimen_code"],
                    normalized_value="FOLFOXIRI plus bevacizumab, 6 cycles",
                    transformation="Mapped local regimen code MIL-FB-6 using the demo code table.",
                    source_pointer="$.regimen_code",
                ),
                EvidenceFact(
                    key="local_response_code",
                    label="Local response code",
                    category="treatment",
                    raw_value=payload["response_code"],
                    normalized_value=None,
                    transformation="No mapping exists; value remains source-only.",
                    source_pointer="$.response_code",
                ),
            ],
            warnings=["One local response code could not be normalized."],
            unmapped_values=[f"response_code={payload['response_code']}"],
            retrieval_reference="fixtures/milan/treatment.local.json",
            original_media_type="application/json",
            original_content=content.decode("utf-8"),
        )

    def _read_dicom_metadata(self) -> EvidenceEnvelope:
        path = self._root / "baseline-ct.dicom-metadata.json"
        content = path.read_bytes()
        payload = json.loads(content)
        return EvidenceEnvelope(
            source_institution=self.institution,
            source_identifier=payload["StudyInstanceUID"],
            source_format="DICOM metadata JSON",
            observed_at=_timestamp(payload["ObservedAt"]),
            received_at=_timestamp(payload["ReceivedAt"]),
            content_hash=_hash(content),
            transformation_status=TransformationStatus.ORIGINAL,
            facts=[
                EvidenceFact(
                    key="baseline_imaging",
                    label="Baseline imaging",
                    category="imaging",
                    raw_value=(
                        f"{payload['Modality']} {payload['BodyPartExamined']} "
                        f"{payload['StudyDate']}"
                    ),
                    normalized_value="Baseline contrast-enhanced CT of the liver (2025-02-18)",
                    transformation="Combined selected DICOM metadata; no pixels were interpreted.",
                    source_pointer="Modality, BodyPartExamined, StudyDate",
                )
            ],
            warnings=["Only DICOM metadata is present; no image interpretation was performed."],
            retrieval_reference="fixtures/milan/baseline-ct.dicom-metadata.json",
            original_media_type="application/dicom+json",
            original_content=content.decode("utf-8"),
        )


class UtrechtLocalSource:
    institution = "UMC Utrecht"

    def __init__(self, fixture_root: Path | None = None) -> None:
        self._root = fixture_root or Path(__file__).parent / "fixtures" / "utrecht"

    def read_snapshot(self, case_id: str) -> list[EvidenceEnvelope]:
        if case_id != "CRC-EU-001":
            return []
        return [self._read_fhir(), self._read_requirements()]

    def _read_fhir(self) -> EvidenceEnvelope:
        path = self._root / "referral.fhir.json"
        content = path.read_bytes()
        payload = json.loads(content)
        patient = next(
            entry["resource"]
            for entry in payload["entry"]
            if entry["resource"]["resourceType"] == "Patient"
        )
        condition = next(
            entry["resource"]
            for entry in payload["entry"]
            if entry["resource"]["resourceType"] == "Condition"
        )
        return EvidenceEnvelope(
            source_institution=self.institution,
            source_identifier=payload["id"],
            source_format="FHIR-like JSON",
            observed_at=_timestamp(payload["timestamp"]),
            received_at=_timestamp(payload["received_at"]),
            content_hash=_hash(content),
            transformation_status=TransformationStatus.PARTIAL,
            facts=[
                EvidenceFact(
                    key="patient_identifier",
                    label="Received patient identifier",
                    category="identity",
                    raw_value=patient["identifier"][0]["value"],
                    normalized_value=patient["identifier"][0]["value"],
                    transformation="Copied from the received referral bundle.",
                    source_pointer="Bundle.entry[Patient].identifier[0].value",
                ),
                EvidenceFact(
                    key="diagnosis_date",
                    label="Received diagnosis date",
                    category="diagnosis",
                    raw_value=condition["onsetDateTime"],
                    normalized_value=condition["onsetDateTime"],
                    transformation="Already ISO formatted; retained unchanged.",
                    source_pointer="Bundle.entry[Condition].onsetDateTime",
                ),
            ],
            warnings=[
                "FHIR-like demonstration JSON was not validated against a production profile."
            ],
            retrieval_reference="fixtures/utrecht/referral.fhir.json",
            original_media_type="application/fhir+json",
            original_content=content.decode("utf-8"),
        )

    def _read_requirements(self) -> EvidenceEnvelope:
        path = self._root / "review-requirements.json"
        content = path.read_bytes()
        payload = json.loads(content)
        return EvidenceEnvelope(
            source_institution=self.institution,
            source_identifier=payload["id"],
            source_format="review requirements JSON",
            observed_at=_timestamp(payload["observed_at"]),
            received_at=_timestamp(payload["received_at"]),
            content_hash=_hash(content),
            transformation_status=TransformationStatus.ORIGINAL,
            facts=[
                EvidenceFact(
                    key="molecular_requirement",
                    label="Molecular evidence requirement",
                    category="review_requirement",
                    raw_value=payload["requirements"]["molecular"],
                    normalized_value=None,
                    transformation="Requirement retained verbatim.",
                    source_pointer="$.requirements.molecular",
                ),
                EvidenceFact(
                    key="review_state",
                    label="Review state",
                    category="workflow",
                    raw_value=payload["review_state"],
                    normalized_value="Awaiting evidence preparation",
                    transformation="Mapped local workflow label to collaboration wording.",
                    source_pointer="$.review_state",
                ),
            ],
            retrieval_reference="fixtures/utrecht/review-requirements.json",
            original_media_type="application/json",
            original_content=content.decode("utf-8"),
        )
