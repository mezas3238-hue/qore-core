"""IC Markets DEMO provider-native M1 capture for 24 missing QORE instruments.

Source algorithm adapted verbatim from the tested nine-market Capitalizer 10Y M1
clone (repo commit 18c338aedd5013ce65a6cb6408ffbc2e904a6217).
New scoped broker-account proof is mandatory. First-known native M1 is retained
without synthesis, OHLC guessing, interpolation, trading or token refresh.
No fresh OOS claim: the underlying period is already previously inspected.
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

from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiCredentials
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    probe_catalog,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m5_capture_v1 import (
    _ReadOnlyIcMarketsHistoryClient,
)
from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    M1_10Y, universe,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_ICMARKETS_DEMO_24_MISSING_NATIVE_M1_10Y_V1"
SCHEMA = "qore.native.icmarkets_demo_24_missing_m1_10y.v1"
RAW_SCHEMA = "qore.native.icmarkets_demo_24_missing_m1_10y.raw.v1"
PERIOD_M1 = 1
TARGET_START = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
TARGET_END_EXCLUSIVE = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
CHUNK_DAYS = 2
MAX_BARS_PER_CHUNK = CHUNK_DAYS * 24 * 60

# This is an as-of-source universe contract, never inferred from outcomes.
TARGET_SYMBOLS = tuple(s for s in universe() if s not in M1_10Y)
PROVIDER_SYMBOL_MAP: dict[str, str] = {
    symbol: ("US500" if symbol == "SP500" else symbol)
    for symbol in TARGET_SYMBOLS
}
if len(TARGET_SYMBOLS) != 24:
    raise RuntimeError("M1_UNIVERSE_24_INTEGRITY_FAILED")


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
    client: _ReadOnlyIcMarketsHistoryClient,
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
    client: _ReadOnlyIcMarketsHistoryClient,
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


def require_icmarkets_source(symbol: str) -> tuple[int, int]:
    """Positive IC Markets DEMO broker + exact catalog provider-ID proof.

    The primary US500 alias is the historical original SP500 provider symbol
    in the CIBO 12-market Atlas. It is not guessed from numerical similarity.
    Provider must currently expose US500 as enabled; no auto symbol fallbacks.
    """
    if symbol not in TARGET_SYMBOLS:
        raise ValueError("M1_SYMBOL_ALREADY_ARCHIVED_OR_NOT_ADMITTED")
    report = probe_catalog()
    if report["status"] != "ICMARKETS_DEMO_CATALOG_VERIFIED":
        raise ValueError("ICMARKETS_DEMO_ACCOUNT_PROOF_FAILED")
    source = PROVIDER_SYMBOL_MAP[symbol]
    candidates = report["catalog"]["catalog_exact_matches"]
    match = candidates.get(source)
    if (match is None or match["broker_symbol"] != source
            or match["enabled"] is not True
            or type(match["symbol_id"]) is not int or match["symbol_id"] <= 0):
        raise ValueError("EXACT_PROVIDER_M1_SYMBOL_ID_UNAVAILABLE")
    account_id = report["_ephemeral_account_id"]
    if type(account_id) is not int or account_id <= 0:
        raise ValueError("BROKER_DEMO_ACCOUNT_UNVERIFIED")
    return account_id, match["symbol_id"]


def clone_symbol(
    symbol: str, output: Path, *, source_proof: tuple[int, int] | None = None,
) -> dict[str, object]:
    if symbol not in TARGET_SYMBOLS:
        raise ValueError("M1_SYMBOL_ALREADY_ARCHIVED_OR_NOT_ADMITTED")
    if (not isinstance(source_proof, tuple) or len(source_proof) != 2
            or any(type(x) is not int or x <= 0 for x in source_proof)):
        raise ValueError("EXACT_DEMO_BROKER_SOURCE_PROOF_REQUIRED")
    # Environment scope is confined to this single research process.
    os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(source_proof[0])
    os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
    output.mkdir(parents=True, exist_ok=True)

    client = _ReadOnlyIcMarketsHistoryClient(
        credentials=_credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits = _selected_symbol(client, symbol)
        if symbol_id != source_proof[1]:
            raise RuntimeError("PROVIDER_SYMBOL_ID_CHANGED_AFTER_CATALOG_PROOF")

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
        "source_account_confirmed_icmarkets_demo": True,
        "source_symbol_id_proven_before_read": True,
        "source_provider": "cTrader_ICMarkets_DEMO",
        "scope_read_only": True,
        "research_evidence_previously_inspected": True,
        "fresh_holdout": False,
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
    source_proof = require_icmarkets_source(args.symbol)
    result = clone_symbol(args.symbol, args.output, source_proof=source_proof)
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
