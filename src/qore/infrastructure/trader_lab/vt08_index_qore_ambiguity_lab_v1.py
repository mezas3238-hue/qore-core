"""Frozen, exhaustive QORE experiment over explicit VT-08 Index ambiguities."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_c2_positional_r1_backtest import (
    ModeledTrade,
    _load_market,
    _max_drawdown_r,
    _max_losing_streak,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    OWNER_ENTRY_ANCHORS_NY,
    Vt08IndexC2R1Bar,
    Vt08IndexC2R1ProtectedSwing,
    _aggregate_contiguous_m15,
    _latest_complete_source_days,
    _window_bars,
    protected_swings_in_candle2,
    resolve_daily_bias,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_qore_ambiguity_lab.v1"
LAB_ID = "VT08_INDEX_QORE_AMBIGUITY_LAB_V1"
FREEZE_DOCUMENT = "docs/research/VT08-INDEX-QORE-AMBIGUITY-LAB-V1-FREEZE.md"
CONSUMED_START = "2024-08-13"
CONSUMED_END = "2026-09-11"
_NY = ZoneInfo("America/New_York")


class AmbiguityLabError(InfrastructureError):
    __slots__ = ()


class ClosurePolicy(StrEnum):
    C2_ONLY = "c2-only"
    C2_OR_C3_BODY_CLOSE = "c2-or-c3-body-close"
    C2_OR_C3_BODY_ENGULF = "c2-or-c3-body-engulf"
    C2_OR_C3_RANGE_ENGULF = "c2-or-c3-range-engulf"


class SwingPolicy(StrEnum):
    UNIQUE_ONLY = "unique-only"
    FIRST_CAUSAL = "first-causal"
    LATEST_CAUSAL = "latest-causal"
    FARTHEST_STRUCTURAL = "farthest-structural"


class StopPolicy(StrEnum):
    PROTECTED_SWING_EXTREME = "protected-swing-extreme"
    CISD_LEVEL = "cisd-level"


class TargetPolicy(StrEnum):
    R1_5 = "1.5r"
    R2 = "2r"
    R2_5 = "2.5r"
    R3 = "3r"

    @property
    def multiple(self) -> Decimal:
        return {
            TargetPolicy.R1_5: Decimal("1.5"),
            TargetPolicy.R2: Decimal("2"),
            TargetPolicy.R2_5: Decimal("2.5"),
            TargetPolicy.R3: Decimal("3"),
        }[self]


class LifecyclePolicy(StrEnum):
    NEXT_H4_BOUNDARY = "next-h4-boundary"
    TWO_H4_BOUNDARIES = "two-h4-boundaries"

    @property
    def m15_bars(self) -> int:
        return 16 if self is LifecyclePolicy.NEXT_H4_BOUNDARY else 32


class DailyPolicy(StrEnum):
    UNIQUE_ONLY = "unique-only"
    FIRST_CHRONOLOGICAL = "first-chronological"


@dataclass(frozen=True, slots=True)
class Variant:
    closure: ClosurePolicy
    swing: SwingPolicy
    stop: StopPolicy
    target: TargetPolicy
    lifecycle: LifecyclePolicy
    daily: DailyPolicy

    @property
    def variant_id(self) -> str:
        material = "|".join(
            (self.closure, self.swing, self.stop, self.target, self.lifecycle, self.daily)
        )
        return "V-" + sha256(material.encode()).hexdigest()[:12]

    def payload(self) -> dict[str, str]:
        return {
            "variant_id": self.variant_id,
            "closure": self.closure,
            "swing": self.swing,
            "stop": self.stop,
            "target": self.target,
            "lifecycle": self.lifecycle,
            "daily": self.daily,
        }


@dataclass(frozen=True, slots=True)
class Signal:
    symbol: str
    decision_at: datetime
    anchor: int
    side: DemoTradingSetupSide
    protected_swing: Vt08IndexC2R1ProtectedSwing
    closure_kind: str


def variants() -> tuple[Variant, ...]:
    result = tuple(
        Variant(*items)
        for items in itertools.product(
            tuple(ClosurePolicy),
            tuple(SwingPolicy),
            tuple(StopPolicy),
            tuple(TargetPolicy),
            tuple(LifecyclePolicy),
            tuple(DailyPolicy),
        )
    )
    if len(result) != 512 or len({item.variant_id for item in result}) != 512:
        raise AmbiguityLabError("frozen grid cardinality drifted")
    return result


def _closure(
    *,
    policy: ClosurePolicy,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
    decision_at: datetime,
    side: DemoTradingSetupSide,
) -> tuple[Vt08IndexC2R1Bar, Vt08IndexC2R1Bar, str] | None:
    local = decision_at.astimezone(_NY)
    reference = _aggregate_contiguous_m15(
        bars_by_open, opened_at_local=local - timedelta(hours=8), count=16
    )
    c2 = _aggregate_contiguous_m15(
        bars_by_open, opened_at_local=local - timedelta(hours=4), count=16
    )
    if reference is None or c2 is None:
        return None
    swept = (
        c2.low < reference.low if side is DemoTradingSetupSide.LONG else c2.high > reference.high
    )
    inside = (
        c2.close > reference.low if side is DemoTradingSetupSide.LONG else c2.close < reference.high
    )
    other_sweep = (
        c2.high > reference.high if side is DemoTradingSetupSide.LONG else c2.low < reference.low
    )
    if swept and inside and not other_sweep:
        return reference, c2, "c2"
    if policy is ClosurePolicy.C2_ONLY:
        return None

    c1 = _aggregate_contiguous_m15(
        bars_by_open, opened_at_local=local - timedelta(hours=12), count=16
    )
    failed_c2 = reference
    c3 = c2
    if c1 is None:
        return None
    swept = (
        failed_c2.low < c1.low if side is DemoTradingSetupSide.LONG else failed_c2.high > c1.high
    )
    failed = (
        failed_c2.close <= c1.low
        if side is DemoTradingSetupSide.LONG
        else failed_c2.close >= c1.high
    )
    if not (swept and failed):
        return None
    body_high = max(failed_c2.open, failed_c2.close)
    body_low = min(failed_c2.open, failed_c2.close)
    close_through = (
        c3.close > body_high if side is DemoTradingSetupSide.LONG else c3.close < body_low
    )
    if not close_through:
        return None
    if policy is ClosurePolicy.C2_OR_C3_BODY_ENGULF:
        engulf = c3.open <= body_low if side is DemoTradingSetupSide.LONG else c3.open >= body_high
        if not engulf:
            return None
    if policy is ClosurePolicy.C2_OR_C3_RANGE_ENGULF:
        engulf = (
            c3.high > failed_c2.high
            and c3.low < failed_c2.low
            and (
                c3.close > failed_c2.high
                if side is DemoTradingSetupSide.LONG
                else c3.close < failed_c2.low
            )
        )
        if not engulf:
            return None
    return c1, c3, "c3"


def _select_swing(
    swings: tuple[Vt08IndexC2R1ProtectedSwing, ...],
    *,
    policy: SwingPolicy,
    side: DemoTradingSetupSide,
) -> Vt08IndexC2R1ProtectedSwing | None:
    if not swings or (policy is SwingPolicy.UNIQUE_ONLY and len(swings) != 1):
        return None
    if policy in (SwingPolicy.UNIQUE_ONLY, SwingPolicy.FIRST_CAUSAL):
        return swings[0]
    if policy is SwingPolicy.LATEST_CAUSAL:
        return swings[-1]

    def price(item: Vt08IndexC2R1ProtectedSwing) -> Decimal:
        return item.price

    return min(swings, key=price) if side is DemoTradingSetupSide.LONG else max(swings, key=price)


def _signal(
    *,
    symbol: str,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
    decision_at: datetime,
    closure: ClosurePolicy,
    swing: SwingPolicy,
) -> Signal | None:
    local = decision_at.astimezone(_NY)
    source_days = _latest_complete_source_days(bars_by_open, before_local=local)
    if source_days is None:
        return None
    side = resolve_daily_bias(previous_day=source_days[0], current_day=source_days[1])
    if side is None:
        return None
    resolved = _closure(
        policy=closure, bars_by_open=bars_by_open, decision_at=decision_at, side=side
    )
    if resolved is None:
        return None
    reference, closure_bar, kind = resolved
    m15 = _window_bars(bars_by_open, opened_at=closure_bar.opened_at, count=16)
    if m15 is None:
        return None
    important = reference.low if side is DemoTradingSetupSide.LONG else reference.high
    selected = _select_swing(
        protected_swings_in_candle2(m15, side=side, important_level=important),
        policy=swing,
        side=side,
    )
    if selected is None:
        return None
    return Signal(symbol, decision_at, local.hour, side, selected, kind)


def _model(
    signal: Signal,
    variant: Variant,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
) -> ModeledTrade | None:
    entry_bar = bars_by_open.get(signal.decision_at.astimezone(UTC))
    if entry_bar is None:
        return None
    entry = entry_bar.open
    stop = (
        signal.protected_swing.price
        if variant.stop is StopPolicy.PROTECTED_SWING_EXTREME
        else signal.protected_swing.cisd_level
    )
    risk = entry - stop if signal.side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        return None
    target = (
        entry + variant.target.multiple * risk
        if signal.side is DemoTradingSetupSide.LONG
        else entry - variant.target.multiple * risk
    )
    if target <= 0:
        return None
    retained: list[Vt08IndexC2R1Bar] = []
    cursor = signal.decision_at.astimezone(UTC)
    for _ in range(variant.lifecycle.m15_bars):
        bar = bars_by_open.get(cursor)
        if bar is None:
            return None
        retained.append(bar)
        cursor += timedelta(minutes=15)
    exit_price = retained[-1].close
    exited_at = retained[-1].closed_at
    reason = "lifecycle"
    for bar in retained:
        if bar.low <= stop <= bar.high:
            exit_price, exited_at, reason = stop, bar.closed_at, "stop"
            break
        if bar.low <= target <= bar.high:
            exit_price, exited_at, reason = target, bar.closed_at, "target"
            break
    pnl = exit_price - entry if signal.side is DemoTradingSetupSide.LONG else entry - exit_price
    return ModeledTrade(
        symbol=signal.symbol,
        signal_at=signal.decision_at,
        exited_at=exited_at,
        anchor_hour_ny=signal.anchor,
        side=signal.side,
        entry=entry,
        stop=stop,
        target=target,
        exit_price=exit_price,
        exit_reason=reason,
        r_multiple=pnl / risk,
        return_rate=pnl / entry,
    )


def _metrics(trades: Iterable[ModeledTrade]) -> dict[str, object]:
    ordered = tuple(sorted(trades, key=lambda item: (item.signal_at, item.symbol)))
    values = tuple(item.r_multiple for item in ordered)
    wins = sum(value > 0 for value in values)
    gross_win = sum((value for value in values if value > 0), Decimal())
    gross_loss = -sum((value for value in values if value < 0), Decimal())
    total = sum(values, Decimal())
    return {
        "sample": len(values),
        "wins": wins,
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "profit_factor": str(gross_win / gross_loss) if gross_loss else None,
        "total_r": str(total),
        "mean_r": str(total / len(values)) if values else "0",
        "max_drawdown_r": str(_max_drawdown_r(values)),
        "max_losing_streak": _max_losing_streak(values),
    }


def _mean(trades: Iterable[ModeledTrade]) -> Decimal:
    values = tuple(item.r_multiple for item in trades)
    return sum(values, Decimal()) / len(values) if values else Decimal()


def _adjudicate(trades: tuple[ModeledTrade, ...]) -> dict[str, object]:
    ordered = tuple(sorted(trades, key=lambda item: (item.signal_at, item.symbol)))
    n = len(ordered)
    quartiles = tuple(ordered[(n * i) // 4 : (n * (i + 1)) // 4] for i in range(4))
    q_means = tuple(_mean(part) for part in quartiles)
    second_half = _mean(ordered[n // 2 :])
    market_counts = Counter(item.symbol for item in ordered)
    anchor_counts = Counter(item.anchor_hour_ny for item in ordered)
    loo_market = {
        market: _mean(item for item in ordered if item.symbol != market)
        for market in AUTHORIZED_MARKETS
    }
    loo_anchor = {
        str(anchor): _mean(item for item in ordered if item.anchor_hour_ny != anchor)
        for anchor in OWNER_ENTRY_ANCHORS_NY
    }
    metrics = _metrics(ordered)
    pf_raw = metrics["profit_factor"]
    pf = Decimal(str(pf_raw)) if pf_raw is not None else Decimal("Infinity")
    positive_quartiles = sum(value > 0 for value in q_means)
    checks = {
        "sample": n >= 120,
        "market_samples": all(market_counts[item] >= 25 for item in AUTHORIZED_MARKETS),
        "anchor_samples": all(anchor_counts[item] >= 20 for item in OWNER_ENTRY_ANCHORS_NY),
        "aggregate_mean": Decimal(str(metrics["mean_r"])) > 0,
        "profit_factor": pf >= Decimal("1.05"),
        "second_half": second_half > 0,
        "quartiles": positive_quartiles >= 3,
        "leave_one_market": all(value > 0 for value in loo_market.values()),
        "leave_one_anchor": all(value > 0 for value in loo_anchor.values()),
        "drawdown": Decimal(str(metrics["max_drawdown_r"])) <= 12,
    }
    worst_loo = min((*loo_market.values(), *loo_anchor.values()), default=Decimal())
    return {
        "metrics": metrics,
        "market_counts": dict(market_counts),
        "anchor_counts": {str(key): value for key, value in anchor_counts.items()},
        "quartile_mean_r": [str(value) for value in q_means],
        "positive_quartiles": positive_quartiles,
        "second_half_mean_r": str(second_half),
        "leave_one_market_out_mean_r": {key: str(value) for key, value in loo_market.items()},
        "leave_one_anchor_out_mean_r": {key: str(value) for key, value in loo_anchor.items()},
        "worst_leave_one_out_mean_r": str(worst_loo),
        "checks": checks,
        "eligible": all(checks.values()),
    }


def _rank(item: dict[str, object]) -> tuple[object, ...]:
    adj = item["adjudication"]
    assert isinstance(adj, dict)
    metrics = adj["metrics"]
    assert isinstance(metrics, dict)
    return (
        -int(adj["positive_quartiles"]),
        -Decimal(str(adj["worst_leave_one_out_mean_r"])),
        -Decimal(str(adj["second_half_mean_r"])),
        -Decimal(str(metrics["mean_r"])),
        Decimal(str(metrics["max_drawdown_r"])),
        str(item["variant_id"]),
    )


def _eligible(item: dict[str, object]) -> bool:
    adjudication = item["adjudication"]
    if not isinstance(adjudication, dict):
        raise AmbiguityLabError("variant adjudication must be an object")
    eligible = adjudication["eligible"]
    if not isinstance(eligible, bool):
        raise AmbiguityLabError("variant eligibility must be bool")
    return eligible


def build_report(*, nas100: Path, sp500: Path, us30: Path) -> dict[str, object]:
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    datasets: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    provenance: dict[str, object] = {}
    for symbol, path in paths.items():
        fingerprint, provider, checked_at, bars = _load_market(path, expected_symbol=symbol)
        datasets[symbol] = {item.opened_at.astimezone(UTC): item for item in bars}
        provenance[symbol] = {
            "provider_symbol": provider,
            "account_fingerprint": fingerprint,
            "checked_at": checked_at.isoformat(),
            "m15_bars": len(bars),
        }

    signal_cache: dict[tuple[str, ClosurePolicy, SwingPolicy], tuple[Signal, ...]] = {}
    for symbol, indexed in datasets.items():
        decisions = tuple(
            opened
            for opened in indexed
            if opened.astimezone(_NY).minute == 0
            and opened.astimezone(_NY).hour in OWNER_ENTRY_ANCHORS_NY
        )
        for closure, swing in itertools.product(tuple(ClosurePolicy), tuple(SwingPolicy)):
            signal_cache[(symbol, closure, swing)] = tuple(
                signal
                for decision in decisions
                if (
                    signal := _signal(
                        symbol=symbol,
                        bars_by_open=indexed,
                        decision_at=decision,
                        closure=closure,
                        swing=swing,
                    )
                )
                is not None
            )

    results: list[dict[str, object]] = []
    for variant in variants():
        trades: list[ModeledTrade] = []
        for symbol, indexed in datasets.items():
            by_day: dict[date, list[Signal]] = defaultdict(list)
            for signal in signal_cache[(symbol, variant.closure, variant.swing)]:
                by_day[signal.decision_at.astimezone(_NY).date()].append(signal)
            for day in sorted(by_day):
                signals = sorted(by_day[day], key=lambda item: item.decision_at)
                if variant.daily is DailyPolicy.UNIQUE_ONLY and len(signals) != 1:
                    continue
                modeled = _model(signals[0], variant, indexed)
                if modeled is not None:
                    trades.append(modeled)
        adjudication = _adjudicate(tuple(trades))
        results.append({**variant.payload(), "adjudication": adjudication})

    eligible = sorted((item for item in results if _eligible(item)), key=_rank)
    selected = eligible[0]["variant_id"] if eligible else None
    return {
        "schema": SCHEMA,
        "lab_id": LAB_ID,
        "research_only": True,
        "consumed_evidence": True,
        "fresh_holdout": False,
        "freeze_document": FREEZE_DOCUMENT,
        "grid_size": len(results),
        "provenance": provenance,
        "variants": results,
        "eligible_variant_count": len(eligible),
        "selection": selected or "NO_CANDIDATE",
        "governance": {
            "source_methodology_claim": False,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
            "fresh_validation_required": True,
            "cibo_used_for_signal_selection": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(nas100=args.nas100, sp500=args.sp500, us30=args.us30)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"grid_size": report["grid_size"], "selection": report["selection"]}))


if __name__ == "__main__":
    main()
