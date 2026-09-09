"""CIBO Market-Only Lab: chronological, Trader-blind market understanding research.

The lab consumes only sanitized read-only market-evidence artifacts.  At each
information cutoff it freezes a deterministic Market State from bars closed at
or before the cutoff.  Only after that fingerprint is fixed does it inspect a
later horizon for evaluation.  It imports no Trader evaluator, backtest,
walk-forward, capability-profile or selection module and creates no execution
authority.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.cibo.market_only_lab.v1"
_STATE_SCHEMA = "qore.cibo.market_state.v1"
_PRIMARY_PERIOD = "M15"
_CONTEXT_PERIOD = "H4"
_WARMUP = 160
_EVALUATION_HORIZON = 4
_SAMPLE_STRIDE = 4
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
    checked_at: datetime
    software_sha: str
    evidence_digest: str
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


def _aware(value: str, *, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CiboMarketOnlyLabError(f"{field} must be ISO timestamp") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboMarketOnlyLabError(f"{field} must be timezone-aware")
    return result.astimezone(UTC)


def _price(value: object, *, field: str) -> Decimal:
    if type(value) is not str:
        raise CiboMarketOnlyLabError(f"{field} must be decimal text")
    try:
        result = Decimal(value)
    except Exception as error:
        raise CiboMarketOnlyLabError(f"{field} must be decimal text") from error
    if not result.is_finite() or result <= 0:
        raise CiboMarketOnlyLabError(f"{field} must be positive finite")
    return result


def _bar(value: object, *, period: str) -> _Bar:
    row = _object(value, field=f"{period} bar")
    opened = _aware(_text(row.get("opened_at"), field="opened_at"), field="opened_at")
    closed = _aware(_text(row.get("closed_at"), field="closed_at"), field="closed_at")
    if closed <= opened:
        raise CiboMarketOnlyLabError("bar close must follow open")
    open_value = _price(row.get("open"), field="open")
    high = _price(row.get("high"), field="high")
    low = _price(row.get("low"), field="low")
    close = _price(row.get("close"), field="close")
    if high < max(open_value, low, close) or low > min(open_value, high, close):
        raise CiboMarketOnlyLabError("OHLC geometry invalid")
    return _Bar(opened, closed, open_value, high, low, close)


def _load(path: Path) -> _Market:
    try:
        raw = path.read_bytes()
        decoded: object = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise CiboMarketOnlyLabError(f"cannot read market evidence: {path}") from error
    payload = _object(decoded, field="market evidence")
    if payload.get("environment") != "demo" or payload.get("read_only") is not True:
        raise CiboMarketOnlyLabError("CIBO Market-Only requires read-only DEMO evidence")
    account = _text(payload.get("account_fingerprint"), field="account_fingerprint")
    if len(account) != 64:
        raise CiboMarketOnlyLabError("account_fingerprint must be sha256 hex")
    symbol_payload = _object(payload.get("symbol"), field="symbol")
    symbol = _text(symbol_payload.get("symbol_name"), field="symbol_name")
    checked_at = _aware(_text(payload.get("checked_at"), field="checked_at"), field="checked_at")
    software_sha = _text(payload.get("software_sha"), field="software_sha")
    if len(software_sha) != 40:
        raise CiboMarketOnlyLabError("software_sha must be exact commit SHA")
    periods = _object(payload.get("periods"), field="periods")
    m15_values = _array(periods.get(_PRIMARY_PERIOD), field="M15")
    h4_values = _array(periods.get(_CONTEXT_PERIOD), field="H4")
    m15 = tuple(_bar(item, period=_PRIMARY_PERIOD) for item in m15_values)
    h4 = tuple(_bar(item, period=_CONTEXT_PERIOD) for item in h4_values)
    if len(m15) <= _WARMUP + _EVALUATION_HORIZON or len(h4) < 16:
        raise CiboMarketOnlyLabError("insufficient bars for Market-Only evaluation")
    if tuple(sorted(m15, key=lambda item: item.opened_at)) != m15:
        raise CiboMarketOnlyLabError("M15 bars must be chronological")
    if tuple(sorted(h4, key=lambda item: item.opened_at)) != h4:
        raise CiboMarketOnlyLabError("H4 bars must be chronological")
    if any(bar.closed_at > checked_at for bar in (*m15, *h4)):
        raise CiboMarketOnlyLabError("market evidence contains future/unclosed bars")
    return _Market(
        symbol=symbol,
        account_fingerprint=account,
        checked_at=checked_at,
        software_sha=software_sha,
        evidence_digest=sha256(raw).hexdigest(),
        m15=m15,
        h4=h4,
    )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, _ZERO) / Decimal(len(values))


def _fraction(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return _ZERO
    return numerator / denominator


def _true_range(previous_close: Decimal, bar: _Bar) -> Decimal:
    return max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))


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
    last = bars[end].close
    tolerance = _atr_fraction(bars, end, min(20, long)) * last * Decimal("0.20")
    difference = short_mean - long_mean
    if difference > tolerance:
        return "up"
    if difference < -tolerance:
        return "down"
    return "neutral"


def _h4_index_at(bars: tuple[_Bar, ...], cutoff: datetime) -> int | None:
    candidate: int | None = None
    for index, bar in enumerate(bars):
        if bar.closed_at <= cutoff:
            candidate = index
        else:
            break
    return candidate


def _percentile(value: Decimal, population: tuple[Decimal, ...]) -> Decimal:
    if not population:
        return Decimal("0.5")
    less_or_equal = sum(item <= value for item in population)
    return Decimal(less_or_equal) / Decimal(len(population))


def _session(cutoff: datetime) -> str:
    hour = cutoff.hour
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 21:
        return "new-york"
    return "off-peak"


def _state(market: _Market, index: int) -> dict[str, object]:
    bars = market.m15
    current = bars[index]
    cutoff = current.closed_at
    direction = _direction(bars, index, 12, 48)
    earlier_direction = _direction(bars, index - 16, 12, 48)
    h4_index = _h4_index_at(market.h4, cutoff)
    h4_direction = "unknown" if h4_index is None else _direction(market.h4, h4_index, 4, 12)

    atr = _atr_fraction(bars, index, 16)
    atr_history = tuple(
        _atr_fraction(bars, cursor, 16)
        for cursor in range(max(32, index - 160), index + 1)
    )
    vol_percentile = _percentile(atr, atr_history)
    if vol_percentile >= Decimal("0.70"):
        volatility = "high"
    elif vol_percentile <= Decimal("0.30"):
        volatility = "low"
    else:
        volatility = "normal"

    prior_high = max(item.high for item in bars[index - 24 : index])
    prior_low = min(item.low for item in bars[index - 24 : index])
    breakout = "up" if current.close > prior_high else "down" if current.close < prior_low else "none"
    range_fraction = _fraction(
        max(item.high for item in bars[index - 24 : index + 1])
        - min(item.low for item in bars[index - 24 : index + 1]),
        current.close,
    )
    momentum = _fraction(current.close - bars[index - 8].close, bars[index - 8].close)
    prior_momentum = _fraction(
        bars[index - 8].close - bars[index - 16].close,
        bars[index - 16].close,
    )
    acceleration = momentum - prior_momentum
    contradictions: list[str] = []
    if direction in {"up", "down"} and h4_direction in {"up", "down"} and direction != h4_direction:
        contradictions.append("m15-h4-direction-conflict")
    if breakout in {"up", "down"} and direction in {"up", "down"} and breakout != direction:
        contradictions.append("breakout-trend-conflict")

    transition = earlier_direction not in {"unknown", direction}
    pullback = (
        (direction == "up" and momentum < 0)
        or (direction == "down" and momentum > 0)
    )
    if contradictions:
        regime = "unknown"
    elif direction == h4_direction == "up":
        regime = "trend-up"
    elif direction == h4_direction == "down":
        regime = "trend-down"
    elif direction == "neutral" and abs(momentum) <= max(atr, Decimal("0.00000001")):
        regime = "range"
    else:
        regime = "uncertain"

    uncertainty = Decimal("0.15")
    if regime in {"unknown", "uncertain"}:
        uncertainty += Decimal("0.35")
    uncertainty += min(Decimal("0.30"), Decimal(len(contradictions)) * Decimal("0.15"))
    if h4_direction == "unknown":
        uncertainty += Decimal("0.20")
    uncertainty = min(_ONE, uncertainty)

    base: dict[str, object] = {
        "schema": _STATE_SCHEMA,
        "instrument": market.symbol,
        "information_cutoff": cutoff.isoformat(timespec="microseconds"),
        "session": _session(cutoff),
        "timeframe": _PRIMARY_PERIOD,
        "direction": direction,
        "structure": direction,
        "trend": direction,
        "persistence": direction == earlier_direction and direction in {"up", "down"},
        "range_fraction": format(range_fraction, "f"),
        "volatility": volatility,
        "volatility_percentile": format(vol_percentile, "f"),
        "expansion": volatility == "high",
        "compression": volatility == "low",
        "momentum_fraction": format(momentum, "f"),
        "acceleration_fraction": format(acceleration, "f"),
        "breakout": breakout,
        "reversion": direction == "neutral" and breakout == "none",
        "pullback": pullback,
        "transition": transition,
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
            "h4_last_closed_at": (
                None if h4_index is None else market.h4[h4_index].closed_at.isoformat(timespec="microseconds")
            ),
        },
    }
    canonical = json.dumps(base, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    base["market_state_fingerprint"] = sha256(canonical.encode("utf-8")).hexdigest()
    return base


def _realized_direction(market: _Market, index: int, state: dict[str, object]) -> tuple[str, str]:
    current = market.m15[index]
    future = market.m15[index + _EVALUATION_HORIZON]
    move = _fraction(future.close - current.close, current.close)
    atr = _atr_fraction(market.m15, index, 16)
    threshold = max(atr * Decimal("0.50"), Decimal("0.00000001"))
    if move > threshold:
        direction = "up"
    elif move < -threshold:
        direction = "down"
    else:
        direction = "neutral"
    regime = _text(state["regime_hypothesis"], field="regime_hypothesis")
    if regime == "trend-up":
        correctness = "correct" if direction == "up" else "incorrect"
    elif regime == "trend-down":
        correctness = "correct" if direction == "down" else "incorrect"
    elif regime == "range":
        correctness = "correct" if direction == "neutral" else "incorrect"
    else:
        correctness = "unscored-uncertain"
    return direction, correctness


def _run_market(market: _Market) -> dict[str, object]:
    records: list[dict[str, object]] = []
    scored = 0
    correct = 0
    false_certainty = 0
    unknown_count = 0
    transitions = 0
    for index in range(_WARMUP, len(market.m15) - _EVALUATION_HORIZON, _SAMPLE_STRIDE):
        state = _state(market, index)
        # The state and its fingerprint are complete before chronology advances.
        realized_direction, correctness = _realized_direction(market, index, state)
        regime = _text(state["regime_hypothesis"], field="regime_hypothesis")
        uncertainty = Decimal(_text(state["uncertainty"], field="uncertainty"))
        if regime in {"unknown", "uncertain"}:
            unknown_count += 1
        if state["transition"] is True:
            transitions += 1
        if correctness in {"correct", "incorrect"}:
            scored += 1
            correct += correctness == "correct"
            if correctness == "incorrect" and uncertainty <= Decimal("0.25"):
                false_certainty += 1
        records.append(
            {
                "frozen_market_state": state,
                "post_freeze_evaluation": {
                    "horizon_m15_bars": _EVALUATION_HORIZON,
                    "realized_direction": realized_direction,
                    "regime_correctness": correctness,
                    "oracle_visible_to_state": False,
                },
            }
        )
    if not records:
        raise CiboMarketOnlyLabError("no Market-Only evaluation records produced")
    return {
        "symbol": market.symbol,
        "evidence_digest": market.evidence_digest,
        "record_count": len(records),
        "scored_regime_count": scored,
        "regime_accuracy": None if scored == 0 else format(Decimal(correct) / Decimal(scored), "f"),
        "unknown_or_uncertain_count": unknown_count,
        "unknown_or_uncertain_rate": format(Decimal(unknown_count) / Decimal(len(records)), "f"),
        "false_certainty_count": false_certainty,
        "transition_count": transitions,
        "records": records,
    }


def run_market_only_lab(paths: tuple[Path, ...]) -> dict[str, object]:
    if not paths:
        raise CiboMarketOnlyLabError("at least one market evidence path is required")
    markets = tuple(_load(path) for path in paths)
    symbols = tuple(item.symbol for item in markets)
    if len(set(symbols)) != len(symbols):
        raise CiboMarketOnlyLabError("market evidence symbols must be unique")
    accounts = {item.account_fingerprint for item in markets}
    if len(accounts) != 1:
        raise CiboMarketOnlyLabError("Market-Only comparison requires one exact DEMO account")
    results = tuple(_run_market(market) for market in markets)
    aggregate_scored = sum(cast(int, item["scored_regime_count"]) for item in results)
    aggregate_correct = 0
    for item in results:
        accuracy = item["regime_accuracy"]
        if type(accuracy) is str:
            aggregate_correct += int(
                (Decimal(accuracy) * Decimal(cast(int, item["scored_regime_count"]))).to_integral_value()
            )
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
        "aggregate_scored_regime_count": aggregate_scored,
        "aggregate_regime_accuracy": (
            None
            if aggregate_scored == 0
            else format(Decimal(aggregate_correct) / Decimal(aggregate_scored), "f")
        ),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "usage: python -m qore.infrastructure.cibo.market_only_lab MARKET_EVIDENCE [MARKET_EVIDENCE ...]",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_market_only_lab(tuple(Path(item) for item in args))
    except CiboMarketOnlyLabError as error:
        print(f"CIBO Market-Only Lab blocked: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
