"""VT08 Index R46 — recent-2Y failure forensics / cross-window transport.

Diagnostic only. R46 reconstructs the exact frozen R44/R43 identity on the
consumed five-year and recent two-year windows and compares *causal pre-entry*
state. It does not tune, suppress, resize, promote, or authorize a candidate.

The key invariant is that every predictor in the feature matrix is available
at or before the signal timestamp. Outcome columns are labels only.
"""

from __future__ import annotations

import argparse
import heapq
import json
from collections import defaultdict, deque
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as r17
from qore.infrastructure.trader_lab import vt08_index_r22_concurrent_stable_formation as r22
from qore.infrastructure.trader_lab import vt08_index_r24_open_position_pressure as r24
from qore.infrastructure.trader_lab import vt08_index_r25_r23_failure_forensics as r25
from qore.infrastructure.trader_lab import vt08_index_r26_formation_health_governor as r26
from qore.infrastructure.trader_lab import vt08_index_r29_candidate_freeze as r29
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import vt08_index_r33_causal_poi_health_governor as r33
from qore.infrastructure.trader_lab import vt08_index_r34_hybrid_formation_poi_health as r34
from qore.infrastructure.trader_lab import vt08_index_r35_five_year_temporal_contract as r35
from qore.infrastructure.trader_lab import vt08_index_r42_hierarchical_nas100_prior as r42
from qore.infrastructure.trader_lab import vt08_index_r43_sp500_long_stability_prior as r43
from qore.infrastructure.trader_lab import vt08_index_r44_candidate_freeze as freeze
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r46_cross_window_transport_forensics.v1"
IDENTITY = "VT08_INDEX_R46_CROSS_WINDOW_TRANSPORT_FORENSICS_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
MIN_COHORT_SAMPLE = 20
_NY = ZoneInfo("America/New_York")


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator > 0 else Decimal()


def _range_state(value: Decimal) -> str:
    if value < Decimal("0.80"):
        return "compressed"
    if value > Decimal("1.20"):
        return "expanded"
    return "normal"


def _body_sign(bar: Vt08IndexC2R1Bar) -> int:
    return (bar.close > bar.open) - (bar.close < bar.open)


def _aligned(bar: Vt08IndexC2R1Bar, side_value: str) -> bool:
    wanted = 1 if side_value == "long" else -1
    return _body_sign(bar) == wanted


def _loss_cluster(loss_streak: int) -> str:
    if loss_streak <= 0:
        return "L0"
    if loss_streak == 1:
        return "L1"
    if loss_streak <= 3:
        return "L2_3"
    return "L4_PLUS"


def _pressure_bucket(active_count: int, active_risk: Decimal) -> str:
    if active_count == 0:
        return "NONE"
    if active_risk <= Decimal("0.25"):
        return "LOW"
    if active_risk <= Decimal("0.50"):
        return "MEDIUM"
    return "HIGH"


def _governor_state(*, warn: bool, hard: bool, loss: bool) -> str:
    rows: list[str] = []
    if hard:
        rows.append("HARD_DD")
    elif warn:
        rows.append("WARN_DD")
    if loss:
        rows.append("LOSS_DEFENSE")
    return "+".join(rows) if rows else "NORMAL"


def _minutes(a: datetime, b: datetime) -> int:
    return max(0, int((a.astimezone(UTC) - b.astimezone(UTC)).total_seconds() // 60))


def _latest_completed_h4(
    h4: dict[datetime, Vt08IndexC2R1Bar],
    *,
    decision: datetime,
    count: int,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    rows = [
        h4[key]
        for key in sorted(h4)
        if h4[key].closed_at.astimezone(UTC) <= decision.astimezone(UTC)
    ]
    return tuple(rows[-count:])


def _cross_index_state(
    *,
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    decision: datetime,
    side_value: str,
) -> str:
    wanted = 1 if side_value == "long" else -1
    signs: list[int] = []
    for symbol in contract.MARKETS:
        rows = _latest_completed_h4(
            h4_by_symbol[symbol],
            decision=decision,
            count=1,
        )
        if not rows:
            continue
        signs.append(_body_sign(rows[-1]))
    if len(signs) != len(contract.MARKETS):
        return "insufficient"
    if all(value == wanted for value in signs):
        return "unanimous_with_side"
    if all(value == -wanted for value in signs):
        return "unanimous_against_side"
    return "mixed"


def _closure_reference_state(
    opportunity: r4.ExpandedOpportunity,
    *,
    h4: dict[datetime, Vt08IndexC2R1Bar],
) -> tuple[str, str]:
    signal = opportunity.signal
    model = signal.model_kind.value
    if model == "same-c2-intracandle":
        return "same_c2_live", "NA"
    rows = _latest_completed_h4(
        h4,
        decision=signal.signal_at,
        count=3,
    )
    if len(rows) < 2:
        return "insufficient", "0"
    closure = rows[-1]
    if model == "c3-closure-next-h4-expansion" and len(rows) >= 3:
        reference = rows[-3]
    else:
        reference = rows[-2]
    ratio = _ratio(closure.high - closure.low, reference.high - reference.low)
    return _range_state(ratio), str(ratio)


def _daily_context(
    opportunity: r4.ExpandedOpportunity,
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
) -> dict[str, str]:
    signal = opportunity.signal
    source_days = v7._latest_complete_source_days(
        indexed,
        before_local=signal.h4_opened_at.astimezone(_NY),
    )
    if source_days is None:
        return {
            "source_day_relationship": "insufficient",
            "previous_source_day_body_alignment": "insufficient",
            "current_source_day_body_alignment": "insufficient",
            "recent_daily_range_state": "insufficient",
            "recent_daily_range_ratio": "0",
        }
    previous_day, current_day = source_days
    relationship = (
        "breakout"
        if current_day.close > previous_day.high
        or current_day.close < previous_day.low
        else "reversal"
    )
    ratio = _ratio(
        current_day.high - current_day.low,
        previous_day.high - previous_day.low,
    )
    return {
        "source_day_relationship": relationship,
        "previous_source_day_body_alignment": (
            "aligned"
            if _aligned(previous_day, signal.side.value)
            else "opposed"
        ),
        "current_source_day_body_alignment": (
            "aligned"
            if _aligned(current_day, signal.side.value)
            else "opposed"
        ),
        "recent_daily_range_state": _range_state(ratio),
        "recent_daily_range_ratio": str(ratio),
    }


def _h4_context(
    opportunity: r4.ExpandedOpportunity,
    *,
    h4: dict[datetime, Vt08IndexC2R1Bar],
) -> dict[str, str]:
    rows = _latest_completed_h4(
        h4,
        decision=opportunity.signal.signal_at,
        count=3,
    )
    if len(rows) < 3:
        return {
            "recent_h4_range_state": "insufficient",
            "recent_h4_range_ratio": "0",
        }
    latest_range = rows[-1].high - rows[-1].low
    baseline = Decimal(str(median([rows[-2].high - rows[-2].low, rows[-3].high - rows[-3].low])))
    ratio = _ratio(latest_range, baseline)
    return {
        "recent_h4_range_state": _range_state(ratio),
        "recent_h4_range_ratio": str(ratio),
    }


def _causal_trace(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
) -> tuple[dict[str, Any], ...]:
    """Replay the exact R34 causal allocator and record pre-entry state."""

    formation = r29.frozen_formation_health_profile()
    overlay = r43.BASE_POI_OVERLAY
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=r24.BASE_RISK.rolling_trades + 1,
    )
    tier_histories: dict[str, deque[Decimal]] = {
        tier: deque(maxlen=formation.rolling_tier_trades)
        for tier in r26.ADAPTIVE_TIERS
    }
    poi_histories: dict[str, deque[Decimal]] = {
        family: deque(maxlen=overlay.rolling_family_trades)
        for family in r33.POI_FAMILIES
    }
    loss_streak = 0
    exit_heap: list[tuple[datetime, int, Decimal, str, str, Decimal]] = []
    active: dict[int, tuple[Decimal, str]] = {}
    traces: list[dict[str, Any]] = []
    cursor = 0
    next_trade_id = 0

    def settle(until: datetime) -> None:
        nonlocal equity, loss_streak
        while exit_heap and exit_heap[0][0] <= until:
            (
                _exit_at,
                trade_id,
                weighted_value,
                tier,
                family,
                raw_value,
            ) = heapq.heappop(exit_heap)
            active.pop(trade_id, None)
            equity += weighted_value
            history.append(equity)
            loss_streak = loss_streak + 1 if weighted_value < 0 else 0
            if tier in tier_histories:
                tier_histories[tier].append(raw_value)
            poi_histories[family].append(raw_value)

    while cursor < len(stream):
        batch_time = stream[cursor][0].signal.signal_at.astimezone(UTC)
        settle(batch_time)
        end = cursor + 1
        while (
            end < len(stream)
            and stream[end][0].signal.signal_at.astimezone(UTC) == batch_time
        ):
            end += 1
        batch = stream[cursor:end]

        dd_before = max(history) - equity
        active_risk = sum((item[0] for item in active.values()), Decimal())
        active_count = len(active)
        requested: list[Decimal] = []
        metadata: list[dict[str, Any]] = []

        for opportunity, _outcome in batch:
            tier = r25._quality_tier(opportunity)
            family = str(opportunity.source_poi_kind)
            weight = r22._quality_weight(opportunity, r24.BASE_QUALITY)

            tier_state = "STATIC"
            if tier in tier_histories:
                tier_mult, tier_state = r26._health_multiplier(
                    tuple(tier_histories[tier]),
                    profile=formation,
                )
                weight *= tier_mult

            poi_mult, poi_state = r34._health(
                tuple(poi_histories[family]),
                minimum=overlay.min_observations,
                cold=overlay.cold_multiplier,
                weak=overlay.weak_multiplier,
                threshold=overlay.healthy_mean_threshold_r,
            )
            weight *= poi_mult

            warn = hard = loss = False
            if dd_before >= r24.BASE_RISK.hard_dd_r:
                weight *= r24.BASE_RISK.hard_multiplier
                hard = True
            elif dd_before >= r24.BASE_RISK.warn_dd_r:
                weight *= r24.BASE_RISK.warn_multiplier
                warn = True
            if loss_streak >= 2:
                weight *= r24.BASE_RISK.loss_multiplier
                loss = True

            requested.append(max(r34.MIN_EFFECTIVE_WEIGHT, weight))
            same_side = sum(
                active_side == opportunity.signal.side.value
                for _active_weight, active_side in active.values()
            )
            metadata.append(
                {
                    "formation_tier": tier,
                    "formation_health_state": tier_state,
                    "poi_health_state": poi_state,
                    "dd_before_r": str(dd_before),
                    "loss_streak_before": loss_streak,
                    "loss_cluster": _loss_cluster(loss_streak),
                    "active_count_before": active_count,
                    "active_risk_before_r": str(active_risk),
                    "same_side_open_before": same_side,
                    "concurrent_pressure": _pressure_bucket(
                        active_count,
                        active_risk,
                    ),
                    "governor_state": _governor_state(
                        warn=warn,
                        hard=hard,
                        loss=loss,
                    ),
                }
            )

        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=r24.BASE_RISK.portfolio_risk_budget_r,
        )

        for ((opportunity, outcome), weight, meta) in zip(
            batch,
            weights,
            metadata,
            strict=True,
        ):
            trace = dict(meta)
            trace["base_r34_weight"] = str(weight)
            trace["budget_scaled_batch"] = scaled
            traces.append(trace)
            raw_value = outcome.r_multiple - PRIMARY_STRESS
            weighted_value = raw_value * weight
            active[next_trade_id] = (weight, opportunity.signal.side.value)
            heapq.heappush(
                exit_heap,
                (
                    outcome.exited_at.astimezone(UTC),
                    next_trade_id,
                    weighted_value,
                    str(meta["formation_tier"]),
                    str(opportunity.source_poi_kind),
                    raw_value,
                ),
            )
            next_trade_id += 1

        cursor = end

    settle(datetime.max.replace(tzinfo=UTC))
    if len(traces) != len(stream):
        raise ValueError("R46 causal trace changed source-complete sample")
    return tuple(traces)


def _frozen_assignment(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
) -> tuple[tuple[r15.AssignedTrade, ...], tuple[dict[str, Any], ...]]:
    _base_row, base_assigned = r34._row(
        stream,
        overlay=r43.BASE_POI_OVERLAY,
    )
    trace = _causal_trace(stream)
    for item, state in zip(base_assigned, trace, strict=True):
        if item.weight != Decimal(str(state["base_r34_weight"])):
            raise ValueError("R46 trace drifted from exact R34 assignment")
    r42_assigned, _r42_diagnostics = r42._apply_prior(base_assigned)
    final_assigned, _r43_diagnostics = r43._apply_sp500_long_prior(r42_assigned)
    return final_assigned, trace


def _period_id(window_id: str, item: r15.AssignedTrade) -> str:
    exited = item.exited_at.astimezone(_NY).date()
    if window_id == "5Y":
        boundaries = r35._annual_boundaries()
        for index in range(5):
            if boundaries[index] <= exited < boundaries[index + 1]:
                return f"Y{index + 1}"
        return "OUTSIDE"
    boundaries = (
        r45.START_DATE,
        date(2025, 9, 15),
        r45.END_DATE_EXCLUSIVE,
    )
    for index in range(2):
        if boundaries[index] <= exited < boundaries[index + 1]:
            return f"Y{index + 1}"
    return "OUTSIDE"


def _feature_row(
    item: r15.AssignedTrade,
    *,
    state: dict[str, Any],
    window_id: str,
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    h4_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    opportunity = item.opportunity
    signal = opportunity.signal
    base = r17._feature_values(opportunity)
    daily = _daily_context(
        opportunity,
        indexed=indexed_by_symbol[item.symbol],
    )
    h4_context = _h4_context(
        opportunity,
        h4=h4_by_symbol[item.symbol],
    )
    expansion_state, expansion_ratio = _closure_reference_state(
        opportunity,
        h4=h4_by_symbol[item.symbol],
    )
    risk = abs(signal.entry - signal.stop)
    cisd_latency_bars = _minutes(
        signal.cisd_confirmed_at,
        opportunity.poi_touch_at,
    ) // 15
    continuation_latency_bars = _minutes(
        signal.signal_at,
        signal.cisd_confirmed_at,
    ) // 15
    h4_entry_latency_minutes = _minutes(
        signal.signal_at,
        signal.h4_opened_at,
    )

    return {
        "window_id": window_id,
        "period_id": _period_id(window_id, item),
        "symbol": item.symbol,
        "timestamp": signal.signal_at.astimezone(UTC).isoformat(),
        "exit_timestamp": item.exited_at.astimezone(UTC).isoformat(),
        "anchor": str(signal.h4_opened_at.astimezone(_NY).hour),
        "side": signal.side.value,
        "market_side": f"{item.symbol}|{signal.side.value}",
        "poi": str(opportunity.source_poi_kind),
        "market_poi": f"{item.symbol}|{opportunity.source_poi_kind}",
        "side_poi": f"{signal.side.value}|{opportunity.source_poi_kind}",
        "market_side_poi": (
            f"{item.symbol}|{signal.side.value}|{opportunity.source_poi_kind}"
        ),
        "model_kind": signal.model_kind.value,
        "rearm": "REARM" if int(opportunity.rearm_index) > 0 else "INITIAL",
        "formation_tier": state["formation_tier"],
        "formation_health_state": state["formation_health_state"],
        "poi_health_state": state["poi_health_state"],
        "source_day_relationship": daily["source_day_relationship"],
        "previous_source_day_body_alignment": daily[
            "previous_source_day_body_alignment"
        ],
        "current_source_day_body_alignment": daily[
            "current_source_day_body_alignment"
        ],
        "risk_fraction_bucket": base["risk_fraction"],
        "risk_fraction": str(_ratio(risk, signal.entry)),
        "protected_swing_to_cisd_fraction": str(
            _ratio(abs(signal.cisd_level - signal.protected_swing_extreme), signal.entry)
        ),
        "cisd_latency_bucket": base["cisd_latency"],
        "cisd_latency_m15": cisd_latency_bars,
        "continuation_latency_bucket": base["continuation_latency"],
        "continuation_latency_m15": continuation_latency_bars,
        "h4_entry_latency_bucket": base["h4_entry_latency"],
        "h4_entry_latency_minutes": h4_entry_latency_minutes,
        "poi_age_bucket": base["poi_age"],
        "closure_reference_expansion_state": expansion_state,
        "closure_reference_range_ratio": expansion_ratio,
        "recent_h4_range_state": h4_context["recent_h4_range_state"],
        "recent_h4_range_ratio": h4_context["recent_h4_range_ratio"],
        "recent_daily_range_state": daily["recent_daily_range_state"],
        "recent_daily_range_ratio": daily["recent_daily_range_ratio"],
        "cross_index_state": _cross_index_state(
            h4_by_symbol=h4_by_symbol,
            decision=signal.signal_at,
            side_value=signal.side.value,
        ),
        "concurrent_pressure": state["concurrent_pressure"],
        "active_count_before": state["active_count_before"],
        "active_risk_before_r": state["active_risk_before_r"],
        "same_side_open_before": state["same_side_open_before"],
        "loss_cluster": state["loss_cluster"],
        "loss_streak_before": state["loss_streak_before"],
        "governor_state": state["governor_state"],
        "budget_scaled_batch": state["budget_scaled_batch"],
        "base_r34_weight": state["base_r34_weight"],
        "effective_weight": str(item.weight),
        "outcome_r": str(item.outcome.r_multiple),
    }


def _feature_rows(
    *,
    assigned: Sequence[r15.AssignedTrade],
    trace: Sequence[dict[str, Any]],
    window_id: str,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> list[dict[str, Any]]:
    indexed_by_symbol = {
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }
    h4_by_symbol = {
        symbol: v6._build_h4(indexed)
        for symbol, indexed in indexed_by_symbol.items()
    }
    return [
        _feature_row(
            item,
            state=state,
            window_id=window_id,
            indexed_by_symbol=indexed_by_symbol,
            h4_by_symbol=h4_by_symbol,
        )
        for item, state in zip(assigned, trace, strict=True)
    ]


def _metrics_rows(
    rows: Sequence[dict[str, Any]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["exit_timestamp"]),
            str(row["symbol"]),
            str(row["timestamp"]),
        ),
    )
    values = tuple(
        (Decimal(str(row["outcome_r"])) - stress)
        * Decimal(str(row["effective_weight"]))
        for row in ordered
    )
    return fx._metrics(values)


def _breakdown(
    rows: Sequence[dict[str, Any]],
    *,
    key: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {
        label: {
            "primary": _metrics_rows(items, stress=PRIMARY_STRESS),
            "secondary": _metrics_rows(items, stress=SECONDARY_STRESS),
        }
        for label, items in sorted(groups.items())
    }


def _period_breakdown(
    rows: Sequence[dict[str, Any]],
    *,
    key: str,
) -> dict[str, Any]:
    groups: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        groups[str(row[key])][str(row["period_id"])].append(row)
    result: dict[str, Any] = {}
    for label, periods in sorted(groups.items()):
        result[label] = {
            period: {
                "primary": _metrics_rows(items, stress=PRIMARY_STRESS),
                "secondary": _metrics_rows(items, stress=SECONDARY_STRESS),
            }
            for period, items in sorted(periods.items())
            if period != "OUTSIDE"
        }
    return result


def _transport_table(
    *,
    five: dict[str, Any],
    two: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in sorted(set(five) & set(two)):
        f = five[label]["secondary"]
        t = two[label]["secondary"]
        fs = int(f["sample"])
        ts = int(t["sample"])
        if not fs or not ts:
            continue
        fm = Decimal(str(f["mean_r"]))
        tm = Decimal(str(t["mean_r"]))
        ft = Decimal(str(f["total_r"]))
        tt = Decimal(str(t["total_r"]))
        rows.append(
            {
                "label": label,
                "five_year_sample": fs,
                "two_year_sample": ts,
                "five_year_secondary_pf": f["profit_factor"],
                "two_year_secondary_pf": t["profit_factor"],
                "five_year_secondary_total_r": str(ft),
                "two_year_secondary_total_r": str(tt),
                "five_year_secondary_mean_r": str(fm),
                "two_year_secondary_mean_r": str(tm),
                "mean_transport_delta_r": str(tm - fm),
                "positive_5y_negative_2y": ft > 0 and tt < 0,
                "minimum_sample_pass": min(fs, ts) >= MIN_COHORT_SAMPLE,
            }
        )
    rows.sort(
        key=lambda row: (
            Decimal(str(row["mean_transport_delta_r"])),
            -min(int(row["five_year_sample"]), int(row["two_year_sample"])),
        )
    )
    return rows


def _recent_y1_drags(
    breakdown: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, periods in breakdown.items():
        y1 = periods.get("Y1")
        if not y1:
            continue
        metrics = y1["secondary"]
        sample = int(metrics["sample"])
        total = Decimal(str(metrics["total_r"]))
        if sample >= 10 and total < 0:
            rows.append(
                {
                    "label": label,
                    "sample": sample,
                    "secondary_total_r": str(total),
                    "secondary_pf": metrics["profit_factor"],
                    "secondary_mean_r": metrics["mean_r"],
                }
            )
    rows.sort(key=lambda row: Decimal(str(row["secondary_total_r"])))
    return rows


DIMENSIONS = (
    "symbol",
    "side",
    "market_side",
    "poi",
    "market_poi",
    "side_poi",
    "market_side_poi",
    "anchor",
    "model_kind",
    "rearm",
    "formation_tier",
    "formation_health_state",
    "poi_health_state",
    "source_day_relationship",
    "previous_source_day_body_alignment",
    "current_source_day_body_alignment",
    "risk_fraction_bucket",
    "cisd_latency_bucket",
    "continuation_latency_bucket",
    "h4_entry_latency_bucket",
    "poi_age_bucket",
    "closure_reference_expansion_state",
    "recent_h4_range_state",
    "recent_daily_range_state",
    "cross_index_state",
    "concurrent_pressure",
    "loss_cluster",
    "governor_state",
)


def _window(
    *,
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> dict[str, Any]:
    assigned, trace = _frozen_assignment(stream)
    rows = _feature_rows(
        assigned=assigned,
        trace=trace,
        window_id=window_id,
        bars_by_symbol=bars_by_symbol,
    )
    return {
        "sample": len(rows),
        "primary": _metrics_rows(rows, stress=PRIMARY_STRESS),
        "secondary": _metrics_rows(rows, stress=SECONDARY_STRESS),
        "rows": rows,
        "breakdowns": {
            dimension: _breakdown(rows, key=dimension)
            for dimension in DIMENSIONS
        },
        "period_breakdowns": {
            dimension: _period_breakdown(rows, key=dimension)
            for dimension in DIMENSIONS
        },
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R46 frozen R44 dependency contract drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    if len(five_stream) != freeze.FIVE_YEAR_SAMPLE:
        raise ValueError(f"R46 5Y sample drift: {len(five_stream)}")
    if not contract.validates_trade_count(years=2, sample=len(two_stream)):
        raise ValueError(f"R46 2Y density drift: {len(two_stream)}")

    five = _window(
        stream=five_stream,
        bars_by_symbol={k: tuple(v) for k, v in five_bars.items()},
        window_id="5Y",
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol={k: tuple(v) for k, v in two_bars.items()},
        window_id="2Y",
    )

    transport = {
        dimension: _transport_table(
            five=five["breakdowns"][dimension],
            two=two["breakdowns"][dimension],
        )
        for dimension in DIMENSIONS
    }
    recent_y1_drags = {
        dimension: _recent_y1_drags(two["period_breakdowns"][dimension])
        for dimension in DIMENSIONS
    }
    strongest_breaks = [
        {"dimension": dimension, **row}
        for dimension, rows in transport.items()
        for row in rows
        if bool(row["positive_5y_negative_2y"])
        and bool(row["minimum_sample_pass"])
    ]
    strongest_breaks.sort(
        key=lambda row: (
            Decimal(str(row["mean_transport_delta_r"])),
            -min(int(row["five_year_sample"]), int(row["two_year_sample"])),
        )
    )

    y1_drags = [
        {"dimension": dimension, **row}
        for dimension, rows in recent_y1_drags.items()
        for row in rows[:12]
    ]
    y1_drags.sort(key=lambda row: Decimal(str(row["secondary_total_r"])))

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.RULE_FINGERPRINT,
            "rules_changed": False,
            "retuning_performed": False,
        },
        "five_year": {
            "sample": five["sample"],
            "primary": five["primary"],
            "secondary": five["secondary"],
            "breakdowns": five["breakdowns"],
            "period_breakdowns": five["period_breakdowns"],
            "feature_matrix": five["rows"],
        },
        "recent_two_year": {
            "sample": two["sample"],
            "primary": two["primary"],
            "secondary": two["secondary"],
            "breakdowns": two["breakdowns"],
            "period_breakdowns": two["period_breakdowns"],
            "feature_matrix": two["rows"],
        },
        "transport": transport,
        "strongest_positive_5y_to_negative_2y_breaks": strongest_breaks[:60],
        "recent_y1_largest_secondary_drags": y1_drags[:60],
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "frozen_candidate_reconstructed_exactly": True,
            "all_predictors_known_at_or_before_entry": True,
            "post_entry_outcome_used_as_predictor": False,
            "calendar_or_year_used_as_runtime_feature": False,
            "cohort_to_rule_automatic": False,
            "optimization_grid_used": False,
            "signal_suppression_performed": False,
            "risk_retuning_performed": False,
            "candidate_created": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "candidate": report["candidate"],
                "five_year": {
                    "sample": report["five_year"]["sample"],
                    "primary": report["five_year"]["primary"],
                    "secondary": report["five_year"]["secondary"],
                },
                "recent_two_year": {
                    "sample": report["recent_two_year"]["sample"],
                    "primary": report["recent_two_year"]["primary"],
                    "secondary": report["recent_two_year"]["secondary"],
                },
                "strongest_breaks": report[
                    "strongest_positive_5y_to_negative_2y_breaks"
                ][:20],
                "recent_y1_drags": report[
                    "recent_y1_largest_secondary_drags"
                ][:20],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
