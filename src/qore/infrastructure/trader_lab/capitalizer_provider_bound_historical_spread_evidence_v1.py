"""Provider-bound historical spread evidence for consumed Capitalizer ledgers.

This module binds historical cTrader BID/ASK ticks to already-selected consumed
trade timestamps. It does not select trades from outcomes, does not mutate the
strategy, and does not touch the sealed fresh holdout.

Raw tick streams are never persisted. Only the latest causal quote at or before
each entry/exit timestamp, its age, and the resulting spread are retained.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_10y_m1_clone_v1 import (
    TARGET_SYMBOLS,
    _credentials,
    _selected_symbol,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_PROVIDER_BOUND_HISTORICAL_SPREAD_EVIDENCE_V1"
LOOKBACK_SECONDS = 60
MAX_QUOTE_AGE_MS = 30_000
MIN_REQUEST_INTERVAL_SECONDS = 0.25
PRICE_SCALE = Decimal("100000")
QUOTE_TYPES = (("BID", 1), ("ASK", 2))


@dataclass(frozen=True, slots=True)
class TradeQuoteNeed:
    symbol: str
    entry_at: str
    exit_at: str
    entry_price: str
    original_stop_price: str


@dataclass(frozen=True, slots=True)
class CausalQuote:
    quote_type: str
    event_at: str
    observed_at_ms: int
    age_ms: int
    price: str
    future_quote_used: bool = False
    synthetic_quote: bool = False
    interpolated_quote: bool = False


@dataclass(frozen=True, slots=True)
class SpreadObservation:
    symbol: str
    entrant_entry_at: str
    event_kind: str
    event_at: str
    bid_observed_at_ms: int
    ask_observed_at_ms: int
    bid_age_ms: int
    ask_age_ms: int
    bid_price: str
    ask_price: str
    spread_price: str
    structural_risk_price: str
    spread_r: str
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    future_quote_used: bool = False
    synthetic_quote: bool = False
    interpolated_quote: bool = False


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("spread-evidence timestamps must be timezone-aware")
    return parsed


def _load_needs(path: Path, *, symbol: str) -> tuple[TradeQuoteNeed, ...]:
    rows: list[TradeQuoteNeed] = []
    seen: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("spread source row must be object")
            if raw.get("symbol") != symbol:
                continue
            key = (symbol, str(raw["entry_at"]))
            if key in seen:
                raise ValueError("spread source entrant identity collision")
            seen.add(key)
            rows.append(
                TradeQuoteNeed(
                    symbol=symbol,
                    entry_at=str(raw["entry_at"]),
                    exit_at=str(raw["exit_at"]),
                    entry_price=str(raw["entry_price"]),
                    original_stop_price=str(raw["original_stop_price"]),
                )
            )
    if not rows:
        raise ValueError(f"spread source has no rows for {symbol}")
    return tuple(sorted(rows, key=lambda row: _aware(row.entry_at)))


def _decode_tick_times(ticks: tuple[object, ...]) -> tuple[tuple[int, int], ...]:
    """Decode cTrader newest-first absolute+delta timestamp encoding."""

    if not ticks:
        return ()
    first_timestamp = getattr(ticks[0], "timestamp", None)
    first_price = getattr(ticks[0], "tick", None)
    if type(first_timestamp) is not int or first_timestamp <= 0:
        raise ValueError("first historical tick must contain absolute Unix ms")
    if type(first_price) is not int or first_price <= 0:
        raise ValueError("historical tick price must be positive int")

    result: list[tuple[int, int]] = [(first_timestamp, first_price)]
    previous_at = first_timestamp
    for item in ticks[1:]:
        delta = getattr(item, "timestamp", None)
        price = getattr(item, "tick", None)
        if type(delta) is not int or delta < 0:
            raise ValueError("historical tick delta timestamp must be non-negative")
        if type(price) is not int or price <= 0:
            raise ValueError("historical tick price must be positive int")
        current_at = previous_at - delta
        if current_at > previous_at:
            raise ValueError("decoded historical tick chronology inverted")
        result.append((current_at, price))
        previous_at = current_at
    return tuple(result)


def _request_quote(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    symbol_id: int,
    digits: int,
    event_at: datetime,
    quote_name: str,
    quote_type: int,
    request_index: int,
) -> CausalQuote:
    event_ms = int(event_at.timestamp() * 1000)
    from_at = event_at - timedelta(seconds=LOOKBACK_SECONDS)
    result = client.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": symbol_id,
            "type": quote_type,
            "fromTimestamp": int(from_at.timestamp() * 1000),
            "toTimestamp": event_ms,
        },
        client_msg_id=(
            f"capitalizer-spread:{symbol}:{quote_name}:{request_index}"
        ),
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(
            f"historical {quote_name} request failed: "
            f"{type(result.error).__name__}"
        )
    if getattr(result.value, "ctidTraderAccountId", None) != client.account_id:
        raise RuntimeError("historical quote response account mismatch")
    if getattr(result.value, "hasMore", None) is True:
        raise RuntimeError("60-second historical quote window unexpectedly truncated")

    raw_ticks = tuple(cast(Iterable[object], getattr(result.value, "tickData", ())))
    decoded = _decode_tick_times(raw_ticks)
    causal = tuple((at, price) for at, price in decoded if at <= event_ms)
    if not causal:
        raise RuntimeError(
            f"no causal {quote_name} quote in {LOOKBACK_SECONDS}s window"
        )
    observed_at_ms, relative_price = max(causal, key=lambda item: item[0])
    age_ms = event_ms - observed_at_ms
    if age_ms < 0:
        raise RuntimeError("future historical quote selected")
    if age_ms > MAX_QUOTE_AGE_MS:
        raise RuntimeError(
            f"stale historical {quote_name} quote: {age_ms}ms"
        )
    price = (Decimal(relative_price) / PRICE_SCALE).quantize(
        Decimal(1).scaleb(-digits)
    )
    return CausalQuote(
        quote_type=quote_name,
        event_at=event_at.isoformat(),
        observed_at_ms=observed_at_ms,
        age_ms=age_ms,
        price=str(price),
    )


def build_market_spread_evidence(
    ledger_path: Path,
    *,
    symbol: str,
    population_role: str,
    output: Path,
) -> dict[str, object]:
    if symbol not in TARGET_SYMBOLS:
        raise ValueError(f"symbol outside Capitalizer universe: {symbol}")
    if not population_role.startswith("CONSUMED_"):
        raise ValueError("spread evidence is restricted to consumed periods")

    needs = _load_needs(ledger_path, symbol=symbol)
    output.mkdir(parents=True, exist_ok=True)
    client = SpotwareCTraderOpenApiClient(
        credentials=_credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                "cTrader DEMO authentication failed: "
                f"{type(ready.error).__name__}"
            )
        provider_symbol, symbol_id, digits = _selected_symbol(client, symbol)

        cache: dict[tuple[str, str], CausalQuote] = {}
        request_index = 0

        def quote(event_at: datetime, quote_name: str, quote_type: int) -> CausalQuote:
            nonlocal request_index
            key = (event_at.isoformat(), quote_name)
            cached = cache.get(key)
            if cached is not None:
                return cached
            row = _request_quote(
                client,
                symbol=symbol,
                symbol_id=symbol_id,
                digits=digits,
                event_at=event_at,
                quote_name=quote_name,
                quote_type=quote_type,
                request_index=request_index,
            )
            request_index += 1
            cache[key] = row
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
            return row

        observations: list[SpreadObservation] = []
        for need in needs:
            risk = abs(
                Decimal(need.entry_price) - Decimal(need.original_stop_price)
            )
            if risk <= 0:
                raise ValueError("spread evidence requires positive structural risk")
            for event_kind, raw_at in (
                ("ENTRY", need.entry_at),
                ("EXIT", need.exit_at),
            ):
                event_at = _aware(raw_at)
                bid = quote(event_at, "BID", 1)
                ask = quote(event_at, "ASK", 2)
                bid_price = Decimal(bid.price)
                ask_price = Decimal(ask.price)
                if ask_price < bid_price:
                    raise RuntimeError("provider historical spread is negative")
                spread = ask_price - bid_price
                observations.append(
                    SpreadObservation(
                        symbol=symbol,
                        entrant_entry_at=need.entry_at,
                        event_kind=event_kind,
                        event_at=event_at.isoformat(),
                        bid_observed_at_ms=bid.observed_at_ms,
                        ask_observed_at_ms=ask.observed_at_ms,
                        bid_age_ms=bid.age_ms,
                        ask_age_ms=ask.age_ms,
                        bid_price=bid.price,
                        ask_price=ask.price,
                        spread_price=str(spread),
                        structural_risk_price=str(risk),
                        spread_r=str(spread / risk),
                        provider_symbol=provider_symbol,
                        provider_symbol_id=symbol_id,
                        digits=digits,
                    )
                )
    finally:
        client.close()

    expected = len(needs) * 2
    if len(observations) != expected:
        raise RuntimeError("spread evidence coverage mismatch")
    entrant_keys = {(row.symbol, row.entrant_entry_at) for row in observations}
    if len(entrant_keys) != len(needs):
        raise RuntimeError("spread evidence entrant coverage mismatch")

    spread_r_values = tuple(Decimal(row.spread_r) for row in observations)
    ages = tuple(
        max(row.bid_age_ms, row.ask_age_ms) for row in observations
    )
    report: dict[str, object] = {
        "identity": IDENTITY,
        "population_role": population_role,
        "canonical_symbol": symbol,
        "provider_symbol": provider_symbol,
        "provider_symbol_id": symbol_id,
        "digits": digits,
        "entrants": len(needs),
        "expected_events": expected,
        "observed_events": len(observations),
        "event_coverage": "1",
        "max_quote_age_ms": max(ages),
        "quote_age_ceiling_ms": MAX_QUOTE_AGE_MS,
        "mean_spread_r": str(
            sum(spread_r_values, Decimal("0"))
            / Decimal(len(spread_r_values))
        ),
        "max_spread_r": str(max(spread_r_values)),
        "negative_spreads": 0,
        "future_quote_used": False,
        "synthetic_quote_used": False,
        "interpolated_quote_used": False,
        "outcome_used_for_quote_selection": False,
        "fresh_holdout_touched": False,
        "spread_evidence_bound": True,
        "commission_evidence_bound": False,
        "slippage_evidence_bound": False,
        "cost_certification_satisfied": False,
        "raw_ticks_persisted": False,
    }
    stem = f"capitalizer-{symbol.lower()}-{population_role.lower()}-spread-evidence-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-events.jsonl").open("w", encoding="utf-8") as handle:
        for row in observations:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    parser.add_argument("symbol", choices=TARGET_SYMBOLS)
    parser.add_argument("population_role")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report = build_market_spread_evidence(
        args.ledger,
        symbol=args.symbol,
        population_role=args.population_role,
        output=args.output,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
