from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r131_daily_compressed_source_retest as r131,
)


def test_r131_source_and_target_are_pinned() -> None:
    assert r131.SOURCE_R130_RUN_ID == 36077074851
    assert r131.SOURCE_R130_ARTIFACT_ID == 10839674224
    assert r131.SOURCE_R130_ARTIFACT_DIGEST == (
        "sha256:5cbf36ba630f60af21726d5dc4259d6d"
        "8e2024f92d405a003a6c60ba5a64cfa5"
    )
    assert r131.TARGET_COHORT == (
        "CLOSE_BREAKOUT|NO_FAILED_ATTEMPT"
    )
    assert r131.TARGET_DAILY_RANGE_STATE == "compressed"
    assert r131.EXPECTED_TARGET == {
        "5Y": 104,
        "2Y": 50,
        "R66": 37,
    }


def test_r131_density_contract_is_canonical() -> None:
    assert r131.EXPECTED_CANONICAL == {
        "5Y": 2448,
        "2Y": 1017,
        "R66": 773,
    }
    assert r131.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
