"""Offline bridge: sanitized cTrader M5 trendbars to the SMT census CSV contract.

Pure formatting only. Does NOT open a network connection, request private
credentials, infer broker identity, retrieve more pages or emit trade signals.
The upstream authenticated DEMO client remains responsible for market custody.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from io import StringIO
from typing import Final

from qore.infrastructure.ctrader_demo_market_data import (
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
)
from qore.infrastructure.trader_lab.index_smt_census import (
    BROKER,
    CSV_FIELDS,
    ENVIRONMENT,
    ORIGIN,
    SMTExportError,
)
from qore.infrastructure.trader_lab.index_smt_research import SYMBOLS, Symbol

RELATIVE_PRICE_SCALE: Final[Decimal] = Decimal("100000")
PERIOD: Final[timedelta] = timedelta(minutes=5)


def _relative_price(value: int, *, digits: int) -> str:
    if type(value) is not int or value <= 0:
        raise SMTExportError("cTrader relative price must be positive")
    try:
        quantum = Decimal(1).scaleb(-digits)
        result = (Decimal(value) / RELATIVE_PRICE_SCALE).quantize(
            quantum, rounding=ROUND_HALF_EVEN
        )
    except (InvalidOperation, ValueError) as exc:
        raise SMTExportError("cTrader relative price normalization failed") from exc
    if not result.is_finite() or result <= 0:
        raise SMTExportError("cTrader normalized price is not finite/positive")
    return format(result, f".{digits}f")


def encode_sanitized_ctrader_m5(
    result: CTraderTrendbarReadResult,
    *,
    canonical_symbol: Symbol,
    runtime_instrument: str,
    broker_symbol: str,
    broker_symbol_id: int,
    broker_digits: int,
    server: str,
    observed_at: datetime,
) -> str:
    """Encode a provider-result batch, checking exact broker mapping and closure.

    `observed_at` is the authorized observation clock. A candle is only
    admitted when its entire five-minute interval has closed at that clock.
    The resulting string can be passed to load_ctrader_m5_export unchanged.
    """
    if not isinstance(result, CTraderTrendbarReadResult):
        raise SMTExportError("cTrader result type mismatch")
    if canonical_symbol not in SYMBOLS or not runtime_instrument:
        raise SMTExportError("unsupported SMT symbol or missing runtime instrument")
    if not broker_symbol or broker_symbol.strip() != broker_symbol:
        raise SMTExportError("missing exact broker-symbol mapping")
    if not server or server.strip() != server:
        raise SMTExportError("missing explicit cTrader DEMO server identity")
    if (
        type(broker_symbol_id) is not int
        or broker_symbol_id <= 0
        or type(broker_digits) is not int
        or broker_digits < 0
    ):
        raise SMTExportError("invalid expected symbol ID or price digits")
    if observed_at.tzinfo is None or observed_at.utcoffset() != timedelta(0):
        raise SMTExportError("observation clock must be explicit UTC")
    if (
        result.instrument != runtime_instrument
        or result.symbol_id != broker_symbol_id
        or result.digits != broker_digits
    ):
        raise SMTExportError("cTrader runtime mapping/precision mismatch")
    if result.period is not CTraderTrendbarPeriod.M5:
        raise SMTExportError("cTrader trendbars must be native M5")
    if result.has_more:
        raise SMTExportError("truncated cTrader historical result; pagination is required")
    if not result.trendbars:
        raise SMTExportError("cTrader returned no M5 trendbars")

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    previous_at: datetime | None = None
    for trendbar in result.trendbars:
        try:
            opened_at = datetime.fromtimestamp(
                trendbar.utc_timestamp_in_minutes * 60, tz=UTC
            )
        except (OverflowError, OSError, ValueError) as exc:
            raise SMTExportError("cTrader M5 timestamp is out of range") from exc
        if opened_at.minute % 5 or opened_at.second:
            raise SMTExportError("cTrader M5 source timestamp is off-grid")
        if previous_at is not None and opened_at <= previous_at:
            raise SMTExportError("cTrader M5 batch is unordered or contains duplicates")
        if opened_at + PERIOD > observed_at:
            raise SMTExportError("a not-yet-closed cTrader M5 bar was supplied")
        previous_at = opened_at

        low = trendbar.low_relative
        values = {
            "open": _relative_price(low + trendbar.delta_open, digits=result.digits),
            "high": _relative_price(low + trendbar.delta_high, digits=result.digits),
            "low": _relative_price(low, digits=result.digits),
            "close": _relative_price(low + trendbar.delta_close, digits=result.digits),
        }
        writer.writerow({
            "origin": ORIGIN,
            "broker": BROKER,
            "environment": ENVIRONMENT,
            "server": server,
            "canonical_symbol": canonical_symbol,
            "broker_symbol": broker_symbol,
            "open_time_utc": opened_at.isoformat(),
            **values,
            "closed": "true",
        })
    return output.getvalue()
