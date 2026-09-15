"""One-shot retained-evidence Forex holdout replay for ICT Turtle Soup R2."""

from __future__ import annotations

import heapq
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.ict_turtle_soup_r2_all_session import (
    IDENTITY,
    MIN_PROJECTED_R,
    LiquiditySide,
    M5Bar,
    Side,
)

NY = ZoneInfo("America/New_York")
HOLDOUT_ID = "VT08_R3_15_FINAL_INDEPENDENT_2020_2022"
EVAL_OPEN = datetime(2020, 7, 1, tzinfo=UTC)
EVAL_CLOSE = datetime(2022, 7, 1, tzinfo=UTC)
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
}


@dataclass(frozen=True, slots=True)
class Pool:
    pool_id: str
    symbol: str
    family: str
    side: LiquiditySide
    level: Decimal
    known_at: datetime


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    side: Side
    swept_pool_id: str
    swept_family: str
    target_pool_id: str
    target_family: str
    sweep_at: datetime
    cisd_at: datetime
    entry_at: datetime
    exit_at: datetime
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    projected_r: Decimal
    gross_r: Decimal
    primary_net_r: Decimal
    stress_net_r: Decimal
    exit_reason: str


@dataclass(frozen=True, slots=True)
class Evidence:
    symbol: str
    digits: int
    bars: tuple[M5Bar, ...]


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("evidence timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: str) -> Decimal:
    return Decimal(value)


def _load_evidence(path: Path) -> Evidence:
    payload = json.loads(path.read_text())
    if payload.get("holdout_id") != HOLDOUT_ID:
        raise ValueError(f"unexpected holdout id in {path}")
    if _dt(payload["evaluation_opened_at"]) != EVAL_OPEN:
        raise ValueError("holdout evaluation open drift")
    if _dt(payload["evaluation_closed_at"]) != EVAL_CLOSE:
        raise ValueError("holdout evaluation close drift")
    if payload.get("read_only") is not True:
        raise ValueError("holdout evidence must be read-only")
    symbol_payload = payload["symbol"]
    symbol = symbol_payload["symbol_name"]
    digits = int(symbol_payload["digits"])
    raw = payload["periods"]["M5"]
    bars = tuple(
        M5Bar(
            opened_at=_dt(item["opened_at"]),
            closed_at=_dt(item["closed_at"]),
            open=_decimal(item["open"]),
            high=_decimal(item["high"]),
            low=_decimal(item["low"]),
            close=_decimal(item["close"]),
        )
        for item in raw
    )
    if bars != tuple(sorted(bars, key=lambda bar: bar.opened_at)):
        raise ValueError(f"M5 evidence is not chronological for {symbol}")
    if len({bar.opened_at for bar in bars}) != len(bars):
        raise ValueError(f"duplicate M5 bars for {symbol}")
    return Evidence(symbol=symbol, digits=digits, bars=bars)


def _range_pool_pair(
    symbol: str,
    family: str,
    key: str,
    bars: Iterable[M5Bar],
    known_at: datetime,
) -> tuple[Pool, Pool] | tuple[()]:
    selected = tuple(bars)
    if not selected:
        return ()
    high = max(bar.high for bar in selected)
    low = min(bar.low for bar in selected)
    stem = f"{symbol}:{family}:{key}"
    return (
        Pool(f"{stem}:buy", symbol, family, LiquiditySide.BUY_SIDE, high, known_at),
        Pool(f"{stem}:sell", symbol, family, LiquiditySide.SELL_SIDE, low, known_at),
    )


def _local_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, NY).astimezone(UTC)


def _session_complete(bars: tuple[M5Bar, ...], expected: int) -> bool:
    if len(bars) != expected:
        return False
    return all(
        left.closed_at == right.opened_at
        for left, right in zip(bars, bars[1:], strict=False)
    )


def build_pools(evidence: Evidence) -> tuple[Pool, ...]:
    by_day: dict[date, list[M5Bar]] = defaultdict(list)
    by_week: dict[date, list[M5Bar]] = defaultdict(list)
    asia: dict[date, list[M5Bar]] = defaultdict(list)
    london: dict[date, list[M5Bar]] = defaultdict(list)
    ny_am: dict[date, list[M5Bar]] = defaultdict(list)
    ny_pm: dict[date, list[M5Bar]] = defaultdict(list)

    for bar in evidence.bars:
        local = bar.opened_at.astimezone(NY)
        day = local.date()
        by_day[day].append(bar)
        week = day - timedelta(days=day.weekday())
        by_week[week].append(bar)
        wall = local.timetz().replace(tzinfo=None)
        if time(20, 0) <= wall < time(23, 59, 59, 999999):
            asia[day + timedelta(days=1)].append(bar)
        if time(2, 0) <= wall < time(5, 0):
            london[day].append(bar)
        if time(8, 30) <= wall < time(11, 0):
            ny_am[day].append(bar)
        if time(13, 30) <= wall < time(16, 0):
            ny_pm[day].append(bar)

    pools: list[Pool] = []
    for day, bars in sorted(by_day.items()):
        pools.extend(
            _range_pool_pair(
                evidence.symbol,
                "previous-ny-day",
                day.isoformat(),
                bars,
                _local_midnight(day + timedelta(days=1)),
            )
        )
    for week, bars in sorted(by_week.items()):
        pools.extend(
            _range_pool_pair(
                evidence.symbol,
                "previous-ny-week",
                week.isoformat(),
                bars,
                _local_midnight(week + timedelta(days=7)),
            )
        )
    for day, bars in sorted(asia.items()):
        ordered = tuple(sorted(bars, key=lambda bar: bar.opened_at))
        if _session_complete(ordered, 48):
            pools.extend(
                _range_pool_pair(
                    evidence.symbol,
                    "asia",
                    day.isoformat(),
                    ordered,
                    _local_midnight(day),
                )
            )
    for day, bars in sorted(london.items()):
        ordered = tuple(sorted(bars, key=lambda bar: bar.opened_at))
        if _session_complete(ordered, 36):
            known = datetime.combine(day, time(5, 0), NY).astimezone(UTC)
            pools.extend(
                _range_pool_pair(evidence.symbol, "london", day.isoformat(), ordered, known)
            )
    for day, bars in sorted(ny_am.items()):
        ordered = tuple(sorted(bars, key=lambda bar: bar.opened_at))
        if _session_complete(ordered, 30):
            known = datetime.combine(day, time(11, 0), NY).astimezone(UTC)
            pools.extend(
                _range_pool_pair(evidence.symbol, "ny-am", day.isoformat(), ordered, known)
            )
    for day, bars in sorted(ny_pm.items()):
        ordered = tuple(sorted(bars, key=lambda bar: bar.opened_at))
        if _session_complete(ordered, 30):
            known = datetime.combine(day, time(16, 0), NY).astimezone(UTC)
            pools.extend(
                _range_pool_pair(evidence.symbol, "ny-pm", day.isoformat(), ordered, known)
            )
    return tuple(sorted(pools, key=lambda pool: (pool.known_at, pool.pool_id)))


def first_sweeps(
    bars: tuple[M5Bar, ...], pools: tuple[Pool, ...]
) -> tuple[dict[str, datetime], dict[datetime, tuple[str, ...]]]:
    buy_heap: list[tuple[Decimal, str]] = []
    sell_heap: list[tuple[Decimal, str]] = []
    cursor = 0
    first: dict[str, datetime] = {}
    groups: dict[datetime, list[str]] = defaultdict(list)
    for bar in bars:
        while cursor < len(pools) and pools[cursor].known_at <= bar.opened_at:
            pool = pools[cursor]
            if pool.side is LiquiditySide.BUY_SIDE:
                heapq.heappush(buy_heap, (pool.level, pool.pool_id))
            else:
                heapq.heappush(sell_heap, (-pool.level, pool.pool_id))
            cursor += 1
        while buy_heap and buy_heap[0][0] < bar.high:
            _level, pool_id = heapq.heappop(buy_heap)
            first[pool_id] = bar.opened_at
            groups[bar.opened_at].append(pool_id)
        while sell_heap and -sell_heap[0][0] > bar.low:
            _neg_level, pool_id = heapq.heappop(sell_heap)
            first[pool_id] = bar.opened_at
            groups[bar.opened_at].append(pool_id)
    return first, {key: tuple(value) for key, value in groups.items()}


def _opposing(bar: M5Bar, side: Side) -> bool:
    return bar.close < bar.open if side is Side.LONG else bar.close > bar.open


def _reclaims(bar: M5Bar, side: Side, level: Decimal) -> bool:
    return bar.close > level if side is Side.LONG else bar.close < level


def _cisd(bar: M5Bar, side: Side, threshold: Decimal) -> bool:
    return bar.close > threshold if side is Side.LONG else bar.close < threshold


def _profit_factor(values: list[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    if losses == 0:
        return None
    return gains / losses


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


def _session_bucket(moment: datetime) -> str:
    local = moment.astimezone(NY)
    wall = local.timetz().replace(tzinfo=None)
    if wall >= time(20, 0):
        return "asia-reference-window"
    if time(2, 0) <= wall < time(5, 0):
        return "london"
    if time(8, 30) <= wall < time(11, 0):
        return "ny-am"
    if time(13, 30) <= wall < time(16, 0):
        return "ny-pm"
    return "other"


def _simulate_trade(
    bars: tuple[M5Bar, ...],
    entry_index: int,
    end_index: int,
    *,
    side: Side,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[datetime, Decimal, str, Decimal]:
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target - entry if side is Side.LONG else entry - target
    for bar in bars[entry_index:end_index]:
        if side is Side.LONG:
            if bar.open <= stop:
                exit_price = bar.open
                return bar.opened_at, exit_price, "gap-stop", (exit_price - entry) / risk
            if bar.open >= target:
                return bar.opened_at, target, "target", reward / risk
            stop_touch = bar.low <= stop
            target_touch = bar.high >= target
            if stop_touch and target_touch:
                return bar.closed_at, stop, "stop-first", Decimal(-1)
            if stop_touch:
                return bar.closed_at, stop, "stop", Decimal(-1)
            if target_touch:
                return bar.closed_at, target, "target", reward / risk
        else:
            if bar.open >= stop:
                exit_price = bar.open
                return bar.opened_at, exit_price, "gap-stop", (entry - exit_price) / risk
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
    final = bars[end_index - 1]
    gross = (final.close - entry) / risk if side is Side.LONG else (entry - final.close) / risk
    return final.closed_at, final.close, "time-exit", gross


def replay_symbol(evidence: Evidence) -> tuple[list[Trade], Counter[str], dict[str, object]]:
    bars = evidence.bars
    pools = build_pools(evidence)
    by_id = {pool.pool_id: pool for pool in pools}
    first, groups = first_sweeps(bars, pools)
    index_by_time = {bar.opened_at: index for index, bar in enumerate(bars)}
    funnel: Counter[str] = Counter()
    trades: list[Trade] = []
    next_available = EVAL_OPEN
    tick = Decimal(1).scaleb(-evidence.digits)

    for sweep_at in sorted(groups):
        if not EVAL_OPEN <= sweep_at < EVAL_CLOSE:
            continue
        ids = groups[sweep_at]
        funnel["swept-pool-events"] += 1
        funnel["swept-pools"] += len(ids)
        if len(ids) != 1:
            funnel["ambiguous-multi-pool-sweep"] += 1
            continue
        if sweep_at < next_available:
            funnel["ignored-position-open"] += 1
            continue
        pool = by_id[ids[0]]
        side = Side.LONG if pool.side is LiquiditySide.SELL_SIDE else Side.SHORT
        sweep_index = index_by_time[sweep_at]
        sweep_day = sweep_at.astimezone(NY).date()
        end_index = sweep_index + 1
        while end_index < len(bars) and bars[end_index].opened_at.astimezone(NY).date() == sweep_day:
            end_index += 1

        cursor = sweep_index if _opposing(bars[sweep_index], side) else sweep_index - 1
        if cursor < 0 or bars[cursor].opened_at < pool.known_at:
            funnel["no-opposing-series"] += 1
            continue
        if not _opposing(bars[cursor], side):
            funnel["no-opposing-series"] += 1
            continue
        while (
            cursor > 0
            and bars[cursor - 1].opened_at >= pool.known_at
            and bars[cursor - 1].closed_at == bars[cursor].opened_at
            and _opposing(bars[cursor - 1], side)
        ):
            cursor -= 1
        threshold = bars[cursor].open

        reclaim_index: int | None = None
        cisd_index: int | None = None
        for index in range(sweep_index, end_index):
            bar = bars[index]
            if reclaim_index is None and _reclaims(bar, side, pool.level):
                reclaim_index = index
            if reclaim_index is not None and _cisd(bar, side, threshold):
                cisd_index = index
                break
        if reclaim_index is None:
            funnel["no-reclaim"] += 1
            continue
        if cisd_index is None:
            funnel["no-cisd"] += 1
            continue
        entry_index = cisd_index + 1
        if entry_index >= end_index or bars[cisd_index].closed_at != bars[entry_index].opened_at:
            funnel["no-causal-entry"] += 1
            continue
        entry_bar = bars[entry_index]
        entry = entry_bar.open
        adverse = bars[sweep_index : cisd_index + 1]
        stop = (
            min(bar.low for bar in adverse) - tick
            if side is Side.LONG
            else max(bar.high for bar in adverse) + tick
        )
        target_candidates = [
            other
            for other in pools
            if other.side is not pool.side
            and other.known_at <= entry_bar.opened_at
            and (first.get(other.pool_id) is None or first[other.pool_id] >= entry_bar.opened_at)
            and (
                (side is Side.LONG and other.level > entry)
                or (side is Side.SHORT and other.level < entry)
            )
        ]
        if not target_candidates:
            funnel["no-opposing-target"] += 1
            continue
        target_pool = (
            min(target_candidates, key=lambda item: item.level)
            if side is Side.LONG
            else max(target_candidates, key=lambda item: item.level)
        )
        risk = entry - stop if side is Side.LONG else stop - entry
        reward = target_pool.level - entry if side is Side.LONG else entry - target_pool.level
        if risk <= 0 or reward <= 0:
            funnel["invalid-geometry"] += 1
            continue
        projected_r = reward / risk
        if projected_r < MIN_PROJECTED_R:
            funnel["insufficient-projected-r"] += 1
            continue
        exit_at, exit_price, reason, gross_r = _simulate_trade(
            bars,
            entry_index,
            end_index,
            side=side,
            entry=entry,
            stop=stop,
            target=target_pool.level,
        )
        trade = Trade(
            symbol=evidence.symbol,
            side=side,
            swept_pool_id=pool.pool_id,
            swept_family=pool.family,
            target_pool_id=target_pool.pool_id,
            target_family=target_pool.family,
            sweep_at=sweep_at,
            cisd_at=bars[cisd_index].closed_at,
            entry_at=entry_bar.opened_at,
            exit_at=exit_at,
            entry=entry,
            stop=stop,
            target=target_pool.level,
            exit_price=exit_price,
            projected_r=projected_r,
            gross_r=gross_r,
            primary_net_r=gross_r - PRIMARY_FRICTION_R,
            stress_net_r=gross_r - STRESS_FRICTION_R,
            exit_reason=reason,
        )
        trades.append(trade)
        funnel["trade"] += 1
        next_available = max(next_available, exit_at)

    metadata = {
        "pool_count": len(pools),
        "first_swept_pool_count": len(first),
        "m5_bar_count": len(bars),
    }
    return trades, funnel, metadata


def _group_summary(trades: list[Trade], key_fn: object) -> dict[str, dict[str, object]]:
    groups: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        key = str(key_fn(trade))  # type: ignore[operator]
        groups[key].append(trade)
    result: dict[str, dict[str, object]] = {}
    for key, selected in sorted(groups.items()):
        net = [trade.primary_net_r for trade in selected]
        result[key] = {
            "trades": len(selected),
            "total_net_r": str(sum(net, Decimal(0))),
            "mean_net_r": str(sum(net, Decimal(0)) / len(selected)),
            "profit_factor": None if _profit_factor(net) is None else str(_profit_factor(net)),
        }
    return result


def _concentration(trades: list[Trade], key_fn: object) -> Decimal | None:
    positive = [trade for trade in trades if trade.primary_net_r > 0]
    total = sum((trade.primary_net_r for trade in positive), Decimal(0))
    if total <= 0:
        return None
    groups: dict[str, Decimal] = defaultdict(Decimal)
    for trade in positive:
        groups[str(key_fn(trade))] += trade.primary_net_r  # type: ignore[operator]
    return max(groups.values()) / total


def _json_trade(trade: Trade) -> dict[str, object]:
    payload = asdict(trade)
    for key, value in tuple(payload.items()):
        if isinstance(value, Decimal):
            payload[key] = str(value)
        elif isinstance(value, datetime):
            payload[key] = value.astimezone(UTC).isoformat()
        elif isinstance(value, Side):
            payload[key] = value.value
    return payload


def run(root: Path, output: Path) -> dict[str, object]:
    files = sorted(root.rglob("market-evidence.json"))
    evidence = [_load_evidence(path) for path in files]
    symbols = {item.symbol for item in evidence}
    if symbols != EXPECTED_SYMBOLS:
        raise ValueError(f"retained symbol set mismatch: {sorted(symbols)}")
    all_trades: list[Trade] = []
    all_funnel: Counter[str] = Counter()
    per_symbol_meta: dict[str, object] = {}
    for item in sorted(evidence, key=lambda ev: ev.symbol):
        trades, funnel, metadata = replay_symbol(item)
        all_trades.extend(trades)
        all_funnel.update(funnel)
        per_symbol_meta[item.symbol] = metadata
    all_trades.sort(key=lambda trade: (trade.entry_at, trade.symbol))
    primary = [trade.primary_net_r for trade in all_trades]
    gross = [trade.gross_r for trade in all_trades]
    stress = [trade.stress_net_r for trade in all_trades]
    wins = sum(value > 0 for value in primary)
    losses = sum(value < 0 for value in primary)
    flats = len(primary) - wins - losses
    total_primary = sum(primary, Decimal(0))
    total_gross = sum(gross, Decimal(0))
    total_stress = sum(stress, Decimal(0))
    symbols_sorted = sorted(EXPECTED_SYMBOLS)
    lomo = {
        symbol: str(
            sum(
                (trade.primary_net_r for trade in all_trades if trade.symbol != symbol),
                Decimal(0),
            )
        )
        for symbol in symbols_sorted
    }
    report: dict[str, object] = {
        "schema": "qore.trader_lab.ict_turtle_soup_r2_forex_holdout.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "evaluation_opened_at": EVAL_OPEN.isoformat(),
        "evaluation_closed_at": EVAL_CLOSE.isoformat(),
        "retained_evidence_only": True,
        "symbols": symbols_sorted,
        "trade_count": len(all_trades),
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "gross_total_r": str(total_gross),
        "gross_mean_r": None if not gross else str(total_gross / len(gross)),
        "primary_friction_r": str(PRIMARY_FRICTION_R),
        "primary_total_r": str(total_primary),
        "primary_mean_r": None if not primary else str(total_primary / len(primary)),
        "primary_profit_factor": None if _profit_factor(primary) is None else str(_profit_factor(primary)),
        "stress_friction_r": str(STRESS_FRICTION_R),
        "stress_total_r": str(total_stress),
        "stress_mean_r": None if not stress else str(total_stress / len(stress)),
        "stress_profit_factor": None if _profit_factor(stress) is None else str(_profit_factor(stress)),
        "max_drawdown_r": str(_max_drawdown(primary)),
        "longest_losing_streak": _longest_loss(primary),
        "funnel": dict(sorted(all_funnel.items())),
        "exit_reasons": dict(sorted(Counter(trade.exit_reason for trade in all_trades).items())),
        "per_symbol": _group_summary(all_trades, lambda trade: trade.symbol),
        "per_side": _group_summary(all_trades, lambda trade: trade.side.value),
        "per_year": _group_summary(all_trades, lambda trade: trade.entry_at.astimezone(NY).year),
        "per_quarter": _group_summary(
            all_trades,
            lambda trade: (
                f"{trade.entry_at.astimezone(NY).year}-Q"
                f"{((trade.entry_at.astimezone(NY).month - 1) // 3) + 1}"
            ),
        ),
        "per_session": _group_summary(all_trades, lambda trade: _session_bucket(trade.entry_at)),
        "per_hour_ny": _group_summary(all_trades, lambda trade: trade.entry_at.astimezone(NY).hour),
        "leave_one_symbol_out_total_r": lomo,
        "positive_gain_concentration": {
            "symbol": None if _concentration(all_trades, lambda trade: trade.symbol) is None else str(_concentration(all_trades, lambda trade: trade.symbol)),
            "side": None if _concentration(all_trades, lambda trade: trade.side.value) is None else str(_concentration(all_trades, lambda trade: trade.side.value)),
            "year": None if _concentration(all_trades, lambda trade: trade.entry_at.astimezone(NY).year) is None else str(_concentration(all_trades, lambda trade: trade.entry_at.astimezone(NY).year)),
        },
        "per_symbol_metadata": per_symbol_meta,
        "fresh_for_ict_turtle_soup_identity": True,
        "globally_unseen_data": False,
        "post_result_rule_change_authorized": False,
        "forensics_required_before_any_new_identity": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    (output / "trades.json").write_text(
        json.dumps([_json_trade(trade) for trade in all_trades], sort_keys=True, indent=2) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: ict_turtle_soup_r2_forex_holdout SOURCE_ROOT OUTPUT_DIR")
    report = run(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
