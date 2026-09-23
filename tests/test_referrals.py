from pathlib import Path

from fastapi.testclient import TestClient

from collab.app import create_app


def test_referral_carries_requirements_and_persists(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    command = {
        "need": {
            "case_id": "CRC-EU-001",
            "diagnosis": "Metastatic colorectal cancer with liver-limited metastases",
            "decision_focus": "Conversion therapy and liver-metastasis resectability",
            "referring_country": "Italy",
            "preferred_languages": ["Italian", "English"],
            "available_evidence": ["pathology", "treatment_timeline", "current_ct_summary"],
        },
        "centre_id": "utrecht-crc",
        "clinician_id": "eva-van-dijk",
        "urgency": "expedited",
        "sender": {
            "clinician_name": "Dr Luca Bianchi",
            "institution": "Istituto Nazionale dei Tumori, Milan",
            "country": "Italy",
        },
    }

    with TestClient(create_app(state_path)) as client:
        response = client.post("/api/referrals", json=command)

    assert response.status_code == 201
    referral = response.json()
    assert referral["centre"]["id"] == "utrecht-crc"
    assert referral["clinician"]["fictional"] is True
    assert referral["urgency"] == "expedited"
    assert referral["sender"]["clinician_name"] == "Dr Luca Bianchi"
    assert referral["responsibility"]["actor"] == "Istituto Nazionale dei Tumori, Milan"
    statuses = {item["key"]: item["status"] for item in referral["requirements"]}
    assert statuses["pathology"] == "present"
    assert statuses["baseline-ct"] == "missing"

    with TestClient(create_app(state_path)) as client:
        persisted = client.get("/api/referrals/current")

    assert persisted.status_code == 200
    assert persisted.json()["id"] == referral["id"]


def test_referral_rejects_clinician_from_another_centre(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "state.json")) as client:
        response = client.post(
            "/api/referrals",
            json={
                "need": {},
                "centre_id": "utrecht-crc",
                "clinician_id": "lea-martin",
                "urgency": "routine",
                "sender": {
                    "clinician_name": "Dr Luca Bianchi",
                    "institution": "Istituto Nazionale dei Tumori, Milan",
                    "country": "Italy",
                },
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "The selected clinician does not belong to this centre."
