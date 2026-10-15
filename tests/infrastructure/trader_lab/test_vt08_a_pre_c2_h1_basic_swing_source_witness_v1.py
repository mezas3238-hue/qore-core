"""Basic H1 pivot is source-described; relevance is deliberately NOT proven."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import (
    _bar_receipt,
)
from qore.infrastructure.trader_lab.vt08_a_pre_c2_h1_basic_swing_source_witness_v1 import (
    basic_swing_witnesses,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

C2 = datetime(2025, 5, 15, 12, tzinfo=UTC)
SHA3, SHA15 = "a" * 64, "b" * 64


def fixture(*, middle_low="98", middle_high="105", missing=False):
    catalog = {}
    ids = []
    beginning = C2 - timedelta(hours=3)
    for i in range(12):
        t = beginning + i * timedelta(minutes=15)
        idx = i // 4
        lows = ["100", middle_low, "99"]
        highs = ["104", middle_high, "103"]
        bar = Vt08B01Bar(
            opened_at=t, closed_at=t + timedelta(minutes=15),
            open=Decimal("102"), high=Decimal(highs[idx]),
            low=Decimal(lows[idx]), close=Decimal("101"),
        )
        r = _bar_receipt(bar, SHA15, "M15")
        catalog[r["source_bar_id"]] = {**r, "market": "EURJPY"}
        ids.append(r["source_bar_id"])
    return {
        "schema": "qore.vt08.a_b.market_raw_custody_catalog.v1",
        "market": "EURJPY",
        "pinned_raw_shas": [SHA3, SHA15],
        "source_raw_market_map": {SHA3: "EURJPY", SHA15: "EURJPY"},
        "bar_catalog": catalog,
        "source_only_events": [{
            "market": "EURJPY",
            "c2_opened_at_utc": C2.isoformat(),
            "decision_at_utc": (C2 + timedelta(minutes=30)).isoformat(),
            "source_complete": False,
            "source_bar_groups": {
                "pre_c2_h1_m15_raw_bar_receipts": [] if missing else ids,
            },
        }],
        "source_only_event_count": 1,
        "author_fidelity_certified": False,
        "cognitive_certified": False,
        "economic_gates_certified": False,
        "pnl_evaluated": False,
        "orders": 0, "fills": 0,
    }


def test_bullish_basic_swing_low_source_rule_not_relevance():
    result = basic_swing_witnesses(fixture())
    assert result["strict_3h1_bullish_basic_pivot_count"] == 1
    assert result["strict_3h1_bearish_basic_pivot_count"] == 1
    row = result["review_witnesses"][0]
    assert row["basic_swing_bullish_low"]
    assert row["basic_swing_bearish_high"]
    assert row["h1_candle_available_at_utc"] == C2.isoformat()
    assert row["source_author_pivot_definition_observable"]
    assert row["source_author_valid_separation_established"] is False
    assert row["source_author_relevant_swing_verified"] is False
    assert not row["eq_regime_authorized"]
    assert result["profit_factor"] is None
    assert result["broker_fills"] == 0


def test_non_pivot_basic_swing_does_not_fail_as_invalid_author_method():
    result = basic_swing_witnesses(
        fixture(middle_low="100", middle_high="102"),
    )
    assert result["strict_3h1_bullish_basic_pivot_count"] == 0
    assert result["strict_3h1_bearish_basic_pivot_count"] == 0
    row = result["review_witnesses"][0]
    assert not row["basic_swing_bullish_low"]
    assert row["source_author_relevant_swing_verified"] is False


def test_h1_missing_cannot_be_fabricated_from_other_intervals():
    r = basic_swing_witnesses(fixture(missing=True))
    assert r["missing_pre_c2_h1_context"] == 1
    assert not r["review_witnesses"][0]["pre_c2_h1_complete"]


def test_future_lookahead_or_bad_clock_rejected():
    p = fixture()
    p["source_only_events"][0]["c2_opened_at_utc"] = (
        C2 - timedelta(minutes=30)
    ).isoformat()
    with pytest.raises(ValueError, match="pre-C2 custody/clock"):
        basic_swing_witnesses(p)


def test_cross_market_falsified_ledger_rejected():
    p = fixture()
    p["source_raw_market_map"][SHA15] = "USDCHF"
    with pytest.raises(ValueError, match="custody"):
        basic_swing_witnesses(p)


def test_modified_real_bar_invalidates_hash():
    p = fixture()
    key = p["source_only_events"][0]["source_bar_groups"][
        "pre_c2_h1_m15_raw_bar_receipts"
    ][4]
    p["bar_catalog"][key]["ohlc"] = ("102", "110", "98", "101")
    with pytest.raises(ValueError, match="sha drift"):
        basic_swing_witnesses(p)


def test_duplicate_case_cannot_be_counted_twice():
    p = fixture()
    p["source_only_events"].append(p["source_only_events"][0].copy())
    p["source_only_event_count"] = 2
    with pytest.raises(ValueError, match="duplicate source C3"):
        basic_swing_witnesses(p)


def test_false_methodology_and_pnl_claims_never_allowed():
    p = fixture()
    p["author_fidelity_certified"] = True
    with pytest.raises(ValueError, match="trade authority"):
        basic_swing_witnesses(p)
    p = fixture()
    p["pnl_evaluated"] = True
    with pytest.raises(ValueError, match="trade authority"):
        basic_swing_witnesses(p)
