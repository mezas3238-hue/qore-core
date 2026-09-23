"""Journey / Destination Intelligence for VT08 Forex Cognitive V1.

This layer interprets only the causal Situation Model. It does not predict a
future terminal outcome, invent target thresholds, or turn consumed PnL into a
runtime rule. Its output is research/shadow cognition with no order authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_memory import (
    cognitive_memory_fingerprint,
    market_anchor_context,
)
from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)

SCHEMA: Final = "qore.vt08.forex.cognitive.journey_destination.v1"


class Vt08JourneyState(StrEnum):
    PRE_ENTRY = "PRE_ENTRY"
    ADVANCING = "ADVANCING"
    STALLED = "STALLED"
    EXHAUSTION_RISK = "EXHAUSTION_RISK"
    DESTINATION_REACHED = "DESTINATION_REACHED"
    INVALIDATED = "INVALIDATED"
    UNKNOWN = "UNKNOWN"


class Vt08DestinationState(StrEnum):
    SUPPORTED = "SUPPORTED"
    APPROACHING = "APPROACHING"
    REACHED = "REACHED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Vt08JourneyAssessment:
    journey_state: Vt08JourneyState
    destination_state: Vt08DestinationState
    reason_codes: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    situation_fingerprint: str
    cognitive_memory_fingerprint: str
    market_anchor_context_fingerprint: str
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if self.execution_authorized:
            raise ValueError("VT08 Journey Intelligence has no execution authority")

    def fingerprint(self) -> str:
        payload = {
            "schema": SCHEMA,
            "journey_state": self.journey_state.value,
            "destination_state": self.destination_state.value,
            "reason_codes": self.reason_codes,
            "supporting_evidence": self.supporting_evidence,
            "contradictions": self.contradictions,
            "uncertainty": self.uncertainty,
            "situation_fingerprint": self.situation_fingerprint,
            "cognitive_memory_fingerprint": self.cognitive_memory_fingerprint,
            "market_anchor_context_fingerprint": (
                self.market_anchor_context_fingerprint
            ),
            "execution_authorized": self.execution_authorized,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _destination_state(raw: str) -> Vt08DestinationState:
    normalized = raw.upper()
    if normalized == "SUPPORTED":
        return Vt08DestinationState.SUPPORTED
    if normalized == "APPROACHING":
        return Vt08DestinationState.APPROACHING
    if normalized == "REACHED":
        return Vt08DestinationState.REACHED
    if normalized == "CONTRADICTED":
        return Vt08DestinationState.CONTRADICTED
    return Vt08DestinationState.UNKNOWN


def assess_journey(
    situation: Vt08ForexSituationModel,
) -> Vt08JourneyAssessment:
    """Classify the live journey without importing another Trader's thresholds."""
    context = market_anchor_context(
        situation.market,
        situation.anchor_hour_ny,
    )
    reasons: list[str] = []
    support = list(situation.supporting_evidence)
    contradictions = list(situation.material_contradictions)
    uncertainty = list(situation.material_uncertainties)
    destination = _destination_state(situation.structural_destination_state)

    position_is_open = situation.position_state.upper() in {
        "OPEN",
        "ACTIVE",
        "PROTECTED",
        "REDUCED",
    }

    if not position_is_open:
        state = Vt08JourneyState.PRE_ENTRY
        reasons.append("JOURNEY:POSITION_NOT_OPEN")
    elif not situation.h4_lifecycle_valid:
        state = Vt08JourneyState.INVALIDATED
        contradictions.append("JOURNEY:H4_LIFECYCLE_EXPIRED")
        reasons.append("JOURNEY:LIFECYCLE_INVALIDATED")
    elif contradictions or destination is Vt08DestinationState.CONTRADICTED:
        state = Vt08JourneyState.INVALIDATED
        reasons.append("JOURNEY:MATERIAL_THESIS_CONTRADICTION")
    elif destination is Vt08DestinationState.REACHED:
        state = Vt08JourneyState.DESTINATION_REACHED
        reasons.append("JOURNEY:STRUCTURAL_DESTINATION_REACHED")
    elif situation.exhaustion_state.upper() in {
        "CONFIRMED",
        "MATERIAL",
        "EXHAUSTION_RISK",
    }:
        state = Vt08JourneyState.EXHAUSTION_RISK
        reasons.append("JOURNEY:CAUSAL_EXHAUSTION_EVIDENCE")
    elif (
        situation.journey_stage.upper() == "STALLED"
        or situation.displacement_state.upper() in {"STALLED", "WEAKENING"}
    ):
        state = Vt08JourneyState.STALLED
        reasons.append("JOURNEY:DELIVERY_STALLED")
    elif (
        destination
        in {
            Vt08DestinationState.SUPPORTED,
            Vt08DestinationState.APPROACHING,
        }
        and situation.displacement_state.upper()
        in {"CONFIRMED", "CONTINUING", "EXPANDING"}
    ):
        state = Vt08JourneyState.ADVANCING
        reasons.append("JOURNEY:DELIVERY_ADVANCING_TOWARD_DESTINATION")
    else:
        state = Vt08JourneyState.UNKNOWN
        uncertainty.append("JOURNEY:STATE_NOT_CAUSALLY_RESOLVED")
        reasons.append("JOURNEY:UNRESOLVED")

    return Vt08JourneyAssessment(
        journey_state=state,
        destination_state=destination,
        reason_codes=tuple(dict.fromkeys(reasons)),
        supporting_evidence=tuple(dict.fromkeys(support)),
        contradictions=tuple(dict.fromkeys(contradictions)),
        uncertainty=tuple(dict.fromkeys(uncertainty)),
        situation_fingerprint=situation.fingerprint(),
        cognitive_memory_fingerprint=cognitive_memory_fingerprint(),
        market_anchor_context_fingerprint=str(context["fingerprint"]),
    )
