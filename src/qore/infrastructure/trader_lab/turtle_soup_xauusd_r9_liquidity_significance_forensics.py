"""Pre-entry liquidity-significance forensics for Turtle Soup XAUUSD R9.

The R9 path lab showed that recent BREAK A/B failures mostly invalidate before
reaching any active DOL. This module moves upstream to the first causal link:
was the swept C1 boundary meaningful liquidity before the raid?

No outcome-derived threshold search is performed. Continuous externality,
HTF-edge proximity, prior-boundary proximity, and C1 anatomy are described by
period and by diagnostic journey stage only.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r7_structural_abstention_lab as r7
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r8_structural_break_counterfactual as r8
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_causal_break_discriminator as r9
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_journey_divergence_forensics as r9j
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Side,
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R9_LIQUIDITY_SIGNIFICANCE_FORENSICS_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_PRE_ENTRY_LIQUIDITY_SIGNIFICANCE_NOT_FRESH_HOLDOUT"

FEATURES = (
    "c1_body_fraction",
    "c1_directional_wick_fraction",
    "c1_range_vs_prior20_source",
    "raid_depth_c1_range_fraction",
    "c1_externality_rank_20",
    "c1_beyond_prior3_source_range_fraction",
    "c1_beyond_prior5_source_range_fraction",
    "c1_beyond_prior20_source_range_fraction",
    "c1_prior_h4_edge_distance_fraction",
    "c1_prior_d1_edge_distance_fraction",
    "c1_nearest_prior_h1_boundary_source_fraction",
    "c1_nearest_prior_h4_boundary_source_fraction",
    "c1_nearest_prior_d1_boundary_source_fraction",
    "c1_nearest_prior_h1_boundary_age_minutes",
    "c1_nearest_prior_h4_boundary_age_minutes",
    "c1_nearest_prior_d1_boundary_age_minutes",
)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _range(candle: SourceCandle | None) -> Decimal | None:
    if candle is None:
        return None
    value = candle.high - candle.low
    return value if value > 0 else None


def _ratio(num: Decimal | None, den: Decimal | None) -> Decimal | None:
    if num is None or den is None or den <= 0:
        return None
    return num / den


def _minutes(left: datetime, right: datetime) -> Decimal:
    return Decimal(str((right - left).total_seconds())) / Decimal(60)


def _prior_completed(
    candles: Sequence[SourceCandle], opens: Sequence[datetime], at: datetime
) -> SourceCandle | None:
    pos = bisect.bisect_left(opens, at) - 1
    while pos >= 0:
        candle = candles[pos]
        if candle.closed_at <= at:
            return candle
        pos -= 1
    return None


def _prior_window(
    candles: Sequence[SourceCandle],
    index_by_open: Mapping[datetime, int],
    opened_at: datetime,
    count: int,
) -> list[SourceCandle]:
    pos = index_by_open.get(opened_at)
    if pos is None:
        return []
    return list(candles[max(0, pos - count):pos])


def _side_boundary(candle: SourceCandle, side: Side) -> Decimal:
    return candle.low if side is Side.LONG else candle.high


def _externality_rank(c1: SourceCandle, prior: Sequence[SourceCandle], side: Side) -> Decimal | None:
    if not prior:
        return None
    level = _side_boundary(c1, side)
    if side is Side.LONG:
        at_or_beyond = sum(1 for candle in prior if candle.low <= level)
    else:
        at_or_beyond = sum(1 for candle in prior if candle.high >= level)
    return Decimal(at_or_beyond) / len(prior)


def _beyond_prior(c1: SourceCandle, prior: Sequence[SourceCandle], side: Side, normalizer: Decimal) -> Decimal | None:
    if not prior or normalizer <= 0:
        return None
    level = _side_boundary(c1, side)
    if side is Side.LONG:
        prior_edge = min(candle.low for candle in prior)
        return (prior_edge - level) / normalizer
    prior_edge = max(candle.high for candle in prior)
    return (level - prior_edge) / normalizer


def _edge_distance(level: Decimal, candle: SourceCandle | None, side: Side) -> Decimal | None:
    span = _range(candle)
    if candle is None or span is None:
        return None
    if side is Side.LONG:
        return (level - candle.low) / span
    return (candle.high - level) / span


def _nearest_boundary(
    level: Decimal,
    candles: Sequence[SourceCandle],
    side: Side,
    at: datetime,
    normalizer: Decimal,
) -> tuple[Decimal | None, Decimal | None]:
    if normalizer <= 0:
        return None, None
    prior = [candle for candle in candles if candle.closed_at <= at][-20:]
    if not prior:
        return None, None
    ranked = sorted(
        ((abs(_side_boundary(candle, side) - level), candle) for candle in prior),
        key=lambda item: (item[0], item[1].opened_at),
    )
    distance, candle = ranked[0]
    return distance / normalizer, _minutes(candle.closed_at, at)


def _c1_anatomy(c1: SourceCandle, side: Side) -> tuple[Decimal | None, Decimal | None]:
    span = _range(c1)
    if span is None:
        return None, None
    body = abs(c1.close - c1.open) / span
    if side is Side.LONG:
        wick = (min(c1.open, c1.close) - c1.low) / span
    else:
        wick = (c1.high - max(c1.open, c1.close)) / span
    return body, wick


def _features(
    setup: r3.Setup,
    c1: SourceCandle,
    frames: Mapping[str, Sequence[SourceCandle]],
    frame_indexes: Mapping[str, Mapping[datetime, int]],
    h1: Sequence[SourceCandle],
    h4: Sequence[SourceCandle],
    daily: Sequence[SourceCandle],
    h4_opens: Sequence[datetime],
    d1_opens: Sequence[datetime],
) -> dict[str, Any]:
    side = setup.context.signal.side
    c2 = setup.source
    c2_range = c2.high - c2.low
    c1_range = c1.high - c1.low
    if c2_range <= 0 or c1_range <= 0:
        raise ValueError("non-positive C1/C2 range in liquidity significance forensics")
    source = list(frames[setup.context.timeframe])
    index = frame_indexes[setup.context.timeframe]
    p3 = _prior_window(source, index, c1.opened_at, 3)
    p5 = _prior_window(source, index, c1.opened_at, 5)
    p20 = _prior_window(source, index, c1.opened_at, 20)
    mean20 = (
        sum((candle.high - candle.low for candle in p20), Decimal(0)) / len(p20)
        if p20
        else None
    )
    body, wick = _c1_anatomy(c1, side)
    level = _side_boundary(c1, side)
    raid_extreme = c2.low if side is Side.LONG else c2.high
    raid_depth = abs(raid_extreme - level)
    prior_h4 = _prior_completed(h4, h4_opens, c2.opened_at)
    prior_d1 = _prior_completed(daily, d1_opens, c2.opened_at)
    h1_dist, h1_age = _nearest_boundary(level, h1, side, c2.opened_at, c2_range)
    h4_dist, h4_age = _nearest_boundary(level, h4, side, c2.opened_at, c2_range)
    d1_dist, d1_age = _nearest_boundary(level, daily, side, c2.opened_at, c2_range)
    return {
        "c1_body_fraction": body,
        "c1_directional_wick_fraction": wick,
        "c1_range_vs_prior20_source": _ratio(c1_range, mean20),
        "raid_depth_c1_range_fraction": raid_depth / c1_range,
        "c1_externality_rank_20": _externality_rank(c1, p20, side),
        "c1_beyond_prior3_source_range_fraction": _beyond_prior(c1, p3, side, c2_range),
        "c1_beyond_prior5_source_range_fraction": _beyond_prior(c1, p5, side, c2_range),
        "c1_beyond_prior20_source_range_fraction": _beyond_prior(c1, p20, side, c2_range),
        "c1_prior_h4_edge_distance_fraction": _edge_distance(level, prior_h4, side),
        "c1_prior_d1_edge_distance_fraction": _edge_distance(level, prior_d1, side),
        "c1_nearest_prior_h1_boundary_source_fraction": h1_dist,
        "c1_nearest_prior_h4_boundary_source_fraction": h4_dist,
        "c1_nearest_prior_d1_boundary_source_fraction": d1_dist,
        "c1_nearest_prior_h1_boundary_age_minutes": h1_age,
        "c1_nearest_prior_h4_boundary_age_minutes": h4_age,
        "c1_nearest_prior_d1_boundary_age_minutes": d1_age,
    }


def _percentile(values: Sequence[Decimal], q_num: int, q_den: int) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = Decimal(len(ordered) - 1) * Decimal(q_num) / Decimal(q_den)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - Decimal(low)
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def _describe(rows: Sequence[dict[str, Any]], feature: str) -> dict[str, Any]:
    values = [_d(row[feature]) for row in rows if row.get(feature) is not None]
    return {
        "n": len(values),
        "p25": str(_percentile(values, 1, 4)) if values else None,
        "median": str(_percentile(values, 1, 2)) if values else None,
        "p75": str(_percentile(values, 3, 4)) if values else None,
        "mean": str(sum(values, Decimal(0)) / len(values)) if values else None,
    }


def _stage_profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    stages = (
        "SELECTED_DOL_REACHED",
        "INVALIDATED_BEFORE_ANY_ACTIVE_DOL",
        "NEARER_DOL_REACHED_THEN_INVALIDATED",
    )
    result: dict[str, Any] = {}
    for stage in stages:
        members = [row for row in rows if row["journey_failure_stage"] == stage]
        result[stage] = {
            "trades": len(members),
            "features": {feature: _describe(members, feature) for feature in FEATURES},
        }
    return result


def _family_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    historical = [row for row in rows if int(row["year"]) in r9.HISTORICAL_YEARS]
    recent = [row for row in rows if int(row["year"]) in r9.RECENT_YEARS]
    return {
        "historical_2016_2023": _stage_profiles(historical),
        "recent_2024_2026": _stage_profiles(recent),
        "by_year": {
            str(year): _stage_profiles([row for row in rows if int(row["year"]) == year])
            for year in range(2016, 2027)
        },
    }


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


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    episodes, _source_index = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    h1 = build_h1(evidence.bars)
    h4 = build_h4(evidence.bars)
    daily = build_daily(h4)
    frames: dict[str, Sequence[SourceCandle]] = {"H1": h1, "H4": h4}
    indexes = {
        timeframe: {candle.opened_at: index for index, candle in enumerate(candles)}
        for timeframe, candles in frames.items()
    }
    by_open = {
        timeframe: {candle.opened_at: candle for candle in candles}
        for timeframe, candles in frames.items()
    }
    h4_opens = tuple(candle.opened_at for candle in h4)
    d1_opens = tuple(candle.opened_at for candle in daily)
    d1_regime = r5._aggregate(evidence.bars, "D1")
    h4_regime = r5._aggregate(evidence.bars, "H4")
    family_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in r8.BREAK_FAMILIES}
    retained = 0
    for setup, trade in selected:
        row = causal._record(setup, trade, evidence.bars, opens)
        row.update(r5._regime_features(row, d1_regime, h4_regime))
        if r7._is_abstain(row):
            continue
        retained += 1
        family = next(
            (name for name, signature in r8.BREAK_FAMILIES.items() if r8._matches(row, signature)),
            None,
        )
        if family is None:
            continue
        c1 = by_open[setup.context.timeframe].get(setup.context.signal.c1_opened_at)
        if c1 is None:
            raise ValueError("C1 missing in liquidity significance forensics")
        target_rows = episodes.get(trade.episode_id)
        if not target_rows:
            raise ValueError("selected episode missing in liquidity significance forensics")
        row.update(r9j._path_diagnostic(trade, target_rows, evidence, opens))
        row.update(
            _features(
                setup,
                c1,
                frames,
                indexes,
                h1,
                h4,
                daily,
                h4_opens,
                d1_opens,
            )
        )
        row["family"] = family
        row["year"] = datetime.fromisoformat(str(row["entry_at"])).year
        family_rows[family].append(row)

    if retained != 5612:
        raise ValueError(f"R7 retained drift: {retained}")
    expected = {
        "BREAK_A_DEEP_RAID_MID_LATE_CISD": 151,
        "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": 88,
    }
    for name, count in expected.items():
        if len(family_rows[name]) != count:
            raise ValueError(f"family drift {name}: {len(family_rows[name])} != {count}")

    payload = {
        "schema": "qore.turtle_soup_xauusd_r9.liquidity_significance_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            **reproduction,
            "r7_retained": retained,
            "break_a_trades": len(family_rows["BREAK_A_DEEP_RAID_MID_LATE_CISD"]),
            "break_b_trades": len(family_rows["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"]),
        },
        "question": "DOES_PRE_ENTRY_C1_LIQUIDITY_SIGNIFICANCE_SEPARATE_DOL_CAPABLE_FROM_PRE_DOL_INVALIDATED_BREAK_A_B_JOURNEYS",
        "features": list(FEATURES),
        "families": {name: _family_report(rows) for name, rows in family_rows.items()},
        "interpretation_contract": {
            "year_is_diagnostic_partition_only": True,
            "post_entry_stage_is_label_only": True,
            "post_entry_stage_allowed_as_operating_input": False,
            "automatic_threshold_search": False,
            "return_maximising_feature_selection": False,
            "candidate_rule_promoted": False,
        },
        "governance": {
            "diagnostic_only": True,
            "fresh_holdout_consumed": False,
            "year_or_date_allowed_as_operating_rule": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "liquidity-significance-report.json").write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n"
    )
    for family, name in (
        ("BREAK_A_DEEP_RAID_MID_LATE_CISD", "break-a-liquidity.json"),
        ("BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4", "break-b-liquidity.json"),
    ):
        (output / name).write_text(
            json.dumps(_jsonable(family_rows[family]), indent=2, sort_keys=True) + "\n"
        )
    return _jsonable(payload)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
