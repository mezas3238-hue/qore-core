from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r38_candidate_freeze as freeze,
)


def test_r38_freeze_constants_are_exact() -> None:
    assert freeze.EXPECTED_TRADES == 863
    assert freeze.EXPECTED_PF == "2.958703779880710298093151891"
    assert freeze.EXPECTED_DD == "5.824645307409961208739068649"
    assert freeze.IDENTITY == "TURTLE_SOUP_EURUSD_R38_STRUCTURAL_RISK_CANDIDATE_001"
