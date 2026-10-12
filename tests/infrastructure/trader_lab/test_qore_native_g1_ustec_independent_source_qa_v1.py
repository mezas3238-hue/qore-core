"""Negative source-only USTEC alias proof audits; no live broker calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_ustec_independent_source_qa_v1 as q


def test_source_identity_immutable_and_alias_blocked():
    assert q.SOURCE_RUN == 38285063753
    assert q.SOURCE_ARTIFACT == 11762668603
    assert q.SOURCE_SHA == "1626667cb8a2ac40702a021e8422d9fdec252e75"
    assert len(q.WINDOWS) == 3


def test_asof_zero_and_crossed_not_free():
    b = [(0, 100000), (2000, 100005), (4000, 100030)]
    a = [(1000, 100020), (3000, 100005), (5000, 100010)]
    assert q.asof_qa(b, a) == {
        "missing_side": 1, "stale_side": 0,
        "crossed_spread": 2, "zero_spread": 1,
        "positive_spread": 2,
    }


def test_stale_quote_not_forward_filled():
    out = q.asof_qa([(0, 100000)], [(1000, 100010), (8000, 100020)])
    assert out["missing_side"] == 1
    assert out["stale_side"] == 1


def test_sha_bytes_tampering_fails(tmp_path: Path):
    names = ["USTEC-CANDIDATE-SOURCE-NOT-NET.json"] + [f"test-{x}.jsonl" for x in range(12)]
    for name in names:
        (tmp_path / name).write_text(name+"\n")
    (tmp_path / "SHA256SUMS.txt").write_text("".join(
        hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()+"  "+name+"\n"
        for name in names
    ))
    assert len(q._files(tmp_path)) == 13
    (tmp_path / names[0]).write_text("TAMPER")
    with pytest.raises(ValueError, match="BYTES_SHA_MISMATCH"):
        q._files(tmp_path)


def test_decode_integer_price_cannot_change(tmp_path: Path):
    n = tmp_path / "USTEC-1-BID-integer.jsonl"
    d = tmp_path / "USTEC-1-BID-decoded.jsonl"
    epoch = 1600174800000
    n.write_text(json.dumps({"epoch_ms": epoch, "integer_price_1e5": 1135000000})+"\n")
    d.write_text(json.dumps({"event_time_utc": "2020-09-15T13:00:00.000Z",
                             "native_sequence": 0, "price": "11350"})+"\n")
    meta = {"integer_file": n.name, "decoded_file": d.name,
            "integer_sha256": q._sha(n.read_bytes()),
            "decoded_sha256": q._sha(d.read_bytes()),
            "count": 1, "requests": 1}
    assert q._side(tmp_path, meta, 1, "BID", epoch, epoch+600000) == [(epoch, 1135000000)]
    d.write_text(json.dumps({"event_time_utc": "2020-09-15T13:00:00.000Z",
                             "native_sequence": 0, "price": "11350.01"})+"\n")
    meta["decoded_sha256"] = q._sha(d.read_bytes())
    with pytest.raises(ValueError, match="PRICE_MISMATCH"):
        q._side(tmp_path, meta, 1, "BID", epoch, epoch+600000)


def test_empty_original_artifact_cannot_pass(tmp_path: Path):
    with pytest.raises(ValueError, match="SHA_REGISTER_MISSING"):
        q.audit(tmp_path)
