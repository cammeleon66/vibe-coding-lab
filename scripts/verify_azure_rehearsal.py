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
    unauthenticated = build_opener()
    health = request_json(unauthenticated, base_url, "/api/health")
    if health["status"] != "ok" or health["mode"] != "azure-synthetic-rehearsal":
        raise RuntimeError(f"Azure health response was not ready: {health}")
    try:
        request_json(unauthenticated, base_url, "/api/journey")
    except RuntimeError as error:
        if "HTTP 401" not in str(error):
            raise
    else:
        raise RuntimeError("Protected journey API was accessible without the demo session.")

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

    def action(payload: dict[str, object]) -> Any:
        return call("/api/journey/actions", method="POST", payload=payload)

    for source_id in ("utrecht_patient_summary", "utrecht_imaging"):
        regional = action({"type": "query_regional_source", "source_id": source_id})
    if len(regional["regional_exchange"]["source_checks"]) != 2:
        raise RuntimeError("The regional hospital source checks did not complete.")
    regional = action({"type": "approve_regional_exchange"})
    if not regional["regional_exchange"]["sharing_approved"]:
        raise RuntimeError("The regional sharing approval was not persisted.")
    scale = action({"type": "open_scale_reveal"})
    if scale["regional_exchange"]["phase"] != "scale_reveal":
        raise RuntimeError("The European scale reveal did not open.")
    international = action({"type": "open_international_referral"})
    if international["regional_exchange"]["phase"] != "international_referral":
        raise RuntimeError("The international referral did not open after the scale reveal.")

    action({"type": "enter_role", "role": "milan"})
    action({"type": "select_patient", "patient_id": "CRC-EU-001"})
    for source_id in ("milan_ehr", "milan_documents", "milan_pacs"):
        source_snapshot = action({"type": "query_source", "source_id": source_id})
    if source_snapshot["stages"][2]["status"] != "current":
        raise RuntimeError("Federated Milan source checks did not unlock referral preparation.")

    action(
        {
            "type": "confirm_referral_question",
            "question": ("Please assess response to conversion therapy and liver resectability."),
        }
    )
    matches = action({"type": "query_expert_directory"})
    if matches["destinations"][0]["centre_id"] != "utrecht-crc":
        raise RuntimeError("Utrecht was not the highest explainable destination match.")
    action(
        {
            "type": "select_destination",
            "centre_id": "utrecht-crc",
            "clinician_id": "eva-van-dijk",
        }
    )
    action({"type": "query_requirements"})
    prepared = action({"type": "prepare_referral_package"})
    if prepared["package"]["case_version"] != 1:
        raise RuntimeError("Azure package preparation did not produce case version 1.")
    sent = action(
        {
            "type": "approve_referral_package",
            "referral_assessment": (
                "Giulia has liver-limited metastatic colorectal cancer with response after "
                "conversion therapy. Please assess resectability and the next "
                "multidisciplinary step."
            ),
        }
    )
    if not sent["package"]["approved"] or sent["next_role"] != "utrecht":
        raise RuntimeError("Milan approval did not release case version 1 to Utrecht.")

    action({"type": "enter_role", "role": "utrecht"})
    action({"type": "acknowledge_case_version", "case_version": 1})
    action(
        {
            "type": "record_provisional_opinion",
            "opinion": (
                "The response supports multidisciplinary liver review, but original "
                "baseline CT and restaging liver MRI are needed before the final opinion."
            ),
        }
    )
    requested = action(
        {
            "type": "request_evidence",
            "requested_evidence": [
                "Original baseline liver CT",
                "Restaging liver MRI",
            ],
            "clinical_reason": (
                "Original lesion sites and current vessel relationships must be reviewed "
                "before the multidisciplinary resectability decision."
            ),
        }
    )
    if requested["next_role"] != "milan":
        raise RuntimeError("The Utrecht imaging request did not return responsibility to Milan.")
    action({"type": "enter_role", "role": "milan"})

    arrival = call(
        "/api/evidence-arrivals",
        method="POST",
        payload={
            "event_id": "azure-event-grid-imaging-001",
            "event_type": "Microsoft.Storage.BlobCreated",
            "subject": "/synthetic/milan/CRC-EU-001/imaging",
            "case_id": "CRC-EU-001",
            "evidence_set": "baseline-and-restaging-imaging",
            "occurred_at": "2026-09-23T18:00:00Z",
        },
    )
    updated = arrival["prepared_case"]
    if arrival["duplicate"] or updated["version"] != 2 or updated["delta"] is None:
        raise RuntimeError("Event Grid did not produce the expected prepared case v2 delta.")

    approved = action({"type": "approve_evidence_update", "case_version": 2})
    if approved["update_approved_versions"] != [2]:
        raise RuntimeError("Milan did not approve the version 2 sharing update.")
    action({"type": "enter_role", "role": "utrecht"})
    action({"type": "acknowledge_case_version", "case_version": 2})
    action(
        {
            "type": "record_final_opinion",
            "opinion": (
                "Case version 2 accounts for the original lesion sites and current vessel "
                "relationships. The case is appropriate for Utrecht liver MDO review to "
                "determine the combined local treatment plan."
            ),
        }
    )
    accepted = action(
        {
            "type": "accept_mdo_outcome",
            "scheduled_for": "29 September 2026 at 14:00 CEST",
            "next_action": (
                "Discuss the Utrecht opinion and MDO schedule with Giulia, confirm "
                "attendance, and provide any interval clinical changes."
            ),
        }
    )
    if accepted["mdo_outcome"]["case_version"] != 2:
        raise RuntimeError("Utrecht MDO acceptance did not reference case version 2.")
    action({"type": "enter_role", "role": "milan"})
    returned = call("/api/journey")
    restored = call("/api/journey")
    if returned["mdo_outcome"] != restored["mdo_outcome"]:
        raise RuntimeError("The returned MDO outcome did not survive journey refresh.")
    if len(restored["activity"]) < 26:
        raise RuntimeError("The persisted cross-hospital activity timeline is incomplete.")

    call("/api/reset", method="POST")
    clean = call("/api/journey")
    if (
        clean["active_role"] is not None
        or clean["activity"]
        or clean["regional_exchange"]["phase"] != "regional_exchange"
    ):
        raise RuntimeError("Azure rehearsal reset did not restore a clean state.")

    print(
        json.dumps(
            {
                "status": "pass",
                "mode": preflight["mode"],
                "protected_access": "pass",
                "regional_sources": 2,
                "international_sources": 3,
                "prepared_versions": [1, 2],
                "event_grid_event": arrival["event_id"],
                "mdo_case_version": accepted["mdo_outcome"]["case_version"],
                "timeline_events": len(restored["activity"]),
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
