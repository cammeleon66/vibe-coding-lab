from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from collab.app import create_app
from collab.directory import SyntheticExpertDirectory
from collab.models import (
    ClinicalNeed,
    EvidenceEnvelope,
    ReferralCreate,
    ReferralSender,
    Urgency,
)
from collab.preparation import CasePreparationService
from collab.referrals import ReferralService
from collab.sources import MilanLocalSource, UtrechtLocalSource


def _referral():
    return ReferralService(SyntheticExpertDirectory()).create(
        ReferralCreate(
            need=ClinicalNeed(),
            centre_id="utrecht-crc",
            clinician_id="eva-van-dijk",
            urgency=Urgency.EXPEDITED,
            sender=ReferralSender(
                clinician_name="Dr Luca Bianchi",
                institution="Istituto Nazionale dei Tumori, Milan",
                country="Italy",
            ),
        )
    )


def _command() -> dict[str, object]:
    return {
        "need": ClinicalNeed().model_dump(),
        "centre_id": "utrecht-crc",
        "clinician_id": "eva-van-dijk",
        "urgency": "expedited",
        "sender": {
            "clinician_name": "Dr Luca Bianchi",
            "institution": "Istituto Nazionale dei Tumori, Milan",
            "country": "Italy",
        },
    }


def test_milan_adapter_preserves_formats_warnings_and_unmapped_values() -> None:
    evidence = MilanLocalSource().read_snapshot("CRC-EU-001")

    assert {item.source_format for item in evidence} == {
        "CDA/XML",
        "PDF-derived text",
        "local JSON",
        "DICOM metadata JSON",
    }
    assert all(item.content_hash for item in evidence)
    cda = next(item for item in evidence if item.source_format == "CDA/XML")
    diagnosis_date = next(item for item in cda.facts if item.key == "diagnosis_date")
    assert diagnosis_date.raw_value == "14/02/2025"
    assert diagnosis_date.normalized_value == "2025-02-14"
    assert cda.warnings
    assert "<ClinicalDocument" in cda.original_content
    assert cda.original_media_type == "application/xml"
    treatment = next(item for item in evidence if item.source_format == "local JSON")
    assert treatment.unmapped_values == ["response_code=PRX"]


def test_utrecht_adapter_is_structurally_different_and_preserves_requirement() -> None:
    evidence = UtrechtLocalSource().read_snapshot("CRC-EU-001")

    assert {item.source_format for item in evidence} == {
        "FHIR-like JSON",
        "review requirements JSON",
    }
    fhir = next(item for item in evidence if item.source_format == "FHIR-like JSON")
    assert "production profile" in fhir.warnings[0]
    requirement = next(
        fact for item in evidence for fact in item.facts if fact.key == "molecular_requirement"
    )
    assert "RAS, BRAF and MMR/MSI" in requirement.raw_value


def test_prepared_case_keeps_conflict_missingness_provenance_and_boundary() -> None:
    prepared = CasePreparationService([MilanLocalSource(), UtrechtLocalSource()]).prepare(
        _referral()
    )

    assert {item.field for item in prepared.conflicts} >= {
        "patient_identifier",
        "diagnosis_date",
    }
    assert {item.field for item in prepared.missing} == {
        "ras_status",
        "braf_status",
        "mmr_msi_status",
    }
    assert all(item.provenance[0].source_institution == "UMC Utrecht" for item in prepared.missing)
    assert "response_code=PRX" in prepared.unmapped_values
    assert all(claim.provenance for claim in prepared.claims)
    assert any(
        claim.raw_value == "14/02/2025" and claim.normalized_value == "2025-02-14"
        for claim in prepared.claims
    )
    valid_support = {claim.id for claim in prepared.claims} | {item.id for item in prepared.missing}
    assert all(set(statement.support_ids) <= valid_support for statement in prepared.synthesis)
    claims_by_id = {claim.id: claim for claim in prepared.claims}
    allowed_statements = {
        f"{claim.label}: {claim.normalized_value or claim.raw_value}."
        for claim_id in ("diagnosis-1", "systemic-treatment-1", "baseline-imaging-1")
        if (claim := claims_by_id.get(claim_id)) is not None
    }
    allowed_statements.update(item.description for item in prepared.conflicts)
    allowed_statements.update(item.description for item in prepared.missing)
    assert {item.text for item in prepared.synthesis} <= allowed_statements
    synthesis_text = " ".join(item.text for item in prepared.synthesis).lower()
    assert "recommend" not in synthesis_text
    assert "resectable" not in synthesis_text


def test_prepare_and_source_endpoints_persist_from_referral(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    with TestClient(create_app(state_path)) as client:
        assert client.post("/api/referrals", json=_command()).status_code == 201
        prepared_response = client.post("/api/cases/current/prepare")
        assert prepared_response.status_code == 200
        prepared = prepared_response.json()
        source_id = prepared["claims"][0]["provenance"][0]["evidence_id"]
        source_response = client.get(f"/api/cases/current/sources/{source_id}")
        assert source_response.status_code == 200
        assert source_response.json()["source_identifier"] == source_id
        assert source_response.json()["original_content"]

    with TestClient(create_app(state_path)) as client:
        persisted = client.get("/api/cases/current")

    assert persisted.status_code == 200
    assert persisted.json()["referral_id"] == prepared["referral_id"]


def test_prepare_and_source_endpoints_show_failure_paths(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        prepare = client.post("/api/cases/current/prepare")
        source = client.get("/api/cases/current/sources/unknown")

    assert prepare.status_code == 409
    assert "Create a referral" in prepare.json()["detail"]
    assert source.status_code == 404
    assert source.json()["detail"] == "No prepared case is available."


def test_partial_molecular_panel_keeps_specific_missing_components() -> None:
    evidence = MilanLocalSource().read_snapshot("CRC-EU-001")
    requirement = UtrechtLocalSource().read_snapshot("CRC-EU-001")
    evidence[0].facts.append(
        evidence[0]
        .facts[0]
        .model_copy(
            update={
                "key": "ras_status",
                "label": "RAS status",
                "category": "molecular",
                "raw_value": "wild type",
                "normalized_value": "wild type",
                "source_pointer": "/ClinicalDocument/component/molecular/ras",
            }
        )
    )

    class PartialPanelSource:
        def read_snapshot(self, case_id: str) -> list[EvidenceEnvelope]:
            return evidence + requirement if case_id == "CRC-EU-001" else []

    prepared = CasePreparationService([PartialPanelSource()]).prepare(_referral())

    assert {item.field for item in prepared.missing} == {
        "braf_status",
        "mmr_msi_status",
    }


@pytest.mark.parametrize("source", [MilanLocalSource(), UtrechtLocalSource()])
def test_adapters_return_no_evidence_for_unknown_case(
    source: MilanLocalSource | UtrechtLocalSource,
) -> None:
    assert source.read_snapshot("UNKNOWN") == []
