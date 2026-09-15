"""Read-only native-D1 development evidence for Turtle Soup candidate R1.

This collector is intentionally isolated from the legacy first-cohort workflows.
It requests provider-native cTrader D1 bars only and never submits, amends, or
cancels an order. The resulting payload is development evidence; it grants no
fresh-OOS, DEMO, LIVE, or production authority.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _connect_and_resolve_symbol,
    _native_int,
    _normalized_price,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1_collection_windows import (
    build_overlapped_collection_windows,
)
from qore.kernel.result import Failure

_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r1.d1_development_evidence.v1"
_NATIVE_D1_PERIOD = 12
_D1_SECONDS = 86_400
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_REQUIRED_COVERAGE_DAYS = 730
_CHUNK_DAYS = 90
_PAGE_COUNT = 5_000
_RECENT_BOUNDARY_TOLERANCE_DAYS = 10


@dataclass(frozen=True, slots=True)
class TurtleSoupR1D1Bar:
    opened_at: datetime
    closed_at: datetime
    open: str
    high: str
    low: str
    close: str

    def __post_init__(self) -> None:
        for field_name, timestamp in (
            ("opened_at", self.opened_at),
            ("closed_at", self.closed_at),
        ):
            if (
                type(timestamp) is not datetime
                or timestamp.tzinfo is None
                or timestamp.utcoffset() is None
            ):
                raise CTraderDemoLabProbeError(
                    f"Turtle Soup D1 {field_name} must be timezone-aware"
                )
        if self.closed_at <= self.opened_at:
            raise CTraderDemoLabProbeError(
                "Turtle Soup D1 closed_at must follow opened_at"
            )
        values = tuple(Decimal(item) for item in (self.open, self.high, self.low, self.close))
        if any(not item.is_finite() or item <= 0 for item in values):
            raise CTraderDemoLabProbeError(
                "Turtle Soup D1 prices must be positive finite values"
            )
        open_value, high_value, low_value, close_value = values
        if high_value < max(open_value, low_value, close_value):
            raise CTraderDemoLabProbeError("Turtle Soup D1 high violates OHLC geometry")
        if low_value > min(open_value, high_value, close_value):
            raise CTraderDemoLabProbeError("Turtle Soup D1 low violates OHLC geometry")

    def payload(self) -> dict[str, str]:
        return {
            "opened_at": self.opened_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "closed_at": self.closed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }


@dataclass(frozen=True, slots=True)
class TurtleSoupR1D1Evidence:
    account_fingerprint: str
    symbol_name: str
    symbol_digits: int
    checked_at: datetime
    requested_opened_at: datetime
    bars: tuple[TurtleSoupR1D1Bar, ...]
    software_sha: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", self.account_fingerprint) is None:
            raise CTraderDemoLabProbeError("account fingerprint must be SHA-256")
        if re.fullmatch(r"[A-Z0-9][A-Z0-9]{1,31}", self.symbol_name) is None:
            raise CTraderDemoLabProbeError("symbol name must use canonical uppercase syntax")
        if type(self.symbol_digits) is not int or self.symbol_digits < 0:
            raise CTraderDemoLabProbeError("symbol_digits must be non-negative int")
        if re.fullmatch(r"[0-9a-f]{40}", self.software_sha) is None:
            raise CTraderDemoLabProbeError("software_sha must be exact Git SHA")
        if type(self.bars) is not tuple or not self.bars:
            raise CTraderDemoLabProbeError("Turtle Soup D1 evidence requires bars")
        if tuple(sorted(self.bars, key=lambda item: item.opened_at)) != self.bars:
            raise CTraderDemoLabProbeError("Turtle Soup D1 bars must be chronological")
        if len({item.opened_at for item in self.bars}) != len(self.bars):
            raise CTraderDemoLabProbeError("Turtle Soup D1 bars must be unique")
        first = self.bars[0].opened_at
        last = self.bars[-1].closed_at
        if last - first < timedelta(days=_REQUIRED_COVERAGE_DAYS):
            raise CTraderDemoLabProbeError(
                "Turtle Soup D1 evidence requires at least 730 calendar days of span"
            )
        if last < self.checked_at - timedelta(days=_RECENT_BOUNDARY_TOLERANCE_DAYS):
            raise CTraderDemoLabProbeError("Turtle Soup D1 evidence is stale")
        if any(item.closed_at > self.checked_at for item in self.bars):
            raise CTraderDemoLabProbeError("Turtle Soup D1 evidence must be fully closed")

    def evidence_digest(self) -> str:
        encoded = json.dumps(
            [item.payload() for item in self.bars],
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def payload(self) -> dict[str, object]:
        first = self.bars[0].opened_at
        last = self.bars[-1].closed_at
        return {
            "schema": _SCHEMA,
            "environment": "development-market-data",
            "read_only": True,
            "research_only": True,
            "fresh_oos_consumed": False,
            "research_identity": "turtle-soup-candidate-r1",
            "symbol": self.symbol_name,
            "symbol_digits": self.symbol_digits,
            "period": "D1",
            "native_period_value": _NATIVE_D1_PERIOD,
            "account_fingerprint": self.account_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "requested_opened_at": self.requested_opened_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "required_coverage_days": _REQUIRED_COVERAGE_DAYS,
            "bar_count": len(self.bars),
            "first_opened_at": first.astimezone(UTC).isoformat(timespec="microseconds"),
            "last_closed_at": last.astimezone(UTC).isoformat(timespec="microseconds"),
            "span_seconds": int((last - first).total_seconds()),
            "software_sha": self.software_sha,
            "evidence_digest_sha256": self.evidence_digest(),
            "bars": [item.payload() for item in self.bars],
        }


def _parse_bar(
    native: object,
    *,
    digits: int,
    checked_at: datetime,
) -> TurtleSoupR1D1Bar | None:
    low_relative = _native_int(native, "low")
    opened_minutes = _native_int(native, "utcTimestampInMinutes")
    opened_at = datetime.fromtimestamp(opened_minutes * 60, tz=UTC)
    closed_at = opened_at + timedelta(seconds=_D1_SECONDS)
    if closed_at > checked_at:
        return None
    return TurtleSoupR1D1Bar(
        opened_at=opened_at,
        closed_at=closed_at,
        open=_normalized_price(
            low_relative + _native_int(native, "deltaOpen"), digits=digits
        ),
        high=_normalized_price(
            low_relative + _native_int(native, "deltaHigh"), digits=digits
        ),
        low=_normalized_price(low_relative, digits=digits),
        close=_normalized_price(
            low_relative + _native_int(native, "deltaClose"), digits=digits
        ),
    )


def _collect_d1_window(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    account_id: int,
    symbol_id: int,
    digits: int,
    opened_at: datetime,
    checked_at: datetime,
    window_index: int,
    timeout_seconds: float,
) -> tuple[TurtleSoupR1D1Bar, ...]:
    cursor_end = checked_at
    retained: dict[datetime, TurtleSoupR1D1Bar] = {}
    page_index = 0
    while cursor_end > opened_at:
        response = client.request(
            "ProtoOAGetTrendbarsReq",
            {
                "ctidTraderAccountId": account_id,
                "count": _PAGE_COUNT,
                "fromTimestamp": int(opened_at.timestamp() * 1000),
                "period": _NATIVE_D1_PERIOD,
                "symbolId": symbol_id,
                "toTimestamp": int(cursor_end.timestamp() * 1000),
            },
            client_msg_id=f"qore-turtle-soup-d1:{symbol_id}:{window_index}:{page_index}",
            timeout_seconds=timeout_seconds,
        )
        if isinstance(response, Failure):
            raise CTraderDemoLabProbeError("cTrader Turtle Soup D1 trendbar read failed")
        native_bars = getattr(response.value, "trendbar", None)
        if native_bars is None:
            raise CTraderDemoLabProbeError("cTrader Turtle Soup D1 response missing bars")
        page: list[TurtleSoupR1D1Bar] = []
        for native in cast(tuple[object, ...], tuple(native_bars)):
            parsed = _parse_bar(native, digits=digits, checked_at=checked_at)
            if parsed is None or parsed.opened_at < opened_at:
                continue
            existing = retained.get(parsed.opened_at)
            if existing is not None and existing != parsed:
                raise CTraderDemoLabProbeError(
                    "cTrader Turtle Soup D1 pages contradict on same bar"
                )
            retained[parsed.opened_at] = parsed
            page.append(parsed)
        has_more = getattr(response.value, "hasMore", False)
        if type(has_more) is not bool:
            raise CTraderDemoLabProbeError("cTrader Turtle Soup D1 hasMore must be bool")
        if not page:
            if has_more:
                raise CTraderDemoLabProbeError(
                    "cTrader Turtle Soup D1 pagination reported more without progress"
                )
            break
        earliest = min(item.opened_at for item in page)
        if not has_more or earliest <= opened_at:
            break
        next_end = earliest - timedelta(milliseconds=1)
        if next_end >= cursor_end:
            raise CTraderDemoLabProbeError("cTrader Turtle Soup D1 pagination stalled")
        cursor_end = next_end
        page_index += 1
        if page_index > 100:
            raise CTraderDemoLabProbeError("cTrader Turtle Soup D1 pagination unsafe")
    return tuple(retained[key] for key in sorted(retained))


def collect_turtle_soup_r1_d1_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    symbol_name: str,
    requested_opened_at: datetime,
    checked_at: datetime,
    software_sha: str,
    timeout_seconds: float = 15.0,
) -> TurtleSoupR1D1Evidence:
    if requested_opened_at.tzinfo is None or requested_opened_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("requested_opened_at must be timezone-aware")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError("requested_opened_at must predate checked_at")
    account_id, account_fingerprint, symbol = _connect_and_resolve_symbol(
        client,
        symbol_name=symbol_name,
        timeout_seconds=timeout_seconds,
    )
    retained: dict[datetime, TurtleSoupR1D1Bar] = {}
    windows = build_overlapped_collection_windows(
        opened_at=opened,
        checked_at=checked,
        chunk_span=timedelta(days=_CHUNK_DAYS),
        bar_span=timedelta(seconds=_D1_SECONDS),
    )
    for window_index, (window_opened_at, window_checked_at) in enumerate(windows):
        window = _collect_d1_window(
            client,
            account_id=account_id,
            symbol_id=symbol.symbol_id,
            digits=symbol.digits,
            opened_at=window_opened_at,
            checked_at=window_checked_at,
            window_index=window_index,
            timeout_seconds=timeout_seconds,
        )
        for bar in window:
            existing = retained.get(bar.opened_at)
            if existing is not None and existing != bar:
                raise CTraderDemoLabProbeError(
                    "cTrader Turtle Soup D1 windows contradict on same bar"
                )
            retained[bar.opened_at] = bar
    return TurtleSoupR1D1Evidence(
        account_fingerprint=account_fingerprint,
        symbol_name=symbol.symbol_name,
        symbol_digits=symbol.digits,
        checked_at=checked,
        requested_opened_at=opened,
        bars=tuple(retained[key] for key in sorted(retained)),
        software_sha=software_sha,
    )


def _explicit_checked_at() -> datetime:
    raw = _required_env("QORE_TURTLE_SOUP_CHECKED_AT")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CTraderDemoLabProbeError(
            "QORE_TURTLE_SOUP_CHECKED_AT must be an ISO-8601 timestamp"
        ) from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoLabProbeError(
            "QORE_TURTLE_SOUP_CHECKED_AT must be timezone-aware"
        )
    return value.astimezone(UTC)


def main() -> None:
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
    symbol_name = _required_env("QORE_TURTLE_SOUP_SYMBOL", "QORE_DEMO_LAB_SYMBOL")
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    lookback_days = int(os.environ.get("QORE_TURTLE_SOUP_LOOKBACK_DAYS", "760"))
    if not _MIN_LOOKBACK_DAYS <= lookback_days <= _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError(
            "Turtle Soup lookback days must be between 730 and 1095"
        )
    checked_at = _explicit_checked_at()
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_turtle_soup_r1_d1_evidence(
            client,
            symbol_name=symbol_name,
            requested_opened_at=checked_at - timedelta(days=lookback_days),
            checked_at=checked_at,
            software_sha=software_sha,
        )
        print(
            json.dumps(
                evidence.payload(),
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
