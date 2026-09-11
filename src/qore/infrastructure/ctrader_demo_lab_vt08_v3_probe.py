"""Two-year read-only cTrader DEMO evidence for VT-08 CRT 1-5-9 V3.

V3 needs retained M15 for H4/H1/M15 nesting plus provider D1 context. Broker
symbol resolution is inherited from the explicit 11-market VT-08 V2 resolver;
no fuzzy alias inference is introduced here.

The generic Lab closed-trendbar contract intentionally remains M1/M5/M15/H4.
Provider D1 is parsed into a V3-private immutable bar so this research adapter
can request native D1 (period 12) without silently widening the shared collector.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Protocol, cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _CHUNK_DAYS,
    _HISTORICAL_PAGE_COUNT,
    _HISTORICAL_REQUEST_PAUSE_SECONDS,
    _collect_period_window,
    _native_int,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
    CTraderDemoLabSymbolEvidence,
    _normalized_price,
)
from qore.infrastructure.ctrader_demo_lab_vt08_v2_probe import (
    _PROVIDER_ROOTS,
    _connect_and_resolve,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_SCHEMA = "qore.ctrader_demo.vt08_crt_159_v3_evidence.v1"
_REQUIRED_COVERAGE_DAYS = 730
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_RECENT_TOLERANCE_DAYS = 10
_NATIVE_M15_PERIOD = 7
_M15_SECONDS = 900
_NATIVE_D1_PERIOD = 12
_D1_SECONDS = 86_400
_PRIMARY_SOURCE_SHA256 = (
    "9968f10cee6b5c94d7406c3cdc31bef2623221a5a6e6529f7b4293c1bbe97664",
    "fceacd2b59039bc94aea3b7390804c1c68f1ac10b1e7bc3e318a7645d867a5ee",
    "57206b5c3e48a2281b4648da7c69b1c20c39ea5c1edd34c689a1a9080341c225",
)


class _HistoricalBar(Protocol):
    opened_at: datetime
    closed_at: datetime

    def payload(self) -> dict[str, str]: ...


@dataclass(frozen=True, slots=True)
class _Vt08V3DailyBar:
    opened_at: datetime
    closed_at: datetime
    open: str
    high: str
    low: str
    close: str

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise CTraderDemoLabProbeError("VT-08 V3 D1 opened_at must be aware")
        if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
            raise CTraderDemoLabProbeError("VT-08 V3 D1 closed_at must be aware")
        if self.closed_at <= self.opened_at:
            raise CTraderDemoLabProbeError("VT-08 V3 D1 close must follow open")

    def payload(self) -> dict[str, str]:
        return {
            "period": "D1",
            "opened_at": self.opened_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "closed_at": self.closed_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }


def _validate_period(
    name: str,
    bars: tuple[_HistoricalBar, ...],
    *,
    opened_at: datetime,
    checked_at: datetime,
) -> None:
    if not bars:
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} evidence is empty"
        )
    first = bars[0].opened_at
    last = bars[-1].closed_at
    if last - first < timedelta(days=_REQUIRED_COVERAGE_DAYS):
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} spans less than 730 days"
        )
    if first < opened_at:
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} predates requested boundary"
        )
    if last < checked_at - timedelta(days=_RECENT_TOLERANCE_DAYS):
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} evidence is stale"
        )


def _parse_d1_bar(
    native: object,
    *,
    digits: int,
    checked_at: datetime,
) -> _Vt08V3DailyBar | None:
    low_relative = _native_int(native, "low")
    delta_open = _native_int(native, "deltaOpen")
    delta_high = _native_int(native, "deltaHigh")
    delta_close = _native_int(native, "deltaClose")
    opened_minutes = _native_int(native, "utcTimestampInMinutes")
    bar_opened = datetime.fromtimestamp(opened_minutes * 60, tz=UTC)
    bar_closed = bar_opened + timedelta(seconds=_D1_SECONDS)
    if bar_closed > checked_at:
        return None
    return _Vt08V3DailyBar(
        opened_at=bar_opened,
        closed_at=bar_closed,
        open=_normalized_price(low_relative + delta_open, digits=digits),
        high=_normalized_price(low_relative + delta_high, digits=digits),
        low=_normalized_price(low_relative, digits=digits),
        close=_normalized_price(low_relative + delta_close, digits=digits),
    )


def _collect_d1_window(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    account_id: int,
    symbol: CTraderDemoLabSymbolEvidence,
    opened_at: datetime,
    checked_at: datetime,
    window_index: int,
    timeout_seconds: float,
) -> tuple[_Vt08V3DailyBar, ...]:
    cursor_end = checked_at
    retained: dict[datetime, _Vt08V3DailyBar] = {}
    page_index = 0
    while cursor_end > opened_at:
        sleep(_HISTORICAL_REQUEST_PAUSE_SECONDS)
        response = client.request(
            "ProtoOAGetTrendbarsReq",
            {
                "ctidTraderAccountId": account_id,
                "count": _HISTORICAL_PAGE_COUNT,
                "fromTimestamp": int(opened_at.timestamp() * 1000),
                "period": _NATIVE_D1_PERIOD,
                "symbolId": symbol.symbol_id,
                "toTimestamp": int(cursor_end.timestamp() * 1000),
            },
            client_msg_id=(
                f"qore-vt08-v3-d1:{symbol.symbol_id}:"
                f"{window_index}:{page_index}"
            ),
            timeout_seconds=timeout_seconds,
        )
        if isinstance(response, Failure):
            raise CTraderDemoLabProbeError("cTrader DEMO D1 trendbar read failed")
        native_bars = getattr(response.value, "trendbar", None)
        if native_bars is None:
            raise CTraderDemoLabProbeError(
                "cTrader DEMO D1 trendbar response is missing bars"
            )
        page: list[_Vt08V3DailyBar] = []
        for native in cast(tuple[object, ...], tuple(native_bars)):
            parsed = _parse_d1_bar(
                native,
                digits=symbol.digits,
                checked_at=checked_at,
            )
            if parsed is None or parsed.opened_at < opened_at:
                continue
            existing = retained.get(parsed.opened_at)
            if existing is not None and existing != parsed:
                raise CTraderDemoLabProbeError(
                    "cTrader D1 pages contradict on the same trendbar"
                )
            retained[parsed.opened_at] = parsed
            page.append(parsed)
        has_more = getattr(response.value, "hasMore", False)
        if type(has_more) is not bool:
            raise CTraderDemoLabProbeError("cTrader D1 hasMore must be bool")
        if not page:
            if has_more:
                raise CTraderDemoLabProbeError(
                    "cTrader D1 pagination reported more data without progress"
                )
            break
        earliest = min(item.opened_at for item in page)
        if not has_more or earliest <= opened_at:
            break
        next_end = earliest - timedelta(milliseconds=1)
        if next_end >= cursor_end:
            raise CTraderDemoLabProbeError(
                "cTrader D1 pagination failed to move backward"
            )
        cursor_end = next_end
        page_index += 1
        if page_index > 10_000:
            raise CTraderDemoLabProbeError(
                "cTrader D1 pagination exceeded safe bound"
            )
    return tuple(retained[key] for key in sorted(retained))


def _collect_m15_history(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    account_id: int,
    symbol: CTraderDemoLabSymbolEvidence,
    opened: datetime,
    checked: datetime,
    timeout_seconds: float,
) -> tuple[CTraderDemoLabClosedTrendbar, ...]:
    retained: dict[datetime, CTraderDemoLabClosedTrendbar] = {}
    cursor = opened
    window_index = 0
    while cursor < checked:
        window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
        bars = _collect_period_window(
            client,
            account_id=account_id,
            symbol=symbol,
            period_name="M15",
            native_period=_NATIVE_M15_PERIOD,
            seconds=_M15_SECONDS,
            opened_at=cursor,
            checked_at=window_end,
            window_index=window_index,
            timeout_seconds=timeout_seconds,
        )
        for bar in bars:
            existing = retained.get(bar.opened_at)
            if existing is not None and existing != bar:
                raise CTraderDemoLabProbeError(
                    "VT-08 V3 M15 acquisition windows contradict on one bar"
                )
            retained[bar.opened_at] = bar
        cursor = window_end
        window_index += 1
    return tuple(retained[key] for key in sorted(retained))


def _collect_d1_history(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    account_id: int,
    symbol: CTraderDemoLabSymbolEvidence,
    opened: datetime,
    checked: datetime,
    timeout_seconds: float,
) -> tuple[_Vt08V3DailyBar, ...]:
    retained: dict[datetime, _Vt08V3DailyBar] = {}
    cursor = opened
    window_index = 0
    while cursor < checked:
        window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
        bars = _collect_d1_window(
            client,
            account_id=account_id,
            symbol=symbol,
            opened_at=cursor,
            checked_at=window_end,
            window_index=window_index,
            timeout_seconds=timeout_seconds,
        )
        for bar in bars:
            existing = retained.get(bar.opened_at)
            if existing is not None and existing != bar:
                raise CTraderDemoLabProbeError(
                    "VT-08 V3 D1 acquisition windows contradict on one bar"
                )
            retained[bar.opened_at] = bar
        cursor = window_end
        window_index += 1
    return tuple(retained[key] for key in sorted(retained))


def _coverage_payload(bars: tuple[_HistoricalBar, ...]) -> dict[str, object]:
    return {
        "bar_count": len(bars),
        "first_opened_at": bars[0].opened_at.isoformat(timespec="microseconds"),
        "last_closed_at": bars[-1].closed_at.isoformat(timespec="microseconds"),
        "span_seconds": int(
            (bars[-1].closed_at - bars[0].opened_at).total_seconds()
        ),
    }


def collect_vt08_v3_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    canonical_symbol: str,
    requested_opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> dict[str, object]:
    if canonical_symbol not in _PROVIDER_ROOTS:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 market is outside Core 11-market set"
        )
    if requested_opened_at.tzinfo is None or checked_at.tzinfo is None:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 acquisition timestamps must be aware"
        )
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 acquisition start must predate end"
        )
    (
        account_id,
        account_fingerprint,
        symbol,
        provider_symbol,
    ) = _connect_and_resolve(
        client,
        canonical_symbol=canonical_symbol,
        timeout_seconds=timeout_seconds,
    )
    m15 = _collect_m15_history(
        client,
        account_id=account_id,
        symbol=symbol,
        opened=opened,
        checked=checked,
        timeout_seconds=timeout_seconds,
    )
    d1 = _collect_d1_history(
        client,
        account_id=account_id,
        symbol=symbol,
        opened=opened,
        checked=checked,
        timeout_seconds=timeout_seconds,
    )
    _validate_period("M15", m15, opened_at=opened, checked_at=checked)
    _validate_period("D1", d1, opened_at=opened, checked_at=checked)
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": account_fingerprint,
        "symbol": symbol.payload(),
        "canonical_symbol": canonical_symbol,
        "provider_symbol_name": provider_symbol,
        "checked_at": checked.isoformat(timespec="microseconds"),
        "requested_opened_at": opened.isoformat(timespec="microseconds"),
        "required_coverage_days": _REQUIRED_COVERAGE_DAYS,
        "historical_chunk_days": _CHUNK_DAYS,
        "historical_page_count": _HISTORICAL_PAGE_COUNT,
        "primary_source_sha256": list(_PRIMARY_SOURCE_SHA256),
        "decision_timeframe": "M15",
        "context_timeframes": [
            "D1-provider-native",
            "H4-derived-M15",
            "H1-derived-M15",
            "M15",
        ],
        "source_clock": {
            "timezone": "America/New_York",
            "h4_reference_open": "01:00",
            "h4_manipulation_open": "05:00",
            "h4_distribution_open": "09:00",
            "h1_reference_open": "09:00",
            "h1_manipulation_open": "10:00",
            "m15_reference_open": "11:00",
            "m15_manipulation_open": "11:15",
            "entry_open": "11:30",
            "distribution_expiry": "13:00",
        },
        "coverage": {
            "M15": _coverage_payload(m15),
            "D1": _coverage_payload(d1),
        },
        "periods": {
            "M15": [bar.payload() for bar in m15],
            "D1": [bar.payload() for bar in d1],
        },
    }


def main() -> None:
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
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError(
            "QORE_SOFTWARE_SHA must be exact Git SHA"
        )
    canonical_symbol = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = int(
        os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "760")
    )
    if not _MIN_LOOKBACK_DAYS <= lookback_days <= _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 lookback must be 730..1095 days"
        )
    checked_at = datetime.now(UTC)
    opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt08_v3_evidence(
            client,
            canonical_symbol=canonical_symbol,
            requested_opened_at=opened_at,
            checked_at=checked_at,
        )
        payload["requested_lookback_days"] = lookback_days
        payload["software_sha"] = software_sha
        print(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
