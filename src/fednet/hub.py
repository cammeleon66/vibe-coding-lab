"""Federation hub (SITE=hub): UI host, typed BFF, policy, routing, fan-out, audit."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fednet import data
from fednet.audit import body_digest
from fednet.cohort import CohortQuery
from fednet.common import (
    Runtime,
    base_app,
    new_correlation_id,
    signed_dependency,
    unavailable_detail,
)
from fednet.policy import Decision, PolicyRequest, evaluate
from fednet.signing import VerifiedCall
from fednet.transport import RemoteError, SignedClient, SiteUnavailable

ACCESS_COOKIE = "fed_demo_access"
ACCESS_TTL_SECONDS = 12 * 60 * 60
CONNECTED = ("nl", "de")


class AccessCreate(BaseModel):
    code: str = Field(max_length=200)


class PeerReviewRequest(BaseModel):
    patient_id: str
    expert_id: str
    categories: list[str]
    question: str = Field(max_length=600)


class OpinionRequest(BaseModel):
    opinion: str = Field(min_length=10, max_length=4000)
    include_cohort_evidence: bool = True


class CohortRequest(BaseModel):
    query: CohortQuery = Field(default_factory=CohortQuery)


class ConnectivityRequest(BaseModel):
    online: bool


def _token(secret: str) -> str:
    expires = str(int(time.time()) + ACCESS_TTL_SECONDS)
    return expires + "." + hmac.new(secret.encode(), expires.encode(), hashlib.sha256).hexdigest()


def _valid_token(token: str | None, secret: str) -> bool:
    if not token or "." not in token:
        return False
    expires, signature = token.split(".", 1)
    if not expires.isdigit() or int(expires) <= time.time():
        return False
    expected = hmac.new(secret.encode(), expires.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


ACCESS_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>European oncology network (synthetic)</title><style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3f5f7;
font-family:Inter,system-ui,sans-serif;color:#14212b}
main{width:min(26rem,calc(100% - 2rem));padding:2rem;background:#fff;border:1px solid #d5dde3;
border-radius:8px}h1{font-size:1.4rem;margin:.4rem 0 1rem}p{color:#4a5a66;line-height:1.5}
.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
color:#0b6e75}label{display:block;margin:1.2rem 0 .4rem;font-weight:600}
input,button{width:100%;box-sizing:border-box;min-height:2.8rem;font:inherit;border-radius:6px}
input{border:1px solid #9aa9b4;padding:0 .8rem}button{margin-top:.8rem;border:0;
background:#0b6e75;color:#fff;font-weight:700;cursor:pointer}#error{color:#b42318;min-height:1.4rem}
</style></head><body><main><div class="eyebrow">Synthetic clinical demonstration</div>
<h1>European oncology network</h1><p>Enter the shared demo code.</p>
<form id="f"><label for="code">Demo access code</label>
<input id="code" type="password" autocomplete="current-password" required autofocus>
<button type="submit">Open workspace</button><p id="error" role="alert"></p></form></main>
<script>document.getElementById("f").addEventListener("submit",async e=>{e.preventDefault();
const r=await fetch("/api/demo-access",{method:"POST",headers:{"Content-Type":"application/json"},
body:JSON.stringify({code:document.getElementById("code").value})});
if(r.ok){const n=new URLSearchParams(location.search).get("next")||"/";
location.assign(n.startsWith("/")&&!n.startsWith("//")?n:"/");return}
document.getElementById("error").textContent="That access code is not valid."});</script>
</body></html>"""


def _score(expert: dict[str, Any], query: str) -> int:
    tokens = {token for token in query.lower().replace(",", " ").split() if token}
    return len(tokens & set(expert["tags"]))


def create_hub_app(
    runtime: Runtime,
    *,
    workstation: dict[str, SignedClient],
    federation: dict[str, SignedClient],
    admin: dict[str, SignedClient],
    frontend_dist: Path | None = None,
    access_code: str | None = None,
    session_secret: str | None = None,
) -> FastAPI:
    if bool(access_code) != bool(session_secret):
        raise RuntimeError("DEMO_ACCESS_CODE and DEMO_SESSION_SECRET must be set together.")
    application = base_app(runtime, "European federation hub (synthetic)")
    from_site = signed_dependency(runtime, ("nl-hub", "de-hub"))

    @application.middleware("http")
    async def require_access(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if (
            not access_code
            or not session_secret
            or path in {"/api/health", "/api/demo-access", "/demo-access"}
            or path.startswith("/hub/")
            or _valid_token(request.cookies.get(ACCESS_COOKIE), session_secret)
        ):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Demo access is required."}, status_code=401)
        return RedirectResponse(f"/demo-access?next={path}", status_code=307)

    @application.get("/demo-access", response_class=HTMLResponse)
    def access_page() -> str:
        return ACCESS_PAGE

    @application.post("/api/demo-access", status_code=status.HTTP_204_NO_CONTENT)
    def grant_access(payload: AccessCreate, response: Response) -> None:
        if not access_code or not session_secret:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Demo access is not configured.")
        if not hmac.compare_digest(payload.code.encode(), access_code.encode()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "The demo access code is invalid.")
        response.set_cookie(ACCESS_COOKIE, _token(session_secret), max_age=ACCESS_TTL_SECONDS,
                            httponly=True, secure=True, samesite="strict")

    # ---- helpers -------------------------------------------------------------------

    def record(**fields: Any) -> None:
        runtime.record(**fields)

    def pending() -> list[str]:
        return list(runtime.read_json("state/pending.json", []))

    def set_pending(sites: list[str]) -> None:
        runtime.write_json("state/pending.json", sites)

    def reconcile(site: str, site_generation: int | None) -> bool:
        """Push the current reset generation to a site that missed it."""
        if site_generation == runtime.generation and site not in pending():
            return True
        try:
            admin[site].call("POST", "/admin/reset", correlation_id=new_correlation_id(),
                             payload={"generation": runtime.generation}, timeout=10.0)
        except (SiteUnavailable, RemoteError):
            return False
        set_pending([item for item in pending() if item != site])
        record(source="hub", destination=site, correlation_id="reset", operation="reset",
               step="RECONCILED", status="ok",
               detail=f"{data.SITES[site]['name']} reconciled to generation {runtime.generation}")
        return True

    def bff(site: str, method: str, path: str, payload: Any = None, timeout: float = 10.0) -> Any:
        try:
            return workstation[site].call(method, path, correlation_id=new_correlation_id(),
                                          payload=payload, timeout=timeout)
        except SiteUnavailable as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                unavailable_detail(error.site)) from error
        except RemoteError as error:
            raise HTTPException(error.status_code, error.detail) from error

    def deliver(site: str, path: str, payload: Any, correlation_id: str, operation: str) -> Any:
        common = {"source": "hub", "destination": site, "correlation_id": correlation_id,
                  "operation": operation}
        try:
            result = federation[site].call("POST", path, correlation_id=correlation_id,
                                           payload=payload, timeout=10.0, retries=1)
        except SiteUnavailable as error:
            record(**common, step="DELIVERY_FAILED", status="failed",
                   detail=unavailable_detail(site))
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                unavailable_detail(site)) from error
        except RemoteError as error:
            record(**common, step="DELIVERY_FAILED", status="failed", detail=str(error.detail))
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error.detail)) from error
        record(**common, step="DELIVERED", status="ok",
               detail=f"Accepted by {data.SITES[site]['name']}")
        return result

    def fan_out(source: str, targets: list[str], query: CohortQuery,
                correlation_id: str) -> dict[str, Any]:
        decisions = [evaluate(PolicyRequest("cohort_aggregate", source, t)) for t in targets]
        decision = Decision(all(item.allowed for item in decisions),
                            [reason for item in decisions for reason in item.reasons])
        record(source=source, destination="+".join(targets), correlation_id=correlation_id,
               operation="cohort_query", step="POLICY_ALLOWED" if decision.allowed
               else "POLICY_DENIED", status="ok" if decision.allowed else "denied",
               detail="; ".join(decision.reasons),
               policy={"allowed": decision.allowed, "reasons": decision.reasons},
               payload=query.model_dump())
        if not decision.allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "; ".join(decision.reasons))
        results: list[dict[str, Any]] = []
        unavailable: list[dict[str, str]] = []
        for target in targets:
            common = {"source": "hub", "destination": target, "correlation_id": correlation_id,
                      "operation": "cohort_query"}
            record(**common, step="QUERY_ROUTED", status="ok",
                   detail=f"Typed query sent to {data.SITES[target]['name']} cohort engine")
            try:
                aggregate = federation[target].call(
                    "POST", "/federation/cohort", correlation_id=correlation_id,
                    payload={"query": query.model_dump()}, timeout=15.0)
            except (SiteUnavailable, RemoteError):
                unavailable.append({"site": target, "detail": unavailable_detail(target)})
                record(**common, step="SITE_UNAVAILABLE", status="failed",
                       detail=unavailable_detail(target))
                continue
            results.append({**aggregate, "name": data.SITES[target]["name"]})
            record(source=target, destination="hub", correlation_id=correlation_id,
                   operation="cohort_query", step="AGGREGATE_RETURNED", status="ok",
                   detail=f"{aggregate['records_queried_locally']} queried locally · "
                   f"{aggregate['records_transferred']} records transferred",
                   payload=aggregate)
        return {
            "correlation_id": correlation_id,
            "query": query.model_dump(),
            "results": results,
            "unavailable": unavailable,
            "complete": not unavailable,
            "not_connected": data.CATALOGUE_ONLY_SITES,
            "records_transferred": 0,
        }

    # ---- health, sites, reset ----------------------------------------------------

    @application.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "hub", "name": data.SITES["hub"]["name"],
                "environment": data.SITES["hub"]["environment"], "version": runtime.version,
                "generation": runtime.generation, "started_at": runtime.started_at}

    @application.get("/api/sites")
    def sites() -> dict[str, Any]:
        items: list[dict[str, Any]] = [
            {**health(), "site": "hub", "reachable": True, "latency_ms": 0,
             "role": "Routing, policy, audit"}
        ]
        isolated = set(runtime.read_json("state/isolated.json", []))
        for site in CONNECTED:
            body, elapsed, error = workstation[site].health()
            reachable = body is not None
            synced = reachable and reconcile(site, int(body["generation"]) if body else None)
            items.append({
                "site": site, "name": data.SITES[site]["name"],
                "environment": data.SITES[site]["environment"], "reachable": reachable,
                "latency_ms": round(elapsed * 1000), "error": error,
                "version": body.get("version") if body else None,
                "generation": runtime.generation if synced else (body or {}).get("generation"),
                "synced": synced, "warm": reachable and elapsed < 2.0,
                "isolated": site in isolated,
                "role": "Treating hospital" if site == "nl" else "Expert centre",
            })
        return {"generation": runtime.generation, "pending_reset": pending(),
                "synced": not pending(), "sites": items,
                "catalogue_only": data.CATALOGUE_ONLY_SITES}

    @application.post("/api/reset")
    def reset() -> dict[str, Any]:
        for site in runtime.read_json("state/isolated.json", []):
            try:
                admin[site].call("POST", "/admin/connectivity", correlation_id="reset",
                                 payload={"online": True}, timeout=10.0)
            except (SiteUnavailable, RemoteError):
                continue
        runtime.write_json("state/isolated.json", [])
        runtime.store.delete_prefix("audit/")
        runtime.store.delete_prefix("routes/")
        runtime.generation = runtime.generation + 1
        set_pending(list(CONNECTED))
        for site in CONNECTED:
            reconcile(site, None)
        record(source="hub", destination="nl+de", correlation_id="reset", operation="reset",
               step="RESET", status="ok" if not pending() else "partial",
               detail=f"generation {runtime.generation}"
               + (f"; pending: {', '.join(pending())}" if pending() else ""))
        return {"generation": runtime.generation, "pending_reset": pending()}

    @application.post("/api/sites/{site}/connectivity")
    def set_connectivity(site: str, request: ConnectivityRequest) -> dict[str, Any]:
        if site not in CONNECTED:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown connected site.")
        correlation_id = new_correlation_id()
        try:
            admin[site].call("POST", "/admin/connectivity", correlation_id=correlation_id,
                             payload={"online": request.online}, timeout=10.0)
        except SiteUnavailable as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                f"{data.SITES[site]['name']} cannot be reached to change its "
                                "connectivity (is the service stopped?)") from error
        except RemoteError as error:
            raise HTTPException(error.status_code, error.detail) from error
        isolated = set(runtime.read_json("state/isolated.json", []))
        if request.online:
            isolated.discard(site)
        else:
            isolated.add(site)
        runtime.write_json("state/isolated.json", sorted(isolated))
        record(source="hub", destination=site, correlation_id=correlation_id,
               operation="connectivity",
               step="SITE_RECONNECTED" if request.online else "SITE_ISOLATED",
               status="ok" if request.online else "failed",
               detail=f"Operator {'reconnected' if request.online else 'isolated'} "
               f"{data.SITES[site]['name']}")
        return {"site": site, "online": request.online}

    # ---- federation services (metadata only) ----------------------------------------

    @application.get("/api/federation/experts")
    def experts(q: str = "") -> list[dict[str, Any]]:
        scored = [(_score(item, q), item) for item in data.EXPERTS]
        minimum = (len(q.split()) + 1) // 2 if q.strip() else 0
        return [
            {key: value for key, value in item.items() if key != "tags"} | {"score": score}
            for score, item in sorted(scored, key=lambda pair: -pair[0])
            if score >= minimum
        ]

    @application.get("/api/federation/activity")
    def activity(correlation_id: str | None = None) -> dict[str, Any]:
        events = [event.model_dump() for event in runtime.audit.events(runtime.generation)]
        unavailable: list[str] = []
        for site in CONNECTED:
            try:
                events.extend(admin[site].call("GET", "/admin/audit", correlation_id="audit-read",
                                               timeout=5.0, allow_cold_start=False))
            except (SiteUnavailable, RemoteError):
                unavailable.append(site)
        if correlation_id:
            events = [event for event in events if event["correlation_id"] == correlation_id]
        events.sort(key=lambda event: event["timestamp"])
        return {"events": events, "unavailable": unavailable, "generation": runtime.generation}

    @application.get("/api/federation/progress")
    def progress() -> dict[str, bool]:
        events = runtime.audit.events(runtime.generation)

        def seen(operation: str, step: str, destination: str | None = None) -> bool:
            return any(e.operation == operation and e.step == step
                       and (destination is None or e.destination == destination) for e in events)

        return {
            "case_sent": seen("peer_review", "DELIVERED", "de"),
            "cohort_compared": any(e.step == "AGGREGATE_RETURNED" and e.source == "de"
                                   for e in events),
            "opinion_returned": seen("peer_review_opinion", "DELIVERED", "nl"),
            "research_run": seen("cohort_query", "POLICY_ALLOWED", "nl+de"),
            "disconnect_seen": any(e.step in {"DELIVERY_FAILED", "SITE_UNAVAILABLE"}
                                   for e in events),
        }

    @application.get("/api/federation/peer-reviews/{case_id}/package")
    def package(case_id: str) -> dict[str, Any]:
        try:
            result = admin["nl"].call("GET", f"/admin/peer-reviews/{case_id}/package",
                                      correlation_id="package-read", timeout=10.0)
        except SiteUnavailable as error:
            raise HTTPException(503, unavailable_detail("nl")) from error
        except RemoteError as error:
            raise HTTPException(error.status_code, error.detail) from error
        digest = body_digest(result["bundle"])
        audited = [e for e in runtime.audit.events(runtime.generation)
                   if e.correlation_id == result["correlation_id"] and e.step == "VERIFIED"
                   and e.operation == "peer_review"]
        return {**result, "retrieved_from": "UMC Utrecht", "sha256": digest,
                "matches_audit": bool(audited) and audited[-1].body_sha256 == digest}

    # ---- site → hub (signed) -------------------------------------------------------

    @application.post("/hub/peer-reviews", status_code=status.HTTP_202_ACCEPTED)
    def route_peer_review(
        payload: dict[str, Any], call: VerifiedCall = Depends(from_site)
    ) -> dict[str, Any]:
        source, destination = call.signer, str(payload["destination"])
        correlation_id = call.correlation_id
        route_key = f"routes/{correlation_id}-peer_review.json"
        cached = runtime.read_json(route_key)
        if cached is not None:
            return dict(cached)
        common = {"source": source, "destination": destination,
                  "correlation_id": correlation_id, "operation": "peer_review"}
        record(**common, step="VERIFIED", status="ok",
               detail=f"Signature verified ({call.key_name}); case {payload['case_id']}",
               manifest={"resources": len(payload["bundle"]["entry"])},
               payload=payload["bundle"])
        decision = evaluate(PolicyRequest("peer_review", source, destination,
                                          tuple(payload["categories"]),
                                          len(payload["bundle"]["entry"])))
        record(**common, step="POLICY_ALLOWED" if decision.allowed else "POLICY_DENIED",
               status="ok" if decision.allowed else "denied", detail="; ".join(decision.reasons),
               policy={"allowed": decision.allowed, "reasons": decision.reasons})
        if not decision.allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "; ".join(decision.reasons))
        record(**common, step="ROUTED", status="ok",
               detail=f"Routing to {data.SITES[destination]['name']} (expert "
               f"{payload['expert_id']})")
        deliver(destination, "/federation/peer-reviews", payload, correlation_id, "peer_review")
        result = {"delivered": True, "destination": destination}
        runtime.write_json(route_key, result)
        return result

    @application.post("/hub/results", status_code=status.HTTP_202_ACCEPTED)
    def route_opinion(
        payload: dict[str, Any], call: VerifiedCall = Depends(from_site)
    ) -> dict[str, Any]:
        destination = str(payload["destination"])
        common = {"source": call.signer, "destination": destination,
                  "correlation_id": call.correlation_id, "operation": "peer_review_opinion"}
        record(**common, step="VERIFIED", status="ok",
               detail=f"Signature verified ({call.key_name})", payload=payload)
        decision = evaluate(PolicyRequest("peer_review_opinion", call.signer, destination))
        record(**common, step="POLICY_ALLOWED", status="ok", detail="; ".join(decision.reasons),
               policy={"allowed": True, "reasons": decision.reasons})
        record(**common, step="ROUTED", status="ok", detail="Routing opinion to UMC Utrecht")
        deliver(destination, "/federation/opinions", payload, call.correlation_id,
                "peer_review_opinion")
        return {"delivered": True}

    @application.post("/hub/cohort-queries")
    def route_cohort(
        payload: dict[str, Any], call: VerifiedCall = Depends(from_site)
    ) -> dict[str, Any]:
        targets = [str(item) for item in payload["targets"]]
        if not targets or any(item not in CONNECTED for item in targets):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown cohort target.")
        record(source=call.signer, destination="hub", correlation_id=call.correlation_id,
               operation="cohort_query", step="VERIFIED", status="ok",
               detail=f"Signature verified ({call.key_name})")
        return fan_out(call.signer, targets, CohortQuery.model_validate(payload["query"]),
                       call.correlation_id)

    # ---- typed BFF (browser → hub → hospital workstation APIs) ----------------------

    @application.get("/api/nl/patients")
    def nl_patients() -> Any:
        return bff("nl", "GET", "/workstation/patients")

    @application.get("/api/nl/patients/{patient_id}")
    def nl_chart(patient_id: str) -> Any:
        return bff("nl", "GET", f"/workstation/patients/{patient_id}")

    @application.get("/api/nl/peer-reviews")
    def nl_reviews() -> Any:
        return bff("nl", "GET", "/workstation/peer-reviews")

    @application.post("/api/nl/peer-reviews", status_code=status.HTTP_201_CREATED)
    def nl_send(request: PeerReviewRequest) -> Any:
        if pending():
            for site in list(pending()):
                reconcile(site, None)
        if pending():
            names = ", ".join(data.SITES[site]["name"] for site in pending())
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"Reset not yet applied at {names}; reconnect before sharing.")
        return bff("nl", "POST", "/workstation/peer-reviews", request.model_dump(), timeout=60.0)

    @application.post("/api/nl/peer-reviews/{case_id}/resend")
    def nl_resend(case_id: str) -> Any:
        return bff("nl", "POST", f"/workstation/peer-reviews/{case_id}/resend", timeout=60.0)

    @application.get("/api/de/inbox")
    def de_inbox() -> Any:
        return bff("de", "GET", "/workstation/inbox")

    @application.get("/api/de/inbox/{case_id}")
    def de_case(case_id: str) -> Any:
        return bff("de", "GET", f"/workstation/inbox/{case_id}")

    @application.post("/api/de/inbox/{case_id}/cohort-query")
    def de_compare(case_id: str, request: CohortRequest) -> Any:
        return bff("de", "POST", f"/workstation/inbox/{case_id}/cohort-query",
                   request.model_dump(), timeout=60.0)

    @application.post("/api/de/inbox/{case_id}/opinion")
    def de_opinion(case_id: str, request: OpinionRequest) -> Any:
        return bff("de", "POST", f"/workstation/inbox/{case_id}/opinion", request.model_dump(),
                   timeout=60.0)

    @application.post("/api/research/cohort-queries")
    def research(request: CohortRequest) -> dict[str, Any]:
        return fan_out("hub", list(CONNECTED), request.query, new_correlation_id())

    # ---- frontend --------------------------------------------------------------------

    if frontend_dist is not None and (frontend_dist / "index.html").exists():
        root = frontend_dist.resolve()
        if (root / "assets").exists():
            application.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @application.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            if path.startswith(("api/", "hub/")):
                raise HTTPException(status.HTTP_404_NOT_FOUND)
            requested = (root / path).resolve()
            if path and requested.is_file() and requested.is_relative_to(root):
                return FileResponse(requested)
            return FileResponse(root / "index.html")

    return application
