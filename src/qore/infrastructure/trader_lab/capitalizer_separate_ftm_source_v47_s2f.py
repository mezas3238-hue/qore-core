"""V47-S2F fully separate Failure-to-Manipulate source stream.

FTM does not pass through the reversal-first V3 candidate stream.  It begins
from a causal liquidity sweep, requires continuation-aligned HTF context,
proves the expected reversal stayed structurally unconfirmed, then requires
real ICT M3 MSS/displacement plus independent M1 CISD/MSS/FVG/OB.

This module is pre-economic and uses the frozen generic structural-target
resolver only when it resolves one unambiguous target.

Frozen by PR #623 comment 5900576271.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import argparse
import json
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
    capitalizer_canonical_source_context_binders_v47_s0 as context_binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_structural_targets_v47_s0 as structural_targets,
)
from qore.infrastructure.trader_lab import (
    capitalizer_ftm_raw_population_v47_s1r_c as raw,
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
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerFailureToManipulateObservation,
    CapitalizerLiquiditySideTaken,
    assess_failure_to_manipulate,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_SEPARATE_FTM_SOURCE_STREAM_V47_S2F"
PREDECLARATION_COMMENT_ID = 5900576271


@dataclass(frozen=True, slots=True)
class S2FFtmCandidate:
    symbol: str
    session: CapitalizerSession
    operating_date: date
    side: CapitalizerSide
    sweep: raw.FTMRawSweep
    m3_mss: v3_source.M3MssEvent
    htf: context_binders.S0HTFContext
    m15: context_binders.S0CISDBinding
    m1: s2.S2IndependentM1
    structural_target: structural_targets.S0StructuralTargetBinding
    failure_to_manipulate: CapitalizerFailureToManipulateObservation
    primary_armed_level: Decimal
    fallback_armed_level: Decimal | None
    primary_entry_mode: str
    armed_at: datetime
    causal: bool = True
    reversal_stream_required: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("S2F symbol must be uppercase")
        if s1._aware(self.armed_at) != s1._aware(self.m1.armed_at):
            raise ValueError("S2F arm timestamp drift")
        if self.m3_mss.side is not self.side:
            raise ValueError("S2F M3 MSS direction drift")
        if self.m15.cisd.direction is not s2._direction(self.side):
            raise ValueError("S2F M15 direction drift")
        if self.m1.binding.m1_cisd.direction is not s2._direction(self.side):
            raise ValueError("S2F M1 direction drift")
        if not self.failure_to_manipulate.confirmed:
            raise ValueError("S2F requires confirmed FTM")
        if (
            not self.causal
            or self.reversal_stream_required
            or self.outcome_used
        ):
            raise ValueError("S2F governance drift")


def _continuation_side(
    taken_side: raw.FTMTakenSide,
) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if taken_side is raw.FTMTakenSide.HIGH
        else CapitalizerSide.SHORT
    )


def _taken_side(
    value: raw.FTMTakenSide,
) -> CapitalizerLiquiditySideTaken:
    return (
        CapitalizerLiquiditySideTaken.HIGH
        if value is raw.FTMTakenSide.HIGH
        else CapitalizerLiquiditySideTaken.LOW
    )


def _expected_reversal_direction(
    taken_side: raw.FTMTakenSide,
) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BEARISH
        if taken_side is raw.FTMTakenSide.HIGH
        else CapitalizerSourceDirection.BULLISH
    )


def _m3_between(
    prepared: s1._PreparedSourceSeries,
    *,
    start: datetime,
    end: datetime,
) -> tuple[TFBar, ...]:
    return tuple(
        row
        for row in s1._prepared_tf_between(
            prepared.m3,
            prepared.m3_opened,
            start=start,
            end=end,
        )
        if isinstance(row, TFBar)
    )


def _continuation_m3_mss(
    prepared: s1._PreparedSourceSeries,
    *,
    sweep: raw.FTMRawSweep,
    side: CapitalizerSide,
) -> v3_source.M3MssEvent | None:
    start = sweep.sweep_at - s1.LOOKBACK
    bars = _m3_between(prepared, start=start, end=sweep.deadline)
    if not bars:
        return None
    closes = tuple(row.closed_at for row in bars)
    pivots = _pivots(bars)
    return v3_source._find_m3_mss(
        bars,
        closes,
        pivots,
        after=sweep.sweep_at,
        before=sweep.deadline,
        side=side,
    )


def _target_binding(
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


def bind_s2f_candidates(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    prepared: s1._PreparedSourceSeries,
    session: CapitalizerSession,
    operating_day: date,
    funnel: dict[str, int] | None = None,
    rejections: dict[str, int] | None = None,
) -> tuple[S2FFtmCandidate, ...]:
    """Build separate FTM candidates without reading outcomes."""

    def bump(store: dict[str, int] | None, key: str) -> None:
        if store is not None:
            store[key] = store.get(key, 0) + 1

    sweeps = raw.raw_sweeps_for_day(
        bars,
        prepared=prepared,
        session=session,
        operating_day=operating_day,
    )
    if funnel is not None:
        funnel["raw_sweeps"] = funnel.get("raw_sweeps", 0) + len(sweeps)

    result: list[S2FFtmCandidate] = []
    for sweep in sweeps:
        side = _continuation_side(sweep.taken_side)
        direction = s2._direction(side)

        htf = context_binders.bind_latest_h1_context(
            bars,
            decision_at=sweep.sweep_at,
        )
        if htf is None:
            bump(rejections, "HTF_CONTEXT_UNRESOLVED")
            continue
        if (
            htf.daily_bias.direction is not direction
            or htf.closure.direction is not direction
        ):
            bump(rejections, "HTF_NOT_CONTINUATION_ALIGNED")
            continue
        bump(funnel, "htf_continuation_aligned")

        m3_mss = _continuation_m3_mss(
            prepared,
            sweep=sweep,
            side=side,
        )
        if m3_mss is None:
            bump(rejections, "CONTINUATION_M3_MSS_UNRESOLVED")
            continue
        bump(funnel, "continuation_m3_mss")

        m15 = s2.bind_s2_m15_cisd(
            bars,
            direction=direction,
            higher_timeframe_closure=htf.closure,
            after=htf.confirmed_at,
            before=sweep.deadline,
        )
        if m15 is None:
            bump(rejections, "CONTINUATION_M15_CISD_UNRESOLVED")
            continue
        bump(funnel, "continuation_m15")

        m1_after = max(
            sweep.sweep_at,
            m3_mss.confirmed_at,
            m15.confirmed_at,
        )
        m1 = s2.bind_independent_m1_structure(
            bars,
            side=side,
            higher_timeframe_closure=htf.closure,
            after=m1_after,
            before=sweep.deadline,
        )
        if m1 is None:
            bump(rejections, "CONTINUATION_M1_TRIAD_UNRESOLVED")
            continue
        bump(funnel, "continuation_m1")

        expected_at = raw.first_structural_m1_cisd(
            bars,
            direction=_expected_reversal_direction(sweep.taken_side),
            after=sweep.sweep_at,
            before=m1.armed_at,
            htf_closure=htf.closure,
        )
        if expected_at is not None:
            bump(rejections, "EXPECTED_REVERSAL_CONFIRMED_BEFORE_FTM_ARM")
            continue

        ftm = assess_failure_to_manipulate(
            taken_side=_taken_side(sweep.taken_side),
            level_taken=True,
            post_sweep_closure_observed=True,
            expected_reversal_cisd=None,
            continuation_protected_swing=m1.binding.protected_swing,
            daily_bias=htf.daily_bias,
        )
        if not ftm.confirmed:
            bump(rejections, "FTM_CONTRACT_NOT_CONFIRMED")
            continue
        bump(funnel, "ftm_confirmed")

        primary, fallback, mode = s0.resolve_s0_armed_levels(
            side=side,
            zone=m1.zone,
        )
        target = _target_binding(
            bars,
            direction=direction,
            entry_price=primary,
            decision_at=m1.armed_at,
        )
        if target is None:
            bump(rejections, "UNAMBIGUOUS_STRUCTURAL_TARGET_UNRESOLVED")
            continue
        bump(funnel, "target_bound")

        result.append(
            S2FFtmCandidate(
                symbol=sweep.symbol,
                session=session,
                operating_date=operating_day,
                side=side,
                sweep=sweep,
                m3_mss=m3_mss,
                htf=htf,
                m15=m15,
                m1=m1,
                structural_target=target,
                failure_to_manipulate=ftm,
                primary_armed_level=primary,
                fallback_armed_level=fallback,
                primary_entry_mode=mode,
                armed_at=m1.armed_at,
            )
        )
        bump(funnel, "armed_ftm_candidates")

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


def resolve_exact_fill(
    client: SpotwareCTraderOpenApiClient,
    *,
    candidate: S2FFtmCandidate,
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
    candidate: S2FFtmCandidate,
    *,
    fill_price: Decimal,
    fill_at: datetime,
) -> remediation.CapitalizerStructuralTargetResolution:
    return remediation.resolve_structural_target(
        direction=s2._direction(candidate.side),
        entry_price=fill_price,
        decision_at=fill_at,
        candidates=candidate.structural_target.candidates,
    )


def _evidence_stamps(
    candidate: S2FFtmCandidate,
    *,
    fill_at: datetime,
) -> tuple[v46_adapter.CapitalizerHistoricalEvidenceStamp, ...]:
    m1_mss_at = candidate.m1.binding.m1_mss.confirmed_at
    if m1_mss_at is None:
        raise ValueError("S2F M1 MSS timestamp missing")
    rows = {
        "HTF_POI": candidate.htf.confirmed_at,
        "HTF_CLOSURE": candidate.htf.confirmed_at,
        "HTF_BIAS": candidate.htf.confirmed_at,
        "STRUCTURAL_TARGET": candidate.armed_at,
        "PROTECTED_SWING": candidate.m1.binding.confirmed_at,
        "ICT_LIQUIDITY_REFERENCE": candidate.sweep.sweep_at,
        "ICT_LIQUIDITY_RAID": candidate.sweep.sweep_at,
        "ICT_MSS": candidate.m3_mss.confirmed_at,
        "ICT_DISPLACEMENT": candidate.m3_mss.confirmed_at,
        "ICT_FVG": candidate.m1.zone.fvg_confirmed_at,
        "ICT_PD_ARRAY_RETRACE": fill_at,
        "ICT_NO_CHASE": fill_at,
        "TTRADES_LTF_CISD": candidate.m15.confirmed_at,
        "TTRADES_CONTINUATION": candidate.m1.binding.confirmed_at,
        "TTRADES_WICK": candidate.m1.binding.confirmed_at,
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
    candidate: S2FFtmCandidate,
    *,
    fill: s1.S1ExactFill,
) -> v46_adapter.CapitalizerCanonicalHistoricalBundle:
    resolution = fill.resolution
    if resolution.fill_at is None or resolution.fill_price is None:
        raise ValueError("S2F exact fill required")
    fill_at = resolution.fill_at
    fill_price = resolution.fill_price
    direction = s2._direction(candidate.side)

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
    wick = remediation.assess_wick_formation(
        direction=direction,
        important_level_reached=True,
        intracandle_cisd=candidate.m1.binding.m1_cisd,
        protected_swing=candidate.m1.binding.protected_swing,
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
        protected_swing=candidate.m1.binding.protected_swing,
        ict=v46_adapter.CapitalizerCanonicalICTFacts(
            liquidity_reference_defined=True,
            liquidity_raid_observed=True,
            market_structure_shift_confirmed=True,
            displacement_significant=True,
            fvg_present_in_displacement=True,
            entry_retrace_into_valid_pd_array=no_chase.confirmed,
        ),
        no_chase=no_chase,
        ltf_cisd=candidate.m15.cisd,
        fractal_alignment=None,
        failure_to_manipulate=candidate.failure_to_manipulate,
        wick_formation=wick,
        m1_mss=candidate.m1.binding.m1_mss,
        m1_fvg_confirmed=True,
        m1_order_block=candidate.m1.binding.order_block,
        evidence_timestamps=_evidence_stamps(candidate, fill_at=fill_at),
        asian_open_reference=asian_open,
    )


@dataclass(frozen=True, slots=True)
class S2FPeriodMarketReport:
    identity: str
    period: str
    symbol: str
    session: str
    operating_days_scanned: int
    raw_sweeps: int
    htf_continuation_aligned: int
    continuation_m3_mss: int
    continuation_m15: int
    continuation_m1: int
    ftm_confirmed: int
    target_bound: int
    armed_ftm_candidates: int
    forensic_rejections: dict[str, int]
    exact_provider_fill_queried: bool = False
    terminal_outcome_read: bool = False
    economics_calculated: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S2F report identity drift")
        if self.period not in s1.PERIODS:
            raise ValueError("S2F report period drift")
        if not (
            self.raw_sweeps
            >= self.htf_continuation_aligned
            >= self.continuation_m3_mss
            >= self.continuation_m15
            >= self.continuation_m1
            >= self.ftm_confirmed
            >= self.target_bound
            >= self.armed_ftm_candidates
        ):
            raise ValueError("S2F funnel monotonicity drift")
        if (
            self.exact_provider_fill_queried
            or self.terminal_outcome_read
            or self.economics_calculated
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S2F prefill governance drift")


def audit_period_market(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    symbol: str,
    session: CapitalizerSession,
    period: str,
) -> S2FPeriodMarketReport:
    if period not in s1.PERIODS:
        raise ValueError("unknown S2F period")
    start, end = s1.PERIODS[period]
    prepared = s1._prepare_source_series(bars)
    days = s1._operating_days(
        bars,
        session=session,
        period_start=start,
        period_end=end,
    )
    opened = prepared.opened
    funnel: dict[str, int] = {}
    forensic: dict[str, int] = {}
    for day in days:
        local = s1._day_slice(
            bars,
            opened,
            operating_day=day,
            session=session,
        )
        if not local:
            continue
        bind_s2f_candidates(
            local,
            prepared=prepared,
            session=session,
            operating_day=day,
            funnel=funnel,
            rejections=forensic,
        )

    return S2FPeriodMarketReport(
        identity=IDENTITY,
        period=period,
        symbol=symbol,
        session=session.value,
        operating_days_scanned=len(days),
        raw_sweeps=funnel.get("raw_sweeps", 0),
        htf_continuation_aligned=funnel.get("htf_continuation_aligned", 0),
        continuation_m3_mss=funnel.get("continuation_m3_mss", 0),
        continuation_m15=funnel.get("continuation_m15", 0),
        continuation_m1=funnel.get("continuation_m1", 0),
        ftm_confirmed=funnel.get("ftm_confirmed", 0),
        target_bound=funnel.get("target_bound", 0),
        armed_ftm_candidates=funnel.get("armed_ftm_candidates", 0),
        forensic_rejections=dict(sorted(forensic.items())),
    )


def _load_consumed(root: Path, symbol: str) -> tuple[CapitalizerM1Bar, ...]:
    rows = tuple(
        row
        for row in iter_cibo_m1(root)
        if s1.CONSUMED_LOAD_START <= row.opened_at < s1.CONSUMED_LOAD_END
    )
    if not rows:
        raise ValueError("S2F provider-native M1 is empty")
    if any(row.symbol != symbol for row in rows):
        raise ValueError("S2F symbol mismatch")
    return rows


def write_report(report: S2FPeriodMarketReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-v47-s2f-{report.period}-{report.symbol.lower()}.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def aggregate(root: Path, output: Path) -> dict[str, object]:
    reports: list[S2FPeriodMarketReport] = []
    for path in sorted(root.rglob("capitalizer-v47-s2f-*.json")):
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_payload, dict):
            raise ValueError("S2F report must be object")
        reports.append(S2FPeriodMarketReport(**raw_payload))
    if len(reports) != 27:
        raise ValueError(f"S2F requires 27 reports, got {len(reports)}")
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "market_period_reports": len(reports),
        "market_count": len({row.symbol for row in reports}),
        "funnel": {
            "raw_sweeps": sum(row.raw_sweeps for row in reports),
            "htf_continuation_aligned": sum(
                row.htf_continuation_aligned for row in reports
            ),
            "continuation_m3_mss": sum(
                row.continuation_m3_mss for row in reports
            ),
            "continuation_m15": sum(row.continuation_m15 for row in reports),
            "continuation_m1": sum(row.continuation_m1 for row in reports),
            "ftm_confirmed": sum(row.ftm_confirmed for row in reports),
            "target_bound": sum(row.target_bound for row in reports),
            "armed_ftm_candidates": sum(
                row.armed_ftm_candidates for row in reports
            ),
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
        "exact_provider_fill_queried": False,
        "terminal_outcome_read": False,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
        "next_phase": (
            "S2F_READY_FOR_EXACT_FILL_V46"
            if sum(row.armed_ftm_candidates for row in reports) > 0
            else "S2F_NO_FULL_PREFILL_CANDIDATES_ROOT_CAUSE_REQUIRED"
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v47-s2f-aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


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
        bars = _load_consumed(args.m1_root, args.symbol)
        for period in s1.PERIODS:
            report = audit_period_market(
                bars,
                symbol=args.symbol,
                session=CapitalizerSession(args.session),
                period=period,
            )
            write_report(report, args.output)
            print(json.dumps(asdict(report), sort_keys=True))
        return

    print(json.dumps(aggregate(args.input, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
