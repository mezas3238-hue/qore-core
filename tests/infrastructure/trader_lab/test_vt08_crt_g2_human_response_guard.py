"""R10 adversarial G2 human review protocol, NEVER a simulated certificate."""
from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_g2_human_response_guard import (
    audit_g2_human_responses_structural_only,
)
from qore.infrastructure.trader_lab.vt08_crt_g2_independent_blind_review import (
    build_g2_independent_review_packets,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def fixtures(market: CrtPureMarket = CrtPureMarket.AUDUSD):
    utc = datetime(2025, 2, 3, tzinfo=UTC)
    source = []
    n = 16 if market is CrtPureMarket.AUDUSD else 20
    for k in range(n):
        started = utc + k * timedelta(days=2)
        h4 = []
        for i in range(3):
            h4.append({
                "opened_at_utc": (started + i * timedelta(hours=4)).isoformat(),
                "open_relative": 100, "high_relative": 105 + i,
                "low_relative": 95 - i, "close_relative": 101,
            })
        source.append({
            "market": market.value,
            "blind_case_id": f"original-case-{k:03d}",
            "source_event_id": f"source-{k:03d}",
            "decision_clock_utc": (
                started + timedelta(hours=12, minutes=45)
            ).isoformat(),
            "c2_closed_at_utc": (started + timedelta(hours=12)).isoformat(),
            "c0_closed_h4": h4[0], "c1_closed_h4": h4[1],
            "c2_closed_h4": h4[2],
            "c0_direction": "BULLISH",
            "c1_direction": "BEARISH",
            "conflict_kind": "OPPOSITE",
            "selected_reference": None,
            "independent_reviewer_adjudicated": False,
            "owner_approval": False,
            "not_a_trade": True,
            "not_fresh_holdout": True,
        })
    _, reviewer, _, replies = build_g2_independent_review_packets(
        market, tuple(source)
    )
    return reviewer, replies


@pytest.mark.parametrize("market", [CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY])
def test_original_blank_36_exposes_exactly_all_missing_answers(market):
    reviewer, replies = fixtures(market)
    state = audit_g2_human_responses_structural_only(
        market.value, reviewer, replies
    )
    n = 16 if market is CrtPureMarket.AUDUSD else 20
    assert state["frozen_R9_review_cases"] == n
    assert state["unanswered"] == n
    assert state["blocker_counts"] == {"UNANSWERED_BLIND_CASE": n}
    assert state["structurally_complete_NOT_APPROVED"] is False
    assert state["independent_GitHub_identity_authenticated"] is False
    assert state["G_M1_PASS"] is False and state["G_M5_ISSUED"] is False


def _filled():
    reviewer, replies = fixtures()
    editable = list(copy.deepcopy(replies))
    for item in editable:
        item["human_choice"] = "INSUFFICIENT_SOURCE"
        item["source_quote_locator"] = (
            "SOURCE_GAP: no authenticated old CRT prioritization rule"
        )
        item["causal_reason_for_choice"] = (
            "No original three-source policy supplies priority between these "
            "two contemporaneous closed H4 references at decision time."
        )
        item["counterexample_if_any"] = (
            "When both are plausible, a numeric label alone is insufficient."
        )
    return reviewer, tuple(editable)


def test_even_fake_filled_36_structurally_complete_cannot_certify():
    reviewer, replies = _filled()
    out = audit_g2_human_responses_structural_only(
        "AUDUSD", reviewer, replies
    )
    assert out["structurally_complete_NOT_APPROVED"] is True
    assert out["structurally_answered"] == 16
    assert out["answer_distribution_NOT_TRUTH"] == {"INSUFFICIENT_SOURCE": 16}
    assert out["blocker_counts"] == {}
    assert not out["independent_GitHub_identity_authenticated"]
    assert not out["source_citations_independently_verified"]
    assert not out["G_M1_PASS"]
    assert not out["G_M2_PASS"]
    assert not out["GLOBAL_CERTIFIED"]


@pytest.mark.parametrize("attack", [
    "self_approved", "self_owner_approved", "self_certified",
    "digest", "additional_fake_cert", "choice_unknown", "duplicate_response",
    "deleted_case", "reorder", "market", "wrong_reviewer_sha", "tampered_candle",
])
def test_adversarial_responses_or_casebook_tamper_hard_fails(attack):
    reviewer, replies = _filled()
    casebook = list(copy.deepcopy(reviewer))
    answers = list(copy.deepcopy(replies))
    if attack == "self_approved":
        answers[0]["independent_reviewer_github_review_verified"] = True
    elif attack == "self_owner_approved":
        answers[0]["owner_github_approval_verified"] = True
    elif attack == "self_certified":
        answers[0]["methodology_gate_passed"] = True
    elif attack == "digest":
        answers[0]["reviewer_payload_sha256"] = "a" * 64
    elif attack == "additional_fake_cert":
        answers[0]["GLOBAL_CERTIFIED"] = True
    elif attack == "choice_unknown":
        answers[0]["human_choice"] = "EXECUTE"
    elif attack == "duplicate_response":
        answers[1] = answers[0]
    elif attack == "deleted_case":
        answers.pop(0)
    elif attack == "reorder":
        answers.reverse()
    elif attack == "market":
        casebook[0]["market"] = "USDJPY"
    elif attack == "wrong_reviewer_sha":
        answers[0]["must_verify_external_github_identity"] = False
    else:
        casebook[0]["closed_H4_C0_C1_C2"][0]["high_relative"] += 5
    with pytest.raises(ValueError):
        audit_g2_human_responses_structural_only(
            "AUDUSD", tuple(casebook), tuple(answers)
        )


@pytest.mark.parametrize("attack,block", [
    ("missing_reason", "MISSING_INDEPENDENT_CAUSAL_REASON"),
    ("missing_locator", "MISSING_SOURCE_OR_QORE_PROPOSAL_LOCATOR"),
    ("unlabeled_source", "SOURCE_PROVENANCE_KIND_UNLABELED"),
    ("missing_counterexample", "MISSING_COUNTEREXAMPLE_OR_EXPLICIT_NONE_RATIONALE"),
    ("mislabel_insufficient", "INSUFFICIENT_SOURCE_REQUIRES_EXPLICIT_GAP"),
    ("positive_with_only_gap", "POSITIVE_SELECTION_CANNOT_CITE_ONLY_SOURCE_GAP"),
])
def test_incomplete_human_reason_does_not_become_ready(attack, block):
    reviewer, replies = _filled()
    answers = list(copy.deepcopy(replies))
    if attack == "missing_reason":
        answers[0]["causal_reason_for_choice"] = ""
    elif attack == "missing_locator":
        answers[0]["source_quote_locator"] = None
    elif attack == "unlabeled_source":
        answers[0]["source_quote_locator"] = "some web URL with no source author"
    elif attack == "missing_counterexample":
        answers[0]["counterexample_if_any"] = ""
    elif attack == "mislabel_insufficient":
        answers[0]["source_quote_locator"] = "QORE_ENGINEERING:G2:v1"
    else:
        answers[0]["human_choice"] = "C0"
    out = audit_g2_human_responses_structural_only(
        "AUDUSD", reviewer, tuple(answers)
    )
    assert block in out["blocker_counts"]
    assert not out["structurally_complete_NOT_APPROVED"]
    assert not out["G_M1_PASS"]
