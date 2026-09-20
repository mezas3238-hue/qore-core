"""Nine-market replay of the stricter ICT + TTrades entry-admission sequence.

This module does two deliberately separated things:

1. It replays an M5 causal *entry-admission surrogate* over the immutable 55,532
   Capitalizer geometry candidates. The surrogate requires:
   - prior structural liquidity reference;
   - liquidity raid;
   - post-raid market-structure shift;
   - significant displacement (QORE deterministic, non-fitted M5 operationalization);
   - directional FVG formed around the displacement;
   - subsequent retrace into that FVG;
   - entry open still inside the FVG (anti-chase);
   - TTrades-compatible M5 CISD/protected-swing surrogate.

2. It keeps full ICT + TTrades source fidelity fail-closed because the consumed corpus
   has no native M1 and does not prove the exact H1->M15->M1 route.

The accepted-surrogate economics use the SAME entry and SAME structural target from the
immutable replay ledger, but replace the old one-bar stop with the causal protected-swing
surrogate. No future outcome is used to select entries.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_protected_swing_corrected_replay_v1 import (
    _lifecycle,
    _protected_swing_surrogate,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOIKind,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)

IDENTITY = "QORE_CAPITALIZER_STRICT_ENTRY_ACCEPTANCE_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STRICT_ENTRY_ACCEPTANCE_REPLAY_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerEntryFunnel:
    total_candidates: int
    liquidity_reference: int
    liquidity_raid: int
    market_structure_shift: int
    significant_displacement: int
    fvg_in_displacement: int
    retrace_into_fvg: int
    anti_chase_entry_inside_fvg: int
    ttrades_cisd_protected_swing: int
    accepted_m5_surrogate: int


@dataclass(frozen=True, slots=True)
class CapitalizerStrictEntryMarketReport:
    identity: str
    symbol: str
    session: str
    funnel: CapitalizerEntryFunnel
    surrogate_acceptance_rate: str
    baseline_matched_metrics: CapitalizerR0Metrics | None
    accepted_corrected_metrics: CapitalizerR0Metrics | None
    median_protected_swing_width_vs_original: str | None
    rejection_reasons: tuple[tuple[str, int], ...]
    source_entry_conditions_integrated_in_trader: bool = True
    ict_original_primary: bool = True
    ttrades_secondary_refinement: bool = True
    qore_m5_operationalization: bool = True
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    full_dual_source_entry_pass_count: int = 0
    source_faithful_replay_complete: bool = False
    outcome_used_for_selection: bool = False
    numeric_fit_used: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerStrictEntryMatrix:
    identity: str
    markets: tuple[CapitalizerStrictEntryMarketReport, ...]
    complete_nine_market_universe: bool
    total_candidates: int
    accepted_m5_surrogate: int
    surrogate_acceptance_rate: str
    aggregate_baseline_matched_metrics: CapitalizerR0Metrics | None
    aggregate_accepted_corrected_metrics: CapitalizerR0Metrics | None
    aggregate_rejection_reasons: tuple[tuple[str, int], ...]
    source_entry_conditions_integrated_in_trader: bool = True
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    full_dual_source_entry_pass_count: int = 0
    source_faithful_replay_complete: bool = False
    outcome_used_for_selection: bool = False
    numeric_fit_used: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class _AcceptedTrade:
    entry_at: datetime
    baseline_r: Decimal
    corrected_r: Decimal
    baseline_reason: str
    corrected_reason: str
    baseline_bars: int
    corrected_bars: int
    baseline_ambiguity: bool
    corrected_ambiguity: bool
    baseline_reward_r: Decimal
    corrected_reward_r: Decimal
    stop_width_ratio: Decimal


@dataclass(frozen=True, slots=True)
class _ConditionTrace:
    liquidity_reference: bool = False
    liquidity_raid: bool = False
    market_structure_shift: bool = False
    significant_displacement: bool = False
    fvg_in_displacement: bool = False
    retrace_into_fvg: bool = False
    anti_chase_entry_inside_fvg: bool = False
    ttrades_cisd_protected_swing: bool = False
    protected_swing_price: Decimal | None = None
    rejection_reason: str = "LIQUIDITY_REFERENCE_NOT_FOUND"


def _source_bar(bar: CapitalizerM5Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"strict entry replay requires one replay ledger, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw: Any = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("strict entry replay row must be an object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("strict entry replay cannot consume outcome-selected rows")
            rows.append(raw)
    if not rows:
        raise ValueError("strict entry replay requires candidates")
    return tuple(rows)


def _session_start_index(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    index: int,
) -> int:
    session = capitalizer_session_at(bars[index].opened_at)
    if session is None:
        raise ValueError("candidate signal must be inside Capitalizer session")
    cursor = index
    while cursor > 0:
        previous = bars[cursor - 1]
        current = bars[cursor]
        if current.opened_at - previous.opened_at != BAR_DURATION:
            break
        if capitalizer_session_at(previous.opened_at) is not session:
            break
        cursor -= 1
    return cursor


def _swing_indices(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    start: int,
    end_exclusive: int,
    high: bool,
) -> tuple[int, ...]:
    result: list[int] = []
    lower = max(start + 1, 1)
    upper = min(end_exclusive - 1, len(bars) - 1)
    for index in range(lower, upper):
        left = bars[index - 1]
        center = bars[index]
        right = bars[index + 1]
        if high and center.high > left.high and center.high > right.high:
            result.append(index)
        if not high and center.low < left.low and center.low < right.low:
            result.append(index)
    return tuple(result)


def _significant_displacement(bar: CapitalizerM5Bar, side: CapitalizerSide) -> bool:
    """Non-fitted M5 operationalization: directional body dominates total wick."""

    if bar.range <= 0:
        return False
    directional = (
        bar.close > bar.open
        if side is CapitalizerSide.LONG
        else bar.close < bar.open
    )
    return directional and bar.body > (bar.range - bar.body)


def _fvg_for_mss(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    mss_index: int,
    confirmation_index: int,
    side: CapitalizerSide,
) -> tuple[int, Decimal, Decimal] | None:
    if mss_index <= 0 or mss_index + 1 > confirmation_index:
        return None
    poi = detect_fair_value_gap(
        candle1=_source_bar(bars[mss_index - 1]),
        candle2=_source_bar(bars[mss_index]),
        candle3=_source_bar(bars[mss_index + 1]),
    )
    if poi is None:
        return None
    expected = (
        CapitalizerSourcePOIKind.BULLISH_FVG
        if side is CapitalizerSide.LONG
        else CapitalizerSourcePOIKind.BEARISH_FVG
    )
    if poi.kind is not expected:
        return None
    return mss_index + 1, poi.lower_price, poi.upper_price


def _trace_conditions(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    confirmation_index: int,
    entry_index: int,
    side: CapitalizerSide,
) -> _ConditionTrace:
    start = _session_start_index(bars, index=confirmation_index)

    # ICT liquidity reference: most recent completed three-bar swing before the raid.
    refs = _swing_indices(
        bars,
        start=start,
        end_exclusive=confirmation_index,
        high=side is CapitalizerSide.SHORT,
    )
    if not refs:
        return _ConditionTrace()

    for reference_index in reversed(refs):
        reference_price = (
            bars[reference_index].high
            if side is CapitalizerSide.SHORT
            else bars[reference_index].low
        )

        raid_indices = tuple(
            index
            for index in range(reference_index + 2, confirmation_index + 1)
            if (
                bars[index].high > reference_price
                if side is CapitalizerSide.SHORT
                else bars[index].low < reference_price
            )
        )
        if not raid_indices:
            continue

        for raid_index in raid_indices:
            opposite_swings = _swing_indices(
                bars,
                start=start,
                end_exclusive=raid_index + 1,
                high=side is CapitalizerSide.LONG,
            )
            opposite_swings = tuple(index for index in opposite_swings if index < raid_index)
            if not opposite_swings:
                continue
            break_index = opposite_swings[-1]
            break_price = (
                bars[break_index].high
                if side is CapitalizerSide.LONG
                else bars[break_index].low
            )

            mss_candidates = tuple(
                index
                for index in range(raid_index + 1, confirmation_index + 1)
                if (
                    bars[index].close > break_price
                    if side is CapitalizerSide.LONG
                    else bars[index].close < break_price
                )
            )
            if not mss_candidates:
                continue

            for mss_index in mss_candidates:
                if not _significant_displacement(bars[mss_index], side):
                    continue
                fvg = _fvg_for_mss(
                    bars,
                    mss_index=mss_index,
                    confirmation_index=confirmation_index,
                    side=side,
                )
                if fvg is None:
                    continue
                fvg_confirm_index, lower, upper = fvg

                retrace_indices = tuple(
                    index
                    for index in range(fvg_confirm_index + 1, confirmation_index + 1)
                    if bars[index].high >= lower and bars[index].low <= upper
                )
                if not retrace_indices:
                    continue

                entry_open = bars[entry_index].open
                inside = lower <= entry_open <= upper
                if not inside:
                    return _ConditionTrace(
                        liquidity_reference=True,
                        liquidity_raid=True,
                        market_structure_shift=True,
                        significant_displacement=True,
                        fvg_in_displacement=True,
                        retrace_into_fvg=True,
                        anti_chase_entry_inside_fvg=False,
                        rejection_reason="ENTRY_OPEN_OUTSIDE_FVG_CHASE",
                    )

                protected = _protected_swing_surrogate(
                    bars,
                    confirmation_index=confirmation_index,
                    side=side,
                )
                if protected is None:
                    return _ConditionTrace(
                        liquidity_reference=True,
                        liquidity_raid=True,
                        market_structure_shift=True,
                        significant_displacement=True,
                        fvg_in_displacement=True,
                        retrace_into_fvg=True,
                        anti_chase_entry_inside_fvg=True,
                        rejection_reason="TTRADES_CISD_PROTECTED_SWING_NOT_CONFIRMED",
                    )
                protected_price, _ = protected
                geometry_ok = (
                    protected_price < entry_open
                    if side is CapitalizerSide.LONG
                    else protected_price > entry_open
                )
                if not geometry_ok:
                    return _ConditionTrace(
                        liquidity_reference=True,
                        liquidity_raid=True,
                        market_structure_shift=True,
                        significant_displacement=True,
                        fvg_in_displacement=True,
                        retrace_into_fvg=True,
                        anti_chase_entry_inside_fvg=True,
                        ttrades_cisd_protected_swing=False,
                        rejection_reason="PROTECTED_SWING_GEOMETRY_INVALID",
                    )
                return _ConditionTrace(
                    liquidity_reference=True,
                    liquidity_raid=True,
                    market_structure_shift=True,
                    significant_displacement=True,
                    fvg_in_displacement=True,
                    retrace_into_fvg=True,
                    anti_chase_entry_inside_fvg=True,
                    ttrades_cisd_protected_swing=True,
                    protected_swing_price=protected_price,
                    rejection_reason="ACCEPTED_M5_SURROGATE",
                )

    # Return the deepest causal stage reached across alternatives.
    # This deliberately preserves a coarse funnel and never consults outcomes.
    raid_any = any(
        (
            bars[index].high > bars[ref].high
            if side is CapitalizerSide.SHORT
            else bars[index].low < bars[ref].low
        )
        for ref in refs
        for index in range(ref + 2, confirmation_index + 1)
    )
    return _ConditionTrace(
        liquidity_reference=True,
        liquidity_raid=raid_any,
        rejection_reason=(
            "MARKET_STRUCTURE_SHIFT_NOT_CONFIRMED"
            if raid_any
            else "LIQUIDITY_RAID_NOT_OBSERVED"
        ),
    )


def _metrics_from_values(
    values: tuple[Decimal, ...],
    *,
    reasons: tuple[str, ...],
    bars_held: tuple[int, ...],
    ambiguities: tuple[bool, ...],
    planned_rewards: tuple[Decimal, ...],
) -> CapitalizerR0Metrics | None:
    if not values:
        return None
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return CapitalizerR0Metrics(
        trades=len(values),
        wins=sum(value > 0 for value in values),
        losses=sum(value < 0 for value in values),
        flats=sum(value == 0 for value in values),
        total_gross_r=str(total),
        mean_gross_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if gross_loss == 0 else str(gross_profit / gross_loss),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        median_planned_reward_r=str(median(planned_rewards)),
        median_bars_held=str(median(bars_held)),
        stop_exits=sum(reason == "STOP" for reason in reasons),
        target_exits=sum(reason == "TARGET" for reason in reasons),
        session_exits=sum(reason == "SESSION_EXIT" for reason in reasons),
        ambiguous_stop_first_exits=sum(ambiguities),
    )


def build_market_report(
    *,
    replay_root: Path,
    m5_root: Path,
) -> CapitalizerStrictEntryMarketReport:
    rows = _load_rows(replay_root)
    symbols = {str(row["symbol"]) for row in rows}
    sessions = {str(row["session"]) for row in rows}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("strict entry report requires one market/session")
    symbol = next(iter(symbols))
    session = next(iter(sessions))

    bars = tuple(iter_atlas_m5(m5_root))
    if not bars or bars[0].symbol != symbol:
        raise ValueError("strict entry M5 artifact must match replay symbol")
    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}

    counts = Counter()
    rejection = Counter()
    accepted: list[_AcceptedTrade] = []

    for row in rows:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        confirmation_index = by_open.get(signal_at - BAR_DURATION)
        entry_index = by_open.get(entry_at)
        if confirmation_index is None or entry_index is None:
            raise ValueError("strict entry timestamps must map to exact M5 bars")

        side = CapitalizerSide(str(row["side"]))
        trace = _trace_conditions(
            bars,
            confirmation_index=confirmation_index,
            entry_index=entry_index,
            side=side,
        )
        for field in (
            "liquidity_reference",
            "liquidity_raid",
            "market_structure_shift",
            "significant_displacement",
            "fvg_in_displacement",
            "retrace_into_fvg",
            "anti_chase_entry_inside_fvg",
            "ttrades_cisd_protected_swing",
        ):
            if getattr(trace, field):
                counts[field] += 1
        rejection[trace.rejection_reason] += 1

        if not trace.ttrades_cisd_protected_swing or trace.protected_swing_price is None:
            continue
        counts["accepted_m5_surrogate"] += 1

        entry_price = Decimal(str(row["entry_price"]))
        original_stop = Decimal(str(row["stop_price"]))
        target_price = Decimal(str(row["target_price"]))
        protected_stop = trace.protected_swing_price

        corrected = _lifecycle(
            bars,
            entry_index=entry_index,
            side=side,
            entry_price=entry_price,
            stop_price=protected_stop,
            target_price=target_price,
        )
        original_risk = abs(entry_price - original_stop)
        protected_risk = abs(entry_price - protected_stop)
        if original_risk <= 0 or protected_risk <= 0:
            raise ValueError("strict accepted trade requires positive risk")

        accepted.append(
            _AcceptedTrade(
                entry_at=entry_at,
                baseline_r=Decimal(str(row["realized_gross_r"])),
                corrected_r=corrected.realized_r,
                baseline_reason=str(row["exit_reason"]),
                corrected_reason=corrected.exit_reason,
                baseline_bars=int(row["bars_held"]),
                corrected_bars=corrected.bars_held,
                baseline_ambiguity=bool(row["same_bar_stop_target_ambiguity"]),
                corrected_ambiguity=corrected.same_bar_ambiguity,
                baseline_reward_r=abs(target_price - entry_price) / original_risk,
                corrected_reward_r=abs(target_price - entry_price) / protected_risk,
                stop_width_ratio=protected_risk / original_risk,
            )
        )

    accepted.sort(key=lambda item: item.entry_at)
    baseline_metrics = _metrics_from_values(
        tuple(item.baseline_r for item in accepted),
        reasons=tuple(item.baseline_reason for item in accepted),
        bars_held=tuple(item.baseline_bars for item in accepted),
        ambiguities=tuple(item.baseline_ambiguity for item in accepted),
        planned_rewards=tuple(item.baseline_reward_r for item in accepted),
    )
    corrected_metrics = _metrics_from_values(
        tuple(item.corrected_r for item in accepted),
        reasons=tuple(item.corrected_reason for item in accepted),
        bars_held=tuple(item.corrected_bars for item in accepted),
        ambiguities=tuple(item.corrected_ambiguity for item in accepted),
        planned_rewards=tuple(item.corrected_reward_r for item in accepted),
    )

    total = len(rows)
    funnel = CapitalizerEntryFunnel(
        total_candidates=total,
        liquidity_reference=counts["liquidity_reference"],
        liquidity_raid=counts["liquidity_raid"],
        market_structure_shift=counts["market_structure_shift"],
        significant_displacement=counts["significant_displacement"],
        fvg_in_displacement=counts["fvg_in_displacement"],
        retrace_into_fvg=counts["retrace_into_fvg"],
        anti_chase_entry_inside_fvg=counts["anti_chase_entry_inside_fvg"],
        ttrades_cisd_protected_swing=counts["ttrades_cisd_protected_swing"],
        accepted_m5_surrogate=counts["accepted_m5_surrogate"],
    )
    return CapitalizerStrictEntryMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        funnel=funnel,
        surrogate_acceptance_rate=str(
            Decimal(funnel.accepted_m5_surrogate) / Decimal(total)
        ),
        baseline_matched_metrics=baseline_metrics,
        accepted_corrected_metrics=corrected_metrics,
        median_protected_swing_width_vs_original=(
            None
            if not accepted
            else str(median(item.stop_width_ratio for item in accepted))
        ),
        rejection_reasons=tuple(
            sorted(rejection.items(), key=lambda item: (-item[1], item[0]))
        ),
    )


def write_market_report(
    report: CapitalizerStrictEntryMarketReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-strict-entry-acceptance-replay-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_reports(root: Path) -> tuple[CapitalizerStrictEntryMarketReport, ...]:
    paths = sorted(root.rglob("capitalizer-*-strict-entry-acceptance-replay-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"strict entry matrix requires 9 market reports, got {len(paths)}")
    result: list[CapitalizerStrictEntryMarketReport] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("identity") != IDENTITY:
            raise ValueError("unexpected strict entry report identity")
        result.append(
            CapitalizerStrictEntryMarketReport(
                **{
                    **raw,
                    "funnel": CapitalizerEntryFunnel(**raw["funnel"]),
                    "baseline_matched_metrics": (
                        None
                        if raw["baseline_matched_metrics"] is None
                        else CapitalizerR0Metrics(**raw["baseline_matched_metrics"])
                    ),
                    "accepted_corrected_metrics": (
                        None
                        if raw["accepted_corrected_metrics"] is None
                        else CapitalizerR0Metrics(**raw["accepted_corrected_metrics"])
                    ),
                    "rejection_reasons": tuple(
                        (str(item[0]), int(item[1]))
                        for item in raw["rejection_reasons"]
                    ),
                }
            )
        )
    return tuple(sorted(result, key=lambda item: item.symbol))


def _aggregate_metrics(
    reports: tuple[CapitalizerStrictEntryMarketReport, ...],
    *,
    corrected: bool,
) -> CapitalizerR0Metrics | None:
    # Market reports do not retain trade-level chronology. The aggregate metrics below are
    # therefore additive except DD/streak, which are conservatively reported as the worst
    # market values rather than fabricating cross-market chronology.
    metrics = tuple(
        (
            report.accepted_corrected_metrics
            if corrected
            else report.baseline_matched_metrics
        )
        for report in reports
    )
    metrics = tuple(item for item in metrics if item is not None)
    if not metrics:
        return None

    trades = sum(item.trades for item in metrics)
    gross_profit = sum((Decimal(item.gross_profit_r) for item in metrics), Decimal("0"))
    gross_loss = sum((Decimal(item.gross_loss_r) for item in metrics), Decimal("0"))
    total = sum((Decimal(item.total_gross_r) for item in metrics), Decimal("0"))
    planned = tuple(Decimal(item.median_planned_reward_r) for item in metrics)
    held = tuple(Decimal(item.median_bars_held) for item in metrics)
    return CapitalizerR0Metrics(
        trades=trades,
        wins=sum(item.wins for item in metrics),
        losses=sum(item.losses for item in metrics),
        flats=sum(item.flats for item in metrics),
        total_gross_r=str(total),
        mean_gross_r=str(total / Decimal(trades)),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if gross_loss == 0 else str(gross_profit / gross_loss),
        max_drawdown_r=str(max(Decimal(item.max_drawdown_r) for item in metrics)),
        max_losing_streak=max(item.max_losing_streak for item in metrics),
        median_planned_reward_r=str(median(planned)),
        median_bars_held=str(median(held)),
        stop_exits=sum(item.stop_exits for item in metrics),
        target_exits=sum(item.target_exits for item in metrics),
        session_exits=sum(item.session_exits for item in metrics),
        ambiguous_stop_first_exits=sum(
            item.ambiguous_stop_first_exits for item in metrics
        ),
    )


def build_matrix(root: Path) -> CapitalizerStrictEntryMatrix:
    reports = _load_reports(root)
    expected = {
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "USDCAD",
        "USDJPY",
        "XAUUSD",
    }
    if {item.symbol for item in reports} != expected:
        raise ValueError("strict entry replay universe mismatch")

    total = sum(item.funnel.total_candidates for item in reports)
    accepted = sum(item.funnel.accepted_m5_surrogate for item in reports)
    reasons: Counter[str] = Counter()
    for report in reports:
        reasons.update(dict(report.rejection_reasons))

    return CapitalizerStrictEntryMatrix(
        identity=MATRIX_IDENTITY,
        markets=reports,
        complete_nine_market_universe=True,
        total_candidates=total,
        accepted_m5_surrogate=accepted,
        surrogate_acceptance_rate=str(Decimal(accepted) / Decimal(total)),
        aggregate_baseline_matched_metrics=_aggregate_metrics(
            reports,
            corrected=False,
        ),
        aggregate_accepted_corrected_metrics=_aggregate_metrics(
            reports,
            corrected=True,
        ),
        aggregate_rejection_reasons=tuple(
            sorted(reasons.items(), key=lambda item: (-item[1], item[0]))
        ),
    )


def write_matrix(report: CapitalizerStrictEntryMatrix, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-strict-entry-acceptance-replay-v1.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# QORE Capitalizer — Strict Entry Acceptance Replay V1",
        "",
        "- Trader entry gate is integrated fail-closed before QORE Risk.",
        "- This replay is an M5 causal surrogate, not full H1->M15->M1 source fidelity.",
        "- Full dual-source pass count remains 0 until native M1/finer evidence exists.",
        "",
        "| Market | Candidates | Accepted M5 surrogate | Acceptance | PF before | PF strict+PS | DD before | DD strict+PS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for market in report.markets:
        base = market.baseline_matched_metrics
        strict = market.accepted_corrected_metrics
        lines.append(
            f"| {market.symbol} | {market.funnel.total_candidates} | "
            f"{market.funnel.accepted_m5_surrogate} | "
            f"{Decimal(market.surrogate_acceptance_rate) * 100:.2f}% | "
            f"{'-' if base is None else base.profit_factor} | "
            f"{'-' if strict is None else strict.profit_factor} | "
            f"{'-' if base is None else base.max_drawdown_r + 'R'} | "
            f"{'-' if strict is None else strict.max_drawdown_r + 'R'} |"
        )
    lines.extend(
        [
            "",
            f"- Total candidates: {report.total_candidates}",
            f"- Accepted M5 surrogate: {report.accepted_m5_surrogate}",
            f"- Acceptance rate: {Decimal(report.surrogate_acceptance_rate) * 100:.2f}%",
            "",
            "## Rejection funnel",
            "",
        ]
    )
    lines.extend(
        f"- {reason}: {count}"
        for reason, count in report.aggregate_rejection_reasons
    )
    (output / "capitalizer-nine-market-strict-entry-acceptance-replay-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer strict ICT+TTrades entry acceptance replay"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("m5_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report = build_market_report(replay_root=args.replay_root, m5_root=args.m5_root)
        write_market_report(report, args.output)
        print(json.dumps(asdict(report), sort_keys=True))
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(
        json.dumps(
            {
                "identity": matrix_report.identity,
                "total_candidates": matrix_report.total_candidates,
                "accepted_m5_surrogate": matrix_report.accepted_m5_surrogate,
                "surrogate_acceptance_rate": matrix_report.surrogate_acceptance_rate,
                "full_dual_source_entry_pass_count": (
                    matrix_report.full_dual_source_entry_pass_count
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
