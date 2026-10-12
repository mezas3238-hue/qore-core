"""Source-only negative regression tests for 29 genuine broker side streams."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_remaining29_independent_qa_v1 as a


def test_universe_29_and_original_digest_are_pinned():
    assert len(a.FROZEN_TARGETS) == 29
    assert a.ORIGINAL_RUN == 38283737706
    assert a.ORIGINAL_ARTIFACT_ID == 11762222336
    assert a.ORIGINAL_ZIP_SHA256 == "be123f91e2069390e3bb44f9ce8b9398e3216b9ce483b7441f7f2aebb918f1c0"


def test_causal_asof_no_future_zero_not_free_spread():
    bid = [(0, 100000), (2000, 100005), (4000, 100030)]
    ask = [(1000, 100020), (3000, 100005), (5000, 100010)]
    r = a.source_asof(bid, ask)
    assert r["quality_counts"] == {
        "missing_side": 1, "stale_side": 0,
        "crossed_spread": 2, "zero_spread": 1,
        "positive_spread": 2,
    }
    assert r["historical_order_cost_measured"] is False


def test_source_stale_and_missing_are_not_valid_observations():
    r = a.source_asof([(0, 100000)], [(1000, 100010), (8000, 100020)])
    assert r["quality_counts"]["missing_side"] == 1
    assert r["quality_counts"]["stale_side"] == 1
    assert r["quality_counts"]["positive_spread"] == 1


def test_tampered_sha_fails(tmp_path: Path):
    orig = tmp_path / "test.json"
    orig.write_bytes(b'{"source":true}\n')
    (tmp_path / "SOURCE_SHA256SUMS.txt").write_text(a.sha(orig.read_bytes())+"  test.json\n")
    assert len(a.check_register(tmp_path, "SOURCE_SHA256SUMS.txt", 1)) == 1
    orig.write_text('{"source":false}\n')
    with pytest.raises(ValueError, match="SOURCE_SHA_MISMATCH"):
        a.check_register(tmp_path, "SOURCE_SHA256SUMS.txt", 1)


def test_unattested_extra_file_fails(tmp_path: Path):
    (tmp_path / "SOURCE_SHA256SUMS.txt").write_text("")
    (tmp_path / "extra.jsonl").write_text("inject\n")
    with pytest.raises(ValueError, match="SOURCE_FILE_SET_UNVERIFIED"):
        a.check_register(tmp_path, "SOURCE_SHA256SUMS.txt", 1)


def test_decimal_integer_source_trace_and_timestamp_are_exact(tmp_path: Path):
    at = 1600174800000
    native = tmp_path / "EURUSD-1-BID-integer.jsonl"
    decoded = tmp_path / "EURUSD-1-BID-decoded.jsonl"
    native.write_text(json.dumps({"epoch_ms": at, "integer_price_1e5": 110012}) + "\n")
    decoded.write_text(json.dumps({"event_time_utc": "2020-09-15T13:00:00.000Z",
                                   "native_sequence": 0, "price": "1.10012"}) + "\n")
    meta = {
        "native_int_file": native.name, "decoded_file": decoded.name,
        "native_int_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
        "decoded_sha256": hashlib.sha256(decoded.read_bytes()).hexdigest(),
        "native_tick_count": 1, "historical_provider_requests": 1,
    }
    rows, repeated = a.audit_side(tmp_path, "EURUSD", 1, "BID", meta, at, at+600000)
    assert rows == [(at, 110012)]
    assert repeated == 0
    decoded.write_text(json.dumps({"event_time_utc": "2020-09-15T13:00:00.000Z",
                                   "native_sequence": 0, "price": "1.10013"}) + "\n")
    meta["decoded_sha256"] = hashlib.sha256(decoded.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="SOURCE_DECODER_DECIMAL_MISMATCH"):
        a.audit_side(tmp_path, "EURUSD", 1, "BID", meta, at, at+600000)


def test_unavailable_original_source_does_not_pass(tmp_path: Path):
    with pytest.raises(ValueError, match="SOURCE_SHA_REGISTER_MISSING"):
        a.audit(tmp_path)


def test_same_ms_opposite_price_is_ambiguous_not_auto_sorted(tmp_path: Path):
    epoch = 1600174800000
    ints = [{"epoch_ms": epoch, "integer_price_1e5": 100000},
            {"epoch_ms": epoch, "integer_price_1e5": 100001}]
    dec = [{"event_time_utc": "2020-09-15T13:00:00.000Z",
            "native_sequence": i, "price": str(row["integer_price_1e5"]/100000)}
           for i, row in enumerate(ints)]
    source = tmp_path / "EURUSD-1-ASK-integer.jsonl"
    decoded = tmp_path / "EURUSD-1-ASK-decoded.jsonl"
    source.write_text("\n".join(json.dumps(x) for x in ints) + "\n")
    decoded.write_text("\n".join(json.dumps(x) for x in dec) + "\n")
    meta = {
        "native_int_file": source.name, "decoded_file": decoded.name,
        "native_int_sha256": a.sha(source.read_bytes()),
        "decoded_sha256": a.sha(decoded.read_bytes()),
        "native_tick_count": 2, "historical_provider_requests": 1,
    }
    with pytest.raises(ValueError, match="SAME_MILLISECOND_PRICE_ORDER_AMBIGUOUS"):
        a.audit_side(tmp_path, "EURUSD", 1, "ASK", meta, epoch, epoch + 600000)
