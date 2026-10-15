"""Research-only pre-registered composite CRT; no sizing or broker entry."""

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_crt_three_source_candidate_v1 import (
    evaluate_three_source_case,
)


def fixture() -> dict[str, object]:
    return {
        "schema": "qore.vt08.crt_pure.gm2_real_blinded_casebook.v1",
        "case_id": "triad-dev-only",
        "market": "AUDUSD",
        "parent_H4_direction_context": "BULLISH",
        "parent_H4_c3_opened_at_utc": "2025-03-03T10:00:00+00:00",
        "parent_H4_C1_ohlc": {
            "opened_at_utc": "2025-03-03T02:00:00+00:00",
            "open_relative": 100, "high_relative": 110,
            "low_relative": 90, "close_relative": 105,
        },
        "parent_H4_C2_ohlc": {
            "opened_at_utc": "2025-03-03T06:00:00+00:00",
            "open_relative": 105, "high_relative": 108,
            "low_relative": 88, "close_relative": 95,
        },
        "M15_observed_prefix_through_C2": [
            {
                "opened_at_utc": "2025-03-03T10:00:00+00:00",
                "open_relative": 95, "high_relative": 99,
                "low_relative": 92, "close_relative": 97,
            },
            {
                "opened_at_utc": "2025-03-03T10:15:00+00:00",
                "open_relative": 97, "high_relative": 99,
                "low_relative": 90, "close_relative": 96,
            },
        ],
        "reference_level_selection": "UNRESOLVED_BY_PRIMARY_SOURCE",
        "author_model1_equivalence": "NOT_ADJUDICATED",
        "is_execution_authorized": False,
        "future_C3_withheld_from_blind_file": True,
        "not_new_holdout": True,
    }


def test_bullish_h4_m15_one_sided_reclaim_is_conceptual_only() -> None:
    result = evaluate_three_source_case(fixture())
    assert result["conceptual_state"] == "CONCEPTUAL_CANDIDATE"
    assert result["htf_direction_from_closed_candles"] == "BULLISH"
    assert result["ltf_direction_from_closed_candles"] == "BULLISH"
    assert result["h4_target_midpoint_double_relative"] == 200
    assert result["invalidating_m15_extreme_relative"] == 90
    assert result["not_trading_signal"] and result["not_certified"]
    assert result["no_capital_or_volume_authority"] and result["no_sizing_used"]


def test_bearish_h4_m15_validates_mirror_case() -> None:
    data = fixture()
    h4 = data["parent_H4_C2_ohlc"]  # type: ignore[assignment]
    h4.update({"high_relative": 112, "low_relative": 91, "close_relative": 105})
    m15 = data["M15_observed_prefix_through_C2"]  # type: ignore[assignment]
    m15[0].update({
        "open_relative": 105, "high_relative": 109,
        "low_relative": 100, "close_relative": 105,
    })
    m15[1].update({
        "open_relative": 105, "high_relative": 111,
        "low_relative": 100, "close_relative": 103,
    })
    result = evaluate_three_source_case(data)
    assert result["conceptual_state"] == "CONCEPTUAL_CANDIDATE"
    assert result["htf_direction_from_closed_candles"] == "BEARISH"


def test_opposite_micro_abstains_not_rearms() -> None:
    data = fixture()
    m15 = data["M15_observed_prefix_through_C2"]  # type: ignore[assignment]
    m15[1].update({"high_relative": 101, "low_relative": 92, "close_relative": 94})
    assert evaluate_three_source_case(data)["why"] == "M15_OPPOSES_H4_PARENT"


def test_no_one_side_parent_or_two_sided_parent_abstains() -> None:
    for high, low in ((108, 91), (112, 88)):
        data = fixture()
        h4 = data["parent_H4_C2_ohlc"]  # type: ignore[assignment]
        h4.update({"high_relative": high, "low_relative": low})
        assert evaluate_three_source_case(data)["conceptual_state"] == "ABSTAIN"


def test_consumed_target_abstains_even_if_micro_confirmation_exists() -> None:
    data = fixture()
    m15 = data["M15_observed_prefix_through_C2"]  # type: ignore[assignment]
    m15[0].update({
        "high_relative": 109, "low_relative": 100,
        "open_relative": 101, "close_relative": 104,
    })
    m15[1].update({
        "high_relative": 109, "low_relative": 98,
        "open_relative": 104, "close_relative": 105,
    })
    assert evaluate_three_source_case(data)["why"] == "H4_MIDPOINT_DOL_ALREADY_CONSUMED"


def test_future_sizing_and_unclosed_m15_rejected() -> None:
    for key in ("future_C3", "sizing_lots", "economic_PnL"):
        data = deepcopy(fixture())
        data[key] = 3
        with pytest.raises(ValueError, match="unexpected blind case"):
            evaluate_three_source_case(data)
    data = fixture()
    m15 = data["M15_observed_prefix_through_C2"]  # type: ignore[assignment]
    m15[1]["opened_at_utc"] = "2025-03-03T10:30:00+00:00"
    with pytest.raises(ValueError, match="future/partial"):
        evaluate_three_source_case(data)
