from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r44_candidate_freeze as r44,
)


def test_r44_binds_exact_r43_pass() -> None:
    assert r44.SOURCE_RUN_ID == 35357443440
    assert r44.SOURCE_ARTIFACT_ID == 10552052483
    assert r44.EXPECTED_TRADES == 907
    assert r44.EXPECTED_POSITIVE_ANNUAL_BLOCKS == 5
    assert r44.EXPECTED_POLICY == "R43_RANK2_025"
    assert r44.EXPECTED_SHORT_SCALE == "0.005"
    assert r44.EXPECTED_RANK2_SCALE == "0.25"
