from __future__ import annotations

import json

from collab.models import EvidenceArrivalEvent, PreparedCase, Referral
from collab.preparation import CasePreparationService
from collab.sources import EvidenceArrivalSource


class EvidenceArrivalError(ValueError):
    pass


class EvidenceArrivalService:
    """Application seam for local delivery now and Event Grid delivery later."""

    def __init__(
        self,
        source: EvidenceArrivalSource,
        preparation: CasePreparationService,
    ) -> None:
        self._source = source
        self._preparation = preparation

    def apply(
        self,
        event: EvidenceArrivalEvent,
        referral: Referral,
        previous: PreparedCase,
    ) -> PreparedCase:
        if event.case_id != previous.case_id:
            raise EvidenceArrivalError(
                "The evidence event does not belong to the current prepared case."
            )
        try:
            evidence = self._source.read_arrival(event)
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
            raise EvidenceArrivalError(
                "Late imaging evidence could not be parsed from the source fixture."
            ) from error
        if not evidence:
            raise EvidenceArrivalError("The evidence event does not reference a supported set.")
        return self._preparation.refresh(referral, previous, evidence)
