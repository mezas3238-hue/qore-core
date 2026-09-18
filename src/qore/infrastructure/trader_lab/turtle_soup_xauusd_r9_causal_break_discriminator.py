"""Causal discriminator research for Turtle Soup XAUUSD structural breaks.

Research only. R9 starts from the frozen R7 retained population and the two
pre-registered R8 structural-break families. It expands pre-entry journey
instrumentation at continuous resolution so historically valid and recently
invalid instances can be compared without using year/date as an operating
feature and without mining a return-maximising threshold.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r2_cibo_full as r2
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r7_structural_abstention_lab as r7
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r8_structural_break_counterfactual as r8
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Side,
    SourceCandle,
    build_h1,
    build_h4,
    causal_cisd,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R9_CAUSAL_BREAK_DISCRIMINATOR_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_CAUSAL_BREAK_DISCRIMINATOR_NOT_FRESH_HOLDOUT"

EARLY_YEARS = frozenset(range(2016, 2021))
TRANSITION_YEARS = frozenset({2021, 2022, 2023})
HISTORICAL_YEARS = EARLY_YEARS | TRANSITION_YEARS
RECENT_YEARS = frozenset({2024, 2025, 2026})

CONTINUOUS_FEATURES = (
    "raid_depth_abs",
    "raid_depth_bps",
    "raid_depth_source_fraction",
    "raid_depth_prior20_source_fraction",
    "prior_equal_touch_count",
    "raid_violation_bars_to_cisd",
    "reclaim_latency_minutes",
    "reclaim_fraction_of_sweep",
    "reclaim_overshoot_source_fraction",
    "raid_to_cisd_minutes",
    "reclaim_to_cisd_minutes",
    "cisd_progress_exact",
    "cisd_displacement_abs",
    "cisd_displacement_source_fraction",
    "cisd_displacement_lower_range_fraction",
    "cisd_confirmation_range_source_fraction",
    "opposing_series_length",
    "protected_risk_abs",
    "protected_risk_bps",
    "protected_risk_source_fraction_exact",
    "protected_risk_h1_fraction",
    "protected_risk_h4_fraction",
    "protected_risk_d1_fraction",
    "protected_swing_age_minutes",
    "protected_swing_confirmation_minutes",
    "ps_distance_from_liquidity_source_fraction",
    "active_dol_count",
    "active_dol_family_count",
    "selected_dol_rank",
    "nearer_dol_count",
    "selected_dol_age_minutes",
    "dol_distance_abs",
    "dol_distance_bps",
    "dol_distance_source_fraction",
    "dol_distance_h4_fraction",
    "dol_distance_d1_fraction",
    "d1_prior_range_vs20_exact",
    "d1_range_5v20_exact",
    "d1_efficiency_5_exact",
    "d1_efficiency_20_exact",
    "d1_location_20_exact",
    "d1_reversal_edge_20_exact",
    "h4_range_3v20_exact",
    "h4_efficiency_6_exact",
    "h4_efficiency_20_exact",
    "h4_location_20_exact",
    "h4_reversal_edge_20_exact",
    "prior_d1_body_fraction",
    "prior_h4_body_fraction",
)

CATEGORICAL_FEATURES = (
    "side",
    "source_timeframe",
    "entry_mode",
    "target_route",
    "target_kind",
    "target_timeframe",
    "prior_body_alignment",
    "liquidity_pristine_before_raid",
    "prior_d1_body_alignment",
    "prior_h4_body_alignment",
    "h4_trend_state_20",
    "d1_trend_state_20",
)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _safe_ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _minutes(left: datetime, right: datetime) -> Decimal:
    return Decimal(str((right - left).total_seconds())) / Decimal(60)


def _iso_year(row: Mapping[str, Any]) -> int:
    return datetime.fromisoformat(str(row["entry_at"])).year


def _percentile(values: Sequence[Decimal], numerator: int, denominator: int) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = Decimal(len(ordered) - 1) * Decimal(numerator) / Decimal(denominator)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _describe(rows: Sequence[dict[str, Any]], feature: str) -> dict[str, Any]:
    values = [_d(row[feature]) for row in rows if row.get(feature) is not None]
    if not values:
        return {
            "n": 0,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
            "mean": None,
        }
    total = sum(values, Decimal(0))
    return {
        "n": len(values),
        "min": str(min(values)),
        "p25": str(_percentile(values, 1, 4)),
        "median": str(_percentile(values, 1, 2)),
        "p75": str(_percentile(values, 3, 4)),
        "max": str(max(values)),
        "mean": str(total / len(values)),
    }


def _stat(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = [_d(row["primary_net_r"]) for row in rows]
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    return {
        "trades": len(rows),
        "total_primary_r": str(total),
        "mean_primary_r": str(total / len(rows)) if rows else None,
        "profit_factor": str(gross_profit / gross_loss) if gross_loss > 0 else None,
        "target_rate": (
            str(Decimal(sum(1 for row in rows if "TARGET" in str(row["exit_reason"]))) / len(rows))
            if rows
            else None
        ),
        "stop_rate": (
            str(Decimal(sum(1 for row in rows if "STOP" in str(row["exit_reason"]))) / len(rows))
            if rows
            else None
        ),
    }


def _period(rows: Sequence[dict[str, Any]], years: frozenset[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _body_alignment(bar: Any | None, side: str) -> str:
    if bar is None:
        return "missing"
    if bar.close == bar.open:
        return "doji"
    with_trade = bar.close > bar.open if side == "long" else bar.close < bar.open
    return "with_trade" if with_trade else "against_trade"


def _body_fraction(bar: Any | None) -> Decimal | None:
    if bar is None:
        return None
    span = _d(bar.high) - _d(bar.low)
    if span <= 0:
        return None
    return abs(_d(bar.close) - _d(bar.open)) / span


def _prior_completed_source(
    candles: Sequence[SourceCandle],
    opens: Sequence[datetime],
    at: datetime,
) -> SourceCandle | None:
    pos = bisect.bisect_left(opens, at) - 1
    if pos < 0:
        return None
    candle = candles[pos]
    return candle if candle.closed_at <= at else (candles[pos - 1] if pos > 0 else None)


def _source_range(candle: Any | None) -> Decimal | None:
    if candle is None:
        return None
    value = _d(candle.high) - _d(candle.low)
    return value if value > 0 else None


def _first_reclaim_bar(c2: SourceCandle, c1: SourceCandle, side: Side, raid_at: datetime) -> Any | None:
    level = c1.low if side is Side.LONG else c1.high
    for bar in c2.m5:
        if bar.opened_at < raid_at:
            continue
        reclaimed = bar.close > level if side is Side.LONG else bar.close < level
        if reclaimed:
            return bar
    return None


def _prior_equal_touches(c2: SourceCandle, c1: SourceCandle, side: Side, raid_at: datetime) -> int:
    level = c1.low if side is Side.LONG else c1.high
    return sum(
        1
        for bar in c2.m5
        if bar.opened_at < raid_at
        and ((bar.low <= level) if side is Side.LONG else (bar.high >= level))
    )


def _violation_bars_to_cisd(c2: SourceCandle, c1: SourceCandle, side: Side, raid_at: datetime, cisd_at: datetime) -> int:
    level = c1.low if side is Side.LONG else c1.high
    return sum(
        1
        for bar in c2.m5
        if raid_at <= bar.opened_at < cisd_at
        and ((bar.low < level) if side is Side.LONG else (bar.high > level))
    )


def _lower_confirmation(setup: r3.Setup) -> tuple[Any, Any]:
    signal = setup.context.signal
    lower = r3._lower_sources(setup.source, setup.context.timeframe)
    extreme = setup.source.low if signal.side is Side.LONG else setup.source.high
    found = causal_cisd(lower, side=signal.side, extreme=extreme)
    if found is None or found.confirmed_at != signal.cisd_at:
        raise ValueError("R9 CISD reconstruction drift")
    confirmed = next((item for item in lower if item.closed_at == found.confirmed_at), None)
    if confirmed is None:
        raise ValueError("R9 confirming lower-timeframe source missing")
    return found, confirmed


def _opposing_series_length(setup: r3.Setup, series_opened_at: datetime, extreme_at: datetime) -> int:
    lower = r3._lower_sources(setup.source, setup.context.timeframe)
    return sum(1 for candle in lower if series_opened_at <= candle.opened_at <= extreme_at)


def _mean_prior_source_range(
    candles: Sequence[SourceCandle],
    index_by_open: Mapping[datetime, int],
    opened_at: datetime,
    count: int = 20,
) -> Decimal | None:
    pos = index_by_open.get(opened_at)
    if pos is None:
        return None
    previous = candles[max(0, pos - count):pos]
    if not previous:
        return None
    ranges = [candle.high - candle.low for candle in previous if candle.high > candle.low]
    if not ranges:
        return None
    return sum(ranges, Decimal(0)) / len(ranges)


def _regime_exact(at: datetime, side: str, d1: r5.RegimeSeries, h4: r5.RegimeSeries) -> dict[str, Any]:
    d20 = r5._history(d1, at, 20)
    d5 = d20[-5:]
    d1last = d20[-1:] if d20 else ()
    h20 = r5._history(h4, at, 20)
    h6 = h20[-6:]
    h3 = h20[-3:]
    d_loc = r5._location(d20)
    h_loc = r5._location(h20)
    prior_d1 = d20[-1] if d20 else None
    prior_h4 = h20[-1] if h20 else None
    return {
        "d1_prior_range_vs20_exact": r5._range_ratio(d1last, d20),
        "d1_range_5v20_exact": r5._range_ratio(d5, d20),
        "d1_efficiency_5_exact": r5._efficiency(d5),
        "d1_efficiency_20_exact": r5._efficiency(d20),
        "d1_location_20_exact": d_loc,
        "d1_reversal_edge_20_exact": r5._reversal_edge(d_loc, side),
        "h4_range_3v20_exact": r5._range_ratio(h3, h20),
        "h4_efficiency_6_exact": r5._efficiency(h6),
        "h4_efficiency_20_exact": r5._efficiency(h20),
        "h4_location_20_exact": h_loc,
        "h4_reversal_edge_20_exact": r5._reversal_edge(h_loc, side),
        "prior_d1_body_alignment": _body_alignment(prior_d1, side),
        "prior_h4_body_alignment": _body_alignment(prior_h4, side),
        "prior_d1_body_fraction": _body_fraction(prior_d1),
        "prior_h4_body_fraction": _body_fraction(prior_h4),
    }


def _active_dol_features(
    trade: r3.RoutedTrade,
    episode_rows: Sequence[r3.TargetCandidate],
    side: Side,
    source_range: Decimal,
    prior_h4_range: Decimal | None,
    prior_d1_range: Decimal | None,
) -> dict[str, Any]:
    active: dict[tuple[str, str, Decimal, datetime], r3.TargetCandidate] = {}
    for route in r3.TARGET_ROUTES:
        for candidate in r3._active_targets(
            episode_rows,
            at=trade.entry_at,
            side=side,
            anchor=trade.entry,
            route=route,
        ):
            active[(candidate.kind, candidate.timeframe, candidate.level, candidate.known_at)] = candidate
    candidates = list(active.values())
    candidates.sort(key=lambda item: (abs(item.level - trade.entry), item.known_at, item.level))
    selected = [
        candidate
        for candidate in candidates
        if candidate.level == trade.target
        and candidate.kind == trade.target_kind
        and candidate.timeframe == trade.target_timeframe
    ]
    selected_candidate = selected[0] if selected else None
    selected_rank = (
        next((index + 1 for index, candidate in enumerate(candidates) if candidate is selected_candidate), None)
        if selected_candidate is not None
        else None
    )
    reward = abs(trade.target - trade.entry)
    return {
        "active_dol_count": len(candidates),
        "active_dol_family_count": len({(candidate.kind, candidate.timeframe) for candidate in candidates}),
        "selected_dol_rank": selected_rank,
        "nearer_dol_count": None if selected_rank is None else selected_rank - 1,
        "selected_dol_age_minutes": (
            None if selected_candidate is None else _minutes(selected_candidate.known_at, trade.entry_at)
        ),
        "dol_distance_abs": reward,
        "dol_distance_bps": _safe_ratio(reward * Decimal(10000), trade.entry),
        "dol_distance_source_fraction": _safe_ratio(reward, source_range),
        "dol_distance_h4_fraction": _safe_ratio(reward, prior_h4_range),
        "dol_distance_d1_fraction": _safe_ratio(reward, prior_d1_range),
    }


def _continuous_record(
    setup: r3.Setup,
    trade: r3.RoutedTrade,
    c1: SourceCandle,
    prior20_source_range: Decimal | None,
    h1: Sequence[SourceCandle],
    h1_opens: Sequence[datetime],
    h4: Sequence[SourceCandle],
    h4_opens: Sequence[datetime],
    d1: r5.RegimeSeries,
    h4_regime: r5.RegimeSeries,
    episode_rows: Sequence[r3.TargetCandidate],
) -> dict[str, Any]:
    signal = setup.context.signal
    side = signal.side
    c2 = setup.source
    source_range = c2.high - c2.low
    if source_range <= 0:
        raise ValueError("R9 non-positive source range")
    raid_level = c1.low if side is Side.LONG else c1.high
    raid_extreme = c2.low if side is Side.LONG else c2.high
    raid_depth = abs(raid_extreme - raid_level)
    reclaim = _first_reclaim_bar(c2, c1, side, signal.raid_at)
    reclaim_fraction = None
    reclaim_overshoot = None
    reclaim_latency = None
    reclaim_to_cisd = None
    if reclaim is not None and raid_depth > 0:
        reclaim_move = (
            reclaim.close - raid_extreme if side is Side.LONG else raid_extreme - reclaim.close
        )
        reclaim_fraction = reclaim_move / raid_depth
        reclaim_overshoot = abs(reclaim.close - raid_level) / source_range
        reclaim_latency = _minutes(signal.raid_at, reclaim.closed_at)
        reclaim_to_cisd = _minutes(reclaim.closed_at, signal.cisd_at)

    found, confirmed = _lower_confirmation(setup)
    displacement = (
        confirmed.close - found.threshold if side is Side.LONG else found.threshold - confirmed.close
    )
    confirm_range = confirmed.high - confirmed.low
    lower = r3._lower_sources(c2, setup.context.timeframe)
    lower_ranges = [item.high - item.low for item in lower if item.opened_at < confirmed.opened_at and item.high > item.low]
    mean_lower_range = (
        sum(lower_ranges, Decimal(0)) / len(lower_ranges) if lower_ranges else None
    )
    source_minutes = _minutes(c2.opened_at, c2.closed_at)
    risk = abs(trade.entry - trade.stop)

    prior_h1 = _prior_completed_source(h1, h1_opens, trade.entry_at)
    prior_h4 = _prior_completed_source(h4, h4_opens, trade.entry_at)
    prior_d1_rows = r5._history(d1, trade.entry_at, 1)
    prior_d1 = prior_d1_rows[-1] if prior_d1_rows else None
    prior_h1_range = _source_range(prior_h1)
    prior_h4_range = _source_range(prior_h4)
    prior_d1_range = _source_range(prior_d1)

    touches = _prior_equal_touches(c2, c1, side, signal.raid_at)
    record: dict[str, Any] = {
        "raid_depth_abs": raid_depth,
        "raid_depth_bps": _safe_ratio(raid_depth * Decimal(10000), raid_level),
        "raid_depth_source_fraction": raid_depth / source_range,
        "raid_depth_prior20_source_fraction": _safe_ratio(raid_depth, prior20_source_range),
        "prior_equal_touch_count": touches,
        "liquidity_pristine_before_raid": "yes" if touches == 0 else "no",
        "raid_violation_bars_to_cisd": _violation_bars_to_cisd(c2, c1, side, signal.raid_at, signal.cisd_at),
        "reclaim_latency_minutes": reclaim_latency,
        "reclaim_fraction_of_sweep": reclaim_fraction,
        "reclaim_overshoot_source_fraction": reclaim_overshoot,
        "raid_to_cisd_minutes": _minutes(signal.raid_at, signal.cisd_at),
        "reclaim_to_cisd_minutes": reclaim_to_cisd,
        "cisd_progress_exact": _safe_ratio(_minutes(c2.opened_at, signal.cisd_at), source_minutes),
        "cisd_displacement_abs": displacement,
        "cisd_displacement_source_fraction": _safe_ratio(displacement, source_range),
        "cisd_displacement_lower_range_fraction": _safe_ratio(displacement, mean_lower_range),
        "cisd_confirmation_range_source_fraction": _safe_ratio(confirm_range, source_range),
        "opposing_series_length": _opposing_series_length(setup, found.series_opened_at, found.extreme_at),
        "protected_risk_abs": risk,
        "protected_risk_bps": _safe_ratio(risk * Decimal(10000), trade.entry),
        "protected_risk_source_fraction_exact": risk / source_range,
        "protected_risk_h1_fraction": _safe_ratio(risk, prior_h1_range),
        "protected_risk_h4_fraction": _safe_ratio(risk, prior_h4_range),
        "protected_risk_d1_fraction": _safe_ratio(risk, prior_d1_range),
        "protected_swing_age_minutes": _minutes(found.extreme_at, trade.entry_at),
        "protected_swing_confirmation_minutes": _minutes(found.extreme_at, found.confirmed_at),
        "ps_distance_from_liquidity_source_fraction": abs(trade.stop - raid_level) / source_range,
    }
    record.update(
        _active_dol_features(
            trade,
            episode_rows,
            side,
            source_range,
            prior_h4_range,
            prior_d1_range,
        )
    )
    record.update(_regime_exact(trade.entry_at, trade.side, d1, h4_regime))
    return record


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _feature_profile(rows: Sequence[dict[str, Any]], feature: str) -> dict[str, Any]:
    historical = _period(rows, HISTORICAL_YEARS)
    recent = _period(rows, RECENT_YEARS)
    hist_desc = _describe(historical, feature)
    recent_desc = _describe(recent, feature)
    hist_median = hist_desc["median"]
    recent_median = recent_desc["median"]
    delta = None
    if hist_median is not None and recent_median is not None:
        delta = str(_d(recent_median) - _d(hist_median))
    return {
        "early_2016_2020": _describe(_period(rows, EARLY_YEARS), feature),
        "transition_2021_2023": _describe(_period(rows, TRANSITION_YEARS), feature),
        "historical_2016_2023": hist_desc,
        "recent_2024_2026": recent_desc,
        "recent_minus_historical_median": delta,
        "by_year": {
            str(year): _describe([row for row in rows if int(row["year"]) == year], feature)
            for year in range(2016, 2027)
        },
        "historical_winners": _describe([row for row in historical if _d(row["primary_net_r"]) > 0], feature),
        "historical_non_winners": _describe([row for row in historical if _d(row["primary_net_r"]) <= 0], feature),
        "recent_winners": _describe([row for row in recent if _d(row["primary_net_r"]) > 0], feature),
        "recent_non_winners": _describe([row for row in recent if _d(row["primary_net_r"]) <= 0], feature),
    }


def _categorical_profile(rows: Sequence[dict[str, Any]], feature: str) -> dict[str, Any]:
    values = sorted({str(row.get(feature, "missing")) for row in rows})
    result: dict[str, Any] = {}
    for value in values:
        selected = [row for row in rows if str(row.get(feature, "missing")) == value]
        result[value] = {
            "full": _stat(selected),
            "early_2016_2020": _stat(_period(selected, EARLY_YEARS)),
            "transition_2021_2023": _stat(_period(selected, TRANSITION_YEARS)),
            "recent_2024_2026": _stat(_period(selected, RECENT_YEARS)),
        }
    return result


def _half_year_stats(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        at = datetime.fromisoformat(str(row["entry_at"]))
        grouped[f"{at.year}-H{1 if at.month <= 6 else 2}"].append(row)
    return {key: _stat(grouped[key]) for key in sorted(grouped)}


def _leave_one_year_out(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(year): _stat([row for row in rows if int(row["year"]) != year])
        for year in range(2016, 2027)
    }


def _family_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "full": _stat(rows),
        "early_2016_2020": _stat(_period(rows, EARLY_YEARS)),
        "transition_2021_2023": _stat(_period(rows, TRANSITION_YEARS)),
        "historical_2016_2023": _stat(_period(rows, HISTORICAL_YEARS)),
        "recent_2024_2026": _stat(_period(rows, RECENT_YEARS)),
        "by_year": {
            str(year): _stat([row for row in rows if int(row["year"]) == year])
            for year in range(2016, 2027)
        },
        "half_year": _half_year_stats(rows),
        "leave_one_year_out": _leave_one_year_out(rows),
        "continuous_feature_profiles": {
            feature: _feature_profile(rows, feature) for feature in CONTINUOUS_FEATURES
        },
        "categorical_feature_profiles": {
            feature: _categorical_profile(rows, feature) for feature in CATEGORICAL_FEATURES
        },
    }


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    episodes, _source_index = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    h1 = build_h1(evidence.bars)
    h4 = build_h4(evidence.bars)
    h1_opens = tuple(candle.opened_at for candle in h1)
    h4_opens = tuple(candle.opened_at for candle in h4)
    frames = {"H1": h1, "H4": h4}
    frame_index = {
        timeframe: {candle.opened_at: index for index, candle in enumerate(candles)}
        for timeframe, candles in frames.items()
    }
    frame_by_open = {
        timeframe: {candle.opened_at: candle for candle in candles}
        for timeframe, candles in frames.items()
    }
    d1_regime = r5._aggregate(evidence.bars, "D1")
    h4_regime = r5._aggregate(evidence.bars, "H4")

    family_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in r8.BREAK_FAMILIES}
    r7_kept_count = 0
    for setup, trade in selected:
        row = causal._record(setup, trade, evidence.bars, opens)
        row.update(r5._regime_features(row, d1_regime, h4_regime))
        if r7._is_abstain(row):
            continue
        r7_kept_count += 1
        matched_name = next(
            (
                name
                for name, signature in r8.BREAK_FAMILIES.items()
                if r8._matches(row, signature)
            ),
            None,
        )
        if matched_name is None:
            continue
        timeframe = setup.context.timeframe
        c1 = frame_by_open[timeframe].get(setup.context.signal.c1_opened_at)
        if c1 is None:
            raise ValueError("R9 previous source candle missing")
        prior20 = _mean_prior_source_range(
            frames[timeframe],
            frame_index[timeframe],
            setup.source.opened_at,
        )
        episode_rows = episodes.get(trade.episode_id)
        if not episode_rows:
            raise ValueError("R9 selected CIBO episode missing")
        row.update(
            _continuous_record(
                setup,
                trade,
                c1,
                prior20,
                h1,
                h1_opens,
                h4,
                h4_opens,
                d1_regime,
                h4_regime,
                episode_rows,
            )
        )
        row["family"] = matched_name
        row["year"] = _iso_year(row)
        family_rows[matched_name].append(row)

    if r7_kept_count != 5612:
        raise ValueError(f"R7 retained drift: expected 5612, got {r7_kept_count}")
    expected = {
        "BREAK_A_DEEP_RAID_MID_LATE_CISD": 151,
        "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": 88,
    }
    for name, count in expected.items():
        if len(family_rows[name]) != count:
            raise ValueError(f"R9 family drift for {name}: expected {count}, got {len(family_rows[name])}")

    payload = {
        "schema": "qore.turtle_soup_xauusd_r9.causal_break_discriminator.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            **reproduction,
            "r7_retained": r7_kept_count,
            "break_a_trades": len(family_rows["BREAK_A_DEEP_RAID_MID_LATE_CISD"]),
            "break_b_trades": len(family_rows["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"]),
        },
        "pre_registered_break_families": {
            name: dict(signature) for name, signature in r8.BREAK_FAMILIES.items()
        },
        "continuous_features": list(CONTINUOUS_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "families": {
            name: _family_report(rows) for name, rows in family_rows.items()
        },
        "research_question": "WHAT_PRE_ENTRY_GEOMETRY_DISTINGUISHES_HISTORICALLY_VALID_BREAK_A_B_JOURNEYS_FROM_RECENTLY_INVALID_INSTANCES_WITHOUT_DATE_AS_A_RULE",
        "interpretation_contract": {
            "year_is_diagnostic_partition_only": True,
            "continuous_values_are_descriptive_not_thresholds": True,
            "winner_loser_profiles_are_forensic_not_operating_rules": True,
            "automatic_threshold_search": False,
            "return_maximising_feature_selection": False,
            "candidate_rule_promoted": False,
        },
        "governance": {
            "diagnostic_only": True,
            "fresh_holdout_consumed": False,
            "post_entry_information_allowed_as_input": False,
            "year_or_date_allowed_as_operating_rule": False,
            "automatic_candidate_promotion": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "causal-break-discriminator.json").write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n"
    )
    (output / "break-a-cases.json").write_text(
        json.dumps(_jsonable(family_rows["BREAK_A_DEEP_RAID_MID_LATE_CISD"]), indent=2, sort_keys=True) + "\n"
    )
    (output / "break-b-cases.json").write_text(
        json.dumps(_jsonable(family_rows["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"]), indent=2, sort_keys=True) + "\n"
    )
    return _jsonable(payload)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
