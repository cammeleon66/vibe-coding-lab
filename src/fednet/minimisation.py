"""Source-side minimisation: build a new bundle from allowlisted fields.

This is allowlist-based minimisation and direct-identifier removal, not
anonymisation. The original record is never filtered in place or forwarded.
"""

from __future__ import annotations

import secrets
from datetime import date
from typing import Any

from fednet.data import DIAGNOSIS_DATE, SHARING_CATEGORIES

SHAREABLE = {item["id"] for item in SHARING_CATEGORIES if item["shareable"]}
NEVER_SHARED = {item["id"] for item in SHARING_CATEGORIES if not item["shareable"]}

# Only these fields are ever copied, per resource type.
FIELD_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "Condition": ("code", "stage", "bodySite", "clinicalStatus"),
    "MedicationStatement": ("medication", "line", "cycles", "outcome"),
    "DiagnosticReport": ("code", "conclusion"),
    "Observation": ("code", "value", "method"),
    "ImagingStudy": ("modality", "description", "numberOfSeries", "conclusion"),
    "Procedure": ("code", "outcome"),
}


class MinimisationError(ValueError):
    pass


def new_case_pseudonym() -> str:
    return "case-" + secrets.token_hex(4)


def _months_since_diagnosis(value: str) -> int:
    moment = date.fromisoformat(value)
    return (moment.year - DIAGNOSIS_DATE.year) * 12 + moment.month - DIAGNOSIS_DATE.month


def _age_band(birth_date: str, today: date) -> str:
    born = date.fromisoformat(birth_date)
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    low = age // 5 * 5
    return f"{low}-{low + 4}"


def build_package(
    record: list[dict[str, Any]],
    categories: list[str],
    *,
    pseudonym: str,
    today: date,
) -> dict[str, Any]:
    """Pure: returns a FHIR-shaped collection bundle plus a minimisation report."""
    selected = set(categories)
    blocked = selected & NEVER_SHARED
    if blocked:
        raise MinimisationError(
            "Not shareable for peer review: " + ", ".join(sorted(blocked))
        )
    unknown = selected - SHAREABLE
    if unknown:
        raise MinimisationError("Unknown categories: " + ", ".join(sorted(unknown)))
    patient = next(item for item in record if item["resourceType"] == "Patient")
    entries: list[dict[str, Any]] = []
    for resource in record:
        category = resource["meta"]["category"]
        if category not in selected:
            continue
        allowed = FIELD_ALLOWLIST.get(resource["resourceType"])
        if allowed is None:
            continue
        built: dict[str, Any] = {
            "resourceType": resource["resourceType"],
            "id": f"{pseudonym}-{len(entries) + 1}",
            "category": category,
            "title": resource["meta"]["title"],
            "subject": {"reference": f"Patient/{pseudonym}"},
            "monthsSinceDiagnosis": _months_since_diagnosis(resource["effectiveDate"]),
        }
        for field in allowed:
            if field in resource:
                built[field] = resource[field]
        entries.append(built)
    removed = [
        "name", "identifier (MRN, national ID)", "birth date (age band kept)", "address",
        "contacts", "narrative text", "contained resources", "attachment URLs",
        "DICOM patient tags", "absolute dates (months since diagnosis kept)",
    ]
    return {
        "bundle": {
            "resourceType": "Bundle",
            "type": "collection",
            "meta": {"profile": "peer-review-minimised", "synthetic": True},
            "subject": {
                "pseudonym": pseudonym,
                "ageBand": _age_band(patient["birthDate"], today),
                "sex": patient["gender"],
            },
            "entry": entries,
        },
        "report": {
            "source_resources": len(record),
            "shared_resources": len(entries),
            "categories": sorted(selected),
            "identifiers_removed": removed,
            "method": "allowlist minimisation and direct-identifier removal (not anonymisation)",
        },
    }


def manifest(bundle: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in bundle.get("entry", []):
        counts[entry["resourceType"]] = counts.get(entry["resourceType"], 0) + 1
    return counts
