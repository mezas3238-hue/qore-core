from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    MarketBarOrigin,
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketObservationValidationError,
    MarketOhlcField,
    MarketOhlcFieldValidity,
    MarketPrice,
    MarketPriceSide,
    MarketTimeframe,
    MarketTimeframeCode,
    QualifiedOhlcBarObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1)),
        source_id=SourceId(_uuid(2)),
        port_name=PortName("market-data.test"),
    )


def _valid(value: str) -> MarketOhlcField:
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=MarketPrice(Decimal(value)),
    )


def _missing() -> MarketOhlcField:
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.MISSING,
        price=None,
    )


def _bar(
    *,
    open_field: MarketOhlcField,
    high_field: MarketOhlcField,
    low_field: MarketOhlcField,
    close_field: MarketOhlcField,
) -> QualifiedOhlcBarObservation:
    opened_at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(10)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        timeframe=MarketTimeframe(MarketTimeframeCode.M5),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=open_field,
        high=high_field,
        low=low_field,
        close=close_field,
        evidence_ref=MarketObservationEvidenceReference(_uuid(11)),
    )


@pytest.mark.parametrize(
    ("open_field", "high_field", "low_field", "close_field"),
    [
        (_valid("1.50000"), _valid("1.00000"), _missing(), _valid("0.99000")),
        (_valid("0.99000"), _valid("1.00000"), _missing(), _valid("1.20000")),
        (_valid("0.80000"), _missing(), _valid("1.00000"), _valid("1.01000")),
        (_valid("1.01000"), _missing(), _valid("1.00000"), _valid("0.85000")),
    ],
)
def test_bar_rejects_pairwise_range_conflict_when_other_extreme_is_missing(
    open_field: MarketOhlcField,
    high_field: MarketOhlcField,
    low_field: MarketOhlcField,
    close_field: MarketOhlcField,
) -> None:
    with pytest.raises(MarketObservationValidationError):
        _bar(
            open_field=open_field,
            high_field=high_field,
            low_field=low_field,
            close_field=close_field,
        )
