from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r125_targeted_persistent_cisd as r125,
)


def test_r125_sources_and_target_are_pinned() -> None:
    assert r125.SOURCE_R124_RUN_ID == 36058115950
    assert r125.SOURCE_R124_ARTIFACT_ID == 10832559781
    assert r125.SOURCE_R124_ARTIFACT_DIGEST == (
        "sha256:e77c6302cf6b0b6e94332bc9ea0bad4f"
        "308ceccf85d111818e08e306b2cb7865"
    )
    assert r125.TARGET_STATE == (
        "SWEEP_REVERSAL|PRIOR_DEEPER_THAN_FINAL_PS"
    )
    assert r125.EXPECTED_TARGET_STATE == {
        "5Y": 235,
        "2Y": 110,
        "R66": 101,
    }


def test_r125_uses_frozen_persistent_semantics() -> None:
    assert r125.r78.IDENTITY == (
        "VT08_INDEX_R78_PERSISTENT_CISD_SERIES_RECOVERY_FALSIFICATION_001"
    )
    assert r125.r108.TARGET_R == r125.Decimal("2.5")
