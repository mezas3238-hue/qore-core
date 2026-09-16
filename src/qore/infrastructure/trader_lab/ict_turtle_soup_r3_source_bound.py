"""Source-bound ICT/TTrades Turtle Soup R3 consumed-development replay."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.ict_turtle_soup_r2_all_session import M5Bar

IDENTITY = "ICT_TURTLE_SOUP_R3_H4_C2_M15_CISD"
HOLDOUT_ID = "VT08_R3_15_FINAL_INDEPENDENT_2020_2022"
EVAL_OPEN = datetime(2020, 7, 1, tzinfo=UTC)
EVAL_CLOSE = datetime(2022, 7, 1, tzinfo=UTC)
NY = ZoneInfo("America/New_York")
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
}
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")


class Side(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class Evidence:
    symbol: str
    digits: int
    bars: tuple[M5Bar, ...]


@dataclass(frozen=True, slots=True)
class H4Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    m5: tuple[M5Bar, ...]


@dataclass(frozen=True, slots=True)
class M15Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    m5: tuple[M5Bar, ...]


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    side: Side
    c1_opened_at: datetime
    c2_opened_at: datetime
    sweep_at: datetime
    cisd_at: datetime
    entry_at: datetime
    exit_at: datetime
    relevant_level: Decimal
    cisd_threshold: Decimal
    protected_swing: Decimal
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    projected_r: Decimal
    gross_r: Decimal
    primary_net_r: Decimal
    stress_net_r: Decimal
    exit_reason: str
    session_bucket: str


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def _load_evidence(path: Path) -> Evidence:
    payload = json.loads(path.read_text())
    if payload.get("holdout_id") != HOLDOUT_ID:
        raise ValueError(f"unexpected holdout id in {path}")
    if _dt(payload["evaluation_opened_at"]) != EVAL_OPEN:
        raise ValueError("evaluation open drift")
    if _dt(payload["evaluation_closed_at"]) != EVAL_CLOSE:
        raise ValueError("evaluation close drift")
    if payload.get("read_only") is not True:
        raise ValueError("retained evidence must be read-only")
    symbol_payload = payload["symbol"]
    symbol = str(symbol_payload["symbol_name"])
    digits = int(symbol_payload["digits"])
    bars = tuple(
        M5Bar(
            opened_at=_dt(item["opened_at"]),
            closed_at=_dt(item["closed_at"]),
            open=Decimal(item["open"]),
            high=Decimal(item["high"]),
            low=Decimal(item["low"]),
            close=Decimal(item["close"]),
        )
        for item in payload["periods"]["M5"]
    )
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise ValueError(f"M5 not chronological for {symbol}")
    if len({bar.opened_at for bar in bars}) != len(bars):
        raise ValueError(f"duplicate M5 bars for {symbol}")
    return Evidence(symbol=symbol, digits=digits, bars=bars)


def _contiguous(bars: tuple[M5Bar, ...]) -> bool:
    return all(
        left.closed_at == right.opened_at
        for left, right in zip(bars, bars[1:], strict=False)
    )


def _h4_key(bar: M5Bar) -> tuple[date, int]:
    local = bar.opened_at.astimezone(NY)
    return local.date(), (local.hour // 4) * 4


def _build_h4(bars: tuple[M5Bar, ...]) -> tuple[H4Bar, ...]:
    grouped: dict[tuple[date, int], list[M5Bar]] = defaultdict(list)
    for bar in bars:
        grouped[_h4_key(bar)].append(bar)
    result: list[H4Bar] = []
    for (day, hour), raw in sorted(grouped.items()):
        ordered = tuple(sorted(raw, key=lambda item: item.opened_at))
        if len(ordered) != 48 or not _contiguous(ordered):
            continue
        first_local = ordered[0].opened_at.astimezone(NY)
        if first_local.date() != day or first_local.hour != hour or first_local.minute != 0:
            continue
        result.append(
            H4Bar(
                opened_at=ordered[0].opened_at,
                closed_at=ordered[-1].closed_at,
                open=ordered[0].open,
                high=max(bar.high for bar in ordered),
                low=min(bar.low for bar in ordered),
                close=ordered[-1].close,
                m5=ordered,
            )
        )
    return tuple(result)


def _build_m15(h4: H4Bar) -> tuple[M15Bar, ...]:
    if len(h4.m5) != 48 or not _contiguous(h4.m5):
        return ()
    result: list[M15Bar] = []
    for start in range(0, 48, 3):
        chunk = h4.m5[start : start + 3]
        if len(chunk) != 3 or not _contiguous(chunk):
            return ()
        result.append(
            M15Bar(
                opened_at=chunk[0].opened_at,
                closed_at=chunk[-1].closed_at,
                open=chunk[0].open,
                high=max(bar.high for bar in chunk),
                low=min(bar.low for bar in chunk),
                close=chunk[-1].close,
                m5=chunk,
            )
        )
    return tuple(result)


def _opposing(bar: M15Bar, side: Side) -> bool:
    if side is Side.LONG:
        return bar.close < bar.open
    return bar.close > bar.open


def _sweeps(bar: M15Bar, side: Side, level: Decimal) -> bool:
    if side is Side.LONG:
        return bar.low < level
    return bar.high > level


def _confirms_cisd(bar: M15Bar, side: Side, threshold: Decimal) -> bool:
    if side is Side.LONG:
        return bar.close > threshold
    return bar.close < threshold


def _find_cisd(
    bars: tuple[M15Bar, ...], side: Side, level: Decimal
) -> tuple[int, int, Decimal] | None:
    sweep_index = next(
        (index for index, bar in enumerate(bars) if _sweeps(bar, side, level)),
        None,
    )
    if sweep_index is None:
        return None
    cursor = sweep_index if _opposing(bars[sweep_index], side) else sweep_index - 1
    if cursor < 0 or not _opposing(bars[cursor], side):
        return None
    while cursor > 0 and _opposing(bars[cursor - 1], side):
        cursor -= 1
    threshold = bars[cursor].open
    cisd_index = next(
        (
            index
            for index in range(sweep_index, len(bars))
            if _confirms_cisd(bars[index], side, threshold)
        ),
        None,
    )
    if cisd_index is None:
        return None
    return cursor, cisd_index, threshold


def _session_bucket(moment: datetime) -> str:
    wall = moment.astimezone(NY).timetz().replace(tzinfo=None)
    if wall >= time(20, 0) or wall < time(2, 0):
        return "asia"
    if time(2, 0) <= wall < time(8, 30):
        return "london"
    if time(8, 30) <= wall < time(16, 0):
        return "new-york"
    return "other"


def _simulate_c3(
    c3: H4Bar,
    *,
    side: Side,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[datetime, Decimal, str, Decimal]:
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target - entry if side is Side.LONG else entry - target
    for bar in c3.m5:
        if side is Side.LONG:
            if bar.open <= stop:
                return bar.opened_at, bar.open, "gap-stop", (bar.open - entry) / risk
            if bar.open >= target:
                return bar.opened_at, target, "target", reward / risk
            stop_touch = bar.low <= stop
            target_touch = bar.high >= target
        else:
            if bar.open >= stop:
                return bar.opened_at, bar.open, "gap-stop", (entry - bar.open) / risk
            if bar.open <= target:
                return bar.opened_at, target, "target", reward / risk
            stop_touch = bar.high >= stop
            target_touch = bar.low <= target
        if stop_touch and target_touch:
            return bar.closed_at, stop, "stop-first", Decimal(-1)
        if stop_touch:
            return bar.closed_at, stop, "stop", Decimal(-1)
        if target_touch:
            return bar.closed_at, target, "target", reward / risk
    final = c3.m5[-1]
    gross = (
        (final.close - entry) / risk
        if side is Side.LONG
        else (entry - final.close) / risk
    )
    return final.closed_at, final.close, "time-exit", gross


def replay_symbol(evidence: Evidence) -> tuple[list[Trade], Counter[str]]:
    h4 = _build_h4(evidence.bars)
    trades: list[Trade] = []
    funnel: Counter[str] = Counter()

    for index in range(3, len(h4) - 1):
        window = h4[index - 3 : index]
        c1 = h4[index - 1]
        c2 = h4[index]
        c3 = h4[index + 1]

        if not (c1.closed_at == c2.opened_at and c2.closed_at == c3.opened_at):
            funnel["h4-discontinuity"] += 1
            continue
        if not EVAL_OPEN <= c2.opened_at < EVAL_CLOSE:
            continue

        funnel["c2-cycles"] += 1
        c1_relevant_low = c1.low == min(bar.low for bar in window)
        c1_relevant_high = c1.high == max(bar.high for bar in window)

        bullish = c1_relevant_low and c2.low < c1.low and c2.close > c1.low
        bearish = c1_relevant_high and c2.high > c1.high and c2.close < c1.high
        if bullish and bearish:
            funnel["ambiguous-both-sides"] += 1
            continue
        if not bullish and not bearish:
            funnel["no-source-c2-reversal"] += 1
            continue

        side = Side.LONG if bullish else Side.SHORT
        funnel["source-c2-reversal"] += 1
        level = c1.low if side is Side.LONG else c1.high
        m15 = _build_m15(c2)
        if len(m15) != 16:
            funnel["m15-data-invalid"] += 1
            continue

        cisd = _find_cisd(m15, side, level)
        if cisd is None:
            funnel["no-cisd"] += 1
            continue
        series_start, cisd_index, threshold = cisd
        causal = m15[series_start : cisd_index + 1]
        protected = (
            min(bar.low for bar in causal)
            if side is Side.LONG
            else max(bar.high for bar in causal)
        )
        sweep_at = next(bar.opened_at for bar in m15 if _sweeps(bar, side, level))
        entry = c3.open
        stop = protected
        target = c1.high if side is Side.LONG else c1.low

        risk = entry - stop if side is Side.LONG else stop - entry
        reward = target - entry if side is Side.LONG else entry - target
        if risk <= 0:
            funnel["invalid-protected-swing-geometry"] += 1
            continue
        if reward <= 0:
            funnel["no-causal-opposing-target"] += 1
            continue

        projected_r = reward / risk
        exit_at, exit_price, reason, gross_r = _simulate_c3(
            c3,
            side=side,
            entry=entry,
            stop=stop,
            target=target,
        )
        trades.append(
            Trade(
                symbol=evidence.symbol,
                side=side,
                c1_opened_at=c1.opened_at,
                c2_opened_at=c2.opened_at,
                sweep_at=sweep_at,
                cisd_at=m15[cisd_index].closed_at,
                entry_at=c3.opened_at,
                exit_at=exit_at,
                relevant_level=level,
                cisd_threshold=threshold,
                protected_swing=protected,
                entry=entry,
                stop=stop,
                target=target,
                exit_price=exit_price,
                projected_r=projected_r,
                gross_r=gross_r,
                primary_net_r=gross_r - PRIMARY_FRICTION_R,
                stress_net_r=gross_r - STRESS_FRICTION_R,
                exit_reason=reason,
                session_bucket=_session_bucket(sweep_at),
            )
        )
        funnel["trade"] += 1

    return trades, funnel


def _profit_factor(values: list[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _max_drawdown(values: list[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _longest_loss(values: list[Decimal]) -> int:
    best = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _group_summary(
    trades: list[Trade], key_fn: Callable[[Trade], object]
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        groups[str(key_fn(trade))].append(trade)
    result: dict[str, dict[str, object]] = {}
    for key, selected in sorted(groups.items()):
        net = [trade.primary_net_r for trade in selected]
        total = sum(net, Decimal(0))
        pf = _profit_factor(net)
        result[key] = {
            "trades": len(selected),
            "wins": sum(value > 0 for value in net),
            "losses": sum(value < 0 for value in net),
            "flats": sum(value == 0 for value in net),
            "total_net_r": str(total),
            "mean_net_r": str(total / len(selected)),
            "profit_factor": None if pf is None else str(pf),
        }
    return result


def _quantiles(values: list[Decimal]) -> dict[str, str] | None:
    if not values:
        return None
    ordered = sorted(values)

    def pick(p: Decimal) -> Decimal:
        index = int((len(ordered) - 1) * p)
        return ordered[index]

    return {
        "min": str(ordered[0]),
        "p25": str(pick(Decimal("0.25"))),
        "median": str(Decimal(str(median(ordered)))),
        "p75": str(pick(Decimal("0.75"))),
        "max": str(ordered[-1]),
    }


def _json_trade(trade: Trade) -> dict[str, object]:
    return {
        "identity": IDENTITY,
        "symbol": trade.symbol,
        "side": trade.side.value,
        "c1_opened_at": trade.c1_opened_at.astimezone(UTC).isoformat(),
        "c2_opened_at": trade.c2_opened_at.astimezone(UTC).isoformat(),
        "sweep_at": trade.sweep_at.astimezone(UTC).isoformat(),
        "cisd_at": trade.cisd_at.astimezone(UTC).isoformat(),
        "entry_at": trade.entry_at.astimezone(UTC).isoformat(),
        "exit_at": trade.exit_at.astimezone(UTC).isoformat(),
        "relevant_level": str(trade.relevant_level),
        "cisd_threshold": str(trade.cisd_threshold),
        "protected_swing": str(trade.protected_swing),
        "entry": str(trade.entry),
        "stop": str(trade.stop),
        "target": str(trade.target),
        "exit_price": str(trade.exit_price),
        "projected_r": str(trade.projected_r),
        "gross_r": str(trade.gross_r),
        "primary_net_r": str(trade.primary_net_r),
        "stress_net_r": str(trade.stress_net_r),
        "exit_reason": trade.exit_reason,
        "session_bucket": trade.session_bucket,
    }


def run(root: Path, output: Path) -> dict[str, object]:
    files = sorted(root.rglob("market-evidence.json"))
    evidence = [_load_evidence(path) for path in files]
    symbols = {item.symbol for item in evidence}
    if symbols != EXPECTED_SYMBOLS:
        raise ValueError(f"retained symbol set mismatch: {sorted(symbols)}")

    all_trades: list[Trade] = []
    funnel: Counter[str] = Counter()
    for item in sorted(evidence, key=lambda value: value.symbol):
        trades, item_funnel = replay_symbol(item)
        all_trades.extend(trades)
        funnel.update(item_funnel)

    all_trades.sort(key=lambda trade: (trade.entry_at, trade.symbol))
    gross = [trade.gross_r for trade in all_trades]
    primary = [trade.primary_net_r for trade in all_trades]
    stress = [trade.stress_net_r for trade in all_trades]
    total_gross = sum(gross, Decimal(0))
    total_primary = sum(primary, Decimal(0))
    total_stress = sum(stress, Decimal(0))
    primary_pf = _profit_factor(primary)
    stress_pf = _profit_factor(stress)

    lomo = {
        symbol: str(
            sum(
                (
                    trade.primary_net_r
                    for trade in all_trades
                    if trade.symbol != symbol
                ),
                Decimal(0),
            )
        )
        for symbol in sorted(EXPECTED_SYMBOLS)
    }

    report: dict[str, object] = {
        "identity": IDENTITY,
        "evidence_status": "CONSUMED_DEVELOPMENT_ONLY",
        "holdout_id": HOLDOUT_ID,
        "evaluation_opened_at": EVAL_OPEN.isoformat(),
        "evaluation_closed_at": EVAL_CLOSE.isoformat(),
        "symbols": sorted(EXPECTED_SYMBOLS),
        "session_filter_applied": False,
        "asia_london_new_york_all_eligible": True,
        "minimum_projected_r_gate": None,
        "friction": {
            "gross_r_per_trade": "0",
            "primary_r_per_trade": str(PRIMARY_FRICTION_R),
            "stress_r_per_trade": str(STRESS_FRICTION_R),
        },
        "funnel": dict(sorted(funnel.items())),
        "aggregate": {
            "trades": len(all_trades),
            "wins": sum(value > 0 for value in primary),
            "losses": sum(value < 0 for value in primary),
            "flats": sum(value == 0 for value in primary),
            "gross_total_r": str(total_gross),
            "gross_mean_r": (
                None if not all_trades else str(total_gross / len(all_trades))
            ),
            "primary_total_r": str(total_primary),
            "primary_mean_r": (
                None if not all_trades else str(total_primary / len(all_trades))
            ),
            "primary_profit_factor": (
                None if primary_pf is None else str(primary_pf)
            ),
            "stress_total_r": str(total_stress),
            "stress_mean_r": (
                None if not all_trades else str(total_stress / len(all_trades))
            ),
            "stress_profit_factor": None if stress_pf is None else str(stress_pf),
            "max_drawdown_r": str(_max_drawdown(primary)),
            "longest_losing_streak": _longest_loss(primary),
        },
        "projected_r_distribution": _quantiles(
            [trade.projected_r for trade in all_trades]
        ),
        "by_symbol": _group_summary(all_trades, lambda trade: trade.symbol),
        "by_side": _group_summary(all_trades, lambda trade: trade.side.value),
        "by_session_diagnostic": _group_summary(
            all_trades, lambda trade: trade.session_bucket
        ),
        "by_ny_hour_diagnostic": _group_summary(
            all_trades, lambda trade: trade.sweep_at.astimezone(NY).hour
        ),
        "by_year": _group_summary(
            all_trades, lambda trade: trade.entry_at.astimezone(NY).year
        ),
        "by_quarter": _group_summary(
            all_trades,
            lambda trade: (
                trade.entry_at.astimezone(NY).year,
                (trade.entry_at.astimezone(NY).month - 1) // 3 + 1,
            ),
        ),
        "by_exit_reason": _group_summary(all_trades, lambda trade: trade.exit_reason),
        "leave_one_symbol_out_primary_total_r": lomo,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (output / "trades.json").write_text(
        json.dumps([_json_trade(trade) for trade in all_trades], indent=2) + "\n"
    )
    return report


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: python -m qore.infrastructure.trader_lab."
            "ict_turtle_soup_r3_source_bound SOURCE_ROOT OUTPUT_DIR"
        )
    report = run(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
