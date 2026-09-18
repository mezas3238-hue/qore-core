from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r38_candidate_freeze as r38,
)


def test_r38_freeze_binds_exact_r37_candidate() -> None:
    assert r38.SOURCE_RUN_ID == 35352145888
    assert r38.SOURCE_ARTIFACT_ID == 10550221115
    assert r38.EXPECTED_TRADES == 374
    assert r38.FAMILY_SET == "R37_G25_FIXED"
    assert r38.STRUCTURAL_POLICY == "SQ3_H1_BALANCED"
    assert r38.DRAWDOWN_GOVERNOR == "DD_1_3_SCALE_075_025"


def test_r38_freeze_keeps_holdout_sealed_by_contract() -> None:
    assert r38.EXPECTED_PF == "1.914184192504076803125810726"
    assert r38.EXPECTED_DD == "4.650727254116239059338971594"
