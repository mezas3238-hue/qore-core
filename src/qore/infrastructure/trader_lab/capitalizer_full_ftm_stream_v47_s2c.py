"""V47-S2C full Failure-to-Manipulate source stream.

Builds a distinct FTM candidate population from provider-native M1 without
requiring the reversal-first V3 path. This phase is pre-economic.

Frozen by PR #623 comment 5901846384.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as v46_adapter,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_composition_v47_s2 as s2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_structural_targets_v47_s0 as structural_targets,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cibo_10y_m1_clone_v1 as m1_clone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_ftm_raw_population_v47_s1r_c as raw_ftm,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3_source,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
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
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
    CapitalizerLiquiditySideTaken,
    assess_failure_to_manipulate,
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_structural_extraction_v2 import (
    protected_swing_from_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _pivots,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_V47_S2C_FULL_FTM_STREAM"
PREDECLARATION_COMMENT_ID = 5901846384
SOURCE_M1_RUN_ID = s1.SOURCE_M1_RUN_ID
SOURCE_M1_SHA = s1.SOURCE_M1_SHA
COGNITIVE_TOKEN = s1.COGNITIVE_TOKEN
PERIODS = s1.PERIODS


@dataclass(frozen=True, slots=True)
class FTMContinuationBinding:
    confirmed_at: datetime
    cisd: CapitalizerCISDObservation
    protected_swing: CapitalizerProtectedSwingObservation
    causal_series: tuple[CapitalizerSourceBar, ...]

    def __post_init__(self) -> None:
        s1._aware(self.confirmed_at)
        if not getattr(self.cisd, "setup_confirmed", False):
            raise ValueError("S2C continuation CISD must be setup-confirmed")
        if not getattr(self.protected_swing, "confirmed", False):
            raise ValueError("S2C continuation protected swing missing")
        if not self.causal_series:
            raise ValueError("S2C continuation causal series missing")


@dataclass(frozen=True, slots=True)
class S2CFTMCandidate:
    symbol: str
    session: CapitalizerSession
    operating_date: date
    side: CapitalizerSide
    liquidity_source: str
    liquidity_price: Decimal
    sweep_at: datetime
    deadline: datetime
    htf: binders.S0HTFContext
    continuation: FTMContinuationBinding
    ftm: CapitalizerFailureToManipulateObservation
    ict_m3_mss: v3_source.M3MssEvent
    ict_fvg_confirmed_at: datetime
    m1: s2.S2IndependentM1
    armed_at: datetime
    primary_armed_level: Decimal
    fallback_armed_level: Decimal | None
    primary_entry_mode: str
    structural_target: structural_targets.S0StructuralTargetBinding
    wick: remediation.CapitalizerWickFormationObservation
    causal: bool = True
    outcome_used: bool = False

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("S2C symbol must be uppercase")
        if self.armed_at != self.m1.armed_at:
            raise ValueError("S2C arm timestamp must equal independent M1 readiness")
        if self.armed_at >= self.deadline:
            raise ValueError("S2C must arm before source deadline")
        if not self.ftm.confirmed:
            raise ValueError("S2C requires confirmed FTM")
        if not self.structural_target.resolution.resolved:
            raise ValueError("S2C requires deterministic structural target")
        if not self.wick.confirmed:
            raise ValueError("S2C requires confirmed wick")
        if not self.causal or self.outcome_used:
            raise ValueError("S2C governance drift")


@dataclass(frozen=True, slots=True)
class S2CAdmittedFillRow:
    identity: str
    period: str
    symbol: str
    session: str
    operating_date: str
    side: str
    route: str
    sweep_at: str
    continuation_confirmed_at: str
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
    candidate_promotion_allowed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or self.period not in PERIODS:
            raise ValueError("S2C admitted row identity/period drift")
        if self.route != "FAILURE_TO_MANIPULATE_CONTINUATION":
            raise ValueError("S2C admitted row route drift")
        if (
            not self.provider_native_m1
            or not self.exact_provider_tick_fill
            or not self.official_v46_adapter_passed
            or self.outcome_used_for_selection
            or self.terminal_outcome_read
            or self.realized_r_read
            or self.fresh_holdout_opened
            or self.candidate_promotion_allowed
            or self.trader_certified
        ):
            raise ValueError("S2C admitted row governance drift")


@dataclass(frozen=True, slots=True)
class S2CPeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    raw_sweeps: int
    htf_continuation_aligned: int
    continuation_first: int
    continuation_binding: int
    ict_continuation_mss_fvg: int
    independent_m1_bound: int
    deterministic_target_bound: int
    exact_fills: int
    v46_rejected_after_fill: int
    admitted_exact_fills: int
    provider_tick_requests: int
    forensic_rejections: dict[str, int] = field(default_factory=dict)
    economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        counts = (
            self.raw_sweeps,
            self.htf_continuation_aligned,
            self.continuation_first,
            self.continuation_binding,
            self.ict_continuation_mss_fvg,
            self.independent_m1_bound,
            self.deterministic_target_bound,
            self.exact_fills,
            self.v46_rejected_after_fill,
            self.admitted_exact_fills,
            self.provider_tick_requests,
        )
        if any(value < 0 for value in counts):
            raise ValueError("S2C counts cannot be negative")
        if not (
            self.raw_sweeps
            >= self.htf_continuation_aligned
            >= self.continuation_first
            >= self.continuation_binding
            >= self.ict_continuation_mss_fvg
            >= self.independent_m1_bound
            >= self.deterministic_target_bound
        ):
            raise ValueError("S2C funnel monotonicity drift")
        if self.admitted_exact_fills + self.v46_rejected_after_fill > self.exact_fills:
            raise ValueError("S2C post-fill classification drift")
        if self.economics_calculated or self.fresh_holdout_opened or self.trader_certified:
            raise ValueError("S2C report governance drift")


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


def _continuation_side(
    taken: raw_ftm.FTMTakenSide,
) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if taken is raw_ftm.FTMTakenSide.HIGH
        else CapitalizerSide.SHORT
    )


def _liquidity_side(
    taken: raw_ftm.FTMTakenSide,
) -> CapitalizerLiquiditySideTaken:
    return (
        CapitalizerLiquiditySideTaken.HIGH
        if taken is raw_ftm.FTMTakenSide.HIGH
        else CapitalizerLiquiditySideTaken.LOW
    )


def _source(bar: CapitalizerM1Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _opposing(
    bar: CapitalizerM1Bar,
    direction: CapitalizerSourceDirection,
) -> bool:
    if bar.close == bar.open:
        return False
    if direction is CapitalizerSourceDirection.BULLISH:
        return bar.close < bar.open
    return bar.close > bar.open


def first_continuation_binding(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    after: datetime,
    before: datetime,
    htf_closure: CapitalizerSourceClosureObservation,
) -> FTMContinuationBinding | None:
    selected = tuple(
        row
        for row in bars
        if s1._aware(after) < row.closed_at <= s1._aware(before)
    )
    for index, confirmation in enumerate(selected):
        cursor = index - 1
        if cursor < 0 or not _opposing(selected[cursor], direction):
            continue
        start = cursor
        while start > 0 and _opposing(selected[start - 1], direction):
            start -= 1
        series_rows = selected[start:index]
        if not series_rows:
            continue
        series = tuple(_source(row) for row in series_rows)
        observed = detect_cisd(
            causal_series=series,
            confirmation_bar=_source(confirmation),
            direction=direction,
            important_level_reached=True,
            higher_timeframe_closure=htf_closure,
        )
        if not observed.setup_confirmed:
            continue
        protected = protected_swing_from_cisd(
            cisd=observed,
            causal_series=series,
            confirmation_bar=_source(confirmation),
            origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        )
        if not protected.confirmed:
            continue
        return FTMContinuationBinding(
            confirmed_at=confirmation.closed_at,
            cisd=observed,
            protected_swing=protected,
            causal_series=series,
        )
    return None


def _continuation_m3_mss(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    after: datetime,
    before: datetime,
) -> v3_source.M3MssEvent | None:
    m3 = _aggregate_tf(bars, minutes=3)
    closes = tuple(row.closed_at for row in m3)
    pivots = _pivots(m3)
    return v3_source._find_m3_mss(
        m3,
        closes,
        pivots,
        after=after,
        before=before,
        side=side,
    )


def _resolve_exact_fill(
    client: SpotwareCTraderOpenApiClient,
    *,
    candidate: S2CFTMCandidate,
    bars: tuple[CapitalizerM1Bar, ...],
    symbol_id: int,
    digits: int,
    request_prefix: str,
) -> tuple[s1.S1ExactFill | None, int]:
    levels: list[tuple[Decimal, str]] = [
        (candidate.primary_armed_level, candidate.primary_entry_mode)
    ]
    if candidate.fallback_armed_level is not None:
        levels.append((candidate.fallback_armed_level, "FVG_CE_50"))

    requests = 0
    for level, mode in levels:
        intervals = s1.possible_touch_intervals(
            bars,
            side=candidate.side,
            level=level,
            start=candidate.armed_at,
            end=candidate.deadline,
        )
        for index, (start, end) in enumerate(intervals):
            resolution, used, _ticks = s1._request_complete_interval(
                client,
                symbol_id=symbol_id,
                side=candidate.side,
                level=level,
                start=start,
                end=end,
                digits=digits,
                request_prefix=f"{request_prefix}:{mode}:{index}",
            )
            requests += used
            if resolution is not None:
                return (
                    s1.S1ExactFill(
                        level=level,
                        mode=mode,
                        resolution=resolution,
                        request_count=requests,
                    ),
                    requests,
                )
    return None, requests


def _target_at_fill(
    candidate: S2CFTMCandidate,
    *,
    fill_price: Decimal,
    fill_at: datetime,
) -> remediation.CapitalizerStructuralTargetResolution:
    return remediation.resolve_structural_target(
        direction=_direction(candidate.side),
        entry_price=fill_price,
        decision_at=fill_at,
        candidates=candidate.structural_target.candidates,
    )


def _evidence_stamps(
    candidate: S2CFTMCandidate,
    *,
    fill_at: datetime,
) -> tuple[v46_adapter.CapitalizerHistoricalEvidenceStamp, ...]:
    m1_mss_at = candidate.m1.binding.m1_mss.confirmed_at
    if m1_mss_at is None:
        raise ValueError("S2C M1 MSS timestamp required")
    rows = {
        "HTF_POI": candidate.htf.confirmed_at,
        "HTF_CLOSURE": candidate.htf.confirmed_at,
        "HTF_BIAS": candidate.htf.confirmed_at,
        "STRUCTURAL_TARGET": candidate.armed_at,
        "PROTECTED_SWING": candidate.continuation.confirmed_at,
        "ICT_LIQUIDITY_REFERENCE": candidate.sweep_at,
        "ICT_LIQUIDITY_RAID": candidate.sweep_at,
        "ICT_MSS": candidate.ict_m3_mss.confirmed_at,
        "ICT_DISPLACEMENT": candidate.ict_m3_mss.confirmed_at,
        "ICT_FVG": candidate.ict_fvg_confirmed_at,
        "ICT_PD_ARRAY_RETRACE": fill_at,
        "ICT_NO_CHASE": fill_at,
        "TTRADES_LTF_CISD": candidate.continuation.confirmed_at,
        "TTRADES_CONTINUATION": candidate.continuation.confirmed_at,
        "TTRADES_WICK": candidate.continuation.confirmed_at,
        "M1_MSS": m1_mss_at,
        "M1_FVG": candidate.m1.zone.fvg_confirmed_at,
        "M1_ORDER_BLOCK": candidate.m1.binding.confirmed_at,
    }
    return tuple(
        v46_adapter.CapitalizerHistoricalEvidenceStamp(
            key=key,
            observed_at=value,
        )
        for key, value in sorted(rows.items())
    )


def build_post_fill_bundle(
    candidate: S2CFTMCandidate,
    *,
    fill: s1.S1ExactFill,
) -> v46_adapter.CapitalizerCanonicalHistoricalBundle:
    resolution = fill.resolution
    if resolution.fill_at is None or resolution.fill_price is None:
        raise ValueError("S2C exact fill required")
    fill_at = resolution.fill_at
    fill_price = resolution.fill_price
    target = _target_at_fill(
        candidate,
        fill_price=fill_price,
        fill_at=fill_at,
    )
    no_chase = remediation.assess_no_chase_entry(
        entry_price=fill_price,
        pd_array_lower=candidate.m1.zone.fvg_low,
        pd_array_upper=candidate.m1.zone.fvg_high,
        pd_array_confirmed_at=candidate.m1.zone.fvg_confirmed_at,
        entry_at=fill_at,
    )
    asian_open = (
        v46_adapter.resolve_historical_asian_open_reference(fill_at)
        if candidate.session is CapitalizerSession.ASIA
        else None
    )
    return v46_adapter.CapitalizerCanonicalHistoricalBundle(
        symbol=candidate.symbol,
        side=candidate.side,
        session=candidate.session,
        decision_at=fill_at,
        cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        entry_price=fill_price,
        daily_bias=candidate.htf.daily_bias,
        htf_closure=candidate.htf.closure,
        structural_target=target,
        protected_swing=candidate.continuation.protected_swing,
        ict=v46_adapter.CapitalizerCanonicalICTFacts(
            liquidity_reference_defined=bool(candidate.liquidity_source),
            liquidity_raid_observed=True,
            market_structure_shift_confirmed=True,
            displacement_significant=True,
            fvg_present_in_displacement=True,
            entry_retrace_into_valid_pd_array=no_chase.confirmed,
        ),
        no_chase=no_chase,
        ltf_cisd=candidate.continuation.cisd,
        fractal_alignment=None,
        failure_to_manipulate=candidate.ftm,
        wick_formation=candidate.wick,
        m1_mss=candidate.m1.binding.m1_mss,
        m1_fvg_confirmed=True,
        m1_order_block=candidate.m1.binding.order_block,
        evidence_timestamps=_evidence_stamps(candidate, fill_at=fill_at),
        asian_open_reference=asian_open,
    )


def bind_ftm_candidates_for_day(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    prepared: s1._PreparedSourceSeries,
    session: CapitalizerSession,
    operating_day: date,
    funnel: dict[str, int],
    rejections: dict[str, int],
) -> tuple[S2CFTMCandidate, ...]:
    def bump(key: str) -> None:
        rejections[key] = rejections.get(key, 0) + 1

    source_start, source_end = s1.source_session_bounds(
        operating_day,
        session=session,
    )
    execution = s1._prepared_m1_between(
        prepared,
        start=source_start,
        end=source_end,
    )
    sweeps = raw_ftm.raw_sweeps_for_day(
        bars,
        prepared=prepared,
        session=session,
        operating_day=operating_day,
    )
    funnel["raw_sweeps"] = funnel.get("raw_sweeps", 0) + len(sweeps)
    result: list[S2CFTMCandidate] = []

    for sweep in sweeps:
        side = _continuation_side(sweep.taken_side)
        direction = _direction(side)
        htf = binders.bind_latest_h1_context(
            bars,
            decision_at=sweep.sweep_at,
        )
        if htf is None:
            bump("HTF_CONTEXT_UNRESOLVED")
            continue
        if htf.daily_bias.direction is not direction:
            bump("HTF_BIAS_NOT_CONTINUATION")
            continue
        funnel["htf_continuation_aligned"] = (
            funnel.get("htf_continuation_aligned", 0) + 1
        )

        expected, continuation_direction = raw_ftm._direction_pair(
            sweep.taken_side
        )
        reversal_at = raw_ftm.first_structural_m1_cisd(
            bars,
            direction=expected,
            after=sweep.sweep_at,
            before=sweep.deadline,
            htf_closure=htf.closure,
        )
        continuation_at = raw_ftm.first_structural_m1_cisd(
            bars,
            direction=continuation_direction,
            after=sweep.sweep_at,
            before=sweep.deadline,
            htf_closure=htf.closure,
        )
        if continuation_at is None:
            bump("CONTINUATION_CISD_UNRESOLVED")
            continue
        if reversal_at is not None and reversal_at <= continuation_at:
            bump("EXPECTED_REVERSAL_CONFIRMED_FIRST")
            continue
        funnel["continuation_first"] = funnel.get("continuation_first", 0) + 1

        continuation = first_continuation_binding(
            bars,
            direction=direction,
            after=sweep.sweep_at,
            before=sweep.deadline,
            htf_closure=htf.closure,
        )
        if continuation is None or continuation.confirmed_at != continuation_at:
            bump("CONTINUATION_BINDING_UNRESOLVED")
            continue
        funnel["continuation_binding"] = (
            funnel.get("continuation_binding", 0) + 1
        )

        ftm = assess_failure_to_manipulate(
            taken_side=_liquidity_side(sweep.taken_side),
            level_taken=True,
            post_sweep_closure_observed=True,
            expected_reversal_cisd=None,
            continuation_protected_swing=continuation.protected_swing,
            daily_bias=htf.daily_bias,
        )
        if not ftm.confirmed:
            bump("FTM_CONTRACT_NOT_CONFIRMED")
            continue

        m3 = _continuation_m3_mss(
            execution,
            side=side,
            after=sweep.sweep_at,
            before=sweep.deadline,
        )
        if m3 is None:
            bump("ICT_CONTINUATION_M3_MSS_UNRESOLVED")
            continue
        ict_fvg_at = s2._ict_displacement_fvg_confirmed_at(
            execution,
            event=m3,
        )
        if ict_fvg_at is None:
            bump("ICT_CONTINUATION_FVG_UNRESOLVED")
            continue
        funnel["ict_continuation_mss_fvg"] = (
            funnel.get("ict_continuation_mss_fvg", 0) + 1
        )

        m1_after = max(
            continuation.confirmed_at,
            m3.confirmed_at,
            ict_fvg_at,
        )
        m1 = s2.bind_independent_m1_structure(
            bars,
            side=side,
            higher_timeframe_closure=htf.closure,
            after=m1_after,
            before=sweep.deadline,
        )
        if m1 is None:
            bump("INDEPENDENT_M1_TRIAD_UNRESOLVED")
            continue
        funnel["independent_m1_bound"] = (
            funnel.get("independent_m1_bound", 0) + 1
        )

        primary, fallback, mode = s0.resolve_s0_armed_levels(
            side=side,
            zone=m1.zone,
        )
        target = structural_targets.bind_structural_target(
            bars,
            direction=direction,
            entry_price=primary,
            decision_at=m1.armed_at,
        )
        if not target.resolution.resolved:
            bump("STRUCTURAL_TARGET_UNRESOLVED")
            continue
        funnel["deterministic_target_bound"] = (
            funnel.get("deterministic_target_bound", 0) + 1
        )

        wick = remediation.assess_wick_formation(
            direction=direction,
            important_level_reached=True,
            intracandle_cisd=continuation.cisd,
            protected_swing=continuation.protected_swing,
        )
        if not wick.confirmed:
            bump("WICK_UNRESOLVED")
            continue

        route = remediation.resolve_source_entry_route(
            fractal_alignment=None,
            failure_to_manipulate=ftm,
        )
        if (
            not route.resolved
            or route.route is None
            or route.route.value != "FAILURE_TO_MANIPULATE_CONTINUATION"
        ):
            bump("FTM_ROUTE_UNRESOLVED")
            continue

        try:
            result.append(
                S2CFTMCandidate(
                    symbol=sweep.symbol,
                    session=sweep.session,
                    operating_date=sweep.operating_date,
                    side=side,
                    liquidity_source=sweep.liquidity_source,
                    liquidity_price=sweep.liquidity_price,
                    sweep_at=sweep.sweep_at,
                    deadline=sweep.deadline,
                    htf=htf,
                    continuation=continuation,
                    ftm=ftm,
                    ict_m3_mss=m3,
                    ict_fvg_confirmed_at=ict_fvg_at,
                    m1=m1,
                    armed_at=m1.armed_at,
                    primary_armed_level=primary,
                    fallback_armed_level=fallback,
                    primary_entry_mode=mode,
                    structural_target=target,
                    wick=wick,
                )
            )
        except ValueError:
            bump("CANDIDATE_INVARIANT_REJECT")
            continue

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.armed_at,
                row.symbol,
                row.side.value,
                row.primary_armed_level,
            ),
        )
    )


def _admitted_row(
    *,
    period: str,
    candidate: S2CFTMCandidate,
    fill: s1.S1ExactFill,
    isolation: s0.SourceStrategyIsolationAssessment,
) -> S2CAdmittedFillRow:
    result = isolation.canonical_result
    engine = result.source_engine_assessment
    resolution = fill.resolution
    if (
        not result.passes_to_qore_risk
        or engine is None
        or engine.trade_plan is None
        or resolution.fill_at is None
        or resolution.fill_price is None
        or result.route_resolution.route is None
    ):
        raise ValueError("S2C admitted row requires canonical Risk handoff")
    plan = engine.trade_plan
    return S2CAdmittedFillRow(
        identity=IDENTITY,
        period=period,
        symbol=candidate.symbol,
        session=candidate.session.value,
        operating_date=candidate.operating_date.isoformat(),
        side=candidate.side.value,
        route=result.route_resolution.route.value,
        sweep_at=candidate.sweep_at.isoformat(),
        continuation_confirmed_at=candidate.continuation.confirmed_at.isoformat(),
        armed_at=candidate.armed_at.isoformat(),
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


def build_period_market_population(
    client: SpotwareCTraderOpenApiClient,
    *,
    consumed_bars: tuple[CapitalizerM1Bar, ...],
    symbol: str,
    session: CapitalizerSession,
    period: str,
    symbol_id: int,
    digits: int,
) -> tuple[S2CPeriodMarketReport, tuple[S2CAdmittedFillRow, ...]]:
    if period not in PERIODS:
        raise ValueError("unknown S2C period")
    if not market_is_allowed(session=session, symbol=symbol):
        raise ValueError("S2C market outside frozen universe")
    period_start, period_end = PERIODS[period]
    prepared = s1._prepare_source_series(consumed_bars)
    bars = s1._prepared_m1_between(
        prepared,
        start=period_start - s1.LOOKBACK,
        end=period_end + timedelta(days=2),
    )
    opened = tuple(row.opened_at for row in bars)
    days = s1._operating_days(
        bars,
        session=session,
        period_start=period_start,
        period_end=period_end,
    )

    funnel: dict[str, int] = {}
    forensic: dict[str, int] = {}
    exact_fills = 0
    v46_rejected = 0
    requests = 0
    admitted: list[S2CAdmittedFillRow] = []

    for day in days:
        local = s1._day_slice(
            bars,
            opened,
            operating_day=day,
            session=session,
        )
        if not local:
            continue
        candidates = bind_ftm_candidates_for_day(
            local,
            prepared=prepared,
            session=session,
            operating_day=day,
            funnel=funnel,
            rejections=forensic,
        )
        for index, candidate in enumerate(candidates):
            fill, used = _resolve_exact_fill(
                client,
                candidate=candidate,
                bars=local,
                symbol_id=symbol_id,
                digits=digits,
                request_prefix=(
                    f"capitalizer-s2c:{period}:{symbol}:"
                    f"{day.isoformat()}:{index}"
                ),
            )
            requests += used
            if fill is None:
                forensic["EXACT_PROVIDER_FILL_NOT_PROVEN"] = (
                    forensic.get("EXACT_PROVIDER_FILL_NOT_PROVEN", 0) + 1
                )
                continue
            exact_fills += 1
            bundle = build_post_fill_bundle(candidate, fill=fill)
            isolation = s0.assess_source_strategy_isolation_bundle(bundle)
            if not isolation.canonical_result.passes_to_qore_risk:
                v46_rejected += 1
                for reason in isolation.canonical_result.reasons:
                    key = f"V46:{reason}"
                    forensic[key] = forensic.get(key, 0) + 1
                continue
            row = _admitted_row(
                period=period,
                candidate=candidate,
                fill=fill,
                isolation=isolation,
            )
            entry_at = datetime.fromisoformat(row.entry_at).astimezone(UTC)
            if period_start <= entry_at < period_end:
                admitted.append(row)

    report = S2CPeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        raw_sweeps=funnel.get("raw_sweeps", 0),
        htf_continuation_aligned=funnel.get("htf_continuation_aligned", 0),
        continuation_first=funnel.get("continuation_first", 0),
        continuation_binding=funnel.get("continuation_binding", 0),
        ict_continuation_mss_fvg=funnel.get("ict_continuation_mss_fvg", 0),
        independent_m1_bound=funnel.get("independent_m1_bound", 0),
        deterministic_target_bound=funnel.get("deterministic_target_bound", 0),
        exact_fills=exact_fills,
        v46_rejected_after_fill=v46_rejected,
        admitted_exact_fills=len(admitted),
        provider_tick_requests=requests,
        forensic_rejections=dict(sorted(forensic.items())),
    )
    return report, tuple(
        sorted(
            admitted,
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol),
        )
    )


def write_market_outputs(
    *,
    output: Path,
    report: S2CPeriodMarketReport,
    rows: tuple[S2CAdmittedFillRow, ...],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    slug = f"{report.period}-{report.symbol.lower()}"
    (output / f"capitalizer-s2c-{slug}-report.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-s2c-{slug}-fills.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def select_max3(
    rows: tuple[S2CAdmittedFillRow, ...],
) -> tuple[S2CAdmittedFillRow, ...]:
    grouped: dict[tuple[str, str], list[S2CAdmittedFillRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.session, row.operating_date)].append(row)
    selected: list[S2CAdmittedFillRow] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol, row.route),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol, row.route),
        )
    )


def aggregate(root: Path, output: Path) -> dict[str, object]:
    reports: list[S2CPeriodMarketReport] = []
    rows: list[S2CAdmittedFillRow] = []
    for path in sorted(root.rglob("capitalizer-s2c-*-report.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        reports.append(S2CPeriodMarketReport(**raw))
    for path in sorted(root.rglob("capitalizer-s2c-*-fills.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(S2CAdmittedFillRow(**json.loads(line)))
    if len(reports) != 27:
        raise ValueError(f"S2C requires 27 reports, got {len(reports)}")

    output.mkdir(parents=True, exist_ok=True)
    periods: dict[str, object] = {}
    for period in PERIODS:
        population = tuple(row for row in rows if row.period == period)
        max3 = select_max3(population)
        periods[period] = {
            "admitted_exact_fills": len(population),
            "max3_selected_fills": len(max3),
            "max3_is_ceiling_not_quota": True,
            "outcome_used_for_selection": False,
        }
        with (output / f"capitalizer-s2c-{period}-max3.jsonl").open(
            "w",
            encoding="utf-8",
        ) as handle:
            for row in max3:
                handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "market_period_reports": len(reports),
        "market_count": len({row.symbol for row in reports}),
        "funnel": {
            "raw_sweeps": sum(row.raw_sweeps for row in reports),
            "htf_continuation_aligned": sum(
                row.htf_continuation_aligned for row in reports
            ),
            "continuation_first": sum(row.continuation_first for row in reports),
            "continuation_binding": sum(row.continuation_binding for row in reports),
            "ict_continuation_mss_fvg": sum(
                row.ict_continuation_mss_fvg for row in reports
            ),
            "independent_m1_bound": sum(
                row.independent_m1_bound for row in reports
            ),
            "deterministic_target_bound": sum(
                row.deterministic_target_bound for row in reports
            ),
            "exact_fills": sum(row.exact_fills for row in reports),
            "v46_rejected_after_fill": sum(
                row.v46_rejected_after_fill for row in reports
            ),
            "admitted_exact_fills": len(rows),
        },
        "forensic_rejections": dict(
            sorted(
                (
                    key,
                    sum(row.forensic_rejections.get(key, 0) for row in reports),
                )
                for key in {
                    key
                    for row in reports
                    for key in row.forensic_rejections
                }
            )
        ),
        "periods": periods,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "candidate_promotion_allowed": False,
        "trader_certified": False,
        "next_phase": (
            "S2C_FTM_POPULATION_READY_FOR_TWO_ROUTE_FREEZE"
            if rows
            else "S2C_ZERO_FTM_ADMISSION_REQUIRES_ROOT_CAUSE"
        ),
    }
    (output / "capitalizer-s2c-aggregate.json").write_text(
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
            raise RuntimeError(f"S2C cTrader authentication failed: {ready.error}")
        _provider_symbol, symbol_id, digits = m1_clone._selected_symbol(
            client,
            args.symbol,
        )
        consumed = s1._load_consumed_bars(args.m1_root)
        if not consumed or any(row.symbol != args.symbol for row in consumed):
            raise ValueError("S2C provider-native M1 symbol/source mismatch")
        for period in PERIODS:
            report, rows = build_period_market_population(
                client,
                consumed_bars=consumed,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
                symbol_id=symbol_id,
                digits=digits,
            )
            write_market_outputs(output=args.output, report=report, rows=rows)
            print(json.dumps(asdict(report), sort_keys=True))
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("--symbol", required=True)
    market.add_argument("--session", required=True)
    market.add_argument("--output", type=Path, required=True)
    matrix = sub.add_parser("aggregate")
    matrix.add_argument("input", type=Path)
    matrix.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "market":
        _run_market(args)
    else:
        print(json.dumps(aggregate(args.input, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
