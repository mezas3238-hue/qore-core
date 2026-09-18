from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r36_candidate_freeze as freeze,
)


def test_r36_freeze_constants_are_exact() -> None:
    assert freeze.IDENTITY == "TURTLE_SOUP_EURUSD_R36_FRAGILITY_CANDIDATE_001"
    assert freeze.SELECTED_FAMILY_SET == "R36_F235_FROZEN"
    assert freeze.SELECTED_GOVERNOR == "FRAGILITY_050_025_010"
    assert freeze.EXPECTED_TRADES == 366
    assert freeze.EXPECTED_DD == "3.83972573211060055575442915"
