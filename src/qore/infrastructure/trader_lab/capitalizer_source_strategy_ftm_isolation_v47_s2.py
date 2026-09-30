"""V47-S2 full separate Failure-to-Manipulate source-strategy isolation.

Builds the FTM route without routing through the reversal-first V3 stream.
All work is pre-economic: causal candidate assembly, exact provider tick fill,
and official V46 acceptance only.

Frozen by PR #623 comment 5901844217.
"""

from __future__ import annotations

import argparse
import json
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
    TFBar,
    _pivots,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_SOURCE_STRATEGY_FTM_ISOLATION_V47_S2"
PREDECLARATION_COMMENT_ID = 5901844217
SOURCE_M1_RUN_ID = s1.SOURCE_M1_RUN_ID
SOURCE_M1_SHA = s1.SOURCE_M1_SHA
PERIODS = s1.PERIODS
COGNITIVE_TOKEN = s1.COGNITIVE_TOKEN


@dataclass(frozen=True, slots=True)
class FTMContinuationBinding:
    confirmed_at: datetime
    cisd: CapitalizerCISDObservation
    protected_swing: CapitalizerProtectedSwingObservation
    causal_series: tuple[CapitalizerSourceBar, ...]

    def __post_init__(self) -> None:
        s1._aware(self.confirmed_at)
        if not self.cisd.setup_confirmed:
            raise ValueError("FTM continuation requires setup-confirmed CISD")
        if not self.protected_swing.confirmed:
            raise ValueError("FTM continuation requires protected swing")
        if self.protected_swing.direction is not self.cisd.direction:
            raise ValueError("FTM continuation swing direction drift")
        if not self.causal_series:
            raise ValueError("FTM continuation requires causal series")


@dataclass(frozen=True, slots=True)
class FTMCanonicalCandidate:
    symbol: str
    session: CapitalizerSession
    operating_date: date
    side: CapitalizerSide
    sweep: raw_ftm.FTMRawSweep
    htf: binders.S0HTFContext
    continuation: FTMContinuationBinding
    failure_to_manipulate: CapitalizerFailureToManipulateObservation
    continuation_m3_mss: v3_source.M3MssEvent
    ict_displacement_fvg_confirmed_at: datetime
    m1: s2.S2IndependentM1
    target: structural_targets.S0StructuralTargetBinding
    armed_at: datetime
    primary_armed_level: Decimal
    fallback_armed_level: Decimal | None
    primary_entry_mode: str
    wick_formation: remediation.CapitalizerWickFormationObservation
    causal: bool = True
    outcome_used: bool = False

    def __post_init__(self) -> None:
        arm = s1._aware(self.armed_at)
        if arm != s1._aware(self.m1.armed_at):
            raise ValueError("FTM candidate arms with independent M1")
        if self.side is CapitalizerSide.LONG:
            if self.continuation.cisd.direction is not CapitalizerSourceDirection.BULLISH:
                raise ValueError("FTM LONG continuation direction drift")
        else:
            if self.continuation.cisd.direction is not CapitalizerSourceDirection.BEARISH:
                raise ValueError("FTM SHORT continuation direction drift")
        if not self.failure_to_manipulate.confirmed:
            raise ValueError("FTM candidate requires confirmed FTM")
        if not self.target.resolution.resolved:
            raise ValueError("FTM candidate requires unambiguous structural target")
        if not self.wick_formation.confirmed:
            raise ValueError("FTM candidate requires source wick formation")
        if arm >= s1._aware(self.sweep.deadline):
            raise ValueError("FTM candidate armed outside source deadline")
        if not self.causal or self.outcome_used:
            raise ValueError("FTM candidate governance drift")


@dataclass(frozen=True, slots=True)
class FTMAdmittedFillRow:
    identity: str
    period: str
    symbol: str
    session: str
    operating_date: str
    side: str
    route: str
    sweep_at: str
    continuation_cisd_at: str
    continuation_m3_mss_at: str
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
    exact_provider_tick_fill: bool = True
    official_v46_adapter_passed: bool = True
    outcome_used_for_selection: bool = False
    terminal_outcome_read: bool = False
    realized_r_read: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or self.period not in PERIODS:
            raise ValueError("FTM admitted row identity/period drift")
        if self.route != "FAILURE_TO_MANIPULATE_CONTINUATION":
            raise ValueError("FTM admitted row route drift")
        if (
            not self.exact_provider_tick_fill
            or not self.official_v46_adapter_passed
            or self.outcome_used_for_selection
            or self.terminal_outcome_read
            or self.realized_r_read
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("FTM admitted row governance drift")


@dataclass(frozen=True, slots=True)
class FTMPeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    raw_sweeps: int
    continuation_first: int
    continuation_binding: int
    continuation_m3: int
    continuation_m3_fvg: int
    independent_m1: int
    unambiguous_target: int
    routed_ftm: int
    exact_fills: int
    v46_rejected_after_fill: int
    admitted_exact_fills: int
    provider_tick_requests: int
    rejections: dict[str, int] = field(default_factory=dict)
    terminal_outcome_read: bool = False
    economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or self.period not in PERIODS:
            raise ValueError("FTM report identity/period drift")
        chain = (
            self.raw_sweeps,
            self.continuation_first,
            self.continuation_binding,
            self.continuation_m3,
            self.continuation_m3_fvg,
            self.independent_m1,
            self.unambiguous_target,
            self.routed_ftm,
        )
        if any(value < 0 for value in (*chain, self.exact_fills, self.admitted_exact_fills)):
            raise ValueError("FTM report counts cannot be negative")
        if any(left < right for left, right in zip(chain[:-1], chain[1:], strict=True)):
            raise ValueError("FTM funnel monotonicity drift")
        if self.admitted_exact_fills + self.v46_rejected_after_fill > self.exact_fills:
            raise ValueError("FTM post-fill classification drift")
        if (
            self.terminal_outcome_read
            or self.economics_calculated
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("FTM report governance drift")


def _bump(store: dict[str, int], key: str) -> None:
    store[key] = store.get(key, 0) + 1


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


def _side(direction: CapitalizerSourceDirection) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSide.SHORT
    )


def _continuation_direction(
    taken_side: raw_ftm.FTMTakenSide,
) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if taken_side is raw_ftm.FTMTakenSide.HIGH
        else CapitalizerSourceDirection.BEARISH
    )


def _expected_direction(
    taken_side: raw_ftm.FTMTakenSide,
) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BEARISH
        if taken_side is raw_ftm.FTMTakenSide.HIGH
        else CapitalizerSourceDirection.BULLISH
    )


def _taken_side(
    taken_side: raw_ftm.FTMTakenSide,
) -> CapitalizerLiquiditySideTaken:
    return (
        CapitalizerLiquiditySideTaken.HIGH
        if taken_side is raw_ftm.FTMTakenSide.HIGH
        else CapitalizerLiquiditySideTaken.LOW
    )


def first_setup_cisd_binding(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    after: datetime,
    before: datetime,
    htf_closure: CapitalizerSourceClosureObservation,
) -> FTMContinuationBinding | None:
    """Return first HTF-aligned setup-confirmed M1 CISD after a sweep."""

    # Typed at runtime by detect_cisd; object keeps this helper independent of
    # a circular type import while mypy validates call sites below.
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
        return FTMContinuationBinding(
            confirmed_at=confirmation.closed_at,
            cisd=observed,
            protected_swing=protected,
            causal_series=series,
        )
    return None


def _continuation_m3(
    rows: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    pivots: tuple[object, ...],
    *,
    sweep: raw_ftm.FTMRawSweep,
    side: CapitalizerSide,
) -> v3_source.M3MssEvent | None:
    if not rows:
        return None
    return v3_source._find_m3_mss(
        rows,
        closes,
        pivots,  # type: ignore[arg-type]
        after=sweep.sweep_at,
        before=sweep.deadline,
        side=side,
    )


def _ict_fvg_at(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    mss: v3_source.M3MssEvent,
) -> datetime | None:
    return s2._ict_displacement_fvg_confirmed_at(bars, event=mss)


def _target(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
    decision_at: datetime,
) -> structural_targets.S0StructuralTargetBinding | None:
    binding = structural_targets.bind_structural_target(
        bars,
        direction=direction,
        entry_price=entry_price,
        decision_at=decision_at,
    )
    return binding if binding.resolution.resolved else None


def bind_ftm_candidates_for_day(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
    prepared: s1._PreparedSourceSeries,
    funnel: dict[str, int],
    rejections: dict[str, int],
) -> tuple[FTMCanonicalCandidate, ...]:
    sweeps = raw_ftm.raw_sweeps_for_day(
        bars,
        prepared=prepared,
        session=session,
        operating_day=operating_day,
    )
    funnel["raw_sweeps"] = funnel.get("raw_sweeps", 0) + len(sweeps)
    result: list[FTMCanonicalCandidate] = []

    source_start, source_end = s1.source_session_bounds(
        operating_day,
        session=session,
    )
    execution = s1._prepared_m1_between(
        prepared,
        start=source_start,
        end=source_end,
    )
    m3_rows = tuple(
        row
        for row in s1._prepared_tf_between(
            prepared.m3,
            prepared.m3_opened,
            start=source_start - s1.LOOKBACK,
            end=source_end,
        )
        if isinstance(row, TFBar)
    )
    m3_closes = tuple(row.closed_at for row in m3_rows)
    m3_pivots = _pivots(m3_rows)
    htf_by_hour: dict[datetime, binders.S0HTFContext | None] = {}

    for sweep in sweeps:
        hour_open = sweep.sweep_at.replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        if hour_open not in htf_by_hour:
            htf_by_hour[hour_open] = binders.bind_latest_h1_context(
                bars,
                decision_at=sweep.sweep_at,
            )
        htf = htf_by_hour[hour_open]
        if htf is None:
            _bump(rejections, "HTF_CONTEXT_UNRESOLVED")
            continue
        continuation_direction = _continuation_direction(sweep.taken_side)
        expected_direction = _expected_direction(sweep.taken_side)
        if (
            htf.daily_bias.direction is not continuation_direction
            or htf.closure.direction is not continuation_direction
        ):
            _bump(rejections, "HTF_NOT_ALIGNED_WITH_CONTINUATION")
            continue

        continuation_at = raw_ftm.first_structural_m1_cisd(
            bars,
            direction=continuation_direction,
            after=sweep.sweep_at,
            before=sweep.deadline,
            htf_closure=htf.closure,
        )
        reversal_at = raw_ftm.first_structural_m1_cisd(
            bars,
            direction=expected_direction,
            after=sweep.sweep_at,
            before=sweep.deadline,
            htf_closure=htf.closure,
        )
        if continuation_at is None or (
            reversal_at is not None and reversal_at <= continuation_at
        ):
            _bump(rejections, "CONTINUATION_NOT_FIRST_STRUCTURAL_CISD")
            continue
        funnel["continuation_first"] = funnel.get("continuation_first", 0) + 1

        continuation = first_setup_cisd_binding(
            bars,
            direction=continuation_direction,
            after=sweep.sweep_at,
            before=continuation_at,
            htf_closure=htf.closure,
        )
        if continuation is None or continuation.confirmed_at != continuation_at:
            _bump(rejections, "CONTINUATION_SETUP_BINDING_UNRESOLVED")
            continue
        funnel["continuation_binding"] = funnel.get("continuation_binding", 0) + 1

        side = _side(continuation_direction)
        m3 = _continuation_m3(
            m3_rows,
            m3_closes,
            m3_pivots,
            sweep=sweep,
            side=side,
        )
        if m3 is None:
            _bump(rejections, "CONTINUATION_M3_MSS_UNRESOLVED")
            continue
        funnel["continuation_m3"] = funnel.get("continuation_m3", 0) + 1

        ict_fvg_at = _ict_fvg_at(execution, mss=m3)
        if ict_fvg_at is None:
            _bump(rejections, "CONTINUATION_M3_FVG_UNRESOLVED")
            continue
        funnel["continuation_m3_fvg"] = (
            funnel.get("continuation_m3_fvg", 0) + 1
        )

        entry_after = max(
            continuation.confirmed_at,
            m3.confirmed_at,
            ict_fvg_at,
        )
        m1 = s2.bind_independent_m1_structure(
            bars,
            side=side,
            higher_timeframe_closure=htf.closure,
            after=entry_after,
            before=sweep.deadline,
        )
        if m1 is None:
            _bump(rejections, "INDEPENDENT_M1_TRIAD_UNRESOLVED")
            continue
        funnel["independent_m1"] = funnel.get("independent_m1", 0) + 1

        # FTM expected reversal must remain absent up to the actual candidate arm.
        reversal_before_arm = raw_ftm.first_structural_m1_cisd(
            bars,
            direction=expected_direction,
            after=sweep.sweep_at,
            before=m1.armed_at,
            htf_closure=htf.closure,
        )
        if reversal_before_arm is not None:
            _bump(rejections, "EXPECTED_REVERSAL_CONFIRMED_BEFORE_ARM")
            continue

        primary, fallback, mode = s0.resolve_s0_armed_levels(
            side=side,
            zone=m1.zone,
        )
        target = _target(
            bars,
            direction=continuation_direction,
            entry_price=primary,
            decision_at=m1.armed_at,
        )
        if target is None:
            _bump(rejections, "STRUCTURAL_TARGET_AMBIGUOUS_OR_UNRESOLVED")
            continue
        funnel["unambiguous_target"] = funnel.get("unambiguous_target", 0) + 1

        ftm = assess_failure_to_manipulate(
            taken_side=_taken_side(sweep.taken_side),
            level_taken=True,
            post_sweep_closure_observed=True,
            expected_reversal_cisd=None,
            continuation_protected_swing=continuation.protected_swing,
            daily_bias=htf.daily_bias,
        )
        if not ftm.confirmed:
            _bump(rejections, "FTM_OBSERVATION_NOT_CONFIRMED")
            continue
        wick = remediation.assess_wick_formation(
            direction=continuation_direction,
            important_level_reached=continuation.cisd.important_level_reached,
            intracandle_cisd=continuation.cisd,
            protected_swing=continuation.protected_swing,
        )
        if not wick.confirmed:
            _bump(rejections, "FTM_WICK_NOT_CONFIRMED")
            continue

        result.append(
            FTMCanonicalCandidate(
                symbol=sweep.symbol,
                session=session,
                operating_date=operating_day,
                side=side,
                sweep=sweep,
                htf=htf,
                continuation=continuation,
                failure_to_manipulate=ftm,
                continuation_m3_mss=m3,
                ict_displacement_fvg_confirmed_at=ict_fvg_at,
                m1=m1,
                target=target,
                armed_at=m1.armed_at,
                primary_armed_level=primary,
                fallback_armed_level=fallback,
                primary_entry_mode=mode,
                wick_formation=wick,
            )
        )
        funnel["routed_ftm"] = funnel.get("routed_ftm", 0) + 1

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.armed_at,
                row.side.value,
                row.primary_armed_level,
            ),
        )
    )


def _exact_fill(
    client: SpotwareCTraderOpenApiClient,
    *,
    candidate: FTMCanonicalCandidate,
    bars: tuple[CapitalizerM1Bar, ...],
    symbol_id: int,
    digits: int,
    request_prefix: str,
) -> tuple[s1.S1ExactFill | None, int]:
    levels = [(candidate.primary_armed_level, candidate.primary_entry_mode)]
    if candidate.fallback_armed_level is not None:
        levels.append((candidate.fallback_armed_level, "FVG_CE_50"))

    requests = 0
    for level, mode in levels:
        intervals = s1.possible_touch_intervals(
            bars,
            side=candidate.side,
            level=level,
            start=candidate.armed_at,
            end=candidate.sweep.deadline,
        )
        for index, (start, end) in enumerate(intervals):
            resolved, used, _ticks = s1._request_complete_interval(
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
            if resolved is not None:
                return (
                    s1.S1ExactFill(
                        level=level,
                        mode=mode,
                        resolution=resolved,
                        request_count=requests,
                    ),
                    requests,
                )
    return None, requests


def _target_at_fill(
    candidate: FTMCanonicalCandidate,
    *,
    fill_price: Decimal,
    fill_at: datetime,
) -> remediation.CapitalizerStructuralTargetResolution:
    return remediation.resolve_structural_target(
        direction=_continuation_direction(candidate.sweep.taken_side),
        entry_price=fill_price,
        decision_at=fill_at,
        candidates=candidate.target.candidates,
    )


def _evidence_stamps(
    candidate: FTMCanonicalCandidate,
    *,
    fill_at: datetime,
) -> tuple[v46_adapter.CapitalizerHistoricalEvidenceStamp, ...]:
    m1_mss_at = candidate.m1.binding.m1_mss.confirmed_at
    if m1_mss_at is None:
        raise ValueError("FTM exact-fill bundle requires M1 MSS time")
    rows = {
        "HTF_POI": candidate.htf.confirmed_at,
        "HTF_CLOSURE": candidate.htf.confirmed_at,
        "HTF_BIAS": candidate.htf.confirmed_at,
        "STRUCTURAL_TARGET": candidate.armed_at,
        "PROTECTED_SWING": candidate.m1.binding.confirmed_at,
        "ICT_LIQUIDITY_REFERENCE": candidate.sweep.sweep_at,
        "ICT_LIQUIDITY_RAID": candidate.sweep.sweep_at,
        "ICT_MSS": candidate.continuation_m3_mss.confirmed_at,
        "ICT_DISPLACEMENT": candidate.continuation_m3_mss.confirmed_at,
        "ICT_FVG": candidate.ict_displacement_fvg_confirmed_at,
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
        v46_adapter.CapitalizerHistoricalEvidenceStamp(key=key, observed_at=value)
        for key, value in sorted(rows.items())
    )


def build_post_fill_bundle(
    candidate: FTMCanonicalCandidate,
    *,
    fill: s1.S1ExactFill,
) -> v46_adapter.CapitalizerCanonicalHistoricalBundle:
    resolved = fill.resolution
    if resolved.fill_at is None or resolved.fill_price is None:
        raise ValueError("FTM post-fill bundle requires exact fill")
    fill_at = resolved.fill_at
    fill_price = resolved.fill_price
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
    asian = (
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
        protected_swing=candidate.m1.binding.protected_swing,
        ict=v46_adapter.CapitalizerCanonicalICTFacts(
            liquidity_reference_defined=bool(candidate.sweep.liquidity_source),
            liquidity_raid_observed=True,
            market_structure_shift_confirmed=True,
            displacement_significant=True,
            fvg_present_in_displacement=True,
            entry_retrace_into_valid_pd_array=no_chase.confirmed,
        ),
        no_chase=no_chase,
        ltf_cisd=candidate.continuation.cisd,
        fractal_alignment=None,
        failure_to_manipulate=candidate.failure_to_manipulate,
        wick_formation=candidate.wick_formation,
        m1_mss=candidate.m1.binding.m1_mss,
        m1_fvg_confirmed=True,
        m1_order_block=candidate.m1.binding.order_block,
        evidence_timestamps=_evidence_stamps(candidate, fill_at=fill_at),
        asian_open_reference=asian,
    )


def _admitted_row(
    *,
    period: str,
    candidate: FTMCanonicalCandidate,
    fill: s1.S1ExactFill,
    assessment: s0.SourceStrategyIsolationAssessment,
) -> FTMAdmittedFillRow:
    result = assessment.canonical_result
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
        raise ValueError("FTM admitted row requires canonical Risk handoff")
    plan = engine.trade_plan
    return FTMAdmittedFillRow(
        identity=IDENTITY,
        period=period,
        symbol=candidate.symbol,
        session=candidate.session.value,
        operating_date=candidate.operating_date.isoformat(),
        side=candidate.side.value,
        route=result.route_resolution.route.value,
        sweep_at=candidate.sweep.sweep_at.isoformat(),
        continuation_cisd_at=candidate.continuation.confirmed_at.isoformat(),
        continuation_m3_mss_at=candidate.continuation_m3_mss.confirmed_at.isoformat(),
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
) -> tuple[FTMPeriodMarketReport, tuple[FTMAdmittedFillRow, ...]]:
    if period not in PERIODS:
        raise ValueError("unknown FTM period")
    if not market_is_allowed(session=session, symbol=symbol):
        raise ValueError("FTM market outside frozen universe")
    start, end = PERIODS[period]
    prepared = s1._prepare_source_series(consumed_bars)
    bars = s1._prepared_m1_between(
        prepared,
        start=start - s1.LOOKBACK,
        end=end + timedelta(days=2),
    )
    opened = tuple(row.opened_at for row in bars)
    days = s1._operating_days(
        bars,
        session=session,
        period_start=start,
        period_end=end,
    )
    funnel: dict[str, int] = {}
    rejections: dict[str, int] = {}
    admitted: list[FTMAdmittedFillRow] = []
    exact_fills = 0
    v46_rejected = 0
    requests = 0

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
            session=session,
            operating_day=day,
            prepared=prepared,
            funnel=funnel,
            rejections=rejections,
        )
        for index, candidate in enumerate(candidates):
            fill, used = _exact_fill(
                client,
                candidate=candidate,
                bars=local,
                symbol_id=symbol_id,
                digits=digits,
                request_prefix=(
                    f"capitalizer-ftm:{period}:{symbol}:{day.isoformat()}:{index}"
                ),
            )
            requests += used
            if fill is None:
                _bump(rejections, "EXACT_PROVIDER_FILL_NOT_PROVEN")
                continue
            exact_fills += 1
            bundle = build_post_fill_bundle(candidate, fill=fill)
            assessment = s0.assess_source_strategy_isolation_bundle(bundle)
            if not assessment.canonical_result.passes_to_qore_risk:
                v46_rejected += 1
                for reason in assessment.canonical_result.reasons:
                    _bump(rejections, f"V46:{reason}")
                for reason in assessment.canonical_result.dual_source_entry_acceptance.reasons:
                    _bump(rejections, f"V46_DUAL:{reason}")
                continue
            row = _admitted_row(
                period=period,
                candidate=candidate,
                fill=fill,
                assessment=assessment,
            )
            entry_at = datetime.fromisoformat(row.entry_at).astimezone(UTC)
            if start <= entry_at < end:
                admitted.append(row)

    report = FTMPeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        raw_sweeps=funnel.get("raw_sweeps", 0),
        continuation_first=funnel.get("continuation_first", 0),
        continuation_binding=funnel.get("continuation_binding", 0),
        continuation_m3=funnel.get("continuation_m3", 0),
        continuation_m3_fvg=funnel.get("continuation_m3_fvg", 0),
        independent_m1=funnel.get("independent_m1", 0),
        unambiguous_target=funnel.get("unambiguous_target", 0),
        routed_ftm=funnel.get("routed_ftm", 0),
        exact_fills=exact_fills,
        v46_rejected_after_fill=v46_rejected,
        admitted_exact_fills=len(admitted),
        provider_tick_requests=requests,
        rejections=dict(sorted(rejections.items())),
    )
    return report, tuple(
        sorted(
            admitted,
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol),
        )
    )


def write_market(
    output: Path,
    report: FTMPeriodMarketReport,
    rows: tuple[FTMAdmittedFillRow, ...],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    slug = f"{report.period}-{report.symbol.lower()}"
    (output / f"capitalizer-ftm-s2-{slug}-report.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"capitalizer-ftm-s2-{slug}-fills.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def aggregate(root: Path, output: Path) -> dict[str, object]:
    reports: list[FTMPeriodMarketReport] = []
    rows: list[FTMAdmittedFillRow] = []
    for path in sorted(root.rglob("capitalizer-ftm-s2-*-report.json")):
        reports.append(FTMPeriodMarketReport(**json.loads(path.read_text())))
    for path in sorted(root.rglob("capitalizer-ftm-s2-*-fills.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(FTMAdmittedFillRow(**json.loads(line)))
    if len(reports) != 27:
        raise ValueError(f"FTM S2 requires 27 reports, got {len(reports)}")
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "market_count": len({row.symbol for row in reports}),
        "market_period_reports": len(reports),
        "funnel": {
            "raw_sweeps": sum(row.raw_sweeps for row in reports),
            "continuation_first": sum(row.continuation_first for row in reports),
            "continuation_binding": sum(row.continuation_binding for row in reports),
            "continuation_m3": sum(row.continuation_m3 for row in reports),
            "continuation_m3_fvg": sum(row.continuation_m3_fvg for row in reports),
            "independent_m1": sum(row.independent_m1 for row in reports),
            "unambiguous_target": sum(row.unambiguous_target for row in reports),
            "routed_ftm": sum(row.routed_ftm for row in reports),
            "exact_fills": sum(row.exact_fills for row in reports),
            "v46_rejected_after_fill": sum(
                row.v46_rejected_after_fill for row in reports
            ),
            "admitted_exact_fills": len(rows),
        },
        "rejections": dict(
            sorted(
                (
                    key,
                    sum(row.rejections.get(key, 0) for row in reports),
                )
                for key in {
                    key
                    for row in reports
                    for key in row.rejections
                }
            )
        ),
        "periods": {
            period: {
                "admitted_exact_fills": sum(row.period == period for row in rows)
            }
            for period in PERIODS
        },
        "terminal_outcome_read": False,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
        "next_phase": (
            "FTM_EXACT_FILL_POPULATION_READY_FOR_COMBINED_RECOMPETITION"
            if rows
            else "FTM_ZERO_ADMITTED_POPULATION_REQUIRES_ROOT_CAUSE"
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    with (output / "capitalizer-ftm-s2-all-fills.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in sorted(
            rows,
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        ):
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    (output / "capitalizer-ftm-s2-aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _market(args: argparse.Namespace) -> None:
    client = SpotwareCTraderOpenApiClient(
        credentials=m1_clone._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"FTM cTrader authentication failed: {ready.error}")
        _provider, symbol_id, digits = m1_clone._selected_symbol(client, args.symbol)
        bars = s1._load_consumed_bars(args.m1_root)
        if not bars or any(row.symbol != args.symbol for row in bars):
            raise ValueError("FTM provider-native M1 symbol/source mismatch")
        for period in PERIODS:
            report, rows = build_period_market_population(
                client,
                consumed_bars=bars,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
                symbol_id=symbol_id,
                digits=digits,
            )
            write_market(args.output, report, rows)
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
        _market(args)
    else:
        print(json.dumps(aggregate(args.input, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
