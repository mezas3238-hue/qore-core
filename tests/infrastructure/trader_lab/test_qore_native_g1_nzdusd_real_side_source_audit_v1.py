"""G1 NZDUSD independent source-quality checks, synthetic inputs only."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_nzdusd_real_side_source_audit_v1 as a


def test_asof_positive_crossed_and_zero_are_separate_not_net():
    bid = [(0, 100000), (2000, 100005), (4000, 100020)]
    ask = [(1000, 100020), (3000, 100005), (5000, 100010)]
    out = a.asof_spot_quality(bid, ask)
    assert out["combined_distinct_source_instants"] == 6
    assert out["incomplete_one_side"] == 1
    assert out["positive_spread_source_snapshots"] == 2
    assert out["zero_spread_quarantined_not_free"] == 1
    assert out["crossed_quote_quarantined"] == 2
    assert out["NET_execution_cost_measured"] is False
    assert out["positive_spread_median_bps"] > 0


def test_stale_not_filled_with_future_quotes():
    bid = [(0, 100000)]
    ask = [(1000, 100010), (10000, 100010)]
    out = a.asof_spot_quality(bid, ask, max_age_ms=5000)
    assert out["positive_spread_source_snapshots"] == 1
    assert out["stale_side_quarantined"] == 1
    assert out["incomplete_one_side"] == 1


def test_empty_side_and_bad_age_fail_closed():
    with pytest.raises(ValueError, match="both sides"):
        a.asof_spot_quality([(0, 100000)], [])
    with pytest.raises(ValueError, match="positive staleness"):
        a.asof_spot_quality([(0, 100000)], [(0, 100010)], max_age_ms=0)


def test_scope_and_expected_real_source_sha_are_frozen():
    assert a.SOURCE_RUN == 38279593236
    assert a.SOURCE_ARTIFACT == 11760547215
    assert a.SOURCE_HEAD == "ef69b1b6ea2dbbd689bc3e090f9581e15bbb7ad6"
    assert a.SOURCE_ZIP_SHA256 == "e593ba684ae7073968371f4fa1d00673ce773e71a5fab000c80a672fbc33a64d"
    assert a.MAX_ASOF_AGE_MS == 5000


def test_sha_witness_rejects_mutation_and_unaccounted_file(tmp_path: Path):
    names = ["native-quote-source-PILOT-NOT-NET.json"] + [f"row-{i}.jsonl" for i in range(12)]
    sha_register = {}
    for name in names:
        data = (name + "\n").encode()
        (tmp_path / name).write_bytes(data)
        sha_register[name] = hashlib.sha256(data).hexdigest()
    (tmp_path / "OUTPUT_SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sha_register.items())
    )
    assert a._parse_source_sha(tmp_path) == sha_register
    (tmp_path / "row-0.jsonl").write_text("TAMPER\n")
    with pytest.raises(ValueError, match="tampered"):
        a._parse_source_sha(tmp_path)
    (tmp_path / "row-0.jsonl").write_bytes(b"row-0.jsonl\n")
    (tmp_path / "unlisted.jsonl").write_text("unaccounted\n")
    with pytest.raises(ValueError, match="unaccounted"):
        a._parse_source_sha(tmp_path)


def test_report_does_not_fabricate_source_if_manifest_missing(tmp_path: Path):
    with pytest.raises(ValueError, match="source SHA scope"):
        a.audit(tmp_path)


def test_source_clock_only_accepts_explicit_utc():
    assert a._time_ms("2020-09-15T13:00:00.001Z") == 1600174800001
    with pytest.raises(ValueError, match="UTC"):
        a._time_ms("2020-09-15T13:00:00")
