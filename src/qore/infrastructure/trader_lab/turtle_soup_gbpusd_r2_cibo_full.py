"""GBPUSD Turtle Soup R2 modeled from CIBO pre-entry market intelligence.

R2 deliberately separates model-development from temporal validation inside the
already-consumed ten-year CIBO corpus.  The 2016-09-17..2022-09-17 block may
fit transparent feature effects; 2022-09-17..2026-09-17 is never used to fit
those effects.  The whole corpus remains consumed development evidence, not a
fresh holdout.

Only information available before NEXT_SOURCE_OPEN may select a trade. Forward
MFE/MAE and target-time statistics are diagnostics only and never model inputs.
"""
from __future__ import annotations

import json
import sys
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as journey
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_r1 as r1
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
    SourceCandle,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_GBPUSD_R2_CIBO_FULL_CONTEXT"
SYMBOL = "GBPUSD"
SOURCE_RUN_ID = 35166210458
SOURCE_ARTIFACT_ID = 10475449182
SOURCE_ARTIFACT_DIGEST = "sha256:77d5b65ce3c6763e3ac5f620e4167d4ef071bfe1c13746cd5ca7ad9788268dcf"
EVAL_OPEN = datetime(2016, 9, 17, tzinfo=UTC)
TRAIN_CLOSE = datetime(2022, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")
SHRINKAGE_N = Decimal(120)
NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class ContextSignal:
    signal: r1.Signal
    timeframe: str
    side: str
    session: str
    weekday: str
    prior_body_alignment: str
    fvg_before_entry: str
    exact_equal_liquidity: str
    raid_depth_range_bucket: str
    reclaim_latency_bucket: str
    cisd_progress_bucket: str
    protected_risk_range_bucket: str
    source_range_state_bucket: str
    body_fraction_bucket: str
    rejection_wick_bucket: str
    close_location_bucket: str
    projected_r_bucket: str
    target_distance_range_bucket: str


FEATURES = (
    "timeframe",
    "side",
    "session",
    "weekday",
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
    "projected_r_bucket",
    "target_distance_range_bucket",
)


def _bucket(value: Decimal | None, cuts: tuple[Decimal, ...]) -> str:
    if value is None:
        return "missing"
    for index, cut in enumerate(cuts):
        if value <= cut:
            return f"q{index + 1}:<=${cut}".replace("$", "")
    return f"q{len(cuts) + 1}:>{cuts[-1]}"


def _latency_bucket(minutes: int | None) -> str:
    if minutes is None:
        return "missing"
    if minutes <= 5:
        return "<=5m"
    if minutes <= 15:
        return "6-15m"
    if minutes <= 30:
        return "16-30m"
    if minutes <= 60:
        return "31-60m"
    if minutes <= 120:
        return "61-120m"
    return ">120m"


def _first_reclaim_latency(c2: SourceCandle, c1: SourceCandle, side: Side, raid_at: datetime) -> int | None:
    level = c1.low if side is Side.LONG else c1.high
    for bar in c2.m5:
        if bar.opened_at < raid_at:
            continue
        reclaimed = bar.close > level if side is Side.LONG else bar.close < level
        if reclaimed:
            return int((bar.closed_at - raid_at).total_seconds() // 60)
    return None


def _fvg_before_entry(bars: Sequence[Bar], raid_at: datetime, entry_at: datetime, side: Side) -> bool:
    sample = [bar for bar in bars if raid_at <= bar.opened_at < entry_at]
    for index in range(2, len(sample)):
        first, third = sample[index - 2], sample[index]
        if side is Side.LONG and third.low > first.high:
            return True
        if side is Side.SHORT and third.high < first.low:
            return True
    return False


def _geometry(candle: SourceCandle, side: Side) -> tuple[Decimal, Decimal, Decimal]:
    span = candle.high - candle.low
    if span <= 0:
        return Decimal(0), Decimal(0), Decimal("0.5")
    body = abs(candle.close - candle.open) / span
    if side is Side.LONG:
        wick = (min(candle.open, candle.close) - candle.low) / span
        close_location = (candle.close - candle.low) / span
    else:
        wick = (candle.high - max(candle.open, candle.close)) / span
        close_location = (candle.high - candle.close) / span
    return body, max(wick, Decimal(0)), close_location


def _same_boundary(candle: SourceCandle, side: Side) -> Decimal:
    return candle.low if side is Side.LONG else candle.high


def _context_signals(evidence: r1.Evidence) -> tuple[list[ContextSignal], dict[str, int]]:
    all_context: list[ContextSignal] = []
    funnel: dict[str, int] = defaultdict(int)
    for timeframe, candles, minutes in (
        ("H1", build_h1(evidence.bars), 60),
        ("H4", build_h4(evidence.bars), 240),
    ):
        signals, raw_funnel = r1._source_signals(candles, timeframe)
        for key, value in raw_funnel.items():
            funnel[key] += value
        index = {candle.opened_at: i for i, candle in enumerate(candles)}
        for signal in signals:
            pos = index.get(signal.c2_opened_at)
            if pos is None or pos <= 0:
                continue
            c2 = candles[pos]
            c1 = candles[pos - 1]
            side = signal.side
            source_range = c2.high - c2.low
            previous = candles[max(0, pos - 20):pos]
            mean_prior_range = (
                sum((item.high - item.low for item in previous), Decimal(0)) / len(previous)
                if previous else None
            )
            raid_level = c1.low if side is Side.LONG else c1.high
            raid_extreme = c2.low if side is Side.LONG else c2.high
            raid_depth = abs(raid_extreme - raid_level)
            raid_units = None if not mean_prior_range or mean_prior_range <= 0 else raid_depth / mean_prior_range
            reclaim_latency = _first_reclaim_latency(c2, c1, side, signal.raid_at)
            cisd_progress = Decimal(str((signal.cisd_at - c2.opened_at).total_seconds() / 60)) / Decimal(minutes)
            risk = signal.entry - signal.protected_swing if side is Side.LONG else signal.protected_swing - signal.entry
            protected_ratio = None if source_range <= 0 else risk / source_range
            range_state = None if not mean_prior_range or mean_prior_range <= 0 else source_range / mean_prior_range
            body, wick, close_location = _geometry(c2, side)
            target_distance = signal.target - signal.entry if side is Side.LONG else signal.entry - signal.target
            target_ratio = None if source_range <= 0 else target_distance / source_range
            peers = [
                _same_boundary(item, side)
                for item in candles[max(0, pos - 21):pos - 1]
            ]
            equal = any(level == _same_boundary(c1, side) for level in peers)
            local = signal.raid_at.astimezone(NY)
            all_context.append(ContextSignal(
                signal=signal,
                timeframe=timeframe,
                side=side.value,
                session=signal.session_bucket,
                weekday=local.strftime("%A"),
                prior_body_alignment=signal.prior_body_alignment,
                fvg_before_entry="yes" if _fvg_before_entry(c2.m5, signal.raid_at, signal.entry_at, side) else "no",
                exact_equal_liquidity="yes" if equal else "no",
                raid_depth_range_bucket=_bucket(raid_units, (Decimal("0.05"), Decimal("0.10"), Decimal("0.25"), Decimal("0.50"))),
                reclaim_latency_bucket=_latency_bucket(reclaim_latency),
                cisd_progress_bucket=_bucket(cisd_progress, (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))),
                protected_risk_range_bucket=_bucket(protected_ratio, (Decimal("0.25"), Decimal("0.50"), Decimal("1.0"), Decimal("2.0"))),
                source_range_state_bucket=_bucket(range_state, (Decimal("0.75"), Decimal("1.0"), Decimal("1.5"), Decimal("2.0"))),
                body_fraction_bucket=_bucket(body, (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))),
                rejection_wick_bucket=_bucket(wick, (Decimal("0.10"), Decimal("0.25"), Decimal("0.50"))),
                close_location_bucket=_bucket(close_location, (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))),
                projected_r_bucket=_bucket(signal.projected_r, (Decimal("0.5"), Decimal("1.0"), Decimal("1.5"), Decimal("2.5"))),
                target_distance_range_bucket=_bucket(target_ratio, (Decimal("0.5"), Decimal("1.0"), Decimal("2.0"), Decimal("4.0"))),
            ))
    all_context.sort(key=lambda item: (item.signal.entry_at, 0 if item.timeframe == "H4" else 1))
    return all_context, dict(funnel)


def _simulate_fast(evidence: r1.Evidence, signal: r1.Signal, closes: Sequence[datetime]) -> r1.Trade:
    stop = signal.protected_swing
    risk = signal.entry - stop if signal.side is Side.LONG else stop - signal.entry
    reward = signal.target - signal.entry if signal.side is Side.LONG else signal.entry - signal.target
    start = bisect_left(closes, signal.entry_at)
    end_at = min(signal.entry_at + timedelta(hours=24), EVAL_CLOSE)
    end = bisect_left(closes, end_at)
    path = evidence.bars[start:end]
    if not path:
        raise ValueError("empty execution path")
    exit_at = path[-1].closed_at
    exit_price = path[-1].close
    reason = "time-24h"
    gross = ((exit_price - signal.entry) / risk if signal.side is Side.LONG else (signal.entry - exit_price) / risk)
    for bar in path:
        if signal.side is Side.LONG:
            if bar.open <= stop:
                exit_at, exit_price, reason, gross = bar.opened_at, bar.open, "gap-stop", (bar.open - signal.entry) / risk; break
            if bar.open >= signal.target:
                exit_at, exit_price, reason, gross = bar.opened_at, signal.target, "gap-target-capped", reward / risk; break
            stop_touch, target_touch = bar.low <= stop, bar.high >= signal.target
        else:
            if bar.open >= stop:
                exit_at, exit_price, reason, gross = bar.opened_at, bar.open, "gap-stop", (signal.entry - bar.open) / risk; break
            if bar.open <= signal.target:
                exit_at, exit_price, reason, gross = bar.opened_at, signal.target, "gap-target-capped", reward / risk; break
            stop_touch, target_touch = bar.high >= stop, bar.low <= signal.target
        if stop_touch and target_touch:
            exit_at, exit_price, reason, gross = bar.closed_at, stop, "stop-first", Decimal(-1); break
        if stop_touch:
            exit_at, exit_price, reason, gross = bar.closed_at, stop, "stop", Decimal(-1); break
        if target_touch:
            exit_at, exit_price, reason, gross = bar.closed_at, signal.target, "target", reward / risk; break
    return r1.Trade(
        timeframe=signal.timeframe, side=signal.side, c1_opened_at=signal.c1_opened_at,
        c2_opened_at=signal.c2_opened_at, raid_at=signal.raid_at, cisd_at=signal.cisd_at,
        entry_at=signal.entry_at, exit_at=exit_at, entry=signal.entry, stop=stop,
        target=signal.target, exit_price=exit_price, projected_r=signal.projected_r,
        gross_r=gross, primary_net_r=gross - PRIMARY_FRICTION_R,
        stress_net_r=gross - STRESS_FRICTION_R, exit_reason=reason,
        session_bucket=signal.session_bucket, prior_body_alignment=signal.prior_body_alignment,
    )


def _fit_model(rows: Sequence[tuple[ContextSignal, r1.Trade]]) -> dict[str, Any]:
    train = [(ctx, trade) for ctx, trade in rows if EVAL_OPEN <= trade.entry_at < TRAIN_CLOSE]
    if not train:
        raise ValueError("empty R2 training set")
    baseline = sum((trade.primary_net_r for _, trade in train), Decimal(0)) / len(train)
    effects: dict[str, dict[str, dict[str, str | int]]] = {}
    for feature in FEATURES:
        groups: dict[str, list[Decimal]] = defaultdict(list)
        for ctx, trade in train:
            groups[str(getattr(ctx, feature))].append(trade.primary_net_r)
        feature_rows: dict[str, dict[str, str | int]] = {}
        for value, labels in sorted(groups.items()):
            mean = sum(labels, Decimal(0)) / len(labels)
            n = Decimal(len(labels))
            shrunk = (n * mean + SHRINKAGE_N * baseline) / (n + SHRINKAGE_N)
            feature_rows[value] = {"n": len(labels), "mean_primary_r": str(mean), "shrunk_mean_primary_r": str(shrunk), "effect": str(shrunk - baseline)}
        effects[feature] = feature_rows
    return {
        "schema": "qore.turtle_soup_gbpusd_r2.model.v1",
        "identity": IDENTITY,
        "candidate_base": r1.IDENTITY,
        "training_open": EVAL_OPEN.isoformat(),
        "training_close": TRAIN_CLOSE.isoformat(),
        "validation_open": TRAIN_CLOSE.isoformat(),
        "validation_close": EVAL_CLOSE.isoformat(),
        "training_candidates": len(train),
        "baseline_primary_r": str(baseline),
        "shrinkage_n": str(SHRINKAGE_N),
        "features": list(FEATURES),
        "effects": effects,
        "selection_rule": "predicted_primary_r_gt_0",
        "post_entry_features_forbidden": ["mfe", "mae", "target_hit", "target_time", "exit_reason", "future_price"],
    }


def _predict(ctx: ContextSignal, model: dict[str, Any]) -> Decimal:
    baseline = Decimal(str(model["baseline_primary_r"]))
    effects = model["effects"]
    total = Decimal(0)
    used = 0
    for feature in FEATURES:
        value = str(getattr(ctx, feature))
        row = effects.get(feature, {}).get(value)
        if row is None:
            continue
        total += Decimal(str(row["effect"]))
        used += 1
    return baseline if used == 0 else baseline + total / Decimal(used)


def _select_and_replay(rows: Sequence[tuple[ContextSignal, r1.Trade]], model: dict[str, Any], opened_at: datetime, closed_at: datetime) -> list[r1.Trade]:
    eligible = [(ctx, trade) for ctx, trade in rows if opened_at <= trade.entry_at < closed_at and _predict(ctx, model) > 0]
    eligible.sort(key=lambda item: (item[1].entry_at, 0 if item[0].timeframe == "H4" else 1))
    selected: list[r1.Trade] = []
    busy_until = opened_at
    for _ctx, trade in eligible:
        if trade.entry_at < busy_until:
            continue
        selected.append(trade)
        busy_until = trade.exit_at
    return selected


def _stat(trades: Sequence[r1.Trade], attr: str = "primary_net_r") -> dict[str, Any]:
    values = [getattr(trade, attr) for trade in trades]
    return r1._stat(values)


def _groups(trades: Sequence[r1.Trade], key: str) -> dict[str, Any]:
    grouped: dict[str, list[r1.Trade]] = defaultdict(list)
    for trade in trades:
        value = getattr(trade, key)
        if hasattr(value, "value"):
            value = value.value
        grouped[str(value)].append(trade)
    return {name: _stat(items) for name, items in sorted(grouped.items())}


def _temporal(trades: Sequence[r1.Trade], kind: str) -> dict[str, Any]:
    grouped: dict[str, list[r1.Trade]] = defaultdict(list)
    for trade in trades:
        if kind == "year":
            key = str(trade.entry_at.year)
        else:
            key = f"{trade.entry_at.year}-Q{((trade.entry_at.month - 1)//3)+1}"
        grouped[key].append(trade)
    return {key: _stat(items) for key, items in sorted(grouped.items())}


def _diagnostic_forward(evidence: r1.Evidence, trades: Sequence[r1.Trade], closes: Sequence[datetime]) -> dict[str, Any]:
    mfe240: list[Decimal] = []; mae240: list[Decimal] = []; mfe1440: list[Decimal] = []; mae1440: list[Decimal] = []
    target_minutes: list[int] = []
    for trade in trades:
        risk = abs(trade.entry - trade.stop)
        if risk <= 0:
            continue
        start = bisect_left(closes, trade.entry_at)
        for horizon, mfes, maes in ((240, mfe240, mae240), (1440, mfe1440, mae1440)):
            end = bisect_left(closes, trade.entry_at + timedelta(minutes=horizon))
            path = evidence.bars[start:end]
            if not path:
                continue
            if trade.side is Side.LONG:
                mfe = (max(bar.high for bar in path) - trade.entry) / risk
                mae = (trade.entry - min(bar.low for bar in path)) / risk
            else:
                mfe = (trade.entry - min(bar.low for bar in path)) / risk
                mae = (max(bar.high for bar in path) - trade.entry) / risk
            mfes.append(max(mfe, Decimal(0))); maes.append(max(mae, Decimal(0)))
        if "target" in trade.exit_reason:
            target_minutes.append(int((trade.exit_at - trade.entry_at).total_seconds() // 60))
    def med(values: Sequence[Decimal]) -> str | None:
        return None if not values else str(median(values))
    return {
        "diagnostic_only_not_model_inputs": True,
        "median_mfe_240m_r": med(mfe240), "median_mae_240m_r": med(mae240),
        "median_mfe_1440m_r": med(mfe1440), "median_mae_1440m_r": med(mae1440),
        "median_target_time_minutes": None if not target_minutes else float(median(target_minutes)),
    }


def run(source_root: Path, output: Path) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != SYMBOL or provenance["retained_bars"] != 745274:
        raise ValueError("unexpected GBPUSD CIBO corpus")
    closes = [bar.opened_at for bar in evidence.bars]
    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = EVAL_OPEN, EVAL_CLOSE
        contexts, funnel = _context_signals(evidence)
        rows = [(ctx, _simulate_fast(evidence, ctx.signal, closes)) for ctx in contexts]
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close
    model = _fit_model(rows)
    full = _select_and_replay(rows, model, EVAL_OPEN, EVAL_CLOSE)
    validation = _select_and_replay(rows, model, TRAIN_CLOSE, EVAL_CLOSE)
    training = _select_and_replay(rows, model, EVAL_OPEN, TRAIN_CLOSE)
    payload = {
        "schema": "qore.turtle_soup_gbpusd_r2.cibo_full_context_replay.v1",
        "identity": IDENTITY,
        "symbol": SYMBOL,
        "evidence_status": "CONSUMED_DEVELOPMENT_REPLAY_WITH_INTERNAL_TEMPORAL_VALIDATION_NOT_FRESH_HOLDOUT",
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "retained_m5_bars": provenance["retained_bars"],
        "model": model,
        "candidate_contract": {
            "base_pattern": "PRIOR_CANDLE_RAID_EXACT_C2_CAUSAL_CISD_NEXT_SOURCE_OPEN",
            "stop": "PROTECTED_SWING_EXACT_NO_OFFSET",
            "target": "UNTOUCHED_C1_OPPOSITE_BOUNDARY",
            "timeframes": ["H1", "H4"],
            "sides": ["long", "short"],
            "single_position": True,
            "same_m5_bar_tie": "STOP_FIRST",
            "selection": "transparent_smoothed_pre_entry_context_score_predicted_primary_r_gt_0",
        },
        "candidate_pool": len(rows),
        "training_selected": len(training),
        "validation_selected": len(validation),
        "full_selected": len(full),
        "training_primary": _stat(training),
        "validation_primary": _stat(validation),
        "validation_stress_010r": _stat(validation, "stress_net_r"),
        "full_primary": _stat(full),
        "full_stress_010r": _stat(full, "stress_net_r"),
        "full_by_side": _groups(full, "side"),
        "full_by_timeframe": _groups(full, "timeframe"),
        "full_by_session_diagnostic": _groups(full, "session_bucket"),
        "full_by_prior_body_diagnostic": _groups(full, "prior_body_alignment"),
        "full_by_year": _temporal(full, "year"),
        "full_by_quarter": _temporal(full, "quarter"),
        "validation_by_year": _temporal(validation, "year"),
        "validation_by_quarter": _temporal(validation, "quarter"),
        "forward_diagnostics_full": _diagnostic_forward(evidence, full, closes),
        "funnel": funnel,
        "governance": {
            "fresh_holdout": False,
            "validation_block_used_for_fit": False,
            "post_entry_leakage_allowed": False,
            "automatic_promotion_allowed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "model.json").write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
    (output / "report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "trades-full.json").write_text(json.dumps([r1._json_trade(item) for item in full], indent=2, sort_keys=True) + "\n")
    (output / "trades-validation.json").write_text(json.dumps([r1._json_trade(item) for item in validation], indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module SOURCE_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
