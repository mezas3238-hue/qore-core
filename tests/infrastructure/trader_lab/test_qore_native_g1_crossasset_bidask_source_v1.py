"""Synthetic contract/causality regressions for 2-market G1 source pilot."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_crossasset_bidask_source_v1 as s


def fake_catalog():
    return {
        "status": "ICMARKETS_DEMO_CATALOG_VERIFIED",
        "account_is_live": False,
        "_ephemeral_account_id": 15,
        "catalog": {
            "catalog_exact_matches": {
                "XAGUSD": {"broker_symbol": "XAGUSD", "symbol_id": 12, "enabled": True},
                "US500": {"broker_symbol": "US500", "symbol_id": 32, "enabled": True},
            }
        },
    }


def test_frozen_two_family_source_pilot_before_prices():
    assert s.TARGETS == {"XAGUSD": "XAGUSD", "SP500": "US500"}
    assert len(s.FROZEN_UTC_WINDOWS) == 3
    assert s.PARENT_NATIVE_M1_RUN == 38262534602
    assert s.FROZEN_UTC_WINDOWS == s.FROZEN_WINDOWS
    assert all(s.window_milliseconds(w)[1] - s.window_milliseconds(w)[0] == 600_000
               for w in s.FROZEN_UTC_WINDOWS)


def test_exact_current_account_symbols_no_alias_guess():
    manifest = fake_catalog()
    assert s.contract_proof(manifest, "XAGUSD") == (15, 12)
    assert s.contract_proof(manifest, "SP500") == (15, 32)
    manifest["catalog"]["catalog_exact_matches"]["US500"]["broker_symbol"] = "SPX500"
    with pytest.raises(s.SourceBlock, match="EXACT_PROVIDER_ALIAS_NOT_VERIFIED"):
        s.contract_proof(manifest, "SP500")
    with pytest.raises(s.SourceBlock, match="INVALID_UNIVERSE"):
        s.contract_proof(fake_catalog(), "NAS100")


def test_broker_must_be_exact_demo_and_enabled():
    m = fake_catalog()
    m["account_is_live"] = True
    with pytest.raises(s.SourceBlock, match="SOURCE_DEMO_ACCOUNT"):
        s.contract_proof(m, "XAGUSD")
    m = fake_catalog()
    m["catalog"]["catalog_exact_matches"]["XAGUSD"]["enabled"] = False
    with pytest.raises(s.SourceBlock, match="EXACT_PROVIDER_SYMBOL"):
        s.contract_proof(m, "XAGUSD")


def test_metal_and_index_int_price_decimal_and_sha(tmp_path: Path):
    sample = [(1600174800000, 2500123), (1600174800100, 2500124)]
    result = s.write_side(tmp_path, "XAGUSD", 1, "BID", sample, 1)
    native = (tmp_path / result["native_int_file"]).read_bytes()
    decoded = (tmp_path / result["decoded_file"]).read_bytes()
    assert hashlib.sha256(native).hexdigest() == result["native_int_sha256"]
    assert hashlib.sha256(decoded).hexdigest() == result["decoded_sha256"]
    docs = [json.loads(x) for x in decoded.splitlines()]
    assert [x["price"] for x in docs] == ["25.00123", "25.00124"]
    index = s.write_side(tmp_path, "SP500", 1, "ASK", [(1600174800000, 450010000)], 1)
    assert json.loads((tmp_path / index["decoded_file"]).read_text().splitlines()[0])["price"] == "4500.1"


def test_reject_unordered_integer_ticks_and_unsupported_market(tmp_path: Path):
    with pytest.raises(s.SourceBlock, match="BAD_SOURCE_TICK_CLOCK_ORDER"):
        s.write_side(tmp_path, "XAGUSD", 1, "ASK", [(100, 200), (99, 201)], 1)
    with pytest.raises(s.SourceBlock, match="BAD_SOURCE_INTEGER"):
        s.write_side(tmp_path, "SP500", 1, "ASK", [(100, 0)], 1)
    with pytest.raises(s.SourceBlock, match="INVALID_WRITER_SCOPE"):
        s.write_side(tmp_path, "NAS100", 1, "ASK", [(100, 300)], 1)


def test_no_trading_mutation_messages_permitted():
    accepted = s.ReadOnlyTickPilot._HISTORY_ONLY_REQUEST_NAMES
    assert "ProtoOAGetTickDataReq" in accepted
    assert not any(x in accepted for x in (
        "ProtoOANewOrderReq", "ProtoOACancelOrderReq", "ProtoOAModifyOrderReq",
        "ProtoOARefreshTokenReq", "ProtoOASubscribeSpotsReq", "ProtoOAReconcileReq",
    ))


def test_provider_signed_delta_decoder_reused_unchanged():
    from qore.infrastructure.trader_lab.qore_native_icmarkets_bidask_source_pilot_v1 import decode_native

    class Fake:
        def __init__(self, timestamp, tick):
            self.timestamp, self.tick = timestamp, tick

    assert decode_native((Fake(200, 100000), Fake(-50, 2), Fake(-10, -3)), 100, 200) == [
        (200, 100000), (150, 100002), (140, 99999),
    ]
