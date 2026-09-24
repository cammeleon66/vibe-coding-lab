from pathlib import Path
from shutil import copytree

import pytest
from fastapi.testclient import TestClient

import collab.app as app_module
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


def test_preflight_reports_local_demo_readiness_and_boundaries(tmp_path: Path) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    with TestClient(
        create_app(
            tmp_path / "state.json",
            mdo_base_url="http://localhost:5174",
            research_authorization_code="research-code",
            frontend_dist=frontend_dist,
        )
    ) as client:
        response = client.get("/api/preflight")

    assert response.status_code == 200
    report = response.json()
    assert report["ready"] is True
    assert report["mode"] == "synthetic-rehearsal"
    checks = {item["id"]: item for item in report["checks"]}
    assert checks["runtime-mode"]["status"] == "pass"
    assert checks["fixtures"]["status"] == "pass"
    assert checks["state-store"]["status"] == "pass"
    assert checks["frontend-build"]["status"] == "pass"
    assert checks["research-authorization"]["status"] == "pass"
    assert "no private MDO state is accessed" in checks["mdo-boundary"]["detail"]


def test_preflight_fails_when_presenter_build_is_missing(tmp_path: Path) -> None:
    with TestClient(
        create_app(
            tmp_path / "state.json",
            frontend_dist=tmp_path / "missing-frontend-dist",
        )
    ) as client:
        report = client.get("/api/preflight").json()

    assert report["ready"] is False
    checks = {item["id"]: item for item in report["checks"]}
    assert checks["frontend-build"]["status"] == "fail"


def test_preflight_uses_configured_packaged_frontend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frontend_dist = tmp_path / "packaged-frontend"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST", str(frontend_dist))
    installed_module = tmp_path / "site-packages" / "collab" / "app.py"
    monkeypatch.setattr(app_module, "__file__", str(installed_module))
    fixture_root = Path(__file__).parents[1] / "src" / "collab" / "fixtures"

    with TestClient(
        create_app(tmp_path / "state.json", fixture_root=fixture_root)
    ) as client:
        report = client.get("/api/preflight").json()

    checks = {item["id"]: item for item in report["checks"]}
    assert checks["frontend-build"]["status"] == "pass"


def test_shared_demo_code_protects_ui_and_api(tmp_path: Path) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    with TestClient(
        create_app(
            tmp_path / "state.json",
            frontend_dist=frontend_dist,
            demo_access_code="shared-demo-code",
            demo_session_secret="session-signing-secret",
        ),
        base_url="https://testserver",
        follow_redirects=False,
    ) as client:
        protected_page = client.get("/")
        protected_api = client.get("/api/preflight")
        health = client.get("/api/health")
        event_grid = client.post("/api/event-grid/evidence-arrivals", json=[])
        wrong_code = client.post("/api/demo-access", json={"code": "wrong"})
        accepted = client.post(
            "/api/demo-access", json={"code": "shared-demo-code"}
        )
        unlocked_page = client.get("/")

    assert protected_page.status_code == 307
    assert protected_page.headers["location"].startswith("/demo-access")
    assert protected_api.status_code == 401
    assert health.status_code == 200
    assert event_grid.status_code == 403
    assert wrong_code.status_code == 401
    assert accepted.status_code == 204
    assert "demo_access_session=" in accepted.headers["set-cookie"]
    assert unlocked_page.status_code == 200


def test_preflight_fails_when_a_fixture_cannot_be_parsed(tmp_path: Path) -> None:
    source_fixtures = Path(__file__).parents[1] / "src" / "collab" / "fixtures"
    fixture_root = tmp_path / "fixtures"
    copytree(source_fixtures, fixture_root)
    (fixture_root / "milan" / "treatment.local.json").write_text("{", encoding="utf-8")
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html>", encoding="utf-8")

    with TestClient(
        create_app(
            tmp_path / "state.json",
            frontend_dist=frontend_dist,
            fixture_root=fixture_root,
        )
    ) as client:
        report = client.get("/api/preflight").json()

    checks = {item["id"]: item for item in report["checks"]}
    assert report["ready"] is False
    assert checks["fixtures"]["status"] == "fail"
    assert "Fixture rehearsal failed" in checks["fixtures"]["detail"]


def test_reset_returns_demo_to_a_clean_state(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    with TestClient(create_app(state_path)) as client:
        assert (
            client.post(
                "/api/referrals",
                json={
                    "need": {},
                    "centre_id": "utrecht-crc",
                    "clinician_id": "eva-van-dijk",
                    "urgency": "routine",
                    "sender": {
                        "clinician_name": "Dr Luca Bianchi",
                        "institution": "Istituto Nazionale dei Tumori, Milan",
                        "country": "Italy",
                    },
                },
            ).status_code
            == 201
        )
        assert client.post("/api/reset").status_code == 204
        assert client.get("/api/referrals/current").json() is None
        assert client.get("/api/cases/current").json() is None
        assert client.get("/api/cases/current/versions").json() == []
