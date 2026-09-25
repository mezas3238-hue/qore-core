from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r130_low_concurrent_source_retest as r130,
)


def test_r130_source_and_target_are_pinned() -> None:
    assert r130.SOURCE_R129_RUN_ID == 36076610569
    assert r130.SOURCE_R129_ARTIFACT_ID == 10839404006
    assert r130.SOURCE_R129_ARTIFACT_DIGEST == (
        "sha256:db94ff3d983c35e05aa71b3f9133fc8e"
        "cb4215d494cf06c8ed1784c6df25677d"
    )
    assert r130.TARGET_COHORT == (
        "CLOSE_BREAKOUT|NO_FAILED_ATTEMPT"
    )
    assert r130.TARGET_CONCURRENT_PRESSURE == "LOW"
    assert r130.EXPECTED_TARGET == {
        "5Y": 217,
        "2Y": 95,
        "R66": 55,
    }


def test_r130_density_contract_is_canonical() -> None:
    assert r130.EXPECTED_CANONICAL == {
        "5Y": 2448,
        "2Y": 1017,
        "R66": 773,
    }
    assert r130.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
