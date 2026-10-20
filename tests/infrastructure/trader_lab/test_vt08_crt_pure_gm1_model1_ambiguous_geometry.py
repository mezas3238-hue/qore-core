"""Synthetic regression only; original-source eligibility is not certified."""

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_gm1_model1_ambiguous_geometry import (
    enumerate_case_model1_geometry,
)


def case() -> dict[str, object]:
    return {
        "schema": "qore.vt08.crt_pure.gm2_real_blinded_casebook.v1",
        "case_id": "test-case-dual-possible-ref",
        "market": "AUDUSD",
        "decision_clock_utc": "2025-03-03T10:30:00+00:00",
        "parent_H4_direction_context": "BEARISH",
        "parent_H4_c3_opened_at_utc": "2025-03-03T10:00:00+00:00",
        "parent_H4_C1_ohlc": {
            "opened_at_utc": "2025-03-03T02:00:00+00:00",
            "open_relative": 102, "high_relative": 108,
            "low_relative": 99, "close_relative": 104,
        },
        "parent_H4_C2_ohlc": {
            "opened_at_utc": "2025-03-03T06:00:00+00:00",
            "open_relative": 104, "high_relative": 110,
            "low_relative": 100, "close_relative": 106,
        },
        "M15_observed_prefix_through_C2": [
            {
                "opened_at_utc": "2025-03-03T10:00:00+00:00",
                "open_relative": 106, "high_relative": 112,
                "low_relative": 105, "close_relative": 109,
            },
            {
                "opened_at_utc": "2025-03-03T10:15:00+00:00",
                "open_relative": 108, "high_relative": 109,
                "low_relative": 102, "close_relative": 103,
            },
        ],
        "reference_level_selection": "UNRESOLVED_BY_PRIMARY_SOURCE",
        "author_model1_equivalence": "NOT_ADJUDICATED",
        "is_execution_authorized": False,
        "future_C3_withheld_from_blind_file": True,
        "not_new_holdout": True,
    }


def test_same_source_candle_confirms_against_two_unapproved_h4_levels() -> None:
    result = enumerate_case_model1_geometry(case())
    assert result["mechanical_source_candle_hypotheses"] == 2
    assert result["mechanical_confirmations_by_C2"] == 2
    assert len(result["reference_origins_with_observations"]) == 2
    assert {r["unapproved_reference"] for r in result["observations"]} == {
        "UNADJUDICATED_H4_C1", "UNADJUDICATED_H4_C2"
    }
    assert all(r["entry_authorized"] is False for r in result["observations"])
    assert all(r["source_event_authenticity"] is False for r in result["observations"])
    assert result["reference_selector_source_approved"] is False


def test_no_future_confirmation_is_counted() -> None:
    data = case()
    data["M15_observed_prefix_through_C2"][1]["close_relative"] = 107  # type: ignore[index]
    result = enumerate_case_model1_geometry(data)
    assert result["mechanical_source_candle_hypotheses"] == 2
    assert result["mechanical_confirmations_by_C2"] == 0


def test_future_and_economic_payload_is_rejected() -> None:
    for forbidden_key in ("future_C3", "trade_PnL", "position_lots"):
        data = deepcopy(case())
        data[forbidden_key] = 12
        with pytest.raises(ValueError, match="unexpected blind case"):
            enumerate_case_model1_geometry(data)


def test_geometry_cannot_access_future_close_at_decision_clock() -> None:
    data = case()
    data["M15_observed_prefix_through_C2"][1]["opened_at_utc"] = "2025-03-03T10:30:00+00:00"  # type: ignore[index]
    with pytest.raises(ValueError, match="future/partial"):
        enumerate_case_model1_geometry(data)
