"""Canonical source-candidate assembly primitives for Capitalizer V47-S0.

S0 is pre-economic. It builds deterministic, causal binders needed to transform
provider-native history into the V46 canonical historical bundle.

The first closed primitive is exact provider-tick fill resolution. Unlike the
legacy M1 touch convention, S0 never back-dates a fill to the opening timestamp
of an M1 bar whose later high/low proved the touch.

Frozen in PR #623 comment 5889541472.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as v46_adapter,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as context_binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3_source,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
    CapitalizerLiquiditySideTaken,
    assess_failure_to_manipulate,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    CapitalizerFractalAlignmentObservation,
    assess_fractal_alignment,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_V47_S0"
PREDECLARATION_COMMENT_ID = 5889541472
PRICE_SCALE = Decimal(100_000)


class S0BinderStatus(StrEnum):
    READY = "READY"
    COMPOSER_READY_REQUIRES_BINDING = "COMPOSER_READY_REQUIRES_BINDING"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class S0Binder:
    key: str
    status: S0BinderStatus
    hard_blocker: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class S0ICTSourceEvent:
    symbol: str
    session: CapitalizerSession
    operating_date: date
    side: CapitalizerSide
    source_event_at: datetime
    h1_deadline: datetime
    closeback: v3_source.SweepCloseback
    m3_mss: v3_source.M3MssEvent
    zone: v3_source.M1EntryZone
    primary_armed_level: Decimal
    fallback_armed_level: Decimal | None
    primary_entry_mode: str
    causal: bool = True
    outcome_used: bool = False
    legacy_m1_fill_used: bool = False

    def __post_init__(self) -> None:
        event_at = _aware(self.source_event_at)
        deadline = _aware(self.h1_deadline)
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("S0 source event symbol must be uppercase")
        if event_at > deadline:
            raise ValueError("S0 source event cannot arm after H1 deadline")
        if _aware(self.closeback.closeback_at) > event_at:
            raise ValueError("S0 closeback cannot occur after source event")
        if _aware(self.m3_mss.confirmed_at) > event_at:
            raise ValueError("S0 M3 MSS cannot occur after source event")
        if _aware(self.zone.fvg_confirmed_at) > event_at:
            raise ValueError("S0 M1 FVG cannot confirm after source event")
        if self.primary_armed_level <= 0:
            raise ValueError("S0 primary armed level must be positive")
        if self.fallback_armed_level is not None and self.fallback_armed_level <= 0:
            raise ValueError("S0 fallback armed level must be positive")
        if not self.zone.fvg_low <= self.primary_armed_level <= self.zone.fvg_high:
            raise ValueError("S0 primary arm escaped confirmed FVG")
        ce = (self.zone.fvg_low + self.zone.fvg_high) / Decimal("2")
        if self.fallback_armed_level is not None and self.fallback_armed_level != ce:
            raise ValueError("S0 fallback must be frozen FVG CE")
        if self.outcome_used or self.legacy_m1_fill_used or not self.causal:
            raise ValueError("S0 source event governance violated")


def resolve_s0_armed_levels(
    *,
    side: CapitalizerSide,
    zone: v3_source.M1EntryZone,
) -> tuple[Decimal, Decimal | None, str]:
    """Apply A1 entry priority without looking at later fills/outcomes."""

    ce = (zone.fvg_low + zone.fvg_high) / Decimal("2")
    if zone.overlap_low is None or zone.overlap_high is None:
        return ce, None, "FVG_CE_50"
    primary = (
        zone.overlap_high
        if side is CapitalizerSide.LONG
        else zone.overlap_low
    )
    fallback = None if primary == ce else ce
    return primary, fallback, "OB_FVG_RETEST"


def bind_ict_source_events(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
) -> tuple[S0ICTSourceEvent, ...]:
    """Compose provider-native M1 into frozen V3 source events, pre-fill only.

    The legacy V3 lifecycle, fixed-2R target, buffered stop and M1 fill helper
    are deliberately not called.
    """

    ordered = tuple(sorted(bars, key=lambda row: row.opened_at))
    if ordered != bars:
        raise ValueError("S0 ICT arming requires chronological M1")
    if not ordered:
        return ()
    symbol = ordered[0].symbol
    if any(row.symbol != symbol for row in ordered):
        raise ValueError("S0 ICT arming requires one symbol")

    execution_by_day, reference_by_day = _index_day_inputs(
        ordered,
        session=session,
    )
    day_key = operating_day.isoformat()
    execution = execution_by_day.get(day_key, ())
    if len(execution) < 15:
        return ()

    previous_day = v3_source._previous_day_range(
        ordered,
        operating_day=operating_day,
    )
    h1 = _aggregate_h1(ordered)
    h1_swings = v3_source._build_h1_swings(h1)
    m5 = _aggregate_tf(ordered, minutes=5)
    m3 = _aggregate_tf(ordered, minutes=3)
    m5_closes = tuple(item.closed_at for item in m5)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)

    events: list[S0ICTSourceEvent] = []
    for h1_open, h1_deadline, hour_bars in v3_source._h1_windows(execution):
        levels = v3_source._liquidity_levels(
            prior_session=reference_by_day.get(day_key),
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            continue
        _sweep_seen, closeback = v3_source._find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if closeback is None:
            continue
        mss = v3_source._find_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            after=closeback.closeback_at,
            before=h1_deadline,
            side=closeback.side,
        )
        if mss is None:
            continue
        zone = v3_source._m1_causal_zone(execution, event=mss)
        if zone is None:
            continue
        source_event_at = max(mss.confirmed_at, zone.fvg_confirmed_at)
        primary, fallback, mode = resolve_s0_armed_levels(
            side=closeback.side,
            zone=zone,
        )
        events.append(
            S0ICTSourceEvent(
                symbol=symbol,
                session=session,
                operating_date=operating_day,
                side=closeback.side,
                source_event_at=source_event_at,
                h1_deadline=h1_deadline,
                closeback=closeback,
                m3_mss=mss,
                zone=zone,
                primary_armed_level=primary,
                fallback_armed_level=fallback,
                primary_entry_mode=mode,
            )
        )
    return tuple(
        sorted(
            events,
            key=lambda item: (
                item.source_event_at,
                item.side.value,
                item.primary_armed_level,
            ),
        )
    )


def _source_direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


@dataclass(frozen=True, slots=True)
class S0CanonicalArmedCandidate:
    event: S0ICTSourceEvent
    context: context_binders.S0SourceContextBinding
    m1: context_binders.S0M1StructureBinding
    armed_at: datetime
    causal: bool = True
    economics_read: bool = False

    def __post_init__(self) -> None:
        armed = _aware(self.armed_at)
        if armed != _aware(self.event.source_event_at):
            raise ValueError("S0 canonical candidate arm timestamp drift")
        direction = _source_direction(self.event.side)
        if self.context.direction is not direction:
            raise ValueError("S0 canonical candidate context direction drift")
        if self.m1.m1_cisd.direction is not direction:
            raise ValueError("S0 canonical candidate M1 direction drift")
        if self.m1.protected_swing.direction is not direction:
            raise ValueError("S0 canonical candidate protected swing drift")
        if self.context.m15.confirmed_at > armed or self.m1.confirmed_at > armed:
            raise ValueError("S0 canonical candidate used future confirmation")
        stop = self.m1.protected_swing.swing_price
        entry = self.event.primary_armed_level
        valid_stop = (
            stop < entry
            if self.event.side is CapitalizerSide.LONG
            else stop > entry
        )
        if not valid_stop:
            raise ValueError("S0 canonical candidate protected stop geometry invalid")
        if not self.causal or self.economics_read:
            raise ValueError("S0 canonical candidate governance violated")


def bind_canonical_armed_candidates(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
) -> tuple[S0CanonicalArmedCandidate, ...]:
    """Compose the frozen pre-fill source path without reading outcomes."""

    result: list[S0CanonicalArmedCandidate] = []
    for event in bind_ict_source_events(
        bars,
        session=session,
        operating_day=operating_day,
    ):
        direction = _source_direction(event.side)
        context = context_binders.bind_canonical_source_context(
            bars,
            direction=direction,
            entry_price=event.primary_armed_level,
            decision_at=event.source_event_at,
        )
        if context is None:
            continue
        m1 = context_binders.bind_m1_source_structure(
            bars,
            direction=direction,
            higher_timeframe_closure=context.htf.closure,
            zone=event.zone,
            after=context.m15.confirmed_at,
            before=event.source_event_at,
        )
        if m1 is None:
            continue
        try:
            candidate = S0CanonicalArmedCandidate(
                event=event,
                context=context,
                m1=m1,
                armed_at=event.source_event_at,
            )
        except ValueError:
            continue
        result.append(candidate)
    return tuple(
        sorted(
            result,
            key=lambda item: (
                item.armed_at,
                item.event.side.value,
                item.event.primary_armed_level,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class S0RouteWickBinding:
    direction: CapitalizerSourceDirection
    fractal_alignment: CapitalizerFractalAlignmentObservation
    failure_to_manipulate: CapitalizerFailureToManipulateObservation
    wick_formation: remediation.CapitalizerWickFormationObservation
    route_resolution: remediation.CapitalizerSourceRouteResolution
    causal: bool = True
    numeric_priority_used: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        if self.fractal_alignment.direction is not self.direction:
            raise ValueError("S0 fractal direction drift")
        if self.wick_formation.direction is not self.direction:
            raise ValueError("S0 wick direction drift")
        if (
            not self.causal
            or self.numeric_priority_used
            or self.outcome_used
        ):
            raise ValueError("S0 route/wick governance violated")


def resolve_s0_route_and_wick(
    *,
    direction: CapitalizerSourceDirection,
    h1_closure: CapitalizerSourceClosureObservation,
    daily_bias: CapitalizerDailyBiasObservation,
    m15_cisd: CapitalizerCISDObservation,
    m1_cisd: CapitalizerCISDObservation,
    m1_protected_swing: CapitalizerProtectedSwingObservation,
    liquidity_side_taken: CapitalizerLiquiditySideTaken,
) -> S0RouteWickBinding:
    """Compose the frozen FRACTAL/FTM/wick semantics and fail closed on ambiguity."""

    fractal = assess_fractal_alignment(
        higher_timeframe_bias=direction,
        h1_closure=h1_closure,
        m15_cisd=m15_cisd,
        m1_protected_swing=m1_protected_swing,
    )
    ftm = assess_failure_to_manipulate(
        taken_side=liquidity_side_taken,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd=m1_cisd,
        continuation_protected_swing=m1_protected_swing,
        daily_bias=daily_bias,
    )
    wick = remediation.assess_wick_formation(
        direction=direction,
        important_level_reached=m1_cisd.important_level_reached,
        intracandle_cisd=m1_cisd,
        protected_swing=m1_protected_swing,
    )
    route = remediation.resolve_source_entry_route(
        fractal_alignment=fractal,
        failure_to_manipulate=ftm,
    )
    return S0RouteWickBinding(
        direction=direction,
        fractal_alignment=fractal,
        failure_to_manipulate=ftm,
        wick_formation=wick,
        route_resolution=route,
    )


def bind_s0_route_and_wick(
    candidate: S0CanonicalArmedCandidate,
) -> S0RouteWickBinding:
    side = (
        CapitalizerLiquiditySideTaken.HIGH
        if candidate.event.closeback.reference.kind == "HIGH"
        else CapitalizerLiquiditySideTaken.LOW
    )
    return resolve_s0_route_and_wick(
        direction=candidate.context.direction,
        h1_closure=candidate.context.htf.closure,
        daily_bias=candidate.context.htf.daily_bias,
        m15_cisd=candidate.context.m15.cisd,
        m1_cisd=candidate.m1.m1_cisd,
        m1_protected_swing=candidate.m1.protected_swing,
        liquidity_side_taken=side,
    )


@dataclass(frozen=True, slots=True)
class S0RoutedCanonicalCandidate:
    candidate: S0CanonicalArmedCandidate
    route_wick: S0RouteWickBinding

    def __post_init__(self) -> None:
        if not self.route_wick.route_resolution.resolved:
            raise ValueError("S0 routed candidate requires deterministic source route")
        if not self.route_wick.wick_formation.confirmed:
            raise ValueError("S0 routed candidate requires confirmed wick formation")


def bind_routed_canonical_armed_candidates(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
) -> tuple[S0RoutedCanonicalCandidate, ...]:
    result: list[S0RoutedCanonicalCandidate] = []
    for candidate in bind_canonical_armed_candidates(
        bars,
        session=session,
        operating_day=operating_day,
    ):
        route_wick = bind_s0_route_and_wick(candidate)
        if (
            not route_wick.route_resolution.resolved
            or not route_wick.wick_formation.confirmed
        ):
            continue
        result.append(
            S0RoutedCanonicalCandidate(
                candidate=candidate,
                route_wick=route_wick,
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class DecodedProviderTick:
    observed_at: datetime
    price: Decimal


@dataclass(frozen=True, slots=True)
class ProviderFillResolution:
    side: CapitalizerSide
    quote_side: str
    armed_level: Decimal
    interval_start: datetime
    interval_end: datetime
    filled: bool
    fill_at: datetime | None
    fill_price: Decimal | None
    provider_tick_count: int
    provider_native: bool = True
    interpolation_used: bool = False
    synthetic_tick_used: bool = False
    m1_open_backdating_used: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        _aware(self.interval_start)
        _aware(self.interval_end)
        if self.interval_end < self.interval_start:
            raise ValueError("S0 fill interval cannot move backward")
        if self.quote_side not in {"ASK", "BID"}:
            raise ValueError("S0 quote side must be ASK/BID")
        expected = "ASK" if self.side is CapitalizerSide.LONG else "BID"
        if self.quote_side != expected:
            raise ValueError("S0 executable quote side mismatch")
        if self.armed_level <= 0:
            raise ValueError("S0 armed level must be positive")
        if self.provider_tick_count < 0:
            raise ValueError("S0 tick count cannot be negative")
        if self.filled != (self.fill_at is not None and self.fill_price is not None):
            raise ValueError("S0 fill payload mismatch")
        if self.fill_at is not None:
            fill_at = _aware(self.fill_at)
            if not self.interval_start <= fill_at <= self.interval_end:
                raise ValueError("S0 fill timestamp outside requested interval")
        if (
            not self.provider_native
            or self.interpolation_used
            or self.synthetic_tick_used
            or self.m1_open_backdating_used
            or self.outcome_used
        ):
            raise ValueError("S0 provider-fill governance violated")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("S0 requires timezone-aware timestamps")
    return value.astimezone(UTC)


def decode_provider_tick_interval(
    ticks: tuple[object, ...],
    *,
    interval_start: datetime,
    interval_end: datetime,
    digits: int,
    has_more: bool,
) -> tuple[DecodedProviderTick, ...]:
    """Decode complete cTrader compressed historical ticks for one interval.

    cTrader historical tick payloads are newest-first. The first row is
    absolute; subsequent rows carry timestamp/price deltas.
    """

    start = _aware(interval_start)
    end = _aware(interval_end)
    if end < start:
        raise ValueError("S0 tick interval cannot move backward")
    if has_more:
        raise ValueError("S0 exact fill requires complete tick response")
    if digits < 0:
        raise ValueError("S0 digits must be non-negative")
    if not ticks:
        return ()

    current_timestamp: int | None = None
    current_relative: int | None = None
    newest_first: list[DecodedProviderTick] = []
    quant = Decimal(1).scaleb(-digits)

    for index, raw in enumerate(ticks):
        timestamp = getattr(raw, "timestamp", None)
        relative = getattr(raw, "tick", None)
        if type(timestamp) is not int or type(relative) is not int:
            raise ValueError("S0 historical tick lacks integer fields")
        if index == 0:
            if timestamp <= 0 or relative <= 0:
                raise ValueError("S0 first historical tick must be absolute")
            current_timestamp = timestamp
            current_relative = relative
        else:
            if current_timestamp is None or current_relative is None:
                raise AssertionError("S0 internal tick decoder state missing")
            current_timestamp += timestamp
            current_relative += relative

        if current_timestamp <= 0 or current_relative <= 0:
            raise ValueError("S0 decoded tick became non-positive")
        observed_at = datetime.fromtimestamp(current_timestamp / 1000, tz=UTC)
        if not start <= observed_at <= end:
            raise ValueError("S0 decoded tick escaped requested interval")
        price = (Decimal(current_relative) / PRICE_SCALE).quantize(quant)
        newest_first.append(
            DecodedProviderTick(observed_at=observed_at, price=price)
        )

    for newer, older in zip(
        newest_first[:-1],
        newest_first[1:],
        strict=True,
    ):
        if older.observed_at > newer.observed_at:
            raise ValueError("S0 provider ticks are not newest-first")

    return tuple(reversed(newest_first))


def resolve_exact_provider_fill(
    *,
    side: CapitalizerSide,
    armed_level: Decimal,
    interval_start: datetime,
    interval_end: datetime,
    ticks: tuple[object, ...],
    digits: int,
    has_more: bool,
) -> ProviderFillResolution:
    """Resolve first executable provider quote that reaches an armed level.

    LONG uses ASK <= level.
    SHORT uses BID >= level.
    """

    if not armed_level.is_finite() or armed_level <= 0:
        raise ValueError("S0 armed level must be finite and positive")
    decoded = decode_provider_tick_interval(
        ticks,
        interval_start=interval_start,
        interval_end=interval_end,
        digits=digits,
        has_more=has_more,
    )
    match: DecodedProviderTick | None = None
    for tick in decoded:
        reached = (
            tick.price <= armed_level
            if side is CapitalizerSide.LONG
            else tick.price >= armed_level
        )
        if reached:
            match = tick
            break

    return ProviderFillResolution(
        side=side,
        quote_side="ASK" if side is CapitalizerSide.LONG else "BID",
        armed_level=armed_level,
        interval_start=_aware(interval_start),
        interval_end=_aware(interval_end),
        filled=match is not None,
        fill_at=None if match is None else match.observed_at,
        fill_price=None if match is None else match.price,
        provider_tick_count=len(decoded),
    )


def request_provider_tick_interval(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    side: CapitalizerSide,
    interval_start: datetime,
    interval_end: datetime,
    request_id: str,
) -> tuple[tuple[object, ...], bool]:
    """Read the executable quote side only; no mutation/execution API is used."""

    quote_type = 2 if side is CapitalizerSide.LONG else 1
    result = client.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": symbol_id,
            "type": quote_type,
            "fromTimestamp": int(_aware(interval_start).timestamp() * 1000),
            "toTimestamp": int(_aware(interval_end).timestamp() * 1000),
        },
        client_msg_id=request_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(
            "S0 historical tick request failed: "
            f"{type(result.error).__name__}"
        )
    if getattr(result.value, "ctidTraderAccountId", None) != client.account_id:
        raise RuntimeError("S0 historical tick response account mismatch")
    tick_data = tuple(
        cast(Iterable[object], getattr(result.value, "tickData", ()))
    )
    has_more = getattr(result.value, "hasMore", None)
    if type(has_more) is not bool:
        raise RuntimeError("S0 historical tick response missing hasMore")
    return tick_data, has_more




@dataclass(frozen=True, slots=True)
class SourceStrategyIsolationAssessment:
    canonical_result: v46_adapter.CapitalizerCanonicalHistoricalAdapterResult
    cognitive_gate_source: str = "EXOGENOUS_PASS_FOR_SOURCE_STRATEGY_ISOLATION"
    full_trader_fidelity_claimed: bool = False
    candidate_promotion_allowed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.cognitive_gate_source != (
            "EXOGENOUS_PASS_FOR_SOURCE_STRATEGY_ISOLATION"
        ):
            raise ValueError("S0 isolation cognitive source identity drift")
        if (
            self.full_trader_fidelity_claimed
            or self.candidate_promotion_allowed
            or self.trader_certified
        ):
            raise ValueError("S0 isolation cannot claim full Trader authority")


def assess_source_strategy_isolation_bundle(
    bundle: v46_adapter.CapitalizerCanonicalHistoricalBundle,
) -> SourceStrategyIsolationAssessment:
    """Run the official V46 adapter under an explicit exogenous PASS token.

    This helper never synthesizes a PASS. The caller must construct the bundle
    with PASS_TO_STRATEGY and accepts that the result is source-strategy
    isolation only, not a historical replay of the full cognitive Trader.
    """

    if (
        bundle.cognitive_gate_decision
        is not CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY
    ):
        raise ValueError(
            "S0 source-strategy isolation requires explicit exogenous PASS"
        )
    result = v46_adapter.assess_canonical_historical_bundle(bundle)
    return SourceStrategyIsolationAssessment(canonical_result=result)


def build_readiness_report() -> dict[str, object]:
    """Track S0 construction blockers without opening economics."""

    binders = (
        S0Binder(
            key="ICT_SOURCE_EVENT_ARMING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 composes provider-native M1 through the frozen V3 "
                "liquidity/sweep/M3-MSS/M1-zone primitives, applies A1 armed "
                "levels, and never calls the legacy V3 fill/lifecycle."
            ),
        ),
        S0Binder(
            key="HTF_POI_AND_CLOSURE_BINDING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 source-context composition binds the latest causal H1 "
                "Candle2/Candle3 closure to the authentic interacted source POI."
            ),
        ),
        S0Binder(
            key="DAILY_BIAS_BINDING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 derives daily bias directly from the bound causal H1 "
                "source closure; no independent historical bias assertion is used."
            ),
        ),
        S0Binder(
            key="M15_CISD_BINDING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 binds the first causal M15 opposing-series CISD after "
                "the HTF closure and before the decision timestamp."
            ),
        ),
        S0Binder(
            key="PROTECTED_SWING_BINDING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 extracts the canonical protected swing from the bound "
                "M1 CISD causal series; the M15 structural support is not used "
                "as the canonical stop."
            ),
        ),
        S0Binder(
            key="M1_MSS_FVG_OB_BINDING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 binds M1 CISD, M1 MSS, displacement-linked FVG, the "
                "source OB causal series and its M1 protected swing into the "
                "same pre-fill candidate path."
            ),
        ),
        S0Binder(
            key="STRUCTURAL_TARGET_CANDIDATE_BINDING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 composes exact H1/H4/D1 source frames into the frozen "
                "bounded target family and applies the V46 unambiguous resolver."
            ),
        ),
        S0Binder(
            key="DETERMINISTIC_ROUTE_AND_WICK_BINDING",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "V47-S0 composes source FRACTAL and FTM observations, applies "
                "the frozen exactly-one V46 route resolver, and binds wick "
                "formation from actual M1 CISD/location/protected-swing evidence."
            ),
        ),
        S0Binder(
            key="EXACT_PROVIDER_TICK_FILL",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "S0 decodes complete provider tick intervals and resolves "
                "first executable ASK/BID touch without M1-open backdating."
            ),
        ),
        S0Binder(
            key="V46_CANONICAL_BUNDLE_ASSEMBLY",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "S0 isolation wrapper calls the official V46-R2 adapter and "
                "requires an explicit exogenous PASS token; it cannot claim "
                "full-Trader fidelity or promotion authority."
            ),
        ),
    )
    blockers = tuple(row.key for row in binders if row.hard_blocker)
    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "evaluation": "PRE_ECONOMIC_CANDIDATE_ASSEMBLY_READINESS",
        "binders": [asdict(row) for row in binders],
        "blocking_binder_count": len(blockers),
        "blocking_binders": blockers,
        "canonical_source_context_binding_ready": True,
        "canonical_prefill_candidate_path_ready": True,
        "deterministic_route_and_wick_binding_ready": True,
        "no_chase_execution_area_bound": True,
        "exact_provider_tick_fill_ready": True,
        "legacy_m1_open_backdating_allowed": False,
        "v41_30s_threshold_reused": False,
        "v41_features_used": False,
        "exogenous_cognitive_pass_isolation_only": True,
        "strategy_economics_calculated": False,
        "exit_simulation_run": False,
        "realized_r_read": False,
        "fresh_holdout_opened": False,
        "candidate_count": 0,
        "trader_certified": False,
        "next_phase": (
            "CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_READY_FOR_ISOLATION_REPLAY"
            if not blockers
            else "CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_GAPS_REMAIN"
        ),
    }


def write_report(report: dict[str, object], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-canonical-source-candidate-assembly-v47-s0.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build_readiness_report()
    write_report(report, Path("audit-output"))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
