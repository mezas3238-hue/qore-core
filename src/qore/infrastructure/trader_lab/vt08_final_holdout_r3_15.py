"""Frozen R3.15 independent-holdout adjudication for VT-08 B COMBINED."""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from typing import cast

from qore.infrastructure.traders.vt08_b01_r3_8 import (
    AUTHORIZED_FOREX_MARKETS,
    methodology_fingerprint,
)
from qore.kernel.errors import InfrastructureError

HOLDOUT_ID = "VT08_R3_15_FINAL_INDEPENDENT_2020_2022"
OPENED_AT = datetime(2020, 7, 1, tzinfo=UTC)
CLOSED_AT = datetime(2022, 7, 1, tzinfo=UTC)
PORTFOLIO = {
    ("AUDJPY", "short"),
    ("GBPUSD", "short"),
    ("GBPJPY", "long"),
    ("GBPJPY", "short"),
}
MIN_SAMPLE = 30
MAX_VARIANCE = Decimal("0.01")


class Vt08R315Error(InfrastructureError):
    __slots__ = ()


def _obj(v: object, name: str) -> dict[str, object]:
    if type(v) is not dict:
        raise Vt08R315Error(f"{name} must be object")
    return cast(dict[str, object], v)


def _text(v: object, name: str) -> str:
    if type(v) is not str or not v:
        raise Vt08R315Error(f"{name} must be text")
    return v


def _dec(v: object, name: str) -> Decimal:
    try:
        value = Decimal(_text(v, name))
    except InvalidOperation as exc:
        raise Vt08R315Error(f"{name} must be decimal") from exc
    if not value.is_finite():
        raise Vt08R315Error(f"{name} must be finite")
    return value


def _ts(v: object, name: str) -> datetime:
    value = datetime.fromisoformat(_text(v, name))
    if value.tzinfo is None or value.utcoffset() is None:
        raise Vt08R315Error(f"{name} must be aware")
    return value.astimezone(UTC)


def compile_holdout(paths: tuple[Path, ...]) -> dict[str, object]:
    if len(paths) != 7:
        raise Vt08R315Error("exactly seven backtests required")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    software_shas: set[str] = set()
    for path in paths:
        payload = _obj(json.loads(path.read_text()), "backtest")
        if _text(payload.get("schema"), "schema") != "qore.trader_lab.vt08_b01_backtest.r3.8.v1":
            raise Vt08R315Error("unexpected backtest schema")
        if _text(payload.get("trader_code"), "trader_code") != "vt-08":
            raise Vt08R315Error("wrong Trader")
        if _text(payload.get("methodology_fingerprint"), "methodology_fingerprint") != methodology_fingerprint():
            raise Vt08R315Error("methodology drift")
        symbol = _text(payload.get("symbol"), "symbol")
        seen.add(symbol)
        software_shas.add(_text(payload.get("software_sha"), "software_sha"))
        raw_trades = payload.get("trades")
        if type(raw_trades) is not list:
            raise Vt08R315Error("trades must be array")
        for raw in raw_trades:
            trade = _obj(raw, "trade")
            signal = _ts(trade.get("signal_at"), "signal_at")
            side = _text(trade.get("side"), "side")
            if OPENED_AT <= signal < CLOSED_AT and (symbol, side) in PORTFOLIO:
                row = dict(trade)
                row["symbol"] = symbol
                rows.append(row)
    if seen != set(AUTHORIZED_FOREX_MARKETS):
        raise Vt08R315Error("frozen seven-market set mismatch")
    if len(software_shas) != 1:
        raise Vt08R315Error("mixed software SHA")
    rows.sort(key=lambda row: _ts(row["signal_at"], "signal_at"))
    values = tuple(_dec(row.get("return_rate"), "return_rate") for row in rows)
    n = len(values)
    mean = sum(values, Decimal(0)) / Decimal(n) if n else Decimal(0)
    variance = (
        sum(((v - mean) ** 2 for v in values), Decimal(0)) / Decimal(n)
        if n else Decimal(0)
    )
    wins = sum(v > 0 for v in values)
    losses = sum(v < 0 for v in values)
    gross_profit = sum((v for v in values if v > 0), Decimal(0))
    gross_loss = abs(sum((v for v in values if v < 0), Decimal(0)))
    equity = Decimal(1)
    peak = equity
    max_dd = Decimal(0)
    losing = 0
    max_losing = 0
    for value in values:
        equity *= Decimal(1) + value
        peak = max(peak, equity)
        if peak:
            max_dd = max(max_dd, (peak - equity) / peak)
        if value <= 0:
            losing += 1
            max_losing = max(max_losing, losing)
        else:
            losing = 0
    risk_pass = n >= MIN_SAMPLE and variance <= MAX_VARIANCE
    return {
        "schema": "qore.vt08.r3.15.final-independent-holdout.v1",
        "holdout_id": HOLDOUT_ID,
        "independent_validation": True,
        "methodology_mutation_after_holdout": False,
        "opened_at": OPENED_AT.isoformat(),
        "closed_at": CLOSED_AT.isoformat(),
        "software_sha": next(iter(software_shas)),
        "methodology_fingerprint": methodology_fingerprint(),
        "portfolio": "B_COMBINED",
        "sample_size": n,
        "wins": wins,
        "losses": losses,
        "flats": n - wins - losses,
        "win_rate": format(Decimal(wins) / Decimal(n) if n else Decimal(0), "f"),
        "mean_return": format(mean, "f"),
        "population_variance": format(variance, "f"),
        "profit_factor": None if gross_loss == 0 else format(gross_profit / gross_loss, "f"),
        "compounded_return": format(equity - Decimal(1), "f"),
        "maximum_drawdown": format(max_dd, "f"),
        "max_losing_streak": max_losing,
        "median_return": format(Decimal(str(median(values))) if values else Decimal(0), "f"),
        "risk_policy": {
            "policy_id": "vt08-r315-final-demo-v1",
            "min_sample_size": MIN_SAMPLE,
            "max_population_variance": format(MAX_VARIANCE, "f"),
            "approved": risk_pass,
        },
        "returns": [format(v, "f") for v in values],
        "trades": rows,
        "live_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 8 or args[0] != "aggregate":
        print("usage: ... aggregate <seven backtests>", file=sys.stderr)
        return 2
    try:
        report = compile_holdout(tuple(Path(p) for p in args[1:]))
    except (OSError, json.JSONDecodeError, Vt08R315Error) as error:
        print(f"VT-08 R3.15 failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
