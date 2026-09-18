from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r36_candidate_freeze as r36,
)


def test_r36_freeze_binds_exact_passing_r35_evidence() -> None:
    assert r36.SOURCE_RUN_ID == 35370716933
    assert r36.SOURCE_ARTIFACT_ID == 10558517399
    assert r36.SOURCE_GIT_SHA == "03465666dc235e06002f189d4db476813150960e"
    assert r36.SELECTED_ENSEMBLE == "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
    assert r36.SELECTED_POLICY == "CONFIDENCE_100_050_010"


def test_r36_frozen_development_metrics() -> None:
    assert r36.EXPECTED_TRADES == 371
    assert r36.EXPECTED_PF == "1.917321619841829026960123251"
    assert r36.EXPECTED_DD == "5.34575969539718361901697478"
    assert r36.EXPECTED_TOTAL == "61.20501737968874858251138689"
