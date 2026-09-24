"""Hospital service (SITE=nl or SITE=de). Owns its data, audit and nonces."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from fednet import data
from fednet.audit import utc_now
from fednet.cohort import CohortAggregate, CohortQuery, run_query
from fednet.common import (
    Runtime,
    base_app,
    new_correlation_id,
    signed_dependency,
    unavailable_detail,
)
from fednet.minimisation import MinimisationError, build_package, manifest, new_case_pseudonym
from fednet.signing import VerifiedCall
from fednet.transport import RemoteError, SignedClient, SiteUnavailable


class PeerReviewCreate(BaseModel):
    patient_id: str
    expert_id: str
    categories: list[str]
    question: str = Field(max_length=600)


class OpinionCreate(BaseModel):
    opinion: str = Field(min_length=10, max_length=4000)
    include_cohort_evidence: bool = True


class CohortRequest(BaseModel):
    query: CohortQuery = Field(default_factory=CohortQuery)


class ResetRequest(BaseModel):
    generation: int


class ConnectivityRequest(BaseModel):
    online: bool


def _remote_failure(error: Exception) -> HTTPException:
    if isinstance(error, SiteUnavailable):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, unavailable_detail(error.site))
    assert isinstance(error, RemoteError)
    return HTTPException(error.status_code, error.detail)


def create_site_app(site: str, runtime: Runtime, hub: SignedClient) -> FastAPI:
    info = data.SITES[site]
    application = base_app(runtime, f"{info['name']} (synthetic)")
    workstation = signed_dependency(runtime, (f"ws-{site}",))
    federation = signed_dependency(runtime, (f"hub-{site}",))
    admin = signed_dependency(runtime, (f"admin-{site}",))
    cohort_tables = data.utrecht_cohort() if site == "nl" else data.heidelberg_cohort()

    @application.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": site,
            "name": info["name"],
            "environment": info["environment"],
            "version": runtime.version,
            "generation": runtime.generation,
            "started_at": runtime.started_at,
        }

    # ---- federation namespace (hub → site) -------------------------------------

    @application.post("/federation/cohort", response_model=CohortAggregate)
    def local_cohort(
        request: CohortRequest, call: VerifiedCall = Depends(federation)
    ) -> CohortAggregate:
        aggregate = run_query(cohort_tables, request.query)
        runtime.record(
            source=site, destination="hub", correlation_id=call.correlation_id,
            operation="cohort_query", step="LOCAL_QUERY_EXECUTED", status="ok",
            detail=f"{aggregate.records_queried_locally} records queried locally · "
            f"{aggregate.records_transferred} transferred · {aggregate.suppressed_cells} "
            "small cells suppressed",
            payload=aggregate.model_dump(),
        )
        return aggregate

    # ---- admin namespace (hub admin → site) -------------------------------------

    @application.post("/admin/reset")
    def reset(request: ResetRequest, call: VerifiedCall = Depends(admin)) -> dict[str, int]:
        for prefix in ("peer-reviews/", "inbox/", "audit/"):
            runtime.store.delete_prefix(prefix)
        runtime.generation = request.generation
        runtime.record(
            source="hub", destination=site, correlation_id=call.correlation_id,
            operation="reset", step="RESET", status="ok",
            detail=f"generation {request.generation}",
        )
        return {"generation": request.generation}

    @application.post("/admin/connectivity")
    def connectivity(
        request: ConnectivityRequest, call: VerifiedCall = Depends(admin)
    ) -> dict[str, bool]:
        runtime.isolated = not request.online
        runtime.record(
            source="hub", destination=site, correlation_id=call.correlation_id,
            operation="connectivity", step="RECONNECTED" if request.online else "ISOLATED",
            status="ok" if request.online else "failed",
            detail=f"{info['name']} "
            + ("back online" if request.online else "isolated: all traffic refused at the edge"),
        )
        return {"online": request.online}

    @application.get("/admin/audit")
    def audit(call: VerifiedCall = Depends(admin)) -> list[dict[str, Any]]:
        return [event.model_dump() for event in runtime.audit.events(runtime.generation)]

    if site == "nl":
        _register_nl(application, runtime, hub, workstation, federation, admin)
    else:
        _register_de(application, runtime, hub, workstation, federation)
    return application


def _register_nl(
    application: FastAPI, runtime: Runtime, hub: SignedClient, workstation: Any,
    federation: Any, admin: Any,
) -> None:
    record = data.maria_record()

    def load(case_id: str) -> dict[str, Any]:
        item = runtime.read_json(f"peer-reviews/{case_id}.json")
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown peer-review case.")
        return dict(item)

    def all_reviews() -> list[dict[str, Any]]:
        return [
            runtime.read_json(key)
            for key in runtime.store.list("peer-reviews/")
        ]

    @application.get("/workstation/patients")
    def worklist(_: VerifiedCall = Depends(workstation)) -> list[dict[str, Any]]:
        reviews = all_reviews()
        return [
            {
                "id": data.PATIENT_ID, "name": "Maria Janssen", "age": 57, "sex": "F",
                "mrn": "UMCU-00482913",
                "summary": "mCRC, KRAS G12C, progression after FOLFOX and FOLFIRI",
                "flag": "Local options limited", "open_peer_reviews": len(reviews),
            },
            {"id": "umcu-00391177", "name": "Thomas Bakker", "age": 64, "sex": "M",
             "mrn": "UMCU-00391177", "summary": "Stage III rectal cancer, post neoadjuvant CRT",
             "flag": "Routine follow-up", "open_peer_reviews": 0, "restricted": True},
            {"id": "umcu-00517620", "name": "Fatima El Amrani", "age": 49, "sex": "F",
             "mrn": "UMCU-00517620", "summary": "Stage II colon cancer, adjuvant decision",
             "flag": "Local MDO next week", "open_peer_reviews": 0, "restricted": True},
        ]

    @application.get("/workstation/patients/{patient_id}")
    def chart(patient_id: str, _: VerifiedCall = Depends(workstation)) -> dict[str, Any]:
        if patient_id != data.PATIENT_ID:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chart not available in this demo.")
        return {
            "patient": record[0],
            "resources": record,
            "resource_count": len(record),
            "sharing_categories": data.SHARING_CATEGORIES,
            "peer_reviews": all_reviews(),
        }

    @application.get("/workstation/peer-reviews")
    def reviews(_: VerifiedCall = Depends(workstation)) -> list[dict[str, Any]]:
        return all_reviews()

    @application.post("/workstation/peer-reviews", status_code=status.HTTP_201_CREATED)
    def send_peer_review(
        request: PeerReviewCreate, _: VerifiedCall = Depends(workstation)
    ) -> dict[str, Any]:
        if request.patient_id != data.PATIENT_ID:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown patient.")
        expert = next((item for item in data.EXPERTS if item["id"] == request.expert_id), None)
        if expert is None or not expert["connected"]:
            raise HTTPException(status.HTTP_409_CONFLICT, "Expert site is not connected.")
        correlation_id = new_correlation_id()
        pseudonym = new_case_pseudonym()
        clinician = data.SITES["nl"]["clinician"]
        common = {"source": "nl", "destination": expert["site"], "correlation_id": correlation_id,
                  "operation": "peer_review"}
        runtime.record(**common, step="AUTHORIZED", status="ok",
                       detail=f"{clinician} (treating oncologist) authorised sharing for "
                       "peer review")
        try:
            package = build_package(record, request.categories, pseudonym=pseudonym,
                                    today=date.today())
        except MinimisationError as error:
            runtime.record(**common, step="MINIMISATION_REFUSED", status="denied",
                           detail=str(error))
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
        bundle, report = package["bundle"], package["report"]
        runtime.record(**common, step="MINIMISED", status="ok",
                       detail=f"{report['source_resources']} → {report['shared_resources']} "
                       "resources (allowlist)", manifest=manifest(bundle))
        runtime.record(**common, step="IDENTIFIERS_REMOVED", status="ok",
                       detail=f"case pseudonym {pseudonym}; "
                       + ", ".join(report["identifiers_removed"][:5]) + " …")
        runtime.record(**common, step="BUNDLE_BUILT", status="ok",
                       detail="FHIR-shaped collection bundle", manifest=manifest(bundle),
                       payload=bundle)
        review = {
            "case_id": pseudonym, "correlation_id": correlation_id, "patient_id": data.PATIENT_ID,
            "expert": expert, "question": request.question, "categories": report["categories"],
            "report": report, "bundle": bundle, "status": "sending", "created_at": utc_now(),
            "opinion": None, "error": None,
        }
        runtime.write_json(f"peer-reviews/{pseudonym}.json", review)
        try:
            hub.call(
                "POST", "/hub/peer-reviews", correlation_id=correlation_id, timeout=40.0,
                payload={"case_id": pseudonym, "destination": expert["site"],
                         "expert_id": expert["id"], "question": request.question,
                         "categories": report["categories"], "bundle": bundle,
                         "report": report},
            )
        except (SiteUnavailable, RemoteError) as error:
            detail = (
                unavailable_detail(error.site) if isinstance(error, SiteUnavailable)
                else str(error.detail)
            )
            review.update(status="delivery_failed", error=detail)
            runtime.write_json(f"peer-reviews/{pseudonym}.json", review)
            runtime.record(**common, step="SEND_FAILED", status="failed", detail=detail)
            return review
        review["status"] = "delivered"
        runtime.write_json(f"peer-reviews/{pseudonym}.json", review)
        runtime.record(**common, step="SENT", status="ok",
                       detail="Hub confirmed delivery to Heidelberg")
        return review

    @application.post("/workstation/peer-reviews/{case_id}/resend")
    def resend(case_id: str, _: VerifiedCall = Depends(workstation)) -> dict[str, Any]:
        review = load(case_id)
        if review["status"] != "delivery_failed":
            raise HTTPException(status.HTTP_409_CONFLICT, "Only failed deliveries can be resent.")
        common = {"source": "nl", "destination": review["expert"]["site"],
                  "correlation_id": review["correlation_id"], "operation": "peer_review"}
        try:
            hub.call("POST", "/hub/peer-reviews", correlation_id=review["correlation_id"],
                     timeout=40.0,
                     payload={"case_id": case_id, "destination": review["expert"]["site"],
                              "expert_id": review["expert"]["id"],
                              "question": review["question"], "categories": review["categories"],
                              "bundle": review["bundle"], "report": review["report"]})
        except (SiteUnavailable, RemoteError) as error:
            detail = (unavailable_detail(error.site) if isinstance(error, SiteUnavailable)
                      else str(error.detail))
            review.update(error=detail)
            runtime.write_json(f"peer-reviews/{case_id}.json", review)
            runtime.record(**common, step="SEND_FAILED", status="failed", detail=detail)
            return review
        review.update(status="delivered", error=None)
        runtime.write_json(f"peer-reviews/{case_id}.json", review)
        runtime.record(**common, step="SENT", status="ok", detail="Resent after reconnect")
        return review

    @application.post("/federation/opinions")
    def receive_opinion(
        payload: dict[str, Any], call: VerifiedCall = Depends(federation)
    ) -> dict[str, Any]:
        review = load(str(payload["case_id"]))
        review["opinion"] = {
            "text": payload["opinion"], "author": payload["author"],
            "institution": payload["institution"], "cohort": payload.get("cohort"),
            "received_at": utc_now(),
        }
        review["status"] = "opinion_received"
        runtime.write_json(f"peer-reviews/{review['case_id']}.json", review)
        runtime.record(source="de", destination="nl", correlation_id=call.correlation_id,
                       operation="peer_review_opinion", step="RECEIVED", status="ok",
                       detail=f"Opinion from {payload['author']} stored in the UMC Utrecht "
                       "record", payload=payload)
        return {"received": True}

    @application.get("/admin/peer-reviews/{case_id}/package")
    def package_as_sent(case_id: str, _: VerifiedCall = Depends(admin)) -> dict[str, Any]:
        review = load(case_id)
        return {"case_id": case_id, "correlation_id": review["correlation_id"],
                "bundle": review["bundle"], "report": review["report"]}


def _register_de(
    application: FastAPI, runtime: Runtime, hub: SignedClient, workstation: Any, federation: Any
) -> None:
    def load(case_id: str) -> dict[str, Any]:
        item = runtime.read_json(f"inbox/{case_id}.json")
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown case.")
        return dict(item)

    @application.post("/federation/peer-reviews")
    def receive_case(
        payload: dict[str, Any], call: VerifiedCall = Depends(federation)
    ) -> dict[str, Any]:
        key = f"inbox/{payload['case_id']}.json"
        existing = runtime.read_json(key)
        if existing is not None:
            return {"received": True, "case_id": payload["case_id"], "duplicate": True}
        runtime.write_json(key, {
            "case_id": payload["case_id"], "correlation_id": call.correlation_id,
            "from_site": "UMC Utrecht", "requested_by": data.SITES["nl"]["clinician"],
            "question": payload["question"], "categories": payload["categories"],
            "bundle": payload["bundle"], "report": payload["report"],
            "received_at": utc_now(), "status": "new", "cohort": None, "opinion": None,
        })
        runtime.record(source="hub", destination="de", correlation_id=call.correlation_id,
                       operation="peer_review", step="RECEIVED", status="ok",
                       detail="Approved case package stored in Heidelberg; shown in "
                       "Dr Müller's inbox", manifest={"resources": len(payload["bundle"]["entry"])},
                       payload=payload["bundle"])
        return {"received": True, "case_id": payload["case_id"]}

    @application.get("/workstation/inbox")
    def inbox(_: VerifiedCall = Depends(workstation)) -> list[dict[str, Any]]:
        cases = [runtime.read_json(key) for key in runtime.store.list("inbox/")]
        return sorted(cases, key=lambda item: item["received_at"], reverse=True)

    @application.get("/workstation/inbox/{case_id}")
    def case(case_id: str, _: VerifiedCall = Depends(workstation)) -> dict[str, Any]:
        item = load(case_id)
        if item["status"] == "new":
            item["status"] = "in_review"
            runtime.write_json(f"inbox/{case_id}.json", item)
        return item

    @application.post("/workstation/inbox/{case_id}/cohort-query")
    def compare(
        case_id: str, request: CohortRequest, _: VerifiedCall = Depends(workstation)
    ) -> dict[str, Any]:
        item = load(case_id)
        correlation_id = new_correlation_id()
        runtime.record(source="de", destination="hub", correlation_id=correlation_id,
                       operation="cohort_query", step="QUERY_REQUESTED", status="ok",
                       detail="Dr Anna Müller: compare with our patients (typed query, "
                       "no free SQL)", payload=request.query.model_dump())
        try:
            result = hub.call("POST", "/hub/cohort-queries", correlation_id=correlation_id,
                              timeout=40.0,
                              payload={"targets": ["de"], "query": request.query.model_dump(),
                                       "case_id": case_id})
        except (SiteUnavailable, RemoteError) as error:
            raise _remote_failure(error) from error
        item["cohort"] = {"correlation_id": correlation_id, **result}
        runtime.write_json(f"inbox/{case_id}.json", item)
        runtime.record(source="hub", destination="de", correlation_id=correlation_id,
                       operation="cohort_query", step="AGGREGATE_RECEIVED", status="ok",
                       detail="Aggregate only; 0 patient records transferred")
        return item

    @application.post("/workstation/inbox/{case_id}/opinion")
    def send_opinion(
        case_id: str, request: OpinionCreate, _: VerifiedCall = Depends(workstation)
    ) -> dict[str, Any]:
        item = load(case_id)
        cohort = item.get("cohort") if request.include_cohort_evidence else None
        payload = {
            "case_id": case_id, "destination": "nl", "opinion": request.opinion,
            "author": data.SITES["de"]["clinician"], "institution": data.SITES["de"]["name"],
            "cohort": {"results": cohort["results"]} if cohort else None,
        }
        runtime.record(source="de", destination="nl", correlation_id=item["correlation_id"],
                       operation="peer_review_opinion", step="OPINION_SIGNED", status="ok",
                       detail="Dr Anna Müller signed the peer-review opinion")
        try:
            hub.call("POST", "/hub/results", correlation_id=item["correlation_id"],
                     timeout=40.0, payload=payload)
        except (SiteUnavailable, RemoteError) as error:
            raise _remote_failure(error) from error
        item.update(status="completed", opinion={"text": request.opinion, "sent_at": utc_now()})
        runtime.write_json(f"inbox/{case_id}.json", item)
        return item
