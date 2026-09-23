from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from collab.arrivals import EvidenceArrivalError, EvidenceArrivalService
from collab.directory import SyntheticExpertDirectory
from collab.handoff import CollaborationWorkflow, HandoffError
from collab.models import (
    CaseUpdateError,
    ClinicalNeed,
    DemoState,
    EvidenceArrivalEvent,
    EvidenceArrivalResult,
    EvidenceEnvelope,
    HandoffCreate,
    HandoffManifest,
    HumanOpinion,
    HumanOpinionCreate,
    HumanReviewState,
    MatchResponse,
    PreparedCase,
    Referral,
    ReferralCreate,
)
from collab.persistence import JsonStateStore
from collab.preparation import CasePreparationService, PreparationError
from collab.referrals import ReferralError, ReferralService
from collab.sources import MilanLateImagingSource, MilanLocalSource, UtrechtLocalSource


def create_app(
    state_path: Path | None = None,
    arrival_service: EvidenceArrivalService | None = None,
    mdo_base_url: str | None = None,
) -> FastAPI:
    directory = SyntheticExpertDirectory()
    referral_service = ReferralService(directory)
    preparation_service = CasePreparationService([MilanLocalSource(), UtrechtLocalSource()])
    evidence_arrivals = arrival_service or EvidenceArrivalService(
        MilanLateImagingSource(),
        preparation_service,
    )
    configured_mdo_url = mdo_base_url or os.getenv("MDO_DEMO_URL") or "http://localhost:5174"
    collaboration = CollaborationWorkflow(configured_mdo_url)
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
        store.save(DemoState(current_referral=referral))
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
                prepared_case_versions=[prepared],
            )
        )
        return prepared

    @application.get(
        "/api/cases/current/versions",
        response_model=list[PreparedCase],
    )
    def case_versions() -> list[PreparedCase]:
        return store.load().prepared_case_versions

    @application.get(
        "/api/cases/current/versions/{version}",
        response_model=PreparedCase,
    )
    def case_version(version: int) -> PreparedCase:
        prepared = next(
            (item for item in store.load().prepared_case_versions if item.version == version),
            None,
        )
        if prepared is None:
            raise HTTPException(status_code=404, detail="Prepared case version was not found.")
        return prepared

    @application.get(
        "/api/cases/current/update-error",
        response_model=CaseUpdateError | None,
    )
    def case_update_error() -> CaseUpdateError | None:
        return store.load().case_update_error

    @application.get(
        "/api/cases/current/review",
        response_model=HumanReviewState,
    )
    def current_review() -> HumanReviewState:
        state = store.load()
        if state.current_prepared_case is None:
            raise HTTPException(status_code=404, detail="No prepared case is available.")
        opinion = state.human_opinions[-1] if state.human_opinions else None
        return collaboration.review_state(state.current_prepared_case, opinion)

    @application.post(
        "/api/cases/current/reviews",
        response_model=HumanReviewState,
        status_code=status.HTTP_201_CREATED,
    )
    def record_review(command: HumanOpinionCreate) -> HumanReviewState:
        with store.locked():
            state = store.load()
            if state.current_prepared_case is None:
                raise HTTPException(status_code=409, detail="Prepare the current case first.")
            try:
                opinion = collaboration.record_opinion(state.current_prepared_case, command)
            except HandoffError as error:
                status_code = (
                    status.HTTP_409_CONFLICT
                    if command.case_version != state.current_prepared_case.version
                    else status.HTTP_422_UNPROCESSABLE_CONTENT
                )
                raise HTTPException(status_code=status_code, detail=str(error)) from error
            store.save(
                state.model_copy(update={"human_opinions": [*state.human_opinions, opinion]})
            )
            return collaboration.review_state(state.current_prepared_case, opinion)

    @application.get(
        "/api/cases/current/reviews",
        response_model=list[HumanOpinion],
    )
    def review_history() -> list[HumanOpinion]:
        return store.load().human_opinions

    @application.post(
        "/api/cases/current/handoffs",
        response_model=HandoffManifest,
        status_code=status.HTTP_201_CREATED,
    )
    def create_handoff(command: HandoffCreate) -> HandoffManifest:
        with store.locked():
            state = store.load()
            prepared = state.current_prepared_case
            if prepared is None:
                raise HTTPException(status_code=409, detail="Prepare the current case first.")
            opinion = state.human_opinions[-1] if state.human_opinions else None
            if command.case_version != prepared.version:
                raise HTTPException(
                    status_code=409,
                    detail=f"Case v{prepared.version} is current; refresh before handoff.",
                )
            if opinion is None or command.opinion_id != opinion.id:
                raise HTTPException(
                    status_code=409,
                    detail="The selected human opinion is not the current review.",
                )
            try:
                manifest = collaboration.create_manifest(
                    prepared,
                    opinion,
                    len(state.handoff_manifests) + 1,
                )
            except HandoffError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            store.save(
                state.model_copy(update={"handoff_manifests": [*state.handoff_manifests, manifest]})
            )
            return manifest

    @application.get(
        "/api/cases/current/handoffs",
        response_model=list[HandoffManifest],
    )
    def handoff_history() -> list[HandoffManifest]:
        return store.load().handoff_manifests

    @application.post(
        "/api/evidence-arrivals",
        response_model=EvidenceArrivalResult,
    )
    def receive_evidence(event: EvidenceArrivalEvent) -> EvidenceArrivalResult:
        with store.locked():
            state = store.load()
            if state.current_referral is None or state.current_prepared_case is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Prepare the current case before delivering late evidence.",
                )
            fingerprint = hashlib.sha256(
                event.model_dump_json(exclude={"occurred_at"}).encode("utf-8")
            ).hexdigest()
            processed_fingerprint = state.processed_evidence_events.get(event.event_id)
            if processed_fingerprint is not None:
                if processed_fingerprint != fingerprint:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="The event ID was already used for a different evidence delivery.",
                    )
                return EvidenceArrivalResult(
                    event_id=event.event_id,
                    duplicate=True,
                    prepared_case=state.current_prepared_case,
                )
            try:
                refreshed = evidence_arrivals.apply(
                    event,
                    state.current_referral,
                    state.current_prepared_case,
                )
            except (EvidenceArrivalError, PreparationError) as error:
                update_error = CaseUpdateError(
                    event_id=event.event_id,
                    message=str(error),
                    occurred_at=event.occurred_at,
                    preserved_version=state.current_prepared_case.version,
                )
                store.save(state.model_copy(update={"case_update_error": update_error}))
                raise HTTPException(status_code=422, detail=str(error)) from error
            next_state = state.model_copy(
                update={
                    "current_prepared_case": refreshed,
                    "prepared_case_versions": [*state.prepared_case_versions, refreshed],
                    "processed_evidence_events": {
                        **state.processed_evidence_events,
                        event.event_id: fingerprint,
                    },
                    "case_update_error": None,
                }
            )
            try:
                store.save(next_state)
            except OSError as error:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "The evidence update could not be persisted; "
                        f"case v{state.current_prepared_case.version} remains current."
                    ),
                ) from error
            return EvidenceArrivalResult(
                event_id=event.event_id,
                duplicate=False,
                prepared_case=refreshed,
            )

    @application.get(
        "/api/cases/current/sources/{evidence_id}",
        response_model=EvidenceEnvelope,
    )
    def current_case_source(evidence_id: str, version: int | None = None) -> EvidenceEnvelope:
        state = store.load()
        prepared = (
            state.current_prepared_case
            if version is None
            else next(
                (item for item in state.prepared_case_versions if item.version == version),
                None,
            )
        )
        if prepared is None:
            detail = (
                "No prepared case is available."
                if version is None
                else "Prepared case version was not found."
            )
            raise HTTPException(status_code=404, detail=detail)
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
