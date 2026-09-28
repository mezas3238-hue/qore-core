from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_foundation import (
    V12MicrostructureAvailability,
    build_v12_causal_microstructure_snapshot,
)
from qore.infrastructure.historical_quote_side_evidence import (
    HistoricalQuoteSideObservation,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketPrice, MarketPriceSide
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)

_BASE = datetime(2017, 6, 1, 14, 0, tzinfo=UTC)
_RETRIEVED = datetime(2026, 9, 28, 18, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("7d000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7d000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


def _quote(
    *,
    side: MarketPriceSide,
    event_at: datetime,
    relative_price: int,
    symbol_id: int = 456,
) -> HistoricalQuoteSideObservation:
    return HistoricalQuoteSideObservation(
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        provider_account_id=123,
        provider_symbol_id=symbol_id,
        provider_symbol="USTEC",
        quote_side=side,
        provider_event_at=event_at,
        retrieved_at=_RETRIEVED,
        provider_wire_timestamp_value=int(event_at.timestamp() * 1_000),
        provider_wire_price_value=relative_price,
        relative_price=relative_price,
        price=MarketPrice(Decimal(relative_price) / Decimal("10000000")),
    )


def test_microstructure_snapshot_uses_latest_causal_side_state() -> None:
    evaluation = _BASE + timedelta(seconds=2)
    bids = (
        _quote(
            side=MarketPriceSide.BID,
            event_at=_BASE + timedelta(milliseconds=500),
            relative_price=2_012_400_000,
        ),
        _quote(
            side=MarketPriceSide.BID,
            event_at=_BASE + timedelta(milliseconds=1_500),
            relative_price=2_012_420_000,
        ),
    )
    asks = (
        _quote(
            side=MarketPriceSide.ASK,
            event_at=_BASE + timedelta(milliseconds=700),
            relative_price=2_012_450_000,
        ),
        _quote(
            side=MarketPriceSide.ASK,
            event_at=_BASE + timedelta(milliseconds=1_700),
            relative_price=2_012_470_000,
        ),
    )

    snapshot = build_v12_causal_microstructure_snapshot(
        bid_observations=bids,
        ask_observations=asks,
        evaluation_at=evaluation,
        staleness_limit_ms=1_000,
    )

    assert snapshot.availability is V12MicrostructureAvailability.AVAILABLE
    assert snapshot.bid_age_ms == 500
    assert snapshot.ask_age_ms == 300
    assert snapshot.spread_relative_price == 50_000
    assert snapshot.side_age_skew_ms == 200
    one_second = snapshot.windows[0]
    assert one_second.bid_update_count == 1
    assert one_second.ask_update_count == 1
    assert one_second.update_imbalance_bps == 0


def test_microstructure_snapshot_does_not_force_stale_pairing() -> None:
    evaluation = _BASE + timedelta(seconds=10)
    bids = (
        _quote(
            side=MarketPriceSide.BID,
            event_at=evaluation - timedelta(milliseconds=100),
            relative_price=2_012_400_000,
        ),
    )
    asks = (
        _quote(
            side=MarketPriceSide.ASK,
            event_at=evaluation - timedelta(seconds=5),
            relative_price=2_012_450_000,
        ),
    )

    snapshot = build_v12_causal_microstructure_snapshot(
        bid_observations=bids,
        ask_observations=asks,
        evaluation_at=evaluation,
        staleness_limit_ms=1_000,
    )

    assert snapshot.availability is V12MicrostructureAvailability.INSUFFICIENT
    assert snapshot.spread_relative_price is None
    assert snapshot.crossed_quote is None
    assert snapshot.bid_age_ms == 100
    assert snapshot.ask_age_ms == 5_000


def test_microstructure_snapshot_preserves_same_ms_provider_order() -> None:
    evaluation = _BASE + timedelta(seconds=1)
    event_at = evaluation - timedelta(milliseconds=100)
    bids = (
        _quote(
            side=MarketPriceSide.BID,
            event_at=event_at,
            relative_price=2_012_400_000,
        ),
        _quote(
            side=MarketPriceSide.BID,
            event_at=event_at,
            relative_price=2_012_420_000,
        ),
    )
    asks = (
        _quote(
            side=MarketPriceSide.ASK,
            event_at=event_at,
            relative_price=2_012_450_000,
        ),
    )

    snapshot = build_v12_causal_microstructure_snapshot(
        bid_observations=bids,
        ask_observations=asks,
        evaluation_at=evaluation,
        staleness_limit_ms=1_000,
    )

    assert snapshot.bid_relative_price == 2_012_420_000
    assert snapshot.spread_relative_price == 30_000


def test_microstructure_snapshot_rejects_future_provider_event() -> None:
    evaluation = _BASE + timedelta(seconds=1)
    bids = (
        _quote(
            side=MarketPriceSide.BID,
            event_at=evaluation + timedelta(milliseconds=1),
            relative_price=2_012_400_000,
        ),
    )

    with pytest.raises(ValueError, match="future provider event"):
        build_v12_causal_microstructure_snapshot(
            bid_observations=bids,
            ask_observations=(),
            evaluation_at=evaluation,
            staleness_limit_ms=1_000,
        )


def test_microstructure_snapshot_rejects_cross_side_identity_drift() -> None:
    evaluation = _BASE + timedelta(seconds=1)
    bids = (
        _quote(
            side=MarketPriceSide.BID,
            event_at=evaluation - timedelta(milliseconds=100),
            relative_price=2_012_400_000,
        ),
    )
    asks = (
        _quote(
            side=MarketPriceSide.ASK,
            event_at=evaluation - timedelta(milliseconds=100),
            relative_price=2_012_450_000,
            symbol_id=999,
        ),
    )

    with pytest.raises(ValueError, match="different provider identity"):
        build_v12_causal_microstructure_snapshot(
            bid_observations=bids,
            ask_observations=asks,
            evaluation_at=evaluation,
            staleness_limit_ms=1_000,
        )
