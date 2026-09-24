"""Local cohort engine (pure). Runs inside a hospital; only aggregates leave."""

from __future__ import annotations

import hashlib
from statistics import median
from typing import Any, Literal

from pydantic import BaseModel, Field

from fednet.data import ARM_LABELS

K_ANONYMITY_THRESHOLD = 5
Outcome = Literal["response_rate", "median_pfs"]


def _all_outcomes() -> list[Outcome]:
    return ["response_rate", "median_pfs"]


class CohortQuery(BaseModel):
    """Typed query. There is no free-text SQL."""

    diagnosis: Literal["metastatic_colorectal_cancer"] = "metastatic_colorectal_cancer"
    kras_variant: Literal["G12C", "G12D", "G12V", "any"] = "G12C"
    min_prior_lines: int = Field(default=2, ge=0, le=4)
    outcomes: list[Outcome] = Field(default_factory=_all_outcomes)

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:16]


class ArmAggregate(BaseModel):
    arm: str
    label: str
    n: int | None
    n_display: str
    response_rate: float | None = None
    median_pfs_months: float | None = None
    suppressed: bool = False


class CohortAggregate(BaseModel):
    site: str
    query_digest: str
    records_scanned: int
    records_queried_locally: int
    records_transferred: int = 0
    k_threshold: int = K_ANONYMITY_THRESHOLD
    suppressed_cells: int
    arms: list[ArmAggregate]


def run_query(tables: dict[str, list[dict[str, Any]]], query: CohortQuery) -> CohortAggregate:
    site = tables["site"][0]["site"]
    diagnoses = {
        row["person_id"]
        for row in tables["condition_occurrence"]
        if row["condition_concept"] == query.diagnosis
    }
    variants = {
        row["person_id"]
        for row in tables["measurement"]
        if row["measurement_concept"] == "KRAS"
        and (query.kras_variant == "any" or row["value_as_concept"] == query.kras_variant)
    }
    prior_lines: dict[int, int] = {}
    arm_of: dict[int, str] = {}
    for row in tables["drug_era"]:
        if row["regimen"].startswith("arm_"):
            arm_of[row["person_id"]] = row["regimen"].removeprefix("arm_")
        else:
            prior_lines[row["person_id"]] = prior_lines.get(row["person_id"], 0) + 1
    matching = sorted(
        person_id
        for person_id in diagnoses & variants
        if prior_lines.get(person_id, 0) >= query.min_prior_lines
    )
    outcomes = {row["person_id"]: row for row in tables["outcome"]}
    arms: list[ArmAggregate] = []
    suppressed = 0
    for arm, label in ARM_LABELS.items():
        members = [pid for pid in matching if arm_of.get(pid) == arm and pid in outcomes]
        if not members:
            continue
        if len(members) < K_ANONYMITY_THRESHOLD:
            suppressed += 1
            arms.append(
                ArmAggregate(arm=arm, label=label, n=None, n_display=f"<{K_ANONYMITY_THRESHOLD}",
                             suppressed=True)
            )
            continue
        responders = sum(1 for pid in members if outcomes[pid]["best_response"] == "PR")
        arms.append(
            ArmAggregate(
                arm=arm,
                label=label,
                n=len(members),
                n_display=str(len(members)),
                response_rate=round(responders / len(members), 2)
                if "response_rate" in query.outcomes
                else None,
                median_pfs_months=round(median(outcomes[pid]["pfs_months"] for pid in members), 1)
                if "median_pfs" in query.outcomes
                else None,
            )
        )
    return CohortAggregate(
        site=site,
        query_digest=query.digest(),
        records_scanned=len(tables["person"]),
        records_queried_locally=len(matching),
        suppressed_cells=suppressed,
        arms=arms,
    )
