"""Directional reporting wrapper for the VT-31 Silver Bullet V2 backtest.

The source-bound backtest is the behavioral source of truth.  This module does
not change setup selection, fill modeling, exits, or methodology.  It enriches
the canonical NAS100 backtest payload with deterministic LONG/SHORT reporting
so Trader Lab and Story Forensics do not have to reconstruct direction counts
from individual trade rows.

Research only.  No DEMO/LIVE/Risk/execution authority is created here.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    Vt31SilverBulletV2BacktestError,
    run_vt31_silver_bullet_v2_backtest,
)

_SCHEMA = "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1"
_SYMBOL = "NAS100"
_SIDES = frozenset({"long", "short"})
_OUTCOMES = frozenset({"target", "stop", "gap_censored", "data_end_censored"})
_TERMINAL_OUTCOMES = frozenset({"target", "stop"})


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
    """One immutable filled-trade direction summary."""

    side: str
    trade_count: int
    terminal_sample_size: int
    target_count: int
    stop_count: int
    gap_censored_count: int
    data_end_censored_count: int
    win_rate: Decimal
    expectancy_r: Decimal
    population_variance_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "trade_count": self.trade_count,
            "terminal_sample_size": self.terminal_sample_size,
            "target_count": self.target_count,
            "stop_count": self.stop_count,
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
        if side not in _SIDES:
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
        rows.append(_TradeRow(side=side, outcome=outcome, r_multiple=r_multiple))
    return tuple(rows)


def _summary(rows: tuple[_TradeRow, ...], *, side: str) -> Vt31SilverBulletV2DirectionalSummary:
    selected = tuple(row for row in rows if row.side == side)
    terminal = tuple(row for row in selected if row.r_multiple is not None)
    values = tuple(cast(Decimal, row.r_multiple) for row in terminal)
    target_count = sum(row.outcome == "target" for row in terminal)
    stop_count = sum(row.outcome == "stop" for row in terminal)
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
        trade_count=len(selected),
        terminal_sample_size=len(terminal),
        target_count=target_count,
        stop_count=stop_count,
        gap_censored_count=sum(row.outcome == "gap_censored" for row in selected),
        data_end_censored_count=sum(
            row.outcome == "data_end_censored" for row in selected
        ),
        win_rate=win_rate,
        expectancy_r=expectancy,
        population_variance_r=variance,
    )


def enrich_vt31_silver_bullet_v2_backtest_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    """Add fail-closed LONG/SHORT metrics to one canonical VT-31 V2 backtest payload."""

    if _text(payload.get("schema"), field_name="schema") != _SCHEMA:
        raise Vt31SilverBulletV2BacktestReportError("unexpected VT-31 V2 backtest schema")
    if _text(payload.get("symbol"), field_name="symbol") != _SYMBOL:
        raise Vt31SilverBulletV2BacktestReportError("directional report is NAS100-only")
    filled_count = _strict_int(payload.get("filled_count"), field_name="filled_count")
    rows = _trade_rows(payload)
    if len(rows) != filled_count:
        raise Vt31SilverBulletV2BacktestReportError(
            "filled_count must equal the number of retained trade rows"
        )

    long_summary = _summary(rows, side="long")
    short_summary = _summary(rows, side="short")
    if long_summary.trade_count + short_summary.trade_count != filled_count:
        raise Vt31SilverBulletV2BacktestReportError(
            "LONG + SHORT counts must reconcile to filled_count"
        )

    enriched = dict(payload)
    enriched["long_trade_count"] = long_summary.trade_count
    enriched["short_trade_count"] = short_summary.trade_count
    enriched["directional_breakdown"] = {
        "long": long_summary.payload(),
        "short": short_summary.payload(),
    }
    return enriched


def run_vt31_silver_bullet_v2_backtest_report(path: Path) -> dict[str, object]:
    """Run the canonical backtest and attach deterministic directional reporting."""

    return enrich_vt31_silver_bullet_v2_backtest_payload(
        run_vt31_silver_bullet_v2_backtest(path).payload()
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
