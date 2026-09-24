"""Hub policy decision point (pure). Rules are code, not a policy product."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from fednet.minimisation import NEVER_SHARED, SHAREABLE

CONNECTED_SITES = {"nl", "de"}
Purpose = Literal["peer_review", "peer_review_opinion", "cohort_aggregate"]


@dataclass(frozen=True)
class PolicyRequest:
    purpose: Purpose
    source: str
    destination: str
    categories: tuple[str, ...] = ()
    resource_count: int = 0
    row_level: bool = False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def evaluate(request: PolicyRequest) -> Decision:
    reasons: list[str] = []
    allowed = True
    if request.destination not in CONNECTED_SITES:
        return Decision(False, [f"{request.destination} is not connected to the federation"])
    hub_initiated = request.source == "hub" and request.purpose == "cohort_aggregate"
    if request.source not in CONNECTED_SITES and not hub_initiated:
        return Decision(False, [f"{request.source} is not a federation member"])
    reasons.append(f"members: {request.source} → {request.destination}")
    if request.source != request.destination:
        reasons.append("cross-border transfer: purpose-limited, minimised payload required")
    if request.purpose == "peer_review":
        if not request.categories:
            allowed = False
            reasons.append("no approved categories")
        blocked = set(request.categories) & NEVER_SHARED
        if blocked:
            allowed = False
            reasons.append("category not permitted for peer review: " + ", ".join(sorted(blocked)))
        unknown = set(request.categories) - SHAREABLE - NEVER_SHARED
        if unknown:
            allowed = False
            reasons.append("unknown category: " + ", ".join(sorted(unknown)))
        if allowed:
            reasons.append("purpose peer review: categories within approved set")
    elif request.purpose == "peer_review_opinion":
        reasons.append("purpose: returning opinion on an existing peer-review case")
    elif request.purpose == "cohort_aggregate":
        if request.row_level:
            allowed = False
            reasons.append("row-level results are never permitted")
        else:
            reasons.append("aggregate-only query; small cells suppressed at source (k=5)")
    return Decision(allowed, reasons)
