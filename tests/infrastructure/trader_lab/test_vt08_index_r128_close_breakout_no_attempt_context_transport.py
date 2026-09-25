from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r128_close_breakout_no_attempt_context_transport as r128,
)


def test_r128_source_and_cohort_are_pinned() -> None:
    assert r128.SOURCE_R127_RUN_ID == 36075356615
    assert r128.SOURCE_R127_ARTIFACT_ID == 10839628548
    assert r128.SOURCE_R127_ARTIFACT_DIGEST == (
        "sha256:e604bf6828ab9b38d1d88f239ff36ffd"
        "67d46cb37755f0154c0038fb4474877b"
    )
    assert r128.COHORT_STATE == (
        "CLOSE_BREAKOUT|NO_FAILED_ATTEMPT"
    )
    assert r128.EXPECTED_COHORT == {
        "5Y": 578,
        "2Y": 230,
        "R66": 161,
    }
    assert r128.MIN_REPORT_SAMPLE == 20


def test_r128_dimensions_reuse_frozen_r105_vocabulary() -> None:
    assert "cisd_latency_bucket" in r128.r105.DIMENSIONS
    assert "continuation_latency_bucket" in r128.r105.DIMENSIONS
    assert "cross_index_state" in r128.r105.DIMENSIONS
    assert "current_source_day_body_alignment" in r128.r105.DIMENSIONS
