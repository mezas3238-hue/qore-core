"""Read-only, as-of closed-M1 native-fact producers for VT31.

This module does not select trades or mutate positions. A producer may return
NOT_EVALUABLE; callers must never silently turn that into a healthy False.
The caller supplies frozen thesis boundaries and confirmed destinations. This
module never derives a level from realized PnL, exit outcomes or future bars.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    StructuralDestinationCandidate,
)

FactStatus = Literal["OBSERVED", "NOT_EVALUABLE"]
DestinationStatus = Literal["AVAILABLE", "NOT_APPLICABLE", "MISSING_REQUIRED"]


@dataclass(frozen=True, slots=True)
class CausalBooleanFact:
    name: str
    status: FactStatus
    value: bool | None
    observed_at: datetime | None
    source: str
    reason: str

    def __post_init__(self) -> None:
        if self.status == "OBSERVED" and (
            type(self.value) is not bool or self.observed_at is None
        ):
            raise ValueError("observed fact requires value and time")
        if self.status == "NOT_EVALUABLE" and self.value is not None:
            raise ValueError("unavailable fact must not masquerade as False")
        if self.observed_at is not None and (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise ValueError("fact timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ConfirmedDestination:
    candidate: StructuralDestinationCandidate
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("destination confirmation must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CausalDestinationFact:
    status: DestinationStatus
    candidate: StructuralDestinationCandidate | None
    observed_at: datetime | None
    source: str
    reason: str

    def __post_init__(self) -> None:
        if self.status == "AVAILABLE":
            if self.candidate is None or self.observed_at is None:
                raise ValueError("available destination requires confirmed source")
        elif self.candidate is not None:
            raise ValueError("unavailable destination cannot have a candidate")


@dataclass(frozen=True, slots=True)
class MarketNativeProducerReport:
    as_of: datetime
    structure_invalidated: CausalBooleanFact
    liquidity_failure_confirmed: CausalBooleanFact
    regime_changed_against_thesis: CausalBooleanFact
    next_structural_target: CausalDestinationFact

    @property
    def not_evaluable_facts(self) -> tuple[str, ...]:
        return tuple(
            fact.name
            for fact in (
                self.structure_invalidated,
                self.liquidity_failure_confirmed,
                self.regime_changed_against_thesis,
            )
            if fact.status == "NOT_EVALUABLE"
        )


def _boundary_fact(
    *,
    name: str,
    closed: tuple[OhlcSnapshot, ...],
    side: str,
    boundary: Decimal | None,
    source: str,
    eligible: bool | None = True,
) -> CausalBooleanFact:
    if eligible is not True or boundary is None or not closed:
        why = (
            "FROZEN_THESIS_PREREQUISITE_NOT_PROVEN"
            if eligible is not True
            else "FROZEN_BOUNDARY_MISSING"
            if boundary is None
            else "NO_CLOSED_M1"
        )
        return CausalBooleanFact(name, "NOT_EVALUABLE", None, None, source, why)
    if not boundary.is_finite() or boundary <= 0:
        raise ValueError("frozen native boundary must be positive finite")

    for bar in closed:
        close = Decimal(str(bar.close))
        adverse = close < boundary if side == "long" else close > boundary
        if adverse:
            return CausalBooleanFact(
                name, "OBSERVED", True, bar.closed_at, source,
                "CLOSED_M1_ADVERSE_BOUNDARY_BREACH",
            )
    return CausalBooleanFact(
        name, "OBSERVED", False, closed[-1].closed_at, source,
        "NO_ADVERSE_BREACH_IN_CLOSED_PATH",
    )


def _regime_fact(
    *,
    entry_regime: str | None,
    current_regime: str | None,
    regime_observed_at: datetime | None,
    as_of: datetime,
    side: str,
) -> CausalBooleanFact:
    source = "frozen-entry-regime-versus-causal-current-regime"
    opposite = "bearish" if side == "long" else "bullish"
    valid_states = frozenset({"bullish", "bearish", "mixed", "flat"})
    if (
        entry_regime not in valid_states
        or current_regime not in valid_states
        or regime_observed_at is None
    ):
        return CausalBooleanFact(
            "regime_changed_against_thesis", "NOT_EVALUABLE", None,
            None, source, "ENTRY_OR_CAUSAL_CURRENT_REGIME_UNAVAILABLE",
        )
    if regime_observed_at.tzinfo is None or regime_observed_at.utcoffset() is None:
        raise ValueError("regime observation must be timezone-aware")
    if regime_observed_at > as_of:
        raise ValueError("future regime observation forbidden")
    # MIXED/FLAT is a real, observed frozen regime, not a missing input.
    # A new adverse regime exists only when the entry regime was NOT
    # already adverse for the thesis and the current closed-H1 regime is.
    # This is a state transition, not a prediction or terminal-loss label.
    changed = entry_regime != opposite and current_regime == opposite
    return CausalBooleanFact(
        "regime_changed_against_thesis", "OBSERVED", changed,
        regime_observed_at, source,
        "CONFIRMED_OPPOSITE_REGIME" if changed else "NO_OPPOSITE_REGIME",
    )


def _destination_fact(
    *,
    side: str,
    as_of: datetime,
    primary_target: Decimal,
    primary_reached: bool,
    primary_accepted: bool,
    candidates: Sequence[ConfirmedDestination],
) -> CausalDestinationFact:
    if not primary_reached:
        return CausalDestinationFact(
            "NOT_APPLICABLE", None, None, "primary-target-lifecycle",
            "PRIMARY_TARGET_NOT_REACHED",
        )
    if not primary_accepted:
        return CausalDestinationFact(
            "NOT_APPLICABLE", None, None, "primary-target-lifecycle",
            "PRIMARY_TARGET_NOT_ACCEPTED",
        )
    eligible = [
        item for item in candidates
        if item.observed_at <= as_of
        and (
            item.candidate.level > primary_target
            if side == "long"
            else item.candidate.level < primary_target
        )
    ]
    if not eligible:
        return CausalDestinationFact(
            "MISSING_REQUIRED", None, None, "confirmed-structural-destinations",
            "NO_CAUSAL_CONFIRMED_DESTINATION_BEYOND_PRIMARY",
        )
    selected = min(
        eligible,
        key=lambda item: (
            abs(item.candidate.level - primary_target),
            item.observed_at,
            item.candidate.source,
        ),
    )
    return CausalDestinationFact(
        "AVAILABLE", selected.candidate, selected.observed_at,
        selected.candidate.source, "CLOSEST_CONFIRMED_BEYOND_PRIMARY",
    )


def produce_market_native_facts(
    *,
    bars_since_fill: Sequence[OhlcSnapshot],
    as_of: datetime,
    side: str,
    structural_invalidation_level: Decimal | None,
    liquidity_failure_boundary: Decimal | None,
    reference_reclaim_confirmed_at_entry: bool | None,
    entry_regime: str | None,
    current_regime: str | None,
    regime_observed_at: datetime | None,
    primary_target: Decimal,
    primary_target_reached: bool,
    primary_target_accepted: bool,
    confirmed_next_destinations: Sequence[ConfirmedDestination] = (),
) -> MarketNativeProducerReport:
    """Produce observable facts, preserving NA when thesis evidence is absent.

    Only closed M1 bars with close <= as_of are examined, even if the input
    stream contains later market events. This is intentionally session-neutral.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if side not in {"long", "short"}:
        raise ValueError("side must be long or short")
    if not primary_target.is_finite() or primary_target <= 0:
        raise ValueError("primary structural target must be positive finite")
    closed = tuple(sorted(
        (
            bar for bar in bars_since_fill
            if bar.timeframe.seconds == 60 and bar.closed_at <= as_of
        ),
        key=lambda bar: bar.closed_at,
    ))
    if closed and any(bar.instrument.symbol != "NAS100" for bar in closed):
        raise ValueError("VT31 fact producer requires NAS100 evidence")
    if closed and len({bar.closed_at for bar in closed}) != len(closed):
        raise ValueError("duplicate causal M1 close timestamp")
    return MarketNativeProducerReport(
        as_of=as_of,
        structure_invalidated=_boundary_fact(
            name="structure_invalidated", closed=closed, side=side,
            boundary=structural_invalidation_level,
            source="frozen-structure-level-closed-m1",
        ),
        liquidity_failure_confirmed=_boundary_fact(
            name="liquidity_failure_confirmed", closed=closed, side=side,
            boundary=liquidity_failure_boundary,
            eligible=reference_reclaim_confirmed_at_entry,
            source="frozen-liquidity-reclaim-boundary-closed-m1",
        ),
        regime_changed_against_thesis=_regime_fact(
            entry_regime=entry_regime, current_regime=current_regime,
            regime_observed_at=regime_observed_at, as_of=as_of, side=side,
        ),
        next_structural_target=_destination_fact(
            side=side, as_of=as_of, primary_target=primary_target,
            primary_reached=primary_target_reached,
            primary_accepted=primary_target_accepted,
            candidates=confirmed_next_destinations,
        ),
    )
