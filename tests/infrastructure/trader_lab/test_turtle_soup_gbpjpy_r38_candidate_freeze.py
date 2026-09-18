from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r38_candidate_freeze as freeze,
)


def test_r38_freeze_constants_are_exact() -> None:
    assert freeze.IDENTITY == "TURTLE_SOUP_GBPJPY_R38_STRUCTURAL_FRAGILITY_CANDIDATE_001"
    assert freeze.SOURCE_RUN_ID == 35373705221
    assert freeze.SOURCE_ARTIFACT_ID == 10559845896
    assert freeze.SOURCE_GIT_SHA == "93b887a257bef65b151983501d7d0017795f1040"


def test_r38_frozen_results_are_exact() -> None:
    assert freeze.EXPECTED_TRADES == 897
    assert freeze.EXPECTED_PF == "1.852918712035185462516517131"
    assert freeze.EXPECTED_DD == "5.06150896610739539086014902"
    assert freeze.EXPECTED_POSITIVE_ANNUAL_BLOCKS == 5
    assert freeze.EXPECTED_2Y_TRADES == 371
    assert freeze.EXPECTED_2Y_PF == "2.217710737671459829306457352"
    assert freeze.EXPECTED_2Y_DD == "3.25486421385985457309113347"
