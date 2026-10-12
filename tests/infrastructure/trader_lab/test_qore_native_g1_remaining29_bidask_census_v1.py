"""Synthetic negative/boundary tests for the frozen 29-market native source census."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_remaining29_bidask_census_v1 as c


def fake_catalog():
    return {
        "status": "ICMARKETS_DEMO_CATALOG_VERIFIED",
        "account_is_live": False,
        "_ephemeral_account_id": 99,
        "catalog": {
            "catalog_exact_matches": {
                symbol: {"broker_symbol": symbol, "enabled": True,
                         "symbol_id": idx + 1}
                for idx, symbol in enumerate(c.FROZEN_TARGETS)
            }
        },
    }


def test_target_universe_exact_29_no_old_sources_or_nas100():
    assert len(c.FROZEN_TARGETS) == 29
    assert len(set(c.FROZEN_TARGETS)) == 29
    assert all(s not in c.FROZEN_TARGETS for s in (
        "NZDUSD", "XAGUSD", "SP500", "NAS100"
    ))
    assert "EURUSD" in c.FROZEN_TARGETS and "XAUUSD" in c.FROZEN_TARGETS
    assert c.EXPECTED_WINDOWS == c.FROZEN_WINDOWS
    assert c.SOURCE_M1_PROOF_RUN == 38262534602


def test_exact_29_symbol_ids_and_live_or_alias_fails_closed():
    account, symbols = c._source_symbols(fake_catalog())
    assert account == 99
    assert len(symbols) == 29 and all(x > 0 for x in symbols.values())
    item = fake_catalog()
    item["account_is_live"] = True
    with pytest.raises(c.SourceBlock, match="SOURCE_DEMO_ACCOUNT_UNVERIFIED"):
        c._source_symbols(item)
    item = fake_catalog()
    item["catalog"]["catalog_exact_matches"]["EURUSD"]["broker_symbol"] = "EURUSD.alt"
    _, matched = c._source_symbols(item)
    assert "EURUSD" not in matched and len(matched) == 28


def test_integer_to_decimal_stream_is_exact_and_source_sha(tmp_path: Path):
    result = c._write_side(
        tmp_path, "XAUUSD", 1, "BID",
        [(1600174800000, 195001234), (1600174800100, 195001235)], 1,
    )
    first = (tmp_path / result["native_int_file"]).read_bytes()
    second = (tmp_path / result["decoded_file"]).read_bytes()
    assert c._sha(tmp_path / result["native_int_file"]) == hashlib.sha256(first).hexdigest()
    assert c._sha(tmp_path / result["decoded_file"]) == hashlib.sha256(second).hexdigest()
    rows = [json.loads(x) for x in second.splitlines()]
    assert [x["price"] for x in rows] == ["1950.01234", "1950.01235"]


def test_bad_clock_or_invalid_price_fails_before_sha_claim(tmp_path: Path):
    with pytest.raises(c.SourceBlock, match="CHRONOLOGY"):
        c._write_side(tmp_path, "US30", 1, "ASK", [(20, 1), (19, 2)], 1)
    with pytest.raises(c.SourceBlock, match="INTEGER_INVALID"):
        c._write_side(tmp_path, "EURUSD", 1, "ASK", [(20, 0)], 1)
    with pytest.raises(c.SourceBlock, match="WRITER_SCOPE"):
        c._write_side(tmp_path, "NZDUSD", 1, "ASK", [(20, 11)], 1)


def test_catalog_precondition_blocked_is_auditable_no_fake_ticks(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(c, "probe_catalog", lambda: {"status": "SOURCE_UNAVAILABLE"})
    report = c.census(tmp_path)
    assert report["status"] == "G1_ALL_29_SOURCE_PRECONDITION_BLOCKED_NOT_NET"
    assert report["attempted"] == 0 and report["complete"] == 0
    assert report["historical_NET_authorized"] is False
    assert report["certified_traders"] == 0
    assert (tmp_path / "G1-29-SOURCE-CENSUS-NOT-NET.json").is_file()


def test_no_trade_or_oauth_refresh_protobuf_allowed():
    allowed = c.ReadOnlyTickPilot._HISTORY_ONLY_REQUEST_NAMES
    assert "ProtoOAGetTickDataReq" in allowed
    assert all(word not in allowed for word in (
        "ProtoOANewOrderReq", "ProtoOAModifyOrderReq", "ProtoOACancelOrderReq",
        "ProtoOARefreshTokenReq", "ProtoOAReconcileReq", "ProtoOASubscribeSpotsReq",
    ))


def test_preregistered_windows_ten_minutes_and_no_embargo_economic_access():
    for win in c.EXPECTED_WINDOWS:
        left, right = c.window_milliseconds(win)
        assert right - left == 600000
    assert c.SOURCE_G0_SHA256 == "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
