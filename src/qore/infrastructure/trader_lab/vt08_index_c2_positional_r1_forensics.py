"""Post-result failure forensics for frozen VT-08 Index C2 Positional R1.

This module diagnoses one already-consumed R1 replay artifact. It never changes
trading rules, never selects a profitable subset for execution, and grants no
promotion authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.research_block_bootstrap import _draw_start
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_c2_positional_r1_forensics.v1"
EXPECTED_REPLAY_SCHEMA = "qore.trader_lab.vt08_index_c2_positional_r1_backtest.v1"
EXPECTED_REPLAY_HEAD = "5232540cdb444473ddf0bfae01beb2e672cea344"
EXPECTED_FREEZE_COMMIT = "31bee8643cb09659a66e9ed793c1cb2bf9ba6353"
EXPECTED_MARKETS = ("NAS100", "SP500", "US30")
EXPECTED_ANCHORS = (2, 6, 10)
BOOTSTRAP_SEED = 20260913
BOOTSTRAP_PATHS = 10_000
BOOTSTRAP_BLOCK_LENGTHS = (5, 10, 20)
_NY = ZoneInfo("America/New_York")


class Vt08IndexC2R1ForensicsError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    signal_at: datetime
    anchor_hour_ny: int
    side: str
    exit_reason: str
    r_multiple: Decimal


@dataclass(frozen=True, slots=True)
class Stats:
    sample_size: int
    winning_trades: int
    losing_trades: int
    flat_trades: int
    total_r: Decimal
    mean_r: Decimal
    profit_factor: Decimal | None
    max_drawdown_r: Decimal
    max_losing_streak: int

    def payload(self) -> dict[str, object]:
        return {
            "sample_size": self.sample_size,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "flat_trades": self.flat_trades,
            "win_rate": (
                format(Decimal(self.winning_trades) / Decimal(self.sample_size), "f")
                if self.sample_size
                else "0"
            ),
            "total_r": format(self.total_r, "f"),
            "mean_r": format(self.mean_r, "f"),
            "profit_factor": (
                format(self.profit_factor, "f")
                if self.profit_factor is not None
                else None
            ),
            "max_drawdown_r": format(self.max_drawdown_r, "f"),
            "max_losing_streak": self.max_losing_streak,
        }


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08IndexC2R1ForensicsError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08IndexC2R1ForensicsError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08IndexC2R1ForensicsError(f"{name} must be non-empty text")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise Vt08IndexC2R1ForensicsError(f"{name} must be int")
    return value


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08IndexC2R1ForensicsError(f"{name} must be Decimal text") from error
    if not parsed.is_finite():
        raise Vt08IndexC2R1ForensicsError(f"{name} must be finite")
    return parsed


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08IndexC2R1ForensicsError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08IndexC2R1ForensicsError(f"{name} must be timezone-aware")
    return parsed


def _load(path: Path) -> tuple[dict[str, object], tuple[Trade, ...]]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexC2R1ForensicsError("cannot read R1 replay") from error
    payload = _object(decoded, name="R1 replay")
    if payload.get("schema") != EXPECTED_REPLAY_SCHEMA:
        raise Vt08IndexC2R1ForensicsError("unexpected R1 replay schema")
    if payload.get("research_only") is not True:
        raise Vt08IndexC2R1ForensicsError("R1 replay must remain research-only")
    if (
        payload.get("consumed_evidence") is not True
        or payload.get("fresh_holdout") is not False
    ):
        raise Vt08IndexC2R1ForensicsError("R1 replay governance drifted")
    governance = _object(payload.get("governance"), name="governance")
    if governance.get("pre_economic_freeze_commit") != EXPECTED_FREEZE_COMMIT:
        raise Vt08IndexC2R1ForensicsError("pre-economic freeze binding drifted")
    if any(
        governance.get(key) is not False
        for key in ("demo_eligible", "live_authorized", "production_authorized")
    ):
        raise Vt08IndexC2R1ForensicsError("R1 replay has forbidden execution authority")

    markets = _array(payload.get("markets"), name="markets")
    symbols: set[str] = set()
    trades: list[Trade] = []
    for market_raw in markets:
        market = _object(market_raw, name="market")
        symbol = _text(market.get("symbol"), name="symbol")
        symbols.add(symbol)
        for trade_raw in _array(market.get("trades"), name=f"{symbol}.trades"):
            trade = _object(trade_raw, name="trade")
            if _text(trade.get("symbol"), name="trade.symbol") != symbol:
                raise Vt08IndexC2R1ForensicsError("trade/market symbol mismatch")
            anchor = _integer(
                trade.get("anchor_hour_new_york"),
                name="anchor_hour_new_york",
            )
            if anchor not in EXPECTED_ANCHORS:
                raise Vt08IndexC2R1ForensicsError("unexpected R1 anchor")
            side = _text(trade.get("side"), name="side")
            if side not in {"long", "short"}:
                raise Vt08IndexC2R1ForensicsError("unexpected side")
            trades.append(
                Trade(
                    symbol=symbol,
                    signal_at=_timestamp(trade.get("signal_at"), name="signal_at"),
                    anchor_hour_ny=anchor,
                    side=side,
                    exit_reason=_text(trade.get("exit_reason"), name="exit_reason"),
                    r_multiple=_decimal(trade.get("r_multiple"), name="r_multiple"),
                )
            )
    if tuple(sorted(symbols)) != tuple(sorted(EXPECTED_MARKETS)):
        raise Vt08IndexC2R1ForensicsError("R1 market set drifted")
    trades.sort(key=lambda item: (item.signal_at, item.symbol))
    if not trades:
        raise Vt08IndexC2R1ForensicsError("R1 replay cannot be empty")
    return payload, tuple(trades)


def _stats(trades: tuple[Trade, ...]) -> Stats:
    values = tuple(item.r_multiple for item in trades)
    sample = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = sample - wins - losses
    total = sum(values, Decimal(0))
    mean = total / Decimal(sample) if sample else Decimal(0)
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
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
    return Stats(
        sample_size=sample,
        winning_trades=wins,
        losing_trades=losses,
        flat_trades=flats,
        total_r=total,
        mean_r=mean,
        profit_factor=profit_factor,
        max_drawdown_r=max_dd,
        max_losing_streak=max_streak,
    )


def _group(
    trades: tuple[Trade, ...],
    key: Callable[[Trade], str],
) -> dict[str, object]:
    buckets: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        buckets[key(trade)].append(trade)
    return {
        label: _stats(tuple(rows)).payload()
        for label, rows in sorted(buckets.items())
    }


def _chronological_partitions(
    trades: tuple[Trade, ...],
    parts: int,
) -> list[tuple[Trade, ...]]:
    result: list[tuple[Trade, ...]] = []
    n = len(trades)
    for index in range(parts):
        start = index * n // parts
        end = (index + 1) * n // parts
        result.append(trades[start:end])
    return result


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        raise Vt08IndexC2R1ForensicsError("quantile values cannot be empty")
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _max_drawdown_float(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def _circular_block_sample(
    values: tuple[float, ...],
    *,
    block_length: int,
    seed: int,
    replicate: int,
) -> list[float]:
    n = len(values)
    if n == 0 or block_length < 1:
        raise Vt08IndexC2R1ForensicsError("invalid block bootstrap input")
    sampled: list[float] = []
    draw = 0
    while len(sampled) < n:
        start = _draw_start(
            seed=seed,
            replicate=replicate,
            draw=draw,
            sample_size=n,
        )
        sampled.extend(values[(start + offset) % n] for offset in range(block_length))
        draw += 1
    return sampled[:n]


def _block_bootstrap(
    trades: tuple[Trade, ...],
    *,
    block_length: int,
    paths: int = BOOTSTRAP_PATHS,
) -> dict[str, object]:
    values = tuple(float(item.r_multiple) for item in trades)
    seed = BOOTSTRAP_SEED + block_length
    means: list[float] = []
    totals: list[float] = []
    drawdowns: list[float] = []
    for replicate in range(paths):
        sampled = _circular_block_sample(
            values,
            block_length=block_length,
            seed=seed,
            replicate=replicate,
        )
        total = sum(sampled)
        totals.append(total)
        means.append(total / len(sampled))
        drawdowns.append(_max_drawdown_float(sampled))
    return {
        "seed": seed,
        "paths": paths,
        "block_length_trades": block_length,
        "probability_mean_r_positive": sum(value > 0 for value in means) / paths,
        "mean_r_p05": _quantile(means, 0.05),
        "mean_r_p50": _quantile(means, 0.50),
        "mean_r_p95": _quantile(means, 0.95),
        "terminal_r_p05": _quantile(totals, 0.05),
        "terminal_r_p50": _quantile(totals, 0.50),
        "terminal_r_p95": _quantile(totals, 0.95),
        "max_drawdown_r_p50": _quantile(drawdowns, 0.50),
        "max_drawdown_r_p95": _quantile(drawdowns, 0.95),
    }


def _market_getter(trade: Trade) -> object:
    return trade.symbol


def _anchor_getter(trade: Trade) -> object:
    return trade.anchor_hour_ny


def _leave_one_out(
    trades: tuple[Trade, ...],
    *,
    dimension: str,
) -> dict[str, object]:
    labels: tuple[object, ...]
    getter: Callable[[Trade], object]
    if dimension == "market":
        labels = EXPECTED_MARKETS
        getter = _market_getter
    elif dimension == "anchor":
        labels = EXPECTED_ANCHORS
        getter = _anchor_getter
    else:
        raise Vt08IndexC2R1ForensicsError("unsupported leave-one-out dimension")
    return {
        str(label): _stats(
            tuple(item for item in trades if getter(item) != label)
        ).payload()
        for label in labels
    }


def build_report(path: Path) -> dict[str, object]:
    replay, trades = _load(path)
    halves = _chronological_partitions(trades, 2)
    quartiles = _chronological_partitions(trades, 4)
    annual = _group(
        trades,
        lambda item: str(item.signal_at.astimezone(_NY).year),
    )
    market_anchor = _group(
        trades,
        lambda item: f"{item.symbol}|{item.anchor_hour_ny:02d}:00",
    )
    market_side = _group(trades, lambda item: f"{item.symbol}|{item.side}")
    anchor_side = _group(
        trades,
        lambda item: f"{item.anchor_hour_ny:02d}:00|{item.side}",
    )
    quartile_stats = [_stats(part).payload() for part in quartiles]
    quartile_positive = sum(
        Decimal(cast(str, item["mean_r"])) > 0 for item in quartile_stats
    )
    bootstrap = {
        str(length): _block_bootstrap(trades, block_length=length)
        for length in BOOTSTRAP_BLOCK_LENGTHS
    }
    bootstrap_all_p05_nonpositive = all(
        cast(float, item["mean_r_p05"]) <= 0.0 for item in bootstrap.values()
    )

    aggregate = _stats(trades)
    replay_aggregate = _object(
        replay.get("aggregate_equal_risk_trade_economics"),
        name="replay aggregate",
    )
    if (
        _integer(replay_aggregate.get("sample_size"), name="sample_size")
        != aggregate.sample_size
    ):
        raise Vt08IndexC2R1ForensicsError("replay sample size does not reconcile")
    if _decimal(replay_aggregate.get("total_r"), name="total_r") != aggregate.total_r:
        raise Vt08IndexC2R1ForensicsError("replay total R does not reconcile")

    second_half = _stats(halves[1])
    return {
        "schema": SCHEMA,
        "research_only": True,
        "consumed_evidence": True,
        "methodology_mutation": False,
        "source_replay_head": EXPECTED_REPLAY_HEAD,
        "source_freeze_commit": EXPECTED_FREEZE_COMMIT,
        "aggregate": aggregate.payload(),
        "by_market": _group(trades, lambda item: item.symbol),
        "by_anchor_new_york": _group(
            trades,
            lambda item: f"{item.anchor_hour_ny:02d}:00",
        ),
        "by_side": _group(trades, lambda item: item.side),
        "by_year": annual,
        "by_market_anchor": market_anchor,
        "by_market_side": market_side,
        "by_anchor_side": anchor_side,
        "by_exit_reason": _group(trades, lambda item: item.exit_reason),
        "chronological_halves": {
            "first": _stats(halves[0]).payload(),
            "second": second_half.payload(),
        },
        "chronological_quartiles": {
            f"q{index + 1}": payload
            for index, payload in enumerate(quartile_stats)
        },
        "leave_one_market_out": _leave_one_out(trades, dimension="market"),
        "leave_one_anchor_out": _leave_one_out(trades, dimension="anchor"),
        "block_bootstrap": bootstrap,
        "diagnostic_adjudication": {
            "quartiles_with_positive_mean_r": quartile_positive,
            "quartile_count": 4,
            "bootstrap_p05_mean_r_nonpositive_at_all_block_lengths": (
                bootstrap_all_p05_nonpositive
            ),
            "second_half_mean_r_positive": second_half.mean_r > 0,
            "evidence_supports_robust_positive_edge": (
                quartile_positive >= 3
                and not bootstrap_all_p05_nonpositive
                and second_half.mean_r > 0
            ),
            "retrospective_subset_selection_authorized": False,
            "methodology_change_authorized": False,
            "fresh_unseen_validation_required_before_promotion": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.replay)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    args.out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
