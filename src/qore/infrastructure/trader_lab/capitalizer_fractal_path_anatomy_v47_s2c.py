"""V47-S2C provider-native MAE/MFE path audit for frozen FRACTAL economics."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
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
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_V47_S2C_FRACTAL_PATH_AND_LOSS_ANATOMY"
PREDECLARATION_COMMENT_ID = 5901892907
SOURCE_S2B_RUN_ID = 36651366703
SOURCE_S2B_SHA = "59d826f3b24031e52e6c0f32e8cca1ecfb4d0524"
ONE_MILLISECOND = timedelta(milliseconds=1)


@dataclass(frozen=True, slots=True)
class PathPoint:
    observed_at: datetime
    price: Decimal
    exact_tick: bool

    def __post_init__(self) -> None:
        s1._aware(self.observed_at)
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError("path point price must be positive finite")


@dataclass(frozen=True, slots=True)
class FractalPathAuditRow:
    identity: str
    period: str
    symbol: str
    session: str
    side: str
    entry_at: str
    exit_at: str
    exit_reason: str
    realized_gross_r: str
    outcome_label: str
    mae_r: str
    mfe_r: str
    mae_at: str
    mfe_at: str
    time_to_mae_minutes: int
    time_to_mfe_minutes: int
    path_order: str
    exact_partial_interval_ticks_used: bool
    terminal_outcome_research_label_only: bool = True
    mae_mfe_productive_feature_allowed: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S2C path identity drift")
        if self.outcome_label not in {"WINNER", "LOSER", "FLAT"}:
            raise ValueError("S2C outcome label drift")
        if self.path_order not in {
            "MAE_BEFORE_MFE",
            "MFE_BEFORE_MAE",
            "SAME_INTERVAL_AMBIGUOUS",
        }:
            raise ValueError("S2C path order drift")
        if (
            not self.terminal_outcome_research_label_only
            or self.mae_mfe_productive_feature_allowed
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S2C path governance drift")


def _side(value: str) -> CapitalizerSide:
    return CapitalizerSide(value)


def _risk(row: s2b.S2BGrossTrade) -> Decimal:
    value = Decimal(row.initial_risk_price)
    if not value.is_finite() or value <= 0:
        raise ValueError("S2C requires positive initial risk")
    return value


def _overlapping_bars(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    start: datetime,
    end: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    start_at = s1._aware(start)
    end_at = s1._aware(end)
    return tuple(
        row
        for row in bars
        if row.opened_at < end_at and row.closed_at > start_at
    )


def _partial_ticks(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    side: CapitalizerSide,
    start: datetime,
    end: datetime,
    digits: int,
    prefix: str,
) -> tuple[PathPoint, ...]:
    if s1._aware(end) < s1._aware(start):
        return ()
    ticks = s2b._complete_ticks(
        client,
        symbol_id=symbol_id,
        exit_quote_side=s2b._exit_quote_side(side),
        start=start,
        end=end,
        digits=digits,
        request_prefix=prefix,
    )
    return tuple(
        PathPoint(
            observed_at=row.observed_at,
            price=row.price,
            exact_tick=True,
        )
        for row in ticks
    )


def build_path_points(
    client: SpotwareCTraderOpenApiClient,
    *,
    trade: s2b.S2BGrossTrade,
    bars: tuple[CapitalizerM1Bar, ...],
    symbol_id: int,
    digits: int,
) -> tuple[tuple[PathPoint, ...], bool]:
    entry_at = s1._aware(datetime.fromisoformat(trade.entry_at))
    exit_at = s1._aware(datetime.fromisoformat(trade.exit_at))
    if exit_at < entry_at:
        raise ValueError("S2C exit precedes entry")
    side = _side(trade.side)
    overlap = _overlapping_bars(bars, start=entry_at, end=exit_at + ONE_MILLISECOND)
    if not overlap:
        raise ValueError("S2C path has no provider-native M1")

    exact_partial_interval_ticks_used = False
    points: list[PathPoint] = [
        PathPoint(
            observed_at=entry_at,
            price=Decimal(trade.entry_price),
            exact_tick=True,
        )
    ]
    for index, bar in enumerate(overlap):
        partial_start = max(entry_at, bar.opened_at)
        partial_end = min(exit_at, bar.closed_at - ONE_MILLISECOND)
        partial = partial_start > bar.opened_at or partial_end < bar.closed_at - ONE_MILLISECOND
        if partial:
            exact_partial_interval_ticks_used = True
            points.extend(
                _partial_ticks(
                    client,
                    symbol_id=symbol_id,
                    side=side,
                    start=partial_start,
                    end=partial_end,
                    digits=digits,
                    prefix=(
                        f"s2c-path:{trade.period}:{trade.symbol}:"
                        f"{trade.entry_at}:{index}"
                    ),
                )
            )
            continue

        # Full M1 interval: magnitudes are exact to provider-native M1, but
        # high-vs-low ordering inside this minute is deliberately unresolved.
        points.append(
            PathPoint(
                observed_at=bar.opened_at,
                price=bar.low,
                exact_tick=False,
            )
        )
        points.append(
            PathPoint(
                observed_at=bar.opened_at,
                price=bar.high,
                exact_tick=False,
            )
        )

    points.append(
        PathPoint(
            observed_at=exit_at,
            price=Decimal(trade.exit_price),
            exact_tick=True,
        )
    )
    return (
        tuple(sorted(points, key=lambda row: (row.observed_at, row.price))),
        exact_partial_interval_ticks_used,
    )


def audit_trade(
    client: SpotwareCTraderOpenApiClient,
    *,
    trade: s2b.S2BGrossTrade,
    bars: tuple[CapitalizerM1Bar, ...],
    symbol_id: int,
    digits: int,
) -> FractalPathAuditRow:
    points, exact_partial_interval_ticks_used = build_path_points(
        client,
        trade=trade,
        bars=bars,
        symbol_id=symbol_id,
        digits=digits,
    )
    side = _side(trade.side)
    entry = Decimal(trade.entry_price)
    risk = _risk(trade)
    if side is CapitalizerSide.LONG:
        adverse = tuple((entry - row.price) / risk for row in points)
        favorable = tuple((row.price - entry) / risk for row in points)
    else:
        adverse = tuple((row.price - entry) / risk for row in points)
        favorable = tuple((entry - row.price) / risk for row in points)

    mae = max(max(adverse), Decimal("0"))
    mfe = max(max(favorable), Decimal("0"))
    mae_indices = tuple(index for index, value in enumerate(adverse) if value == mae)
    mfe_indices = tuple(index for index, value in enumerate(favorable) if value == mfe)
    mae_index = mae_indices[0]
    mfe_index = mfe_indices[0]
    mae_point = points[mae_index]
    mfe_point = points[mfe_index]

    if mae_point.observed_at < mfe_point.observed_at:
        order = "MAE_BEFORE_MFE"
    elif mfe_point.observed_at < mae_point.observed_at:
        order = "MFE_BEFORE_MAE"
    else:
        order = "SAME_INTERVAL_AMBIGUOUS"

    entry_at = s1._aware(datetime.fromisoformat(trade.entry_at))
    realized = Decimal(trade.realized_gross_r)
    label = "WINNER" if realized > 0 else "LOSER" if realized < 0 else "FLAT"
    return FractalPathAuditRow(
        identity=IDENTITY,
        period=trade.period,
        symbol=trade.symbol,
        session=trade.session,
        side=trade.side,
        entry_at=trade.entry_at,
        exit_at=trade.exit_at,
        exit_reason=trade.exit_reason,
        realized_gross_r=trade.realized_gross_r,
        outcome_label=label,
        mae_r=str(mae),
        mfe_r=str(mfe),
        mae_at=mae_point.observed_at.isoformat(),
        mfe_at=mfe_point.observed_at.isoformat(),
        time_to_mae_minutes=max(
            0,
            int((mae_point.observed_at - entry_at).total_seconds() // 60),
        ),
        time_to_mfe_minutes=max(
            0,
            int((mfe_point.observed_at - entry_at).total_seconds() // 60),
        ),
        path_order=order,
        exact_partial_interval_ticks_used=exact_partial_interval_ticks_used,
    )


def _median(values: tuple[Decimal, ...]) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    value = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / Decimal("2")
    )
    return str(value)


def summarize(rows: tuple[FractalPathAuditRow, ...]) -> dict[str, object]:
    winners = tuple(row for row in rows if row.outcome_label == "WINNER")
    losers = tuple(row for row in rows if row.outcome_label == "LOSER")
    full_stop = tuple(row for row in losers if row.exit_reason == "STOP")

    def vals(sample: tuple[FractalPathAuditRow, ...], field: str) -> tuple[Decimal, ...]:
        return tuple(Decimal(getattr(row, field)) for row in sample)

    return {
        "trades": len(rows),
        "winners": len(winners),
        "losers": len(losers),
        "full_stop_losers": len(full_stop),
        "median_mae_r_winners": _median(vals(winners, "mae_r")),
        "median_mfe_r_winners": _median(vals(winners, "mfe_r")),
        "median_mae_r_losers": _median(vals(losers, "mae_r")),
        "median_mfe_r_losers": _median(vals(losers, "mfe_r")),
        "median_mfe_r_full_stop_losers": _median(vals(full_stop, "mfe_r")),
        "mae_before_mfe": sum(row.path_order == "MAE_BEFORE_MFE" for row in rows),
        "mfe_before_mae": sum(row.path_order == "MFE_BEFORE_MAE" for row in rows),
        "same_interval_ambiguous": sum(
            row.path_order == "SAME_INTERVAL_AMBIGUOUS" for row in rows
        ),
    }


def _load_trades(root: Path, symbol: str) -> tuple[s2b.S2BGrossTrade, ...]:
    rows: list[s2b.S2BGrossTrade] = []
    for path in root.rglob("capitalizer-s2b-chronology.jsonl"):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = s2b.S2BGrossTrade(**json.loads(line))
            if row.symbol == symbol:
                rows.append(row)
    return tuple(
        sorted(rows, key=lambda row: datetime.fromisoformat(row.entry_at))
    )


def write_market(
    output: Path,
    rows: tuple[FractalPathAuditRow, ...],
    symbol: str,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / f"capitalizer-s2c-path-{symbol.lower()}.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_s2b_run_id": SOURCE_S2B_RUN_ID,
        "source_s2b_sha": SOURCE_S2B_SHA,
        "summary": summarize(rows),
        "mae_mfe_productive_feature_allowed": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }
    (output / f"capitalizer-s2c-path-{symbol.lower()}-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )


def aggregate(root: Path, output: Path) -> dict[str, object]:
    rows: list[FractalPathAuditRow] = []
    for path in sorted(root.rglob("capitalizer-s2c-path-*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(FractalPathAuditRow(**json.loads(line)))
    if len(rows) != 91:
        raise ValueError(f"S2C path audit requires 91 rows, got {len(rows)}")
    periods = {
        period: summarize(tuple(row for row in rows if row.period == period))
        for period in ("reserved", "validation", "development")
    }
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_s2b_run_id": SOURCE_S2B_RUN_ID,
        "source_s2b_sha": SOURCE_S2B_SHA,
        "frozen_population_rows": len(rows),
        "periods": periods,
        "overall_descriptive_only": summarize(tuple(rows)),
        "mae_mfe_audit_complete": True,
        "terminal_outcome_research_label_only": True,
        "mae_mfe_productive_feature_allowed": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v47-s2c-fractal-path-anatomy.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))
    return payload


def _market(args: argparse.Namespace) -> None:
    trades = _load_trades(args.s2b_root, args.symbol)
    if not trades:
        write_market(args.output, (), args.symbol)
        return
    client = SpotwareCTraderOpenApiClient(
        credentials=m1_clone._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"S2C cTrader authentication failed: {ready.error}")
        _provider, symbol_id, digits = m1_clone._selected_symbol(client, args.symbol)
        bars = s1._load_consumed_bars(args.m1_root)
        if not bars or any(row.symbol != args.symbol for row in bars):
            raise ValueError("S2C provider-native M1 source mismatch")
        audited = tuple(
            audit_trade(
                client,
                trade=trade,
                bars=bars,
                symbol_id=symbol_id,
                digits=digits,
            )
            for trade in trades
        )
        write_market(args.output, audited, args.symbol)
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("s2b_root", type=Path)
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
        aggregate(args.input, args.output)


if __name__ == "__main__":
    main()
