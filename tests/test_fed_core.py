from __future__ import annotations

import json
from datetime import date

import pytest

from fednet.audit import MASK, AuditLog, redact
from fednet.cohort import CohortQuery, run_query
from fednet.data import DIRECT_IDENTIFIERS, heidelberg_cohort, maria_record, utrecht_cohort
from fednet.minimisation import MinimisationError, build_package
from fednet.policy import PolicyRequest, evaluate
from fednet.signing import NonceStore, SignatureError, load_keys, sign, verify
from fednet.storage import FileDocumentStore, MemoryDocumentStore

DEFAULT = ["diagnosis", "treatment_history", "pathology", "molecular", "relevant_imaging"]


def _verify(headers: dict[str, str], body: bytes, **overrides: object) -> None:
    keys = load_keys("de", allow_dev_keys=True)
    arguments: dict[str, object] = {
        "keys": [keys["hub-de"]], "audience": "de", "method": "POST",
        "path": "/federation/peer-reviews", "query": "", "headers": headers, "body": body,
        "nonces": NonceStore(MemoryDocumentStore()),
    }
    arguments.update(overrides)
    verify(**arguments)  # type: ignore[arg-type]


def test_record_has_27_resources_and_default_package_has_9() -> None:
    package = build_package(maria_record(), DEFAULT, pseudonym="case-x", today=date(2026, 9, 24))
    assert package["report"]["source_resources"] == 27
    assert package["report"]["shared_resources"] == 9
    assert package["bundle"]["subject"] == {"pseudonym": "case-x", "ageBand": "55-59",
                                            "sex": "female"}


def test_package_never_contains_direct_identifiers_even_with_all_optional_categories() -> None:
    categories = [*DEFAULT, "labs", "performance_status", "comorbidities"]
    text = json.dumps(build_package(maria_record(), categories, pseudonym="case-y",
                                    today=date(2026, 9, 24))["bundle"], ensure_ascii=False)
    for identifier in DIRECT_IDENTIFIERS:
        assert identifier not in text
    for forbidden in ("presentedForm", "contained", "dicomTags", '"text"', "effectiveDate",
                      "2024-", "2026-"):
        assert forbidden not in text


@pytest.mark.parametrize("category", ["identifiers", "full_ehr", "made_up"])
def test_unshareable_categories_are_refused(category: str) -> None:
    with pytest.raises(MinimisationError):
        build_package(maria_record(), [*DEFAULT, category], pseudonym="c", today=date.today())


def test_unchecked_categories_stay_home() -> None:
    bundle = build_package(maria_record(), ["diagnosis"], pseudonym="c",
                           today=date.today())["bundle"]
    assert {entry["category"] for entry in bundle["entry"]} == {"diagnosis"}


def test_heidelberg_cohort_is_computed_with_small_cell_suppression() -> None:
    aggregate = run_query(heidelberg_cohort(), CohortQuery())
    assert aggregate.records_scanned == 200
    assert aggregate.records_queried_locally == 38
    assert aggregate.records_transferred == 0
    arms = {arm.arm: arm for arm in aggregate.arms}
    assert arms["A"].n == 17 and arms["A"].response_rate == 0.41
    assert arms["B"].n == 18
    assert arms["C"].suppressed and arms["C"].n is None and arms["C"].n_display == "<5"
    assert aggregate.suppressed_cells == 1
    assert "person_id" not in aggregate.model_dump_json()


def test_utrecht_cohort_and_query_parameters_change_results() -> None:
    assert run_query(utrecht_cohort(), CohortQuery()).records_queried_locally == 13
    broader = run_query(heidelberg_cohort(), CohortQuery(min_prior_lines=0))
    assert broader.records_queried_locally > 38


def test_policy_rules() -> None:
    assert evaluate(PolicyRequest("peer_review", "nl", "de", tuple(DEFAULT))).allowed
    assert not evaluate(PolicyRequest("peer_review", "nl", "de", ("identifiers",))).allowed
    assert not evaluate(PolicyRequest("peer_review", "nl", "milan", tuple(DEFAULT))).allowed
    assert not evaluate(PolicyRequest("cohort_aggregate", "de", "de", row_level=True)).allowed
    assert evaluate(PolicyRequest("cohort_aggregate", "hub", "nl")).allowed
    assert not evaluate(PolicyRequest("peer_review", "hub", "nl", tuple(DEFAULT))).allowed


def test_signature_roundtrip_and_rejections() -> None:
    hub_keys = load_keys("hub", allow_dev_keys=True)
    body = b'{"a":1}'
    headers = sign(hub_keys["hub-de"], method="POST", path="/federation/peer-reviews",
                   body=body, correlation_id="corr_1")
    _verify(dict(headers), body)
    with pytest.raises(SignatureError, match="mismatch"):
        _verify(dict(headers), b'{"a":2}')
    with pytest.raises(SignatureError, match="mismatch"):
        _verify(dict(headers), body, path="/federation/cohort")
    with pytest.raises(SignatureError, match="window"):
        _verify(dict(headers), body, now=float(headers["x-fed-timestamp"]) + 301)


def test_signature_is_directional() -> None:
    de_keys = load_keys("de", allow_dev_keys=True)
    # Heidelberg's own outgoing key cannot produce a message that Heidelberg accepts.
    headers = sign(de_keys["de-hub"], method="POST", path="/federation/peer-reviews",
                   correlation_id="corr_1")
    with pytest.raises(SignatureError):
        _verify(dict(headers), b"")
    ws = sign(load_keys("hub", allow_dev_keys=True)["ws-de"], method="POST",
              path="/federation/peer-reviews", correlation_id="corr_1")
    with pytest.raises(SignatureError, match="Unknown or unacceptable key"):
        _verify(dict(ws), b"")


def test_replay_is_rejected_after_restart(tmp_path: object) -> None:
    from pathlib import Path

    root = Path(str(tmp_path))
    hub_keys = load_keys("hub", allow_dev_keys=True)
    headers = sign(hub_keys["hub-de"], method="POST", path="/federation/peer-reviews",
                   correlation_id="corr_1")
    _verify(dict(headers), b"", nonces=NonceStore(FileDocumentStore(root)))
    with pytest.raises(SignatureError, match="Replayed"):
        _verify(dict(headers), b"", nonces=NonceStore(FileDocumentStore(root)))


def test_missing_keys_fail_in_azure_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FED_KEY_NL_HUB", raising=False)
    with pytest.raises(RuntimeError, match="FED_KEY_NL_HUB"):
        load_keys("nl", allow_dev_keys=False)


def test_audit_is_immutable_and_redacted() -> None:
    store = MemoryDocumentStore()
    log = AuditLog(store, "hub")
    bundle = build_package(maria_record(), DEFAULT, pseudonym="c", today=date.today())["bundle"]
    event = log.record(1, source="nl", destination="de", correlation_id="corr_1",
                       operation="peer_review", step="VERIFIED", status="ok", payload=bundle)
    assert event.body_sha256 and len(event.body_sha256) == 64
    snapshot = json.dumps(event.snapshot, ensure_ascii=False)
    assert "p.G12C" not in snapshot and "FOLFOX" not in snapshot and MASK in snapshot
    assert event.snapshot["entry"][0]["resourceType"] == "Condition"
    key = store.list("audit/")[0]
    assert not store.create(key, b"tampered")
    assert redact({"a": [1, "x"], "resourceType": "B"}) == {"a": [MASK, MASK],
                                                             "resourceType": "B"}


def test_store_rejects_path_traversal(tmp_path: object) -> None:
    from pathlib import Path

    store = FileDocumentStore(Path(str(tmp_path)))
    for key in ("../x", "/abs", "a//b", "a/./b"):
        with pytest.raises(ValueError):
            store.write(key, b"")
