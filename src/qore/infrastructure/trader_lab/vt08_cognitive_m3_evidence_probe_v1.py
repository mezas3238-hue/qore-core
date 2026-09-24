"""Collect M3-only DEMO evidence over the exact immutable 1095D window.

The shared long-horizon Lab DTO intentionally supports the historical
M1/M5/M15/H4 contract only. This research-local adapter reads native cTrader M3
trendbars directly so the shared certified collector is not broadened.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Final, cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _CHUNK_DAYS,
    _HISTORICAL_PAGE_COUNT,
    _HISTORICAL_REQUEST_PAUSE_SECONDS,
    _connect_and_resolve_symbol,
    _native_int,
    _normalized_price,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabSymbolEvidence
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

PERIOD_NAME: Final = "M3"
NATIVE_PERIOD: Final = 3
PERIOD_SECONDS: Final = 180
MIN_SPAN_DAYS: Final = 1080


@dataclass(frozen=True, slots=True)
class M3ClosedBar:
    opened_at: datetime
    closed_at: datetime
    open: str
    high: str
    low: str
    close: str

    def payload(self) -> dict[str, str]:
        return {
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }


def _aware_env(name: str) -> datetime:
    raw = _required_env(name)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _parse_native_m3(
    native: object,
    *,
    digits: int,
    checked_at: datetime,
) -> M3ClosedBar | None:
    low_relative = _native_int(native, "low")
    delta_open = _native_int(native, "deltaOpen")
    delta_high = _native_int(native, "deltaHigh")
    delta_close = _native_int(native, "deltaClose")
    opened_minutes = _native_int(native, "utcTimestampInMinutes")
    opened_at = datetime.fromtimestamp(opened_minutes * 60, tz=UTC)
    closed_at = opened_at + timedelta(seconds=PERIOD_SECONDS)
    if closed_at > checked_at:
        return None
    return M3ClosedBar(
        opened_at=opened_at,
        closed_at=closed_at,
        open=_normalized_price(low_relative + delta_open, digits=digits),
        high=_normalized_price(low_relative + delta_high, digits=digits),
        low=_normalized_price(low_relative, digits=digits),
        close=_normalized_price(low_relative + delta_close, digits=digits),
    )


def _collect_m3_window(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    account_id: int,
    symbol: CTraderDemoLabSymbolEvidence,
    opened_at: datetime,
    checked_at: datetime,
    window_index: int,
    timeout_seconds: float,
) -> tuple[M3ClosedBar, ...]:
    cursor_end = checked_at
    retained: dict[datetime, M3ClosedBar] = {}
    page_index = 0
    while cursor_end > opened_at:
        sleep(_HISTORICAL_REQUEST_PAUSE_SECONDS)
        response = client.request(
            "ProtoOAGetTrendbarsReq",
            {
                "ctidTraderAccountId": account_id,
                "count": _HISTORICAL_PAGE_COUNT,
                "fromTimestamp": int(opened_at.timestamp() * 1000),
                "period": NATIVE_PERIOD,
                "symbolId": symbol.symbol_id,
                "toTimestamp": int(cursor_end.timestamp() * 1000),
            },
            client_msg_id=(
                f"qore-vt08-m3:{symbol.symbol_id}:{window_index}:{page_index}"
            ),
            timeout_seconds=timeout_seconds,
        )
        if isinstance(response, Failure):
            raise ValueError("cTrader DEMO M3 trendbar read failed")
        native_bars = getattr(response.value, "trendbar", None)
        if native_bars is None:
            raise ValueError("cTrader DEMO M3 trendbar response is missing bars")

        page: list[M3ClosedBar] = []
        for native in cast(tuple[object, ...], tuple(native_bars)):
            parsed = _parse_native_m3(
                native,
                digits=symbol.digits,
                checked_at=checked_at,
            )
            if parsed is None or parsed.opened_at < opened_at:
                continue
            existing = retained.get(parsed.opened_at)
            if existing is not None and existing != parsed:
                raise ValueError("M3 historical pages contradict on same open")
            retained[parsed.opened_at] = parsed
            page.append(parsed)

        has_more = getattr(response.value, "hasMore", False)
        if type(has_more) is not bool:
            raise ValueError("cTrader M3 hasMore must be bool")
        if not page:
            if has_more:
                raise ValueError("M3 pagination reported more data without progress")
            break
        earliest = min(item.opened_at for item in page)
        if not has_more or earliest <= opened_at:
            break
        next_end = earliest - timedelta(milliseconds=1)
        if next_end >= cursor_end:
            raise ValueError("M3 pagination failed to move backward")
        cursor_end = next_end
        page_index += 1
        if page_index > 10_000:
            raise ValueError("M3 pagination exceeded safe bound")

    return tuple(retained[key] for key in sorted(retained))


def collect_m3_payload() -> dict[str, object]:
    symbol_name = _required_env("QORE_DEMO_LAB_SYMBOL")
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise ValueError("QORE_SOFTWARE_SHA must be exact lowercase Git SHA")
    opened = _aware_env("QORE_M3_REQUESTED_OPENED_AT")
    checked = _aware_env("QORE_M3_CHECKED_AT")
    if opened >= checked:
        raise ValueError("M3 requested boundary must predate checked boundary")

    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID",
            "QORE_CTRADER_DEMO_CLIENT_ID",
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID",
                "QORE_CTRADER_ACCOUNT_ID",
            )
        ),
    )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        account_id, fingerprint, symbol = _connect_and_resolve_symbol(
            client,
            symbol_name=symbol_name,
            timeout_seconds=15.0,
        )
        retained: dict[datetime, M3ClosedBar] = {}
        cursor = opened
        window_index = 0
        while cursor < checked:
            window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
            bars = _collect_m3_window(
                client,
                account_id=account_id,
                symbol=symbol,
                opened_at=cursor,
                checked_at=window_end,
                window_index=window_index,
                timeout_seconds=15.0,
            )
            for bar in bars:
                existing = retained.get(bar.opened_at)
                if existing is not None and existing != bar:
                    raise ValueError("M3 windows contradict on same open")
                retained[bar.opened_at] = bar
            cursor = window_end
            window_index += 1
    finally:
        client.close()

    ordered = tuple(retained[key] for key in sorted(retained))
    if not ordered:
        raise ValueError("M3 collection returned no bars")
    if ordered[-1].closed_at - ordered[0].opened_at < timedelta(days=MIN_SPAN_DAYS):
        raise ValueError("M3 actual span is shorter than frozen 1095D profile contract")
    if ordered[0].opened_at < opened:
        raise ValueError("M3 evidence predates requested immutable boundary")
    if ordered[-1].closed_at < checked - timedelta(days=10):
        raise ValueError("M3 evidence is stale at recent boundary")

    return {
        "schema": "qore.trader_lab.vt08.m3_evidence.v1",
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "account_fingerprint": fingerprint,
        "symbol": {
            "symbol_name": symbol.symbol_name,
            "digits": symbol.digits,
        },
        "software_sha": software_sha,
        "requested_opened_at": opened.isoformat(),
        "checked_at": checked.isoformat(),
        "period": PERIOD_NAME,
        "native_period": NATIVE_PERIOD,
        "period_seconds": PERIOD_SECONDS,
        "bar_count": len(ordered),
        "first_opened_at": ordered[0].opened_at.isoformat(),
        "last_closed_at": ordered[-1].closed_at.isoformat(),
        "bars": [item.payload() for item in ordered],
        "strategy_replay_performed": False,
    }


def main() -> None:
    print(json.dumps(collect_m3_payload(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
