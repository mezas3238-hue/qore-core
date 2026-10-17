"""Source EQ arithmetic is testable; swing validity and economics are not."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_a_b_market_custody_catalog_v1 import (
    STAGE,
    build_catalog,
)
from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import _bar_receipt
from qore.infrastructure.trader_lab.vt08_a_source_conditional_eq_review_v1 import (
    conditional_eq_witnesses,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

C2 = datetime(2025, 6, 16, 13, tzinfo=UTC)
SHA3, SHA15 = "a" * 64, "b" * 64


def _source(start, count, mins, sha, profile, op, high, low, close):
    out = []
    for i in range(count):
        at = start + timedelta(minutes=mins * i)
        bar = Vt08B01Bar(
            opened_at=at, closed_at=at + timedelta(minutes=mins),
            open=Decimal(op), high=Decimal(high),
            low=Decimal(low), close=Decimal(close),
        )
        out.append(_bar_receipt(bar, sha, profile))
    return out


def _catalog(*, h1=True):
    case = {
        "market": "EURJPY",
        "stage": STAGE,
        "c1_opened_at_utc": (C2 - timedelta(minutes=30)).isoformat(),
        "c2_opened_at_utc": C2.isoformat(),
        "decision_at_utc": (C2 + timedelta(minutes=30)).isoformat(),
        "source_m3_file_sha256": SHA3,
        "source_m15_file_sha256": SHA15,
        "c1_m3_raw_bar_receipts": _source(
            C2 - timedelta(minutes=30), 10, 3, SHA3, "M3",
            "101", "103", "100", "101",
        ),
        "c2_m3_raw_bar_receipts": _source(
            C2, 10, 3, SHA3, "M3", "100", "102", "99", "101",
        ),
        "c2_m15_raw_bar_receipts": _source(
            C2, 2, 15, SHA15, "M15", "100", "102", "99", "101",
        ),
        "pre_c2_h1_m15_raw_bar_receipts": _source(
            C2 - timedelta(hours=3), 12, 15, SHA15, "M15",
            "101", "103", "100", "101",
        ) if h1 else [],
        "pre_c2_h1_context_available": h1,
        "A_rule_complete": False, "cognitive_ready": False,
        "broker_fill": False, "pnl_read": False,
    }
    report = {
        "market": "EURJPY",
        "source_m3_sha256": SHA3, "source_m15_sha256": SHA15,
        "c2_windows_total": 1, "stage_counts": {STAGE: 1},
        "pnl_evaluated": False,
        "examples_by_stage": {STAGE: [case]},
    }
    frozen = {"market_rows": {"EURJPY": {
        "m3_raw_sha256": SHA3, "m15_raw_sha256": SHA15,
        "c2_windows_total": 1, "stage_counts": {STAGE: 1},
    }}}
    return build_catalog(
        market="EURJPY", source_report=report, frozen_manifest=frozen,
    )


def test_realistic_c2_conditional_eq_is_not_author_admission():
    report = conditional_eq_witnesses(_catalog())
    assert report["source_case_count"] == 1
    assert report["prior_h1_incomplete_cases"] == 0
    row = report["all_conditional_eq_witnesses"][0]
    assert row["eq_if_prior_bullish_swing_source_valid_with_close"] == "100.5"
    assert row["eq_if_prior_bullish_swing_valid_but_close_against"] == "100"
    assert row["actual_frozen_c2_body_direction"] == "BULLISH"
    assert not row["eq_selection_authorized"]
    assert not row["eq_swing_identity_author_adjudicated"]
    assert not row["breaker_low_author_adjudicated"]
    assert not row["htf_untouched_target_author_adjudicated"]
    assert report["source_complete_entries"] == 0
    assert report["verified_fills"] == 0
    assert report["profit_factor"] is None


def test_missing_pre_c2_h1_is_preserved_not_imputed():
    report = conditional_eq_witnesses(_catalog(h1=False))
    assert report["prior_h1_incomplete_cases"] == 1
    assert not report["all_conditional_eq_witnesses"][0][
        "prior_h1_context_available"
    ]


def test_m3_m15_mismatch_detected_not_averaged():
    catalog = _catalog()
    event = catalog["source_only_events"][0]
    bar = catalog["bar_catalog"][
        event["source_bar_groups"]["c2_m15_raw_bar_receipts"][0]
    ]
    bar["ohlc"] = ("100", "105", "99", "101")
    with pytest.raises(ValueError, match="SHA"):
        conditional_eq_witnesses(catalog)


def test_source_market_cross_join_rejected():
    catalog = _catalog()
    catalog["source_raw_market_map"][SHA15] = "USDCHF"
    with pytest.raises(ValueError, match="custody"):
        conditional_eq_witnesses(catalog)


def test_tampered_source_bar_id_and_c3_lookahead_rejected():
    catalog = _catalog()
    event = catalog["source_only_events"][0]
    id0 = event["source_bar_groups"]["c2_m3_raw_bar_receipts"][0]
    catalog["bar_catalog"][id0]["source_bar_id"] = "f" * 64
    with pytest.raises(ValueError, match="SHA"):
        conditional_eq_witnesses(catalog)
    catalog = _catalog()
    catalog["source_only_events"][0]["decision_at_utc"] = C2.isoformat()
    with pytest.raises(ValueError, match="too early"):
        conditional_eq_witnesses(catalog)


def test_source_only_cannot_become_certified_by_editing_flag():
    catalog = _catalog()
    catalog["author_fidelity_certified"] = True
    with pytest.raises(ValueError, match="certified"):
        conditional_eq_witnesses(catalog)


def test_duplicate_event_inventory_rejected():
    catalog = _catalog()
    catalog["source_only_events"].append(
        dict(catalog["source_only_events"][0])
    )
    catalog["source_only_event_count"] = 2
    with pytest.raises(ValueError, match="duplicate source decision"):
        conditional_eq_witnesses(catalog)


def test_h1_context_clock_or_profile_tamper_rejected():
    catalog = _catalog()
    event = catalog["source_only_events"][0]
    key = event["source_bar_groups"]["pre_c2_h1_m15_raw_bar_receipts"][0]
    catalog["bar_catalog"][key]["profile"] = "M15_PRE_C2_H1"
    with pytest.raises(ValueError, match="original M15"):
        conditional_eq_witnesses(catalog)


def test_no_broker_fill_pnl_gate_from_eq():
    catalog = _catalog()
    catalog["fills"] = 1
    with pytest.raises(ValueError, match="orders or fills"):
        conditional_eq_witnesses(catalog)
