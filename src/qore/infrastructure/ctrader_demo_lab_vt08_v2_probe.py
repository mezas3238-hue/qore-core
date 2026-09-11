"""Read-only cTrader DEMO evidence for reconstructed VT-08 H4 PO3 V2.

The falsified first V2 campaign retained only M15 and therefore could not bind
intraday expansion to a completed daily bias.  The reconstructed collector keeps
M15 plus provider-native D1, while preserving canonical Core market identity and
explicit fail-closed provider alias resolution.

The shared Lab trendbar contract remains unchanged. D1 is decoded privately with
cTrader native period 12 so this research adapter does not silently widen common
execution infrastructure.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
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
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_SCHEMA = "qore.ctrader_demo.vt08_crt_h4_amd_v2_evidence.v2"
_NATIVE_M15_PERIOD = 7
_M15_SECONDS = 900
_NATIVE_D1_PERIOD = 12
_D1_SECONDS = 86_400
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_REQUIRED_COVERAGE_DAYS = 730
_RECENT_BOUNDARY_TOLERANCE_DAYS = 10
_PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271",
)
_PROVIDER_SUFFIX_SEPARATORS = frozenset({".", "_", "-", "/"})

_PROVIDER_ROOTS: dict[str, tuple[str, ...]] = {
    "EURUSD": ("EURUSD",),
    "GBPUSD": ("GBPUSD",),
    "USDJPY": ("USDJPY",),
    "AUDUSD": ("AUDUSD",),
    "USDCAD": ("USDCAD",),
    "XAUUSD": ("XAUUSD", "GOLD"),
    "GBPJPY": ("GBPJPY",),
    "AUDJPY": ("AUDJPY",),
    "NAS100": ("NAS100", "USTEC", "US100", "USTECH", "NASDAQ100"),
    "SP500": ("SP500", "US500", "SPX500", "USSPX500"),
    "US30": ("US30", "DJ30", "DJI30", "WALLSTREET30"),
}


class _HistoricalBar(Protocol):
    @property
    def opened_at(self) -> datetime: ...

    @property
    def closed_at(self) -> datetime: ...

    def payload(self) -> dict[str, str]: ...


@dataclass(frozen=True, slots=True)
class _Vt08V2DailyBar:
    opened_at: datetime
    closed_at: datetime
    open: str
    high: str
    low: str
    close: str

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise CTraderDemoLabProbeError("VT-08 V2 D1 opened_at must be aware")
        if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
            raise CTraderDemoLabProbeError("VT-08 V2 D1 closed_at must be aware")
        if self.closed_at <= self.opened_at:
            raise CTraderDemoLabProbeError("VT-08 V2 D1 close must follow open")

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


def _root_match(name: str, root: str) -> bool:
    upper = name.upper()
    root_upper = root.upper()
    if upper == root_upper:
        return True
    if not upper.startswith(root_upper) or len(upper) <= len(root_upper):
        return False
    if upper[len(root_upper)] not in _PROVIDER_SUFFIX_SEPARATORS:
        return False
    suffix = upper[len(root_upper) + 1 :]
    return bool(suffix) and re.fullmatch(r"[A-Z0-9]+", suffix) is not None


def select_vt08_provider_symbol_name(
    canonical_symbol: str,
    symbols: tuple[tuple[str, bool], ...],
) -> str:
    """Resolve one Core canonical market to one explicit enabled provider alias."""

    roots = _PROVIDER_ROOTS.get(canonical_symbol)
    if roots is None:
        raise CTraderDemoLabProbeError("unsupported VT-08 canonical market")
    if type(symbols) is not tuple or any(
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not str
        or type(item[1]) is not bool
        for item in symbols
    ):
        raise CTraderDemoLabProbeError(
            "provider symbols must be immutable name/enabled pairs"
        )
    enabled = tuple(name for name, is_enabled in symbols if is_enabled)
    for root in roots:
        exact = tuple(name for name in enabled if name.upper() == root.upper())
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise CTraderDemoLabProbeError(
                "duplicate exact cTrader provider symbol identity"
            )
        suffixed = tuple(name for name in enabled if _root_match(name, root))
        if len(suffixed) == 1:
            return suffixed[0]
        if len(suffixed) > 1:
            raise CTraderDemoLabProbeError(
                "canonical VT-08 provider alias is ambiguous at one explicit root"
            )
    raise CTraderDemoLabProbeError(
        f"canonical {canonical_symbol} has no enabled explicit cTrader provider alias"
    )


def _connect_and_resolve(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    canonical_symbol: str,
    timeout_seconds: float,
) -> tuple[int, str, CTraderDemoLabSymbolEvidence, str]:
    """Authenticate read-only DEMO and bind one canonical market to provider metadata."""

    if not client.is_ready:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CTraderDemoLabProbeError(
                f"cTrader DEMO authentication failed: {type(connected.error).__name__}"
            )
    account_id = client.account_id
    listed = client.request(
        "ProtoOASymbolsListReq",
        {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
        client_msg_id=f"qore-vt08-symbol-list:{canonical_symbol}",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(listed, Failure):
        raise CTraderDemoLabProbeError("cTrader DEMO symbol-list read failed")
    native_symbols = getattr(listed.value, "symbol", None)
    if native_symbols is None:
        raise CTraderDemoLabProbeError("cTrader DEMO symbol list is missing")
    observed: list[tuple[str, bool]] = []
    by_name: dict[str, object] = {}
    for item in cast(tuple[object, ...], tuple(native_symbols)):
        name = getattr(item, "symbolName", None)
        enabled = getattr(item, "enabled", None)
        if type(name) is not str or type(enabled) is not bool:
            continue
        if name in by_name:
            raise CTraderDemoLabProbeError("cTrader DEMO symbol list duplicates names")
        observed.append((name, enabled))
        by_name[name] = item
    provider_symbol_name = select_vt08_provider_symbol_name(
        canonical_symbol, tuple(observed)
    )
    selected = by_name[provider_symbol_name]
    symbol_id = _native_int(selected, "symbolId")
    details = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
        client_msg_id=f"qore-vt08-symbol-details:{canonical_symbol}:{symbol_id}",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(details, Failure):
        raise CTraderDemoLabProbeError("cTrader DEMO symbol-details read failed")
    native_details = getattr(details.value, "symbol", None)
    if native_details is None:
        raise CTraderDemoLabProbeError("cTrader DEMO symbol details are missing")
    detail = next(
        (
            item
            for item in cast(tuple[object, ...], tuple(native_details))
            if getattr(item, "symbolId", None) == symbol_id
        ),
        None,
    )
    if detail is None:
        raise CTraderDemoLabProbeError("exact cTrader provider symbol details are absent")
    canonical = CTraderDemoLabSymbolEvidence(
        symbol_id=symbol_id,
        symbol_name=canonical_symbol,
        digits=_native_int(detail, "digits"),
        min_volume_units=_native_int(detail, "minVolume"),
        max_volume_units=_native_int(detail, "maxVolume"),
        step_volume_units=_native_int(detail, "stepVolume"),
    )
    return (
        account_id,
        compute_ctrader_demo_lab_account_fingerprint(account_id),
        canonical,
        provider_symbol_name,
    )


def _parse_d1_bar(
    native: object,
    *,
    digits: int,
    checked_at: datetime,
) -> _Vt08V2DailyBar | None:
    low_relative = _native_int(native, "low")
    delta_open = _native_int(native, "deltaOpen")
    delta_high = _native_int(native, "deltaHigh")
    delta_close = _native_int(native, "deltaClose")
    opened_minutes = _native_int(native, "utcTimestampInMinutes")
    bar_opened = datetime.fromtimestamp(opened_minutes * 60, tz=UTC)
    bar_closed = bar_opened + timedelta(seconds=_D1_SECONDS)
    if bar_closed > checked_at:
        return None
    return _Vt08V2DailyBar(
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
) -> tuple[_Vt08V2DailyBar, ...]:
    cursor_end = checked_at
    retained: dict[datetime, _Vt08V2DailyBar] = {}
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
                f"qore-vt08-v2-d1:{symbol.symbol_id}:{window_index}:{page_index}"
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
        page: list[_Vt08V2DailyBar] = []
        for native in cast(tuple[object, ...], tuple(native_bars)):
            parsed = _parse_d1_bar(native, digits=symbol.digits, checked_at=checked_at)
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
            raise CTraderDemoLabProbeError("cTrader D1 pagination exceeded safe bound")
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
                    "VT-08 V2 M15 acquisition windows contradict on one bar"
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
) -> tuple[_Vt08V2DailyBar, ...]:
    retained: dict[datetime, _Vt08V2DailyBar] = {}
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
                    "VT-08 V2 D1 acquisition windows contradict on one bar"
                )
            retained[bar.opened_at] = bar
        cursor = window_end
        window_index += 1
    return tuple(retained[key] for key in sorted(retained))


def _validate_period(
    name: str,
    bars: Sequence[_HistoricalBar],
    *,
    requested_opened_at: datetime,
    checked_at: datetime,
) -> None:
    if not bars:
        raise CTraderDemoLabProbeError(f"VT-08 V2 {name} evidence is empty")
    first = bars[0].opened_at.astimezone(UTC)
    last = bars[-1].closed_at.astimezone(UTC)
    if last - first < timedelta(days=_REQUIRED_COVERAGE_DAYS):
        raise CTraderDemoLabProbeError(f"VT-08 V2 {name} spans less than 730 days")
    if first < requested_opened_at.astimezone(UTC):
        raise CTraderDemoLabProbeError(
            f"VT-08 V2 {name} predates requested acquisition boundary"
        )
    if last < checked_at.astimezone(UTC) - timedelta(
        days=_RECENT_BOUNDARY_TOLERANCE_DAYS
    ):
        raise CTraderDemoLabProbeError(f"VT-08 V2 {name} evidence is stale")


def _coverage_payload(bars: Sequence[_HistoricalBar]) -> dict[str, object]:
    return {
        "bar_count": len(bars),
        "first_opened_at": bars[0].opened_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "last_closed_at": bars[-1].closed_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "span_seconds": int(
            (bars[-1].closed_at - bars[0].opened_at).total_seconds()
        ),
    }


def collect_vt08_v2_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    canonical_symbol: str,
    requested_opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> dict[str, object]:
    """Collect source-required M15 plus D1 evidence for one Core market."""

    if canonical_symbol not in _PROVIDER_ROOTS:
        raise CTraderDemoLabProbeError("VT-08 V2 market is outside Core 11-market set")
    if requested_opened_at.tzinfo is None or checked_at.tzinfo is None:
        raise CTraderDemoLabProbeError("VT-08 V2 acquisition timestamps must be aware")
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError("VT-08 V2 acquisition start must predate end")
    if type(timeout_seconds) is not float or timeout_seconds <= 0:
        raise CTraderDemoLabProbeError("timeout_seconds must be positive float")

    account_id, account_fingerprint, symbol, provider_symbol = _connect_and_resolve(
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
    _validate_period(
        "M15", m15, requested_opened_at=opened, checked_at=checked
    )
    _validate_period("D1", d1, requested_opened_at=opened, checked_at=checked)
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
        "context_timeframes": ["D1-provider-native", "H4-derived-M15", "M15"],
        "source_sequence_policy": {
            "timezone": "America/New_York",
            "forex_sequence_open_hours": [1, 5, 9],
            "futures_style_sequence_open_hours": [2, 6, 10],
            "futures_style_markets": ["NAS100", "SP500", "US30", "XAUUSD"],
            "maximum_setups_per_market_day": 1,
        },
        "invalidates_prior_m15_only_campaign": True,
        "coverage": {"M15": _coverage_payload(m15), "D1": _coverage_payload(d1)},
        "periods": {
            "M15": [bar.payload() for bar in m15],
            "D1": [bar.payload() for bar in d1],
        },
    }


def main() -> None:
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"
        ),
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
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError("QORE_SOFTWARE_SHA must be exact lowercase Git SHA")
    canonical_symbol = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = int(os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "760"))
    if not _MIN_LOOKBACK_DAYS <= lookback_days <= _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError("VT-08 V2 lookback must be 730..1095 days")
    checked_at = datetime.now(UTC)
    requested_opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt08_v2_evidence(
            client,
            canonical_symbol=canonical_symbol,
            requested_opened_at=requested_opened_at,
            checked_at=checked_at,
        )
        payload["requested_lookback_days"] = lookback_days
        payload["software_sha"] = software_sha
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
