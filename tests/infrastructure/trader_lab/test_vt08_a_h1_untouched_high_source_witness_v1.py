"""VT08 target source: untouched OBSERVED HTF highs, never author selection."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_a_h1_untouched_high_source_witness_v1 import (
    H1HighState,
    witness_events,
)
from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import (
    _bar_receipt,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T = datetime(2025, 6, 15, 11, tzinfo=UTC)
SHA3, SHA15 = "a" * 64, "b" * 64


def make_bar(at, *, high="103", low="98", opening="99", close="100"):
    return Vt08B01Bar(
        opened_at=at, closed_at=at + timedelta(minutes=15),
        open=Decimal(opening), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
    )


def raw_data(*, first_high="106", c2_high="103", future_high=None):
    # Complete 11:00 H1 then 12:00 C2 (first two M15),
    # with no source gap through C3=12:30.
    out = [make_bar(T + i * timedelta(minutes=15),
                    high=first_high if i < 4 else c2_high)
           for i in range(6)]
    if future_high is not None:
        out.append(make_bar(T + timedelta(minutes=90), high=future_high))
    return out


def catalog(native):
    c2 = T + timedelta(hours=1)
    chosen = native[4:6]
    ids = []
    by_id = {}
    for bar in chosen:
        receipt = _bar_receipt(bar, SHA15, "M15")
        key = receipt["source_bar_id"]
        ids.append(key)
        by_id[key] = {**receipt, "market": "EURJPY"}
    return {
        "schema": "qore.vt08.a_b.market_raw_custody_catalog.v1",
        "market": "EURJPY",
        "source_raw_market_map": {SHA3: "EURJPY", SHA15: "EURJPY"},
        "pinned_raw_shas": [SHA3, SHA15],
        "bar_catalog": by_id,
        "source_only_event_count": 1,
        "source_only_events": [{
            "market": "EURJPY",
            "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": (c2 + timedelta(minutes=30)).isoformat(),
            "source_complete": False,
            "source_bar_groups": {"c2_m15_raw_bar_receipts": ids},
        }],
        "author_fidelity_certified": False,
        "cognitive_certified": False,
        "economic_gates_certified": False,
        "pnl_evaluated": False,
        "orders": 0,
        "fills": 0,
    }


def inspect(native=None):
    bars = raw_data() if native is None else native
    return witness_events(
        market="EURJPY", source_catalog=catalog(bars),
        native_m15=bars, raw_m15_sha256=SHA15,
    )


def test_h1_high_prior_and_untouched_is_only_a_physical_witness():
    out = inspect()
    assert out["frozen_source_events"] == 1
    assert out["source_gap_resets"] == 0
    assert out["observed_h1_highs_formed"] == 1
    assert out["cases_exactly_one_observed_h1_high"] == 1
    assert out["cases_zero_observed_h1_highs"] == 0
    assert out["cases_any_high_above_c2_close_proxy"] == 1
    assert out["cases_multiple_highs_above_c2_close_proxy"] == 0
    row = out["witnesses"][0]
    assert row["witness_count"] == 1
    level = row["untouched_h1_high_candidates"][0]
    assert level["high"] == "106"
    assert len(level["origin_source_m15_bar_ids"]) == 4
    assert level["higher_than_c2_close_proxy"]
    assert not level["author_target_relevance_verified"]
    assert not row["author_target_selected"]
    assert out["source_complete_entries"] == out["broker_fills"] == 0
    assert out["profit_factor"] is None


def test_taken_high_before_c3_is_no_longer_untouched():
    out = inspect(raw_data(c2_high="107"))
    assert out["witnesses"][0]["witness_count"] == 0
    assert out["cases_zero_observed_h1_highs"] == 1
    assert out["cases_any_high_above_c2_close_proxy"] == 0
    assert out["observed_h1_highs_touched"] >= 1


def test_higher_price_after_decision_cannot_censor_prior_target():
    result = inspect(raw_data(future_high="1000"))
    assert result["witnesses"][0]["witness_count"] == 1
    assert result["witnesses"][0]["untouched_h1_high_candidates"][0]["high"] == "106"


def test_market_gap_invalidates_previous_untouched_attestation():
    st = H1HighState("EURJPY", SHA15)
    for bar in raw_data()[:4]:
        st.advance(bar)
    assert len(st.active) == 1
    st.advance(make_bar(T + timedelta(hours=2)))
    assert len(st.active) == 0
    assert st.source_gaps == 1


def test_duplicate_market_and_foreign_sha_fail_closed():
    bars = raw_data()
    payload = catalog(bars)
    payload["source_raw_market_map"][SHA15] = "USDCHF"
    with pytest.raises(ValueError, match="market"):
        witness_events(
            market="EURJPY", source_catalog=payload,
            native_m15=bars, raw_m15_sha256=SHA15,
        )


def test_corrupt_catalog_ohlc_is_rejected_by_real_native_data():
    bars = raw_data()
    payload = catalog(bars)
    id0 = payload["source_only_events"][0]["source_bar_groups"][
        "c2_m15_raw_bar_receipts"
    ][0]
    payload["bar_catalog"][id0]["ohlc"] = ("99", "108", "98", "100")
    with pytest.raises(ValueError, match="catalog differs"):
        witness_events(
            market="EURJPY", source_catalog=payload,
            native_m15=bars, raw_m15_sha256=SHA15,
        )


def test_duplicate_events_cannot_inflate_untouched_target_count():
    bars = raw_data()
    payload = catalog(bars)
    payload["source_only_events"].append(payload["source_only_events"][0].copy())
    payload["source_only_event_count"] = 2
    with pytest.raises(ValueError, match="duplicate C3"):
        witness_events(
            market="EURJPY", source_catalog=payload,
            native_m15=bars, raw_m15_sha256=SHA15,
        )


def test_authorization_and_false_pnl_never_allowed():
    bars = raw_data()
    payload = catalog(bars)
    payload["pnl_evaluated"] = True
    with pytest.raises(ValueError, match="trading authority"):
        witness_events(
            market="EURJPY", source_catalog=payload,
            native_m15=bars, raw_m15_sha256=SHA15,
        )


def test_nonchronological_native_feed_is_rejected():
    bars = raw_data()
    bars[2], bars[3] = bars[3], bars[2]
    with pytest.raises(ValueError, match="overlapping/out-of-order"):
        inspect(bars)


def test_c2_close_missing_prevents_target_attestation():
    bars = raw_data()
    bars = bars[:5]
    payload = catalog(raw_data())
    with pytest.raises(ValueError, match="native original missing"):
        witness_events(
            market="EURJPY", source_catalog=payload,
            native_m15=bars, raw_m15_sha256=SHA15,
        )


def test_stale_native_m15_source_cannot_be_certified():
    bars = raw_data()
    payload = catalog(bars)
    with pytest.raises(ValueError, match="market"):
        witness_events(
            market="USDCHF", source_catalog=payload,
            native_m15=bars, raw_m15_sha256=SHA15,
        )
