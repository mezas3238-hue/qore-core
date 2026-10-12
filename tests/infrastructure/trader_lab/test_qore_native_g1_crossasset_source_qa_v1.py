"""Synthetic unit gates for strict two-symbol genuine-source postcollection QA."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_crossasset_source_qa_v1 as q


def test_frozen_real_origin_scopes_and_sha_digest():
    assert q.SOURCE_RUN == 38282585181
    assert q.SOURCE_HEAD == "626909b960525dbf3ca0c7ab0a554b56d03c0170"
    assert q.SYMBOL_ARTIFACT["SP500"]["provider"] == "US500"
    assert len(q.WINDOWS) == 3
    assert len(q.SYMBOL_ARTIFACT["XAGUSD"]["zip_sha256"]) == 64


def test_asof_states_exhaustive_not_pnl():
    bid = [(0, 100000), (2000, 100005), (4000, 100030)]
    ask = [(1000, 100020), (3000, 100005), (5000, 100010)]
    x = q.asof_quality(bid, ask)
    assert x["source_distinct_asof_instants"] == 6
    assert x["quality_counts"] == {
        "missing_side": 1, "stale_side": 0, "crossed_spread": 2,
        "zero_spread": 1, "positive_spread": 2,
    }
    assert x["positive_spread_p50_bps"] is not None
    assert x["NET_economics_measured"] is False


def test_asof_staleness_quarantined_not_midpoint():
    x = q.asof_quality([(0, 100000)], [(1000, 100010), (20000, 100010)])
    assert x["quality_counts"]["missing_side"] == 1
    assert x["quality_counts"]["stale_side"] == 1
    assert x["quality_counts"]["positive_spread"] == 1


def test_asof_empty_source_rejected():
    with pytest.raises(ValueError, match="MISSING_BID_OR_ASK"):
        q.asof_quality([], [(1, 200000)])


def test_exact_witness_register_and_mutation_detection(tmp_path: Path):
    names = ["SOURCE-CROSSASSET-NOT-NET.json"] + [
        f"test-side-{n}.jsonl" for n in range(12)
    ]
    for name in names:
        (tmp_path / name).write_text(name + "\n")
    (tmp_path / "OUTPUT_SHA256SUMS.txt").write_text(
        "".join(hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
                + "  " + name + "\n" for name in names)
    )
    assert len(q._verified_files(tmp_path)) == 13
    (tmp_path / names[-1]).write_text("tampered")
    with pytest.raises(ValueError, match="ORIGINAL_SHA_MISMATCH"):
        q._verified_files(tmp_path)
    (tmp_path / names[-1]).write_text(names[-1] + "\n")
    (tmp_path / "extra.jsonl").write_text("injected")
    with pytest.raises(ValueError, match="FILES_NOT_EXACT"):
        q._verified_files(tmp_path)


def test_price_integer_to_decimal_is_exact_not_float(tmp_path: Path):
    a = [{"epoch_ms": 1600174800000, "integer_price_1e5": 2700010}]
    b = [{"event_time_utc": "2020-09-15T13:00:00.000Z",
          "native_sequence": 0, "price": "27.00010"}]
    n = tmp_path / "xagusd-1-BID-integer.jsonl"
    d = tmp_path / "xagusd-1-BID-decoded.jsonl"
    n.write_text(json.dumps(a[0]) + "\n")
    d.write_text(json.dumps(b[0]) + "\n")
    meta = {
        "native_int_file": n.name, "decoded_file": d.name,
        "native_int_sha256": q.sha(n.read_bytes()),
        "decoded_sha256": q.sha(d.read_bytes()),
        "native_tick_count": 1, "historical_provider_requests": 1,
    }
    values, ties = q._side(tmp_path, meta, "XAGUSD", 1, "BID", 1600174800000, 1600175400000)
    assert values == [(1600174800000, 2700010)] and ties == 0
    b[0]["price"] = "27.00009"
    d.write_text(json.dumps(b[0]) + "\n")
    meta["decoded_sha256"] = q.sha(d.read_bytes())
    with pytest.raises(ValueError, match="NATIVE_PRICE_MISMATCH"):
        q._side(tmp_path, meta, "XAGUSD", 1, "BID", 1600174800000, 1600175400000)


def test_same_ms_conflicting_prices_cannot_reconstruct_causal_order(tmp_path: Path):
    base = 1600174800000
    na = [{"epoch_ms": base, "integer_price_1e5": 1234567},
          {"epoch_ms": base, "integer_price_1e5": 1234568}]
    de = [{"event_time_utc": "2020-09-15T13:00:00.000Z",
           "native_sequence": i, "price": str(x["integer_price_1e5"] / 100000)}
          for i, x in enumerate(na)]
    n = tmp_path / "sp500-1-ASK-integer.jsonl"
    d = tmp_path / "sp500-1-ASK-decoded.jsonl"
    n.write_text("\n".join(json.dumps(x) for x in na) + "\n")
    d.write_text("\n".join(json.dumps(x) for x in de) + "\n")
    meta = {
        "native_int_file": n.name, "decoded_file": d.name,
        "native_int_sha256": q.sha(n.read_bytes()), "decoded_sha256": q.sha(d.read_bytes()),
        "native_tick_count": 2, "historical_provider_requests": 1,
    }
    with pytest.raises(ValueError, match="SAME_MS_CONFLICTING_PRICE"):
        q._side(tmp_path, meta, "SP500", 1, "ASK", base, base+600000)


def test_unverified_non_target_market_must_not_pass(tmp_path: Path):
    with pytest.raises(ValueError, match="OUT_OF_SCOPE"):
        q.audit_symbol(tmp_path, "NAS100")
