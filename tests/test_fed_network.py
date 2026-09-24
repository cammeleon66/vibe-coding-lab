from __future__ import annotations

import json

from conftest import Network, build_network, send_case
from fastapi.testclient import TestClient

from fednet.data import DIRECT_IDENTIFIERS


def _steps(network: Network, correlation_id: str) -> list[tuple[str, str]]:
    events = network.ui().get("/api/federation/activity",
                              params={"correlation_id": correlation_id}).json()["events"]
    return [(event["service"], event["step"]) for event in events]


def test_worklist_and_chart_come_from_the_nl_service(net: Network) -> None:
    patients = net.ui().get("/api/nl/patients").json()
    assert patients[0]["name"] == "Maria Janssen"
    chart = net.ui().get("/api/nl/patients/umcu-00482913").json()
    assert chart["resource_count"] == 27
    assert net.ui().get("/api/de/inbox").json() == []


def test_expert_search_returns_metadata_only(net: Network) -> None:
    experts = net.ui().get("/api/federation/experts",
                           params={"q": "KRAS G12C colorectal cancer"}).json()
    assert [item["site"] for item in experts] == ["de", "milan", "antwerp"]
    assert experts[0]["connected"] and not experts[1]["connected"]
    assert "patients" not in json.dumps(experts)


def test_full_peer_review_across_three_services(net: Network) -> None:
    review = send_case(net)
    assert review["status"] == "delivered"
    correlation_id = review["correlation_id"]

    inbox = net.ui().get("/api/de/inbox").json()
    assert len(inbox) == 1 and inbox[0]["correlation_id"] == correlation_id
    assert len(inbox[0]["bundle"]["entry"]) == 9
    for identifier in DIRECT_IDENTIFIERS:
        assert identifier not in json.dumps(inbox[0], ensure_ascii=False)

    steps = _steps(net, correlation_id)
    for expected in [("nl", "AUTHORIZED"), ("nl", "MINIMISED"), ("nl", "IDENTIFIERS_REMOVED"),
                     ("nl", "BUNDLE_BUILT"), ("hub", "VERIFIED"), ("hub", "POLICY_ALLOWED"),
                     ("hub", "ROUTED"), ("de", "RECEIVED"), ("hub", "DELIVERED"),
                     ("nl", "SENT")]:
        assert expected in steps

    case_id = inbox[0]["case_id"]
    compared = net.ui().post(f"/api/de/inbox/{case_id}/cohort-query", json={}).json()
    result = compared["cohort"]["results"][0]
    assert result["site"] == "de" and result["records_queried_locally"] == 38
    assert result["records_transferred"] == 0

    sent = net.ui().post(f"/api/de/inbox/{case_id}/opinion",
                         json={"opinion": "Consider a KRAS G12C inhibitor combination."})
    assert sent.status_code == 200, sent.text
    reviews = net.ui().get("/api/nl/peer-reviews").json()
    assert reviews[0]["status"] == "opinion_received"
    assert reviews[0]["opinion"]["cohort"]["results"][0]["records_queried_locally"] == 38
    assert ("nl", "RECEIVED") in _steps(net, correlation_id)

    progress = net.ui().get("/api/federation/progress").json()
    assert progress["case_sent"] and progress["cohort_compared"] and progress["opinion_returned"]


def test_no_identifiers_or_rows_cross_any_service_boundary(net: Network) -> None:
    send_case(net, ["diagnosis", "treatment_history", "pathology", "molecular",
                    "relevant_imaging", "labs", "performance_status", "comorbidities"])
    case_id = net.ui().get("/api/de/inbox").json()[0]["case_id"]
    net.ui().post(f"/api/de/inbox/{case_id}/cohort-query", json={})
    net.ui().post("/api/research/cohort-queries", json={})
    net.captured.clear()
    net.ui().post(f"/api/de/inbox/{case_id}/cohort-query", json={})
    net.ui().post(f"/api/de/inbox/{case_id}/opinion", json={"opinion": "Synthetic opinion text."})
    send_case(net)
    hub_bound = [body for target, path, body in net.captured
                 if target == "hub" or path.startswith("/federation/")]
    assert hub_bound
    for body in hub_bound:
        text = body.decode()
        assert "person_id" not in text
        for identifier in DIRECT_IDENTIFIERS:
            assert identifier not in text


def test_package_retrieved_from_owning_site_matches_audit_digest(net: Network) -> None:
    review = send_case(net)
    package = net.ui().get(f"/api/federation/peer-reviews/{review['case_id']}/package").json()
    assert package["retrieved_from"] == "UMC Utrecht"
    assert package["matches_audit"] is True
    hub_events = [event for event in net.ui().get("/api/federation/activity").json()["events"]
                  if event["service"] == "hub" and event["step"] == "VERIFIED"]
    assert "p.G12C" not in json.dumps(hub_events, ensure_ascii=False)


def test_package_digest_still_matches_after_opinion_returns(net: Network) -> None:
    review = send_case(net)
    net.ui().post(f"/api/de/inbox/{review['case_id']}/opinion",
                  json={"opinion": "Consider a KRAS G12C inhibitor combination."})
    package = net.ui().get(f"/api/federation/peer-reviews/{review['case_id']}/package").json()
    assert package["matches_audit"] is True


def test_research_view_fans_out_to_both_engines(net: Network) -> None:
    result = net.ui().post("/api/research/cohort-queries",
                           json={"query": {"min_prior_lines": 0}}).json()
    assert {item["site"] for item in result["results"]} == {"nl", "de"}
    assert result["complete"] and result["records_transferred"] == 0
    assert [item["site"] for item in result["not_connected"]] == ["milan", "antwerp", "oxford"]


def test_disconnect_heidelberg_fails_for_real_and_recovers(net: Network) -> None:
    net.down.add("de")
    review = send_case(net)
    assert review["status"] == "delivery_failed"
    assert review["error"] == "Heidelberg unavailable — federated result incomplete"
    inbox = net.ui().get("/api/de/inbox")
    assert inbox.status_code == 503
    assert inbox.json()["detail"] == "Heidelberg unavailable — federated result incomplete"
    research = net.ui().post("/api/research/cohort-queries", json={}).json()
    assert not research["complete"] and research["unavailable"][0]["site"] == "de"
    sites = {item["site"]: item for item in net.ui().get("/api/sites").json()["sites"]}
    assert sites["de"]["reachable"] is False and sites["nl"]["reachable"] is True
    assert net.ui().get("/api/federation/progress").json()["disconnect_seen"]

    net.down.clear()
    resent = net.ui().post(f"/api/nl/peer-reviews/{review['case_id']}/resend").json()
    assert resent["status"] == "delivered"
    rerun = net.ui().post("/api/research/cohort-queries", json={}).json()
    assert rerun["complete"] and rerun["correlation_id"] != research["correlation_id"]


def test_operator_isolation_switch_cuts_heidelberg_at_its_edge(net: Network) -> None:
    switched = net.ui().post("/api/sites/de/connectivity", json={"online": False})
    assert switched.status_code == 200
    direct = TestClient(net.apps["de"]).get("/api/health")
    assert direct.status_code == 503 and "x-fed-service" not in direct.headers
    review = send_case(net)
    assert review["status"] == "delivery_failed"
    assert net.ui().get("/api/de/inbox").status_code == 503
    sites = {item["site"]: item for item in net.ui().get("/api/sites").json()["sites"]}
    assert sites["de"]["reachable"] is False and sites["de"]["isolated"] is True
    assert net.ui().get("/api/federation/progress").json()["disconnect_seen"]

    assert net.ui().post("/api/sites/de/connectivity", json={"online": True}).status_code == 200
    resent = net.ui().post(f"/api/nl/peer-reviews/{review['case_id']}/resend").json()
    assert resent["status"] == "delivered"
    steps = [e["step"] for e in net.ui().get("/api/federation/activity").json()["events"]]
    assert {"SITE_ISOLATED", "SITE_RECONNECTED", "ISOLATED", "RECONNECTED"} <= set(steps)


def test_reset_brings_isolated_sites_back_online(net: Network) -> None:
    net.ui().post("/api/sites/de/connectivity", json={"online": False})
    assert net.ui().post("/api/reset").json()["pending_reset"] == []
    sites = {item["site"]: item for item in net.ui().get("/api/sites").json()["sites"]}
    assert sites["de"]["reachable"] is True and sites["de"]["isolated"] is False


def test_isolation_switch_requires_admin_signature(net: Network) -> None:
    blocked = TestClient(net.apps["de"]).post("/admin/connectivity", json={"online": False})
    assert blocked.status_code == 401
    assert net.ui().post("/api/sites/milan/connectivity", json={"online": False}).status_code == 404


def test_reset_generations_reconcile_after_reconnect(net: Network) -> None:
    send_case(net)
    net.down.add("de")
    reset = net.ui().post("/api/reset").json()
    assert reset["pending_reset"] == ["de"]
    blocked = net.ui().post("/api/nl/peer-reviews", json={
        "patient_id": "umcu-00482913", "expert_id": "exp-heidelberg-mueller",
        "categories": ["diagnosis"], "question": "q"})
    assert blocked.status_code == 409
    net.down.clear()
    sites = net.ui().get("/api/sites").json()
    assert sites["synced"] and all(item["generation"] == reset["generation"]
                                   for item in sites["sites"])
    assert net.ui().get("/api/de/inbox").json() == []
    assert net.ui().get("/api/nl/peer-reviews").json() == []
    assert send_case(net)["status"] == "delivered"


def test_hospital_namespaces_reject_wrong_credentials(net: Network) -> None:
    from fastapi.testclient import TestClient

    from fednet.signing import sign

    de = TestClient(net.apps["de"])
    hub_keys = net.runtimes["hub"].keys
    # A workstation key cannot call the federation namespace.
    headers = sign(hub_keys["ws-de"], method="POST", path="/federation/peer-reviews",
                   body=b"{}", correlation_id="corr_x")
    response = de.post("/federation/peer-reviews", content=b"{}", headers=headers)
    assert response.status_code == 401
    assert de.get("/workstation/inbox").status_code == 401
    assert de.get("/api/health").json()["environment"].startswith("HEIDELBERG")


def test_hub_bff_is_not_a_transparent_proxy(net: Network) -> None:
    assert net.ui().get("/api/nl/workstation/patients").status_code == 404
    assert net.ui().get("/api/de/admin/audit").status_code == 404


def test_blocked_categories_are_refused_before_leaving_nl(net: Network) -> None:
    response = net.ui().post("/api/nl/peer-reviews", json={
        "patient_id": "umcu-00482913", "expert_id": "exp-heidelberg-mueller",
        "categories": ["diagnosis", "identifiers"], "question": "q"})
    assert response.status_code == 422
    assert net.ui().get("/api/de/inbox").json() == []


def test_access_code_gate() -> None:
    network = build_network(access_code="letmein")
    assert network.ui().get("/api/nl/patients").status_code == 401
    assert network.ui().get("/api/health").status_code == 200
    assert network.ui().post("/api/demo-access", json={"code": "wrong"}).status_code == 401
    assert network.ui().post("/api/demo-access", json={"code": "letmein"}).status_code == 204
    assert network.ui().get("/api/nl/patients").status_code == 200
