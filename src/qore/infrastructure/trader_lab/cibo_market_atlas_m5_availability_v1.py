"""CIBO Market Atlas V1 — provider M5 availability discovery.

Research-only. Discovers the deepest verified M5 history exposed by cTrader DEMO
for the frozen atlas universe. It does not infer missing data, trade, or mutate
any trader. All outputs are manifests for later GitHub Actions atlas stages.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable
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

IDENTITY = "CIBO_MARKET_ATLAS_20Y_V1"
SCHEMA = "qore.cibo_market_atlas.m5_availability.v1"
FROZEN_CLOSE = datetime(2026, 9, 16, 23, 59, tzinfo=UTC)
PROBE_FLOOR = datetime(1970, 1, 1, tzinfo=UTC)
PERIOD_M5 = 5
REQUEST_PAUSE_SECONDS = 0.20
TARGET_SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
    "NAS100",
    "SP500",
    "US30",
    "XAUUSD",
    "XAGUSD",
)


@dataclass(frozen=True, slots=True)
class ProbeWindow:
    opened_at: datetime
    closed_at: datetime
    has_data: bool
    first_bar_at: datetime | None
    last_bar_at: datetime | None
    returned_bars: int


@dataclass(frozen=True, slots=True)
class AvailabilityManifest:
    schema: str
    identity: str
    symbol_requested: str
    symbol_status: str
    provider_symbol_name: str | None
    provider_symbol_id: int | None
    digits: int | None
    probe_floor: str
    frozen_close: str
    earliest_verified_m5: str | None
    latest_verified_m5: str | None
    earliest_verified_month: str | None
    yearly_probe_count: int
    monthly_probe_count: int
    months_with_data: int
    months_without_data_after_first_observation: int
    observed_years: tuple[int, ...]
    contiguous_from_earliest_month: bool | None
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


def _month_start(value: datetime) -> datetime:
    return datetime(value.year, value.month, 1, tzinfo=UTC)


def _next_month(value: datetime) -> datetime:
    if value.month == 12:
        return datetime(value.year + 1, 1, 1, tzinfo=UTC)
    return datetime(value.year, value.month + 1, 1, tzinfo=UTC)


def _year_start(value: datetime) -> datetime:
    return datetime(value.year, 1, 1, tzinfo=UTC)


def month_grid(start: datetime, end: datetime) -> tuple[tuple[datetime, datetime], ...]:
    cursor = _month_start(start)
    result: list[tuple[datetime, datetime]] = []
    while cursor < end:
        nxt = min(_next_month(cursor), end)
        result.append((cursor, nxt))
        cursor = _next_month(cursor)
    return tuple(result)


def year_grid(start: datetime, end: datetime) -> tuple[tuple[datetime, datetime], ...]:
    cursor = _year_start(start)
    result: list[tuple[datetime, datetime]] = []
    while cursor < end:
        nxt = min(datetime(cursor.year + 1, 1, 1, tzinfo=UTC), end)
        result.append((cursor, nxt))
        cursor = datetime(cursor.year + 1, 1, 1, tzinfo=UTC)
    return tuple(result)


def first_contiguous_month(windows: tuple[ProbeWindow, ...]) -> datetime | None:
    observed = [index for index, item in enumerate(windows) if item.has_data]
    if not observed:
        return None
    for start in observed:
        if all(item.has_data for item in windows[start:]):
            return windows[start].opened_at
    return None


def _native_int(value: object, name: str) -> int:
    raw = getattr(value, name)
    if type(raw) is not int:
        raise TypeError(f"{name} must be int")
    return raw


def _bar_timestamp(native: object) -> datetime:
    return datetime.fromtimestamp(_native_int(native, "utcTimestampInMinutes") * 60, tz=UTC)


def _probe_window(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
    client_msg_id: str,
) -> ProbeWindow:
    sleep(REQUEST_PAUSE_SECONDS)
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": account_id,
            "count": 10,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": PERIOD_M5,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000),
        },
        client_msg_id=client_msg_id,
        timeout_seconds=45.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"cTrader M5 availability probe failed: {result.error}")
    bars = tuple(cast(Iterable[object], getattr(result.value, "trendbar", ())))
    timestamps = tuple(sorted(_bar_timestamp(item) for item in bars))
    return ProbeWindow(
        opened_at=opened_at,
        closed_at=closed_at,
        has_data=bool(timestamps),
        first_bar_at=timestamps[0] if timestamps else None,
        last_bar_at=timestamps[-1] if timestamps else None,
        returned_bars=len(timestamps),
    )


def _refine_first_day(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    month_open: datetime,
    month_close: datetime,
) -> datetime | None:
    cursor = month_open
    index = 0
    while cursor < month_close:
        nxt = min(cursor + timedelta(days=1), month_close)
        window = _probe_window(
            client,
            account_id=account_id,
            symbol_id=symbol_id,
            opened_at=cursor,
            closed_at=nxt,
            client_msg_id=f"atlas-first-day:{symbol_id}:{index}",
        )
        if window.first_bar_at is not None:
            return window.first_bar_at
        cursor = nxt
        index += 1
    return None


def _unavailable_manifest(symbol_name: str) -> AvailabilityManifest:
    return AvailabilityManifest(
        schema=SCHEMA,
        identity=IDENTITY,
        symbol_requested=symbol_name,
        symbol_status="UNAVAILABLE_EXACT_SYMBOL",
        provider_symbol_name=None,
        provider_symbol_id=None,
        digits=None,
        probe_floor=PROBE_FLOOR.isoformat(),
        frozen_close=FROZEN_CLOSE.isoformat(),
        earliest_verified_m5=None,
        latest_verified_m5=None,
        earliest_verified_month=None,
        yearly_probe_count=0,
        monthly_probe_count=0,
        months_with_data=0,
        months_without_data_after_first_observation=0,
        observed_years=(),
        contiguous_from_earliest_month=None,
        read_only=True,
        demo_eligible=False,
        live_authorized=False,
        real_capital_authorized=False,
        production_authorized=False,
    )


def discover_symbol(symbol_name: str) -> tuple[AvailabilityManifest, tuple[ProbeWindow, ...]]:
    if symbol_name not in TARGET_SYMBOLS:
        raise ValueError(f"symbol outside frozen atlas scope: {symbol_name}")
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        account_id = client.account_id
        listed = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
            client_msg_id="cibo-atlas-symbol-list",
            timeout_seconds=30.0,
        )
        if isinstance(listed, Failure):
            raise RuntimeError(f"cTrader symbol discovery failed: {listed.error}")
        native_symbols = tuple(cast(Iterable[object], getattr(listed.value, "symbol", ())))
        selected = next(
            (
                item
                for item in native_symbols
                if getattr(item, "symbolName", None) == symbol_name
                and getattr(item, "enabled", None) is True
            ),
            None,
        )
        if selected is None:
            return _unavailable_manifest(symbol_name), ()

        symbol_id = _native_int(selected, "symbolId")
        details = client.request(
            "ProtoOASymbolByIdReq",
            {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
            client_msg_id=f"cibo-atlas-symbol:{symbol_id}",
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
            raise RuntimeError("exact symbol details missing")
        digits = _native_int(detail, "digits")

        yearly_windows = tuple(
            _probe_window(
                client,
                account_id=account_id,
                symbol_id=symbol_id,
                opened_at=opened,
                closed_at=closed,
                client_msg_id=f"cibo-atlas-year:{symbol_id}:{index}",
            )
            for index, (opened, closed) in enumerate(year_grid(PROBE_FLOOR, FROZEN_CLOSE))
        )
        observed_year_windows = tuple(item for item in yearly_windows if item.has_data)
        if not observed_year_windows:
            manifest = AvailabilityManifest(
                schema=SCHEMA,
                identity=IDENTITY,
                symbol_requested=symbol_name,
                symbol_status="NO_M5_HISTORY_OBSERVED",
                provider_symbol_name=str(getattr(selected, "symbolName")),
                provider_symbol_id=symbol_id,
                digits=digits,
                probe_floor=PROBE_FLOOR.isoformat(),
                frozen_close=FROZEN_CLOSE.isoformat(),
                earliest_verified_m5=None,
                latest_verified_m5=None,
                earliest_verified_month=None,
                yearly_probe_count=len(yearly_windows),
                monthly_probe_count=0,
                months_with_data=0,
                months_without_data_after_first_observation=0,
                observed_years=(),
                contiguous_from_earliest_month=None,
                read_only=True,
                demo_eligible=False,
                live_authorized=False,
                real_capital_authorized=False,
                production_authorized=False,
            )
            return manifest, ()

        first_year_open = observed_year_windows[0].opened_at
        monthly_windows = tuple(
            _probe_window(
                client,
                account_id=account_id,
                symbol_id=symbol_id,
                opened_at=opened,
                closed_at=closed,
                client_msg_id=f"cibo-atlas-month:{symbol_id}:{index}",
            )
            for index, (opened, closed) in enumerate(month_grid(first_year_open, FROZEN_CLOSE))
        )
        observed = tuple(item for item in monthly_windows if item.has_data)
        earliest_month = observed[0].opened_at if observed else None
        earliest = (
            _refine_first_day(
                client,
                account_id=account_id,
                symbol_id=symbol_id,
                month_open=observed[0].opened_at,
                month_close=observed[0].closed_at,
            )
            if observed
            else None
        )
        latest = observed[-1].last_bar_at if observed else None
        first_observed_index = next(
            (index for index, item in enumerate(monthly_windows) if item.has_data), None
        )
        missing_after = (
            sum(not item.has_data for item in monthly_windows[first_observed_index:])
            if first_observed_index is not None
            else 0
        )
        contiguous = first_contiguous_month(monthly_windows)
        manifest = AvailabilityManifest(
            schema=SCHEMA,
            identity=IDENTITY,
            symbol_requested=symbol_name,
            symbol_status="AVAILABLE" if observed else "NO_M5_HISTORY_OBSERVED",
            provider_symbol_name=str(getattr(selected, "symbolName")),
            provider_symbol_id=symbol_id,
            digits=digits,
            probe_floor=PROBE_FLOOR.isoformat(),
            frozen_close=FROZEN_CLOSE.isoformat(),
            earliest_verified_m5=None if earliest is None else earliest.isoformat(),
            latest_verified_m5=None if latest is None else latest.isoformat(),
            earliest_verified_month=None if earliest_month is None else earliest_month.isoformat(),
            yearly_probe_count=len(yearly_windows),
            monthly_probe_count=len(monthly_windows),
            months_with_data=len(observed),
            months_without_data_after_first_observation=missing_after,
            observed_years=tuple(sorted({item.opened_at.year for item in observed})),
            contiguous_from_earliest_month=(
                contiguous == earliest_month if earliest_month is not None else None
            ),
            read_only=True,
            demo_eligible=False,
            live_authorized=False,
            real_capital_authorized=False,
            production_authorized=False,
        )
        return manifest, monthly_windows
    finally:
        client.close()


def write_manifest(symbol_name: str, output: Path) -> dict[str, Any]:
    manifest, windows = discover_symbol(symbol_name)
    output.mkdir(parents=True, exist_ok=True)
    payload = asdict(manifest)
    (output / "availability.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "monthly-probes.json").write_text(
        json.dumps(
            [
                {
                    "opened_at": item.opened_at.isoformat(),
                    "closed_at": item.closed_at.isoformat(),
                    "has_data": item.has_data,
                    "first_bar_at": None
                    if item.first_bar_at is None
                    else item.first_bar_at.isoformat(),
                    "last_bar_at": None
                    if item.last_bar_at is None
                    else item.last_bar_at.isoformat(),
                    "returned_bars": item.returned_bars,
                }
                for item in windows
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=TARGET_SYMBOLS)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = write_manifest(args.symbol, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
