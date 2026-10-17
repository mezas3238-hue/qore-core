"""Adversarial cognition recognizes confirmed CRT but cannot grant authority."""
from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_gm3_cognitive_replay import (
    audit_v3_positive_cognition,
)


def _record() -> dict[str, object]:
    return {
        "schema": "qore.vt08.crt_three_source.v3.third_candle_development.v1",
        "policy_id": "VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE",
        "market": "AUDUSD",
        "source_event_id": "v3-qualitative-event",
        "c3_H4_opened_at_utc": "2025-03-03T08:00:00+00:00",
        "year_utc": "2025",
        "parent_direction": "BULLISH",
        "decision_clock_utc": "2025-03-03T08:45:00+00:00",
        "m15_confirmed_triples_checked": 1,
        "opposing_micro_patterns": 0,
        "structural_invalidation_price_if_candidate": "90",
        "conceptual_state": "CONCEPTUAL_CANDIDATE_V3",
        "why": "H4_PURGE_THEN_M15_SOURCE_AND_BODY_CONFIRM",
        "source_authority_adjudicated": False,
        "independent_method_review_complete": False,
        "not_a_trade": True,
        "no_sizing_or_capital_authority": True,
        "prior_dev_sample_not_fresh_holdout": True,
    }


def test_real_source_contract_positive_recognition_but_no_entry() -> None:
    result = audit_v3_positive_cognition(_record())
    assert result["causal_source_event_detected"] is True
    assert result["causal_confirmation_recognized"] is True
    assert result["cognitive_action"] == "ABSTAIN"
    assert "CRT_CONFIRMATION_COMPLETE" in result["reason_why"]
    assert "CRT_SOURCE_STRATEGY_NOT_CLOSED" in result["reason_why"]
    assert result["no_sizing"] and result["no_broker_order"]
    assert result["cognition_GM3_pass"] is False
    assert result["source_authority_claimed"] is False


def test_unexpected_future_or_financial_field_rejected() -> None:
    for key in ("future_C3_close", "position_lots", "profit_factor"):
        sample = _record()
        sample[key] = 1
        with pytest.raises(ValueError, match="unknown or future/sizing"):
            audit_v3_positive_cognition(sample)


def test_fake_reviewer_signature_or_broker_order_rejected() -> None:
    for key, value in (
        ("source_authority_adjudicated", True),
        ("independent_method_review_complete", True),
        ("not_a_trade", False),
        ("no_sizing_or_capital_authority", False),
    ):
        sample = _record()
        sample[key] = value
        with pytest.raises(ValueError, match="forge review/trading"):
            audit_v3_positive_cognition(sample)


def test_c3_future_or_no_closed_candle_cannot_be_declared_causal() -> None:
    for clock in (
        "2025-03-03T07:45:00+00:00",
        "2025-03-03T12:00:00+00:00",
        "2025-03-03T08:37:00+00:00",
    ):
        sample = _record()
        sample["decision_clock_utc"] = clock
        with pytest.raises(ValueError, match="close causally"):
            audit_v3_positive_cognition(sample)


def test_unapproved_source_policy_cannot_be_spoofed() -> None:
    sample = deepcopy(_record())
    sample["policy_id"] = "ROMEO_APPROVED_PRIMARY_2026"
    with pytest.raises(ValueError, match="policy mismatch"):
        audit_v3_positive_cognition(sample)
    sample = _record()
    sample["market"] = "BTCUSD"
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        audit_v3_positive_cognition(sample)


def test_wait_case_cannot_impersonate_positive_model1_confirmation() -> None:
    sample = _record()
    sample["conceptual_state"] = "WAIT_M15"
    with pytest.raises(ValueError, match="confirmed V3"):
        audit_v3_positive_cognition(sample)
