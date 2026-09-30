"""Source-faithful deterministic observation primitives for Capitalizer V2.

These primitives encode only author mechanics that are explicit enough to operationalize
without outcome fitting. More complex observations (CISD causal-series reconstruction,
full H1/M15/M1 alignment, and Failure-to-Manipulate state) remain separate follow-up work.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class CapitalizerSourceDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class CapitalizerSourceClosureKind(StrEnum):
    CANDLE2_REVERSAL = "CANDLE2_REVERSAL"
    CANDLE3_CONFIRMATION = "CANDLE3_CONFIRMATION"


class CapitalizerProtectedSwingOrigin(StrEnum):
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceBar:
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        for value in (self.open, self.high, self.low, self.close):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError("source bar values must be finite Decimal values")
        if self.low > self.high:
            raise ValueError("source bar low cannot exceed high")
        if not self.low <= self.open <= self.high:
            raise ValueError("source bar open must lie within range")
        if not self.low <= self.close <= self.high:
            raise ValueError("source bar close must lie within range")

    @property
    def body_high(self) -> Decimal:
        return max(self.open, self.close)

    @property
    def body_low(self) -> Decimal:
        return min(self.open, self.close)


@dataclass(frozen=True, slots=True)
class CapitalizerSourceClosureObservation:
    kind: CapitalizerSourceClosureKind
    direction: CapitalizerSourceDirection
    point_of_interest_present: bool
    source_rule_satisfied: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("closure observation requires reasons")


def detect_candle2_reversal_closure(
    *,
    previous: CapitalizerSourceBar,
    candle2: CapitalizerSourceBar,
    point_of_interest_present: bool,
) -> CapitalizerSourceClosureObservation | None:
    """Detect TTrades Candle 2: sweep prior extreme, close back inside prior range, at POI."""

    bullish = candle2.low < previous.low and previous.low < candle2.close <= previous.high
    bearish = candle2.high > previous.high and previous.low <= candle2.close < previous.high

    if bullish and bearish:
        # Outside bar returning inside is directionally ambiguous for this primitive.
        return None
    if not bullish and not bearish:
        return None

    direction = (
        CapitalizerSourceDirection.BULLISH
        if bullish
        else CapitalizerSourceDirection.BEARISH
    )
    return CapitalizerSourceClosureObservation(
        kind=CapitalizerSourceClosureKind.CANDLE2_REVERSAL,
        direction=direction,
        point_of_interest_present=point_of_interest_present,
        source_rule_satisfied=point_of_interest_present,
        reasons=(
            "PREVIOUS_EXTREME_SWEPT",
            "CLOSE_BACK_INSIDE_PREVIOUS_RANGE",
            "HIGHER_TIMEFRAME_POI_PRESENT"
            if point_of_interest_present
            else "HIGHER_TIMEFRAME_POI_MISSING",
        ),
    )


def detect_candle3_confirmation(
    *,
    candle2: CapitalizerSourceBar,
    candle3: CapitalizerSourceBar,
    point_of_interest_present: bool,
    candle2_reversal_already_confirmed: bool,
) -> CapitalizerSourceClosureObservation | None:
    """Detect delayed Candle 3 confirmation only when Candle 2 failed to confirm."""

    if candle2_reversal_already_confirmed:
        return None

    bullish = (
        candle3.high <= candle2.high
        and candle3.low >= candle2.low
        and candle3.close > candle2.body_high
    )
    bearish = (
        candle3.high <= candle2.high
        and candle3.low >= candle2.low
        and candle3.close < candle2.body_low
    )

    if bullish == bearish:
        return None

    direction = (
        CapitalizerSourceDirection.BULLISH
        if bullish
        else CapitalizerSourceDirection.BEARISH
    )
    return CapitalizerSourceClosureObservation(
        kind=CapitalizerSourceClosureKind.CANDLE3_CONFIRMATION,
        direction=direction,
        point_of_interest_present=point_of_interest_present,
        source_rule_satisfied=point_of_interest_present,
        reasons=(
            "CANDLE2_REVERSAL_NOT_CONFIRMED",
            "CANDLE3_CLOSED_THROUGH_CANDLE2_BODY",
            "CANDLE3_DID_NOT_SWEEP_CANDLE2_RANGE",
            "HIGHER_TIMEFRAME_POI_PRESENT"
            if point_of_interest_present
            else "HIGHER_TIMEFRAME_POI_MISSING",
        ),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerProtectedSwingObservation:
    direction: CapitalizerSourceDirection
    swing_price: Decimal
    origin: CapitalizerProtectedSwingOrigin
    closure_through_causal_series_confirmed: bool
    confirmed: bool
    reasons: tuple[str, ...]


def confirm_protected_swing(
    *,
    direction: CapitalizerSourceDirection,
    swing_price: Decimal,
    origin: CapitalizerProtectedSwingOrigin,
    closure_through_causal_series_confirmed: bool,
) -> CapitalizerProtectedSwingObservation:
    if not isinstance(swing_price, Decimal) or not swing_price.is_finite():
        raise ValueError("protected swing price must be finite Decimal")
    return CapitalizerProtectedSwingObservation(
        direction=direction,
        swing_price=swing_price,
        origin=origin,
        closure_through_causal_series_confirmed=closure_through_causal_series_confirmed,
        confirmed=closure_through_causal_series_confirmed,
        reasons=(
            f"ORIGIN:{origin.value}",
            (
                "CAUSAL_SERIES_CLOSURE_CONFIRMED"
                if closure_through_causal_series_confirmed
                else "CAUSAL_SERIES_CLOSURE_MISSING"
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerStructuralTargetObservation:
    direction: CapitalizerSourceDirection
    target_price: Decimal
    untouched: bool
    higher_timeframe: bool
    valid: bool
    reasons: tuple[str, ...]


def assess_structural_target(
    *,
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
    target_price: Decimal,
    untouched: bool,
    higher_timeframe: bool,
) -> CapitalizerStructuralTargetObservation:
    for value in (entry_price, target_price):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("target prices must be finite Decimal")

    directionally_valid = (
        target_price > entry_price
        if direction is CapitalizerSourceDirection.BULLISH
        else target_price < entry_price
    )
    valid = untouched and higher_timeframe and directionally_valid
    reasons: list[str] = []
    reasons.append("TARGET_UNTOUCHED" if untouched else "TARGET_ALREADY_TAKEN")
    reasons.append(
        "TARGET_HIGHER_TIMEFRAME"
        if higher_timeframe
        else "TARGET_NOT_HIGHER_TIMEFRAME"
    )
    reasons.append(
        "TARGET_DIRECTIONALLY_VALID"
        if directionally_valid
        else "TARGET_WRONG_SIDE_OF_ENTRY"
    )
    return CapitalizerStructuralTargetObservation(
        direction=direction,
        target_price=target_price,
        untouched=untouched,
        higher_timeframe=higher_timeframe,
        valid=valid,
        reasons=tuple(reasons),
    )
