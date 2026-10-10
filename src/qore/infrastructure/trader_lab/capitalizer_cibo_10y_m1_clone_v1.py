"""Retain a ten-year native-M1 clone for the nine-market Capitalizer universe.

Research only. This is the M1 execution-resolution companion to the already-consumed
CIBO 10Y M5 Atlas. It uses the same provider identities and exact 2016-09-17 to
2026-09-17 window, reads native provider M1, and never synthesizes M1 from M5.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
SCHEMA = "qore.capitalizer.cibo.m1_clone.v1"
RAW_SCHEMA = "qore.capitalizer.cibo.raw_m1.v1"
PERIOD_M1 = 1
TARGET_START = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
TARGET_END_EXCLUSIVE = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
CHUNK_DAYS = 2
MAX_BARS_PER_CHUNK = CHUNK_DAYS * 24 * 60

PROVIDER_SYMBOL_MAP: dict[str, str] = {
    "AUDJPY": "AUDJPY",
    "AUDUSD": "AUDUSD",
    "EURUSD": "EURUSD",
    "GBPJPY": "GBPJPY",
    "GBPUSD": "GBPUSD",
    "USDCAD": "USDCAD",
    "USDJPY": "USDJPY",
    "NAS100": "USTEC",
    "XAUUSD": "XAUUSD",
}
TARGET_SYMBOLS = tuple(PROVIDER_SYMBOL_MAP)


@dataclass(frozen=True, slots=True)
class RawM1Bar:
    schema: str
    identity: str
    canonical_symbol: str
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    opened_at: str
    utc_timestamp_in_minutes: int
    low_relative: int
    delta_open: int
    delta_high: int
    delta_close: int
    volume: int | None
    open_relative: int
    high_relative: int
    close_relative: int

    def payload_identity(self) -> tuple[int, ...]:
        return (
            self.low_relative,
            self.delta_open,
            self.delta_high,
            self.delta_close,
            -1 if self.volume is None else self.volume,
        )


def _required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError(f"missing required environment variable: {' or '.join(names)}")


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
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


def _native_int(value: object, name: str) -> int:
    raw = getattr(value, name)
    if type(raw) is not int:
        raise TypeError(f"{name} must be int")
    return raw


def _optional_native_int(value: object, name: str) -> int | None:
    raw = getattr(value, name, None)
    if raw is None:
        return None
    if type(raw) is not int:
        raise TypeError(f"{name} must be int when present")
    return raw


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _year_partitions() -> tuple[tuple[str, datetime, datetime], ...]:
    rows: list[tuple[str, datetime, datetime]] = []
    cursor = TARGET_START
    while cursor < TARGET_END_EXCLUSIVE:
        year_end = datetime(cursor.year + 1, 1, 1, tzinfo=UTC)
        closed_at = min(year_end, TARGET_END_EXCLUSIVE)
        rows.append((str(cursor.year), cursor, closed_at))
        cursor = closed_at
    return tuple(rows)


def _selected_symbol(
    client: SpotwareCTraderOpenApiClient,
    canonical_symbol: str,
) -> tuple[str, int, int]:
    provider_symbol = PROVIDER_SYMBOL_MAP[canonical_symbol]
    listed = client.request(
        "ProtoOASymbolsListReq",
        {"ctidTraderAccountId": client.account_id, "includeArchivedSymbols": False},
        client_msg_id=f"capitalizer-m1-symbols:{canonical_symbol}",
        timeout_seconds=30.0,
    )
    if isinstance(listed, Failure):
        raise RuntimeError(f"M1 symbol discovery failed: {listed.error}")
    native = tuple(cast(Iterable[object], getattr(listed.value, "symbol", ())))
    selected = next(
        (
            item
            for item in native
            if getattr(item, "symbolName", None) == provider_symbol
            and getattr(item, "enabled", None) is True
        ),
        None,
    )
    if selected is None:
        raise RuntimeError(f"provider symbol unavailable: {canonical_symbol}->{provider_symbol}")
    symbol_id = _native_int(selected, "symbolId")

    details = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": client.account_id, "symbolId": [symbol_id]},
        client_msg_id=f"capitalizer-m1-symbol:{symbol_id}",
        timeout_seconds=30.0,
    )
    if isinstance(details, Failure):
        raise RuntimeError(f"M1 symbol details failed: {details.error}")
    detail = next(
        (
            item
            for item in cast(Iterable[object], getattr(details.value, "symbol", ()))
            if getattr(item, "symbolId", None) == symbol_id
        ),
        None,
    )
    if detail is None:
        raise RuntimeError("provider symbol details missing")
    return provider_symbol, symbol_id, _native_int(detail, "digits")


def _read_chunk(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
    chunk_index: int,
) -> tuple[object, ...]:
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": PERIOD_M1,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=f"capitalizer-m1:{symbol}:{chunk_index}",
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"native M1 request failed for {symbol}: {result.error}")
    native = tuple(cast(Iterable[object], getattr(result.value, "trendbar", ())))
    if len(native) > MAX_BARS_PER_CHUNK:
        raise RuntimeError("provider returned more M1 bars than calendar grid permits")
    return native


def _provider_bar(
    native: object,
    *,
    canonical_symbol: str,
    provider_symbol: str,
    symbol_id: int,
    digits: int,
) -> RawM1Bar:
    minute = _native_int(native, "utcTimestampInMinutes")
    low = _native_int(native, "low")
    delta_open = _native_int(native, "deltaOpen")
    delta_high = _native_int(native, "deltaHigh")
    delta_close = _native_int(native, "deltaClose")
    if (
        minute < 0
        or low <= 0
        or min(delta_open, delta_high, delta_close) < 0
        or delta_open > delta_high
        or delta_close > delta_high
    ):
        raise ValueError("invalid provider-native M1 payload")
    opened_at = datetime.fromtimestamp(minute * 60, tz=UTC)
    return RawM1Bar(
        schema=RAW_SCHEMA,
        identity=IDENTITY,
        canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol,
        provider_symbol_id=symbol_id,
        digits=digits,
        opened_at=opened_at.isoformat(),
        utc_timestamp_in_minutes=minute,
        low_relative=low,
        delta_open=delta_open,
        delta_high=delta_high,
        delta_close=delta_close,
        volume=_optional_native_int(native, "volume"),
        open_relative=low + delta_open,
        high_relative=low + delta_high,
        close_relative=low + delta_close,
    )


def clone_symbol(symbol: str, output: Path) -> dict[str, object]:
    if symbol not in TARGET_SYMBOLS:
        raise ValueError(f"symbol outside Capitalizer universe: {symbol}")
    output.mkdir(parents=True, exist_ok=True)

    client = SpotwareCTraderOpenApiClient(
        credentials=_credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits = _selected_symbol(client, symbol)

        total = 0
        identical_duplicates = 0
        contradiction_count = 0
        chunk_index = 0
        partition_rows: list[dict[str, object]] = []

        for label, opened_at, closed_at in _year_partitions():
            retained: dict[int, RawM1Bar] = {}
            cursor = opened_at
            nonempty_chunks = 0
            while cursor < closed_at:
                chunk_close = min(cursor + timedelta(days=CHUNK_DAYS), closed_at)
                native_rows = _read_chunk(
                    client,
                    symbol=symbol,
                    symbol_id=symbol_id,
                    opened_at=cursor,
                    closed_at=chunk_close,
                    chunk_index=chunk_index,
                )
                nonempty_chunks += int(bool(native_rows))
                for native in native_rows:
                    bar = _provider_bar(
                        native,
                        canonical_symbol=symbol,
                        provider_symbol=provider_symbol,
                        symbol_id=symbol_id,
                        digits=digits,
                    )
                    bar_at = datetime.fromisoformat(bar.opened_at)
                    if not (opened_at <= bar_at < closed_at):
                        raise RuntimeError("provider returned M1 outside requested partition")
                    previous = retained.get(bar.utc_timestamp_in_minutes)
                    if previous is None:
                        retained[bar.utc_timestamp_in_minutes] = bar
                    elif previous.payload_identity() == bar.payload_identity():
                        identical_duplicates += 1
                    else:
                        contradiction_count += 1
                        raise RuntimeError("contradictory M1 payload")
                cursor = chunk_close
                chunk_index += 1

            raw_path = output / "RAW_M1_LEDGER" / f"{label}.jsonl"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            ordered = tuple(retained[key] for key in sorted(retained))
            with raw_path.open("w", encoding="utf-8") as handle:
                for row in ordered:
                    handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

            total += len(ordered)
            partition_rows.append(
                {
                    "partition": label,
                    "requested_start": opened_at.isoformat(),
                    "requested_end_exclusive": closed_at.isoformat(),
                    "retained_m1": len(ordered),
                    "nonempty_chunks": nonempty_chunks,
                    "first_observed_m1": None if not ordered else ordered[0].opened_at,
                    "last_observed_m1": None if not ordered else ordered[-1].opened_at,
                    "raw_sha256": _sha256(raw_path),
                }
            )
    finally:
        client.close()

    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "canonical_symbol": symbol,
        "provider_symbol": provider_symbol,
        "provider_symbol_id": symbol_id,
        "digits": digits,
        "target_start": TARGET_START.isoformat(),
        "target_end_exclusive": TARGET_END_EXCLUSIVE.isoformat(),
        "retained_m1": total,
        "identical_duplicates": identical_duplicates,
        "contradictory_m1": contradiction_count,
        "partitions": partition_rows,
        "provider_native_m1": True,
        "synthetic_m1": False,
        "interpolated_m1": False,
        "read_only": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    manifest_path = output / "m1-clone-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (output / "MANIFEST_SHA256SUMS.txt").write_text(
        f"{_sha256(manifest_path)}  m1-clone-manifest.json\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=TARGET_SYMBOLS)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = clone_symbol(args.symbol, args.output)
    print(
        json.dumps(
            {
                "identity": result["identity"],
                "symbol": result["canonical_symbol"],
                "retained_m1": result["retained_m1"],
                "provider_native_m1": result["provider_native_m1"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
