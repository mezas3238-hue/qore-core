"""Negative/positive synthetic tests for Native G1-PRE pilot format; NO historical claims."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_pre_quote_source_gate_v1 as g


def example():
    records = [
        {
            "canonical_symbol": "EURUSD", "provider_symbol": "EURUSD",
            "provider_symbol_id": 1, "source_sequence": 1,
            "decision_time_utc": "2026-10-12T13:00:02Z",
            "bid_market_time_utc": "2026-10-12T13:00:01Z",
            "ask_market_time_utc": "2026-10-12T13:00:01Z",
            "both_sides_received_at_utc": None,
            "bid": "1.10000", "ask": "1.10002",
        },
        {
            "canonical_symbol": "XAUUSD", "provider_symbol": "XAUUSD",
            "provider_symbol_id": 2, "source_sequence": 15,
            "decision_time_utc": "2026-10-12T13:00:02Z",
            "bid_market_time_utc": "2026-10-12T13:00:00Z",
            "ask_market_time_utc": "2026-10-12T13:00:01Z",
            "both_sides_received_at_utc": None,
            "bid": "4000.00", "ask": "4000.38",
        },
    ]
    manifest = {
        "identity": g.IDENTITY,
        "g0_source_sha256": g.G0_SOURCE_SHA,
        "provider": "CTRADER_OPEN_API",
        "environment": "DEMO",
        "source_kind": "NATIVE_SIDE_TICKS_PAIRED_ASOF",
        "timestamp_timezone": "UTC",
        "historical_NET_economics_claimed": False,
        "production_enabled": False,
        "capture_mode": "HISTORICAL_BACKFILL",
        "broker_name": "SYNTHETIC_TEST_NOT_REAL",
        "broker_server": "SYNTHETIC_TEST_NOT_REAL",
        "account_fingerprint_sha256": "a" * 64,
        "instruments": [
            {
                "canonical_symbol": "EURUSD", "provider_symbol": "EURUSD",
                "provider_symbol_id": 1, "tick_size": "0.00001",
                "broker_contract_document_sha256": "b" * 64,
            },
            {
                "canonical_symbol": "XAUUSD", "provider_symbol": "XAUUSD",
                "provider_symbol_id": 2, "tick_size": "0.01",
                "broker_contract_document_sha256": "c" * 64,
            },
        ],
    }
    return manifest, records


def inspect(manifest, rows):
    raw = ("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n").encode()
    manifest["quotes_jsonl_sha256"] = hashlib.sha256(raw).hexdigest()
    return g.audit(manifest, raw)


def test_2_of_33_audited_format_never_net():
    m, rows = example()
    out = inspect(m, rows)
    assert out["pilot_market_count"] == 2
    assert len(out["unseen_markets"]) == 31
    assert out["asof_format_valid_rows_not_fills"] == 2
    assert out["historical_NET_authorized"] is False
    assert out["source_native_tick_origin_independently_verified"] is False
    assert out["certified_traders"] == 0


def test_fail_closed_against_tampered_source_bytes():
    m, rows = example()
    inspect(m, rows)
    with pytest.raises(ValueError, match="SHA256"):
        g.audit(m, b'{"fake":true}\n')


def test_future_bid_lookahead_and_unverified_local_time_are_rejected():
    m, rows = example()
    rows[0]["bid_market_time_utc"] = "2026-10-12T13:00:03Z"
    with pytest.raises(ValueError, match="lookahead"):
        inspect(m, rows)
    m, rows = example()
    rows[0]["ask_market_time_utc"] = "2026-10-12T13:00:01"
    with pytest.raises(ValueError, match="UTC"):
        inspect(m, rows)


def test_alias_and_symbol_id_not_auto_homologated():
    m, rows = example()
    rows[0]["provider_symbol"] = "NDX100"
    with pytest.raises(ValueError, match="alias"):
        inspect(m, rows)
    m, rows = example()
    m["instruments"][0]["provider_symbol_id"] = 999
    with pytest.raises(ValueError, match="alias"):
        inspect(m, rows)


def test_stale_crossed_and_zero_quarantined_not_free_cost():
    m, rows = example()
    rows[0]["ask"] = rows[0]["bid"]
    rows[1]["bid_market_time_utc"] = "2026-10-12T12:59:45Z"
    out = inspect(m, rows)
    assert out["per_symbol"]["EURUSD"]["zero_spread_quarantined"] == 1
    assert out["per_symbol"]["XAUUSD"]["stale_asof_quarantined"] == 1
    assert out["asof_format_valid_rows_not_fills"] == 0
    m, rows = example()
    rows[0]["ask"] = "1.09998"
    out = inspect(m, rows)
    assert out["per_symbol"]["EURUSD"]["crossed_quarantined"] == 1


def test_reject_source_sequence_and_tick_errors():
    m, rows = example()
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ValueError, match="sequence"):
        inspect(m, rows)
    m, rows = example()
    rows[0]["ask"] = "1.100021"
    with pytest.raises(ValueError, match="tick size"):
        inspect(m, rows)


def test_backfill_must_not_claim_forward_receipt():
    m, rows = example()
    rows[0]["both_sides_received_at_utc"] = "2026-10-12T13:00:02Z"
    with pytest.raises(ValueError, match="backfill"):
        inspect(m, rows)


def test_forward_receipt_causality_and_blocked_net():
    m, rows = example()
    m["capture_mode"] = "FORWARD_PAPER_CAPTURE"
    for row in rows:
        row["both_sides_received_at_utc"] = row["decision_time_utc"]
    out = inspect(m, rows)
    assert out["asof_format_valid_rows_not_fills"] == 2
    assert out["paper_order_submission_authorized"] is False
    rows[0]["both_sides_received_at_utc"] = "2026-10-12T13:00:03Z"
    with pytest.raises(ValueError, match="receipt causality"):
        inspect(m, rows)


def test_fail_closed_fake_provider_live_and_screenshot_promotions():
    for change in (
        ("provider", "BROKER_SCREENSHOT"),
        ("environment", "LIVE"),
        ("source_kind", "USER_STATIC_BID_ASK"),
        ("historical_NET_economics_claimed", True),
        ("production_enabled", True),
    ):
        m, rows = example()
        m[change[0]] = change[1]
        with pytest.raises(ValueError, match="contract"):
            inspect(m, rows)


def test_not_market_data_not_strategy_not_production():
    m, rows = example()
    assert "SYNTHETIC" in m["broker_name"]
    assert inspect(m, rows)["status"] == "SOURCE_FORMAT_TRIAGED_EXTERNAL_ATTESTATION_PENDING"
