"""Synthetic attacks on VT08 B R10, not synthetic trade permission."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_b_r10_blind_cognitive_admission_inventory_v1 import (
    CLASSES,
    MULTI,
    NO_PIVOT,
    audit_blind_cognitive_admission,
)

T0 = datetime(2026, 3, 16, 12, tzinfo=UTC)
MARKET = "EURJPY"


def _fixture() -> dict[str, object]:
    c2, c3 = T0.isoformat(), (T0 + timedelta(minutes=30)).isoformat()
    case_id = hashlib.sha256(f"{MARKET}|{c2}|{c3}".encode()).hexdigest()
    case = {
        "market": MARKET,
        "c2_opened_at_utc": c2,
        "decision_at_utc": c3,
        "case_id_sha256": case_id,
        "pre_c2_three_h1_physically_complete": True,
        "basic_bullish_h1_pivot": True,
        "target_cardinality": 2,
        "source_unconsumed_h1_highs": [{"high": "1.52"}, {"high": "1.55"}],
        "diagnostic_review_class": MULTI,
        "rater_A": None,
        "rater_B_independent": None,
        "author_adjudication": "NOT_STARTED_D",
        "source_author_relevant_swing_verified": False,
        "source_author_target_selected": False,
        "source_author_breaker_verified": False,
        "source_author_ps_cisd_verified": False,
        "source_author_poi_verified": False,
        "methodology_source_complete": False,
        "cognitive_verified": False,
        "broker_fill_verified": False,
    }
    return {
        "schema": "qore.vt08.a.blind_three_source_review_join.v1",
        "market": MARKET, "frozen_event_count": 1,
        "selection_basis": "CHRONOLOGY_AND_PHYSICAL_SOURCE_ONLY_NO_PNL",
        "B_independent_semantic_review_complete": False,
        "signed_A_B_manifest": None,
        "source_complete_entries": 0,
        "broker_fills": 0,
        "profit_factor": None,
        "sortino": None,
        "max_drawdown": None,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "certified": False,
        "category_counts": {k: int(k == MULTI) for k in CLASSES},
        "all_source_only_cases": [case],
    }


def _run(report: dict[str, object]) -> dict[str, object]:
    return audit_blind_cognitive_admission(report, expected_market=MARKET)


def test_truthful_all_fields_blocked_not_executable() -> None:
    result = _run(_fixture())
    assert result["cases_review_queued"] == 1
    assert result["unverified_cognitive_field_instances"] == 27
    assert result["cognitive_causal_fields_required"] == 27
    assert result["source_author_complete"] == 0
    assert result["cognitive_admissions"] == 0
    assert result["verified_fills"] == 0
    assert result["approved_a_b_manifest_sha256"] is None
    assert len(result["review_queue"][0]["cognitive_missing_fields"]) == 27
    assert result["review_queue"][0]["cognitive_execute_authorized"] is False


@pytest.mark.parametrize(
    ("field", "forgery", "message"),
    [
        ("methodology_source_complete", True, "forged"),
        ("cognitive_verified", True, "forged"),
        ("broker_fill_verified", True, "forged"),
        ("source_author_breaker_verified", True, "forged"),
        ("rater_A", "architectA", "forged"),
        ("rater_B_independent", "architectB", "forged"),
        ("author_adjudication", "A_AND_B_PASS", "forged"),
        ("terminal_pnl", "3.2", "injected"),
        ("situation_27_field_receipts", {}, "injected"),
        ("candidate_event_v1", {}, "injected"),
        ("net_pnl", 20, "injected"),
    ],
)
def test_no_false_semantics_or_outcome(field: str, forgery: object, message: str) -> None:
    report = _fixture()
    report["all_source_only_cases"][0][field] = forgery
    with pytest.raises(ValueError, match=message):
        _run(report)


def test_source_case_id_cannot_change() -> None:
    report = _fixture()
    report["all_source_only_cases"][0]["case_id_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="identity"):
        _run(report)


def test_no_lookahead_in_c3() -> None:
    report = _fixture()
    report["all_source_only_cases"][0]["decision_at_utc"] = (
        T0 + timedelta(minutes=45)
    ).isoformat()
    with pytest.raises(ValueError, match="clock"):
        _run(report)


def test_no_duplicated_source_identity() -> None:
    report = _fixture()
    report["all_source_only_cases"].append(
        deepcopy(report["all_source_only_cases"][0])
    )
    report["frozen_event_count"] = 2
    with pytest.raises(ValueError, match="duplicate"):
        _run(report)


def test_no_selection_of_52_only() -> None:
    report = _fixture()
    report["all_source_only_cases"][0]["basic_bullish_h1_pivot"] = False
    with pytest.raises(ValueError, match="category"):
        _run(report)


def test_bucket_counts_not_rewritten() -> None:
    report = _fixture()
    report["category_counts"][MULTI] = 0
    report["category_counts"][NO_PIVOT] = 1
    with pytest.raises(ValueError, match="bucket"):
        _run(report)


def test_cannot_fake_signed_manifest() -> None:
    report = _fixture()
    report["signed_A_B_manifest"] = "f" * 64
    with pytest.raises(ValueError, match="authority"):
        _run(report)


def test_cannot_fake_profit_factor() -> None:
    report = _fixture()
    report["profit_factor"] = 1.8
    with pytest.raises(ValueError, match="authority"):
        _run(report)


def test_cannot_mix_other_market() -> None:
    report = _fixture()
    report["all_source_only_cases"][0]["market"] = "CADJPY"
    with pytest.raises(ValueError, match="mixed"):
        _run(report)
