from dataclasses import replace
from decimal import Decimal

from qore.infrastructure.cibo_efficiency_pass_sensor import (
    CiboEfficiencyPassSnapshot,
    CiboEfficiencyTrend,
    compare_efficiency_passes,
)
from qore.infrastructure.cibo_maximum_capability_efficiency import (
    CiboMaximumCapabilityEvidence,
    build_maximum_capability_scorecard,
)


def _evidence(value: Decimal) -> CiboMaximumCapabilityEvidence:
    one = Decimal("1")
    return CiboMaximumCapabilityEvidence(
        causal_utility_captured=value,
        causal_utility_available=one,
        realized_value_captured=value,
        realized_value_frontier=one,
        risk_adjusted_utility_captured=value,
        risk_adjusted_utility_frontier=one,
        positive_opportunities_captured=value,
        positive_opportunities_available=one,
        efficient_redeployments=value,
        eligible_redeployments=one,
        optionality_preserved_value=value,
        optionality_frontier_value=one,
        cognitive_value_captured=value,
        cognitive_value_available=one,
        lifecycle_value_captured=value,
        lifecycle_value_frontier=one,
        compound_value_captured=value,
        compound_value_frontier=one,
        portfolio_value_captured=value,
        portfolio_value_frontier=one,
        leverage_value_captured=value,
        leverage_value_frontier=one,
        twin_value_captured=value,
        twin_value_frontier=one,
        t14_redeployed_value=value,
        t14_redeployable_value=one,
    )


def test_efficiency_sensor_measures_exact_pass_improvement() -> None:
    before = CiboEfficiencyPassSnapshot(
        pass_id="PASS_001",
        scorecard=build_maximum_capability_scorecard(
            _evidence(Decimal("0.80"))
        ),
    )
    after = CiboEfficiencyPassSnapshot(
        pass_id="PASS_002",
        scorecard=build_maximum_capability_scorecard(
            _evidence(Decimal("0.85"))
        ),
    )

    delta = compare_efficiency_passes(before, after)

    assert delta.sovereign_absolute_delta == Decimal("0.05")
    assert delta.sovereign_basis_points_delta == Decimal("500")
    assert delta.sovereign_trend is CiboEfficiencyTrend.IMPROVED
    assert delta.improved_dimensions == 13
    assert delta.regressed_dimensions == 0
    assert delta.improved_without_regression is True


def test_one_regressed_dimension_blocks_clean_improvement_signal() -> None:
    base = _evidence(Decimal("0.80"))
    before = CiboEfficiencyPassSnapshot(
        pass_id="PASS_A",
        scorecard=build_maximum_capability_scorecard(base),
    )
    mixed = replace(
        _evidence(Decimal("0.90")),
        portfolio_value_captured=Decimal("0.79"),
    )
    after = CiboEfficiencyPassSnapshot(
        pass_id="PASS_B",
        scorecard=build_maximum_capability_scorecard(mixed),
    )

    delta = compare_efficiency_passes(before, after)

    assert delta.regressed_dimensions == 1
    assert delta.weakest_dimension_after == "PORTFOLIO_EFFICIENCY"
    assert delta.sovereign_after == Decimal("0.79")
    assert delta.sovereign_trend is CiboEfficiencyTrend.REGRESSED
    assert delta.improved_without_regression is False


def test_target_is_only_proven_when_after_pass_reaches_9999() -> None:
    before = CiboEfficiencyPassSnapshot(
        pass_id="PASS_998",
        scorecard=build_maximum_capability_scorecard(
            _evidence(Decimal("0.9998"))
        ),
    )
    after = CiboEfficiencyPassSnapshot(
        pass_id="PASS_999",
        scorecard=build_maximum_capability_scorecard(
            _evidence(Decimal("0.9999"))
        ),
    )

    delta = compare_efficiency_passes(before, after)

    assert delta.target_proven_after is True
    assert delta.sovereign_basis_points_delta == Decimal("1")
