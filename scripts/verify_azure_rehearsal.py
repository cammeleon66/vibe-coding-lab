from __future__ import annotations

import argparse
import json
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, OpenerDirector, Request, build_opener


def request_json(
    opener: OpenerDirector,
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with opener.open(request, timeout=60) as response:
            content = response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with HTTP {error.code}: {detail}") from error
    return None if not content else json.loads(content)


def verify(base_url: str, access_code: str | None = None) -> None:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(
        path: str,
        *,
        method: str = "GET",
        payload: object | None = None,
    ) -> Any:
        return request_json(
            opener,
            base_url,
            path,
            method=method,
            payload=payload,
        )

    if access_code:
        call("/api/demo-access", method="POST", payload={"code": access_code})

    preflight = call("/api/preflight")
    if not preflight["ready"] or preflight["mode"] != "azure-synthetic-rehearsal":
        raise RuntimeError(f"Azure preflight was not ready: {preflight}")

    call("/api/reset", method="POST")
    referral = call(
        "/api/referrals",
        method="POST",
        payload={
            "need": {},
            "centre_id": "utrecht-crc",
            "clinician_id": "eva-van-dijk",
            "urgency": "expedited",
            "sender": {
                "clinician_name": "Dr Luca Bianchi",
                "institution": "Istituto Nazionale dei Tumori, Milan",
                "country": "Italy",
            },
        },
    )
    prepared = call("/api/cases/current/prepare", method="POST")
    if referral["id"] != prepared["referral_id"] or prepared["version"] != 1:
        raise RuntimeError("Azure referral-to-prepared-case continuity failed.")

    arrival = call(
        "/api/evidence-arrivals",
        method="POST",
        payload={
            "event_id": "azure-event-grid-imaging-001",
            "event_type": "Microsoft.Storage.BlobCreated",
            "subject": "/synthetic/milan/CRC-EU-001/imaging",
            "case_id": prepared["case_id"],
            "evidence_set": "baseline-and-restaging-imaging",
            "occurred_at": "2026-09-23T18:00:00Z",
        },
    )
    updated = arrival["prepared_case"]
    if arrival["duplicate"] or updated["version"] != 2 or updated["delta"] is None:
        raise RuntimeError("Event Grid did not produce the expected prepared case v2 delta.")

    review_state = call("/api/cases/current/review")
    conditions = [
        {
            "issue_id": condition["issue_id"],
            "status": "resolved",
            "resolution": "Reviewed explicitly for this synthetic Azure rehearsal.",
        }
        for condition in review_state["required_conditions"]
    ]
    reviewed = call(
        "/api/cases/current/reviews",
        method="POST",
        payload={
            "case_version": 2,
            "reviewer": "Dr Eva van Dijk (fictional)",
            "opinion": (
                "The source-linked imaging update warrants multidisciplinary "
                "reassessment; no automated resectability conclusion is recorded."
            ),
            "conditions": conditions,
            "next_responsibility": {
                "actor": "Synthetic Utrecht colorectal liver team",
                "action": "Carry the versioned case into multidisciplinary review.",
            },
        },
    )
    if not reviewed["handoff_ready"] or reviewed["opinion"] is None:
        raise RuntimeError("Azure human-review responsibility gate did not become ready.")

    manifest = call(
        "/api/cases/current/handoffs",
        method="POST",
        payload={
            "case_version": 2,
            "opinion_id": reviewed["opinion"]["id"],
        },
    )
    if manifest["evidence_version"] != 2 or not manifest["separate_backend"]:
        raise RuntimeError("Azure MDO handoff continuity was not preserved.")

    call("/api/reset", method="POST")
    if call("/api/cases/current") is not None:
        raise RuntimeError("Azure rehearsal reset did not restore a clean state.")

    print(
        json.dumps(
            {
                "status": "pass",
                "mode": preflight["mode"],
                "prepared_versions": [1, 2],
                "event_grid_event": arrival["event_id"],
                "handoff_manifest": manifest["id"],
                "final_state": "clean",
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--access-code")
    arguments = parser.parse_args()
    verify(arguments.base_url, arguments.access_code)


if __name__ == "__main__":
    main()
