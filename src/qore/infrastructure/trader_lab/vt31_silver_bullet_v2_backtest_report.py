"""Directional characterization for the source-bound VT-31 Silver Bullet V2 backtest."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    Vt31SilverBulletV2BacktestError,
    _contiguous,
    _expected_next,
    _load,
    _ny_date,
    _ny_wall,
    run_vt31_silver_bullet_v2_backtest,
)
from qore.infrastructure.traders.contracts import DemoTradingDecision
from qore.infrastructure.traders.vt31_silver_bullet_v2 import (
    Vt31SilverBulletV2Input,
    evaluate_vt31_silver_bullet_v2,
)

_SCHEMA = "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1"
_SYMBOL = "NAS100"
_SIDES = ("long", "short")
_SIDE_SET = frozenset(_SIDES)
_OUTCOMES = frozenset(
    {"target", "stop", "breakeven", "gap_censored", "data_end_censored"}
)
_TERMINAL_OUTCOMES = frozenset({"target", "stop", "breakeven"})


class Vt31SilverBulletV2BacktestReportError(Vt31SilverBulletV2BacktestError):
    """Directional VT-31 V2 report enrichment failed closed."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _TradeRow:
    side: str
    outcome: str
    r_multiple: Decimal | None


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2DirectionalSummary:
    """One immutable Core-style direction bucket."""

    side: str
    setup_count: int
    filled_count: int
    terminal_sample_size: int
    target_count: int
    stop_count: int
    breakeven_count: int
    gap_censored_count: int
    data_end_censored_count: int
    win_rate: Decimal
    expectancy_r: Decimal
    population_variance_r: Decimal

    @property
    def unfilled_count(self) -> int:
        return self.setup_count - self.filled_count

    @property
    def fill_rate(self) -> Decimal:
        if not self.setup_count:
            return Decimal(0)
        return Decimal(self.filled_count) / Decimal(self.setup_count)

    def payload(self) -> dict[str, object]:
        return {
            "setup_count": self.setup_count,
            "filled_count": self.filled_count,
            "unfilled_count": self.unfilled_count,
            "fill_rate": format(self.fill_rate, "f"),
            "terminal_sample_size": self.terminal_sample_size,
            "target_count": self.target_count,
            "stop_count": self.stop_count,
            "breakeven_count": self.breakeven_count,
            "gap_censored_count": self.gap_censored_count,
            "data_end_censored_count": self.data_end_censored_count,
            "win_rate": format(self.win_rate, "f"),
            "expectancy_r": format(self.expectancy_r, "f"),
            "population_variance_r": format(self.population_variance_r, "f"),
        }


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt31SilverBulletV2BacktestReportError(f"{field_name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise Vt31SilverBulletV2BacktestReportError(f"{field_name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise Vt31SilverBulletV2BacktestReportError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _strict_int(value: object, *, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt31SilverBulletV2BacktestReportError(
            f"{field_name} must be a non-negative int"
        )
    return value


def _optional_decimal(value: object, *, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not str or not value:
        raise Vt31SilverBulletV2BacktestReportError(
            f"{field_name} must be decimal text or null"
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise Vt31SilverBulletV2BacktestReportError(
            f"{field_name} must be decimal text"
        ) from error
    if not parsed.is_finite():
        raise Vt31SilverBulletV2BacktestReportError(f"{field_name} must be finite")
    return parsed


def _trade_rows(payload: dict[str, object]) -> tuple[_TradeRow, ...]:
    raw_trades = _array(payload.get("trades"), field_name="trades")
    rows: list[_TradeRow] = []
    for index, raw in enumerate(raw_trades):
        trade = _object(raw, field_name=f"trade[{index}]")
        side = _text(trade.get("side"), field_name=f"trade[{index}] side")
        if side not in _SIDE_SET:
            raise Vt31SilverBulletV2BacktestReportError(
                f"trade[{index}] side is not canonical LONG/SHORT"
            )
        outcome = _text(trade.get("outcome"), field_name=f"trade[{index}] outcome")
        if outcome not in _OUTCOMES:
            raise Vt31SilverBulletV2BacktestReportError(
                f"trade[{index}] outcome is unsupported"
            )
        r_multiple = _optional_decimal(
            trade.get("r_multiple"), field_name=f"trade[{index}] r_multiple"
        )
        terminal = outcome in _TERMINAL_OUTCOMES
        if terminal != (r_multiple is not None):
            raise Vt31SilverBulletV2BacktestReportError(
                f"trade[{index}] terminal state and r_multiple disagree"
            )
        if outcome == "breakeven" and r_multiple != Decimal(0):
            raise Vt31SilverBulletV2BacktestReportError(
                f"trade[{index}] breakeven must have zero R"
            )
        rows.append(_TradeRow(side=side, outcome=outcome, r_multiple=r_multiple))
    return tuple(rows)


def _validated_side_counts(value: dict[str, int]) -> dict[str, int]:
    if set(value) != _SIDE_SET:
        raise Vt31SilverBulletV2BacktestReportError(
            "side_counts must contain exactly canonical LONG/SHORT"
        )
    result: dict[str, int] = {}
    for side in _SIDES:
        count = value[side]
        if type(count) is not int or count < 0:
            raise Vt31SilverBulletV2BacktestReportError(
                f"side_counts[{side}] must be a non-negative int"
            )
        result[side] = count
    return result


def _summary(
    rows: tuple[_TradeRow, ...],
    *,
    side: str,
    setup_count: int,
) -> Vt31SilverBulletV2DirectionalSummary:
    selected = tuple(row for row in rows if row.side == side)
    if len(selected) > setup_count:
        raise Vt31SilverBulletV2BacktestReportError(
            f"filled {side} trades cannot exceed {side} setups"
        )
    terminal = tuple(row for row in selected if row.r_multiple is not None)
    values = tuple(cast(Decimal, row.r_multiple) for row in terminal)
    target_count = sum(row.outcome == "target" for row in terminal)
    stop_count = sum(row.outcome == "stop" for row in terminal)
    breakeven_count = sum(row.outcome == "breakeven" for row in terminal)
    win_rate = (
        Decimal(target_count) / Decimal(len(terminal)) if terminal else Decimal(0)
    )
    expectancy = (
        sum(values, Decimal(0)) / Decimal(len(values)) if values else Decimal(0)
    )
    variance = (
        sum(((value - expectancy) ** 2 for value in values), Decimal(0))
        / Decimal(len(values))
        if values
        else Decimal(0)
    )
    return Vt31SilverBulletV2DirectionalSummary(
        side=side,
        setup_count=setup_count,
        filled_count=len(selected),
        terminal_sample_size=len(terminal),
        target_count=target_count,
        stop_count=stop_count,
        breakeven_count=breakeven_count,
        gap_censored_count=sum(row.outcome == "gap_censored" for row in selected),
        data_end_censored_count=sum(
            row.outcome == "data_end_censored" for row in selected
        ),
        win_rate=win_rate,
        expectancy_r=expectancy,
        population_variance_r=variance,
    )


def _setup_side_counts(path: Path) -> dict[str, int]:
    """Recover SETUP direction from the canonical decision loop and exact M1 evidence."""

    series, _account, _evidence, _checked_at, _software_sha = _load(path)
    day_groups: dict[date, list[OhlcSnapshot]] = {}
    for bar in series:
        day_groups.setdefault(_ny_date(bar.opened_at), []).append(bar)

    counts = {side: 0 for side in _SIDES}
    for local_day in sorted(day_groups):
        bars = tuple(day_groups[local_day])
        reference = tuple(
            item
            for item in bars
            if (9, 0, 0) <= _ny_wall(item.opened_at) < (10, 0, 0)
        )
        session = tuple(
            item
            for item in bars
            if (10, 0, 0) <= _ny_wall(item.opened_at) < (11, 0, 0)
        )
        if len(reference) != 60 or not _contiguous(reference) or not session:
            continue
        if _ny_wall(session[0].opened_at) != (10, 0, 0):
            continue

        prefix: list[OhlcSnapshot] = list(reference)
        previous_session_bar: OhlcSnapshot | None = None
        for bar in session:
            if previous_session_bar is not None and not _expected_next(
                previous_session_bar, bar
            ):
                break
            prefix.append(bar)
            evaluated = evaluate_vt31_silver_bullet_v2(
                Vt31SilverBulletV2Input(
                    instrument=Instrument(_SYMBOL),
                    as_of=bar.closed_at,
                    m1_candles=tuple(prefix),
                )
            )
            if evaluated.decision is DemoTradingDecision.SETUP:
                if evaluated.setup is None:
                    raise Vt31SilverBulletV2BacktestReportError(
                        "SETUP decision is missing VT-31 V2 setup geometry"
                    )
                side = evaluated.setup.side.value
                if side not in _SIDE_SET:
                    raise Vt31SilverBulletV2BacktestReportError(
                        "VT-31 V2 setup side is not canonical LONG/SHORT"
                    )
                counts[side] += 1
                break
            previous_session_bar = bar
    return counts


def enrich_vt31_silver_bullet_v2_backtest_payload(
    payload: dict[str, object],
    *,
    setup_side_counts: dict[str, int],
) -> dict[str, object]:
    """Attach Core-style SETUP and filled-trade LONG/SHORT characterization."""

    if _text(payload.get("schema"), field_name="schema") != _SCHEMA:
        raise Vt31SilverBulletV2BacktestReportError("unexpected VT-31 V2 backtest schema")
    if _text(payload.get("symbol"), field_name="symbol") != _SYMBOL:
        raise Vt31SilverBulletV2BacktestReportError("directional report is NAS100-only")

    setup_count = _strict_int(payload.get("setup_count"), field_name="setup_count")
    filled_count = _strict_int(payload.get("filled_count"), field_name="filled_count")
    side_counts = _validated_side_counts(setup_side_counts)
    if sum(side_counts.values()) != setup_count:
        raise Vt31SilverBulletV2BacktestReportError(
            "LONG + SHORT setup counts must reconcile to setup_count"
        )

    rows = _trade_rows(payload)
    if len(rows) != filled_count:
        raise Vt31SilverBulletV2BacktestReportError(
            "filled_count must equal the number of retained trade rows"
        )

    summaries = {
        side: _summary(rows, side=side, setup_count=side_counts[side])
        for side in _SIDES
    }
    if sum(item.filled_count for item in summaries.values()) != filled_count:
        raise Vt31SilverBulletV2BacktestReportError(
            "LONG + SHORT filled counts must reconcile to filled_count"
        )

    enriched = dict(payload)
    enriched["side_counts"] = dict(side_counts)
    enriched["by_side"] = {side: summaries[side].payload() for side in _SIDES}
    enriched["long_setup_count"] = side_counts["long"]
    enriched["short_setup_count"] = side_counts["short"]
    enriched["long_trade_count"] = summaries["long"].filled_count
    enriched["short_trade_count"] = summaries["short"].filled_count
    return enriched


def run_vt31_silver_bullet_v2_backtest_report(path: Path) -> dict[str, object]:
    """Run canonical backtest and attach Core-style directional characterization."""

    report = run_vt31_silver_bullet_v2_backtest(path).payload()
    side_counts = _setup_side_counts(path)
    return enrich_vt31_silver_bullet_v2_backtest_payload(
        report,
        setup_side_counts=side_counts,
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print(
            "usage: python -m qore.infrastructure.trader_lab."
            "vt31_silver_bullet_v2_backtest_report PATH",
            file=sys.stderr,
        )
        return 2
    payload = run_vt31_silver_bullet_v2_backtest_report(Path(arguments[0]))
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
