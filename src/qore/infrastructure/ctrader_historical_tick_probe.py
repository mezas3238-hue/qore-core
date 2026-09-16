"""Read-only historical cTrader tick acquisition for consumed VT-31 research."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from importlib import import_module

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_SCALE = Decimal(100_000)
_MAX_WINDOW_MS = 604_800_000

class HistoricalTickProbeError(RuntimeError):
    """Historical tick evidence cannot be proven complete."""

@dataclass(frozen=True, slots=True)
class HistoricalTick:
    timestamp_ms: int
    relative_price: int

def _decode(native: object) -> tuple[HistoricalTick, ...]:
    rows = tuple(getattr(native, "tickData", ()))
    if not rows:
        return ()
    decoded: list[HistoricalTick] = []
    previous: int | None = None
    for row in rows:
        raw_ts = getattr(row, "timestamp", None)
        price = getattr(row, "tick", None)
        if type(raw_ts) is not int or type(price) is not int or price <= 0:
            raise HistoricalTickProbeError("invalid native tick payload")
        timestamp = raw_ts if previous is None else previous - raw_ts
        if timestamp < 0 or (previous is not None and timestamp > previous):
            raise HistoricalTickProbeError("invalid relative tick chronology")
        decoded.append(HistoricalTick(timestamp, price))
        previous = timestamp
    return tuple(decoded)

def acquire(client: CTraderOpenApiMessageClientBoundary, *, symbol_id: int, quote_type: int, from_ms: int, to_ms: int, timeout_seconds: float = 15.0) -> tuple[HistoricalTick, ...]:
    """Acquire one bounded quote-side window, paginating newest-first fail closed."""
    if quote_type not in (1, 2):
        raise HistoricalTickProbeError("quote_type must be BID(1) or ASK(2)")
    if not (0 <= from_ms <= to_ms and to_ms - from_ms <= _MAX_WINDOW_MS):
        raise HistoricalTickProbeError("historical tick window must be <= one week")
    if not client.is_ready:
        auth = client.connect_and_authenticate()
        if isinstance(auth, Failure):
            raise HistoricalTickProbeError("cTrader authentication failed")
    upper = to_ms
    all_ticks: list[HistoricalTick] = []
    page = 0
    while True:
        page += 1
        response = client.request("ProtoOAGetTickDataReq", {"ctidTraderAccountId": client.account_id, "symbolId": symbol_id, "type": quote_type, "fromTimestamp": from_ms, "toTimestamp": upper}, client_msg_id=f"qore-vt31-consumed-ticks:{symbol_id}:{quote_type}:{page}", timeout_seconds=timeout_seconds)
        if isinstance(response, Failure):
            raise HistoricalTickProbeError("historical tick request failed")
        chunk = _decode(response.value)
        if not chunk:
            if getattr(response.value, "hasMore", False):
                raise HistoricalTickProbeError("provider asserted hasMore with empty page")
            break
        all_ticks.extend(chunk)
        if not getattr(response.value, "hasMore", False):
            break
        oldest = chunk[-1].timestamp_ms
        if oldest <= from_ms or oldest >= upper:
            raise HistoricalTickProbeError("historical tick pagination made no progress")
        upper = oldest - 1
    unique = {(t.timestamp_ms, t.relative_price): t for t in all_ticks}
    return tuple(sorted(unique.values(), key=lambda t: (t.timestamp_ms, t.relative_price)))

def _required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise HistoricalTickProbeError(f"missing runtime input: {name}")
    return value

def _symbol_id(client: CTraderOpenApiMessageClientBoundary, name: str) -> int:
    response = client.request("ProtoOASymbolsListReq", {"ctidTraderAccountId": client.account_id, "includeArchivedSymbols": True}, client_msg_id="qore-vt31-tick-symbol-list", timeout_seconds=15.0)
    if isinstance(response, Failure):
        raise HistoricalTickProbeError("symbol-list read failed")
    symbols = tuple(getattr(response.value, "symbol", ())) + tuple(getattr(response.value, "archivedSymbol", ()))
    for symbol in symbols:
        if getattr(symbol, "symbolName", None) == name:
            value = getattr(symbol, "symbolId", None)
            if type(value) is int and value > 0:
                return value
    raise HistoricalTickProbeError("requested symbol is unavailable")

def main() -> int:
    account = int(_required("QORE_CTRADER_DEMO_ACCOUNT_ID"))
    credentials = CTraderOpenApiCredentials(client_id=_required("QORE_CTRADER_CLIENT_ID"), client_secret=_required("QORE_CTRADER_CLIENT_SECRET"), access_token=_required("QORE_CTRADER_ACCESS_TOKEN"), refresh_token=_required("QORE_CTRADER_REFRESH_TOKEN"), ctid_trader_account_id=account)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    messages = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
    client._bindings.messages["ProtoOAGetTickDataReq"] = messages.ProtoOAGetTickDataReq
    client._bindings.messages["ProtoOAGetTickDataRes"] = messages.ProtoOAGetTickDataRes
    try:
        auth = client.connect_and_authenticate()
        if isinstance(auth, Failure):
            raise HistoricalTickProbeError("cTrader authentication failed")
        symbol = _required("QORE_VT31_TICK_SYMBOL")
        symbol_id = _symbol_id(client, symbol)
        from_ms = int(_required("QORE_VT31_TICK_FROM_MS")); to_ms = int(_required("QORE_VT31_TICK_TO_MS"))
        sides: dict[str, object] = {}
        for label, quote_type in (("bid", 1), ("ask", 2)):
            ticks = acquire(client, symbol_id=symbol_id, quote_type=quote_type, from_ms=from_ms, to_ms=to_ms)
            canonical = "\n".join(f"{t.timestamp_ms},{t.relative_price}" for t in ticks)
            sides[label] = {"count": len(ticks), "first_timestamp_ms": ticks[0].timestamp_ms if ticks else None, "last_timestamp_ms": ticks[-1].timestamp_ms if ticks else None, "sha256": sha256(canonical.encode("ascii")).hexdigest()}
        payload = {"schema": "qore.vt31.consumed_historical_tick_probe.v1", "read_only": True, "symbol": symbol, "from_ms": from_ms, "to_ms": to_ms, "quote_sides": sides, "checked_at": datetime.now(UTC).isoformat()}
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return 0
    finally:
        client.close()

if __name__ == "__main__":
    raise SystemExit(main())
