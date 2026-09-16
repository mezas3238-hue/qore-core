"""Read-only cTrader historical tick probe for consumed VT-31 fill-bar windows.

This is research-only infrastructure. It does not alter VT-31 trading semantics,
open a new holdout, or authorize execution. Windows supplied to this probe must
already belong to consumed R5/R6/R8 evidence.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    _RESEARCH_MARKETS,
    _connect_and_resolve_market,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_RELATIVE_PRICE_SCALE = Decimal(100_000)
_MAX_WINDOW_MS = 604_800_000
_MIN_REQUEST_INTERVAL_SECONDS = 0.21
_QUOTE_TYPES = {"BID": 1, "ASK": 2}


@dataclass(frozen=True, slots=True)
class HistoricalTick:
    timestamp_ms: int
    relative_price: int


def _int_env(name: str) -> int:
    value = _required_env(name)
    try:
        parsed = int(value)
    except ValueError as error:
        raise CTraderDemoLabProbeError(f"{name} must be an integer") from error
    if parsed <= 0:
        raise CTraderDemoLabProbeError(f"{name} must be positive")
    return parsed


def _decode_page(native_ticks: object) -> tuple[HistoricalTick, ...]:
    """Decode cTrader's newest-first delta representation.

    ProtoOAGetTickDataRes carries one absolute first record. Subsequent records
    carry signed deltas relative to the preceding record for both timestamp and
    tick price. Zero deltas are valid (for example multiple changes in one ms or
    an unchanged quote). The reconstructed timestamp must never move forward and
    the reconstructed relative price must remain positive.
    """
    items = tuple(cast(object, item) for item in cast(object, native_ticks))
    if not items:
        return ()
    decoded: list[HistoricalTick] = []
    previous_timestamp: int | None = None
    previous_relative_price: int | None = None
    for index, item in enumerate(items):
        raw_timestamp = getattr(item, "timestamp", None)
        raw_tick = getattr(item, "tick", None)
        if type(raw_timestamp) is not int or type(raw_tick) is not int:
            raise CTraderDemoLabProbeError("historical tick payload is malformed")
        if index == 0:
            if raw_timestamp <= 0 or raw_tick <= 0:
                raise CTraderDemoLabProbeError(
                    "historical tick absolute anchor is non-positive"
                )
            timestamp_ms = raw_timestamp
            relative_price = raw_tick
        else:
            if previous_timestamp is None or previous_relative_price is None:
                raise AssertionError("previous historical tick missing")
            timestamp_ms = previous_timestamp + raw_timestamp
            relative_price = previous_relative_price + raw_tick
            if timestamp_ms > previous_timestamp:
                raise CTraderDemoLabProbeError("historical ticks are not newest-first")
            if relative_price <= 0:
                raise CTraderDemoLabProbeError(
                    "historical tick reconstructed price is non-positive"
                )
        if timestamp_ms <= 0:
            raise CTraderDemoLabProbeError("historical tick timestamp delta is invalid")
        decoded.append(
            HistoricalTick(
                timestamp_ms=timestamp_ms,
                relative_price=relative_price,
            )
        )
        previous_timestamp = timestamp_ms
        previous_relative_price = relative_price
    return tuple(decoded)


def _enable_research_tick_messages(client: SpotwareCTraderOpenApiClient) -> None:
    """Admit historical-tick messages only inside this isolated research probe."""
    try:
        messages = importlib.import_module(
            "ctrader_open_api.messages.OpenApiMessages_pb2"
        )
        request_type = getattr(messages, "ProtoOAGetTickDataReq")
        response_type = getattr(messages, "ProtoOAGetTickDataRes")
    except (ImportError, AttributeError) as error:
        raise CTraderDemoLabProbeError(
            "official cTrader SDK historical-tick messages are unavailable"
        ) from error
    bindings = getattr(client, "_bindings", None)
    admitted = getattr(bindings, "messages", None)
    if not isinstance(admitted, dict):
        raise CTraderDemoLabProbeError("cTrader SDK binding registry is unavailable")
    admitted["ProtoOAGetTickDataReq"] = request_type
    admitted["ProtoOAGetTickDataRes"] = response_type


def _collect_side(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    quote_type: str,
    opened_ms: int,
    closed_ms: int,
    timeout_seconds: float,
) -> tuple[HistoricalTick, ...]:
    quote_value = _QUOTE_TYPES[quote_type]
    current_to = closed_ms
    collected: list[HistoricalTick] = []
    page = 0
    while True:
        page += 1
        response = client.request(
            "ProtoOAGetTickDataReq",
            {
                "ctidTraderAccountId": account_id,
                "symbolId": symbol_id,
                "type": quote_value,
                "fromTimestamp": opened_ms,
                "toTimestamp": current_to,
            },
            client_msg_id=(
                f"vt31-ticks:{symbol_id}:{quote_type}:{opened_ms}:{current_to}:{page}"
            ),
            timeout_seconds=timeout_seconds,
        )
        if isinstance(response, Failure):
            raise CTraderDemoLabProbeError(
                f"historical {quote_type} tick request failed"
            )
        value = response.value
        if getattr(value, "ctidTraderAccountId", None) != account_id:
            raise CTraderDemoLabProbeError("historical tick account mismatch")
        native_ticks = getattr(value, "tickData", None)
        if native_ticks is None:
            raise CTraderDemoLabProbeError("historical tick response is missing tickData")
        decoded = _decode_page(native_ticks)
        for tick in decoded:
            if not opened_ms <= tick.timestamp_ms <= closed_ms:
                raise CTraderDemoLabProbeError("historical tick escaped requested window")
        collected.extend(decoded)
        has_more = getattr(value, "hasMore", False)
        if type(has_more) is not bool:
            raise CTraderDemoLabProbeError("historical tick hasMore is malformed")
        if not has_more:
            break
        if not decoded:
            raise CTraderDemoLabProbeError("historical tick pagination made no progress")
        next_to = decoded[-1].timestamp_ms - 1
        if next_to < opened_ms or next_to >= current_to:
            raise CTraderDemoLabProbeError("historical tick pagination boundary is invalid")
        current_to = next_to
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS)
    unique: dict[tuple[int, int], HistoricalTick] = {}
    for tick in collected:
        unique[(tick.timestamp_ms, tick.relative_price)] = tick
    return tuple(sorted(unique.values(), key=lambda item: item.timestamp_ms))


def _projection(ticks: tuple[HistoricalTick, ...], digits: int) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for tick in ticks:
        price = Decimal(tick.relative_price) / _RELATIVE_PRICE_SCALE
        result.append(
            {
                "timestamp_ms": tick.timestamp_ms,
                "timestamp": datetime.fromtimestamp(tick.timestamp_ms / 1000, tz=UTC).isoformat(),
                "relative_price": tick.relative_price,
                "price": format(price, f".{digits}f"),
            }
        )
    return result


def main() -> None:
    market = _required_env("QORE_DEMO_LAB_SYMBOL")
    if market not in _RESEARCH_MARKETS:
        raise CTraderDemoLabProbeError("market must be NAS100, SP500 or US30")
    opened_ms = _int_env("QORE_TICK_WINDOW_OPEN_MS")
    closed_ms = _int_env("QORE_TICK_WINDOW_CLOSE_MS")
    if closed_ms <= opened_ms:
        raise CTraderDemoLabProbeError("tick window must close after it opens")
    if closed_ms - opened_ms > _MAX_WINDOW_MS:
        raise CTraderDemoLabProbeError("historical tick window exceeds cTrader one-week limit")
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        _enable_research_tick_messages(client)
        account_id, fingerprint, symbol, provider_symbol = _connect_and_resolve_market(
            client,
            market=market,
            timeout_seconds=10.0,
        )
        bid = _collect_side(
            client,
            account_id=account_id,
            symbol_id=symbol.symbol_id,
            quote_type="BID",
            opened_ms=opened_ms,
            closed_ms=closed_ms,
            timeout_seconds=10.0,
        )
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS)
        ask = _collect_side(
            client,
            account_id=account_id,
            symbol_id=symbol.symbol_id,
            quote_type="ASK",
            opened_ms=opened_ms,
            closed_ms=closed_ms,
            timeout_seconds=10.0,
        )
        payload: dict[str, object] = {
            "schema": "qore.vt31.consumed_historical_tick_window.v1",
            "research_only": True,
            "opens_new_holdout": False,
            "market": market,
            "provider_symbol": provider_symbol,
            "symbol_id": symbol.symbol_id,
            "digits": symbol.digits,
            "account_fingerprint": fingerprint,
            "opened_ms": opened_ms,
            "closed_ms": closed_ms,
            "bid": _projection(bid, symbol.digits),
            "ask": _projection(ask, symbol.digits),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    finally:
        client.close()


if __name__ == "__main__":
    main()
