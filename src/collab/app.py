from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from collab.directory import SyntheticExpertDirectory
from collab.models import (
    ClinicalNeed,
    DemoState,
    EvidenceEnvelope,
    MatchResponse,
    PreparedCase,
    Referral,
    ReferralCreate,
)
from collab.persistence import JsonStateStore
from collab.preparation import CasePreparationService, PreparationError
from collab.referrals import ReferralError, ReferralService
from collab.sources import MilanLocalSource, UtrechtLocalSource


def create_app(state_path: Path | None = None) -> FastAPI:
    directory = SyntheticExpertDirectory()
    referral_service = ReferralService(directory)
    preparation_service = CasePreparationService([MilanLocalSource(), UtrechtLocalSource()])
    store = JsonStateStore(state_path or Path("data") / "demo-state.json")

    application = FastAPI(title="European oncology collaboration demo")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "synthetic-rehearsal"}

    @application.post("/api/expert-matches", response_model=MatchResponse)
    def expert_matches(need: ClinicalNeed) -> MatchResponse:
        return directory.find_matches(need)

    @application.get("/api/referrals/current", response_model=Referral | None)
    def current_referral() -> Referral | None:
        return store.load().current_referral

    @application.post(
        "/api/referrals",
        response_model=Referral,
        status_code=status.HTTP_201_CREATED,
    )
    def create_referral(command: ReferralCreate) -> Referral:
        try:
            referral = referral_service.create(command)
        except ReferralError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        store.save(DemoState(current_referral=referral, current_prepared_case=None))
        return referral

    @application.get("/api/cases/current", response_model=PreparedCase | None)
    def current_case() -> PreparedCase | None:
        return store.load().current_prepared_case

    @application.post("/api/cases/current/prepare", response_model=PreparedCase)
    def prepare_current_case() -> PreparedCase:
        state = store.load()
        if state.current_referral is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Create a referral before preparing the clinical workspace.",
            )
        try:
            prepared = preparation_service.prepare(state.current_referral)
        except PreparationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        store.save(
            DemoState(
                current_referral=state.current_referral,
                current_prepared_case=prepared,
            )
        )
        return prepared

    @application.get(
        "/api/cases/current/sources/{evidence_id}",
        response_model=EvidenceEnvelope,
    )
    def current_case_source(evidence_id: str) -> EvidenceEnvelope:
        prepared = store.load().current_prepared_case
        if prepared is None:
            raise HTTPException(status_code=404, detail="No prepared case is available.")
        evidence = next(
            (item for item in prepared.evidence if item.source_identifier == evidence_id),
            None,
        )
        if evidence is None:
            raise HTTPException(status_code=404, detail="Source evidence was not found.")
        return evidence

    @application.post("/api/reset", status_code=status.HTTP_204_NO_CONTENT)
    def reset() -> None:
        store.save(DemoState())

    frontend_dist = Path("frontend") / "dist"
    assets_path = frontend_dist / "assets"
    if assets_path.exists():
        application.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    if (frontend_dist / "index.html").exists():

        @application.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            requested = frontend_dist / path
            if path and requested.is_file():
                return FileResponse(requested)
            return FileResponse(frontend_dist / "index.html")

    return application


app = create_app()
