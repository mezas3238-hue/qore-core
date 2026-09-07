"""Long-horizon read-only cTrader DEMO evidence collector for Trader Lab.

The credibility gate is bound to the exact timeframes consumed by the first
cohort: M5 and M15 execution data plus H4 structural context.  Those periods
must cover at least the requested two-year horizon.  M1 is retained only as a
recent auxiliary/schema-compatible series because no first-cohort evaluator
consumes M1.

Every cTrader historical window is fully paginated using ``count``/``hasMore``
and requests are paced below the provider historical-data rate limit.  The
collector never submits, amends, cancels, or otherwise mutates an order.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import sleep
from typing import cast

from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabMarketEvidence,
    CTraderDemoLabProbeError,
    CTraderDemoLabSymbolEvidence,
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_CHUNK_DAYS = 30
_AUXILIARY_M1_LOOKBACK_DAYS = 30
_COVERAGE_TOLERANCE_DAYS = 10
_HISTORICAL_PAGE_COUNT = 5_000
_HISTORICAL_REQUEST_PAUSE_SECONDS = 0.22
_PRICE_SCALE = Decimal(100_000)
_PERIODS: tuple[tuple[str, int, int], ...] = (
    ("M1", 1, 60),
    ("M5", 5, 300),
    ("M15", 7, 900),
    ("H4", 10, 14_400),
)
_TWO_YEAR_REQUIRED_PERIODS = ("M5", "M15", "H4")


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise CTraderDemoLabProbeError(f"missing required environment input: {name}")


def _native_int(value: object, name: str) -> int:
    result = getattr(value, name, None)
    if type(result) is not int:
        raise CTraderDemoLabProbeError(f"cTrader {name} must be an int")
    return result


def _normalized_price(relative: int, *, digits: int) -> str:
    if type(relative) is not int or relative <= 0:
        raise CTraderDemoLabProbeError(
            "cTrader reconstructed relative price must be positive"
        )
    value = Decimal(relative) / _PRICE_SCALE
    return format(value, f".{digits}f")


def _connect_and_resolve_symbol(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    symbol_name: str,
    timeout_seconds: float,
) -> tuple[int, str, CTraderDemoLabSymbolEvidence]:
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
        client_msg_id="qore-long-lab-symbol-list",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(listed, Failure):
        raise CTraderDemoLabProbeError("cTrader DEMO symbol-list read failed")
    native_symbols = getattr(listed.value, "symbol", None)
    if native_symbols is None:
        raise CTraderDemoLabProbeError("cTrader DEMO symbol list is missing")
    selected = next(
        (
            item
            for item in cast(tuple[object, ...], tuple(native_symbols))
            if getattr(item, "symbolName", None) == symbol_name
            and getattr(item, "enabled", None) is True
        ),
        None,
    )
    if selected is None:
        raise CTraderDemoLabProbeError("requested cTrader DEMO symbol is absent or disabled")
    symbol_id = _native_int(selected, "symbolId")
    details = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
        client_msg_id=f"qore-long-lab-symbol-details:{symbol_id}",
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
        raise CTraderDemoLabProbeError("cTrader DEMO exact symbol details are absent")
    symbol = CTraderDemoLabSymbolEvidence(
        symbol_id=symbol_id,
        symbol_name=symbol_name,
        digits=_native_int(detail, "digits"),
        min_volume_units=_native_int(detail, "minVolume"),
        max_volume_units=_native_int(detail, "maxVolume"),
        step_volume_units=_native_int(detail, "stepVolume"),
    )
    return (
        account_id,
        compute_ctrader_demo_lab_account_fingerprint(account_id),
        symbol,
    )


def _parse_native_bar(
    native: object,
    *,
    period_name: str,
    seconds: int,
    digits: int,
    checked_at: datetime,
) -> CTraderDemoLabClosedTrendbar | None:
    low_relative = _native_int(native, "low")
    delta_open = _native_int(native, "deltaOpen")
    delta_high = _native_int(native, "deltaHigh")
    delta_close = _native_int(native, "deltaClose")
    opened_minutes = _native_int(native, "utcTimestampInMinutes")
    bar_opened = datetime.fromtimestamp(opened_minutes * 60, tz=UTC)
    bar_closed = bar_opened + timedelta(seconds=seconds)
    if bar_closed > checked_at:
        return None
    return CTraderDemoLabClosedTrendbar(
        period=period_name,
        opened_at=bar_opened,
        closed_at=bar_closed,
        open=_normalized_price(low_relative + delta_open, digits=digits),
        high=_normalized_price(low_relative + delta_high, digits=digits),
        low=_normalized_price(low_relative, digits=digits),
        close=_normalized_price(low_relative + delta_close, digits=digits),
    )


def _collect_period_window(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    account_id: int,
    symbol: CTraderDemoLabSymbolEvidence,
    period_name: str,
    native_period: int,
    seconds: int,
    opened_at: datetime,
    checked_at: datetime,
    window_index: int,
    timeout_seconds: float,
) -> tuple[CTraderDemoLabClosedTrendbar, ...]:
    """Consume every provider page for one bounded historical window."""
    cursor_end = checked_at
    retained: dict[datetime, CTraderDemoLabClosedTrendbar] = {}
    page_index = 0
    while cursor_end > opened_at:
        sleep(_HISTORICAL_REQUEST_PAUSE_SECONDS)
        response = client.request(
            "ProtoOAGetTrendbarsReq",
            {
                "ctidTraderAccountId": account_id,
                "count": _HISTORICAL_PAGE_COUNT,
                "fromTimestamp": int(opened_at.timestamp() * 1000),
                "period": native_period,
                "symbolId": symbol.symbol_id,
                "toTimestamp": int(cursor_end.timestamp() * 1000),
            },
            client_msg_id=(
                f"qore-long-lab-trendbars:{symbol.symbol_id}:{period_name}:"
                f"{window_index}:{page_index}"
            ),
            timeout_seconds=timeout_seconds,
        )
        if isinstance(response, Failure):
            raise CTraderDemoLabProbeError(
                f"cTrader DEMO {period_name} trendbar read failed"
            )
        native_bars = getattr(response.value, "trendbar", None)
        if native_bars is None:
            raise CTraderDemoLabProbeError(
                f"cTrader DEMO {period_name} trendbar response is missing bars"
            )
        page: list[CTraderDemoLabClosedTrendbar] = []
        for native in cast(tuple[object, ...], tuple(native_bars)):
            parsed = _parse_native_bar(
                native,
                period_name=period_name,
                seconds=seconds,
                digits=symbol.digits,
                checked_at=checked_at,
            )
            if parsed is None or parsed.opened_at < opened_at:
                continue
            existing = retained.get(parsed.opened_at)
            if existing is not None and existing != parsed:
                raise CTraderDemoLabProbeError(
                    "cTrader historical pages contradict on the same trendbar"
                )
            retained[parsed.opened_at] = parsed
            page.append(parsed)

        has_more_value = getattr(response.value, "hasMore", False)
        if type(has_more_value) is not bool:
            raise CTraderDemoLabProbeError("cTrader trendbar hasMore must be a bool")
        if not page:
            if has_more_value:
                raise CTraderDemoLabProbeError(
                    "cTrader trendbar pagination reported more data without progress"
                )
            break
        earliest = min(item.opened_at for item in page)
        if not has_more_value or earliest <= opened_at:
            break
        next_end = earliest - timedelta(milliseconds=1)
        if next_end >= cursor_end:
            raise CTraderDemoLabProbeError(
                "cTrader trendbar pagination failed to move backward"
            )
        cursor_end = next_end
        page_index += 1
        if page_index > 10_000:
            raise CTraderDemoLabProbeError("cTrader trendbar pagination exceeded safe bound")

    return tuple(retained[key] for key in sorted(retained))


def _merge_bars(
    retained: dict[tuple[str, datetime], CTraderDemoLabClosedTrendbar],
    bars: tuple[CTraderDemoLabClosedTrendbar, ...],
) -> None:
    for bar in bars:
        key = (bar.period, bar.opened_at)
        existing = retained.get(key)
        if existing is not None and existing != bar:
            raise CTraderDemoLabProbeError(
                "cTrader long-horizon windows contradict on the same trendbar"
            )
        retained[key] = bar


def _period_bars(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...], period: str
) -> tuple[CTraderDemoLabClosedTrendbar, ...]:
    return tuple(item for item in bars if item.period == period)


def _validate_two_year_coverage(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...],
    *,
    requested_opened_at: datetime,
    checked_at: datetime,
) -> None:
    tolerance = timedelta(days=_COVERAGE_TOLERANCE_DAYS)
    for period in _TWO_YEAR_REQUIRED_PERIODS:
        retained = _period_bars(bars, period)
        if not retained:
            raise CTraderDemoLabProbeError(
                f"cTrader long-horizon evidence is missing {period}"
            )
        first = retained[0].opened_at
        last = retained[-1].closed_at
        if first > requested_opened_at + tolerance:
            raise CTraderDemoLabProbeError(
                f"cTrader {period} history does not reach the two-year boundary"
            )
        if last < checked_at - tolerance:
            raise CTraderDemoLabProbeError(
                f"cTrader {period} history is stale at the recent boundary"
            )


def _validate_auxiliary_m1(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...], *, checked_at: datetime
) -> None:
    retained = _period_bars(bars, "M1")
    if not retained:
        raise CTraderDemoLabProbeError("cTrader auxiliary M1 evidence is missing")
    tolerance = timedelta(days=_COVERAGE_TOLERANCE_DAYS)
    if retained[-1].closed_at < checked_at - tolerance:
        raise CTraderDemoLabProbeError("cTrader auxiliary M1 evidence is stale")


def _coverage_payload(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...]
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for period, _native_period, _seconds in _PERIODS:
        retained = _period_bars(bars, period)
        if not retained:
            continue
        result[period] = {
            "bar_count": len(retained),
            "first_opened_at": retained[0].opened_at.isoformat(timespec="microseconds"),
            "last_closed_at": retained[-1].closed_at.isoformat(timespec="microseconds"),
            "span_days": (retained[-1].closed_at - retained[0].opened_at).days,
        }
    return result


def collect_long_horizon_market_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    symbol_name: str,
    requested_opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> CTraderDemoLabMarketEvidence:
    """Collect two-year consumed periods plus recent auxiliary M1 evidence."""
    if requested_opened_at.tzinfo is None or requested_opened_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("requested_opened_at must be timezone-aware")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
    if not isinstance(timeout_seconds, float) or timeout_seconds <= 0:
        raise CTraderDemoLabProbeError("timeout_seconds must be positive")
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError("requested_opened_at must predate checked_at")

    account_id, account_fingerprint, symbol = _connect_and_resolve_symbol(
        client,
        symbol_name=symbol_name,
        timeout_seconds=timeout_seconds,
    )
    retained: dict[tuple[str, datetime], CTraderDemoLabClosedTrendbar] = {}

    cursor = opened
    window_index = 0
    while cursor < checked:
        window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
        for period_name, native_period, seconds in _PERIODS:
            if period_name not in _TWO_YEAR_REQUIRED_PERIODS:
                continue
            period_bars = _collect_period_window(
                client,
                account_id=account_id,
                symbol=symbol,
                period_name=period_name,
                native_period=native_period,
                seconds=seconds,
                opened_at=cursor,
                checked_at=window_end,
                window_index=window_index,
                timeout_seconds=timeout_seconds,
            )
            _merge_bars(retained, period_bars)
        cursor = window_end
        window_index += 1

    auxiliary_opened = max(
        opened,
        checked - timedelta(days=_AUXILIARY_M1_LOOKBACK_DAYS),
    )
    m1_native = next(item for item in _PERIODS if item[0] == "M1")
    m1_bars = _collect_period_window(
        client,
        account_id=account_id,
        symbol=symbol,
        period_name=m1_native[0],
        native_period=m1_native[1],
        seconds=m1_native[2],
        opened_at=auxiliary_opened,
        checked_at=checked,
        window_index=window_index,
        timeout_seconds=timeout_seconds,
    )
    _merge_bars(retained, m1_bars)

    if not retained:
        raise CTraderDemoLabProbeError("cTrader long-horizon collection returned no evidence")
    bars = tuple(sorted(retained.values(), key=lambda item: (item.period, item.opened_at)))
    _validate_two_year_coverage(
        bars,
        requested_opened_at=opened,
        checked_at=checked,
    )
    _validate_auxiliary_m1(bars, checked_at=checked)
    return CTraderDemoLabMarketEvidence(
        account_fingerprint=account_fingerprint,
        symbol=symbol,
        checked_at=checked,
        bars=bars,
    )


def main() -> None:
    """Collect credibility-grade two-year DEMO evidence without printing secrets."""
    credentials = CTraderOpenApiCredentials(
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
    symbol_name = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = int(os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "730"))
    if lookback_days < _MIN_LOOKBACK_DAYS or lookback_days > _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError(
            "long-horizon Lab lookback days must be between 730 and 1095"
        )
    checked_at = datetime.now(UTC)
    requested_opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_long_horizon_market_evidence(
            client,
            symbol_name=symbol_name,
            requested_opened_at=requested_opened_at,
            checked_at=checked_at,
        )
        payload = evidence.sanitized_payload()
        payload["requested_lookback_days"] = lookback_days
        payload["requested_opened_at"] = requested_opened_at.isoformat(timespec="microseconds")
        payload["historical_chunk_days"] = _CHUNK_DAYS
        payload["historical_page_count"] = _HISTORICAL_PAGE_COUNT
        payload["two_year_required_periods"] = list(_TWO_YEAR_REQUIRED_PERIODS)
        payload["auxiliary_m1_lookback_days"] = _AUXILIARY_M1_LOOKBACK_DAYS
        payload["coverage"] = _coverage_payload(evidence.bars)
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
