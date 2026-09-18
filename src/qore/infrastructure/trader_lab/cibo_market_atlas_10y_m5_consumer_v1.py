"""CIBO Market Atlas — ten-year canonical M5 market consumer.

Research-only. Reads cTrader DEMO M5 evidence for the frozen twelve-market Atlas
universe and retains lossless provider-relative OHLC rows plus explicit data-quality
observations. It does not trade, infer a trader rule, or authorize capital.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
PARENT_IDENTITY = "CIBO_MARKET_ATLAS_20Y_V1"
SCHEMA = "qore.cibo_market_atlas.m5_consumption.v1"
RAW_SCHEMA = "qore.cibo_market_atlas.raw_m5.v1"
QUALITY_SCHEMA = "qore.cibo_market_atlas.data_quality.v1"
PERIOD_M5 = 5
REQUEST_COUNT = 5000
REQUEST_PAUSE_SECONDS = 0.12
TARGET_START = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
TARGET_END_EXCLUSIVE = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
CHUNK_DAYS = 7

PROVIDER_SYMBOL_MAP: dict[str, str] = {
    "AUDJPY": "AUDJPY",
    "AUDUSD": "AUDUSD",
    "EURUSD": "EURUSD",
    "GBPJPY": "GBPJPY",
    "GBPUSD": "GBPUSD",
    "USDCAD": "USDCAD",
    "USDJPY": "USDJPY",
    "NAS100": "USTEC",
    "SP500": "US500",
    "US30": "US30",
    "XAUUSD": "XAUUSD",
    "XAGUSD": "XAGUSD",
}
TARGET_SYMBOLS = tuple(PROVIDER_SYMBOL_MAP)


@dataclass(frozen=True, slots=True)
class Partition:
    label: str
    opened_at: datetime
    closed_at: datetime


@dataclass(frozen=True, slots=True)
class RawM5Bar:
    schema: str
    identity: str
    parent_identity: str
    canonical_symbol: str
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    pip_position: int | None
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


@dataclass(frozen=True, slots=True)
class PartitionManifest:
    schema: str
    identity: str
    canonical_symbol: str
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    pip_position: int | None
    partition: str
    requested_start: str
    requested_end_exclusive: str
    first_observed_m5: str | None
    last_observed_m5: str | None
    retained_bars: int
    identical_duplicates: int
    contradictory_bars: int
    timestamp_alignment_errors: int
    out_of_window_bars: int
    unresolved_gap_runs: int
    unresolved_calendar_slots: int
    raw_integrity_status: str
    session_adjusted_completeness: float | None
    read_only: bool
    demo_eligible: bool
    live_authorized: bool
    real_capital_authorized: bool
    production_authorized: bool


@dataclass(frozen=True, slots=True)
class SymbolConsumptionManifest:
    schema: str
    identity: str
    parent_identity: str
    canonical_symbol: str
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    pip_position: int | None
    target_start: str
    target_end_exclusive: str
    earliest_observed_m5: str | None
    latest_observed_m5: str | None
    retained_bars: int
    partitions: tuple[dict[str, Any], ...]
    raw_integrity_status: str
    expected_open_calendar_status: str
    research_evidence_consumed: bool
    read_only: bool
    demo_eligible: bool
    live_authorized: bool
    real_capital_authorized: bool
    production_authorized: bool


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


def _bar_timestamp(native: object) -> datetime:
    return datetime.fromtimestamp(_native_int(native, "utcTimestampInMinutes") * 60, tz=UTC)


def partition_grid(
    start: datetime = TARGET_START,
    end: datetime = TARGET_END_EXCLUSIVE,
) -> tuple[Partition, ...]:
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("partition grid requires aware start < end")
    result: list[Partition] = []
    cursor = start
    while cursor < end:
        year_end = datetime(cursor.year + 1, 1, 1, tzinfo=UTC)
        closed_at = min(year_end, end)
        result.append(Partition(str(cursor.year), cursor, closed_at))
        cursor = closed_at
    return tuple(result)


def chunk_grid(partition: Partition) -> tuple[tuple[datetime, datetime], ...]:
    result: list[tuple[datetime, datetime]] = []
    cursor = partition.opened_at
    while cursor < partition.closed_at:
        closed_at = min(cursor + timedelta(days=CHUNK_DAYS), partition.closed_at)
        result.append((cursor, closed_at))
        cursor = closed_at
    return tuple(result)


def _spans_weekend(opened_at: datetime, closed_at: datetime) -> bool:
    cursor = opened_at.date()
    final = closed_at.date()
    while cursor <= final:
        if cursor.weekday() >= 5:
            return True
        cursor += timedelta(days=1)
    return False


def unresolved_gap_records(bars: tuple[RawM5Bar, ...]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for previous, current in zip(bars, bars[1:], strict=False):
        previous_at = datetime.fromisoformat(previous.opened_at)
        current_at = datetime.fromisoformat(current.opened_at)
        delta_minutes = int((current_at - previous_at).total_seconds() // 60)
        if delta_minutes <= PERIOD_M5:
            continue
        gap_start = previous_at + timedelta(minutes=PERIOD_M5)
        gap_end = current_at
        records.append(
            {
                "schema": QUALITY_SCHEMA,
                "identity": IDENTITY,
                "canonical_symbol": previous.canonical_symbol,
                "kind": "UNRESOLVED_CLOSURE_OR_MISSING_DATA",
                "previous_bar_at": previous.opened_at,
                "next_bar_at": current.opened_at,
                "gap_start": gap_start.isoformat(),
                "gap_end_exclusive": gap_end.isoformat(),
                "calendar_slots_without_bars": max(delta_minutes // PERIOD_M5 - 1, 0),
                "spans_weekend": _spans_weekend(gap_start, gap_end),
                "market_open_expected": None,
                "outcome_only": False,
            }
        )
    return tuple(records)


def _provider_bar(
    native: object,
    *,
    canonical_symbol: str,
    provider_symbol: str,
    provider_symbol_id: int,
    digits: int,
    pip_position: int | None,
) -> RawM5Bar:
    low = _native_int(native, "low")
    delta_open = _native_int(native, "deltaOpen")
    delta_high = _native_int(native, "deltaHigh")
    delta_close = _native_int(native, "deltaClose")
    timestamp_minutes = _native_int(native, "utcTimestampInMinutes")
    if low <= 0 or min(delta_open, delta_high, delta_close, timestamp_minutes) < 0:
        raise ValueError("invalid provider-relative M5 payload")
    if delta_open > delta_high or delta_close > delta_high:
        raise ValueError("provider M5 open/close exceeds high")
    opened_at = datetime.fromtimestamp(timestamp_minutes * 60, tz=UTC)
    return RawM5Bar(
        schema=RAW_SCHEMA,
        identity=IDENTITY,
        parent_identity=PARENT_IDENTITY,
        canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol,
        provider_symbol_id=provider_symbol_id,
        digits=digits,
        pip_position=pip_position,
        opened_at=opened_at.isoformat(),
        utc_timestamp_in_minutes=timestamp_minutes,
        low_relative=low,
        delta_open=delta_open,
        delta_high=delta_high,
        delta_close=delta_close,
        volume=_optional_native_int(native, "volume"),
        open_relative=low + delta_open,
        high_relative=low + delta_high,
        close_relative=low + delta_close,
    )


def _read_chunk(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
    client_msg_id: str,
) -> tuple[object, ...]:
    sleep(REQUEST_PAUSE_SECONDS)
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": account_id,
            "count": REQUEST_COUNT,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": PERIOD_M5,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=client_msg_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"cTrader M5 consumption failed: {result.error}")
    bars = tuple(cast(Iterable[object], getattr(result.value, "trendbar", ())))
    if len(bars) >= REQUEST_COUNT:
        raise RuntimeError("weekly M5 request reached provider count cap; refusing truncation")
    return bars


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _partition_quality(
    canonical_symbol: str,
    partition: Partition,
    bars: tuple[RawM5Bar, ...],
    *,
    identical_duplicates: int,
    contradictions: tuple[dict[str, Any], ...],
    alignment_errors: tuple[dict[str, Any], ...],
    out_of_window: tuple[dict[str, Any], ...],
) -> tuple[tuple[dict[str, Any], ...], int]:
    gaps = unresolved_gap_records(bars)
    records = contradictions + alignment_errors + out_of_window + gaps
    unresolved_slots = sum(
        int(item["calendar_slots_without_bars"])
        for item in gaps
        if item["kind"] == "UNRESOLVED_CLOSURE_OR_MISSING_DATA"
    )
    duplicate_record: tuple[dict[str, Any], ...] = ()
    if identical_duplicates:
        duplicate_record = (
            {
                "schema": QUALITY_SCHEMA,
                "identity": IDENTITY,
                "canonical_symbol": canonical_symbol,
                "partition": partition.label,
                "kind": "IDENTICAL_DUPLICATE_BAR",
                "count": identical_duplicates,
                "outcome_only": False,
            },
        )
    return duplicate_record + records, unresolved_slots


def _consume_partition(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    canonical_symbol: str,
    provider_symbol: str,
    provider_symbol_id: int,
    digits: int,
    pip_position: int | None,
    partition: Partition,
    output: Path,
) -> PartitionManifest:
    by_timestamp: dict[int, RawM5Bar] = {}
    identical_duplicates = 0
    contradictions: list[dict[str, Any]] = []
    alignment_errors: list[dict[str, Any]] = []
    out_of_window: list[dict[str, Any]] = []

    for index, (opened_at, closed_at) in enumerate(chunk_grid(partition)):
        native_bars = _read_chunk(
            client,
            account_id=account_id,
            symbol_id=provider_symbol_id,
            opened_at=opened_at,
            closed_at=closed_at,
            client_msg_id=(
                f"cibo-atlas-10y:{provider_symbol_id}:{partition.label}:{index}"
            ),
        )
        for native in native_bars:
            bar = _provider_bar(
                native,
                canonical_symbol=canonical_symbol,
                provider_symbol=provider_symbol,
                provider_symbol_id=provider_symbol_id,
                digits=digits,
                pip_position=pip_position,
            )
            bar_at = _bar_timestamp(native)
            if bar.utc_timestamp_in_minutes % PERIOD_M5 != 0:
                alignment_errors.append(
                    {
                        "schema": QUALITY_SCHEMA,
                        "identity": IDENTITY,
                        "canonical_symbol": canonical_symbol,
                        "partition": partition.label,
                        "kind": "TIMESTAMP_ALIGNMENT_ERROR",
                        "opened_at": bar.opened_at,
                        "outcome_only": False,
                    }
                )
                continue
            if not (partition.opened_at <= bar_at < partition.closed_at):
                out_of_window.append(
                    {
                        "schema": QUALITY_SCHEMA,
                        "identity": IDENTITY,
                        "canonical_symbol": canonical_symbol,
                        "partition": partition.label,
                        "kind": "OUT_OF_WINDOW_BAR",
                        "opened_at": bar.opened_at,
                        "outcome_only": False,
                    }
                )
                continue
            existing = by_timestamp.get(bar.utc_timestamp_in_minutes)
            if existing is None:
                by_timestamp[bar.utc_timestamp_in_minutes] = bar
                continue
            if existing.payload_identity() == bar.payload_identity():
                identical_duplicates += 1
                continue
            contradictions.append(
                {
                    "schema": QUALITY_SCHEMA,
                    "identity": IDENTITY,
                    "canonical_symbol": canonical_symbol,
                    "partition": partition.label,
                    "kind": "CONTRADICTORY_BAR",
                    "opened_at": bar.opened_at,
                    "first_payload": existing.payload_identity(),
                    "second_payload": bar.payload_identity(),
                    "outcome_only": False,
                }
            )

    bars = tuple(by_timestamp[key] for key in sorted(by_timestamp))
    quality_records, unresolved_slots = _partition_quality(
        canonical_symbol,
        partition,
        bars,
        identical_duplicates=identical_duplicates,
        contradictions=tuple(contradictions),
        alignment_errors=tuple(alignment_errors),
        out_of_window=tuple(out_of_window),
    )

    raw_path = output / "RAW_M5_LEDGER" / f"{partition.label}.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_path.open("w", encoding="utf-8") as handle:
        for bar in bars:
            handle.write(json.dumps(asdict(bar), sort_keys=True) + "\n")

    quality_path = output / "DATA_QUALITY_LEDGER" / f"{partition.label}.jsonl"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    with quality_path.open("w", encoding="utf-8") as handle:
        for record in quality_records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    integrity_status = (
        "CLEAN_PROVIDER_PAYLOAD"
        if not contradictions and not alignment_errors and not out_of_window
        else "FAILED_PROVIDER_PAYLOAD_INTEGRITY"
    )
    manifest = PartitionManifest(
        schema=f"{SCHEMA}.partition",
        identity=IDENTITY,
        canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol,
        provider_symbol_id=provider_symbol_id,
        digits=digits,
        pip_position=pip_position,
        partition=partition.label,
        requested_start=partition.opened_at.isoformat(),
        requested_end_exclusive=partition.closed_at.isoformat(),
        first_observed_m5=None if not bars else bars[0].opened_at,
        last_observed_m5=None if not bars else bars[-1].opened_at,
        retained_bars=len(bars),
        identical_duplicates=identical_duplicates,
        contradictory_bars=len(contradictions),
        timestamp_alignment_errors=len(alignment_errors),
        out_of_window_bars=len(out_of_window),
        unresolved_gap_runs=sum(
            item["kind"] == "UNRESOLVED_CLOSURE_OR_MISSING_DATA"
            for item in quality_records
        ),
        unresolved_calendar_slots=unresolved_slots,
        raw_integrity_status=integrity_status,
        session_adjusted_completeness=None,
        read_only=True,
        demo_eligible=False,
        live_authorized=False,
        real_capital_authorized=False,
        production_authorized=False,
    )
    manifest_path = output / "PARTITION_MANIFEST" / f"{partition.label}.json"
    _write_json(manifest_path, asdict(manifest))
    digest_path = output / "PARTITION_MANIFEST" / f"{partition.label}.sha256"
    digest_path.write_text(
        f"{_sha256(raw_path)}  {raw_path.relative_to(output)}\n"
        f"{_sha256(quality_path)}  {quality_path.relative_to(output)}\n"
        f"{_sha256(manifest_path)}  {manifest_path.relative_to(output)}\n"
    )
    return manifest


def _selected_symbol(
    client: SpotwareCTraderOpenApiClient,
    *,
    canonical_symbol: str,
) -> tuple[str, int, int, int | None]:
    provider_symbol = PROVIDER_SYMBOL_MAP[canonical_symbol]
    account_id = client.account_id
    listed = client.request(
        "ProtoOASymbolsListReq",
        {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
        client_msg_id="cibo-atlas-10y-symbol-list",
        timeout_seconds=30.0,
    )
    if isinstance(listed, Failure):
        raise RuntimeError(f"cTrader symbol discovery failed: {listed.error}")
    native_symbols = tuple(cast(Iterable[object], getattr(listed.value, "symbol", ())))
    selected = next(
        (
            item
            for item in native_symbols
            if getattr(item, "symbolName", None) == provider_symbol
            and getattr(item, "enabled", None) is True
        ),
        None,
    )
    if selected is None:
        raise RuntimeError(
            f"required provider symbol unavailable: {canonical_symbol}->{provider_symbol}"
        )
    symbol_id = _native_int(selected, "symbolId")
    details = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
        client_msg_id=f"cibo-atlas-10y-symbol:{symbol_id}",
        timeout_seconds=30.0,
    )
    if isinstance(details, Failure):
        raise RuntimeError(f"cTrader symbol details failed: {details.error}")
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
    return (
        provider_symbol,
        symbol_id,
        _native_int(detail, "digits"),
        _optional_native_int(detail, "pipPosition"),
    )


def consume_symbol(canonical_symbol: str, output: Path) -> SymbolConsumptionManifest:
    if canonical_symbol not in TARGET_SYMBOLS:
        raise ValueError(f"symbol outside frozen Atlas scope: {canonical_symbol}")
    output.mkdir(parents=True, exist_ok=True)
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits, pip_position = _selected_symbol(
            client, canonical_symbol=canonical_symbol
        )
        manifests = tuple(
            _consume_partition(
                client,
                account_id=client.account_id,
                canonical_symbol=canonical_symbol,
                provider_symbol=provider_symbol,
                provider_symbol_id=symbol_id,
                digits=digits,
                pip_position=pip_position,
                partition=partition,
                output=output,
            )
            for partition in partition_grid()
        )
    finally:
        client.close()

    observed = tuple(item for item in manifests if item.first_observed_m5 is not None)
    total_bars = sum(item.retained_bars for item in manifests)
    status = (
        "CLEAN_PROVIDER_PAYLOAD"
        if all(item.raw_integrity_status == "CLEAN_PROVIDER_PAYLOAD" for item in manifests)
        else "FAILED_PROVIDER_PAYLOAD_INTEGRITY"
    )
    manifest = SymbolConsumptionManifest(
        schema=f"{SCHEMA}.symbol",
        identity=IDENTITY,
        parent_identity=PARENT_IDENTITY,
        canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol,
        provider_symbol_id=symbol_id,
        digits=digits,
        pip_position=pip_position,
        target_start=TARGET_START.isoformat(),
        target_end_exclusive=TARGET_END_EXCLUSIVE.isoformat(),
        earliest_observed_m5=(None if not observed else observed[0].first_observed_m5),
        latest_observed_m5=(None if not observed else observed[-1].last_observed_m5),
        retained_bars=total_bars,
        partitions=tuple(asdict(item) for item in manifests),
        raw_integrity_status=status,
        expected_open_calendar_status="UNVERIFIED_PROVIDER_SESSION_CALENDAR",
        research_evidence_consumed=True,
        read_only=True,
        demo_eligible=False,
        live_authorized=False,
        real_capital_authorized=False,
        production_authorized=False,
    )
    _write_json(output / "symbol-consumption-manifest.json", asdict(manifest))
    return manifest


def manifest_paths(output: Path) -> Iterator[Path]:
    yield output / "symbol-consumption-manifest.json"
    yield from sorted((output / "PARTITION_MANIFEST").glob("*.json"))
    yield from sorted((output / "PARTITION_MANIFEST").glob("*.sha256"))


def write_root_hashes(output: Path) -> None:
    lines = [f"{_sha256(path)}  {path.relative_to(output)}" for path in manifest_paths(output)]
    (output / "MANIFEST_SHA256SUMS.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=TARGET_SYMBOLS)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = consume_symbol(args.symbol, args.output)
    write_root_hashes(args.output)
    print(json.dumps(asdict(manifest), sort_keys=True))
    if manifest.raw_integrity_status != "CLEAN_PROVIDER_PAYLOAD":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
