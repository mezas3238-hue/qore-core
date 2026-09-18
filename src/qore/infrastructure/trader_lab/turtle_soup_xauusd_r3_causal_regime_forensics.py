"""Causal pre-entry regime forensics for Turtle Soup XAUUSD R3.

Diagnostic only. Reproduces the frozen R3 selection on the consumed 10Y corpus,
then joins each executed trade to information that was available before entry.
No feature discovered here is promoted to an operating filter.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as journey
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair

IDENTITY = "TURTLE_SOUP_XAUUSD_R3_CAUSAL_REGIME_FORENSICS_V1"
BASELINE_YEARS = frozenset({2016, 2017, 2018, 2019})
RECENT_YEARS = frozenset({2024, 2025, 2026})
CONTEXT_FEATURES = (
    "prior_body_alignment",
    "fvg_before_entry",
    "exact_equal_liquidity",
    "raid_depth_range_bucket",
    "reclaim_latency_bucket",
    "cisd_progress_bucket",
    "protected_risk_range_bucket",
    "source_range_state_bucket",
    "body_fraction_bucket",
    "rejection_wick_bucket",
    "close_location_bucket",
)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _stat(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = [_d(row["primary_net_r"]) for row in rows]
    positive = sum((value for value in values if value > 0), Decimal(0))
    negative = -sum((value for value in values if value < 0), Decimal(0))
    target = sum(1 for row in rows if "TARGET" in str(row["exit_reason"]))
    stop = sum(1 for row in rows if "STOP" in str(row["exit_reason"]))
    total = sum(values, Decimal(0))
    return {
        "trades": len(rows),
        "total_primary_r": str(total),
        "mean_primary_r": str(total / len(rows)) if rows else None,
        "profit_factor": str(positive / negative) if negative > 0 else None,
        "target_rate": str(Decimal(target) / len(rows)) if rows else None,
        "stop_rate": str(Decimal(stop) / len(rows)) if rows else None,
    }


def _group(rows: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {name: _stat(items) for name, items in sorted(groups.items())}


def _close_before(bars: Sequence[Any], opens: Sequence[datetime], at: datetime) -> Decimal | None:
    pos = bisect.bisect_left(opens, at) - 1
    return None if pos < 0 else bars[pos].close


def _calendar_return(
    bars: Sequence[Any], opens: Sequence[datetime], *, at: datetime, days: int
) -> Decimal | None:
    recent = _close_before(bars, opens, at)
    past = _close_before(bars, opens, at - timedelta(days=days))
    if recent is None or past is None or past <= 0:
        return None
    return recent / past - Decimal(1)


def _trend_sign(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value > 0:
        return "bull"
    if value < 0:
        return "bear"
    return "flat"


def _aligned_trend(side: str, value: Decimal | None) -> str:
    if value is None:
        return "missing"
    aligned = value if side == "long" else -value
    if aligned > 0:
        return "with_trade"
    if aligned < 0:
        return "against_trade"
    return "flat"


def _json_trade(trade: r3.RoutedTrade) -> dict[str, Any]:
    raw = asdict(trade)
    return {
        key: (
            value.isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, Decimal)
            else value
        )
        for key, value in raw.items()
    }


def _reproduce_selected(
    source_root: Path, target_root: Path
) -> tuple[Any, list[tuple[r3.Setup, r3.RoutedTrade]], dict[str, Any]]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD 10Y corpus")
    episodes, source_index = repair._load_targets_fail_closed(target_root)
    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, _funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close
    opens = tuple(bar.opened_at for bar in evidence.bars)
    rows: list[
        tuple[
            r3.Setup,
            dict[tuple[str, str], tuple[Decimal | None, r3.RoutedTrade | None, str]],
        ]
    ] = []
    unmatched = 0
    for setup in setups:
        signal = setup.context.signal
        episode_id = source_index.get(
            (signal.cisd_at, signal.side.value, setup.context.timeframe, signal.target)
        )
        if episode_id is None:
            unmatched += 1
            continue
        target_rows = episodes[episode_id]
        outcomes = {
            action: r3._simulate(setup, target_rows, evidence, opens, action)
            for action in r3.ACTIONS
        }
        rows.append((setup, outcomes))
    router = r3._fit_router(rows)
    selected: list[tuple[r3.Setup, r3.RoutedTrade]] = []
    busy_until = r3.EVAL_OPEN
    for setup, outcomes in rows:
        _action, outcome = r3._choose(setup, outcomes, router)
        if outcome is None:
            continue
        _value, trade, _reason = outcome
        if trade is None or trade.entry_at < busy_until:
            continue
        selected.append((setup, trade))
        busy_until = trade.exit_at
    return evidence, selected, {
        "retained_bars": provenance["retained_bars"],
        "setups": len(setups),
        "routed_rows": len(rows),
        "unmatched": unmatched,
        "ambiguous_source_opposite_keys": repair._LAST_AMBIGUOUS_KEYS,
    }


def _record(
    setup: r3.Setup,
    trade: r3.RoutedTrade,
    bars: Sequence[Any],
    opens: Sequence[datetime],
) -> dict[str, Any]:
    ctx = setup.context
    row = _json_trade(trade)
    row["year"] = trade.entry_at.year
    for feature in CONTEXT_FEATURES:
        row[feature] = str(getattr(ctx, feature))
    row["weekday"] = str(ctx.weekday)
    ret5 = _calendar_return(bars, opens, at=trade.entry_at, days=5)
    ret20 = _calendar_return(bars, opens, at=trade.entry_at, days=20)
    row["return_5d"] = None if ret5 is None else str(ret5)
    row["return_20d"] = None if ret20 is None else str(ret20)
    row["trend_5d"] = _trend_sign(ret5)
    row["trend_20d"] = _trend_sign(ret20)
    row["aligned_trend_5d"] = _aligned_trend(trade.side, ret5)
    row["aligned_trend_20d"] = _aligned_trend(trade.side, ret20)
    risk = abs(trade.entry - trade.stop)
    reward = abs(trade.target - trade.entry)
    row["risk_abs"] = str(risk)
    row["reward_abs"] = str(reward)
    row["structural_rr"] = str(reward / risk) if risk > 0 else None
    return row


def _period(rows: Sequence[dict[str, Any]], years: frozenset[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _feature_shift(
    baseline: Sequence[dict[str, Any]], recent: Sequence[dict[str, Any]], feature: str
) -> dict[str, Any]:
    values = sorted({str(row[feature]) for row in baseline} | {str(row[feature]) for row in recent})
    result: dict[str, Any] = {}
    for value in values:
        b = [row for row in baseline if str(row[feature]) == value]
        r = [row for row in recent if str(row[feature]) == value]
        result[value] = {
            "baseline_share": str(Decimal(len(b)) / len(baseline)) if baseline else None,
            "recent_share": str(Decimal(len(r)) / len(recent)) if recent else None,
            "baseline": _stat(b),
            "recent": _stat(r),
        }
    return result


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = _reproduce_selected(source_root, target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    rows = [_record(setup, trade, evidence.bars, opens) for setup, trade in selected]
    if len(rows) != 5885:
        raise ValueError(f"R3 reproduction drift: {len(rows)} executed trades")
    total = sum((_d(row["primary_net_r"]) for row in rows), Decimal(0))
    if abs(total - Decimal("707.7490491424")) > Decimal("0.0001"):
        raise ValueError(f"R3 R-total reproduction drift: {total}")

    baseline = _period(rows, BASELINE_YEARS)
    recent = _period(rows, RECENT_YEARS)
    yearly = {
        str(year): _stat([row for row in rows if int(row["year"]) == year])
        for year in range(2016, 2027)
    }
    diagnostic_features = (
        "side",
        "source_timeframe",
        "entry_mode",
        "target_route",
        "session_bucket",
        "prior_body_alignment",
        "trend_5d",
        "trend_20d",
        "aligned_trend_5d",
        "aligned_trend_20d",
        *CONTEXT_FEATURES[1:],
    )
    feature_shifts = {
        feature: _feature_shift(baseline, recent, feature)
        for feature in diagnostic_features
    }

    short_recent = [row for row in recent if row["side"] == "short"]
    short_recent_bull20 = [row for row in short_recent if row["trend_20d"] == "bull"]
    short_recent_not_bull20 = [row for row in short_recent if row["trend_20d"] != "bull"]
    long_recent = [row for row in recent if row["side"] == "long"]

    payload = {
        "schema": "qore.turtle_soup_xauusd_r3.causal_regime_forensics.v1",
        "identity": IDENTITY,
        "source_r3_run": 35256772043,
        "source_r3_artifact": 10513151886,
        "evidence_status": "CONSUMED_R3_AND_CIBO_10Y_CAUSAL_DIAGNOSTIC_NOT_FRESH_HOLDOUT",
        "reproduction": reproduction,
        "full": _stat(rows),
        "baseline_2016_2019": _stat(baseline),
        "recent_2024_2026": _stat(recent),
        "yearly": yearly,
        "baseline_by_side": _group(baseline, "side"),
        "recent_by_side": _group(recent, "side"),
        "recent_short_in_bull_20d": _stat(short_recent_bull20),
        "recent_short_not_in_bull_20d": _stat(short_recent_not_bull20),
        "recent_long": _stat(long_recent),
        "feature_shifts": feature_shifts,
        "diagnosis": {
            "question": "WHAT_PRE_ENTRY_STATE_CHANGED_WHEN_R3_JOURNEY_COMPLETION_DEGRADED_AFTER_2023",
            "trend_features_are_causal": True,
            "post_entry_features_used_for_diagnosis_only": ["exit_reason", "primary_net_r"],
            "rules_promoted": False,
            "fresh_holdout_consumed": False,
        },
        "governance": {
            "diagnostic_only": True,
            "automatic_filter_promotion": False,
            "automatic_candidate_promotion": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "causal-regime-forensics.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "enriched-trades.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
