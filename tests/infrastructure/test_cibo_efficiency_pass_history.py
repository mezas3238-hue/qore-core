from decimal import Decimal

from qore.infrastructure.cibo_efficiency_pass_history import (
    CiboEfficiencyPassHistory,
    append_efficiency_pass,
)
from qore.infrastructure.cibo_efficiency_pass_sensor import (
    CiboEfficiencyPassSnapshot,
)
from qore.infrastructure.cibo_maximum_capability_efficiency import (
    CiboMaximumCapabilityEvidence,
    build_maximum_capability_scorecard,
)


def _snapshot(pass_id: str, value: str) -> CiboEfficiencyPassSnapshot:
    v = Decimal(value)
    one = Decimal("1")
    evidence = CiboMaximumCapabilityEvidence(
        causal_utility_captured=v,
        causal_utility_available=one,
        realized_value_captured=v,
        realized_value_frontier=one,
        risk_adjusted_utility_captured=v,
        risk_adjusted_utility_frontier=one,
        positive_opportunities_captured=v,
        positive_opportunities_available=one,
        efficient_redeployments=v,
        eligible_redeployments=one,
        optionality_preserved_value=v,
        optionality_frontier_value=one,
        cognitive_value_captured=v,
        cognitive_value_available=one,
        lifecycle_value_captured=v,
        lifecycle_value_frontier=one,
        compound_value_captured=v,
        compound_value_frontier=one,
        portfolio_value_captured=v,
        portfolio_value_frontier=one,
        leverage_value_captured=v,
        leverage_value_frontier=one,
        twin_value_captured=v,
        twin_value_frontier=one,
        t14_redeployed_value=v,
        t14_redeployable_value=one,
    )
    return CiboEfficiencyPassSnapshot(
        pass_id=pass_id,
        scorecard=build_maximum_capability_scorecard(evidence),
    )


def test_history_tracks_best_latest_and_distance_to_target() -> None:
    history = CiboEfficiencyPassHistory()
    for pass_id, value in (
        ("P1", "0.80"),
        ("P2", "0.85"),
        ("P3", "0.83"),
    ):
        history = append_efficiency_pass(
            history,
            _snapshot(pass_id, value),
        )

    assert history.latest.pass_id == "P3"
    assert history.best.pass_id == "P2"
    assert history.target_distance == Decimal("0.1699")
    assert history.regression_count == 1
    assert history.clean_improvement_count == 1
    assert len(history.deltas) == 2
