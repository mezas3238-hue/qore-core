"""R9 G2 reviewer input strips engine labels and separates sealed records."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_g2_independent_blind_review import (
    ALLOWED_CHOICES,
    build_g2_independent_review_packets,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

MARKET = CrtPureMarket.AUDUSD
EPOCH = datetime(2025, 6, 2, tzinfo=UTC)
H4 = timedelta(hours=4)


def case(opposing: bool = True) -> dict:
    candles = []
    for i in range(3):
        candles.append({
            "opened_at_utc": (EPOCH + i * H4).isoformat(),
            "open_relative": 100, "high_relative": 110 + i,
            "low_relative": 90 - i, "close_relative": 100,
        })
    return {
        "market": MARKET.value, "blind_case_id": "source-c0-c1-frozen",
        "source_event_id": "source-v3-eid-001",
        "parent_id": "parent-should-not-leak",
        "decision_clock_utc": (EPOCH + 3 * H4 + timedelta(minutes=45)).isoformat(),
        "c2_closed_at_utc": (EPOCH + 3 * H4).isoformat(),
        "c0_closed_h4": candles[0],
        "c1_closed_h4": candles[1],
        "c2_closed_h4": candles[2],
        "c0_direction": "BULLISH",
        "c1_direction": "BEARISH" if opposing else "BULLISH",
        "conflict_kind": "OPPOSITE" if opposing else "SAME",
        "selected_reference": None,
        "independent_reviewer_adjudicated": False,
        "owner_approval": False, "not_a_trade": True,
        "not_fresh_holdout": True,
    }


def packets(rows: tuple[dict, ...] | None = None):
    return build_g2_independent_review_packets(
        MARKET, (case(),) if rows is None else rows
    )


def test_human_reviewer_receives_candles_but_no_engine_decision_or_source_id() -> None:
    manifest, reviewer, sealed, empty = packets()
    assert manifest["reviewer_cases"] == 1
    assert manifest["engine_distribution_SEALED_ONLY"] == {"OPPOSITE": 1}
    assert len(reviewer) == len(sealed) == len(empty) == 1
    visible = reviewer[0]
    payload = json.dumps(visible, sort_keys=True).lower()
    for secret in (
        "source-v3-eid", "parent-should", "conflict_kind", "c0_direction",
        "c1_direction", "opposite", "bearish", "engine", "gm4", "outcome",
        "terminal", "sizing_performed", "profit", "g7",
    ):
        assert secret not in payload
    assert visible["closed_H4_C0_C1_C2"][0]["H4"] == "C0"
    assert visible["allowed_answer_choices"] == ALLOWED_CHOICES
    assert visible["reviewer_result"] is None
    assert sealed[0]["engine_conflict_kind"] == "OPPOSITE"
    assert sealed[0]["source_event_id"] == case()["source_event_id"]
    assert empty[0]["human_choice"] is None
    assert not empty[0]["methodology_gate_passed"]
    assert not manifest["G_M1_PASS"] and not manifest["GLOBAL_CERTIFIED"]


def test_review_hash_matches_exact_immutable_visible_payload() -> None:
    manifest, reviewer, sealed, templates = packets()
    raw = json.dumps(
        reviewer[0], sort_keys=True, separators=(",", ":")
    ).encode()
    assert sealed[0]["reviewer_payload_sha256"] == hashlib.sha256(raw).hexdigest()
    assert templates[0]["reviewer_payload_sha256"] == sealed[0][
        "reviewer_payload_sha256"
    ]
    assert manifest["sealed_packet_sha256"] != manifest["reviewer_packet_sha256"]


def test_changed_engine_labels_do_not_change_visible_reviewer_input() -> None:
    one = packets()[1][0]
    two = packets((case(opposing=False),))[1][0]
    assert one == two
    assert packets()[2][0]["engine_conflict_kind"] == "OPPOSITE"
    assert packets((case(opposing=False),))[2][0]["engine_conflict_kind"] == "SAME"


@pytest.mark.parametrize("tamper", [
    "future_H4", "noncontiguous_H4", "invalid_price", "forged_review",
    "bad_market", "duplicate", "contradict_engine_labels",
    "fake_owner", "wrong_c2_close",
])
def test_invalid_source_or_review_cannot_enter_reviewer_packet(tamper: str) -> None:
    x = copy.deepcopy(case())
    cases = (x,)
    if tamper == "future_H4":
        x["c2_closed_h4"]["opened_at_utc"] = (
            EPOCH + 5 * H4
        ).isoformat()
    elif tamper == "noncontiguous_H4":
        x["c1_closed_h4"]["opened_at_utc"] = (
            EPOCH + H4 + timedelta(minutes=5)
        ).isoformat()
    elif tamper == "invalid_price":
        x["c0_closed_h4"]["high_relative"] = 1
    elif tamper == "forged_review":
        x["independent_reviewer_adjudicated"] = True
    elif tamper == "bad_market":
        x["market"] = "USDJPY"
    elif tamper == "duplicate":
        cases = (x, copy.deepcopy(x))
    elif tamper == "contradict_engine_labels":
        x["conflict_kind"] = "SAME"
    elif tamper == "fake_owner":
        x["owner_approval"] = True
    else:
        x["c2_closed_at_utc"] = (EPOCH + 4 * H4).isoformat()
    with pytest.raises(ValueError):
        packets(cases)


def test_btcusd_source_is_frozen_and_empty_payload_is_rejected() -> None:
    with pytest.raises(ValueError, match="frozen"):
        build_g2_independent_review_packets(CrtPureMarket.BTCUSD, (case(),))
    with pytest.raises(ValueError, match="empty"):
        packets(())
