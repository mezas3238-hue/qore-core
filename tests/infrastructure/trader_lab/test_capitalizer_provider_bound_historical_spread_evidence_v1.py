from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_provider_bound_historical_spread_evidence_v1 as evidence,
)


@dataclass(frozen=True)
class Tick:
    timestamp: int
    tick: int


def test_absolute_first_tick_is_latest_provider_quote() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    observed = target - timedelta(milliseconds=1250)
    ticks = (
        Tick(int(observed.timestamp() * 1000), 108765),
        Tick(-500, -1),
    )

    row = evidence._absolute_first_tick(
        ticks,
        quote_type="BID",
        target_at=target,
        digits=5,
        has_more=False,
    )

    assert row.observed_at == observed.isoformat()
    assert row.age_ms == 1250
    assert row.price == "1.08765"
    assert row.source_tick_count == 2
    assert row.provider_native is True
    assert row.future_quote_used is False
    assert row.interpolation_used is False
    assert row.synthetic_quote_used is False


def test_absolute_first_tick_rejects_future_quote() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    ticks = (
        Tick(int((target + timedelta(milliseconds=1)).timestamp() * 1000), 108765),
    )
    with pytest.raises(ValueError, match="future quote"):
        evidence._absolute_first_tick(
            ticks,
            quote_type="ASK",
            target_at=target,
            digits=5,
            has_more=False,
        )


def test_absolute_first_tick_rejects_quote_older_than_30s() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    ticks = (
        Tick(int((target - timedelta(seconds=31)).timestamp() * 1000), 108765),
    )
    with pytest.raises(ValueError, match="exceeds max age"):
        evidence._absolute_first_tick(
            ticks,
            quote_type="BID",
            target_at=target,
            digits=5,
            has_more=False,
        )


def test_spread_row_requires_non_crossed_provider_quotes() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    bid = evidence.HistoricalQuote(
        quote_type="BID",
        observed_at=target.isoformat(),
        age_ms=0,
        price="1.10000",
        source_tick_count=1,
        response_has_more=False,
    )
    ask = evidence.HistoricalQuote(
        quote_type="ASK",
        observed_at=target.isoformat(),
        age_ms=0,
        price="1.10020",
        source_tick_count=1,
        response_has_more=False,
    )
    row = evidence.SpreadEvidenceRow(
        period="CONSUMED_VALIDATION_2022_2024",
        canonical_symbol="EURUSD",
        provider_symbol="EURUSD",
        provider_symbol_id=1,
        digits=5,
        side="LONG",
        entrant_entry_at=target.isoformat(),
        event="ENTRY",
        event_at=target.isoformat(),
        structural_risk_price="0.00100",
        bid=bid,
        ask=ask,
        spread_price="0.00020",
        spread_over_structural_risk=str(
            Decimal("0.00020") / Decimal("0.00100")
        ),
    )
    assert Decimal(row.spread_over_structural_risk) == Decimal("0.2")
