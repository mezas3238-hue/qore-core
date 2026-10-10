"""Streaming reader for consumed CIBO Atlas RAW_M5_LEDGER artifacts.

This is an artifact adapter, not a second market replay engine. It preserves the artifact's
chronology and converts provider-relative prices into exact Decimal prices.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

PRICE_SCALE = Decimal(100_000)
BAR_DURATION = timedelta(minutes=5)
EXPECTED_SCHEMA = "qore.cibo_market_atlas.raw_m5.v1"
EXPECTED_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerM5Bar:
    symbol: str
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None
    digits: int

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("bar symbol must be uppercase")
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("bar opened_at must be timezone-aware")
        if self.closed_at - self.opened_at != BAR_DURATION:
            raise ValueError("Capitalizer artifact bar must be exact M5")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("bar prices must be positive")
        if self.low > min(self.open, self.close):
            raise ValueError("bar low cannot exceed open/close")
        if self.high < max(self.open, self.close):
            raise ValueError("bar high cannot be below open/close")
        if self.low > self.high:
            raise ValueError("bar low cannot exceed high")
        if self.volume is not None and self.volume < 0:
            raise ValueError("bar volume must be non-negative when present")
        if self.digits <= 0:
            raise ValueError("bar digits must be positive")

    @property
    def range(self) -> Decimal:
        return self.high - self.low

    @property
    def body(self) -> Decimal:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> Decimal:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> Decimal:
        return min(self.open, self.close) - self.low


def _price(value: object, *, digits: int, field_name: str) -> Decimal:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be positive provider-relative int")
    return (Decimal(value) / PRICE_SCALE).quantize(Decimal(1).scaleb(-digits))


def _bar_from_row(row: dict[str, Any]) -> CapitalizerM5Bar:
    if row.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("unexpected raw M5 schema")
    if row.get("identity") != EXPECTED_IDENTITY:
        raise ValueError("unexpected raw M5 identity")
    symbol = row.get("canonical_symbol")
    opened_raw = row.get("opened_at")
    digits = row.get("digits")
    volume = row.get("volume")
    if not isinstance(symbol, str):
        raise ValueError("raw M5 row requires canonical_symbol")
    if not isinstance(opened_raw, str):
        raise ValueError("raw M5 row requires opened_at")
    if type(digits) is not int:
        raise ValueError("raw M5 row requires integer digits")
    if volume is not None and type(volume) is not int:
        raise ValueError("raw M5 volume must be int or null")
    parsed_opened_at = datetime.fromisoformat(opened_raw)
    if parsed_opened_at.tzinfo is None or parsed_opened_at.utcoffset() is None:
        raise ValueError("raw M5 opened_at must be timezone-aware")
    opened_at = parsed_opened_at.astimezone(UTC)
    return CapitalizerM5Bar(
        symbol=symbol,
        opened_at=opened_at,
        closed_at=opened_at + BAR_DURATION,
        open=_price(row.get("open_relative"), digits=digits, field_name="open_relative"),
        high=_price(row.get("high_relative"), digits=digits, field_name="high_relative"),
        low=_price(row.get("low_relative"), digits=digits, field_name="low_relative"),
        close=_price(row.get("close_relative"), digits=digits, field_name="close_relative"),
        volume=volume,
        digits=digits,
    )


def iter_atlas_m5(root: Path) -> Iterator[CapitalizerM5Bar]:
    """Yield exact artifact chronology and fail closed on duplicates/backward time."""

    files = sorted((root / "RAW_M5_LEDGER").glob("*.jsonl"))
    if not files:
        raise ValueError("RAW_M5_LEDGER partitions not found")

    previous_at: datetime | None = None
    previous_symbol: str | None = None
    seen_at: set[datetime] = set()
    for path in files:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("raw M5 JSONL row must be object")
                bar = _bar_from_row(raw)
                if previous_symbol is not None and bar.symbol != previous_symbol:
                    raise ValueError("one Atlas artifact root must contain exactly one symbol")
                if bar.opened_at in seen_at:
                    raise ValueError("duplicate M5 timestamp in Atlas artifact")
                if previous_at is not None and bar.opened_at < previous_at:
                    raise ValueError("Atlas M5 chronology moved backward")
                seen_at.add(bar.opened_at)
                previous_at = bar.opened_at
                previous_symbol = bar.symbol
                yield bar
