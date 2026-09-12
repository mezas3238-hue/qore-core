"""Fresh-holdout projection for the frozen VT-08 executable B01 subset."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_demo_lab_historical_holdout_probe import (
    CONSUMED_BASELINE_BOUNDARY,
    EVALUATION_CLOSED_AT,
    EVALUATION_OPENED_AT,
    HOLDOUT_ID,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import AUTHORIZED_FOREX_MARKETS
from qore.infrastructure.traders.vt08_b01_source_contract_r3_9 import (
    CONTRACT_VERSION,
    source_contract_fingerprint,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_b01_fresh_holdout.r3.10.v1"
_PARENT_SCHEMA = "qore.trader_lab.vt08_b01_backtest.r3.8.v1"
_NY = ZoneInfo("America/New_York")


class Vt08B01FreshHoldoutError(InfrastructureError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01FreshHoldoutError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01FreshHoldoutError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08B01FreshHoldoutError(f"{name} must be non-empty text")
    return value


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08B01FreshHoldoutError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08B01FreshHoldoutError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _return(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08B01FreshHoldoutError(f"{name} must be Decimal text") from error
    if not parsed.is_finite():
        raise Vt08B01FreshHoldoutError(f"{name} must be finite")
    return parsed


def _metrics(trades: list[dict[str, object]]) -> dict[str, object]:
    values = [_return(item.get("return_rate"), name="return_rate") for item in trades]
    sample = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = sample - wins - losses
    mean = sum(values, Decimal(0)) / Decimal(sample) if sample else Decimal(0)
    win_rate = Decimal(wins) / Decimal(sample) if sample else Decimal(0)
    exit_reasons: Counter[str] = Counter()
    sides: Counter[str] = Counter()
    anchors: Counter[str] = Counter()
    anchor_wins: Counter[str] = Counter()
    side_wins: Counter[str] = Counter()
    for item, value in zip(trades, values, strict=True):
        exit_reasons[_text(item.get("exit_reason"), name="exit_reason")] += 1
        side = _text(item.get("side"), name="side")
        sides[side] += 1
        if value > 0:
            side_wins[side] += 1
        signal = _timestamp(item.get("signal_at"), name="signal_at")
        anchor = f"{signal.astimezone(_NY).hour:02d}:00"
        anchors[anchor] += 1
        if value > 0:
            anchor_wins[anchor] += 1
    return {
        "sample_size": sample,
        "winning_trades": wins,
        "losing_trades": losses,
        "flat_trades": flats,
        "win_rate": format(win_rate, "f"),
        "mean_return": format(mean, "f"),
        "exit_reason_counts": dict(sorted(exit_reasons.items())),
        "side_counts": dict(sorted(sides.items())),
        "side_wins": dict(sorted(side_wins.items())),
        "anchor_counts": dict(sorted(anchors.items())),
        "anchor_wins": dict(sorted(anchor_wins.items())),
    }


def _load_parent(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08B01FreshHoldoutError(f"cannot read {path}") from error
    payload = _object(decoded, name="R3.8 backtest")
    if _text(payload.get("schema"), name="schema") != _PARENT_SCHEMA:
        raise Vt08B01FreshHoldoutError("unexpected parent backtest schema")
    if _text(payload.get("trader_code"), name="trader_code") != "vt-08":
        raise Vt08B01FreshHoldoutError("backtest does not belong to VT-08")
    return payload


def compile_market_holdout(path: Path) -> dict[str, object]:
    payload = _load_parent(path)
    symbol = _text(payload.get("symbol"), name="symbol")
    if symbol not in AUTHORIZED_FOREX_MARKETS:
        raise Vt08B01FreshHoldoutError("unexpected holdout market")
    raw_trades = _array(payload.get("trades"), name="trades")
    retained: list[dict[str, object]] = []
    for raw in raw_trades:
        trade = _object(raw, name="trade")
        signal = _timestamp(trade.get("signal_at"), name="signal_at")
        if EVALUATION_OPENED_AT <= signal < EVALUATION_CLOSED_AT:
            retained.append(trade)
    result = {
        "schema": _SCHEMA,
        "holdout_id": HOLDOUT_ID,
        "trader_code": "vt-08",
        "symbol": symbol,
        "research_only": True,
        "independent_holdout": True,
        "source_contract_version": CONTRACT_VERSION,
        "source_contract_fingerprint": source_contract_fingerprint(),
        "parent_executable_schema": _PARENT_SCHEMA,
        "parent_methodology_fingerprint": _text(
            payload.get("methodology_fingerprint"), name="methodology_fingerprint"
        ),
        "software_sha": _text(payload.get("software_sha"), name="software_sha"),
        "evaluation_opened_at": EVALUATION_OPENED_AT.isoformat(),
        "evaluation_closed_at": EVALUATION_CLOSED_AT.isoformat(),
        "consumed_baseline_boundary": CONSUMED_BASELINE_BOUNDARY.isoformat(),
        "no_consumed_baseline_overlap": True,
        "executable_scope": "narrow-completed-c2-b01",
        "c3_included": False,
        "c3_status": "source-authorized-but-outside-frozen-machine-executable-subset",
        "methodology_mutation_from_holdout": False,
        "raw_acquisition_sample_size": payload.get("sample_size"),
        "metrics": _metrics(retained),
        "trades": retained,
    }
    return result


def compile_aggregate(paths: tuple[Path, ...]) -> dict[str, object]:
    if len(paths) != len(AUTHORIZED_FOREX_MARKETS):
        raise Vt08B01FreshHoldoutError("aggregate requires exactly seven market reports")
    reports = [compile_market_holdout(path) for path in paths]
    by_symbol = {
        _text(item.get("symbol"), name="symbol"): item
        for item in reports
    }
    if set(by_symbol) != set(AUTHORIZED_FOREX_MARKETS):
        raise Vt08B01FreshHoldoutError("aggregate must contain the frozen seven markets")
    software_shas = {
        _text(item.get("software_sha"), name="software_sha") for item in reports
    }
    if len(software_shas) != 1:
        raise Vt08B01FreshHoldoutError("all holdout markets must use one software SHA")

    all_trades: list[dict[str, object]] = []
    for symbol in sorted(by_symbol):
        all_trades.extend(
            _object(item, name="trade")
            for item in _array(by_symbol[symbol].get("trades"), name="trades")
        )
    per_market = {
        symbol: _object(report.get("metrics"), name="metrics")
        for symbol, report in sorted(by_symbol.items())
    }
    return {
        "schema": "qore.trader_lab.vt08_b01_fresh_holdout_aggregate.r3.10.v1",
        "holdout_id": HOLDOUT_ID,
        "trader_code": "vt-08",
        "research_only": True,
        "independent_holdout": True,
        "source_contract_version": CONTRACT_VERSION,
        "source_contract_fingerprint": source_contract_fingerprint(),
        "software_sha": next(iter(software_shas)),
        "evaluation_opened_at": EVALUATION_OPENED_AT.isoformat(),
        "evaluation_closed_at": EVALUATION_CLOSED_AT.isoformat(),
        "consumed_baseline_boundary": CONSUMED_BASELINE_BOUNDARY.isoformat(),
        "no_consumed_baseline_overlap": True,
        "market_count": len(reports),
        "symbols": sorted(by_symbol),
        "executable_scope": "narrow-completed-c2-b01",
        "c3_included": False,
        "methodology_mutation_from_holdout": False,
        "metrics": _metrics(all_trades),
        "per_market": per_market,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2 or args[0] not in {"market", "aggregate"}:
        print(
            "usage: vt08_b01_fresh_holdout_r3_10 market <backtest.json> | "
            "aggregate <seven backtest.json paths>",
            file=sys.stderr,
        )
        return 2
    try:
        if args[0] == "market":
            if len(args) != 2:
                raise Vt08B01FreshHoldoutError("market mode requires one backtest")
            payload = compile_market_holdout(Path(args[1]))
        else:
            if len(args) != 8:
                raise Vt08B01FreshHoldoutError("aggregate mode requires seven backtests")
            payload = compile_aggregate(tuple(Path(item) for item in args[1:]))
    except Vt08B01FreshHoldoutError as error:
        print(f"VT-08 fresh holdout failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
