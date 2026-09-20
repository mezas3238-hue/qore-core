"""Streaming reader for Capitalizer's retained CIBO native-M1 clone."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

PRICE_SCALE = Decimal(100_000)
BAR_DURATION = timedelta(minutes=1)
EXPECTED_SCHEMA = "qore.capitalizer.cibo.raw_m1.v1"
EXPECTED_IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerM1Bar:
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
            raise ValueError("M1 bar symbol must be uppercase")
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("M1 opened_at must be timezone-aware")
        if self.closed_at - self.opened_at != BAR_DURATION:
            raise ValueError("Capitalizer M1 bar must be exact one minute")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("M1 prices must be positive")
        if self.low > min(self.open, self.close):
            raise ValueError("M1 low cannot exceed open/close")
        if self.high < max(self.open, self.close):
            raise ValueError("M1 high cannot be below open/close")
        if self.low > self.high:
            raise ValueError("M1 low cannot exceed high")
        if self.volume is not None and self.volume < 0:
            raise ValueError("M1 volume must be non-negative")
        if self.digits <= 0:
            raise ValueError("M1 digits must be positive")

    @property
    def range(self) -> Decimal:
        return self.high - self.low

    @property
    def body(self) -> Decimal:
        return abs(self.close - self.open)

    @property
    def bullish(self) -> bool:
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        return self.close < self.open


def _price(value: object, *, digits: int, field_name: str) -> Decimal:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be positive provider-relative int")
    return (Decimal(value) / PRICE_SCALE).quantize(Decimal(1).scaleb(-digits))


def _bar_from_row(row: dict[str, Any]) -> CapitalizerM1Bar:
    if row.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("unexpected raw M1 schema")
    if row.get("identity") != EXPECTED_IDENTITY:
        raise ValueError("unexpected raw M1 identity")
    symbol = row.get("canonical_symbol")
    opened_raw = row.get("opened_at")
    digits = row.get("digits")
    volume = row.get("volume")
    if not isinstance(symbol, str):
        raise ValueError("raw M1 row requires canonical_symbol")
    if not isinstance(opened_raw, str):
        raise ValueError("raw M1 row requires opened_at")
    if type(digits) is not int:
        raise ValueError("raw M1 row requires integer digits")
    if volume is not None and type(volume) is not int:
        raise ValueError("raw M1 volume must be int or null")
    parsed = datetime.fromisoformat(opened_raw)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("raw M1 opened_at must be timezone-aware")
    opened_at = parsed.astimezone(UTC)
    return CapitalizerM1Bar(
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


def iter_cibo_m1(root: Path) -> Iterator[CapitalizerM1Bar]:
    files = sorted((root / "RAW_M1_LEDGER").glob("*.jsonl"))
    if not files:
        raise ValueError("RAW_M1_LEDGER partitions not found")

    previous_at: datetime | None = None
    previous_symbol: str | None = None
    for path in files:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("raw M1 JSONL row must be object")
                bar = _bar_from_row(raw)
                if previous_symbol is not None and bar.symbol != previous_symbol:
                    raise ValueError("one M1 artifact root must contain one symbol")
                if previous_at is not None and bar.opened_at <= previous_at:
                    raise ValueError("M1 chronology must be strictly increasing")
                previous_at = bar.opened_at
                previous_symbol = bar.symbol
                yield bar
