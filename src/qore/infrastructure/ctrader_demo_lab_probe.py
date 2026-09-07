"""Read-only cTrader DEMO evidence collector for first-cohort Trader Lab.

The collector authenticates through the existing fail-closed Open API client,
verifies one exact enabled broker symbol, and reads provider-native M1/M5/M15/H4
closed trendbars.  It never submits, amends, cancels, or otherwise mutates an
order.  Secret material is accepted only by the CLI entry point and is never
included in the sanitized evidence payload.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from re import fullmatch
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure

_PRICE_SCALE = Decimal(100_000)
_PERIODS: tuple[tuple[str, int, int], ...] = (
    ("M1", 1, 60),
    ("M5", 5, 300),
    ("M15", 7, 900),
    ("H4", 10, 14_400),
)


class CTraderDemoLabProbeError(InfrastructureError):
    """Read-only DEMO Lab probe failed closed."""

    __slots__ = ()


def _aware(value: datetime, *, field_name: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoLabProbeError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


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


@dataclass(frozen=True, slots=True)
class CTraderDemoLabClosedTrendbar:
    period: str
    opened_at: datetime
    closed_at: datetime
    open: str
    high: str
    low: str
    close: str

    def __post_init__(self) -> None:
        if self.period not in {item[0] for item in _PERIODS}:
            raise CTraderDemoLabProbeError("unsupported Lab trendbar period")
        opened = _aware(self.opened_at, field_name="trendbar opened_at")
        closed = _aware(self.closed_at, field_name="trendbar closed_at")
        if closed <= opened:
            raise CTraderDemoLabProbeError("trendbar closed_at must follow opened_at")
        values = tuple(Decimal(item) for item in (self.open, self.high, self.low, self.close))
        if any(not item.is_finite() or item <= 0 for item in values):
            raise CTraderDemoLabProbeError("trendbar prices must be positive finite values")
        open_value, high_value, low_value, close_value = values
        if high_value < max(open_value, low_value, close_value):
            raise CTraderDemoLabProbeError("trendbar high violates OHLC geometry")
        if low_value > min(open_value, high_value, close_value):
            raise CTraderDemoLabProbeError("trendbar low violates OHLC geometry")

    def payload(self) -> dict[str, str]:
        return {
            "period": self.period,
            "opened_at": self.opened_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "closed_at": self.closed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }


@dataclass(frozen=True, slots=True)
class CTraderDemoLabSymbolEvidence:
    symbol_id: int
    symbol_name: str
    digits: int
    min_volume_units: int
    max_volume_units: int
    step_volume_units: int

    def __post_init__(self) -> None:
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoLabProbeError("symbol_id must be a positive int")
        if (
            type(self.symbol_name) is not str
            or fullmatch(r"[A-Z0-9][A-Z0-9]{1,31}", self.symbol_name) is None
        ):
            raise CTraderDemoLabProbeError("symbol_name must use canonical uppercase syntax")
        if type(self.digits) is not int or self.digits < 0:
            raise CTraderDemoLabProbeError("digits must be a non-negative int")
        for field_name, value in (
            ("min_volume_units", self.min_volume_units),
            ("max_volume_units", self.max_volume_units),
            ("step_volume_units", self.step_volume_units),
        ):
            if type(value) is not int or value <= 0:
                raise CTraderDemoLabProbeError(f"{field_name} must be a positive int")
        if self.min_volume_units > self.max_volume_units:
            raise CTraderDemoLabProbeError("minimum volume must not exceed maximum")
        if self.min_volume_units % self.step_volume_units != 0:
            raise CTraderDemoLabProbeError("minimum volume must align to broker step")

    def payload(self) -> dict[str, object]:
        return {
            "symbol_id": self.symbol_id,
            "symbol_name": self.symbol_name,
            "digits": self.digits,
            "min_volume_units": self.min_volume_units,
            "max_volume_units": self.max_volume_units,
            "step_volume_units": self.step_volume_units,
        }


@dataclass(frozen=True, slots=True)
class CTraderDemoLabMarketEvidence:
    account_fingerprint: str
    symbol: CTraderDemoLabSymbolEvidence
    checked_at: datetime
    bars: tuple[CTraderDemoLabClosedTrendbar, ...]

    def __post_init__(self) -> None:
        if fullmatch(r"[0-9a-f]{64}", self.account_fingerprint) is None:
            raise CTraderDemoLabProbeError("account_fingerprint must be sha256 hex")
        if not isinstance(self.symbol, CTraderDemoLabSymbolEvidence):
            raise CTraderDemoLabProbeError("symbol must be CTraderDemoLabSymbolEvidence")
        checked = _aware(self.checked_at, field_name="checked_at")
        if type(self.bars) is not tuple or not self.bars or any(
            type(item) is not CTraderDemoLabClosedTrendbar for item in self.bars
        ):
            raise CTraderDemoLabProbeError("bars must be a non-empty trendbar tuple")
        for item in self.bars:
            item.__post_init__()
            if item.closed_at > checked:
                raise CTraderDemoLabProbeError("Lab evidence must contain only closed bars")
        keys = tuple((item.period, item.opened_at) for item in self.bars)
        if len(set(keys)) != len(keys):
            raise CTraderDemoLabProbeError("Lab evidence must not duplicate trendbars")
        if tuple(sorted(self.bars, key=lambda item: (item.period, item.opened_at))) != self.bars:
            raise CTraderDemoLabProbeError("Lab trendbars must use canonical order")
        observed_periods = {item.period for item in self.bars}
        if observed_periods != {item[0] for item in _PERIODS}:
            raise CTraderDemoLabProbeError("Lab evidence requires M1/M5/M15/H4")

    def sanitized_payload(self) -> dict[str, object]:
        by_period: dict[str, list[dict[str, str]]] = {item[0]: [] for item in _PERIODS}
        for bar in self.bars:
            by_period[bar.period].append(bar.payload())
        return {
            "schema": "qore.ctrader_demo.lab_market_evidence.v1",
            "environment": "demo",
            "read_only": True,
            "account_discovered": True,
            "account_is_live": False,
            "trading_permission_verified": True,
            "account_fingerprint": self.account_fingerprint,
            "symbol": self.symbol.payload(),
            "checked_at": self.checked_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "periods": by_period,
        }

    def sanitized_json(self) -> str:
        return json.dumps(
            self.sanitized_payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )


def collect_ctrader_demo_lab_market_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    symbol_name: str,
    opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> CTraderDemoLabMarketEvidence:
    """Authenticate and collect exact broker metadata plus native closed trendbars."""
    if (
        not isinstance(symbol_name, str)
        or fullmatch(r"[A-Z0-9][A-Z0-9]{1,31}", symbol_name) is None
    ):
        raise CTraderDemoLabProbeError("symbol_name must use canonical uppercase syntax")
    opened = _aware(opened_at, field_name="opened_at")
    checked = _aware(checked_at, field_name="checked_at")
    if opened >= checked:
        raise CTraderDemoLabProbeError("opened_at must predate checked_at")
    if not isinstance(timeout_seconds, float) or timeout_seconds <= 0:
        raise CTraderDemoLabProbeError("timeout_seconds must be positive")
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
        client_msg_id="qore-lab-symbol-list",
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
        client_msg_id=f"qore-lab-symbol-details:{symbol_id}",
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

    bars: list[CTraderDemoLabClosedTrendbar] = []
    for period_name, native_period, seconds in _PERIODS:
        response = client.request(
            "ProtoOAGetTrendbarsReq",
            {
                "ctidTraderAccountId": account_id,
                "fromTimestamp": int(opened.timestamp() * 1000),
                "period": native_period,
                "symbolId": symbol_id,
                "toTimestamp": int(checked.timestamp() * 1000),
            },
            client_msg_id=f"qore-lab-trendbars:{symbol_id}:{period_name}",
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
        period_bars: list[CTraderDemoLabClosedTrendbar] = []
        for native in cast(tuple[object, ...], tuple(native_bars)):
            low_relative = _native_int(native, "low")
            delta_open = _native_int(native, "deltaOpen")
            delta_high = _native_int(native, "deltaHigh")
            delta_close = _native_int(native, "deltaClose")
            opened_minutes = _native_int(native, "utcTimestampInMinutes")
            bar_opened = datetime.fromtimestamp(opened_minutes * 60, tz=UTC)
            bar_closed = bar_opened + timedelta(seconds=seconds)
            if bar_closed > checked:
                continue
            period_bars.append(
                CTraderDemoLabClosedTrendbar(
                    period=period_name,
                    opened_at=bar_opened,
                    closed_at=bar_closed,
                    open=_normalized_price(low_relative + delta_open, digits=symbol.digits),
                    high=_normalized_price(low_relative + delta_high, digits=symbol.digits),
                    low=_normalized_price(low_relative, digits=symbol.digits),
                    close=_normalized_price(low_relative + delta_close, digits=symbol.digits),
                )
            )
        if not period_bars:
            raise CTraderDemoLabProbeError(
                f"cTrader DEMO {period_name} returned no closed trendbars"
            )
        bars.extend(period_bars)

    account_fingerprint = sha256(
        f"qore:ctrader-demo-account:v1:{account_id}".encode("ascii")
    ).hexdigest()
    return CTraderDemoLabMarketEvidence(
        account_fingerprint=account_fingerprint,
        symbol=symbol,
        checked_at=checked,
        bars=tuple(sorted(bars, key=lambda item: (item.period, item.opened_at))),
    )


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise CTraderDemoLabProbeError(f"missing required environment input: {name}")
    return value


def main() -> None:
    """Collect a secret-free DEMO market artifact; never print credential material."""
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID"),
        client_secret=_required_env("QORE_CTRADER_CLIENT_SECRET"),
        access_token=_required_env("QORE_CTRADER_ACCESS_TOKEN"),
        refresh_token=_required_env("QORE_CTRADER_REFRESH_TOKEN"),
        ctid_trader_account_id=int(_required_env("QORE_CTRADER_DEMO_ACCOUNT_ID")),
    )
    symbol_name = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = int(os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "30"))
    if lookback_days < 7 or lookback_days > 180:
        raise CTraderDemoLabProbeError("Lab lookback days must be between 7 and 180")
    checked_at = datetime.now(UTC)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_ctrader_demo_lab_market_evidence(
            client,
            symbol_name=symbol_name,
            opened_at=checked_at - timedelta(days=lookback_days),
            checked_at=checked_at,
        )
        print(evidence.sanitized_json())
    finally:
        client.close()


if __name__ == "__main__":
    main()
