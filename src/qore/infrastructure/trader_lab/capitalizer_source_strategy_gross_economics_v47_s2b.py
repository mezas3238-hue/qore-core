"""V47-S2B frozen gross economics for the remediated FRACTAL population.

Consumes only the authoritative S2-A MAX3 exact-fill population from run
36642644284 / ff6c9745690dde76520aecf608e44401622a1074.

No candidate construction or selection happens here. Fresh Holdout is excluded.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cibo_10y_m1_clone_v1 as m1_clone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s2 as s2,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_V47_S2B_FROZEN_GROSS_ECONOMICS"
PREDECLARATION_COMMENT_ID = 5901733888
SOURCE_S2A_RUN_ID = 36642644284
SOURCE_S2A_SHA = "ff6c9745690dde76520aecf608e44401622a1074"
SOURCE_S2A_IDENTITY = s2.IDENTITY
EXPECTED_PERIOD_COUNTS = {
    "reserved": 30,
    "validation": 30,
    "development": 31,
}
ONE_MILLISECOND = timedelta(milliseconds=1)


@dataclass(frozen=True, slots=True)
class S2BGrossTrade:
    identity: str
    source_identity: str
    period: str
    symbol: str
    session: str
    operating_date: str
    side: str
    route: str
    entry_at: str
    entry_price: str
    stop_price: str
    target_price: str
    initial_risk_price: str
    target_r: str
    exit_at: str
    exit_price: str
    exit_reason: str
    realized_gross_r: str
    m1_bars_held: int
    exact_exit_ticks_required: bool
    stop_first_fallback_used: bool
    source_s2a_run_id: int = SOURCE_S2A_RUN_ID
    source_s2a_sha: str = SOURCE_S2A_SHA
    candidate_reselected: bool = False
    stop_changed: bool = False
    target_changed: bool = False
    costs_applied: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or self.source_identity != SOURCE_S2A_IDENTITY:
            raise ValueError("S2B identity drift")
        if self.period not in EXPECTED_PERIOD_COUNTS:
            raise ValueError("S2B period drift")
        if self.exit_reason not in {"STOP", "TARGET", "SESSION_EXIT"}:
            raise ValueError("S2B exit reason unsupported")
        if self.m1_bars_held <= 0:
            raise ValueError("S2B bars held must be positive")
        if (
            self.candidate_reselected
            or self.stop_changed
            or self.target_changed
            or self.costs_applied
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S2B governance drift")


@dataclass(frozen=True, slots=True)
class S2BMetrics:
    trades: int
    wins: int
    losses: int
    flats: int
    total_r: str
    expectancy_r: str
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    payoff_ratio: str | None
    max_drawdown_r: str
    max_losing_streak: int
    trade_sequence_sharpe: str | None
    trade_sequence_sortino: str | None
    stop_exits: int
    target_exits: int
    session_exits: int
    exact_tick_lifecycle_rows: int
    stop_first_fallback_rows: int
    target_r_min: str | None
    target_r_median: str | None
    target_r_mean: str | None
    target_r_max: str | None


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("S2B requires timezone-aware timestamps")
    return value.astimezone(UTC)


def _d(value: str) -> Decimal:
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("S2B requires finite decimal")
    return result


def _side(value: str) -> CapitalizerSide:
    return CapitalizerSide(value)


def _risk(
    *,
    side: CapitalizerSide,
    entry: Decimal,
    stop: Decimal,
) -> Decimal:
    risk = entry - stop if side is CapitalizerSide.LONG else stop - entry
    if risk <= 0:
        raise ValueError("S2B protected stop geometry invalid")
    return risk


def _realized_r(
    *,
    side: CapitalizerSide,
    entry: Decimal,
    exit_price: Decimal,
    risk: Decimal,
) -> Decimal:
    return (
        (exit_price - entry) / risk
        if side is CapitalizerSide.LONG
        else (entry - exit_price) / risk
    )


def _touches(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    stop: Decimal,
    target: Decimal,
) -> tuple[bool, bool]:
    if side is CapitalizerSide.LONG:
        return bar.low <= stop, bar.high >= target
    return bar.high >= stop, bar.low <= target


def _exit_quote_side(position_side: CapitalizerSide) -> CapitalizerSide:
    # Historical tick API maps LONG -> ASK and SHORT -> BID.
    # Closing LONG sells at BID; closing SHORT buys at ASK.
    return (
        CapitalizerSide.SHORT
        if position_side is CapitalizerSide.LONG
        else CapitalizerSide.LONG
    )


def _complete_ticks(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    exit_quote_side: CapitalizerSide,
    start: datetime,
    end: datetime,
    digits: int,
    request_prefix: str,
    depth: int = 0,
) -> tuple[s0.DecodedProviderTick, ...]:
    if depth > 20:
        raise RuntimeError("S2B provider tick pagination exceeded safe recursion")
    start_at = _aware(start)
    end_at = _aware(end)
    if end_at < start_at:
        return ()
    raw, has_more = s0.request_provider_tick_interval(
        client,
        symbol_id=symbol_id,
        side=exit_quote_side,
        interval_start=start_at,
        interval_end=end_at,
        request_id=(
            f"{request_prefix}:{depth}:{int(start_at.timestamp() * 1000)}"
        ),
    )
    if not has_more:
        return s0.decode_provider_tick_interval(
            raw,
            interval_start=start_at,
            interval_end=end_at,
            digits=digits,
            has_more=False,
        )

    span_ms = int((end_at - start_at).total_seconds() * 1000)
    if span_ms <= 1:
        raise RuntimeError("S2B incomplete provider tick interval cannot split")
    midpoint = start_at + timedelta(milliseconds=span_ms // 2)
    left = _complete_ticks(
        client,
        symbol_id=symbol_id,
        exit_quote_side=exit_quote_side,
        start=start_at,
        end=midpoint,
        digits=digits,
        request_prefix=request_prefix,
        depth=depth + 1,
    )
    right_start = midpoint + ONE_MILLISECOND
    if right_start > end_at:
        return left
    right = _complete_ticks(
        client,
        symbol_id=symbol_id,
        exit_quote_side=exit_quote_side,
        start=right_start,
        end=end_at,
        digits=digits,
        request_prefix=request_prefix,
        depth=depth + 1,
    )
    return tuple(sorted((*left, *right), key=lambda row: row.observed_at))


def _first_exact_exit(
    ticks: tuple[s0.DecodedProviderTick, ...],
    *,
    side: CapitalizerSide,
    stop: Decimal,
    target: Decimal,
) -> tuple[str, datetime, Decimal] | None:
    for tick in ticks:
        if side is CapitalizerSide.LONG:
            stop_hit = tick.price <= stop
            target_hit = tick.price >= target
        else:
            stop_hit = tick.price >= stop
            target_hit = tick.price <= target
        if stop_hit:
            return "STOP", tick.observed_at, stop
        if target_hit:
            return "TARGET", tick.observed_at, target
    return None


def _entry_bar(
    bars: tuple[CapitalizerM1Bar, ...],
    entry_at: datetime,
) -> int:
    at = _aware(entry_at)
    for index, bar in enumerate(bars):
        if bar.opened_at <= at < bar.closed_at:
            return index
    raise ValueError("S2B exact entry is outside provider-native M1")


def replay_trade(
    client: SpotwareCTraderOpenApiClient,
    *,
    source: s2.S2AdmittedFillRow,
    bars: tuple[CapitalizerM1Bar, ...],
    symbol_id: int,
    digits: int,
) -> S2BGrossTrade:
    side = _side(source.side)
    entry_at = _aware(datetime.fromisoformat(source.entry_at))
    entry = _d(source.entry_price)
    stop = _d(source.stop_price)
    target = _d(source.target_price)
    risk = _risk(side=side, entry=entry, stop=stop)
    target_r = _realized_r(
        side=side,
        entry=entry,
        exit_price=target,
        risk=risk,
    )
    if target_r <= 0:
        raise ValueError("S2B source target must be favorable")

    _session_start, session_end = s1.source_session_bounds(
        date.fromisoformat(source.operating_date),
        session=CapitalizerSession(source.session),
    )
    if not entry_at < session_end:
        raise ValueError("S2B entry must precede official source-session end")

    usable = tuple(
        bar
        for bar in bars
        if bar.opened_at < session_end
        and bar.closed_at > entry_at
    )
    if not usable:
        raise ValueError("S2B has no provider-native M1 after entry")

    start_index = _entry_bar(usable, entry_at)
    exact_required = False
    stop_first_fallback = False
    examined = 0

    for relative_index, bar in enumerate(usable[start_index:]):
        examined += 1
        stop_hit, target_hit = _touches(
            bar,
            side=side,
            stop=stop,
            target=target,
        )
        is_entry_bar = relative_index == 0

        if is_entry_bar and (stop_hit or target_hit):
            exact_required = True
            end = min(
                bar.closed_at - ONE_MILLISECOND,
                session_end - ONE_MILLISECOND,
            )
            ticks = _complete_ticks(
                client,
                symbol_id=symbol_id,
                exit_quote_side=_exit_quote_side(side),
                start=entry_at,
                end=end,
                digits=digits,
                request_prefix=(
                    f"s2b-entry:{source.period}:{source.symbol}:"
                    f"{source.entry_at}"
                ),
            )
            exact = _first_exact_exit(
                ticks,
                side=side,
                stop=stop,
                target=target,
            )
            if exact is not None:
                reason, exit_at, exit_price = exact
                return _trade_row(
                    source=source,
                    risk=risk,
                    target_r=target_r,
                    exit_reason=reason,
                    exit_at=exit_at,
                    exit_price=exit_price,
                    bars_held=examined,
                    exact_required=exact_required,
                    stop_first_fallback=stop_first_fallback,
                )
            # Any OHLC touch that occurred before entry is correctly ignored.
            continue

        if not stop_hit and not target_hit:
            continue
        if stop_hit and not target_hit:
            return _trade_row(
                source=source,
                risk=risk,
                target_r=target_r,
                exit_reason="STOP",
                exit_at=bar.closed_at,
                exit_price=stop,
                bars_held=examined,
                exact_required=exact_required,
                stop_first_fallback=stop_first_fallback,
            )
        if target_hit and not stop_hit:
            return _trade_row(
                source=source,
                risk=risk,
                target_r=target_r,
                exit_reason="TARGET",
                exit_at=bar.closed_at,
                exit_price=target,
                bars_held=examined,
                exact_required=exact_required,
                stop_first_fallback=stop_first_fallback,
            )

        exact_required = True
        try:
            ticks = _complete_ticks(
                client,
                symbol_id=symbol_id,
                exit_quote_side=_exit_quote_side(side),
                start=bar.opened_at,
                end=min(
                    bar.closed_at - ONE_MILLISECOND,
                    session_end - ONE_MILLISECOND,
                ),
                digits=digits,
                request_prefix=(
                    f"s2b-both:{source.period}:{source.symbol}:"
                    f"{bar.opened_at.isoformat()}"
                ),
            )
            exact = _first_exact_exit(
                ticks,
                side=side,
                stop=stop,
                target=target,
            )
        except RuntimeError:
            exact = None
        if exact is not None:
            reason, exit_at, exit_price = exact
            return _trade_row(
                source=source,
                risk=risk,
                target_r=target_r,
                exit_reason=reason,
                exit_at=exit_at,
                exit_price=exit_price,
                bars_held=examined,
                exact_required=exact_required,
                stop_first_fallback=stop_first_fallback,
            )

        # Frozen conservative ambiguity law.
        stop_first_fallback = True
        return _trade_row(
            source=source,
            risk=risk,
            target_r=target_r,
            exit_reason="STOP",
            exit_at=bar.closed_at,
            exit_price=stop,
            bars_held=examined,
            exact_required=exact_required,
            stop_first_fallback=stop_first_fallback,
        )

    final = max(
        (bar for bar in usable if bar.closed_at <= session_end),
        key=lambda row: row.closed_at,
        default=None,
    )
    if final is None:
        raise ValueError("S2B missing provider-native session close")
    return _trade_row(
        source=source,
        risk=risk,
        target_r=target_r,
        exit_reason="SESSION_EXIT",
        exit_at=final.closed_at,
        exit_price=final.close,
        bars_held=max(examined, 1),
        exact_required=exact_required,
        stop_first_fallback=stop_first_fallback,
    )


def _trade_row(
    *,
    source: s2.S2AdmittedFillRow,
    risk: Decimal,
    target_r: Decimal,
    exit_reason: str,
    exit_at: datetime,
    exit_price: Decimal,
    bars_held: int,
    exact_required: bool,
    stop_first_fallback: bool,
) -> S2BGrossTrade:
    side = _side(source.side)
    entry = _d(source.entry_price)
    realized = _realized_r(
        side=side,
        entry=entry,
        exit_price=exit_price,
        risk=risk,
    )
    return S2BGrossTrade(
        identity=IDENTITY,
        source_identity=source.identity,
        period=source.period,
        symbol=source.symbol,
        session=source.session,
        operating_date=source.operating_date,
        side=source.side,
        route=source.route,
        entry_at=source.entry_at,
        entry_price=source.entry_price,
        stop_price=source.stop_price,
        target_price=source.target_price,
        initial_risk_price=str(risk),
        target_r=str(target_r),
        exit_at=_aware(exit_at).isoformat(),
        exit_price=str(exit_price),
        exit_reason=exit_reason,
        realized_gross_r=str(realized),
        m1_bars_held=bars_held,
        exact_exit_ticks_required=exact_required,
        stop_first_fallback_used=stop_first_fallback,
    )


def _median(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _ratio(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def metrics(rows: tuple[S2BGrossTrade, ...]) -> S2BMetrics:
    ordered = tuple(
        sorted(rows, key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol))
    )
    values = tuple(_d(row.realized_gross_r) for row in ordered)
    targets = tuple(_d(row.target_r) for row in ordered)
    n = len(values)
    total = sum(values, Decimal("0"))
    mean = Decimal("0") if not n else total / Decimal(n)
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    gp = sum(wins, Decimal("0"))
    gl = -sum(losses, Decimal("0"))
    pf = None if gl == 0 else gp / gl
    avg_win = None if not wins else gp / Decimal(len(wins))
    avg_loss = None if not losses else gl / Decimal(len(losses))
    payoff = (
        None
        if avg_win is None or avg_loss is None or avg_loss == 0
        else avg_win / avg_loss
    )

    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
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

    sharpe: Decimal | None = None
    sortino: Decimal | None = None
    if n >= 2:
        variance = sum(
            ((value - mean) ** 2 for value in values),
            Decimal("0"),
        ) / Decimal(n - 1)
        std = variance.sqrt()
        if std > 0:
            sharpe = mean / std * Decimal(n).sqrt()
        downside = sum(
            ((min(value, Decimal("0"))) ** 2 for value in values),
            Decimal("0"),
        ) / Decimal(n)
        downside_dev = downside.sqrt()
        if downside_dev > 0:
            sortino = mean / downside_dev * Decimal(n).sqrt()

    return S2BMetrics(
        trades=n,
        wins=len(wins),
        losses=len(losses),
        flats=sum(value == 0 for value in values),
        total_r=str(total),
        expectancy_r=str(mean),
        gross_profit_r=str(gp),
        gross_loss_r=str(gl),
        profit_factor=_ratio(pf),
        payoff_ratio=_ratio(payoff),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        trade_sequence_sharpe=_ratio(sharpe),
        trade_sequence_sortino=_ratio(sortino),
        stop_exits=sum(row.exit_reason == "STOP" for row in ordered),
        target_exits=sum(row.exit_reason == "TARGET" for row in ordered),
        session_exits=sum(row.exit_reason == "SESSION_EXIT" for row in ordered),
        exact_tick_lifecycle_rows=sum(
            row.exact_exit_ticks_required for row in ordered
        ),
        stop_first_fallback_rows=sum(
            row.stop_first_fallback_used for row in ordered
        ),
        target_r_min=None if not targets else str(min(targets)),
        target_r_median=_ratio(_median(targets)),
        target_r_mean=(
            None
            if not targets
            else str(sum(targets, Decimal("0")) / Decimal(len(targets)))
        ),
        target_r_max=None if not targets else str(max(targets)),
    )


def _load_s2a_rows(root: Path) -> tuple[s2.S2AdmittedFillRow, ...]:
    rows: list[s2.S2AdmittedFillRow] = []
    for path in sorted(root.glob("capitalizer-s2a-*-max3.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(s2.S2AdmittedFillRow(**json.loads(line)))
    counts = {
        period: sum(row.period == period for row in rows)
        for period in EXPECTED_PERIOD_COUNTS
    }
    if counts != EXPECTED_PERIOD_COUNTS:
        raise ValueError(
            f"S2B frozen S2-A population drift: {counts} != {EXPECTED_PERIOD_COUNTS}"
        )
    if len(rows) != sum(EXPECTED_PERIOD_COUNTS.values()):
        raise ValueError("S2B frozen S2-A total population drift")
    return tuple(rows)


def write_market(
    *,
    client: SpotwareCTraderOpenApiClient,
    rows: tuple[s2.S2AdmittedFillRow, ...],
    bars: tuple[CapitalizerM1Bar, ...],
    symbol: str,
    symbol_id: int,
    digits: int,
    output: Path,
) -> tuple[S2BGrossTrade, ...]:
    selected = tuple(row for row in rows if row.symbol == symbol)
    trades = tuple(
        replay_trade(
            client,
            source=row,
            bars=bars,
            symbol_id=symbol_id,
            digits=digits,
        )
        for row in selected
    )
    output.mkdir(parents=True, exist_ok=True)
    with (output / f"capitalizer-s2b-{symbol.lower()}-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in trades:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    report = {
        "identity": IDENTITY,
        "source_s2a_run_id": SOURCE_S2A_RUN_ID,
        "source_s2a_sha": SOURCE_S2A_SHA,
        "symbol": symbol,
        "frozen_population_rows": len(selected),
        "replayed_rows": len(trades),
        "metrics": asdict(metrics(trades)),
        "candidate_reselected": False,
        "costs_applied": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }
    (output / f"capitalizer-s2b-{symbol.lower()}-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return trades


def _load_trade_rows(root: Path) -> tuple[S2BGrossTrade, ...]:
    rows: list[S2BGrossTrade] = []
    for path in sorted(root.rglob("capitalizer-s2b-*-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(S2BGrossTrade(**json.loads(line)))
    return tuple(rows)


def aggregate(root: Path, output: Path) -> dict[str, object]:
    rows = _load_trade_rows(root)
    if len(rows) != sum(EXPECTED_PERIOD_COUNTS.values()):
        raise ValueError(f"S2B requires 91 frozen trades, got {len(rows)}")
    by_period: dict[str, object] = {}
    by_year: dict[str, object] = {}
    for period, expected in EXPECTED_PERIOD_COUNTS.items():
        subset = tuple(row for row in rows if row.period == period)
        if len(subset) != expected:
            raise ValueError(f"S2B {period} population drift")
        by_period[period] = asdict(metrics(subset))

    years: dict[int, list[S2BGrossTrade]] = defaultdict(list)
    for row in rows:
        years[datetime.fromisoformat(row.entry_at).year].append(row)
    for year in sorted(years):
        by_year[str(year)] = asdict(metrics(tuple(years[year])))

    chronology = tuple(
        sorted(rows, key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol))
    )
    output.mkdir(parents=True, exist_ok=True)
    with (output / "capitalizer-s2b-chronology.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in chronology:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_s2a_run_id": SOURCE_S2A_RUN_ID,
        "source_s2a_sha": SOURCE_S2A_SHA,
        "frozen_population_rows": len(rows),
        "periods": by_period,
        "years": by_year,
        "overall": asdict(metrics(rows)),
        "population_reselected": False,
        "costs_applied": False,
        "fresh_holdout_opened": False,
        "full_cognitive_gate_replayed": False,
        "ftm_stream_included": False,
        "trader_certified": False,
        "next_phase": "S2B_GROSS_ECONOMICS_READY_FOR_ADJUDICATION",
    }
    (output / "capitalizer-s2b-gross-economics.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _market(args: argparse.Namespace) -> None:
    rows = _load_s2a_rows(args.s2a_root)
    selected = tuple(row for row in rows if row.symbol == args.symbol)
    if not selected:
        # A market may legitimately have no frozen MAX3 rows.
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / f"capitalizer-s2b-{args.symbol.lower()}-trades.jsonl").write_text(
            "",
            encoding="utf-8",
        )
        report = {
            "identity": IDENTITY,
            "source_s2a_run_id": SOURCE_S2A_RUN_ID,
            "source_s2a_sha": SOURCE_S2A_SHA,
            "symbol": args.symbol,
            "frozen_population_rows": 0,
            "replayed_rows": 0,
            "metrics": asdict(metrics(())),
            "candidate_reselected": False,
            "costs_applied": False,
            "fresh_holdout_opened": False,
            "trader_certified": False,
        }
        (
            args.output / f"capitalizer-s2b-{args.symbol.lower()}-report.json"
        ).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return

    client = SpotwareCTraderOpenApiClient(
        credentials=m1_clone._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"S2B cTrader authentication failed: {ready.error}")
        _provider_symbol, symbol_id, digits = m1_clone._selected_symbol(
            client,
            args.symbol,
        )
        bars = s1._load_consumed_bars(args.m1_root)
        if not bars or any(row.symbol != args.symbol for row in bars):
            raise ValueError("S2B provider-native M1 symbol/source mismatch")
        write_market(
            client=client,
            rows=rows,
            bars=bars,
            symbol=args.symbol,
            symbol_id=symbol_id,
            digits=digits,
            output=args.output,
        )
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("s2a_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("--symbol", required=True)
    market.add_argument("--output", type=Path, required=True)

    matrix = sub.add_parser("aggregate")
    matrix.add_argument("input", type=Path)
    matrix.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "market":
        _market(args)
    else:
        print(json.dumps(aggregate(args.input, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
