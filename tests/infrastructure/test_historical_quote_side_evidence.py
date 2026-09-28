from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure import ctrader_historical_tick_data as tick_data
from qore.infrastructure.historical_quote_side_evidence import (
    HistoricalQuoteSideEvidenceError,
    HistoricalQuoteSideObservation,
    retain_ctrader_historical_quote_side_page,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketPrice, MarketPriceSide
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)

_BASE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("78000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("78000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


@dataclass(frozen=True)
class NativeTick:
    timestamp: int
    tick: int


def _page(
    quote_type: tick_data.CTraderQuoteType,
) -> tick_data.CTraderHistoricalTickPage:
    request = tick_data.CTraderHistoricalTickRequest(
        account_id=123,
        symbol_id=456,
        quote_type=quote_type,
        from_at=_BASE,
        to_at=_BASE + timedelta(hours=1),
    )
    newest = _BASE + timedelta(minutes=10)
    return tick_data.decode_historical_tick_page(
        request=request,
        native_ticks=(
            NativeTick(int(newest.timestamp() * 1_000), 2_012_410_000),
            NativeTick(-250, 2_012_400_000),
        ),
        has_more=False,
        digits=2,
    )


def test_historical_observation_keeps_provider_and_retrieval_time_distinct() -> None:
    retrieved_at = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    retained = retain_ctrader_historical_quote_side_page(
        page=_page(tick_data.CTraderQuoteType.BID),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        provider_symbol="NAS100",
        retrieved_at=retrieved_at,
    )

    assert len(retained) == 2
    assert all(item.quote_side is MarketPriceSide.BID for item in retained)
    assert all(item.retrieved_at == retrieved_at for item in retained)
    assert retained[0].replay_available_at == retained[0].provider_event_at
    assert retained[0].provider_event_at != retained[0].retrieved_at


def test_bid_page_does_not_invent_or_pair_an_ask() -> None:
    retained = retain_ctrader_historical_quote_side_page(
        page=_page(tick_data.CTraderQuoteType.BID),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        provider_symbol="NAS100",
        retrieved_at=datetime(2026, 9, 28, 12, 0, tzinfo=UTC),
    )

    assert {item.quote_side for item in retained} == {MarketPriceSide.BID}
    assert all(not hasattr(item, "ask") for item in retained)


def test_ask_page_remains_independent_ask_stream() -> None:
    retained = retain_ctrader_historical_quote_side_page(
        page=_page(tick_data.CTraderQuoteType.ASK),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        provider_symbol="NAS100",
        retrieved_at=datetime(2026, 9, 28, 12, 0, tzinfo=UTC),
    )

    assert {item.quote_side for item in retained} == {MarketPriceSide.ASK}


def test_retrieval_cannot_be_falsely_backdated_before_provider_event() -> None:
    page = _page(tick_data.CTraderQuoteType.BID)

    with pytest.raises(
        HistoricalQuoteSideEvidenceError,
        match="must not predate provider_event_at",
    ):
        retain_ctrader_historical_quote_side_page(
            page=page,
            instrument=Instrument("NAS100"),
            source=_SOURCE,
            provider_symbol="NAS100",
            retrieved_at=_BASE,
        )


def test_historical_side_boundary_rejects_mid_price_identity() -> None:
    with pytest.raises(
        HistoricalQuoteSideEvidenceError,
        match="must be BID or ASK",
    ):
        HistoricalQuoteSideObservation(
            instrument=Instrument("NAS100"),
            source=_SOURCE,
            provider_account_id=123,
            provider_symbol_id=456,
            provider_symbol="NAS100",
            quote_side=MarketPriceSide.MID,
            provider_event_at=_BASE,
            retrieved_at=_BASE + timedelta(days=1),
            relative_price=2_012_400_000,
            price=MarketPrice(Decimal("20124.00")),
        )
