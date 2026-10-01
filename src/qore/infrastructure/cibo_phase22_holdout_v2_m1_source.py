"""Full source-only NAS100 M1 corpus for CIBO Phase22 V2 / VT31.

This collector stores provider-relative M1 rows for the active V2 interval.
It deliberately does not serialize them as the old 730-day VT31 evidence
schema, because that would misstate the actual six-month holdout span.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import sleep
from typing import cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    candidate_is_burn_clean_for_all_lineages,
)
from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import (
    cibo_market_atlas_10y_m5_consumer_v1 as base,
)
from qore.kernel.result import Failure

IDENTITY = "CIBO_PHASE22_HOLDOUT_V2_NAS100_M1_SOURCE_V1"
PERIOD_M1 = 1
CHUNK_DAYS = 2
MAX_CALENDAR_BARS_PER_CHUNK = CHUNK_DAYS * 24 * 60


@dataclass(frozen=True, slots=True)
class RawM1Bar:
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


def chunk_grid(
    start_at: datetime,
    end_exclusive_at: datetime,
) -> tuple[tuple[datetime, datetime], ...]:
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise CiboCapitalManagementError("M1 start must be timezone-aware")
    if end_exclusive_at.tzinfo is None or end_exclusive_at.utcoffset() is None:
        raise CiboCapitalManagementError("M1 end must be timezone-aware")
    if end_exclusive_at <= start_at:
        raise CiboCapitalManagementError("M1 source interval invalid")
    rows: list[tuple[datetime, datetime]] = []
    cursor = start_at
    while cursor < end_exclusive_at:
        closed_at = min(cursor + timedelta(days=CHUNK_DAYS), end_exclusive_at)
        rows.append((cursor, closed_at))
        cursor = closed_at
    return tuple(rows)


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


def _raw_bar(
    native: object,
    *,
    provider_symbol: str,
    provider_symbol_id: int,
    digits: int,
    pip_position: int | None,
) -> RawM1Bar:
    low = _native_int(native, "low")
    delta_open = _native_int(native, "deltaOpen")
    delta_high = _native_int(native, "deltaHigh")
    delta_close = _native_int(native, "deltaClose")
    timestamp_minutes = _native_int(native, "utcTimestampInMinutes")
    if low <= 0 or min(delta_open, delta_high, delta_close, timestamp_minutes) < 0:
        raise CiboCapitalManagementError("invalid provider-relative M1 payload")
    if delta_open > delta_high or delta_close > delta_high:
        raise CiboCapitalManagementError("provider M1 open/close exceeds high")
    opened_at = datetime.fromtimestamp(timestamp_minutes * 60, tz=UTC)
    return RawM1Bar(
        canonical_symbol="NAS100",
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
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
    label: str,
) -> tuple[object, ...]:
    sleep(base.REQUEST_PAUSE_SECONDS)
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": PERIOD_M1,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=f"cibo-phase22-v2-m1:{label}",
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"cTrader V2 M1 consumption failed: {result.error}")
    rows = tuple(cast(Iterable[object], getattr(result.value, "trendbar", ())))
    if len(rows) > MAX_CALENDAR_BARS_PER_CHUNK:
        raise RuntimeError("provider returned more M1 rows than calendar permits")
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_nas100_m1(output: Path) -> dict[str, object]:
    candidate = ACTIVE_USD60_HOLDOUT_CANDIDATE
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError("V2 M1 source requires burn-clean holdout")
    output.mkdir(parents=True, exist_ok=True)

    client = SpotwareCTraderOpenApiClient(credentials=base._credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits, pip_position = base._selected_symbol(
            client,
            canonical_symbol="NAS100",
        )
        by_timestamp: dict[int, RawM1Bar] = {}
        identical_duplicates = 0
        for index, (opened_at, closed_at) in enumerate(
            chunk_grid(candidate.start_at, candidate.end_exclusive_at)
        ):
            for native in _read_chunk(
                client,
                symbol_id=symbol_id,
                opened_at=opened_at,
                closed_at=closed_at,
                label=str(index),
            ):
                bar = _raw_bar(
                    native,
                    provider_symbol=provider_symbol,
                    provider_symbol_id=symbol_id,
                    digits=digits,
                    pip_position=pip_position,
                )
                at = datetime.fromisoformat(bar.opened_at)
                if not candidate.start_at <= at < candidate.end_exclusive_at:
                    raise CiboCapitalManagementError(
                        "M1 provider row outside V2 window"
                    )
                existing = by_timestamp.get(bar.utc_timestamp_in_minutes)
                if existing is None:
                    by_timestamp[bar.utc_timestamp_in_minutes] = bar
                elif existing.payload_identity() == bar.payload_identity():
                    identical_duplicates += 1
                else:
                    raise CiboCapitalManagementError(
                        "contradictory duplicate M1 row"
                    )
    finally:
        client.close()

    bars = tuple(by_timestamp[key] for key in sorted(by_timestamp))
    if not bars:
        raise CiboCapitalManagementError("V2 NAS100 M1 corpus is empty")

    raw_path = output / "RAW_M1_LEDGER" / "holdout-v2.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_path.open("w", encoding="utf-8") as handle:
        for bar in bars:
            handle.write(json.dumps(asdict(bar), sort_keys=True) + "\n")

    manifest = {
        "schema": "qore.cibo.phase22.holdout-v2-nas100-m1-source.v1",
        "identity": IDENTITY,
        "candidate_id": candidate.candidate_id,
        "canonical_symbol": "NAS100",
        "provider_symbol": provider_symbol,
        "provider_symbol_id": symbol_id,
        "digits": digits,
        "pip_position": pip_position,
        "period_minutes": PERIOD_M1,
        "window": {
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
        },
        "retained_bars": len(bars),
        "first_observed_m1": bars[0].opened_at,
        "last_observed_m1": bars[-1].opened_at,
        "identical_duplicates": identical_duplicates,
        "raw_sha256": _sha256(raw_path),
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "productive_authority": False,
    }
    manifest_path = output / "phase22-v2-nas100-m1-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "SHA256SUMS.txt").write_text(
        f"{_sha256(raw_path)}  {raw_path.relative_to(output)}\n"
        f"{_sha256(manifest_path)}  {manifest_path.relative_to(output)}\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(collect_nas100_m1(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
