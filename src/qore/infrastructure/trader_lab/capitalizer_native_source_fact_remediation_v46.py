"""Internal canonical fact remediation for Capitalizer V46-R1.

This module closes only deterministic source/Owner-contract gaps identified by
V46 Phase A.  It contains no economic scoring, no strategy outcome access and
no parameter optimization.

Frozen in PR #623 comment 5883167207.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    CapitalizerFractalAlignmentObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    CapitalizerStructuralTargetObservation,
    assess_structural_target,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    bar_interacts_with_poi,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    CapitalizerSourceEntryRoute,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)

IDENTITY = "QORE_CAPITALIZER_NATIVE_SOURCE_FACT_REMEDIATION_V46_R1"
PREDECLARATION_COMMENT_ID = 5883167207


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("V46-R1 requires timezone-aware timestamps")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class CapitalizerHTFPOIContext:
    present: bool
    interacting_pois: tuple[CapitalizerSourcePOI, ...]
    numeric_score_used: bool = False
    outcome_aware: bool = False

    def __post_init__(self) -> None:
        if self.present != bool(self.interacting_pois):
            raise ValueError("HTF POI presence must match interacting POIs")
        if self.numeric_score_used or self.outcome_aware:
            raise ValueError("HTF POI context cannot score or use outcomes")


def resolve_htf_poi_context(
    *,
    bar: CapitalizerSourceBar,
    pois: tuple[CapitalizerSourcePOI, ...],
) -> CapitalizerHTFPOIContext:
    """Retain every source-equivalent POI touched by the completed HTF bar."""

    interacting = tuple(
        sorted(
            (
                poi
                for poi in pois
                if bar_interacts_with_poi(bar=bar, poi=poi)
            ),
            key=lambda item: (
                item.kind.value,
                item.lower_price,
                item.upper_price,
            ),
        )
    )
    return CapitalizerHTFPOIContext(
        present=bool(interacting),
        interacting_pois=interacting,
    )


@dataclass(frozen=True, slots=True)
class CapitalizerStructuralTargetCandidate:
    kind: CapitalizerSourceTargetKind
    target_price: Decimal
    observed_at: datetime
    untouched: bool
    higher_timeframe: bool

    def __post_init__(self) -> None:
        if not self.target_price.is_finite():
            raise ValueError("target candidate price must be finite")
        _aware(self.observed_at)


@dataclass(frozen=True, slots=True)
class CapitalizerStructuralTargetResolution:
    resolved: bool
    observation: CapitalizerStructuralTargetObservation | None
    target_kind: CapitalizerSourceTargetKind | None
    eligible_candidate_count: int
    reasons: tuple[str, ...]
    outcome_aware: bool = False
    numeric_priority_used: bool = False

    def __post_init__(self) -> None:
        if self.resolved != (
            self.observation is not None and self.target_kind is not None
        ):
            raise ValueError("target resolution payload mismatch")
        if not self.reasons:
            raise ValueError("target resolution requires reasons")
        if self.outcome_aware or self.numeric_priority_used:
            raise ValueError("target resolution cannot optimize or use outcomes")


def resolve_structural_target(
    *,
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
    decision_at: datetime,
    candidates: tuple[CapitalizerStructuralTargetCandidate, ...],
) -> CapitalizerStructuralTargetResolution:
    """Resolve only one unambiguous causal structural target.

    No nearest/farthest/R:R preference is permitted.  Multiple distinct valid
    targets remain unresolved for a later explicitly governed target policy.
    """

    decision = _aware(decision_at)
    eligible: list[
        tuple[CapitalizerStructuralTargetCandidate, CapitalizerStructuralTargetObservation]
    ] = []
    for candidate in candidates:
        if _aware(candidate.observed_at) > decision:
            continue
        observation = assess_structural_target(
            direction=direction,
            entry_price=entry_price,
            target_price=candidate.target_price,
            untouched=candidate.untouched,
            higher_timeframe=candidate.higher_timeframe,
        )
        if observation.valid:
            eligible.append((candidate, observation))

    unique = {
        (item.kind.value, item.target_price): (item, observation)
        for item, observation in eligible
    }
    if not unique:
        return CapitalizerStructuralTargetResolution(
            resolved=False,
            observation=None,
            target_kind=None,
            eligible_candidate_count=0,
            reasons=("NO_ELIGIBLE_STRUCTURAL_TARGET",),
        )
    prices = {price for _kind, price in unique}
    kinds = {kind for kind, _price in unique}
    if len(prices) != 1 or len(kinds) != 1:
        return CapitalizerStructuralTargetResolution(
            resolved=False,
            observation=None,
            target_kind=None,
            eligible_candidate_count=len(unique),
            reasons=("MULTIPLE_STRUCTURAL_TARGETS_REVIEW_REQUIRED",),
        )

    candidate, observation = next(iter(unique.values()))
    return CapitalizerStructuralTargetResolution(
        resolved=True,
        observation=observation,
        target_kind=candidate.kind,
        eligible_candidate_count=1,
        reasons=("UNAMBIGUOUS_CAUSAL_STRUCTURAL_TARGET",),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerNoChaseObservation:
    confirmed: bool
    entry_price: Decimal
    pd_array_lower: Decimal
    pd_array_upper: Decimal
    pd_array_confirmed_at: datetime
    entry_at: datetime
    reasons: tuple[str, ...]
    tolerance_used: bool = False
    outcome_aware: bool = False

    def __post_init__(self) -> None:
        if self.pd_array_lower > self.pd_array_upper:
            raise ValueError("PD-array lower cannot exceed upper")
        if _aware(self.pd_array_confirmed_at) > _aware(self.entry_at):
            raise ValueError("PD array cannot be confirmed after entry")
        if self.tolerance_used or self.outcome_aware:
            raise ValueError("no-chase cannot use tolerance or outcomes")


def assess_no_chase_entry(
    *,
    entry_price: Decimal,
    pd_array_lower: Decimal,
    pd_array_upper: Decimal,
    pd_array_confirmed_at: datetime,
    entry_at: datetime,
) -> CapitalizerNoChaseObservation:
    confirmed = pd_array_lower <= entry_price <= pd_array_upper
    return CapitalizerNoChaseObservation(
        confirmed=confirmed,
        entry_price=entry_price,
        pd_array_lower=pd_array_lower,
        pd_array_upper=pd_array_upper,
        pd_array_confirmed_at=pd_array_confirmed_at,
        entry_at=entry_at,
        reasons=(
            "ENTRY_REMAINS_INSIDE_CONFIRMED_PD_ARRAY"
            if confirmed
            else "ENTRY_LEFT_CONFIRMED_PD_ARRAY_CHASE"
        ,),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerWickFormationObservation:
    direction: CapitalizerSourceDirection
    important_level_reached: bool
    intracandle_cisd_confirmed: bool
    protected_swing_confirmed: bool
    confirmed: bool
    reasons: tuple[str, ...]
    numeric_wick_threshold_used: bool = False
    outcome_aware: bool = False

    def __post_init__(self) -> None:
        expected = (
            self.important_level_reached
            and self.intracandle_cisd_confirmed
            and self.protected_swing_confirmed
        )
        if self.confirmed != expected:
            raise ValueError("wick formation confirmation drift")
        if self.numeric_wick_threshold_used or self.outcome_aware:
            raise ValueError("wick formation cannot use threshold/outcome")


def assess_wick_formation(
    *,
    direction: CapitalizerSourceDirection,
    important_level_reached: bool,
    intracandle_cisd: CapitalizerCISDObservation | None,
    protected_swing: CapitalizerProtectedSwingObservation | None,
) -> CapitalizerWickFormationObservation:
    cisd_ok = (
        intracandle_cisd is not None
        and intracandle_cisd.direction is direction
        and intracandle_cisd.setup_confirmed
    )
    swing_ok = (
        protected_swing is not None
        and protected_swing.direction is direction
        and protected_swing.confirmed
    )
    confirmed = important_level_reached and cisd_ok and swing_ok
    return CapitalizerWickFormationObservation(
        direction=direction,
        important_level_reached=important_level_reached,
        intracandle_cisd_confirmed=cisd_ok,
        protected_swing_confirmed=swing_ok,
        confirmed=confirmed,
        reasons=(
            "IMPORTANT_LEVEL_REACHED"
            if important_level_reached
            else "IMPORTANT_LEVEL_NOT_REACHED",
            "INTRACANDLE_CISD_CONFIRMED"
            if cisd_ok
            else "INTRACANDLE_CISD_NOT_CONFIRMED",
            "PROTECTED_SWING_CONFIRMED"
            if swing_ok
            else "PROTECTED_SWING_NOT_CONFIRMED",
        ),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerM1MSSObservation:
    direction: CapitalizerSourceDirection
    swing_price: Decimal | None
    confirmed_at: datetime | None
    confirmed: bool
    future_bar_used: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.confirmed != (
            self.swing_price is not None and self.confirmed_at is not None
        ):
            raise ValueError("M1 MSS confirmation payload mismatch")
        if self.future_bar_used:
            raise ValueError("M1 MSS cannot use a future bar")


def _latest_structural_swing(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    before_index: int,
    direction: CapitalizerSourceDirection,
) -> Decimal | None:
    want_high = direction is CapitalizerSourceDirection.BULLISH
    latest: Decimal | None = None
    for index in range(1, before_index - 1):
        left = bars[index - 1]
        center = bars[index]
        right = bars[index + 1]
        if want_high:
            is_swing = center.high > left.high and center.high > right.high
            price = center.high
        else:
            is_swing = center.low < left.low and center.low < right.low
            price = center.low
        if is_swing:
            latest = price
    return latest


def detect_m1_mss(
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    direction: CapitalizerSourceDirection,
    after: datetime,
    before: datetime,
) -> CapitalizerM1MSSObservation:
    """Confirm first completed M1 close through latest opposite swing."""

    after_utc = _aware(after)
    before_utc = _aware(before)
    if after_utc > before_utc:
        raise ValueError("M1 MSS requires after <= before")
    ordered = tuple(sorted(bars, key=lambda row: row.closed_at))
    if ordered != bars:
        raise ValueError("M1 MSS bars must be chronological")

    for index, bar in enumerate(bars):
        if bar.closed_at <= after_utc:
            continue
        if bar.closed_at > before_utc:
            break
        swing = _latest_structural_swing(
            bars,
            before_index=index,
            direction=direction,
        )
        if swing is None:
            continue
        crossed = (
            bar.close > swing
            if direction is CapitalizerSourceDirection.BULLISH
            else bar.close < swing
        )
        if crossed:
            return CapitalizerM1MSSObservation(
                direction=direction,
                swing_price=swing,
                confirmed_at=bar.closed_at,
                confirmed=True,
                future_bar_used=False,
                reasons=("M1_CLOSE_THROUGH_LATEST_OPPOSITE_SWING",),
            )

    return CapitalizerM1MSSObservation(
        direction=direction,
        swing_price=None,
        confirmed_at=None,
        confirmed=False,
        future_bar_used=False,
        reasons=("M1_MSS_NOT_CONFIRMED",),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerM1OrderBlockObservation:
    direction: CapitalizerSourceDirection
    opposing_candle_count: int
    poi_reached: bool
    cisd_confirmed: bool
    confirmed: bool
    reasons: tuple[str, ...]
    outcome_aware: bool = False

    def __post_init__(self) -> None:
        expected = (
            self.opposing_candle_count > 0
            and self.poi_reached
            and self.cisd_confirmed
        )
        if self.confirmed != expected:
            raise ValueError("M1 order-block confirmation drift")
        if self.outcome_aware:
            raise ValueError("M1 order block cannot use outcomes")


def assess_m1_order_block(
    *,
    direction: CapitalizerSourceDirection,
    causal_series: tuple[CapitalizerSourceBar, ...],
    poi_reached: bool,
    cisd: CapitalizerCISDObservation | None,
) -> CapitalizerM1OrderBlockObservation:
    if direction is CapitalizerSourceDirection.BULLISH:
        opposing = all(bar.close < bar.open for bar in causal_series)
    else:
        opposing = all(bar.close > bar.open for bar in causal_series)
    count = len(causal_series) if causal_series and opposing else 0
    cisd_ok = (
        cisd is not None
        and cisd.direction is direction
        and cisd.structural_confirmed
    )
    confirmed = count > 0 and poi_reached and cisd_ok
    return CapitalizerM1OrderBlockObservation(
        direction=direction,
        opposing_candle_count=count,
        poi_reached=poi_reached,
        cisd_confirmed=cisd_ok,
        confirmed=confirmed,
        reasons=(
            "OPPOSING_CAUSAL_SERIES_PRESENT"
            if count > 0
            else "OPPOSING_CAUSAL_SERIES_MISSING",
            "SOURCE_POI_REACHED" if poi_reached else "SOURCE_POI_NOT_REACHED",
            "CISD_VALIDATES_ORDER_BLOCK"
            if cisd_ok
            else "CISD_ORDER_BLOCK_CONFIRMATION_MISSING",
        ),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerSourceRouteResolution:
    route: CapitalizerSourceEntryRoute | None
    resolved: bool
    reasons: tuple[str, ...]
    numeric_score_used: bool = False
    outcome_aware: bool = False

    def __post_init__(self) -> None:
        if self.resolved != (self.route is not None):
            raise ValueError("route resolution payload mismatch")
        if self.numeric_score_used or self.outcome_aware:
            raise ValueError("route resolver cannot score/use outcomes")


def resolve_source_entry_route(
    *,
    fractal_alignment: CapitalizerFractalAlignmentObservation | None,
    failure_to_manipulate: CapitalizerFailureToManipulateObservation | None,
) -> CapitalizerSourceRouteResolution:
    fractal_ok = (
        fractal_alignment is not None and fractal_alignment.confirmed
    )
    ftm_ok = (
        failure_to_manipulate is not None
        and failure_to_manipulate.confirmed
    )
    if fractal_ok == ftm_ok:
        return CapitalizerSourceRouteResolution(
            route=None,
            resolved=False,
            reasons=(
                "SOURCE_ROUTE_AMBIGUOUS_BOTH_CONFIRMED"
                if fractal_ok
                else "SOURCE_ROUTE_UNRESOLVED_NONE_CONFIRMED"
            ,),
        )
    route = (
        CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION
        if fractal_ok
        else CapitalizerSourceEntryRoute.FAILURE_TO_MANIPULATE_CONTINUATION
    )
    return CapitalizerSourceRouteResolution(
        route=route,
        resolved=True,
        reasons=(f"SOURCE_ROUTE_RESOLVED:{route.value}",),
    )
