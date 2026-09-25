from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r121_r120_cohort_risk_ablation as r121,
)


def test_r121_source_and_surface_are_pinned() -> None:
    assert r121.SOURCE_R120_RUN_ID == 35792388753
    assert r121.SOURCE_R120_ARTIFACT_ID == 10722073618
    assert r121.SOURCE_R120_ARTIFACT_DIGEST == (
        "sha256:f9d86e1347a5634686d26d1dd9e1975"
        "b240146acd348e0294e45fd3369eaf3bd"
    )
    assert r121.EXPECTED_CANONICAL == {
        "5Y": 2448,
        "2Y": 1017,
        "R66": 773,
    }
    assert r121.EXPECTED_COHORT == {
        "5Y": 504,
        "2Y": 178,
        "R66": 149,
    }


def test_r121_transport_state_is_exact_and_bounded() -> None:
    assert r121._transport_state(
        "CLOSE_BREAKOUT",
        "PRIOR_DEEPER_THAN_FINAL_PS",
    )
    assert not r121._transport_state(
        "SWEEP_REVERSAL",
        "PRIOR_DEEPER_THAN_FINAL_PS",
    )
    assert not r121._transport_state(
        "CLOSE_BREAKOUT",
        "NO_FAILED_ATTEMPT",
    )


def test_r121_policy_reuses_existing_r102_r58_contracts() -> None:
    assert r121.CONTROL_POLICY_ID == "EXPLICIT_FULL_R58_STANDARD_BASE"
    assert r121.VARIANT_POLICY_ID == (
        "R120_CLOSE_BREAKOUT_PRIOR_DEEPER_R58_PROMOTION"
    )
    assert r102.MIN_EFFECTIVE_WEIGHT == r55.MIN_EFFECTIVE_WEIGHT
    assert r102.MAX_REQUESTED_WEIGHT == r55.MAX_REQUESTED_WEIGHT
    assert r102.PORTFOLIO_BUDGET_R == r55.PORTFOLIO_BUDGET_R
