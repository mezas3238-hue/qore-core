"""V47-S2E gross economics for the frozen S2D two-route population.

This module is route-agnostic. It consumes only S2D-selected rows and applies
the same exact-fill/protected-stop/structural-target/session lifecycle to both
FRACTAL and FTM. It performs no candidate selection.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import (
    capitalizer_cibo_10y_m1_clone_v1 as m1_clone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_gross_economics_v47_s2b as s2b,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_two_route_population_v47_s2d as s2d,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_V47_S2E_TWO_ROUTE_GROSS_ECONOMICS"


@dataclass(frozen=True, slots=True)
class S2EGrossTrade:
    identity: str
    source_population_identity: str
    source_stream: str
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
    candidate_reselected: bool = False
    route_priority_used: bool = False
    costs_applied: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S2E identity drift")
        if self.source_population_identity != s2d.IDENTITY:
            raise ValueError("S2E source population drift")
        if self.source_stream not in {"FRACTAL", "FTM"}:
            raise ValueError("S2E stream drift")
        if self.exit_reason not in {"STOP", "TARGET", "SESSION_EXIT"}:
            raise ValueError("S2E exit reason drift")
        if (
            self.candidate_reselected
            or self.route_priority_used
            or self.costs_applied
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S2E governance drift")


@dataclass(frozen=True, slots=True)
class S2EMetrics:
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
    stop_exits: int
    target_exits: int
    session_exits: int
    exact_tick_lifecycle_rows: int
    stop_first_fallback_rows: int


def _d(value: str) -> Decimal:
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("S2E requires finite Decimal")
    return result


def _side(value: str) -> CapitalizerSide:
    return CapitalizerSide(value)


def _entry_bar(
    bars: tuple[CapitalizerM1Bar, ...],
    entry_at: datetime,
) -> int:
    at = entry_at.astimezone(UTC)
    for index, bar in enumerate(bars):
        if bar.opened_at <= at < bar.closed_at:
            return index
    raise ValueError("S2E exact entry outside provider-native M1")


def _trade(
    *,
    source: s2d.S2DPopulationRow,
    risk: Decimal,
    target_r: Decimal,
    exit_reason: str,
    exit_at: datetime,
    exit_price: Decimal,
    bars_held: int,
    exact_required: bool,
    stop_first_fallback: bool,
) -> S2EGrossTrade:
    side = _side(source.side)
    entry = _d(source.entry_price)
    realized_r = s2b._realized_r(
        side=side,
        entry=entry,
        exit_price=exit_price,
        risk=risk,
    )
    return S2EGrossTrade(
        identity=IDENTITY,
        source_population_identity=s2d.IDENTITY,
        source_stream=source.source_stream,
        period=source.period,
        symbol=source.symbol,
        session=source.session,
        operating_date=source.operating_date,
        side=side.value,
        route=source.route,
        entry_at=source.entry_at,
        entry_price=source.entry_price,
        stop_price=source.stop_price,
        target_price=source.target_price,
        initial_risk_price=str(risk),
        target_r=str(target_r),
        exit_at=exit_at.astimezone(UTC).isoformat(),
        exit_price=str(exit_price),
        exit_reason=exit_reason,
        realized_gross_r=str(realized_r),
        m1_bars_held=bars_held,
        exact_exit_ticks_required=exact_required,
        stop_first_fallback_used=stop_first_fallback,
    )


def replay_trade(
    client: SpotwareCTraderOpenApiClient,
    *,
    source: s2d.S2DPopulationRow,
    bars: tuple[CapitalizerM1Bar, ...],
    symbol_id: int,
    digits: int,
) -> S2EGrossTrade:
    entry_at = datetime.fromisoformat(source.entry_at).astimezone(UTC)
    entry = _d(source.entry_price)
    stop = _d(source.stop_price)
    target = _d(source.target_price)
    side = _side(source.side)
    risk = s2b._risk(side=side, entry=entry, stop=stop)
    target_r = s2b._realized_r(
        side=side,
        entry=entry,
        exit_price=target,
        risk=risk,
    )
    if target_r <= 0:
        raise ValueError("S2E structural target must be favorable")

    _session_start, session_end = s1.source_session_bounds(
        date.fromisoformat(source.operating_date),
        session=CapitalizerSession(source.session),
    )
    usable = tuple(
        bar
        for bar in bars
        if bar.opened_at < session_end and bar.closed_at > entry_at
    )
    if not usable:
        raise ValueError("S2E missing provider-native M1 after entry")
    start_index = _entry_bar(usable, entry_at)
    exact_required = False
    stop_first = False
    examined = 0

    for relative_index, bar in enumerate(usable[start_index:]):
        examined += 1
        stop_hit, target_hit = s2b._touches(
            bar,
            side=side,
            stop=stop,
            target=target,
        )
        is_entry_bar = relative_index == 0
        if is_entry_bar and (stop_hit or target_hit):
            exact_required = True
            ticks = s2b._complete_ticks(
                client,
                symbol_id=symbol_id,
                exit_quote_side=s2b._exit_quote_side(side),
                start=entry_at,
                end=min(
                    bar.closed_at - s2b.ONE_MILLISECOND,
                    session_end - s2b.ONE_MILLISECOND,
                ),
                digits=digits,
                request_prefix=f"s2e-entry:{source.symbol}:{source.entry_at}",
            )
            exact = s2b._first_exact_exit(
                ticks,
                side=side,
                stop=stop,
                target=target,
            )
            if exact is not None:
                reason, exit_at, exit_price = exact
                return _trade(
                    source=source,
                    risk=risk,
                    target_r=target_r,
                    exit_reason=reason,
                    exit_at=exit_at,
                    exit_price=exit_price,
                    bars_held=examined,
                    exact_required=exact_required,
                    stop_first_fallback=stop_first,
                )
            continue

        if not stop_hit and not target_hit:
            continue
        if stop_hit and not target_hit:
            return _trade(
                source=source,
                risk=risk,
                target_r=target_r,
                exit_reason="STOP",
                exit_at=bar.closed_at,
                exit_price=stop,
                bars_held=examined,
                exact_required=exact_required,
                stop_first_fallback=stop_first,
            )
        if target_hit and not stop_hit:
            return _trade(
                source=source,
                risk=risk,
                target_r=target_r,
                exit_reason="TARGET",
                exit_at=bar.closed_at,
                exit_price=target,
                bars_held=examined,
                exact_required=exact_required,
                stop_first_fallback=stop_first,
            )

        exact_required = True
        try:
            ticks = s2b._complete_ticks(
                client,
                symbol_id=symbol_id,
                exit_quote_side=s2b._exit_quote_side(side),
                start=bar.opened_at,
                end=min(
                    bar.closed_at - s2b.ONE_MILLISECOND,
                    session_end - s2b.ONE_MILLISECOND,
                ),
                digits=digits,
                request_prefix=f"s2e-both:{source.symbol}:{bar.opened_at.isoformat()}",
            )
            exact = s2b._first_exact_exit(
                ticks,
                side=side,
                stop=stop,
                target=target,
            )
        except RuntimeError:
            exact = None
        if exact is not None:
            reason, exit_at, exit_price = exact
            return _trade(
                source=source,
                risk=risk,
                target_r=target_r,
                exit_reason=reason,
                exit_at=exit_at,
                exit_price=exit_price,
                bars_held=examined,
                exact_required=exact_required,
                stop_first_fallback=stop_first,
            )
        stop_first = True
        return _trade(
            source=source,
            risk=risk,
            target_r=target_r,
            exit_reason="STOP",
            exit_at=bar.closed_at,
            exit_price=stop,
            bars_held=examined,
            exact_required=exact_required,
            stop_first_fallback=stop_first,
        )

    final = max(
        (bar for bar in usable if bar.closed_at <= session_end),
        key=lambda row: row.closed_at,
        default=None,
    )
    if final is None:
        raise ValueError("S2E missing provider-native session close")
    return _trade(
        source=source,
        risk=risk,
        target_r=target_r,
        exit_reason="SESSION_EXIT",
        exit_at=final.closed_at,
        exit_price=final.close,
        bars_held=max(examined, 1),
        exact_required=exact_required,
        stop_first_fallback=stop_first,
    )


def metrics(rows: tuple[S2EGrossTrade, ...]) -> S2EMetrics:
    ordered = tuple(
        sorted(rows, key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol))
    )
    values = tuple(_d(row.realized_gross_r) for row in ordered)
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    total = sum(values, Decimal("0"))
    gp = sum(wins, Decimal("0"))
    gl = -sum(losses, Decimal("0"))
    expectancy = Decimal("0") if not values else total / Decimal(len(values))
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
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return S2EMetrics(
        trades=len(values),
        wins=len(wins),
        losses=len(losses),
        flats=sum(value == 0 for value in values),
        total_r=str(total),
        expectancy_r=str(expectancy),
        gross_profit_r=str(gp),
        gross_loss_r=str(gl),
        profit_factor=None if pf is None else str(pf),
        payoff_ratio=None if payoff is None else str(payoff),
        max_drawdown_r=str(dd),
        max_losing_streak=max_streak,
        stop_exits=sum(row.exit_reason == "STOP" for row in ordered),
        target_exits=sum(row.exit_reason == "TARGET" for row in ordered),
        session_exits=sum(row.exit_reason == "SESSION_EXIT" for row in ordered),
        exact_tick_lifecycle_rows=sum(row.exact_exit_ticks_required for row in ordered),
        stop_first_fallback_rows=sum(row.stop_first_fallback_used for row in ordered),
    )


def _load_population(root: Path) -> tuple[s2d.S2DPopulationRow, ...]:
    path = root / "capitalizer-s2d-selected.jsonl"
    if not path.is_file():
        raise ValueError("S2E selected S2D population missing")
    rows: list[s2d.S2DPopulationRow] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(s2d.S2DPopulationRow(**json.loads(line)))
    return tuple(rows)


def write_market(
    *,
    client: SpotwareCTraderOpenApiClient,
    population: tuple[s2d.S2DPopulationRow, ...],
    bars: tuple[CapitalizerM1Bar, ...],
    symbol: str,
    symbol_id: int,
    digits: int,
    output: Path,
) -> None:
    rows = tuple(row for row in population if row.symbol == symbol)
    trades = tuple(
        replay_trade(
            client,
            source=row,
            bars=bars,
            symbol_id=symbol_id,
            digits=digits,
        )
        for row in rows
    )
    output.mkdir(parents=True, exist_ok=True)
    with (output / f"capitalizer-s2e-{symbol.lower()}-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in trades:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "population_rows": len(rows),
        "replayed_rows": len(trades),
        "metrics": asdict(metrics(trades)),
        "candidate_reselected": False,
        "route_priority_used": False,
        "costs_applied": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }
    (output / f"capitalizer-s2e-{symbol.lower()}-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def aggregate(root: Path, output: Path) -> dict[str, object]:
    rows: list[S2EGrossTrade] = []
    for path in sorted(root.rglob("capitalizer-s2e-*-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(S2EGrossTrade(**json.loads(line)))
    by_period: dict[str, object] = {}
    for period in ("reserved", "validation", "development"):
        subset = tuple(row for row in rows if row.period == period)
        by_period[period] = asdict(metrics(subset))
    by_stream: dict[str, object] = {}
    for stream in ("FRACTAL", "FTM"):
        subset = tuple(row for row in rows if row.source_stream == stream)
        by_stream[stream] = asdict(metrics(subset))
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "population_rows": len(rows),
        "overall": asdict(metrics(tuple(rows))),
        "periods": by_period,
        "streams": by_stream,
        "candidate_reselected": False,
        "route_priority_used": False,
        "costs_applied": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-s2e-gross-economics.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _market(args: argparse.Namespace) -> None:
    population = _load_population(args.population_root)
    selected = tuple(row for row in population if row.symbol == args.symbol)
    if not selected:
        args.output.mkdir(parents=True, exist_ok=True)
        with (args.output / f"capitalizer-s2e-{args.symbol.lower()}-trades.jsonl").open(
            "w",
            encoding="utf-8",
        ):
            pass
        report = {
            "identity": IDENTITY,
            "symbol": args.symbol,
            "population_rows": 0,
            "replayed_rows": 0,
            "metrics": asdict(metrics(())),
            "candidate_reselected": False,
            "route_priority_used": False,
            "costs_applied": False,
            "fresh_holdout_opened": False,
            "trader_certified": False,
        }
        (args.output / f"capitalizer-s2e-{args.symbol.lower()}-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return

    client = SpotwareCTraderOpenApiClient(
        credentials=m1_clone._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"S2E cTrader authentication failed: {ready.error}")
        _provider_symbol, symbol_id, digits = m1_clone._selected_symbol(
            client,
            args.symbol,
        )
        bars = s1._load_consumed_bars(args.m1_root)
        if not bars or any(row.symbol != args.symbol for row in bars):
            raise ValueError("S2E provider-native M1 mismatch")
        write_market(
            client=client,
            population=population,
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
    market.add_argument("population_root", type=Path)
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
