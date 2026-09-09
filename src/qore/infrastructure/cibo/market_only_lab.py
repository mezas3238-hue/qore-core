"""Chronological Trader-blind CIBO Market-Only research lab.

Only read-only market evidence is accepted. A Market State is frozen from bars
closed at or before its information cutoff. Future bars are inspected only
after that freeze to evaluate the reading. This module imports no Trader,
backtest, capability, selection, or execution component.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.cibo.market_only_lab.v1"
_STATE_SCHEMA = "qore.cibo.market_state.v1"
_WARMUP = 160
_HORIZON = 4
_STRIDE = 4
_ZERO = Decimal(0)
_ONE = Decimal(1)


class CiboMarketOnlyLabError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class _Market:
    symbol: str
    account_fingerprint: str
    software_sha: str
    evidence_digest: str
    checked_at: datetime
    m15: tuple[_Bar, ...]
    h4: tuple[_Bar, ...]


def _object(value: object, *, field: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise CiboMarketOnlyLabError(f"{field} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field: str) -> list[object]:
    if type(value) is not list:
        raise CiboMarketOnlyLabError(f"{field} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if type(value) is not str or not value:
        raise CiboMarketOnlyLabError(f"{field} must be non-empty text")
    return value


def _timestamp(value: object, *, field: str) -> datetime:
    raw = _text(value, field=field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise CiboMarketOnlyLabError(f"{field} must be ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CiboMarketOnlyLabError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, field: str) -> Decimal:
    raw = _text(value, field=field)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise CiboMarketOnlyLabError(f"{field} must be decimal text") from error
    if not parsed.is_finite() or parsed <= 0:
        raise CiboMarketOnlyLabError(f"{field} must be positive finite")
    return parsed


def _bar(value: object, *, period: str) -> _Bar:
    row = _object(value, field=f"{period} bar")
    opened = _timestamp(row.get("opened_at"), field="opened_at")
    closed = _timestamp(row.get("closed_at"), field="closed_at")
    if closed <= opened:
        raise CiboMarketOnlyLabError("bar close must follow bar open")
    open_value = _decimal(row.get("open"), field="open")
    high = _decimal(row.get("high"), field="high")
    low = _decimal(row.get("low"), field="low")
    close = _decimal(row.get("close"), field="close")
    if high < max(open_value, low, close):
        raise CiboMarketOnlyLabError("bar high violates OHLC geometry")
    if low > min(open_value, high, close):
        raise CiboMarketOnlyLabError("bar low violates OHLC geometry")
    return _Bar(opened, closed, open_value, high, low, close)


def _load(path: Path) -> _Market:
    try:
        raw = path.read_bytes()
        decoded: object = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CiboMarketOnlyLabError(f"cannot read market evidence: {path}") from error
    payload = _object(decoded, field="market evidence")
    if payload.get("environment") != "demo":
        raise CiboMarketOnlyLabError("Market-Only evidence must be DEMO")
    if payload.get("read_only") is not True:
        raise CiboMarketOnlyLabError("Market-Only evidence must be read-only")

    account = _text(payload.get("account_fingerprint"), field="account_fingerprint")
    if re.fullmatch(r"[0-9a-f]{64}", account) is None:
        raise CiboMarketOnlyLabError("account_fingerprint must be sha256 hex")
    software_sha = _text(payload.get("software_sha"), field="software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CiboMarketOnlyLabError("software_sha must be exact commit SHA")
    symbol_row = _object(payload.get("symbol"), field="symbol")
    symbol = _text(symbol_row.get("symbol_name"), field="symbol_name")
    checked_at = _timestamp(payload.get("checked_at"), field="checked_at")
    periods = _object(payload.get("periods"), field="periods")
    m15 = tuple(_bar(item, period="M15") for item in _array(periods.get("M15"), field="M15"))
    h4 = tuple(_bar(item, period="H4") for item in _array(periods.get("H4"), field="H4"))
    if len(m15) <= _WARMUP + _HORIZON or len(h4) < 16:
        raise CiboMarketOnlyLabError("insufficient Market-Only history")
    if tuple(sorted(m15, key=lambda item: item.opened_at)) != m15:
        raise CiboMarketOnlyLabError("M15 bars must be chronological")
    if tuple(sorted(h4, key=lambda item: item.opened_at)) != h4:
        raise CiboMarketOnlyLabError("H4 bars must be chronological")
    if any(item.closed_at > checked_at for item in (*m15, *h4)):
        raise CiboMarketOnlyLabError("market evidence contains future bars")
    return _Market(
        symbol=symbol,
        account_fingerprint=account,
        software_sha=software_sha,
        evidence_digest=sha256(raw).hexdigest(),
        checked_at=checked_at,
        m15=m15,
        h4=h4,
    )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, _ZERO) / Decimal(len(values))


def _fraction(numerator: Decimal, denominator: Decimal) -> Decimal:
    return _ZERO if denominator == 0 else numerator / denominator


def _true_range(previous_close: Decimal, bar: _Bar) -> Decimal:
    return max(
        bar.high - bar.low,
        abs(bar.high - previous_close),
        abs(bar.low - previous_close),
    )


def _atr_fraction(bars: tuple[_Bar, ...], end: int, length: int) -> Decimal:
    start = max(1, end - length + 1)
    values = tuple(
        _true_range(bars[index - 1].close, bars[index]) / bars[index].close
        for index in range(start, end + 1)
    )
    return _mean(values) if values else _ZERO


def _direction(bars: tuple[_Bar, ...], end: int, short: int, long: int) -> str:
    if end + 1 < long:
        return "unknown"
    short_mean = _mean(tuple(item.close for item in bars[end - short + 1 : end + 1]))
    long_mean = _mean(tuple(item.close for item in bars[end - long + 1 : end + 1]))
    tolerance = (
        _atr_fraction(bars, end, min(20, long))
        * bars[end].close
        * Decimal("0.20")
    )
    difference = short_mean - long_mean
    if difference > tolerance:
        return "up"
    if difference < -tolerance:
        return "down"
    return "neutral"


def _h4_index_at(bars: tuple[_Bar, ...], cutoff: datetime) -> int | None:
    result: int | None = None
    for index, bar in enumerate(bars):
        if bar.closed_at > cutoff:
            break
        result = index
    return result


def _percentile(value: Decimal, population: tuple[Decimal, ...]) -> Decimal:
    if not population:
        return Decimal("0.5")
    count = sum(item <= value for item in population)
    return Decimal(count) / Decimal(len(population))


def _session(cutoff: datetime) -> str:
    if cutoff.hour < 7:
        return "asia"
    if cutoff.hour < 13:
        return "london"
    if cutoff.hour < 21:
        return "new-york"
    return "off-peak"


def _breakout(current: _Bar, previous: tuple[_Bar, ...]) -> str:
    if current.close > max(item.high for item in previous):
        return "up"
    if current.close < min(item.low for item in previous):
        return "down"
    return "none"


def _state(market: _Market, index: int) -> dict[str, object]:
    bars = market.m15
    current = bars[index]
    cutoff = current.closed_at
    direction = _direction(bars, index, 12, 48)
    previous_direction = _direction(bars, index - 16, 12, 48)
    h4_index = _h4_index_at(market.h4, cutoff)
    h4_direction = (
        "unknown"
        if h4_index is None
        else _direction(market.h4, h4_index, 4, 12)
    )

    atr = _atr_fraction(bars, index, 16)
    history = tuple(
        _atr_fraction(bars, cursor, 16)
        for cursor in range(max(32, index - 160), index + 1)
    )
    percentile = _percentile(atr, history)
    if percentile >= Decimal("0.70"):
        volatility = "high"
    elif percentile <= Decimal("0.30"):
        volatility = "low"
    else:
        volatility = "normal"

    breakout = _breakout(current, bars[index - 24 : index])
    range_fraction = _fraction(
        max(item.high for item in bars[index - 24 : index + 1])
        - min(item.low for item in bars[index - 24 : index + 1]),
        current.close,
    )
    momentum = _fraction(
        current.close - bars[index - 8].close,
        bars[index - 8].close,
    )
    prior_momentum = _fraction(
        bars[index - 8].close - bars[index - 16].close,
        bars[index - 16].close,
    )
    contradictions: list[str] = []
    if (
        direction in {"up", "down"}
        and h4_direction in {"up", "down"}
        and direction != h4_direction
    ):
        contradictions.append("m15-h4-direction-conflict")
    if (
        breakout in {"up", "down"}
        and direction in {"up", "down"}
        and breakout != direction
    ):
        contradictions.append("breakout-trend-conflict")

    if contradictions:
        regime = "unknown"
    elif direction == h4_direction == "up":
        regime = "trend-up"
    elif direction == h4_direction == "down":
        regime = "trend-down"
    elif direction == "neutral" and abs(momentum) <= max(
        atr, Decimal("0.00000001")
    ):
        regime = "range"
    else:
        regime = "uncertain"

    uncertainty = Decimal("0.15")
    if regime in {"unknown", "uncertain"}:
        uncertainty += Decimal("0.35")
    uncertainty += min(
        Decimal("0.30"),
        Decimal(len(contradictions)) * Decimal("0.15"),
    )
    if h4_direction == "unknown":
        uncertainty += Decimal("0.20")
    uncertainty = min(_ONE, uncertainty)

    h4_closed_at = None
    if h4_index is not None:
        h4_closed_at = market.h4[h4_index].closed_at.isoformat(
            timespec="microseconds"
        )
    base: dict[str, object] = {
        "schema": _STATE_SCHEMA,
        "instrument": market.symbol,
        "information_cutoff": cutoff.isoformat(timespec="microseconds"),
        "session": _session(cutoff),
        "timeframe": "M15",
        "direction": direction,
        "structure": direction,
        "trend": direction,
        "persistence": (
            direction == previous_direction and direction in {"up", "down"}
        ),
        "range_fraction": format(range_fraction, "f"),
        "volatility": volatility,
        "volatility_percentile": format(percentile, "f"),
        "expansion": volatility == "high",
        "compression": volatility == "low",
        "momentum_fraction": format(momentum, "f"),
        "acceleration_fraction": format(momentum - prior_momentum, "f"),
        "breakout": breakout,
        "reversion": direction == "neutral" and breakout == "none",
        "pullback": (
            (direction == "up" and momentum < 0)
            or (direction == "down" and momentum > 0)
        ),
        "transition": previous_direction not in {"unknown", direction},
        "spread_cost": "unknown",
        "multi_timeframe": {"M15": direction, "H4": h4_direction},
        "regime_hypothesis": regime,
        "uncertainty": format(uncertainty, "f"),
        "contradictions": tuple(sorted(contradictions)),
        "unsupported_dimensions": (
            "news-event-causality",
            "order-book-liquidity",
            "provider-spread-cost-history",
        ),
        "provenance": {
            "market_evidence_sha256": market.evidence_digest,
            "market_software_sha": market.software_sha,
            "account_fingerprint": market.account_fingerprint,
            "m15_last_closed_at": cutoff.isoformat(timespec="microseconds"),
            "h4_last_closed_at": h4_closed_at,
        },
    }
    canonical = json.dumps(
        base,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    base["market_state_fingerprint"] = sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    return base


def _evaluate(
    market: _Market,
    index: int,
    state: dict[str, object],
) -> tuple[str, str]:
    current = market.m15[index]
    future = market.m15[index + _HORIZON]
    move = _fraction(future.close - current.close, current.close)
    threshold = max(
        _atr_fraction(market.m15, index, 16) * Decimal("0.50"),
        Decimal("0.00000001"),
    )
    if move > threshold:
        realized = "up"
    elif move < -threshold:
        realized = "down"
    else:
        realized = "neutral"
    regime = _text(state.get("regime_hypothesis"), field="regime_hypothesis")
    expected = {
        "trend-up": "up",
        "trend-down": "down",
        "range": "neutral",
    }.get(regime)
    if expected is None:
        return realized, "unscored-uncertain"
    return realized, "correct" if realized == expected else "incorrect"


def _run_market(market: _Market) -> dict[str, object]:
    records: list[dict[str, object]] = []
    scored = 0
    correct = 0
    false_certainty = 0
    uncertain = 0
    transitions = 0
    stop = len(market.m15) - _HORIZON
    for index in range(_WARMUP, stop, _STRIDE):
        state = _state(market, index)
        realized, correctness = _evaluate(market, index, state)
        regime = _text(state.get("regime_hypothesis"), field="regime_hypothesis")
        uncertainty = Decimal(_text(state.get("uncertainty"), field="uncertainty"))
        if regime in {"unknown", "uncertain"}:
            uncertain += 1
        if state.get("transition") is True:
            transitions += 1
        if correctness in {"correct", "incorrect"}:
            scored += 1
            if correctness == "correct":
                correct += 1
            elif uncertainty <= Decimal("0.25"):
                false_certainty += 1
        records.append(
            {
                "frozen_market_state": state,
                "post_freeze_evaluation": {
                    "horizon_m15_bars": _HORIZON,
                    "realized_direction": realized,
                    "regime_correctness": correctness,
                    "oracle_visible_to_state": False,
                },
            }
        )
    if not records:
        raise CiboMarketOnlyLabError("no Market-Only records produced")
    return {
        "symbol": market.symbol,
        "evidence_digest": market.evidence_digest,
        "record_count": len(records),
        "scored_regime_count": scored,
        "correct_regime_count": correct,
        "regime_accuracy": (
            None if scored == 0 else format(Decimal(correct) / Decimal(scored), "f")
        ),
        "unknown_or_uncertain_count": uncertain,
        "unknown_or_uncertain_rate": format(
            Decimal(uncertain) / Decimal(len(records)), "f"
        ),
        "false_certainty_count": false_certainty,
        "transition_count": transitions,
        "records": records,
    }


def _result_int(result: dict[str, object], field: str) -> int:
    value = result.get(field)
    if type(value) is not int:
        raise CiboMarketOnlyLabError(f"{field} must be exact int")
    return value


def run_market_only_lab(paths: tuple[Path, ...]) -> dict[str, object]:
    """Run a deterministic Trader-blind chronological study over exact markets."""
    if not paths:
        raise CiboMarketOnlyLabError("at least one market path is required")
    markets = tuple(_load(path) for path in paths)
    symbols = tuple(item.symbol for item in markets)
    if len(set(symbols)) != len(symbols):
        raise CiboMarketOnlyLabError("market symbols must be unique")
    accounts = {item.account_fingerprint for item in markets}
    if len(accounts) != 1:
        raise CiboMarketOnlyLabError(
            "Market-Only comparison requires one exact DEMO account"
        )
    results = tuple(_run_market(market) for market in markets)
    scored = sum(_result_int(item, "scored_regime_count") for item in results)
    correct = sum(_result_int(item, "correct_regime_count") for item in results)
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "trader_outputs_consumed": False,
        "trader_history_consumed": False,
        "oracle_visible_at_decision_time": False,
        "market_count": len(markets),
        "symbols": symbols,
        "account_fingerprint": markets[0].account_fingerprint,
        "market_state_policy": "past-only-m15+h4-deterministic-v1",
        "evaluation_policy": "freeze-state-then-advance-4-m15-bars-v1",
        "unknown_is_neutral": False,
        "insufficient_evidence_is_confidence": False,
        "aggregate_scored_regime_count": scored,
        "aggregate_regime_accuracy": (
            None if scored == 0 else format(Decimal(correct) / Decimal(scored), "f")
        ),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "usage: python -m qore.infrastructure.cibo.market_only_lab "
            "MARKET_EVIDENCE [MARKET_EVIDENCE ...]",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_market_only_lab(tuple(Path(item) for item in args))
    except CiboMarketOnlyLabError as error:
        print(f"CIBO Market-Only Lab blocked: {error}", file=sys.stderr)
        return 1
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
