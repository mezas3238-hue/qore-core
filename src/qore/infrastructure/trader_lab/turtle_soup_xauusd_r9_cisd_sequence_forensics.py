"""Pre-entry CISD sequence-efficiency forensics for Turtle Soup XAUUSD R9.

Diagnostic research only. The module distinguishes genuine directional
expansion from a late/technical CISD crossing by measuring the full M5 path
from raid/reclaim to causal CISD. All features are known by CISD confirmation
and therefore before either R3 entry mode can fill.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
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
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side, SourceCandle, build_h1, build_h4

IDENTITY = "TURTLE_SOUP_XAUUSD_R9_CISD_SEQUENCE_FORENSICS_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_PRE_ENTRY_CISD_SEQUENCE_NOT_FRESH_HOLDOUT"

FEATURES = (
    "raid_to_cisd_m5_bars",
    "reclaim_to_cisd_m5_bars",
    "raid_to_cisd_path_efficiency",
    "reclaim_to_cisd_path_efficiency",
    "raid_to_cisd_favorable_step_share",
    "reclaim_to_cisd_favorable_step_share",
    "raid_to_cisd_net_source_fraction",
    "reclaim_to_cisd_net_source_fraction",
    "post_reclaim_max_reviolation_raid_fraction",
    "post_reclaim_max_reviolation_source_fraction",
    "confirm_bar_body_fraction",
    "confirm_bar_favorable_close_location",
    "confirm_bar_overlap_previous_fraction",
    "confirm_bar_range_vs_prior6_m5",
    "confirm_directional_streak",
    "reclaim_close_favorable_location",
)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _ratio(num: Decimal | None, den: Decimal | None) -> Decimal | None:
    if num is None or den is None or den <= 0:
        return None
    return num / den


def _path_efficiency(bars: Sequence[Any]) -> Decimal | None:
    if len(bars) < 2:
        return None
    moves = [abs(bars[i].close - bars[i - 1].close) for i in range(1, len(bars))]
    total = sum(moves, Decimal(0))
    if total <= 0:
        return None
    return abs(bars[-1].close - bars[0].close) / total


def _favorable_step_share(bars: Sequence[Any], side: Side) -> Decimal | None:
    if len(bars) < 2:
        return None
    deltas = [bars[i].close - bars[i - 1].close for i in range(1, len(bars))]
    nonzero = [delta for delta in deltas if delta != 0]
    if not nonzero:
        return None
    favorable = sum(1 for delta in nonzero if (delta > 0 if side is Side.LONG else delta < 0))
    return Decimal(favorable) / len(nonzero)


def _favorable_close_location(bar: Any, side: Side) -> Decimal | None:
    span = bar.high - bar.low
    if span <= 0:
        return None
    return (bar.close - bar.low) / span if side is Side.LONG else (bar.high - bar.close) / span


def _body_fraction(bar: Any) -> Decimal | None:
    span = bar.high - bar.low
    return None if span <= 0 else abs(bar.close - bar.open) / span


def _overlap_fraction(current: Any, previous: Any) -> Decimal | None:
    span = current.high - current.low
    if span <= 0:
        return None
    overlap = max(Decimal(0), min(current.high, previous.high) - max(current.low, previous.low))
    return overlap / span


def _directional_streak(bars: Sequence[Any], side: Side) -> int:
    count = 0
    for bar in reversed(bars):
        favorable = bar.close > bar.open if side is Side.LONG else bar.close < bar.open
        if not favorable:
            break
        count += 1
    return count


def _mean_range(bars: Sequence[Any]) -> Decimal | None:
    ranges = [bar.high - bar.low for bar in bars if bar.high > bar.low]
    return None if not ranges else sum(ranges, Decimal(0)) / len(ranges)


def _sequence_features(setup: r3.Setup, c1: SourceCandle) -> dict[str, Any]:
    signal = setup.context.signal
    side = signal.side
    c2 = setup.source
    source_range = c2.high - c2.low
    if source_range <= 0:
        raise ValueError("non-positive source range")
    raid_level = c1.low if side is Side.LONG else c1.high
    raid_extreme = c2.low if side is Side.LONG else c2.high
    raid_depth = abs(raid_extreme - raid_level)
    reclaim = r9._first_reclaim_bar(c2, c1, side, signal.raid_at)
    if reclaim is None:
        raise ValueError("R9 sequence could not reproduce reclaim")
    path = [
        bar for bar in c2.m5
        if bar.opened_at >= signal.raid_at and bar.closed_at <= signal.cisd_at
    ]
    reclaim_path = [bar for bar in path if bar.closed_at >= reclaim.closed_at]
    if not path:
        raise ValueError("empty raid-to-CISD M5 path")
    confirm = path[-1]
    previous = path[-2] if len(path) >= 2 else None
    prior6 = [bar for bar in c2.m5 if bar.closed_at <= confirm.opened_at][-6:]
    prior6_mean = _mean_range(prior6)

    if side is Side.LONG:
        raid_net = confirm.close - raid_extreme
        reclaim_net = confirm.close - reclaim.close
        worst_after_reclaim = min((bar.low for bar in reclaim_path), default=reclaim.low)
        re_violation = max(Decimal(0), raid_level - worst_after_reclaim)
    else:
        raid_net = raid_extreme - confirm.close
        reclaim_net = reclaim.close - confirm.close
        worst_after_reclaim = max((bar.high for bar in reclaim_path), default=reclaim.high)
        re_violation = max(Decimal(0), worst_after_reclaim - raid_level)

    return {
        "raid_to_cisd_m5_bars": len(path),
        "reclaim_to_cisd_m5_bars": len(reclaim_path),
        "raid_to_cisd_path_efficiency": _path_efficiency(path),
        "reclaim_to_cisd_path_efficiency": _path_efficiency(reclaim_path),
        "raid_to_cisd_favorable_step_share": _favorable_step_share(path, side),
        "reclaim_to_cisd_favorable_step_share": _favorable_step_share(reclaim_path, side),
        "raid_to_cisd_net_source_fraction": raid_net / source_range,
        "reclaim_to_cisd_net_source_fraction": reclaim_net / source_range,
        "post_reclaim_max_reviolation_raid_fraction": _ratio(re_violation, raid_depth),
        "post_reclaim_max_reviolation_source_fraction": re_violation / source_range,
        "confirm_bar_body_fraction": _body_fraction(confirm),
        "confirm_bar_favorable_close_location": _favorable_close_location(confirm, side),
        "confirm_bar_overlap_previous_fraction": None if previous is None else _overlap_fraction(confirm, previous),
        "confirm_bar_range_vs_prior6_m5": _ratio(confirm.high - confirm.low, prior6_mean),
        "confirm_directional_streak": _directional_streak(path, side),
        "reclaim_close_favorable_location": _favorable_close_location(reclaim, side),
    }


def _percentile(values: Sequence[Decimal], n: int, d: int) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = Decimal(len(ordered) - 1) * Decimal(n) / Decimal(d)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - Decimal(lo)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def _describe(rows: Sequence[dict[str, Any]], feature: str) -> dict[str, Any]:
    vals = [_d(row[feature]) for row in rows if row.get(feature) is not None]
    return {
        "n": len(vals),
        "p25": str(_percentile(vals, 1, 4)) if vals else None,
        "median": str(_percentile(vals, 1, 2)) if vals else None,
        "p75": str(_percentile(vals, 3, 4)) if vals else None,
        "mean": str(sum(vals, Decimal(0)) / len(vals)) if vals else None,
    }


def _profiles(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    stages = (
        "SELECTED_DOL_REACHED",
        "INVALIDATED_BEFORE_ANY_ACTIVE_DOL",
        "NEARER_DOL_REACHED_THEN_INVALIDATED",
    )
    return {
        stage: {
            "trades": len(members := [row for row in rows if row["journey_failure_stage"] == stage]),
            "features": {feature: _describe(members, feature) for feature in FEATURES},
        }
        for stage in stages
    }


def _family_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "early_2016_2020": _profiles([row for row in rows if int(row["year"]) in r9.EARLY_YEARS]),
        "transition_2021_2023": _profiles([row for row in rows if int(row["year"]) in r9.TRANSITION_YEARS]),
        "recent_2024_2026": _profiles([row for row in rows if int(row["year"]) in r9.RECENT_YEARS]),
        "by_year": {str(year): _profiles([row for row in rows if int(row["year"]) == year]) for year in range(2016, 2027)},
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    episodes, _ = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    frames = {"H1": build_h1(evidence.bars), "H4": build_h4(evidence.bars)}
    by_open = {tf: {candle.opened_at: candle for candle in candles} for tf, candles in frames.items()}
    d1 = r5._aggregate(evidence.bars, "D1")
    h4reg = r5._aggregate(evidence.bars, "H4")
    families: dict[str, list[dict[str, Any]]] = {name: [] for name in r8.BREAK_FAMILIES}
    retained = 0
    for setup, trade in selected:
        row = causal._record(setup, trade, evidence.bars, opens)
        row.update(r5._regime_features(row, d1, h4reg))
        if r7._is_abstain(row):
            continue
        retained += 1
        family = next((name for name, sig in r8.BREAK_FAMILIES.items() if r8._matches(row, sig)), None)
        if family is None:
            continue
        c1 = by_open[setup.context.timeframe].get(setup.context.signal.c1_opened_at)
        if c1 is None:
            raise ValueError("C1 missing")
        target_rows = episodes.get(trade.episode_id)
        if not target_rows:
            raise ValueError("episode missing")
        row.update(r9j._path_diagnostic(trade, target_rows, evidence, opens))
        row.update(_sequence_features(setup, c1))
        row["family"] = family
        row["year"] = trade.entry_at.year
        families[family].append(row)

    expected = {"BREAK_A_DEEP_RAID_MID_LATE_CISD": 151, "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": 88}
    if retained != 5612:
        raise ValueError(f"R7 retained drift: {retained}")
    for name, count in expected.items():
        if len(families[name]) != count:
            raise ValueError(f"family drift {name}: {len(families[name])} != {count}")

    payload = {
        "schema": "qore.turtle_soup_xauusd_r9.cisd_sequence_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {**reproduction, "r7_retained": retained, "break_a_trades": len(families["BREAK_A_DEEP_RAID_MID_LATE_CISD"]), "break_b_trades": len(families["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"])},
        "question": "DOES_PRE_ENTRY_RAID_RECLAIM_CISD_PATH_EFFICIENCY_SEPARATE_GENUINE_EXPANSION_FROM_TECHNICAL_CROSSING",
        "features": list(FEATURES),
        "families": {name: _family_report(rows) for name, rows in families.items()},
        "interpretation_contract": {"post_entry_stage_is_label_only": True, "post_entry_stage_allowed_as_operating_input": False, "automatic_threshold_search": False, "return_maximising_feature_selection": False, "candidate_rule_promoted": False},
        "governance": {"diagnostic_only": True, "fresh_holdout_consumed": False, "year_or_date_allowed_as_operating_rule": False, "demo_eligible": False, "live_authorized": False, "real_capital_authorized": False, "production_authorized": False},
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "cisd-sequence-report.json").write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n")
    (output / "break-a-sequences.json").write_text(json.dumps(_jsonable(families["BREAK_A_DEEP_RAID_MID_LATE_CISD"]), indent=2, sort_keys=True) + "\n")
    (output / "break-b-sequences.json").write_text(json.dumps(_jsonable(families["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"]), indent=2, sort_keys=True) + "\n")
    return _jsonable(payload)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
