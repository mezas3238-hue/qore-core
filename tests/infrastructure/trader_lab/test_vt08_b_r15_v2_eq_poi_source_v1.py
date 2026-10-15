"""R15 source-first EQ branch and POI order, adversarial test coverage."""
from __future__ import annotations

from decimal import Decimal as D

import pytest

from qore.infrastructure.trader_lab.vt08_b_r15_v2_eq_poi_source_v1 import (
    POI_HIERARCHY,
    bullish_c2_eq_conditional,
    continuation_poi_priority,
)


def test_bullish_c2_full_eq_not_close_to_low() -> None:
    result = bullish_c2_eq_conditional(
        opened=D("100"), high=D("112"), low=D("95"), closed=D("104"),
    )
    assert result["source_EQ_if_swing_is_bullish"] == "103.5"
    assert result["source_EQ_if_swing_is_bearish"] == "99.5"
    assert result["counterfactual_wrong_close_to_low_for_bullish_swing"]
    assert result["chosen_trade_EQ"] is None
    assert result["chosen_author_swing_identity"] is None


def test_full_vs_close_to_low_equal_when_close_at_high() -> None:
    result = bullish_c2_eq_conditional(
        opened=D("100"), high=D("110"), low=D("95"), closed=D("110"),
    )
    assert not result["counterfactual_wrong_close_to_low_for_bullish_swing"]


@pytest.mark.parametrize("case", [
    dict(opened=D("100"), high=D("103"), low=D("99"), closed=D("98")),
    dict(opened=D("100"), high=D("103"), low=D("99"), closed=D("100")),
    dict(opened=D("100"), high=D("103"), low=D("99"), closed=D("99.5")),
])
def test_nonbullish_or_impossible_candle_fails(case: dict) -> None:
    with pytest.raises(ValueError, match="bullish body|physically impossible"):
        bullish_c2_eq_conditional(**case)


def test_author_poi_order_and_fvg_first() -> None:
    assert POI_HIERARCHY == ("FVG", "SWING_HIGH_LOW", "CISD_RETEST")
    out = continuation_poi_priority(
        {"FVG": 1, "SWING_HIGH_LOW": 1, "CISD_RETEST": 1},
        protected_swing_author_validated=True,
    )
    assert out["highest_available_tier"] == "FVG"
    assert out["chosen_poi"] is None


def test_poi_fallback_to_swing_then_cisd() -> None:
    quantities = {"FVG": 0, "SWING_HIGH_LOW": 1, "CISD_RETEST": 1}
    assert continuation_poi_priority(
        quantities, protected_swing_author_validated=True,
    )["highest_available_tier"] == "SWING_HIGH_LOW"
    quantities["SWING_HIGH_LOW"] = 0
    assert continuation_poi_priority(
        quantities, protected_swing_author_validated=True,
    )["highest_available_tier"] == "CISD_RETEST"


def test_same_tier_ambiguity_remains_unknown() -> None:
    result = continuation_poi_priority(
        {"FVG": 2, "SWING_HIGH_LOW": 1, "CISD_RETEST": 0},
        protected_swing_author_validated=True,
    )
    assert result["status"] == "D_MULTIPLE_SAME_TIER_OBJECTS"
    assert result["chosen_poi"] is None


def test_no_unverified_protected_swing_bypass() -> None:
    result = continuation_poi_priority(
        {"FVG": 1, "SWING_HIGH_LOW": 0, "CISD_RETEST": 0},
        protected_swing_author_validated=False,
    )
    assert result["status"] == "D_PROTECTED_SWING_UNVERIFIED"
    assert result["chosen_poi"] is None


@pytest.mark.parametrize("counts", [
    {"FVG": True, "SWING_HIGH_LOW": 0, "CISD_RETEST": 0},
    {"FVG": -1, "SWING_HIGH_LOW": 0, "CISD_RETEST": 0},
    {"FVG": 1, "SWING_HIGH_LOW": 0},
    {"FVG": 1, "SWING_HIGH_LOW": 0, "CISD_RETEST": 0, "OWNER": 1},
])
def test_bad_poi_counts_rejected(counts: dict) -> None:
    with pytest.raises(ValueError, match="invalid"):
        continuation_poi_priority(
            counts, protected_swing_author_validated=True,
        )


def test_no_poi_no_trade_choice() -> None:
    result = continuation_poi_priority(
        {"FVG": 0, "SWING_HIGH_LOW": 0, "CISD_RETEST": 0},
        protected_swing_author_validated=True,
    )
    assert result["status"] == "NO_SOURCE_POI_AVAILABLE"
    assert result["chosen_poi"] is None
