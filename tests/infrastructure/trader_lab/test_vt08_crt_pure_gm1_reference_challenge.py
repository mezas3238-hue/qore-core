"""Reference-dispute packet is diagnostic and must NEVER choose old levels."""

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_gm1_reference_challenge import (
    enumerate_reference_dispute,
)


def blind_case() -> dict[str, object]:
    return {
        "case_id": "case-1",
        "market": "AUDUSD",
        "is_execution_authorized": False,
        "future_C3_withheld_from_blind_file": True,
        "not_new_holdout": True,
        "reference_level_selection": "UNRESOLVED_BY_PRIMARY_SOURCE",
        "author_model1_equivalence": "NOT_ADJUDICATED",
        "parent_H4_direction_context": "BULLISH",
        "parent_H4_c3_opened_at_utc": "2025-03-03T10:00:00+00:00",
        "parent_H4_C1_ohlc": {
            "opened_at_utc": "2025-03-03T02:00:00+00:00",
            "open_relative": 100,
            "high_relative": 108,
            "low_relative": 89,
            "close_relative": 103,
        },
        "parent_H4_C2_ohlc": {
            "opened_at_utc": "2025-03-03T06:00:00+00:00",
            "open_relative": 103,
            "high_relative": 110,
            "low_relative": 91,
            "close_relative": 105,
        },
        "decision_clock_utc": "2025-03-03T10:30:00+00:00",
        "M15_observed_prefix_through_C2": [
            {
                "opened_at_utc": "2025-03-03T10:00:00+00:00",
                "open_relative": 105,
                "high_relative": 109,
                "low_relative": 94,
                "close_relative": 106,
            },
            {
                "opened_at_utc": "2025-03-03T10:15:00+00:00",
                "open_relative": 106,
                "high_relative": 108,
                "low_relative": 93,
                "close_relative": 104,
            },
        ],
    }


def test_two_causal_h4_extrema_are_preserved_without_source_choice() -> None:
    result = enumerate_reference_dispute(blind_case())
    assert result["distinct_raw_price_count"] == 2
    refs = result["two_raw_h4_extrema"]
    assert [ref["raw_extremum_relative"] for ref in refs] == [89, 91]
    assert [ref["origin"] for ref in refs] == ["H4_C1", "H4_C2"]
    assert result["source_authorized_selection"] is None
    assert result["selection_verdict"] == "UNRESOLVED_BY_PRIMARY_SOURCE"
    assert result["safety_audit_action"] == "ABSTAIN"
    assert all(ref["certified_old_crt_level"] is False for ref in refs)


def test_bearish_opens_two_old_high_reference_questions() -> None:
    case = blind_case()
    case["parent_H4_direction_context"] = "BEARISH"
    result = enumerate_reference_dispute(case)
    assert [ref["raw_extremum_relative"] for ref in result["two_raw_h4_extrema"]] == [
        108,
        110,
    ]


def test_equal_prices_do_not_prove_source_selected_level() -> None:
    case = blind_case()
    case["parent_H4_C2_ohlc"]["low_relative"] = 89  # type: ignore[index]
    result = enumerate_reference_dispute(case)
    assert result["distinct_raw_price_count"] == 1
    assert len(result["two_raw_h4_extrema"]) == 2
    assert result["source_authorized_selection"] is None


def test_untrusted_future_or_sizing_payload_blocks_packet_generation() -> None:
    for field in ("future_C3_reveal", "risk_per_trade", "trade_PnL"):
        case = deepcopy(blind_case())
        case[field] = 42
        with pytest.raises(ValueError, match="sealed future|unexpected blind case"):
            enumerate_reference_dispute(case)


def test_future_origin_cannot_be_labelled_old_level() -> None:
    case = blind_case()
    case["parent_H4_C1_ohlc"]["opened_at_utc"] = "2025-03-03T11:00:00+00:00"  # type: ignore[index]
    with pytest.raises(ValueError, match="noncausal or disconnected H4"):
        enumerate_reference_dispute(case)
