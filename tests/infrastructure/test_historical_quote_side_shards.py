from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.historical_quote_side_evidence import (
    HistoricalQuoteSideObservation,
)
from qore.infrastructure.historical_quote_side_shards import (
    HistoricalQuoteSideShardSink,
    historical_shard_dataset_digest,
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
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("7a000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7a000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


def _observation(
    *,
    observed_at: datetime,
    retrieved_at: datetime,
    relative_price: int,
    wire_timestamp_value: int | None = None,
    wire_price_value: int | None = None,
) -> HistoricalQuoteSideObservation:
    return HistoricalQuoteSideObservation(
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        provider_account_id=123,
        provider_symbol_id=456,
        provider_symbol="USTEC",
        quote_side=MarketPriceSide.BID,
        provider_event_at=observed_at,
        retrieved_at=retrieved_at,
        provider_wire_timestamp_value=(
            int(observed_at.timestamp() * 1_000)
            if wire_timestamp_value is None
            else wire_timestamp_value
        ),
        provider_wire_price_value=(
            relative_price if wire_price_value is None else wire_price_value
        ),
        relative_price=relative_price,
        price=MarketPrice(Decimal(relative_price) / Decimal("10000000")),
    )


def test_shard_content_identity_excludes_retrieval_time(tmp_path) -> None:
    first_time = _BASE + timedelta(days=1)
    second_time = _BASE + timedelta(days=2)
    events = (
        (_BASE, 2012400000),
        (_BASE + timedelta(milliseconds=250), 2012410000),
    )

    first = HistoricalQuoteSideShardSink(tmp_path / "first").write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=first_time,
        observations=tuple(
            _observation(
                observed_at=event_at,
                retrieved_at=first_time,
                relative_price=price,
            )
            for event_at, price in events
        ),
    )
    second = HistoricalQuoteSideShardSink(tmp_path / "second").write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=second_time,
        observations=tuple(
            _observation(
                observed_at=event_at,
                retrieved_at=second_time,
                relative_price=price,
            )
            for event_at, price in events
        ),
    )

    assert first.content_sha256 == second.content_sha256
    assert first.provenance_sha256 != second.provenance_sha256


def test_dataset_digest_is_stable_across_retrieval_provenance(tmp_path) -> None:
    event_at = _BASE
    first_time = _BASE + timedelta(days=1)
    second_time = _BASE + timedelta(days=2)

    first = HistoricalQuoteSideShardSink(tmp_path / "first").write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=first_time,
        observations=(
            _observation(
                observed_at=event_at,
                retrieved_at=first_time,
                relative_price=2012400000,
            ),
        ),
    )
    second = HistoricalQuoteSideShardSink(tmp_path / "second").write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=second_time,
        observations=(
            _observation(
                observed_at=event_at,
                retrieved_at=second_time,
                relative_price=2012400000,
            ),
        ),
    )

    assert historical_shard_dataset_digest((first,)) == (
        historical_shard_dataset_digest((second,))
    )


def test_shard_sink_fails_closed_on_overwrite(tmp_path) -> None:
    sink = HistoricalQuoteSideShardSink(tmp_path)
    retrieved_at = _BASE + timedelta(days=1)
    kwargs = dict(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=retrieved_at,
        observations=(
            _observation(
                observed_at=_BASE,
                retrieved_at=retrieved_at,
                relative_price=2012400000,
            ),
        ),
    )

    sink.write_page(**kwargs)

    import pytest

    with pytest.raises(FileExistsError):
        sink.write_page(**kwargs)


def test_shard_preserves_same_millisecond_provider_event_order(tmp_path) -> None:
    retrieved_at = _BASE + timedelta(days=1)
    observations = (
        _observation(
            observed_at=_BASE,
            retrieved_at=retrieved_at,
            relative_price=2012420000,
        ),
        _observation(
            observed_at=_BASE,
            retrieved_at=retrieved_at,
            relative_price=2012400000,
        ),
    )
    sink = HistoricalQuoteSideShardSink(tmp_path)
    record = sink.write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=retrieved_at,
        observations=observations,
    )

    raw = gzip.decompress((tmp_path / record.relative_path).read_bytes()).decode()
    rows = [json.loads(line) for line in raw.splitlines()]
    retained_prices = [
        row["tick"]["relative_price"]
        for row in rows
        if "tick" in row
    ]

    assert retained_prices == [2012420000, 2012400000]


def test_shard_rejects_non_chronological_observations(tmp_path) -> None:
    import pytest

    retrieved_at = _BASE + timedelta(days=1)
    with pytest.raises(ValueError, match="already be chronological"):
        HistoricalQuoteSideShardSink(tmp_path).write_page(
            quote_side=MarketPriceSide.BID,
            window_index=0,
            page_index=0,
            request_from_at=_BASE - timedelta(minutes=1),
            request_to_at=_BASE + timedelta(minutes=1),
            retrieved_at=retrieved_at,
            observations=(
                _observation(
                    observed_at=_BASE + timedelta(milliseconds=1),
                    retrieved_at=retrieved_at,
                    relative_price=2012410000,
                ),
                _observation(
                    observed_at=_BASE,
                    retrieved_at=retrieved_at,
                    relative_price=2012400000,
                ),
            ),
        )


def test_shard_persists_wire_deltas_and_decoded_price(tmp_path) -> None:
    retrieved_at = _BASE + timedelta(days=1)
    observations = (
        _observation(
            observed_at=_BASE,
            retrieved_at=retrieved_at,
            relative_price=2_012_400_000,
            wire_timestamp_value=-250,
            wire_price_value=-10_000,
        ),
    )
    sink = HistoricalQuoteSideShardSink(tmp_path)
    record = sink.write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=retrieved_at,
        observations=observations,
    )

    raw = gzip.decompress((tmp_path / record.relative_path).read_bytes()).decode()
    rows = [json.loads(line) for line in raw.splitlines()]
    assert rows[0]["header"]["schema"] == (
        "qore.shared.wp05.v12.historical_quote_side_shard.v2"
    )
    tick = next(row["tick"] for row in rows if "tick" in row)
    assert tick["provider_wire_timestamp_value"] == -250
    assert tick["provider_wire_price_value"] == -10_000
    assert tick["relative_price"] == 2_012_400_000
