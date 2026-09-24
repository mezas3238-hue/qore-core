from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r124_targeted_source_retest as r124,
)


def test_r124_source_and_target_state_are_pinned() -> None:
    assert r124.SOURCE_R123_RUN_ID == 36057291367
    assert r124.SOURCE_R123_ARTIFACT_ID == 10832868254
    assert r124.SOURCE_R123_ARTIFACT_DIGEST == (
        "sha256:fe8f42308f272443732f2706ec9e8170"
        "fea66c9d8023d419aa388042d84e9bd1"
    )
    assert r124.TARGET_STATE == (
        "SWEEP_REVERSAL|PRIOR_DEEPER_THAN_FINAL_PS"
    )
    assert r124.EXPECTED_TARGET_STATE == {
        "5Y": 235,
        "2Y": 110,
        "R66": 101,
    }


def test_r124_target_predicate_is_exact() -> None:
    assert r124._is_target_state(
        mechanism="SWEEP_REVERSAL",
        relation="PRIOR_DEEPER_THAN_FINAL_PS",
    )
    assert not r124._is_target_state(
        mechanism="CLOSE_BREAKOUT",
        relation="PRIOR_DEEPER_THAN_FINAL_PS",
    )
    assert not r124._is_target_state(
        mechanism="SWEEP_REVERSAL",
        relation="NO_FAILED_ATTEMPT",
    )
