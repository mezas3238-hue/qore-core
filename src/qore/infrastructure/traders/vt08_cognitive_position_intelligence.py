"""Position Intelligence for VT08 Forex Cognitive V1.

The layer can reason about HOLD / PROTECT / REDUCE / EXIT in research/shadow.
It never submits an order, changes quantity, or grants capital authority.

No contextual trailing/reduction threshold is silently copied from another
Trader. Structural protection and reduction remain disabled in the default
policy until VT08-specific replay/validation calibrates them.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_journey_intelligence import (
    Vt08JourneyAssessment,
    Vt08JourneyState,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08PositionAction,
)

SCHEMA: Final = "qore.vt08.forex.cognitive.position_intelligence.v1"


@dataclass(frozen=True, slots=True)
class Vt08PositionPolicy:
    """VT08-specific management switches; no foreign thresholds are embedded."""

    allow_confirmed_structural_protection: bool
    allow_reduce_on_causal_exhaustion: bool
    exit_on_h4_lifecycle_end: bool = True
    exit_on_material_thesis_invalidation: bool = True
    exit_on_bound_destination_reached: bool = True

    @property
    def calibrated(self) -> bool:
        return bool(
            self.allow_confirmed_structural_protection
            or self.allow_reduce_on_causal_exhaustion
        )


RESEARCH_UNCALIBRATED_POSITION_POLICY: Final = Vt08PositionPolicy(
    allow_confirmed_structural_protection=False,
    allow_reduce_on_causal_exhaustion=False,
)


@dataclass(frozen=True, slots=True)
class Vt08PositionSnapshot:
    as_of: datetime
    side: str
    entry_price: Decimal
    current_price: Decimal
    initial_stop: Decimal
    current_stop: Decimal
    bound_destination: Decimal
    protection_candidate: Decimal | None = None
    protection_candidate_confirmed: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("VT08 position as_of must be timezone-aware")
        if self.side not in {"long", "short"}:
            raise ValueError("VT08 position side must be long or short")
        for name in (
            "entry_price",
            "current_price",
            "initial_stop",
            "current_stop",
            "bound_destination",
        ):
            value = getattr(self, name)
            if not value.is_finite() or value <= 0:
                raise ValueError(f"VT08 position {name} must be positive finite")
        if self.protection_candidate is not None and (
            not self.protection_candidate.is_finite()
            or self.protection_candidate <= 0
        ):
            raise ValueError("VT08 protection candidate must be positive finite")
        if self.side == "long":
            if not self.current_stop <= self.entry_price < self.bound_destination:
                raise ValueError("VT08 long position geometry invalid")
            if self.initial_stop > self.current_stop:
                raise ValueError("VT08 long current stop widened beyond initial stop")
        else:
            if not self.bound_destination < self.entry_price <= self.current_stop:
                raise ValueError("VT08 short position geometry invalid")
            if self.initial_stop < self.current_stop:
                raise ValueError("VT08 short current stop widened beyond initial stop")


@dataclass(frozen=True, slots=True)
class Vt08PositionDecision:
    action: Vt08PositionAction
    next_stop: Decimal | None
    reason_codes: tuple[str, ...]
    policy_calibrated: bool
    journey_fingerprint: str
    execution_authorized: bool = False
    quantity_change_authorized: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.execution_authorized
            or self.quantity_change_authorized
            or self.capital_authority
        ):
            raise ValueError("VT08 Position Intelligence is research/shadow only")

    def fingerprint(self) -> str:
        payload = {
            "schema": SCHEMA,
            "action": self.action.value,
            "next_stop": (
                None if self.next_stop is None else format(self.next_stop, "f")
            ),
            "reason_codes": self.reason_codes,
            "policy_calibrated": self.policy_calibrated,
            "journey_fingerprint": self.journey_fingerprint,
            "execution_authorized": self.execution_authorized,
            "quantity_change_authorized": self.quantity_change_authorized,
            "capital_authority": self.capital_authority,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def improves_stop(
    *,
    side: str,
    current_stop: Decimal,
    current_price: Decimal,
    candidate_stop: Decimal,
) -> bool:
    """Return True only for a monotonic, executable-side stop improvement."""
    if side == "long":
        return current_stop < candidate_stop < current_price
    if side == "short":
        return current_price < candidate_stop < current_stop
    raise ValueError("VT08 side must be long or short")


def decide_position(
    *,
    position: Vt08PositionSnapshot,
    journey: Vt08JourneyAssessment,
    policy: Vt08PositionPolicy = RESEARCH_UNCALIBRATED_POSITION_POLICY,
) -> Vt08PositionDecision:
    reasons: list[str] = []

    if (
        journey.journey_state is Vt08JourneyState.INVALIDATED
        and policy.exit_on_material_thesis_invalidation
    ):
        reasons.append("POSITION:EXIT_CAUSAL_THESIS_INVALIDATED")
        return Vt08PositionDecision(
            action=Vt08PositionAction.EXIT,
            next_stop=None,
            reason_codes=tuple(reasons),
            policy_calibrated=policy.calibrated,
            journey_fingerprint=journey.fingerprint(),
        )

    if (
        journey.journey_state is Vt08JourneyState.DESTINATION_REACHED
        and policy.exit_on_bound_destination_reached
    ):
        reasons.append("POSITION:EXIT_BOUND_DESTINATION_REACHED")
        return Vt08PositionDecision(
            action=Vt08PositionAction.EXIT,
            next_stop=None,
            reason_codes=tuple(reasons),
            policy_calibrated=policy.calibrated,
            journey_fingerprint=journey.fingerprint(),
        )

    if journey.journey_state is Vt08JourneyState.EXHAUSTION_RISK:
        if policy.allow_reduce_on_causal_exhaustion:
            reasons.append("POSITION:REDUCE_CAUSAL_EXHAUSTION")
            return Vt08PositionDecision(
                action=Vt08PositionAction.REDUCE,
                next_stop=None,
                reason_codes=tuple(reasons),
                policy_calibrated=True,
                journey_fingerprint=journey.fingerprint(),
            )
        reasons.append("POSITION:HOLD_REDUCTION_NOT_VT08_CALIBRATED")

    candidate = position.protection_candidate
    if (
        candidate is not None
        and position.protection_candidate_confirmed
        and improves_stop(
            side=position.side,
            current_stop=position.current_stop,
            current_price=position.current_price,
            candidate_stop=candidate,
        )
    ):
        if policy.allow_confirmed_structural_protection:
            reasons.append("POSITION:PROTECT_CONFIRMED_STRUCTURE")
            return Vt08PositionDecision(
                action=Vt08PositionAction.PROTECT,
                next_stop=candidate,
                reason_codes=tuple(reasons),
                policy_calibrated=True,
                journey_fingerprint=journey.fingerprint(),
            )
        reasons.append("POSITION:HOLD_PROTECTION_NOT_VT08_CALIBRATED")
    elif candidate is not None and position.protection_candidate_confirmed:
        reasons.append("POSITION:HOLD_CANDIDATE_DOES_NOT_IMPROVE_STOP")

    if not reasons:
        reasons.append("POSITION:HOLD_THESIS_STILL_ACTIVE")

    return Vt08PositionDecision(
        action=Vt08PositionAction.HOLD,
        next_stop=None,
        reason_codes=tuple(dict.fromkeys(reasons)),
        policy_calibrated=policy.calibrated,
        journey_fingerprint=journey.fingerprint(),
    )
