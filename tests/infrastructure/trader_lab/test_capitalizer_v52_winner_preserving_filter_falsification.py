from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_v52_winner_preserving_filter_falsification import (
    EXPECTANCY_MIN_EXCLUSIVE,
    PF_EXISTENCE_MIN_EXCLUSIVE,
    WINNER_COUNT_PRESERVATION_MIN,
    WINNER_R_PRESERVATION_MIN,
)


def test_v52_thresholds_match_research_contract() -> None:
    assert WINNER_COUNT_PRESERVATION_MIN == Decimal("0.80")
    assert WINNER_R_PRESERVATION_MIN == Decimal("0.90")
    assert PF_EXISTENCE_MIN_EXCLUSIVE == Decimal("1")
    assert EXPECTANCY_MIN_EXCLUSIVE == Decimal("0")
