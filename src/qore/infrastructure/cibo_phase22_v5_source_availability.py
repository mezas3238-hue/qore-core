"""Read-only DEMO source-availability probe for Phase22 V5.

Only symbol metadata and trendbar timestamps are read. No Trader methodology is
executed and no broker mutation request type is permitted.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v5_governance import (
    PHASE22_V5_CANDIDATE,
    assert_phase22_v5_pre_outcome_governance,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_10y_m5_consumer_v1 import (
    PROVIDER_SYMBOL_MAP,
)
from qore.kernel.result import Failure

PERIOD_M1 = 1
PERIOD_M5 = 5
M1_WINDOW = timedelta(days=2)
M5_WINDOW = timedelta(days=7)
REQUIRED_M5_SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
)
ALLOWED_REQUEST_TYPES = frozenset(
    {"ProtoOASymbolsListReq", "ProtoOAGetTrendbarsReq"}
)


@dataclass(frozen=True, slots=True)
class V5SourceBoundaryProbe:
    symbol: str
    provider_symbol: str
    timeframe: str
    first_window_start: datetime
    first_window_end: datetime
    last_window_start: datetime
    last_window_end: datetime
    first_window_bars: int
    last_window_bars: int
    first_observed_at: datetime | None
    last_observed_at: datetime | None
    available: bool


def probe_windows(
    start_at: datetime,
    end_exclusive_at: datetime,
    timeframe: str,
) -> tuple[tuple[datetime, datetime], tuple[datetime, datetime]]:
    if timeframe == "M1":
        width = M1_WINDOW
    elif timeframe == "M5":
        width = M5_WINDOW
    else:
        raise CiboCapitalManagementError("V5 timeframe must be M1 or M5")
    if (
        start_at.tzinfo is None
        or start_at.utcoffset() is None
        or end_exclusive_at.tzinfo is None
        or end_exclusive_at.utcoffset() is None
        or end_exclusive_at <= start_at
    ):
        raise CiboCapitalManagementError("V5 probe interval invalid")
    return (
        (start_at, min(start_at + width, end_exclusive_at)),
        (max(start_at, end_exclusive_at - width), end_exclusive_at),
    )


def assess_probe(
    *,
    symbol: str,
    provider_symbol: str,
    timeframe: str,
    first_window: tuple[datetime, datetime],
    last_window: tuple[datetime, datetime],
    first_timestamps: tuple[datetime, ...],
    last_timestamps: tuple[datetime, ...],
) -> V5SourceBoundaryProbe:
    if symbol not in REQUIRED_M5_SYMBOLS:
        raise CiboCapitalManagementError("V5 source symbol outside surface")
    if timeframe == "M1" and symbol != "NAS100":
        raise CiboCapitalManagementError("V5 M1 is NAS100-only")
    period = PERIOD_M1 if timeframe == "M1" else PERIOD_M5
    for rows, window in (
        (first_timestamps, first_window),
        (last_timestamps, last_window),
    ):
        if rows != tuple(sorted(rows)) or len(rows) != len(set(rows)):
            raise CiboCapitalManagementError("V5 source timestamps invalid")
        if any(
            value.tzinfo is None
            or value.utcoffset() is None
            or not (window[0] <= value < window[1])
            or int(value.timestamp() // 60) % period != 0
            for value in rows
        ):
            raise CiboCapitalManagementError("V5 source timestamp drift")
    available = bool(first_timestamps and last_timestamps)
    return V5SourceBoundaryProbe(
        symbol=symbol,
        provider_symbol=provider_symbol,
        timeframe=timeframe,
        first_window_start=first_window[0],
        first_window_end=first_window[1],
        last_window_start=last_window[0],
        last_window_end=last_window[1],
        first_window_bars=len(first_timestamps),
        last_window_bars=len(last_timestamps),
        first_observed_at=first_timestamps[0] if first_timestamps else None,
        last_observed_at=last_timestamps[-1] if last_timestamps else None,
        available=available,
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required DEMO environment variable: {name}")
    return value


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID"),
        client_secret=_required_env("QORE_CTRADER_CLIENT_SECRET"),
        access_token=_required_env("QORE_CTRADER_ACCESS_TOKEN"),
        refresh_token=_required_env("QORE_CTRADER_REFRESH_TOKEN"),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID")
        ),
    )


def _native_int(value: object, name: str) -> int:
    raw = getattr(value, name)
    if type(raw) is not int:
        raise TypeError(f"{name} must be int")
    return raw


def _request(
    client: SpotwareCTraderOpenApiClient,
    request_type: str,
    payload: dict[str, object],
    *,
    client_msg_id: str,
) -> object:
    if request_type not in ALLOWED_REQUEST_TYPES:
        raise CiboCapitalManagementError(
            "V5 source probe attempted broker mutation"
        )
    result = client.request(
        request_type,
        payload,
        client_msg_id=client_msg_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"V5 read-only provider request failed: {result.error}")
    return result.value


def _provider_symbol_id(
    client: SpotwareCTraderOpenApiClient,
    canonical_symbol: str,
) -> tuple[str, int]:
    provider_symbol = PROVIDER_SYMBOL_MAP[canonical_symbol]
    response = _request(
        client,
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": client.account_id,
            "includeArchivedSymbols": False,
        },
        client_msg_id=f"cibo-v5-symbol:{canonical_symbol}",
    )
    symbols = tuple(cast(Iterable[object], getattr(response, "symbol", ())))
    selected = next(
        (
            item
            for item in symbols
            if getattr(item, "symbolName", None) == provider_symbol
            and getattr(item, "enabled", None) is True
        ),
        None,
    )
    if selected is None:
        raise RuntimeError(f"V5 provider symbol unavailable: {canonical_symbol}")
    return provider_symbol, _native_int(selected, "symbolId")


def _read_timestamps(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    period: int,
    opened_at: datetime,
    closed_at: datetime,
    label: str,
) -> tuple[datetime, ...]:
    response = _request(
        client,
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": period,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=f"cibo-v5-source:{label}",
    )
    rows = tuple(cast(Iterable[object], getattr(response, "trendbar", ())))
    maximum = int(
        (closed_at - opened_at).total_seconds() // 60 // period
    ) + 1
    if len(rows) > maximum:
        raise RuntimeError("V5 provider returned impossible bar count")
    return tuple(
        sorted(
            datetime.fromtimestamp(
                _native_int(item, "utcTimestampInMinutes") * 60,
                tz=UTC,
            )
            for item in rows
        )
    )


def run_probe() -> dict[str, object]:
    assert_phase22_v5_pre_outcome_governance()
    candidate = PHASE22_V5_CANDIDATE
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    probes: list[V5SourceBoundaryProbe] = []
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        for symbol in REQUIRED_M5_SYMBOLS:
            provider_symbol, symbol_id = _provider_symbol_id(client, symbol)
            timeframes = ("M5", "M1") if symbol == "NAS100" else ("M5",)
            for timeframe in timeframes:
                first, last = probe_windows(
                    candidate.start_at,
                    candidate.end_exclusive_at,
                    timeframe,
                )
                period = PERIOD_M1 if timeframe == "M1" else PERIOD_M5
                first_rows = _read_timestamps(
                    client,
                    symbol_id=symbol_id,
                    period=period,
                    opened_at=first[0],
                    closed_at=first[1],
                    label=f"{symbol}:{timeframe}:first",
                )
                last_rows = _read_timestamps(
                    client,
                    symbol_id=symbol_id,
                    period=period,
                    opened_at=last[0],
                    closed_at=last[1],
                    label=f"{symbol}:{timeframe}:last",
                )
                probes.append(
                    assess_probe(
                        symbol=symbol,
                        provider_symbol=provider_symbol,
                        timeframe=timeframe,
                        first_window=first,
                        last_window=last,
                        first_timestamps=first_rows,
                        last_timestamps=last_rows,
                    )
                )
    finally:
        client.close()

    expected = {(symbol, "M5") for symbol in REQUIRED_M5_SYMBOLS}
    expected.add(("NAS100", "M1"))
    observed = {(item.symbol, item.timeframe) for item in probes}
    if observed != expected:
        raise CiboCapitalManagementError("V5 source probe surface incomplete")
    available = all(item.available for item in probes)
    return {
        "schema": "qore.cibo.phase22.v5-source-availability.v1",
        "candidate_id": candidate.candidate_id,
        "window": {
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
        },
        "probe_count": len(probes),
        "required_surface_count": len(expected),
        "source_available": available,
        "status": "SOURCE_AVAILABLE" if available else "SOURCE_UNAVAILABLE",
        "probes": [
            {
                **asdict(item),
                "first_window_start": item.first_window_start.isoformat(),
                "first_window_end": item.first_window_end.isoformat(),
                "last_window_start": item.last_window_start.isoformat(),
                "last_window_end": item.last_window_end.isoformat(),
                "first_observed_at": (
                    None
                    if item.first_observed_at is None
                    else item.first_observed_at.isoformat()
                ),
                "last_observed_at": (
                    None
                    if item.last_observed_at is None
                    else item.last_observed_at.isoformat()
                ),
            }
            for item in probes
        ],
        "allowed_broker_request_types": sorted(ALLOWED_REQUEST_TYPES),
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "broker_mutation": False,
        "positions_opened": 0,
        "positions_closed": 0,
        "orders_created": 0,
        "orders_modified": 0,
        "orders_cancelled": 0,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "productive_authority": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = run_probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    if payload["source_available"] is not True:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
