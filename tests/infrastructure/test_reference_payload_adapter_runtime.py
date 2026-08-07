from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.ingestion import ExternalOhlcPayload, ExternalQuotePayload
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.reference_adapters import ReferenceAdapterValidationError
from qore.infrastructure.reference_payload_adapters import (
    ReferenceExternalMarketDataPayloadAdapter,
)

_NOW = datetime(2026, 8, 7, 23, 50, tzinfo=UTC)
_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e3000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("e3000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.external-reference"),
)


def test_reference_payload_adapter_rejects_non_string_quote_instrument() -> None:
    payload = ExternalQuotePayload(
        source=_DESCRIPTOR,
        instrument=cast(str, object()),
        observed_at=_NOW,
        bid="1.0",
        ask="1.1",
    )

    with pytest.raises(ReferenceAdapterValidationError, match="instrument must be a string"):
        ReferenceExternalMarketDataPayloadAdapter(
            _DESCRIPTOR,
            quotes=(payload,),
        )


def test_reference_payload_adapter_rejects_non_string_ohlc_instrument() -> None:
    payload = ExternalOhlcPayload(
        source=_DESCRIPTOR,
        instrument=cast(str, object()),
        timeframe_seconds="900",
        opened_at=_NOW,
        closed_at=_NOW,
        open="1.0",
        high="1.1",
        low="0.9",
        close="1.0",
    )

    with pytest.raises(ReferenceAdapterValidationError, match="instrument must be a string"):
        ReferenceExternalMarketDataPayloadAdapter(
            _DESCRIPTOR,
            ohlc=(payload,),
        )


def test_reference_payload_adapter_rejects_non_datetime_ohlc_interval() -> None:
    payload = ExternalOhlcPayload(
        source=_DESCRIPTOR,
        instrument="EURUSD",
        timeframe_seconds="900",
        opened_at=cast(datetime, object()),
        closed_at=_NOW,
        open="1.0",
        high="1.1",
        low="0.9",
        close="1.0",
    )

    with pytest.raises(ReferenceAdapterValidationError, match="interval values must be datetime"):
        ReferenceExternalMarketDataPayloadAdapter(
            _DESCRIPTOR,
            ohlc=(payload,),
        )
