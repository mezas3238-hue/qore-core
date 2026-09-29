"""V47-S1 source-strategy isolation population and exact-fill replay.

S1 evaluates only the source-faithful strategy conditional on the explicit
EXOGENOUS_PASS_FOR_SOURCE_STRATEGY_ISOLATION token.  S1-A constructs the
canonical population and exact provider fills without reading terminal outcomes.

Frozen in PR #623 comments 5894199332, 5894211842 and 5894267606.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as v46_adapter,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as context_binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cibo_10y_m1_clone_v1 as m1_clone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3_source,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    ReferenceLiquidity,
    TFBar,
    _aggregate_tf,
    _pivots,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_SOURCE_STRATEGY_ISOLATION_V47_S1"
PREDECLARATION_COMMENT_ID = 5894199332
SEMANTIC_AMENDMENT_A1_COMMENT_ID = 5894211842
SEMANTIC_AMENDMENT_A2_COMMENT_ID = 5894267606
COGNITIVE_TOKEN = "EXOGENOUS_PASS_FOR_SOURCE_STRATEGY_ISOLATION"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
NEW_YORK = ZoneInfo("America/New_York")
LOOKBACK = timedelta(days=21)
ONE_MILLISECOND = timedelta(milliseconds=1)

PERIODS: dict[str, tuple[datetime, datetime]] = {
    "reserved": (
        datetime(2020, 9, 17, tzinfo=UTC),
        datetime(2022, 9, 17, tzinfo=UTC),
    ),
    "validation": (
        datetime(2022, 9, 17, tzinfo=UTC),
        datetime(2024, 9, 17, tzinfo=UTC),
    ),
    "development": (
        datetime(2024, 9, 17, tzinfo=UTC),
        datetime(2026, 9, 17, tzinfo=UTC),
    ),
}


@dataclass(frozen=True, slots=True)
class S1ExactFill:
    level: Decimal
    mode: str
    resolution: s0.ProviderFillResolution
    request_count: int

    def __post_init__(self) -> None:
        if self.mode not in {"OB_FVG_RETEST", "FVG_CE_50"}:
            raise ValueError("S1 exact fill mode drift")
        if not self.resolution.filled:
            raise ValueError("S1 exact fill requires provider-confirmed fill")
        if self.request_count <= 0:
            raise ValueError("S1 exact fill requires provider request")


@dataclass(frozen=True, slots=True)
class S1AdmittedFillRow:
    identity: str
    period: str
    symbol: str
    session: str
    operating_date: str
    side: str
    route: str
    armed_at: str
    entry_at: str
    entry_price: str
    armed_level_used: str
    entry_mode: str
    stop_price: str
    target_price: str
    target_kind: str
    provider_tick_count: int
    provider_request_count: int
    cognitive_gate_source: str = COGNITIVE_TOKEN
    provider_native_m1: bool = True
    exact_provider_tick_fill: bool = True
    official_v46_adapter_passed: bool = True
    outcome_used_for_selection: bool = False
    terminal_outcome_read: bool = False
    realized_r_read: bool = False
    fresh_holdout_opened: bool = False
    full_trader_fidelity_claimed: bool = False
    candidate_promotion_allowed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S1 admitted row identity drift")
        if self.period not in PERIODS:
            raise ValueError("S1 admitted row period drift")
        if self.cognitive_gate_source != COGNITIVE_TOKEN:
            raise ValueError("S1 admitted row cognitive token drift")
        if (
            not self.provider_native_m1
            or not self.exact_provider_tick_fill
            or not self.official_v46_adapter_passed
            or self.outcome_used_for_selection
            or self.terminal_outcome_read
            or self.realized_r_read
            or self.fresh_holdout_opened
            or self.full_trader_fidelity_claimed
            or self.candidate_promotion_allowed
            or self.trader_certified
        ):
            raise ValueError("S1 admitted row governance violated")


@dataclass(frozen=True, slots=True)
class S1PeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    period_start: str
    period_end_exclusive: str
    operating_days_scanned: int
    routed_armed_candidates: int
    primary_fill_passes: int
    fallback_fill_passes: int
    no_provider_fill: int
    v46_rejected_after_fill: int
    admitted_exact_fills: int
    provider_tick_requests: int
    source_m1_run_id: int = SOURCE_M1_RUN_ID
    source_m1_sha: str = SOURCE_M1_SHA
    full_source_window_census: bool = True
    provider_native_m1: bool = True
    exact_tick_fill_required: bool = True
    outcome_used_for_selection: bool = False
    terminal_outcome_read: bool = False
    realized_r_read: bool = False
    strategy_economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    candidate_promotion_allowed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S1 market report identity drift")
        if self.period not in PERIODS:
            raise ValueError("S1 market report period drift")
        if (
            not self.full_source_window_census
            or not self.provider_native_m1
            or not self.exact_tick_fill_required
            or self.outcome_used_for_selection
            or self.terminal_outcome_read
            or self.realized_r_read
            or self.strategy_economics_calculated
            or self.fresh_holdout_opened
            or self.candidate_promotion_allowed
            or self.trader_certified
        ):
            raise ValueError("S1 market report governance violated")
        classified = (
            self.primary_fill_passes
            + self.fallback_fill_passes
            + self.no_provider_fill
        )
        if classified != self.routed_armed_candidates:
            raise ValueError("S1 fill classification count drift")
        if self.admitted_exact_fills + self.v46_rejected_after_fill > (
            self.primary_fill_passes + self.fallback_fill_passes
        ):
            raise ValueError("S1 post-fill classification count drift")


@dataclass(frozen=True, slots=True)
class _PreparedSourceSeries:
    h1: tuple[AggregatedBar, ...]
    m5: tuple[TFBar, ...]
    m3: tuple[TFBar, ...]


def _prepare_source_series(
    bars: tuple[CapitalizerM1Bar, ...],
) -> _PreparedSourceSeries:
    """Precompute immutable HTF series once per era without changing lookback."""

    return _PreparedSourceSeries(
        h1=_aggregate_h1(bars),
        m5=_aggregate_tf(bars, minutes=5),
        m3=_aggregate_tf(bars, minutes=3),
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("S1 requires timezone-aware timestamps")
    return value.astimezone(UTC)


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


def source_session_bounds(
    operating_day: date,
    *,
    session: CapitalizerSession,
) -> tuple[datetime, datetime]:
    """Return the official V46 source window, not the old research bucket."""

    if session is CapitalizerSession.LONDON:
        start = datetime.combine(operating_day, time(2, 0), tzinfo=NEW_YORK)
        end = datetime.combine(operating_day, time(5, 0), tzinfo=NEW_YORK)
        return start.astimezone(UTC), end.astimezone(UTC)
    if session is CapitalizerSession.NEW_YORK:
        start = datetime.combine(operating_day, time(7, 0), tzinfo=NEW_YORK)
        end = datetime.combine(operating_day, time(9, 0), tzinfo=NEW_YORK)
        return start.astimezone(UTC), end.astimezone(UTC)

    # ICT/V46 R3: 19:00 EST or 20:00 EDT == next UTC midnight.
    reference = datetime.combine(
        operating_day + timedelta(days=1),
        time(0, 0),
        tzinfo=UTC,
    )
    verified = v46_adapter.resolve_historical_asian_open_reference(
        reference + timedelta(minutes=1)
    )
    if verified.reference_at != reference:
        raise ValueError("S1 Asian Open source mapping drift")
    return reference, reference + timedelta(hours=2)


def prior_source_session_bounds(
    operating_day: date,
    *,
    session: CapitalizerSession,
) -> tuple[datetime, datetime]:
    if session is CapitalizerSession.ASIA:
        return source_session_bounds(
            operating_day,
            session=CapitalizerSession.NEW_YORK,
        )
    if session is CapitalizerSession.LONDON:
        return source_session_bounds(
            operating_day - timedelta(days=1),
            session=CapitalizerSession.ASIA,
        )
    return source_session_bounds(
        operating_day,
        session=CapitalizerSession.LONDON,
    )


def _bars_between(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    start: datetime,
    end: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    return tuple(
        bar
        for bar in bars
        if _aware(start) <= bar.opened_at < _aware(end)
    )


def _reference_liquidity(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    operating_day: date,
    session: CapitalizerSession,
) -> ReferenceLiquidity | None:
    start, end = prior_source_session_bounds(
        operating_day,
        session=session,
    )
    rows = _bars_between(bars, start=start, end=end)
    if len(rows) < 30:
        return None
    prior = (
        CapitalizerSession.NEW_YORK
        if session is CapitalizerSession.ASIA
        else CapitalizerSession.ASIA
        if session is CapitalizerSession.LONDON
        else CapitalizerSession.LONDON
    )
    source = f"COMPLETED_{prior.value}_SOURCE_SESSION"
    return ReferenceLiquidity(
        opened_at=rows[0].opened_at,
        closed_at=rows[-1].closed_at,
        high=max(row.high for row in rows),
        low=min(row.low for row in rows),
        source=source,
    )


def bind_source_window_ict_events(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
    prepared: _PreparedSourceSeries | None = None,
) -> tuple[s0.S0ICTSourceEvent, ...]:
    """Run the frozen S0/V3 event primitives over the complete source window."""

    ordered = tuple(sorted(bars, key=lambda row: row.opened_at))
    if ordered != bars:
        raise ValueError("S1 source-window arming requires chronological M1")
    if not ordered:
        return ()
    symbol = ordered[0].symbol
    if any(row.symbol != symbol for row in ordered):
        raise ValueError("S1 source-window arming requires one symbol")

    source_start, source_end = source_session_bounds(
        operating_day,
        session=session,
    )
    execution = _bars_between(ordered, start=source_start, end=source_end)
    if len(execution) < 15:
        return ()

    previous_day = v3_source._previous_day_range(
        ordered,
        operating_day=operating_day,
    )
    prior_session = _reference_liquidity(
        ordered,
        operating_day=operating_day,
        session=session,
    )
    if prepared is None:
        h1 = _aggregate_h1(ordered)
        m5 = _aggregate_tf(ordered, minutes=5)
        m3 = _aggregate_tf(ordered, minutes=3)
    else:
        context_start = source_start - LOOKBACK
        context_end = source_end + timedelta(hours=1)
        h1 = tuple(
            row
            for row in prepared.h1
            if row.opened_at >= context_start and row.closed_at <= context_end
        )
        m5 = tuple(
            row
            for row in prepared.m5
            if row.opened_at >= context_start and row.closed_at <= context_end
        )
        m3 = tuple(
            row
            for row in prepared.m3
            if row.opened_at >= context_start and row.closed_at <= context_end
        )
    h1_swings = v3_source._build_h1_swings(h1)
    m5_closes = tuple(item.closed_at for item in m5)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)

    events: list[s0.S0ICTSourceEvent] = []
    for h1_open, h1_deadline, hour_bars in v3_source._h1_windows(execution):
        deadline = min(h1_deadline, source_end)
        levels = v3_source._liquidity_levels(
            prior_session=prior_session,
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
            h1_deadline=deadline,
        )
        if closeback is None:
            continue
        mss = v3_source._find_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            after=closeback.closeback_at,
            before=deadline,
            side=closeback.side,
        )
        if mss is None:
            continue
        zone = v3_source._m1_causal_zone(execution, event=mss)
        if zone is None:
            continue
        source_event_at = max(mss.confirmed_at, zone.fvg_confirmed_at)
        if source_event_at >= deadline:
            continue
        primary, fallback, mode = s0.resolve_s0_armed_levels(
            side=closeback.side,
            zone=zone,
        )
        events.append(
            s0.S0ICTSourceEvent(
                symbol=symbol,
                session=session,
                operating_date=operating_day,
                side=closeback.side,
                source_event_at=source_event_at,
                h1_deadline=deadline,
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


def bind_source_window_routed_candidates(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
    prepared: _PreparedSourceSeries | None = None,
) -> tuple[s0.S0RoutedCanonicalCandidate, ...]:
    result: list[s0.S0RoutedCanonicalCandidate] = []
    for event in bind_source_window_ict_events(
        bars,
        session=session,
        operating_day=operating_day,
        prepared=prepared,
    ):
        direction = _direction(event.side)
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
            candidate = s0.S0CanonicalArmedCandidate(
                event=event,
                context=context,
                m1=m1,
                armed_at=event.source_event_at,
            )
            route_wick = s0.bind_s0_route_and_wick(candidate)
            if (
                not route_wick.route_resolution.resolved
                or not route_wick.wick_formation.confirmed
            ):
                continue
            result.append(
                s0.S0RoutedCanonicalCandidate(
                    candidate=candidate,
                    route_wick=route_wick,
                )
            )
        except ValueError:
            continue
    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.candidate.armed_at,
                row.candidate.event.side.value,
                row.candidate.event.primary_armed_level,
            ),
        )
    )


def possible_touch_intervals(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    level: Decimal,
    start: datetime,
    end: datetime,
) -> tuple[tuple[datetime, datetime], ...]:
    """Use M1 only to locate minutes in which an executable fill is possible."""

    opened = _aware(start)
    closed = _aware(end)
    if closed <= opened:
        return ()
    result: list[tuple[datetime, datetime]] = []
    for bar in bars:
        if bar.closed_at <= opened:
            continue
        if bar.opened_at >= closed:
            break
        possible = (
            bar.low <= level
            if side is CapitalizerSide.LONG
            else bar.high >= level
        )
        if not possible:
            continue
        interval_start = max(opened, bar.opened_at)
        interval_end = min(closed - ONE_MILLISECOND, bar.closed_at - ONE_MILLISECOND)
        if interval_end >= interval_start:
            result.append((interval_start, interval_end))
    return tuple(result)


def _request_complete_interval(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    side: CapitalizerSide,
    level: Decimal,
    start: datetime,
    end: datetime,
    digits: int,
    request_prefix: str,
    depth: int = 0,
) -> tuple[s0.ProviderFillResolution | None, int, int]:
    """Query exact ticks, recursively splitting incomplete provider responses."""

    if depth > 20:
        raise RuntimeError("S1 provider tick pagination exceeded safe recursion")
    ticks, has_more = s0.request_provider_tick_interval(
        client,
        symbol_id=symbol_id,
        side=side,
        interval_start=start,
        interval_end=end,
        request_id=f"{request_prefix}:{depth}:{int(start.timestamp()*1000)}",
    )
    requests = 1
    if not has_more:
        resolved = s0.resolve_exact_provider_fill(
            side=side,
            armed_level=level,
            interval_start=start,
            interval_end=end,
            ticks=ticks,
            digits=digits,
            has_more=False,
        )
        return (resolved if resolved.filled else None, requests, resolved.provider_tick_count)

    span_ms = int((_aware(end) - _aware(start)).total_seconds() * 1000)
    if span_ms <= 1:
        raise RuntimeError("S1 incomplete provider tick response cannot be split")
    midpoint = _aware(start) + timedelta(milliseconds=span_ms // 2)
    left, left_requests, left_ticks = _request_complete_interval(
        client,
        symbol_id=symbol_id,
        side=side,
        level=level,
        start=start,
        end=midpoint,
        digits=digits,
        request_prefix=request_prefix,
        depth=depth + 1,
    )
    requests += left_requests
    if left is not None:
        return left, requests, left_ticks
    right_start = midpoint + ONE_MILLISECOND
    if right_start > _aware(end):
        return None, requests, left_ticks
    right, right_requests, right_ticks = _request_complete_interval(
        client,
        symbol_id=symbol_id,
        side=side,
        level=level,
        start=right_start,
        end=end,
        digits=digits,
        request_prefix=request_prefix,
        depth=depth + 1,
    )
    return right, requests + right_requests, left_ticks + right_ticks


def resolve_candidate_exact_fill(
    client: SpotwareCTraderOpenApiClient,
    *,
    candidate: s0.S0RoutedCanonicalCandidate,
    bars: tuple[CapitalizerM1Bar, ...],
    symbol_id: int,
    digits: int,
    request_prefix: str,
) -> tuple[S1ExactFill | None, int]:
    event = candidate.candidate.event
    deadline = event.h1_deadline
    levels: list[tuple[Decimal, str]] = [
        (event.primary_armed_level, event.primary_entry_mode)
    ]
    if event.fallback_armed_level is not None:
        levels.append((event.fallback_armed_level, "FVG_CE_50"))

    total_requests = 0
    for level, mode in levels:
        intervals = possible_touch_intervals(
            bars,
            side=event.side,
            level=level,
            start=event.source_event_at,
            end=deadline,
        )
        for index, (start, end) in enumerate(intervals):
            resolved, requests, _ticks = _request_complete_interval(
                client,
                symbol_id=symbol_id,
                side=event.side,
                level=level,
                start=start,
                end=end,
                digits=digits,
                request_prefix=f"{request_prefix}:{mode}:{index}",
            )
            total_requests += requests
            if resolved is not None:
                return (
                    S1ExactFill(
                        level=level,
                        mode=mode,
                        resolution=resolved,
                        request_count=total_requests,
                    ),
                    total_requests,
                )
    return None, total_requests


def _target_resolution_at_fill(
    candidate: s0.S0RoutedCanonicalCandidate,
    *,
    fill_price: Decimal,
    fill_at: datetime,
) -> remediation.CapitalizerStructuralTargetResolution:
    return remediation.resolve_structural_target(
        direction=candidate.candidate.context.direction,
        entry_price=fill_price,
        decision_at=fill_at,
        candidates=candidate.candidate.context.structural_target.candidates,
    )


def _evidence_stamps(
    candidate: s0.S0RoutedCanonicalCandidate,
    *,
    fill_at: datetime,
) -> tuple[v46_adapter.CapitalizerHistoricalEvidenceStamp, ...]:
    armed = candidate.candidate
    event = armed.event
    m1_mss_at = armed.m1.m1_mss.confirmed_at
    if m1_mss_at is None:
        raise ValueError("S1 admitted candidate requires M1 MSS timestamp")
    rows = {
        "HTF_POI": armed.context.htf.confirmed_at,
        "HTF_CLOSURE": armed.context.htf.confirmed_at,
        "HTF_BIAS": armed.context.htf.confirmed_at,
        "STRUCTURAL_TARGET": armed.armed_at,
        "PROTECTED_SWING": armed.m1.confirmed_at,
        "ICT_LIQUIDITY_REFERENCE": event.closeback.sweep_at,
        "ICT_LIQUIDITY_RAID": event.closeback.sweep_at,
        "ICT_MSS": event.m3_mss.confirmed_at,
        "ICT_DISPLACEMENT": event.m3_mss.confirmed_at,
        "ICT_FVG": event.zone.fvg_confirmed_at,
        "ICT_PD_ARRAY_RETRACE": fill_at,
        "ICT_NO_CHASE": fill_at,
        "TTRADES_LTF_CISD": armed.context.m15.confirmed_at,
        "TTRADES_CONTINUATION": armed.m1.confirmed_at,
        "TTRADES_WICK": armed.m1.confirmed_at,
        "M1_MSS": m1_mss_at,
        "M1_FVG": event.zone.fvg_confirmed_at,
        "M1_ORDER_BLOCK": armed.m1.confirmed_at,
    }
    return tuple(
        v46_adapter.CapitalizerHistoricalEvidenceStamp(
            key=key,
            observed_at=value,
        )
        for key, value in sorted(rows.items())
    )


def build_post_fill_bundle(
    candidate: s0.S0RoutedCanonicalCandidate,
    *,
    fill: S1ExactFill,
) -> v46_adapter.CapitalizerCanonicalHistoricalBundle:
    resolution = fill.resolution
    if resolution.fill_at is None or resolution.fill_price is None:
        raise ValueError("S1 post-fill bundle requires exact fill")
    armed = candidate.candidate
    event = armed.event
    fill_at = resolution.fill_at
    fill_price = resolution.fill_price

    target = _target_resolution_at_fill(
        candidate,
        fill_price=fill_price,
        fill_at=fill_at,
    )
    no_chase = remediation.assess_no_chase_entry(
        entry_price=fill_price,
        pd_array_lower=event.zone.fvg_low,
        pd_array_upper=event.zone.fvg_high,
        pd_array_confirmed_at=event.zone.fvg_confirmed_at,
        entry_at=fill_at,
    )
    asian_open = (
        v46_adapter.resolve_historical_asian_open_reference(fill_at)
        if event.session is CapitalizerSession.ASIA
        else None
    )
    return v46_adapter.CapitalizerCanonicalHistoricalBundle(
        symbol=event.symbol,
        side=event.side,
        session=event.session,
        decision_at=fill_at,
        cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        entry_price=fill_price,
        daily_bias=armed.context.htf.daily_bias,
        htf_closure=armed.context.htf.closure,
        structural_target=target,
        protected_swing=armed.m1.protected_swing,
        ict=v46_adapter.CapitalizerCanonicalICTFacts(
            liquidity_reference_defined=bool(event.closeback.reference.source),
            liquidity_raid_observed=True,
            market_structure_shift_confirmed=True,
            displacement_significant=True,
            fvg_present_in_displacement=True,
            entry_retrace_into_valid_pd_array=no_chase.confirmed,
        ),
        no_chase=no_chase,
        ltf_cisd=armed.context.m15.cisd,
        fractal_alignment=candidate.route_wick.fractal_alignment,
        failure_to_manipulate=candidate.route_wick.failure_to_manipulate,
        wick_formation=candidate.route_wick.wick_formation,
        m1_mss=armed.m1.m1_mss,
        m1_fvg_confirmed=True,
        m1_order_block=armed.m1.order_block,
        evidence_timestamps=_evidence_stamps(candidate, fill_at=fill_at),
        asian_open_reference=asian_open,
    )


def _row_from_admitted(
    *,
    period: str,
    candidate: s0.S0RoutedCanonicalCandidate,
    fill: S1ExactFill,
    isolation: s0.SourceStrategyIsolationAssessment,
) -> S1AdmittedFillRow:
    result = isolation.canonical_result
    engine = result.source_engine_assessment
    if (
        not result.passes_to_qore_risk
        or engine is None
        or engine.trade_plan is None
    ):
        raise ValueError("S1 admitted row requires canonical Risk handoff")
    resolution = fill.resolution
    if resolution.fill_at is None or resolution.fill_price is None:
        raise ValueError("S1 admitted row requires exact provider fill")
    plan = engine.trade_plan
    route = result.route_resolution.route
    if route is None:
        raise ValueError("S1 admitted row requires resolved source route")
    return S1AdmittedFillRow(
        identity=IDENTITY,
        period=period,
        symbol=candidate.candidate.event.symbol,
        session=candidate.candidate.event.session.value,
        operating_date=candidate.candidate.event.operating_date.isoformat(),
        side=candidate.candidate.event.side.value,
        route=route.value,
        armed_at=candidate.candidate.armed_at.isoformat(),
        entry_at=resolution.fill_at.isoformat(),
        entry_price=str(resolution.fill_price),
        armed_level_used=str(fill.level),
        entry_mode=fill.mode,
        stop_price=str(plan.initial_stop_price),
        target_price=str(plan.target_price),
        target_kind=plan.target_kind.value,
        provider_tick_count=resolution.provider_tick_count,
        provider_request_count=fill.request_count,
    )


def select_max3(
    rows: tuple[S1AdmittedFillRow, ...],
) -> tuple[S1AdmittedFillRow, ...]:
    grouped: dict[tuple[str, str], list[S1AdmittedFillRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.session, row.operating_date)].append(row)
    selected: list[S1AdmittedFillRow] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda row: (
                datetime.fromisoformat(row.entry_at),
                row.symbol,
            ),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda row: (
                datetime.fromisoformat(row.entry_at),
                row.symbol,
            ),
        )
    )


def _period_bars(
    root: Path,
    *,
    start: datetime,
    end: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    opened = start - LOOKBACK
    closed = end + timedelta(days=2)
    return tuple(
        bar
        for bar in iter_cibo_m1(root)
        if opened <= bar.opened_at < closed
    )


def _operating_days(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    period_start: datetime,
    period_end: datetime,
) -> tuple[date, ...]:
    observed = {
        bar.opened_at.astimezone(NEW_YORK).date()
        for bar in bars
        if period_start <= bar.opened_at < period_end
    }
    return tuple(
        day
        for day in sorted(observed)
        if (
            source_session_bounds(day, session=session)[1] > period_start
            and source_session_bounds(day, session=session)[0] < period_end
        )
    )


def _day_slice(
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    *,
    operating_day: date,
    session: CapitalizerSession,
) -> tuple[CapitalizerM1Bar, ...]:
    source_start, source_end = source_session_bounds(
        operating_day,
        session=session,
    )
    start = source_start - LOOKBACK
    end = source_end + timedelta(hours=1)
    left = bisect.bisect_left(opened, start)
    right = bisect.bisect_right(opened, end)
    return bars[left:right]


def build_period_market_population(
    client: SpotwareCTraderOpenApiClient,
    *,
    m1_root: Path,
    symbol: str,
    session: CapitalizerSession,
    period: str,
    symbol_id: int,
    digits: int,
) -> tuple[S1PeriodMarketReport, tuple[S1AdmittedFillRow, ...]]:
    if period not in PERIODS:
        raise ValueError("unknown S1 period")
    if not market_is_allowed(session=session, symbol=symbol):
        raise ValueError("S1 symbol/session outside frozen universe")
    period_start, period_end = PERIODS[period]
    bars = _period_bars(m1_root, start=period_start, end=period_end)
    if not bars:
        raise ValueError("S1 period has no provider-native M1")
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("S1 M1 symbol mismatch")
    opened = tuple(bar.opened_at for bar in bars)
    prepared = _prepare_source_series(bars)
    operating_days = _operating_days(
        bars,
        session=session,
        period_start=period_start,
        period_end=period_end,
    )

    routed = 0
    primary = 0
    fallback = 0
    no_fill = 0
    rejected = 0
    requests = 0
    admitted: list[S1AdmittedFillRow] = []

    for operating_day in operating_days:
        local_bars = _day_slice(
            bars,
            opened,
            operating_day=operating_day,
            session=session,
        )
        if not local_bars:
            continue
        candidates = bind_source_window_routed_candidates(
            local_bars,
            session=session,
            operating_day=operating_day,
            prepared=prepared,
        )
        for index, candidate in enumerate(candidates):
            routed += 1
            fill, fill_requests = resolve_candidate_exact_fill(
                client,
                candidate=candidate,
                bars=local_bars,
                symbol_id=symbol_id,
                digits=digits,
                request_prefix=(
                    f"capitalizer-s1:{period}:{symbol}:"
                    f"{operating_day.isoformat()}:{index}"
                ),
            )
            requests += fill_requests
            if fill is None:
                no_fill += 1
                continue
            if fill.mode == "FVG_CE_50" and (
                candidate.candidate.event.primary_entry_mode != "FVG_CE_50"
            ):
                fallback += 1
            else:
                primary += 1

            bundle = build_post_fill_bundle(candidate, fill=fill)
            isolation = s0.assess_source_strategy_isolation_bundle(bundle)
            if not isolation.canonical_result.passes_to_qore_risk:
                rejected += 1
                continue
            row = _row_from_admitted(
                period=period,
                candidate=candidate,
                fill=fill,
                isolation=isolation,
            )
            entry_at = datetime.fromisoformat(row.entry_at).astimezone(UTC)
            if not period_start <= entry_at < period_end:
                continue
            admitted.append(row)

    report = S1PeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        period_start=period_start.isoformat(),
        period_end_exclusive=period_end.isoformat(),
        operating_days_scanned=len(operating_days),
        routed_armed_candidates=routed,
        primary_fill_passes=primary,
        fallback_fill_passes=fallback,
        no_provider_fill=no_fill,
        v46_rejected_after_fill=rejected,
        admitted_exact_fills=len(admitted),
        provider_tick_requests=requests,
    )
    return report, tuple(
        sorted(
            admitted,
            key=lambda row: (
                datetime.fromisoformat(row.entry_at),
                row.symbol,
            ),
        )
    )


def write_market_outputs(
    *,
    output: Path,
    report: S1PeriodMarketReport,
    rows: tuple[S1AdmittedFillRow, ...],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    slug = f"{report.period}-{report.symbol.lower()}"
    (output / f"capitalizer-s1a-{slug}-report.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-s1a-{slug}-fills.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> tuple[S1PeriodMarketReport, ...]:
    reports: list[S1PeriodMarketReport] = []
    for path in sorted(root.rglob("capitalizer-s1a-*-report.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("S1 market report must be JSON object")
        reports.append(S1PeriodMarketReport(**raw))
    return tuple(reports)


def _load_rows(root: Path) -> tuple[S1AdmittedFillRow, ...]:
    rows: list[S1AdmittedFillRow] = []
    for path in sorted(root.rglob("capitalizer-s1a-*-fills.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(S1AdmittedFillRow(**json.loads(line)))
    return tuple(rows)


def aggregate_s1a(root: Path, output: Path) -> dict[str, object]:
    reports = _load_reports(root)
    rows = _load_rows(root)
    if len(reports) != 27:
        raise ValueError(f"S1A aggregate requires 27 market-period reports, got {len(reports)}")
    report_keys = {(row.period, row.symbol, row.session) for row in reports}
    if len(report_keys) != 27:
        raise ValueError("S1A aggregate market-period report identities are not unique")
    expected = {
        (period, symbol, session.value)
        for period in PERIODS
        for session in CapitalizerSession
        for symbol in (
            ("USDJPY", "AUDJPY", "AUDUSD", "GBPJPY")
            if session is CapitalizerSession.ASIA
            else ("EURUSD", "GBPUSD")
            if session is CapitalizerSession.LONDON
            else ("XAUUSD", "USDCAD", "NAS100")
        )
    }
    if report_keys != expected:
        missing = sorted(expected - report_keys)
        extra = sorted(report_keys - expected)
        raise ValueError(f"S1A report universe mismatch missing={missing} extra={extra}")
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "semantic_amendment_a1_comment_id": SEMANTIC_AMENDMENT_A1_COMMENT_ID,
        "semantic_amendment_a2_comment_id": SEMANTIC_AMENDMENT_A2_COMMENT_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "full_source_window_census": True,
        "exact_provider_tick_fill": True,
        "cognitive_gate_source": COGNITIVE_TOKEN,
        "terminal_outcome_read": False,
        "realized_r_read": False,
        "strategy_economics_calculated": False,
        "fresh_holdout_opened": False,
        "full_trader_fidelity_claimed": False,
        "candidate_promotion_allowed": False,
        "trader_certified": False,
        "market_period_reports": len(reports),
        "market_count": len({row.symbol for row in reports}),
        "periods": {},
    }
    period_payload: dict[str, object] = {}
    output.mkdir(parents=True, exist_ok=True)
    for period in PERIODS:
        population = tuple(row for row in rows if row.period == period)
        max3 = select_max3(population)
        period_payload[period] = {
            "admitted_exact_fills": len(population),
            "max3_selected_fills": len(max3),
            "max3_is_ceiling_not_quota": True,
            "outcome_used_for_selection": False,
        }
        with (output / f"capitalizer-s1a-{period}-max3.jsonl").open(
            "w",
            encoding="utf-8",
        ) as handle:
            for row in max3:
                handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    payload["periods"] = period_payload
    payload["next_phase"] = "S1A_POPULATION_READY_FOR_FROZEN_GROSS_ECONOMICS"
    (output / "capitalizer-s1a-aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _run_market(args: argparse.Namespace) -> None:
    client = SpotwareCTraderOpenApiClient(
        credentials=m1_clone._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"S1 cTrader DEMO authentication failed: {ready.error}")
        _provider_symbol, symbol_id, digits = m1_clone._selected_symbol(
            client,
            args.symbol,
        )
        for period in PERIODS:
            report, rows = build_period_market_population(
                client,
                m1_root=args.m1_root,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
                symbol_id=symbol_id,
                digits=digits,
            )
            write_market_outputs(
                output=args.output,
                report=report,
                rows=rows,
            )
            print(json.dumps(asdict(report), sort_keys=True))
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("s1a-market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("--symbol", required=True)
    market.add_argument("--session", required=True)
    market.add_argument("--output", type=Path, required=True)

    aggregate = sub.add_parser("s1a-aggregate")
    aggregate.add_argument("input", type=Path)
    aggregate.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "s1a-market":
        _run_market(args)
    else:
        report = aggregate_s1a(args.input, args.output)
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
