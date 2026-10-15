"""G-M3 source-open safety contract. Synthetic cases do NOT certify G-M3."""

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_gm3_real_case_safety import (
    audit_blind_case,
)


def blind_case() -> dict[str, object]:
    return {
        "market": "AUDUSD",
        "parent_H4_direction_context": "BULLISH",
        "parent_H4_c3_opened_at_utc": "2025-03-03T10:00:00+00:00",
        "parent_H4_C1_ohlc": {"opened_at_utc": "2025-03-03T02:00:00+00:00"},
        "parent_H4_C2_ohlc": {"opened_at_utc": "2025-03-03T06:00:00+00:00"},
        "case_id": "fixture-causal-001",
        "decision_clock_utc": "2025-03-03T10:30:00+00:00",
        "is_execution_authorized": False,
        "future_C3_withheld_from_blind_file": True,
        "reference_level_selection": "UNRESOLVED_BY_PRIMARY_SOURCE",
        "author_model1_equivalence": "NOT_ADJUDICATED",
        "M15_observed_prefix_through_C2": [
            {
                "opened_at_utc": "2025-03-03T10:00:00+00:00",
                "open_relative": 100,
                "high_relative": 110,
                "low_relative": 90,
                "close_relative": 102,
            },
            {
                "opened_at_utc": "2025-03-03T10:15:00+00:00",
                "open_relative": 102,
                "high_relative": 109,
                "low_relative": 88,
                "close_relative": 103,
            },
        ],
    }


def test_real_case_adapter_abstains_if_model1_source_not_closed() -> None:
    result = audit_blind_case(blind_case())
    assert result["reason_action"] == "ABSTAIN"
    assert result["certification_router_action"] == "WAIT"
    assert result["certification_router_state"] == "UNRESOLVED"
    assert result["G_M4_missing_source_router_safety_checked"] is True
    assert result["G_M5_real_evidence_certificate_issued"] is False
    assert result["G_M5_forged_all_pass_certificate_issued"] is False
    assert result["G_M5_anti_forgery_safety_checked"] is True
    assert "THREE_SOURCE_RULE_OPEN:multiple_reference_priority" in (
        result["G_M5_source_primary_blockers"]
    )
    assert "THREE_SOURCE_RULE_OPEN:multiple_reference_priority" in result["unresolved_source_concepts"]
    assert result["G_M3_source_fidelity_certified"] is False
    assert result["no_profit_loss_or_sizing_used"] is True
    assert result["no_trade"] is True


def test_future_candle_or_sealed_reveal_cannot_contaminate_review() -> None:
    case = blind_case()
    case["C3_M5_reveal_after_independent_review"] = []
    with pytest.raises(ValueError, match="sealed future"):
        audit_blind_case(case)
    case = blind_case()
    case["M15_observed_prefix_through_C2"][1]["opened_at_utc"] = "2025-03-03T10:30:00+00:00"  # type: ignore[index]
    with pytest.raises(ValueError, match="future/partial"):
        audit_blind_case(case)


def test_spoofed_source_or_btc_market_rejected() -> None:
    case = blind_case()
    case["reference_level_selection"] = "CANONICAL"
    with pytest.raises(ValueError, match="unexpectedly claims"):
        audit_blind_case(case)
    case = deepcopy(blind_case())
    case["market"] = "BTCUSD"
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        audit_blind_case(case)


@pytest.mark.parametrize(
    ("field", "content"),
    (
        ("future_C3_known_close", 110),
        ("broker_fill", 0),
        ("cash_sizing", 1),
        ("after_c2_outcome", "WIN"),
        ("secret_reveal", "C3"),
    ),
)
def test_blind_review_disallows_unknown_payload_columns(
    field: str, content: object
) -> None:
    case = blind_case()
    case[field] = content
    with pytest.raises(ValueError, match="sealed future|unexpected blind case fields"):
        audit_blind_case(case)


def test_fake_h4_origin_is_detected_before_cognition() -> None:
    case = blind_case()
    case["parent_H4_C2_ohlc"] = {"opened_at_utc": "2025-03-03T05:00:00+00:00"}
    with pytest.raises(ValueError, match="noncausal or disconnected H4"):
        audit_blind_case(case)


def test_m15_prefix_must_begin_at_real_parent_c3_open() -> None:
    case = blind_case()
    case["parent_H4_c3_opened_at_utc"] = "2025-03-03T09:45:00+00:00"
    case["parent_H4_C2_ohlc"] = {"opened_at_utc": "2025-03-03T05:45:00+00:00"}
    case["parent_H4_C1_ohlc"] = {"opened_at_utc": "2025-03-03T01:45:00+00:00"}
    with pytest.raises(ValueError, match="disconnected from parent"):
        audit_blind_case(case)


def test_boolean_price_is_not_valid_integer_ohlc() -> None:
    case = blind_case()
    case["M15_observed_prefix_through_C2"][0]["open_relative"] = True  # type: ignore[index]
    with pytest.raises(ValueError, match="non-integer"):
        audit_blind_case(case)


def test_source_case_cannot_claim_fresh_holdout() -> None:
    case = blind_case()
    case["not_new_holdout"] = False
    with pytest.raises(ValueError, match="fresh holdout"):
        audit_blind_case(case)
