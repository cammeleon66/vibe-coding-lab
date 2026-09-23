from __future__ import annotations

import hashlib
import logging
import os
import secrets
from pathlib import Path
from time import monotonic, sleep
from typing import Protocol
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from fastapi import Cookie, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from collab.arrivals import EvidenceArrivalError, EvidenceArrivalService
from collab.azure_adapters import (
    AzureBlobEvidenceArrivalPublisher,
    AzureBlobStateStore,
    AzureLateImagingSource,
    AzureMilanSource,
    AzureUtrechtSource,
    create_container_client,
    event_grid_blob_url,
    parse_event_grid_payload,
    seed_synthetic_fixtures,
    subscription_validation_code,
)
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
    PreflightCheck,
    PreflightReport,
    PreparedCase,
    Referral,
    ReferralCreate,
    ReferralSender,
    ResearchAuthorizationCreate,
    ResearchPublication,
    Urgency,
    utc_now,
)
from collab.persistence import JsonStateStore, StateConflictError, StateStore
from collab.preparation import CasePreparationService, PreparationError
from collab.referrals import ReferralError, ReferralService
from collab.research import (
    LocalFabricAdapterFake,
    OneLakeProjectionAdapter,
    ResearchProjectionError,
    ResearchProjectionModule,
    ResearchPublicationError,
)
from collab.sources import (
    EvidenceArrivalSource,
    InstitutionSource,
    MilanLateImagingSource,
    MilanLocalSource,
    UtrechtLocalSource,
)


class EvidenceArrivalPublisher(Protocol):
    def publish(self, event: EvidenceArrivalEvent) -> None: ...

    def read_event(self, blob_url: str) -> EvidenceArrivalEvent: ...

    def reset(self) -> None: ...


logger = logging.getLogger("collab")


def create_app(
    state_path: Path | None = None,
    arrival_service: EvidenceArrivalService | None = None,
    mdo_base_url: str | None = None,
    research_adapter: OneLakeProjectionAdapter | None = None,
    research_authorization_code: str | None = None,
    frontend_dist: Path | None = None,
    fixture_root: Path | None = None,
    state_store: StateStore | None = None,
    institution_sources: list[InstitutionSource] | None = None,
    late_imaging_source: EvidenceArrivalSource | None = None,
    arrival_publisher: EvidenceArrivalPublisher | None = None,
    runtime_mode: str | None = None,
    event_grid_webhook_secret: str | None = None,
) -> FastAPI:
    repository_root = Path(__file__).resolve().parents[2]
    configured_fixture_root = fixture_root or Path(__file__).parent / "fixtures"
    configured_runtime_mode = runtime_mode or os.getenv("APP_RUNTIME_MODE") or "local"
    reported_runtime_mode = (
        "synthetic-rehearsal"
        if configured_runtime_mode == "local"
        else f"{configured_runtime_mode}-synthetic-rehearsal"
    )
    configured_event_grid_secret = event_grid_webhook_secret or os.getenv(
        "EVENT_GRID_WEBHOOK_SECRET"
    )
    directory = SyntheticExpertDirectory(configured_fixture_root / "expert_centres.json")
    referral_service = ReferralService(directory)
    configured_publisher = arrival_publisher
    if configured_runtime_mode == "azure" and institution_sources is None:
        credential = DefaultAzureCredential(
            managed_identity_client_id=os.getenv("AZURE_CLIENT_ID"),
            exclude_interactive_browser_credential=True,
        )
        milan_container = create_container_client(
            os.environ["MILAN_STORAGE_ACCOUNT_URL"],
            os.getenv("MILAN_SOURCE_CONTAINER", "source"),
            credential,
        )
        milan_event_container = create_container_client(
            os.environ["MILAN_STORAGE_ACCOUNT_URL"],
            os.getenv("MILAN_EVENT_CONTAINER", "events"),
            credential,
        )
        utrecht_container = create_container_client(
            os.environ["UTRECHT_STORAGE_ACCOUNT_URL"],
            os.getenv("UTRECHT_SOURCE_CONTAINER", "source"),
            credential,
        )
        shared_container = create_container_client(
            os.environ["SHARED_STORAGE_ACCOUNT_URL"],
            os.getenv("SHARED_STATE_CONTAINER", "collaboration"),
            credential,
        )
        if os.getenv("SEED_AZURE_FIXTURES", "false").lower() == "true":
            seed_synthetic_fixtures(
                milan_container,
                utrecht_container,
                configured_fixture_root,
            )
        configured_sources: list[InstitutionSource] = [
            AzureMilanSource(milan_container),
            AzureUtrechtSource(utrecht_container),
        ]
        configured_late_source: EvidenceArrivalSource = AzureLateImagingSource(milan_container)
        configured_publisher = configured_publisher or AzureBlobEvidenceArrivalPublisher(
            milan_event_container
        )
        store = state_store or AzureBlobStateStore(shared_container)
    else:
        configured_sources = institution_sources or [
            MilanLocalSource(configured_fixture_root / "milan"),
            UtrechtLocalSource(configured_fixture_root / "utrecht"),
        ]
        configured_late_source = late_imaging_source or MilanLateImagingSource(
            configured_fixture_root / "milan"
        )
        store = state_store or JsonStateStore(state_path or Path("data") / "demo-state.json")
    preparation_service = CasePreparationService(configured_sources)
    evidence_arrivals = arrival_service or EvidenceArrivalService(
        configured_late_source,
        preparation_service,
    )
    configured_mdo_url = mdo_base_url or os.getenv("MDO_DEMO_URL") or "http://localhost:5174"
    collaboration = CollaborationWorkflow(configured_mdo_url)
    research = ResearchProjectionModule(research_adapter or LocalFabricAdapterFake())
    configured_research_code = research_authorization_code or os.getenv(
        "RESEARCH_DEMO_AUTHORIZATION_CODE"
    )
    research_sessions: set[str] = set()

    if configured_runtime_mode == "azure":
        connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        if connection_string:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(
                connection_string=connection_string,
                logger_name="collab",
            )

    application = FastAPI(title="European oncology collaboration demo")

    @application.exception_handler(StateConflictError)
    async def state_conflict_handler(
        _request: Request,
        error: StateConflictError,
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": reported_runtime_mode}

    @application.get("/api/preflight", response_model=PreflightReport)
    def preflight() -> PreflightReport:
        required_fixtures = [
            configured_fixture_root / "expert_centres.json",
            configured_fixture_root / "milan" / "referral.cda.xml",
            configured_fixture_root / "milan" / "pathology.pdf.txt",
            configured_fixture_root / "milan" / "treatment.local.json",
            configured_fixture_root / "milan" / "baseline-ct.dicom-metadata.json",
            configured_fixture_root / "milan" / "restaging-mri.dicom-metadata.json",
            configured_fixture_root / "utrecht" / "referral.fhir.json",
            configured_fixture_root / "utrecht" / "review-requirements.json",
        ]
        missing_fixtures = (
            [
                path.relative_to(configured_fixture_root).as_posix()
                for path in required_fixtures
                if not path.is_file() or path.stat().st_size == 0
            ]
            if configured_runtime_mode == "local"
            else []
        )
        invalid_fixture_detail: str | None = None
        if not missing_fixtures:
            try:
                rehearsal_referral = referral_service.create(
                    ReferralCreate(
                        need=ClinicalNeed(),
                        centre_id="utrecht-crc",
                        clinician_id="eva-van-dijk",
                        urgency=Urgency.EXPEDITED,
                        sender=ReferralSender(
                            clinician_name="Synthetic preflight",
                            institution="Synthetic preflight",
                            country="Italy",
                        ),
                    )
                )
                rehearsal_case = preparation_service.prepare(rehearsal_referral)
                evidence_arrivals.apply(
                    EvidenceArrivalEvent(
                        event_id="preflight-imaging",
                        case_id=rehearsal_case.case_id,
                        evidence_set="baseline-and-restaging-imaging",
                        occurred_at=utc_now(),
                    ),
                    rehearsal_referral,
                    rehearsal_case,
                )
            except (OSError, ValueError, KeyError, IndexError) as error:
                invalid_fixture_detail = str(error)
        checks = [
            PreflightCheck(
                id="runtime-mode",
                label="Deterministic runtime",
                status="pass",
                detail=(
                    f"{configured_runtime_mode.title()} synthetic rehearsal mode is active; "
                    "no live AI adapter is configured."
                ),
            ),
            PreflightCheck(
                id="fixtures",
                label="Synthetic source fixtures",
                status=(
                    "pass" if not missing_fixtures and invalid_fixture_detail is None else "fail"
                ),
                detail=(
                    (
                        f"All {len(required_fixtures)} required source fixtures parse "
                        "through preparation and late-arrival rehearsal."
                    )
                    if not missing_fixtures and invalid_fixture_detail is None
                    else (
                        f"Missing or empty fixtures: {', '.join(missing_fixtures)}."
                        if missing_fixtures
                        else f"Fixture rehearsal failed: {invalid_fixture_detail}."
                    )
                ),
            ),
        ]
        try:
            store.load()
            store.check_writable()
        except (OSError, ValueError) as error:
            checks.append(
                PreflightCheck(
                    id="state-store",
                    label=(
                        "Azure collaboration state"
                        if configured_runtime_mode == "azure"
                        else "Local state store"
                    ),
                    status="fail",
                    detail=f"Collaboration state cannot be loaded or written: {error}",
                )
            )
        else:
            checks.append(
                PreflightCheck(
                    id="state-store",
                    label=(
                        "Azure collaboration state"
                        if configured_runtime_mode == "azure"
                        else "Local state store"
                    ),
                    status="pass",
                    detail=(
                        "Azure Blob collaboration state can be loaded and written."
                        if configured_runtime_mode == "azure"
                        else "Local rehearsal state can be loaded and atomically written."
                    ),
                )
            )
        frontend_index = (frontend_dist or repository_root / "frontend" / "dist") / "index.html"
        checks.extend(
            [
                PreflightCheck(
                    id="frontend-build",
                    label="Presenter build",
                    status="pass" if frontend_index.is_file() else "fail",
                    detail=(
                        "The production frontend build is available to FastAPI."
                        if frontend_index.is_file()
                        else "Run `npm run build` in frontend before the rehearsal."
                    ),
                ),
                PreflightCheck(
                    id="mdo-boundary",
                    label="MDO narrative handoff",
                    status="pass",
                    detail=(
                        f"Deep-link target is {configured_mdo_url}. Availability is not probed "
                        "and no private MDO state is accessed."
                    ),
                ),
                PreflightCheck(
                    id="research-authorization",
                    label="Optional research epilogue",
                    status="pass" if configured_research_code else "warning",
                    detail=(
                        "A separate local research authorization code is configured."
                        if configured_research_code
                        else "Not configured; the primary clinical presenter path remains ready."
                    ),
                    required=False,
                ),
            ]
        )
        return PreflightReport(
            ready=all(check.status != "fail" for check in checks if check.required),
            mode=reported_runtime_mode,
            checked_at=utc_now(),
            checks=checks,
            limitations=[
                (
                    "Preflight exercises approved Azure Blob adapters but does not contact "
                    "Fabric, the autonomous MDO backend, or live AI."
                    if configured_runtime_mode == "azure"
                    else (
                        "Preflight does not contact Azure, Fabric, the autonomous MDO "
                        "backend, or live AI."
                    )
                ),
                "Clinical fidelity remains subject to external oncology review.",
            ],
        )

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
        with store.locked():
            try:
                referral = referral_service.create(command)
            except ReferralError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            store.save(DemoState(current_referral=referral))
            logger.info("referral_created", extra={"referral_id": referral.id})
            return referral

    @application.get("/api/cases/current", response_model=PreparedCase | None)
    def current_case() -> PreparedCase | None:
        return store.load().current_prepared_case

    @application.post("/api/cases/current/prepare", response_model=PreparedCase)
    def prepare_current_case() -> PreparedCase:
        with store.locked():
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
            logger.info(
                "case_prepared",
                extra={"case_id": prepared.case_id, "case_version": prepared.version},
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
            logger.info(
                "handoff_created",
                extra={
                    "case_id": manifest.case_id,
                    "case_version": manifest.evidence_version,
                    "manifest_id": manifest.id,
                },
            )
            return manifest

    @application.get(
        "/api/cases/current/handoffs",
        response_model=list[HandoffManifest],
    )
    def handoff_history() -> list[HandoffManifest]:
        return store.load().handoff_manifests

    def require_research_role(session: str | None) -> None:
        if session is None or session not in research_sessions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Research projection access requires the separately authorized "
                    "synthetic-researcher role; clinical access is not inherited."
                ),
            )

    @application.post("/api/research/authorize", status_code=status.HTTP_204_NO_CONTENT)
    def authorize_research(
        command: ResearchAuthorizationCreate,
        response: Response,
    ) -> None:
        if configured_research_code is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Research authorization is not configured for this rehearsal.",
            )
        if not secrets.compare_digest(command.authorization_code, configured_research_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The synthetic research authorization code is invalid.",
            )
        session = uuid4().hex
        research_sessions.add(session)
        response.set_cookie(
            "research_demo_session",
            session,
            httponly=True,
            samesite="strict",
            secure=configured_runtime_mode == "azure",
        )

    @application.get(
        "/api/research/projection",
        response_model=ResearchPublication | None,
    )
    def current_research_projection(
        research_demo_session: str | None = Cookie(default=None),
    ) -> ResearchPublication | None:
        require_research_role(research_demo_session)
        return store.load().research_publication

    @application.post(
        "/api/research/projection",
        response_model=ResearchPublication,
        status_code=status.HTTP_201_CREATED,
    )
    def publish_research_projection(
        research_demo_session: str | None = Cookie(default=None),
    ) -> ResearchPublication:
        require_research_role(research_demo_session)
        with store.locked():
            state = store.load()
            if state.current_prepared_case is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Prepare the synthetic case before publishing a research projection.",
                )
            try:
                projection = research.project(state.current_prepared_case)
            except ResearchProjectionError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            pending = state.research_pending_projection
            if pending is None or pending.id != projection.id:
                try:
                    store.save(state.model_copy(update={"research_pending_projection": projection}))
                except OSError as error:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=(
                            "The research projection could not enter the pending publication "
                            "state; nothing was published."
                        ),
                    ) from error
            try:
                receipt = research.publish_projection(projection)
            except ResearchPublicationError as error:
                store.save(state.model_copy(update={"research_pending_projection": None}))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(error),
                ) from error
            publication = ResearchPublication(projection=projection, receipt=receipt)
            try:
                latest = store.load()
                store.save(
                    latest.model_copy(
                        update={
                            "research_publication": publication,
                            "research_pending_projection": None,
                        }
                    )
                )
            except OSError as error:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "The adapter accepted the idempotent projection but confirmation "
                        "could not be persisted; retry to reconcile it."
                    ),
                ) from error
            return publication

    def apply_evidence_event(event: EvidenceArrivalEvent) -> EvidenceArrivalResult:
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
                logger.warning(
                    "evidence_refresh_failed",
                    extra={
                        "event_id": event.event_id,
                        "preserved_version": update_error.preserved_version,
                    },
                )
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
            logger.info(
                "case_version_advanced",
                extra={
                    "case_id": refreshed.case_id,
                    "event_id": event.event_id,
                    "from_version": state.current_prepared_case.version,
                    "to_version": refreshed.version,
                },
            )
            return EvidenceArrivalResult(
                event_id=event.event_id,
                duplicate=False,
                prepared_case=refreshed,
            )

    @application.post(
        "/api/evidence-arrivals",
        response_model=EvidenceArrivalResult,
    )
    def receive_evidence(event: EvidenceArrivalEvent) -> EvidenceArrivalResult:
        if configured_publisher is None:
            return apply_evidence_event(event)

        state = store.load()
        if state.current_referral is None or state.current_prepared_case is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prepare the current case before delivering late evidence.",
            )
        if event.event_id in state.processed_evidence_events:
            return EvidenceArrivalResult(
                event_id=event.event_id,
                duplicate=True,
                prepared_case=state.current_prepared_case,
            )
        try:
            configured_publisher.publish(event)
        except OSError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

        deadline = monotonic() + 20
        while monotonic() < deadline:
            latest = store.load()
            if event.event_id in latest.processed_evidence_events:
                if latest.current_prepared_case is None:
                    break
                return EvidenceArrivalResult(
                    event_id=event.event_id,
                    duplicate=False,
                    prepared_case=latest.current_prepared_case,
                )
            if (
                latest.case_update_error is not None
                and latest.case_update_error.event_id == event.event_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=latest.case_update_error.message,
                )
            sleep(0.25)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "The Azure evidence trigger was published, but Event Grid did not confirm "
                "the case refresh within 20 seconds."
            ),
        )

    @application.post("/api/event-grid/evidence-arrivals")
    async def receive_event_grid_evidence(
        request: Request,
        x_event_grid_secret: str | None = Header(default=None),
    ) -> dict[str, object]:
        try:
            events = parse_event_grid_payload(await request.json())
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        validation_code = subscription_validation_code(events)
        if validation_code is not None:
            return {"validationResponse": validation_code}
        if (
            configured_publisher is None
            or configured_event_grid_secret is None
            or not secrets.compare_digest(
                x_event_grid_secret or "",
                configured_event_grid_secret,
            )
        ):
            raise HTTPException(status_code=403, detail="Event Grid delivery is not authorized.")

        accepted: list[str] = []
        for item in events:
            if item.get("eventType") != "Microsoft.Storage.BlobCreated":
                continue
            try:
                event = configured_publisher.read_event(event_grid_blob_url(item))
                apply_evidence_event(event)
            except (OSError, ValueError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            accepted.append(event.event_id)
            logger.info(
                "event_grid_delivery_accepted",
                extra={"event_id": event.event_id},
            )
        return {"accepted_event_ids": accepted}

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
    def reset(response: Response) -> None:
        try:
            with store.locked():
                store.load()
                store.save(DemoState())
                if configured_publisher is not None:
                    configured_publisher.reset()
        except OSError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        research_sessions.clear()
        response.delete_cookie("research_demo_session", samesite="strict")

    frontend_dist_path = frontend_dist or repository_root / "frontend" / "dist"
    assets_path = frontend_dist_path / "assets"
    if assets_path.exists():
        application.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    if (frontend_dist_path / "index.html").exists():

        @application.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            requested = frontend_dist_path / path
            if path and requested.is_file():
                return FileResponse(requested)
            return FileResponse(frontend_dist_path / "index.html")

    return application


app = create_app()
