"""B R9 adversarial isolated M15 tests; never imports an A producer."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_b_r9_independent_h1_target_join_audit_v1 import (
    INCOMPLETE,
    MULTIPLE,
    NO_PIVOT,
    NO_TARGET,
    REVIEW,
    _receipt_id,
    audit_native_r9,
)

MARKET = "EURJPY"
SHA = "a" * 64
T0 = datetime(2026, 1, 5, 12, tzinfo=UTC)


def _fixture() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict]:
    native = {}
    ids = []
    for i in range(14):
        opened = T0 + timedelta(minutes=15 * i)
        # Three H1 highs descend, remain untouched. The middle H1 LOW is
        # lower than both neighbors. The final two bars are frozen C2.
        h = ("1.40", "1.30", "1.20", "1.15")[min(i // 4, 3)]
        low = ("1.00", "0.90", "1.05", "1.10")[min(i // 4, 3)]
        row = {
            "opened_at": opened.isoformat(),
            "closed_at": (opened + timedelta(minutes=15)).isoformat(),
            "open": "1.11", "high": h, "low": low, "close": "1.12",
        }
        native[opened] = row
        ids.append(_receipt_id(row, opened, SHA))
    c2 = T0 + timedelta(hours=3)
    c3 = c2 + timedelta(minutes=30)
    key = {
        "market": MARKET, "c2_opened_at_utc": c2.isoformat(),
        "decision_at_utc": c3.isoformat(),
    }
    levels = []
    for i, h in enumerate(("1.40", "1.30", "1.20")):
        start = T0 + timedelta(hours=i)
        levels.append({
            "high": h,
            "origin_h1_opened_at_utc": start.isoformat(),
            "origin_h1_available_at_utc": (start + timedelta(hours=1)).isoformat(),
            "origin_source_m15_bar_ids": ids[4 * i:4 * (i + 1)],
            "higher_than_c2_close_proxy": True,
            "continuity_since_origin": "OBSERVED_GAP_FREE_M15_ONLY",
            "author_target_relevance_verified": False,
        })
    cat = {
        "schema": "qore.vt08.a_b.market_raw_custody_catalog.v1",
        "market": MARKET,
        "source_raw_market_map": {SHA: MARKET},
        "source_only_event_count": 1,
        "source_only_events": [{
            **key,
            "source_complete": False,
            "source_bar_groups": {"pre_c2_h1_m15_raw_bar_receipts": ids[:12]},
        }],
    }
    target = {
        "schema": "qore.vt08.a.observed_h1_untouched_high_witness.v1",
        "market": MARKET, "input_m15_source_sha256": SHA,
        "frozen_source_events": 1,
        "witnesses": [{
            **key, "c2_close_price_source_proxy": "1.12",
            "witness_count": 3, "untouched_h1_high_candidates": levels,
        }],
        "source_complete_entries": 0, "broker_fills": 0,
        "profit_factor": None, "certified": False,
        "holdout_7y_accessed": False, "sizing_used": False,
    }
    join = {
        "schema": "qore.vt08.a.blind_three_source_review_join.v1",
        "market": MARKET, "frozen_event_count": 1,
        "all_source_only_cases": [{
            **key,
            "c2_eq_full_conditional": str((Decimal("1.15") + Decimal("1.10")) / 2),
            "c2_eq_close_to_low_conditional": str(
                (Decimal("1.12") + Decimal("1.10")) / 2
            ),
            "source_unconsumed_h1_highs": levels,
            "target_cardinality": 3,
            "h1_swing_source_ids": [ids[:4], ids[4:8], ids[8:12]],
            "pre_c2_three_h1_physically_complete": True,
            "basic_bullish_h1_pivot": True, "basic_bearish_h1_pivot": False,
            "diagnostic_review_class": MULTIPLE,
            "source_author_relevant_swing_verified": False,
            "source_author_target_selected": False,
            "source_author_breaker_verified": False,
            "source_author_ps_cisd_verified": False,
            "source_author_poi_verified": False,
            "methodology_source_complete": False,
            "cognitive_verified": False,
            "broker_fill_verified": False,
            "author_adjudication": "NOT_STARTED_D",
        }],
        "category_counts": {
            INCOMPLETE: 0, NO_PIVOT: 0, NO_TARGET: 0, MULTIPLE: 1, REVIEW: 0,
        },
        "signed_A_B_manifest": None,
        "B_independent_semantic_review_complete": False,
        "source_complete_entries": 0, "broker_fills": 0,
        "profit_factor": None, "certified": False,
        "sizing_used": False, "holdout_7y_accessed": False,
    }
    return cat, target, join, native


def _run(fixture: tuple) -> dict[str, object]:
    cat, target, joined, native = fixture
    return audit_native_r9(
        market=MARKET, catalog=cat, target=target, joined=joined,
        native=native, raw_sha=SHA,
    )


def test_independent_native_h1_and_pivot_replay() -> None:
    outcome = _run(_fixture())
    assert outcome["source_events_audited"] == 1
    assert outcome["r6_native_high_levels_checked"] == 3
    assert outcome["r7_physical_classes"] == {MULTIPLE: 1}
    assert outcome["source_complete_entries"] == 0
    assert outcome["approved_a_b_manifest_sha256"] is None


def test_high_price_forgery_even_with_new_report_hash() -> None:
    case = _fixture()
    case[1]["witnesses"][0]["untouched_h1_high_candidates"][0]["high"] = "1.99"
    case[2]["all_source_only_cases"][0]["source_unconsumed_h1_highs"][0]["high"] = "1.99"
    with pytest.raises(ValueError, match="altered"):
        _run(case)


def test_eq_price_forgery_rejected() -> None:
    case = _fixture()
    case[2]["all_source_only_cases"][0]["c2_eq_full_conditional"] = "9.99"
    with pytest.raises(ValueError, match="EQ"):
        _run(case)


def test_pivot_class_can_not_be_overridden() -> None:
    case = _fixture()
    case[2]["all_source_only_cases"][0]["basic_bullish_h1_pivot"] = False
    with pytest.raises(ValueError, match="pivot"):
        _run(case)


def test_physical_source_cannot_claim_author_complete() -> None:
    case = _fixture()
    case[2]["all_source_only_cases"][0]["methodology_source_complete"] = True
    with pytest.raises(ValueError, match="permission"):
        _run(case)


def test_missing_high_or_h1_origin_rejected() -> None:
    case = _fixture()
    case[1]["witnesses"][0]["untouched_h1_high_candidates"].pop()
    with pytest.raises(ValueError, match="cardinality"):
        _run(case)


def test_cross_market_raw_sha_rejected() -> None:
    case = _fixture()
    case[1]["input_m15_source_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="SHA"):
        _run(case)


def test_future_h1_origin_rejected() -> None:
    case = _fixture()
    later = (T0 + timedelta(days=3)).isoformat()
    case[1]["witnesses"][0]["untouched_h1_high_candidates"][0][
        "origin_h1_available_at_utc"
    ] = later
    with pytest.raises(ValueError, match="altered"):
        _run(case)


def test_gap_quarantines_previous_untouched_highs() -> None:
    case = _fixture()
    native = case[3]
    native.pop(T0 + timedelta(minutes=15 * 10))
    with pytest.raises(ValueError, match="missing|origin|cardinality"):
        _run(case)


def test_touch_equal_high_invalidates_old_level() -> None:
    case = _fixture()
    row = case[3][T0 + timedelta(hours=1)]
    row["high"] = "1.40"  # equality must count as touch of first H1
    with pytest.raises(ValueError, match="cardinality|altered"):
        _run(case)


def test_duplicate_source_event_identity_fails_closed() -> None:
    case = _fixture()
    case[0]["source_only_events"].append(
        deepcopy(case[0]["source_only_events"][0])
    )
    with pytest.raises(ValueError, match="repeated"):
        _run(case)


def test_no_fake_independent_a_b_signature() -> None:
    case = _fixture()
    case[2]["signed_A_B_manifest"] = "a" * 64
    with pytest.raises(ValueError, match="signature"):
        _run(case)
