"""G-M3 source-open safety contract. Synthetic cases do NOT certify G-M3."""

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_gm3_real_case_safety import (
    audit_blind_case,
)


def blind_case() -> dict[str, object]:
    return {
        "market": "AUDUSD",
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
    assert "model_1_reference_selection" in result["unresolved_source_concepts"]
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
