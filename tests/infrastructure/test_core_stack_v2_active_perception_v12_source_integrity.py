from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v12_source_integrity import (
    V12SourceIntegrityError,
    audit_historical_quote_side_page,
)
from qore.infrastructure.historical_quote_side_evidence import (
    HistoricalQuoteSideObservation,
)
from qore.infrastructure.historical_quote_side_shards import (
    HistoricalQuoteSideShardSink,
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
_RETRIEVED = datetime(2026, 9, 28, 17, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("7c000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7c000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


def _observation(
    *,
    event_at: datetime,
    relative_price: int,
) -> HistoricalQuoteSideObservation:
    return HistoricalQuoteSideObservation(
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        provider_account_id=123,
        provider_symbol_id=456,
        provider_symbol="USTEC",
        quote_side=MarketPriceSide.BID,
        provider_event_at=event_at,
        retrieved_at=_RETRIEVED,
        provider_wire_timestamp_value=int(event_at.timestamp() * 1_000),
        provider_wire_price_value=relative_price,
        relative_price=relative_price,
        price=MarketPrice(Decimal(relative_price) / Decimal("10000000")),
    )


def _write_page(
    tmp_path,
    observations: tuple[HistoricalQuoteSideObservation, ...],
):
    sink = HistoricalQuoteSideShardSink(tmp_path)
    record = sink.write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=_BASE - timedelta(minutes=1),
        request_to_at=_BASE + timedelta(minutes=1),
        retrieved_at=_RETRIEVED,
        observations=observations,
    )
    return tmp_path / record.relative_path


def test_source_integrity_audits_real_raw_page_and_same_ms_updates(tmp_path) -> None:
    path = _write_page(
        tmp_path,
        (
            _observation(event_at=_BASE, relative_price=2_012_400_000),
            _observation(event_at=_BASE, relative_price=2_012_410_000),
            _observation(
                event_at=_BASE + timedelta(milliseconds=250),
                relative_price=2_012_420_000,
            ),
        ),
    )

    audited = audit_historical_quote_side_page(path)

    assert audited.side == "BID"
    assert audited.tick_count == 3
    assert audited.same_timestamp_multiupdate_groups == 1
    assert audited.same_timestamp_distinct_price_groups == 1
    assert audited.exact_same_timestamp_row_repeat_count == 0
    assert audited.max_internal_gap_ms == 250


def test_source_integrity_measures_exact_same_timestamp_row_repeat(tmp_path) -> None:
    repeated = _observation(event_at=_BASE, relative_price=2_012_400_000)
    path = _write_page(tmp_path, (repeated, repeated))

    audited = audit_historical_quote_side_page(path)

    assert audited.same_timestamp_multiupdate_groups == 1
    assert audited.exact_same_timestamp_row_repeat_count == 1


def test_source_integrity_rejects_raw_content_hash_tamper(tmp_path) -> None:
    path = _write_page(
        tmp_path,
        (_observation(event_at=_BASE, relative_price=2_012_400_000),),
    )
    rows = [
        json.loads(line)
        for line in gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()
    ]
    rows[1]["tick"]["relative_price"] += 1
    raw = ("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n").encode()
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))

    with pytest.raises(V12SourceIntegrityError, match="content hash"):
        audit_historical_quote_side_page(path)
