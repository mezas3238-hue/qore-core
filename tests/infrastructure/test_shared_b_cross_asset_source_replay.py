from __future__ import annotations

import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_cross_asset_source_replay import (
    FROZEN_PILOT_INDICES,
    SharedBCrossAssetReplayError,
    classify_verified_window_counts,
    raw_dataset_digest,
    verify_historical_quote_shard,
)
from qore.infrastructure.historical_quote_side_shards import (
    HistoricalQuoteSideShardSink,
)
from qore.infrastructure.market_observation import MarketPriceSide


def _expected(record: object) -> dict[str, object]:
    return {
        "quote_side": record.quote_side.value,
        "window_index": record.window_index,
        "page_index": record.page_index,
        "request_from_at": record.request_from_at.isoformat(
            timespec="microseconds"
        ),
        "request_to_at": record.request_to_at.isoformat(
            timespec="microseconds"
        ),
        "retrieved_at": record.retrieved_at.isoformat(
            timespec="microseconds"
        ),
        "tick_count": record.tick_count,
        "content_sha256": record.content_sha256,
        "provenance_sha256": record.provenance_sha256,
        "relative_path": record.relative_path,
    }


def test_shared_b_raw_shard_verifies_from_sealed_bytes(tmp_path) -> None:
    root = tmp_path / "data"
    sink = HistoricalQuoteSideShardSink(root)
    start = datetime(2017, 1, 3, 12, 0, tzinfo=UTC)
    record = sink.write_page(
        quote_side=MarketPriceSide.BID,
        window_index=0,
        page_index=0,
        request_from_at=start,
        request_to_at=start + timedelta(minutes=1),
        retrieved_at=datetime(2026, 9, 30, 16, 0, tzinfo=UTC),
        observations=(),
    )

    verified = verify_historical_quote_shard(
        path=root / record.relative_path,
        expected=_expected(record),
    )

    assert verified.quote_side == "BID"
    assert verified.window_index == 0
    assert verified.tick_count == 0
    digest = raw_dataset_digest(
        provider_symbol="US2000",
        shards=(verified,),
    )
    expected_payload = [
        (
            "US2000",
            "bid",
            0,
            0,
            0,
            record.content_sha256,
        )
    ]
    expected = hashlib.sha256(
        json.dumps(
            expected_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    assert digest == expected


def test_shared_b_raw_shard_tamper_fails_closed(tmp_path) -> None:
    root = tmp_path / "data"
    sink = HistoricalQuoteSideShardSink(root)
    start = datetime(2017, 1, 3, 12, 0, tzinfo=UTC)
    record = sink.write_page(
        quote_side=MarketPriceSide.ASK,
        window_index=0,
        page_index=0,
        request_from_at=start,
        request_to_at=start + timedelta(minutes=1),
        retrieved_at=datetime(2026, 9, 30, 16, 0, tzinfo=UTC),
        observations=(),
    )
    path = root / record.relative_path
    lines = gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()
    header = json.loads(lines[0])
    header["header"]["tick_count"] = 1
    lines[0] = json.dumps(header, sort_keys=True)
    path.write_bytes(
        gzip.compress(
            ("\n".join(lines) + "\n").encode("utf-8"),
            compresslevel=9,
            mtime=0,
        )
    )

    with pytest.raises(
        SharedBCrossAssetReplayError,
        match="tick count mismatch",
    ):
        verify_historical_quote_shard(
            path=path,
            expected=_expected(record),
        )


def test_shared_b_frozen_coverage_classification() -> None:
    full = {
        index: {"BID": 10, "ASK": 11}
        for index in FROZEN_PILOT_INDICES
    }
    assert classify_verified_window_counts(full).value == (
        "full_bid_ask_history"
    )

    partial = {
        index: {"BID": 10, "ASK": 11}
        for index in FROZEN_PILOT_INDICES
    }
    partial[FROZEN_PILOT_INDICES[2]]["ASK"] = 0
    assert classify_verified_window_counts(partial).value == (
        "partial_bid_ask_history"
    )

    none = {
        index: {"BID": 0, "ASK": 0}
        for index in FROZEN_PILOT_INDICES
    }
    assert classify_verified_window_counts(none).value == "no_history"


def test_shared_b_coverage_rejects_missing_frozen_window() -> None:
    counts = {
        index: {"BID": 1, "ASK": 1}
        for index in FROZEN_PILOT_INDICES[:-1]
    }
    with pytest.raises(
        SharedBCrossAssetReplayError,
        match="frozen pilot windows",
    ):
        classify_verified_window_counts(counts)
